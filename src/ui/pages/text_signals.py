"""
Sprint 6 — Text Signals Dashboard.

Visualizes the NLP pipeline that converts unstructured client communications
(emails, call transcripts, CRM notes) into structured opportunity signals.

Sections
--------
  1. Pipeline Diagram   — visual flow: Email → Extraction → Signals → ML Update
  2. Signal Overview    — KPI row + signal type distribution
  3. Email Browser      — per-client email viewer with extracted signal badges
  4. Signal Matrix      — all-clients heatmap of signal flags
  5. Urgency Alerts     — red alert cards for churn/urgency clients
  6. Process Button     — trigger the NLP pipeline and show results

"In Production" annotations on every integration point.
"""

from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.nlp.pipeline import run_pipeline, get_pipeline_summary
from src.data_sources.text_signals import (
    get_client_signals, get_signal_summary,
    get_all_signal_summaries, get_urgency_alerts, count_signals_by_type,
)
from src.data_sources.crm import get_all_clients
from src.ui.components import production_badge


# ── Helpers ───────────────────────────────────────────────────────────────────

_SOURCE_ICONS = {
    "email":           "📧",
    "call_transcript": "📞",
    "crm_note":        "📋",
}

_SIGNAL_COLORS = {
    "mentions_price":   "#ECB22E",
    "asks_for_results": "#36C5F0",
    "churn_risk":       "#E01E5A",
    "urgency_signal":   "#FF6B35",
    "interest_signal":  "#2EB67D",
}

_SIGNAL_LABELS = {
    "mentions_price":   "💰 Price Concern",
    "asks_for_results": "📊 Asks for Results",
    "churn_risk":       "🚨 Churn Risk",
    "urgency_signal":   "⚡ Urgency",
    "interest_signal":  "✅ Interest Signal",
}


def _sentiment_color(s: float | None) -> str:
    if s is None:
        return "#666"
    if s > 0.2:
        return "#2EB67D"
    if s < -0.2:
        return "#E01E5A"
    return "#ECB22E"


def _signal_badge(label: str, color: str) -> str:
    return (
        f'<span style="background:{color};color:#fff;font-size:0.72em;'
        f'padding:2px 8px;border-radius:10px;margin:2px;font-weight:600;">'
        f'{label}</span>'
    )


# ── Section 1: Pipeline diagram ───────────────────────────────────────────────

def _render_pipeline_diagram() -> None:
    st.subheader("NLP Processing Pipeline")
    st.caption(
        "How unstructured client communications become ML features "
        "that improve opportunity detection accuracy."
    )

    st.html("""
    <div style="display:flex;align-items:center;gap:0;flex-wrap:wrap;
                background:#1a1d21;border-radius:8px;padding:20px 16px;
                margin-bottom:8px;font-family:-apple-system,sans-serif;">

      <!-- Step 1 -->
      <div style="text-align:center;padding:12px 16px;background:#2d3139;
                  border-radius:6px;min-width:130px;">
        <div style="font-size:1.6em;">📧 📞 📋</div>
        <div style="color:#d1d2d3;font-size:0.85em;font-weight:600;margin-top:4px;">
          Client Comms</div>
        <div style="color:#888;font-size:0.72em;">Email · Call · CRM</div>
      </div>

      <div style="color:#36C5F0;font-size:1.5em;padding:0 8px;">→</div>

      <!-- Step 2 -->
      <div style="text-align:center;padding:12px 16px;background:#2d3139;
                  border-radius:6px;min-width:130px;">
        <div style="font-size:1.6em;">🔍</div>
        <div style="color:#d1d2d3;font-size:0.85em;font-weight:600;margin-top:4px;">
          Text Extraction</div>
        <div style="color:#888;font-size:0.72em;">Keyword + LLM</div>
      </div>

      <div style="color:#36C5F0;font-size:1.5em;padding:0 8px;">→</div>

      <!-- Step 3 -->
      <div style="text-align:center;padding:12px 16px;background:#2d3139;
                  border-radius:6px;min-width:130px;">
        <div style="font-size:1.6em;">📊</div>
        <div style="color:#d1d2d3;font-size:0.85em;font-weight:600;margin-top:4px;">
          Signal Flags</div>
        <div style="color:#888;font-size:0.72em;">
          sentiment · price · churn<br>urgency · interest</div>
      </div>

      <div style="color:#36C5F0;font-size:1.5em;padding:0 8px;">→</div>

      <!-- Step 4 -->
      <div style="text-align:center;padding:12px 16px;background:#2d3139;
                  border-radius:6px;min-width:130px;">
        <div style="font-size:1.6em;">🤖</div>
        <div style="color:#d1d2d3;font-size:0.85em;font-weight:600;margin-top:4px;">
          ML Feature Update</div>
        <div style="color:#888;font-size:0.72em;">5 new features → model</div>
      </div>

      <div style="color:#36C5F0;font-size:1.5em;padding:0 8px;">→</div>

      <!-- Step 5 -->
      <div style="text-align:center;padding:12px 16px;background:#2d3139;
                  border-radius:6px;min-width:130px;">
        <div style="font-size:1.6em;">🎯</div>
        <div style="color:#d1d2d3;font-size:0.85em;font-weight:600;margin-top:4px;">
          Better Scores</div>
        <div style="color:#888;font-size:0.72em;">+accuracy · +context</div>
      </div>

    </div>
    """)

    production_badge(
        "Production: Emails are ingested via Gmail API (OAuth2) every 30 minutes. "
        "Call recordings are transcribed by OpenAI Whisper (local) or AssemblyAI. "
        "CRM notes are pulled from HubSpot API v3 /crm/v3/objects/notes. "
        "LLM extraction uses claude-haiku-4-5 with a structured JSON output prompt "
        "(temperature=0 for determinism). Falls back to keyword matching "
        "if the API call fails or takes > 3 seconds."
    )


