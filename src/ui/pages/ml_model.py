"""
Sprint 5 — ML Model Dashboard.

Shows the ML model, don't just use it (per the demo architecture directive).

Sections
--------
  1. Model Card      — training metadata, AUC-ROC, precision/recall/F1,
                       training history chart.
  2. Feature Importance — horizontal bar chart (plotly), annotated with
                          what each feature means for opportunity detection.
  3. Predictions Table — all clients with rule_score | ml_probability |
                         blended_score columns.
  4. Why This Opportunity? — per-row SHAP explanation panel.
  5. Retrain Button  — triggers train_model.run() and refreshes the page.

"In Production" annotations explain every integration point.
"""

from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from src.ml.model import load_metadata, load_training_history, model_is_trained
from src.ml.explainer import get_feature_importance, explain_single, FEATURE_LABELS
from src.ml.inference import predict_for_all, get_inference_summary
from src.ml.dataset import FEATURE_NAMES, _metrics_to_row
from src.agents.rules import OPPORTUNITY_LABELS
from src.ui.components import production_badge, score_bar


# ── Retrain helper ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=5)
def _cached_metadata():
    return load_metadata()


@st.cache_data(ttl=60)
def _cached_predictions():
    return predict_for_all()


def _run_training() -> dict | None:
    try:
        from scripts.train_model import run as train_run
        with st.spinner("Training model… this takes 10–30 seconds."):
            result = train_run(augment=True, cv_folds=5, verbose=False)
        st.cache_data.clear()
        return result
    except Exception as e:
        st.error(f"Training failed: {e}")
        return None


# ── Model card ────────────────────────────────────────────────────────────────

def _render_model_card(meta: dict) -> None:
    st.subheader("Model Card")

    m = meta["metrics"]
    trained_at = meta.get("trained_at", "")[:16].replace("T", " ")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("AUC-ROC",   f"{m['auc_roc']:.4f}",
                help="Area Under ROC Curve. 1.0 = perfect. 0.5 = random.")
    col2.metric("Avg Precision", f"{m['avg_precision']:.4f}",
                help="Area under Precision-Recall curve. More relevant for imbalanced data.")
    col3.metric("Precision",  f"{m['precision']:.4f}",
                help="Of all predicted positives, how many were actually positive.")
    col4.metric("Recall",     f"{m['recall']:.4f}",
                help="Of all true positives, how many did the model catch.")
    col5.metric("F1 Score",   f"{m['f1']:.4f}",
                help="Harmonic mean of precision and recall.")

    st.caption(
        f"Trained: **{trained_at}** · "
        f"Samples: **{meta['n_samples']:,}** · "
        f"Features: **{meta['n_features']}** · "
        f"CV folds: **{meta['cv_folds']}** · "
        f"Algorithm: **RandomForestClassifier**"
    )

    production_badge(
        "Production: Model artifact stored as data/models/rf_model.joblib. "
        "In production it's uploaded to S3 (versioned) after each nightly retrain. "
        "AUC-ROC target: ≥ 0.80. If below threshold, retrain is flagged for human review. "
        "Model is a RandomForestClassifier (200 trees, balanced class weights, max_depth=8)."
    )


