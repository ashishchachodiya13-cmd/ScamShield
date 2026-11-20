# SCAMSHIELD UPGRADE RULES (ALWAYS-ON)

You are working on ScamShield: an AI-assisted decision-support tool that helps senior citizens in India judge suspicious SMS / WhatsApp / call-transcript messages. Python 3.11, FastAPI, SQLite, vanilla HTML/CSS/JS, Tesseract OCR (eng+hin), Google Gemini API.
The project already works. It is an UPGRADE of the existing code in this folder. Never start a second project.

## NON-NEGOTIABLE PRODUCT RULES
- The deterministic rule engine (app/pipeline + data/*.json) alone decides red flags, category, score and risk level. Gemini only writes the plain-language explanation from the masked text, category and matched flags. If Gemini fails, the predefined template is used. Safety actions come only from data/actions.json, never from the LLM.
- A message with no red flag is shown as "No known red flag found - stay cautious". Never label anything "Safe" or "Genuine".
- Mask phone numbers, OTPs, account numbers BEFORE any text leaves the server (LLM call) and before anything is logged.
- Never store raw messages, screenshots, OCR text, OTPs, phone numbers or account numbers. Store only anonymised metadata (time, risk level, score, category, flag IDs).
- Never log personal data, passwords, tokens or API keys.
- Keep Hindi/Hinglish normalisation, OCR review step, feedback, existing rules and all existing tests. Do not delete or weaken a failing test to make it pass; fix the cause.
- Do not change existing API response shapes without updating every consumer and the tests. Prefer adding new endpoints.
- Do not claim a feature works unless you ran it or a test proves it. Features needing a real phone must be listed in docs/MOBILE_TEST_CHECKLIST.md as "NOT VERIFIED - manual test needed".

## ENGINEERING RULES
- Allowed new Python deps only: argon2-cffi, PyJWT, python-multipart, httpx (tests). Rate limiting: small in-memory limiter module or slowapi. Frontend: no framework, no build step; Chart.js 4.x vendored locally in static/vendor; icons as inline SVG (Lucide style); no emoji icons.
- Secrets only from environment (.env). Never overwrite the user's .env. Maintain .env.example with placeholders.
- Keep the app runnable after every stage: `uvicorn app.main:app --reload`.
- After each stage: run `pytest -q`, fix regressions, then append a short entry to docs/PROGRESS.md (stage, what changed, tests status, known gaps). Do not do work from other stages.
- Stop at the end of the stage and report: files changed, tests result, what I should manually check.
