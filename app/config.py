import os
from pathlib import Path
from dotenv import load_dotenv

# Ensure .env is loaded
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "scamshield.db"
BACKUPS_DIR = DATA_DIR / "backups"

APP_ENV = os.getenv("APP_ENV", "dev").lower().strip()
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production-min-32-chars-long").strip()

# Enforce JWT_SECRET requirement in non-dev environments
if APP_ENV != "dev":
    if not JWT_SECRET or JWT_SECRET == "dev-secret-change-in-production-min-32-chars-long" or len(JWT_SECRET) < 32:
        raise RuntimeError("JWT_SECRET must be explicitly set to a secure key (min 32 chars) in production.")

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 12
JWT_REMEMBER_DAYS = 30
PASSWORD_RESET_EXPIRY_MINUTES = 30

# Cookie settings
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() in ("true", "1") or (APP_ENV != "dev")
COOKIE_SAMESITE = "lax"
ACCESS_COOKIE_NAME = "access_token"
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"
