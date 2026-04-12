"""
Sprint 2 — Streamlit Dashboard.

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
from src.ui.pages import opportunities, alert_feed, accuracy

# ── Sidebar navigation ────────────────────────────────────────────────────────
PAGES = {
    "Opportunities": opportunities,
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
        "**Sprint 2** — Detection Engine & Alerts\n\n"
        "The agent observes client metrics daily, "
        "detects upsell opportunities using business rules, "
        "and sends internal alerts to the team."
    )

# ── Page render ───────────────────────────────────────────────────────────────
demo_banner()
PAGES[page_name].render()
