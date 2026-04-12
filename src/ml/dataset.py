"""
Sprint 5 — Training Dataset Builder.

Assembles a labeled feature matrix for training the opportunity acceptance
prediction model.

Feature vector (13 columns)
----------------------------
  ctr, bounce_rate, pages_per_session, conversion_rate, organic_traffic,
  roas, ad_spend_monthly, email_open_rate, keyword_rankings, days_inactive,
  account_age_days, industry_code, opportunity_type_code

Target
------
  accepted = 1 (client bought the upsell)
  accepted = 0 (rejected, ignored, too_expensive, or escalated)

Data sources (in priority order)
---------------------------------
  1. Real feedback_log rows from the DB (Sprint 4 outcomes).
  2. Synthetic augmentation from labeled_test_dataset.json (Sprint 1).
  3. Programmatically generated rows from the synthetic client corpus so the
     training set always has ≥ MIN_SAMPLES rows regardless of real data.

In production
-------------
  Only sources 1 is used once the system has been running for 4+ weeks.
  Sources 2–3 act as warm-start priors until real data accumulates.
  Each accepted proposal automatically adds a new row during the daily job.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np

import config
from src.db.schema import get_connection
from src.agents.rules import (
    ALL_OPPORTUNITY_TYPES, SUGGESTED_PRICES,
    LANDING_PAGE_OPTIMIZATION, SEO_CONTENT, RETARGETING_CAMPAIGN,
    EMAIL_AUTOMATION, REACTIVATION, CONVERSION_RATE_AUDIT, UPSELL_AD_BUDGET,
)
from src.synthetic.generator import INDUSTRIES

# ── Constants ─────────────────────────────────────────────────────────────────
MIN_SAMPLES      = 150    # minimum rows before training is allowed
AUGMENT_FACTOR   = 3      # copies of each labeled row with added noise
RANDOM_SEED      = config.SYNTHETIC_SEED

FEATURE_NAMES = [
    "ctr",
    "bounce_rate",
    "pages_per_session",
    "conversion_rate",
    "organic_traffic",
    "roas",
    "ad_spend_monthly",
    "email_open_rate",
    "keyword_rankings",
    "days_inactive",
    "account_age_days",
    "industry_code",
    "opportunity_type_code",
]

# Deterministic encodings (stable across runs)
INDUSTRY_CODES = {ind: i for i, ind in enumerate(sorted(INDUSTRIES))}
OPP_TYPE_CODES  = {ot: i for i, ot in enumerate(ALL_OPPORTUNITY_TYPES)}


# ── Feature extraction ────────────────────────────────────────────────────────

def _metrics_to_row(
    metrics: dict,
    industry: str,
    opportunity_type: str,
    account_age_days: int = 365,
) -> list[float]:
    """Convert a metrics dict into a fixed-length feature vector."""
    ad_spend_daily   = metrics.get("ad_spend", 0) or 0
    ad_spend_monthly = ad_spend_daily * 30

    return [
        float(metrics.get("ctr",               0) or 0),
        float(metrics.get("bounce_rate",        0) or 0),
        float(metrics.get("pages_per_session",  1) or 1),
        float(metrics.get("conversion_rate",    0) or 0),
        float(metrics.get("organic_traffic",    0) or 0),
        float(metrics.get("roas",               0) or 0),
        float(ad_spend_monthly),
        float(metrics.get("email_open_rate",    0) or 0),
        float(metrics.get("keyword_rankings",   0) or 0),
        float(metrics.get("days_inactive",      0) or 0),
        float(account_age_days),
        float(INDUSTRY_CODES.get(industry, 0)),
        float(OPP_TYPE_CODES.get(opportunity_type, 0)),
    ]


def _add_noise(row: list[float], rng: np.random.Generator) -> list[float]:
    """Add ±10% Gaussian noise to numeric features (not encodings)."""
    result = []
    for i, v in enumerate(row):
        if i < 11:   # numeric features only (not industry_code, opp_type_code)
            noise = float(rng.normal(1.0, 0.08))
            result.append(max(0.0, v * noise))
        else:
            result.append(v)
    return result


# ── Real data from DB ─────────────────────────────────────────────────────────

def _load_real_data() -> tuple[list[list[float]], list[int]]:
    """
    Pull accepted/rejected proposals from the DB and join with client metrics.
    Returns (X, y).
    """
    X, y = [], []
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT
            fl.outcome,
            p.client_id,
            o.opportunity_type,
            c.account_age_days,
            c.industry,
            cm.ctr, cm.bounce_rate, cm.pages_per_session, cm.conversion_rate,
            cm.organic_traffic, cm.roas, cm.ad_spend,
            cm.email_open_rate, cm.keyword_rankings, cm.days_inactive
        FROM feedback_log fl
        JOIN proposals     p  ON p.id = fl.proposal_id
        JOIN opportunities o  ON o.id = p.opportunity_id
        JOIN clients       c  ON c.id = p.client_id
        LEFT JOIN (
            SELECT client_id, ctr, bounce_rate, pages_per_session,
                   conversion_rate, organic_traffic, roas, ad_spend,
                   email_open_rate, keyword_rankings, days_inactive
            FROM client_metrics
            WHERE (client_id, date) IN (
                SELECT client_id, MAX(date) FROM client_metrics GROUP BY client_id
            )
        ) cm ON cm.client_id = p.client_id
        WHERE fl.outcome IN ('accepted','rejected','too_expensive','ignored','escalated')
        """
    ).fetchall()
    conn.close()

    for row in rows:
        r = dict(row)
        metrics = {
            "ctr":              r.get("ctr"),
            "bounce_rate":      r.get("bounce_rate"),
            "pages_per_session": r.get("pages_per_session"),
            "conversion_rate":  r.get("conversion_rate"),
            "organic_traffic":  r.get("organic_traffic"),
            "roas":             r.get("roas"),
            "ad_spend":         r.get("ad_spend"),
            "email_open_rate":  r.get("email_open_rate"),
            "keyword_rankings": r.get("keyword_rankings"),
            "days_inactive":    r.get("days_inactive"),
        }
        label = 1 if r["outcome"] == "accepted" else 0
        feature_row = _metrics_to_row(
            metrics,
            r.get("industry", ""),
            r.get("opportunity_type", ""),
            int(r.get("account_age_days") or 365),
        )
        X.append(feature_row)
        y.append(label)

    return X, y


