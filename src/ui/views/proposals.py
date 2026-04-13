"""
Sprint 3 — Proposal Review & Approval Page.

This page implements the human-in-the-loop approval workflow described in the
Sprint 3 plan.  It shows every generated proposal with:

  Left panel  — Opportunity data: the raw signals that triggered the detection.
  Right panel — Proposal preview: the email that would be sent to the client.

Actions available per proposal
-------------------------------
  Approve  → status changes to 'approved'; in production this triggers a
              Slack DM to the account manager confirming the send.
  Reject   → status changes to 'rejected'; opportunity resets to 'detected'
              so a new (or revised) proposal can be generated next run.
  Edit     → inline text editor that replaces the proposal body before approval.
  Generate → on-demand button to generate a proposal for a specific detected
              opportunity that doesn't yet have one.

"In Production" annotation on every key element explains the real integration.
"""

from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import streamlit as st
import pandas as pd
from datetime import datetime

from src.agents.proposal_generator import (
    get_all_proposals,
    approve_proposal,
    reject_proposal,
    update_proposal_body,
    generate_proposal,
    generate_proposals_for_all,
)
from src.agents.scorer import score_all_clients
from src.agents.rules import OPPORTUNITY_LABELS, SUGGESTED_PRICES
from src.ui.components import score_bar, production_badge, page_header


# ── Status colours (OPB semantic badge system) ─────────────────────────────────
_STATUS_COLORS = {
    "draft":    {"dot": "#F07020", "bg": "#FEF0E6", "text": "#7A3800"},
    "approved": {"dot": "#27B97C", "bg": "#E0F7EF", "text": "#0D5C3A"},
    "sent":     {"dot": "#003366", "bg": "#E0EAF4", "text": "#001F4D"},
    "rejected": {"dot": "#E03448", "bg": "#FDEAEA", "text": "#7A1020"},
    "accepted": {"dot": "#27B97C", "bg": "#E0F7EF", "text": "#0D5C3A"},
}

_STATUS_LABELS = {
    "draft":    "Draft",
    "approved": "Approved — Ready to Send",
    "sent":     "Sent",
    "rejected": "Rejected",
    "accepted": "Accepted by Client",
}


def _status_badge(status: str) -> str:
    c     = _STATUS_COLORS.get(status, {"dot": "#6B7280", "bg": "#F4F6F9", "text": "#1C1C2E"})
    label = _STATUS_LABELS.get(status, status.title())
    return (
        f'<span style="display:inline-flex;align-items:center;gap:6px;'
        f'background:{c["bg"]};color:{c["text"]};'
        f'padding:4px 12px;border-radius:20px;'
        f'font-size:10px;font-weight:600;'
        f'font-family:Plus Jakarta Sans,sans-serif;letter-spacing:.5px;">'
        f'<span style="width:6px;height:6px;border-radius:50%;'
        f'background:{c["dot"]};display:inline-block;flex-shrink:0;"></span>'
        f'{label}</span>'
    )


# ── Page sections ──────────────────────────────────────────────────────────────

def _render_kpis(proposals: list[dict]) -> None:
    total   = len(proposals)
    draft   = sum(1 for p in proposals if p["status"] == "draft")
    approved = sum(1 for p in proposals if p["status"] == "approved")
    sent    = sum(1 for p in proposals if p["status"] in ("sent", "accepted"))
    value   = sum(p["suggested_price"] for p in proposals if p["status"] != "rejected")

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Proposals", total)
    k2.metric("Drafts (Pending Review)", draft)
    k3.metric("Approved", approved)
    k4.metric("Sent / Accepted", sent)
    k5.metric("Pipeline Value", f"${value:,.0f}")

    production_badge(
        "In production: proposal counts sync in real time via the DB. "
        "Approved proposals trigger a SendGrid API call. "
        "Sent/Accepted status is updated when the client replies (Sprint 4 feedback loop)."
    )


