import sqlite3
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from contextlib import contextmanager

from app.config import DB_PATH
from app.migrations.runner import run_migrations


def get_db_path(custom_path: Optional[Path] = None) -> Path:
    return custom_path or DB_PATH


@contextmanager
def get_db_connection(db_path: Optional[Path] = None):
    """
    Context manager for SQLite database connections.
    Enforces foreign keys, WAL mode, and sqlite3.Row row_factory.
    """
    path = get_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: Optional[Path] = None):
    """Initializes and runs all pending database migrations."""
    path = get_db_path(db_path)
    run_migrations(path)


# ==============================================================================
# Users & Preferences
# ==============================================================================

def get_user_by_email(email: str, db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
    """Retrieves a user by lower-cased email address."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
        return cursor.fetchone()


def get_user_by_id(user_id: int, db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
    """Retrieves a user by ID."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return cursor.fetchone()


def create_user(
    email: str,
    name: str,
    password_hash: str,
    language: str = "en",
    large_text: bool = False,
    retain_masked_text: bool = False,
    db_path: Optional[Path] = None,
) -> int:
    """
    Creates a new user and initializes their default preferences.
    Returns the new user ID.
    """
    now = datetime.now(timezone.utc).isoformat()
    clean_email = email.strip().lower()

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (email, name, password_hash, created_at, last_login_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (clean_email, name.strip(), password_hash, now, None)
        )
        user_id = cursor.lastrowid

        # Initialize default preferences
        cursor.execute(
            """
            INSERT INTO preferences (user_id, language, large_text, retain_masked_text, notify_settings)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, language, 1 if large_text else 0, 1 if retain_masked_text else 0, "{}")
        )
        conn.commit()
        return user_id


def update_user_last_login(user_id: int, db_path: Optional[Path] = None) -> None:
    """Updates user last_login_at timestamp."""
    now = datetime.now(timezone.utc).isoformat()
    with get_db_connection(db_path) as conn:
        conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now, user_id))
        conn.commit()


def update_user_profile(
    user_id: int,
    name: Optional[str] = None,
    password_hash: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> None:
    """Updates user profile information (name and/or password)."""
    with get_db_connection(db_path) as conn:
        if name is not None and password_hash is not None:
            conn.execute(
                "UPDATE users SET name = ?, password_hash = ? WHERE id = ?",
                (name.strip(), password_hash, user_id)
            )
        elif name is not None:
            conn.execute("UPDATE users SET name = ? WHERE id = ?", (name.strip(), user_id))
        elif password_hash is not None:
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
        conn.commit()


def delete_user_account(user_id: int, db_path: Optional[Path] = None) -> None:
    """
    Permanently deletes user account.
    Foreign key ON DELETE CASCADE automatically removes:
    sessions, analyses, preferences, password_resets.
    """
    with get_db_connection(db_path) as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()


def get_user_preferences(user_id: int, db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
    """Retrieves user preferences."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM preferences WHERE user_id = ?", (user_id,))
        return cursor.fetchone()


def update_user_preferences(
    user_id: int,
    language: Optional[str] = None,
    large_text: Optional[bool] = None,
    retain_masked_text: Optional[bool] = None,
    notify_settings: Optional[Dict[str, Any]] = None,
    db_path: Optional[Path] = None,
) -> None:
    """Updates user preferences."""
    current = get_user_preferences(user_id, db_path)
    new_lang = language if language is not None else (current["language"] if current else "en")
    new_large = (1 if large_text else 0) if large_text is not None else (current["large_text"] if current else 0)
    new_retain = (1 if retain_masked_text else 0) if retain_masked_text is not None else (current["retain_masked_text"] if current else 0)
    new_notify = json.dumps(notify_settings) if notify_settings is not None else (current["notify_settings"] if current else "{}")

    with get_db_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO preferences (user_id, language, large_text, retain_masked_text, notify_settings)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                language = excluded.language,
                large_text = excluded.large_text,
                retain_masked_text = excluded.retain_masked_text,
                notify_settings = excluded.notify_settings
            """,
            (user_id, new_lang, new_large, new_retain, new_notify)
        )
        conn.commit()


# ==============================================================================
# Sessions (JTI Revocation)
# ==============================================================================

def create_session(jti: str, user_id: int, expires_at: str, db_path: Optional[Path] = None) -> None:
    """Stores a new active session token JTI."""
    with get_db_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO sessions (jti, user_id, expires_at, revoked_at) VALUES (?, ?, ?, NULL)",
            (jti, user_id, expires_at)
        )
        conn.commit()


def get_session(jti: str, db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
    """Retrieves a session by JTI."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE jti = ?", (jti,))
        return cursor.fetchone()


