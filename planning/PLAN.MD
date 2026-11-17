# Development Plan: "Hidden Opportunities Agent" for a Marketing Agency

## Overview
This plan uses **2-week sprints** to build an AI agent that autonomously detects upsell opportunities, creates proposals, negotiates, and closes low-value sales. It is designed for a marketing agency with a small team (project lead, developer/data engineer, marketing/sales expert) and low-cost or open-source tools.

**Total sprints for MVP (Sprints 1–4):** 8 weeks  
**Advanced sprints (Sprints 5–7):** 6 additional weeks  

| Sprint | Goal | Key Deliverable |
|--------|------|------------------|
| 1 | Define signals and data sources | Opportunity map + test dataset |
| 2 | Build detection engine | Agent that identifies opportunities and generates internal alerts |
| 3 | Create automated proposal generation | Agent that writes personalized proposals |
| 4 | Limited autonomous action + pilot | Agent running with 3 real clients |
| 5 | From heuristic rules to machine learning | Predictive model for opportunity probability |
| 6 | Integrate unstructured data (emails, calls, CRM notes) | Agent that understands natural language |
| 7 | Autonomous negotiation and closing of low-value sales | Agent that negotiates, closes, and collects payment |

---

## Sprint 1: Exploration and business rule definition

**Goal:** Identify which hidden sales opportunities to look for and how to detect them using existing data.

### Activities
1. **Internal workshop** (1 day) with account and sales teams:
   - List 5 types of upsell/cross-sell that worked in the past.
   - Examples:
     - Client with good CTR but poor conversion → offer landing page optimization.
     - Client with high organic traffic but no blog → offer SEO content.
     - Client spending over $2000 on Google Ads → offer retargeting.
     - Client with low email open rates → offer email automation.
     - Client inactive for 45 days → offer "express reactivation".

2. **Identify available data sources** (2 days):
   - Google Analytics (bounce rate, time on site, conversions).
   - Meta Ads Manager (CTR, CPC, ROAS).
   - CRM (payment history, tickets).
   - Email marketing platform (opens, clicks).
   - SEO tool (rankings, organic traffic).

3. **Create initial detection rules** (3 days):
   - Translate each opportunity into a simple rule (no complex AI initially).
   - Example rule:
"IF (CTR > 4%) AND (bounce rate > 70%) AND (pages per session < 2)
THEN opportunity = "optimized landing page"
acceptance_probability = 0.7"
- Define numerical thresholds based on agency historical averages.

4. **Prepare test dataset** (4 days):
- Extract anonymized data from 10 past clients (with permission).
- Manually label what real opportunities existed (for later validation).

### Deliverables
- Document with 5–7 business rules.
- List of data sources and access methods (APIs, CSV exports).
- Test dataset with 10 clients and their metrics.
- Simple script (Python or Google Sheets) that applies rules and shows opportunities.

### Agent role at end of sprint
Not yet acting – we only have rules and data.

---

## Sprint 2: Detection engine and internal alerts

**Goal:** The agent can observe data in real time (or daily) and generate alerts for the team.

### Activities
1. **Automate data extraction** (3 days):
- Use n8n, Make, or Python scripts with cron jobs.
- Connect to APIs (Google Analytics, Meta, etc.) or scheduled exports to Google Sheets.
- Store data in a simple database (SQLite or Airtable).

2. **Implement rule engine** (3 days):
- Write code (Python) that each morning:
- Takes data from the last 24–48 hours for each client.
- Applies the rules from Sprint 1.
- Calculates an "opportunity score" (0–100).
- Stores results in an "opportunities detected" table.

3. **Generate internal alerts** (4 days):
- Create a Slack or Telegram channel where the agent posts summaries.
- Alert format: [Client: Pizzeria X]
Opportunity: Optimized landing page (confidence: 82%)
Data: CTR 5.2% | Bounce 78% | Current conversion 1.3%
Suggested action: Offer A/B test of landing page for $300.
- Include link to a simple dashboard (Streamlit or Looker Studio).

