from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.agents.negotiator import (
    start_negotiation, process_client_reply, kill_negotiation,
    get_thread, get_active_negotiations, get_negotiation_summary,
)
from src.agents.payment_link import create_payment_link, list_payment_links, get_payment_link
from src.agents.feedback_loop import record_client_reply, INTENT_TOO_EXPENSIVE
from src.db.schema import get_connection

router = APIRouter(tags=["negotiations"])


class ReplyRequest(BaseModel):
    message: str
    simulated: bool = False


class KillRequest(BaseModel):
    reason: str = "manual_kill_switch_ui"


class TooExpensiveRequest(BaseModel):
    proposal_id: str


class PaymentLinkRequest(BaseModel):
    proposal_id: str
    custom_amount: float | None = None


@router.get("/negotiations/summary")
def summary() -> dict:
    return get_negotiation_summary()


@router.get("/negotiations/active")
def active_negotiations() -> list[dict]:
    return get_active_negotiations()


@router.get("/negotiations/history")
def history() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT nl.proposal_id, nl.turn, nl.role, nl.message,
               nl.intent, nl.offer_price, nl.timestamp,
               c.name AS client_name, o.opportunity_type
        FROM negotiation_log nl
        JOIN proposals     p ON p.id  = nl.proposal_id
        JOIN clients       c ON c.id  = p.client_id
        JOIN opportunities o ON o.id  = p.opportunity_id
        ORDER BY nl.timestamp DESC
        LIMIT 200
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/negotiations/{proposal_id}/thread")
def thread(proposal_id: str) -> list[dict]:
    return get_thread(proposal_id)


@router.post("/negotiations/{proposal_id}/reply")
def reply(proposal_id: str, req: ReplyRequest) -> dict:
    result = process_client_reply(proposal_id, req.message, simulated=req.simulated)
    return result


@router.post("/negotiations/{proposal_id}/kill")
def kill(proposal_id: str, req: KillRequest) -> dict:
    kill_negotiation(proposal_id, reason=req.reason)
    return {"killed": True}


@router.post("/negotiations/{proposal_id}/start")
def start(proposal_id: str) -> dict:
    return start_negotiation(proposal_id)


@router.post("/negotiations/too-expensive")
def too_expensive(req: TooExpensiveRequest) -> dict:
    try:
        result = record_client_reply(
            req.proposal_id,
            intent=INTENT_TOO_EXPENSIVE,
            notes="[DEMO] Client indicated the price is too high.",
            simulated=True,
        )
        return {"method": "feedback", "result": result}
    except Exception:
        neg = start_negotiation(req.proposal_id)
        return {"method": "direct_start", "result": neg}


@router.get("/payment-links")
def payment_links() -> list[dict]:
    return list_payment_links()


@router.post("/payment-links")
def create_link(req: PaymentLinkRequest) -> dict:
    kwargs = {}
    if req.custom_amount is not None:
        kwargs["custom_amount"] = req.custom_amount
    return create_payment_link(req.proposal_id, **kwargs)
