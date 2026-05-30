from fastapi import APIRouter
from pydantic import BaseModel
from src.agents.seasonal_engine import get_upcoming_events, get_current_boosts, get_seasonal_multiplier
from src.agents.propensity_ranker import update_client_propensity_tiers, get_all_propensities
from src.integrations.whatsapp import (
    set_channel_preference, get_opted_in_clients, load_whatsapp_log,
)

router = APIRouter(tags=["seasonal", "propensity", "whatsapp"])


# ── Seasonal calendar ──────────────────────────────────────────────────────────

@router.get("/seasonal/upcoming")
def upcoming_events(weeks: int = 8) -> list[dict]:
    return get_upcoming_events(n_weeks=weeks)


@router.get("/seasonal/boosts")
def current_boosts() -> list[dict]:
    return get_current_boosts()


# ── Propensity ─────────────────────────────────────────────────────────────────

@router.post("/propensity/update")
def update_propensity() -> dict:
    counts = update_client_propensity_tiers()
    return {"updated": True, "counts": counts}


@router.get("/propensity/clients")
def propensity_clients() -> list[dict]:
    return get_all_propensities()


# ── WhatsApp ───────────────────────────────────────────────────────────────────

class ChannelRequest(BaseModel):
    client_id: str
    channel: str
    whatsapp_number: str | None = None


@router.patch("/clients/channel")
def update_channel(req: ChannelRequest) -> dict:
    set_channel_preference(req.client_id, req.channel, req.whatsapp_number)
    return {"updated": True}


@router.get("/whatsapp/opted-in")
def opted_in() -> list[dict]:
    return get_opted_in_clients()


@router.get("/whatsapp/log")
def whatsapp_log() -> list[dict]:
    return load_whatsapp_log()