4. **Validate with historical data** (4 days):
- Run the engine on past data from 10 clients.
- Compare detected opportunities vs. real ones the agency actually sold.
- Adjust thresholds (e.g., if too many false positives, raise minimum confidence).

### Deliverables
- Automated script or workflow that runs daily.
- Slack/Telegram alert channel.
- Basic dashboard listing opportunities per client.
- Accuracy metrics (e.g., 80% of real opportunities detected).

### Agent role
Now a **automatic analyst** that notifies humans but does not act alone.

---

## Sprint 3: Autonomous proposal generation

**Goal:** The agent can write personalized commercial proposals and leave them ready for human review.

### Activities
1. **Create proposal templates per opportunity type** (2 days):
- For each rule, a template with placeholders:
Subject: Proposal to improve [metric] for [client]
Hi [client_name],
We noticed that your [ads/landing/emails] have [positive fact],
but [negative fact]. For $[price] we can implement [solution]
which we estimate will increase [metric] by [%].
Would you like a 15-min demo?
- Define suggested prices based on agency packages.

2. **Integrate text generation with AI** (4 days):
- Use OpenAI API (GPT-3.5/4) or a small local model (e.g., Llama 3 via Groq).
- The agent takes opportunity data (client, metrics, type) and fills the template.
- Add a personalized paragraph: "For example, your 78% bounce rate means 8 out of 10 visitors leave without seeing your offer..."

3. **Build proposal repository** (3 days):
- Each generated proposal is saved in a folder (Google Drive or Dropbox) named `Client_X_Opportunity_Y_date.md`.
- Notify the account executive: "Proposal ready for review at [link]".

4. **Add human approval logic** (3 days):
- Agent only generates proposals, does not send them.
- A button or command in Slack: `/approve proposal ID123` → agent sends it by email to client.
- Log which proposals were sent and which were rejected (for learning).

### Deliverables
- Automated proposal generator (GPT integration).
- Shared folder with daily generated proposals.
- Approval flow via Slack/email.
- Log of sent vs. accepted proposals.

### Agent role
A **copywriter assistant** that speeds up commercial work, but always with human oversight for sending.

---

## Sprint 4: Limited autonomous action and real pilot

**Goal:** Agent can act alone in low-risk cases and measure results with real clients.

### Activities
1. **Define autonomy thresholds** (2 days):
- Opportunities with confidence > 90% and value < $200 → agent can send proposal directly without approval.
- Opportunities with confidence 70–90% → still require human approval.
- Retention opportunities (cold client) → agent can send an automatic reactivation message.

2. **Implement conditional auto-sending** (3 days):
- Connect to email API (Gmail, SendGrid, or agency CRM).
- Agent sends proposal and BCCs the account executive.
- Logs date and content sent.

3. **Create feedback loop** (3 days):
- If client replies "yes", agent schedules a meeting in the executive's calendar (Google Calendar API).
- If client says "no" or ignores, agent notes it and reduces confidence for that opportunity type with that client.
- If client complains, agent escalates to human immediately.

4. **Pilot with 3 real clients** (4 days):
- Select low-risk clients (good relationship, small packages).
- Activate agent only for them for 2 weeks.
- Measure:
- Number of opportunities detected.
- Proposals sent (automatic vs. approved).
- Acceptance rate.
- Time saved by the team.

5. **Review and adjust** (2 days):
- Team analyzes pilot results.
- Adjusts rules, thresholds, and templates.
- Decides whether to expand to more clients.

### Deliverables
- Fully functional agent (autonomous + supervised modes).
- Pilot report with metrics.
- User manual for the agency team.
- Scaling plan (next sprints: more data sources, predictive models).

### Agent role
A **sales assistant** that can close small opportunities by itself and learns from each interaction.

---

## Sprint 5: From heuristic rules to machine learning

