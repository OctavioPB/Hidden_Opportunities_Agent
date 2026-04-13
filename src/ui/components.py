"""
Shared UI components — OPB brand design system v2.
"""

import streamlit as st


# ── OPB Brand CSS ──────────────────────────────────────────────────────────────

_BRAND_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,300&family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;0,9..144,600;1,9..144,300;1,9..144,400&display=swap');

/* ── Design tokens ── */
:root {
  --navy:        #003366;
  --navy-80:     #1A4D80;
  --navy-60:     #336699;
  --navy-10:     #E8EFF8;
  --gold:        #C8982A;
  --gold-light:  #E8C46A;
  --gold-pale:   #FBF5E6;
  --ink:         #0D1B2E;
  --body:        #374151;
  --muted:       #6B7280;
  --border:      #E2E8F0;
  --surface:     #F8FAFC;
  --white:       #FFFFFF;
  --bg:          #F1F5F9;
  --green:       #059669;
  --red:         #DC2626;
  --amber:       #D97706;
  --radius-lg:   14px;
  --radius-md:   10px;
  --radius-sm:   6px;
  --shadow-sm:   0 1px 3px rgba(0,0,0,.08), 0 1px 2px rgba(0,0,0,.04);
  --shadow-md:   0 4px 12px rgba(0,0,0,.08), 0 2px 4px rgba(0,0,0,.04);
}

/* ══════════════════════════════════
   PAGE LAYOUT
══════════════════════════════════ */
.stApp {
  background-color: #F1F5F9 !important;
}
.block-container {
  padding-top: 2rem !important;
  padding-left: 2.5rem !important;
  padding-right: 2.5rem !important;
  padding-bottom: 5rem !important;
  max-width: 1440px !important;
}

/* ══════════════════════════════════
   STREAMLIT TOP TOOLBAR
══════════════════════════════════ */
[data-testid="stHeader"] {
  background: rgba(241,245,249,.92) !important;
  backdrop-filter: blur(10px) !important;
  border-bottom: 1px solid #E2E8F0 !important;
  box-shadow: 0 1px 3px rgba(0,0,0,.04) !important;
}

/* ══════════════════════════════════
   SIDEBAR — COMPLETE COVERAGE
══════════════════════════════════ */
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
  border-right: 1px solid rgba(255,255,255,.06) !important;
  padding: 0 !important;
}
section[data-testid="stSidebar"] > div:first-child {
  padding: 0 !important;
}

/* Sidebar text overrides */
section[data-testid="stSidebar"] .stMarkdown p {
  color: rgba(255,255,255,.55) !important;
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 12px !important;
  line-height: 1.65 !important;
}
section[data-testid="stSidebar"] .stMarkdown strong {
  color: rgba(255,255,255,.80) !important;
  font-weight: 600 !important;
}
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p,
section[data-testid="stSidebar"] [data-testid="stCaption"] p {
  color: rgba(255,255,255,.40) !important;
  font-size: 11px !important;
  line-height: 1.7 !important;
  padding: 0 20px !important;
  font-family: 'Plus Jakarta Sans', sans-serif !important;
}
/* Sidebar dividers */
section[data-testid="stSidebar"] hr,
section[data-testid="stSidebar"] .stDivider hr,
section[data-testid="stSidebar"] [data-testid="stDivider"] hr {
  border: none !important;
  height: 1px !important;
  background: rgba(255,255,255,.10) !important;
  margin: 6px 0 !important;
}
section[data-testid="stSidebar"] .stDivider,
section[data-testid="stSidebar"] [data-testid="stDivider"] {
  margin: 10px 0 !important;
}