# ── Section 2: Signal overview ─────────────────────────────────────────────────

def _render_signal_overview() -> None:
    db_stats = get_pipeline_summary()
    counts   = count_signals_by_type()

    st.subheader("Signal Overview")

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Total Texts", db_stats["total_signals"])
    k2.metric("Processed",   db_stats["processed"])
    k3.metric("Pending",     db_stats["unprocessed"])
    k4.metric("Churn Flags", db_stats["churn_count"],
              delta=f"⚠️ {db_stats['churn_count']}" if db_stats["churn_count"] else None,
              delta_color="inverse")
    k5.metric("Urgency",     db_stats["urgency_count"])
    k6.metric("Price Mentions", counts.get("price_mentions", 0))

    if db_stats["processed"] == 0:
        st.info(
            "No signals have been processed yet. "
            "Click **Process Emails Now** below to run the NLP pipeline."
        )
        return

    # Signal distribution bar chart
    signal_counts = {
        "Price Concern":    counts.get("price_mentions", 0),
        "Asks for Results": counts.get("results_queries", 0),
        "Churn Risk":       counts.get("churn_flags", 0),
        "Urgency":          counts.get("urgency_flags", 0),
        "Interest":         counts.get("interest_flags", 0),
    }

    labels = list(signal_counts.keys())
    values = list(signal_counts.values())
    colors = ["#ECB22E", "#36C5F0", "#E01E5A", "#FF6B35", "#2EB67D"]

    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker_color=colors,
        text=values,
        textposition="outside",
    ))
    fig.update_layout(
        title="Signal Type Distribution",
        yaxis_title="# Texts with Signal",
        template="plotly_dark",
        height=250,
        margin=dict(t=40, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)

    production_badge(
        "Production: Signal counts are computed from the text_signals table and "
        "cached in a Redis layer (TTL: 10 minutes) to avoid repeated full-table scans. "
        "A Slack digest is posted every morning summarising the churn risk count."
    )


# ── Section 3: Email browser ──────────────────────────────────────────────────

def _render_email_browser() -> None:
    st.subheader("Email Browser")
    st.caption("Select a client to view their communications and extracted signals.")

    clients = get_all_clients()
    if not clients:
        st.info("No clients found. Run `python scripts/seed_db.py` first.")
        return

    client_map = {c["name"]: c["id"] for c in clients}
    selected_name = st.selectbox("Client", list(client_map.keys()))
    client_id = client_map[selected_name]

    signals = get_client_signals(client_id)
    summary = get_signal_summary(client_id)

    if not signals:
        st.info(f"No communications found for {selected_name}. Process emails first.")
        return

    # Client signal summary bar
    badge_html = ""
    for key, label in _SIGNAL_LABELS.items():
        if summary.get(key):
            badge_html += _signal_badge(label, _SIGNAL_COLORS[key])

    sent_color = _sentiment_color(summary.get("sentiment_score"))
    st.html(
        f'<div style="background:#1a1d21;border-radius:6px;padding:10px 14px;'
        f'border-left:4px solid {sent_color};margin-bottom:10px;">'
        f'<span style="color:#d1d2d3;font-weight:600;">{selected_name}</span>'
        f'<span style="color:{sent_color};margin-left:12px;font-size:0.85em;">'
        f'Sentiment: {summary.get("sentiment_score", 0):.2f}</span>'
        f'<span style="margin-left:12px;">{badge_html}</span>'
        f'</div>'
    )

    is_processed = any(s.get("sentiment") is not None for s in signals)
    if not is_processed:
        st.caption("Signals not yet extracted for this client. Run the pipeline first.")

    for sig in signals:
        source_icon = _SOURCE_ICONS.get(sig.get("source", ""), "📄")
        source_label = sig.get("source", "unknown").replace("_", " ").title()

        badges = ""
        if sig.get("sentiment") is not None:
            s = sig["sentiment"]
            sc = _sentiment_color(s)
            badges += _signal_badge(f"Sentiment: {s:.2f}", sc)
        for key, label in _SIGNAL_LABELS.items():
            if sig.get(key):
                badges += _signal_badge(label, _SIGNAL_COLORS[key])

        st.html(
            f'<div style="background:#1a1d21;border:1px solid #2d3139;border-radius:6px;'
            f'padding:12px 14px;margin:6px 0;">'
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">'
            f'<span style="font-size:1.2em;">{source_icon}</span>'
            f'<span style="color:#888;font-size:0.82em;">{source_label}</span>'
            f'<span style="color:#555;font-size:0.78em;margin-left:auto;">'
            f'{(sig.get("processed_at","")[:16]).replace("T"," ")}</span>'
            f'</div>'
            f'<div style="color:#d1d2d3;font-size:0.88em;line-height:1.5;margin-bottom:8px;">'
            f'"{sig.get("raw_text","")}"</div>'
            f'<div>{badges}</div>'
            f'</div>'
        )

    production_badge(
        "Production: Each email is stored with its Message-ID to prevent duplicates. "
        "Full thread context (reply chain) is preserved so the LLM can analyze "
        "the complete conversation history, not just individual messages. "
        "PII (names, email addresses) is stripped before LLM processing per GDPR."
    )


# ── Section 4: Signal matrix ──────────────────────────────────────────────────

def _render_signal_matrix() -> None:
    st.subheader("Signal Matrix — All Clients")
    st.caption(
        "Each row is a client. Each column is a signal type. "
        "Color = signal active (darker = higher risk). "
        "Sort by Churn Risk to prioritize outreach."
    )

    clients = {c["id"]: c["name"] for c in get_all_clients()}
    summaries = get_all_signal_summaries()

    if not summaries:
        st.info("No signal summaries found. Process emails first.")
        return

    rows = []
    for s in summaries:
        rows.append({
            "Client":        clients.get(s["client_id"], s["client_id"]),
            "Sentiment":     round(s.get("sentiment_score", 0), 2),
            "Price Concern": bool(s.get("mentions_price")),
            "Asks Results":  bool(s.get("asks_for_results")),
            "Churn Risk":    bool(s.get("churn_risk")),
            "Urgency":       bool(s.get("urgency_signal")),
            "Interest":      bool(s.get("interest_signal")),
            "# Signals":     s.get("n_signals", 0),
        })

    df = pd.DataFrame(rows).sort_values("Churn Risk", ascending=False)

    st.dataframe(
        df,
        column_config={
            "Sentiment":     st.column_config.NumberColumn("Sentiment", format="%.2f"),
            "Price Concern": st.column_config.CheckboxColumn("💰 Price"),
            "Asks Results":  st.column_config.CheckboxColumn("📊 Results"),
            "Churn Risk":    st.column_config.CheckboxColumn("🚨 Churn"),
            "Urgency":       st.column_config.CheckboxColumn("⚡ Urgency"),
            "Interest":      st.column_config.CheckboxColumn("✅ Interest"),
        },
        hide_index=True,
        use_container_width=True,
    )

    production_badge(
        "Production: This matrix is exported as a CSV every morning and "
        "attached to the team's Slack digest. High-churn clients are flagged "
        "and assigned to the account manager with the lowest current caseload. "
        "The reactivation opportunity score gets a +15 bonus when churn_risk=1."
    )


# ── Section 5: Urgency alerts ─────────────────────────────────────────────────

def _render_urgency_alerts() -> None:
    st.subheader("Urgency Alerts")
    st.caption(
        "Clients where churn or urgency signals were detected. "
        "These require immediate outreach by an account manager."
    )

    alerts = get_urgency_alerts()

    if not alerts:
        st.success("No urgency or churn alerts detected. All clients look healthy.")
        return

    for alert in alerts:
        churn   = bool(alert.get("churn_risk"))
        urgency = bool(alert.get("urgency_signal"))
        border  = "#E01E5A" if churn else "#FF6B35"
        icon    = "🚨" if churn else "⚡"
        label   = "CHURN RISK" if churn else "URGENCY"
        badge_color = "#E01E5A" if churn else "#FF6B35"

        sentiment_val = alert.get("avg_sentiment")
        if sentiment_val is not None:
            sent_str = f"Avg sentiment: {float(sentiment_val):.2f}"
        else:
            sent_str = "Sentiment: pending"

        tags = _signal_badge(label, badge_color)
        if churn and urgency:
            tags += _signal_badge("⚡ URGENCY", "#FF6B35")

        # Snippet from most recent communication
        texts = (alert.get("combined_text") or "").split(" ||| ")
        snippet = texts[0][:120] + "…" if texts and len(texts[0]) > 120 else (texts[0] if texts else "")

        st.html(
            f'<div style="background:#1a1d21;border-left:4px solid {border};'
            f'border-radius:6px;padding:14px 18px;margin:8px 0;">'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">'
            f'<span style="font-size:1.3em;">{icon}</span>'
            f'<span style="color:#d1d2d3;font-weight:600;font-size:1em;">'
            f'{alert.get("client_name","")}</span>'
            f'<span style="color:#888;font-size:0.82em;">· {alert.get("industry","")}</span>'
            f'<span style="margin-left:auto;">{tags}</span>'
            f'</div>'
            f'<div style="color:#888;font-size:0.82em;margin-bottom:4px;">'
            f'Account manager: <strong style="color:#d1d2d3">'
            f'{alert.get("account_manager","—")}</strong>'
            f' · {sent_str}</div>'
            f'<div style="color:#aaa;font-size:0.85em;font-style:italic;">'
            f'"{snippet}"</div>'
            f'</div>'
        )

    production_badge(
        "Production: When churn_risk=1 is first detected for a client, "
        "the system immediately sends a Slack DM to the account manager "
        "with a suggested reactivation message draft. If no action is taken "
        "within 48 hours, an escalation email goes to the team lead. "
        "These alerts are deduplicated: a client only appears once per 7-day window."
    )


# ── Process panel ─────────────────────────────────────────────────────────────

def _render_process_panel() -> None:
    with st.container(border=True):
        c1, c2 = st.columns([4, 1])
        with c1:
            db_stats = get_pipeline_summary()
            unproc = db_stats["unprocessed"]
            total  = db_stats["total_signals"]
            if unproc > 0:
                st.markdown(
                    f"**{unproc} of {total} texts** still need signal extraction. "
                    "Click to run the NLP pipeline."
                )
            else:
                st.markdown(
                    f"All **{total} texts** are processed. "
                    "Click to reprocess with latest settings."
                )
        with c2:
            if st.button("Process Emails Now", type="primary", use_container_width=True):
                with st.spinner("Running NLP pipeline…"):
                    result = run_pipeline(
                        reprocess_all=(unproc == 0),
                        use_llm=False,
                        verbose=False,
                    )
                st.success(
                    f"Done! Processed {result['total_processed']} texts · "
                    f"Churn alerts: {result['churn_alerts']} · "
                    f"Urgency alerts: {result['urgency_alerts']}"
                )
                st.rerun()

        production_badge(
            "Production: This pipeline runs automatically at 07:00 and 19:00 via "
            "cron. Manual trigger is available here and via a Slack slash command "
            "(/process-signals). LLM extraction is toggled with DEMO_MODE=false + API key."
        )


# ── Main render ────────────────────────────────────────────────────────────────

def render() -> None:
    st.title("Text Signals — Active Listener")
    st.caption(
        "Sprint 6: the agent reads client emails, call transcripts, and CRM notes "
        "to detect subtle signals that structured metrics miss. "
        "These signals become new ML features, improving acceptance probability estimates."
    )

    production_badge(
        "Sprint 6 — NLP pipeline powered by keyword extraction (demo) + optional LLM "
        "(claude-haiku-4-5 or GPT-3.5-turbo in production). Signals are stored in the "
        "text_signals table and joined into the ML feature matrix at training time. "
        "The 5 new features (sentiment, price concern, results interest, churn risk, urgency) "
        "expand the Random Forest from 13 to 18 features."
    )

    st.divider()

    _render_pipeline_diagram()

    st.divider()

    _render_process_panel()

    st.divider()

    _render_signal_overview()

    st.divider()

    tab1, tab2, tab3 = st.tabs(["Email Browser", "Signal Matrix", "Urgency Alerts"])

    with tab1:
        _render_email_browser()

    with tab2:
        _render_signal_matrix()

    with tab3:
        _render_urgency_alerts()
