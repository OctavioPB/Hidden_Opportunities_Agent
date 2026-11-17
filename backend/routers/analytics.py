from fastapi import APIRouter, Query
from src.agents.analytics_engine import (
    get_analytics_summary, save_analytics_snapshot, get_snapshots,
)

router = APIRouter(tags=["analytics"])


@router.get("/analytics/summary")
def summary(period_days: int = Query(30, ge=0, le=3650)) -> dict:
    return get_analytics_summary(period_days=period_days)


@router.post("/analytics/snapshot")
def take_snapshot() -> dict:
    return save_analytics_snapshot()


@router.get("/analytics/snapshots")
def snapshots(limit: int = Query(12, ge=1, le=500)) -> list[dict]:
    return get_snapshots(limit=limit)
