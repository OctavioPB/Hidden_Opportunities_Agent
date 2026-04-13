"""
Sprint 2 — Accuracy Metrics Page.

Runs the rules engine against the 10 labeled test clients and shows
precision, recall, and per-rule performance.

This page answers: "How well is the detection engine working?"
In production this would be retrained after every pilot sprint.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import json
import streamlit as st
import pandas as pd

from src.agents.rules import evaluate, OPPORTUNITY_LABELS
from src.ui.components import production_badge, score_bar


_LABELED_PATH = Path(__file__).parent.parent.parent.parent / "data" / "synthetic" / "labeled_test_dataset.json"

_PRODUCTION_NOTE = (
    "Production: after each pilot sprint, the account team labels real outcomes "
    "(opportunity accepted / rejected / ignored). This page re-runs against those labels "
    "to monitor whether the rules engine needs threshold adjustment."
)


@st.cache_data(ttl=300)
def _run_validation():
    cases = json.loads(_LABELED_PATH.read_text())
    rows = []
    tp = fp = fn = 0

    for case in cases:
        detected = {r.opportunity_type for r in evaluate(case["metrics"])}
        expected = set(case["expected_opportunities"])

        case_tp = len(detected & expected)
        case_fp = len(detected - expected)
        case_fn = len(expected - detected)

        tp += case_tp
        fp += case_fp
        fn += case_fn

        rows.append({
            "Client":    case["client_name"],
            "Expected":  ", ".join(OPPORTUNITY_LABELS.get(o, o) for o in sorted(expected)) or "—",
            "Detected":  ", ".join(OPPORTUNITY_LABELS.get(o, o) for o in sorted(detected)) or "—",
            "TP": case_tp,
            "FP": case_fp,
            "FN": case_fn,
            "Status":    "Perfect" if detected == expected else ("Extra" if case_fp > 0 else "Missed"),
        })

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return rows, {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn}


def render():
    st.title("Detection Accuracy")
    st.caption(
        "Validation against the 10 manually labeled test clients from Sprint 1. "
        "Measures how accurately the rule engine detects the right opportunities."
    )
    production_badge(_PRODUCTION_NOTE)
    st.divider()

    rows, metrics = _run_validation()

    # ── KPI row ───────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Precision", f"{metrics['precision']:.1%}",
              help="Of all detected opportunities, how many were correct?")
    k2.metric("Recall", f"{metrics['recall']:.1%}",
              help="Of all real opportunities, how many did we detect?")
    k3.metric("F1 Score", f"{metrics['f1']:.1%}",
              help="Harmonic mean of precision and recall.")
    k4.metric("Test Clients", len(rows))

    st.divider()

    # ── Score bar for recall (target >= 80%) ─────────────────────────────────
    st.markdown("**Recall vs. target (80%)**")
    score_bar(metrics["recall"] * 100, label="Target: 80%+")

    # Target line note
    if metrics["recall"] >= 0.80:
        st.success(f"Recall {metrics['recall']:.1%} — meets the Sprint 2 target of 80%.")
    else:
        st.warning(
            f"Recall {metrics['recall']:.1%} — below the Sprint 2 target of 80%. "
            "Consider lowering detection thresholds in src/agents/rules.py."
        )

    st.divider()

    # ── Per-client breakdown ──────────────────────────────────────────────────
    st.markdown("**Per-client results**")

    df = pd.DataFrame(rows)

    def _style_status(val):
        if val == "Perfect":
            return "background-color: #E0F7EF; color: #0D5C3A; font-weight: 600;"
        if val == "Extra":
            return "background-color: #FEF0E6; color: #7A3800;"
        return "background-color: #FDEAEA; color: #7A1020;"

    st.dataframe(
        df.style.map(_style_status, subset=["Status"]),
        hide_index=True,
        use_container_width=True,
    )

    st.divider()

    # ── Confusion summary ─────────────────────────────────────────────────────
    st.markdown("**Confusion summary**")
    cs_col1, cs_col2 = st.columns(2)

    with cs_col1:
        st.markdown(f"""
        | | |
        |---|---|
        | **True Positives** | {metrics['tp']} — correctly detected |
        | **False Positives** | {metrics['fp']} — detected but shouldn't have |
        | **False Negatives** | {metrics['fn']} — missed real opportunities |
        """)

    with cs_col2:
        st.info(
            "**Tuning guide:**\n\n"
            "- Too many FP → raise thresholds in `rules.py` (e.g., `ctr_high` from 4% to 5%).\n"
            "- Too many FN → lower thresholds or add new rules.\n"
            "- In Sprint 5 this tuning is replaced by the ML model."
        )

    production_badge(_PRODUCTION_NOTE)
