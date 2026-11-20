import re
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.config import (
    ACCESS_COOKIE_NAME,
    CSRF_COOKIE_NAME,
    COOKIE_SECURE,
    COOKIE_SAMESITE,
    PASSWORD_RESET_EXPIRY_MINUTES,
    JWT_EXPIRY_HOURS,
    JWT_REMEMBER_DAYS,
)
from app.database import (
    get_user_by_email,
    get_user_by_id,
    create_user,
    update_user_last_login,
    update_user_profile,
    delete_user_account,
    get_user_preferences,
    create_session,
    get_session,
    revoke_session,
    revoke_all_user_sessions,
    create_password_reset,
    get_password_reset,
    mark_password_reset_used,
)
from app.security import (
    hash_password,
    verify_password,
    validate_password_strength,
    create_access_token,
    decode_access_token,
    generate_reset_token,
    hash_reset_token,
    generate_csrf_token,
    verify_csrf,
    send_password_reset_notification,
)
from app.limiter import enforce_rate_limit
from app.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    PreferencesResponse,
    UserMeResponse,
    UserUpdateRequest,
    DeleteAccountRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    AuthMessageResponse,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


# ==============================================================================
# Authentication Dependencies
# ==============================================================================

def get_current_user_optional(request: Request) -> Optional[sqlite3.Row]:
    """
    Optional authentication dependency.
    Extracts user from cookie or Authorization header. Returns None if unauthenticated.
    """
    token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        return None

    jti = payload.get("jti")
    if not jti:
        return None

    # Verify session is not revoked
    session = get_session(jti)
    if not session or session["revoked_at"] is not None:
        return None

    # Check expiration
    expires_at = datetime.fromisoformat(session["expires_at"])
    if expires_at < datetime.now(timezone.utc):
        return None

    user_id = int(payload.get("sub", 0))
    user = get_user_by_id(user_id)
    return user


def get_current_user(request: Request) -> sqlite3.Row:
    """
    Required authentication dependency.
    Raises 401 if not authenticated or session is invalid/revoked.
    """
    user = get_current_user_optional(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def _build_user_response(user: sqlite3.Row) -> UserResponse:
    return UserResponse(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        created_at=user["created_at"],
        last_login_at=user["last_login_at"],
    )


def _build_preferences_response(prefs: Optional[sqlite3.Row]) -> PreferencesResponse:
    if not prefs:
        return PreferencesResponse()
    try:
        notify_dict = json.loads(prefs["notify_settings"]) if prefs["notify_settings"] else {}
    except Exception:
        notify_dict = {}
    return PreferencesResponse(
        language=prefs["language"] or "en",
        large_text=bool(prefs["large_text"]),
        retain_masked_text=bool(prefs["retain_masked_text"]),
        notify_settings=notify_dict,
    )


# ==============================================================================
# Auth Routes
# ==============================================================================

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(req: UserRegisterRequest, request: Request, response: Response):
    """
    Registers a new user account.
    - Rate limit: 3 registrations/hour/IP
    - Validates email format and password strength
    - Sets authentication & CSRF cookies upon creation
    """
    # Rate limit: 3 per hour per IP
    enforce_rate_limit(request, key_prefix="auth:register", limit=3, window_seconds=3600)

    clean_email = req.email.strip().lower()
    if not EMAIL_REGEX.match(clean_email):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid email address format.",
        )

    # Password validation
    validate_password_strength(req.password, email=clean_email)

    # Check for existing email
    existing = get_user_by_email(clean_email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    pwd_hash = hash_password(req.password)
    user_id = create_user(
        email=clean_email,
        name=req.name.strip(),
        password_hash=pwd_hash,
    )

    user = get_user_by_id(user_id)

    # Automatically log in the newly registered user
    token, jti, expires_at = create_access_token(user["id"], user["email"], remember_me=False)
    create_session(jti, user["id"], expires_at)
    update_user_last_login(user["id"])

    # Set access token cookie
    max_age_seconds = JWT_EXPIRY_HOURS * 3600
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=token,
        max_age=max_age_seconds,
        httponly=True,
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
        path="/",
    )

    # Set CSRF token cookie (readable by JS)
    csrf_token = generate_csrf_token()
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=max_age_seconds,
        httponly=False,
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
        path="/",
    )

    return _build_user_response(user)


@router.post("/login", response_model=UserResponse)
async def login_user(req: UserLoginRequest, request: Request, response: Response):
    """
    Authenticates a user with email and password.
    - Rate limit: 5 login attempts/min per IP+email
    - Generic error message to prevent account enumeration
    - Issues HttpOnly JWT cookie and readable CSRF cookie
    """
    clean_email = req.email.strip().lower()

    # Rate limit: 5 attempts per minute per IP + email
    enforce_rate_limit(
        request,
        key_prefix="auth:login",
        limit=5,
        window_seconds=60,
        extra_key=clean_email,
    )

    user = get_user_by_email(clean_email)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Successful login: issue JWT and session
    token, jti, expires_at = create_access_token(user["id"], user["email"], remember_me=req.remember_me)
    create_session(jti, user["id"], expires_at)
    update_user_last_login(user["id"])

    max_age_seconds = (JWT_REMEMBER_DAYS if req.remember_me else JWT_EXPIRY_HOURS) * 3600
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=token,
        max_age=max_age_seconds,
        httponly=True,
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
        path="/",
    )

    csrf_token = generate_csrf_token()
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=max_age_seconds,
        httponly=False,
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
        path="/",
    )

    # Return refreshed user record
    updated_user = get_user_by_id(user["id"])
    return _build_user_response(updated_user)


