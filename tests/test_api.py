"""
HTTP-level tests for the FastAPI backend (every router in backend/routers).

They run the real app through Starlette's TestClient against a throw-away
SQLite database, so they cover routing, request validation, status codes and
the JSON shape the React frontend relies on.

Fixture data: three clients —
  * "Idle Co"  — inactive for 60 days (triggers the reactivation rule), with a
                 sent proposal, an approved proposal and a text signal;
  * two more clients, each with one sent proposal, used by the negotiation and
    follow-up flows.
"""

import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient

import config


def _conn(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


@pytest.fixture()
def api(tmp_path, monkeypatch):
    """TestClient on an isolated DB + log directory. Yields (client, ids)."""
    db_file, logs = tmp_path / "api.db", tmp_path / "logs"
    logs.mkdir()
    monkeypatch.setattr(config, "DB_PATH", db_file)
    monkeypatch.setattr(config, "LOGS_DIR", logs)
    monkeypatch.setattr(config, "DEMO_MODE", True)
    for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "STRIPE_SECRET_KEY"):
        monkeypatch.setattr(config, key, "")

    # Log paths are module constants resolved at import time — redirect them
    from src.agents import (
        churn_escalation, email_sender, feedback_loop, follow_up_engine, negotiator, payment_link,
    )
    from src.integrations import hubspot, whatsapp
    for module, attr, name in [
        (negotiator, "NEGOTIATION_LOG", "negotiations.jsonl"),
        (payment_link, "PAYMENT_LINKS_LOG", "payment_links.jsonl"),
        (follow_up_engine, "FOLLOW_UP_LOG", "follow_ups.jsonl"),
        (feedback_loop, "FEEDBACK_LOG", "feedback.jsonl"),
        (feedback_loop, "CALENDAR_LOG", "calendar.jsonl"),
        (feedback_loop, "ESCALATION_LOG", "escalations.jsonl"),
        (email_sender, "SENT_LOG", "sent.jsonl"),
        (hubspot, "CRM_SYNC_LOG", "crm.jsonl"),
        (whatsapp, "WA_LOG", "wa.jsonl"),
        (churn_escalation, "CHURN_ESC_LOG", "churn.jsonl"),
    ]:
        monkeypatch.setattr(module, attr, logs / name)

    from backend.main import app
    from src.agents import scorer
    from src.db.schema import init_db, migrate_db

    init_db()
    migrate_db()
    scorer.invalidate_cache()
    ids = _populate(db_file)

    with TestClient(app) as client:
        yield client, ids
    scorer.invalidate_cache()


def _populate(db_file: Path) -> dict:
    conn = _conn(db_file)
    now = datetime.now().isoformat()
    ids: dict = {"clients": [], "props": []}

    for i, name in enumerate(["Idle Co", "Beta Ltd", "Gamma Inc"]):
        cid = f"client-{i}"
        conn.execute(
            "INSERT INTO clients (id, name, industry, contact_email, account_manager, is_demo_scenario) "
            "VALUES (?,?,?,?,?,?)",
            (cid, name, "retail", f"{cid}@demo.local", "Dana Reyes", 1 if i == 0 else 0),
        )
        conn.execute(
            "INSERT INTO client_metrics (client_id, date, days_inactive, days_since_last_contact, "
            "ctr, roas, ad_spend, bounce_rate, conversion_rate, email_open_rate) "
            "VALUES (?, '2026-01-10', ?, ?, 0.02, 3.0, 40, 0.4, 0.03, 0.30)",
            (cid, 60 if i == 0 else 1, 60 if i == 0 else 1),
        )
        oid, pid = str(uuid.uuid4()), str(uuid.uuid4())
        conn.execute(
            "INSERT INTO opportunities (id, client_id, opportunity_type, score, status) "
            "VALUES (?,?,?,?,?)", (oid, cid, "reactivation", 80.0, "proposal_generated"),
        )
        status = "approved" if i == 2 else "sent"
        conn.execute(
            "INSERT INTO proposals (id, opportunity_id, client_id, subject, body, suggested_price, "
            "status, created_at, sent_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (pid, oid, cid, "Subject", "Body", 400.0, status, now, now),
        )
        ids["clients"].append(cid)
        ids["props"].append(pid)

    conn.execute(
        "INSERT INTO text_signals (client_id, source, raw_text, sentiment, churn_risk, urgency_signal) "
        "VALUES ('client-0', 'email', 'we may cancel', -0.7, 1, 0)"
    )
    conn.commit()
    conn.close()
    return ids


