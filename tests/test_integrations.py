"""
Coverage for the paths that only run outside DEMO_MODE (SendGrid, Slack,
Telegram, Stripe, HubSpot, WhatsApp, LLM providers) and for the CLI scripts.

Nothing here touches the network: HTTP calls are replaced with recorders and
the provider SDKs with fake modules injected into sys.modules.
"""

import json
import sqlite3
import sys
import types
import urllib.request
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
import pytest

import config


@pytest.fixture()
def prod(tmp_path, monkeypatch):
    """Non-demo mode with fake credentials, temp DB/logs and one proposal."""
    db_file, logs = tmp_path / "prod.db", tmp_path / "logs"
    logs.mkdir()
    monkeypatch.setattr(config, "DB_PATH", db_file)
    monkeypatch.setattr(config, "LOGS_DIR", logs)
    monkeypatch.setattr(config, "DEMO_MODE", False)
    for name, value in {
        "ANTHROPIC_API_KEY": "", "OPENAI_API_KEY": "", "STRIPE_SECRET_KEY": "",
        "SENDGRID_API_KEY": "sg-test", "SLACK_WEBHOOK_URL": "https://hooks.invalid/x",
        "TELEGRAM_BOT_TOKEN": "bot-test", "TELEGRAM_CHAT_ID": "1", "HUBSPOT_API_KEY": "hs-test",
        "LLM_PROVIDER": "auto",
    }.items():
        monkeypatch.setattr(config, name, value)

    from src.agents import feedback_loop, negotiator, payment_link
    from src.integrations import hubspot, whatsapp
    monkeypatch.setattr(negotiator, "NEGOTIATION_LOG", logs / "neg.jsonl")
    monkeypatch.setattr(payment_link, "PAYMENT_LINKS_LOG", logs / "pay.jsonl")
    monkeypatch.setattr(feedback_loop, "FEEDBACK_LOG", logs / "fb.jsonl")
    monkeypatch.setattr(hubspot, "CRM_SYNC_LOG", logs / "crm.jsonl")
    monkeypatch.setattr(whatsapp, "WA_LOG", logs / "wa.jsonl")

    from src.db.schema import init_db, migrate_db
    init_db()
    migrate_db()
    conn = sqlite3.connect(db_file)
    conn.execute("INSERT INTO clients (id, name, industry, contact_email, account_manager) "
                 "VALUES ('c1','Acme','retail','a@demo.local','Dana Reyes')")
    conn.execute("INSERT INTO opportunities (id, client_id, opportunity_type, score) "
                 "VALUES ('o1','c1','seo_content',80)")
    conn.execute("INSERT INTO proposals (id, opportunity_id, client_id, subject, body, suggested_price, status) "
                 "VALUES ('p1','o1','c1','Subject','Body',500,'approved')")
    conn.commit()
    conn.close()
    return db_file


class Recorder:
    """Stands in for httpx.post and remembers every request."""

    def __init__(self, status: int = 200, error: Exception | None = None):
        self.calls: list[NS] = []
        self.status, self.error = status, error

    def __call__(self, url, **kwargs):
        self.calls.append(NS(url=url, **kwargs))
        if self.error:
            raise self.error
        return NS(status_code=self.status, raise_for_status=lambda: None)


def _fake_module(monkeypatch, name: str, **attrs) -> None:
    module = types.ModuleType(name)
    module.__dict__.update(attrs)
    monkeypatch.setitem(sys.modules, name, module)


def _fake_llms(monkeypatch, reply: str | Exception):
    """Install fake `anthropic` and `openai` SDKs that answer with `reply`."""
    def answer():
        if isinstance(reply, Exception):
            raise reply
        return reply

    class Anthropic:
        def __init__(self, **_):
            self.messages = NS(create=lambda **_: NS(content=[NS(text=answer())]))

    class OpenAI:
        def __init__(self, **_):
            create = lambda **_: NS(choices=[NS(message=NS(content=answer()))])  # noqa: E731
            self.chat = NS(completions=NS(create=create))

    _fake_module(monkeypatch, "anthropic", Anthropic=Anthropic)
    _fake_module(monkeypatch, "openai", OpenAI=OpenAI)


