"""
Sprint 4 — Client Reply Feedback Loop.

When a client responds to a proposal (or ignores it), the agent:
  1. Records the outcome in feedback_log.
  2. Updates the proposal status.
  3. Adjusts a per-client, per-opportunity-type confidence modifier so the
     detection engine is smarter on the next run.
  4. Triggers downstream actions depending on intent:
       accepted      → schedule a meeting (Google Calendar API in production)
       rejected      → log and reduce confidence
       too_expensive → log, may offer discount in Sprint 7
       need_more_info → flag for human follow-up
       ignored       → log and reduce confidence (same as rejected but milder)
       escalated     → alert account manager immediately

DEMO MODE
   Downstream actions (calendar, Slack escalation) are written to log files.

PRODUCTION MODE
   Calendar: Google Calendar API v3 — insert event on account manager's calendar.
   Escalation: POST to Slack webhook with @account_manager mention.

This module is the core "learning" mechanism before Sprint 5 introduces ML.
Every recorded outcome becomes a training row for the predictive model.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import config
from src.db.schema import get_connection

# ── Valid reply intents ───────────────────────────────────────────────────────
INTENT_ACCEPTED      = "accepted"
INTENT_REJECTED      = "rejected"
INTENT_TOO_EXPENSIVE = "too_expensive"
INTENT_NEED_INFO     = "need_more_info"
INTENT_IGNORED       = "ignored"
INTENT_ESCALATED     = "escalated"

ALL_INTENTS = [
    INTENT_ACCEPTED,
    INTENT_REJECTED,
    INTENT_TOO_EXPENSIVE,
    INTENT_NEED_INFO,
    INTENT_IGNORED,
    INTENT_ESCALATED,
]

# Human-friendly labels shown in the UI
INTENT_LABELS = {
    INTENT_ACCEPTED:      "Yes — accepted the proposal",
    INTENT_REJECTED:      "No — not interested",
    INTENT_TOO_EXPENSIVE: "Too expensive",
    INTENT_NEED_INFO:     "Needs more information",
    INTENT_IGNORED:       "No reply (ignored)",
    INTENT_ESCALATED:     "Complaint / escalation needed",
}

# Confidence adjustments per intent (added to future opportunity scores for
# this client × opportunity_type pair).  Stored in a new DB column / table.
_CONFIDENCE_DELTA = {
    INTENT_ACCEPTED:      +15.0,
    INTENT_REJECTED:      -20.0,
    INTENT_TOO_EXPENSIVE:  -8.0,
    INTENT_NEED_INFO:      +3.0,
    INTENT_IGNORED:       -10.0,
    INTENT_ESCALATED:     -30.0,
}

# Revenue credited per intent (for pilot report)
_REVENUE_BY_INTENT = {
    INTENT_ACCEPTED:      None,   # set from actual proposal price
    INTENT_REJECTED:      0.0,
    INTENT_TOO_EXPENSIVE: 0.0,
    INTENT_NEED_INFO:     0.0,
    INTENT_IGNORED:       0.0,
    INTENT_ESCALATED:     0.0,
}

# ── Feedback log path (demo) ──────────────────────────────────────────────────
FEEDBACK_LOG = config.LOGS_DIR / "feedback.jsonl"
CALENDAR_LOG = config.LOGS_DIR / "calendar_events.jsonl"
ESCALATION_LOG = config.LOGS_DIR / "escalations.jsonl"


# ── Main entry point ──────────────────────────────────────────────────────────

def record_client_reply(
    proposal_id: str,
    intent: str,
    notes: str = "",
    simulated: bool = False,
) -> dict[str, Any]:
    """
    Process a client reply for a given proposal.

    Parameters
    ----------
    proposal_id : str
    intent : str
        One of ALL_INTENTS.
    notes : str
        Free-text note from the account manager.
    simulated : bool
        True when called from the demo UI (simulation mode).

    Returns
    -------
    dict describing what actions were taken.
    """
    if intent not in ALL_INTENTS:
        raise ValueError(f"Unknown intent {intent!r}. Must be one of {ALL_INTENTS}.")

    conn = get_connection()

    # ── Load proposal + opportunity + client ──────────────────────────────────
    row = conn.execute(
        """
        SELECT p.*, o.opportunity_type, o.score,
               c.name AS client_name, c.account_manager,
               c.contact_email
        FROM proposals p
        JOIN opportunities o ON o.id = p.opportunity_id
        JOIN clients       c ON c.id = p.client_id
        WHERE p.id = ?
        """,
        (proposal_id,),
    ).fetchone()

    if row is None:
        conn.close()
        raise ValueError(f"Proposal {proposal_id!r} not found.")

    p = dict(row)
    now = datetime.now().isoformat()

    # ── 1. Determine revenue ──────────────────────────────────────────────────
    revenue = (
        p["suggested_price"] if intent == INTENT_ACCEPTED
        else _REVENUE_BY_INTENT.get(intent, 0.0)
    )

    # ── 2. Insert feedback_log row ────────────────────────────────────────────
    conn.execute(
        """
        INSERT INTO feedback_log
            (opportunity_id, proposal_id, outcome, revenue, notes, logged_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (p["opportunity_id"], proposal_id, intent, revenue, notes, now),
    )

    # ── 3. Update proposal status ─────────────────────────────────────────────
    new_proposal_status = {
        INTENT_ACCEPTED:      "accepted",
        INTENT_REJECTED:      "rejected",
        INTENT_TOO_EXPENSIVE: "rejected",
        INTENT_NEED_INFO:     "sent",        # keep open for follow-up
        INTENT_IGNORED:       "sent",
        INTENT_ESCALATED:     "rejected",
    }[intent]

    conn.execute(
        "UPDATE proposals SET status=?, updated_at=? WHERE id=?",
        (new_proposal_status, now, proposal_id),
    )

    # ── 4. Update opportunity status ──────────────────────────────────────────
    new_opp_status = {
        INTENT_ACCEPTED:      "closed",
        INTENT_REJECTED:      "rejected",
        INTENT_TOO_EXPENSIVE: "rejected",
        INTENT_NEED_INFO:     "sent",
        INTENT_IGNORED:       "rejected",
        INTENT_ESCALATED:     "escalated",
    }[intent]

    conn.execute(
        "UPDATE opportunities SET status=?, updated_at=? WHERE id=?",
        (new_opp_status, now, p["opportunity_id"]),
    )

    conn.commit()
    conn.close()

    # ── 5. Adjust confidence modifier ─────────────────────────────────────────
    delta = _CONFIDENCE_DELTA.get(intent, 0.0)
    _store_confidence_modifier(p["client_id"], p["opportunity_type"], delta)

    # ── 6. Downstream actions ─────────────────────────────────────────────────
    actions_taken: list[str] = []

    if intent == INTENT_ACCEPTED:
        meeting = _schedule_meeting(p, simulated=simulated)
        actions_taken.append(f"Meeting scheduled: {meeting['event_id']}")

    elif intent == INTENT_ESCALATED:
        escalation = _escalate_to_human(p, notes, simulated=simulated)
        actions_taken.append(f"Escalated to {p['account_manager']}: {escalation['alert_id']}")

    # ── 7. Write to feedback log ──────────────────────────────────────────────
    log_entry = {
        "timestamp":        now,
        "proposal_id":      proposal_id,
        "client_id":        p["client_id"],
        "client_name":      p["client_name"],
        "opportunity_type": p["opportunity_type"],
        "intent":           intent,
        "revenue":          revenue,
        "confidence_delta": delta,
        "notes":            notes,
        "actions_taken":    actions_taken,
        "simulated":        simulated,
    }
    _write_feedback_log(log_entry)

    result = {
        "ok":               True,
        "proposal_id":      proposal_id,
        "intent":           intent,
        "intent_label":     INTENT_LABELS[intent],
        "revenue":          revenue,
        "confidence_delta": delta,
        "new_proposal_status": new_proposal_status,
        "new_opp_status":   new_opp_status,
        "actions_taken":    actions_taken,
        "simulated":        simulated,
    }

    print(
        f"[feedback_loop] {'[SIM] ' if simulated else ''}"
        f"Proposal {proposal_id[:8]}… | intent={intent} | "
        f"Δconfidence={delta:+.0f} | revenue=${revenue or 0:.0f}"
    )

    return result