# ── Synthetic augmentation ────────────────────────────────────────────────────

def _load_labeled_dataset() -> tuple[list[list[float]], list[int]]:
    """
    Load the Sprint 1 labeled test dataset and convert to feature vectors.
    Each case has metrics + expected_opportunities; treat expected as accepted (1),
    and all opportunity types NOT expected as rejected (0).
    """
    labeled_path = config.SYNTHETIC_DIR / "labeled_test_dataset.json"
    if not labeled_path.exists():
        return [], []

    cases  = json.loads(labeled_path.read_text())
    X, y   = [], []

    for case in cases:
        metrics  = case.get("metrics", {})
        expected = set(case.get("expected_opportunities", []))
        industry = case.get("industry", "Restaurant")
        age      = case.get("account_age_days", 365)

        for opp_type in ALL_OPPORTUNITY_TYPES:
            label = 1 if opp_type in expected else 0
            X.append(_metrics_to_row(metrics, industry, opp_type, age))
            y.append(label)

    return X, y


def _generate_synthetic_rows(
    n: int = 300,
    rng: np.random.Generator | None = None,
) -> tuple[list[list[float]], list[int]]:
    """
    Generate synthetic training rows using the rule engine as a noisy oracle.
    Rule fires → label=1 with 80% probability (20% noise for realism).
    Rule does not fire → label=0 with 90% probability.
    """
    from src.agents.rules import evaluate
    from src.synthetic.generator import (
        _generate_client, _generate_metrics_history, INDUSTRIES, INDUSTRY_PROFILES,
    )
    import random as _rnd

    if rng is None:
        rng = np.random.default_rng(RANDOM_SEED)

    _rnd.seed(RANDOM_SEED)

    X, y = [], []
    for _ in range(n):
        industry = _rnd.choice(INDUSTRIES)
        client   = _generate_client(str(id(_)), industry=industry)
        history  = _generate_metrics_history(client, days=1)
        if not history:
            continue

        m = history[0]
        detected_types = {r.opportunity_type for r in evaluate(m)}

        for opp_type in ALL_OPPORTUNITY_TYPES:
            fired = opp_type in detected_types
            # Noisy oracle: rule=True → label 1 with p=0.80
            if fired:
                label = 1 if rng.random() < 0.80 else 0
            else:
                label = 1 if rng.random() < 0.10 else 0   # 10% false negatives

            X.append(_metrics_to_row(
                m, industry, opp_type,
                int(client.get("account_age_days", 365)),
            ))
            y.append(label)

    return X, y


# ── Main builder ──────────────────────────────────────────────────────────────

def build_dataset(
    augment: bool = True,
    verbose: bool = True,
) -> tuple[list[list[float]], list[int], list[str]]:
    """
    Build the full training dataset.

    Returns
    -------
    X : list[list[float]]   — feature matrix
    y : list[int]           — labels (0 or 1)
    feature_names : list[str]
    """
    rng = np.random.default_rng(RANDOM_SEED)

    # Source 1: real DB feedback
    X_real, y_real = _load_real_data()
    if verbose:
        print(f"[dataset] Real DB rows: {len(X_real)}")

    # Source 2: labeled test dataset
    X_lab, y_lab = _load_labeled_dataset()
    if verbose:
        print(f"[dataset] Labeled dataset rows: {len(X_lab)}")

    # Source 3: programmatic synthetic rows (always included as warm-start)
    X_syn, y_syn = _generate_synthetic_rows(n=300, rng=rng)
    if verbose:
        print(f"[dataset] Synthetic rows: {len(X_syn)}")

    # Merge
    X = X_real + X_lab + X_syn
    y = y_real + y_lab + y_syn

    # Augment with noise copies of labeled + real data
    if augment and (X_real or X_lab):
        X_aug, y_aug = [], []
        for row, label in zip(X_real + X_lab, y_real + y_lab):
            for _ in range(AUGMENT_FACTOR):
                X_aug.append(_add_noise(row, rng))
                y_aug.append(label)
        X += X_aug
        y += y_aug
        if verbose:
            print(f"[dataset] After augmentation: {len(X)} total rows")

    if verbose:
        pos = sum(y)
        neg = len(y) - pos
        print(f"[dataset] Class balance: {pos} positive ({pos/len(y):.0%}), {neg} negative")

    return X, y, FEATURE_NAMES