# ── Health & errors ───────────────────────────────────────────────────────────

def test_health(api):
    client, _ = api
    assert client.get("/api/health").json() == {"status": "ok"}


def test_unknown_proposal_is_404_with_message_not_500(api):
    client, _ = api
    r = client.post("/api/pilot/reply", json={"proposal_id": "nope", "intent": "accepted"})
    assert r.status_code == 404
    assert "not found" in r.json()["detail"].lower()


def test_invalid_intent_is_400(api):
    client, ids = api
    r = client.post("/api/pilot/reply", json={"proposal_id": ids["props"][0], "intent": "bogus"})
    assert r.status_code == 400


# ── Opportunities & clients ───────────────────────────────────────────────────

def test_opportunities_list_filters_and_meta(api):
    client, _ = api
    rows = client.get("/api/opportunities").json()
    assert {r["client_name"] for r in rows} == {"Idle Co"}
    assert rows[0]["opportunity_type"] == "reactivation"
    assert rows[0]["propensity_tier"] == "medium"

    assert client.get("/api/opportunities?opp_type=seo_content").json() == []
    assert len(client.get("/api/opportunities?demo_only=true").json()) == 1
    meta = client.get("/api/opportunities/meta").json()
    assert meta == {"types": ["reactivation"], "industries": ["retail"]}


def test_client_detail_and_404(api):
    client, ids = api
    r = client.get(f"/api/clients/{ids['clients'][0]}/detail")
    assert r.status_code == 200
    body = r.json()
    assert body["client"]["name"] == "Idle Co"
    assert body["metrics"]["days_inactive"] == 60
    assert body["signals_summary"]["churn_risk"] == 1
    assert all("_metrics" not in o for o in body["opportunities"])

    assert client.get("/api/clients/missing/detail").status_code == 404
    assert len(client.get("/api/clients").json()) == 3
    assert [c["name"] for c in client.get("/api/clients/demo").json()] == ["Idle Co"]


# ── Proposals ─────────────────────────────────────────────────────────────────

def test_proposals_list_and_metrics(api):
    client, ids = api
    assert len(client.get("/api/proposals").json()) == 3
    assert len(client.get("/api/proposals?status=approved").json()) == 1

    bulk = client.get("/api/proposals/metrics").json()
    assert set(bulk) == set(ids["props"])
    single = client.get(f"/api/proposals/{ids['props'][0]}/metrics").json()
    assert single == bulk[ids["props"][0]]
    assert single["ad_spend"] == 40 * 30          # stored per day, reported per month
    assert client.get("/api/proposals/missing/metrics").status_code == 404


def test_revoke_only_works_on_approved(api):
    client, ids = api
    assert client.post(f"/api/proposals/{ids['props'][0]}/revoke").status_code == 409  # sent
    assert client.post(f"/api/proposals/{ids['props'][2]}/revoke").status_code == 200  # approved
    assert client.get("/api/proposals?status=draft").json()[0]["id"] == ids["props"][2]


def test_approve_reject_and_edit(api):
    client, ids = api
    draft = ids["props"][2]
    client.post(f"/api/proposals/{draft}/revoke")
    assert client.patch(f"/api/proposals/{draft}/body", json={"body": "New text"}).status_code == 200
    assert client.get("/api/proposals?status=draft").json()[0]["body"] == "New text"
    assert client.post(f"/api/proposals/{draft}/approve").json() == {"approved": True}
    assert client.post(f"/api/proposals/{draft}/reject", json={"reason": "no"}).json() == {"rejected": True}


# ── Pilot / feedback loop ─────────────────────────────────────────────────────

