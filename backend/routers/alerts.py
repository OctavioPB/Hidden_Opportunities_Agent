import config
from fastapi import APIRouter
from pydantic import BaseModel
from src.agents.alerts import load_alert_log, dispatch
from src.agents.scorer import score_all_clients
from src.data_sources.crm import get_demo_clients

router = APIRouter(tags=["alerts"])


class RunRequest(BaseModel):
    scope: str = "All clients"
    min_score: int = 60


@router.get("/alerts")
def get_alerts() -> list[dict]:
    return list(reversed(load_alert_log()))


@router.post("/alerts/run")
def run_alerts(req: RunRequest) -> dict:
    all_results = score_all_clients()
    if req.scope == "Demo clients only":
        demo_ids = {c["id"] for c in get_demo_clients()}
        results = [r for r in all_results if r["client_id"] in demo_ids]
    else:
        results = all_results
    alertable = [r for r in results if r["score"] >= req.min_score]
    if alertable:
        dispatch(alertable)
    return {"dispatched": len(alertable)}


@router.delete("/alerts")
def clear_alerts() -> dict:
    log_path = config.LOGS_DIR / "alerts.jsonl"
    if log_path.exists():
        log_path.write_text("")
    return {"cleared": True}
