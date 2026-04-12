"""
Sprint 5 — Opportunity Scorer (updated).

Fetches the latest metrics for every client (or a specific client) from
the data sources layer and applies the rules engine to produce a ranked
list of detected opportunities.

Sprint 5 update: if the ML model is trained, each opportunity dict is
augmented with `ml_probability` (0–1) and `blended_score` (rule + ML blend).
The Opportunities dashboard uses `blended_score` when available.
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

    Sprint 5: if the ML model is trained, augments each row with
    `ml_probability` and `blended_score`.  Otherwise both are None and
    the UI falls back to the rule score.

    Returns a list of dicts, one per detected opportunity, sorted by score.
    """
    # Lazy-load ML model once per call (not per client)
    try:
        from src.ml.model import load_model, model_is_trained
        from src.ml.dataset import _metrics_to_row
        from src.ml.model import predict_proba
        _ml_active = model_is_trained()
        _ml_model  = load_model() if _ml_active else None
    except Exception:
        _ml_active = False
        _ml_model  = None

    clients = crm.get_all_clients()
    results = []

    for client in clients:
        cid = client["id"]
        opportunities = score_client(cid)
        metrics       = _get_merged_metrics(cid)

        for opp in opportunities:
            ml_prob    = None
            blended    = opp.score

            if _ml_active and _ml_model is not None:
                try:
                    from src.ml.dataset import _metrics_to_row, INDUSTRY_CODES, OPP_TYPE_CODES
                    feat = _metrics_to_row(
                        metrics,
                        client.get("industry", ""),
                        opp.opportunity_type,
                        int(client.get("account_age_days") or 365),
                    )
                    ml_prob = round(predict_proba(feat, _ml_model), 4)
                    blended = round(0.55 * ml_prob * 100 + 0.45 * opp.score, 1)
                except Exception:
                    pass

            results.append({
                "client_id":        cid,
                "client_name":      client["name"],
                "industry":         client["industry"],
                "opportunity_type": opp.opportunity_type,
                "label":            opp.label,
                "score":            opp.score,          # rule-engine score (0–100)
                "ml_probability":   ml_prob,            # ML acceptance prob (0–1) or None
                "blended_score":    blended,             # final ranking score
                "suggested_price":  opp.suggested_price,
                "rationale":        opp.rationale,
                "triggered_signals": opp.triggered_signals,
                "is_demo_scenario": client.get("is_demo_scenario", 0),
            })

    sort_key = "blended_score" if any(r["ml_probability"] is not None for r in results) else "score"
    return sorted(results, key=lambda r: r[sort_key], reverse=True)


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
