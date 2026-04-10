"""
Google Analytics data source.

DEMO MODE  → reads from local SQLite (client_metrics table).
PRODUCTION → Google Analytics Data API v1
             Endpoint: POST https://analyticsdata.googleapis.com/v1beta/properties/{propertyId}:runReport
             Auth: OAuth 2.0 service account (google-auth library)
             Docs: https://developers.google.com/analytics/devguides/reporting/data/v1
"""

from src.data_sources._base import annotate, query

_PRODUCTION_NOTE = (
    "Production: Google Analytics Data API v1 — "
    "POST /v1beta/properties/{propertyId}:runReport "
    "with OAuth 2.0 service account credentials."
)


def get_client_metrics(client_id: str, days: int = 30) -> list[dict]:
    """
    Return daily GA metrics for a client over the last N days.

    Fields: date, bounce_rate, pages_per_session, conversion_rate, organic_traffic.
    """
    rows = query(
        """
        SELECT date, bounce_rate, pages_per_session, conversion_rate, organic_traffic
        FROM client_metrics
        WHERE client_id = ?
        ORDER BY date DESC
        LIMIT ?
        """,
        (client_id, days),
    )
    return annotate(rows, _PRODUCTION_NOTE)


def get_latest_metrics(client_id: str) -> dict | None:
    """Return the single most recent GA metrics snapshot for a client."""
    rows = query(
        """
        SELECT date, bounce_rate, pages_per_session, conversion_rate, organic_traffic
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
    """Return the most recent GA snapshot for every client (for bulk detection)."""
    rows = query(
        """
        SELECT cm.client_id, cm.date, cm.bounce_rate, cm.pages_per_session,
               cm.conversion_rate, cm.organic_traffic
        FROM client_metrics cm
        INNER JOIN (
            SELECT client_id, MAX(date) AS max_date
            FROM client_metrics
            GROUP BY client_id
        ) latest ON cm.client_id = latest.client_id AND cm.date = latest.max_date
        """
    )
    return annotate(rows, _PRODUCTION_NOTE)
