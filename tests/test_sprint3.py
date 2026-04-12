"""
Sprint 3 tests — Proposal Generator.

Coverage:
1. Template rendering — all 7 opportunity types produce valid subject + body.
2. Context builder — required keys are present and have correct types.
3. Insight paragraph — template fallback returns non-empty text for each type.
4. LLM fallback — when no API key is configured, generation uses template.
5. DB persistence — generate_proposal writes to proposals table.
6. Markdown export — exported file exists and contains expected content.
7. Approval workflow — approve, reject, and edit functions update DB correctly.
8. generate_proposals_for_all — only generates for qualifying opportunities.
9. Proposal log — get_all_proposals returns expected structure.
10. GOVERNANCE.md — file exists and contains required sections.
"""

from __future__ import annotations

import json
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import config


# ── Shared fixtures ───────────────────────────────────────────────────────────

SAMPLE_CLIENT = {
    "id":              "test-client-001",
    "name":            "Bella Cucina Restaurant",
    "industry":        "Restaurant",
    "company_size":    "small",
    "account_age_days": 180,
    "monthly_spend":   1500.0,
    "contact_email":   "owner@bellacucina.demo",
    "account_manager": "Maria López",
    "is_demo_scenario": 1,
}

SAMPLE_METRICS = {
    "ctr":              0.055,
    "bounce_rate":      0.78,
    "pages_per_session": 1.4,
    "conversion_rate":  0.008,
    "organic_traffic":  1200,
    "keyword_rankings": 12,
    "email_open_rate":  0.09,
    "email_click_rate": 0.02,
    "roas":             2.1,
    "ad_spend":         75.0,   # daily → $2250/month
    "days_inactive":    10,
    "days_since_last_contact": 8,
}

ALL_OPP_TYPES = [
    "landing_page_optimization",
    "seo_content",
    "retargeting_campaign",
    "email_automation",
    "reactivation",
    "conversion_rate_audit",
    "upsell_ad_budget",
]


# ── 1. Template rendering ─────────────────────────────────────────────────────

class TestTemplateRendering:
    def setup_method(self):
        from src.agents.proposal_generator import _build_context, _render_template
        self._build_context   = _build_context
        self._render_template = _render_template

    def _ctx(self, opp_type: str) -> dict:
        ctx = self._build_context(SAMPLE_CLIENT, SAMPLE_METRICS, opp_type)
        ctx["insight_paragraph"] = "Este es un párrafo de prueba."
        return ctx

    @pytest.mark.parametrize("opp_type", ALL_OPP_TYPES)
    def test_subject_is_non_empty_string(self, opp_type):
        subject, _ = self._render_template(opp_type, self._ctx(opp_type))
        assert isinstance(subject, str) and subject.strip()

    @pytest.mark.parametrize("opp_type", ALL_OPP_TYPES)
    def test_body_is_non_empty_string(self, opp_type):
        _, body = self._render_template(opp_type, self._ctx(opp_type))
        assert isinstance(body, str) and len(body) > 50

    @pytest.mark.parametrize("opp_type", ALL_OPP_TYPES)
    def test_subject_contains_client_name(self, opp_type):
        subject, _ = self._render_template(opp_type, self._ctx(opp_type))
        assert "Bella Cucina" in subject

    @pytest.mark.parametrize("opp_type", ALL_OPP_TYPES)
    def test_body_contains_insight_paragraph(self, opp_type):
        ctx = self._ctx(opp_type)
        _, body = self._render_template(opp_type, ctx)
        assert "Este es un párrafo de prueba." in body

    def test_unknown_opp_type_uses_generic_template(self):
        ctx = self._ctx("landing_page_optimization")
        ctx["insight_paragraph"] = "Insight."
        subject, body = self._render_template("nonexistent_type", ctx)
        assert subject
        assert body


# ── 2. Context builder ────────────────────────────────────────────────────────

