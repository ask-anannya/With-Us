import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
DEMO_MODE = os.getenv("DEMO_MODE", "0") == "1"
ON_VERCEL = bool(os.getenv("VERCEL"))


def _db_url() -> str:
    """WITH_US_DB wins (tests, local). On Vercel, Neon/Postgres sets DATABASE_URL or POSTGRES_URL."""
    url = os.getenv("WITH_US_DB") or os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or ""
    if not url:
        return f"sqlite:///{BACKEND_DIR / 'with_us.db'}"
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


DB_URL = _db_url()
SEED_DIR = BACKEND_DIR / "seed"
# Vercel's filesystem is read-only except /tmp
UPLOAD_DIR = Path("/tmp/with-us-uploads") if ON_VERCEL else BACKEND_DIR / "uploads"
