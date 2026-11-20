import csv
import io
import json
import sqlite3
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.routers.auth import get_current_user
from app.database import (
    get_user_stats_overview,
    get_user_reports_stats,
    get_user_analyses_for_export,
)
from app.pipeline.rules import RuleEngine
from app.schemas import (
    StatsOverviewResponse,
    ReportsResponse,
    CategoryBreakdownItem,
    TimelineItem,
)

router = APIRouter(prefix="/api", tags=["stats-and-reports"])

rule_engine = RuleEngine()
categories_by_id = {c.id: c for c in rule_engine.config.categories}


def _get_category_name(category_id: str, language: str = "en") -> str:
    cat = categories_by_id.get(category_id)
    if cat:
        return cat.name_hi if language == "hi" else cat.name_en
    return "General Suspicious Communication" if language == "en" else "सामान्य संदिग्ध संदेश"


@router.get("/stats/overview", response_model=StatsOverviewResponse)
async def get_stats_overview(user: sqlite3.Row = Depends(get_current_user)):
    """
    Returns user dashboard overview computed strictly via SQL aggregates.
    Zero hardcoded numbers. New users receive zeros and empty arrays.
    """
    raw_stats = get_user_stats_overview(user["id"])

    # Enrich recent scans with human-readable category names
    for scan in raw_stats["recent_scans"]:
        scan["category_name"] = _get_category_name(scan["category"], scan.get("language", "en"))

    for scan in raw_stats["recent_high_risk"]:
        scan["category_name"] = _get_category_name(scan["category"], scan.get("language", "en"))

    for cat_item in raw_stats["category_distribution"]:
        cat_item["category_name"] = _get_category_name(cat_item["category"])

    return StatsOverviewResponse(
        total_scans=raw_stats["total_scans"],
        high_risk_count=raw_stats["high_risk_count"],
        medium_risk_count=raw_stats["medium_risk_count"],
        low_risk_count=raw_stats["low_risk_count"],
        recent_scans=raw_stats["recent_scans"],
        recent_high_risk=raw_stats["recent_high_risk"],
        category_distribution=raw_stats["category_distribution"],
        risk_distribution=raw_stats["risk_distribution"],
    )


@router.get("/stats/reports", response_model=ReportsResponse)
async def get_stats_reports(
    range: str = Query("week", pattern="^(week|month|all)$", description="Date range: week, month, or all"),
    user: sqlite3.Row = Depends(get_current_user),
):
    """
    Returns detailed report statistics (risk percentages, category breakdown, timeline activity).
    """
    raw_reports = get_user_reports_stats(user["id"], date_range=range)

    cat_breakdown: List[CategoryBreakdownItem] = []
    for item in raw_reports["category_breakdown"]:
        cat_breakdown.append(
            CategoryBreakdownItem(
                category=_get_category_name(item["category"]),
                count=item["count"],
                percentage=item["percentage"],
            )
        )

    timeline: List[TimelineItem] = [
        TimelineItem(
            date=t["date"],
            total=t["total"],
            high=t["high"],
            medium=t["medium"],
            low=t["low"],
        )
        for t in raw_reports["activity_timeline"]
    ]

    return ReportsResponse(
        range=raw_reports["range"],
        total_scans=raw_reports["total_scans"],
        high_risk_count=raw_reports["high_risk_count"],
        medium_risk_count=raw_reports["medium_risk_count"],
        low_risk_count=raw_reports["low_risk_count"],
        high_risk_percentage=raw_reports["high_risk_percentage"],
        category_breakdown=cat_breakdown,
        activity_timeline=timeline,
    )


@router.get("/reports/export")
async def export_reports(
    format: str = Query("csv", pattern="^(csv|json)$", description="Export format: csv or json"),
    user: sqlite3.Row = Depends(get_current_user),
):
    """
    Exports the user's historical analyses in anonymized CSV or JSON format.
    STRICT PRIVACY: Never exports raw text, phone numbers, or passwords.
    User isolation: only exports the authenticated user's own data.
    """
    rows = get_user_analyses_for_export(user["id"])

    export_records = []
    for r in rows:
        flag_ids_list = json.loads(r["flag_ids"]) if r["flag_ids"] else []
        export_records.append({
            "id": r["id"],
            "created_at": r["created_at"],
            "risk_level": r["risk_level"],
            "score": r["score"],
            "category": r["category"],
            "category_name": _get_category_name(r["category"], r["language"]),
            "flag_ids": "; ".join(flag_ids_list),
            "language": r["language"],
            "source": r["source"],
        })

    if format.lower() == "json":
        json_content = json.dumps(export_records, indent=2)
        return Response(
            content=json_content,
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="scamshield_report.json"'},
        )
    else:
        # Default CSV export
        output = io.StringIO()
        fieldnames = ["id", "created_at", "risk_level", "score", "category", "category_name", "flag_ids", "language", "source"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for record in export_records:
            writer.writerow(record)

        csv_content = output.getvalue()
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="scamshield_report.csv"'},
        )
