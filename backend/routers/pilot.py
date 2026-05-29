from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.agents.scorer import score_client, persist_opportunities, score_all_clients
from src.agents.proposal_generator import generate_proposal, get_all_proposals, approve_proposal
from src.agents.email_sender import send_proposal_email, load_sent_log
from src.agents.feedback_loop import (
    record_client_reply, get_pilot_metrics,
    load_feedback_log, load_calendar_log, load_escalation_log,
    INTENT_LABELS, ALL_INTENTS,
)
from src.agents.auto_sender import get_send_queue_summary, process_auto_send_queue, get_autonomy_tier
from src.db.schema import get_connection

router = APIRouter(tags=["pilot"])


class DetectRequest(BaseModel):
    client_id: str


class GenerateRequest(BaseModel):
    client_id: str


class SendRequest(BaseModel):
    proposal_id: str
    opp_score: float
    opp_price: float
    opp_type: str


class ReplyRequest(BaseModel):
    proposal_id: str
    intent: str
    notes: str = ""
    simulated: bool = True


class FeedbackRequest(BaseModel):
    proposal_id: str
    intent: str


@router.post("/pilot/detect")
def detect(req: DetectRequest) -> dict:
    opps = score_client(req.client_id)
    all_scored = score_all_clients()
    persist_opportunities(all_scored)

    conn = get_connection()
    tier_map = {}
    for opp in opps:
        tier = get_autonomy_tier(opp.score, opp.suggested_price, opp.opportunity_type)
        tier_map[opp.opportunity_type] = tier

    conn.close()
    return {
        "opportunities": [
            {
                "label":            opp.label,
                "opportunity_type": opp.opportunity_type,
                "score":            opp.score,
                "suggested_price":  opp.suggested_price,
                "rationale":        opp.rationale,
                "tier":             tier_map.get(opp.opportunity_type, "B"),
            }
            for opp in opps
        ]
    }


@router.post("/pilot/generate")
def generate(req: GenerateRequest) -> dict:
    conn = get_connection()
    opp_row = conn.execute(
        """
        SELECT id, opportunity_type, score, status
        FROM opportunities
        WHERE client_id = ?
          AND status IN ('detected', 'proposal_generated')
        ORDER BY score DESC LIMIT 1
        """,
        (req.client_id,),
    ).fetchone()

    if opp_row is None:
        conn.close()
        raise HTTPException(400, "No qualifying opportunity found. Run detect first.")

    opp = dict(opp_row)
    existing = conn.execute(
        "SELECT id, subject, body, status FROM proposals "
        "WHERE opportunity_id=? AND status NOT IN ('rejected') "
        "ORDER BY created_at DESC LIMIT 1",
        (opp["id"],),
    ).fetchone()
    conn.close()

    if existing:
        p = dict(existing)
        return {"proposal_id": p["id"], "subject": p["subject"], "status": p["status"], "already_existed": True}

    result = generate_proposal(opp["id"], rationale="Demo simulation.")
    return {
        "proposal_id": result["proposal_id"],
        "subject":     result["subject"],
        "status":      result["status"],
        "already_existed": False,
    }


@router.post("/pilot/send")
def send(req: SendRequest) -> dict:
    tier = get_autonomy_tier(req.opp_score, req.opp_price, req.opp_type)
    approve_proposal(req.proposal_id, approved_by="autonomous" if tier == "C" else "demo_user")
    try:
        send_proposal_email(
            req.proposal_id,
            send_mode="autonomous" if tier == "C" else "approved",
            bcc_manager=True,
        )
    except Exception as e:
        raise HTTPException(500, str(e))
    return {"sent": True, "tier": tier}


@router.post("/pilot/reply")
def reply(req: ReplyRequest) -> dict:
    result = record_client_reply(
        req.proposal_id, req.intent,
        notes=req.notes, simulated=req.simulated,
    )
    return result


@router.get("/pilot/metrics")
def pilot_metrics() -> dict:
    return get_pilot_metrics()


@router.get("/pilot/sent-log")
def sent_log() -> list[dict]:
    return list(reversed(load_sent_log()[-20:]))


@router.get("/pilot/feedback-log")
def feedback_log() -> dict:
    return {
        "feedback":    list(reversed(load_feedback_log()[-20:])),
        "calendars":   load_calendar_log(),
        "escalations": load_escalation_log(),
        "intent_labels": INTENT_LABELS,
        "all_intents":   ALL_INTENTS,
    }


@router.get("/pilot/auto-queue")
def auto_queue() -> dict:
    return get_send_queue_summary()


@router.post("/pilot/process-auto-queue")
def process_auto_queue() -> dict:
    results = process_auto_send_queue(dry_run=False)
    sent_count = len([r for r in results if not r.get("dry_run")])
    return {"sent": sent_count}
