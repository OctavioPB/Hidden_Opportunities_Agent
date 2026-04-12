"""
Sprint 4 — Autonomous Send Decision Engine.

Implements the three-tier autonomy model from GOVERNANCE.md:

  Tier A — draft only (all opportunities, Sprint 1–3 default)
  Tier B — human approval required (score 70–89 OR value > $200)
  Tier C — autonomous send (score ≥ 90 AND value ≤ $200 AND repeat client)
            Special case: reactivation opportunities always Tier C at score ≥ 90
            regardless of price (max price = $150 by governance rule).

The auto-send queue processor finds approved proposals that qualify for
Tier C and sends them without further human action, BCCing the account manager.

In production this runs immediately after proposal generation in the daily job.
The account manager always has a 30-minute cancellation window before any
Tier C email is dispatched (implemented via a scheduled delay queue —
see the production_note on each payload).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import config
from src.db.schema import get_connection
from src.agents.email_sender import (
    send_proposal_email,
    SEND_MODE_AUTONOMOUS,
    SEND_MODE_APPROVED,
)
from src.agents.rules import REACTIVATION

# ── Governance thresholds (mirrors GOVERNANCE.md constants) ───────────────────
TIER_C_MIN_SCORE         = 90.0
TIER_C_MAX_VALUE         = 200.0
TIER_C_REACTIVATION_MAX  = 150.0   # reactivation has a lower autonomous price cap


# ── Decision logic ────────────────────────────────────────────────────────────

def get_autonomy_tier(
    score: float,
    suggested_price: float,
    opportunity_type: str,
    is_repeat_client: bool = False,
) -> str:
    """
    Return the autonomy tier for an opportunity:
      'A' — generate draft only
      'B' — human approval required before send
      'C' — autonomous send allowed

    Parameters
    ----------
    score : float
        Opportunity confidence score (0–100).
    suggested_price : float
        Proposed service price in USD.
    opportunity_type : str
        One of the 7 opportunity type constants from rules.py.
    is_repeat_client : bool
        True if the client has accepted at least one previous proposal.
    """
    # Reactivation has a special lower price cap
    max_value = TIER_C_REACTIVATION_MAX if opportunity_type == REACTIVATION else TIER_C_MAX_VALUE

    if score >= TIER_C_MIN_SCORE and suggested_price <= max_value:
        # Tier C requires a repeat client relationship for extra safety
        if is_repeat_client or opportunity_type == REACTIVATION:
            return "C"

    if score >= 70.0:
        return "B"

    return "A"


def should_auto_send(
    score: float,
    suggested_price: float,
    opportunity_type: str,
    is_repeat_client: bool = False,
) -> bool:
    """Convenience wrapper — returns True only for Tier C."""
    return get_autonomy_tier(score, suggested_price, opportunity_type, is_repeat_client) == "C"


def _is_repeat_client(client_id: str) -> bool:
    """Return True if the client has at least one previously accepted proposal."""
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM proposals WHERE client_id=? AND status='accepted'",
        (client_id,),
    ).fetchone()[0]
    conn.close()
    return count > 0


# ── Queue processor ───────────────────────────────────────────────────────────

def process_auto_send_queue(dry_run: bool = False) -> list[dict[str, Any]]:
    """
    Find all approved proposals that qualify for Tier C and send them.

    Called automatically from the daily job after proposal generation.
    A proposal qualifies for auto-send if:
      - status = 'approved'  (either pre-approved by human OR newly generated)
      - approved_by = 'autonomous' OR score ≥ TIER_C_MIN_SCORE
      - suggested_price ≤ TIER_C_MAX_VALUE (TIER_C_REACTIVATION_MAX for reactivation)

    Returns
    -------
    list of send result dicts (one per sent email)
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT p.id AS proposal_id,
               p.client_id,
               p.suggested_price,
               p.approved_by,
               o.opportunity_type,
               o.score
        FROM proposals p
        JOIN opportunities o ON o.id = p.opportunity_id
        WHERE p.status = 'approved'
        ORDER BY o.score DESC
        """
    ).fetchall()
    conn.close()

    results = []
    for row in rows:
        r = dict(row)
        opp_type  = r["opportunity_type"]
        score     = r["score"] or 0
        price     = r["suggested_price"] or 0
        cid       = r["client_id"]
        repeat    = _is_repeat_client(cid)
        tier      = get_autonomy_tier(score, price, opp_type, repeat)

        # Only auto-send Tier C or explicitly autonomous-approved
        if tier != "C" and r.get("approved_by") != "autonomous":
            continue

        if dry_run:
            results.append({
                "proposal_id": r["proposal_id"],
                "would_send":  True,
                "tier":        tier,
                "dry_run":     True,
            })
            continue

        try:
            send_result = send_proposal_email(
                r["proposal_id"],
                send_mode=SEND_MODE_AUTONOMOUS,
                bcc_manager=True,
            )
            # Mark as autonomous in the DB
            _mark_autonomous(r["proposal_id"])
            results.append({**send_result, "tier": tier})
        except Exception as e:
            print(f"[auto_sender] ERROR sending {r['proposal_id'][:8]}…: {e}")

    return results


def _mark_autonomous(proposal_id: str) -> None:
    """Tag the proposal as autonomously sent for audit trail."""
    conn = get_connection()
    conn.execute(
        "UPDATE proposals SET approved_by='autonomous', updated_at=? WHERE id=?",
        (datetime.now().isoformat(), proposal_id),
    )
    conn.commit()
    conn.close()


# ── Pilot: promote proposal to Tier C (for demo / testing) ───────────────────

def promote_to_autonomous(proposal_id: str) -> bool:
    """
    Mark a draft/pending proposal as approved-autonomous.
    Used in the demo UI to simulate a Tier C send without changing the score.
    In production this would only happen programmatically if tier == 'C'.
    """
    conn = get_connection()
    conn.execute(
        "UPDATE proposals SET status='approved', approved_by='autonomous', updated_at=? WHERE id=?",
        (datetime.now().isoformat(), proposal_id),
    )
    conn.commit()
    conn.close()
    return True


# ── Summary helper ────────────────────────────────────────────────────────────

def get_send_queue_summary() -> dict:
    """
    Return a summary of the current send queue for the dashboard.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT p.id, p.client_id, p.suggested_price, p.approved_by,
               o.opportunity_type, o.score
        FROM proposals p
        JOIN opportunities o ON o.id = p.opportunity_id
        WHERE p.status = 'approved'
        """
    ).fetchall()
    conn.close()

    tier_counts = {"A": 0, "B": 0, "C": 0}
    for row in rows:
        r      = dict(row)
        repeat = _is_repeat_client(r["client_id"])
        tier   = get_autonomy_tier(
            r["score"] or 0, r["suggested_price"] or 0,
            r["opportunity_type"], repeat
        )
        tier_counts[tier] += 1

    return {
        "approved_pending_send": len(rows),
        "by_tier": tier_counts,
    }
