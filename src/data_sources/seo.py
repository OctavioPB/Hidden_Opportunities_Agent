"""
SEO tool data source.

DEMO MODE  → reads from local SQLite (client_metrics table).
PRODUCTION → Semrush API or Ahrefs API v3
             Semrush endpoint: GET https://api.semrush.com/?type=domain_organic&key={apiKey}&domain={domain}
             Ahrefs endpoint:  GET https://apiv2.ahrefs.com?from=organic_keywords&target={domain}&token={token}
             Docs: https://developer.semrush.com/api/v3/
"""

from src.data_sources._base import annotate, query

_PRODUCTION_NOTE = (
    "Production: Semrush API — "
    "GET api.semrush.com/?type=domain_organic&key={apiKey}&domain={domain}. "
    "Alt: Ahrefs API v3 /organic_keywords with Bearer token."
)


def get_seo_metrics(client_id: str, days: int = 30) -> list[dict]:
    """
    Return daily SEO metrics for a client.

    Fields: date, organic_traffic, keyword_rankings.
    """
    rows = query(
        """
        SELECT date, organic_traffic, keyword_rankings
        FROM client_metrics
        WHERE client_id = ?
        ORDER BY date DESC
        LIMIT ?
        """,
        (client_id, days),
    )
    return annotate(rows, _PRODUCTION_NOTE)


def get_latest_seo_metrics(client_id: str) -> dict | None:
    """Return the single most recent SEO snapshot for a client."""
    rows = query(
        """
        SELECT date, organic_traffic, keyword_rankings
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
    """Return the most recent SEO snapshot for every client."""
    rows = query(
        """
        SELECT cm.client_id, cm.date, cm.organic_traffic, cm.keyword_rankings
        FROM client_metrics cm
        INNER JOIN (
            SELECT client_id, MAX(date) AS max_date
            FROM client_metrics
            GROUP BY client_id
        ) latest ON cm.client_id = latest.client_id AND cm.date = latest.max_date
        """
    )
    return annotate(rows, _PRODUCTION_NOTE)
