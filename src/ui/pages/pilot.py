"""
Sprint 4 — Pilot Dashboard & Full Cycle Simulation.

This page is the showpiece of Sprint 4.  It demonstrates the complete agent
loop end-to-end:

  Detect → Generate Proposal → (Auto-send or Approve) → Client Reply → Feedback

The "Simulation Speed" toggle controls the demo experience:
  SLOW   — Step-through mode. Each event is explained with annotations.
            The presenter clicks "Next Step" at each stage to advance.
  FAST   — Full cycle in one click. Seeds a client scenario and runs
            detect → propose → reply → feedback without pausing.

The Pilot Metrics section shows the aggregated report that would be handed to
agency leadership after a two-week pilot with three real clients.

"In Production" annotations on every key element explain the real integration.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import streamlit as st

from src.agents.scorer import score_client, persist_opportunities, score_all_clients
from src.agents.proposal_generator import (
    generate_proposal, get_all_proposals, approve_proposal,
)
from src.agents.email_sender import send_proposal_email, load_sent_log
from src.agents.feedback_loop import (
    record_client_reply, get_pilot_metrics, load_feedback_log,
    load_calendar_log, load_escalation_log,
    INTENT_LABELS, ALL_INTENTS,
    INTENT_ACCEPTED, INTENT_REJECTED, INTENT_TOO_EXPENSIVE,
    INTENT_NEED_INFO, INTENT_IGNORED, INTENT_ESCALATED,
)
from src.agents.auto_sender import (
    get_autonomy_tier, get_send_queue_summary, process_auto_send_queue,
)
from src.agents.rules import OPPORTUNITY_LABELS, SUGGESTED_PRICES
from src.data_sources.crm import get_demo_clients, get_all_clients
from src.ui.components import score_bar, production_badge


# ── Demo scenario scripts ─────────────────────────────────────────────────────
# Pre-scripted client reply sequences for the fast-mode demo.
# Each scenario tells a different story about the feedback loop.

SCENARIOS = {
    "Easy Close": {
        "description": "High-score opportunity, client accepts immediately.",
        "reply_intent": INTENT_ACCEPTED,
        "notes": "Client replied: 'Yes, let's do it! Please schedule a call.'",
    },
    "Price Objection": {
        "description": "Client interested but pushes back on price.",
        "reply_intent": INTENT_TOO_EXPENSIVE,
        "notes": "Client replied: 'Interesting, but the price is too high for us right now.'",
    },
    "No Reply": {
        "description": "Client ignores the proposal for 14 days.",
        "reply_intent": INTENT_IGNORED,
        "notes": "No response after 14 days. Confidence reduced for future outreach.",
    },
    "Escalation": {
        "description": "Client complains and requests human follow-up.",
        "reply_intent": INTENT_ESCALATED,
        "notes": "Client replied: 'Please stop sending automated emails. I want to speak with a person.'",
    },
}


# ── Colours / display helpers ─────────────────────────────────────────────────

_INTENT_COLORS = {
    INTENT_ACCEPTED:      "#2EB67D",
    INTENT_REJECTED:      "#E01E5A",
    INTENT_TOO_EXPENSIVE: "#ECB22E",
    INTENT_NEED_INFO:     "#36C5F0",
    INTENT_IGNORED:       "#888888",
    INTENT_ESCALATED:     "#E01E5A",
}

_TIER_COLORS = {"A": "#888", "B": "#ECB22E", "C": "#2EB67D"}
_TIER_LABELS = {
    "A": "Tier A — Draft Only",
    "B": "Tier B — Human Approval Required",
    "C": "Tier C — Autonomous Send",
}


def _tier_badge(tier: str) -> str:
    color = _TIER_COLORS.get(tier, "#888")
    label = _TIER_LABELS.get(tier, tier)
    return (
        f'<span style="background:{color};color:#fff;padding:2px 10px;'
        f'border-radius:4px;font-size:0.78em;font-weight:700;">{label}</span>'
    )


def _intent_badge(intent: str) -> str:
    color = _INTENT_COLORS.get(intent, "#888")
    label = INTENT_LABELS.get(intent, intent)
    return (
        f'<span style="background:{color};color:#fff;padding:2px 10px;'
        f'border-radius:4px;font-size:0.78em;font-weight:700;">{label}</span>'
    )


def _step_header(n: int, title: str, done: bool = False) -> None:
    icon = "✅" if done else f"**{n}.**"
    st.markdown(f"### {icon} {title}")


# ── Step panels ───────────────────────────────────────────────────────────────

def _step_detect(client_id: str, slow: bool) -> list[dict] | None:
    """Step 1: Run the detection engine for the selected client."""
    _step_header(1, "Detect Opportunity", done=False)
    st.caption("The agent scans the client's latest metrics and applies the rules engine.")

    if slow:
        production_badge(
            "Production: The detection engine runs daily at 08:00 via cron. "
            "Metrics are fetched from Google Analytics, Meta Ads, HubSpot CRM, "
            "and email platform APIs."
        )

    with st.spinner("Running detection engine…"):
        opps = score_client(client_id)

    if not opps:
        st.warning("No opportunities detected for this client with current metrics.")
        return None

    # Persist and return
    all_scored = score_all_clients()
    persist_opportunities(all_scored)

    for opp in opps:
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{opp.label}**")
                st.caption(opp.rationale)
                score_bar(opp.score)
            with col2:
                tier = get_autonomy_tier(opp.score, opp.suggested_price, opp.opportunity_type)
                st.html(_tier_badge(tier))
                st.markdown(f"**${opp.suggested_price:,.0f}**")

    return [
        {
            "label":            opp.label,
            "opportunity_type": opp.opportunity_type,
            "score":            opp.score,
            "suggested_price":  opp.suggested_price,
            "rationale":        opp.rationale,
        }
        for opp in opps
    ]


def _step_generate(client_id: str, slow: bool) -> dict | None:
    """Step 2: Generate a proposal for the top opportunity."""
    _step_header(2, "Generate Proposal", done=False)
    st.caption("The agent selects the highest-score opportunity and generates a personalized email draft.")

    if slow:
        production_badge(
            "Production: The proposal generator calls the LLM (Claude Haiku or GPT-3.5) "
            "to write a personalized insight paragraph. The draft is saved to the DB "
            "and uploaded to Google Drive. The account manager is notified via Slack."
        )

    conn = None
    try:
        from src.db.schema import get_connection
        conn = get_connection()

        # Find the top detected opportunity for this client
        opp_row = conn.execute(
            """
            SELECT id, opportunity_type, score, status
            FROM opportunities
            WHERE client_id = ?
              AND status IN ('detected', 'proposal_generated')
            ORDER BY score DESC
            LIMIT 1
            """,
            (client_id,),
        ).fetchone()

        if opp_row is None:
            st.warning("No qualifying opportunity in the DB. Run Step 1 first.")
            return None

        opp = dict(opp_row)

        # Check if a draft already exists
        existing_proposal = conn.execute(
            "SELECT id, subject, body, status FROM proposals "
            "WHERE opportunity_id=? AND status NOT IN ('rejected') "
            "ORDER BY created_at DESC LIMIT 1",
            (opp["id"],),
        ).fetchone()

        if existing_proposal:
            p = dict(existing_proposal)
            st.info(f"Using existing proposal draft `{p['id'][:8]}…` (status: {p['status']})")
        else:
            with st.spinner("Generating proposal…"):
                result = generate_proposal(opp["id"], rationale="Demo simulation.")
            p = {
                "id":      result["proposal_id"],
                "subject": result["subject"],
                "body":    result["body"],
                "status":  result["status"],
            }
            st.success(f"Proposal `{p['id'][:8]}…` generated ({result.get('generation_method', 'template')} method).")

        with st.container(border=True):
            st.markdown(f"**Subject:** {p['subject']}")
            st.divider()
            st.markdown(p["body"])

        return {"proposal_id": p["id"], "subject": p["subject"], "status": p["status"]}

    finally:
        if conn:
            conn.close()


def _step_send(proposal_id: str, opp_score: float, opp_price: float, opp_type: str, slow: bool) -> bool:
    """Step 3: Send (or auto-send) the proposal."""
    _step_header(3, "Send Proposal", done=False)

    tier = get_autonomy_tier(opp_score, opp_price, opp_type)
    st.html(_tier_badge(tier))

    if slow:
        if tier == "C":
            st.success(
                "**Tier C — Autonomous Send.** "
                f"Score {opp_score:.0f} ≥ 90 and price ${opp_price:,.0f} ≤ $200. "
                "The agent sends the email directly (BCCing the account manager). "
                "No human approval needed."
            )
        else:
            st.info(
                "**Tier B — Human Approval Required.** "
                "An account manager must click Approve before the email is sent."
            )

        production_badge(
            "Production: Tier C sends via SendGrid API (POST /v3/mail/send) "
            "with a 30-minute cancellation window. "
            "The account manager receives a BCC and a Slack notification with a 'Cancel' button."
        )

    # Approve and send
    approve_proposal(proposal_id, approved_by="autonomous" if tier == "C" else "demo_user")

    try:
        from src.db.schema import get_connection
        conn = get_connection()
        status = conn.execute("SELECT status FROM proposals WHERE id=?", (proposal_id,)).fetchone()
        conn.close()
        if status and status[0] in ("sent", "accepted"):
            st.info("This proposal was already sent.")
            return True
    except Exception:
        pass

    with st.spinner("Sending email…"):
        try:
            send_proposal_email(
                proposal_id,
                send_mode="autonomous" if tier == "C" else "approved",
                bcc_manager=True,
            )
            time.sleep(0.3)   # visual pause
        except Exception as e:
            st.error(f"Send failed: {e}")
            return False

    st.success("Email sent. BCC delivered to account manager.")
    return True


def _step_reply(proposal_id: str, scenario_intent: str | None, slow: bool) -> str | None:
    """Step 4: Simulate client reply."""
    _step_header(4, "Client Reply", done=False)
    st.caption("Simulate how the client responds to the proposal.")

    if slow:
        production_badge(
            "Production: Client replies are parsed by the LLM (structured JSON output). "
            "The agent watches the email thread via Gmail API webhooks "
            "and processes replies within minutes of receipt."
        )

    if scenario_intent:
        intent = scenario_intent
        st.info(f"**Scenario reply:** {INTENT_LABELS[intent]}")
    else:
        intent = st.selectbox(
            "Client replied…",
            ALL_INTENTS,
            format_func=lambda i: INTENT_LABELS[i],
            key=f"reply_intent_{proposal_id}",
        )

    return intent


def _step_feedback(proposal_id: str, intent: str, slow: bool) -> dict | None:
    """Step 5: Process feedback and update confidence."""
    _step_header(5, "Feedback Loop", done=False)
    st.caption("The agent records the outcome and adjusts its confidence for future opportunities.")

    if slow:
        production_badge(
            "Production: Feedback is stored in the DB and used to retrain "
            "the ML model in Sprint 5. A Google Calendar event is created "
            "when the client accepts. Escalations trigger an immediate Slack @mention."
        )

    # Check if feedback already recorded for this proposal
    try:
        from src.db.schema import get_connection
        conn = get_connection()
        existing_fb = conn.execute(
            "SELECT outcome FROM feedback_log WHERE proposal_id=? LIMIT 1",
            (proposal_id,),
        ).fetchone()
        conn.close()
        if existing_fb:
            st.info(f"Feedback already recorded for this proposal: **{INTENT_LABELS.get(existing_fb[0], existing_fb[0])}**")
            return None
    except Exception:
        pass

    with st.spinner("Recording feedback…"):
        result = record_client_reply(proposal_id, intent, simulated=True)
        time.sleep(0.4)

    # Visual result
    color = _INTENT_COLORS.get(intent, "#888")

    st.html(
        f'<div style="border-left:4px solid {color};background:#1a1d21;'
        f'border-radius:6px;padding:12px 16px;margin:8px 0;">'
        f'<div style="color:{color};font-weight:700;margin-bottom:6px;">'
        f'{INTENT_LABELS[intent]}</div>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;color:#d1d2d3;">'
        f'<div><span style="color:#999;font-size:0.8em;">REVENUE</span><br>'
        f'${result["revenue"] or 0:,.0f}</div>'
        f'<div><span style="color:#999;font-size:0.8em;">CONFIDENCE Δ</span><br>'
        f'<span style="color:{color};">{result["confidence_delta"]:+.0f} pts</span></div>'
        f'<div><span style="color:#999;font-size:0.8em;">ACTIONS</span><br>'
        f'{"<br>".join(result["actions_taken"]) or "none"}</div>'
        f'</div></div>'
    )

    if intent == INTENT_ACCEPTED:
        st.balloons()
        st.success("Meeting scheduled on account manager's calendar.")
    elif intent == INTENT_ESCALATED:
        st.error("ESCALATED — account manager notified immediately.")

    return result


# ── Full-cycle demo runner ────────────────────────────────────────────────────

def _run_full_cycle(client_id: str, scenario_name: str, slow: bool) -> None:
    """Execute the complete detect → propose → send → reply → feedback cycle."""
    scenario = SCENARIOS[scenario_name]
    intent   = scenario["reply_intent"]

    # ── Step 1: Detect ────────────────────────────────────────────────────────
    with st.container(border=True):
        opps = _step_detect(client_id, slow)
        if not opps:
            return
        if slow:
            if not st.button("Next: Generate Proposal →", key="btn_s2"):
                return

    # ── Step 2: Generate ──────────────────────────────────────────────────────
    with st.container(border=True):
        proposal = _step_generate(client_id, slow)
        if not proposal:
            return
        if slow:
            if not st.button("Next: Send →", key="btn_s3"):
                return

    proposal_id = proposal["proposal_id"]
    top_opp     = opps[0]

    # Load actual score/price/type from DB
    try:
        from src.db.schema import get_connection
        conn = get_connection()
        p_row = conn.execute(
            "SELECT o.score, p.suggested_price, o.opportunity_type "
            "FROM proposals p JOIN opportunities o ON o.id=p.opportunity_id "
            "WHERE p.id=?", (proposal_id,)
        ).fetchone()
        conn.close()
        if p_row:
            opp_score = p_row["score"] or top_opp["score"]
            opp_price = p_row["suggested_price"] or top_opp["suggested_price"]
            opp_type  = p_row["opportunity_type"] or top_opp["opportunity_type"]
        else:
            opp_score = top_opp["score"]
            opp_price = top_opp["suggested_price"]
            opp_type  = top_opp["opportunity_type"]
    except Exception:
        opp_score = top_opp["score"]
        opp_price = top_opp["suggested_price"]
        opp_type  = top_opp["opportunity_type"]

    # ── Step 3: Send ──────────────────────────────────────────────────────────
    with st.container(border=True):
        sent_ok = _step_send(proposal_id, opp_score, opp_price, opp_type, slow)
        if not sent_ok:
            return
        if slow:
            if not st.button("Next: Simulate Client Reply →", key="btn_s4"):
                return

    # ── Step 4: Reply ─────────────────────────────────────────────────────────
    with st.container(border=True):
        resolved_intent = _step_reply(proposal_id, intent, slow)
        if resolved_intent is None:
            return
        if slow:
            if not st.button("Next: Process Feedback →", key="btn_s5"):
                return

    # ── Step 5: Feedback ──────────────────────────────────────────────────────
    with st.container(border=True):
        _step_feedback(proposal_id, resolved_intent, slow)


# ── Pilot metrics panel ───────────────────────────────────────────────────────

def _render_pilot_metrics() -> None:
    st.subheader("Pilot Report")
    st.caption(
        "Aggregated metrics for the pilot period. "
        "In a production pilot this covers 2 weeks with 3 real clients."
    )

    m = get_pilot_metrics()

    # KPI row
    k = st.columns(5)
    k[0].metric("Opportunities Detected", m["total_opportunities"])
    k[1].metric("Proposals Generated", m["proposals_generated"])
    k[2].metric("Proposals Sent", m["proposals_sent"],
                help=f"Autonomous: {m['autonomous_sent']} | Approved: {m['approved_sent']}")
    k[3].metric("Accepted", m["proposals_accepted"],
                delta=f"{m['acceptance_rate_pct']}% rate")
    k[4].metric("Revenue", f"${m['total_revenue']:,.0f}")

    k2 = st.columns(4)
    k2[0].metric("Escalations", m["escalations"])
    k2[1].metric("Rejections / Ignores", m["proposals_rejected"])
    k2[2].metric("Time Saved (est.)", f"{m['time_saved_hours']}h",
                 help="20 min manually per proposal → 2 min with agent")
    k2[3].metric("Autonomous Sends", m["autonomous_sent"],
                 help="Tier C: score ≥ 90, value ≤ $200")

    production_badge(
        "Production: This report is generated from the DB and emailed to agency leadership "
        "every Friday as a PDF. Metrics include client satisfaction surveys (NPS) "
        "and CRM revenue attribution."
    )

    # By-type breakdown
    if m["by_type"]:
        st.divider()
        st.caption("Proposals by opportunity type")
        for row in m["by_type"]:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(OPPORTUNITY_LABELS.get(row["opportunity_type"], row["opportunity_type"]))
            with col2:
                st.markdown(f"**{row['cnt']}** proposals")
            with col3:
                acc = row["accepted"] or 0
                st.markdown(f"**{acc}** accepted")


# ── Sent email log ─────────────────────────────────────────────────────────────

def _render_sent_log() -> None:
    st.subheader("Sent Email Log")
    sent = load_sent_log()
    if not sent:
        st.info("No emails sent yet. Run the simulation above.")
        return

    for entry in reversed(sent[-10:]):
        mode_color = "#2EB67D" if entry.get("send_mode") == "autonomous" else "#ECB22E"
        st.html(
            f'<div style="border-left:4px solid {mode_color};background:#1a1d21;'
            f'border-radius:6px;padding:10px 14px;margin:6px 0;">'
            f'<div style="display:grid;grid-template-columns:2fr 2fr 1fr 1fr;gap:4px 12px;color:#d1d2d3;">'
            f'<div><span style="color:#999;font-size:0.78em;">CLIENT</span><br>{entry.get("client_name","")}</div>'
            f'<div><span style="color:#999;font-size:0.78em;">SUBJECT</span><br>'
            f'<span style="font-size:0.85em;">{entry.get("subject","")[:50]}…</span></div>'
            f'<div><span style="color:#999;font-size:0.78em;">MODE</span><br>'
            f'<span style="color:{mode_color};font-weight:600;">{entry.get("send_mode","").upper()}</span></div>'
            f'<div><span style="color:#999;font-size:0.78em;">TIME</span><br>'
            f'{(entry.get("timestamp","")[:16]).replace("T"," ")}</div>'
            f'</div></div>'
        )

    production_badge(
        "Production: Sent emails are tracked via SendGrid open/click events, "
        "stored in the DB as engagement signals, and surfaced in the pilot report."
    )


# ── Main render ────────────────────────────────────────────────────────────────

def render() -> None:
    st.title("Pilot — Full Cycle Demo")
    st.caption(
        "This page demonstrates the complete agent loop: "
        "detect → generate → send → client reply → feedback. "
        "The feedback loop updates the agent's confidence for each client, "
        "making future proposals smarter."
    )

    production_badge(
        "Sprint 4 — Limited Autonomous Action. "
        "Tier C opportunities (score ≥ 90, value ≤ $200) are sent autonomously. "
        "All other proposals require explicit human approval. "
        "Every action is logged for audit. No real emails are sent in demo mode."
    )

    st.divider()

    # ── Controls ───────────────────────────────────────────────────────────────
    ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 1])

    with ctrl1:
        # Client selector
        all_clients = get_all_clients()
        demo_clients = get_demo_clients()
        demo_ids = {c["id"] for c in demo_clients}

        client_options = all_clients
        client_map = {c["id"]: f"{'🎯 ' if c['id'] in demo_ids else ''}{c['name']} ({c['industry']})"
                      for c in client_options}
        sel_client_id = st.selectbox(
            "Client",
            options=list(client_map.keys()),
            format_func=lambda cid: client_map[cid],
        )

    with ctrl2:
        scenario_name = st.selectbox(
            "Demo Scenario",
            options=list(SCENARIOS.keys()),
            help="Pre-scripted client reply sequence. The 'slow' mode allows custom replies.",
        )
        st.caption(SCENARIOS[scenario_name]["description"])

    with ctrl3:
        st.write("")
        st.write("")
        slow_mode = st.toggle("Slow mode", value=True,
                              help="Step-through with explanations (slow) vs. full cycle in one click (fast).")

    st.divider()

    # ── Simulation ─────────────────────────────────────────────────────────────
    sim_col, _ = st.columns([3, 1])
    with sim_col:
        if slow_mode:
            st.info(
                "**Slow mode** — Click through each step with explanations. "
                "Ideal for live demos where you want to explain what's happening."
            )
        else:
            st.success(
                "**Fast mode** — Full cycle in one click. "
                "Ideal for quick stakeholder demos under 3 minutes."
            )

    if not slow_mode:
        if st.button("Run Full Demo Cycle", type="primary", use_container_width=True):
            with st.container(border=True):
                _run_full_cycle(sel_client_id, scenario_name, slow=False)
            st.rerun()
    else:
        _run_full_cycle(sel_client_id, scenario_name, slow=True)

    st.divider()

    # ── Auto-send queue status ─────────────────────────────────────────────────
    with st.expander("Auto-Send Queue", icon="📤"):
        queue = get_send_queue_summary()
        qc1, qc2, qc3, qc4 = st.columns(4)
        qc1.metric("Pending (Approved)", queue["approved_pending_send"])
        qc2.metric("Tier A", queue["by_tier"]["A"])
        qc3.metric("Tier B", queue["by_tier"]["B"])
        qc4.metric("Tier C (auto)", queue["by_tier"]["C"])

        if queue["by_tier"]["C"] > 0:
            if st.button("Process Tier C Queue Now", type="primary"):
                results = process_auto_send_queue(dry_run=False)
                sent_count = len([r for r in results if not r.get("dry_run")])
                st.success(f"Sent {sent_count} autonomous email(s).")
                st.rerun()
        else:
            st.caption("No Tier C proposals in queue.")

        production_badge(
            "Production: Tier C queue is processed automatically 30 minutes after "
            "proposal generation, giving account managers a cancellation window. "
            "The queue runs at 08:30 daily via cron."
        )

    st.divider()

    # ── Tabs: Pilot Report | Sent Log | Feedback Log ───────────────────────────
    tab1, tab2, tab3 = st.tabs(["Pilot Report", "Sent Emails", "Feedback Log"])

    with tab1:
        _render_pilot_metrics()

    with tab2:
        _render_sent_log()

    with tab3:
        st.subheader("Feedback & Outcome Log")
        feedback = load_feedback_log()
        calendars = load_calendar_log()
        escalations = load_escalation_log()

        if not feedback:
            st.info("No feedback recorded yet. Run the simulation above.")
        else:
            fc1, fc2, fc3 = st.columns(3)
            fc1.metric("Feedback Entries", len(feedback))
            fc2.metric("Meetings Scheduled", len(calendars))
            fc3.metric("Escalations", len(escalations))

            for entry in reversed(feedback[-15:]):
                intent = entry.get("intent", "")
                color  = _INTENT_COLORS.get(intent, "#888")
                delta  = entry.get("confidence_delta", 0)
                delta_str = f"{delta:+.0f}" if delta != 0 else "0"
                st.html(
                    f'<div style="border-left:4px solid {color};background:#1a1d21;'
                    f'padding:8px 14px;margin:4px 0;border-radius:4px;">'
                    f'<span style="color:{color};font-weight:700;">{INTENT_LABELS.get(intent, intent)}</span>'
                    f'&nbsp;&nbsp;<span style="color:#999;font-size:0.8em;">'
                    f'{entry.get("client_name","")}</span>'
                    f'&nbsp;·&nbsp;<span style="color:#999;font-size:0.8em;">'
                    f'Δconfidence {delta_str}</span>'
                    f'&nbsp;·&nbsp;<span style="color:#999;font-size:0.8em;">'
                    f'${entry.get("revenue") or 0:,.0f} revenue</span>'
                    f'</div>'
                )
