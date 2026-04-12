"""
Shared UI components used across Streamlit pages.
"""

import streamlit as st


def production_badge(note: str) -> None:
    """Render an 'In Production' info tooltip."""
    with st.expander("In Production", icon="🔗"):
        st.caption(note)


def score_bar(score: float, label: str = "") -> None:
    """Render a colored progress bar for an opportunity score."""
    if score >= 80:
        color = "red"
        tier  = "HIGH"
    elif score >= 60:
        color = "orange"
        tier  = "MEDIUM"
    else:
        color = "gray"
        tier  = "LOW"

    bar_html = f"""
    <div style="margin: 4px 0;">
      <div style="display:flex; align-items:center; gap:8px;">
        <div style="flex:1; background:#e0e0e0; border-radius:4px; height:12px; overflow:hidden;">
          <div style="width:{score}%; background:{color}; height:100%; border-radius:4px;"></div>
        </div>
        <span style="font-size:0.85em; color:{color}; font-weight:600; min-width:90px;">
          {tier} &nbsp;{score:.0f}/100
        </span>
      </div>
      {"<small style='color:#888;'>"+label+"</small>" if label else ""}
    </div>
    """
    st.html(bar_html)


def slack_message_card(alert: dict) -> None:
    """
    Render a single alert as a simulated Slack message card.
    Matches the visual format of a real Slack Block Kit message.
    """
    score = alert.get("score", 0)
    if score >= 80:
        dot_color = "#E01E5A"  # red
    elif score >= 60:
        dot_color = "#ECB22E"  # yellow
    else:
        dot_color = "#2EB67D"  # green (low priority)

    label     = alert.get("label", alert.get("opportunity_type", ""))
    client    = alert.get("client_name", "Unknown")
    price     = alert.get("suggested_price", 0)
    ts        = alert.get("timestamp", "")[:16].replace("T", " ")

    slack_html = f"""
    <div style="
        border-left: 4px solid {dot_color};
        background: #1a1d21;
        border-radius: 6px;
        padding: 12px 16px;
        margin: 8px 0;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    ">
      <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
        <span style="font-weight:700; color:#d1d2d3; font-size:0.95em;">
          Hidden Opportunities Agent
        </span>
        <span style="
          background: {dot_color};
          color: white;
          font-size: 0.7em;
          padding: 1px 6px;
          border-radius: 3px;
          font-weight: 600;
        ">APP</span>
        <span style="color:#666; font-size:0.8em;">{ts}</span>
      </div>
      <div style="color:#e8e8e8; font-size:1em; font-weight:600; margin-bottom:4px;">
        New Opportunity Detected
      </div>
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:4px 16px; margin:8px 0;">
        <div><span style="color:#999; font-size:0.8em;">CLIENT</span><br>
             <span style="color:#d1d2d3;">{client}</span></div>
        <div><span style="color:#999; font-size:0.8em;">OPPORTUNITY</span><br>
             <span style="color:#d1d2d3;">{label}</span></div>
        <div><span style="color:#999; font-size:0.8em;">CONFIDENCE</span><br>
             <span style="color:{dot_color}; font-weight:600;">{score:.0f}%</span></div>
        <div><span style="color:#999; font-size:0.8em;">PRICE</span><br>
             <span style="color:#d1d2d3;">${price:,.0f}</span></div>
      </div>
    </div>
    """
    st.html(slack_html)


def demo_banner() -> None:
    """Show a persistent demo mode banner at the top of every page."""
    st.html("""
    <div style="
        background: linear-gradient(90deg, #1a1d21, #2d3139);
        border: 1px solid #404449;
        border-radius: 6px;
        padding: 8px 16px;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 10px;
    ">
      <span style="color: #ECB22E; font-weight: 700; font-size:0.85em;">DEMO MODE</span>
      <span style="color: #888; font-size: 0.82em;">
        All data is synthetic. In production, each panel connects to the real API
        shown in the "In Production" expanders.
      </span>
    </div>
    """)