def _render_training_history() -> None:
    history = load_training_history()
    if len(history) < 2:
        return

    st.subheader("Training History")
    df = pd.DataFrame(history)
    df["trained_at"] = pd.to_datetime(df["trained_at"])
    df = df.sort_values("trained_at")

    metrics_df = pd.json_normalize(df["metrics"])
    for col in ["auc_roc", "f1", "precision", "recall"]:
        if col in metrics_df.columns:
            metrics_df[col] = metrics_df[col].astype(float)

    metrics_df["trained_at"] = df["trained_at"].values
    metrics_df["n_samples"]  = df["n_samples"].values

    fig = go.Figure()
    colors = {"auc_roc": "#36C5F0", "f1": "#2EB67D", "precision": "#ECB22E", "recall": "#E01E5A"}
    for metric, color in colors.items():
        if metric in metrics_df.columns:
            fig.add_trace(go.Scatter(
                x=metrics_df["trained_at"], y=metrics_df[metric],
                name=metric.upper().replace("_", "-"),
                line=dict(color=color, width=2),
                mode="lines+markers",
            ))

    fig.update_layout(
        title="Model Metrics Over Retraining Runs",
        xaxis_title="Training Date",
        yaxis_title="Score",
        yaxis_range=[0, 1],
        template="plotly_dark",
        height=250,
        margin=dict(t=40, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)

    production_badge(
        "Production: Training history is stored in data/models/training_history.jsonl. "
        "Each entry records timestamp, sample count, and all CV metrics. "
        "A drop in AUC-ROC > 0.05 triggers a Slack alert to the ML team."
    )


# ── Feature importance ────────────────────────────────────────────────────────

def _render_feature_importance() -> None:
    st.subheader("Feature Importance")
    st.caption(
        "Global feature importance from the RandomForest model. "
        "Higher importance = more influence on the acceptance probability prediction."
    )

    importance = get_feature_importance()
    if not importance:
        st.info("Train the model first to see feature importance.")
        return

    labels  = [f["label"] for f in importance]
    values  = [f["importance"] for f in importance]
    colors  = [
        "#2EB67D" if v >= max(values) * 0.6 else
        "#ECB22E" if v >= max(values) * 0.3 else "#888"
        for v in values
    ]

    fig = go.Figure(go.Bar(
        x=values[::-1],
        y=labels[::-1],
        orientation="h",
        marker_color=colors[::-1],
        text=[f"{v:.4f}" for v in values[::-1]],
        textposition="outside",
    ))
    fig.update_layout(
        xaxis_title="Importance Score",
        template="plotly_dark",
        height=380,
        margin=dict(t=10, b=20, l=160),
        xaxis=dict(range=[0, max(values) * 1.25]),
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("What does each feature mean?", icon="ℹ️"):
        from src.ml.explainer import FEATURE_DIRECTIONS
        rows = []
        for f in importance:
            rows.append({
                "Feature":     f["label"],
                "Importance":  f"{f['importance']:.4f}",
                "Direction":   FEATURE_DIRECTIONS.get(f["name"], ""),
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    production_badge(
        "Production: Feature importance is extracted from sklearn's "
        "RandomForestClassifier.feature_importances_ (mean decrease in impurity). "
        "For more granular attribution, SHAP TreeExplainer values are computed "
        "nightly and stored per-opportunity in the DB."
    )


# ── Predictions table ─────────────────────────────────────────────────────────

def _render_predictions_table(predictions: list[dict]) -> None:
    st.subheader("ML Predictions — All Clients")
    st.caption(
        "Rule score (heuristic) vs. ML probability (model) vs. blended score "
        "(0.55 × ML + 0.45 × rule). Click a row to see the SHAP explanation."
    )

    if not predictions:
        st.info("No predictions available. Train the model and run the daily job.")
        return

    rows = []
    for p in predictions:
        ml_pct = f"{p['ml_probability']:.0%}" if p["ml_probability"] is not None else "—"
        rows.append({
            "Client":       p["client_name"],
            "Industry":     p["industry"],
            "Opportunity":  OPPORTUNITY_LABELS.get(p["opportunity_type"], p["opportunity_type"]),
            "Rule Score":   p["rule_score"],
            "ML Prob":      ml_pct,
            "Blended":      p["blended_score"],
            "Price ($)":    p.get("suggested_price", 0),
            "Demo":         bool(p.get("is_demo_scenario")),
            "_opp_type":    p["opportunity_type"],
            "_client_id":   p["client_id"],
        })

    df = pd.DataFrame(rows)
    display_df = df.drop(columns=["_opp_type", "_client_id"])

    st.dataframe(
        display_df,
        column_config={
            "Rule Score": st.column_config.ProgressColumn(
                "Rule Score", min_value=0, max_value=100, format="%.0f"
            ),
            "Blended": st.column_config.ProgressColumn(
                "Blended Score", min_value=0, max_value=100, format="%.1f"
            ),
            "Price ($)": st.column_config.NumberColumn("Price ($)", format="$%.0f"),
            "Demo":      st.column_config.CheckboxColumn("Demo"),
        },
        hide_index=True,
        use_container_width=True,
    )

    production_badge(
        "Production: ML probabilities are written back to opportunities.ml_probability "
        "in the DB after each daily inference run. The blended score drives "
        "opportunity ranking and proposal generation thresholds."
    )

    return df


# ── SHAP explanation panel ────────────────────────────────────────────────────

def _render_why_panel(predictions: list[dict]) -> None:
    st.subheader("Why This Opportunity?")
    st.caption(
        "Select a client-opportunity pair to see which features most influenced "
        "the ML model's acceptance probability estimate."
    )

    if not predictions:
        return

    options = {
        f"{p['client_name']} — {OPPORTUNITY_LABELS.get(p['opportunity_type'], p['opportunity_type'])}": p
        for p in predictions[:20]   # top 20 for the selector
    }
    sel_label = st.selectbox("Select opportunity to explain", list(options.keys()))
    sel_pred  = options[sel_label]

    explanation = sel_pred.get("explanation")

    if explanation is None:
        st.info("Run inference after training the model to see explanations.")
        return

    # ── Narrative ─────────────────────────────────────────────────────────────
    prob = explanation.get("probability", 0)
    st.html(
        f'<div style="background:#1a1d21;border-radius:6px;padding:14px 18px;'
        f'border-left:4px solid {"#2EB67D" if prob >= 0.7 else "#ECB22E" if prob >= 0.5 else "#E01E5A"};">'
        f'<div style="color:#d1d2d3;font-size:1em;">{explanation.get("narrative","")}</div>'
        f'</div>'
    )

    # ── SHAP waterfall bar chart ──────────────────────────────────────────────
    top_features = explanation.get("top_features", [])
    if top_features:
        names   = [f["label"] for f in top_features]
        shap_vs = [f["shap_value"] for f in top_features]
        values  = [f["value"] for f in top_features]
        colors  = ["#2EB67D" if sv > 0 else "#E01E5A" for sv in shap_vs]

        fig = go.Figure(go.Bar(
            x=shap_vs[::-1],
            y=names[::-1],
            orientation="h",
            marker_color=colors[::-1],
            text=[f"{sv:+.3f} (value: {v:.3g})" for sv, v in zip(shap_vs[::-1], values[::-1])],
            textposition="outside",
        ))
        fig.add_vline(x=0, line_color="#555", line_width=1)
        fig.update_layout(
            title=f"SHAP Feature Contributions — Acceptance Probability: {prob:.0%}",
            xaxis_title="SHAP value (impact on model output)",
            template="plotly_dark",
            height=300,
            margin=dict(t=40, b=20, l=160),
        )
        st.plotly_chart(fig, use_container_width=True)

        if not explanation.get("shap_available"):
            st.caption(
                "SHAP library not available — showing feature importance as proxy. "
                "Install shap: `pip install shap`"
            )

    production_badge(
        "Production: SHAP values are computed using shap.TreeExplainer (exact Shapley values "
        "for RandomForest). Each explanation is stored as JSON in opportunities.ml_explanation. "
        "Account managers see the top-3 factors in plain English in the Slack notification."
    )


# ── Main render ────────────────────────────────────────────────────────────────

def render() -> None:
    st.title("ML Model — Predictive Analyst")
    st.caption(
        "Sprint 5: the agent learns from historical proposal outcomes and predicts "
        "which clients are most likely to accept an upsell offer. "
        "Rule-based scores are blended with ML probabilities for a more accurate ranking."
    )

    production_badge(
        "Sprint 5 — RandomForestClassifier trained on real feedback + synthetic data. "
        "SHAP explanations provide interpretability. "
        "The model replaces (and keeps as fallback) the heuristic rules from Sprint 2. "
        "In production: retrained nightly, versioned in S3, monitored for drift."
    )

    st.divider()

    # ── Retrain panel ──────────────────────────────────────────────────────────
    with st.container(border=True):
        rc1, rc2 = st.columns([4, 1])
        with rc1:
            if model_is_trained():
                meta = _cached_metadata()
                trained_at = (meta or {}).get("trained_at", "")[:16].replace("T", " ")
                st.markdown(f"Model trained at **{trained_at}**. Click to retrain on latest data.")
            else:
                st.markdown("**No model trained yet.** Click to train on the current dataset.")
        with rc2:
            if st.button("Retrain Model", type="primary", use_container_width=True):
                result = _run_training()
                if result:
                    st.success(
                        f"Model retrained! AUC-ROC: {result['metrics']['auc_roc']:.4f} "
                        f"on {result['n_samples']:,} samples."
                    )
                st.rerun()

        production_badge(
            "Production: Retraining is triggered automatically when ≥ 10 new feedback "
            "rows exist since the last training run. Manual retrain is available here "
            "for immediate updates after a large batch of proposals is accepted/rejected."
        )

    st.divider()

    if not model_is_trained():
        st.info(
            "No trained model found. Click **Retrain Model** above to train the "
            "RandomForest on the current dataset (takes 10–30 seconds)."
        )
        return

    # ── Load data ──────────────────────────────────────────────────────────────
    meta        = _cached_metadata()
    predictions = _cached_predictions()
    summary     = get_inference_summary()

    # ── KPI row ────────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("AUC-ROC", f"{meta['metrics']['auc_roc']:.4f}" if meta else "—")
    k2.metric("Predictions Run", summary["total_predictions"])
    k3.metric("High Probability (≥70%)", summary["high_prob_count"])
    k4.metric("Avg ML Probability",
              f"{summary['avg_ml_probability']:.0%}" if summary["avg_ml_probability"] else "—")

    st.divider()

    # ── Tabs ───────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "Model Card", "Feature Importance", "Predictions", "Why This Opportunity?"
    ])

    with tab1:
        if meta:
            _render_model_card(meta)
            _render_training_history()
        else:
            st.info("No metadata found.")

    with tab2:
        _render_feature_importance()

    with tab3:
        _render_predictions_table(predictions)

    with tab4:
        _render_why_panel(predictions)
