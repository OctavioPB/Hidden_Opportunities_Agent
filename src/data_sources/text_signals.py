"""
Sprint 6 — Text Signals Data Source.

Provides read access to the NLP pipeline output stored in the text_signals
table. Used by:
  - The ML dataset builder (get_signal_summary → ML feature vector)
  - The UI dashboard (get_client_signals → email browser)
  - The urgency alert system (get_urgency_alerts → red-alert panel)

In production
-------------
  This module would read from a PostgreSQL table (or BigQuery view) that
  is populated nightly by the NLP pipeline. In the demo, it reads from the
  local SQLite text_signals table populated by scripts/seed_db.py and
  scripts/process_text.py.
"""

from __future__ import annotations

from typing import Any

from src.db.schema import get_connection


def get_client_signals(client_id: str) -> list[dict[str, Any]]:
    """
    Return all text signal records for a specific client.

    Each dict includes: id, source, raw_text, sentiment,
    mentions_price, asks_for_results, churn_risk, urgency_signal,
    interest_signal, processed_at.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT id, source, raw_text, sentiment,
               mentions_price, asks_for_results, churn_risk,
               urgency_signal, interest_signal, processed_at
        FROM text_signals
        WHERE client_id = ?
        ORDER BY processed_at DESC
        """,
        (client_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_signal_summary(client_id: str) -> dict[str, Any]:
    """
    Aggregate text signals for a single client into ML feature values.

    Returns
    -------
    {
        sentiment_score  : float   (-1 to 1, mean of all rows)
        mentions_price   : int     (1 if any row has flag set)
        asks_for_results : int
        churn_risk       : int
        urgency_signal   : int
        interest_signal  : int
        n_signals        : int     (number of records)
    }
    All values are 0 / 0.0 if no processed signals exist.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT sentiment, mentions_price, asks_for_results,
               churn_risk, urgency_signal, interest_signal
        FROM text_signals
        WHERE client_id = ? AND sentiment IS NOT NULL
        """,
        (client_id,),
    ).fetchall()
    conn.close()

    if not rows:
        return {
            "sentiment_score":  0.0,
            "mentions_price":   0,
            "asks_for_results": 0,
            "churn_risk":       0,
            "urgency_signal":   0,
            "interest_signal":  0,
            "n_signals":        0,
        }

    sentiments = [r["sentiment"] or 0.0 for r in rows]
    return {
        "sentiment_score":  round(sum(sentiments) / len(sentiments), 4),
        "mentions_price":   int(any(r["mentions_price"]   for r in rows)),
        "asks_for_results": int(any(r["asks_for_results"] for r in rows)),
        "churn_risk":       int(any(r["churn_risk"]       for r in rows)),
        "urgency_signal":   int(any(r["urgency_signal"]   for r in rows)),
        "interest_signal":  int(any(r["interest_signal"]  for r in rows)),
        "n_signals":        len(rows),
    }


def get_all_signal_summaries() -> list[dict[str, Any]]:
    """
    Return aggregated signal summaries for EVERY client that has signals.
    Used to build the signal matrix in the dashboard.
    """
    conn = get_connection()
    client_ids = [
        r[0] for r in conn.execute(
            "SELECT DISTINCT client_id FROM text_signals"
        ).fetchall()
    ]
    conn.close()

    summaries = []
    for cid in client_ids:
        s = get_signal_summary(cid)
        s["client_id"] = cid
        summaries.append(s)
    return summaries


def get_urgency_alerts() -> list[dict[str, Any]]:
    """
    Return client-level urgency alerts:
    clients where churn_risk=1 OR urgency_signal=1.

    Includes client name for the alert panel.

    In production: this triggers a Slack DM to the account manager
    within 30 minutes of the NLP pipeline completing.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            ts.client_id,
            c.name AS client_name,
            c.account_manager,
            c.industry,
            MAX(ts.churn_risk)     AS churn_risk,
            MAX(ts.urgency_signal) AS urgency_signal,
            AVG(ts.sentiment)      AS avg_sentiment,
            GROUP_CONCAT(ts.raw_text, ' ||| ') AS combined_text
        FROM text_signals ts
        JOIN clients c ON c.id = ts.client_id
        WHERE ts.churn_risk = 1 OR ts.urgency_signal = 1
        GROUP BY ts.client_id
        ORDER BY c.name
        """,
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_signals_by_type() -> dict[str, int]:
    """
    Count total signals of each type across all clients.
    Used for the dashboard KPI row.
    """
    conn = get_connection()
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(mentions_price)   AS price_mentions,
            SUM(asks_for_results) AS results_queries,
            SUM(churn_risk)       AS churn_flags,
            SUM(urgency_signal)   AS urgency_flags,
            SUM(interest_signal)  AS interest_flags
        FROM text_signals
        WHERE sentiment IS NOT NULL
        """
    ).fetchone()
    conn.close()

    if row is None:
        return {k: 0 for k in [
            "total", "price_mentions", "results_queries",
            "churn_flags", "urgency_flags", "interest_flags",
        ]}
    return dict(row)
