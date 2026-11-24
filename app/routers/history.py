import json
import math
import sqlite3
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.routers.auth import get_current_user
from app.security import verify_csrf
from app.database import (
    get_analysis,
    list_analyses,
    delete_analysis,
    clear_user_history,
)
from app.pipeline.rules import RuleEngine
from app.pipeline.actions import ActionsManager
from app.pipeline.explain import ExplanationManager
from app.schemas import (
    HistoryItemResponse,
    HistoryListResponse,
    HistoryDetailResponse,
    MatchedFlag,
    AuthMessageResponse,
)

router = APIRouter(prefix="/api/history", tags=["history"])

# Singletons for rebuilding details
rule_engine = RuleEngine()
actions_manager = ActionsManager()
explanation_manager = ExplanationManager()

categories_by_id = {c.id: c for c in rule_engine.config.categories}
flags_by_id = {f.id: f for f in rule_engine.config.flags}


def _get_category_name(category_id: str, language: str = "en") -> str:
    cat = categories_by_id.get(category_id)
    if cat:
        return cat.name_hi if language == "hi" else cat.name_en
    return "General Suspicious Communication" if language == "en" else "सामान्य संदिग्ध संदेश"


@router.get("", response_model=HistoryListResponse)
async def get_history(
    search: Optional[str] = Query(None, description="Search category or red flag names"),
    risk: Optional[str] = Query(None, description="Filter by risk level (Low, Medium, High)"),
    category: Optional[str] = Query(None, description="Filter by category ID"),
    from_date: Optional[str] = Query(None, alias="from", description="ISO start date"),
    to_date: Optional[str] = Query(None, alias="to", description="ISO end date"),
    sort: str = Query("desc", pattern="^(asc|desc)$", description="Sort order by date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    user: sqlite3.Row = Depends(get_current_user),
):
    """
    Lists paginated analysis history for the authenticated user with optional filters.
    User isolation: users can only ever access their own history records.
    Search matches category names and flag labels only (no raw text stored).
    """
    sort_desc = (sort.lower() == "desc")
    rows, total_count = list_analyses(
        user_id=user["id"],
        search=search,
        risk=risk,
        category=category,
        from_date=from_date,
        to_date=to_date,
        sort_desc=sort_desc,
        page=page,
        page_size=page_size,
    )

    items: List[HistoryItemResponse] = []
    for r in rows:
        flag_ids = json.loads(r["flag_ids"]) if r["flag_ids"] else []
        items.append(
            HistoryItemResponse(
                id=r["id"],
                created_at=r["created_at"],
                risk_level=r["risk_level"],
                score=r["score"],
                category=r["category"],
                category_name=_get_category_name(r["category"], r["language"]),
                flag_ids=flag_ids,
                flag_count=len(flag_ids),
                language=r["language"],
                source=r["source"],
                has_masked_text=bool(r["masked_text"]),
            )
        )

    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 0

    return HistoryListResponse(
        items=items,
        total=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{analysis_id}", response_model=HistoryDetailResponse)
async def get_history_detail(
    analysis_id: int,
    user: sqlite3.Row = Depends(get_current_user),
):
    """
    Retrieves full details for a specific analysis record.
    Rebuilds matched red flags, certified safety actions, and verified template explanations.
    Returns 404 if the record does not exist or belongs to another user.
    """
    row = get_analysis(analysis_id, user_id=user["id"])
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis record not found.",
        )

    flag_ids = json.loads(row["flag_ids"]) if row["flag_ids"] else []
    matched_flags: List[MatchedFlag] = []
    for fid in flag_ids:
        flag_def = flags_by_id.get(fid)
        if flag_def:
            matched_flags.append(
                MatchedFlag(
                    id=flag_def.id,
                    name_en=flag_def.name_en,
                    name_hi=flag_def.name_hi,
                    weight=flag_def.weight,
                    snippets=[],  # snippets are not stored
                )
            )

    lang = row["language"] or "en"
    category_id = row["category"]
    actions = actions_manager.get_actions(category_id, language=lang)

    is_zero_flags = (len(flag_ids) == 0)
    explanation = explanation_manager.get_template_explanation(
        category_id=category_id,
        language=lang,
        is_zero_flags=is_zero_flags,
    )

    masked_text = row["masked_text"]
    retained_label = (
        "Masked text saved by user preference"
        if masked_text
        else "No message text stored for privacy"
    )

    return HistoryDetailResponse(
        id=row["id"],
        created_at=row["created_at"],
        risk_level=row["risk_level"],
        score=row["score"],
        category=category_id,
        category_name=_get_category_name(category_id, lang),
        matched_flags=matched_flags,
        explanation=explanation,
        actions=actions,
        avoid=actions.donts,
        reporting_channels=actions.official_channels,
        language=lang,
        source=row["source"],
        masked_text=masked_text,
        retained_label=retained_label,
    )


@router.delete("/{analysis_id}", response_model=AuthMessageResponse)
async def delete_history_item(
    analysis_id: int,
    request: Request,
    user: sqlite3.Row = Depends(get_current_user),
):
    """
    Deletes an individual history item.
    Returns 404 if the item does not exist or belongs to another user.
    """
    verify_csrf(request)
    deleted = delete_analysis(analysis_id, user_id=user["id"])
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis record not found.",
        )
    return AuthMessageResponse(status="ok", message="History record deleted successfully.")


@router.delete("", response_model=AuthMessageResponse)
async def clear_history(
    request: Request,
    confirm: bool = Query(False, description="Must be true to confirm bulk deletion"),
    user: sqlite3.Row = Depends(get_current_user),
):
    """
    Clears all history records for the current user.
    Requires explicit confirm=true query parameter.
    """
    verify_csrf(request)
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation required (confirm=true) to clear all history records.",
        )
    deleted_count = clear_user_history(user["id"])
    return AuthMessageResponse(
        status="ok",
        message=f"Cleared {deleted_count} history records successfully.",
    )
