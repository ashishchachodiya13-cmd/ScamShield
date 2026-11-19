# 🛡️ ScamShield – AI-Assisted Decision-Support System for Scam Communication Identification

**ScamShield** is an AI-assisted decision-support system specifically designed to protect **senior citizens in India** from fraudulent communication (SMS, WhatsApp messages, and phone call transcripts).

> **Important Disclaimer:** ScamShield is a lightweight, point-of-receipt decision-support tool. It is **NOT** a replacement for law enforcement or official reporting portals such as the **National Cyber Crime Helpline (1930)**, **[cybercrime.gov.in](https://cybercrime.gov.in)**, or **[Sanchar Saathi / Chakshu](https://sancharsaathi.gov.in)**.

---

## 🎯 Key Objectives & Core Principles

1. **Rule Engine Decides, AI Only Explains:** Detection, risk scoring, and categorization are governed 100% deterministically by transparent, weighted rules stored in JSON. The LLM is never allowed to guess risk levels or hallucinate safety actions.
2. **Senior-Citizen First Accessibility:** 
   - Minimum **20px body font size** with high-contrast, WCAG AAA compliant styling.
   - Big, easily clickable touch targets (56px+ buttons).
   - Seamless one-click bilingual toggle between **English** and **हिन्दी**.
   - Clear, color-coded + icon-tagged risk badges (**High**, **Medium**, **Low**).
3. **Strict Zero-Flag Invariant:** Messages with zero detected red flags are flagged as *"No known red flags found – stay cautious"*. **No message is ever labelled "Safe"**.
4. **Privacy-First Data Protection:** 
   - Raw personal data is masked with placeholders (`[PHONE]`, `[OTP]`, `[ACCOUNT]`) before any external service or LLM invocation.
   - Raw messages are **never** stored or logged to any database.
5. **Human-in-the-Loop OCR:** Uploaded screenshots are extracted via Tesseract OCR and displayed in an editable review window side-by-side with the image so the user can verify/correct misspelled text before analysis.

---

## 🏗️ Architecture & Pipeline Flow

```
[ User Input (Text or Screenshot) ]
                 │
                 ▼
[ Tesseract OCR (eng + hin) ] ──► [ User Review & Correction Window ]
                 │
                 ▼
[ Preprocessing & Hinglish Normalisation ]
                 │
                 ▼
[ Sensitive PII Masking: [PHONE], [OTP], [ACCOUNT] ]
                 │
                 ▼
[ Deterministic Rule Engine (data/red_flags.json) ]
                 ├──► Weighted Scoring (<=2 Low, 3-5 Medium, >=6 High)
                 └──► Category Classification (6 Target Categories)
                 │
        ┌────────┴──────────────────────────┐
        ▼                                   ▼
[ Static Safety Actions ]        [ Explanation Engine ]
  (data/actions.json)              (data/templates.json)
  • Category Do's & Don'ts         • Google Gemini API (google-genai SDK)
  • Official Helplines (1930)      • Fallback to predefined templates
        │                                   │
        └─────────────────┬─────────────────┘
                          ▼
            [ Accessible UI / JSON Response ]
```

---

## 📦 Project Structure

```
SchamShield/
├── docs/
│   ├── ScamShield_Synopsis.docx
│   └── ScamShield_Use_Case_Specifications.docx
├── data/
│   ├── red_flags.json           # Red flags, weights, multilingual patterns, category mappings
│   ├── actions.json             # Predefined category safety actions & official helplines (EN & HI)
│   ├── templates.json           # Predefined plain-language explanations & fallback templates
│   ├── sample_dataset.csv       # 30 labelled messages (dev/test split, scam across 6 categories + genuine)
│   └── tessdata/                # Tesseract OCR language packs (eng.traineddata, hin.traineddata)
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application, REST endpoints, static file mounting
│   ├── schemas.py               # Pydantic models for request/response & config validation
│   ├── database.py              # SQLite storage for anonymised feedback only (NEVER raw messages)
│   └── pipeline/
│       ├── __init__.py
│       ├── preprocess.py        # Normalisation & sensitive data masking ([PHONE], [OTP], [ACCOUNT])
│       ├── rules.py             # Weighted rule engine, threshold scoring, category classifier
│       ├── ocr.py               # Tesseract OCR wrapper for English & Hindi screenshot reading
│       ├── explain.py           # Gemini API integration via google-genai SDK + template fallback
│       └── actions.py           # Predefined safety action checklists
├── static/
│   ├── index.html               # Senior-accessible single-page interface
│   ├── css/
│   │   └── style.css            # 20px+ font, high contrast, responsive accessible layout
│   └── js/
│       ├── i18n.js              # Complete English and Hindi UI translation dictionary
│       └── app.js               # Frontend controller: OCR preview & edit flow, analysis, feedback
├── tests/
│   ├── test_rules.py            # Rule engine unit tests (including mandatory CBI test case)
│   ├── test_preprocess.py       # PII masking & Hinglish normalisation tests
│   ├── test_ocr.py              # OCR extraction & error resilience tests
│   ├── test_explain.py          # LLM template fallback & feedback privacy tests
│   └── test_api.py              # FastAPI endpoint integration tests
├── evaluate.py                  # CLI evaluation tool (Precision, Recall, Accuracy, Confusion Matrix)
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment configuration template
├── .gitignore
└── README.md
```

---

## 🛠️ Tech Stack

- **Backend:** Python 3.11, FastAPI, Pydantic v2, Uvicorn
- **OCR:** Tesseract OCR via `pytesseract` (languages: English + Hindi)
- **Detection & Actions:** Pure Python rule engine, configurable JSON files
- **AI Explanation:** Google Gemini API (`google-genai` SDK) with graceful static template fallback
- **Database:** SQLite (strictly anonymised feedback; raw messages are never stored)
- **Frontend:** Plain HTML5, CSS3, JavaScript (no framework overhead), served by FastAPI
- **Testing:** `pytest`, `pytest-asyncio`

---

## 🚀 Setup & Installation (Windows)

### 1. Prerequisites
- **Python 3.11+** installed and added to PATH.
- **Tesseract OCR**:
  - Install via Windows Package Manager:
    ```powershell
    winget install UB-Mannheim.TesseractOCR
    ```
  - Standard installation directory: `C:\Program Files\Tesseract-OCR\tesseract.exe`.
  - The project comes pre-configured with Hindi (`hin.traineddata`) and English (`eng.traineddata`) language models in `data/tessdata/`.

### 2. Clone / Open Workspace & Create Virtual Environment
```powershell
cd c:\Users\THINKPAD\Downloads\SchamShield

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1
```

### 3. Install Python Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
Open `.env` and set your Google Gemini API key:
```ini
GEMINI_API_KEY=AIzaSy...your_actual_key_here
TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
```
*(Note: If `GEMINI_API_KEY` is not provided or fails, ScamShield automatically and transparently falls back to certified predefined template explanations from `data/templates.json`.)*

---

## 🏃 Running the Application

Start the FastAPI server:
```powershell
uvicorn app.main:app --reload --port 8000
```
Open your web browser and navigate to:
```
http://localhost:8000
```

---

## 🧪 Running Unit & Integration Tests

Execute the complete test suite (30 automated tests):
```powershell
pytest tests/ -v
```

All tests verify:
1. **Mandatory Test Case:** `"Main CBI officer bol raha hu. Aapke naam par arrest warrant hai. Turant 50,000 transfer kijiye aur kisi ko mat batana."` $\rightarrow$ **High risk, Digital Arrest**, matched flags: *authority_impersonation, urgency_threat, immediate_payment, secrecy_demand*.
2. **Zero-Flag Invariant:** Harmless messages score 0 and are **never** labelled "Safe".
3. **Threshold Boundaries:** Low ($\le 2$), Medium ($3-5$), High ($\ge 6$).
4. **Hinglish Normalisation & PII Masking:** Phone numbers, OTPs, bank accounts, cards, UPI IDs, PAN, and Aadhaar numbers.
5. **OCR Extraction:** Image text handling and blank image fallbacks.
6. **Graceful Degradation:** Template explanation fallback on missing API keys or network timeouts.
7. **Feedback Privacy:** SQLite schema verification ensuring zero raw text columns.

---

## 📊 Performance Evaluation (`evaluate.py`)

ScamShield includes an evaluation harness (`evaluate.py`) that benchmarks the deterministic rule engine on labelled message datasets **without** invoking external LLM APIs.

### Run on the Included 30-Message Benchmark:
```powershell
# Evaluate entire dataset (30 samples)
python evaluate.py --split all

# Evaluate Development set
python evaluate.py --split dev

# Evaluate Test set
python evaluate.py --split test
```

### Benchmark Results Summary:
```
====================================================================
 ScamShield Performance Evaluation Report  (Split: ALL)
====================================================================
 Total Samples Evaluated : 30
 Total Scams in Set      : 20
 Total Genuine in Set    : 10
--------------------------------------------------------------------
 Accuracy                : 100.00%
 Precision               : 100.00%
 Recall                  : 100.00%
 F1-Score                : 100.00%
 Category Accuracy       : 90.00% (18/20)
--------------------------------------------------------------------
 Confusion Matrix:
                      Predicted Scam    Predicted Genuine
   Actual Scam       :     20              0               (Total: 20)
   Actual Genuine    :     0               10              (Total: 10)
====================================================================
```

### Evaluating Custom Datasets (150–200 Messages):
To test on your own research dataset, provide a CSV with columns: `id,message,label,category,split` and pass it via the CLI:
```powershell
python evaluate.py --dataset path/to/your_dataset.csv --split test
```

---

## 📋 Use Case Specifications Coverage (`UC1`–`UC13`)

| Use Case ID | Description | Implementation Component |
|-------------|-------------|--------------------------|
| **UC1** | Submit Suspicious Message (Abstract) | `app/main.py` (`POST /api/analyze`) |
| **UC2** | Enter / Paste Message Text | `static/index.html` (`#message-input`) |
| **UC3** | Upload Screenshot | `static/index.html` (`#screenshot-file`), `app/main.py` (`POST /api/ocr`) |
| **UC4** | Extract Text (OCR via Tesseract) | `app/pipeline/ocr.py` (`extract_text_from_image`) |
| **UC5** | Review & Correct Extracted Text | `static/index.html` (`#ocr-box`), side-by-side preview & text editor |
| **UC6** | Select Language (English / Hindi) | `static/js/i18n.js`, real-time toggle switch |
| **UC7** | Preprocess & Mask Sensitive Data | `app/pipeline/preprocess.py` (`preprocess_message`, `mask_sensitive_data`) |
| **UC8** | Detect Red Flags, Classify & Score | `app/pipeline/rules.py` (`RuleEngine.evaluate`) |
| **UC9** | View Analysis Result | `static/index.html` (`#results-section`), colored risk banner & actions |
| **UC10** | Read Plain-Language Explanation | `app/pipeline/explain.py` (Gemini API + `data/templates.json` fallback) |
| **UC11** | Submit User Feedback (Optional) | `static/js/app.js`, `app/database.py` (SQLite anonymised feedback) |
| **UC12** | Manage Rules, Weights & Actions | `data/red_flags.json`, `data/actions.json`, `data/templates.json` |
| **UC13** | Evaluate Detection Performance | `evaluate.py` (Precision, Recall, Accuracy, Confusion Matrix) |

---

## 🛡️ Target Scam Categories Covered

1. **Digital Arrest Scam:** Impersonation of CBI, Police, Customs, or Judges threatening arrest over video call, demanding money transfers to "safe accounts".
2. **KYC / Account-Block Fraud:** Pretexts claiming PAN suspended, SIM deactivated, or power disconnection, requesting remote-access apps (AnyDesk) or phishing links.
3. **Lottery / Prize Scam:** Fake KBC or lucky draw winnings requiring upfront registration fees or taxes.
4. **Job Scam:** Unrealistic work-from-home offers requiring advance documentation or security deposits.
5. **Loan Scam:** Fake pre-approved instant loans demanding advance processing fees to personal UPI IDs.
6. **Family Emergency Scam:** Callers pretending a child or relative is hospitalized or in police custody, requiring urgent funds under secrecy.
7. **General Suspicious:** Communication with mixed or unclassified high-pressure tactics.

---

## 👥 Authors & Acknowledgments

- **Ashish Chachodiya** (EN24CS3060011)
- **Harshvardhan Singh Sisodiya** (EN24CS3060021)
- **Ishan Dabriya** (EN24CS3060022)

*Department of Computer Science & Engineering, Medicaps University, Indore (Aug–Dec 2026)*
