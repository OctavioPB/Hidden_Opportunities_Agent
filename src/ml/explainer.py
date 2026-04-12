"""
Sprint 5 — SHAP Explainability Layer.

Provides:
  1. Per-prediction natural-language explanation:
     "This opportunity has 78% acceptance probability because the CTR is high
      (+12 pts) and the client is highly inactive (+8 pts), offset by a low
      ROAS (−5 pts)."

  2. Global feature importance (from the RF model's .feature_importances_).

  3. SHAP values for the full dataset (used to render the beeswarm / bar chart
     in the UI).

SHAP is computed using shap.TreeExplainer which gives exact Shapley values
for tree-based models in O(TLD) time — fast enough to run per-request in demo.

In production
-------------
  SHAP values are pre-computed nightly and stored in the DB as a JSON column
  in the `opportunities` table so the dashboard loads instantly.
  Re-computed any time the model is retrained.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from src.ml.dataset import FEATURE_NAMES
from src.ml.model import load_model, load_metadata

# Human-friendly feature labels for the UI
FEATURE_LABELS = {
    "ctr":               "Click-Through Rate",
    "bounce_rate":       "Bounce Rate",
    "pages_per_session": "Pages per Session",
    "conversion_rate":   "Conversion Rate",
    "organic_traffic":   "Organic Traffic",
    "roas":              "ROAS",
    "ad_spend_monthly":  "Monthly Ad Spend",
    "email_open_rate":   "Email Open Rate",
    "keyword_rankings":  "Keyword Rankings",
    "days_inactive":     "Days Inactive",
    "account_age_days":  "Account Age (days)",
    "industry_code":     "Industry",
    "opportunity_type_code": "Opportunity Type",
}

# Direction hint: which direction of this feature increases acceptance
FEATURE_DIRECTIONS = {
    "ctr":               "higher → better",
    "bounce_rate":       "lower → better",
    "pages_per_session": "higher → better",
    "conversion_rate":   "lower means gap → opportunity",
    "organic_traffic":   "higher with low conversion → opportunity",
    "roas":              "context-dependent",
    "ad_spend_monthly":  "higher → retargeting/upsell opportunity",
    "email_open_rate":   "lower → automation opportunity",
    "keyword_rankings":  "lower count → SEO gap",
    "days_inactive":     "higher → reactivation opportunity",
    "account_age_days":  "longer → established relationship",
    "industry_code":     "categorical",
    "opportunity_type_code": "categorical",
}


# ── SHAP computation ──────────────────────────────────────────────────────────

def get_shap_values(
    X: list[list[float]],
    model=None,
) -> tuple[np.ndarray, np.ndarray] | None:
    """
    Compute SHAP values for a feature matrix X.

    Returns (shap_values_class1, base_values) or None if SHAP is unavailable.
    shap_values_class1 has shape (n_samples, n_features).
    """
    try:
        import shap
    except ImportError:
        return None

    if model is None:
        model = load_model()
    if model is None:
        return None

    Xarr     = np.array(X, dtype=float)
    explainer = shap.TreeExplainer(model)
    sv        = explainer.shap_values(Xarr)

    # For binary classification RF, shap_values is a list [class0_sv, class1_sv]
    if isinstance(sv, list):
        sv_class1  = sv[1]
        base_value = float(explainer.expected_value[1])
    else:
        sv_class1  = sv
        base_value = float(explainer.expected_value)

    return sv_class1, np.full(sv_class1.shape[0], base_value)


def explain_single(
    feature_row: list[float],
    model=None,
    top_n: int = 5,
) -> dict[str, Any]:
    """
    Generate a natural-language explanation for a single prediction.

    Returns a dict with:
      - probability: float (0–1)
      - top_features: list of {name, label, shap_value, direction, value}
      - narrative: str — human-readable sentence
      - shap_available: bool
    """
    if model is None:
        model = load_model()

    from src.ml.model import predict_proba
    prob = predict_proba(feature_row, model)

    shap_result = get_shap_values([feature_row], model)

    if shap_result is None:
        # Fallback: use feature importance rank as proxy explanation
        return _fallback_explanation(feature_row, prob, top_n)

    sv_row = shap_result[0][0]   # shape: (n_features,)

    # Sort features by absolute SHAP value
    ranked = sorted(
        zip(FEATURE_NAMES, sv_row, feature_row),
        key=lambda t: abs(t[1]),
        reverse=True,
    )[:top_n]

    top_features = [
        {
            "name":      name,
            "label":     FEATURE_LABELS.get(name, name),
            "shap_value": round(float(sv), 4),
            "value":     round(float(val), 4),
            "direction": FEATURE_DIRECTIONS.get(name, ""),
            "positive":  float(sv) > 0,
        }
        for name, sv, val in ranked
    ]

    narrative = _build_narrative(prob, top_features)

    return {
        "probability":    round(prob, 4),
        "top_features":   top_features,
        "narrative":      narrative,
        "shap_available": True,
    }


def _fallback_explanation(
    feature_row: list[float],
    prob: float,
    top_n: int,
) -> dict[str, Any]:
    """Use feature importance as a proxy when SHAP is unavailable."""
    meta = load_metadata()
    if meta and "feature_importance" in meta:
        importance = meta["feature_importance"]
        ranked = sorted(importance.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
        top_features = [
            {
                "name":       name,
                "label":      FEATURE_LABELS.get(name, name),
                "shap_value": round(imp, 4),
                "value":      round(feature_row[FEATURE_NAMES.index(name)], 4) if name in FEATURE_NAMES else 0.0,
                "direction":  FEATURE_DIRECTIONS.get(name, ""),
                "positive":   True,
            }
            for name, imp in ranked
        ]
    else:
        top_features = []

    return {
        "probability":    round(prob, 4),
        "top_features":   top_features,
        "narrative":      f"Acceptance probability: {prob:.0%} (based on feature importance).",
        "shap_available": False,
    }


def _build_narrative(prob: float, top_features: list[dict]) -> str:
    """Build a natural-language sentence from top SHAP features."""
    if not top_features:
        return f"Acceptance probability: {prob:.0%}."

    pos = [f for f in top_features if f["positive"]]
    neg = [f for f in top_features if not f["positive"]]

    reasons_pos = ", ".join(f['label'] for f in pos[:3])
    reasons_neg = ", ".join(f['label'] for f in neg[:2])

    narrative = f"Acceptance probability: {prob:.0%}."
    if pos:
        narrative += f" Strong signals: {reasons_pos}."
    if neg:
        narrative += f" Risk factors: {reasons_neg}."
    return narrative


# ── Global feature importance ─────────────────────────────────────────────────

def get_feature_importance() -> list[dict] | None:
    """
    Return global feature importance from the trained model metadata.
    Sorted descending by importance.
    """
    meta = load_metadata()
    if meta is None:
        return None

    importance = meta.get("feature_importance", {})
    return sorted(
        [
            {
                "name":      name,
                "label":     FEATURE_LABELS.get(name, name),
                "importance": imp,
            }
            for name, imp in importance.items()
        ],
        key=lambda d: d["importance"],
        reverse=True,
    )
