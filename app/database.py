import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any


DB_PATH = Path(__file__).resolve().parent.parent / "data" / "scamshield.db"


def init_db(db_path: Optional[Path] = None):
    """Initializes the SQLite database schema for anonymized feedback."""
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with sqlite3.connect(path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                category TEXT,
                risk_level TEXT,
                helpful INTEGER NOT NULL,
                comment TEXT
            )
            """
        )
        conn.commit()


def save_feedback(
    helpful: bool,
    category: Optional[str] = None,
    risk_level: Optional[str] = None,
    comment: Optional[str] = None,
    db_path: Optional[Path] = None
) -> int:
    """
    Saves user feedback.
    STRICT PRIVACY POLICY:
    Raw messages, masked messages, phone numbers, and user identifiers
    are NEVER passed or saved to this database.
    """
    path = db_path or DB_PATH
    init_db(path)

    timestamp = datetime.now(timezone.utc).isoformat()
    helpful_val = 1 if helpful else 0

    with sqlite3.connect(path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO feedback (timestamp, category, risk_level, helpful, comment)
            VALUES (?, ?, ?, ?, ?)
            """,
            (timestamp, category, risk_level, helpful_val, comment)
        )
        conn.commit()
        return cursor.lastrowid or 0


def get_feedback_stats(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Returns aggregated feedback statistics."""
    path = db_path or DB_PATH
    init_db(path)

    with sqlite3.connect(path) as conn:
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