def _render_generate_panel() -> None:
    """Allow on-demand proposal generation for high-score opportunities."""
    with st.expander("Generate Proposals On-Demand"):
        st.caption(
            "Generate proposals for all detected opportunities with score ≥ threshold "
            "that do not yet have a draft. In production this runs automatically "
            "as part of the daily job (scripts/daily_job.py step 3)."
        )

        col1, col2 = st.columns([1, 3])
        with col1:
            min_score = st.slider(
                "Minimum confidence score", 50, 100, 70, 5,
                help="Only generate proposals for opportunities above this threshold."
            )
        with col2:
            st.write("")
            st.write("")
            if st.button("Generate All Proposals Above Threshold", type="primary"):
                with st.spinner("Generating proposals…"):
                    results = generate_proposals_for_all(min_score=min_score)
                new_ones = [r for r in results if not r.get("already_existed")]
                if new_ones:
                    st.success(f"Generated {len(new_ones)} new proposal(s).")
                else:
                    st.info("No new proposals generated (all qualifying opportunities already have a draft).")
                st.rerun()

        production_badge(
            "In production: 'Generate All' is triggered automatically at 08:05 every morning "
            "by the daily cron job, right after detection. "
            "The LLM call uses OpenAI GPT-3.5 or Claude Haiku via API — "
            "each call costs ~$0.001–0.005. "
            "The markdown file is uploaded to Google Drive via the Drive API v3."
        )


