"""
Sprint 7 tests — Autonomous Negotiation + Payment Links.

Coverage:
 1.  negotiator — start_negotiation writes turn 1 to negotiation_log.
 2.  negotiator — start_negotiation returns offer_price = base * 0.90.
 3.  negotiator — start_negotiation is idempotent (called twice returns same turn).
 4.  negotiator — _extract_intent detects 'accepted' from accept keywords.
 5.  negotiator — _extract_intent detects 'rejected' from reject keywords.
 6.  negotiator — _extract_intent detects 'counter_offer' from counter keywords.
 7.  negotiator — _extract_intent detects 'escalated' from escalation keywords.
 8.  negotiator — _extract_intent returns 'needs_info' for ambiguous text.
 9.  negotiator — process_client_reply writes client turn to DB.
10.  negotiator — process_client_reply generates agent counter on counter_offer intent.
11.  negotiator — process_client_reply offer_price is 15% off on turn 2.
12.  negotiator — process_client_reply returns STATUS_ACCEPTED when client accepts.
13.  negotiator — process_client_reply closes negotiation on rejected intent.
14.  negotiator — process_client_reply escalates after MAX_AGENT_TURNS.
15.  negotiator — kill_negotiation sets STATUS_ESCALATED in DB.
16.  negotiator — get_thread returns turns ordered by turn number.
17.  negotiator — get_active_negotiations returns only open negotiations.
18.  negotiator — get_negotiation_summary returns expected keys.
19.  negotiator — get_negotiation_summary accepted count increments after accept.
20.  payment_link — create_payment_link returns a URL in demo mode.
21.  payment_link — create_payment_link stores URL on proposals.payment_link.
22.  payment_link — create_payment_link is idempotent (second call returns same link).
23.  payment_link — create_payment_link raises ValueError for unknown proposal.
24.  payment_link — get_payment_link returns None before creation.
25.  payment_link — get_payment_link returns URL after creation.
26.  payment_link — record_payment_received sets proposal status to 'paid'.
27.  payment_link — list_payment_links returns proposals with payment_link set.
28.  schema — migrate_db adds payment_link column to proposals.
29.  feedback_loop — too_expensive reply triggers negotiation start (turn in DB).
30.  feedback_loop — accepted reply creates payment link automatically.
"""

from __future__ import annotations

import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import config


# ── Fixtures: isolated in-memory DB ──────────────────────────────────────────

