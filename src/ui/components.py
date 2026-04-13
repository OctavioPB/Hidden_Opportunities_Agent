"""
Shared UI components used across Streamlit pages.
"""

import streamlit as st


# ── OPB Brand CSS injection ────────────────────────────────────────────────────

_BRAND_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,300&family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;0,9..144,600;1,9..144,300;1,9..144,400&display=swap');

:root {
  --primary:    #003366;
  --primary-80: #1A4D80;
  --primary-60: #336699;
  --primary-30: #99BBDD;
  --primary-10: #E0EAF4;
  --gold:       #C8982A;
  --gold-light: #E8C46A;
  --dark:       #1C1C2E;
  --mid:        #6B7280;
  --light:      #F4F6F9;
  --white:      #FFFFFF;
}

/* ── Page ── */
.stApp {
  background-color: #F4F6F9 !important;
}
.block-container {
  padding-top: 2.5rem !important;
  padding-left: 4rem !important;
  padding-right: 4rem !important;
  padding-bottom: 4rem !important;
  max-width: 1400px !important;
}

/* ── Sidebar shell — cover all Streamlit wrappers ── */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div,
section[data-testid="stSidebar"] > div > div,
section[data-testid="stSidebar"] > div > div > div,
[data-testid="stSidebarContent"],
[data-testid="stSidebarContent"] > div,
[data-testid="stSidebarUserContent"],
[data-testid="stSidebarUserContent"] > div {
  background: #003366 !important;
}
section[data-testid="stSidebar"] {
  border-right: 1px solid rgba(255,255,255,.08) !important;
  padding: 0 !important;
}
section[data-testid="stSidebar"] > div:first-child {
  padding: 0 !important;
}
section[data-testid="stSidebar"] .stMarkdown p {
  color: rgba(255,255,255,.72) !important;
  font-family: 'Plus Jakarta Sans', sans-serif !important;
}
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p,
section[data-testid="stSidebar"] [data-testid="stCaption"] p {
  color: rgba(255,255,255,.38) !important;
  font-size: 11px !important;
  line-height: 1.7 !important;
  padding: 0 20px !important;
}
section[data-testid="stSidebar"] hr {
  border: none !important;
  height: 1px !important;
  background: rgba(255,255,255,.12) !important;
  margin: 8px 0 !important;
}
section[data-testid="stSidebar"] .stDivider,
section[data-testid="stSidebar"] [data-testid="stDivider"] {
  margin: 6px 0 !important;
}
section[data-testid="stSidebar"] .stDivider hr,
section[data-testid="stSidebar"] [data-testid="stDivider"] hr {
  background: rgba(255,255,255,.12) !important;
}