def _render_proposal_card(p: dict, idx: int) -> None:
    """Render a single proposal as a side-by-side opportunity + proposal card."""
    status      = p["status"]
    client_name = p["client_name"]
    opp_type    = p["opportunity_type"]
    label       = OPPORTUNITY_LABELS.get(opp_type, opp_type.replace("_", " ").title())
    score       = p["score"] or 0
    price       = p["suggested_price"]
    is_demo     = p.get("is_demo_scenario", 0)
    created     = (p.get("created_at") or "")[:16].replace("T", " ")

    card_key = f"proposal_{p['id']}"

    with st.container(border=True):
        # ── Card header ───────────────────────────────────────────────────────
        hcol1, hcol2, hcol3 = st.columns([3, 2, 1])
        with hcol1:
            demo_tag = " [Demo]" if is_demo else ""
            st.markdown(
                f"**{client_name}**{demo_tag} &nbsp;·&nbsp; *{p['industry']}*  \n"
                f"**{label}**"
            )
        with hcol2:
            st.html(_status_badge(status))
            st.caption(f"Created: {created}")
        with hcol3:
            st.markdown(
                f"<div style='text-align:right;font-family:Fraunces,Georgia,serif;"
                f"font-size:1.5em;font-weight:300;color:#C8982A;'>${price:,.0f}</div>",
                unsafe_allow_html=True,
            )

        score_bar(score)

        # ── Side-by-side panels ───────────────────────────────────────────────
        left, right = st.columns([1, 1])

        # Left: opportunity data panel
        with left:
            st.markdown("**Opportunity Data**")
            st.caption("Raw signals that triggered this proposal")

            opp_conn = None
            try:
                from src.db.schema import get_connection
                import sqlite3
                conn = get_connection()
                metrics_row = conn.execute(
                    """
                    SELECT cm.*
                    FROM client_metrics cm
                    WHERE cm.client_id = ?
                    ORDER BY cm.date DESC
                    LIMIT 1
                    """,
                    (p["client_id"],),
                ).fetchone()
                conn.close()

                if metrics_row:
                    m = dict(metrics_row)
                    metric_display = {
                        "CTR":              f"{m.get('ctr', 0):.1%}",
                        "Bounce Rate":      f"{m.get('bounce_rate', 0):.0%}",
                        "Pages/Session":    f"{m.get('pages_per_session', 0):.1f}",
                        "Conversion Rate":  f"{m.get('conversion_rate', 0):.2%}",
                        "Organic Traffic":  f"{m.get('organic_traffic', 0):,}/mo",
                        "Ad Spend":         f"${(m.get('ad_spend', 0) or 0)*30:,.0f}/mo",
                        "ROAS":             f"{m.get('roas', 0):.1f}x",
                        "Email Open Rate":  f"{m.get('email_open_rate', 0):.1%}",
                        "Days Inactive":    str(m.get("days_inactive", 0)),
                        "Keyword Rankings": str(m.get("keyword_rankings", 0)),
                    }
                    # Show only non-zero metrics
                    shown = {k: v for k, v in metric_display.items()
                             if not v.startswith("0") and v not in ("0", "0.0x", "0.0/mo", "$0/mo")}
                    for k, v in shown.items():
                        st.markdown(f"- **{k}:** {v}")
                else:
                    st.caption("No metrics snapshot found.")
            except Exception as e:
                st.caption(f"Could not load metrics: {e}")

            production_badge(
                "In production, this panel is populated by real-time API calls to "
                "Google Analytics (bounce rate, pages/session), "
                "Meta Ads Manager (CTR, ROAS, ad spend), "
                "Mailchimp (open rate), and HubSpot CRM (days inactive)."
            )

        # Right: proposal preview
        with right:
            st.markdown("**Proposal Preview**")
            st.caption("Email that will be sent to the client")

            subject = p.get("subject", "")
            body    = p.get("body", "")

            # Editable body for draft proposals
            edit_key = f"editing_{p['id']}"
            if edit_key not in st.session_state:
                st.session_state[edit_key] = False

            if status == "draft" and st.session_state[edit_key]:
                new_body = st.text_area(
                    "Edit proposal body",
                    value=body,
                    height=300,
                    key=f"body_edit_{p['id']}",
                    label_visibility="collapsed",
                )
                bcol1, bcol2 = st.columns(2)
                with bcol1:
                    if st.button("Save Changes", key=f"save_{p['id']}", type="primary"):
                        update_proposal_body(p["id"], new_body)
                        st.session_state[edit_key] = False
                        st.success("Proposal updated.")
                        st.rerun()
                with bcol2:
                    if st.button("Cancel", key=f"cancel_{p['id']}"):
                        st.session_state[edit_key] = False
                        st.rerun()
            else:
                # Read-only preview
                with st.container(border=True):
                    st.markdown(f"**Subject:** {subject}")
                    st.divider()
                    st.markdown(body)

            production_badge(
                "In production: when 'Approve' is clicked, this email body is sent via "
                "the SendGrid API (POST /v3/mail/send) to the client's registered email. "
                "A BCC is automatically sent to the account manager. "
                "The sent_at timestamp and status are updated in the CRM."
            )

        # ── Action buttons ────────────────────────────────────────────────────
        if status == "draft":
            acol1, acol2, acol3, _ = st.columns([1, 1, 1, 3])
            with acol1:
                if st.button("Approve", key=f"approve_{p['id']}", type="primary"):
                    approve_proposal(p["id"])
                    st.success("Proposal approved and queued for sending.")
                    st.rerun()
            with acol2:
                if st.button("Edit", key=f"edit_{p['id']}"):
                    st.session_state[edit_key] = True
                    st.rerun()
            with acol3:
                if st.button("Reject", key=f"reject_{p['id']}"):
                    reject_proposal(p["id"], reason="Rejected via UI")
                    st.warning("Proposal rejected. The opportunity is reset for a new proposal.")
                    st.rerun()

            production_badge(
                "In production: 'Approve' triggers a Slack webhook POST that sends "
                "the email via SendGrid and logs the action to HubSpot CRM. "
                "'Reject' can optionally trigger a notification to the detection engine "
                "to adjust the confidence threshold for this opportunity type."
            )

        elif status == "approved":
            st.info(
                f"Approved by **{p.get('approved_by', 'account_manager')}** — "
                f"ready to send. In production, this would be sent automatically "
                f"within the next dispatch window."
            )

            # Allow un-approving back to draft
            if st.button("Revoke Approval", key=f"revoke_{p['id']}"):
                from src.db.schema import get_connection
                conn = get_connection()
                conn.execute(
                    "UPDATE proposals SET status='draft', updated_at=? WHERE id=?",
                    (datetime.now().isoformat(), p["id"]),
                )
                conn.commit()
                conn.close()
                st.rerun()

        elif status in ("sent", "accepted"):
            st.success(
                f"Sent on **{(p.get('sent_at') or p.get('updated_at', ''))[:10]}**. "
                f"Awaiting client response."
            )

        elif status == "rejected":
            st.error("Rejected. A new proposal will be generated on the next daily run.")


