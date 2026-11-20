import sqlite3
import shutil
import logging
from datetime import datetime, timezone
import importlib
from pathlib import Path
from typing import Optional

from app.config import DB_PATH, BACKUPS_DIR

logger = logging.getLogger(__name__)

# List of migration module names
MIGRATION_MODULES = [
    "app.migrations.001_initial_schema",
]


def backup_database(db_path: Path, backups_dir: Path) -> Optional[Path]:
    """
    Creates a backup of the existing database before running migrations.
    Returns the backup path if created, None if DB didn't exist yet.
    """
    if not db_path.exists():
        return None

    # Don't backup 0-byte files
    if db_path.stat().st_size == 0:
        return None

    backups_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    backup_path = backups_dir / f"scamshield_backup_{timestamp}.db"
    shutil.copy2(db_path, backup_path)
    logger.info(f"Database backed up to: {backup_path}")
    return backup_path


def run_migrations(db_path: Optional[Path] = None, backups_dir: Optional[Path] = None) -> int:
    """
    Runs pending database migrations in sequential order.
    Ensures WAL mode, enables foreign keys, tracks PRAGMA user_version.
    Returns the current schema version after migrations.
    """
    target_db = Path(db_path) if db_path else DB_PATH
    target_backups = Path(backups_dir) if backups_dir else BACKUPS_DIR

    target_db.parent.mkdir(parents=True, exist_ok=True)

    # Check current version first
    with sqlite3.connect(target_db) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA user_version")
        current_version = cursor.fetchone()[0]

    migrations = [importlib.import_module(mod) for mod in MIGRATION_MODULES]
    migrations.sort(key=lambda m: m.VERSION)

    max_target_version = max(m.VERSION for m in migrations)
    if current_version >= max_target_version:
        logger.debug(f"Database is already at current version ({current_version}). No migrations needed.")
        return current_version

    # Backup before running any new migrations
    backup_database(target_db, target_backups)

    # Apply pending migrations
    for migration in migrations:
        if migration.VERSION > current_version:
            logger.info(f"Applying migration v{migration.VERSION}: {migration.DESCRIPTION}")
            with sqlite3.connect(target_db) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("PRAGMA journal_mode = WAL")
                cursor = conn.cursor()

                # Execute migration within transaction
                migration.migrate(conn)
                cursor.execute(f"PRAGMA user_version = {migration.VERSION}")
                conn.commit()
                current_version = migration.VERSION

    logger.info(f"Database migrations complete. Current user_version is {current_version}.")
    return current_version
