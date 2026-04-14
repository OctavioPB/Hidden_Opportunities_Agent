"""
Sprint 7 — Autonomous Negotiation Dashboard.

This page visualises and controls the negotiation engine:

  ┌─────────────────────────────────────────────────────────────────┐
  │  KPI row:  Active  |  Auto-resolved  |  Escalated  |  Rate     │
  ├─────────────────────────────────────────────────────────────────┤
  │  Active Negotiations panel                                      │
  │    For each negotiation: client name, turn count, last offer,   │
  │    conversation thread, Kill Switch / Mark Accepted             │
  ├─────────────────────────────────────────────────────────────────┤
  │  Demo simulation panel                                          │
  │    Pick a client → trigger 'too_expensive' reply → watch turns  │
  ├─────────────────────────────────────────────────────────────────┤
  │  Payment Links panel                                            │
  │    Proposals with accepted/paid status; generate / view links   │
  └─────────────────────────────────────────────────────────────────┘

"In Production" annotations explain the real-world integrations at every step.
"""

from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import streamlit as st

from src.agents.negotiator import (
    start_negotiation,
    process_client_reply,
    kill_negotiation,
    get_thread,
    get_active_negotiations,
    get_negotiation_summary,
    STATUS_ACTIVE, STATUS_ACCEPTED, STATUS_REJECTED, STATUS_ESCALATED,
    NEG_INTENT_ACCEPT, NEG_INTENT_REJECT, NEG_INTENT_COUNTER, NEG_INTENT_INFO,
)
from src.agents.payment_link import create_payment_link, list_payment_links, get_payment_link
from src.agents.feedback_loop import record_client_reply, INTENT_TOO_EXPENSIVE
from src.agents.proposal_generator import get_all_proposals
from src.data_sources.crm import get_all_clients
from src.ui.components import page_header, section_header, production_badge


# ── Simulated client replies for the demo ─────────────────────────────────────
_SIM_REPLIES = {
    "Accepts offer (Turn 1)":       "Perfect, I accept. Let's proceed with the offered discount.",
    "Asks for more discount":       "Thank you, but could we possibly get a bit more off?",
    "Rejects definitively":         "I'm sorry, we're not interested at this time.",
    "Ignores — no clear response":  "Hmm, let me think about it and I'll get back to you.",
    "Asks to speak with a person":  "Please stop the automated emails, I'd like to speak with someone.",
}

_INTENT_LABEL = {
    NEG_INTENT_ACCEPT:  ("Accepted",   "#1b5e20"),
    NEG_INTENT_REJECT:  ("Rejected",   "#b71c1c"),
    NEG_INTENT_COUNTER: ("Counter",    "#e65100"),
    NEG_INTENT_INFO:    ("Info",       "#1a237e"),
    "escalated":        ("Escalated",  "#880e4f"),
    None:               ("Pending",    "#424242"),
}


# ── Main render ───────────────────────────────────────────────────────────────

def render() -> None:
    page_header(
        "Autonomous Negotiation",
        "The agent negotiates price with clients over multiple turns using LLM.",
    )

    production_badge(
        "Client replies arrive via SendGrid Inbound Parse. "
        "The agent responds in &lt; 2 min. Stripe generates the payment link on close.",
    )

    summary = get_negotiation_summary()
    _render_kpis(summary)

    st.divider()

    tab_active, tab_demo, tab_payments, tab_history = st.tabs([
        "Active Negotiations",
        "Demo Simulation",
        "Payment Links",
        "History",
    ])

    with tab_active:
        _render_active_negotiations()

    with tab_demo:
        _render_demo_panel()

    with tab_payments:
        _render_payment_links()

    with tab_history:
        _render_history()


# ── KPI row ───────────────────────────────────────────────────────────────────

