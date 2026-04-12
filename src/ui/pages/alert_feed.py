"""
Sprint 2 — Alert Feed Page.

Simulates the Slack/Telegram channel where the agent posts daily summaries.
Shows previously dispatched alerts from logs/alerts.jsonl and allows
triggering a new detection run from the UI.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import streamlit as st

from src.agents.alerts import load_alert_log, dispatch, format_slack_message
from src.agents.scorer import score_all_clients
from src.data_sources.crm import get_demo_clients
from src.ui.components import slack_message_card, production_badge


_PRODUCTION_NOTE_CHANNEL = (
    "Production: alerts are POSTed to a Slack Incoming Webhook URL "
    "(SLACK_WEBHOOK_URL in .env). The message format uses Slack Block Kit. "
    "Each button ('Generate Proposal') triggers a Slack bot action "
    "handled by the agency's Slack App. "
    "Telegram alternative: messages are sent via Bot API to a private channel."
)

_PRODUCTION_NOTE_TRIGGER = (
    "Production: the daily job runs automatically at 08:00 via cron. "
    "This 'Run Now' button simulates a manual trigger — in production "
    "it would call a webhook that starts the pipeline on the server."
)


def render():
    st.title("Alert Feed")
    st.caption(
        "Simulated Slack channel — the agent posts here every morning with newly detected opportunities. "
        "The account team reviews alerts and decides which ones to act on."
    )
    production_badge(_PRODUCTION_NOTE_CHANNEL)
    st.divider()

    # ── Run controls ──────────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("**Trigger Detection Run**")
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            scope = st.radio(
                "Scope",
                ["All clients", "Demo clients only"],
                horizontal=True,
                label_visibility="visible",
            )
        with col2:
            min_score = st.slider("Min confidence score", 0, 100, 60, step=5)
        with col3:
            st.write("")
            run_btn = st.button("Run Now", type="primary", use_container_width=True)

        production_badge(_PRODUCTION_NOTE_TRIGGER)

    if run_btn:
        with st.spinner("Scanning clients and dispatching alerts..."):
            all_results = score_all_clients()

            if scope == "Demo clients only":
                demo_ids = {c["id"] for c in get_demo_clients()}
                results = [r for r in all_results if r["client_id"] in demo_ids]
            else:
                results = all_results

            alertable = [r for r in results if r["score"] >= min_score]

            if alertable:
                dispatch(alertable)
                st.success(
                    f"Dispatched {len(alertable)} alerts "
                    f"({'written to logs/alerts.jsonl in demo mode'})."
                )
            else:
                st.info("No opportunities above the selected confidence threshold.")

        st.rerun()

    # ── Alert log ─────────────────────────────────────────────────────────────
    alerts = load_alert_log()

    if not alerts:
        st.info(
            "No alerts yet. Click **Run Now** above to trigger the detection engine "
            "and populate this feed."
        )
        return

    # Reverse so newest first
    alerts = list(reversed(alerts))

    # Filter by min_score (apply to the display too)
    shown = [a for a in alerts if a.get("score", 0) >= min_score]

    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.markdown(f"**{len(shown)} alerts** matching filter (of {len(alerts)} total)")
    with col_b:
        if st.button("Clear Log", use_container_width=True):
            import config
            log_path = config.LOGS_DIR / "alerts.jsonl"
            if log_path.exists():
                log_path.write_text("")
            st.rerun()

    st.divider()

    for alert in shown:
        slack_message_card(alert)

        # Show the raw Slack payload in an expander
        with st.expander("Raw Slack Block Kit payload"):
            st.caption(
                "This is the exact JSON payload that would be POSTed to the Slack webhook in production."
            )
            payload = alert.get("slack_payload", {})
            st.json({k: v for k, v in payload.items() if k != "_production_integration"})
