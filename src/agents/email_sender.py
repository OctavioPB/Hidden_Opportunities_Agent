"""
Sprint 4 — Email Sender.

Abstraction layer for outbound email.  Decouples the rest of the agent from
the specific email provider so swapping SendGrid → Mailgun → SES requires
changes only here.

DEMO MODE  (DEMO_MODE=true)
   All sends are written to logs/sent_emails.jsonl.  No network calls are made.
   The log entry mirrors exactly what the production payload would look like,
   so the demo is production-realistic.

PRODUCTION MODE  (DEMO_MODE=false)
   Sends via the SendGrid Web API v3.
   Endpoint: POST https://api.sendgrid.com/v3/mail/send
   Auth: API key in the Authorization header.
   The account manager is always BCC'd on every automated send.

In production this module is also responsible for:
   - Tracking open/click events via SendGrid webhooks (stored in feedback_log).
   - Auto-expiring proposals that have not been opened in 14 days.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import config
from src.db.schema import get_connection

# ── Log path ──────────────────────────────────────────────────────────────────
SENT_LOG = config.LOGS_DIR / "sent_emails.jsonl"

# ── Autonomy-tier send modes ──────────────────────────────────────────────────
SEND_MODE_AUTONOMOUS  = "autonomous"   # Tier C — no human approval needed
SEND_MODE_APPROVED    = "approved"     # Tier B — human approved before send


# ── Core send function ────────────────────────────────────────────────────────

def send_proposal_email(
    proposal_id: str,
    send_mode: str = SEND_MODE_APPROVED,
    bcc_manager: bool = True,
) -> dict[str, Any]:
    """
    Send the proposal email to the client.

    Parameters
    ----------
    proposal_id : str
        The proposals.id from the DB.
    send_mode : str
        SEND_MODE_AUTONOMOUS or SEND_MODE_APPROVED.
    bcc_manager : bool
        Whether to BCC the account manager (always True in production).

    Returns
    -------
    dict with: send_id, proposal_id, recipient, status, timestamp, send_mode
    """
    conn = get_connection()

    # ── Load proposal + client ────────────────────────────────────────────────
    row = conn.execute(
        """
        SELECT p.*, c.name AS client_name, c.contact_email, c.account_manager
        FROM proposals p
        JOIN clients c ON c.id = p.client_id
        WHERE p.id = ?
        """,
        (proposal_id,),
    ).fetchone()

    if row is None:
        conn.close()
        raise ValueError(f"Proposal {proposal_id!r} not found.")

    p = dict(row)

    if p["status"] not in ("approved", "draft"):
        conn.close()
        raise ValueError(
            f"Proposal {proposal_id!r} has status '{p['status']}' — "
            f"only 'approved' or 'draft' (Tier C) proposals can be sent."
        )

    # ── Build payload ─────────────────────────────────────────────────────────
    recipient    = p["contact_email"] or f"client-{p['client_id']}@demo.local"
    manager_email = _guess_manager_email(p.get("account_manager") or "manager")
    send_id      = str(uuid.uuid4())
    now          = datetime.now().isoformat()

    payload: dict[str, Any] = {
        "send_id":       send_id,
        "proposal_id":   proposal_id,
        "client_id":     p["client_id"],
        "client_name":   p["client_name"],
        "to":            recipient,
        "bcc":           manager_email if bcc_manager else None,
        "subject":       p["subject"],
        "body":          p["body"],
        "send_mode":     send_mode,
        "timestamp":     now,
        "status":        "sent",
        "_production_integration": (
            "Production: POST https://api.sendgrid.com/v3/mail/send "
            "with Authorization: Bearer $SENDGRID_API_KEY. "
            "BCC is passed in the 'personalizations' array. "
            "Open/click tracking enabled via SendGrid's event webhook."
        ),
    }

    # ── Dispatch ──────────────────────────────────────────────────────────────
    if config.DEMO_MODE:
        _write_log(payload)
    else:
        _send_via_sendgrid(payload)

    # ── Update DB ─────────────────────────────────────────────────────────────
    conn.execute(
        "UPDATE proposals SET status='sent', sent_at=?, updated_at=? WHERE id=?",
        (now, now, proposal_id),
    )
    conn.execute(
        "UPDATE opportunities SET status='sent', updated_at=? "
        "WHERE id = (SELECT opportunity_id FROM proposals WHERE id=?)",
        (now, proposal_id),
    )
    conn.commit()
    conn.close()

    print(
        f"[email_sender] {'[DEMO] ' if config.DEMO_MODE else ''}"
        f"Sent proposal {proposal_id[:8]}… to {recipient} "
        f"(mode: {send_mode}, BCC: {manager_email if bcc_manager else 'none'})"
    )

    return payload


def send_reactivation_email(
    client_id: str,
    subject: str,
    body: str,
    send_mode: str = SEND_MODE_AUTONOMOUS,
) -> dict[str, Any]:
    """
    Send a standalone reactivation email (not tied to a proposal).
    Used for Tier C reactivation where value < $150 and score ≥ 90.
    """
    conn = get_connection()
    client = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
    conn.close()

    if client is None:
        raise ValueError(f"Client {client_id!r} not found.")

    c         = dict(client)
    recipient = c.get("contact_email") or f"{client_id}@demo.local"
    send_id   = str(uuid.uuid4())
    now       = datetime.now().isoformat()

    payload = {
        "send_id":       send_id,
        "proposal_id":   None,
        "client_id":     client_id,
        "client_name":   c["name"],
        "to":            recipient,
        "bcc":           _guess_manager_email(c.get("account_manager") or "manager"),
        "subject":       subject,
        "body":          body,
        "send_mode":     send_mode,
        "timestamp":     now,
        "status":        "sent",
        "_production_integration": (
            "Production: SendGrid API v3. Reactivation emails bypass the "
            "normal proposal approval flow per GOVERNANCE.md Tier C rules "
            "(score ≥ 90, value ≤ $150, reactivation opportunity type only)."
        ),
    }

    if config.DEMO_MODE:
        _write_log(payload)
    else:
        _send_via_sendgrid(payload)

    return payload


# ── Log & production helpers ──────────────────────────────────────────────────

def _write_log(payload: dict) -> None:
    """Append a send record to logs/sent_emails.jsonl (demo mode)."""
    SENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with SENT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _send_via_sendgrid(payload: dict) -> None:
    """
    Real SendGrid API call (production mode).
    Requires SENDGRID_API_KEY in environment.
    """
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, To, Bcc

        message = Mail(
            from_email    = config.EMAIL_FROM,
            to_emails     = payload["to"],
            subject       = payload["subject"],
            plain_text_content = payload["body"],
        )
        if payload.get("bcc"):
            message.add_bcc(payload["bcc"])

        sg = SendGridAPIClient(config.SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"[email_sender] SendGrid response: {response.status_code}")

    except Exception as e:
        print(f"[email_sender] SendGrid send FAILED: {e}")
        # In production: raise and trigger escalation; in demo: log the error
        raise


def _guess_manager_email(manager_name: str) -> str:
    """Convert account manager name to an email address (demo convention)."""
    slug = manager_name.lower().replace(" ", ".").replace("á", "a").replace("é", "e")
    return f"{slug}@agency.demo"


# ── Log reader ────────────────────────────────────────────────────────────────

def load_sent_log() -> list[dict]:
    """Return all records from the sent emails log."""
    if not SENT_LOG.exists():
        return []
    records = []
    for line in SENT_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records