def revoke_session(jti: str, db_path: Optional[Path] = None) -> None:
    """Marks a session JTI as revoked."""
    now = datetime.now(timezone.utc).isoformat()
    with get_db_connection(db_path) as conn:
        conn.execute("UPDATE sessions SET revoked_at = ? WHERE jti = ?", (now, jti))
        conn.commit()


def revoke_all_user_sessions(user_id: int, db_path: Optional[Path] = None) -> None:
    """Revokes all sessions for a specific user (e.g. on password reset)."""
    now = datetime.now(timezone.utc).isoformat()
    with get_db_connection(db_path) as conn:
        conn.execute("UPDATE sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL", (now, user_id))
        conn.commit()


# ==============================================================================
# Password Resets
# ==============================================================================

def create_password_reset(token_hash: str, user_id: int, expires_at: str, db_path: Optional[Path] = None) -> None:
    """Stores a hashed single-use password reset token."""
    with get_db_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO password_resets (token_hash, user_id, expires_at, used_at) VALUES (?, ?, ?, NULL)",
            (token_hash, user_id, expires_at)
        )
        conn.commit()


def get_password_reset(token_hash: str, db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
    """Retrieves a password reset entry by token hash."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM password_resets WHERE token_hash = ?", (token_hash,))
        return cursor.fetchone()


def mark_password_reset_used(token_hash: str, db_path: Optional[Path] = None) -> None:
    """Marks a password reset token as used."""
    now = datetime.now(timezone.utc).isoformat()
    with get_db_connection(db_path) as conn:
        conn.execute("UPDATE password_resets SET used_at = ? WHERE token_hash = ?", (now, token_hash))
        conn.commit()


# ==============================================================================
# Feedback (Preserving Legacy Compatibility)
# ==============================================================================

def save_feedback(
    helpful: bool,
    category: Optional[str] = None,
    risk_level: Optional[str] = None,
    comment: Optional[str] = None,
    analysis_id: Optional[int] = None,
    db_path: Optional[Path] = None,
) -> int:
    """
    Saves user feedback.
    STRICT PRIVACY POLICY:
    Raw messages, masked messages, phone numbers, and user identifiers
    are NEVER passed or saved to this table.
    """
    init_db(db_path)
    timestamp = datetime.now(timezone.utc).isoformat()
    helpful_val = 1 if helpful else 0

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO feedback (timestamp, category, risk_level, helpful, comment, analysis_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (timestamp, category, risk_level, helpful_val, comment, analysis_id)
        )
        conn.commit()
        return cursor.lastrowid or 0


def get_feedback_stats(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Returns aggregated feedback statistics."""
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), SUM(helpful) FROM feedback")
        row = cursor.fetchone()
        total = row[0] if row and row[0] is not None else 0
        helpful = row[1] if row and row[1] is not None else 0
        unhelpful = total - helpful
        return {
            "total_feedback": total,
            "helpful_count": helpful,
            "unhelpful_count": unhelpful,
            "satisfaction_rate": (helpful / total * 100) if total > 0 else 0.0
        }


# ==============================================================================
# Analyses, History & Stats (Stage 2)
# ==============================================================================

