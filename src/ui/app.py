"""
Hidden Opportunities Agent — Streamlit Dashboard.

Main entry point for the OPB brand UI.
Run with:  streamlit run src/ui/app.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

st.set_page_config(
    page_title="OPB · Hidden Opportunities",
    page_icon="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='6' fill='%23003366'/><text x='16' y='22' text-anchor='middle' font-size='18' font-family='Georgia,serif' fill='%23C8982A' font-style='italic'>O</text></svg>",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src.db.schema import init_db, migrate_db
from src.ui.components import inject_brand_css, opb_sidebar_header, nav_group_label
from src.ui.views import opportunities, alert_feed, accuracy, proposals, pilot, ml_model, text_signals, negotiation

# ── Ensure DB schema is up-to-date (safe to call on every reload) ─────────────
init_db()
migrate_db()

# ── Inject OPB brand design system ────────────────────────────────────────────
inject_brand_css()

# ── Pages registry: (label, module, group) ────────────────────────────────────
# Groups: "DEAL PIPELINE" | "INTELLIGENCE" | "ANALYTICS"
PAGES = {
    "Negotiation":   ("Negotiation",   negotiation,    "DEAL PIPELINE"),
    "Proposals":     ("Proposals",     proposals,      "DEAL PIPELINE"),
    "Pilot":         ("Pilot Demo",    pilot,          "DEAL PIPELINE"),
    "Opportunities": ("Opportunities", opportunities,  "INTELLIGENCE"),
    "Text Signals":  ("Text Signals",  text_signals,   "INTELLIGENCE"),
    "ML Model":      ("ML Model",      ml_model,       "INTELLIGENCE"),
    "Alert Feed":    ("Alert Feed",    alert_feed,     "ANALYTICS"),
    "Accuracy":      ("Accuracy",      accuracy,       "ANALYTICS"),
}

# Persist active page across reruns
if "page" not in st.session_state:
    st.session_state.page = "Negotiation"

# ── Sidebar navigation ────────────────────────────────────────────────────────
with st.sidebar:
    opb_sidebar_header()

    # Render nav items, injecting group labels on group change
    last_group = None
    for key, (label, _, group) in PAGES.items():
        if group != last_group:
            nav_group_label(group)
            last_group = group
        is_active = st.session_state.page == key
        if st.button(
            label,
            key=f"nav_{key}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state.page = key
            st.rerun()

    # Sprint version footer
    st.html("""
    <div style="
      position: absolute;
      bottom: 0; left: 0; right: 0;
      padding: 14px 20px;
      border-top: 1px solid rgba(255,255,255,.06);
      background: #003366;
    ">
      <div style="
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 10px; letter-spacing: 1.8px;
        text-transform: uppercase;
        color: rgba(255,255,255,.25);
      ">Sprint 7 · v0.7.0</div>
      <div style="
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 10px; color: rgba(255,255,255,.15);
        margin-top: 2px;
      ">All data synthetic · Demo mode</div>
    </div>
    """)

# ── Page render ───────────────────────────────────────────────────────────────
_, page_module, _ = PAGES[st.session_state.page]
page_module.render()
