import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import settings
from .ai import client as ai_client
from .db import init_db
from .routes import assistant, household, me, plan, prescription, quests

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="With Us", lifespan=lifespan)
for r in (household.router, me.router, plan.router, prescription.router, quests.router, assistant.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    return {"ok": True, "ai": ai_client.available(), "model": settings.GEMINI_MODEL,
            "demo": settings.DEMO_MODE, "tokens": ai_client.TOKENS}
