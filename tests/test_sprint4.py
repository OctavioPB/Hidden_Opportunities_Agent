"""
Sprint 4 tests — Autonomous Send & Feedback Loop.

Coverage:
 1. Email sender — demo mode writes to log, payload structure correct.
 2. Email sender — updates proposal status to 'sent' in DB.
 3. Email sender — raises on unknown proposal ID.
 4. Feedback loop — record_client_reply writes feedback_log entry.
 5. Feedback loop — correct proposal/opportunity status updates per intent.
 6. Feedback loop — confidence_delta matches governance table.
 7. Feedback loop — INTENT_ACCEPTED triggers calendar log entry.
 8. Feedback loop — INTENT_ESCALATED triggers escalation log entry.
 9. Feedback loop — get_pilot_metrics returns expected keys.
10. Auto-sender  — get_autonomy_tier returns correct tier per conditions.
11. Auto-sender  — should_auto_send is True only for Tier C.
12. Auto-sender  — process_auto_send_queue dry-run returns candidates.
13. Auto-sender  — promote_to_autonomous sets approved_by='autonomous'.
14. Daily job    — summary includes auto_sent key.
15. Feedback log — load_feedback_log and load_calendar_log return lists.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import config


# ── Shared DB fixture ─────────────────────────────────────────────────────────

def _make_conn(p):
    conn = sqlite3.connect(str(p), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@pytest.fixture()
def seeded_db(tmp_path, monkeypatch):
    """
    Create a temp DB with one client, one opportunity, one draft proposal,
    and patch all DB-accessing modules to use it.
    """
    db_path = tmp_path / "sprint4.db"
    monkeypatch.setattr(config, "DB_PATH", db_path)

    import src.db.schema as schema
    import src.agents.email_sender as es
    import src.agents.feedback_loop as fl
    import src.agents.auto_sender as aut

    def _conn():
        return _make_conn(db_path)

    monkeypatch.setattr(schema, "get_connection", _conn)
    monkeypatch.setattr(es,     "get_connection", _conn)
    monkeypatch.setattr(fl,     "get_connection", _conn)
    monkeypatch.setattr(aut,    "get_connection", _conn)

    schema.init_db()

    now     = datetime.now().isoformat()
    cid     = "s4-client-001"
    oid     = str(uuid.uuid4())
    pid     = str(uuid.uuid4())

    conn = _conn()
    conn.execute(
        "INSERT INTO clients (id,name,industry,contact_email,account_manager,is_demo_scenario) "
        "VALUES (?,?,?,?,?,?)",
        (cid, "TestCo", "Tech", "owner@testco.demo", "Ana García", 1),
    )
    conn.execute(
        "INSERT INTO opportunities (id,client_id,opportunity_type,score,status,detected_at,updated_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (oid, cid, "email_automation", 85.0, "proposal_generated", now, now),
    )
    conn.execute(
        "INSERT INTO proposals "
        "(id,opportunity_id,client_id,subject,body,suggested_price,status,created_at,updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (pid, oid, cid, "Test Subject", "Test email body.", 300.0, "approved", now, now),
    )
    conn.commit()
    conn.close()

    return {"db_path": db_path, "client_id": cid, "opp_id": oid, "proposal_id": pid,
            "conn": _conn}


# ── 1–3. Email sender ─────────────────────────────────────────────────────────

class TestEmailSender:
    def test_demo_send_writes_to_log(self, seeded_db, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "DEMO_MODE", True)
        import src.agents.email_sender as es
        monkeypatch.setattr(es, "SENT_LOG", tmp_path / "sent.jsonl")
        monkeypatch.setattr(es.config, "DEMO_MODE", True)

        result = es.send_proposal_email(seeded_db["proposal_id"])
        log_path = tmp_path / "sent.jsonl"
        assert log_path.exists()
        entry = json.loads(log_path.read_text().strip())
        assert entry["proposal_id"] == seeded_db["proposal_id"]
        assert entry["status"] == "sent"

    def test_send_payload_structure(self, seeded_db, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "DEMO_MODE", True)
        import src.agents.email_sender as es
        monkeypatch.setattr(es, "SENT_LOG", tmp_path / "sent2.jsonl")
        monkeypatch.setattr(es.config, "DEMO_MODE", True)

        result = es.send_proposal_email(seeded_db["proposal_id"])
        for key in ("send_id", "proposal_id", "client_id", "client_name",
                    "to", "subject", "body", "send_mode", "timestamp", "status"):
            assert key in result, f"Missing key: {key}"

    def test_send_updates_proposal_status_to_sent(self, seeded_db, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "DEMO_MODE", True)
        import src.agents.email_sender as es
        monkeypatch.setattr(es, "SENT_LOG", tmp_path / "sent3.jsonl")
        monkeypatch.setattr(es.config, "DEMO_MODE", True)

        es.send_proposal_email(seeded_db["proposal_id"])
        conn = seeded_db["conn"]()
        row = conn.execute(
            "SELECT status FROM proposals WHERE id=?", (seeded_db["proposal_id"],)
        ).fetchone()
        conn.close()
        assert row["status"] == "sent"

    def test_send_raises_on_unknown_proposal(self, seeded_db, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "DEMO_MODE", True)
        import src.agents.email_sender as es
        monkeypatch.setattr(es, "SENT_LOG", tmp_path / "sent4.jsonl")
        monkeypatch.setattr(es.config, "DEMO_MODE", True)

        with pytest.raises(ValueError, match="not found"):
            es.send_proposal_email("nonexistent-proposal-id")

    def test_send_includes_production_note(self, seeded_db, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "DEMO_MODE", True)
        import src.agents.email_sender as es
        monkeypatch.setattr(es, "SENT_LOG", tmp_path / "sent5.jsonl")
        monkeypatch.setattr(es.config, "DEMO_MODE", True)

        result = es.send_proposal_email(seeded_db["proposal_id"])
        assert "_production_integration" in result
        assert "sendgrid" in result["_production_integration"].lower()

    def test_load_sent_log_returns_list(self, seeded_db, tmp_path, monkeypatch):
        import src.agents.email_sender as es
        monkeypatch.setattr(es, "SENT_LOG", tmp_path / "empty_sent.jsonl")
        result = es.load_sent_log()
        assert isinstance(result, list)


# ── Helper: create a sent proposal for feedback tests ─────────────────────────

def _seed_sent_proposal(seeded_db, tmp_path, monkeypatch) -> str:
    """Send the seeded proposal and return its ID."""
    monkeypatch.setattr(config, "DEMO_MODE", True)
    import src.agents.email_sender as es
    monkeypatch.setattr(es, "SENT_LOG", tmp_path / "fb_sent.jsonl")
    monkeypatch.setattr(es.config, "DEMO_MODE", True)
    es.send_proposal_email(seeded_db["proposal_id"])
    return seeded_db["proposal_id"]


# ── 4–8. Feedback loop ────────────────────────────────────────────────────────

class TestFeedbackLoop:
    @pytest.fixture(autouse=True)
    def _patch_logs(self, tmp_path, monkeypatch):
        import src.agents.feedback_loop as fl
        monkeypatch.setattr(fl, "FEEDBACK_LOG",   tmp_path / "feedback.jsonl")
        monkeypatch.setattr(fl, "CALENDAR_LOG",   tmp_path / "calendar.jsonl")
        monkeypatch.setattr(fl, "ESCALATION_LOG", tmp_path / "escalations.jsonl")
        monkeypatch.setattr(config, "DEMO_MODE", True)
        import src.agents.feedback_loop as fl2
        monkeypatch.setattr(fl2.config, "DEMO_MODE", True)
        self._tmp = tmp_path

    def _make_sent(self, seeded_db, tmp_path, monkeypatch):
        return _seed_sent_proposal(seeded_db, tmp_path, monkeypatch)

    def test_record_reply_writes_feedback_jsonl(self, seeded_db, tmp_path, monkeypatch):
        pid = self._make_sent(seeded_db, tmp_path, monkeypatch)
        from src.agents.feedback_loop import record_client_reply, INTENT_REJECTED
        record_client_reply(pid, INTENT_REJECTED, simulated=True)
        log = tmp_path / "feedback.jsonl"
        assert log.exists()
        entry = json.loads(log.read_text().strip())
        assert entry["intent"] == INTENT_REJECTED
        assert entry["proposal_id"] == pid

    def test_accepted_sets_proposal_status(self, seeded_db, tmp_path, monkeypatch):
        pid = self._make_sent(seeded_db, tmp_path, monkeypatch)
        from src.agents.feedback_loop import record_client_reply, INTENT_ACCEPTED
        record_client_reply(pid, INTENT_ACCEPTED, simulated=True)
        conn = seeded_db["conn"]()
        row = conn.execute("SELECT status FROM proposals WHERE id=?", (pid,)).fetchone()
        conn.close()
        assert row["status"] == "accepted"

    def test_rejected_sets_proposal_status(self, seeded_db, tmp_path, monkeypatch):
        pid = self._make_sent(seeded_db, tmp_path, monkeypatch)
        from src.agents.feedback_loop import record_client_reply, INTENT_REJECTED
        record_client_reply(pid, INTENT_REJECTED, simulated=True)
        conn = seeded_db["conn"]()
        row = conn.execute("SELECT status FROM proposals WHERE id=?", (pid,)).fetchone()
        conn.close()
        assert row["status"] == "rejected"

    def test_accepted_sets_opportunity_closed(self, seeded_db, tmp_path, monkeypatch):
        pid = self._make_sent(seeded_db, tmp_path, monkeypatch)
        from src.agents.feedback_loop import record_client_reply, INTENT_ACCEPTED
        record_client_reply(pid, INTENT_ACCEPTED, simulated=True)
        conn = seeded_db["conn"]()
        row = conn.execute(
            "SELECT status FROM opportunities WHERE id=?", (seeded_db["opp_id"],)
        ).fetchone()
        conn.close()
        assert row["status"] == "closed"

    def test_escalated_sets_opportunity_escalated(self, seeded_db, tmp_path, monkeypatch):
        pid = self._make_sent(seeded_db, tmp_path, monkeypatch)
        from src.agents.feedback_loop import record_client_reply, INTENT_ESCALATED
        record_client_reply(pid, INTENT_ESCALATED, simulated=True)
        conn = seeded_db["conn"]()
        row = conn.execute(
            "SELECT status FROM opportunities WHERE id=?", (seeded_db["opp_id"],)
        ).fetchone()
        conn.close()
        assert row["status"] == "escalated"

    @pytest.mark.parametrize("intent,expected_delta", [
        ("accepted",      +15.0),
        ("rejected",      -20.0),
        ("too_expensive",  -8.0),
        ("need_more_info", +3.0),
        ("ignored",       -10.0),
        ("escalated",     -30.0),
    ])
    def test_confidence_delta_matches_governance(self, seeded_db, tmp_path, monkeypatch, intent, expected_delta):
        # Need fresh proposals for each parametrized call since each seeded_db is shared
        # We can just read from the module constant
        from src.agents.feedback_loop import _CONFIDENCE_DELTA
        assert _CONFIDENCE_DELTA[intent] == expected_delta

    def test_accepted_writes_calendar_event(self, seeded_db, tmp_path, monkeypatch):
        pid = self._make_sent(seeded_db, tmp_path, monkeypatch)
        from src.agents.feedback_loop import record_client_reply, INTENT_ACCEPTED
        record_client_reply(pid, INTENT_ACCEPTED, simulated=True)
        cal_log = tmp_path / "calendar.jsonl"
        assert cal_log.exists()
        entry = json.loads(cal_log.read_text().strip())
        assert "event_id" in entry
        assert "TestCo" in entry["summary"]

    def test_escalated_writes_escalation_log(self, seeded_db, tmp_path, monkeypatch):
        pid = self._make_sent(seeded_db, tmp_path, monkeypatch)
        from src.agents.feedback_loop import record_client_reply, INTENT_ESCALATED
        record_client_reply(pid, INTENT_ESCALATED, notes="Client is upset.", simulated=True)
        esc_log = tmp_path / "escalations.jsonl"
        assert esc_log.exists()
        entry = json.loads(esc_log.read_text().strip())
        assert entry["client_name"] == "TestCo"
        assert "upset" in entry["notes"]

    def test_invalid_intent_raises(self, seeded_db, tmp_path, monkeypatch):
        pid = self._make_sent(seeded_db, tmp_path, monkeypatch)
        from src.agents.feedback_loop import record_client_reply
        with pytest.raises(ValueError, match="Unknown intent"):
            record_client_reply(pid, "not_a_real_intent", simulated=True)

    def test_accepted_credits_revenue(self, seeded_db, tmp_path, monkeypatch):
        pid = self._make_sent(seeded_db, tmp_path, monkeypatch)
        from src.agents.feedback_loop import record_client_reply, INTENT_ACCEPTED
        result = record_client_reply(pid, INTENT_ACCEPTED, simulated=True)
        assert result["revenue"] == 300.0   # matches suggested_price

    def test_rejected_credits_zero_revenue(self, seeded_db, tmp_path, monkeypatch):
        pid = self._make_sent(seeded_db, tmp_path, monkeypatch)
        from src.agents.feedback_loop import record_client_reply, INTENT_REJECTED
        result = record_client_reply(pid, INTENT_REJECTED, simulated=True)
        assert result["revenue"] == 0.0

    def test_feedback_log_returns_list(self, tmp_path, monkeypatch):
        import src.agents.feedback_loop as fl
        monkeypatch.setattr(fl, "FEEDBACK_LOG", tmp_path / "no_feedback.jsonl")
        assert fl.load_feedback_log() == []


# ── 9. get_pilot_metrics ──────────────────────────────────────────────────────

class TestPilotMetrics:
    def test_returns_expected_keys(self, seeded_db, monkeypatch):
        from src.agents.feedback_loop import get_pilot_metrics
        m = get_pilot_metrics()
        required = ("total_opportunities", "proposals_generated", "proposals_sent",
                    "autonomous_sent", "approved_sent", "proposals_accepted",
                    "proposals_rejected", "escalations", "acceptance_rate_pct",
                    "total_revenue", "by_type", "time_saved_hours")
        for k in required:
            assert k in m, f"Missing key: {k}"

    def test_acceptance_rate_is_percentage(self, seeded_db, monkeypatch):
        from src.agents.feedback_loop import get_pilot_metrics
        m = get_pilot_metrics()
        assert 0.0 <= m["acceptance_rate_pct"] <= 100.0

    def test_time_saved_is_non_negative(self, seeded_db, monkeypatch):
        from src.agents.feedback_loop import get_pilot_metrics
        m = get_pilot_metrics()
        assert m["time_saved_hours"] >= 0


# ── 10–13. Auto-sender ────────────────────────────────────────────────────────

class TestAutoSender:
    def test_tier_c_high_score_low_price(self):
        from src.agents.auto_sender import get_autonomy_tier
        tier = get_autonomy_tier(95.0, 150.0, "reactivation", is_repeat_client=False)
        assert tier == "C"

    def test_tier_b_medium_score(self):
        from src.agents.auto_sender import get_autonomy_tier
        tier = get_autonomy_tier(80.0, 150.0, "reactivation", is_repeat_client=True)
        assert tier == "B"

    def test_tier_a_low_score(self):
        from src.agents.auto_sender import get_autonomy_tier
        tier = get_autonomy_tier(55.0, 100.0, "email_automation", is_repeat_client=True)
        assert tier == "A"

    def test_tier_b_high_price(self):
        """Even with score ≥ 90, price > $200 pushes to Tier B (unless reactivation)."""
        from src.agents.auto_sender import get_autonomy_tier
        tier = get_autonomy_tier(92.0, 350.0, "seo_content", is_repeat_client=True)
        assert tier == "B"

    def test_tier_c_reactivation_price_cap(self):
        """Reactivation uses $150 cap instead of $200."""
        from src.agents.auto_sender import get_autonomy_tier
        # $160 > $150 reactivation cap → NOT Tier C even with score ≥ 90
        tier = get_autonomy_tier(95.0, 160.0, "reactivation", is_repeat_client=False)
        assert tier == "B"

    def test_tier_c_requires_repeat_or_reactivation(self):
        """Non-reactivation opp without repeat client history → Tier B even at 92."""
        from src.agents.auto_sender import get_autonomy_tier
        tier = get_autonomy_tier(92.0, 150.0, "email_automation", is_repeat_client=False)
        assert tier == "B"

    def test_tier_c_with_repeat_client(self):
        from src.agents.auto_sender import get_autonomy_tier
        tier = get_autonomy_tier(92.0, 150.0, "email_automation", is_repeat_client=True)
        assert tier == "C"

    def test_should_auto_send_true_for_tier_c(self):
        from src.agents.auto_sender import should_auto_send
        assert should_auto_send(95.0, 150.0, "reactivation") is True

    def test_should_auto_send_false_for_tier_b(self):
        from src.agents.auto_sender import should_auto_send
        assert should_auto_send(80.0, 150.0, "reactivation") is False

    def test_should_auto_send_false_for_tier_a(self):
        from src.agents.auto_sender import should_auto_send
        assert should_auto_send(50.0, 100.0, "email_automation") is False

    def test_process_queue_dry_run_returns_list(self, seeded_db, monkeypatch):
        from src.agents.auto_sender import process_auto_send_queue
        results = process_auto_send_queue(dry_run=True)
        assert isinstance(results, list)

    def test_promote_to_autonomous_sets_approved_by(self, seeded_db, monkeypatch):
        from src.agents.auto_sender import promote_to_autonomous
        promote_to_autonomous(seeded_db["proposal_id"])
        conn = seeded_db["conn"]()
        row = conn.execute(
            "SELECT approved_by, status FROM proposals WHERE id=?",
            (seeded_db["proposal_id"],)
        ).fetchone()
        conn.close()
        assert row["approved_by"] == "autonomous"
        assert row["status"] == "approved"

    def test_get_send_queue_summary_structure(self, seeded_db, monkeypatch):
        from src.agents.auto_sender import get_send_queue_summary
        summary = get_send_queue_summary()
        assert "approved_pending_send" in summary
        assert "by_tier" in summary
        assert set(summary["by_tier"].keys()) == {"A", "B", "C"}


# ── 14. Daily job auto_sent key ───────────────────────────────────────────────

class TestDailyJobSprint4:
    def test_summary_has_auto_sent_key(self):
        from scripts.daily_job import run
        summary = run(dry_run=True, demo_only=True, auto_send=False)
        assert "auto_sent" in summary

    def test_dry_run_auto_sent_is_zero(self):
        from scripts.daily_job import run
        summary = run(dry_run=True, demo_only=True)
        assert summary["auto_sent"] == 0


# ── 15. Log loaders return lists ──────────────────────────────────────────────

class TestLogLoaders:
    def test_feedback_log_empty_returns_list(self, tmp_path, monkeypatch):
        import src.agents.feedback_loop as fl
        monkeypatch.setattr(fl, "FEEDBACK_LOG", tmp_path / "x.jsonl")
        assert fl.load_feedback_log() == []

    def test_calendar_log_empty_returns_list(self, tmp_path, monkeypatch):
        import src.agents.feedback_loop as fl
        monkeypatch.setattr(fl, "CALENDAR_LOG", tmp_path / "y.jsonl")
        assert fl.load_calendar_log() == []

    def test_escalation_log_empty_returns_list(self, tmp_path, monkeypatch):
        import src.agents.feedback_loop as fl
        monkeypatch.setattr(fl, "ESCALATION_LOG", tmp_path / "z.jsonl")
        assert fl.load_escalation_log() == []

    def test_sent_log_empty_returns_list(self, tmp_path, monkeypatch):
        import src.agents.email_sender as es
        monkeypatch.setattr(es, "SENT_LOG", tmp_path / "s.jsonl")
        assert es.load_sent_log() == []