class TestContextBuilder:
    def setup_method(self):
        from src.agents.proposal_generator import _build_context
        self._build_context = _build_context

    def test_context_has_client_name(self):
        ctx = self._build_context(SAMPLE_CLIENT, SAMPLE_METRICS, "landing_page_optimization")
        assert ctx["client_name"] == "Bella Cucina Restaurant"

    def test_context_has_industry(self):
        ctx = self._build_context(SAMPLE_CLIENT, SAMPLE_METRICS, "seo_content")
        assert ctx["industry"] == "Restaurant"

    def test_monthly_ad_spend_is_daily_times_30(self):
        ctx = self._build_context(SAMPLE_CLIENT, SAMPLE_METRICS, "retargeting_campaign")
        assert abs(ctx["monthly_ad_spend"] - SAMPLE_METRICS["ad_spend"] * 30) < 0.01

    def test_suggested_price_matches_rules(self):
        from src.agents.rules import SUGGESTED_PRICES
        for opp_type in ALL_OPP_TYPES:
            ctx = self._build_context(SAMPLE_CLIENT, SAMPLE_METRICS, opp_type)
            assert ctx["suggested_price"] == SUGGESTED_PRICES[opp_type]

    def test_discounted_price_is_80_percent(self):
        ctx = self._build_context(SAMPLE_CLIENT, SAMPLE_METRICS, "reactivation")
        assert ctx["discounted_price"] == round(ctx["suggested_price"] * 0.80)

    def test_insight_paragraph_starts_empty(self):
        ctx = self._build_context(SAMPLE_CLIENT, SAMPLE_METRICS, "email_automation")
        assert ctx["insight_paragraph"] == ""

    def test_context_has_offer_expiry(self):
        ctx = self._build_context(SAMPLE_CLIENT, SAMPLE_METRICS, "reactivation")
        assert "/" in ctx["offer_expiry"]   # DD/MM/YYYY format


# ── 3. Template insight fallback ──────────────────────────────────────────────

class TestTemplateInsight:
    def setup_method(self):
        from src.agents.proposal_generator import _build_context, _template_insight
        self._build_context    = _build_context
        self._template_insight = _template_insight

    @pytest.mark.parametrize("opp_type", ALL_OPP_TYPES)
    def test_fallback_returns_non_empty_string(self, opp_type):
        ctx = self._build_context(SAMPLE_CLIENT, SAMPLE_METRICS, opp_type)
        insight = self._template_insight(ctx, opp_type, "Rationale text.")
        assert isinstance(insight, str) and len(insight) > 20

    @pytest.mark.parametrize("opp_type", ALL_OPP_TYPES)
    def test_fallback_contains_client_name(self, opp_type):
        ctx = self._build_context(SAMPLE_CLIENT, SAMPLE_METRICS, opp_type)
        insight = self._template_insight(ctx, opp_type, "")
        assert "Bella Cucina" in insight

    def test_unknown_type_falls_back_to_rationale(self):
        ctx = self._build_context(SAMPLE_CLIENT, SAMPLE_METRICS, "landing_page_optimization")
        insight = self._template_insight(ctx, "nonexistent", "My rationale.")
        assert "My rationale." in insight


# ── 4. LLM call (no API key → returns None) ───────────────────────────────────

class TestLLMCall:
    def test_returns_none_when_no_keys(self, monkeypatch):
        monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
        monkeypatch.setattr(config, "OPENAI_API_KEY", "")

        from src.agents import proposal_generator as pg
        monkeypatch.setattr(pg.config, "ANTHROPIC_API_KEY", "")
        monkeypatch.setattr(pg.config, "OPENAI_API_KEY", "")

        result = pg._call_llm("test prompt")
        assert result is None

    def test_prompt_builder_returns_string(self):
        from src.agents.proposal_generator import _build_context, _build_llm_prompt
        ctx = _build_context(SAMPLE_CLIENT, SAMPLE_METRICS, "landing_page_optimization")
        prompt = _build_llm_prompt(ctx, "landing_page_optimization", "Some rationale.")
        assert isinstance(prompt, str) and len(prompt) > 50

    def test_prompt_contains_client_name(self):
        from src.agents.proposal_generator import _build_context, _build_llm_prompt
        ctx = _build_context(SAMPLE_CLIENT, SAMPLE_METRICS, "email_automation")
        prompt = _build_llm_prompt(ctx, "email_automation", "")
        assert "Bella Cucina" in prompt


# ── 5 & 6. DB persistence + Markdown export ───────────────────────────────────

