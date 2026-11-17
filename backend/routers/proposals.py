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
    # Only an approval can be revoked — never pull a sent or answered proposal back to draft
    cur = conn.execute(
        "UPDATE proposals SET status='draft', approved_by=NULL, updated_at=? "
        "WHERE id=? AND status='approved'",
        (datetime.now().isoformat(), proposal_id),
    )
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(409, "Only an approved proposal can be revoked.")
    return {"revoked": True}


_METRIC_FIELDS = (
    "ctr", "bounce_rate", "pages_per_session", "conversion_rate", "organic_traffic",
    "ad_spend", "roas", "email_open_rate", "days_inactive", "keyword_rankings",
)


def _shape_metrics(m: dict) -> dict:
    out = {f: m.get(f) or 0 for f in _METRIC_FIELDS}
    out["ad_spend"] *= 30   # stored per day, shown per month
    return out


@router.get("/proposals/metrics")
def get_all_proposal_metrics() -> dict[str, dict]:
    """
    Latest client metrics for every proposal, keyed by proposal id.
    One request for the whole proposals page instead of one per card.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT p.id AS proposal_id, cm.*
        FROM proposals p
        JOIN (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY client_id ORDER BY date DESC, id DESC) AS rn
            FROM client_metrics
        ) cm ON cm.client_id = p.client_id AND cm.rn = 1
        """
    ).fetchall()
    conn.close()
    return {r["proposal_id"]: _shape_metrics(dict(r)) for r in rows}


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
    return _shape_metrics(dict(row))
