import os
import time
import uuid
from typing import Dict, Tuple, Optional
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    OCRResponse,
    FeedbackRequest,
)
from app.pipeline.preprocess import preprocess_message
from app.pipeline.rules import RuleEngine
from app.pipeline.ocr import extract_text_from_image
from app.pipeline.actions import ActionsManager
from app.pipeline.explain import ExplanationManager
from app.database import (
    init_db,
    save_feedback,
    get_feedback_stats,
    create_analysis,
    get_user_preferences,
)
from app.routers.auth import get_current_user_optional
from app.limiter import limiter

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="ScamShield",
    description="AI-Assisted Decision-Support System for Scam Communication Identification",
    version="1.0.0",
)

# CORS middleware with environment-based configuration (Stage 8)
cors_env = os.getenv("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000")
allowed_origins = [o.strip() for o in cors_env.split(",") if o.strip()]
if "*" in allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )


# HTTP Security Headers Middleware (Stage 8)
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "connect-src 'self'; "
        "font-src 'self' data:; "
        "frame-ancestors 'none';"
    )
    return response


# In-memory single-use 5-minute store for shared mobile content (Stage 7)
_share_store: Dict[str, Tuple[float, dict]] = {}


def _clean_expired_shares():
    now = time.time()
    expired = [k for k, v in _share_store.items() if v[0] < now]
    for k in expired:
        _share_store.pop(k, None)


# Initialize pipeline singletons
rule_engine = RuleEngine()
actions_manager = ActionsManager()
explanation_manager = ExplanationManager()
init_db()

# Mount API routers
from app.routers import auth as auth_router
from app.routers import history as history_router
from app.routers import stats as stats_router
from app.routers import preferences as preferences_router

app.include_router(auth_router.router)
app.include_router(history_router.router)
app.include_router(stats_router.router)
app.include_router(preferences_router.router)


