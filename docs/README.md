# Documentation

| Document | For | What it covers |
|---|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Engineers, architects | Components, the loop, scoring order, data model, autonomy tiers, security, deployment |
| [ENGINEERING.md](ENGINEERING.md) | Contributors | Stack, layout, running, testing, CI, conventions, decision log (ED-01 – ED-08) |
| [APPLIED_AI.md](APPLIED_AI.md) | AI/ML engineers, reviewers | Rules, acceptance model and its measured quality, text signals, LLM safeguards |
| [BUSINESS_VALUE.md](BUSINESS_VALUE.md) | Agency leadership, sponsors | Problem, before/after, value drivers, how to read the figures, readiness |
| [KNOWLEDGE_LEARNED.md](KNOWLEDGE_LEARNED.md) | Everyone maintaining the system | Lessons and **open findings** |

Also: [planning/GOVERNANCE.md](../planning/GOVERNANCE.md) (autonomy policy),
[planning/ROADMAP.md](../planning/ROADMAP.md).

> **Status:** a working demonstration on synthetic data. Not ready for real clients; see
> [BUSINESS_VALUE.md §7](BUSINESS_VALUE.md#7-readiness).

## Screenshots

Taken on 2026-11-25 from a freshly seeded demo database (80 synthetic clients) with `DEMO_MODE=true` and
no LLM keys, after one daily job, one model training and simulated client replies. Every figure shown is
illustrative.

| | |
|---|---|
| **Opportunities** — ranked, with signals and rationale ![](img/opportunities.png) | **Seasonal calendar** — upcoming boosts ![](img/seasonal-calendar.png) |
| **Client detail** — latest metrics ![](img/client-detail.png) | **Text signals** — distribution across messages ![](img/text-signals.png) |
| **ML model card** — measured quality ![](img/ml-model.png) | **Explanation** — SHAP contributions ![](img/ml-explain.png) |
| **Proposals** — approve, edit or reject ![](img/proposals.png) | **Follow-ups** — scheduled queue ![](img/follow-ups.png) |
| **Negotiation** — thread and kill switch ![](img/negotiation.png) | **Pilot simulation** — the full cycle step by step ![](img/pilot.png) |
| **Pilot report** — aggregated metrics ![](img/pilot-report.png) | **ROI dashboard** ![](img/roi-dashboard.png) |
| **Alert feed** — Slack-style alerts ![](img/alert-feed.png) | **Detection accuracy** — rule regression check ![](img/accuracy.png) |
| **System overview** — in-app explanation ![](img/overview.png) | **Churn escalations** — signal, date and owner ![](img/churn.png) |
