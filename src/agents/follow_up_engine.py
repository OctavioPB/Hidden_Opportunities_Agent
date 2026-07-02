"""
Feature 1 — Automated Follow-Up Sequences.

When a client ignores a proposal (INTENT_IGNORED), the engine schedules
two follow-up touches spaced 7 and 14 days out, each with a different angle.

DEMO MODE  → sends are written to logs/follow_ups.jsonl; email not dispatched.
PRODUCTION → sends via send_proposal_email(); same delivery pipeline as initial proposals.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta

import config
from src.db.schema import get_connection

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
DAYS_BETWEEN = [7, 14]  # Turn 1 at +7 days, Turn 2 at +14 days


def schedule_follow_up(proposal_id: str) -> list[dict]:
    """
    Create follow-up queue entries for a proposal that was ignored.
    Skips if entries already exist (idempotent).
    """
    conn = get_connection()

    # Check if already scheduled
    existing = conn.execute(
        "SELECT COUNT(*) FROM follow_up_queue WHERE proposal_id=? AND status='pending'",
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
            f"Original proposal: {opp_label} — ${p['suggested_price']:,.0f}\n\n"
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
    PRODUCTION → calls send_proposal_email() with the follow-up content.
    """
    conn = get_connection()
    now_iso = datetime.now().isoformat()

    due = conn.execute(
        """
        SELECT fq.*, c.name AS client_name, c.contact_email,
               p.subject AS original_subject
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
        _send_follow_up(entry)
        _mark_sent(entry["id"])
        sent.append(entry)

    if sent:
        print(f"[follow_up] Processed {len(sent)} due follow-up(s).")
    return sent


def _send_follow_up(entry: dict) -> None:
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
        "_production":   "Production: calls send_proposal_email() with follow-up content via SendGrid.",
    }

    if config.DEMO_MODE:
        FOLLOW_UP_LOG.parent.mkdir(parents=True, exist_ok=True)
        with FOLLOW_UP_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(log_record, ensure_ascii=False) + "\n")
        print(f"[follow_up][DEMO] Turn {entry['sequence_turn']} → {entry['client_name'][:20]} "
              f"({entry['angle']})")
    else:
        try:
            from src.agents.email_sender import send_proposal_email
            send_proposal_email(
                entry["proposal_id"],
                send_mode="follow_up",
                bcc_manager=True,
                override_subject=entry["subject"],
                override_body=entry.get("body", ""),
            )
        except Exception as exc:
            print(f"[follow_up] Send failed for {entry['id'][:8]}: {exc}")


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
    if not FOLLOW_UP_LOG.exists():
        return []
    records = []
    for line in FOLLOW_UP_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records