/* ── Sidebar nav buttons ── */
section[data-testid="stSidebar"] .stButton {
  width: 100% !important;
}
section[data-testid="stSidebar"] .stButton > button,
section[data-testid="stSidebar"] .stButton > button:focus,
section[data-testid="stSidebar"] .stButton > button:active {
  background: transparent !important;
  border: none !important;
  border-left: 3px solid transparent !important;
  border-radius: 0 8px 8px 0 !important;
  color: rgba(255,255,255,.60) !important;
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  padding: 10px 18px 10px 15px !important;
  text-align: left !important;
  width: 100% !important;
  margin: 1px 0 !important;
  transition: background .15s ease, color .15s ease, border-color .15s ease !important;
  box-shadow: none !important;
  letter-spacing: .1px !important;
  outline: none !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
  background: rgba(255,255,255,.07) !important;
  border-left-color: rgba(255,255,255,.20) !important;
  color: rgba(255,255,255,.90) !important;
}
/* Active nav item */
section[data-testid="stSidebar"] .stButton > button[kind="primary"],
section[data-testid="stSidebar"] .stButton > button[data-testid="baseButton-primary"] {
  background: #C8982A !important;
  border-left: 3px solid #C8982A !important;
  color: #FFFFFF !important;
  font-weight: 600 !important;
  box-shadow: none !important;
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover,
section[data-testid="stSidebar"] .stButton > button[data-testid="baseButton-primary"]:hover {
  background: #B8881A !important;
  color: #FFFFFF !important;
}

/* ══════════════════════════════════
   TYPOGRAPHY
══════════════════════════════════ */
/* H1 — Page title */
.stApp h1 {
  font-family: 'Fraunces', Georgia, serif !important;
  font-weight: 400 !important;
  font-size: 26px !important;
  color: #0D1B2E !important;
  letter-spacing: -0.4px !important;
  line-height: 1.25 !important;
  margin-top: 0 !important;
  margin-bottom: 4px !important;
}
/* H2 — Section heading */
.stApp h2 {
  font-family: 'Fraunces', Georgia, serif !important;
  font-weight: 300 !important;
  font-size: 19px !important;
  color: #003366 !important;
  line-height: 1.35 !important;
  margin-top: 2.2rem !important;
  margin-bottom: 10px !important;
}
/* H3 — Subsection */
.stApp h3 {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-weight: 700 !important;
  font-size: 11px !important;
  color: #003366 !important;
  letter-spacing: 1.5px !important;
  text-transform: uppercase !important;
  margin-top: 1.8rem !important;
  margin-bottom: 10px !important;
}

/* ── Body text ── */
.stApp p, .stApp li {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 14px !important;
  line-height: 1.7 !important;
}

/* ── Captions ── */
.stApp [data-testid="stCaptionContainer"] p,
.stApp [data-testid="stCaption"] p {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 12.5px !important;
  color: #6B7280 !important;
  line-height: 1.65 !important;
  margin-top: 2px !important;
}

/* ── Strong / bold ── */
.stApp strong {
  color: #0D1B2E !important;
  font-weight: 600 !important;
}

/* ══════════════════════════════════
   METRIC CARDS
══════════════════════════════════ */
[data-testid="metric-container"] {
  background: #FFFFFF !important;
  border-radius: 12px !important;
  border: 1px solid #E2E8F0 !important;
  border-top: 3px solid #003366 !important;
  box-shadow: 0 1px 4px rgba(0,20,60,.06) !important;
  padding: 20px 24px 18px !important;
}
[data-testid="metric-container"] > div {
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  text-align: center !important;
}
[data-testid="stMetricValue"] {
  font-family: 'Fraunces', Georgia, serif !important;
  font-weight: 300 !important;
  font-size: 28px !important;
  color: #0D1B2E !important;
  line-height: 1.2 !important;
}
[data-testid="stMetricLabel"] div,
[data-testid="stMetricLabel"] p {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 10px !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 1.5px !important;
  color: #6B7280 !important;
  margin-bottom: 6px !important;
  text-align: center !important;
}
[data-testid="stMetricDelta"] {
  display: flex !important;
  justify-content: center !important;
}
[data-testid="stMetricDelta"] > div {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 12px !important;
  font-weight: 500 !important;
}

/* ══════════════════════════════════
   BUTTONS (main content)
══════════════════════════════════ */
.stApp .stButton > button {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  border-radius: 8px !important;
  letter-spacing: .2px !important;
  transition: all .15s ease !important;
  padding: 8px 20px !important;
  box-shadow: none !important;
}
/* Secondary */
.stApp .stButton > button:not([kind="primary"]):not([data-testid="baseButton-primary"]) {
  border: 1px solid #D1D9E6 !important;
  color: #374151 !important;
  background: #FFFFFF !important;
}
.stApp .stButton > button:not([kind="primary"]):not([data-testid="baseButton-primary"]):hover {
  background: #F1F5F9 !important;
  border-color: #003366 !important;
  color: #003366 !important;
}
/* Primary */
.stApp .stButton > button[kind="primary"],
.stApp .stButton > button[data-testid="baseButton-primary"] {
  background: #003366 !important;
  color: #FFFFFF !important;
  border: 1px solid #003366 !important;
}
.stApp .stButton > button[kind="primary"]:hover,
.stApp .stButton > button[data-testid="baseButton-primary"]:hover {
  background: #1A4D80 !important;
  border-color: #1A4D80 !important;
}

/* ══════════════════════════════════
   TABS
══════════════════════════════════ */
[data-baseweb="tab-list"] {
  background: transparent !important;
  border-bottom: 2px solid #E2E8F0 !important;
  gap: 2px !important;
  padding-bottom: 0 !important;
}
[data-baseweb="tab"] {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 11px !important;
  font-weight: 700 !important;
  letter-spacing: 1.2px !important;
  text-transform: uppercase !important;
  color: #9CA3AF !important;
  background: transparent !important;
  padding: 10px 22px !important;
  border-radius: 6px 6px 0 0 !important;
  border-bottom: 2px solid transparent !important;
  margin-bottom: -2px !important;
  transition: color .15s, background .15s !important;
}
[data-baseweb="tab"]:hover {
  color: #003366 !important;
  background: rgba(0,51,102,.04) !important;
}
[data-baseweb="tab"][aria-selected="true"] {
  color: #003366 !important;
  border-bottom: 2px solid #C8982A !important;
  background: transparent !important;
}

/* ══════════════════════════════════
   EXPANDERS
══════════════════════════════════ */
[data-testid="stExpander"] {
  background: #FFFFFF !important;
  border-radius: 10px !important;
  border: 1px solid #E2E8F0 !important;
  box-shadow: none !important;
  overflow: hidden !important;
}
[data-testid="stExpander"] summary {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 12px !important;
  font-weight: 600 !important;
  color: #374151 !important;
  padding: 11px 18px !important;
  background: #FFFFFF !important;
  letter-spacing: .1px !important;
}
[data-testid="stExpander"] summary:hover {
  background: #F8FAFC !important;
}
[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
  padding: 0 18px 14px !important;
  border-top: 1px solid #F1F5F9 !important;
}

/* ══════════════════════════════════
   BORDERED CONTAINERS
══════════════════════════════════ */

/* ══════════════════════════════════
   ALERTS & INFO BOXES
══════════════════════════════════ */
[data-testid="stAlert"] {
  border-radius: 10px !important;
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 13px !important;
  line-height: 1.6 !important;
  border-width: 1px !important;
  border-style: solid !important;
}
[data-testid="stAlert"] p {
  font-size: 13px !important;
  color: inherit !important;
}
/* Info */
[data-testid="stAlert"][data-baseweb="notification"] {
  border-color: #BFDBFE !important;
  background: #EFF6FF !important;
  color: #1E40AF !important;
}
/* Success */
div[data-testid="stAlert"].st-ae {
  background: #ECFDF5 !important;
  border-color: #A7F3D0 !important;
  color: #065F46 !important;
}

/* ══════════════════════════════════
   DATAFRAMES & TABLES
══════════════════════════════════ */
[data-testid="stDataFrame"] {
  border-radius: 10px !important;
  border: 1px solid #E2E8F0 !important;
  overflow: hidden !important;
  box-shadow: 0 1px 3px rgba(0,0,0,.04) !important;
}

/* ══════════════════════════════════
   FORM CONTROLS
══════════════════════════════════ */
[data-testid="stSelectbox"] label p,
[data-testid="stMultiSelect"] label p,
[data-testid="stSlider"] label p,
[data-testid="stToggle"] label p,
[data-testid="stTextArea"] label p,
[data-testid="stTextInput"] label p,
[data-testid="stRadio"] > label p {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 10px !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 1.5px !important;
  color: #6B7280 !important;
  margin-bottom: 4px !important;
}
/* Input focus ring */
[data-baseweb="select"] [data-baseweb="select-container"],
[data-baseweb="input"] {
  border-color: #D1D9E6 !important;
  border-radius: 8px !important;
  background: #FFFFFF !important;
}

/* ══════════════════════════════════
   DIVIDERS
══════════════════════════════════ */
.stDivider hr,
[data-testid="stDivider"] hr {
  border: none !important;
  height: 1px !important;
  background: #E2E8F0 !important;
}
.stDivider,
[data-testid="stDivider"] {
  margin: 22px 0 !important;
}

/* ══════════════════════════════════
   MISC
══════════════════════════════════ */
/* Blockquotes */
.stApp blockquote {
  border-left: 3px solid #C8982A !important;
  background: #FDFAF3 !important;
  padding: 10px 16px !important;
  border-radius: 0 8px 8px 0 !important;
  color: #374151 !important;
  font-style: italic !important;
  margin: 8px 0 !important;
}
/* Inline code */
.stApp code {
  font-family: 'Courier New', monospace !important;
  font-size: 12px !important;
  background: #EFF2F7 !important;
  color: #003366 !important;
  padding: 2px 7px !important;
  border-radius: 4px !important;
  border: 1px solid #DDE4EF !important;
}
.stApp pre code {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
}
/* Spinners */
[data-testid="stSpinner"] {
  color: #003366 !important;
}
/* Progress bar in metrics */
[data-testid="stProgressBar"] > div > div {
  background: #003366 !important;
}
/* Section gap */
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {
  gap: 1rem !important;
}
</style>
"""


def inject_brand_css() -> None:
    """Inject the OPB brand design system CSS."""
    st.markdown(_BRAND_CSS, unsafe_allow_html=True)


# ── Sidebar header ─────────────────────────────────────────────────────────────

def nav_group_label(text: str) -> None:
    """Uppercase section divider label inside the sidebar nav."""
    st.html(f"""
    <div style="
      padding: 18px 20px 5px;
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-size: 9px;
      letter-spacing: 2.8px;
      text-transform: uppercase;
      color: rgba(255,255,255,.28);
      font-weight: 600;
    ">{text}</div>
    """)


def opb_sidebar_header() -> None:
    """OPB monogram + app title in the sidebar."""
    st.html("""
    <div style="
      padding: 20px 20px 18px;
      border-bottom: 1px solid rgba(255,255,255,.07);
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    ">
      <div>
        <div style="
          font-family: 'Fraunces', Georgia, serif;
          font-size: 22px;
          letter-spacing: -0.5px;
          line-height: 1;
          font-weight: 400;
          margin-bottom: 3px;
        ">
          <span style="color:#FFFFFF;">O</span><span style="color:#E8C46A;font-style:italic;">PB</span>
        </div>
        <div style="
          font-family: 'Plus Jakarta Sans', sans-serif;
          font-size: 11px;
          letter-spacing: 2.5px;
          text-transform: uppercase;
          color: rgba(255,255,255,.90);
          line-height: 1;
        ">Hidden Opportunities</div>
      </div>
      <div style="
        background: rgba(200,152,42,.18);
        border: 1px solid rgba(200,152,42,.30);
        border-radius: 5px;
        padding: 3px 8px;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 9px;
        font-weight: 700;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: #E8C46A;
      ">DEMO</div>
    </div>
    """)


# ── Page header ────────────────────────────────────────────────────────────────

def page_header(title: str, subtitle: str = "") -> None:
    """
    Consistent page header: serif title → optional subtitle.
    Replaces the st.title() + st.caption() + st.divider() pattern.
    """
    sub = ""
    if subtitle:
        sub = f"""
        <p style="
          font-family: 'Plus Jakarta Sans', sans-serif;
          font-size: 14px; color: #6B7280;
          line-height: 1.65; margin: 6px 0 0;
          max-width: 680px;
        ">{subtitle}</p>
        """
    st.html(f"""
    <div style="
      padding-bottom: 20px;
      border-bottom: 1px solid #E2E8F0;
      margin-bottom: 28px;
    ">
      <h1 style="
        font-family: 'Fraunces', Georgia, serif;
        font-weight: 400; font-size: 26px;
        color: #0D1B2E; letter-spacing: -0.4px;
        line-height: 1.25; margin: 0;
      ">{title}</h1>
      {sub}
    </div>
    """)


# ── Section header ─────────────────────────────────────────────────────────────

def section_header(title: str, subtitle: str = "") -> None:
    """Gold-accented section divider with optional subtitle."""
    sub = f'<p style="font-family:Plus Jakarta Sans,sans-serif;font-size:13px;color:#6B7280;margin:4px 0 0;line-height:1.5;">{subtitle}</p>' if subtitle else ""
    st.html(f"""
    <div style="display:flex;align-items:flex-start;gap:12px;margin:28px 0 16px;">
      <div style="width:3px;height:36px;background:#C8982A;border-radius:2px;flex-shrink:0;margin-top:2px;"></div>
      <div>
        <div style="
          font-family:'Plus Jakarta Sans',sans-serif;
          font-size:14px;font-weight:700;
          color:#003366;letter-spacing:.1px;
        ">{title}</div>
        {sub}
      </div>
    </div>
    """)


# ── Eyebrow label ──────────────────────────────────────────────────────────────

def eyebrow_label(text: str) -> None:
    """Gold eyebrow label above a section heading."""
    st.html(f"""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;margin-top:4px;">
      <div style="width:20px;height:1px;background:#C8982A;"></div>
      <span style="
        font-family:'Plus Jakarta Sans',sans-serif;
        font-size:9px;letter-spacing:3.5px;text-transform:uppercase;
        color:#C8982A;font-weight:600;
      ">{text}</span>
    </div>
    """)


# ── Production badge ───────────────────────────────────────────────────────────

def production_badge(note: str) -> None:
    """Inline production integration note — safe to use inside expanders."""
    st.html(f"""
    <div style="
      display:flex;align-items:flex-start;gap:10px;
      background:#F0F4F8;
      border-left:3px solid #6B7280;
      border-radius:0 6px 6px 0;
      padding:8px 14px;
      margin:8px 0 16px;
    ">
      <span style="
        font-family:'Plus Jakarta Sans',sans-serif;
        font-size:9px;font-weight:700;letter-spacing:2px;
        text-transform:uppercase;color:#6B7280;
        white-space:nowrap;padding-top:2px;
      ">Production</span>
      <span style="width:1px;min-height:14px;background:#CBD5E1;flex-shrink:0;margin-top:2px;"></span>
      <span style="
        font-family:'Plus Jakarta Sans',sans-serif;
        font-size:12px;color:#4B5563;line-height:1.65;
      ">{note}</span>
    </div>
    """)


# ── Demo banner ────────────────────────────────────────────────────────────────

def demo_banner() -> None:
    """Slim demo-mode banner at the top of the main content area."""
    st.html("""
    <div style="
      background: #FDFAF3;
      border: 1px solid rgba(200,152,42,.25);
      border-left: 3px solid #C8982A;
      border-radius: 8px;
      padding: 8px 18px;
      margin-bottom: 24px;
      display: flex;
      align-items: center;
      gap: 14px;
    ">
      <span style="
        font-family:'Plus Jakarta Sans',sans-serif;
        font-size:9px;font-weight:700;
        letter-spacing:2.5px;text-transform:uppercase;
        color:#C8982A;white-space:nowrap;
      ">Demo Mode</span>
      <span style="width:1px;height:14px;background:#E8C46A;opacity:.4;flex-shrink:0;"></span>
      <span style="
        font-family:'Plus Jakarta Sans',sans-serif;
        font-size:12px;color:#78716C;line-height:1.5;
      ">
        All data is synthetic. In production each panel connects to the live API
        shown in the <strong style="color:#92400E;">Production integration</strong> notes.
      </span>
    </div>
    """)


# ── Score bar ──────────────────────────────────────────────────────────────────

def score_bar(score: float, label: str = "") -> None:
    """Colored confidence score progress bar."""
    if score >= 80:
        fill   = "#059669"
        track  = "#D1FAE5"
        badge  = "#ECFDF5"
        text   = "#065F46"
        tier   = "HIGH"
    elif score >= 60:
        fill   = "#D97706"
        track  = "#FEF3C7"
        badge  = "#FFFBEB"
        text   = "#92400E"
        tier   = "MEDIUM"
    else:
        fill   = "#336699"
        track  = "#DBEAFE"
        badge  = "#EFF6FF"
        text   = "#1E3A5F"
        tier   = "LOW"

    lbl_html = f'<div style="font-family:Plus Jakarta Sans,sans-serif;font-size:11px;color:#6B7280;margin-top:4px;">{label}</div>' if label else ""
    st.html(f"""
    <div style="margin:6px 0 10px;">
      <div style="display:flex;align-items:center;gap:12px;">
        <div style="flex:1;background:{track};border-radius:4px;height:7px;overflow:hidden;">
          <div style="
            width:{score}%;background:{fill};height:100%;
            border-radius:4px;transition:width .4s ease;
          "></div>
        </div>
        <span style="
          font-family:'Plus Jakarta Sans',sans-serif;
          font-size:10px;font-weight:700;letter-spacing:.8px;
          text-transform:uppercase;
          background:{badge};color:{text};
          padding:3px 11px;border-radius:20px;
          min-width:115px;text-align:center;
          border:1px solid {fill}30;
        ">{tier} &nbsp;{score:.0f}/100</span>
      </div>
      {lbl_html}
    </div>
    """)


# ── Slack message card ─────────────────────────────────────────────────────────

def slack_message_card(alert: dict) -> None:
    """Simulated Slack alert card."""
    score = alert.get("score", 0)
    if score >= 80:
        accent     = "#DC2626"
        badge_bg   = "#FEF2F2"
        badge_txt  = "#991B1B"
    elif score >= 60:
        accent     = "#D97706"
        badge_bg   = "#FFFBEB"
        badge_txt  = "#92400E"
    else:
        accent     = "#059669"
        badge_bg   = "#ECFDF5"
        badge_txt  = "#065F46"

    label  = alert.get("label", alert.get("opportunity_type", ""))
    client = alert.get("client_name", "Unknown")
    price  = alert.get("suggested_price", 0)
    ts     = alert.get("timestamp", "")[:16].replace("T", " ")

    st.html(f"""
    <div style="
      border-left: 4px solid {accent};
      background: #1E293B;
      border-radius: 10px;
      padding: 16px 20px;
      margin: 8px 0;
      font-family: 'Plus Jakarta Sans', sans-serif;
      box-shadow: 0 2px 6px rgba(0,0,0,.20);
    ">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
        <span style="font-weight:700;color:#F1F5F9;font-size:13px;">
          Hidden Opportunities Agent
        </span>
        <span style="
          background:{accent};color:#fff;
          font-size:9px;padding:2px 8px;
          border-radius:3px;font-weight:700;letter-spacing:1.5px;
        ">ALERT</span>
        <span style="color:#64748B;font-size:11px;margin-left:auto;">{ts}</span>
      </div>
      <div style="
        color:#E8C46A;font-size:10px;font-weight:700;
        margin-bottom:10px;text-transform:uppercase;letter-spacing:2px;
      ">New Opportunity Detected</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px 24px;">
        <div>
          <div style="color:#64748B;font-size:9px;text-transform:uppercase;letter-spacing:2px;margin-bottom:2px;">Client</div>
          <div style="color:#F1F5F9;font-size:13px;">{client}</div>
        </div>
        <div>
          <div style="color:#64748B;font-size:9px;text-transform:uppercase;letter-spacing:2px;margin-bottom:2px;">Opportunity</div>
          <div style="color:#F1F5F9;font-size:13px;">{label}</div>
        </div>
        <div>
          <div style="color:#64748B;font-size:9px;text-transform:uppercase;letter-spacing:2px;margin-bottom:2px;">Confidence</div>
          <div style="
            display:inline-block;
            background:{badge_bg};color:{badge_txt};
            font-size:12px;font-weight:700;
            padding:2px 10px;border-radius:12px;
          ">{score:.0f}%</div>
        </div>
        <div>
          <div style="color:#64748B;font-size:9px;text-transform:uppercase;letter-spacing:2px;margin-bottom:2px;">Price</div>
          <div style="
            color:#E8C46A;font-size:14px;font-weight:600;
            font-family:'Fraunces',Georgia,serif;
          ">${price:,.0f}</div>
        </div>
      </div>
    </div>
    """)
