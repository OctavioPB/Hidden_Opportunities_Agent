"""
Regression tests for the defects fixed in the application audit.

Each test pins one behaviour that was previously wrong:

 1. negotiator  — a negated acceptance ("can't accept", "not ideal") is not a win.
 2. negotiator  — kill switch / max turns remove the thread from the active list.
 3. negotiator  — an accepted negotiation records revenue and a payment link
                  at the negotiated price.
 4. follow-ups  — a rejection cancels the pending sequence.
 5. follow-ups  — a failed production send stays pending (is not marked sent).
 6. follow-ups  — a finished sequence is not scheduled a second time.
 7. follow-ups  — due entries of an already-resolved proposal are cancelled, not sent.
 8. scorer      — persist_opportunities stores ml_probability; results carry _metrics.
 9. scorer      — a propensity score of 0.0 is kept, not replaced by the default.
10. crm         — get_client_activity reads the latest snapshot, not the history max.
11. seasonal    — get_current_boosts reports the window active this month.
12. text        — batch signal summaries equal the per-client summaries.
13. analytics   — by-type breakdown does not double count repeated feedback rows.
14. alerts      — the "Data:" line shows the metrics the rule fired on.
15. jsonl       — corrupt lines are skipped; newest_first reverses.
"""

import sqlite3
import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import config


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """Fresh temp DB and log directory for each test."""
    db_file = tmp_path / "audit.db"
    logs = tmp_path / "logs"
    logs.mkdir()
    monkeypatch.setattr(config, "DB_PATH", db_file)
    monkeypatch.setattr(config, "DEMO_MODE", True)
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    monkeypatch.setattr(config, "OPENAI_API_KEY", "")
    monkeypatch.setattr(config, "STRIPE_SECRET_KEY", "")
    monkeypatch.setattr(config, "LOGS_DIR", logs)

    # Log paths are module constants resolved at import time — redirect them too
    from src.agents import (
        email_sender, feedback_loop, follow_up_engine, negotiator, payment_link,
    )
    from src.integrations import hubspot
    monkeypatch.setattr(negotiator, "NEGOTIATION_LOG", logs / "negotiations.jsonl")
    monkeypatch.setattr(payment_link, "PAYMENT_LINKS_LOG", logs / "payment_links.jsonl")
    monkeypatch.setattr(follow_up_engine, "FOLLOW_UP_LOG", logs / "follow_ups.jsonl")
    monkeypatch.setattr(feedback_loop, "FEEDBACK_LOG", logs / "feedback.jsonl")
    monkeypatch.setattr(feedback_loop, "CALENDAR_LOG", logs / "calendar_events.jsonl")
    monkeypatch.setattr(feedback_loop, "ESCALATION_LOG", logs / "escalations.jsonl")
    monkeypatch.setattr(email_sender, "SENT_LOG", logs / "sent_emails.jsonl")
    monkeypatch.setattr(hubspot, "CRM_SYNC_LOG", logs / "crm_sync.jsonl")

    from src.agents import scorer
    from src.db.schema import init_db, migrate_db
    init_db()
    migrate_db()
    scorer.invalidate_cache()
    yield db_file
    scorer.invalidate_cache()