def _render_kpis(summary: dict) -> None:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Negotiations",  summary["total_negotiations"])
    c2.metric("Active",              summary["active"],
              delta=None if summary["active"] == 0 else f"{summary['active']} in progress")
    c3.metric("Auto-resolved",       summary["accepted"],
              delta=f"{summary['auto_resolution_rate']}%" if summary["total_negotiations"] > 0 else None,
              delta_color="normal")
    c4.metric("Rejected",            summary["rejected"])
    c5.metric("Escalated",           summary["escalated"])


# ── Active negotiations panel ─────────────────────────────────────────────────

def _render_active_negotiations() -> None:
    section_header("Active Negotiations")

    active = get_active_negotiations()

    if not active:
        st.info(
            "No active negotiations. "
            "Go to the **Demo Simulation** tab to start one.",
        )
        return

    for neg in active:
        pid    = neg["proposal_id"]
        thread = get_thread(pid)

        with st.expander(
            f"**{neg['client_name']}** — {neg['opportunity_type'].replace('_',' ').title()} "
            f"| Turn {neg['turn_count']} | Last activity: {neg['last_activity'][:10]}",
            expanded=True,
        ):
            col_info, col_actions = st.columns([3, 1])

            with col_info:
                st.caption(
                    f"Score: {neg['score'] or 0:.0f} · "
                    f"Original price: ${neg['suggested_price'] or 0:,.0f} · "
                    f"Industry: {neg['industry']}"
                )

                # Chat thread
                _render_thread(thread)

            with col_actions:
                st.markdown("**Actions**")

                # Manual reply input
                client_reply = st.text_area(
                    "Simulate client reply",
                    key=f"reply_{pid}",
                    height=80,
                    placeholder="Client responds…",
                )
                if st.button("Submit reply", key=f"send_{pid}", use_container_width=True):
                    if client_reply.strip():
                        with st.spinner("Agent is processing…"):
                            result = process_client_reply(pid, client_reply.strip())
                        st.success(f"Intent detected: **{result['intent']}**")
                        if result.get("offer_price"):
                            st.info(f"New offer: **${result['offer_price']:,.0f}**")
                        if result["status"] == STATUS_ACCEPTED:
                            st.balloons()
                        st.rerun()
                    else:
                        st.warning("Please enter a reply first.")

                st.markdown("---")

                # Kill switch
                if st.button(
                    "Kill Switch — Escalate to human",
                    key=f"kill_{pid}",
                    use_container_width=True,
                    type="primary",
                ):
                    kill_negotiation(pid, reason="manual_kill_switch_ui")
                    st.warning(
                        f"Negotiation escalated to account manager "
                        f"**{neg['account_manager']}**."
                    )
                    st.rerun()

                st.caption(
                    "The kill switch stops the automated negotiation "
                    "and notifies the account manager via Slack in production."
                )


def _render_thread(thread: list[dict]) -> None:
    """Render a negotiation conversation as a chat-style display."""
    if not thread:
        st.caption("No messages yet.")
        return

    for turn in thread:
        role        = turn["role"]
        msg         = turn["message"] or ""
        intent      = turn.get("intent")
        offer_price = turn.get("offer_price")
        ts          = (turn.get("timestamp") or "")[:16]

        intent_label, _ = _INTENT_LABEL.get(intent, _INTENT_LABEL[None])
        price_tag  = f" · Offer: **${offer_price:,.0f}**" if offer_price else ""
        intent_tag = f" · `{intent_label}`" if intent else ""

        if role == "agent":
            st.html(
                f"<div style='"
                f"background:#E8EFF8;border-radius:8px;"
                f"padding:10px 14px;margin:6px 0;"
                f"border-left:3px solid #003366;"
                f"font-family:Plus Jakarta Sans,sans-serif;'>"
                f"<div style='font-size:10px;font-weight:700;letter-spacing:.8px;"
                f"text-transform:uppercase;color:#003366;margin-bottom:4px;'>"
                f"Agent&nbsp;&nbsp;<span style='font-weight:400;color:#6B7280;"
                f"text-transform:none;letter-spacing:0;'>{ts}{price_tag}</span>"
                f"</div>"
                f"<div style='font-size:13px;color:#0D1B2E;line-height:1.6;'>"
                f"{msg[:400]}{'…' if len(msg)>400 else ''}</div>"
                f"</div>"
            )
        else:
            st.html(
                f"<div style='"
                f"background:#FBF5E6;border-radius:8px;"
                f"padding:10px 14px;margin:6px 0;"
                f"border-left:3px solid #C8982A;"
                f"font-family:Plus Jakarta Sans,sans-serif;'>"
                f"<div style='font-size:10px;font-weight:700;letter-spacing:.8px;"
                f"text-transform:uppercase;color:#92400E;margin-bottom:4px;'>"
                f"Client&nbsp;&nbsp;<span style='font-weight:400;color:#6B7280;"
                f"text-transform:none;letter-spacing:0;'>{ts}{intent_tag}</span>"
                f"</div>"
                f"<div style='font-size:13px;color:#0D1B2E;line-height:1.6;'>"
                f"{msg[:300]}{'…' if len(msg)>300 else ''}</div>"
                f"</div>"
            )