class TestProposalGeneration:
    """End-to-end test using a temporary in-memory DB."""

    @pytest.fixture(autouse=True)
    def _setup_temp_db(self, tmp_path, monkeypatch):
        """Redirect DB and exports to temp directories."""
        db_path       = tmp_path / "test.db"
        exports_dir   = tmp_path / "exports"
        proposals_dir = exports_dir / "proposals"
        proposals_dir.mkdir(parents=True)

        monkeypatch.setattr(config, "DB_PATH", db_path)

        # Patch PROPOSALS_DIR in proposal_generator
        import src.agents.proposal_generator as pg
        monkeypatch.setattr(pg, "PROPOSALS_DIR", proposals_dir)

        # Initialise schema
        import src.db.schema as schema
        monkeypatch.setattr(schema, "get_connection", lambda: __import__("sqlite3").connect(str(db_path)))

        # Re-init
        from src.db.schema import init_db
        # Monkey-patch get_connection to use our temp db
        import sqlite3
        real_conn = lambda: sqlite3.connect(str(db_path), check_same_thread=False)
        real_conn_with_factory = lambda: _make_conn(db_path)

        def _make_conn(p):
            import sqlite3 as _sq
            conn = _sq.connect(str(p), check_same_thread=False)
            conn.row_factory = _sq.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            return conn

        monkeypatch.setattr(schema, "get_connection", lambda: _make_conn(db_path))
        monkeypatch.setattr(pg, "get_connection", lambda: _make_conn(db_path))

        # Seed schema + one client + one opportunity
        schema.init_db()
        conn = _make_conn(db_path)
        now = datetime.now().isoformat()
        conn.execute(
            """INSERT INTO clients
               (id, name, industry, company_size, account_age_days,
                monthly_spend, contact_email, account_manager, is_demo_scenario)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (SAMPLE_CLIENT["id"], SAMPLE_CLIENT["name"], SAMPLE_CLIENT["industry"],
             SAMPLE_CLIENT["company_size"], SAMPLE_CLIENT["account_age_days"],
             SAMPLE_CLIENT["monthly_spend"], SAMPLE_CLIENT["contact_email"],
             SAMPLE_CLIENT["account_manager"], SAMPLE_CLIENT["is_demo_scenario"]),
        )
        self._opp_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO opportunities
               (id, client_id, opportunity_type, score, status, detected_at, updated_at)
               VALUES (?,?,?,?,?,?,?)""",
            (self._opp_id, SAMPLE_CLIENT["id"],
             "landing_page_optimization", 82.0, "detected", now, now),
        )
        conn.commit()
        conn.close()

        self._db_path       = db_path
        self._proposals_dir = proposals_dir
        self._make_conn     = _make_conn

    def _stub_data_sources(self, monkeypatch):
        """Stub all data source calls to return SAMPLE_METRICS."""
        from src.agents import proposal_generator as pg
        monkeypatch.setattr(pg.ga,             "get_latest_metrics",           lambda cid: SAMPLE_METRICS)
        monkeypatch.setattr(pg.meta_ads,       "get_latest_ad_metrics",        lambda cid: SAMPLE_METRICS)
        monkeypatch.setattr(pg.email_marketing,"get_latest_email_metrics",     lambda cid: SAMPLE_METRICS)
        monkeypatch.setattr(pg.seo,            "get_latest_seo_metrics",       lambda cid: SAMPLE_METRICS)
        monkeypatch.setattr(pg.crm,            "get_client",                   lambda cid: SAMPLE_CLIENT)
        monkeypatch.setattr(pg.crm,            "get_client_activity",          lambda cid: SAMPLE_METRICS)
        monkeypatch.setattr(pg,                "_call_llm",                    lambda p: None)

    def test_generate_returns_dict_with_proposal_id(self, monkeypatch):
        self._stub_data_sources(monkeypatch)
        from src.agents.proposal_generator import generate_proposal
        result = generate_proposal(self._opp_id, rationale="Test rationale.")
        assert "proposal_id" in result
        assert result["proposal_id"]

    def test_generate_creates_db_row(self, monkeypatch):
        self._stub_data_sources(monkeypatch)
        from src.agents.proposal_generator import generate_proposal
        result = generate_proposal(self._opp_id, rationale="Test rationale.")
        conn = self._make_conn(self._db_path)
        row = conn.execute(
            "SELECT * FROM proposals WHERE id=?", (result["proposal_id"],)
        ).fetchone()
        conn.close()
        assert row is not None
        assert row["status"] == "draft"
        assert row["client_id"] == SAMPLE_CLIENT["id"]

    def test_generate_updates_opportunity_status(self, monkeypatch):
        self._stub_data_sources(monkeypatch)
        from src.agents.proposal_generator import generate_proposal
        generate_proposal(self._opp_id, rationale="")
        conn = self._make_conn(self._db_path)
        opp = conn.execute(
            "SELECT status FROM opportunities WHERE id=?", (self._opp_id,)
        ).fetchone()
        conn.close()
        assert opp["status"] == "proposal_generated"

    def test_generate_creates_markdown_file(self, monkeypatch):
        self._stub_data_sources(monkeypatch)
        from src.agents.proposal_generator import generate_proposal
        result = generate_proposal(self._opp_id, rationale="")
        assert result["filepath"] is not None
        md_path = Path(result["filepath"])
        assert md_path.exists()
        assert md_path.suffix == ".md"

    def test_markdown_contains_proposal_id(self, monkeypatch):
        self._stub_data_sources(monkeypatch)
        from src.agents.proposal_generator import generate_proposal
        result = generate_proposal(self._opp_id, rationale="")
        content = Path(result["filepath"]).read_text(encoding="utf-8")
        assert result["proposal_id"] in content

    def test_markdown_contains_client_name(self, monkeypatch):
        self._stub_data_sources(monkeypatch)
        from src.agents.proposal_generator import generate_proposal
        result = generate_proposal(self._opp_id, rationale="")
        content = Path(result["filepath"]).read_text(encoding="utf-8")
        assert "Bella Cucina" in content

    def test_generate_idempotent_returns_existing(self, monkeypatch):
        """Calling generate_proposal twice returns the existing proposal."""
        self._stub_data_sources(monkeypatch)
        from src.agents.proposal_generator import generate_proposal
        r1 = generate_proposal(self._opp_id, rationale="")
        r2 = generate_proposal(self._opp_id, rationale="")
        assert r1["proposal_id"] == r2["proposal_id"]
        assert r2.get("already_existed") is True

    def test_generation_method_is_template_when_no_llm(self, monkeypatch):
        self._stub_data_sources(monkeypatch)
        from src.agents.proposal_generator import generate_proposal
        result = generate_proposal(self._opp_id, rationale="")
        assert result["generation_method"] == "template"