def _conn(p: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    return conn


def _seed(db_path: Path, price: float = 400.0, status: str = "sent",
          opp_type: str = "landing_page_optimization") -> dict:
    """Insert one client + opportunity + proposal; return their ids."""
    ids = {"client_id": str(uuid.uuid4()), "opp_id": str(uuid.uuid4()), "prop_id": str(uuid.uuid4())}
    conn = _conn(db_path)
    conn.execute(
        "INSERT INTO clients (id, name, industry, contact_email, account_manager) VALUES (?,?,?,?,?)",
        (ids["client_id"], "Acme Corp", "e-commerce", "acme@demo.local", "Dana Reyes"),
    )
    conn.execute(
        "INSERT INTO opportunities (id, client_id, opportunity_type, score, status) VALUES (?,?,?,?,?)",
        (ids["opp_id"], ids["client_id"], opp_type, 85.0, "proposal_generated"),
    )
    now = datetime.now().isoformat()
    conn.execute(
        "INSERT INTO proposals (id, opportunity_id, client_id, subject, body, suggested_price, "
        "status, created_at, sent_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (ids["prop_id"], ids["opp_id"], ids["client_id"], "Subject", "Body.", price, status, now, now),
    )
    conn.commit()
    conn.close()
    return ids


# ── 1–3. Negotiator ───────────────────────────────────────────────────────────

class TestNegotiationIntent:
    @pytest.mark.parametrize("text", [
        "I can't accept that price",
        "Sorry, we cannot accept this",
        "This is not ideal for us",          # "ideal" contains "deal"
        "That is unacceptable",
        "No deal",
        "No acepto ese precio",
        "I don't agree with this",
    ])
    def test_negated_or_lookalike_is_not_acceptance(self, db, text):
        from src.agents.negotiator import NEG_INTENT_ACCEPT, _extract_intent
        assert _extract_intent(text) != NEG_INTENT_ACCEPT

    @pytest.mark.parametrize("text", [
        "Ok, deal", "We accept the offer", "Acepto", "Sounds good, let's do it", "Agreed",
    ])
    def test_plain_acceptance_still_detected(self, db, text):
        from src.agents.negotiator import NEG_INTENT_ACCEPT, _extract_intent
        assert _extract_intent(text) == NEG_INTENT_ACCEPT


class TestNegotiationLifecycle:
    def test_kill_switch_removes_thread_from_active(self, db):
        from src.agents import negotiator as ng
        ids = _seed(db)
        ng.start_negotiation(ids["prop_id"])
        assert [n["proposal_id"] for n in ng.get_active_negotiations()] == [ids["prop_id"]]

        ng.kill_negotiation(ids["prop_id"])

        assert ng.get_active_negotiations() == []
        summary = ng.get_negotiation_summary()
        assert summary["escalated"] == 1 and summary["active"] == 0

    def test_max_turns_escalation_removes_thread_from_active(self, db):
        from src.agents import negotiator as ng
        ids = _seed(db)
        ng.start_negotiation(ids["prop_id"])
        result = {}
        for _ in range(ng.MAX_AGENT_TURNS):
            result = ng.process_client_reply(ids["prop_id"], "Could you send more information?")

        assert result["status"] == ng.STATUS_ESCALATED
        assert ng.get_active_negotiations() == []
        assert ng.get_negotiation_summary()["escalated"] == 1

    def test_acceptance_records_revenue_and_payment_link_at_negotiated_price(self, db):
        from src.agents import negotiator as ng
        ids = _seed(db, price=400.0)
        ng.start_negotiation(ids["prop_id"])                    # turn 1 → 10% off = 360
        result = ng.process_client_reply(ids["prop_id"], "Ok, deal")

        assert result["status"] == ng.STATUS_ACCEPTED
        assert result["offer_price"] == 360.0
        assert result["payment_link"]

        conn = _conn(db)
        fb = conn.execute(
            "SELECT outcome, revenue FROM feedback_log WHERE proposal_id=?", (ids["prop_id"],)
        ).fetchall()
        link = conn.execute(
            "SELECT payment_link FROM proposals WHERE id=?", (ids["prop_id"],)
        ).fetchone()[0]
        conn.close()
        assert [(r["outcome"], r["revenue"]) for r in fb] == [("accepted", 360.0)]
        assert link == result["payment_link"]


# ── 4–7. Follow-up sequences ──────────────────────────────────────────────────

def _queue_statuses(db_path: Path, proposal_id: str) -> list[str]:
    conn = _conn(db_path)
    rows = conn.execute(
        "SELECT status FROM follow_up_queue WHERE proposal_id=? ORDER BY sequence_turn",
        (proposal_id,),
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def _make_due(db_path: Path) -> None:
    conn = _conn(db_path)
    conn.execute(
        "UPDATE follow_up_queue SET scheduled_at=?",
        ((datetime.now() - timedelta(days=1)).isoformat(),),
    )
    conn.commit()
    conn.close()


class TestFollowUps:
    @pytest.mark.parametrize("intent", ["rejected", "escalated", "too_expensive", "accepted"])
    def test_resolving_reply_cancels_pending_follow_ups(self, db, intent):
        from src.agents.feedback_loop import record_client_reply
        ids = _seed(db)
        record_client_reply(ids["prop_id"], "ignored", simulated=True)
        assert _queue_statuses(db, ids["prop_id"]) == ["pending", "pending"]

        record_client_reply(ids["prop_id"], intent, simulated=True)

        assert _queue_statuses(db, ids["prop_id"]) == ["cancelled", "cancelled"]

    def test_failed_production_send_stays_pending(self, db, monkeypatch):
        from src.agents import email_sender, follow_up_engine as fu
        ids = _seed(db)
        fu.schedule_follow_up(ids["prop_id"])
        _make_due(db)
        monkeypatch.setattr(config, "DEMO_MODE", False)

        def boom(_payload):
            raise RuntimeError("SendGrid down")
        monkeypatch.setattr(email_sender, "_send_via_sendgrid", boom)

        assert fu.process_due_follow_ups() == []
        assert _queue_statuses(db, ids["prop_id"]) == ["pending", "pending"]

    def test_production_send_delivers_follow_up_content(self, db, monkeypatch):
        from src.agents import email_sender, follow_up_engine as fu
        ids = _seed(db)
        fu.schedule_follow_up(ids["prop_id"])
        _make_due(db)
        monkeypatch.setattr(config, "DEMO_MODE", False)
        delivered = []
        monkeypatch.setattr(email_sender, "_send_via_sendgrid", delivered.append)

        sent = fu.process_due_follow_ups()

        assert len(sent) == 2
        assert _queue_statuses(db, ids["prop_id"]) == ["sent", "sent"]
        assert delivered[0]["to"] == "acme@demo.local"
        assert delivered[0]["subject"].startswith("Re: A quick ROI perspective")
        assert delivered[0]["proposal_id"] == ids["prop_id"]
        # the proposal itself is untouched — a follow-up is not a re-send
        conn = _conn(db)
        assert conn.execute(
            "SELECT status FROM proposals WHERE id=?", (ids["prop_id"],)
        ).fetchone()[0] == "sent"
        conn.close()

    def test_finished_sequence_is_not_rescheduled(self, db):
        from src.agents import follow_up_engine as fu
        ids = _seed(db)
        assert len(fu.schedule_follow_up(ids["prop_id"])) == 2
        _make_due(db)
        assert len(fu.process_due_follow_ups()) == 2

        assert fu.schedule_follow_up(ids["prop_id"]) == []
        assert _queue_statuses(db, ids["prop_id"]) == ["sent", "sent"]

    def test_due_follow_ups_of_resolved_proposal_are_cancelled(self, db):
        from src.agents import follow_up_engine as fu
        ids = _seed(db)
        fu.schedule_follow_up(ids["prop_id"])
        _make_due(db)
        conn = _conn(db)
        conn.execute("UPDATE proposals SET status='rejected' WHERE id=?", (ids["prop_id"],))
        conn.commit()
        conn.close()

        assert fu.process_due_follow_ups() == []
        assert _queue_statuses(db, ids["prop_id"]) == ["cancelled", "cancelled"]


# ── 8–10. Scorer and CRM activity ─────────────────────────────────────────────

def _add_metrics(db_path: Path, client_id: str, day: str, **fields) -> None:
    cols = ", ".join(fields)
    marks = ", ".join("?" for _ in fields)
    conn = _conn(db_path)
    conn.execute(
        f"INSERT INTO client_metrics (client_id, date, {cols}) VALUES (?, ?, {marks})",
        (client_id, day, *fields.values()),
    )
    conn.commit()
    conn.close()


class TestScorer:
    def test_persist_stores_ml_probability(self, db):
        from src.agents.scorer import persist_opportunities
        ids = _seed(db)
        row = {"client_id": ids["client_id"], "opportunity_type": "seo_content",
               "score": 70.0, "ml_probability": 0.81}

        assert persist_opportunities([row]) == 1
        # a later run without a model must not erase the stored probability
        assert persist_opportunities([{**row, "score": 72.0, "ml_probability": None}]) == 0

        conn = _conn(db)
        stored = conn.execute(
            "SELECT score, ml_probability FROM opportunities WHERE opportunity_type='seo_content'"
        ).fetchall()
        conn.close()
        assert [(r["score"], r["ml_probability"]) for r in stored] == [(72.0, 0.81)]

    def test_results_carry_metrics_and_zero_propensity(self, db):
        from src.agents import scorer
        ids = _seed(db)
        _add_metrics(db, ids["client_id"], "2026-01-10", days_inactive=60, days_since_last_contact=60)
        conn = _conn(db)
        conn.execute(
            "UPDATE clients SET propensity_tier='low', propensity_score=0.0 WHERE id=?",
            (ids["client_id"],),
        )
        conn.commit()
        conn.close()

        results = scorer.score_all_clients()

        assert results, "an inactive client should trigger reactivation"
        r = results[0]
        assert r["_metrics"]["days_inactive"] == 60
        assert r["propensity_tier"] == "low"
        assert r["propensity_score"] == 0.0

    def test_client_activity_uses_latest_snapshot(self, db):
        from src.data_sources.crm import get_client_activity
        ids = _seed(db)
        _add_metrics(db, ids["client_id"], "2026-01-01", days_inactive=90, days_since_last_contact=90)
        _add_metrics(db, ids["client_id"], "2026-02-01", days_inactive=2, days_since_last_contact=1)

        activity = get_client_activity(ids["client_id"])

        assert activity["days_inactive"] == 2
        assert activity["days_since_last_contact"] == 1


# ── 11. Seasonal ──────────────────────────────────────────────────────────────

class TestSeasonal:
    def test_current_boosts_report_the_active_window(self, monkeypatch):
        from src.agents import seasonal_engine as se

        class July(date):
            @classmethod
            def today(cls):
                return cls(2026, 7, 15)
        monkeypatch.setattr(se, "date", July)

        boosts = {b["opportunity_type"]: b for b in se.get_current_boosts()}

        # landing pages have two windows; July belongs to (3, 4, 7), not (9, 10)
        lpo = boosts["landing_page_optimization"]
        assert 7 in lpo["months"]
        assert lpo["multiplier"] == se.get_seasonal_multiplier("landing_page_optimization", July.today())
        assert all(7 in b["months"] for b in boosts.values())


# ── 12. Text signals ──────────────────────────────────────────────────────────

class TestTextSignals:
    def test_batch_summaries_match_per_client_summaries(self, db):
        from src.data_sources import text_signals as ts
        a, b, c = _seed(db), _seed(db), _seed(db)
        conn = _conn(db)
        rows = [
            # client a: two processed rows
            (a["client_id"], 0.4, 1, 0, 0, 0, 1),
            (a["client_id"], -0.8, 0, 0, 1, 1, 0),
            # client b: one processed, one unprocessed row whose flags must be ignored
            (b["client_id"], 0.2, 0, 1, 0, 0, 0),
            (b["client_id"], None, 1, 0, 1, 1, 1),
            # client c: only unprocessed
            (c["client_id"], None, 0, 0, 0, 0, 0),
        ]
        conn.executemany(
            "INSERT INTO text_signals (client_id, source, raw_text, sentiment, mentions_price, "
            "asks_for_results, churn_risk, urgency_signal, interest_signal) "
            "VALUES (?, 'email', 'x', ?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
        conn.close()

        batch = {s["client_id"]: s for s in ts.get_all_signal_summaries()}

        assert set(batch) == {a["client_id"], b["client_id"], c["client_id"]}
        for cid, summary in batch.items():
            assert summary == {**ts.get_signal_summary(cid), "client_id": cid}

    def test_counts_are_zero_not_null_on_empty_table(self, db):
        from src.data_sources.text_signals import count_signals_by_type
        assert set(count_signals_by_type().values()) == {0}


# ── 13. Analytics ─────────────────────────────────────────────────────────────

class TestAnalytics:
    def test_by_type_counts_each_proposal_once(self, db):
        from src.agents.analytics_engine import get_analytics_summary
        ids = _seed(db, status="accepted")
        conn = _conn(db)
        now = datetime.now().isoformat()
        conn.executemany(
            "INSERT INTO feedback_log (opportunity_id, proposal_id, outcome, revenue, logged_at) "
            "VALUES (?, ?, 'accepted', ?, ?)",
            [(ids["opp_id"], ids["prop_id"], 100.0, now), (ids["opp_id"], ids["prop_id"], 50.0, now)],
        )
        conn.commit()
        conn.close()

        by_type = get_analytics_summary(period_days=0)["by_type"]

        assert by_type == [{
            "opportunity_type": "landing_page_optimization",
            "proposals": 1, "accepted": 1, "revenue": 150.0,
        }]


# ── 14. Alerts ────────────────────────────────────────────────────────────────

class TestAlerts:
    def test_scored_opportunity_renders_real_metrics(self, db):
        from src.agents import scorer
        from src.agents.alerts import format_slack_message
        ids = _seed(db)
        _add_metrics(db, ids["client_id"], "2026-01-10", days_inactive=60, days_since_last_contact=60)

        opp = next(r for r in scorer.score_all_clients() if r["opportunity_type"] == "reactivation")
        text = format_slack_message(opp)["text"]

        assert "Inactive 60 days" in text

    def test_dashboard_link_points_at_configured_ui(self, monkeypatch):
        from src.agents.alerts import format_slack_message, format_telegram_message
        monkeypatch.setattr(config, "DASHBOARD_URL", "https://ops.example.test")
        opp = {"score": 80, "client_name": "X", "label": "L", "suggested_price": 100}

        buttons = format_slack_message(opp)["blocks"][-2]["elements"]
        assert buttons[0]["url"] == "https://ops.example.test"
        assert "https://ops.example.test" in format_telegram_message(opp)


# ── 15. JSONL helper ──────────────────────────────────────────────────────────

class TestJsonl:
    def test_round_trip_skips_corrupt_lines(self, tmp_path):
        from src.jsonl import append_jsonl, read_jsonl
        path = tmp_path / "nested" / "log.jsonl"
        assert read_jsonl(path) == []

        append_jsonl(path, {"n": 1, "when": datetime(2026, 1, 1)})
        with path.open("a", encoding="utf-8") as fh:
            fh.write("{not json\n\n")
        append_jsonl(path, {"n": 2, "text": "señal → ok"})

        assert [r["n"] for r in read_jsonl(path)] == [1, 2]
        assert [r["n"] for r in read_jsonl(path, newest_first=True)] == [2, 1]
        assert read_jsonl(path)[1]["text"] == "señal → ok"


# ── 16. Rules engine ──────────────────────────────────────────────────────────

class TestRulesNullMetrics:
    def test_null_metrics_do_not_crash_evaluation(self):
        from src.agents.rules import evaluate
        metrics = dict.fromkeys(
            ["bounce_rate", "pages_per_session", "conversion_rate", "organic_traffic", "ctr",
             "cpc", "roas", "ad_spend", "email_open_rate", "email_click_rate", "keyword_rankings",
             "days_since_last_contact"],
        )
        metrics["days_inactive"] = 60

        fired = [r.opportunity_type for r in evaluate(metrics)]

        assert fired == ["reactivation"]


# ── 17. Previously unconnected features ───────────────────────────────────────

class TestConnectedFeatures:
    def test_too_expensive_keeps_proposal_and_opportunity_open(self, db):
        from src.agents.feedback_loop import record_client_reply
        from src.agents.scorer import persist_opportunities
        ids = _seed(db)

        res = record_client_reply(ids["prop_id"], "too_expensive", simulated=True)

        assert res["new_proposal_status"] == "sent" and res["new_opp_status"] == "sent"
        # a new detection run updates the open opportunity instead of duplicating it
        assert persist_opportunities([{
            "client_id": ids["client_id"], "opportunity_type": "landing_page_optimization",
            "score": 80.0, "ml_probability": None}]) == 0
        conn = _conn(db)
        assert conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0] == 1
        conn.close()

    def test_confidence_modifier_adjusts_score(self, db):
        from src.agents import scorer
        from src.agents.feedback_loop import get_all_confidence_modifiers, record_client_reply
        ids = _seed(db, opp_type="reactivation")
        _add_metrics(db, ids["client_id"], "2026-01-10", days_inactive=60, days_since_last_contact=60)
        base = next(r for r in scorer.score_all_clients() if r["opportunity_type"] == "reactivation")
        base_score = base["score"]

        record_client_reply(ids["prop_id"], "rejected", simulated=True)   # −20
        scorer.invalidate_cache()

        assert get_all_confidence_modifiers()[(ids["client_id"], "reactivation")] == -20.0
        adjusted = next(r for r in scorer.score_all_clients() if r["opportunity_type"] == "reactivation")
        assert adjusted["score"] == max(0.0, round(base_score - 20.0, 1)) or adjusted["score"] < base_score
        assert adjusted["confidence_modifier"] == -20.0

    def test_whatsapp_preference_triggers_notification(self, db, tmp_path, monkeypatch):
        from src.agents.email_sender import send_proposal_email
        from src.integrations import whatsapp
        from src.integrations.whatsapp import set_channel_preference
        WA_LOG = tmp_path / "wa.jsonl"
        monkeypatch.setattr(whatsapp, "WA_LOG", WA_LOG)
        ids = _seed(db, status="approved")
        set_channel_preference(ids["client_id"], "whatsapp", "+15550001111")

        payload = send_proposal_email(ids["prop_id"])

        assert payload["whatsapp_sent"] is True
        assert WA_LOG.exists()
