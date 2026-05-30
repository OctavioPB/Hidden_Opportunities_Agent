from fastapi import APIRouter
from src.agents.analytics_engine import (
    get_analytics_summary, save_analytics_snapshot, get_snapshots,
)

router = APIRouter(tags=["analytics"])


@router.get("/analytics/summary")
def summary(period_days: int = 30) -> dict:
    return get_analytics_summary(period_days=period_days)


@router.post("/analytics/snapshot")
def take_snapshot() -> dict:
    return save_analytics_snapshot()


@router.get("/analytics/snapshots")
def snapshots(limit: int = 12) -> list[dict]:
    return get_snapshots(limit=limit)
