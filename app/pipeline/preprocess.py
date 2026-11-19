import re
from typing import Tuple, Dict

# Standard Hinglish variant mappings to canonical forms
HINGLISH_MAPPINGS: Dict[str, str] = {
    # Urgency & threat variants
    r"\bturat\b": "turant",
    r"\bturantt\b": "turant",
    r"\bturanto\b": "turant",
    r"\babhi\s+karo\b": "turant",
    r"\babhi\s+karein\b": "turant",
    r"\baaj\s+hi\b": "turant",
    r"\bjald\s+se\s+jald\b": "turant",
    r"\bjaldi\b": "turant",
    r"\bgiraftaar\b": "arrest",
    r"\bgiraftari\b": "arrest",
    r"\barrest\s+kar\s+lenge\b": "arrest",
    r"\barrest\s+ho\s+jayega\b": "arrest",
    r"\bjail\s+bhej\s+denge\b": "jail",

    # Secrecy variants
    r"\bkisi\s+ko\s+bhi\s+mat\s+batana\b": "kisi ko mat batana",
    r"\bkisi\s+ko\s+mat\s+batao\b": "kisi ko mat batana",
    r"\bkisi\s+ko\s+na\s+bataye\b": "kisi ko mat batana",
    r"\bkisi\s+se\s+mat\s+batana\b": "kisi ko mat batana",
    r"\bkisi\s+ko\s+mat\s+kehna\b": "kisi ko mat batana",
    r"\bkisi\s+se\s+share\s+mat\s+karna\b": "kisi ko mat batana",
    r"\bcall\s+mat\s+katna\b": "call mat kaatna",
    r"\bphone\s+mat\s+kaatna\b": "call mat kaatna",

    # Authority variants
    r"\bpolice\s+thane\s+se\b": "police station",
    r"\bthane\s+se\b": "police station",
    r"\bcbi\s+se\s+bol\s+raha\b": "cbi officer",
    r"\bpolice\s+se\s+bol\s+raha\b": "police officer",
    r"\bcbi\s+headquarters\b": "cbi",

    # Payment variants
    r"\bpaise\s+bhejo\b": "transfer kijiye",
    r"\bpaise\s+daalo\b": "transfer kijiye",
    r"\bpaise\s+transfer\s+karo\b": "transfer kijiye",
    r"\bpaise\s+dal\s+do\b": "transfer kijiye",
    r"\brs\s+transfer\b": "transfer money",

    # Sensitive info variants
    r"\botp\s+bhejo\b": "otp share",
    r"\botp\s+batao\b": "otp share",
    r"\bpin\s+batao\b": "pin share",
    r"\botp\s+send\s+karo\b": "otp share",

    # KYC & account variants
    r"\bbijli\s+kat\s+jayegi\b": "electricity cut",
    r"\bbijli\s+cut\s+jayegi\b": "electricity cut",
    r"\bsim\s+band\s+ho\s+jayega\b": "sim deactivated",
    r"\bpan\s+link\s+karo\b": "update kyc",
    r"\bkyc\s+update\s+karo\b": "update kyc",
}


def normalize_text(text: str) -> str:
    """
    Normalizes input text:
    1. Converts to lowercase.
    2. Collapses redundant whitespace.
    3. Standardizes common Hinglish spelling variants.
    """
    if not text:
        return ""

    normalized = text.lower()
    # Normalize multiple whitespace characters to a single space
    normalized = re.sub(r"[ \t\r\f\v]+", " ", normalized)
    normalized = re.sub(r"\n+", "\n", normalized).strip()

    # Apply Hinglish canonical mappings
    for pattern, replacement in HINGLISH_MAPPINGS.items():
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

    return normalized


def mask_sensitive_data(text: str) -> str:
    """
    Masks sensitive personal and financial identifiers with placeholders:
    - Phone numbers -> [PHONE]
    - OTPs / PINs -> [OTP]
    - Bank Account / Card / UPI / PAN / Aadhaar -> [ACCOUNT]
    
    This ensures that raw personally identifiable info (PII) is never logged
    or transmitted to an external LLM API.
    """
    if not text:
        return ""

    masked = text

    # 1. Mask Credit / Debit Card numbers (13 to 19 digits, with optional spaces or dashes)
    # e.g., 4111 2222 3333 4444, 1234-5678-9012-3456
    masked = re.sub(
        r"\b(?:\d{4}[-\s]?){3}\d{1,7}\b",
        "[ACCOUNT]",
        masked
    )

    # 2. Mask Bank Account numbers in account contexts
    # e.g. A/c: 123456789012, Account: 987654321098, A/C No. 501002345678
    masked = re.sub(
        r"(?i)\b(?:a/?c(?:\s*no\.?)?|account(?:\s*number|\s*no\.?)?)\s*[:#-]?\s*(\d{9,18})\b",
        r"a/c [ACCOUNT]",
        masked
    )

    # 3. Mask UPI IDs (e.g. user@oksbi, name99@paytm, 9876543210@ybl)
    masked = re.sub(
        r"\b[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}\b",
        "[ACCOUNT]",
        masked
    )

    # 4. Mask PAN cards (5 letters + 4 digits + 1 letter, e.g. ABCDE1234F)
    masked = re.sub(
        r"\b[A-Za-z]{5}\d{4}[A-Za-z]\b",
        "[ACCOUNT]",
        masked
    )

    # 5. Mask Aadhaar numbers (12 digits, often 4 4 4)
    masked = re.sub(
        r"\b\d{4}\s\d{4}\s\d{4}\b",
        "[ACCOUNT]",
        masked
    )

    # 6. Mask OTPs (4 to 8 digits explicitly preceded or followed by otp/code/pin keywords)
    # e.g. "otp is 123456", "otp: 4829", "code 591023", "verification code: 9283"
    masked = re.sub(
        r"(?i)\b(?:otp|one\s+time\s+password|verification\s+code|code|secret\s+pin)\s*(?:is|:|=|-)?\s*(\d{4,8})\b",
        r"otp is [OTP]",
        masked
    )
    # e.g. "123456 is your OTP"
    masked = re.sub(
        r"(?i)\b(\d{4,8})\s+is\s+your\s+(?:otp|verification\s+code|code)\b",
        r"[OTP] is your otp",
        masked
    )

    # 7. Mask Indian Phone numbers
    # Format: +91-XXXXX-XXXXX, +91XXXXXXXXXX, 0XXXXXXXXXX, or bare 10-digit starting with 6-9
    masked = re.sub(
        r"(?:\+91[\-\s]?)?[6-9]\d{4}[\-\s]?\d{5}\b",
        "[PHONE]",
        masked
    )
    # Also 11-digit starting with 0: 09876543210
    masked = re.sub(
        r"\b0[6-9]\d{9}\b",
        "[PHONE]",
        masked
    )

    return masked


def preprocess_message(text: str) -> Tuple[str, str]:
    """
    Complete preprocessing pipeline:
    Returns (cleaned_normalized_text, masked_text)
    
    - cleaned_normalized_text: lowercased, Hinglish normalized (used by RuleEngine)
    - masked_text: normalized + PII masked (used by LLM explanation layer)
    """
    normalized = normalize_text(text)
    masked = mask_sensitive_data(normalized)
    return normalized, masked
