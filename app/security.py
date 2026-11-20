import hashlib
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHash
from fastapi import Request, HTTPException, status

from app.config import (
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_EXPIRY_HOURS,
    JWT_REMEMBER_DAYS,
    APP_ENV,
    CSRF_HEADER_NAME,
    CSRF_COOKIE_NAME,
)

logger = logging.getLogger(__name__)

# Argon2id password hasher
ph = PasswordHasher()


def validate_password_strength(password: str, email: str = "") -> None:
    """
    Validates password requirements:
    - Min 8 chars
    - Must not be all-numeric
    - Must not equal email (case-insensitive)
    """
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters long.",
        )
    if password.isdigit():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password cannot be all numeric.",
        )
    if email and password.strip().lower() == email.strip().lower():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password cannot be the same as your email address.",
        )


def hash_password(password: str) -> str:
    """Hashes a password with Argon2id."""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a password against an Argon2id hash."""
    try:
        return ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHash):
        return False


def create_access_token(
    user_id: int,
    email: str,
    remember_me: bool = False,
    jti: Optional[str] = None,
) -> Tuple[str, str, str]:
    """
    Creates a JWT access token.
    Returns: (token_str, jti, expires_at_iso)
    """
    token_jti = jti or secrets.token_hex(16)
    duration = timedelta(days=JWT_REMEMBER_DAYS) if remember_me else timedelta(hours=JWT_EXPIRY_HOURS)
    now = datetime.now(timezone.utc)
    expires_at = now + duration

    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "email": email.lower(),
        "jti": token_jti,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, token_jti, expires_at.isoformat()


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decodes and validates a JWT access token.
    Returns payload dict if valid, None if expired or invalid.
    """
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
        logger.debug(f"JWT decode failed: {e}")
        return None


def generate_reset_token() -> Tuple[str, str]:
    """
    Generates a secure random reset token.
    Returns: (raw_token, token_hash)
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_reset_token(raw_token)
    return raw_token, token_hash


def hash_reset_token(raw_token: str) -> str:
    """Computes SHA-256 hash of a reset token for safe storage."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_csrf_token() -> str:
    """Generates a secure CSRF token."""
    return secrets.token_hex(24)


def verify_csrf(request: Request) -> None:
    """
    Verifies CSRF on state-changing requests when authenticated via cookies.
    Checks that X-CSRF-Token header matches csrf_token cookie.
    If no cookies are present (e.g. Bearer auth or guest), CSRF check is bypassed.
    """
    # If state-changing method
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        cookie_csrf = request.cookies.get(CSRF_COOKIE_NAME)
        # Only enforce if csrf_token cookie is present (indicating browser session)
        if cookie_csrf:
            header_csrf = request.headers.get(CSRF_HEADER_NAME)
            if not header_csrf or not secrets.compare_digest(cookie_csrf, header_csrf):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSRF verification failed. Missing or invalid CSRF token.",
                )


def send_password_reset_notification(email: str, reset_link: str) -> None:
    """
    Sends password reset email or logs to console in dev mode.
    Never leaks sensitive details.
    """
    if APP_ENV == "dev":
        print(f"\n========================================================")
        print(f"[DEV ONLY] Password reset requested for: {email}")
        print(f"Reset Link: {reset_link}")
        print(f"========================================================\n")
        logger.info(f"[DEV] Password reset link for {email}: {reset_link}")
    else:
        # Pluggable email stub
        raise NotImplementedError("Email service not configured for non-dev environment.")
