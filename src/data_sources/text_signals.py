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
    # Same aggregation as get_signal_summary(), for all clients in one query.
    # Only processed rows (sentiment IS NOT NULL) contribute to the values;
    # clients whose signals are all unprocessed still appear, with zeros.
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT client_id,
               COALESCE(AVG(sentiment), 0.0)                                         AS sentiment_score,
               MAX(CASE WHEN sentiment IS NOT NULL AND mentions_price   THEN 1 ELSE 0 END) AS mentions_price,
               MAX(CASE WHEN sentiment IS NOT NULL AND asks_for_results THEN 1 ELSE 0 END) AS asks_for_results,
               MAX(CASE WHEN sentiment IS NOT NULL AND churn_risk       THEN 1 ELSE 0 END) AS churn_risk,
               MAX(CASE WHEN sentiment IS NOT NULL AND urgency_signal   THEN 1 ELSE 0 END) AS urgency_signal,
               MAX(CASE WHEN sentiment IS NOT NULL AND interest_signal  THEN 1 ELSE 0 END) AS interest_signal,
               COUNT(sentiment)                                                      AS n_signals
        FROM text_signals
        GROUP BY client_id
        """
    ).fetchall()
    conn.close()

    summaries = []
    for r in rows:
        s = dict(r)
        s["sentiment_score"] = round(s["sentiment_score"], 4)
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
            COALESCE(SUM(mentions_price), 0)   AS price_mentions,
            COALESCE(SUM(asks_for_results), 0) AS results_queries,
            COALESCE(SUM(churn_risk), 0)       AS churn_flags,
            COALESCE(SUM(urgency_signal), 0)   AS urgency_flags,
            COALESCE(SUM(interest_signal), 0)  AS interest_flags
        FROM text_signals
        WHERE sentiment IS NOT NULL
        """
    ).fetchone()
    conn.close()
    # COALESCE: SUM() over zero rows is NULL, which the UI would render as "null"
    return dict(row)
