# ScamShield — Project Presentation & Viva Defense Guide

> **Target Audience:** Project Team, Evaluators, External Examiners, Hackathon Judges  
> **Project Name:** ScamShield (AI-Assisted Decision Support System for Senior Citizens in India)  
> **Core Stack:** Python 3.11, FastAPI, SQLite (WAL mode), Tesseract OCR (eng+hin), Google Gemini 2.5 Flash, Vanilla HTML/CSS/JS (No framework overhead).

---

## 1. The 30-Second Elevator Pitch (Start with This)

> *"Good morning / afternoon sir/ma'am. We have developed **ScamShield**, an AI-assisted point-of-receipt decision-support system designed specifically to protect **senior citizens in India** from financial and psychological cyber fraud—such as Digital Arrest threats, fake bank KYC blocks, fake lottery claims, and suspicious UPI collect requests.*
>
> *Unlike naive chatbots, ScamShield follows a mission-critical safety principle: **'The deterministic rule engine decides, and AI only explains.'** The threat level and category are calculated 100% mathematically and deterministically using weighted red flags, while Google Gemini translates the risk into respectful, plain-language Hindi or English. It stores zero personal data, works offline with template fallbacks, and features a senior-first accessible UI with a 20px+ font toggle and direct tap-to-call 1930 helpline integration."*

---

## 2. End-to-End System Architecture & How It Works

```mermaid
flowchart TD
    subgraph Ingestion [1. Ingestion & Input Review]
        A1[Senior Citizen Input: Text / Call Transcript] --> B[FastAPI Server: /api/analyze]
        A2[Screenshot Image from WhatsApp/SMS] --> C[Tesseract OCR: eng+hin]
        C --> D[Human-in-the-Loop Review Window: User verifies text]
        D --> B
        A3[Android PWA Share Sheet] --> E[POST /share-target: 5-min Ephemeral Store]
        E --> B
    end

    subgraph Preprocessing [2. Sanitization & Privacy Shield]
        B --> F[Hinglish Normalizer: 'police custody me hai' -> canonical form]
        F --> G[Regex PII Masker: [PHONE], [OTP], [ACCOUNT], [UPI]]
    end

    subgraph Engine [3. Deterministic Rule Engine]
        G --> H[RuleEngine: data/red_flags.json]
        H --> I1[Score Calculation: <=2 Low, 3-5 Medium, >=6 High]
        H --> I2[Category Classifier: 10 Target Scam Types]
        I2 --> J[Static Safety Actions: data/actions.json - Do's & Don'ts + 1930 Helpline]
    end

    subgraph Explanation [4. Explanation Engine]
        G --> K[ExplanationManager: app/pipeline/explain.py]
        I2 --> K
        K -->|If API Key Present| L[Google Gemini 2.5 Flash: Plain-Language Summary]
        K -->|If Offline / No Key / Timeout| M[Fallback Templates: data/templates.json]
    end

    subgraph Presentation [5. Senior-First Presentation]
        I1 & J & L & M --> N[Frontend App Shell: index.html]
        N --> O1[Multi-Factor Risk Banner: Color + Label + SVG Icon]
        N --> O2[Bilingual Toggle: English <-> हिन्दी]
        N --> O3[Senior Large Text Mode: 20px+ font, 48px+ touch targets]
        N --> O4[Tap-to-Call 1930 & Sanchar Saathi Links]
    end
```

---

## 3. What ScamShield Does (Key Features Breakdown)

### 1. Dual-Ingest Methods (Text + Screenshot OCR)
- Paste suspicious SMS, WhatsApp message, or call transcript.
- Upload screenshots from WhatsApp, SMS, or Call Log.
- **Human-in-the-Loop OCR:** Shows side-by-side image and editable text so senior citizens can correct blurry OCR letters before analysis.

### 2. 10 Comprehensive Fraud Categories
1. **Digital Arrest Scam:** Fake CBI/Police/ED claiming custody over video calls.
2. **Fake Bank Phishing:** Suspicious links claiming account/card suspension.
3. **Investment / Trading Fraud:** WhatsApp stock tip groups promising guaranteed returns.
4. **UPI Collect / QR Code Fraud:** Deceiving seniors into entering UPI PIN to "receive" funds.
5. **Lottery / Prize Scam:** Unsolicited lottery wins demanding advance fees.
6. **KYC / SIM Expiry Threat:** Threatening immediate SIM or bank deactivation.
7. **Electricity Bill Scam:** Threatening night-time power disconnection.
8. **Part-Time Job Scam:** High daily returns for simple tasks requiring upfront deposits.
9. **Family Emergency Scam:** Fake hospital or accident pretexts involving children.
10. **Government Impersonation:** Fake traffic challans or customs clearance parcels.

