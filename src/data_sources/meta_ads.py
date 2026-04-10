"""
Meta Ads Manager data source.

DEMO MODE  → reads from local SQLite (client_metrics table).
PRODUCTION → Meta Marketing API v20.0
             Endpoint: GET https://graph.facebook.com/v20.0/act_{adAccountId}/insights
             Auth: User or System User Access Token (long-lived)
             Docs: https://developers.facebook.com/docs/marketing-api/insights
"""

from src.data_sources._base import annotate, query

_PRODUCTION_NOTE = (
    "Production: Meta Marketing API v20.0 — "
    "GET /act_{adAccountId}/insights "
    "with a long-lived System User access token."
)


def get_client_ad_metrics(client_id: str, days: int = 30) -> list[dict]:
    """
    Return daily Meta Ads metrics for a client over the last N days.

    Fields: date, ctr, cpc, roas, ad_spend.
    """
    rows = query(
        """
        SELECT date, ctr, cpc, roas, ad_spend
        FROM client_metrics
        WHERE client_id = ?
        ORDER BY date DESC
        LIMIT ?
        """,
        (client_id, days),
    )
    return annotate(rows, _PRODUCTION_NOTE)


def get_latest_ad_metrics(client_id: str) -> dict | None:
    """Return the single most recent Meta Ads snapshot for a client."""
    rows = query(
        """
        SELECT date, ctr, cpc, roas, ad_spend
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
    """Return the most recent Meta Ads snapshot for every client."""
    rows = query(
        """
        SELECT cm.client_id, cm.date, cm.ctr, cm.cpc, cm.roas, cm.ad_spend
        FROM client_metrics cm
        INNER JOIN (
            SELECT client_id, MAX(date) AS max_date
            FROM client_metrics
            GROUP BY client_id
        ) latest ON cm.client_id = latest.client_id AND cm.date = latest.max_date
        """
    )
    return annotate(rows, _PRODUCTION_NOTE)