def test_pilot_reply_accepted_updates_metrics(api):
    client, ids = api
    r = client.post("/api/pilot/reply", json={"proposal_id": ids["props"][0], "intent": "accepted"})
    assert r.status_code == 200
    assert r.json()["new_proposal_status"] == "accepted"

    metrics = client.get("/api/pilot/metrics").json()
    assert metrics["proposals_accepted"] == 1 and metrics["total_revenue"] == 400.0
    assert client.get("/api/pilot/feedback-log").json()["feedback"][0]["intent"] == "accepted"


def test_pilot_detect_generate_send(api):
    client, ids = api
    r = client.post("/api/pilot/detect", json={"client_id": ids["clients"][0]})
    assert r.status_code == 200
    assert r.json()["opportunities"][0]["opportunity_type"] == "reactivation"

    r = client.post("/api/pilot/generate", json={"client_id": ids["clients"][0]})
    assert r.status_code == 200 and r.json()["already_existed"] is True

    r = client.post("/api/pilot/send", json={
        "proposal_id": ids["props"][2], "opp_score": 80, "opp_price": 400, "opp_type": "reactivation"})
    assert r.status_code == 200 and r.json()["sent"] is True
    assert client.get("/api/pilot/sent-log").json()[0]["proposal_id"] == ids["props"][2]
    assert "approved_pending_send" in client.get("/api/pilot/auto-queue").json()


def test_pilot_generate_without_opportunity_is_400(api):
    client, _ = api
    assert client.post("/api/pilot/generate", json={"client_id": "none"}).status_code == 400


# ── Negotiations ──────────────────────────────────────────────────────────────

def test_negotiation_accept_flow(api):
    client, ids = api
    pid = ids["props"][1]
    assert client.post("/api/negotiations/too-expensive", json={"proposal_id": pid}).status_code == 200
    assert [n["proposal_id"] for n in client.get("/api/negotiations/active").json()] == [pid]
    assert client.get(f"/api/negotiations/{pid}/thread").json()[0]["role"] == "agent"

    r = client.post(f"/api/negotiations/{pid}/reply", json={"message": "ok, deal", "simulated": True})
    assert r.json()["status"] == "accepted" and r.json()["offer_price"] == 360.0
    assert client.get("/api/negotiations/active").json() == []
    assert client.get("/api/negotiations/summary").json()["accepted"] == 1
    assert client.get("/api/negotiations/history").json()
    assert client.get("/api/payment-links").json()[0]["proposal_id"] == pid


def test_negotiation_kill_switch(api):
    client, ids = api
    pid = ids["props"][1]
    client.post(f"/api/negotiations/{pid}/start")
    assert client.post(f"/api/negotiations/{pid}/kill", json={}).json() == {"killed": True}
    assert client.get("/api/negotiations/active").json() == []


# ── Follow-ups ────────────────────────────────────────────────────────────────

def test_follow_up_schedule_cancel_and_process(api):
    client, ids = api
    pid = ids["props"][0]
    assert client.post("/api/follow-ups/schedule", json={"proposal_id": pid}).json()["scheduled"] == 2
    queue = client.get(f"/api/follow-ups?proposal_id={pid}").json()
    assert [q["status"] for q in queue] == ["pending", "pending"]

    assert client.delete(f"/api/follow-ups/{queue[0]['id']}/cancel").json() == {"cancelled": True}
    assert client.delete(f"/api/follow-ups/{queue[0]['id']}/cancel").status_code == 404  # already cancelled
    assert client.delete("/api/follow-ups/missing/cancel").status_code == 404
    assert client.post("/api/follow-ups/process").json() == {"processed": 0}   # nothing due yet
    assert client.get("/api/follow-ups/log").json() == []


# ── Alerts ────────────────────────────────────────────────────────────────────

def test_alerts_run_list_clear(api):
    client, _ = api
    assert client.get("/api/alerts").json() == []
    assert client.post("/api/alerts/run", json={"scope": "All clients", "min_score": 60}).json() == {"dispatched": 1}
    alerts = client.get("/api/alerts").json()
    assert alerts[0]["client_name"] == "Idle Co"
    assert "Inactive 60 days" in alerts[0]["slack_payload"]["text"]
    assert client.delete("/api/alerts").json() == {"cleared": True}
    assert client.get("/api/alerts").json() == []


