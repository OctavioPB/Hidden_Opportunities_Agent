"""
Sprint 2 — Alert Formatter and Dispatcher.

Formats opportunity results into Slack-style messages and dispatches them.

DEMO MODE  → writes alerts to logs/alerts.jsonl and returns them as dicts.
             No external network calls are made.
PRODUCTION → POSTs to Slack Incoming Webhook or Telegram Bot API.
             Endpoint (Slack):    POST https://hooks.slack.com/services/...
             Endpoint (Telegram): POST https://api.telegram.org/bot{TOKEN}/sendMessage
             Auth: webhook URL (Slack) or bot token (Telegram) in .env
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

import config

logger = logging.getLogger(__name__)

# ── Score thresholds ──────────────────────────────────────────────────────────
_HIGH   = 80
_MEDIUM = 60

_PRODUCTION_NOTE_SLACK = (
    "Production: POST to Slack Incoming Webhook "
    "(https://hooks.slack.com/services/...) with JSON payload. "
    "Configured via SLACK_WEBHOOK_URL in .env."
)
_PRODUCTION_NOTE_TELEGRAM = (
    "Production: POST to Telegram Bot API "
    "(https://api.telegram.org/bot{TOKEN}/sendMessage). "
    "Configured via TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID in .env."
)


# ── Formatting ────────────────────────────────────────────────────────────────

def _confidence_label(score: float) -> str:
    if score >= _HIGH:
        return f"HIGH ({score:.0f}%)"
    if score >= _MEDIUM:
        return f"MEDIUM ({score:.0f}%)"
    return f"LOW ({score:.0f}%)"


def _score_emoji(score: float) -> str:
    if score >= _HIGH:
        return ":red_circle:"
    if score >= _MEDIUM:
        return ":large_yellow_circle:"
    return ":white_circle:"


def _key_metrics_line(opportunity: dict) -> str:
    """Build the 'Data:' line from triggered signals."""
    signals = opportunity.get("triggered_signals", [])
    parts = []
    m = opportunity.get("_metrics", {})

    signal_map = {
        "high_ctr":                 lambda: f"CTR {m.get('ctr', 0):.1%}",
        "high_bounce":              lambda: f"Bounce {m.get('bounce_rate', 0):.0%}",
        "low_pages_per_session":    lambda: f"Pages/session {m.get('pages_per_session', 0):.1f}",
        "very_high_ctr":            lambda: f"CTR {m.get('ctr', 0):.1%}",
        "very_low_conversion":      lambda: f"Conv {m.get('conversion_rate', 0):.2%}",
        "low_conversion":           lambda: f"Conv {m.get('conversion_rate', 0):.2%}",
        "medium_organic_traffic":   lambda: f"Organic {m.get('organic_traffic', 0):,}/mo",
        "weak_keyword_coverage":    lambda: f"Keywords {m.get('keyword_rankings', 0)}",
        "high_ad_spend":            lambda: f"Ad spend ~${m.get('ad_spend', 0) * 30:,.0f}/mo",
        "weak_roas":                lambda: f"ROAS {m.get('roas', 0):.1f}x",
        "excellent_roas":           lambda: f"ROAS {m.get('roas', 0):.1f}x",
        "low_ad_spend":             lambda: f"Ad spend ~${m.get('ad_spend', 0) * 30:,.0f}/mo",
        "low_email_open_rate":      lambda: f"Open rate {m.get('email_open_rate', 0):.1%}",
        "high_days_inactive":       lambda: f"Inactive {m.get('days_inactive', 0)} days",
    }
    for sig in signals:
        if sig in signal_map:
            parts.append(signal_map[sig]())

    return " | ".join(parts) if parts else "See dashboard for details"


def format_slack_message(opportunity: dict) -> dict:
    """
    Format a single detected opportunity as a Slack Block Kit message.

    Returns the Slack API payload dict (blocks + text fallback).
    In production this dict is POSTed directly to the webhook URL.
    """
    score  = opportunity.get("score", 0)
    emoji  = _score_emoji(score)
    conf   = _confidence_label(score)
    name   = opportunity.get("client_name", "Unknown")
    label  = opportunity.get("label", opportunity.get("opportunity_type", ""))
    price  = opportunity.get("suggested_price", 0)
    ratio  = opportunity.get("rationale", "")
    indust = opportunity.get("industry", "")
    metrics_line = _key_metrics_line(opportunity)

    text_fallback = (
        f"[Client: {name}] Opportunity: {label} (confidence: {conf}) | "
        f"Data: {metrics_line} | Suggested action: Offer {label} for ${price:,.0f}"
    )

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{emoji}  New Opportunity Detected"}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Client:*\n{name} ({indust})"},
                {"type": "mrkdwn", "text": f"*Opportunity:*\n{label}"},
                {"type": "mrkdwn", "text": f"*Confidence:*\n{conf}"},
                {"type": "mrkdwn", "text": f"*Suggested Price:*\n${price:,.0f}"},
            ]
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Data:* {metrics_line}"}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Rationale:* {ratio}"}
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View Dashboard"},
                    "style": "primary",
                    "url": "http://localhost:8501"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Generate Proposal"},
                    "action_id": f"generate_proposal_{opportunity.get('client_id', '')}",
                }
            ]
        },
        {"type": "divider"}
    ]

    return {
        "text": text_fallback,
        "blocks": blocks,
        "_production_integration": _PRODUCTION_NOTE_SLACK,
    }


def format_telegram_message(opportunity: dict) -> str:
    """
    Format a single opportunity as a Telegram HTML message string.
    In production this string is sent as the 'text' param with parse_mode=HTML.
    """
    score  = opportunity.get("score", 0)
    conf   = _confidence_label(score)
    name   = opportunity.get("client_name", "Unknown")
    label  = opportunity.get("label", opportunity.get("opportunity_type", ""))
    price  = opportunity.get("suggested_price", 0)
    ratio  = opportunity.get("rationale", "")
    metrics_line = _key_metrics_line(opportunity)

    return (
        f"<b>New Opportunity Detected</b>\n\n"
        f"<b>Client:</b> {name}\n"
        f"<b>Opportunity:</b> {label}\n"
        f"<b>Confidence:</b> {conf}\n"
        f"<b>Suggested Price:</b> ${price:,.0f}\n\n"
        f"<b>Data:</b> {metrics_line}\n\n"
        f"<i>{ratio}</i>\n\n"
        f"<a href='http://localhost:8501'>View Dashboard</a>"
    )


# ── Dispatch ──────────────────────────────────────────────────────────────────

def _log_alert(alert_record: dict) -> None:
    """Append alert to the demo log file (JSONL format)."""
    log_path = config.LOGS_DIR / "alerts.jsonl"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(alert_record, default=str) + "\n")


def _dispatch_real_slack(payload: dict) -> bool:
    """POST to real Slack webhook. Only called when DEMO_MODE=false."""
    import httpx
    try:
        resp = httpx.post(config.SLACK_WEBHOOK_URL, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"Slack dispatch failed: {e}")
        return False


def _dispatch_real_telegram(text: str) -> bool:
    """POST to real Telegram Bot API. Only called when DEMO_MODE=false."""
    import httpx
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = httpx.post(url, json={
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
        }, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"Telegram dispatch failed: {e}")
        return False


def dispatch(opportunities: list[dict], channel: str = "slack") -> list[dict]:
    """
    Dispatch alerts for a list of detected opportunities.

    Args:
        opportunities: List of opportunity dicts from scorer.score_all_clients()
        channel: 'slack' | 'telegram' | 'both'

    Returns:
        List of dispatched alert records (always returned, even in demo mode).

    In DEMO MODE:  alerts are written to logs/alerts.jsonl — no network calls.
    In PRODUCTION: alerts are POSTed to the configured webhook/bot.
    """
    dispatched = []
    now = datetime.now().isoformat()

    for opp in opportunities:
        slack_payload = format_slack_message(opp)
        telegram_text = format_telegram_message(opp)

        alert_record = {
            "timestamp":        now,
            "client_id":        opp.get("client_id"),
            "client_name":      opp.get("client_name"),
            "opportunity_type": opp.get("opportunity_type"),
            "label":            opp.get("label"),
            "score":            opp.get("score"),
            "suggested_price":  opp.get("suggested_price"),
            "slack_payload":    slack_payload,
            "telegram_text":    telegram_text,
            "demo_mode":        config.DEMO_MODE,
            "_production_integration": {
                "slack":    _PRODUCTION_NOTE_SLACK,
                "telegram": _PRODUCTION_NOTE_TELEGRAM,
            },
        }

        if config.DEMO_MODE:
            _log_alert(alert_record)
        else:
            if channel in ("slack", "both") and config.SLACK_WEBHOOK_URL:
                alert_record["slack_sent"] = _dispatch_real_slack(slack_payload)
            if channel in ("telegram", "both") and config.TELEGRAM_BOT_TOKEN:
                alert_record["telegram_sent"] = _dispatch_real_telegram(telegram_text)

        dispatched.append(alert_record)

    return dispatched


def load_alert_log() -> list[dict]:
    """Load all previously dispatched alerts from the log file."""
    log_path = config.LOGS_DIR / "alerts.jsonl"
    if not log_path.exists():
        return []
    records = []
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records
