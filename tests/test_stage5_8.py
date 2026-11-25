import time
import pytest
import sqlite3
import logging
from fastapi.testclient import TestClient

from app.main import app
from app.limiter import limiter
from app.database import get_db_connection


client = TestClient(app)


def test_get_security_tips():
    """Stage 5: Verify security tips endpoint returns verified tips in EN and HI."""
    resp = client.get("/api/security-tips")
    assert resp.status_code == 200
    tips = resp.json()
    assert len(tips) >= 6
    for tip in tips:
        assert "id" in tip
        assert "source" in tip
        assert "title_en" in tip
        assert "title_hi" in tip
        assert "tip_en" in tip
        assert "tip_hi" in tip
        assert "link" in tip
        # Assert citations reference approved authorities
        assert any(auth in tip["source"] for auth in ["RBI", "I4C", "CERT-In", "DoT", "Road Transport", "1930"])


def test_share_target_flow():
    """Stage 7: Test PWA Web Share Target POST and GET retrieval."""
    post_resp = client.post(
        "/share-target",
        data={"title": "Suspicious SMS", "text": "Urgent: Electricity bill unpaid. Call immediately."},
        follow_redirects=False,
    )
    assert post_resp.status_code == 303
    location = post_resp.headers["location"]
    assert "/#scan?share_token=" in location

    token = location.split("share_token=")[1]
    assert len(token) > 0

    # Retrieve shared content
    get_resp = client.get(f"/api/share-target/{token}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert "Electricity bill unpaid" in data["text"]
    assert data["source"] == "share"

    # Single-use check: second retrieval must return 404
    second_get = client.get(f"/api/share-target/{token}")
    assert second_get.status_code == 404


def test_security_headers():
    """Stage 8: Verify HTTP security headers are emitted on all responses."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in resp.headers.get("content-security-policy", "")
    assert "frame-ancestors 'none'" in resp.headers.get("content-security-policy", "")


def test_rate_limiter_analyze():
    """Stage 8: Verify rate limiting triggers 429 when threshold exceeded."""
    limiter.reset()
    fake_ip = "192.168.1.99"
    headers = {"X-Forwarded-For": fake_ip}

    # Execute 30 allowed requests
    for _ in range(30):
        resp = client.post(
            "/api/analyze",
            json={"text": "Check electricity bill scam", "language": "en"},
            headers=headers,
        )
        assert resp.status_code == 200

    # 31st request must trigger 429
    rate_limited_resp = client.post(
        "/api/analyze",
        json={"text": "Check electricity bill scam", "language": "en"},
        headers=headers,
    )
    assert rate_limited_resp.status_code == 429
    assert "Retry-After" in rate_limited_resp.headers
    limiter.reset()


def test_privacy_and_log_sanitization(caplog):
    """
    Stage 8 Non-Negotiable Rule:
    Ensure raw personal data (phone numbers, OTPs, account numbers)
    NEVER appear in server logs or anywhere in SQLite tables.
    """
    raw_phone = "9876543210"
    raw_otp = "847291"
    raw_acc = "99887766554433"

    message = f"CBI Notice: Transfer money from account {raw_acc} to officer at {raw_phone}. Your verification OTP is {raw_otp}."

    with caplog.at_level(logging.DEBUG):
        resp = client.post(
            "/api/analyze",
            json={"text": message, "language": "en"},
        )
        assert resp.status_code == 200
        result = resp.json()

        # Output must be masked
        assert raw_phone not in result["masked_text"]
        assert raw_otp not in result["masked_text"]
        assert raw_acc not in result["masked_text"]
        assert "[PHONE]" in result["masked_text"]
        assert "[OTP]" in result["masked_text"]
        assert "[ACCOUNT]" in result["masked_text"]

    # Check captured logs
    for record in caplog.records:
        log_text = record.getMessage()
        assert raw_phone not in log_text, f"Raw phone leaked into logs: {log_text}"
        assert raw_otp not in log_text, f"Raw OTP leaked into logs: {log_text}"
        assert raw_acc not in log_text, f"Raw account leaked into logs: {log_text}"

    # Check SQLite database tables
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Check all tables
        tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        for table in tables:
            rows = cursor.execute(f"SELECT * FROM {table}").fetchall()
            for row in rows:
                row_str = " ".join([str(val) for val in row if val is not None])
                assert raw_phone not in row_str, f"Raw phone leaked into table {table}"
                assert raw_otp not in row_str, f"Raw OTP leaked into table {table}"
                assert raw_acc not in row_str, f"Raw account leaked into table {table}"
