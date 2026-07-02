"""
Feature 7 — WhatsApp Business Outreach Channel.

Sends proposal notifications via the Meta WhatsApp Cloud API when a client
has opted in and preferred_channel='whatsapp'.

DEMO MODE  → writes to logs/whatsapp.jsonl; no API call.
PRODUCTION → POSTs to Meta Graph API /messages endpoint.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import config
from src.db.schema import get_connection

WA_LOG = config.LOGS_DIR / "whatsapp.jsonl"

_GRAPH_URL = "https://graph.facebook.com/v19.0/{phone_number_id}/messages"


def send_whatsapp_proposal(client_id: str, proposal_id: str) -> dict:
    """
    Send a WhatsApp proposal notification for an opted-in client.
    Silently skips if client has not opted in.
    """
    conn = get_connection()
    row = conn.execute(
        """
        SELECT c.name, c.whatsapp_number, c.whatsapp_opted_in, c.preferred_channel,
               p.subject, p.suggested_price, o.opportunity_type
        FROM clients c
        JOIN proposals     p ON p.client_id = c.id AND p.id = ?
        JOIN opportunities o ON o.id = p.opportunity_id
        WHERE c.id = ?
        """,
        (proposal_id, client_id),
    ).fetchone()
    conn.close()

    if not row:
        return {"ok": False, "reason": "proposal or client not found"}

    client = dict(row)

    if not client.get("whatsapp_opted_in"):
        return {"ok": False, "reason": "client has not opted in to WhatsApp"}

    phone  = client.get("whatsapp_number", "")
    if not phone:
        return {"ok": False, "reason": "no WhatsApp number on record"}

    opp_label = client["opportunity_type"].replace("_", " ").title()
    message   = (
        f"Hi {client['name']},\n\n"
        f"We've identified an opportunity that could benefit your business: "
        f"*{opp_label}* — a tailored solution at *${client['suggested_price']:,.0f}*.\n\n"
        f"Would you like to learn more? Reply to this message or click below.\n\n"
        f"_(Sent by Hidden Opportunities Agent — reply STOP to opt out)_"
    )

    record = {
        "timestamp":        datetime.now().isoformat(),
        "proposal_id":      proposal_id,
        "client_id":        client_id,
        "client_name":      client["name"],
        "to_number":        phone,
        "opportunity_type": client["opportunity_type"],
        "message":          message,
        "demo_mode":        config.DEMO_MODE,
        "_production": (
            "Production: POST to Meta Graph API /v19.0/{phone_number_id}/messages "
            "using pre-approved template 'proposal_notification'. "
            "Auth: WHATSAPP_ACCESS_TOKEN in .env."
        ),
    }

    if config.DEMO_MODE:
        WA_LOG.parent.mkdir(parents=True, exist_ok=True)
        with WA_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"[whatsapp][DEMO] Message logged for {client['name'][:20]} → {phone}")
    else:
        _post_message(phone, message)

    return {"ok": True, "demo_mode": config.DEMO_MODE, "record": record}


def set_channel_preference(client_id: str, channel: str, whatsapp_number: str | None = None) -> None:
    """Update a client's preferred outreach channel and optionally their WhatsApp number."""
    conn = get_connection()
    if whatsapp_number:
        conn.execute(
            "UPDATE clients SET preferred_channel=?, whatsapp_number=?, whatsapp_opted_in=1 WHERE id=?",
            (channel, whatsapp_number, client_id),
        )
    else:
        conn.execute(
            "UPDATE clients SET preferred_channel=? WHERE id=?",
            (channel, client_id),
        )
    conn.commit()
    conn.close()


def get_opted_in_clients() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, name, whatsapp_number, preferred_channel FROM clients WHERE whatsapp_opted_in=1"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def load_whatsapp_log() -> list[dict]:
    if not WA_LOG.exists():
        return []
    records = []
    for line in WA_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return list(reversed(records))


def _post_message(to_number: str, message: str) -> None:
    import httpx
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    access_token    = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    template_name   = os.getenv("WHATSAPP_TEMPLATE_NAME", "proposal_notification")
    url = _GRAPH_URL.format(phone_number_id=phone_number_id)
    payload = {
        "messaging_product": "whatsapp",
        "to":                to_number,
        "type":              "template",
        "template": {
            "name":     template_name,
            "language": {"code": "en_US"},
            "components": [{"type": "body", "parameters": [{"type": "text", "text": message[:1024]}]}],
        }
    }
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    resp = httpx.post(url, json=payload, headers=headers, timeout=10)
    resp.raise_for_status()
