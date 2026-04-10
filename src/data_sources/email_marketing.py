"""
Email marketing platform data source.

DEMO MODE  → reads from local SQLite (client_metrics + text_signals tables).
PRODUCTION → Mailchimp Marketing API 3.0
             Endpoint: GET https://us1.api.mailchimp.com/3.0/reports
             Auth: API key via Basic Auth (user: "anystring", pass: API key)
             Docs: https://mailchimp.com/developer/marketing/api/reports/
             Alt: ActiveCampaign API v3, Klaviyo API v2023-12-15
"""

from src.data_sources._base import annotate, query

_PRODUCTION_NOTE = (
    "Production: Mailchimp Marketing API 3.0 — "
    "GET /3.0/reports/{campaignId} "
    "with API key via Basic Auth. "
    "Alternatively: ActiveCampaign /api/3/campaigns or Klaviyo /api/campaigns."
)


def get_email_metrics(client_id: str, days: int = 30) -> list[dict]:
    """
    Return daily email marketing metrics for a client.

    Fields: date, email_open_rate, email_click_rate.
    """
    rows = query(
        """
        SELECT date, email_open_rate, email_click_rate
        FROM client_metrics
        WHERE client_id = ?
        ORDER BY date DESC
        LIMIT ?
        """,
        (client_id, days),
    )
    return annotate(rows, _PRODUCTION_NOTE)


def get_latest_email_metrics(client_id: str) -> dict | None:
    """Return the single most recent email metrics snapshot."""
    rows = query(
        """
        SELECT date, email_open_rate, email_click_rate
        FROM client_metrics
        WHERE client_id = ?
        ORDER BY date DESC
        LIMIT 1
        """,
        (client_id,),
    )
    if not rows:
        return None
    return annotate(rows, _PRODUCTION_NOTE)[0]


def get_all_clients_latest() -> list[dict]:
    """Return the most recent email metrics for every client."""
    rows = query(
        """
        SELECT cm.client_id, cm.date, cm.email_open_rate, cm.email_click_rate
        FROM client_metrics cm
        INNER JOIN (
            SELECT client_id, MAX(date) AS max_date
            FROM client_metrics
            GROUP BY client_id
        ) latest ON cm.client_id = latest.client_id AND cm.date = latest.max_date
        """
    )
    return annotate(rows, _PRODUCTION_NOTE)


def get_client_emails(client_id: str) -> list[dict]:
    """
    Return all stored email text signals for a client (for NLP pipeline — Sprint 6).
    """
    rows = query(
        """
        SELECT id, raw_text, sentiment, mentions_price, asks_for_results,
               churn_risk, urgency_signal, processed_at
        FROM text_signals
        WHERE client_id = ? AND source = 'email'
        ORDER BY processed_at DESC
        """,
        (client_id,),
    )
    return annotate(rows, _PRODUCTION_NOTE)