# ── Alerts: Slack and Telegram ────────────────────────────────────────────────

OPPORTUNITY = {"client_id": "c1", "client_name": "Acme", "score": 85, "suggested_price": 100, "label": "SEO"}


@pytest.mark.parametrize("status,ok", [(200, True), (500, False)])
def test_alerts_are_posted_to_both_channels(prod, monkeypatch, status, ok):
    from src.agents.alerts import dispatch
    post = Recorder(status)
    monkeypatch.setattr(httpx, "post", post)

    record = dispatch([OPPORTUNITY], channel="both")[0]

    assert (record["slack_sent"], record["telegram_sent"]) == (ok, ok)
    assert post.calls[0].url == "https://hooks.invalid/x"
    assert "bot-test" in post.calls[1].url


def test_alert_network_errors_do_not_raise(prod, monkeypatch):
    from src.agents.alerts import dispatch
    monkeypatch.setattr(httpx, "post", Recorder(error=httpx.ConnectError("down")))
    record = dispatch([OPPORTUNITY], channel="both")[0]
    assert (record["slack_sent"], record["telegram_sent"]) == (False, False)


# ── Email: SendGrid ───────────────────────────────────────────────────────────

def test_sendgrid_send_with_bcc(prod, monkeypatch):
    sent = []

    class Mail:
        def __init__(self, **kwargs):
            self.kwargs, self.bcc = kwargs, None

        def add_bcc(self, address):
            self.bcc = address

    class Client:
        def __init__(self, key):
            assert key == "sg-test"

        def send(self, message):
            sent.append(message)
            return NS(status_code=202)

    _fake_module(monkeypatch, "sendgrid", SendGridAPIClient=Client)
    _fake_module(monkeypatch, "sendgrid.helpers")
    _fake_module(monkeypatch, "sendgrid.helpers.mail", Mail=Mail)

    from src.agents.email_sender import send_proposal_email
    send_proposal_email("p1")

    assert sent[0].kwargs["to_emails"] == "a@demo.local"
    assert sent[0].bcc == "dana.reyes@agency.demo"


def test_sendgrid_failure_leaves_proposal_unsent(prod, monkeypatch):
    class Client:
        def __init__(self, _key):
            raise RuntimeError("bad key")

    _fake_module(monkeypatch, "sendgrid", SendGridAPIClient=Client)
    _fake_module(monkeypatch, "sendgrid.helpers")
    _fake_module(monkeypatch, "sendgrid.helpers.mail", Mail=lambda **_: NS(add_bcc=lambda _: None))

    from src.agents.email_sender import send_proposal_email
    with pytest.raises(RuntimeError):
        send_proposal_email("p1")
    status = sqlite3.connect(prod).execute("SELECT status FROM proposals WHERE id='p1'").fetchone()[0]
    assert status == "approved"


# ── CRM and WhatsApp ──────────────────────────────────────────────────────────

def test_hubspot_deal_and_note(prod, monkeypatch):
    post = Recorder()
    monkeypatch.setattr(httpx, "post", post)
    from src.integrations.hubspot import create_deal, get_sync_log, log_activity

    create_deal("c1", "p1", 500.0, "seo_content")
    log_activity("c1", "note")

    assert [c.url.rsplit("/", 1)[1] for c in post.calls] == ["deals", "notes"]
    assert post.calls[0].headers["Authorization"] == "Bearer hs-test"
    assert {row["demo_mode"] for row in get_sync_log()} == {0}