# ── Analytics, churn, CRM, seasonal, WhatsApp ─────────────────────────────────

def test_analytics_summary_and_validation(api):
    client, _ = api
    summary = client.get("/api/analytics/summary?period_days=0").json()
    assert summary["proposals_generated"] == 3 and len(summary["weekly_trend"]) == 8
    assert client.get("/api/analytics/summary?period_days=-5").status_code == 422
    assert client.get("/api/analytics/snapshots?limit=0").status_code == 422

    assert client.post("/api/analytics/snapshot").status_code == 200
    assert len(client.get("/api/analytics/snapshots").json()) == 1


def test_churn_scan_deduplicates(api):
    client, _ = api
    first = client.post("/api/churn/scan").json()
    assert first["escalated"] == 1 and first["records"][0]["client_name"] == "Idle Co"
    assert client.post("/api/churn/scan").json()["escalated"] == 0   # inside the 7-day window
    assert len(client.get("/api/churn/escalations").json()) == 1
    assert len(client.get("/api/churn/log").json()) == 1


def test_crm_manual_sync(api):
    client, ids = api
    r = client.post("/api/crm/sync", json={
        "proposal_id": ids["props"][0], "client_id": ids["clients"][0],
        "revenue": 400, "opportunity_type": "reactivation"})
    assert r.json()["ok"] is True
    rows = client.get("/api/crm/sync-log").json()
    assert {row["action"] for row in rows} == {"create_deal", "log_activity"}
    assert len(client.get("/api/crm/log").json()) == 2


def test_seasonal_and_propensity(api):
    client, _ = api
    assert isinstance(client.get("/api/seasonal/upcoming?weeks=52").json(), list)
    assert isinstance(client.get("/api/seasonal/boosts").json(), list)
    counts = client.post("/api/propensity/update").json()["counts"]
    assert counts == {"high": 0, "medium": 3, "low": 0}
    assert len(client.get("/api/propensity/clients").json()) == 3


def test_whatsapp_channel_update_and_validation(api):
    client, ids = api
    cid = ids["clients"][0]
    r = client.patch("/api/clients/channel", json={
        "client_id": cid, "channel": "whatsapp", "whatsapp_number": "+15550001111"})
    assert r.status_code == 200
    assert [c["id"] for c in client.get("/api/whatsapp/opted-in").json()] == [cid]
    assert client.patch("/api/clients/channel", json={"client_id": cid, "channel": "fax"}).status_code == 422
    assert client.patch("/api/clients/channel", json={"client_id": "x", "channel": "email"}).status_code == 404
    assert client.get("/api/whatsapp/log").json() == []


# ── Text signals, accuracy, ML ────────────────────────────────────────────────

def test_text_signals_endpoints(api):
    client, _ = api
    summary = client.get("/api/text-signals/summary").json()
    assert summary["total_signals"] == 1 and summary["counts_by_type"]["churn_flags"] == 1
    assert client.get("/api/text-signals/client/client-0").json()["summary"]["n_signals"] == 1
    assert client.get("/api/text-signals/urgency").json()[0]["client_name"] == "Idle Co"
    assert client.get("/api/text-signals/all-summaries").json()[0]["client_id"] == "client-0"
    assert client.post("/api/text-signals/process", json={"reprocess_all": True}).json()["total_processed"] == 1


def test_accuracy_endpoint(api):
    client, _ = api
    body = client.get("/api/accuracy").json()
    assert set(body["metrics"]) == {"precision", "recall", "f1", "tp", "fp", "fn"}
    assert body["rows"] and body["rows"][0]["status"] in {"Perfect", "Extra", "Missed"}


def test_ml_endpoints_without_model(api, monkeypatch):
    from src.ml import model
    monkeypatch.setattr(model, "MODEL_PATH", Path("/nonexistent/rf_model.joblib"))
    client, _ = api
    assert client.get("/api/ml/status").json() == {"is_trained": False, "metadata": None}
    assert client.get("/api/ml/summary").json()["model_trained"] is False
    assert isinstance(client.get("/api/ml/history").json(), list)
    assert client.get("/api/ml/predictions").status_code == 200