**Goal:** Agent learns from historical data to predict opportunities more accurately, instead of following fixed rules.

### Activities
1. **Collect training dataset** (2 days):
- Use records from previous sprints: clients, metrics, detected opportunities, sent proposals, accepted/rejected.
- Label each row as `real_opportunity = 1` (client bought upsell) or `0` (did not buy or ignored).
- Minimum 100–200 examples (can be augmented with synthetic data).

2. **Select and train base model** (4 days):
- Use a simple, explainable model: **Random Forest** or **XGBoost** (Python libraries).
- Input features: metrics (CTR, bounce rate, spend, inactivity time, etc.), client type (industry, age), opportunity type.
- Target variable: probability of offer acceptance (0 to 1).
- Train and validate with cross-validation.

3. **Replace rules with predictions** (3 days):
- Modify the agent engine: instead of `IF/THEN` rules, call the model for each client daily.
- Model returns, e.g., `acceptance_probability = 0.73` and the most likely opportunity type.
- Keep old rules as fallback while the model lacks enough data.

4. **Interpretability and control** (3 days):
- Generate SHAP or LIME explanations: "This opportunity has 85% probability because CTR is high and the client has bought upsells before."
- Show these explanations in the dashboard and alerts so the team trusts the agent.

### Deliverables
- Trained predictive model (`.pkl` or `.joblib` file).
- Daily inference script replacing rules.
- Dashboard with model accuracy metrics (e.g., AUC-ROC).
- Automatic explanations for each prediction.

### Agent role
Now a **predictive analyst** that not only detects opportunities but estimates real closing probability based on learned patterns.

---

## Sprint 6: Integration with unstructured data (calls, emails, CRM)

**Goal:** Agent listens to sales conversations, emails, and CRM notes to detect subtle signals that numbers miss.

### Activities
1. **Identify unstructured data sources** (2 days):
- Client emails (exchanges with agency).
- Call transcripts (if recorded with consent).
- Internal CRM notes (HubSpot, Pipedrive, etc.).
- Support ticket comments.

2. **Build processing pipeline** (4 days):
- Use free/low-cost tools:
- **Extraction**: Gmail API, CRM API, export recordings (Airtable or Google Drive).
- **Transcription**: OpenAI Whisper (local free) or AssemblyAI API.
- **Sentiment analysis**: Small model (e.g., `textblob` or `transformers`).
- **Intent extraction**: Simple prompt to GPT-3.5/4.
- Schedule daily tasks to process new emails/calls.

3. **Create text‑based signals** (3 days):
- Examples:
- "Client mentioned 'expensive' or 'tight budget' → increase discount probability".
- "Client asked about 'results' or 'case studies' → likely interested in reporting upsell".
- "Client did not reply for 5 days → increase churn risk".
- "Client said 'I'll think about it' 3 times → low closing probability".
- Agent adds these signals as variables to the predictive model.

4. **Validate with a real case** (3 days):
- Take 5 pilot clients and manually review their emails/calls.
- Compare signals detected by agent vs. what a human would detect.
- Adjust prompts and thresholds.

### Deliverables
- Pipeline that processes emails and transcripts daily.
- New database columns: `sentiment_last_week`, `mentions_price`, `asks_for_results`, etc.
- Predictive model retrained including these variables.
- Special alert when an "urgency signal" is detected (e.g., client threatens to leave).

### Agent role
An **active listener** that understands natural language and combines hard metrics with soft conversation signals.

---

## Sprint 7: Autonomous negotiation and closing of low-value sales

**Goal:** Agent not only detects and proposes, but negotiates in real time within authorized limits and can close small sales without human intervention.

### Activities
1. **Define negotiation rules** (2 days):
- Economic limits: e.g., can offer discounts up to 20% or up to $300 without approval.
- Concession types: time-limited discount, free month, extra feature, deferred payment.
- Escalation conditions: if client asks for more than the limit, or negotiation stalls, agent escalates to human.

