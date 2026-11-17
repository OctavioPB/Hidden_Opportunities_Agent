"""
Sprint 5 — Live Inference Engine.

Runs the trained ML model over all clients daily and blends its probability
estimates with the rule-engine scores from Sprint 2.

Blending formula
----------------
  If model is trained:
    blended_score = 0.55 * (ml_probability × 100) + 0.45 * rule_score
  If model is NOT trained (cold start):
    blended_score = rule_score          ← rules-only fallback
    ml_probability = None

The blended score replaces the rule score in the opportunities table column
`ml_probability` (used in the Sprint 5 UI).

In production
-------------
  This module is called from the daily job after detection.
  Predictions are stored in opportunities.ml_probability and
  opportunities.ml_explanation (JSON).
  Fallback to rules-only is automatic if the model file is missing.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from src.ml.dataset import _metrics_to_row
from src.ml.model import load_model, model_is_trained, predict_proba_batch
from src.ml.explainer import explain_batch
from src.agents.rules import ALL_OPPORTUNITY_TYPES, evaluate as rules_evaluate
from src.data_sources import crm
from src.data_sources import google_analytics as ga
from src.data_sources import meta_ads
from src.data_sources import email_marketing
from src.data_sources import seo
from src.db.schema import get_connection

# Blend weights
ML_WEIGHT   = 0.55
RULE_WEIGHT = 0.45


# ── Per-client inference ──────────────────────────────────────────────────────

def _get_latest_metrics(client_id: str) -> dict:
    """Merge the latest metrics snapshot for a client (mirrors scorer.py logic)."""
    merged: dict = {}
    for fetcher, fields in [
        (ga.get_latest_metrics,                     ["bounce_rate", "pages_per_session", "conversion_rate", "organic_traffic"]),
        (meta_ads.get_latest_ad_metrics,            ["ctr", "cpc", "roas", "ad_spend"]),
        (email_marketing.get_latest_email_metrics,  ["email_open_rate", "email_click_rate"]),
        (seo.get_latest_seo_metrics,                ["organic_traffic", "keyword_rankings"]),
    ]:
        snap = fetcher(client_id)
        if snap:
            for f in fields:
                if f in snap:
                    merged[f] = snap[f]

    activity = crm.get_client_activity(client_id)
    if activity:
        merged["days_inactive"] = activity.get("days_inactive", 0) or 0

    return merged


def _predict(
    clients_with_metrics: list[tuple[dict, dict]],
    model,
) -> list[dict[str, Any]]:
    """
    Score every opportunity type for the given (client_row, metrics) pairs.

    All feature rows go through the model in one predict_proba call and all
    surfaced predictions through one SHAP call, so the cost is two batch
    operations regardless of portfolio size.
    """
    # ── Pass 1: rules + feature rows (pure Python) ────────────────────────────
    candidates: list[tuple[dict, str, Any, list[float]]] = []
    for client_row, metrics in clients_with_metrics:
        try:
            industry     = client_row.get("industry", "")
            age          = int(client_row.get("account_age_days") or 365)
            rule_results = {r.opportunity_type: r for r in rules_evaluate(metrics)}
            for opp_type in ALL_OPPORTUNITY_TYPES:
                candidates.append((
                    client_row, opp_type, rule_results.get(opp_type),
                    _metrics_to_row(metrics, industry, opp_type, age),
                ))
        except Exception as e:
            print(f"[inference] Error for client {client_row.get('id')}: {e}")

    # ── Pass 2: one batch of probabilities ────────────────────────────────────
    if model is not None and candidates:
        probs: list[float | None] = list(predict_proba_batch([c[3] for c in candidates], model))
    else:
        probs = [None] * len(candidates)

    kept: list[tuple[dict, str, Any, list[float], float | None, float]] = []
    for (client_row, opp_type, rule_res, feature_row), ml_prob in zip(candidates, probs, strict=True):
        rule_score = rule_res.score if rule_res else 0.0
        blended    = (
            ML_WEIGHT * ml_prob * 100 + RULE_WEIGHT * rule_score
            if ml_prob is not None else rule_score
        )
        # Only surface if either rule or ML thinks it's notable
        if blended < 45 and (ml_prob is None or ml_prob < 0.35):
            continue
        kept.append((client_row, opp_type, rule_res, feature_row, ml_prob, blended))

    # ── Pass 3: one batch of SHAP explanations, only for surfaced rows ────────
    if model is not None and kept:
        explanations: list[dict | None] = list(explain_batch(
            [k[3] for k in kept], model, top_n=4, probs=[k[4] for k in kept],
        ))
    else:
        explanations = [None] * len(kept)

    predictions = []
    for (client_row, opp_type, rule_res, _row, ml_prob, blended), explanation in zip(
        kept, explanations, strict=True
    ):
        predictions.append({
            "client_id":        client_row["id"],
            "client_name":      client_row.get("name", ""),
            "industry":         client_row.get("industry", ""),
            "opportunity_type": opp_type,
            "rule_score":       round(rule_res.score if rule_res else 0.0, 1),
            "ml_probability":   round(ml_prob, 4) if ml_prob is not None else None,
            "blended_score":    round(blended, 1),
            "is_demo_scenario": client_row.get("is_demo_scenario", 0),
            "explanation":      explanation,
            "suggested_price":  rule_res.suggested_price if rule_res else 0,
            "rationale":        rule_res.rationale if rule_res else "",
        })

    return sorted(predictions, key=lambda r: r["blended_score"], reverse=True)


def predict_for_client(
    client_id: str,
    model=None,
) -> list[dict[str, Any]]:
    """
    Run inference for every opportunity type for one client.

    Returns a list of dicts — one per opportunity type that has a meaningful
    ML probability or a rule score above 50.
    """
    if model is None:
        model = load_model()

    client_row = crm.get_client(client_id)
    if client_row is None:
        return []

    return _predict([(client_row, _get_latest_metrics(client_id))], model)


def predict_for_all(model=None) -> list[dict[str, Any]]:
    """
    Run inference for every client in the DB.
    Returns a flat list sorted by blended_score descending.
    """
    if model is None:
        model = load_model()

    # Two queries for the whole portfolio instead of six per client
    from src.agents.scorer import _fetch_all_metrics_batch
    all_metrics = _fetch_all_metrics_batch()
    clients     = crm.get_all_clients()

    return _predict([(c, all_metrics.get(c["id"], {})) for c in clients], model)


# ── Persist ML scores to DB ───────────────────────────────────────────────────

def update_ml_scores(predictions: list[dict]) -> int:
    """
    Write ml_probability into the opportunities table for matching rows.
    Returns number of rows updated.
    """
    conn  = get_connection()
    updated = 0
    for pred in predictions:
        if pred.get("ml_probability") is None:
            continue
        conn.execute(
            """
            UPDATE opportunities
            SET ml_probability = ?, updated_at = datetime('now')
            WHERE client_id = ? AND opportunity_type = ?
              AND status NOT IN ('closed', 'rejected', 'escalated')
            """,
            (pred["ml_probability"], pred["client_id"], pred["opportunity_type"]),
        )
        updated += conn.execute("SELECT changes()").fetchone()[0]

    conn.commit()
    conn.close()
    return updated


# ── Summary helpers for the dashboard ────────────────────────────────────────

def get_inference_summary() -> dict:
    """Quick summary for the ML dashboard KPI row."""
    is_trained = model_is_trained()
    if not is_trained:
        return {
            "model_trained": False,
            "total_predictions": 0,
            "high_prob_count": 0,
            "avg_ml_probability": None,
        }

    conn = get_connection()
    rows = conn.execute(
        "SELECT ml_probability FROM opportunities WHERE ml_probability IS NOT NULL"
    ).fetchall()
    conn.close()

    probs = [r[0] for r in rows if r[0] is not None]
    return {
        "model_trained":     True,
        "total_predictions": len(probs),
        "high_prob_count":   sum(1 for p in probs if p >= 0.7),
        "avg_ml_probability": round(float(np.mean(probs)), 4) if probs else None,
    }
