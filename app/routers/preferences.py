import json
import sqlite3
from fastapi import APIRouter, Depends, Request

from app.routers.auth import get_current_user
from app.security import verify_csrf
from app.database import get_user_preferences, update_user_preferences
from app.schemas import PreferencesResponse, PreferencesUpdateRequest

router = APIRouter(prefix="/api/preferences", tags=["preferences"])


def _format_preferences(prefs: sqlite3.Row) -> PreferencesResponse:
    if not prefs:
        return PreferencesResponse()
    try:
        notify_dict = json.loads(prefs["notify_settings"]) if prefs["notify_settings"] else {}
    except Exception:
        notify_dict = {}

    return PreferencesResponse(
        language=prefs["language"] or "en",
        large_text=bool(prefs["large_text"]),
        retain_masked_text=bool(prefs["retain_masked_text"]),
        notify_settings=notify_dict,
    )


@router.get("", response_model=PreferencesResponse)
async def get_preferences(user: sqlite3.Row = Depends(get_current_user)):
    """Retrieves preferences for the authenticated user."""
    prefs = get_user_preferences(user["id"])
    return _format_preferences(prefs)


@router.put("", response_model=PreferencesResponse)
async def set_preferences(
    req: PreferencesUpdateRequest,
    request: Request,
    user: sqlite3.Row = Depends(get_current_user),
):
    """
    Updates preferences for the authenticated user.
    - Requires CSRF verification for cookie-authenticated sessions
    """
    verify_csrf(request)
    update_user_preferences(
        user_id=user["id"],
        language=req.language,
        large_text=req.large_text,
        retain_masked_text=req.retain_masked_text,
        notify_settings=req.notify_settings,
    )
    updated = get_user_preferences(user["id"])
    return _format_preferences(updated)