2. **Implement negotiation dialog via email/chat** (4 days):
- Use a language model (GPT-4 with system prompt) simulating a salesperson.
- Agent automatically replies when client shows interest in an opportunity.
- Example flow:
1. Agent sends initial proposal (base price).
2. Client replies: "too expensive".
3. Agent offers 10% discount (within limit).
4. Client: "20% better".
5. Agent: "I can do 15% plus a free extra report".
6. Client: "ok".
7. Agent generates payment link and schedules delivery.
- Keep a full negotiation log for auditing.

3. **Integrate payment and simple contract systems** (3 days):
- Connect to Stripe, Mercado Pago or similar (API) to generate payment links.
- Use a simple contract template (e.g., DocuSign API or PDF generation).
- If client pays, agent automatically activates service delivery (e.g., creates a task in Asana or notifies operations team).

4. **Pilot autonomous negotiation** (3 days):
- Select 2 pilot clients with low risk and small opportunities (<$200).
- Activate full negotiation mode for 1 week.
- Monitor every interaction and have a human "kill switch" to intervene.
- Measure: closing rate, client satisfaction (post-survey), time saved.

### Deliverables
- Autonomous negotiation module (prompts + concession logic).
- Payment gateway integration.
- Negotiation log (to train future versions).
- Pilot report: how many sales the agent closed alone, total value, team hours saved.
- Governance manual: limits the agent cannot cross.

### Agent role
An **autonomous seller** for small, recurring sales – negotiates, closes, and collects payment without humans. For large or complex clients, it remains an assistant.

---

## Final State After Sprint 7

The **Hidden Opportunities Agent** is capable of:

- **Observing** structured data (metrics) and unstructured data (emails, calls).
- **Predicting** with machine learning which client would buy which service and with what probability.
- **Acting** by generating personalized proposals, negotiating within limits, and closing low-value sales.
- **Learning** continuously: every successful or failed interaction retrains the model.
- **Scaling** to hundreds of clients without increasing the commercial team.

---

## Recommended Tools for All Sprints

| Sprint | Component | Suggested Tool |
|--------|------------|----------------|
| 1–2 | Data automation | n8n, Make, Python + cron |
| 1–2 | Database | SQLite, Airtable (free tier) |
| 2 | Alerts | Slack, Telegram bot |
| 3,6–7 | LLM for text | OpenAI GPT-3.5/4, Groq (Llama 3), or Claude Haiku |
| 4,7 | Email sending | Gmail API, SendGrid |
| 4 | Calendar | Google Calendar API |
| 5 | ML model | Scikit-learn (Random Forest), SHAP |
| 6 | Transcription | Whisper (local) or AssemblyAI |
| 6 | Sentiment | `cardiffnlp/twitter-roberta-base-sentiment` |
| 6 | Storage (advanced) | PostgreSQL (Supabase free tier) |
| 7 | Payments | Stripe (test mode) |
| 7 | Contracts | DocuSign API or PDF generation with `reportlab` |

---

## Demo Considerations

Since this is a demo project without connecting to real data sources, the implementation will focus on simulating production-like functionality:

- **Synthetic Data Generation**: Use Python libraries (e.g., `faker`, `numpy`) to create realistic mock datasets for client metrics, emails, call transcripts, and CRM notes. Generate historical data for 50–100 fake clients to train models and test detection.
- **Mocked APIs and Integrations**: Simulate external services (Google Analytics, Meta Ads, CRM, email providers) using testing libraries like `responses` or `httpx` for HTTP mocking. For LLMs, use cached responses or local models to avoid API costs.
- **Demo Dashboard and UI**: Build a polished Streamlit or Gradio interface that mimics the final product, displaying opportunities, proposals, and negotiation logs with interactive elements (e.g., approve/reject buttons, simulated email threads).
- **Simulated Autonomy**: Implement negotiation as a chatbot demo (e.g., via Streamlit chat UI) with pre-scripted client responses. Use fake payment links and contract generation without real transactions.
- **Sandbox Environment**: Run all components locally or in a container (Docker), logging actions to files/databases without external sends. Include a "demo mode" toggle to showcase full autonomy safely.
- **Production-Like Appearance**: Ensure the demo includes error handling, loading states, and explanations (e.g., SHAP plots) to impress stakeholders, even if data is fake.

