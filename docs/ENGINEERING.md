# Engineering

How to run, test and change the system.

---

## 1. Stack

| Layer | Choice |
|---|---|
| Frontend | React 18, TypeScript (strict), Vite 5, inline styles with CSS tokens |
| API | FastAPI, Uvicorn, Pydantic |
| Storage | SQLite (WAL, foreign keys on); JSONL logs |
| ML | scikit-learn 1.4 random forest, SHAP |
| LLM (optional) | Anthropic or OpenAI |
| Quality | pytest + coverage, Vitest + Testing Library, ruff, CodeQL |
| Runtime | Python 3.11, Node 20 |

`requirements.txt` also installs `torch`, `transformers`, `reportlab`, `streamlit` and `plotly`. The
first three are not imported anywhere; the last two serve only the legacy UI.

## 2. Repository layout

```
backend/            FastAPI app and routers
frontend/src/       React app; test/ holds the fake backend and fixtures
src/agents/         detection, proposals, sending, feedback, negotiation, follow-ups
src/ml/, src/nlp/   model and text signals
src/data_sources/   inbound adapters
src/integrations/   HubSpot, WhatsApp
src/db/             schema, migrations, indexes
scripts/            command-line entry points
tests/              pytest suite
docs/               this documentation
planning/           original plan, roadmap, governance, UI decisions
```

## 3. Running it

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt      # Windows
python scripts/seed_db.py                          # synthetic data (add --reset to start over)
python scripts/daily_job.py                        # detect, alert, draft, process text
python scripts/train_model.py                      # optional: enables ML blending

uvicorn backend.main:app --reload --port 8000
cd frontend && npm install && npm run dev          # http://localhost:5173
```

| Variable | Default | Purpose |
|---|---|---|
| `DEMO_MODE` | `true` | Log instead of calling outbound services |
| `DB_PATH` | `data/db/opportunities.db` | Database file |
| `LLM_PROVIDER` / `LLM_MODEL` | `openai` / `gpt-3.5-turbo` | LLM selection |
| `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` | empty | Enable the LLM |
| `DASHBOARD_URL` | `http://localhost:5173` | Link in outbound alerts |
| `SYNTHETIC_CLIENT_COUNT`, `SYNTHETIC_SEED` | `75`, `42` | Demo data size and reproducibility |

Provider credentials for production are listed in `.env.example`.

## 4. Testing

```bash
python scripts/seed_db.py            # some tests read the demo database
python -m pytest --cov               # fails below 90%
ruff check .
cd frontend && npm run coverage && npm run build
```

| Suite | Tests | What it covers |
|---|---|---|
| `test_sprint0` – `test_sprint7` | 313 | Features as first built |
| `test_audit_fixes` | 37 | One regression test or more per audited defect |
| `test_api` | 23 | All 14 routers over HTTP |
| `test_integrations` | 27 | Production-mode paths with fake providers; CLI scripts |
| Frontend (Vitest) | 25 | API client, navigation to every page, interactive behaviour |

Measured when this was written: backend 93–94% of lines; frontend 91% of lines, 72% of branches and
functions. The backend gate is in `pyproject.toml`, the frontend gates in `vite.config.ts`.

## 5. Continuous integration

| Workflow | Trigger | Does |
|---|---|---|
| `ci.yml` | Pull requests, pushes to `master` | ruff; backend tests and coverage; frontend tests, coverage and build |
| `codeql.yml` | Pull requests and pushes to `master`, weekly | Security analysis |
| `claude-code-review.yml` | Pull requests from this repository | Automated review |
| `claude.yml` | `@claude` mention by a collaborator | Answers or implements |
| `dependabot.yml` | Weekly | Dependency pull requests |

The two Claude workflows need the `ANTHROPIC_API_KEY` repository secret.

## 6. Conventions that are easy to break

- **Call `invalidate_cache()`** after any write that changes scores, or the UI shows stale results for
  five minutes.
- **Log paths are module constants** resolved at import. Tests must monkeypatch the constant, not only
  `config.LOGS_DIR`, or they write into the real `logs/`.
- **SQL `NULL` metrics are dropped** before rules run. Do not reintroduce `None` into metric dictionaries.
- **Terminal negotiation intents** must be written as a row, or the thread stays "active".
- **Every automated message path** must check that the proposal is still open before sending.
- **Log through `src/jsonl.py`.**
- `config.py` makes stdout tolerant of characters Windows code pages cannot encode. Keep it.

## 7. Engineering decisions

### ED-01: SQLite as the single store
One file, no server, reproducible demos. Cost: one writer at a time and no network access control.

### ED-02: Rules first, model second
Rules explain every opportunity and work with no history. The model only adjusts ordering.

### ED-03: `DEMO_MODE` defaults to true
Forgetting to configure the system must not send anything.

### ED-04: Batch the portfolio
Scoring loads all metrics in one query; inference makes one `predict_proba` and one SHAP call. Explaining
rows one at a time took 53 s for `/api/ml/predictions`; batched, 2.7 s.

### ED-05: Errors from agents are `ValueError`
`backend/main.py` maps them to 400 or 404 with the message, which the UI displays.

### ED-06: Feedback is the only source of truth for learning
The confidence modifier, propensity tiers and real training rows are all derived from `feedback_log`.

### ED-07: A proposal stays open while it is being discussed
`too_expensive`, `ignored` and `need_more_info` keep the opportunity open, so the next detection run does
not create a duplicate.

### ED-08: Pages are loaded on first visit
Only the landing page ships in the main bundle.
