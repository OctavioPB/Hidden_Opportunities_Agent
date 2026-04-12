"""
Sprint 2 tests.

1. Alert formatter — Slack and Telegram format output structure.
2. Dispatcher — demo mode writes to log file, no network calls.
3. Daily job — dry-run returns correct summary structure.
4. Accuracy — labeled dataset achieves >= 80% recall.
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import config

# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_OPP = {
    "client_id":        "demo-001",
    "client_name":      "Bella Cucina Restaurant",
    "industry":         "Restaurant",
    "opportunity_type": "landing_page_optimization",
    "label":            "Landing Page Optimization",
    "score":            82.0,
    "suggested_price":  350,
    "rationale":        "CTR is 5.2% but bounce rate is 78%.",
    "triggered_signals": ["high_ctr", "high_bounce", "low_pages_per_session"],
    "is_demo_scenario": 1,
    "_metrics": {
        "ctr": 0.052, "bounce_rate": 0.78, "pages_per_session": 1.4,
        "days_inactive": 5,
    },
}


# ── Alert formatter ───────────────────────────────────────────────────────────

def test_slack_format_returns_dict():
    from src.agents.alerts import format_slack_message
    payload = format_slack_message(SAMPLE_OPP)
    assert isinstance(payload, dict)


def test_slack_format_has_blocks():
    from src.agents.alerts import format_slack_message
    payload = format_slack_message(SAMPLE_OPP)
    assert "blocks" in payload
    assert len(payload["blocks"]) > 0


def test_slack_format_has_text_fallback():
    from src.agents.alerts import format_slack_message
    payload = format_slack_message(SAMPLE_OPP)
    assert "text" in payload
    assert "Bella Cucina" in payload["text"]


def test_slack_format_has_production_note():
    from src.agents.alerts import format_slack_message
    payload = format_slack_message(SAMPLE_OPP)
    assert "_production_integration" in payload
    assert "webhook" in payload["_production_integration"].lower()


def test_telegram_format_returns_string():
    from src.agents.alerts import format_telegram_message
    text = format_telegram_message(SAMPLE_OPP)
    assert isinstance(text, str)


def test_telegram_format_contains_client_name():
    from src.agents.alerts import format_telegram_message
    text = format_telegram_message(SAMPLE_OPP)
    assert "Bella Cucina" in text


def test_telegram_format_contains_price():
    from src.agents.alerts import format_telegram_message
    text = format_telegram_message(SAMPLE_OPP)
    assert "350" in text


def test_telegram_format_is_html():
    from src.agents.alerts import format_telegram_message
    text = format_telegram_message(SAMPLE_OPP)
    assert "<b>" in text


# ── Key metrics line ──────────────────────────────────────────────────────────

def test_key_metrics_line_renders_signals():
    from src.agents.alerts import _key_metrics_line
    line = _key_metrics_line(SAMPLE_OPP)
    assert "CTR" in line
    assert "Bounce" in line


def test_key_metrics_line_fallback():
    from src.agents.alerts import _key_metrics_line
    opp_no_signals = {**SAMPLE_OPP, "triggered_signals": [], "_metrics": {}}
    line = _key_metrics_line(opp_no_signals)
    assert line  # should not be empty


# ── Dispatcher — demo mode ────────────────────────────────────────────────────

def test_dispatch_demo_writes_to_log(tmp_path, monkeypatch):
    """In demo mode, dispatch must write to the log file and make no network calls."""
    import config as cfg
    monkeypatch.setattr(cfg, "DEMO_MODE", True)
    monkeypatch.setattr(cfg, "LOGS_DIR", tmp_path)

    from src.agents import alerts
    monkeypatch.setattr(alerts, "config", cfg)

    records = alerts.dispatch([SAMPLE_OPP])
    assert len(records) == 1

    log_path = tmp_path / "alerts.jsonl"
    assert log_path.exists()
    line = json.loads(log_path.read_text().strip())
    assert line["client_id"] == "demo-001"
    assert line["opportunity_type"] == "landing_page_optimization"


def test_dispatch_returns_list():
    from src.agents.alerts import dispatch
    records = dispatch([SAMPLE_OPP])
    assert isinstance(records, list)
    assert len(records) == 1


def test_dispatch_record_has_required_keys():
    from src.agents.alerts import dispatch
    records = dispatch([SAMPLE_OPP])
    record = records[0]
    for key in ("timestamp", "client_id", "opportunity_type", "score", "slack_payload"):
        assert key in record, f"Missing key: {key}"


def test_dispatch_multiple_opportunities():
    from src.agents.alerts import dispatch
    opps = [SAMPLE_OPP, {**SAMPLE_OPP, "client_id": "demo-002", "client_name": "LexGroup Law Firm"}]
    records = dispatch(opps)
    assert len(records) == 2


# ── Alert log reader ──────────────────────────────────────────────────────────

def test_load_alert_log_returns_list():
    from src.agents.alerts import load_alert_log
    result = load_alert_log()
    assert isinstance(result, list)


# ── Daily job — dry run ───────────────────────────────────────────────────────

def test_daily_job_dry_run():
    """Dry run should return a valid summary without writing to DB or dispatching."""
    from scripts.daily_job import run
    summary = run(dry_run=True, demo_only=True)

    assert "clients_scanned"        in summary
    assert "opportunities_found"    in summary
    assert "new_in_db"              in summary
    assert "alerts_dispatched"      in summary
    assert summary["dry_run"]       is True
    assert summary["new_in_db"]     == 0
    assert summary["alerts_dispatched"] == 0


def test_daily_job_finds_demo_opportunities():
    from scripts.daily_job import run
    summary = run(dry_run=True, demo_only=True)
    assert summary["opportunities_found"] >= 5  # at least one per demo client


# ── Accuracy validation ───────────────────────────────────────────────────────

def test_accuracy_meets_80_percent_recall():
    """Sprint 2 target: recall >= 80% on the labeled test dataset."""
    import json
    from src.agents.rules import evaluate

    labeled_path = Path(__file__).parent.parent / "data" / "synthetic" / "labeled_test_dataset.json"
    cases = json.loads(labeled_path.read_text())

    tp = fp = fn = 0
    for case in cases:
        detected = {r.opportunity_type for r in evaluate(case["metrics"])}
        expected = set(case["expected_opportunities"])
        tp += len(detected & expected)
        fp += len(detected - expected)
        fn += len(expected - detected)

    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    assert recall >= 0.80, (
        f"Recall {recall:.1%} is below the 80% Sprint 2 target. "
        f"TP={tp}, FP={fp}, FN={fn}"
    )


def test_accuracy_precision_above_60_percent():
    """Precision should be reasonable — too many false positives wastes team time."""
    import json
    from src.agents.rules import evaluate

    labeled_path = Path(__file__).parent.parent / "data" / "synthetic" / "labeled_test_dataset.json"
    cases = json.loads(labeled_path.read_text())

    tp = fp = 0
    for case in cases:
        detected = {r.opportunity_type for r in evaluate(case["metrics"])}
        expected = set(case["expected_opportunities"])
        tp += len(detected & expected)
        fp += len(detected - expected)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    assert precision >= 0.60, (
        f"Precision {precision:.1%} is below 60%. Too many false positives. "
        f"TP={tp}, FP={fp}"
    )