/* ── Sidebar nav buttons ── */
section[data-testid="stSidebar"] .stButton {
  width: 100% !important;
}
section[data-testid="stSidebar"] .stButton > button {
  background: transparent !important;
  border: none !important;
  border-left: 3px solid transparent !important;
  border-radius: 6px !important;
  color: rgba(255,255,255,.72) !important;
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  padding: 9px 14px 9px 13px !important;
  text-align: left !important;
  width: 100% !important;
  margin: 1px 0 !important;
  transition: background .15s ease, border-color .15s ease !important;
  box-shadow: none !important;
  letter-spacing: .2px !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
  background: rgba(255,255,255,.08) !important;
  border-left-color: rgba(255,255,255,.2) !important;
  color: #FFFFFF !important;
}
/* Active nav button — gold accent */
section[data-testid="stSidebar"] .stButton > button[kind="primary"],
section[data-testid="stSidebar"] .stButton > button[data-testid="baseButton-primary"] {
  background: rgba(200,152,42,.15) !important;
  border-left: 3px solid #C8982A !important;
  color: #FFFFFF !important;
  font-weight: 600 !important;
  box-shadow: none !important;
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover,
section[data-testid="stSidebar"] .stButton > button[data-testid="baseButton-primary"]:hover {
  background: rgba(200,152,42,.22) !important;
}

/* ── Headings ── */
.stApp h1 {
  font-family: 'Fraunces', Georgia, serif !important;
  font-weight: 400 !important;
  font-size: 32px !important;
  color: #003366 !important;
  letter-spacing: -0.5px !important;
  line-height: 1.2 !important;
  margin-top: 0 !important;
  margin-bottom: 6px !important;
}
.stApp h2 {
  font-family: 'Fraunces', Georgia, serif !important;
  font-weight: 300 !important;
  font-size: 22px !important;
  color: #003366 !important;
  line-height: 1.3 !important;
  margin-top: 2rem !important;
  margin-bottom: 8px !important;
}
.stApp h3 {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-weight: 600 !important;
  font-size: 15px !important;
  color: #003366 !important;
  letter-spacing: .1px !important;
  margin-top: 1.5rem !important;
  margin-bottom: 6px !important;
}

/* ── Body text ── */
.stApp p, .stApp li {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 15px !important;
  line-height: 1.7 !important;
  color: #1C1C2E !important;
}

/* ── Captions ── */
.stApp [data-testid="stCaptionContainer"] p,
.stApp [data-testid="stCaption"] p {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 12px !important;
  color: #6B7280 !important;
  line-height: 1.6 !important;
}

/* ── Section spacing ── */
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {
  gap: 1.2rem !important;
}

/* ── Metric cards ── */
[data-testid="metric-container"] {
  background: #FFFFFF !important;
  border-radius: 12px !important;
  border-top: 3px solid #003366 !important;
  border-left: 1px solid #E0EAF4 !important;
  border-right: 1px solid #E0EAF4 !important;
  border-bottom: 1px solid #E0EAF4 !important;
  box-shadow: 0 2px 8px rgba(0,51,102,.06) !important;
  padding: 22px 24px 20px !important;
}
[data-testid="stMetricValue"] {
  font-family: 'Fraunces', Georgia, serif !important;
  font-weight: 300 !important;
  font-size: 28px !important;
  color: #003366 !important;
}
[data-testid="stMetricLabel"] div,
[data-testid="stMetricLabel"] p {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 10px !important;
  font-weight: 500 !important;
  text-transform: uppercase !important;
  letter-spacing: 2px !important;
  color: #6B7280 !important;
}
[data-testid="stMetricDelta"] {
  color: #C8982A !important;
  font-size: 13px !important;
}

/* ── Buttons ── */
.stButton > button {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  border-radius: 8px !important;
  border: 1px solid #99BBDD !important;
  color: #003366 !important;
  background: #FFFFFF !important;
  padding: 6px 18px !important;
  transition: all .15s ease !important;
  letter-spacing: .3px !important;
}
.stButton > button:hover {
  background: #E0EAF4 !important;
  border-color: #003366 !important;
}
.stButton > button[data-testid="baseButton-primary"] {
  background: #003366 !important;
  color: #FFFFFF !important;
  border-color: #003366 !important;
}
.stButton > button[data-testid="baseButton-primary"]:hover {
  background: #1A4D80 !important;
}

/* ── Tabs ── */
[data-baseweb="tab-list"] {
  background: transparent !important;
  border-bottom: 1px solid #E0EAF4 !important;
  gap: 0 !important;
}
[data-baseweb="tab"] {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 11px !important;
  font-weight: 600 !important;
  letter-spacing: 1.5px !important;
  text-transform: uppercase !important;
  color: #6B7280 !important;
  background: transparent !important;
  padding: 10px 20px !important;
  border-radius: 6px 6px 0 0 !important;
  border-bottom: 2px solid transparent !important;
  transition: color .15s, border-color .15s !important;
}
[data-baseweb="tab"][aria-selected="true"] {
  color: #003366 !important;
  border-bottom: 2px solid #C8982A !important;
  background: rgba(0,51,102,.04) !important;
}

/* ── Expanders ── */
[data-testid="stExpander"] {
  background: #FFFFFF !important;
  border-radius: 8px !important;
  border: 1px solid #E0EAF4 !important;
  box-shadow: none !important;
}
[data-testid="stExpander"] summary {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  color: #003366 !important;
  padding: 10px 16px !important;
}

/* ── Containers with border ── */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: #FFFFFF !important;
  border-radius: 12px !important;
  border: 1px solid #E0EAF4 !important;
  box-shadow: 0 1px 3px rgba(0,51,102,.05) !important;
}

