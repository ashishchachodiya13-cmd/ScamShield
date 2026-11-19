import pytest
import sqlite3
from app.schemas import MatchedFlag
from app.pipeline.actions import ActionsManager
from app.pipeline.explain import ExplanationManager
from app.database import init_db, save_feedback, get_feedback_stats


@pytest.fixture
def actions_mgr():
    return ActionsManager()


@pytest.fixture
def explain_mgr():
    return ExplanationManager()


def test_actions_manager_digital_arrest(actions_mgr):
    # English
    actions_en = actions_mgr.get_actions("digital_arrest", language="en")
    assert len(actions_en.dos) > 0
    assert len(actions_en.donts) > 0
    assert any("1930" in ch for ch in actions_en.official_channels)
    assert any("NEVER arrest" in d for d in actions_en.dos)

    # Hindi
    actions_hi = actions_mgr.get_actions("digital_arrest", language="hi")
    assert len(actions_hi.dos) > 0
    assert any("वीडियो कॉल" in d for d in actions_hi.dos)


def test_actions_manager_fallback(actions_mgr):
    actions = actions_mgr.get_actions("unknown_category_xyz", language="en")
    assert len(actions.dos) > 0
    assert len(actions.donts) > 0


def test_template_fallback_on_empty_api_key(explain_mgr, monkeypatch):
    # Ensure API key is cleared to test fallback
    monkeypatch.setattr(explain_mgr, "api_key", "")

    dummy_flag = MatchedFlag(
        id="authority_impersonation",
        name_en="Authority Impersonation",
        name_hi="अधिकारी का झूठा दिखावा",
        weight=3,
        snippets=["CBI officer"]
    )

    text, source = explain_mgr.explain(
        masked_text="Main CBI officer bol raha hu.",
        category_id="digital_arrest",
        category_name="Digital Arrest Scam",
        matched_flags=[dummy_flag],
        language="en",
        is_zero_flags=False
    )

    assert source == "template"
    assert "Digital Arrest" in text
    assert len(text) > 30


def test_template_fallback_hindi(explain_mgr, monkeypatch):
    monkeypatch.setattr(explain_mgr, "api_key", "")

    dummy_flag = MatchedFlag(
        id="prize_reward",
        name_en="Prize or Reward Claim",
        name_hi="लॉटरी या इनाम का झूठा दावा",
        weight=2,
        snippets=["लॉटरी"]
    )

    text, source = explain_mgr.explain(
        masked_text="आपकी लॉटरी लगी है।",
        category_id="lottery",
        category_name="लॉटरी / इनाम धोखाधड़ी",
        matched_flags=[dummy_flag],
        language="hi",
        is_zero_flags=False
    )

    assert source == "template"
    assert "लॉटरी" in text


def test_zero_flag_explanation(explain_mgr):
    # English zero flags
    text_en, source_en = explain_mgr.explain(
        masked_text="Hello, how are you?",
        category_id="general_suspicious",
        category_name="General Suspicious",
        matched_flags=[],
        language="en",
        is_zero_flags=True
    )
    assert source_en == "template"
    assert "No known red flags were detected" in text_en
    assert "Safe" not in text_en

    # Hindi zero flags
    text_hi, source_hi = explain_mgr.explain(
        masked_text="नमस्ते आप कैसे हैं",
        category_id="general_suspicious",
        category_name="सामान्य",
        matched_flags=[],
        language="hi",
        is_zero_flags=True
    )
    assert source_hi == "template"
    assert "कोई ज्ञात संदिग्ध संकेत" in text_hi


def test_database_anonymized_feedback(tmp_path):
    db_file = tmp_path / "test_feedback.db"
    init_db(db_file)

    # Save positive feedback
    row_id1 = save_feedback(
        helpful=True,
        category="digital_arrest",
        risk_level="High",
        comment="Very clear explanation for seniors",
        db_path=db_file
    )
    assert row_id1 > 0

    # Save negative feedback
    row_id2 = save_feedback(
        helpful=False,
        category="lottery",
        risk_level="Medium",
        comment=None,
        db_path=db_file
    )
    assert row_id2 > 0

    # Check stats
    stats = get_feedback_stats(db_file)
    assert stats["total_feedback"] == 2
    assert stats["helpful_count"] == 1
    assert stats["unhelpful_count"] == 1
    assert stats["satisfaction_rate"] == 50.0

    # Verify database schema: STRICTLY check that NO raw messages are stored
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(feedback)")
        columns = [col[1] for col in cursor.fetchall()]
        assert "message" not in columns
        assert "raw_message" not in columns
        assert "text" not in columns
        assert "phone" not in columns
