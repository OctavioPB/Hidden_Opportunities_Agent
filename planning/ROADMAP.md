# Product Roadmap — Hidden Opportunities Agent

**Version:** 1.0  
**Date:** 2026-05-29  
**Owner:** OPB · Octavio Pérez Bravo  
**Horizon:** Next 6 sprints (12 weeks)

---

## Context

The current system detects opportunities, generates proposals, routes them through a human-approval workflow, and records client replies. The detection → proposal → dispatch → feedback loop is complete. The next stage of value comes from three directions:

1. **Conversion depth** — the agent detects opportunities but only reaches a fraction of their potential. Most proposals get one send; most ignored clients never hear back.
2. **Retention intelligence** — churn signals are already detected by the NLP pipeline but trigger no automated action.
3. **Stakeholder visibility** — account managers and agency owners lack a single view of what the agent is delivering commercially.

The seven features below are ordered by their expected impact on **agency revenue** and **client retention**, not by engineering convenience.

---

## Priority Overview

| # | Feature | Impact | Effort | Leverages existing? |
|---|---|---|---|---|
| 1 | Automated Follow-Up Sequences | ★★★★★ | M | ✅ High |
| 2 | Executive ROI Dashboard + Weekly Digest | ★★★★★ | M | ✅ High |
| 3 | Churn Prevention Escalation Engine | ★★★★☆ | M | ✅ High |
| 4 | Client Propensity Tiers (Intelligent Prioritization) | ★★★★☆ | L | ✅ High |
| 5 | CRM Write-Back (HubSpot / Salesforce) | ★★★☆☆ | L | ✅ Medium |
| 6 | Seasonal Opportunity Calendar | ★★★☆☆ | L | ✅ Medium |
| 7 | WhatsApp Business Outreach Channel | ★★★☆☆ | M | ✅ High |

**Effort:** S = ≤3 days · M = 1–2 weeks · L = 2–4 weeks  
**Impact:** Stars reflect expected contribution to agency revenue or retention over a 90-day window.

---

## Feature 1 — Automated Follow-Up Sequences

### Business case

The current system sends one proposal per detected opportunity and waits. When a client does not reply, the outcome is logged as `INTENT_IGNORED` in `feedback_log` and confidence is reduced — but nothing else happens. Industry benchmarks for B2B email outreach show 2–5% response on the first touch, rising to 15–25% by the third or fourth contact. The agent is capturing only the first-touch response rate and leaving the majority of conversion potential unused.

A systematic follow-up sequence — three touches spaced 7 and 14 days apart, each with a different angle — would materially increase proposal acceptance rates without detecting additional opportunities.

**Expected outcome:** 3–5× increase in acceptance rate on detected opportunities; measurable in `feedback_log` within one pilot period.

### What the system already has

- `feedback_log` table with `intent`, `proposal_id`, `client_id`, `confidence_delta`, and timestamps.
- `INTENT_IGNORED` constant in `src/agents/feedback_loop.py` — the trigger event is already defined.
- `generate_proposal()` and `send_proposal_email()` in `src/agents/proposal_generator.py` and `email_sender.py` — reusable for follow-up sends.
- `negotiator.py` already writes multi-turn conversation threads — the same `negotiation_log` table can track follow-up sequence turns.
- LLM integration with deterministic template fallback — follow-up copy can be generated with a different prompt.

### What needs to be built

**Schema change** — add `follow_up_queue` table:
```sql
CREATE TABLE follow_up_queue (
    id             TEXT PRIMARY KEY,
    proposal_id    TEXT REFERENCES proposals(id),
    client_id      TEXT REFERENCES clients(id),
    sequence_turn  INTEGER DEFAULT 1,   -- 1, 2, or 3
    scheduled_at   TEXT NOT NULL,       -- ISO 8601, when to send
    status         TEXT DEFAULT 'pending',  -- pending | sent | cancelled
    angle          TEXT,                -- 'roi_focus' | 'competitor' | 'final_reminder'
    created_at     TEXT DEFAULT (datetime('now'))
);
```