# ── Demo simulation panel ─────────────────────────────────────────────────────

def _render_demo_panel() -> None:
    section_header("Full Negotiation Simulation")
    st.caption(
        "Select an existing proposal (or create one via the Proposals page), "
        "simulate a 'price too high' reply, and watch the agent negotiate."
    )

    # Pick a proposal
    all_proposals = get_all_proposals()
    sent_proposals = [
        p for p in all_proposals
        if p["status"] in ("sent", "draft", "approved", "rejected")
    ]

    if not sent_proposals:
        st.warning("No proposals available. Generate one on the **Proposals** page.")
        return

    options = {
        f"{p['client_name']} — {p['opportunity_type'].replace('_',' ').title()} "
        f"(${p['suggested_price']:,.0f}) [{p['status']}]": p["id"]
        for p in sent_proposals
    }

    col_select, col_btn = st.columns([3, 1])
    with col_select:
        selected_label = st.selectbox(
            "Proposal to negotiate",
            list(options.keys()),
            key="demo_proposal_select",
        )
    selected_pid = options[selected_label]

    # Step 1: trigger too_expensive
    st.markdown("**Step 1 — Client says: 'Price is too high'**")
    if st.button(
        "Simulate 'Too Expensive' reply",
        key="sim_too_expensive",
        type="primary",
    ):
        with st.spinner("Recording client reply and opening negotiation…"):
            try:
                record_client_reply(
                    selected_pid,
                    intent=INTENT_TOO_EXPENSIVE,
                    notes="[DEMO] Client indicated the price is too high.",
                    simulated=True,
                )
                st.success(
                    "Reply recorded. The agent has opened a negotiation "
                    "with a 10% discount. See the **Active Negotiations** tab."
                )
            except Exception as e:
                try:
                    neg = start_negotiation(selected_pid)
                    st.success(
                        f"Negotiation started directly. "
                        f"Offer: **${neg.get('offer_price', 0):,.0f}**"
                    )
                except Exception as e2:
                    st.error(f"Error: {e2}")
        st.rerun()

    st.divider()
    st.markdown("**Step 2 — Simulate client reply to counter-offer**")

    thread = get_thread(selected_pid)
    if thread:
        _render_thread(thread)

        reply_choice = st.selectbox(
            "Client reply type",
            list(_SIM_REPLIES.keys()),
            key="sim_reply_choice",
        )
        sim_text = _SIM_REPLIES[reply_choice]
        st.info(f"Reply text: *\"{sim_text}\"*")

        if st.button("Send simulated reply", key="sim_reply_btn", type="primary"):
            with st.spinner("Agent processing reply…"):
                result = process_client_reply(selected_pid, sim_text, simulated=True)
            st.success(f"Intent detected: **{result['intent']}** | Status: **{result['status']}**")
            if result.get("offer_price"):
                st.info(f"New agent offer: **${result['offer_price']:,.0f}**")
            if result["status"] == STATUS_ACCEPTED:
                st.balloons()
                link = get_payment_link(selected_pid)
                if not link:
                    link_result = create_payment_link(selected_pid)
                    link = link_result["url"]
                st.success(f"Payment link generated: `{link}`")
            st.rerun()
    else:
        st.caption("Run Step 1 first to open the negotiation.")

    production_badge(
        "In production, client replies arrive via the SendGrid Inbound Parse webhook. "
        "The agent identifies the thread via the Message-ID header, extracts intent "
        "with the LLM, and sends a response in under 2 minutes.",
    )


