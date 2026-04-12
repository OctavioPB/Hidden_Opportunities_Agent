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
from src.ui.pages import opportunities, alert_feed, accuracy, proposals

# ── Sidebar navigation ────────────────────────────────────────────────────────
PAGES = {
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
        "**Sprint 3** — Proposal Generator\n\n"
        "The agent writes personalized commercial proposals "
        "and queues them for human review and approval "
        "before sending to clients."
    )

# ── Page render ───────────────────────────────────────────────────────────────
demo_banner()
PAGES[page_name].render()
