from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.agents.proposal_generator import (
    get_all_proposals, approve_proposal, reject_proposal,
    update_proposal_body, generate_proposals_for_all,
)
from src.db.schema import get_connection

router = APIRouter(tags=["proposals"])


class GenerateRequest(BaseModel):
    min_score: int = 70


class BodyUpdate(BaseModel):
    body: str


class RejectRequest(BaseModel):
    reason: str = "Rejected via UI"


@router.get("/proposals")
def get_proposals(
    status: str = "All",
    opp_type: str = "All",
    demo_only: bool = False,
) -> list[dict]:
    proposals = get_all_proposals()
    if status != "All":
        proposals = [p for p in proposals if p["status"] == status]
    if opp_type != "All":
        proposals = [p for p in proposals if p["opportunity_type"] == opp_type]
    if demo_only:
        proposals = [p for p in proposals if p.get("is_demo_scenario")]
    return proposals


@router.post("/proposals/generate-all")
def generate_all(req: GenerateRequest) -> dict:
    results = generate_proposals_for_all(min_score=req.min_score)
    new_ones = [r for r in results if not r.get("already_existed")]
    return {"generated": len(new_ones), "total": len(results)}


@router.post("/proposals/{proposal_id}/approve")
def approve(proposal_id: str) -> dict:
    approve_proposal(proposal_id)
    return {"approved": True}


@router.post("/proposals/{proposal_id}/reject")
def reject(proposal_id: str, req: RejectRequest) -> dict:
    reject_proposal(proposal_id, reason=req.reason)
    return {"rejected": True}


@router.patch("/proposals/{proposal_id}/body")
def update_body(proposal_id: str, req: BodyUpdate) -> dict:
    update_proposal_body(proposal_id, req.body)
    return {"updated": True}


@router.post("/proposals/{proposal_id}/revoke")
def revoke_approval(proposal_id: str) -> dict:
    conn = get_connection()
    conn.execute(
        "UPDATE proposals SET status='draft', updated_at=? WHERE id=?",
        (datetime.now().isoformat(), proposal_id),
    )
    conn.commit()
    conn.close()
    return {"revoked": True}


@router.get("/proposals/{proposal_id}/metrics")
def get_proposal_metrics(proposal_id: str) -> dict:
    conn = get_connection()
    row = conn.execute(
        """
        SELECT cm.*
        FROM proposals p
        JOIN client_metrics cm ON cm.client_id = p.client_id
        WHERE p.id = ?
        ORDER BY cm.date DESC
        LIMIT 1
        """,
        (proposal_id,),
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "No metrics found")
    m = dict(row)
    return {
        "ctr":              m.get("ctr", 0),
        "bounce_rate":      m.get("bounce_rate", 0),
        "pages_per_session":m.get("pages_per_session", 0),
        "conversion_rate":  m.get("conversion_rate", 0),
        "organic_traffic":  m.get("organic_traffic", 0),
        "ad_spend":         (m.get("ad_spend", 0) or 0) * 30,
        "roas":             m.get("roas", 0),
        "email_open_rate":  m.get("email_open_rate", 0),
        "days_inactive":    m.get("days_inactive", 0),
        "keyword_rankings": m.get("keyword_rankings", 0),
    }
