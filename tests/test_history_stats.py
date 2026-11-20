import io
import csv
import json
import sqlite3
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.config import (
    ACCESS_COOKIE_NAME,
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    DB_PATH,
)
from app.limiter import limiter

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_limiter():
    limiter.reset()


class Tuple_User:
    def __init__(self, client, user_data, csrf_token):
        self.client = client
        self.user = user_data
        self.csrf = csrf_token

    def __iter__(self):
        return iter((self.client, self.user, self.csrf))


def _create_authenticated_user(email_prefix: str) -> Tuple_User:
    """Helper to create and log in a user, returning TestClient and user data."""
    test_client = TestClient(app)
    email = f"{email_prefix}_{datetime.now().timestamp()}@example.com"
    pwd = "SecurePassword123!"

    reg_res = test_client.post(
        "/api/auth/register",
        json={"email": email, "name": f"User {email_prefix}", "password": pwd},
    )
    assert reg_res.status_code == 201
    user_data = reg_res.json()
    csrf_token = test_client.cookies.get(CSRF_COOKIE_NAME)
    return Tuple_User(test_client, user_data, csrf_token)


# ==============================================================================
# Guest vs Authenticated Scan Persistence Tests
# ==============================================================================

def test_guest_analysis_saves_nothing():
    guest_client = TestClient(app)
    # Check baseline analysis count in DB
    with sqlite3.connect(DB_PATH) as conn:
        before_count = conn.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]

    # Run analysis as guest
    res = guest_client.post(
        "/api/analyze",
        json={"text": "Congratulations you won a lottery in lucky draw!", "language": "en"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["analysis_id"] is None

    # Assert database analysis count is completely unchanged
    with sqlite3.connect(DB_PATH) as conn:
        after_count = conn.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
        assert after_count == before_count


def test_authenticated_analysis_saves_metadata_only():
    user_client, user_data, _ = _create_authenticated_user("authtest")

    # Run analysis
    raw_message = (
        "Main CBI officer bol raha hu. Arrest warrant hai. "
        "Turant 50,000 paise bhejo to account 987654321098 aur kisi ko mat batana."
    )
    res = user_client.post(
        "/api/analyze",
        json={"text": raw_message, "language": "en", "source": "text"},
    )
    assert res.status_code == 200
    data = res.json()
    analysis_id = data["analysis_id"]
    assert analysis_id is not None
    assert analysis_id > 0

    # Verify database persistence
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
        assert row is not None
        assert row["user_id"] == user_data["id"]
        assert row["category"] == "digital_arrest"
        assert row["risk_level"] == "High"
        assert row["score"] >= 6
        assert row["source"] == "text"
        # By default retain_masked_text is False -> masked_text is None
        assert row["masked_text"] is None

        # STRICT PRIVACY: Verify RAW message text does NOT exist in the database row
        assert raw_message not in str(dict(row))
        assert "987654321098" not in str(dict(row))


# ==============================================================================
# History CRUD, Filtering & Pagination Tests
# ==============================================================================

def test_history_list_and_filters():
    user_client, user_data, _ = _create_authenticated_user("histfilter")

    # Perform 3 scans: 2 High Risk (CBI), 1 Low Risk (harmless)
    cbi_msg = "CBI officer here. Arrest warrant issued. Transfer money immediately."
    lottery_msg = "Congratulations winner! Lucky draw prize lottery 10 Lakh won. Pay fee."
    harmless_msg = "Good morning Dad, take your medicine today."

    res1 = user_client.post("/api/analyze", json={"text": cbi_msg, "language": "en"})
    res2 = user_client.post("/api/analyze", json={"text": lottery_msg, "language": "en"})
    res3 = user_client.post("/api/analyze", json={"text": harmless_msg, "language": "en"})
    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res3.status_code == 200

    # 1. Get all history
    all_res = user_client.get("/api/history")
    assert all_res.status_code == 200
    all_data = all_res.json()
    assert all_data["total"] == 3
    assert len(all_data["items"]) == 3

    # 2. Filter by risk = High
    high_res = user_client.get("/api/history?risk=High")
    assert high_res.status_code == 200
    high_data = high_res.json()
    assert all(item["risk_level"] == "High" for item in high_data["items"])
    assert high_data["total"] >= 1

    # 3. Filter by category = lottery
    cat_res = user_client.get("/api/history?category=lottery")
    assert cat_res.status_code == 200
    assert cat_res.json()["total"] == 1
    assert cat_res.json()["items"][0]["category"] == "lottery"

    # 4. Search filter (matches category or flags)
    search_res = user_client.get("/api/history?search=arrest")
    assert search_res.status_code == 200
    assert search_res.json()["total"] >= 1

    # 5. Pagination
    page_res = user_client.get("/api/history?page=1&page_size=2")
    assert page_res.status_code == 200
    pdata = page_res.json()
    assert len(pdata["items"]) == 2
    assert pdata["total"] == 3
    assert pdata["total_pages"] == 2


def test_history_detail_rebuilding():
    user_client, user_data, _ = _create_authenticated_user("histdetail")

    scan_res = user_client.post(
        "/api/analyze",
        json={"text": "CBI officer. Arrest warrant. Transfer money right now. Keep secret.", "language": "en"},
    )
    analysis_id = scan_res.json()["analysis_id"]

    # Fetch detail
    detail_res = user_client.get(f"/api/history/{analysis_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()

    assert detail["id"] == analysis_id
    assert detail["category"] == "digital_arrest"
    assert "Digital Arrest" in detail["category_name"]
    assert len(detail["matched_flags"]) > 0
    assert len(detail["actions"]["dos"]) > 0
    assert len(detail["actions"]["donts"]) > 0
    assert "Digital Arrest" in detail["explanation"]
    assert detail["masked_text"] is None
    assert detail["retained_label"] == "No message text stored for privacy"


def test_delete_history_item_and_clear_all():
    user_client, user_data, csrf = _create_authenticated_user("histdel")

    # Create 2 analyses
    r1 = user_client.post("/api/analyze", json={"text": "Urgent CBI arrest warrant", "language": "en"})
    r2 = user_client.post("/api/analyze", json={"text": "KBC lottery winner 50 Lakh", "language": "en"})
    id1 = r1.json()["analysis_id"]
    id2 = r2.json()["analysis_id"]

    # Delete single item
    del_res = user_client.delete(f"/api/history/{id1}", headers={CSRF_HEADER_NAME: csrf})
    assert del_res.status_code == 200

    # Ensure deleted
    get_res = user_client.get(f"/api/history/{id1}")
    assert get_res.status_code == 404

    # Try clearing without confirm=true -> 400
    clear_err = user_client.delete("/api/history", headers={CSRF_HEADER_NAME: csrf})
    assert clear_err.status_code == 400
    assert "confirm=true" in clear_err.json()["detail"]

    # Clear with confirm=true
    clear_ok = user_client.delete("/api/history?confirm=true", headers={CSRF_HEADER_NAME: csrf})
    assert clear_ok.status_code == 200

    # Verify history is now empty
    empty_res = user_client.get("/api/history")
    assert empty_res.json()["total"] == 0


# ==============================================================================
# User Isolation Tests
# ==============================================================================

def test_user_isolation():
    userA, dataA, csrfA = _create_authenticated_user("userA")
    userB, dataB, csrfB = _create_authenticated_user("userB")

    # User A performs an analysis
    resA = userA.post(
        "/api/analyze",
        json={"text": "CBI officer transfer money urgently", "language": "en"},
    )
    idA = resA.json()["analysis_id"]

    # 1. User B cannot see User A's record in history listing
    listB = userB.get("/api/history")
    assert listB.json()["total"] == 0
    assert len(listB.json()["items"]) == 0

    # 2. User B cannot read User A's detail (returns 404 Not Found, NOT 403)
    detailB = userB.get(f"/api/history/{idA}")
    assert detailB.status_code == 404
    assert detailB.json()["detail"] == "Analysis record not found."

    # 3. User B cannot delete User A's analysis (returns 404)
    delB = userB.delete(f"/api/history/{idA}", headers={CSRF_HEADER_NAME: csrfB})
    assert delB.status_code == 404

    # 4. Record still exists intact for User A
    detailA = userA.get(f"/api/history/{idA}")
    assert detailA.status_code == 200
    assert detailA.json()["id"] == idA


# ==============================================================================
# Empty-State Stats & SQL Aggregate Reporting Tests
# ==============================================================================

def test_empty_state_stats():
    user_client, _, _ = _create_authenticated_user("emptystats")

    # Overview
    ov_res = user_client.get("/api/stats/overview")
    assert ov_res.status_code == 200
    ov = ov_res.json()
    assert ov["total_scans"] == 0
    assert ov["high_risk_count"] == 0
    assert ov["medium_risk_count"] == 0
    assert ov["low_risk_count"] == 0
    assert ov["recent_scans"] == []
    assert ov["recent_high_risk"] == []
    assert ov["category_distribution"] == []
    assert ov["risk_distribution"] == []

    # Reports
    rep_res = user_client.get("/api/stats/reports?range=week")
    assert rep_res.status_code == 200
    rep = rep_res.json()
    assert rep["total_scans"] == 0
    assert rep["high_risk_percentage"] == 0.0
    assert rep["category_breakdown"] == []
    assert rep["activity_timeline"] == []


def test_reports_and_export():
    user_client, user_data, _ = _create_authenticated_user("reportsexport")

    # Perform scans
    user_client.post("/api/analyze", json={"text": "CBI officer arrest warrant transfer money", "language": "en"})
    user_client.post("/api/analyze", json={"text": "KBC lottery winner pay registration fee", "language": "en"})
    user_client.post("/api/analyze", json={"text": "Harmless message drink water", "language": "en"})

    # Check overview
    ov = user_client.get("/api/stats/overview").json()
    assert ov["total_scans"] == 3
    assert ov["high_risk_count"] >= 1
    assert len(ov["category_distribution"]) >= 2

    # Check reports
    rep = user_client.get("/api/stats/reports?range=all").json()
    assert rep["total_scans"] == 3
    assert rep["high_risk_percentage"] > 0
    assert len(rep["category_breakdown"]) >= 2
    assert len(rep["activity_timeline"]) >= 1

    # Export CSV
    csv_res = user_client.get("/api/reports/export?format=csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    csv_reader = csv.DictReader(io.StringIO(csv_res.text))
    rows = list(csv_reader)
    assert len(rows) == 3
    assert "category" in rows[0]
    assert "risk_level" in rows[0]
    # STRICT PRIVACY: verify raw text is NOT in CSV
    assert "message" not in rows[0]
    assert "drink water" not in csv_res.text

    # Export JSON
    json_res = user_client.get("/api/reports/export?format=json")
    assert json_res.status_code == 200
    assert "application/json" in json_res.headers["content-type"]
    json_data = json_res.json()
    assert len(json_data) == 3
    assert json_data[0]["id"] is not None


# ==============================================================================
# Preferences & Masked Text Retention Opt-In Tests
# ==============================================================================

def test_preferences_and_retaining_masked_text():
    user_client, user_data, csrf = _create_authenticated_user("prefmasked")

    # 1. Get default preferences
    pref_res = user_client.get("/api/preferences")
    assert pref_res.status_code == 200
    prefs = pref_res.json()
    assert prefs["retain_masked_text"] is False
    assert prefs["large_text"] is False
    assert prefs["language"] == "en"

    # 2. Update preferences: enable retain_masked_text and large_text
    put_res = user_client.put(
        "/api/preferences",
        json={"retain_masked_text": True, "large_text": True, "language": "hi"},
        headers={CSRF_HEADER_NAME: csrf},
    )
    assert put_res.status_code == 200
    upd_prefs = put_res.json()
    assert upd_prefs["retain_masked_text"] is True
    assert upd_prefs["large_text"] is True
    assert upd_prefs["language"] == "hi"

    # 3. Now run an analysis with retain_masked_text enabled
    raw_text = "Main CBI officer bol raha hu. Turant paise bhejo account: 123456789012."
    scan_res = user_client.post("/api/analyze", json={"text": raw_text, "language": "en"})
    analysis_id = scan_res.json()["analysis_id"]

    # 4. Check history detail
    detail = user_client.get(f"/api/history/{analysis_id}").json()
    assert detail["masked_text"] is not None
    # Masked text is saved with [ACCOUNT] placeholder
    assert "[ACCOUNT]" in detail["masked_text"]
    assert detail["retained_label"] == "Masked text saved by user preference"

    # STRICT PRIVACY: Real bank account number must NEVER be stored
    assert "123456789012" not in detail["masked_text"]


# ==============================================================================
# Privacy Assertion: Zero Raw Messages Anywhere in SQLite
# ==============================================================================

def test_strict_privacy_zero_raw_messages_in_db():
    user_client, _, _ = _create_authenticated_user("privacytest")

    secret_otp = "SECRET998811"
    secret_phone = "9988776655"
    message_with_secrets = (
        f"Urgent call officer at {secret_phone}. Your verification OTP is {secret_otp}. "
        "Pay registration fee immediately."
    )

    user_client.post("/api/analyze", json={"text": message_with_secrets, "language": "en"})

    # Inspect all SQLite tables and columns
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

        for tbl in tables:
            rows = conn.execute(f"SELECT * FROM {tbl}").fetchall()
            for row in rows:
                row_str = str(dict(row))
                assert secret_otp not in row_str, f"Found raw OTP in table {tbl}!"
                assert secret_phone not in row_str, f"Found raw phone in table {tbl}!"