# ── 7. Approval workflow ──────────────────────────────────────────────────────

class TestApprovalWorkflow:
    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, monkeypatch):
        db_path = tmp_path / "workflow.db"
        monkeypatch.setattr(config, "DB_PATH", db_path)

        import src.db.schema as schema
        import src.agents.proposal_generator as pg
        import sqlite3

        def _make_conn(p=db_path):
            conn = sqlite3.connect(str(p), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            return conn

        monkeypatch.setattr(schema, "get_connection", _make_conn)
        monkeypatch.setattr(pg,     "get_connection", _make_conn)
        schema.init_db()

        now = datetime.now().isoformat()
        conn = _make_conn()
        self._client_id = "wf-client-001"
        self._opp_id    = str(uuid.uuid4())
        self._prop_id   = str(uuid.uuid4())

        conn.execute(
            "INSERT INTO clients (id,name,industry) VALUES (?,?,?)",
            (self._client_id, "Test Client", "Tech"),
        )
        conn.execute(
            "INSERT INTO opportunities (id,client_id,opportunity_type,score,status,detected_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (self._opp_id, self._client_id, "email_automation", 75.0, "proposal_generated", now, now),
        )
        conn.execute(
            "INSERT INTO proposals (id,opportunity_id,client_id,subject,body,suggested_price,status,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (self._prop_id, self._opp_id, self._client_id,
             "Test Subject", "Test body text.", 300.0, "draft", now, now),
        )
        conn.commit()
        conn.close()
        self._make_conn = _make_conn

    def _get_proposal(self):
        conn = self._make_conn()
        row = conn.execute("SELECT * FROM proposals WHERE id=?", (self._prop_id,)).fetchone()
        conn.close()
        return dict(row)

    def test_approve_sets_status_to_approved(self):
        from src.agents.proposal_generator import approve_proposal
        approve_proposal(self._prop_id, approved_by="test_user")
        p = self._get_proposal()
        assert p["status"] == "approved"
        assert p["approved_by"] == "test_user"

    def test_approve_returns_true(self):
        from src.agents.proposal_generator import approve_proposal
        result = approve_proposal(self._prop_id)
        assert result is True

    def test_reject_sets_status_to_rejected(self):
        from src.agents.proposal_generator import reject_proposal
        reject_proposal(self._prop_id, reason="Price too high")
        p = self._get_proposal()
        assert p["status"] == "rejected"

    def test_reject_resets_opportunity_to_detected(self):
        from src.agents.proposal_generator import reject_proposal
        import src.db.schema as schema
        reject_proposal(self._prop_id)
        conn = self._make_conn()
        opp = conn.execute("SELECT status FROM opportunities WHERE id=?", (self._opp_id,)).fetchone()
        conn.close()
        assert opp["status"] == "detected"

    def test_edit_updates_body(self):
        from src.agents.proposal_generator import update_proposal_body
        update_proposal_body(self._prop_id, "Updated body content.")
        p = self._get_proposal()
        assert p["body"] == "Updated body content."

    def test_edit_does_not_change_status(self):
        from src.agents.proposal_generator import update_proposal_body
        update_proposal_body(self._prop_id, "New content.")
        p = self._get_proposal()
        assert p["status"] == "draft"


# ── 8. generate_proposals_for_all ────────────────────────────────────────────

