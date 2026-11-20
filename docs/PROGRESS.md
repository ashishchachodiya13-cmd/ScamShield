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

---

## Stage 1 — Auth Backend + Safe DB Migrations

- **Date:** November 2026
- **What Changed:**
  - Added new allowed Python dependencies: `argon2-cffi`, `PyJWT`, `httpx` to `requirements.txt`.
  - Added environment configuration (`APP_ENV`, `JWT_SECRET`, `COOKIE_SECURE`) to `.env.example` with placeholders; created `app/config.py` enforcing production secret safety checks.
  - Implemented unit-testable in-memory sliding window rate limiter (`app/limiter.py`).
  - Implemented password hashing using Argon2id, JWT creation/decoding, hashed single-use password resets, CSRF protection, and email logging stub (`app/security.py`).
  - Built idempotent database migration runner (`app/migrations/runner.py`) with automatic backup creation (`data/backups/`), `PRAGMA user_version` tracking, `PRAGMA foreign_keys = ON`, and WAL journal mode.
  - Added migration `001_initial_schema.py` creating `users`, `sessions`, `analyses`, `preferences`, `password_resets`, and safely extending `feedback` with `analysis_id` and indexing.
  - Upgraded `app/database.py` with thread-safe connection manager and DAOs for users, preferences, sessions, and password resets while preserving backward compatibility for `save_feedback` and `get_feedback_stats`.
  - Added authentication Pydantic models to `app/schemas.py`.
  - Implemented full auth router (`app/routers/auth.py`) providing `/register`, `/login`, `/logout`, `/forgot-password`, `/reset-password`, `/me` (GET, PATCH, DELETE) with rate limiting, generic error messages, session revocation, and CSRF protection.
  - Mounted auth router in `app/main.py` while keeping guest analysis (`POST /api/analyze`) completely open.
  - Created automated migration tests (`tests/test_migrations.py`) and auth test suite (`tests/test_auth.py`).
- **Tests Status:**
  - `pytest -q`: **43 passed, 2 failed** in 2.61s.
    - 15 new tests passing: 3 migration tests + 12 comprehensive auth tests.
    - 0 regressions in pre-existing tests. (The 2 failures remain the pre-existing OCR tests due to missing host Tesseract binary).
  - `evaluate.py --split all`: Accuracy 100%, Precision 100%, Recall 100%, F1-Score 100%, Category Accuracy 90%.
- **Known Gaps:**
  - Frontend auth UI (login/signup forms, session handling) is scheduled for Stage 4.
  - Saving analyses to database for authenticated users is scheduled for Stage 2.

---

## Stage 2 — History, Stats, Reports & Privacy API

- **Date:** November 2026
- **What Changed:**
  - Extended `AnalysisRequest` (optional `source`), `AnalysisResponse` (optional `analysis_id`), and `FeedbackRequest` (optional `analysis_id`) in `app/schemas.py`.
  - Added Pydantic schemas for History (`HistoryItemResponse`, `HistoryListResponse`, `HistoryDetailResponse`), Stats (`StatsOverviewResponse`, `ReportsResponse`), and Preferences (`PreferencesUpdateRequest`).
  - Added database functions to `app/database.py` for analyses persistence, user-scoped querying, pagination, search, detail retrieval, individual and bulk deletion, SQL aggregate dashboard stats, date-ranged reports analytics, and anonymized CSV/JSON export.
  - Implemented `app/routers/history.py` providing user-scoped `GET /api/history` (with search, risk/category filters, date ranges, pagination), `GET /api/history/{id}` (reconstructing matched flags, certified actions, and templates; returning 404 for other users' IDs), `DELETE /api/history/{id}`, and `DELETE /api/history` (requiring `confirm=true`).
  - Implemented `app/routers/stats.py` providing `GET /api/stats/overview` (SQL aggregates, zero hardcoded numbers), `GET /api/stats/reports` (week/month/all ranges with percentages and timeline), and `GET /api/reports/export` (anonymized CSV or JSON export with strict privacy guarantees).
  - Implemented `app/routers/preferences.py` providing `GET /api/preferences` and `PUT /api/preferences` (with CSRF protection).
  - Updated `POST /api/analyze` in `app/main.py`: automatically saves anonymized analysis metadata for authenticated users, respects `preferences.retain_masked_text` (default off), and leaves guest scans completely unsaved (`analysis_id=None`).
  - Updated `POST /api/feedback` in `app/main.py` to link `analysis_id` when submitted.
  - Mounted all Stage 2 routers in `app/main.py`.
  - Added comprehensive test suite in `tests/test_history_stats.py` verifying history CRUD, user isolation (404 on other users' records), empty-state stats, SQL aggregate calculation, anonymized CSV/JSON export, preferences updating, masked-text retention opt-in, and full-database privacy assertions (zero raw text, phone numbers, or OTPs anywhere in SQLite).
- **Tests Status:**
  - `pytest -q`: **53 passed, 2 failed** in 3.65s.
    - 10 new tests passing in `tests/test_history_stats.py`.
    - Total tests: 55 (53 passed; 2 failures are pre-existing OCR tests due to missing Tesseract binary on the host OS).
    - 0 regressions across all tests.
  - `evaluate.py --split all`: Accuracy 100.00%, Precision 100.00%, Recall 100.00%, F1-Score 100.00%, Category Accuracy 90.00%.
- **Known Gaps:**
  - Frontend UI for dashboard, history drawer, reports charts, and preferences settings is scheduled for Stages 4–6.
  - Expanded scam category detection (Investment/Trading, Suspicious UPI, Fake Bank, Govt Impersonation) is scheduled for Stage 3.
