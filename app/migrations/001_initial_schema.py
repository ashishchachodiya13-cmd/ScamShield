import sqlite3
import logging

logger = logging.getLogger(__name__)

VERSION = 1
DESCRIPTION = "Create users, sessions, analyses, preferences, password_resets, and link feedback"


def migrate(conn: sqlite3.Connection) -> None:
    """Applies migration step 1."""
    cursor = conn.cursor()

    # 1. users table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_login_at TEXT
        )
        """
    )
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)")

    # 2. sessions table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            jti TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            expires_at TEXT NOT NULL,
            revoked_at TEXT
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)")

    # 3. analyses table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            score INTEGER NOT NULL,
            category TEXT NOT NULL,
            flag_ids TEXT NOT NULL,
            language TEXT NOT NULL,
            source TEXT NOT NULL CHECK(source IN ('text', 'screenshot', 'share')),
            masked_text TEXT
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_analyses_user_created ON analyses(user_id, created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_analyses_user_risk ON analyses(user_id, risk_level)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_analyses_user_cat ON analyses(user_id, category)")

    # 4. preferences table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS preferences (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            language TEXT NOT NULL DEFAULT 'en',
            large_text INTEGER NOT NULL DEFAULT 0,
            retain_masked_text INTEGER NOT NULL DEFAULT 0,
            notify_settings TEXT DEFAULT '{}'
        )
        """
    )

    # 5. password_resets table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS password_resets (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            expires_at TEXT NOT NULL,
            used_at TEXT
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_password_resets_user_id ON password_resets(user_id)")

    # 6. feedback table (support existing and add analysis_id if missing)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            category TEXT,
            risk_level TEXT,
            helpful INTEGER NOT NULL,
            comment TEXT,
            analysis_id INTEGER REFERENCES analyses(id) ON DELETE SET NULL
        )
        """
    )

    # Check if analysis_id column exists in existing feedback table
    cursor.execute("PRAGMA table_info(feedback)")
    columns = [row[1] for row in cursor.fetchall()]
    if "analysis_id" not in columns:
        logger.info("Migrating legacy feedback table: adding analysis_id column")
        cursor.execute("ALTER TABLE feedback ADD COLUMN analysis_id INTEGER REFERENCES analyses(id) ON DELETE SET NULL")

    logger.info("Migration 001_initial_schema applied successfully.")