def create_analysis(
    user_id: int,
    risk_level: str,
    score: int,
    category: str,
    flag_ids: List[str],
    language: str = "en",
    source: str = "text",
    masked_text: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> int:
    """
    Saves anonymized analysis metadata for an authenticated user.
    Raw text, screenshots, and OCR images are NEVER stored.
    Only anonymized metadata is persisted.
    If preferences.retain_masked_text is enabled, masked_text (never raw) is stored.
    """
    init_db(db_path)
    now = datetime.now(timezone.utc).isoformat()
    flag_ids_json = json.dumps(flag_ids)

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO analyses (user_id, created_at, risk_level, score, category, flag_ids, language, source, masked_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, now, risk_level, score, category, flag_ids_json, language, source, masked_text)
        )
        conn.commit()
        return cursor.lastrowid or 0


def get_analysis(analysis_id: int, user_id: int, db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
    """Retrieves an analysis by ID scoped strictly to the authenticated user."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM analyses WHERE id = ? AND user_id = ?", (analysis_id, user_id))
        return cursor.fetchone()


def list_analyses(
    user_id: int,
    search: Optional[str] = None,
    risk: Optional[str] = None,
    category: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    sort_desc: bool = True,
    page: int = 1,
    page_size: int = 20,
    db_path: Optional[Path] = None,
) -> Tuple[List[sqlite3.Row], int]:
    """
    Lists paginated analyses for an authenticated user with optional filters.
    Search matches category names and flag IDs/names only (no raw text stored).
    Returns (items, total_count).
    """
    query_conditions = ["user_id = ?"]
    params: List[Any] = [user_id]

    if risk:
        query_conditions.append("risk_level = ?")
        params.append(risk.capitalize())

    if category:
        query_conditions.append("category = ?")
        params.append(category.lower())

    if from_date:
        query_conditions.append("created_at >= ?")
        params.append(from_date)

    if to_date:
        query_conditions.append("created_at <= ?")
        params.append(to_date)

    if search:
        search_pattern = f"%{search.strip().lower()}%"
        query_conditions.append("(LOWER(category) LIKE ? OR LOWER(flag_ids) LIKE ?)")
        params.extend([search_pattern, search_pattern])

    where_clause = " WHERE " + " AND ".join(query_conditions)
    sort_order = "DESC" if sort_desc else "ASC"

    # Count total
    count_sql = f"SELECT COUNT(*) FROM analyses{where_clause}"
    items_sql = f"SELECT * FROM analyses{where_clause} ORDER BY created_at {sort_order} LIMIT ? OFFSET ?"

    safe_page = max(1, page)
    safe_size = max(1, min(100, page_size))
    offset = (safe_page - 1) * safe_size

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(count_sql, tuple(params))
        total_count = cursor.fetchone()[0]

        params.extend([safe_size, offset])
        cursor.execute(items_sql, tuple(params))
        items = cursor.fetchall()
        return items, total_count


def delete_analysis(analysis_id: int, user_id: int, db_path: Optional[Path] = None) -> bool:
    """Deletes an analysis by ID scoped to the authenticated user."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM analyses WHERE id = ? AND user_id = ?", (analysis_id, user_id))
        conn.commit()
        return cursor.rowcount > 0


