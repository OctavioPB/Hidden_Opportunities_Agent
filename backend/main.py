"""
FastAPI backend for Hidden Opportunities Agent.
Run from project root: uvicorn backend.main:app --reload --port 8000
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.db.schema import init_db, migrate_db
from backend.routers import (
    opportunities, alerts, accuracy,
    proposals, pilot, ml_model,
    text_signals, negotiations, clients,
)

app = FastAPI(title="Hidden Opportunities Agent API", version="0.7.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()
    migrate_db()


app.include_router(opportunities.router, prefix="/api")
app.include_router(alerts.router,        prefix="/api")
app.include_router(accuracy.router,      prefix="/api")
app.include_router(proposals.router,     prefix="/api")
app.include_router(pilot.router,         prefix="/api")
app.include_router(ml_model.router,      prefix="/api")
app.include_router(text_signals.router,  prefix="/api")
app.include_router(negotiations.router,  prefix="/api")
app.include_router(clients.router,       prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