def test_whatsapp_paths(prod, monkeypatch):
    post = Recorder()
    monkeypatch.setattr(httpx, "post", post)
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123")
    from src.integrations import whatsapp as wa

    assert wa.send_whatsapp_proposal("c1", "nope")["reason"] == "proposal or client not found"
    assert "not opted in" in wa.send_whatsapp_proposal("c1", "p1")["reason"]
    sqlite3_conn = sqlite3.connect(prod)
    sqlite3_conn.execute("UPDATE clients SET whatsapp_opted_in=1")
    sqlite3_conn.commit()
    sqlite3_conn.close()
    assert wa.send_whatsapp_proposal("c1", "p1")["reason"] == "no WhatsApp number on record"

    assert wa.set_channel_preference("c1", "whatsapp", "+15550001111") is True
    assert wa.send_whatsapp_proposal("c1", "p1")["ok"] is True
    assert "/123/messages" in post.calls[0].url
    assert wa.get_opted_in_clients()[0]["whatsapp_number"] == "+15550001111"


# ── Slack escalations ─────────────────────────────────────────────────────────

def test_churn_and_escalation_post_to_slack(prod, monkeypatch):
    posted = []
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout: posted.append(json.loads(req.data)))
    from src.agents.churn_escalation import _send_slack_alert
    from src.agents.feedback_loop import record_client_reply

    _send_slack_alert({"message_to_manager": "churn!"})
    record_client_reply("p1", "escalated", notes="angry")

    assert posted[0]["text"] == "churn!"
    assert "ESCALATION" in posted[1]["text"]


def test_churn_slack_failure_is_swallowed(prod, monkeypatch):
    def fail(*_a, **_kw):
        raise OSError("offline")
    monkeypatch.setattr(urllib.request, "urlopen", fail)
    from src.agents.churn_escalation import _send_slack_alert
    _send_slack_alert({"message_to_manager": "x"})


# ── Stripe ────────────────────────────────────────────────────────────────────

def test_stripe_link(prod, monkeypatch):
    amounts = []
    monkeypatch.setattr(config, "STRIPE_SECRET_KEY", "sk-test")
    _fake_module(
        monkeypatch, "stripe",
        Price=NS(create=lambda **kw: amounts.append(kw["unit_amount"]) or NS(id="price_1")),
        PaymentLink=NS(create=lambda **_: NS(id="plink_real", url="https://pay.invalid/1")),
    )
    from src.agents import payment_link as pl

    result = pl.create_payment_link("p1")

    assert result["simulated"] is False and amounts == [50000]
    assert pl.get_payment_link("p1") == "https://pay.invalid/1"
    assert pl.create_payment_link("p1")["already_existed"] is True
    assert pl.record_payment_received("p1", "cs_1") is True
    assert pl.list_payment_links()[0]["status"] == "paid"


def test_stripe_failure_falls_back_to_demo_link(prod, monkeypatch):
    monkeypatch.setattr(config, "STRIPE_SECRET_KEY", "sk-test")

    def boom(**_):
        raise RuntimeError("stripe down")
    _fake_module(monkeypatch, "stripe", Price=NS(create=boom))
    from src.agents.payment_link import create_payment_link
    assert create_payment_link("p1")["simulated"] is True


# ── LLM providers ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("provider", ["anthropic", "openai"])
def test_negotiator_and_proposals_use_the_llm(prod, monkeypatch, provider):
    _fake_llms(monkeypatch, " LLM text ")
    monkeypatch.setattr(config, f"{provider.upper()}_API_KEY", "key")
    from src.agents import negotiator, proposal_generator

    assert negotiator._build_agent_message(1, "Acme", "retail", "seo_content", 500, 450, 0.1) == "LLM text"
    assert proposal_generator._call_llm("prompt") == "LLM text"


@pytest.mark.parametrize("provider", ["anthropic", "openai"])
def test_llm_failures_fall_back_to_templates(prod, monkeypatch, provider):
    _fake_llms(monkeypatch, RuntimeError("rate limited"))
    monkeypatch.setattr(config, f"{provider.upper()}_API_KEY", "key")
    from src.agents import negotiator, proposal_generator

    message = negotiator._build_agent_message(1, "Acme", "retail", "seo_content", 500, 450, 0.1)
    assert "Dear Acme" in message
    assert proposal_generator._call_llm("prompt") is None