This approach allows the demo to demonstrate end-to-end capabilities while maintaining low risk and cost.

---

## Feedback and Suggestions

### Feedback
This is a pragmatic, well-scoped plan with clear milestones, realistic timelines, and a logical progression from heuristics to AI autonomy. It balances technical feasibility with business value, emphasizing validation (e.g., historical data testing, pilots) and human oversight to mitigate risks. Strengths include the focus on measurable outcomes (e.g., accuracy metrics, time saved) and adaptability for a small agency team.

Potential challenges: Over-reliance on external APIs could introduce reliability issues (e.g., rate limits, access changes); early sprints may underdeliver if data quality is poor; and scaling autonomy raises ethical concerns (e.g., client consent, bias in ML models). The plan assumes steady progress but lacks explicit buffers for setbacks like API integrations or model training failures.

### Suggestions
- **Risk Management:** Add a risk register to each sprint, covering data privacy (GDPR/CCPA compliance), API dependencies, and fallback plans (e.g., manual processes if automation fails).
- **Testing & QA:** Incorporate unit/integration testing in every sprint (e.g., validate rules/models against test datasets) and end-to-end QA before pilots to catch errors early.
- **Security & Ethics:** Integrate data encryption, anonymization, and audit logs from Sprint 1. Define clear ethical guidelines for autonomy (e.g., no high-stakes decisions without consent) and include client opt-in processes.
- **Metrics Expansion:** Beyond closing rates, track client satisfaction (via surveys), retention impact, and ROI per sprint to justify the agent's value.
- **Budget & Resources:** Estimate costs for APIs/tools (e.g., OpenAI credits) and include contingency for premium tiers. Plan for team training on tools and post-MVP maintenance (e.g., model retraining).
- **Scalability Prep:** From Sprint 4, prototype handling larger datasets (e.g., switch to cloud storage like Supabase) and consider modular architecture for future expansions (e.g., multi-agency support).
- **Timeline Buffer:** Add 1–2 weeks as contingency for unforeseen delays, especially in ML/NLP sprints where data labeling could take longer.

---

## Demo Architecture Review (Added 2026-04-09)

> **Context:** This project is a demo. It will not connect to a real CRM, live APIs, or real client data. The goal is to demonstrate how the full system would work in production — convincingly enough that stakeholders understand the integration points and value proposition.

### What This Changes

Since this is a demo, the primary deliverable is **believability and clarity of the integration story**, not functional pipelines. Every sprint should be evaluated against: *"Does this make it obvious how it would work in production?"*

### Sprint-by-Sprint Demo Adjustments

**Sprint 1 — Synthetic data is the foundation, not an afterthought.**
- Generate a realistic dataset of 50–100 fake clients using `faker` + `numpy` at the start of Sprint 1, not Sprint 4. All subsequent sprints depend on this data being rich and consistent.
- Include edge cases in the dataset (e.g., a client who ignores three proposals, a client who negotiates hard) so later sprints have interesting scenarios to demonstrate.
- Define a fixed "demo scenario" — a curated set of 3–5 clients with compelling stories — that will be used in all demos and presentations.

**Sprint 2 — Mock API layer must look real.**
- Build a `data_sources/` module with separate files per integration (`google_analytics.py`, `meta_ads.py`, `crm.py`, etc.), each returning synthetic data from the shared dataset.
- The interface of each module should match what a real API client would look like (e.g., `ga.get_client_metrics(client_id, date_range)`). This makes the "how it integrates in production" story self-evident from the code structure.
- The Slack/Telegram alert can be simulated in the dashboard UI — show a panel styled as a Slack message thread.

