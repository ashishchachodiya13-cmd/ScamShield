import sqlite3
import pytest
from pathlib import Path

from app.migrations.runner import run_migrations, backup_database
from app.database import get_db_connection


def test_migration_on_fresh_database(tmp_path: Path):
    db_file = tmp_path / "fresh_test.db"
    backups_dir = tmp_path / "backups"

    # Run migration
    version = run_migrations(db_path=db_file, backups_dir=backups_dir)
    assert version == 1

    with get_db_connection(db_file) as conn:
        # Check user_version
        cursor = conn.cursor()
        cursor.execute("PRAGMA user_version")
        assert cursor.fetchone()[0] == 1

        # Check all tables created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        assert "users" in tables
        assert "sessions" in tables
        assert "analyses" in tables
        assert "preferences" in tables
        assert "password_resets" in tables
        assert "feedback" in tables


def test_migration_preserves_legacy_feedback_data(tmp_path: Path):
    db_file = tmp_path / "legacy_test.db"
    backups_dir = tmp_path / "backups"

    # Step 1: Create an old-schema DB simulating existing installation
    with sqlite3.connect(db_file) as conn:
        conn.execute(
            """
            CREATE TABLE feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                category TEXT,
                risk_level TEXT,
                helpful INTEGER NOT NULL,
                comment TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO feedback (timestamp, category, risk_level, helpful, comment)
            VALUES ('2026-01-01T10:00:00Z', 'digital_arrest', 'High', 1, 'Very helpful legacy feedback')
            """
        )
        conn.commit()

    # Step 2: Run safe migrations
    version = run_migrations(db_path=db_file, backups_dir=backups_dir)
    assert version == 1

    # Assert backup was created
    backup_files = list(backups_dir.glob("scamshield_backup_*.db"))
    assert len(backup_files) == 1

    # Step 3: Verify existing data was preserved intact
    with get_db_connection(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM feedback")
        row = cursor.fetchone()
        assert row is not None
        assert row["category"] == "digital_arrest"
        assert row["risk_level"] == "High"
        assert row["helpful"] == 1
        assert row["comment"] == "Very helpful legacy feedback"
        assert row["analysis_id"] is None

        # Verify new tables are also ready
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {r[0] for r in cursor.fetchall()}
        assert "users" in tables
        assert "sessions" in tables


def test_migration_idempotent(tmp_path: Path):
    db_file = tmp_path / "idempotent_test.db"
    backups_dir = tmp_path / "backups"

    v1 = run_migrations(db_path=db_file, backups_dir=backups_dir)
    assert v1 == 1

    # Run again: should return same version without errors or extra backups
    v2 = run_migrations(db_path=db_file, backups_dir=backups_dir)
    assert v2 == 1