def _render_proposal_log(proposals: list[dict]) -> None:
    """Compact table view of all proposals."""
    if not proposals:
        return

    rows = []
    for p in proposals:
        rows.append({
            "Client":       p["client_name"],
            "Opportunity":  OPPORTUNITY_LABELS.get(p["opportunity_type"], p["opportunity_type"]),
            "Score":        p["score"] or 0,
            "Price ($)":    p["suggested_price"],
            "Status":       p["status"].replace("_", " ").title(),
            "Created":      (p.get("created_at") or "")[:10],
            "Demo":         bool(p.get("is_demo_scenario")),
        })

    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        column_config={
            "Score":    st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.0f"),
            "Price ($)": st.column_config.NumberColumn("Price ($)", format="$%.0f"),
            "Demo":     st.column_config.CheckboxColumn("Demo"),
        },
        hide_index=True,
        use_container_width=True,
    )


# ── Main render ────────────────────────────────────────────────────────────────

def render() -> None:
    page_header(
        "Proposal Review & Approval",
        "The agent writes personalized proposals based on detected opportunities. "
        "A human must approve each proposal before it is sent to the client.",
    )

    # ── On-demand generation panel ─────────────────────────────────────────────
    _render_generate_panel()
    st.divider()

    # ── Load proposals ─────────────────────────────────────────────────────────
    proposals = get_all_proposals()

    if not proposals:
        st.info(
            "No proposals yet. Use the 'Generate Proposals' panel above "
            "or run `python scripts/daily_job.py` to trigger the pipeline."
        )
        return

    # ── KPIs ──────────────────────────────────────────────────────────────────
    _render_kpis(proposals)
    st.divider()

    # ── Filters ───────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        status_options = ["All"] + sorted({p["status"] for p in proposals})
        sel_status = st.selectbox(
            "Status",
            status_options,
            format_func=lambda s: "All Statuses" if s == "All" else _STATUS_LABELS.get(s, s.title()),
        )
    with col2:
        opp_options = ["All"] + sorted({p["opportunity_type"] for p in proposals})
        sel_opp = st.selectbox(
            "Opportunity Type",
            opp_options,
            format_func=lambda t: "All Types" if t == "All" else OPPORTUNITY_LABELS.get(t, t),
        )
    with col3:
        demo_only = st.toggle("Demo clients only", value=False)

    # ── Apply filters ─────────────────────────────────────────────────────────
    filtered = proposals
    if sel_status != "All":
        filtered = [p for p in filtered if p["status"] == sel_status]
    if sel_opp != "All":
        filtered = [p for p in filtered if p["opportunity_type"] == sel_opp]
    if demo_only:
        filtered = [p for p in filtered if p.get("is_demo_scenario")]

    # ── View toggle ───────────────────────────────────────────────────────────
    view = st.radio("View", ["Cards", "Log"], horizontal=True, label_visibility="collapsed")
    st.divider()

    if view == "Cards":
        if not filtered:
            st.info("No proposals match the current filters.")
        else:
            # Prioritise drafts first so they're easy to action
            priority_order = {"draft": 0, "approved": 1, "sent": 2, "accepted": 3, "rejected": 4}
            filtered_sorted = sorted(filtered, key=lambda p: (priority_order.get(p["status"], 5), -(p["score"] or 0)))
            for idx, p in enumerate(filtered_sorted):
                _render_proposal_card(p, idx)
    else:
        _render_proposal_log(filtered)

    st.divider()

    # ── Reasoning chain explainer ──────────────────────────────────────────────
    with st.expander("How proposals are generated — reasoning chain"):
        st.markdown("""
        Each proposal follows this pipeline:

        ```
        1. Detection Engine (rules.py)
               ↓  detects opportunity + rationale string
        2. Metric Snapshot (data_sources/*.py)
               ↓  latest CTR, bounce rate, ROAS, email open rate, etc.
        3. Context Builder (proposal_generator.py)
               ↓  fills template placeholders with real numbers
        4. LLM Call (OpenAI / Claude Haiku)
               ↓  generates a personalized insight paragraph
               ↓  fallback: deterministic template if no API key
        5. Template Renderer
               ↓  assembles subject + body
        6. Persistence
               ↓  saves to proposals table (status='draft')
               ↓  exports Markdown file to data/exports/proposals/
        7. This UI
               ↓  account manager reviews and approves/rejects
        8. [Sprint 4] Email send via SendGrid API
        ```

        **In production**, step 4 uses GPT-3.5-turbo or Claude Haiku.
        The LLM prompt is grounded in the client's specific metrics to prevent
        hallucination and ensure the numbers in the proposal are accurate.
        """)