# ── Confidence modifier store ─────────────────────────────────────────────────

def _store_confidence_modifier(client_id: str, opp_type: str, delta: float) -> None:
    """
    Persist a cumulative confidence adjustment for a client × opportunity type.
    Stored in the feedback_log; aggregated at query time by get_confidence_modifier().

    In Sprint 5 this table becomes a feature for the ML model.
    """
    # We reuse feedback_log for audit purposes.  The modifier is computed
    # from the sum of confidence_delta values across all feedback rows.
    # No separate table needed — works correctly for the demo scale.
    pass   # already written to feedback_log in record_client_reply()


def get_confidence_modifier(client_id: str, opp_type: str) -> float:
    """
    Return the cumulative confidence modifier for a client × opportunity type.
    Positive = historically receptive; negative = historically resistant.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT fl.outcome
        FROM feedback_log fl
        JOIN proposals p ON p.id = fl.proposal_id
        JOIN opportunities o ON o.id = p.opportunity_id
        WHERE p.client_id = ?
          AND o.opportunity_type = ?
        ORDER BY fl.logged_at DESC
        LIMIT 10
        """,
        (client_id, opp_type),
    ).fetchall()
    conn.close()

    total = 0.0
    for row in rows:
        total += _CONFIDENCE_DELTA.get(row["outcome"], 0.0)
    return max(-50.0, min(50.0, total))   # clamp to [-50, +50]


