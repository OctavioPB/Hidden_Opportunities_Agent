"""
Sprint 6 — NLP Processing Pipeline.

Orchestrates end-to-end text signal extraction:
  1. Load unprocessed (or all) text_signals rows from the DB.
  2. Run signal_extractor.extract_signals() on each raw_text.
  3. Write results back to the text_signals table.
  4. Optionally update the opportunities table with an adjusted score.

In production
-------------
  This pipeline runs nightly after new emails are ingested from the Gmail /
  CRM APIs. DEMO_MODE uses the synthetic text already in the DB (generated
  by scripts/seed_db.py from the generator's _generate_text_signals()).
  LLM extraction can be enabled by setting DEMO_MODE=false in .env and
  providing an API key (OPENAI_API_KEY or ANTHROPIC_API_KEY).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.db.schema import get_connection
from src.nlp.signal_extractor import extract_signals, aggregate_signals


# ── Row processor ─────────────────────────────────────────────────────────────

def _process_row(row: dict, use_llm: bool) -> dict[str, Any]:
    """Extract signals from a single DB row."""
    signals = extract_signals(
        text=row["raw_text"] or "",
        source=row.get("source", "email"),
        use_llm=use_llm,
    )
    signals["id"] = row["id"]
    return signals


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run_pipeline(
    reprocess_all: bool = False,
    use_llm: bool = False,
    verbose: bool = True,
) -> dict[str, Any]:
    """
    Process text signals in the database.

    Parameters
    ----------
    reprocess_all : if True, reprocess even rows that already have signals;
                    if False (default), only process rows where sentiment IS NULL.
    use_llm       : try LLM extraction (falls back to keyword mode).
    verbose       : print progress.

    Returns
    -------
    dict with: total_processed, churn_alerts, urgency_alerts, clients_updated
    """
    conn = get_connection()

    # Load rows to process
    if reprocess_all:
        rows = conn.execute(
            "SELECT id, client_id, source, raw_text FROM text_signals"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, client_id, source, raw_text FROM text_signals "
            "WHERE sentiment IS NULL"
        ).fetchall()

    rows = [dict(r) for r in rows]
    if verbose:
        print(f"[nlp] Processing {len(rows)} text signal rows…")

    churn_alerts   = 0
    urgency_alerts = 0
    clients_seen   = set()

    for row in rows:
        signals = _process_row(row, use_llm=use_llm)

        conn.execute(
            """
            UPDATE text_signals SET
                sentiment       = ?,
                mentions_price  = ?,
                asks_for_results = ?,
                churn_risk      = ?,
                urgency_signal  = ?,
                interest_signal = ?,
                processed_at    = ?
            WHERE id = ?
            """,
            (
                signals["sentiment"],
                signals["mentions_price"],
                signals["asks_for_results"],
                signals["churn_risk"],
                signals["urgency_signal"],
                signals.get("interest_signal", 0),
                datetime.now().isoformat(),
                row["id"],
            ),
        )

        if signals["churn_risk"]:
            churn_alerts += 1
        if signals["urgency_signal"]:
            urgency_alerts += 1
        clients_seen.add(row["client_id"])

    conn.commit()
    conn.close()

    summary = {
        "total_processed":  len(rows),
        "churn_alerts":     churn_alerts,
        "urgency_alerts":   urgency_alerts,
        "clients_updated":  len(clients_seen),
        "extraction_mode":  "llm" if use_llm else "keyword",
        "ran_at":           datetime.now().isoformat(),
    }

    if verbose:
        print(f"[nlp] Done. Processed: {len(rows)} | "
              f"Churn alerts: {churn_alerts} | "
              f"Urgency alerts: {urgency_alerts} | "
              f"Clients: {len(clients_seen)}")

    return summary


def get_pipeline_summary() -> dict[str, Any]:
    """
    Quick summary for the dashboard:
      - total text signals in DB
      - how many have been processed
      - total urgency / churn alerts
    """
    conn = get_connection()

    total = conn.execute("SELECT COUNT(*) FROM text_signals").fetchone()[0]
    processed = conn.execute(
        "SELECT COUNT(*) FROM text_signals WHERE sentiment IS NOT NULL"
    ).fetchone()[0]
    churn = conn.execute(
        "SELECT COUNT(*) FROM text_signals WHERE churn_risk = 1"
    ).fetchone()[0]
    urgency = conn.execute(
        "SELECT COUNT(*) FROM text_signals WHERE urgency_signal = 1"
    ).fetchone()[0]
    price_mentions = conn.execute(
        "SELECT COUNT(DISTINCT client_id) FROM text_signals WHERE mentions_price = 1"
    ).fetchone()[0]
    conn.close()

    return {
        "total_signals":    total,
        "processed":        processed,
        "unprocessed":      total - processed,
        "churn_count":      churn,
        "urgency_count":    urgency,
        "price_mentions_clients": price_mentions,
    }
