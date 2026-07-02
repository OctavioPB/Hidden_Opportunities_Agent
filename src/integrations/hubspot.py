"""
Feature 5 — CRM Write-Back (HubSpot).

When a proposal is accepted, the agent creates a deal in HubSpot,
logs activity on the contact record, and updates lifecycle stage.

DEMO MODE  → writes to logs/crm_sync.jsonl + crm_sync_log table; no API call.
PRODUCTION → POSTs to HubSpot CRM API v3.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

import config
from src.db.schema import get_connection

CRM_SYNC_LOG = config.LOGS_DIR / "crm_sync.jsonl"

_API_BASE = "https://api.hubapi.com"


def create_deal(
    client_id: str,
    proposal_id: str,
    revenue: float,
    opportunity_type: str,
) -> dict:
    """
    Create a HubSpot deal for an accepted proposal.
    Returns the deal record (real or simulated).
    """
    conn = get_connection()
    client = conn.execute(
        "SELECT name, crm_contact_id FROM clients WHERE id=?", (client_id,)
    ).fetchone()
    conn.close()

    client_name = dict(client)["name"] if client else "Unknown"
    opp_label   = opportunity_type.replace("_", " ").title()
    deal_id     = str(uuid.uuid4())
    now         = datetime.now().isoformat()

    deal = {
        "deal_id":          deal_id,
        "dealname":         f"{client_name} — {opp_label}",
        "amount":           revenue,
        "dealstage":        "closedwon",
        "closedate":        now[:10],
        "opportunity_type": opportunity_type,
        "proposal_id":      proposal_id,
        "client_id":        client_id,
        "synced_at":        now,
        "demo_mode":        config.DEMO_MODE,
    }

    if config.DEMO_MODE:
        _log_sync("create_deal", deal, client_id, proposal_id, revenue)
        _store_crm_ref(client_id, proposal_id, deal_id)
        print(f"[crm][DEMO] Deal created: {deal['dealname'][:40]} ${revenue:,.0f}")
    else:
        _post_hubspot_deal(deal, config.HUBSPOT_API_KEY if hasattr(config, "HUBSPOT_API_KEY") else "")

    return deal


def log_activity(client_id: str, note: str) -> dict:
    """Add a CRM activity note on the client's contact record."""
    now    = datetime.now().isoformat()
    record = {
        "action":     "log_activity",
        "client_id":  client_id,
        "note":       note,
        "logged_at":  now,
        "demo_mode":  config.DEMO_MODE,
    }

    if config.DEMO_MODE:
        _log_sync("log_activity", record, client_id, None, None)
        print(f"[crm][DEMO] Activity logged for client {client_id[:8]}")
    else:
        _post_hubspot_note(client_id, note, getattr(config, "HUBSPOT_API_KEY", ""))

    return record


def get_sync_log(limit: int = 50) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM crm_sync_log ORDER BY synced_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def load_crm_log() -> list[dict]:
    if not CRM_SYNC_LOG.exists():
        return []
    records = []
    for line in CRM_SYNC_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return list(reversed(records))


# ── Internal helpers ──────────────────────────────────────────────────────────

def _log_sync(action: str, record: dict, client_id: str, proposal_id: str | None, revenue: float | None) -> None:
    CRM_SYNC_LOG.parent.mkdir(parents=True, exist_ok=True)
    with CRM_SYNC_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    conn = get_connection()
    conn.execute(
        """
        INSERT INTO crm_sync_log (proposal_id, client_id, action, revenue, demo_mode)
        VALUES (?, ?, ?, ?, 1)
        """,
        (proposal_id, client_id, action, revenue),
    )
    conn.commit()
    conn.close()


def _store_crm_ref(client_id: str, proposal_id: str, deal_id: str) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE clients SET crm_deal_id=? WHERE id=?", (deal_id, client_id)
    )
    conn.commit()
    conn.close()


def _post_hubspot_deal(deal: dict, api_key: str) -> None:
    import httpx
    payload = {
        "properties": {
            "dealname":  deal["dealname"],
            "amount":    str(deal["amount"]),
            "dealstage": deal["dealstage"],
            "closedate": deal["closedate"],
        }
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    resp = httpx.post(f"{_API_BASE}/crm/v3/objects/deals", json=payload, headers=headers, timeout=10)
    resp.raise_for_status()


def _post_hubspot_note(client_id: str, note: str, api_key: str) -> None:
    import httpx
    payload = {"properties": {"hs_note_body": note, "hs_timestamp": datetime.now().isoformat()}}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    resp = httpx.post(f"{_API_BASE}/crm/v3/objects/notes", json=payload, headers=headers, timeout=10)
    resp.raise_for_status()