# ── Calendar (meeting scheduling) ────────────────────────────────────────────

def _schedule_meeting(proposal: dict, simulated: bool = False) -> dict:
    """
    Schedule a 30-minute discovery call on the account manager's calendar.

    DEMO  → write to logs/calendar_events.jsonl
    PROD  → Google Calendar API v3:
            POST https://www.googleapis.com/calendar/v3/calendars/primary/events
            with a service-account OAuth token.
    """
    event_id  = str(uuid.uuid4())
    start_dt  = (datetime.now() + timedelta(days=2)).replace(hour=10, minute=0, second=0)
    end_dt    = start_dt + timedelta(minutes=30)
    now       = datetime.now().isoformat()

    event = {
        "event_id":    event_id,
        "summary":     f"Demo call — {proposal['client_name']} ({proposal['opportunity_type'].replace('_', ' ').title()})",
        "description": (
            f"Client accepted proposal #{proposal['id'][:8]}. "
            f"Opportunity: {proposal['opportunity_type']}. "
            f"Value: ${proposal['suggested_price']:,.0f}"
        ),
        "start":       start_dt.isoformat(),
        "end":         end_dt.isoformat(),
        "attendees":   [proposal.get("contact_email", "client@demo.local"),
                        _guess_manager_email(proposal.get("account_manager") or "manager")],
        "created_at":  now,
        "simulated":   simulated,
        "_production_integration": (
            "Production: POST /calendar/v3/calendars/primary/events "
            "with OAuth2 service account. Attendees receive Google Calendar invites. "
            "Event includes the full proposal body in the description."
        ),
    }

    if config.DEMO_MODE or simulated:
        CALENDAR_LOG.parent.mkdir(parents=True, exist_ok=True)
        with CALENDAR_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    else:
        _create_google_calendar_event(event)

    print(f"[feedback_loop] Meeting scheduled: {event_id[:8]}… on {start_dt.strftime('%Y-%m-%d %H:%M')}")
    return event


def _create_google_calendar_event(event: dict) -> None:
    """Stub for production Google Calendar API call."""
    # In production: use google-auth + googleapiclient
    # from googleapiclient.discovery import build
    # service = build('calendar', 'v3', credentials=creds)
    # service.events().insert(calendarId='primary', body={...}).execute()
    raise NotImplementedError("Google Calendar integration not configured.")


# ── Escalation ────────────────────────────────────────────────────────────────

def _escalate_to_human(proposal: dict, notes: str, simulated: bool = False) -> dict:
    """
    Alert the account manager immediately when a client escalates or complains.

    DEMO  → write to logs/escalations.jsonl
    PROD  → POST to Slack webhook with @mention of account manager.
    """
    alert_id = str(uuid.uuid4())
    now      = datetime.now().isoformat()

    alert = {
        "alert_id":    alert_id,
        "timestamp":   now,
        "client_id":   proposal["client_id"],
        "client_name": proposal["client_name"],
        "proposal_id": proposal["id"],
        "manager":     proposal.get("account_manager", ""),
        "notes":       notes,
        "simulated":   simulated,
        "message": (
            f"ESCALATION: Client {proposal['client_name']} has escalated. "
            f"Proposal {proposal['id'][:8]}. "
            f"Notes: {notes or 'none'}. "
            f"Immediate follow-up required by {proposal.get('account_manager', 'account manager')}."
        ),
        "_production_integration": (
            "Production: POST to SLACK_WEBHOOK_URL with blocks containing "
            "@account_manager mention, client name, proposal link, and a "
            "'Take over' button that marks the opportunity as 'human_handling' in the DB."
        ),
    }

    if config.DEMO_MODE or simulated:
        ESCALATION_LOG.parent.mkdir(parents=True, exist_ok=True)
        with ESCALATION_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(alert, ensure_ascii=False) + "\n")
    else:
        _send_slack_escalation(alert)

    print(f"[feedback_loop] ESCALATION logged: {alert_id[:8]}… for {proposal['client_name']}")
    return alert


