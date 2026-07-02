"""
Opportunity Scorer.

score_all_clients() is the hot path — called on every Opportunities page load.

Optimisations applied:
  • All client metrics fetched in ONE SQL query (window function) instead of
    155 clients × 5 data-source queries = 775 round-trips.
  • Propensity tiers fetched in one query, not per-result.
  • Results cached in-process for 5 minutes; filter/sort requests (by type,
    industry, propensity) return instantly from cache.
  • ML model loaded once per scoring run, not per client.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from src.agents.rules import OpportunityResult, evaluate
from src.data_sources import crm
from src.data_sources import google_analytics as ga
from src.data_sources import meta_ads
from src.data_sources import email_marketing
from src.data_sources import seo
from src.db.schema import get_connection

# ── TTL cache ─────────────────────────────────────────────────────────────────
_cache_payload:    list[dict] | None = None
_cache_expires_at: datetime          = datetime.min
_CACHE_TTL = timedelta(minutes=5)


def invalidate_cache() -> None:
    """Call after any write that changes scored opportunities."""
    global _cache_payload, _cache_expires_at
    _cache_payload    = None
    _cache_expires_at = datetime.min


# ── Batch metrics loader ──────────────────────────────────────────────────────

def _fetch_all_metrics_batch() -> dict[str, dict]:
    """
    Fetch the most-recent client_metrics row for every client in one query.
    Returns {client_id: {field: value, ...}}.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT client_id,
               bounce_rate, pages_per_session, conversion_rate, organic_traffic,
               ctr, cpc, roas, ad_spend,
               email_open_rate, email_click_rate,
               keyword_rankings,
               days_inactive, days_since_last_contact
        FROM (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY client_id ORDER BY date DESC) AS rn
            FROM client_metrics
        )
        WHERE rn = 1
        """
    ).fetchall()
    conn.close()

    out: dict[str, dict] = {}
    for row in rows:
        d   = dict(row)
        cid = d.pop("client_id")
        out[cid] = d
    return out


# ── Single-client helpers (used by daily_job / score_client) ──────────────────

def _get_merged_metrics(client_id: str) -> dict:
    merged: dict = {"client_id": client_id}
    for fetcher, fields in [
        (ga.get_latest_metrics,                    ["bounce_rate", "pages_per_session", "conversion_rate", "organic_traffic"]),
        (meta_ads.get_latest_ad_metrics,           ["ctr", "cpc", "roas", "ad_spend"]),
        (email_marketing.get_latest_email_metrics, ["email_open_rate", "email_click_rate"]),
        (seo.get_latest_seo_metrics,               ["organic_traffic", "keyword_rankings"]),
    ]:
        snapshot = fetcher(client_id)
        if snapshot:
            for f in fields:
                if f in snapshot:
                    merged[f] = snapshot[f]
    activity = crm.get_client_activity(client_id)
    if activity:
        merged["days_inactive"]           = activity.get("days_inactive", 0) or 0
        merged["days_since_last_contact"] = activity.get("days_since_last_contact", 0) or 0
    return merged


def score_client(client_id: str) -> list[OpportunityResult]:
    """Score a single client (used by daily_job and per-client views)."""
    metrics = _get_merged_metrics(client_id)
    return evaluate(metrics)


# ── Bulk scorer ───────────────────────────────────────────────────────────────

def score_all_clients() -> list[dict]:
    """
    Run the rules engine + ML scoring against every client.
    Returns a list of opportunity dicts sorted by propensity tier then score.
    Results are cached for 5 minutes; call invalidate_cache() after writes.
    """
    global _cache_payload, _cache_expires_at

    if _cache_payload is not None and datetime.now() < _cache_expires_at:
        return _cache_payload

    # Load ML model once for the whole run
    try:
        from src.ml.model import load_model, model_is_trained, predict_proba_batch
        from src.ml.dataset import _metrics_to_row
        _ml_active = model_is_trained()
        _ml_model  = load_model() if _ml_active else None
    except Exception:
        _ml_active = False
        _ml_model  = None

    # Three queries total for the whole portfolio
    all_metrics = _fetch_all_metrics_batch()   # 1 query — latest metrics per client
    clients     = crm.get_all_clients()        # 1 query — client master data

    conn_p = get_connection()
    propensity: dict[str, tuple] = {
        r[0]: (r[1], r[2])
        for r in conn_p.execute(
            "SELECT id, propensity_tier, propensity_score FROM clients"
        ).fetchall()
    }                                          # 1 query — propensity tiers
    conn_p.close()

    # ── Pass 1: rules engine (pure Python, no DB) ─────────────────────────────
    results:      list[dict]        = []
    feat_rows:    list[list[float]] = []
    feat_indices: list[int]         = []  # which results[] entries need ml_prob

    for client in clients:
        cid     = client["id"]
        metrics = {**all_metrics.get(cid, {}), "client_id": cid}
        tier, pscore = propensity.get(cid, (None, None))

        for opp in evaluate(metrics):
            idx = len(results)
            results.append({
                "client_id":         cid,
                "client_name":       client["name"],
                "industry":          client["industry"],
                "opportunity_type":  opp.opportunity_type,
                "label":             opp.label,
                "score":             opp.score,
                "ml_probability":    None,
                "blended_score":     opp.score,
                "suggested_price":   opp.suggested_price,
                "rationale":         opp.rationale,
                "triggered_signals": opp.triggered_signals,
                "is_demo_scenario":  client.get("is_demo_scenario", 0),
                "propensity_tier":   tier or "medium",
                "propensity_score":  pscore or 0.5,
            })
            if _ml_active and _ml_model is not None:
                try:
                    feat_rows.append(_metrics_to_row(
                        metrics,
                        client.get("industry", ""),
                        opp.opportunity_type,
                        int(client.get("account_age_days") or 365),
                    ))
                    feat_indices.append(idx)
                except Exception:
                    pass

    # ── Pass 2: batch ML inference — one predict_proba call for all rows ──────
    if feat_rows and _ml_model is not None:
        try:
            ml_probs = predict_proba_batch(feat_rows, _ml_model)
            for li, ri in enumerate(feat_indices):
                p = round(ml_probs[li], 4)
                results[ri]["ml_probability"] = p
                results[ri]["blended_score"]  = round(0.55 * p * 100 + 0.45 * results[ri]["score"], 1)
        except Exception:
            pass

    # Seasonal boosts — pure computation, no DB
    try:
        from src.agents.seasonal_engine import apply_seasonal_boosts
        results = apply_seasonal_boosts(results)
    except Exception:
        pass

    _TIER_ORDER = {"high": 0, "medium": 1, "low": 2}
    sort_key    = "blended_score" if any(r.get("ml_probability") is not None for r in results) else "score"
    results     = sorted(
        results,
        key=lambda r: (_TIER_ORDER.get(r.get("propensity_tier", "medium"), 1), -r[sort_key]),
    )

    _cache_payload    = results
    _cache_expires_at = datetime.now() + _CACHE_TTL
    return results


# ── Persistence ───────────────────────────────────────────────────────────────

def persist_opportunities(scored: list[dict]) -> int:
    """
    Upsert detected opportunities into the database.
    Invalidates the in-process cache so the next page load reflects new data.
    """
    conn     = get_connection()
    inserted = 0

    for r in scored:
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
            conn.execute(
                "UPDATE opportunities SET score = ?, updated_at = ? WHERE id = ?",
                (r["score"], datetime.now().isoformat(), existing[0]),
            )

    conn.commit()
    conn.close()
    invalidate_cache()
    return inserted
