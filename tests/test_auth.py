import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
import jwt

from app.main import app
from app.config import (
    ACCESS_COOKIE_NAME,
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    JWT_SECRET,
    JWT_ALGORITHM,
)
from app.database import (
    get_user_by_email,
    get_user_by_id,
    get_session,
    get_password_reset,
    create_session,
)
from app.security import create_access_token, hash_reset_token
from app.limiter import limiter

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_limiter_state():
    """Resets in-memory rate limiter between tests."""
    limiter.reset()


# ==============================================================================
# Registration Tests
# ==============================================================================

def test_register_success():
    email = f"senior_{datetime.now().timestamp()}@example.com"
    res = client.post(
        "/api/auth/register",
        json={"email": email, "name": "Senior Citizen", "password": "SecurePassword123!"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == email.lower()
    assert data["name"] == "Senior Citizen"
    assert "id" in data
    # Check cookies set
    assert ACCESS_COOKIE_NAME in res.cookies
    assert CSRF_COOKIE_NAME in res.cookies


def test_register_duplicate_email():
    email = f"dup_{datetime.now().timestamp()}@example.com"
    # First registration
    res1 = client.post(
        "/api/auth/register",
        json={"email": email, "name": "Original User", "password": "Password123!"},
    )
    assert res1.status_code == 201

    # Second registration with same email (different case)
    res2 = client.post(
        "/api/auth/register",
        json={"email": email.upper(), "name": "Duplicate User", "password": "Password123!"},
    )
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


def test_register_invalid_email_format():
    res = client.post(
        "/api/auth/register",
        json={"email": "invalid-email-address", "name": "User", "password": "Password123!"},
    )
    assert res.status_code == 422


def test_register_weak_password():
    email = f"weak_{datetime.now().timestamp()}@example.com"

    # Too short (< 8 chars)
    res_short = client.post(
        "/api/auth/register",
        json={"email": email, "name": "User", "password": "12345"},
    )
    assert res_short.status_code == 422
    assert "at least 8 characters" in str(res_short.json()["detail"]).lower()

    # All numeric
    res_num = client.post(
        "/api/auth/register",
        json={"email": email, "name": "User", "password": "123456789"},
    )
    assert res_num.status_code == 422
    assert "all numeric" in res_num.json()["detail"]

    # Equal to email
    res_email = client.post(
        "/api/auth/register",
        json={"email": email, "name": "User", "password": email},
    )
    assert res_email.status_code == 422
    assert "same as your email" in res_email.json()["detail"]


# ==============================================================================
# Login Tests
# ==============================================================================

def test_login_success():
    email = f"login_{datetime.now().timestamp()}@example.com"
    pwd = "ValidPassword123!"
    client.post("/api/auth/register", json={"email": email, "name": "Login User", "password": pwd})

    res = client.post("/api/auth/login", json={"email": email, "password": pwd, "remember_me": True})
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == email.lower()
    assert ACCESS_COOKIE_NAME in res.cookies
    assert CSRF_COOKIE_NAME in res.cookies


def test_login_failure_generic_message():
    # Non-existent email
    res1 = client.post(
        "/api/auth/login",
        json={"email": "nonexistent@example.com", "password": "WrongPassword123!"},
    )
    assert res1.status_code == 401
    assert res1.json()["detail"] == "Invalid email or password."

    # Existing user, wrong password
    email = f"wrongpwd_{datetime.now().timestamp()}@example.com"
    client.post("/api/auth/register", json={"email": email, "name": "User", "password": "CorrectPassword123!"})

    res2 = client.post("/api/auth/login", json={"email": email, "password": "IncorrectPassword123!"})
    assert res2.status_code == 401
    assert res2.json()["detail"] == "Invalid email or password."


# ==============================================================================
# Protected Route & Session Tests
# ==============================================================================

def test_protected_route_without_token():
    # Clean client without cookies
    clean_client = TestClient(app)
    res = clean_client.get("/api/auth/me")
    assert res.status_code == 401
    assert "Authentication required" in res.json()["detail"]


def test_logout_revokes_token():
    auth_client = TestClient(app)
    email = f"logout_{datetime.now().timestamp()}@example.com"
    pwd = "ValidPassword123!"
    auth_client.post("/api/auth/register", json={"email": email, "name": "Logout User", "password": pwd})

    # Verify authenticated
    me_res = auth_client.get("/api/auth/me")
    assert me_res.status_code == 200

    # Save cookie value to try using it after logout
    old_cookie = auth_client.cookies.get(ACCESS_COOKIE_NAME)

    # Perform logout
    logout_res = auth_client.post("/api/auth/logout")
    assert logout_res.status_code == 200
    assert logout_res.json()["status"] == "ok"

    # Ensure subsequent request with old cookie fails with 401
    reuse_client = TestClient(app)
    reuse_client.cookies.set(ACCESS_COOKIE_NAME, old_cookie)
    after_res = reuse_client.get("/api/auth/me")
    assert after_res.status_code == 401


def test_expired_token():
    now = datetime.now(timezone.utc)
    expired_time = now - timedelta(hours=2)
    payload = {
        "sub": "9999",
        "email": "expired@example.com",
        "jti": "expired_jti_123",
        "iat": int((now - timedelta(hours=4)).timestamp()),
        "exp": int(expired_time.timestamp()),
    }
    expired_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    test_client = TestClient(app)
    test_client.cookies.set(ACCESS_COOKIE_NAME, expired_token)
    res = test_client.get("/api/auth/me")
    assert res.status_code == 401


# ==============================================================================
# Password Reset Flow (Dev Mode)
# ==============================================================================

def test_password_reset_flow():
    email = f"reset_{datetime.now().timestamp()}@example.com"
    client.post("/api/auth/register", json={"email": email, "name": "Reset User", "password": "OldPassword123!"})

    # Request reset
    forgot_res = client.post("/api/auth/forgot-password", json={"email": email})
    assert forgot_res.status_code == 200
    assert "instructions have been sent" in forgot_res.json()["message"]

    # Verify reset token was created in DB
    user = get_user_by_email(email)
    import sqlite3
    from app.config import DB_PATH
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        reset_row = conn.execute(
            "SELECT * FROM password_resets WHERE user_id = ? ORDER BY expires_at DESC LIMIT 1",
            (user["id"],)
        ).fetchone()
        assert reset_row is not None
        assert reset_row["used_at"] is None

    # Reset using the token
    # For testing, we mock or use raw_token generated; since hash is stored, let's create a known raw token
    import secrets
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_reset_token(raw_token)
    exp = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
    from app.database import create_password_reset
    create_password_reset(token_hash, user["id"], exp)

    # Perform reset
    reset_res = client.post(
        "/api/auth/reset-password",
        json={"token": raw_token, "new_password": "NewStrongPassword123!"},
    )
    assert reset_res.status_code == 200
    assert "Password has been reset successfully" in reset_res.json()["message"]

    # Login with new password
    login_new = client.post("/api/auth/login", json={"email": email, "password": "NewStrongPassword123!"})
    assert login_new.status_code == 200

    # Old password no longer works
    login_old = client.post("/api/auth/login", json={"email": email, "password": "OldPassword123!"})
    assert login_old.status_code == 401

    # Reusing the same reset token must fail
    reuse_res = client.post(
        "/api/auth/reset-password",
        json={"token": raw_token, "new_password": "AnotherPassword123!"},
    )
    assert reuse_res.status_code == 400


# ==============================================================================
# Rate Limiting Tests
# ==============================================================================

def test_rate_limiting_registration():
    # Limit is 3 per hour per IP
    ip_client = TestClient(app)
    headers = {"X-Forwarded-For": "198.51.100.1"}

    # 3 allowed registrations
    for i in range(3):
        res = ip_client.post(
            "/api/auth/register",
            json={"email": f"ratelimit_{i}_{datetime.now().timestamp()}@example.com", "name": f"User {i}", "password": "Password123!"},
            headers=headers,
        )
        assert res.status_code == 201

    # 4th registration triggers 429
    res_exceeded = ip_client.post(
        "/api/auth/register",
        json={"email": f"ratelimit_4_{datetime.now().timestamp()}@example.com", "name": "User 4", "password": "Password123!"},
        headers=headers,
    )
    assert res_exceeded.status_code == 429
    assert "Retry-After" in res_exceeded.headers
    assert "Too many requests" in res_exceeded.json()["detail"]


# ==============================================================================
# Account Deletion & Cascading Tests
# ==============================================================================

def test_delete_account_cascades():
    auth_client = TestClient(app)
    email = f"delete_{datetime.now().timestamp()}@example.com"
    pwd = "DeletePassword123!"
    auth_client.post("/api/auth/register", json={"email": email, "name": "Delete Me", "password": pwd})

    user = get_user_by_email(email)
    user_id = user["id"]

    csrf_token = auth_client.cookies.get(CSRF_COOKIE_NAME)

    # Wrong password aborts
    del_wrong = auth_client.request(
        "DELETE",
        "/api/auth/me",
        json={"password": "WrongPassword!"},
        headers={CSRF_HEADER_NAME: csrf_token},
    )
    assert del_wrong.status_code == 401
    assert get_user_by_id(user_id) is not None

    # Correct password succeeds
    del_res = auth_client.request(
        "DELETE",
        "/api/auth/me",
        json={"password": pwd},
        headers={CSRF_HEADER_NAME: csrf_token},
    )
    assert del_res.status_code == 200
    assert "deleted successfully" in del_res.json()["message"]

    # Verify user was deleted
    assert get_user_by_id(user_id) is None

    # Verify sessions and preferences were cascaded
    import sqlite3
    from app.config import DB_PATH
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        sessions_count = conn.execute("SELECT COUNT(*) FROM sessions WHERE user_id = ?", (user_id,)).fetchone()[0]
        prefs_count = conn.execute("SELECT COUNT(*) FROM preferences WHERE user_id = ?", (user_id,)).fetchone()[0]
        assert sessions_count == 0
        assert prefs_count == 0