def _send_slack_escalation(alert: dict) -> None:
    """Stub for production Slack webhook call."""
    import urllib.request
    payload = json.dumps({"text": alert["message"]}).encode()
    req = urllib.request.Request(
        config.SLACK_WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=5)


def _guess_manager_email(name: str) -> str:
    slug = name.lower().replace(" ", ".").replace("á", "a").replace("é", "e")
    return f"{slug}@agency.demo"


# ── Log readers ───────────────────────────────────────────────────────────────

def _write_feedback_log(entry: dict) -> None:
    FEEDBACK_LOG.parent.mkdir(parents=True, exist_ok=True)
    with FEEDBACK_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_feedback_log() -> list[dict]:
    if not FEEDBACK_LOG.exists():
        return []
    records = []
    for line in FEEDBACK_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records


def load_calendar_log() -> list[dict]:
    if not CALENDAR_LOG.exists():
        return []
    records = []
    for line in CALENDAR_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records


def load_escalation_log() -> list[dict]:
    if not ESCALATION_LOG.exists():
        return []
    records = []
    for line in ESCALATION_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records


# ── Pilot report helpers ──────────────────────────────────────────────────────

def get_pilot_metrics() -> dict:
    """
    Aggregate pilot statistics from the DB.
    Used by the pilot dashboard page.
    """
    conn = get_connection()

    total_opps = conn.execute(
        "SELECT COUNT(*) FROM opportunities"
    ).fetchone()[0]

    proposals_generated = conn.execute(
        "SELECT COUNT(*) FROM proposals"
    ).fetchone()[0]

    sent = conn.execute(
        "SELECT COUNT(*) FROM proposals WHERE status IN ('sent','accepted')"
    ).fetchone()[0]

    autonomous_sent = conn.execute(
        "SELECT COUNT(*) FROM proposals WHERE status IN ('sent','accepted') AND approved_by='autonomous'"
    ).fetchone()[0]

    approved_sent = sent - autonomous_sent

    accepted = conn.execute(
        "SELECT COUNT(*) FROM proposals WHERE status = 'accepted'"
    ).fetchone()[0]

    total_revenue = conn.execute(
        "SELECT COALESCE(SUM(revenue),0) FROM feedback_log WHERE outcome='accepted'"
    ).fetchone()[0]

    rejected = conn.execute(
        "SELECT COUNT(*) FROM feedback_log WHERE outcome IN ('rejected','too_expensive','ignored')"
    ).fetchone()[0]

    escalations = conn.execute(
        "SELECT COUNT(*) FROM feedback_log WHERE outcome='escalated'"
    ).fetchone()[0]

    by_type = conn.execute(
        """
        SELECT o.opportunity_type, COUNT(*) AS cnt,
               SUM(CASE WHEN p.status='accepted' THEN 1 ELSE 0 END) AS accepted
        FROM proposals p
        JOIN opportunities o ON o.id = p.opportunity_id
        GROUP BY o.opportunity_type
        ORDER BY cnt DESC
        """
    ).fetchall()

    conn.close()

    acceptance_rate = (accepted / sent * 100) if sent > 0 else 0.0

    return {
        "total_opportunities":   total_opps,
        "proposals_generated":   proposals_generated,
        "proposals_sent":        sent,
        "autonomous_sent":       autonomous_sent,
        "approved_sent":         approved_sent,
        "proposals_accepted":    accepted,
        "proposals_rejected":    rejected,
        "escalations":           escalations,
        "acceptance_rate_pct":   round(acceptance_rate, 1),
        "total_revenue":         float(total_revenue),
        "by_type": [dict(r) for r in by_type],
        # Estimated time saved: 20 min per proposal manually, 2 min with agent
        "time_saved_hours":      round(proposals_generated * 18 / 60, 1),
    }