**New module** — `src/agents/follow_up_engine.py`:
- `schedule_follow_up(proposal_id)` — called when `INTENT_IGNORED` is recorded; creates 2 queue entries at T+7 and T+14 days.
- `process_due_follow_ups()` — called by the daily job; queries `follow_up_queue WHERE scheduled_at <= now AND status='pending'`, generates a new email variant for each angle, and sends via `send_proposal_email()`.
- `cancel_follow_ups(proposal_id)` — called on `INTENT_ACCEPTED`, `INTENT_REJECTED`, or `INTENT_ESCALATED` to prevent contact after resolution.

**Modify existing** — `src/agents/feedback_loop.py`:
- In `record_client_reply()`, after logging `INTENT_IGNORED`, call `schedule_follow_up(proposal_id)`.
- After any positive resolution, call `cancel_follow_ups(proposal_id)`.

**New FastAPI router** — `backend/routers/follow_ups.py`:
- `GET /api/follow-ups` — list the queue with status and scheduled dates.
- `DELETE /api/follow-ups/{id}` — manually cancel a scheduled follow-up.

**Modify daily job** — `scripts/daily_job.py`: add `process_due_follow_ups()` as step 4.

**Frontend** — new panel inside the Proposals page ("Follow-Up Queue" section): shows scheduled follow-ups per proposal, their angle, and a cancel button.

### Effort & risk

**Effort:** M (1–2 weeks)  
**Risk:** Low — no new external dependencies. All components are recombinations of existing modules.  
**Governance consideration:** Add `MAX_FOLLOW_UPS_PER_PROPOSAL = 3` and `MIN_DAYS_BETWEEN_FOLLOW_UPS = 7` to `GOVERNANCE.md` thresholds.

---

## Feature 2 — Executive ROI Dashboard + Weekly Digest

### Business case

Agency owners and C-level stakeholders are not the people using the daily Proposals page. They evaluate whether to continue using the agent based on a single question: *Is this delivering more revenue than it costs?* The current system has all the data to answer this question — `feedback_log` has `revenue` columns, `proposals` has `status` history, `feedback_log` has `confidence_delta` — but it is scattered across six pages with no executive summary.

Without a clear ROI view, renewal decisions are made on gut feel. A visible return on investment figure accelerates both internal adoption and justification to agency clients.

**Expected outcome:** Reduction in churn of the tool itself; faster onboarding of skeptical stakeholders; baseline for pricing discussions.

### What the system already has

- `feedback_log.revenue` — revenue recorded per accepted proposal.
- `proposals` table — full proposal lifecycle (draft → approved → sent → accepted).
- `get_pilot_metrics()` in `feedback_loop.py` — already computes total opportunities, proposals sent, acceptance rate, revenue, and time saved.
- `load_training_history()` in `src/ml/model.py` — AUC-ROC over time is already stored.

### What needs to be built

**New FastAPI router** — `backend/routers/analytics.py`:
- `GET /api/analytics/summary?period=30d|90d|all` — aggregates:
  - Total pipeline value detected (sum of `suggested_price` on all opportunities).
  - Proposals sent, accepted, rejected, ignored (from `proposals` + `feedback_log`).
  - Estimated time saved: `proposals_generated × 25 minutes` (industry benchmark for manual proposal writing).
  - Conversion rate trend: rolling 7-day acceptance rate.
  - Revenue per account manager.
- `GET /api/analytics/weekly-digest` — computes the delta vs. previous 7 days for each metric.
- `POST /api/analytics/send-digest` — generates a digest email and sends it via SendGrid to a configured recipient list.

**New frontend page** — `frontend/src/pages/AnalyticsDashboardPage.tsx`:
- Hero stats: Pipeline Detected / Revenue Realized / Acceptance Rate / Time Saved.
- Trend charts: hand-coded SVG sparklines for acceptance rate over time (data from weekly snapshots stored in a new `analytics_snapshots` table).
- Breakdown by account manager and by opportunity type.
- "Send Digest Now" button.

