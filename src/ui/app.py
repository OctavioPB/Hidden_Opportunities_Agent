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

from src.ui.components import demo_banner, inject_brand_css
from src.ui.views import opportunities, alert_feed, accuracy, proposals, pilot, ml_model, text_signals

# ── Inject OPB brand design system ────────────────────────────────────────────
inject_brand_css()

# ── Pages registry: (icon, module) ───────────────────────────────────────────
PAGES = {
    "Text Signals":  ("📡", text_signals),
    "ML Model":      ("🤖", ml_model),
    "Pilot":         ("🧪", pilot),
    "Opportunities": ("💡", opportunities),
    "Proposals":     ("📋", proposals),
    "Alert Feed":    ("🔔", alert_feed),
    "Accuracy":      ("🎯", accuracy),
}

# Persist active page across reruns
if "page" not in st.session_state:
    st.session_state.page = "Text Signals"

# ── Sidebar navigation ────────────────────────────────────────────────────────
with st.sidebar:
    st.html('<div style="height:12px;"></div>')

    for name, (icon, _) in PAGES.items():
        is_active = st.session_state.page == name
        if st.button(
            f"{icon}  {name}",
            key=f"nav_{name}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state.page = name
            st.rerun()

# ── Page render ───────────────────────────────────────────────────────────────
demo_banner()
_, page_module = PAGES[st.session_state.page]
page_module.render()
