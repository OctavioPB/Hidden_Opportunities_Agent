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

from src.ui.components import demo_banner, inject_brand_css, opb_sidebar_header
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
    opb_sidebar_header()

    st.html("""
    <div style="
      padding: 14px 20px 6px;
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-size: 9px;
      font-weight: 600;
      letter-spacing: 3px;
      text-transform: uppercase;
      color: rgba(255,255,255,.28);
    ">Navigation</div>
    """)

    # Nav items — st.button gives full CSS control; primary = active page
    for name, (icon, _) in PAGES.items():
        is_active = st.session_state.page == name
        btn_type  = "primary" if is_active else "secondary"
        label     = f"{icon}  {name}"
        if st.button(label, key=f"nav_{name}", use_container_width=True, type=btn_type):
            st.session_state.page = name
            st.rerun()

    st.divider()
    st.caption(
        "**Sprint 6** — Active Listener\n\n"
        "NLP pipeline extracts sentiment, churn risk, and buying signals "
        "from emails and calls. 5 new ML features improve prediction accuracy."
    )

# ── Page render ───────────────────────────────────────────────────────────────
demo_banner()
_, page_module = PAGES[st.session_state.page]
page_module.render()
