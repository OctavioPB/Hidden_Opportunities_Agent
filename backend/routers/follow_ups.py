from fastapi import APIRouter
from pydantic import BaseModel
from src.agents.follow_up_engine import (
    get_follow_up_queue, cancel_follow_ups,
    process_due_follow_ups, load_follow_up_log,
    schedule_follow_up,
)

router = APIRouter(tags=["follow_ups"])


class ScheduleRequest(BaseModel):
    proposal_id: str


@router.get("/follow-ups")
def list_queue(proposal_id: str | None = None) -> list[dict]:
    return get_follow_up_queue(proposal_id)


@router.post("/follow-ups/schedule")
def schedule(req: ScheduleRequest) -> dict:
    entries = schedule_follow_up(req.proposal_id)
    return {"scheduled": len(entries), "entries": entries}


@router.post("/follow-ups/process")
def process_due() -> dict:
    sent = process_due_follow_ups()
    return {"processed": len(sent)}


@router.delete("/follow-ups/{follow_up_id}/cancel")
def cancel(follow_up_id: str) -> dict:
    from src.db.schema import get_connection
    conn = get_connection()
    conn.execute(
        "UPDATE follow_up_queue SET status='cancelled' WHERE id=?", (follow_up_id,)
    )
    conn.commit()
    conn.close()
    return {"cancelled": True}


@router.get("/follow-ups/log")
def follow_up_log() -> list[dict]:
    return load_follow_up_log()
