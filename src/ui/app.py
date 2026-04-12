"""
Sprint 5 — Streamlit Dashboard.

Main entry point for the Hidden Opportunities Agent UI.
Run with:  streamlit run src/ui/app.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

st.set_page_config(
    page_title="Hidden Opportunities Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src.ui.components import demo_banner
from src.ui.pages import opportunities, alert_feed, accuracy, proposals, pilot, ml_model, text_signals

# ── Sidebar navigation ────────────────────────────────────────────────────────
PAGES = {
    "Text Signals":  text_signals,
    "ML Model":      ml_model,
    "Pilot":         pilot,
    "Opportunities": opportunities,
    "Proposals":     proposals,
    "Alert Feed":    alert_feed,
    "Accuracy":      accuracy,
}

with st.sidebar:
    st.title("Hidden Opportunities")
    st.caption("AI Agent for Marketing Agencies")
    st.divider()
    page_name = st.radio("Navigation", list(PAGES.keys()), label_visibility="collapsed")
    st.divider()
    st.caption(
        "**Sprint 6** — Active Listener\n\n"
        "NLP pipeline extracts sentiment, churn risk, and buying signals "
        "from emails and calls. 5 new ML features improve prediction accuracy."
    )

# ── Page render ───────────────────────────────────────────────────────────────
demo_banner()
PAGES[page_name].render()
