"""
Sprint 2 — Opportunities Dashboard Page.

Shows all detected opportunities for every client, with scores, rationale,
key metric signals, and "In Production" annotations for every data source.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import streamlit as st
import pandas as pd

from src.agents.scorer import score_all_clients
from src.agents.rules import OPPORTUNITY_LABELS, SUGGESTED_PRICES
from src.data_sources.crm import get_all_clients
from src.ui.components import score_bar, production_badge


_PRODUCTION_NOTE = (
    "Production: this table is populated by the daily job (scripts/daily_job.py) "
    "which pulls metrics from Google Analytics, Meta Ads, CRM, email platform, and SEO tool APIs "
    "and applies the rules engine. The job runs every morning at 08:00 via cron."
)


@st.cache_data(ttl=60)
def _load_opportunities():
    return score_all_clients()


def render():
    st.title("Detected Opportunities")
    st.caption(
        "All clients scanned daily. Opportunities are ranked by confidence score (0–100). "
        "Each opportunity was detected by a specific combination of business rules."
    )

    production_badge(_PRODUCTION_NOTE)
    st.divider()

    results = _load_opportunities()

    if not results:
        st.info("No opportunities detected. Run `python scripts/daily_job.py` to refresh.")
        return

    # ── Filters ───────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        opp_types = ["All"] + sorted({r["opportunity_type"] for r in results})
        sel_type = st.selectbox(
            "Opportunity Type",
            opp_types,
            format_func=lambda t: "All Types" if t == "All" else OPPORTUNITY_LABELS.get(t, t)
        )
    with col2:
        industries = ["All"] + sorted({r["industry"] for r in results})
        sel_industry = st.selectbox("Industry", industries)
    with col3:
        demo_only = st.toggle("Demo clients only", value=False)

    # ── Apply filters ─────────────────────────────────────────────────────────
    filtered = results
    if sel_type != "All":
        filtered = [r for r in filtered if r["opportunity_type"] == sel_type]
    if sel_industry != "All":
        filtered = [r for r in filtered if r["industry"] == sel_industry]
    if demo_only:
        filtered = [r for r in filtered if r.get("is_demo_scenario")]

    # ── KPI row ───────────────────────────────────────────────────────────────
    total_clients   = len({r["client_id"] for r in filtered})
    total_opps      = len(filtered)
    high_conf       = len([r for r in filtered if r["score"] >= 80])
    total_value     = sum(r["suggested_price"] for r in filtered)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Clients with Opportunities", total_clients)
    k2.metric("Total Opportunities", total_opps)
    k3.metric("High Confidence (>80)", high_conf)
    k4.metric("Pipeline Value", f"${total_value:,.0f}")
    st.divider()

    # ── View toggle ───────────────────────────────────────────────────────────
    view = st.radio("View", ["Cards", "Table"], horizontal=True, label_visibility="collapsed")

    if view == "Cards":
        _render_cards(filtered)
    else:
        _render_table(filtered)


def _render_cards(results: list[dict]) -> None:
    for r in results:
        score  = r["score"]
        label  = r["label"]
        name   = r["client_name"]
        indust = r["industry"]
        price  = r["suggested_price"]
        ratio  = r["rationale"]
        sigs   = r.get("triggered_signals", [])
        is_demo = r.get("is_demo_scenario", 0)

        with st.container(border=True):
            h_col, p_col = st.columns([4, 1])
            with h_col:
                demo_tag = " 🎯" if is_demo else ""
                st.markdown(f"**{name}**{demo_tag} &nbsp;·&nbsp; *{indust}*")
                st.markdown(f"**{label}**")
            with p_col:
                st.markdown(
                    f"<div style='text-align:right;font-family:Fraunces,Georgia,serif;"
                    f"font-size:1.5em;font-weight:300;color:#C8982A;'>${price:,.0f}</div>",
                    unsafe_allow_html=True,
                )

            score_bar(score)

            sig_tags = "  ".join(
                f"`{s.replace('_', ' ')}`" for s in sigs
            )
            st.caption(f"Signals: {sig_tags}")
            st.markdown(f"> {ratio}")

            production_badge(
                "Each signal is computed from live API data in production. "
                "CTR and bounce rate from Google Analytics · Meta Ads API. "
                "Email metrics from Mailchimp API. "
                "Days inactive from HubSpot CRM API."
            )


def _render_table(results: list[dict]) -> None:
    rows = []
    for r in results:
        rows.append({
            "Client":      r["client_name"],
            "Industry":    r["industry"],
            "Opportunity": r["label"],
            "Score":       r["score"],
            "Price ($)":   r["suggested_price"],
            "Signals":     ", ".join(r.get("triggered_signals", [])),
            "Demo":        bool(r.get("is_demo_scenario")),
        })

    df = pd.DataFrame(rows)

    st.dataframe(
        df,
        column_config={
            "Score": st.column_config.ProgressColumn(
                "Score", min_value=0, max_value=100, format="%.0f"
            ),
            "Price ($)": st.column_config.NumberColumn("Price ($)", format="$%.0f"),
            "Demo": st.column_config.CheckboxColumn("Demo"),
        },
        hide_index=True,
        use_container_width=True,
    )

    production_badge(
        "In production this table is refreshed every morning by the daily job. "
        "Data sources: Google Analytics, Meta Ads Manager, HubSpot CRM, Mailchimp, Semrush."
    )
