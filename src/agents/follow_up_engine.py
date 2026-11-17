"""
Feature 1 — Automated Follow-Up Sequences.

When a client ignores a proposal (INTENT_IGNORED), the engine schedules
two follow-up touches spaced 7 and 14 days out, each with a different angle.

DEMO MODE  → sends are written to logs/follow_ups.jsonl; email not dispatched.
PRODUCTION → sends via email_sender.send_reactivation_email(); same SendGrid
             pipeline as initial proposals. A failed send stays 'pending' and is
             retried on the next run.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import config
from src.db.schema import get_connection
from src.jsonl import append_jsonl, read_jsonl

FOLLOW_UP_LOG = config.LOGS_DIR / "follow_ups.jsonl"

# Angles used for each follow-up turn
_ANGLES = {
    1: {
        "angle": "roi_focus",
        "subject_prefix": "Re: A quick ROI perspective on",
        "body_hook": (
            "I wanted to follow up on the proposal I sent recently. "
            "Many clients in your industry see a measurable return within the first 30 days — "
            "I'd love to walk you through a quick before/after scenario specific to your numbers."
        ),
    },
    2: {
        "angle": "final_reminder",
        "subject_prefix": "Last note on",
        "body_hook": (
            "I know things get busy. This will be my last note on this topic — "
            "if the timing isn't right I completely understand. "
            "The offer stands whenever you're ready to revisit it."
        ),
    },
}

MAX_TURNS = 2

# A follow-up only makes sense while the proposal is still awaiting an answer
_OPEN_PROPOSAL_STATUSES = frozenset({"sent", "approved", "draft", "pending_approval"})
DAYS_BETWEEN = [7, 14]  # Turn 1 at +7 days, Turn 2 at +14 days


def schedule_follow_up(proposal_id: str) -> list[dict]:
    """
    Create follow-up queue entries for a proposal that was ignored.

    Idempotent: a proposal gets one sequence. Entries that are pending or
    already sent block a new one — turn 2 tells the client it is the last
    note, so the sequence must not restart after it has run.
    """
    conn = get_connection()

    # Check if already scheduled or already delivered
    existing = conn.execute(
        "SELECT COUNT(*) FROM follow_up_queue "
        "WHERE proposal_id=? AND status IN ('pending', 'sent')",
        (proposal_id,),
    ).fetchone()[0]
    if existing > 0:
        conn.close()
        return []

    # Fetch proposal + client context
    row = conn.execute(
        """
        SELECT p.subject, p.suggested_price, p.client_id,
               c.name AS client_name, o.opportunity_type
        FROM proposals p
        JOIN clients      c ON c.id = p.client_id
        JOIN opportunities o ON o.id = p.opportunity_id
        WHERE p.id = ?
        """,
        (proposal_id,),
    ).fetchone()

    if row is None:
        conn.close()
        return []

    p = dict(row)
    now = datetime.now()
    entries = []

    for turn in range(1, MAX_TURNS + 1):
        angle_cfg  = _ANGLES[turn]
        sched_at   = (now + timedelta(days=DAYS_BETWEEN[turn - 1])).isoformat()
        entry_id   = str(uuid.uuid4())
        opp_label  = p["opportunity_type"].replace("_", " ").title()
        subject    = f"{angle_cfg['subject_prefix']} {opp_label}"
        body       = (
            f"Hi,\n\n{angle_cfg['body_hook']}\n\n"
            f"Original proposal: {opp_label} — ${p['suggested_price'] or 0:,.0f}\n\n"
            f"Happy to jump on a quick call if that's easier.\n\nBest regards"
        )

        conn.execute(
            """
            INSERT INTO follow_up_queue
                (id, proposal_id, client_id, sequence_turn, scheduled_at,
                 status, angle, subject, body)
            VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?)
            """,
            (entry_id, proposal_id, p["client_id"], turn, sched_at,
             angle_cfg["angle"], subject, body),
        )
        entries.append({
            "id": entry_id,
            "proposal_id": proposal_id,
            "client_name": p["client_name"],
            "sequence_turn": turn,
            "scheduled_at": sched_at,
            "angle": angle_cfg["angle"],
            "subject": subject,
        })

    conn.commit()
    conn.close()

    for e in entries:
        print(f"[follow_up] Scheduled turn {e['sequence_turn']} for {e['client_name'][:20]} "
              f"on {e['scheduled_at'][:10]} (angle: {e['angle']})")
    return entries


def cancel_follow_ups(proposal_id: str) -> int:
    """Cancel all pending follow-ups for a resolved proposal."""
    conn = get_connection()
    cur = conn.execute(
        "UPDATE follow_up_queue SET status='cancelled' WHERE proposal_id=? AND status='pending'",
        (proposal_id,),
    )
    n = cur.rowcount
    conn.commit()
    conn.close()
    if n > 0:
        print(f"[follow_up] Cancelled {n} pending follow-up(s) for proposal {proposal_id[:8]}…")
    return n


def process_due_follow_ups() -> list[dict]:
    """
    Send all pending follow-ups that are due now or past-due.
    Called by the daily job.
    DEMO MODE  → logs to follow_ups.jsonl, no email sent.
    PRODUCTION → emails the follow-up content via SendGrid.

    Follow-ups whose proposal has since been resolved (accepted, rejected,
    paid, escalated) are cancelled instead of sent. An entry is marked 'sent'
    only when the send succeeded; failures stay pending for the next run.
    """
    conn = get_connection()
    now_iso = datetime.now().isoformat()

    due = conn.execute(
        """
        SELECT fq.*, c.name AS client_name, c.contact_email,
               p.subject AS original_subject, p.status AS proposal_status
        FROM follow_up_queue fq
        JOIN clients  c ON c.id = fq.client_id
        JOIN proposals p ON p.id = fq.proposal_id
        WHERE fq.status = 'pending'
          AND fq.scheduled_at <= ?
        ORDER BY fq.scheduled_at ASC
        """,
        (now_iso,),
    ).fetchall()
    conn.close()

    sent = []
    for row in due:
        entry = dict(row)
        if entry["proposal_status"] not in _OPEN_PROPOSAL_STATUSES:
            cancel_follow_ups(entry["proposal_id"])
            continue
        if _send_follow_up(entry):
            _mark_sent(entry["id"])
            sent.append(entry)

    if sent:
        print(f"[follow_up] Processed {len(sent)} due follow-up(s).")
    return sent


def _send_follow_up(entry: dict) -> bool:
    """Deliver one follow-up. Returns True when it was sent (or logged, in demo mode)."""
    now = datetime.now().isoformat()
    log_record = {
        "timestamp":     now,
        "follow_up_id":  entry["id"],
        "proposal_id":   entry["proposal_id"],
        "client_name":   entry["client_name"],
        "to_email":      entry.get("contact_email", ""),
        "sequence_turn": entry["sequence_turn"],
        "angle":         entry["angle"],
        "subject":       entry["subject"],
        "body_preview":  (entry.get("body") or "")[:120],
        "demo_mode":     config.DEMO_MODE,
        "_production":   "Production: emails the follow-up content to the client via SendGrid.",
    }

    if config.DEMO_MODE:
        append_jsonl(FOLLOW_UP_LOG, log_record)
        print(f"[follow_up][DEMO] Turn {entry['sequence_turn']} → {entry['client_name'][:20]} "
              f"({entry['angle']})")
        return True

    try:
        from src.agents.email_sender import SEND_MODE_FOLLOW_UP, send_reactivation_email
        send_reactivation_email(
            entry["client_id"],
            subject=entry["subject"],
            body=entry.get("body") or "",
            send_mode=SEND_MODE_FOLLOW_UP,
            proposal_id=entry["proposal_id"],
        )
    except Exception as exc:
        print(f"[follow_up] Send failed for {entry['id'][:8]}, will retry next run: {exc}")
        return False
    append_jsonl(FOLLOW_UP_LOG, log_record)
    return True


def _mark_sent(follow_up_id: str) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE follow_up_queue SET status='sent', sent_at=? WHERE id=?",
        (datetime.now().isoformat(), follow_up_id),
    )
    conn.commit()
    conn.close()


def get_follow_up_queue(proposal_id: str | None = None) -> list[dict]:
    conn = get_connection()
    if proposal_id:
        rows = conn.execute(
            """
            SELECT fq.*, c.name AS client_name
            FROM follow_up_queue fq
            JOIN clients c ON c.id = fq.client_id
            WHERE fq.proposal_id = ?
            ORDER BY fq.sequence_turn
            """,
            (proposal_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT fq.*, c.name AS client_name
            FROM follow_up_queue fq
            JOIN clients c ON c.id = fq.client_id
            ORDER BY fq.scheduled_at ASC
            LIMIT 200
            """,
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def load_follow_up_log() -> list[dict]:
    return read_jsonl(FOLLOW_UP_LOG)
