# Hidden Opportunities Agent

An autonomous revenue agent for marketing agencies. It continuously monitors client data to detect upsell and cross-sell opportunities, generates personalized proposals, runs automated follow-up sequences, monitors churn risk, and surfaces ROI analytics — all in a full-cycle loop that runs daily without manual intervention.

Built across 7 sprints + 7 ROADMAP platform features. All client data is **synthetic**. No real emails, CRM records, or payments are created in demo mode.

---

## Table of Contents

1. [What It Does](#what-it-does)
2. [Architecture](#architecture)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
5. [Platform Features](#platform-features)
6. [Module Reference](#module-reference)
7. [Sprint History](#sprint-history)
8. [Demo Mode vs Production](#demo-mode-vs-production)
9. [Autonomy Tiers & Governance](#autonomy-tiers--governance)
10. [Running Tests](#running-tests)
11. [Docker](#docker)

---

## What It Does

The agent runs a continuous pipeline over a portfolio of agency clients:

```
Daily Pipeline (scripts/daily_job.py)
    │
    ▼
[Data Sources] ──► [Rules Engine + ML Model] ──► [Seasonal Boost] ──► [Propensity Rank]
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
                        [Accepted]     [Too Expensive]      [Ignored]
                             │                │                  │
                             ▼                ▼                  ▼
                    [CRM Write-Back  [Negotiation Engine   [Follow-Up
                    + Payment Link]   (LLM, 3 turns)]       Sequence]
```

**7 opportunity types detected:**

| Type | Trigger Signal |
|---|---|
| Landing Page Optimization | High bounce rate + low conversion rate |
| SEO Content Package | Low organic traffic + declining keyword rankings |
| Retargeting Campaign | Ad spend without retargeting + ROAS below threshold |
| Email Automation | Low email open rate (<15%) |
| Express Reactivation | Client inactive 60+ days in CRM |
| Conversion Rate Audit | Ad spend > $1,000/mo with ROAS < 2× |
| Ad Budget Expansion | ROAS > 4× + CTR > 3% (budget is the constraint) |

---

## Architecture

```
hidden_opportunities_agent/
│
├── config.py                    # Central config — all env vars in one place
│
├── backend/                     # FastAPI application
│   ├── main.py                  # App entry point — registers 14 routers, runs migrations
│   └── routers/                 # One router per domain (thin wrappers over src/)
│       ├── opportunities.py
│       ├── proposals.py
│       ├── text_signals.py
│       ├── negotiations.py
│       ├── follow_ups.py        # Feature 1: follow-up sequences
│       ├── analytics.py         # Feature 2: ROI dashboard
│       ├── churn.py             # Feature 3: churn escalation
│       ├── crm.py               # Feature 5: CRM write-back
│       ├── seasonal.py          # Features 4, 6, 7: propensity, seasonal, WhatsApp
│       ├── pilot.py
│       ├── ml_model.py
│       ├── alerts.py
│       ├── clients.py
│       └── accuracy.py
│
├── src/
│   ├── db/
│   │   └── schema.py            # SQLite schema (12 tables) + init_db() + migrate_db()
│   │
│   ├── synthetic/
│   │   └── generator.py         # 75 synthetic clients + metrics (Faker, seed=42)
│   │
│   ├── data_sources/            # Read-only adapters per data channel
│   │   ├── google_analytics.py
│   │   ├── meta_ads.py
│   │   ├── crm.py
│   │   ├── email_marketing.py
│   │   ├── seo.py
│   │   └── text_signals.py      # NLP signal DB adapter
│   │
│   ├── agents/                  # Core business logic
│   │   ├── rules.py             # Rule-based detector (7 rules)
│   │   ├── scorer.py            # Blended score: 0.55×ML + 0.45×rules + seasonal boost
│   │   ├── alerts.py            # Slack / Telegram dispatcher
│   │   ├── proposal_generator.py   # LLM proposal writer (7 templates)
│   │   ├── email_sender.py      # SendGrid abstraction (demo: JSONL log)
│   │   ├── feedback_loop.py     # Reply processor → follow-ups / negotiation / CRM sync
│   │   ├── auto_sender.py       # 3-tier autonomy engine
│   │   ├── negotiator.py        # Multi-turn price negotiation (LLM)
│   │   ├── payment_link.py      # Stripe Payment Link generator
│   │   ├── follow_up_engine.py  # Feature 1: automated follow-up sequences
│   │   ├── analytics_engine.py  # Feature 2: ROI metrics + weekly snapshots
│   │   ├── churn_escalation.py  # Feature 3: churn signal scanner + escalation
│   │   ├── propensity_ranker.py # Feature 4: client propensity tier scoring
│   │   └── seasonal_engine.py   # Feature 6: seasonal score multipliers + calendar
│   │
│   ├── integrations/            # External service write-back
│   │   ├── hubspot.py           # Feature 5: HubSpot CRM deal sync
│   │   └── whatsapp.py          # Feature 7: WhatsApp Business outreach
│   │
│   ├── nlp/
│   │   ├── signal_extractor.py  # Keyword + optional LLM signal extraction
│   │   └── pipeline.py          # Batch NLP pipeline over text_signals rows
│   │
│   └── ml/
│       ├── dataset.py           # Feature engineering (18 features)
│       ├── model.py             # RandomForestClassifier training + CV
│       ├── explainer.py         # SHAP-based feature importance
│       └── inference.py         # Predict + update ML scores in DB
│
├── frontend/                    # React 18 + TypeScript 5.6 (Vite 5)
│   └── src/
│       ├── App.tsx              # Page router (state-based, no library)
│       ├── pages/               # 10 pages
│       │   ├── OpportunitiesPage.tsx    # Propensity badges, seasonal calendar
│       │   ├── ProposalsPage.tsx        # Proposals + follow-up queue + CRM log
│       │   ├── TextSignalsPage.tsx      # NLP signals + churn escalation tab
│       │   ├── AnalyticsDashboardPage.tsx  # ROI dashboard + weekly trends
│       │   ├── NegotiationPage.tsx
│       │   ├── MLModelPage.tsx
│       │   ├── PilotPage.tsx
│       │   ├── AlertFeedPage.tsx
│       │   ├── AccuracyPage.tsx
│       │   └── InfoPage.tsx
│       ├── components/          # Nav · Footer · Eyebrow
│       └── services/
│           └── api.ts           # Typed HTTP calls for all 14 router domains
│
├── scripts/
│   ├── seed_db.py               # Seed DB with 75 synthetic clients
│   ├── run_detection.py         # One-off opportunity scan
│   ├── train_model.py           # Train + save the ML model
│   ├── process_text.py          # Run NLP pipeline
│   └── daily_job.py             # Full daily pipeline orchestrator (7 steps)
│
├── tests/                       # 313 tests across 8 sprint files
├── data/
│   ├── db/opportunities.db      # SQLite database (auto-created)
│   ├── synthetic/               # Generated JSON fixtures
│   └── exports/proposals/       # Markdown proposal exports
│
├── logs/                        # Demo-mode output (JSONL files)
│   ├── sent_emails.jsonl
│   ├── follow_ups.jsonl
│   ├── crm_sync.jsonl
│   ├── whatsapp_log.jsonl
│   ├── churn_escalations.jsonl
│   └── ...
│
├── run.bat                      # Windows launcher (starts backend + opens browser)
├── GOVERNANCE.md                # Autonomy rules & escalation policy
├── Dockerfile
└── requirements.txt
```

**Database — 12 SQLite tables:**

| Table | Purpose |
|---|---|
| `clients` | Master data + propensity tier, preferred channel, CRM/WhatsApp IDs |
| `client_metrics` | Time-series KPI snapshots per client |
| `opportunities` | Detected opportunities with rule score + ML probability |
| `proposals` | Generated proposals — full status lifecycle + payment link |
| `feedback_log` | Client reply outcomes + revenue realized |
| `text_signals` | NLP-extracted signals from emails, calls, CRM notes |
| `negotiation_log` | Multi-turn negotiation conversation threads |
| `follow_up_queue` | Scheduled follow-up emails (Feature 1) |
| `churn_escalation_log` | Churn escalation records with account manager alerts (Feature 3) |
| `analytics_snapshots` | Weekly ROI metric snapshots for trend charts (Feature 2) |
| `crm_sync_log` | HubSpot deal sync history (Feature 5) |
| `alerts` | Dispatched Slack/Telegram alert records |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- (Optional) Anthropic or OpenAI API key for LLM-powered proposals

### 1. Install backend

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

### 2. Install frontend

```bash
cd frontend
npm install
cd ..
```

### 3. Configure (optional)

```bash
# Create a .env file in the project root — all settings have safe defaults
cp .env.example .env   # or create manually (see Configuration below)
```

The app runs fully in demo mode with no `.env` file at all.

### 4. Seed the database

```bash
python scripts/seed_db.py
python scripts/run_detection.py
```

This creates `data/db/opportunities.db` with 75 synthetic clients, their KPI history, text signals, and 100+ detected opportunities.

### 5. Start both servers

**Terminal 1 — FastAPI backend:**
```bash
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — React frontend:**
```bash
cd frontend
npm run dev
```

Open **http://localhost:5173** — the app starts on the **Opportunities** page.

### Windows shortcut

`run.bat` is provided to launch both processes together.

### Optional: train the ML model

```bash
python scripts/train_model.py
```

Produces `data/models/rf_model.pkl`. The scorer falls back to rule-only scoring when the model file doesn't exist.

### Optional: run the full daily pipeline

```bash
python scripts/daily_job.py
```

---

## Configuration

All settings live in `config.py` and are sourced from environment variables via `.env`.

```dotenv
# ── Demo toggle ─────────────────────────────────────────────────
# true  → no external API calls; all I/O written to local JSONL files
# false → real SendGrid, HubSpot, WhatsApp, Stripe, Slack, etc.
DEMO_MODE=true

# ── LLM ─────────────────────────────────────────────────────────
LLM_PROVIDER=anthropic          # openai | anthropic
LLM_MODEL=claude-haiku-4-5-20251001
ANTHROPIC_API_KEY=sk-ant-...    # optional — enables LLM proposals + negotiation
OPENAI_API_KEY=sk-...           # optional — alternative provider

# ── Email ────────────────────────────────────────────────────────
SENDGRID_API_KEY=SG.xxx         # production only
EMAIL_FROM=agent@youragency.com

# ── Payments ─────────────────────────────────────────────────────
STRIPE_SECRET_KEY=sk_live_...   # production only

# ── Notifications ────────────────────────────────────────────────
SLACK_WEBHOOK_URL=https://hooks.slack.com/...

# ── Synthetic data ───────────────────────────────────────────────
SYNTHETIC_CLIENT_COUNT=75
SYNTHETIC_SEED=42               # fixed seed for reproducible demo data
```

**Minimum config for full demo (no API keys needed):**
```dotenv
DEMO_MODE=true
```

**Minimum config to enable LLM proposals + negotiation:**
```dotenv
DEMO_MODE=true
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Platform Features

Seven features extend the core detect → propose → approve cycle into a closed-loop revenue system:

### Feature 1 — Automated Follow-Up Sequences

When a client ignores a proposal, the agent schedules up to 3 follow-up emails at increasing urgency angles (value reminder → social proof → expiring offer). Each turn uses a different subject line and angle. Sequences cancel automatically on any positive reply.

- **Engine:** `src/agents/follow_up_engine.py`
- **API:** `GET /api/follow-ups`, `POST /api/follow-ups/schedule`, `POST /api/follow-ups/process`
- **UI:** "Follow-Ups" tab in Proposals page
- **Demo mode:** emails logged to `logs/follow_ups.jsonl`

### Feature 2 — Executive ROI Dashboard

Aggregates pipeline value, revenue realized, acceptance rate, time saved, and per-type breakdowns across configurable rolling windows. Weekly snapshots are stored for trend charts.

- **Engine:** `src/agents/analytics_engine.py`
- **API:** `GET /api/analytics/summary?period_days=N`, `POST /api/analytics/snapshot`
- **UI:** Analytics → ROI Dashboard page

### Feature 3 — Churn Prevention Escalation Engine

Scans NLP signals daily for clients with active churn risk or urgency flags. Creates escalation records and notifies account managers. High-churn clients also trigger retention proposals.

- **Engine:** `src/agents/churn_escalation.py`
- **API:** `POST /api/churn/scan`, `GET /api/churn/escalations`
- **UI:** "Churn" tab in Text Signals page — "Run Churn Scan" button + escalation log
- **Demo mode:** escalations logged to `logs/churn_escalations.jsonl`

### Feature 4 — Client Propensity Tiers

Each client is scored by their historical proposal acceptance rate and classified into High / Medium / Low propensity tiers. Tier badges appear on every opportunity card; a filter lets account managers focus on the highest-propensity accounts.

- **Engine:** `src/agents/propensity_ranker.py`
- **API:** `POST /api/propensity/update`, `GET /api/propensity/clients`
- **UI:** Propensity badge + filter dropdown in Opportunities page
- **Schema:** `propensity_score`, `propensity_tier`, `propensity_updated_at` columns on `clients`

### Feature 5 — CRM Write-Back (HubSpot)

Accepted proposals are pushed to HubSpot as closed-won deals, keeping CRM deal stages in sync with agent activity. The sync log is viewable in the Proposals page.

- **Integration:** `src/integrations/hubspot.py`
- **API:** `GET /api/crm/sync-log`, `POST /api/crm/sync`
- **Trigger:** `feedback_loop.py` on `INTENT_ACCEPTED`
- **Demo mode:** deal records logged to `logs/crm_sync.jsonl`

### Feature 6 — Seasonal Opportunity Calendar

Score multipliers are applied based on the marketing calendar — Q4 budget season (×1.20), Black Friday (×1.18), mid-year sprint (×1.10), summer campaigns (×1.12), and more. Upcoming events with their boost percentages appear in an expandable calendar panel on the Opportunities page.

- **Engine:** `src/agents/seasonal_engine.py`
- **API:** `GET /api/seasonal/upcoming?weeks=N`, `GET /api/seasonal/boosts`
- **UI:** "▸ Seasonal Calendar" toggle in Opportunities page
- **Integration:** Applied as a post-score multiplier in `scorer.py` (does not affect ML training)

### Feature 7 — WhatsApp Business Outreach Channel

Opted-in clients can receive proposal outreach via WhatsApp Business API. Each client has a `preferred_channel` field (`email` by default). Clients are opted in per-account by setting `whatsapp_number` and `whatsapp_opted_in=1`.

- **Integration:** `src/integrations/whatsapp.py`
- **API:** `PATCH /api/clients/channel`, `GET /api/whatsapp/log`
- **Demo mode:** messages logged to `logs/whatsapp_log.jsonl`
- **Schema:** `whatsapp_number`, `whatsapp_opted_in`, `preferred_channel` on `clients`

---

## Module Reference

### `config.py`

Central configuration loaded at import time.

| Name | Type | Default | Description |
|---|---|---|---|
| `DEMO_MODE` | `bool` | `True` | When `True`, all external I/O goes to local JSONL files |
| `DB_PATH` | `Path` | `data/db/opportunities.db` | SQLite database path |
| `LOGS_DIR` | `Path` | `logs/` | Demo-mode log file directory |
| `LLM_PROVIDER` | `str` | `"openai"` | `"anthropic"` \| `"openai"` |
| `LLM_MODEL` | `str` | `"gpt-3.5-turbo"` | Model ID passed to the LLM API |

---

### `src/db/schema.py`

```python
from src.db.schema import get_connection, init_db, migrate_db

init_db()      # create all 12 tables if they don't exist (idempotent)
migrate_db()   # add columns/tables to existing DBs without dropping data
conn = get_connection()   # sqlite3.Connection with WAL mode + Row factory
```

Both `init_db()` and `migrate_db()` run automatically at FastAPI startup. `migrate_db()` is safe to call repeatedly — it only adds, never drops.

---

### `src/agents/`

#### `rules.py` — Rule-based detector

```python
from src.agents.rules import evaluate_all_rules

results = evaluate_all_rules(metrics_dict)
# Returns: list of OpportunityResult(type, score, rationale, suggested_price)
```

7 `if/then` rules derived from agency benchmarks. Always available as fallback when the ML model has no training data.

#### `scorer.py` — Blended scorer

```python
from src.agents.scorer import score_all_clients, persist_opportunities

results = score_all_clients()
# Applies rules → ML probability → seasonal multiplier → propensity sort
persist_opportunities(results)
```

**Blending formula:** `final_score = 0.55 × (ml_prob × 100) + 0.45 × rule_score × seasonal_boost`

#### `feedback_loop.py` — Client reply processor

```python
from src.agents.feedback_loop import record_client_reply

result = record_client_reply(proposal_id, intent="accepted", notes="...")
```

**6 intents and their side effects:**

| Intent | Side effects |
|---|---|
| `accepted` | Mark accepted · create Stripe payment link · sync to HubSpot CRM |
| `rejected` | Mark rejected · reduce confidence modifier |
| `too_expensive` | Mark rejected · start LLM negotiation (Sprint 7) |
| `need_more_info` | Keep open · flag for human follow-up |
| `ignored` | Mark ignored · schedule follow-up sequence (Feature 1) |
| `escalated` | Alert account manager immediately |

#### `follow_up_engine.py` — Automated follow-up sequences (Feature 1)

```python
from src.agents.follow_up_engine import schedule_follow_up, process_due_follow_ups

# Schedule 3-turn sequence for an ignored proposal
entries = schedule_follow_up(proposal_id, client_id)

# Process all due entries (called by daily_job.py)
result = process_due_follow_ups()
# Returns: { processed: N }
```

Follow-up angles: `value_reminder` (day 3) → `social_proof` (day 7) → `expiring_offer` (day 14).

#### `analytics_engine.py` — ROI metrics (Feature 2)

```python
from src.agents.analytics_engine import get_analytics_summary, save_analytics_snapshot

summary = get_analytics_summary(period_days=30)
# Returns: pipeline_value, revenue_realized, roi_pct, acceptance_rate,
#          proposals_sent/accepted/rejected, time_saved_hours, by_type[], weekly_trend[]

save_analytics_snapshot()   # persists today's metrics to analytics_snapshots table
```

#### `churn_escalation.py` — Churn scanner (Feature 3)

```python
from src.agents.churn_escalation import scan_and_escalate

result = scan_and_escalate()
# Returns: { escalated: N, records: [...] }
# Demo mode: writes to logs/churn_escalations.jsonl
```

#### `propensity_ranker.py` — Client tier scoring (Feature 4)

```python
from src.agents.propensity_ranker import update_all_propensity_tiers, get_propensity_summary

update_all_propensity_tiers()   # updates propensity_score + propensity_tier on all clients
summary = get_propensity_summary()
# Returns: { high: N, medium: N, low: N }
```

Scoring: acceptance rate from `feedback_log`. Defaults to `medium` for clients with no feedback history.

#### `seasonal_engine.py` — Seasonal multipliers (Feature 6)

```python
from src.agents.seasonal_engine import (
    get_seasonal_multiplier,
    get_upcoming_events,
    apply_seasonal_boosts,
)

mult = get_seasonal_multiplier("retargeting_campaign")  # e.g. 1.18 in October
events = get_upcoming_events(n_weeks=8)  # upcoming marketing calendar events
results = apply_seasonal_boosts(scored_results)  # annotates seasonal_boost field
```

#### `negotiator.py` — Multi-turn negotiation (Sprint 7)

```python
from src.agents.negotiator import start_negotiation, process_client_reply, kill_negotiation

neg = start_negotiation(proposal_id)        # Turn 1: 10% discount offer
result = process_client_reply(proposal_id, "¿Puede bajar un poco más?")
kill_negotiation(proposal_id, reason="manual_kill_switch_ui")
```

3 autonomous turns (10% → 15% → 20% discount). Escalates to human on turn 4 or if discount request exceeds 20%.

---

### `src/integrations/`

#### `hubspot.py` (Feature 5)

```python
from src.integrations.hubspot import sync_deal_to_crm

result = sync_deal_to_crm(
    proposal_id, client_id, revenue, opportunity_type
)
# Demo mode: logs to logs/crm_sync.jsonl
# Production: POST to HubSpot CRM API v3
```

#### `whatsapp.py` (Feature 7)

```python
from src.integrations.whatsapp import send_whatsapp_message

result = send_whatsapp_message(
    to_number="+1234567890",
    subject="New proposal for your account",
    body="..."
)
# Demo mode: logs to logs/whatsapp_log.jsonl
# Production: POST to WhatsApp Business Cloud API
```

---

### `src/nlp/`

#### `signal_extractor.py`

Extracts 6 behavioral signals from raw text. Two-pass: keyword matching first, then optional LLM for ambiguous cases.

```python
from src.nlp.signal_extractor import extract_signals

signals = extract_signals("El precio está muy alto, necesitamos mejores resultados")
# Returns: { sentiment, mentions_price, asks_for_results, churn_risk, urgency_signal, interest_signal }
```

#### `pipeline.py`

```python
from src.nlp.pipeline import run_pipeline

summary = run_pipeline(use_llm=False, reprocess_all=False)
# Returns: { total_processed, churn_alerts, urgency_alerts, errors }
```

---

### `src/ml/`

**18 features** used by the RandomForestClassifier:

| Feature | Source |
|---|---|
| `bounce_rate`, `conversion_rate`, `pages_per_session`, `organic_traffic` | Google Analytics |
| `ctr`, `cpc`, `roas`, `ad_spend` | Meta Ads |
| `email_open_rate`, `email_click_rate` | Email Marketing |
| `keyword_rankings` | SEO |
| `days_since_last_contact`, `days_inactive`, `account_age_days` | CRM |
| `sentiment`, `mentions_price`, `asks_for_results`, `churn_risk`, `urgency_signal` | NLP Pipeline |

```python
from src.ml.model import train_model, load_model
from src.ml.inference import update_ml_scores

metrics = train_model()       # trains + saves to data/models/rf_model.pkl
update_ml_scores()            # updates ml_probability in opportunities table
```

---

### `scripts/`

#### `seed_db.py`

```bash
python scripts/seed_db.py [--clients N] [--seed N]
```

Creates the DB and populates it with synthetic clients, metrics, and demo text signals. Safe to re-run.

#### `run_detection.py`

```bash
python scripts/run_detection.py [--demo-only] [--min-score 70]
```

Runs the full opportunity detection pipeline without starting the server.

#### `train_model.py`

```bash
python scripts/train_model.py [--n-estimators 200] [--quiet]
```

Trains the RandomForestClassifier and saves it to `data/models/rf_model.pkl`.

#### `process_text.py`

```bash
python scripts/process_text.py [--reprocess] [--use-llm] [--quiet]
```

Runs the NLP signal extraction pipeline over all unprocessed `text_signals` rows.

#### `daily_job.py`

Full daily pipeline orchestrator. In production: triggered by cron at 08:00.

```bash
python scripts/daily_job.py [options]

Options:
  --demo-only            Only process demo scenario clients
  --dry-run              Detect but don't persist or dispatch
  --no-proposals         Skip proposal generation
  --no-auto-send         Skip Tier C auto-send
  --no-nlp               Skip NLP pipeline
  --proposal-min-score N Raise the proposal threshold (default: 70)
  --channel telegram     Dispatch alerts to Telegram instead of Slack
```

**Pipeline steps:**
1. Pull latest metrics from all data sources
2. Apply rules engine + ML model to every client
3. Apply seasonal boosts + propensity ranking
4. Persist new opportunities to DB
5. Dispatch alerts (Slack / Telegram / log)
6. Generate proposals for opportunities ≥ score threshold
7. Process Tier C auto-send queue + follow-up sequences
8. Run NLP text processing pipeline
9. Save analytics snapshot (Fridays)

```
Production cron:
  0 8 * * *   cd /app && python scripts/daily_job.py >> logs/cron.log 2>&1
```

---

## Sprint History

| Sprint | Focus | Key Deliverable |
|---|---|---|
| 0 | Foundation | SQLite schema, synthetic data generator (75 clients), data source adapters |
| 1 | Detection | Rule-based engine (7 rules), opportunity scoring |
| 2 | Alerting | Slack/Telegram dispatcher, alert feed UI, accuracy measurement |
| 3 | Proposals | LLM proposal generator (7 templates), Approve/Reject/Edit UI, GOVERNANCE.md |
| 4 | Autonomy | SendGrid sender, feedback loop, 3-tier autonomy engine, pilot cycle UI |
| 5 | ML | RandomForestClassifier + SHAP, 18-feature dataset, blended scoring (55% ML + 45% rules) |
| 6 | NLP | Text signal extraction (6 signals), batch NLP pipeline, text signals dashboard |
| 7 | Negotiation | Multi-turn LLM negotiation, Stripe payment links, kill-switch UI |
| ROADMAP | React migration + 7 features | React 18 + FastAPI migration; Follow-Up Sequences, ROI Dashboard, Churn Escalation, Propensity Tiers, CRM Write-Back, Seasonal Calendar, WhatsApp Channel |

---

## Demo Mode vs Production

Every module checks `config.DEMO_MODE` at call time and takes a different path:

| Feature | Demo Mode (`DEMO_MODE=true`) | Production Mode (`DEMO_MODE=false`) |
|---|---|---|
| Data sources | SQLite synthetic data | Live API calls (GA4, Meta, HubSpot, etc.) |
| Email sending | `logs/sent_emails.jsonl` | SendGrid API |
| Follow-up emails | `logs/follow_ups.jsonl` | SendGrid API |
| HubSpot CRM sync | `logs/crm_sync.jsonl` | HubSpot CRM API v3 |
| WhatsApp outreach | `logs/whatsapp_log.jsonl` | WhatsApp Business Cloud API |
| Churn escalations | `logs/churn_escalations.jsonl` | Slack webhook with @mention |
| Slack alerts | `logs/alerts.jsonl` | Slack webhook |
| LLM proposals | Template fallback (no key needed) | Claude Haiku or GPT-3.5 |
| Stripe links | Fake URL (`buy.stripe.com/demo/...`) | Real Stripe Payment Link |
| Negotiation | Template responses | LLM-generated (Claude Haiku) |
| Calendar | `logs/calendar_events.jsonl` | Google Calendar API v3 |

Demo-mode log files are structured identically to real production payloads — the demo is fully production-realistic without any external accounts.

---

## Autonomy Tiers & Governance

See [`GOVERNANCE.md`](planning/GOVERNANCE.md) for the full policy.

| Tier | Condition | Action |
|---|---|---|
| **A** | score < 70 | Draft only — no email sent |
| **B** | score 70–89 OR price > $200 | Generate + notify account manager — human approves via UI |
| **C** | score ≥ 90 AND price ≤ $200 AND repeat client | Auto-send + BCC account manager (30-min cancel window) |

**Negotiation limits:**
- Maximum 3 autonomous discount turns: 10% → 15% → 20%
- Any request beyond 20% escalates to human
- Kill-switch available at any time via the Negotiation page

**Hard prohibitions (cannot be overridden by config):**
- Never email anyone outside the agency CRM
- Never impersonate a human account manager without disclosure
- Never store client data outside approved databases

---

## Running Tests

```bash
# Full suite
python -m pytest tests/ -v

# Single sprint
python -m pytest tests/test_sprint7.py -v

# With coverage
python -m pytest tests/ --cov=src --cov-report=term-missing
```

**Test isolation:** Every test that touches the DB uses an `isolated_db` fixture that monkeypatches `config.DB_PATH` to a temporary file. Tests never touch the real database.

| File | Tests | Coverage |
|---|---|---|
| `test_sprint0.py` | 12 | Data seeding, source adapters |
| `test_sprint1.py` | 22 | Rules engine, all 7 opportunity types |
| `test_sprint2.py` | 20 | Scorer, alerts, accuracy metrics |
| `test_sprint3.py` | 35 | Proposal generator, LLM fallback, approval flow |
| `test_sprint4.py` | 46 | Email sender, feedback loop, auto-sender, pilot metrics |
| `test_sprint5.py` | 47 | Dataset, model training, SHAP explainer, inference |
| `test_sprint6.py` | 35 | NLP extractor, pipeline, signal aggregation |
| `test_sprint7.py` | 31 | Negotiator, payment links, schema migration |
| **Total** | **313** | |

---

## Docker

```bash
# Build
docker build -t hidden-opp-agent .

# Run backend (port 8000) + frontend (port 5173)
docker run -p 8000:8000 -p 5173:5173 \
  -e DEMO_MODE=true \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  hidden-opp-agent

# With a persistent volume for the database
docker run -p 8000:8000 -p 5173:5173 \
  -v $(pwd)/data:/app/data \
  -e DEMO_MODE=true \
  hidden-opp-agent
```

---

*All client data in this system is synthetic. No real emails, CRM records, WhatsApp messages, or payments are created in demo mode.*
