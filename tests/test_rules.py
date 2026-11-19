import pytest
from app.pipeline.rules import RuleEngine


@pytest.fixture
def engine():
    return RuleEngine()


def test_mandatory_cbi_test_case(engine):
    """
    Mandatory test case specified in prompt:
    'Main CBI officer bol raha hu. Aapke naam par arrest warrant hai. Turant 50,000 transfer kijiye aur kisi ko mat batana.'
    -> High risk, Digital Arrest, flags: authority, urgency/threat, payment demand, secrecy.
    """
    text = (
        "Main CBI officer bol raha hu. Aapke naam par arrest warrant hai. "
        "Turant 50,000 transfer kijiye aur kisi ko mat batana."
    )
    result = engine.evaluate(text)

    # 1. Must be High risk
    assert result["risk_level"] == "High"

    # 2. Must be Digital Arrest category
    assert result["category_id"] == "digital_arrest"

    # 3. Check matched flags
    flag_ids = {f.id for f in result["matched_flags"]}
    assert "authority_impersonation" in flag_ids
    assert "urgency_threat" in flag_ids
    assert "immediate_payment" in flag_ids
    assert "secrecy_demand" in flag_ids

    # 4. Total score calculation: 3 + 2 + 3 + 3 = 11
    assert result["score"] >= 6
    assert result["is_zero_flags"] is False


def test_zero_flag_case(engine):
    """
    Zero-flag case:
    A completely harmless message must trigger zero flags, score 0,
    and must NEVER be labelled 'Safe'.
    """
    harmless_text = "Good morning Dad, did you take your morning medicines today? See you in the evening."
    result = engine.evaluate(harmless_text)

    assert result["score"] == 0
    assert len(result["matched_flags"]) == 0
    assert result["is_zero_flags"] is True
    # System categorizes zero-flags as Low risk decision support, never "Safe"
    assert result["risk_level"] == "Low"
    assert result["risk_level"] != "Safe"


def test_scoring_thresholds(engine):
    """
    Thresholds:
    score <= 2 -> Low
    score 3 to 5 -> Medium
    score >= 6 -> High
    """
    # Low risk (urgency only = weight 2)
    res_low = engine.evaluate("Please call me back immediately, it is urgent.")
    assert res_low["score"] == 2
    assert res_low["risk_level"] == "Low"

    # Medium risk (sensitive info only = weight 3)
    res_med = engine.evaluate("Please share your UPI PIN and OTP to verify your identity.")
    assert res_med["score"] == 3
    assert res_med["risk_level"] == "Medium"

    # High risk (authority 3 + payment 3 = 6)
    res_high = engine.evaluate("Police inspector here. Transfer money to our clearance account.")
    assert res_high["score"] >= 6
    assert res_high["risk_level"] == "High"


def test_category_selection_kyc_fraud(engine):
    text = "Dear customer, your SBI account KYC is expired. Update KYC within 24 hours or account blocked. Click bit.ly/kyc-sbi"
    result = engine.evaluate(text)
    assert result["category_id"] == "kyc_account_block"
    assert result["risk_level"] in ("Medium", "High")


def test_category_selection_lottery(engine):
    text = "Congratulations! You won 25 Lakh in KBC Lucky Draw Lottery. Pay registration fee to claim prize."
    result = engine.evaluate(text)
    assert result["category_id"] == "lottery"
    assert result["risk_level"] in ("Medium", "High")


def test_category_selection_job_scam(engine):
    text = "Work from home part-time job offer! Daily earn Rs 5000. Pay documentation charges of 1500 to start."
    result = engine.evaluate(text)
    assert result["category_id"] == "job_scam"


def test_category_selection_loan_scam(engine):
    text = "Pre-approved loan of 10 Lakhs approved at 2% interest. Transfer processing fee of 5000 immediately."
    result = engine.evaluate(text)
    assert result["category_id"] == "loan_scam"


def test_category_selection_family_emergency(engine):
    text = "Your son is in trouble and admitted to hospital after accident. Transfer money right now and do not tell family."
    result = engine.evaluate(text)
    assert result["category_id"] == "family_emergency"
    assert result["risk_level"] == "High"


def test_hindi_devanagari_detection(engine):
    """
    Hindi (Devanagari) red flag detection
    """
    text = "सीबीआई अधिकारी बोल रहा हूं। तुरंत पैसे ट्रांसफर करें और किसी को मत बताना।"
    result = engine.evaluate(text)
    assert result["risk_level"] == "High"
    assert result["category_id"] == "digital_arrest"
    flag_ids = {f.id for f in result["matched_flags"]}
    assert "authority_impersonation" in flag_ids
    assert "immediate_payment" in flag_ids
    assert "secrecy_demand" in flag_ids
