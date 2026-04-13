# Hidden Opportunities Agent

An autonomous AI sales agent that detects upsell and cross-sell opportunities for a digital marketing agency, generates personalized proposals, negotiates price objections, and closes deals — with minimal human intervention.

Built in 7 sprints across a two-week development cycle. All client data is **synthetic**. No real emails are sent in demo mode.

---

## Table of Contents

1. [What It Does](#what-it-does)
2. [Architecture](#architecture)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
5. [Module Reference](#module-reference)
   - [config.py](#configpy)
   - [src/db/](#srcdb)
   - [src/synthetic/](#srcsynthetic)
   - [src/data_sources/](#srcdataSources)
   - [src/agents/](#srcagents)
   - [src/nlp/](#srcnlp)
   - [src/ml/](#srcml)
   - [src/ui/](#srcui)
   - [scripts/](#scripts)
6. [Sprint History](#sprint-history)
7. [Demo Mode vs Production](#demo-mode-vs-production)
8. [Autonomy Tiers & Governance](#autonomy-tiers--governance)
9. [Running Tests](#running-tests)
10. [Docker](#docker)
11. [Roadmap](#roadmap)

---

## What It Does

The agent runs a continuous loop over a portfolio of agency clients:

```
Daily Cron
    │
    ▼
[Data Sources] ──► [Rules Engine + ML Model] ──► [Opportunity Detection]
                                                          │
                                                          ▼
                                               [Proposal Generator (LLM)]
                                                          │
                                              ┌───────────┴────────────┐
                                              ▼                        ▼
                                     [Tier B: Human             [Tier C: Auto-Send
                                      Approval UI]               + BCC Manager]
                                              │
                                              ▼
                                      [Client Reply]
                                              │
                             ┌────────────────┼─────────────────┐
                             ▼                ▼                  ▼
                        [Accepted]     [Too Expensive]      [Escalated]
                             │                │                  │
                             ▼                ▼                  ▼
                    [Stripe Payment    [Negotiation         [Human Takes
                       Link]           Engine (LLM)]         Over]
                                             │
                                   [Auto-resolve: 10/15/20%
                                    discount over 3 turns]
```

**7 opportunity types detected:**

| Type | Signal |
|---|---|
| Landing Page Optimization | High CTR + high bounce rate |
| SEO Content Package | Low keyword rankings + organic traffic gap |
| Retargeting Campaign | Ad spend without retargeting + ROAS below threshold |
| Email Automation | Low email open rate |
| Reactivation | Client inactive 60+ days |
| Conversion Rate Audit | High CTR + very low conversion rate |
| Ad Budget Expansion | ROAS well above benchmark — room to scale |

---

## Architecture

```
hidden_opportunities_agent/
│
├── config.py                   # Central config — all env vars in one place
│
├── src/
│   ├── db/
│   │   └── schema.py           # SQLite schema + get_connection() helper
│   │
│   ├── synthetic/
│   │   └── generator.py        # Generates 75 realistic fake clients + metrics
│   │
│   ├── data_sources/           # Adapters for each data channel
│   │   ├── _base.py            # Base class + production-note contract
│   │   ├── google_analytics.py
│   │   ├── meta_ads.py
│   │   ├── crm.py
│   │   ├── email_marketing.py
│   │   ├── seo.py
│   │   └── text_signals.py     # NLP signal DB adapter
│   │
│   ├── agents/                 # Core business logic
│   │   ├── rules.py            # Rule-based opportunity detector
│   │   ├── scorer.py           # Blended score: 0.55×ML + 0.45×rules
│   │   ├── alerts.py           # Slack / Telegram dispatcher
│   │   ├── proposal_generator.py  # LLM proposal writer (7 templates)
│   │   ├── email_sender.py     # SendGrid abstraction (demo: JSONL log)
│   │   ├── feedback_loop.py    # Client reply processor + confidence deltas
│   │   ├── auto_sender.py      # 3-tier autonomy engine
│   │   ├── negotiator.py       # Multi-turn price negotiation (Sprint 7)
│   │   └── payment_link.py     # Stripe Payment Link generator (Sprint 7)
│   │
│   ├── nlp/
│   │   ├── signal_extractor.py # Keyword + optional LLM signal extraction
│   │   └── pipeline.py         # Batch NLP pipeline over all text_signals rows
│   │
│   ├── ml/
│   │   ├── dataset.py          # Feature engineering (18 features)
│   │   ├── model.py            # RandomForestClassifier training + CV
│   │   ├── explainer.py        # SHAP-based feature importance
│   │   └── inference.py        # Predict + update ML scores in DB
│   │
│   └── ui/
│       ├── app.py              # Streamlit entry point
│       ├── components.py       # Shared UI widgets (score_bar, badges, etc.)
│       └── views/              # One module per dashboard page
│           ├── negotiation.py  # Sprint 7: negotiations + kill-switch + payments
│           ├── text_signals.py # Sprint 6: NLP signal dashboard
│           ├── ml_model.py     # Sprint 5: model card + SHAP
│           ├── pilot.py        # Sprint 4: full cycle demo
│           ├── proposals.py    # Sprint 3: approve/reject/edit
│           ├── opportunities.py
│           ├── alert_feed.py
│           └── accuracy.py
│
├── scripts/
│   ├── seed_db.py              # Populate DB with synthetic data
│   ├── run_detection.py        # One-off opportunity scan
│   ├── train_model.py          # Train + save the ML model
│   ├── process_text.py         # Run NLP pipeline on unprocessed texts
│   └── daily_job.py            # Full daily pipeline orchestrator
│
├── tests/
│   ├── test_sprint0.py … test_sprint7.py   # 313 tests total
│
├── data/
│   ├── db/opportunities.db     # SQLite database (auto-created)
│   ├── synthetic/              # Generated JSON fixtures
│   └── exports/proposals/      # Markdown proposal exports
│
├── logs/                       # Demo-mode output logs
│   ├── sent_emails.jsonl
│   ├── feedback.jsonl
│   ├── negotiations.jsonl
│   └── payment_links.jsonl
│
├── GOVERNANCE.md               # Autonomy rules & escalation policy
├── Dockerfile
└── requirements.txt
```

**Database tables (SQLite):**

| Table | Purpose |
|---|---|
| `clients` | Client master data (name, industry, contact, account manager) |
| `client_metrics` | Time-series snapshots of all KPIs per client |
| `opportunities` | Detected upsell/cross-sell opportunities with scores |
| `proposals` | Generated proposals with status lifecycle + payment_link |
| `feedback_log` | Client reply outcomes + confidence deltas |
| `text_signals` | NLP-extracted signals from emails, calls, CRM notes |
| `negotiation_log` | Multi-turn negotiation conversation threads |

---

## Quick Start

### Prerequisites

- Python 3.11+
- (Optional) An OpenAI or Anthropic API key for LLM features
- (Optional) A Stripe secret key for payment links

### Install

```bash
git clone <repo>
cd hidden_opportunities_agent
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env   # if available, or create manually — see Configuration below
```

### Seed the database

```bash
python scripts/seed_db.py
```

This creates `data/db/opportunities.db` and populates it with 75 synthetic clients, their metric history, and demo text signals (emails / call transcripts / CRM notes).

### Launch the dashboard

```bash
streamlit run src/ui/app.py
```

Open `http://localhost:8501`. The app starts on the **Negotiation** page (Sprint 7).

### Run the full daily pipeline (optional)

```bash
python scripts/daily_job.py --demo-only
```

---

## Configuration

All settings live in `config.py` and are sourced from environment variables (`.env` file via `python-dotenv`).

Create a `.env` file in the project root:

```dotenv
# ── Demo toggle ────────────────────────────────────────────────
# true  → no external API calls; everything written to local files
# false → real SendGrid, Stripe, Slack, etc.
DEMO_MODE=true

# ── LLM ────────────────────────────────────────────────────────
LLM_PROVIDER=anthropic          # openai | anthropic | auto
LLM_MODEL=claude-haiku-4-5-20251001

ANTHROPIC_API_KEY=sk-ant-...    # optional — enables LLM proposals + negotiation
OPENAI_API_KEY=sk-...           # optional — alternative LLM provider

# ── Email (Sprint 4) ────────────────────────────────────────────
SENDGRID_API_KEY=SG.xxx         # only needed in production mode
EMAIL_FROM=agent@youragency.com

# ── Payments (Sprint 7) ─────────────────────────────────────────
STRIPE_SECRET_KEY=sk_live_...   # only needed in production mode

# ── Notifications ───────────────────────────────────────────────
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

# ── Synthetic data ──────────────────────────────────────────────
SYNTHETIC_CLIENT_COUNT=75       # number of fake clients to generate
SYNTHETIC_SEED=42               # seed for reproducible data
```

**Minimum config for full demo (no API keys needed):**

```dotenv
DEMO_MODE=true
```

**Minimum config for LLM-powered proposals and negotiation:**

```dotenv
DEMO_MODE=true
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Module Reference

### `config.py`

Central configuration loaded at import time. Reads every setting from environment variables with safe defaults.

Key exports:

| Name | Type | Description |
|---|---|---|
| `DEMO_MODE` | `bool` | When `True`, all external I/O goes to local JSONL files |
| `DB_PATH` | `Path` | Path to the SQLite database |
| `LOGS_DIR` | `Path` | Directory for demo-mode log files |
| `EXPORTS_DIR` | `Path` | Directory for Markdown proposal exports |
| `LLM_PROVIDER` | `str` | `"anthropic"` \| `"openai"` \| `"auto"` |
| `LLM_MODEL` | `str` | Model ID to pass to the LLM API |
| `STRIPE_SECRET_KEY` | `str` | Stripe API key (empty in demo mode) |
| `ANTHROPIC_API_KEY` | `str` | Anthropic API key |
| `OPENAI_API_KEY` | `str` | OpenAI API key |

```python
import config
print(config.summary())   # non-sensitive config dict for logging
```

---

### `src/db/`

#### `schema.py`

SQLite schema definition and connection helper.

```python
from src.db.schema import get_connection, init_db, migrate_db

init_db()      # create all tables if they don't exist (idempotent)
migrate_db()   # apply additive column migrations (safe to call repeatedly)
conn = get_connection()   # returns sqlite3.Connection with WAL mode + Row factory
```

`init_db()` is called automatically by `seed_db.py` and by the dashboard on startup. `migrate_db()` is safe to call after pulling a new sprint — it only adds columns, never drops them.

---

### `src/synthetic/`

#### `generator.py`

Generates realistic synthetic data for 75 clients across 8 industries. Called once by `seed_db.py`.

```python
from src.synthetic.generator import generate_all
generate_all()   # seeds clients, metrics, opportunities, text signals
```

The generator uses a fixed random seed (`SYNTHETIC_SEED=42`) so every run produces identical data. Three **demo scenario** clients are always present with pre-scripted metric patterns that showcase every opportunity type.

---

### `src/data_sources/`

Each module is a read-only adapter for one data channel. All modules follow the same contract defined in `_base.py`: every public function must return a production note explaining what the real API call would look like.

#### `google_analytics.py`

```python
from src.data_sources import google_analytics as ga

metrics = ga.get_latest_metrics(client_id)
# Returns: bounce_rate, pages_per_session, conversion_rate, organic_traffic
```

Production: Google Analytics Data API v1 (`runReport`).

#### `meta_ads.py`

```python
from src.data_sources import meta_ads

metrics = meta_ads.get_latest_ad_metrics(client_id)
# Returns: ctr, cpc, roas, ad_spend
```

Production: Meta Marketing API (`/insights` endpoint).

#### `crm.py`

```python
from src.data_sources import crm

client      = crm.get_client(client_id)
activity    = crm.get_client_activity(client_id)   # days_inactive, days_since_last_contact
all_clients = crm.get_all_clients()
demo_clients = crm.get_demo_clients()              # only is_demo_scenario=1 clients
```

Production: HubSpot CRM API v3 (`/crm/v3/objects/contacts`).

#### `email_marketing.py`

```python
from src.data_sources import email_marketing

metrics = email_marketing.get_latest_email_metrics(client_id)
# Returns: email_open_rate, email_click_rate
```

Production: Mailchimp / ActiveCampaign / Klaviyo API.

#### `seo.py`

```python
from src.data_sources import seo

metrics = seo.get_latest_seo_metrics(client_id)
# Returns: organic_traffic, keyword_rankings
```

Production: Ahrefs / SEMrush / Google Search Console API.

#### `text_signals.py`

DB adapter for the NLP pipeline output. Reads from the `text_signals` table.

```python
from src.data_sources.text_signals import (
    get_client_signals,      # list of raw text records for a client
    get_signal_summary,      # aggregated signal flags for a client
    get_urgency_alerts,      # clients with churn_risk=1 or urgency_signal=1
    count_signals_by_type,   # { 'email': N, 'call_transcript': M, ... }
)
```

---

### `src/agents/`

The agents layer is the core of the system. Each module has a single responsibility.

#### `rules.py`

Rule-based opportunity detector. Contains 7 `if/then` rules derived from agency benchmarks.

```python
from src.agents.rules import evaluate_all_rules, OPPORTUNITY_LABELS, SUGGESTED_PRICES

results = evaluate_all_rules(metrics_dict)
# Returns: list of OpportunityResult(type, score, rationale, suggested_price)
```

Each rule fires when specific metric thresholds are exceeded. Scores range 0–100 and reflect how strongly the signal pattern matches the opportunity type. The rules engine is always available as a fallback when the ML model has insufficient training data.

**Opportunity types and default prices:**

| Type | Default Price |
|---|---|
| `landing_page_optimization` | $350 |
| `seo_content` | $500 |
| `retargeting_campaign` | $450 |
| `email_automation` | $600 |
| `reactivation` | $150 |
| `conversion_rate_audit` | $250 |
| `upsell_ad_budget` | $400 |

#### `scorer.py`

Blends rule scores with ML model probability into a unified 0–100 score.

```python
from src.agents.scorer import score_client, score_all_clients, persist_opportunities

# Score one client
results = score_client(client_id)

# Score all clients and return the top opportunities
all_results = score_all_clients()

# Persist detected opportunities to the DB (upsert by client+type)
persist_opportunities(all_results)
```

**Blending formula:**  
`final_score = 0.55 × (ml_probability × 100) + 0.45 × rule_score`

When the ML model is not yet trained, the formula falls back to `rule_score` only.

#### `alerts.py`

Dispatches opportunity alerts to the configured channel.

```python
from src.agents.alerts import dispatch

dispatch(opportunities, channel="slack")    # or "telegram", "log"
```

In demo mode, alerts are written to `logs/alerts.jsonl`. In production, they POST to the configured Slack webhook or Telegram bot.

#### `proposal_generator.py`

Generates personalized sales proposals using LLM + templated fallback.

```python
from src.agents.proposal_generator import (
    generate_proposal,           # generate for one opportunity
    generate_proposals_for_all,  # generate for all opportunities >= min_score
    approve_proposal,
    reject_proposal,
    update_proposal_body,
    get_all_proposals,
)

result = generate_proposal(opportunity_id, rationale="High bounce rate detected")
# Returns: { proposal_id, client_name, subject, body, filepath, status }
```

**Flow:**
1. Load opportunity + client data from DB.
2. Pull latest metrics from all data sources.
3. Build a context dict with all template variables.
4. Call LLM (Anthropic → OpenAI → template fallback) to generate a personalized insight paragraph.
5. Render the appropriate template (7 templates, one per opportunity type), in Spanish.
6. Persist to `proposals` table (status = `'draft'`).
7. Export as a Markdown file to `data/exports/proposals/`.

All 7 templates are in `PROPOSAL_TEMPLATES` within the module — editable without touching business logic.

#### `email_sender.py`

Abstraction layer over SendGrid (or any email provider).

```python
from src.agents.email_sender import send_proposal_email, SEND_MODE_APPROVED, SEND_MODE_AUTONOMOUS

result = send_proposal_email(
    proposal_id,
    send_mode=SEND_MODE_APPROVED,   # or SEND_MODE_AUTONOMOUS for Tier C
    bcc_manager=True,
)
# In demo mode: writes to logs/sent_emails.jsonl
# In production: POST to SendGrid /v3/mail/send
```

The account manager is always BCC'd on every outbound email. In demo mode the full email payload (including headers, HTML, and BCC) is written to the log file exactly as it would be sent, making the demo fully production-realistic.

#### `feedback_loop.py`

Processes client replies and updates confidence scores.

```python
from src.agents.feedback_loop import record_client_reply, INTENT_ACCEPTED, ALL_INTENTS

result = record_client_reply(
    proposal_id,
    intent="accepted",   # one of ALL_INTENTS
    notes="Client replied: 'Let's go!'",
    simulated=True,
)
```

**6 intents:**

| Intent | What happens |
|---|---|
| `accepted` | Mark proposal accepted; schedule meeting; **auto-create Stripe payment link** (Sprint 7) |
| `rejected` | Mark rejected; reduce confidence modifier for this client×type pair |
| `too_expensive` | Mark rejected; **auto-start price negotiation** (Sprint 7) |
| `need_more_info` | Keep open; flag for human follow-up |
| `ignored` | Mark rejected; mild confidence reduction |
| `escalated` | Immediately alert account manager; mark as escalated |

**Confidence modifiers** are cumulative adjustments (`+15` for accept, `−20` for reject, etc.) stored in `feedback_log` and used by the scorer on the next run to personalize scores per client.

#### `auto_sender.py`

Implements the 3-tier autonomy model from `GOVERNANCE.md`.

```python
from src.agents.auto_sender import get_autonomy_tier, process_auto_send_queue

tier = get_autonomy_tier(score=92, suggested_price=150, opportunity_type="reactivation", is_repeat_client=True)
# Returns: "C"

results = process_auto_send_queue(dry_run=False)
# Sends all Tier C proposals and marks them as autonomous in the DB
```

**Tiers:**

| Tier | Condition | Action |
|---|---|---|
| A | score < 70 | Draft only — no send |
| B | score 70–89 OR price > $200 | Require human approval |
| C | score ≥ 90 AND price ≤ $200 AND repeat client | Auto-send with 30-min cancel window |

The cancel window is implemented via a delayed queue in production (see GOVERNANCE.md). In demo mode, Tier C emails send immediately.

#### `negotiator.py`

Multi-turn LLM price negotiation engine (Sprint 7).

```python
from src.agents.negotiator import (
    start_negotiation,      # open a negotiation for a too_expensive reply
    process_client_reply,   # handle the next client turn
    kill_negotiation,       # halt + escalate (kill-switch)
    get_thread,             # full conversation history for a proposal
    get_active_negotiations,
    get_negotiation_summary,
)

# Start (called automatically by feedback_loop on too_expensive)
neg = start_negotiation(proposal_id)
# → agent sends Turn 1 with 10% discount offer

# Process client reply
result = process_client_reply(proposal_id, "Si bajas un poco más podemos hablar.")
# → extracts intent (counter_offer), generates Turn 2 at 15% discount

# Kill switch
kill_negotiation(proposal_id, reason="manual_kill_switch_ui")
# → marks escalated + notifies account manager
```

**Negotiation flow:**

```
Turn 1 (agent): 10% discount + value re-frame
Client: accepts / counter / rejects / escalates
Turn 2 (agent): 15% discount + specific justification
Client: accepts / counter / rejects / escalates
Turn 3 (agent): 20% final offer ("take it or leave it")
Turn 4+: auto-escalate to human account manager
```

**Intent extraction** uses regex word-boundary matching for Spanish/English keywords, with an optional LLM upgrade (Claude Haiku) when `ANTHROPIC_API_KEY` is set.

All turns are written to the `negotiation_log` table: `(proposal_id, turn, role, message, intent, offer_price)`.

#### `payment_link.py`

Stripe Payment Link generator (Sprint 7).

```python
from src.agents.payment_link import (
    create_payment_link,        # create a Stripe link for a proposal
    get_payment_link,           # retrieve existing link URL
    record_payment_received,    # called by Stripe webhook on checkout.session.completed
    list_payment_links,         # all proposals with links
)

result = create_payment_link(proposal_id)
# Demo mode: returns { url: "https://buy.stripe.com/demo/plink_xxx", simulated: True }
# Production: calls Stripe API, returns real checkout URL

# Mark paid after Stripe webhook fires
record_payment_received(proposal_id, stripe_session_id="cs_live_...")
```

In demo mode, a realistic-looking fake Stripe URL is generated and stored in `proposals.payment_link`. The link is idempotent — calling `create_payment_link` twice returns the same URL.

In production, the Stripe webhook endpoint should call `record_payment_received()` to update the proposal status to `'paid'` and close the opportunity.

---

### `src/nlp/`

#### `signal_extractor.py`

Extracts 6 behavioral signals from raw text (emails, call transcripts, CRM notes).

```python
from src.nlp.signal_extractor import extract_signals, aggregate_signals

signals = extract_signals("El precio está muy alto, necesitamos mejores resultados")
# Returns:
# {
#   "sentiment": -0.42,
#   "mentions_price": 1,
#   "asks_for_results": 1,
#   "churn_risk": 0,
#   "urgency_signal": 0,
#   "interest_signal": 0,
#   "extraction_mode": "keyword"
# }

# Aggregate across multiple texts for one client
agg = aggregate_signals([signals1, signals2, signals3])
```

**Extraction modes:**
- `"keyword"` — Fast regex matching, always available (default in `DEMO_MODE=true`)
- `"llm"` — Uses the configured LLM to classify signals with higher accuracy
- `"transformer"` — Uses a local HuggingFace sentiment model for the `sentiment` score

#### `pipeline.py`

Batch-processes all unprocessed `text_signals` rows and writes extracted signals back to the DB.

```python
from src.nlp.pipeline import run_pipeline, get_pipeline_summary

summary = run_pipeline(use_llm=False, reprocess_all=False)
# Returns: { total_processed, churn_alerts, urgency_alerts, errors }

info = get_pipeline_summary()
# Returns stats about the current state of the text_signals table
```

---

### `src/ml/`

#### `dataset.py`

Builds the feature matrix from the DB for model training and inference.

```python
from src.ml.dataset import build_dataset, FEATURE_NAMES

X, y, meta = build_dataset()
# X: numpy array (n_samples, 18)
# y: binary labels (1 = opportunity confirmed)
# meta: list of dicts with client_id, opportunity_type, etc.
```

**18 features** (in order):

| # | Feature | Source |
|---|---|---|
| 1 | `bounce_rate` | Google Analytics |
| 2 | `ctr` | Meta Ads |
| 3 | `roas` | Meta Ads |
| 4 | `email_open_rate` | Email Marketing |
| 5 | `organic_traffic` | SEO / GA |
| 6 | `keyword_rankings` | SEO |
| 7 | `conversion_rate` | GA |
| 8 | `pages_per_session` | GA |
| 9 | `cpc` | Meta Ads |
| 10 | `ad_spend` | Meta Ads |
| 11 | `days_since_last_contact` | CRM |
| 12 | `days_inactive` | CRM |
| 13 | `account_age_days` | CRM |
| 14–18 | `sentiment`, `mentions_price`, `asks_for_results`, `churn_risk`, `urgency_signal` | NLP (Sprint 6) |

#### `model.py`

Trains a `RandomForestClassifier` (200 trees, balanced class weights, `StratifiedKFold` CV).

```python
from src.ml.model import train_model, load_model, MODEL_PATH

metrics = train_model()
# Returns: { accuracy, precision, recall, f1, roc_auc, n_samples, cv_scores }

model = load_model()   # loads from data/models/rf_model.pkl
```

The model is saved to `data/models/rf_model.pkl` via `joblib`. If the file doesn't exist, `load_model()` returns `None` and the system gracefully falls back to rule-only scoring.

#### `explainer.py`

SHAP-based feature importance and per-prediction explanations.

```python
from src.ml.explainer import get_feature_importance, explain_single

# Global feature importance (sorted by |mean SHAP|)
importance = get_feature_importance(model, X_train)
# Returns: [{ feature, importance, direction }, ...]

# Per-prediction explanation
explanation = explain_single(model, feature_vector, feature_names)
# Returns: { probability, top_features, narrative, shap_values }
```

Falls back to `model.feature_importances_` when SHAP is unavailable.

#### `inference.py`

Runs predictions against the trained model for all clients.

```python
from src.ml.inference import predict_for_client, predict_for_all, update_ml_scores

preds = predict_for_client(client_id)
# Returns: list of { opportunity_type, ml_probability, rule_score, blended_score, explanation }

# Update ml_probability in the opportunities table for all detected opps
update_ml_scores()
```

---

### `src/ui/`

#### `app.py`

Streamlit entry point. Defines the sidebar navigation and renders the active page.

```bash
streamlit run src/ui/app.py
```

**Pages (in nav order):**

| Page | Module | Sprint |
|---|---|---|
| Negotiation | `views/negotiation.py` | 7 |
| Text Signals | `views/text_signals.py` | 6 |
| ML Model | `views/ml_model.py` | 5 |
| Pilot | `views/pilot.py` | 4 |
| Opportunities | `views/opportunities.py` | 2 |
| Proposals | `views/proposals.py` | 3 |
| Alert Feed | `views/alert_feed.py` | 2 |
| Accuracy | `views/accuracy.py` | 2 |

#### `views/negotiation.py` (Sprint 7)

Four tabs:
- **Active Negotiations** — one card per open negotiation, with the full chat thread and per-negotiation controls (send a reply, kill-switch button)
- **Demo Simulation** — pick any proposal, simulate a "too expensive" reply, step through the negotiation flow
- **Payment Links** — view all generated Stripe links, manually generate new ones
- **History** — full `negotiation_log` table with filters

#### `views/text_signals.py` (Sprint 6)

NLP dashboard: pipeline diagram, signal-type KPIs, email browser with sentiment badges, signal matrix heatmap, urgency alert panel, "Process Emails Now" button.

#### `views/ml_model.py` (Sprint 5)

Model card (accuracy/precision/recall/F1), feature importance bar chart, predictions table, "Why This Opportunity?" SHAP waterfall chart, Retrain button.

#### `views/pilot.py` (Sprint 4)

Full-cycle demo: Slow mode (step-through with explanations) and Fast mode (single-click end-to-end). Shows Pilot Report, Sent Emails log, and Feedback log.

#### `views/proposals.py` (Sprint 3)

Proposals queue with inline Approve / Reject / Edit controls. Approved proposals are queued for send.

#### `components.py`

Shared widgets used across all pages:

```python
from src.ui.components import (
    page_header,        # page title + subtitle
    score_bar,          # colored progress bar (red/yellow/green)
    production_badge,   # expandable "In Production" annotation
    demo_banner,        # top-of-page demo mode indicator
    inject_brand_css,   # OPB design system CSS
)
```

---

### `scripts/`

#### `seed_db.py`

One-time setup. Creates and populates the database.

```bash
python scripts/seed_db.py
# Options:
#   --clients N   override number of synthetic clients (default: 75)
#   --seed N      override random seed (default: 42)
```

Safe to re-run — drops and recreates synthetic data but preserves any manually entered data if using a separate DB.

#### `run_detection.py`

Run the opportunity detection engine without launching the full UI.

```bash
python scripts/run_detection.py
python scripts/run_detection.py --demo-only
python scripts/run_detection.py --min-score 80
```

Outputs a table of detected opportunities with scores and rationales.

#### `train_model.py`

Train the ML model on the current DB contents and save it to `data/models/rf_model.pkl`.

```bash
python scripts/train_model.py
# Options:
#   --n-estimators N   number of trees (default: 200)
#   --quiet            suppress verbose output
```

Must be run after seeding the DB. The model is automatically loaded by `scorer.py` on the next run.

#### `process_text.py`

Run the NLP pipeline on all unprocessed text signals.

```bash
python scripts/process_text.py
python scripts/process_text.py --reprocess   # re-process already-done rows
python scripts/process_text.py --use-llm     # use LLM for signal extraction
python scripts/process_text.py --quiet
```

#### `daily_job.py`

Full daily pipeline orchestrator. In production, triggered by cron at 08:00.

```bash
python scripts/daily_job.py
python scripts/daily_job.py --demo-only              # only demo scenario clients
python scripts/daily_job.py --dry-run                # detect but don't persist or dispatch
python scripts/daily_job.py --no-proposals           # skip proposal generation
python scripts/daily_job.py --no-auto-send           # skip Tier C auto-send
python scripts/daily_job.py --no-nlp                 # skip NLP pipeline
python scripts/daily_job.py --proposal-min-score 80  # raise the proposal threshold
python scripts/daily_job.py --channel telegram       # dispatch alerts to Telegram
```

**Pipeline steps:**
1. Pull latest metrics from all data sources
2. Apply rules engine to every client
3. Persist new opportunities to DB
4. Dispatch alerts (Slack / Telegram / log)
5. Generate proposals for opportunities ≥ score threshold
6. Process Tier C auto-send queue
7. Run NLP text processing pipeline

```
Production cron:
  0 8 * * *   cd /app && python scripts/daily_job.py >> logs/cron.log 2>&1
```

---

## Sprint History

| Sprint | Focus | Key Deliverable |
|---|---|---|
| 0 | Foundation | SQLite schema, synthetic data generator, data source adapters |
| 1 | Detection | Rule-based engine (7 rules), opportunity scoring |
| 2 | Alerting | Slack/Telegram dispatcher, alert feed UI, accuracy measurement |
| 3 | Proposals | LLM proposal generator (7 templates), Approve/Reject/Edit UI, GOVERNANCE.md |
| 4 | Autonomy | SendGrid sender, feedback loop, 3-tier autonomy engine, full-cycle pilot UI |
| 5 | ML | RandomForest + SHAP, 18-feature dataset, blended scoring (55% ML + 45% rules) |
| 6 | NLP | Text signal extraction (6 signals), batch NLP pipeline, text signals dashboard |
| 7 | Negotiation | Multi-turn price negotiation (LLM), Stripe payment links, kill-switch UI |

---

## Demo Mode vs Production

Every module has two execution paths controlled by `config.DEMO_MODE`:

| Feature | Demo Mode (`DEMO_MODE=true`) | Production Mode (`DEMO_MODE=false`) |
|---|---|---|
| Data sources | SQLite synthetic data | Live API calls (GA, Meta, HubSpot, etc.) |
| Email sending | Write to `logs/sent_emails.jsonl` | POST to SendGrid API |
| Slack alerts | Write to `logs/alerts.jsonl` | POST to Slack webhook |
| Telegram alerts | Write to `logs/alerts.jsonl` | Telegram Bot API |
| LLM proposals | Template fallback (no API needed) | Claude Haiku or GPT-3.5 |
| Stripe links | Fake URL (`buy.stripe.com/demo/...`) | Real Stripe Payment Link |
| Negotiation | Template responses | LLM-generated responses |
| Calendar | Write to `logs/calendar_events.jsonl` | Google Calendar API v3 |
| Escalation | Write to `logs/escalations.jsonl` | POST to Slack with @mention |

The demo-mode log files are structured identically to production payloads, so the demo is fully production-realistic without any external accounts.

---

## Autonomy Tiers & Governance

See [`GOVERNANCE.md`](GOVERNANCE.md) for the full policy. Summary:

- **Tier A** (score < 70): Agent generates a draft only. Human must approve before any email is sent.
- **Tier B** (score 70–89 or value > $200): Agent generates + notifies account manager. Human approves via UI or Slack `/approve` command.
- **Tier C** (score ≥ 90 AND value ≤ $200 AND repeat client): Agent generates + sends + BCC's account manager. 30-minute cancel window.

**Negotiation limits (Sprint 7):**
- Maximum 3 autonomous discount turns (10% → 15% → 20%)
- Any discount beyond 20% escalates to human
- Account manager can halt any negotiation via the kill-switch UI at any time

**Hard-coded prohibitions (cannot be overridden by config):**
- Never email anyone outside the agency CRM
- Never impersonate a human account manager without disclosure
- Never access client financial accounts
- Never store client data outside approved databases

---

## Running Tests

```bash
# Full suite (313 tests)
python -m pytest tests/ -v

# Single sprint
python -m pytest tests/test_sprint7.py -v

# With coverage
python -m pytest tests/ --cov=src --cov-report=term-missing

# Quick smoke test (Sprint 0 — data seeding)
python -m pytest tests/test_sprint0.py -v
```

**Test isolation:** Every test class that interacts with the DB uses an `isolated_db` fixture that monkeypatches `config.DB_PATH` to a temporary file for the duration of that test function and deletes it afterward. Tests never touch the real `data/db/opportunities.db`.

| File | Tests | Coverage |
|---|---|---|
| `test_sprint0.py` | 12 | Data seeding, source adapters |
| `test_sprint1.py` | 22 | Rules engine, all 7 opportunity types |
| `test_sprint2.py` | 20 | Scorer, alerts, accuracy metrics |
| `test_sprint3.py` | 35 | Proposal generator, LLM fallback, approval flow |
| `test_sprint4.py` | 46 | Email sender, feedback loop, auto-sender, pilot metrics |
| `test_sprint5.py` | 47 | Dataset, model training, SHAP explainer, inference |
| `test_sprint6.py` | 35 | NLP extractor, pipeline, signal aggregation |
| `test_sprint7.py` | 31 | Negotiator, payment links, schema migration, integrations |
| **Total** | **313** | |

---

## Docker

```bash
# Build
docker build -t hidden-opp-agent .

# Run (seeds DB on first start, then launches Streamlit on :8501)
docker run -p 8501:8501 \
  -e DEMO_MODE=true \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  hidden-opp-agent

# With a persistent volume for the database
docker run -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  -e DEMO_MODE=true \
  hidden-opp-agent
```

The container runs `seed_db.py` automatically on every start (idempotent — skips if data already exists) and then launches the Streamlit dashboard.

---

## Roadmap

Candidates for **Sprint 8+**:

- **Real-time chat widget** — WebSocket-based in-dashboard negotiation chat for live demos with stakeholders
- **CRM write-back** — update deal stage in HubSpot/Salesforce when a proposal is accepted or paid
- **Scheduled follow-ups** — auto-send a follow-up email N days after a proposal if no reply is received
- **Multi-client analytics** — cross-portfolio dashboard: total pipeline value, average discount given, conversion rate by opportunity type
- **Contract generator** — auto-generate a PDF service agreement when the Stripe payment is confirmed
- **A/B testing for proposals** — track which template variants have higher acceptance rates and auto-promote winners

---

*All client data in this system is synthetic. No real emails, payments, or CRM records are created in demo mode.*