def _make_conn(p: Path):
    conn = sqlite3.connect(str(p), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    """Point config.DB_PATH at a fresh temp DB for each test."""
    db_file = tmp_path / "test_sprint7.db"
    monkeypatch.setattr(config, "DB_PATH", db_file)
    monkeypatch.setattr(config, "DEMO_MODE", True)
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    monkeypatch.setattr(config, "OPENAI_API_KEY", "")
    monkeypatch.setattr(config, "STRIPE_SECRET_KEY", "")
    monkeypatch.setattr(config, "LOGS_DIR", tmp_path / "logs")
    (tmp_path / "logs").mkdir(parents=True, exist_ok=True)

    from src.db.schema import init_db, migrate_db
    init_db()
    migrate_db()
    return db_file


def _seed_proposal(db_path: Path, suggested_price: float = 300.0) -> dict:
    """Insert a minimal client + opportunity + proposal and return their IDs."""
    conn = _make_conn(db_path)
    client_id = str(uuid.uuid4())
    opp_id    = str(uuid.uuid4())
    prop_id   = str(uuid.uuid4())
    now       = datetime.now().isoformat()

    conn.execute(
        """INSERT INTO clients (id, name, industry, contact_email, account_manager)
           VALUES (?, ?, ?, ?, ?)""",
        (client_id, "Acme Corp", "e-commerce", "acme@demo.local", "Carlos García"),
    )
    conn.execute(
        """INSERT INTO opportunities (id, client_id, opportunity_type, score, status)
           VALUES (?, ?, ?, ?, ?)""",
        (opp_id, client_id, "landing_page_optimization", 85.0, "proposal_generated"),
    )
    conn.execute(
        """INSERT INTO proposals
           (id, opportunity_id, client_id, subject, body, suggested_price, status)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (prop_id, opp_id, client_id,
         "Test Subject", "Test body.", suggested_price, "sent"),
    )
    conn.commit()
    conn.close()
    return {"client_id": client_id, "opp_id": opp_id, "prop_id": prop_id}


# ── Negotiator tests ──────────────────────────────────────────────────────────

class TestNegotiatorStartNegotiation:
    def test_writes_turn_1_to_db(self, isolated_db):
        ids = _seed_proposal(isolated_db)
        from src.agents.negotiator import start_negotiation
        start_negotiation(ids["prop_id"])
        conn = _make_conn(isolated_db)
        rows = conn.execute(
            "SELECT * FROM negotiation_log WHERE proposal_id=?", (ids["prop_id"],)
        ).fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0]["role"] == "agent"
        assert rows[0]["turn"] == 1

    def test_offer_price_is_10_pct_off(self, isolated_db):
        ids = _seed_proposal(isolated_db, suggested_price=400.0)
        from src.agents.negotiator import start_negotiation
        result = start_negotiation(ids["prop_id"])
        assert abs(result["offer_price"] - 360.0) < 0.01

    def test_idempotent_second_call(self, isolated_db):
        ids = _seed_proposal(isolated_db)
        from src.agents.negotiator import start_negotiation
        start_negotiation(ids["prop_id"])
        start_negotiation(ids["prop_id"])  # second call
        conn = _make_conn(isolated_db)
        count = conn.execute(
            "SELECT COUNT(*) FROM negotiation_log WHERE proposal_id=?", (ids["prop_id"],)
        ).fetchone()[0]
        conn.close()
        assert count == 1   # only 1 row written

    def test_raises_for_unknown_proposal(self, isolated_db):
        from src.agents.negotiator import start_negotiation
        with pytest.raises(ValueError, match="not found"):
            start_negotiation("nonexistent-id")


class TestExtractIntent:
    def test_accept_keywords(self):
        from src.agents.negotiator import _extract_intent, NEG_INTENT_ACCEPT
        assert _extract_intent("Acepto, de acuerdo.") == NEG_INTENT_ACCEPT
        assert _extract_intent("Ok perfecto, adelante.") == NEG_INTENT_ACCEPT

    def test_reject_keywords(self):
        from src.agents.negotiator import _extract_intent, NEG_INTENT_REJECT
        assert _extract_intent("No me interesa, gracias.") == NEG_INTENT_REJECT
        assert _extract_intent("Lo siento, por ahora no.") == NEG_INTENT_REJECT

    def test_counter_offer_keywords(self):
        from src.agents.negotiator import _extract_intent, NEG_INTENT_COUNTER
        assert _extract_intent("Si bajas un poco más podemos negociar.") == NEG_INTENT_COUNTER

    def test_escalation_keywords(self):
        from src.agents.negotiator import _extract_intent, NEG_INTENT_ESCALATE
        assert _extract_intent("Quiero hablar con alguien, no más emails.") == NEG_INTENT_ESCALATE

    def test_ambiguous_returns_needs_info(self):
        from src.agents.negotiator import _extract_intent, NEG_INTENT_INFO
        assert _extract_intent("Déjame pensarlo.") == NEG_INTENT_INFO


class TestProcessClientReply:
    def _start(self, isolated_db, price=300.0):
        ids = _seed_proposal(isolated_db, suggested_price=price)
        from src.agents.negotiator import start_negotiation
        start_negotiation(ids["prop_id"])
        return ids

    def test_writes_client_turn(self, isolated_db):
        ids = self._start(isolated_db)
        from src.agents.negotiator import process_client_reply
        process_client_reply(ids["prop_id"], "Si bajas un poco más podemos hablar.")
        conn = _make_conn(isolated_db)
        roles = [r["role"] for r in conn.execute(
            "SELECT role FROM negotiation_log WHERE proposal_id=? ORDER BY id",
            (ids["prop_id"],)
        ).fetchall()]
        conn.close()
        assert "client" in roles

    def test_counter_generates_agent_turn_2(self, isolated_db):
        ids = self._start(isolated_db, price=300.0)
        from src.agents.negotiator import process_client_reply
        result = process_client_reply(ids["prop_id"], "podemos negociar el precio?")
        assert result["status"] == "active"
        assert result["agent_message"] is not None

    def test_turn_2_offer_is_15_pct_off(self, isolated_db):
        ids = self._start(isolated_db, price=300.0)
        from src.agents.negotiator import process_client_reply
        result = process_client_reply(ids["prop_id"], "podemos negociar el precio?")
        # 15% off 300 = 255
        assert abs(result["offer_price"] - 255.0) < 0.01

    def test_accept_returns_accepted_status(self, isolated_db):
        ids = self._start(isolated_db)
        from src.agents.negotiator import process_client_reply, STATUS_ACCEPTED
        result = process_client_reply(ids["prop_id"], "Perfecto, acepto la oferta.")
        assert result["status"] == STATUS_ACCEPTED

    def test_reject_closes_negotiation(self, isolated_db):
        ids = self._start(isolated_db)
        from src.agents.negotiator import process_client_reply, STATUS_REJECTED
        result = process_client_reply(ids["prop_id"], "No me interesa, gracias.")
        assert result["status"] == STATUS_REJECTED

    def test_escalates_after_max_turns(self, isolated_db):
        ids = self._start(isolated_db, price=200.0)
        from src.agents import negotiator
        from src.agents.negotiator import process_client_reply, STATUS_ESCALATED
        # Force max turns reached by patching
        original = negotiator.MAX_AGENT_TURNS
        negotiator.MAX_AGENT_TURNS = 1
        try:
            result = process_client_reply(ids["prop_id"], "Todavía es caro.")
        finally:
            negotiator.MAX_AGENT_TURNS = original
        assert result["status"] == STATUS_ESCALATED


class TestKillSwitch:
    def test_kill_sets_escalated(self, isolated_db):
        ids = _seed_proposal(isolated_db)
        from src.agents.negotiator import start_negotiation, kill_negotiation
        start_negotiation(ids["prop_id"])
        kill_negotiation(ids["prop_id"], reason="test_kill")
        conn = _make_conn(isolated_db)
        row = conn.execute(
            "SELECT status FROM proposals WHERE id=?", (ids["prop_id"],)
        ).fetchone()
        conn.close()
        assert row["status"] == "escalated"


class TestGetThread:
    def test_returns_ordered_turns(self, isolated_db):
        ids = _seed_proposal(isolated_db)
        from src.agents.negotiator import start_negotiation, process_client_reply, get_thread
        start_negotiation(ids["prop_id"])
        process_client_reply(ids["prop_id"], "Si bajas más lo pensamos.")
        thread = get_thread(ids["prop_id"])
        assert len(thread) >= 2
        assert thread[0]["turn"] <= thread[1]["turn"]
        assert thread[0]["role"] == "agent"

    def test_empty_for_unknown_proposal(self, isolated_db):
        from src.agents.negotiator import get_thread
        assert get_thread("nonexistent") == []


class TestNegotiationSummary:
    def test_summary_keys(self, isolated_db):
        from src.agents.negotiator import get_negotiation_summary
        s = get_negotiation_summary()
        for key in ("total_negotiations", "active", "accepted", "rejected", "escalated", "auto_resolution_rate"):
            assert key in s

    def test_accepted_count_increments(self, isolated_db):
        ids = _seed_proposal(isolated_db)
        from src.agents.negotiator import start_negotiation, process_client_reply, get_negotiation_summary
        start_negotiation(ids["prop_id"])
        process_client_reply(ids["prop_id"], "Acepto, trato hecho.")
        s = get_negotiation_summary()
        assert s["accepted"] >= 1


# ── Payment link tests ────────────────────────────────────────────────────────

class TestPaymentLink:
    def test_create_returns_url(self, isolated_db):
        ids = _seed_proposal(isolated_db)
        from src.agents.payment_link import create_payment_link
        result = create_payment_link(ids["prop_id"])
        assert result["url"].startswith("https://")
        assert result["simulated"] is True

    def test_url_stored_on_proposal(self, isolated_db):
        ids = _seed_proposal(isolated_db)
        from src.agents.payment_link import create_payment_link, get_payment_link
        result = create_payment_link(ids["prop_id"])
        stored = get_payment_link(ids["prop_id"])
        assert stored == result["url"]

    def test_idempotent(self, isolated_db):
        ids = _seed_proposal(isolated_db)
        from src.agents.payment_link import create_payment_link
        r1 = create_payment_link(ids["prop_id"])
        r2 = create_payment_link(ids["prop_id"])
        assert r1["url"] == r2["url"]
        assert r2.get("already_existed") is True

    def test_raises_for_unknown_proposal(self, isolated_db):
        from src.agents.payment_link import create_payment_link
        with pytest.raises(ValueError, match="not found"):
            create_payment_link("nonexistent-id")

    def test_get_payment_link_none_before_creation(self, isolated_db):
        ids = _seed_proposal(isolated_db)
        from src.agents.payment_link import get_payment_link
        assert get_payment_link(ids["prop_id"]) is None

    def test_get_payment_link_after_creation(self, isolated_db):
        ids = _seed_proposal(isolated_db)
        from src.agents.payment_link import create_payment_link, get_payment_link
        create_payment_link(ids["prop_id"])
        assert get_payment_link(ids["prop_id"]) is not None

    def test_record_payment_sets_paid(self, isolated_db):
        ids = _seed_proposal(isolated_db)
        from src.agents.payment_link import record_payment_received
        record_payment_received(ids["prop_id"])
        conn = _make_conn(isolated_db)
        row = conn.execute(
            "SELECT status FROM proposals WHERE id=?", (ids["prop_id"],)
        ).fetchone()
        conn.close()
        assert row["status"] == "paid"

    def test_list_payment_links_shows_proposals_with_link(self, isolated_db):
        ids = _seed_proposal(isolated_db)
        from src.agents.payment_link import create_payment_link, list_payment_links
        create_payment_link(ids["prop_id"])
        links = list_payment_links()
        assert any(lnk["proposal_id"] == ids["prop_id"] for lnk in links)


# ── Schema migration test ─────────────────────────────────────────────────────

class TestSchemaMigration:
    def test_migrate_adds_payment_link_column(self, isolated_db):
        conn = _make_conn(isolated_db)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(proposals)").fetchall()}
        conn.close()
        assert "payment_link" in cols


# ── Feedback loop integration tests ──────────────────────────────────────────

class TestFeedbackLoopIntegration:
    def test_too_expensive_triggers_negotiation(self, isolated_db):
        ids = _seed_proposal(isolated_db)
        from src.agents.feedback_loop import record_client_reply, INTENT_TOO_EXPENSIVE
        record_client_reply(ids["prop_id"], intent=INTENT_TOO_EXPENSIVE, simulated=True)
        conn = _make_conn(isolated_db)
        count = conn.execute(
            "SELECT COUNT(*) FROM negotiation_log WHERE proposal_id=?", (ids["prop_id"],)
        ).fetchone()[0]
        conn.close()
        assert count >= 1

    def test_accepted_creates_payment_link(self, isolated_db):
        ids = _seed_proposal(isolated_db)
        from src.agents.feedback_loop import record_client_reply, INTENT_ACCEPTED
        from src.agents.payment_link import get_payment_link
        record_client_reply(ids["prop_id"], intent=INTENT_ACCEPTED, simulated=True)
        link = get_payment_link(ids["prop_id"])
        assert link is not None and link.startswith("https://")
