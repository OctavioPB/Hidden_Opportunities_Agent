"""
FastAPI backend for Hidden Opportunities Agent.
Run from project root: uvicorn backend.main:app --reload --port 8000
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.db.schema import init_db, migrate_db
from backend.routers import (
    opportunities, alerts, accuracy,
    proposals, pilot, ml_model,
    text_signals, negotiations, clients,
    follow_ups, analytics, churn, crm, seasonal,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    migrate_db()
    yield


app = FastAPI(title="Hidden Opportunities Agent API", version="0.7.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValueError)
async def value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
    """
    The agents signal bad input (unknown proposal, invalid intent, proposal in
    the wrong status) with ValueError. Report it as a client error with the
    message instead of an opaque 500.
    """
    if isinstance(exc, UnicodeError):   # an encoding bug, not bad input
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
    message = str(exc)
    status = 404 if "not found" in message.lower() else 400
    return JSONResponse(status_code=status, content={"detail": message})


app.include_router(opportunities.router, prefix="/api")
app.include_router(alerts.router,        prefix="/api")
app.include_router(accuracy.router,      prefix="/api")
app.include_router(proposals.router,     prefix="/api")
app.include_router(pilot.router,         prefix="/api")
app.include_router(ml_model.router,      prefix="/api")
app.include_router(text_signals.router,  prefix="/api")
app.include_router(negotiations.router,  prefix="/api")
app.include_router(clients.router,       prefix="/api")
app.include_router(follow_ups.router,    prefix="/api")
app.include_router(analytics.router,     prefix="/api")
app.include_router(churn.router,         prefix="/api")
app.include_router(crm.router,           prefix="/api")
app.include_router(seasonal.router,      prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