/* ── Dividers ── */
.stDivider hr,
[data-testid="stDivider"] hr {
  border: none !important;
  height: 1px !important;
  background: linear-gradient(90deg, #E0EAF4, transparent) !important;
}
.stDivider,
[data-testid="stDivider"] {
  margin: 28px 0 !important;
}

/* ── Form labels ── */
[data-testid="stSelectbox"] label p,
[data-testid="stRadio"] label p,
[data-testid="stSlider"] label p,
[data-testid="stToggle"] label p,
[data-testid="stTextArea"] label p {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 11px !important;
  font-weight: 500 !important;
  text-transform: uppercase !important;
  letter-spacing: 2px !important;
  color: #6B7280 !important;
}

/* ── Info / success / warning / error alerts ── */
[data-testid="stAlert"] {
  border-radius: 8px !important;
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 14px !important;
}

/* ── Blockquote / callout ── */
.stApp blockquote {
  border-left: 3px solid #C8982A !important;
  background: #F4F6F9 !important;
  padding: 10px 16px !important;
  border-radius: 0 8px 8px 0 !important;
  color: #1C1C2E !important;
  font-style: italic !important;
}

/* ── Code blocks ── */
.stApp code {
  font-family: 'Courier New', monospace !important;
  font-size: 13px !important;
  background: #E0EAF4 !important;
  color: #003366 !important;
  padding: 2px 6px !important;
  border-radius: 4px !important;
}
.stApp pre code {
  background: transparent !important;
  padding: 0 !important;
}

/* ── Tables (markdown) ── */
.stApp table {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 14px !important;
  border-collapse: collapse !important;
  width: 100% !important;
}
.stApp table thead tr {
  background: #003366 !important;
}
.stApp table thead th {
  color: #FFFFFF !important;
  font-size: 10px !important;
  text-transform: uppercase !important;
  letter-spacing: 2px !important;
  padding: 12px 16px !important;
  font-weight: 500 !important;
}
.stApp table tbody tr:nth-child(even) {
  background: #E0EAF4 !important;
}
.stApp table tbody tr:nth-child(odd) {
  background: #FFFFFF !important;
}
.stApp table td {
  padding: 10px 16px !important;
  border: 1px solid #E0EAF4 !important;
  color: #1C1C2E !important;
}

/* ── DataFrames ── */
[data-testid="stDataFrame"] {
  border-radius: 8px !important;
  border: 1px solid #E0EAF4 !important;
}

/* ── Top toolbar (header) ── */
[data-testid="stHeader"] {
  background: rgba(244,246,249,.95) !important;
  backdrop-filter: blur(8px) !important;
  border-bottom: 1px solid #E0EAF4 !important;
}

/* ── Spinner ── */
[data-testid="stSpinner"] {
  color: #003366 !important;
}

/* ── Selectbox / input focus ring ── */
[data-baseweb="select"] [data-baseweb="select-container"],
[data-baseweb="input"] {
  border-color: #99BBDD !important;
  border-radius: 8px !important;
}
</style>
"""


def inject_brand_css() -> None:
    """Inject the OPB brand design system CSS into the Streamlit app."""
    st.markdown(_BRAND_CSS, unsafe_allow_html=True)


def opb_sidebar_header() -> None:
    """Render the OPB monogram navigation header inside the sidebar."""
    st.html("""
    <div style="
      padding: 18px 20px 16px;
      border-bottom: 1px solid rgba(255,255,255,.08);
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 4px;
    ">
      <span style="
        font-family: 'Fraunces', Georgia, serif;
        font-size: 24px;
        letter-spacing: -0.5px;
        line-height: 1;
        font-weight: 400;
      ">
        <span style="color:#FFFFFF;">O</span><span style="color:#E8C46A;font-style:italic;">PB</span>
      </span>
      <span style="
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 9px;
        letter-spacing: 3px;
        text-transform: uppercase;
        color: rgba(255,255,255,.32);
        line-height: 1.5;
        text-align: right;
      ">Hidden<br>Opportunities</span>
    </div>
    """)


def eyebrow_label(text: str) -> None:
    """Render a gold eyebrow label above a section."""
    st.html(f"""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;margin-top:4px;">
      <div style="width:24px;height:1px;background:#C8982A;"></div>
      <span style="
        font-family:'Plus Jakarta Sans',sans-serif;
        font-size:9px;
        letter-spacing:4px;
        text-transform:uppercase;
        color:#C8982A;
        font-weight:500;
      ">{text}</span>
    </div>
    """)


def production_badge(note: str) -> None:
    """Render an 'In Production' info tooltip."""
    with st.expander("🔗 In Production"):
        st.caption(note)


def score_bar(score: float, label: str = "") -> None:
    """Render a colored progress bar using OPB semantic colors."""
    if score >= 80:
        color = "#27B97C"
        bg    = "#E0F7EF"
        tier  = "HIGH"
    elif score >= 60:
        color = "#F07020"
        bg    = "#FEF0E6"
        tier  = "MEDIUM"
    else:
        color = "#336699"
        bg    = "#E0EAF4"
        tier  = "LOW"

    bar_html = f"""
    <div style="margin:4px 0 8px;">
      <div style="display:flex;align-items:center;gap:10px;">
        <div style="flex:1;background:#E0EAF4;border-radius:4px;height:8px;overflow:hidden;">
          <div style="width:{score}%;background:{color};height:100%;border-radius:4px;transition:width .4s ease;"></div>
        </div>
        <span style="
          font-family:'Plus Jakarta Sans',sans-serif;
          font-size:10px;
          font-weight:600;
          letter-spacing:1px;
          text-transform:uppercase;
          background:{bg};
          color:{color};
          padding:2px 10px;
          border-radius:20px;
          min-width:110px;
          text-align:center;
        ">{tier} &nbsp;{score:.0f}/100</span>
      </div>
      {"<div style='font-family:Plus Jakarta Sans,sans-serif;font-size:11px;color:#6B7280;margin-top:3px;'>"+label+"</div>" if label else ""}
    </div>
    """
    st.html(bar_html)


def slack_message_card(alert: dict) -> None:
    """
    Render a single alert as a simulated Slack message card.
    Styled with OPB semantic colors on a dark card.
    """
    score = alert.get("score", 0)
    if score >= 80:
        accent = "#E03448"
        badge_bg = "#FDEAEA"
        badge_txt = "#7A1020"
    elif score >= 60:
        accent = "#F07020"
        badge_bg = "#FEF0E6"
        badge_txt = "#7A3800"
    else:
        accent = "#27B97C"
        badge_bg = "#E0F7EF"
        badge_txt = "#0D5C3A"

    label  = alert.get("label", alert.get("opportunity_type", ""))
    client = alert.get("client_name", "Unknown")
    price  = alert.get("suggested_price", 0)
    ts     = alert.get("timestamp", "")[:16].replace("T", " ")

    slack_html = f"""
    <div style="
        border-left: 4px solid {accent};
        background: #1C1C2E;
        border-radius: 8px;
        padding: 14px 18px;
        margin: 8px 0;
        font-family: 'Plus Jakarta Sans', sans-serif;
        box-shadow: 0 1px 4px rgba(0,0,0,.25);
    ">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
        <span style="font-weight:700;color:#F4F6F9;font-size:0.9em;letter-spacing:.2px;">
          Hidden Opportunities Agent
        </span>
        <span style="
          background:{accent};color:#fff;
          font-size:0.65em;padding:2px 7px;
          border-radius:3px;font-weight:700;
          letter-spacing:1px;
        ">ALERT</span>
        <span style="color:#6B7280;font-size:0.78em;margin-left:auto;">{ts}</span>
      </div>
      <div style="color:#E8C46A;font-size:0.82em;font-weight:600;margin-bottom:8px;
                  text-transform:uppercase;letter-spacing:1.5px;">
        New Opportunity Detected
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px 20px;">
        <div>
          <div style="color:#6B7280;font-size:0.72em;text-transform:uppercase;letter-spacing:2px;margin-bottom:2px;">Client</div>
          <div style="color:#F4F6F9;font-size:0.88em;">{client}</div>
        </div>
        <div>
          <div style="color:#6B7280;font-size:0.72em;text-transform:uppercase;letter-spacing:2px;margin-bottom:2px;">Opportunity</div>
          <div style="color:#F4F6F9;font-size:0.88em;">{label}</div>
        </div>
        <div>
          <div style="color:#6B7280;font-size:0.72em;text-transform:uppercase;letter-spacing:2px;margin-bottom:2px;">Confidence</div>
          <div style="
            display:inline-block;
            background:{badge_bg};color:{badge_txt};
            font-size:0.82em;font-weight:700;
            padding:2px 10px;border-radius:12px;
          ">{score:.0f}%</div>
        </div>
        <div>
          <div style="color:#6B7280;font-size:0.72em;text-transform:uppercase;letter-spacing:2px;margin-bottom:2px;">Price</div>
          <div style="color:#E8C46A;font-size:0.88em;font-weight:600;">${price:,.0f}</div>
        </div>
      </div>
    </div>
    """
    st.html(slack_html)


def demo_banner() -> None:
    """Show a persistent OPB-branded demo mode banner at the top of every page."""
    st.html("""
    <div style="
        background: #FFFFFF;
        border: 1px solid #E0EAF4;
        border-left: 4px solid #C8982A;
        border-radius: 8px;
        padding: 10px 18px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 12px;
        box-shadow: 0 1px 3px rgba(0,51,102,.06);
    ">
      <div style="
        font-family:'Plus Jakarta Sans',sans-serif;
        font-size:9px;
        font-weight:600;
        letter-spacing:3px;
        text-transform:uppercase;
        color:#C8982A;
        white-space:nowrap;
      ">Demo Mode</div>
      <div style="width:1px;height:16px;background:#E0EAF4;"></div>
      <div style="
        font-family:'Plus Jakarta Sans',sans-serif;
        font-size:12px;
        color:#6B7280;
        line-height:1.5;
      ">
        All data is synthetic. In production, each panel connects to the real API
        shown in the <strong style="color:#003366;">In Production</strong> expanders.
      </div>
    </div>
    """)
