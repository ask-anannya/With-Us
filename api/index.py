"""Vercel entry point: serves the FastAPI backend at /api."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app import settings  # noqa: E402
from app.main import app  # noqa: E402,F401
from app.seed import ensure_demo  # noqa: E402

if settings.DEMO_MODE:
    ensure_demo()
else:
    from app.db import init_db  # noqa: E402

    init_db()
