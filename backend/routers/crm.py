from fastapi import APIRouter
from pydantic import BaseModel
from src.integrations.hubspot import get_sync_log, load_crm_log, create_deal, log_activity

router = APIRouter(tags=["crm"])


class SyncRequest(BaseModel):
    proposal_id: str
    client_id: str
    revenue: float
    opportunity_type: str


class ActivityRequest(BaseModel):
    client_id: str
    note: str


@router.get("/crm/sync-log")
def sync_log(limit: int = 50) -> list[dict]:
    return get_sync_log(limit=limit)


@router.get("/crm/log")
def crm_log() -> list[dict]:
    return load_crm_log()


@router.post("/crm/sync")
def manual_sync(req: SyncRequest) -> dict:
    deal = create_deal(req.client_id, req.proposal_id, req.revenue, req.opportunity_type)
    log_activity(req.client_id, f"Manual CRM sync for proposal {req.proposal_id[:8]}. Revenue: ${req.revenue:,.0f}")
    return {"ok": True, "deal": deal}