**Sprint 3 — Proposal UI should simulate the approval workflow end-to-end.**
- Instead of a real Slack `/approve` command, build an approval panel in the Streamlit UI with "Approve / Reject / Edit" buttons.
- Show the proposal in a side-by-side view: raw data → generated proposal text → send preview. This communicates the agent's reasoning chain visually.
- Include a "what would happen in production" tooltip or annotation on each UI element explaining the real integration (e.g., "In production this button triggers a Slack bot command via webhook").

**Sprint 4 — The feedback loop is the most important thing to demonstrate.**
- The demo must show a complete cycle: detect opportunity → generate proposal → simulate client reply → agent updates confidence. Even if the "client reply" is a dropdown ("Client said: Yes / No / Too expensive"), the loop must close visually.
- Add a "Simulation Speed" toggle: slow mode (step through each event with explanations) and fast mode (full cycle in one click). This gives you control during live demos.

**Sprint 5 — Show the model, don't just use it.**
- The ML model trained on synthetic data is less important than the dashboard that explains it. Prioritize SHAP plots, feature importance charts, and a "why this opportunity?" explanation panel.
- Include a "retrain" button in the UI that re-runs training on the current dataset and updates the displayed metrics. This demonstrates the continuous learning story.

**Sprint 6 — NLP pipeline visualization matters more than accuracy.**
- Show a pipeline diagram in the UI: raw email text → sentiment score → extracted signals → updated opportunity score. Even if the NLP is basic, the visual flow communicates the architecture.
- Include 3–5 pre-written example emails per client in the synthetic dataset, covering the key signal types (budget concern, churn risk, interest signal). These should be used consistently across all demos.

**Sprint 7 — The negotiation demo is the showstopper.**
- Build a chat-style UI (Streamlit chat or similar) where the user can play the role of the client, typing responses, and the agent negotiates in real time using an LLM.
- Preload 2–3 scripted negotiation scenarios (aggressive negotiator, easy close, escalation to human) accessible via a scenario selector. This ensures the demo never fails due to unexpected LLM output.
- The "kill switch" / escalation to human should be visually dramatic — a red banner, an alert sound, and a handoff panel. This is a key trust-building moment for stakeholders.

### Cross-Cutting Demo Principles

- **"In Production" annotations:** Every integration point in the UI should have a small info icon or sidebar note explaining what the real-world equivalent would be (e.g., "Here we use synthetic data; in production this calls the HubSpot CRM API v3 `/contacts` endpoint").
- **Sprint 0 (pre-work):** Before Sprint 1, set up the project scaffold: Docker container, shared SQLite database, synthetic data generator, and a `demo_mode = True` flag that routes all I/O to local files instead of external services. This prevents setup debt from accumulating across sprints.
- **Consistent demo dataset:** All sprints must use the same 50–100 fake clients. Avoid regenerating synthetic data per sprint — inconsistency breaks the narrative when you demo end-to-end.
- **Speed-run demo mode:** Build a single "Full Demo" button that seeds a specific scenario and walks through the entire detection → proposal → negotiation → close cycle with a pre-scripted client, completable in under 3 minutes for stakeholder presentations.
- **Email reply parsing (Sprint 7 dependency):** The negotiation loop requires parsing client replies. For the demo, route all replies through an LLM with a structured JSON output prompt (e.g., `{"intent": "counter_offer", "requested_discount": 20}`). This is both demo-safe and production-realistic.
- **Governance doc in Sprint 3, not Sprint 7:** The agent's autonomy limits (what it can decide alone vs. escalate) must be documented before Sprint 4 pilots. Draft a one-page `GOVERNANCE.md` in Sprint 3 that defines thresholds, escalation rules, and audit log requirements. This also doubles as demo documentation.

