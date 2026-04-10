"""
Sprint 1 — Opportunity Scorer.

Fetches the latest metrics for every client (or a specific client) from
the data sources layer and applies the rules engine to produce a ranked
list of detected opportunities.

In Sprint 2 this becomes the daily detection job.
In Sprint 5 the rules are augmented (and eventually replaced) by the ML model.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from src.agents.rules import OpportunityResult, evaluate
from src.data_sources import crm
from src.data_sources import google_analytics as ga
from src.data_sources import meta_ads
from src.data_sources import email_marketing
from src.data_sources import seo
from src.db.schema import get_connection


# ── Metric aggregator ─────────────────────────────────────────────────────────

def _get_merged_metrics(client_id: str) -> dict:
    """
    Merge the latest snapshot from all data sources into a single flat dict.
    This is the input vector for the rules engine (and later the ML model).
    """
    merged: dict = {"client_id": client_id}

    for fetcher, fields in [
        (ga.get_latest_metrics,            ["bounce_rate", "pages_per_session", "conversion_rate", "organic_traffic"]),
        (meta_ads.get_latest_ad_metrics,   ["ctr", "cpc", "roas", "ad_spend"]),
        (email_marketing.get_latest_email_metrics, ["email_open_rate", "email_click_rate"]),
        (seo.get_latest_seo_metrics,       ["organic_traffic", "keyword_rankings"]),
    ]:
        snapshot = fetcher(client_id)
        if snapshot:
            for f in fields:
                if f in snapshot:
                    merged[f] = snapshot[f]

    # Pull activity signals from CRM
    activity = crm.get_client_activity(client_id)
    if activity:
        merged["days_inactive"]           = activity.get("days_inactive", 0) or 0
        merged["days_since_last_contact"] = activity.get("days_since_last_contact", 0) or 0

    return merged


# ── Scoring ───────────────────────────────────────────────────────────────────

def score_client(client_id: str) -> list[OpportunityResult]:
    """Return all opportunities detected for a single client."""
    metrics = _get_merged_metrics(client_id)
    return evaluate(metrics)


def score_all_clients() -> list[dict]:
    """
    Run the rules engine against every client in the database.

    Returns a list of dicts, one per detected opportunity, sorted by score.
    """
    clients = crm.get_all_clients()
    results = []

    for client in clients:
        cid = client["id"]
        opportunities = score_client(cid)
        for opp in opportunities:
            results.append({
                "client_id":        cid,
                "client_name":      client["name"],
                "industry":         client["industry"],
                "opportunity_type": opp.opportunity_type,
                "label":            opp.label,
                "score":            opp.score,
                "suggested_price":  opp.suggested_price,
                "rationale":        opp.rationale,
                "triggered_signals": opp.triggered_signals,
                "is_demo_scenario": client.get("is_demo_scenario", 0),
            })

    return sorted(results, key=lambda r: r["score"], reverse=True)


# ── Persistence ───────────────────────────────────────────────────────────────

def persist_opportunities(scored: list[dict]) -> int:
    """
    Upsert detected opportunities into the database.
    Only inserts NEW opportunities (status='detected').
    Returns the count of newly inserted rows.
    """
    conn = get_connection()
    inserted = 0

    for r in scored:
        # Check if this opportunity type is already tracked for this client
        existing = conn.execute(
            """
            SELECT id FROM opportunities
            WHERE client_id = ? AND opportunity_type = ?
              AND status NOT IN ('accepted', 'rejected', 'closed')
            """,
            (r["client_id"], r["opportunity_type"]),
        ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO opportunities
                    (id, client_id, opportunity_type, score, status, detected_at, updated_at)
                VALUES (?, ?, ?, ?, 'detected', ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    r["client_id"],
                    r["opportunity_type"],
                    r["score"],
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ),
            )
            inserted += 1
        else:
            # Update score in case it changed
            conn.execute(
                "UPDATE opportunities SET score = ?, updated_at = ? WHERE id = ?",
                (r["score"], datetime.now().isoformat(), existing[0]),
            )

    conn.commit()
    conn.close()
    return inserted
