import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_root_serves_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "ScamShield" in response.text


def test_analyze_empty_text():
    response = client.post("/api/analyze", json={"text": "   ", "language": "en"})
    assert response.status_code == 400
    assert "cannot be empty" in response.json()["detail"]


def test_analyze_mandatory_cbi_case():
    text = (
        "Main CBI officer bol raha hu. Aapke naam par arrest warrant hai. "
        "Turant 50,000 transfer kijiye aur kisi ko mat batana."
    )
    response = client.post("/api/analyze", json={"text": text, "language": "en"})
    assert response.status_code == 200
    data = response.json()

    assert data["risk_level"] == "High"
    assert data["category"] == "digital_arrest"
    assert data["score"] >= 6
    assert len(data["matched_flags"]) >= 4
    assert len(data["actions"]["dos"]) > 0
    assert len(data["actions"]["donts"]) > 0
    assert data["explanation_source"] in ("llm", "template")


def test_analyze_hindi_language():
    text = "सीबीआई अधिकारी बोल रहा हूं। तुरंत पैसे ट्रांसफर करें और किसी को मत बताना।"
    response = client.post("/api/analyze", json={"text": text, "language": "hi"})
    assert response.status_code == 200
    data = response.json()

    assert data["language"] == "hi"
    assert data["risk_level"] == "High"
    assert "डिजिटल अरेस्ट" in data["category_name"]
    assert len(data["actions"]["dos"]) > 0
    assert any("कॉल" in d or "पुलिस" in d for d in data["actions"]["dos"])


def test_analyze_zero_flags():
    text = "Hello Dad, please remember to drink water and take rest."
    response = client.post("/api/analyze", json={"text": text, "language": "en"})
    assert response.status_code == 200
    data = response.json()

    assert data["score"] == 0
    assert len(data["matched_flags"]) == 0
    assert data["risk_level"] != "Safe"
    assert data["explanation_source"] == "template"


def test_feedback_api():
    res = client.post("/api/feedback", json={
        "helpful": True,
        "category": "digital_arrest",
        "risk_level": "High",
        "comment": "Very reassuring application."
    })
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    # Stats
    stats_res = client.get("/api/feedback/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_feedback"] >= 1
