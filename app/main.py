import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
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
from app.database import init_db, save_feedback, get_feedback_stats

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="ScamShield",
    description="AI-Assisted Decision-Support System for Scam Communication Identification",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize pipeline singletons
rule_engine = RuleEngine()
actions_manager = ActionsManager()
explanation_manager = ExplanationManager()
init_db()


@app.get("/")
async def serve_index():
    """Serves the main senior-citizen friendly web interface."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Index file not found")
    return FileResponse(index_file)


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_message(req: AnalysisRequest):
    """
    Main analysis pipeline:
    1. Validates input text.
    2. Preprocesses Hinglish and masks sensitive data (PII).
    3. Evaluates red flags and calculates weighted risk score & category.
    4. Retrieves predefined category safety actions.
    5. Generates plain-language explanation (LLM or template fallback).
    """
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

    return AnalysisResponse(
        risk_level=risk_level,
        score=score,
        category=category_id,
        category_name=category_name,
        matched_flags=matched_flags,
        explanation=explanation,
        explanation_source=explanation_source,
        actions=actions,
        language=req.language,
        masked_text=masked_text,
    )


@app.post("/api/ocr", response_model=OCRResponse)
async def ocr_screenshot(file: UploadFile = File(...)):
    """
    Extracts text from an uploaded screenshot using Tesseract OCR.
    Enables user to review and correct the extracted text before running analysis (UC3, UC4, UC5).
    """
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
        result = extract_text_from_image(contents)
        return result
    except Exception as e:
        return OCRResponse(
            extracted_text="",
            success=False,
            message=f"Error reading image: {str(e)}. Please paste your message text directly."
        )


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


# Mount static assets
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