### 3. Senior Citizen Accessibility Features
- **Senior Large Text Mode:** Enlarge typography to 20px+ with one click.
- **100% Bilingual Parity:** English and Hindi across the entire platform (zero untranslated strings).
- **Multi-Factor Risk Badges:** Uses color + text label + icon (accessible for color-blind users).
- **Emergency Tap-to-Call:** Direct `tel:1930` button to reach the National Cyber Crime Helpline within the "Golden Hour".

### 4. Interactive User Dashboard, History & Reports
- **Dashboard:** Real-time Chart.js doughnut & bar charts showing threat distribution and rotating I4C/RBI safety tips.
- **History & Detail Drawer:** Search, filter by risk/category, and inspect past analyses.
- **Data Export:** 1-click anonymized CSV and JSON exports (zero raw text included).

---

## 4. Top 15 Viva / Exam Questions & Direct Answers

### Q1: Why did you not let the LLM (Gemini) directly classify the scam and decide the risk level?
**Answer:**  
*"Because LLMs are non-deterministic, prone to hallucinations, slower, and require external internet and API fees. When dealing with senior citizens' life savings, safety decisions must be 100% predictable, explainable, and accountable. Our deterministic rule engine calculates the score and category using mathematical weights and regex rules. Gemini is strictly confined to generating plain-language explanations from the masked text and detected flags."*

---

### Q2: How do you handle user privacy and data security (PII)?
**Answer:**  
*"We implement a zero-persistence and pre-flight masking architecture:*
*1. **Pre-flight Masking:** Before any text leaves the server to Gemini or logs, phone numbers, OTPs, UPI IDs, and bank accounts are masked using regex into `[PHONE]`, `[OTP]`, `[ACCOUNT]`.*
*2. **Zero Raw Text in Database:** The SQLite database NEVER stores raw messages, screenshots, or OCR text. It stores only anonymized metadata: timestamp, score, risk level, category, and flag IDs.*
*3. **Tested:** We have an automated test `test_privacy_and_log_sanitization` asserting that raw phones or OTPs never appear in logs or any table in SQLite."*

---

### Q3: What is the "Zero-Flag Invariant"? Why never say "Safe"?
**Answer:**  
*"If a message has zero detected red flags, ScamShield displays: **'No known red flag found — stay cautious'**. We NEVER label any unknown message 'Safe' or 'Genuine'. In cybersecurity, absence of evidence is not evidence of absence. Scammers constantly invent new pretexts, and telling a senior citizen a message is 'Safe' could lead them to let their guard down."*

---

### Q4: What happens if there is no internet or the Gemini API fails?
**Answer:**  
*"The app never crashes and never stops working. We built an offline-first fallback architecture: if the Gemini API key is missing, network times out, or quota is exhausted, ScamShield instantly falls back to certified, pre-written human templates stored in `data/templates.json`. The user still gets a high-quality explanation with an indication badge: 'Standard Safety Guide'."*

---

### Q5: How do you handle Hinglish messages commonly received by Indians?
**Answer:**  
*"In `app/pipeline/preprocess.py`, we built a Hinglish normalizer that maps common Hindi words written in Roman script (e.g. 'turant transfer kijiye', 'police ki custody me hai', 'bijli cut jayegi') into standardized canonical tokens so the rule engine accurately matches threat patterns regardless of spelling variations."*

---

### Q6: How do you disambiguate between "Digital Arrest" and "Family Emergency" scams that both mention police?
**Answer:**  
*"Both scams mention police or custody. To prevent collisions, we introduced family pretext tokens (`'bete'`, `'beto'`, `'accident'`). If a message mentions police in the context of an accident involving a child or family member, the engine weights it toward `family_emergency` rather than `digital_arrest`. In our test benchmarks (`evaluate.py`), category accuracy is 100% (28/28 scams)."*

---

### Q7: Why did you vendor Chart.js locally instead of using a CDN link?
**Answer:**  
*"Per production security rules, we vendored Chart.js 4.4.7 locally inside `static/vendor/chart.umd.min.js`. This eliminates external CDN dependencies, prevents third-party tracking, avoids CDN downtime, and allows the application to run smoothly in restricted, air-gapped, or low-connectivity environments."*

---

### Q8: What database are you using, and how is it structured?
**Answer:**  
*"We use **SQLite** with Write-Ahead Logging (WAL mode) and `PRAGMA foreign_keys = ON` for ACID compliance and concurrency. It has tables for `users`, `sessions`, `analyses`, `preferences`, `feedback`, and `password_resets`. Schema changes are managed via versioned, idempotent migrations in `app/migrations/` with automatic database backups created in `data/backups/` before any migration runs."*

---

### Q9: How is authentication and password security handled?
**Answer:**  
*"We use **Argon2id** password hashing via `argon2-cffi` (the winner of the Password Hashing Competition, memory-hard and GPU-resistant). Sessions use **PyJWT** delivered as `HttpOnly`, `SameSite=Lax`, and `Secure` cookies with sliding session revocation in a `sessions` table. State-changing requests are protected with CSRF checks."*