@app.get("/")
async def serve_index():
    """Serves the main senior-citizen friendly web interface."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Index file not found")
    return FileResponse(index_file)


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_message(req: AnalysisRequest, request: Request):
    """
    Main analysis pipeline:
    1. Validates input text and enforces sliding window rate limiting.
    2. Preprocesses Hinglish and masks sensitive data (PII).
    3. Evaluates red flags and calculates weighted risk score & category.
    4. Retrieves predefined category safety actions.
    5. Generates plain-language explanation (LLM or template fallback).
    """
    client_ip = limiter.get_client_ip(request)
    allowed, retry_after = limiter.check(f"analyze:{client_ip}", limit=30, window_seconds=60)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many analysis requests. Please wait a moment.",
            headers={"Retry-After": str(retry_after)},
        )

    raw_text = req.text.strip()
    if not raw_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message text cannot be empty. Please paste a message or upload a screenshot."
        )

    # Step 1: Preprocess (normalize Hinglish) and mask sensitive identifiers
    cleaned_normalized, masked_text = preprocess_message(raw_text)

    # Step 2: Rule Engine evaluation
    eval_result = rule_engine.evaluate(cleaned_normalized)

    category_id = eval_result["category_id"]
    category_name = (
        eval_result["category_name_hi"] if req.language == "hi" else eval_result["category_name_en"]
    )
    matched_flags = eval_result["matched_flags"]
    is_zero_flags = eval_result["is_zero_flags"]
    risk_level = eval_result["risk_level"]
    score = eval_result["score"]

    # Step 3: Predefined Safety Actions (never LLM generated)
    actions = actions_manager.get_actions(category_id, language=req.language)

    # Step 4: Plain-language explanation (Gemini LLM or Template fallback)
    explanation, explanation_source = explanation_manager.explain(
        masked_text=masked_text,
        category_id=category_id,
        category_name=category_name,
        matched_flags=matched_flags,
        language=req.language,
        is_zero_flags=is_zero_flags,
    )

    # Step 5: Save anonymized analysis record if user is authenticated (Stage 2)
    analysis_id = None
    user = get_current_user_optional(request)
    if user is not None:
        prefs = get_user_preferences(user["id"])
        retain_masked = bool(prefs["retain_masked_text"]) if prefs else False
        stored_masked = masked_text if retain_masked else None
        flag_ids = [f.id for f in matched_flags]
        analysis_id = create_analysis(
            user_id=user["id"],
            risk_level=risk_level,
            score=score,
            category=category_id,
            flag_ids=flag_ids,
            language=req.language,
            source=req.source,
            masked_text=stored_masked,
        )

    return AnalysisResponse(
        risk_level=risk_level,
        score=score,
        category=category_id,
        category_name=category_name,
        matched_flags=matched_flags,
        explanation=explanation,
        explanation_source=explanation_source,
        actions=actions,
        avoid=actions.donts,
        reporting_channels=actions.official_channels,
        language=req.language,
        masked_text=masked_text,
        analysis_id=analysis_id,
    )


@app.post("/api/ocr", response_model=OCRResponse)
async def ocr_screenshot(request: Request, file: UploadFile = File(...)):
    """
    Extracts text from an uploaded screenshot using Tesseract OCR.
    Enables user to review and correct the extracted text before running analysis (UC3, UC4, UC5).
    """
    client_ip = limiter.get_client_ip(request)
    allowed, retry_after = limiter.check(f"ocr:{client_ip}", limit=15, window_seconds=60)
    if not allowed:
        return OCRResponse(
            extracted_text="",
            success=False,
            message="Too many screenshot uploads. Please wait a moment."
        )

    if not file.content_type.startswith("image/"):
        return OCRResponse(
            extracted_text="",
            success=False,
            message="Uploaded file is not a supported image. Please upload a PNG or JPEG screenshot."
        )

    try:
        contents = await file.read()
        if len(contents) == 0:
            return OCRResponse(
                extracted_text="",
                success=False,
                message="Uploaded image file is empty."
            )
        if len(contents) > 5 * 1024 * 1024:
            return OCRResponse(
                extracted_text="",
                success=False,
                message="Uploaded image exceeds 5MB limit. Please upload a smaller screenshot."
            )
        result = extract_text_from_image(contents)
        return result
    except Exception as e:
        return OCRResponse(
            extracted_text="",
            success=False,
            message=f"Error reading image: {str(e)}. Please paste your message text directly."
        )


@app.post("/share-target")
async def receive_share_target(
    title: Optional[str] = Form(None),
    text: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """
    PWA Web Share Target handler (Stage 7):
    Receives shared text or screenshot from mobile OS (WhatsApp/SMS).
    Stores ephemeral payload in memory for at most 5 minutes.
    Single-use: wiped immediately on first retrieval.
    Zero raw text or images persisted to disk or DB.
    """
    _clean_expired_shares()
    shared_text = ""
    if text:
        shared_text = text.strip()
    elif url:
        shared_text = url.strip()
    elif title:
        shared_text = title.strip()

    if file and file.filename:
        try:
            contents = await file.read()
            if 0 < len(contents) <= 5 * 1024 * 1024 and file.content_type.startswith("image/"):
                ocr_res = extract_text_from_image(contents)
                if ocr_res.success and ocr_res.extracted_text:
                    shared_text = (shared_text + "\n" + ocr_res.extracted_text).strip()
        except Exception:
            pass

    token = str(uuid.uuid4())
    _share_store[token] = (time.time() + 300, {"text": shared_text, "source": "share"})
    return RedirectResponse(url=f"/#scan?share_token={token}", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/api/share-target/{token}")
async def get_share_target(token: str):
    """Retrieves and immediately consumes single-use shared content (Stage 7)."""
    _clean_expired_shares()
    item = _share_store.pop(token, None)
    if not item or item[0] < time.time():
        raise HTTPException(status_code=404, detail="Shared content expired or not found")
    return item[1]



@app.post("/api/feedback")
async def submit_feedback(req: FeedbackRequest):
    """
    Saves anonymized user feedback to SQLite database.
    Raw messages are NEVER stored or logged.
    """
    try:
        row_id = save_feedback(
            helpful=req.helpful,
            category=req.category,
            risk_level=req.risk_level,
            comment=req.comment,
            analysis_id=req.analysis_id,
        )
        return {"status": "ok", "message": "Feedback submitted successfully.", "id": row_id}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Could not save feedback."}
        )


@app.get("/api/feedback/stats")
async def feedback_stats():
    """Returns aggregated feedback metrics."""
    return get_feedback_stats()


@app.get("/api/security-tips")
async def get_security_tips():
    """Returns verified fraud safety tips citing I4C/CERT-In/RBI advice only."""
    tips_file = BASE_DIR / "data" / "security_tips.json"
    if not tips_file.exists():
        return []
    import json
    with open(tips_file, "r", encoding="utf-8") as f:
        return json.load(f)


# Mount static assets
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
