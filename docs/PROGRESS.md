# ScamShield — Upgrade Progress Log

This document tracks the iterative upgrade of ScamShield across Stages 0 through 8.

---

## Stage 0 — Audit Only (Baseline Inspection)

- **Date:** November 2026
- **What Changed:**
  - Initialized git repository baseline commit before upgrade.
  - Saved always-on workspace rules in `AGENTS.md`.
  - Conducted full inspection of existing codebase (`app/`, `data/`, `static/`, `tests/`, `evaluate.py`, `README.md`).
  - Generated comprehensive system audit in `docs/AUDIT.md` covering architecture, request flows, API contracts, database schema, security & privacy boundaries, limitations, and non-negotiable behaviors.
  - Mapped out adjusted implementation checklist for Stages 1–8.
- **Tests Status:**
  - `pytest -q`: **28 passed, 2 failed** in 7.35s.
    - Failures: `tests/test_ocr.py::test_ocr_with_text_image` and `test_ocr_with_blank_image` due to missing Tesseract OCR binary on host machine.
    - 28 core tests passed (rules, Hinglish normalisation, PII masking, Gemini fallback, zero-flags, feedback database, API endpoints).
  - `evaluate.py --split all`:
    - Total evaluated: 30 (20 scam, 10 genuine).
    - Accuracy: **100.00%**
    - Precision: **100.00%**
    - Recall: **100.00%**
    - F1-Score: **100.00%**
    - Category Accuracy: **90.00% (18/20)**
- **Known Gaps:**
  - Missing local Tesseract OCR engine on the test machine causes OCR tests to fail when asserting successful recognition.
  - Category classification ambiguity in `evaluate.py` for messages 18 & 20 (family emergency accident pretexts involving police custody classified as `digital_arrest`).
  - No authentication, user accounts, sessions, or historical analysis tracking (scheduled for Stages 1 & 2).
  - Open CORS (`*` with credentials) and absent rate limiting (scheduled for Stages 1 & 8).