@pytest.mark.parametrize("reply,expected", [
    ("counter_offer", "counter_offer"),
    ("banana", "needs_info"),                     # invalid label → keyword fallback
    (RuntimeError("down"), "needs_info"),
])
def test_negotiator_llm_intent(prod, monkeypatch, reply, expected):
    _fake_llms(monkeypatch, reply)
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "key")
    from src.agents.negotiator import _extract_intent
    assert _extract_intent("hmm") == expected


@pytest.mark.parametrize("provider", ["anthropic", "openai"])
def test_signal_extraction_with_llm(prod, monkeypatch, provider):
    _fake_llms(monkeypatch, json.dumps({"sentiment": -0.5, "churn_risk": True, "summary": "unhappy"}))
    monkeypatch.setattr(config, "LLM_PROVIDER", provider)
    monkeypatch.setattr(config, f"{provider.upper()}_API_KEY", "key")
    from src.nlp.signal_extractor import aggregate_signals, extract_signals

    result = extract_signals("we are leaving")

    assert (result["extraction_mode"], result["churn_risk"], result["sentiment"]) == ("llm", 1, -0.5)
    assert aggregate_signals([result])["churn_risk"] == 1


def test_signal_extraction_bad_llm_output_uses_keywords(prod, monkeypatch):
    _fake_llms(monkeypatch, "not json")
    monkeypatch.setattr(config, "LLM_PROVIDER", "anthropic")
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "key")
    from src.nlp.signal_extractor import extract_signals
    assert extract_signals("hello")["extraction_mode"] == "keyword"
    monkeypatch.setattr(config, "LLM_PROVIDER", "local")
    assert extract_signals("hello")["extraction_mode"] == "keyword"


# ── CLI scripts and synthetic data ────────────────────────────────────────────

@pytest.fixture()
def seeded(tmp_path, monkeypatch):
    """A small freshly seeded database, isolated from data/."""
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "seed.db")
    monkeypatch.setattr(config, "SYNTHETIC_DIR", tmp_path / "synthetic")
    monkeypatch.setattr(config, "SYNTHETIC_CLIENT_COUNT", 3)
    from scripts.seed_db import seed
    from src.agents import scorer
    scorer.invalidate_cache()
    seed(reset=False)
    yield tmp_path
    scorer.invalidate_cache()


def test_seed_with_reset_is_repeatable(seeded):
    from scripts.seed_db import seed
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("INSERT INTO churn_escalation_log (id, client_id) VALUES ('e1','demo-001')")
    conn.commit()

    seed(reset=True)       # used to fail: child rows still referenced clients

    assert conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0] == 8
    assert conn.execute("SELECT COUNT(*) FROM churn_escalation_log").fetchone()[0] == 0
    assert (seeded / "synthetic" / "clients.json").exists()
    conn.close()


@pytest.mark.parametrize("argv,expected", [
    ([], "OPPORTUNITY"),
    (["--demo-only", "--save"], "Persisted"),
    (["--client", "demo-001"], "Scoring client"),
    (["--client", "missing"], "No opportunities detected"),
])
def test_run_detection_cli(seeded, monkeypatch, capsys, argv, expected):
    from scripts import run_detection
    monkeypatch.setattr(sys, "argv", ["run_detection.py", *argv])
    run_detection.main()
    assert expected.lower() in capsys.readouterr().out.lower()


def test_data_source_histories(seeded):
    from src.data_sources import email_marketing, google_analytics, meta_ads, seo
    for fetch in (google_analytics.get_client_metrics, meta_ads.get_client_ad_metrics,
                  seo.get_seo_metrics, email_marketing.get_email_metrics):
        rows = fetch("demo-001", days=5)
        assert len(rows) == 5 and rows[0]["date"] > rows[-1]["date"]
    assert email_marketing.get_client_emails("demo-001")