# ── Payment links panel ───────────────────────────────────────────────────────

def _render_payment_links() -> None:
    section_header("Stripe Payment Links")

    production_badge(
        "POST /v1/payment_links with price_data. The client receives the link "
        "by email. Webhook checkout.session.completed → status 'paid' in DB.",
    )

    links = list_payment_links()

    if not links:
        st.info("No payment links generated yet.")
        _render_manual_link_generator()
        return

    for link in links:
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.markdown(f"**{link['client_name']}**")
                st.caption(
                    f"{link['opportunity_type'].replace('_',' ').title()} · "
                    f"Status: `{link['status']}` · "
                    f"{link['created_at'][:10]}"
                )
            with col2:
                st.metric("Amount", f"${link['suggested_price']:,.0f}")
            with col3:
                st.link_button(
                    "Open link",
                    url=link["payment_link"],
                    use_container_width=True,
                )
            st.code(link["payment_link"], language=None)

    st.divider()
    _render_manual_link_generator()


def _render_manual_link_generator() -> None:
    st.markdown("**Generate payment link manually**")

    accepted_proposals = [
        p for p in get_all_proposals()
        if p["status"] in ("accepted", "sent", "approved") and not get_payment_link(p["id"])
    ]

    if not accepted_proposals:
        st.caption("No accepted or sent proposals without a payment link.")
        return

    options = {
        f"{p['client_name']} — ${p['suggested_price']:,.0f} [{p['status']}]": p["id"]
        for p in accepted_proposals
    }

    col_sel, col_price, col_btn = st.columns([3, 1, 1])
    with col_sel:
        label = st.selectbox("Proposal", list(options.keys()), key="payment_proposal_select")
    pid = options[label]
    base_price = next(p["suggested_price"] for p in accepted_proposals if p["id"] == pid)

    with col_price:
        custom = st.number_input(
            "Amount (USD)", value=float(base_price), min_value=1.0, key="payment_amount"
        )
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Generate Link", key="gen_payment_link", use_container_width=True):
            with st.spinner("Generating link…"):
                result = create_payment_link(pid, custom_amount=custom)
            st.success("Link generated:")
            st.code(result["url"])
            st.rerun()


# ── History panel ─────────────────────────────────────────────────────────────

def _render_history() -> None:
    section_header("Negotiation History")

    from src.db.schema import get_connection
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT nl.proposal_id, nl.turn, nl.role, nl.message,
               nl.intent, nl.offer_price, nl.timestamp,
               c.name AS client_name,
               o.opportunity_type
        FROM negotiation_log nl
        JOIN proposals      p  ON p.id  = nl.proposal_id
        JOIN clients        c  ON c.id  = p.client_id
        JOIN opportunities  o  ON o.id  = p.opportunity_id
        ORDER BY nl.timestamp DESC
        LIMIT 200
        """
    ).fetchall()
    conn.close()

    if not rows:
        st.info("No negotiation history yet.")
        return

    import pandas as pd
    df = pd.DataFrame([dict(r) for r in rows])
    df["message_preview"] = df["message"].str[:80] + "…"
    df = df[["timestamp", "client_name", "opportunity_type",
             "turn", "role", "intent", "offer_price", "message_preview"]]
    df.columns = ["Timestamp", "Client", "Type", "Turn", "Role", "Intent",
                  "Offer Price", "Message (preview)"]
    st.dataframe(df, use_container_width=True, hide_index=True)