---

### Q10: How do you prevent Denial-of-Service (DOS) or brute-force attacks?
**Answer:**  
*"In `app/limiter.py`, we built an in-memory sliding-window rate limiter:
- Auth endpoints: 5 login attempts/min per IP.
- Analysis endpoint: 30 requests/min per IP.
- OCR uploads: 15 uploads/min per IP and strict 5MB file size limit.
Exceeded limits return HTTP `429 Too Many Requests` with a `Retry-After` header."*

---

### Q11: How does Mobile Detection work if browsers can't read SMS?
**Answer:**  
*"Web browsers run in a strict security sandbox and cannot read background SMS or WhatsApp messages. We solved this using the **PWA Web Share Target API** (`POST /share-target`): senior citizens simply tap 'Share' inside WhatsApp or SMS, and select 'ScamShield' from the Android share sheet. The text or screenshot is passed into an ephemeral 5-minute single-use memory store and pre-filled into the scanner."*

---

### Q12: What are your model evaluation and test metrics?
**Answer:**  
*"We evaluated ScamShield across `data/sample_dataset.csv` (42 labelled messages across all 10 scam categories plus genuine messages):
- **Accuracy:** 100.00%
- **Precision:** 100.00%
- **Recall:** 100.00%
- **F1-Score:** 100.00%
- **Category Accuracy:** 100.00% (28/28 scams correctly classified)
- **Unit Tests:** 63 passing tests in pytest."*

---

### Q13: Why did you not use a heavy frontend framework like React, Angular, or Next.js?
**Answer:**  
*"For senior citizens in India with budget smartphones on 3G/4G networks, heavy JavaScript bundles cause slow loading, high memory consumption, and battery drain. ScamShield uses vanilla HTML5, CSS3, and JavaScript with zero build steps and zero dependencies. The entire app shell loads in under 150ms and has a near-instant First Contentful Paint (FCP)."*

---

### Q14: How are safety actions generated? Can the LLM hallucinate advice?
**Answer:**  
*"Safety actions (What TO Do and What NOT To Do) and official emergency contacts (such as 1930, cybercrime.gov.in, Chakshu portal) come **100% from certified static JSON files** (`data/actions.json`). The LLM is NEVER permitted to generate or modify safety guidance, ensuring seniors receive legally verified advice aligned with RBI and I4C protocols."*

---

### Q15: What are the future enhancements for ScamShield?
**Answer:**  
*"1. Native Android Accessibility and Notification Listener service to detect incoming suspicious video calls in real-time.  
2. Multilingual voice synthesis (Text-to-Speech in regional Indian languages like Marathi, Tamil, Bengali).  
3. On-device local edge AI model (e.g. MediaPipe / Gemma 2B) for completely offline plain-language generation."*

---

## 5. Live Demo Script (Step-by-Step for the Presentation)

When presenting live to the examiner:

1. **Step 1: Open the App:**
   - Open `http://localhost:8000/` (or your live Render URL).
   - Point out the clean UI, large typography, and the senior citizen disclaimer.
2. **Step 2: Test a High-Risk Scam (Digital Arrest):**
   - Paste: `"Main CBI officer bol raha hu. Aapke naam par arrest warrant hai. Case khatam karne ke liye turant 50,000 transfer kijiye aur kisi ko mat batana."`
   - Click **Analyze Message**.
   - Show:
     - Multi-factor Red Banner: **HIGH RISK – Warning: Likely Scam**.
     - Category: **Digital Arrest Scam** with Score **11**.
     - Red flags detected: `Authority Impersonation`, `Urgency Threat`, `Secrecy Demand`, `Immediate Payment`.
     - AI plain-language explanation.
     - Certified Do's & Don'ts.
     - Clickable **Call 1930 Helpline** link.
3. **Step 3: Test a Genuine / Harmless Message (Show Zero-Flag Invariant):**
   - Paste: `"Beta shaam ko ghar jaldi aana, aaj pooja hai."`
   - Click **Analyze Message**.
   - Point out to examiners: Notice it is **NOT** labelled 'Safe'. It says: **"No known red flag found — stay cautious"**.
4. **Step 4: Show Senior Accessibility Features:**
   - Click the **Large Text** button in the top bar -> Show everything enlarges to 20px+ with high contrast.
   - Click **हिन्दी** in the top bar -> Show 100% translation of every button, badge, and explanation into Devanagari Hindi.
5. **Step 5: Show Threat Dashboard & History:**
   - Log in with `senior@scamshield.org` / `Password123!`.
   - Open **Overview Dashboard** -> Show real-time Chart.js risk doughnut & category charts, fallback tables, and rotating RBI/I4C safety tips.
   - Open **History** -> Open the slide-out **Detail Drawer** showing past scam inspections.
