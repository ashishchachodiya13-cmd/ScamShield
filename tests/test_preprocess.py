import pytest
from app.pipeline.preprocess import normalize_text, mask_sensitive_data, preprocess_message


def test_whitespace_and_lowercasing():
    raw = "  URGENT:   Please   Review  Your   Account! \n\n  Immediately.  "
    normalized = normalize_text(raw)
    assert "urgent: please review your account!" in normalized
    assert "immediately." in normalized
    assert "   " not in normalized


def test_hinglish_normalization():
    # 'turat' -> 'turant'
    assert "turant" in normalize_text("Turat call kijiye")
    
    # 'kisi ko mat batao' -> 'kisi ko mat batana'
    assert "kisi ko mat batana" in normalize_text("Yeh secret hai kisi ko mat batao")
    
    # 'paise bhejo' -> 'transfer kijiye'
    assert "transfer kijiye" in normalize_text("Turant paise bhejo")
    
    # 'bijli cut jayegi' -> 'electricity cut'
    assert "electricity cut" in normalize_text("Aaj raat bijli cut jayegi")
    
    # 'otp batao' -> 'otp share'
    assert "otp share" in normalize_text("Jaldi se otp batao")


def test_mask_phone_numbers():
    # 10-digit Indian numbers starting with 6-9
    text1 = "Call our officer on 9876543210 immediately."
    masked1 = mask_sensitive_data(text1)
    assert "[PHONE]" in masked1
    assert "9876543210" not in masked1

    # With +91 prefix
    text2 = "Contact us at +91-9123456789 or +91 8888877777."
    masked2 = mask_sensitive_data(text2)
    assert "[PHONE]" in masked2
    assert "9123456789" not in masked2
    assert "8888877777" not in masked2

    # 11-digit with leading 0
    text3 = "Dial 09876543210 now."
    masked3 = mask_sensitive_data(text3)
    assert "[PHONE]" in masked3
    assert "09876543210" not in masked3


def test_mask_otps():
    text1 = "Your one time password is 482910. Do not share with anyone."
    masked1 = mask_sensitive_data(text1)
    assert "[OTP]" in masked1
    assert "482910" not in masked1

    text2 = "Use OTP: 9381 to approve transaction."
    masked2 = mask_sensitive_data(text2)
    assert "[OTP]" in masked2
    assert "9381" not in masked2

    text3 = "849201 is your OTP for netbanking login."
    masked3 = mask_sensitive_data(text3)
    assert "[OTP]" in masked3
    assert "849201" not in masked3


def test_mask_bank_accounts_and_cards():
    # 16-digit card number
    text1 = "Transfer from card 4111 2222 3333 4444 now."
    masked1 = mask_sensitive_data(text1)
    assert "[ACCOUNT]" in masked1
    assert "4111" not in masked1

    # Bank account number in context
    text2 = "Deposit money into A/c: 123456789012 at SBI branch."
    masked2 = mask_sensitive_data(text2)
    assert "[ACCOUNT]" in masked2
    assert "123456789012" not in masked2

    # UPI ID
    text3 = "Send payment to officer.cbi@oksbi immediately."
    masked3 = mask_sensitive_data(text3)
    assert "[ACCOUNT]" in masked3
    assert "officer.cbi@oksbi" not in masked3

    # PAN card
    text4 = "Your PAN ABCDE1234F is deactivated."
    masked4 = mask_sensitive_data(text4)
    assert "[ACCOUNT]" in masked4
    assert "ABCDE1234F" not in masked4


def test_preprocess_message_pipeline():
    raw_message = (
        "Main CBI officer bol raha hu. Turat 50,000 paise bhejo to account: 987654321098. "
        "Call +91 9876543210 for OTP 123456 confirmation."
    )
    cleaned, masked = preprocess_message(raw_message)

    # Cleaned should have normalized Hinglish
    assert "turant" in cleaned
    assert "transfer kijiye" in cleaned

    # Masked should have PII placeholders and NO raw sensitive details
    assert "[ACCOUNT]" in masked
    assert "[PHONE]" in masked
    assert "[OTP]" in masked
    assert "987654321098" not in masked
    assert "9876543210" not in masked
    assert "123456" not in masked