class TestGenerateAll:
    def test_skips_low_score_opportunities(self, monkeypatch, tmp_path):
        """Opportunities below min_score threshold should not generate proposals."""
        db_path = tmp_path / "gen_all.db"
        monkeypatch.setattr(config, "DB_PATH", db_path)

        import sqlite3
        import src.db.schema as schema
        import src.agents.proposal_generator as pg

        def _make_conn(p=db_path):
            conn = sqlite3.connect(str(p), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            return conn

        monkeypatch.setattr(schema, "get_connection", _make_conn)
        monkeypatch.setattr(pg,     "get_connection", _make_conn)
        schema.init_db()

        now = datetime.now().isoformat()
        conn = _make_conn()
        conn.execute("INSERT INTO clients (id,name,industry) VALUES ('c1','Low Score Client','Retail')")
        low_opp_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO opportunities (id,client_id,opportunity_type,score,status,detected_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (low_opp_id, "c1", "email_automation", 45.0, "detected", now, now),
        )
        conn.commit()
        conn.close()

        results = pg.generate_proposals_for_all(min_score=70.0)
        assert results == []   # low score → no proposal generated


# ── 9. get_all_proposals structure ───────────────────────────────────────────

class TestGetAllProposals:
    def test_returns_list(self, tmp_path, monkeypatch):
        db_path = tmp_path / "gap.db"
        monkeypatch.setattr(config, "DB_PATH", db_path)

        import sqlite3
        import src.db.schema as schema
        import src.agents.proposal_generator as pg

        def _make_conn(p=db_path):
            conn = sqlite3.connect(str(p), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            return conn

        monkeypatch.setattr(schema, "get_connection", _make_conn)
        monkeypatch.setattr(pg,     "get_connection", _make_conn)
        schema.init_db()

        result = pg.get_all_proposals()
        assert isinstance(result, list)

    def test_proposals_have_required_keys(self, tmp_path, monkeypatch):
        db_path = tmp_path / "gapkeys.db"
        monkeypatch.setattr(config, "DB_PATH", db_path)

        import sqlite3
        import src.db.schema as schema
        import src.agents.proposal_generator as pg

        def _make_conn(p=db_path):
            conn = sqlite3.connect(str(p), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            return conn

        monkeypatch.setattr(schema, "get_connection", _make_conn)
        monkeypatch.setattr(pg,     "get_connection", _make_conn)
        schema.init_db()

        # Seed a proposal
        now = datetime.now().isoformat()
        cid = "struct-client"
        oid = str(uuid.uuid4())
        pid = str(uuid.uuid4())
        conn = _make_conn()
        conn.execute("INSERT INTO clients (id,name,industry) VALUES (?,?,?)", (cid,"Struct Client","Finance"))
        conn.execute(
            "INSERT INTO opportunities (id,client_id,opportunity_type,score,status,detected_at,updated_at) VALUES (?,?,?,?,?,?,?)",
            (oid,cid,"reactivation",88.0,"proposal_generated",now,now),
        )
        conn.execute(
            "INSERT INTO proposals (id,opportunity_id,client_id,subject,body,suggested_price,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (pid,oid,cid,"Subj","Body",150.0,"draft",now,now),
        )
        conn.commit()
        conn.close()

        proposals = pg.get_all_proposals()
        assert len(proposals) == 1
        p = proposals[0]
        for key in ("id","client_id","client_name","industry","opportunity_type","score",
                    "subject","body","suggested_price","status"):
            assert key in p, f"Missing key: {key}"


# ── 10. GOVERNANCE.md ─────────────────────────────────────────────────────────

class TestGovernanceDoc:
    @pytest.fixture(autouse=True)
    def _governance_path(self):
        self._path = Path(__file__).parent.parent / "GOVERNANCE.md"

    def test_governance_file_exists(self):
        assert self._path.exists(), "GOVERNANCE.md not found in project root"

    def test_governance_has_autonomy_tiers(self):
        content = self._path.read_text(encoding="utf-8")
        assert "Autonomy Tiers" in content

    def test_governance_has_escalation_rules(self):
        content = self._path.read_text(encoding="utf-8")
        assert "Escalation" in content

    def test_governance_has_prohibited_actions(self):
        content = self._path.read_text(encoding="utf-8")
        assert "Prohibited" in content

    def test_governance_has_audit_log(self):
        content = self._path.read_text(encoding="utf-8")
        assert "Audit" in content

    def test_governance_has_thresholds(self):
        content = self._path.read_text(encoding="utf-8")
        assert "MIN_SCORE_FOR_PROPOSAL_GENERATION" in content
