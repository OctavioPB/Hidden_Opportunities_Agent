from fastapi import APIRouter
from src.agents.churn_escalation import (
    run_churn_scan, get_escalation_log, load_churn_log,
)

router = APIRouter(tags=["churn"])


@router.post("/churn/scan")
def scan() -> dict:
    escalated = run_churn_scan()
    return {"escalated": len(escalated), "records": escalated}


@router.get("/churn/escalations")
def escalations(limit: int = 50) -> list[dict]:
    return get_escalation_log(limit=limit)


@router.get("/churn/log")
def churn_log() -> list[dict]:
    return load_churn_log()
