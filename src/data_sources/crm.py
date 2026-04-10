"""
CRM data source.

DEMO MODE  → reads from local SQLite (clients + feedback_log tables).
PRODUCTION → HubSpot CRM API v3 (or Pipedrive API v1)
             Endpoint: GET https://api.hubapi.com/crm/v3/objects/contacts
             Auth: Private App access token (Bearer)
             Docs: https://developers.hubspot.com/docs/api/crm/contacts
"""

from src.data_sources._base import annotate, query

_PRODUCTION_NOTE = (
    "Production: HubSpot CRM API v3 — "
    "GET /crm/v3/objects/contacts (or /deals, /notes) "
    "with a Private App Bearer token. "
    "For Pipedrive: GET /api/v1/persons with an API key."
)


def get_client(client_id: str) -> dict | None:
    """Return a single client record by ID."""
    rows = query(
        "SELECT * FROM clients WHERE id = ?",
        (client_id,),
    )
    if not rows:
        return None
    return annotate(rows, _PRODUCTION_NOTE)[0]


def get_all_clients() -> list[dict]:
    """Return all client records."""
    rows = query("SELECT * FROM clients ORDER BY name")
    return annotate(rows, _PRODUCTION_NOTE)


def get_demo_clients() -> list[dict]:
    """Return only the fixed demo scenario clients."""
    rows = query(
        "SELECT * FROM clients WHERE is_demo_scenario = 1 ORDER BY name"
    )
    return annotate(rows, _PRODUCTION_NOTE)


def get_client_activity(client_id: str) -> dict:
    """
    Return a summary of recent activity for a client:
    last proposal sent, last outcome, days inactive.
    """
    rows = query(
        """
        SELECT
            c.id,
            c.account_age_days,
            c.monthly_spend,
            MAX(cm.days_inactive) AS days_inactive,
            MAX(cm.days_since_last_contact) AS days_since_last_contact
        FROM clients c
        LEFT JOIN client_metrics cm ON cm.client_id = c.id
        WHERE c.id = ?
        GROUP BY c.id
        """,
        (client_id,),
    )
    if not rows:
        return {}
    return annotate(rows, _PRODUCTION_NOTE)[0]


def get_feedback_history(client_id: str) -> list[dict]:
    """Return all past proposal outcomes for a client."""
    rows = query(
        """
        SELECT fl.outcome, fl.revenue, fl.notes, fl.logged_at
        FROM feedback_log fl
        JOIN proposals p ON p.id = fl.proposal_id
        WHERE p.client_id = ?
        ORDER BY fl.logged_at DESC
        """,
        (client_id,),
    )
    return annotate(rows, _PRODUCTION_NOTE)