def clear_user_history(user_id: int, db_path: Optional[Path] = None) -> int:
    """Deletes all analyses for the authenticated user."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM analyses WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount


def get_user_stats_overview(user_id: int, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Computes dashboard overview statistics strictly with SQL aggregates.
    Zero hardcoded values. New users receive zeros and empty lists.
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        # Risk totals
        cursor.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high,
                SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium,
                SUM(CASE WHEN risk_level = 'Low' THEN 1 ELSE 0 END) as low
            FROM analyses
            WHERE user_id = ?
            """,
            (user_id,)
        )
        row = cursor.fetchone()
        total = row["total"] or 0
        high = row["high"] or 0
        medium = row["medium"] or 0
        low = row["low"] or 0

        # Recent scans
        cursor.execute(
            """
            SELECT id, created_at, risk_level, score, category, language, source
            FROM analyses
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 5
            """,
            (user_id,)
        )
        recent_scans = [dict(r) for r in cursor.fetchall()]

        # Recent high-risk
        cursor.execute(
            """
            SELECT id, created_at, risk_level, score, category, language, source
            FROM analyses
            WHERE user_id = ? AND risk_level = 'High'
            ORDER BY created_at DESC
            LIMIT 5
            """,
            (user_id,)
        )
        recent_high_risk = [dict(r) for r in cursor.fetchall()]

        # Category distribution
        cursor.execute(
            """
            SELECT category, COUNT(*) as count
            FROM analyses
            WHERE user_id = ?
            GROUP BY category
            ORDER BY count DESC
            """,
            (user_id,)
        )
        category_dist = [dict(r) for r in cursor.fetchall()]

        # Risk distribution
        cursor.execute(
            """
            SELECT risk_level, COUNT(*) as count
            FROM analyses
            WHERE user_id = ?
            GROUP BY risk_level
            ORDER BY count DESC
            """,
            (user_id,)
        )
        risk_dist = [dict(r) for r in cursor.fetchall()]

        return {
            "total_scans": total,
            "high_risk_count": high,
            "medium_risk_count": medium,
            "low_risk_count": low,
            "recent_scans": recent_scans,
            "recent_high_risk": recent_high_risk,
            "category_distribution": category_dist,
            "risk_distribution": risk_dist,
        }


def get_user_reports_stats(user_id: int, date_range: str = "week", db_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Computes report analytics for a specified range (week, month, all).
    """
    now = datetime.now(timezone.utc)
    params: List[Any] = [user_id]
    range_clean = date_range.lower().strip()

    date_filter = ""
    if range_clean == "week":
        cutoff = (now - timedelta(days=7)).isoformat()
        date_filter = " AND created_at >= ?"
        params.append(cutoff)
    elif range_clean == "month":
        cutoff = (now - timedelta(days=30)).isoformat()
        date_filter = " AND created_at >= ?"
        params.append(cutoff)
    else:
        range_clean = "all"

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        # Aggregates for range
        cursor.execute(
            f"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high,
                SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium,
                SUM(CASE WHEN risk_level = 'Low' THEN 1 ELSE 0 END) as low
            FROM analyses
            WHERE user_id = ?{date_filter}
            """,
            tuple(params)
        )
        summary = cursor.fetchone()
        total = summary["total"] or 0
        high = summary["high"] or 0
        medium = summary["medium"] or 0
        low = summary["low"] or 0
        high_risk_pct = round((high / total * 100), 2) if total > 0 else 0.0

        # Category breakdown
        cursor.execute(
            f"""
            SELECT category, COUNT(*) as count
            FROM analyses
            WHERE user_id = ?{date_filter}
            GROUP BY category
            ORDER BY count DESC
            """,
            tuple(params)
        )
        cat_rows = cursor.fetchall()
        category_breakdown = []
        for r in cat_rows:
            c_count = r["count"]
            c_pct = round((c_count / total * 100), 2) if total > 0 else 0.0
            category_breakdown.append({
                "category": r["category"],
                "count": c_count,
                "percentage": c_pct,
            })

        # Activity timeline (by day)
        cursor.execute(
            f"""
            SELECT
                substr(created_at, 1, 10) as date,
                COUNT(*) as total,
                SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high,
                SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium,
                SUM(CASE WHEN risk_level = 'Low' THEN 1 ELSE 0 END) as low
            FROM analyses
            WHERE user_id = ?{date_filter}
            GROUP BY date
            ORDER BY date ASC
            """,
            tuple(params)
        )
        timeline = [dict(r) for r in cursor.fetchall()]

        return {
            "range": range_clean,
            "total_scans": total,
            "high_risk_count": high,
            "medium_risk_count": medium,
            "low_risk_count": low,
            "high_risk_percentage": high_risk_pct,
            "category_breakdown": category_breakdown,
            "activity_timeline": timeline,
        }


def get_user_analyses_for_export(user_id: int, db_path: Optional[Path] = None) -> List[sqlite3.Row]:
    """Retrieves all user analyses for anonymized CSV/JSON export."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, created_at, risk_level, score, category, flag_ids, language, source
            FROM analyses
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,)
        )
        return cursor.fetchall()