@router.post("/logout", response_model=AuthMessageResponse)
async def logout_user(request: Request, response: Response):
    """
    Logs out the user:
    - Revokes current token JTI in database
    - Clears access and CSRF cookies
    """
    token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if token:
        payload = decode_access_token(token)
        if payload and payload.get("jti"):
            revoke_session(payload["jti"])

    response.delete_cookie(ACCESS_COOKIE_NAME, path="/")
    response.delete_cookie(CSRF_COOKIE_NAME, path="/")

    return AuthMessageResponse(status="ok", message="Logged out successfully.")


@router.post("/forgot-password", response_model=AuthMessageResponse)
async def forgot_password(req: ForgotPasswordRequest, request: Request):
    """
    Initiates password reset workflow.
    - Rate limit: 3 requests/hour per IP+email
    - Generic response: always returns success without leaking whether email exists
    - Single-use hashed token with 30-minute expiration
    - In dev mode: prints reset link to server console
    """
    clean_email = req.email.strip().lower()
    enforce_rate_limit(request, key_prefix="auth:forgot", limit=3, window_seconds=3600, extra_key=clean_email)

    user = get_user_by_email(clean_email)
    if user:
        raw_token, token_hash = generate_reset_token()
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=PASSWORD_RESET_EXPIRY_MINUTES)).isoformat()
        create_password_reset(token_hash, user["id"], expires_at)

        reset_link = f"http://localhost:8000/#/reset-password?token={raw_token}"
        try:
            send_password_reset_notification(user["email"], reset_link)
        except NotImplementedError:
            # Pluggable stub for production if email is not configured
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Email service is not configured on this server.",
            )

    return AuthMessageResponse(
        status="ok",
        message="If an account exists with this email, password reset instructions have been sent.",
    )


@router.post("/reset-password", response_model=AuthMessageResponse)
async def reset_password(req: ResetPasswordRequest, request: Request):
    """
    Completes password reset with a valid token.
    - Verifies token hash, expiration, and single-use status
    - Validates new password strength
    - Revokes all existing user sessions upon password reset
    """
    enforce_rate_limit(request, key_prefix="auth:reset", limit=5, window_seconds=900)

    token_hash = hash_reset_token(req.token)
    reset_entry = get_password_reset(token_hash)

    if not reset_entry or reset_entry["used_at"] is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already used password reset token.",
        )

    expires_at = datetime.fromisoformat(reset_entry["expires_at"])
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token has expired. Please request a new one.",
        )

    user = get_user_by_id(reset_entry["user_id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    validate_password_strength(req.new_password, email=user["email"])
    new_hash = hash_password(req.new_password)

    update_user_profile(user["id"], password_hash=new_hash)
    mark_password_reset_used(token_hash)
    revoke_all_user_sessions(user["id"])

    return AuthMessageResponse(
        status="ok",
        message="Password has been reset successfully. Please log in with your new password.",
    )


@router.get("/me", response_model=UserMeResponse)
async def get_me(user: sqlite3.Row = Depends(get_current_user)):
    """
    Retrieves the currently authenticated user profile and preferences.
    """
    prefs = get_user_preferences(user["id"])
    return UserMeResponse(
        user=_build_user_response(user),
        preferences=_build_preferences_response(prefs),
    )


@router.patch("/me", response_model=UserMeResponse)
async def update_me(
    req: UserUpdateRequest,
    request: Request,
    user: sqlite3.Row = Depends(get_current_user),
):
    """
    Updates the current user profile (name or password).
    - Requires CSRF verification for cookie-authenticated requests
    - Requires current password verification when changing password
    """
    verify_csrf(request)

    new_hash = None
    if req.new_password is not None:
        if not req.current_password or not verify_password(req.current_password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect.",
            )
        validate_password_strength(req.new_password, email=user["email"])
        new_hash = hash_password(req.new_password)

    clean_name = req.name.strip() if req.name is not None else None
    update_user_profile(user["id"], name=clean_name, password_hash=new_hash)

    updated_user = get_user_by_id(user["id"])
    prefs = get_user_preferences(user["id"])
    return UserMeResponse(
        user=_build_user_response(updated_user),
        preferences=_build_preferences_response(prefs),
    )


@router.delete("/me", response_model=AuthMessageResponse)
async def delete_me(
    req: DeleteAccountRequest,
    request: Request,
    response: Response,
    user: sqlite3.Row = Depends(get_current_user),
):
    """
    Deletes the current user account and cascades all associated data.
    - Requires password re-entry confirmation
    - Requires CSRF verification
    - Clears cookies
    """
    verify_csrf(request)

    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password. Account deletion aborted.",
        )

    delete_user_account(user["id"])

    response.delete_cookie(ACCESS_COOKIE_NAME, path="/")
    response.delete_cookie(CSRF_COOKIE_NAME, path="/")

    return AuthMessageResponse(
        status="ok",
        message="Account and all associated records deleted successfully.",
    )