**Schema change** — `analytics_snapshots` table to persist weekly rollups (so the chart doesn't recompute history from scratch each load).

**Scheduled digest** — add `send_weekly_digest()` call to the daily job on Fridays (check `datetime.now().weekday() == 4`).

**Nav change** — add "Analytics Dashboard" to the Analytics nav group.

### Effort & risk

**Effort:** M (1–2 weeks)  
**Risk:** Low — all data exists; the only new external call is a SendGrid email for the digest, which is already integrated.

---

## Feature 3 — Churn Prevention Escalation Engine

### Business case

The NLP pipeline already identifies `churn_risk` and `urgency_signal` flags in client communications. These flags appear in the Text Signals page and that is where they stop. There is no automated action when a client says they are unhappy, considering leaving, or asking competitors for quotes.

Retaining an existing client costs, on average, five times less than acquiring a new one. A churn signal detected on a Monday that triggers an account manager call by Tuesday morning can prevent a cancellation that would take months to replace in new business.

**Expected outcome:** 10–20% reduction in client churn during the pilot period; measurable by comparing 90-day retention rates before and after activation.

### What the system already has

- `text_signals` table with `churn_risk`, `urgency_signal`, `mentions_price`, and `sentiment` columns — all populated by the NLP pipeline.
- `get_urgency_alerts()` in `src/data_sources/text_signals.py` — already queries and returns churn/urgency clients.
- `dispatch()` in `src/agents/alerts.py` — Slack/Telegram dispatch infrastructure is already built and tested.
- `send_proposal_email()` in `email_sender.py` — can be repurposed to send a retention-specific email template.
- `account_manager` column in `clients` table — the right person is already known.

### What needs to be built

**New module** — `src/agents/churn_escalation.py`:
- `run_churn_scan()` — calls `get_urgency_alerts()`, filters for clients not already escalated in the past 7 days (`churn_escalation_log`), and for each qualifying client:
  1. Sends a Slack DM to the assigned `account_manager` with the client name, churn signals detected, and the most recent text snippet.
  2. Generates a retention email draft using the LLM (prompt: "write a check-in email that does not mention the churn risk directly").
  3. Saves the draft as a `proposal` with `status='draft'` and `opportunity_type='retention_check_in'`.
  4. Logs the escalation to `churn_escalation_log` to enforce the 7-day deduplication window.
- `get_churn_escalation_log()` — returns recent escalations for the UI.

**Schema change** — `churn_escalation_log` table:
```sql
CREATE TABLE churn_escalation_log (
    id                TEXT PRIMARY KEY,
    client_id         TEXT REFERENCES clients(id),
    account_manager   TEXT,
    churn_signal      TEXT,           -- e.g. 'churn_risk', 'urgency_signal'
    escalated_at      TEXT,
    proposal_id       TEXT,           -- retention draft created
    slack_sent        INTEGER DEFAULT 0,
    email_draft_id    TEXT
);
```

**Modify daily job** — add `run_churn_scan()` at 07:30 (before the main opportunity scan), so account managers receive churn alerts before the morning briefing.

**New FastAPI endpoint** — `GET /api/churn/escalations?period=7d` — returns recent escalation log for the UI.

**Frontend** — add a "Churn Alerts" section to the Text Signals page (currently the data is shown statically; this section adds the escalation log and a "Escalate Now" button for manual triggering).

**New opportunity type** — add `RETENTION_CHECK_IN = "retention_check_in"` to `src/agents/rules.py` with `suggested_price = 0` (retention is free; the value is avoiding churn, not upselling). This makes retention proposals flow through the standard proposal → approval → send workflow without special-casing.

### Effort & risk

**Effort:** M (1–2 weeks)  
**Risk:** Low on the backend (all components exist). Medium on the UX — the account manager Slack DM must be carefully written so it does not panic the recipient or feel automated/robotic.

---

## Feature 4 — Client Propensity Tiers (Intelligent Prioritization)

### Business case

The agent currently treats all 75 clients equally: every client is scanned daily, every detected opportunity generates a proposal, and every proposal is dispatched. In practice, some clients accept 70% of proposals (high-propensity accounts) while others have never accepted a single one (low-propensity accounts, possibly wrong-fit).

Sending proposals to low-propensity clients at the same frequency as high-propensity clients creates two problems. First, it dilutes the account manager's attention (every proposal they review has the same priority regardless of conversion likelihood). Second, it risks irritating low-propensity clients with repeated outreach they ignore or reject.

Segmenting clients into propensity tiers and adjusting scan frequency and quota accordingly would increase the overall acceptance rate without detecting more opportunities.

**Expected outcome:** 20–35% increase in acceptance rate for the top propensity tier; reduction in ignored proposals by 40%.

### What the system already has

- `feedback_log` — contains every proposal outcome (`intent`, `proposal_id`, `client_id`) with enough history to compute a per-client acceptance rate.
- `opportunities` table — full history of detected opportunities per client.
- `clients` table — `account_age_days`, `monthly_spend`, `industry` are already stored.
- RandomForest ML model (`src/ml/`) — already uses features per client; extending it with a propensity score (a second classification target: "will this client accept a proposal?") is a natural extension of the existing training pipeline.
- `_metrics_to_row()` in `src/ml/dataset.py` — feature engineering already handles the numeric encoding of industry and opportunity type.

### What needs to be built

**Extend `src/ml/dataset.py`**:
- Add a `build_propensity_dataset()` function that creates training rows where the label is `1` if `feedback_log.intent == 'accepted'` for a client in the past 90 days, `0` otherwise.
- Features: `account_age_days`, `monthly_spend`, `industry_code`, `acceptance_rate_90d`, `avg_score_of_sent_proposals`, `n_proposals_sent`, `n_proposals_accepted`.

**Extend `src/ml/model.py`**:
- Add a second model artifact: `data/models/propensity_model.joblib`.
- Add `train_propensity_model()` and `get_client_propensity_score(client_id)` functions.

**Schema change** — add `propensity_tier` and `propensity_score` to `clients`:
```sql
ALTER TABLE clients ADD COLUMN propensity_score REAL;
ALTER TABLE clients ADD COLUMN propensity_tier TEXT;  -- 'high' | 'medium' | 'low'
ALTER TABLE clients ADD COLUMN propensity_updated_at TEXT;
```

**New module** — `src/agents/propensity_ranker.py`:
- `update_client_propensity_tiers()` — runs after each daily scan; computes propensity for all clients and updates the `clients` table.
- `get_high_propensity_clients()` — returns clients with `propensity_tier = 'high'`.

**Modify `score_all_clients()`** in `src/agents/scorer.py`:
- Sort output by `propensity_tier` first (high → medium → low), then by blended score. This surfaces the most actionable opportunities at the top without filtering out low-propensity clients entirely.
- Add a `scan_frequency` check: low-propensity clients are scanned every 3 days instead of daily (reduce noise).

**New FastAPI endpoint** — `GET /api/clients/propensity` — returns all clients with their tier and score.

**Frontend** — add a "Propensity" column and colour-coded tier badge to the Opportunities table view. Add a filter: "High propensity only" toggle.

### Effort & risk

**Effort:** L (2–3 weeks)  
**Risk:** Medium — propensity model requires sufficient feedback history (minimum 20–30 feedback rows) to produce meaningful predictions. In the first weeks of a new deployment, the model will fall back to a simple rule-based tier: `acceptance_rate_90d > 0.5 → high`, `0.2–0.5 → medium`, `< 0.2 → low`.

---

## Feature 5 — CRM Write-Back (HubSpot / Salesforce)

### Business case

Account managers use HubSpot (or Salesforce) as their primary work surface. They log calls, track deals, and measure their pipeline in the CRM — not in this tool. When the agent accepts a proposal and revenue is recorded in `feedback_log`, nothing flows back into HubSpot. This creates a data silo: the agent's output is invisible to the CRM and therefore to any reporting that originates from it.

CRM write-back closes this gap. When a client accepts a proposal, the agent automatically creates a deal in HubSpot, logs the activity on the contact record, and updates the `lifecycle_stage`. Account managers see the result of the agent's work in the tool they already use, which drives trust and adoption.

**Expected outcome:** CRM data quality improvement; reduction in manual data entry time estimated at 15–20 minutes per accepted proposal; better alignment between agent output and quarterly revenue reports.

### What the system already has

- `feedback_log` — `INTENT_ACCEPTED` is the trigger event; `revenue` is already stored.
- `clients` table — `contact_email` and `account_manager` are stored; HubSpot contact ID could be stored in a new column.
- `src/agents/email_sender.py` — already handles SendGrid API calls; the pattern for a typed API client is established and can be replicated for HubSpot.
- `httpx` is already in `requirements.txt` — can be used directly for HubSpot API calls.

### What needs to be built

**Schema change** — add CRM identifiers to `clients`:
```sql
ALTER TABLE clients ADD COLUMN crm_contact_id TEXT;   -- HubSpot contact ID
ALTER TABLE clients ADD COLUMN crm_deal_id    TEXT;   -- last created deal ID
```

**New module** — `src/integrations/hubspot.py`:
- `create_deal(client_id, proposal_id, revenue, opportunity_type)` — POST to `https://api.hubapi.com/crm/v3/objects/deals` with deal name, amount, pipeline stage, and associated contact.
- `log_activity(client_id, note)` — POST to HubSpot engagements API to add a note on the contact record.
- `update_lifecycle_stage(client_id, stage)` — update contact property `lifecyclestage` to `'customer'` on acceptance.
- Reads `HUBSPOT_API_KEY` from `.env`. In demo mode, logs to `logs/crm_sync.jsonl` instead.

**Modify `feedback_loop.py`** — in `record_client_reply()`, after processing `INTENT_ACCEPTED`:
```python
if config.DEMO_MODE:
    _log_crm_sync(proposal_id, revenue)
else:
    from src.integrations.hubspot import create_deal, log_activity
    create_deal(client_id, proposal_id, revenue, opportunity_type)
    log_activity(client_id, f"Proposal accepted via Hidden Opportunities Agent. Revenue: ${revenue:,.0f}")
```

**New FastAPI endpoint** — `GET /api/crm/sync-log` — returns the `crm_sync.jsonl` log in demo mode.

**Frontend** — add a "CRM Sync" status indicator per accepted proposal in the Proposals page (a small HubSpot icon + "Synced" label). Add a `POST /api/crm/sync/{proposal_id}` button for manual re-sync if the automatic sync failed.

**`.env.example` additions**:
```env
HUBSPOT_API_KEY=
HUBSPOT_PIPELINE_ID=
HUBSPOT_DEAL_STAGE_ID=
```

### Effort & risk

**Effort:** L (2–3 weeks)  
**Risk:** Medium — depends on the agency having a HubSpot account with API access. The HubSpot API is well-documented and stable. Salesforce support would be a separate integration with higher complexity (OAuth, SOQL); recommend HubSpot first.

---

## Feature 6 — Seasonal Opportunity Calendar

### Business case

The current detection engine is reactive: it looks at current metric values against fixed thresholds. It does not account for *when* an opportunity is likely to appear based on the time of year. Marketing budgets follow predictable seasonal patterns: Q4 brings year-end spend, January brings planning-mode inactivity, Black Friday demands landing page readiness in October, summer months see reduced email engagement.

A client who has a Q3 ROAS of 3.5× is a borderline "Ad Budget Expansion" candidate (threshold is 4.0×). In September, that same client is two months from their highest-spend period of the year — a proactive pitch in September lands very differently from a reactive one in November.

Adding temporal awareness to the scoring engine — boosting scores for opportunity types that historically perform best in the current calendar window — would surface the right opportunities at the right time.

**Expected outcome:** 15–25% increase in acceptance rates for seasonally-adjusted proposals; reduction in proposals sent in low-conversion windows (summer).

### What the system already has

- `client_metrics` stores `date` for each snapshot — historical patterns exist in the database.
- `src/agents/rules.py` — the threshold dict `T` is already modular; adding a temporal multiplier alongside each threshold is a clean extension.
- `feedback_log` — acceptance outcomes are timestamped; historical acceptance rates by month can be computed to calibrate the multipliers.
- The ML model already uses `account_age_days` as a feature — adding `month_of_year` and `days_until_q4` as features extends the same training pipeline.

### What needs to be built

**New module** — `src/agents/seasonal_engine.py`:
- `SEASONAL_BOOSTS` — a dict mapping `(opportunity_type, month)` to a score multiplier:
  ```python
  SEASONAL_BOOSTS = {
      ("upsell_ad_budget",          [9, 10]):   1.20,  # Q4 ramp-up
      ("landing_page_optimization", [9, 10]):   1.15,  # Pre-peak prep
      ("email_automation",          [1, 2]):    1.10,  # New-year planning
      ("reactivation",              [1, 8]):    1.10,  # Post-holiday + post-summer
      ("seo_content",               [2, 3]):    1.12,  # Q1 content planning
  }
  ```
- `get_seasonal_multiplier(opportunity_type, date)` — returns the applicable multiplier (1.0 if no boost defined for this month).
- `get_upcoming_calendar_events(n_weeks=8)` — returns a list of relevant marketing calendar events in the next N weeks (BFCM, Q4 start, year-end, etc.) — hardcoded initially, API-fed later.

**Modify `score_all_clients()`** in `src/agents/scorer.py`:
- After computing `blended_score`, multiply by `get_seasonal_multiplier(opportunity_type, today)` and cap at 100.
- Log the applied multiplier in the returned dict as `seasonal_boost`.

**Extend ML training** — add `month_of_year` (1–12) and `weeks_until_q4` as features in `_metrics_to_row()` in `src/ml/dataset.py`. Retrain after adding features.

**New FastAPI endpoint** — `GET /api/calendar/upcoming` — returns the next 8 weeks of marketing calendar events and which opportunity types they boost.

**Frontend** — add a "Seasonal Calendar" panel to the Opportunities page: a 8-week horizontal timeline showing upcoming events and the opportunity types they will amplify. Helps account managers plan outreach cadence proactively.

### Effort & risk

**Effort:** L (2–4 weeks, including ML retraining)  
**Risk:** Low on the rules multiplier (pure Python, no new dependencies). Medium on the ML extension (retraining requires sufficient data across multiple months to learn seasonal patterns; before enough data exists, the hardcoded `SEASONAL_BOOSTS` dict serves as the effective mechanism).

---

## Feature 7 — WhatsApp Business Outreach Channel

### Business case

Email open rates for B2B outreach average 15–25%. WhatsApp Business messages have open rates above 80% and response times measured in minutes rather than days. For the specific segment of small and medium clients where the account manager already has a personal or WhatsApp Business relationship, switching proposal delivery to WhatsApp would dramatically increase both response rate and speed.

The alert dispatch infrastructure in `src/agents/alerts.py` already supports multiple channels (Slack, Telegram). WhatsApp Business API follows the same pattern: a POST to a hosted API with a structured message payload. The engineering lift is an additional adapter in an already-abstract dispatch layer.

**Expected outcome:** For clients where WhatsApp is the preferred channel, acceptance rates approach 2× email; response time reduces from days to hours.

### What the system already has

- `dispatch()` in `src/agents/alerts.py` — already handles Slack and Telegram as separate channel adapters with the same interface.
- `send_proposal_email()` — the email body (HTML) can be condensed to a WhatsApp message body with a link to the full proposal.
- `clients` table — `contact_email` exists; add `whatsapp_number` to store the opt-in phone number.
- `httpx` in `requirements.txt` — used for the WhatsApp Cloud API POST.
- `DEMO_MODE` pattern — in demo mode, the WhatsApp message is written to `logs/whatsapp.jsonl` instead of making an API call.

### What needs to be built

**Schema change** — add WhatsApp fields to `clients`:
```sql
ALTER TABLE clients ADD COLUMN whatsapp_number   TEXT;     -- E.164 format: +34600123456
ALTER TABLE clients ADD COLUMN whatsapp_opted_in INTEGER DEFAULT 0;
ALTER TABLE clients ADD COLUMN preferred_channel TEXT DEFAULT 'email';  -- 'email' | 'whatsapp'
```

**New module** — `src/integrations/whatsapp.py`:
- `send_whatsapp_proposal(client_id, proposal_id)` — POSTs to the Meta WhatsApp Cloud API (`https://graph.facebook.com/v19.0/{phone_number_id}/messages`).
- Message format: template message (WhatsApp requires pre-approved templates for business-initiated conversations) with the opportunity type, suggested price, and a URL to a hosted proposal preview page (Feature 7 dependency: a public/shareable proposal link).
- Reads `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN`, and `WHATSAPP_TEMPLATE_NAME` from `.env`.

**Modify `send_proposal_email()` in `email_sender.py`**:
- Check `clients.preferred_channel`; if `'whatsapp'` and `whatsapp_opted_in == 1`, call `send_whatsapp_proposal()` instead of (or in addition to) email.

**Modify `dispatch()` in `alerts.py`**:
- Add WhatsApp as a third alert channel for high-confidence (score ≥ 80) opportunities.

**New FastAPI endpoint** — `PATCH /api/clients/{id}/channel-preference` — updates `preferred_channel` and `whatsapp_number`.

**Frontend** — add a "Channel" column to the client list on the Opportunities page showing the delivery channel badge (Email / WhatsApp). Add a settings panel in the Proposals page per proposal to override the channel before sending.

**`.env.example` additions**:
```env
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_TEMPLATE_NAME=proposal_notification
```

**Compliance requirement:** WhatsApp Business API requires a Meta Business Account, phone number verification, and pre-approved message templates. Approval takes 1–5 business days. The demo mode path (logs to JSONL) allows full development and testing without Meta approval.

### Effort & risk

**Effort:** M (1–2 weeks engineering + 1–5 days Meta approval)  
**Risk:** Medium — the Meta WhatsApp Cloud API is well-documented but template approval is outside engineering control. In low-propensity markets or regulated industries, clients may not expect business communication via WhatsApp; adoption should be opt-in only.

---

## Implementation Sequence

Given the dependencies and the principle of shipping value early, the recommended sprint order is:

```
Sprint 8  — Feature 1: Automated Follow-Up Sequences
Sprint 8  — Feature 7: WhatsApp Channel (can run in parallel — independent)
Sprint 9  — Feature 2: Executive ROI Dashboard + Weekly Digest
Sprint 9  — Feature 3: Churn Prevention Escalation Engine
Sprint 10 — Feature 4: Client Propensity Tiers
Sprint 11 — Feature 5: CRM Write-Back
Sprint 12 — Feature 6: Seasonal Opportunity Calendar
```

Features 1 and 7 are the fastest to ship (both reuse existing dispatch and proposal infrastructure). Features 4 and 6 both depend on having sufficient data in `feedback_log` and `client_metrics` respectively — they are better suited for later sprints after the system has accumulated real outcome data.

---

## Governance additions required

Each feature that changes the agent's autonomous behaviour must be reviewed against `GOVERNANCE.md`. Specific additions needed:

| Feature | Governance change |
|---|---|
| 1 | Add `MAX_FOLLOW_UPS_PER_PROPOSAL = 3` and `MIN_DAYS_BETWEEN_FOLLOW_UPS = 7` |
| 3 | Add `CHURN_ESCALATION_DEDUP_WINDOW_DAYS = 7` and require account manager acknowledgement before escalation repeats |
| 4 | Document tier assignment algorithm and the minimum data requirement for ML-based tiering |
| 7 | Require explicit `whatsapp_opted_in = 1` before any WhatsApp message is sent; add to prohibited actions list: "No WhatsApp messages to clients who have not explicitly opted in" |

---

*Roadmap owner: Octavio Pérez Bravo · Review cadence: every sprint (2 weeks) · This document is version-controlled alongside the agent code.*
