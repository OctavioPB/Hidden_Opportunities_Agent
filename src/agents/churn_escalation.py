"""
Feature 3 — Churn Prevention Escalation Engine.

Scans text_signals for clients with active churn_risk or urgency_signal flags,
deduplicates against a 7-day window, and escalates to the account manager.

DEMO MODE  → escalation logged to logs/churn_escalations.jsonl; no Slack sent.
PRODUCTION → POSTs a Slack DM + creates a retention proposal draft.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta

import config
from src.db.schema import get_connection

CHURN_ESC_LOG = config.LOGS_DIR / "churn_escalations.jsonl"
DEDUP_WINDOW_DAYS = 7


def run_churn_scan() -> list[dict]:
    """
    Identify clients with active churn/urgency signals not yet escalated
    in the past DEDUP_WINDOW_DAYS days, and escalate each one.
    """
    conn = get_connection()

    # Clients with churn or urgency flags
    at_risk = conn.execute(
        """
        SELECT ts.client_id,
               c.name AS client_name,
               c.account_manager,
               c.contact_email,
               c.industry,
               MAX(ts.churn_risk)     AS churn_risk,
               MAX(ts.urgency_signal) AS urgency_signal,
               AVG(ts.sentiment)      AS avg_sentiment,
               GROUP_CONCAT(ts.raw_text, ' ||| ') AS combined_text
        FROM text_signals ts
        JOIN clients c ON c.id = ts.client_id
        WHERE (ts.churn_risk = 1 OR ts.urgency_signal = 1)
        GROUP BY ts.client_id
        """,
    ).fetchall()

    # Clients escalated recently (dedup window)
    cutoff = (datetime.now() - timedelta(days=DEDUP_WINDOW_DAYS)).isoformat()
    recent_ids = {
        r[0] for r in conn.execute(
            "SELECT client_id FROM churn_escalation_log WHERE escalated_at >= ?",
            (cutoff,),
        ).fetchall()
    }
    conn.close()

    escalated = []
    for row in at_risk:
        client = dict(row)
        if client["client_id"] in recent_ids:
            print(f"[churn] Skipping {client['client_name'][:20]} — escalated recently")
            continue
        result = _escalate(client)
        escalated.append(result)

    if escalated:
        print(f"[churn] Escalated {len(escalated)} client(s) with churn/urgency signals.")
    else:
        print("[churn] No new escalations required.")
    return escalated


def _escalate(client: dict) -> dict:
    now      = datetime.now().isoformat()
    esc_id   = str(uuid.uuid4())
    signal   = "churn_risk" if client.get("churn_risk") else "urgency_signal"
    manager  = client.get("account_manager") or "Account Manager"
    snippets = (client.get("combined_text") or "").split(" ||| ")
    snippet  = snippets[0][:200] if snippets else ""

    # Build retention draft message
    draft_body = (
        f"Hi {client['client_name']},\n\n"
        f"I wanted to personally check in and make sure everything is going well "
        f"with the work we're doing together.\n\n"
        f"Would you have 15 minutes this week for a quick call? "
        f"I'd love to hear how things are going from your side and see if there's "
        f"anything we can adjust or improve.\n\n"
        f"Best regards,\n{manager}"
    )

    log_record = {
        "escalation_id":  esc_id,
        "timestamp":      now,
        "client_id":      client["client_id"],
        "client_name":    client["client_name"],
        "account_manager": manager,
        "signal":         signal,
        "avg_sentiment":  client.get("avg_sentiment"),
        "snippet":        snippet,
        "draft_body":     draft_body,
        "message_to_manager": (
            f"⚠️ CHURN RISK: {client['client_name']} — {signal.replace('_',' ')}. "
            f"Sentiment: {(client.get('avg_sentiment') or 0):.2f}. "
            f"Latest: \"{snippet[:100]}\"  |  "
            f"Please reach out within 24 hours."
        ),
        "demo_mode":     config.DEMO_MODE,
        "_production":   "Production: POST to Slack with account manager @mention + 'Mark as handled' button.",
    }

    # Persist to churn_escalation_log
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO churn_escalation_log
            (id, client_id, account_manager, churn_signal, escalated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (esc_id, client["client_id"], manager, signal, now),
    )
    conn.commit()
    conn.close()

    if config.DEMO_MODE:
        CHURN_ESC_LOG.parent.mkdir(parents=True, exist_ok=True)
        with CHURN_ESC_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(log_record, ensure_ascii=False) + "\n")
        print(f"[churn][DEMO] Escalated: {client['client_name'][:20]} — {signal}")
    else:
        _send_slack_alert(log_record)

    return log_record


def _send_slack_alert(record: dict) -> None:
    import urllib.request
    payload = json.dumps({
        "text": record["message_to_manager"],
        "blocks": [{
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*⚠️ Churn Risk Alert*\n{record['message_to_manager']}"}
        }]
    }).encode()
    req = urllib.request.Request(
        config.SLACK_WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception as exc:
        print(f"[churn] Slack send failed: {exc}")


def get_escalation_log(limit: int = 50) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT cel.*, c.name AS client_name, c.industry
        FROM churn_escalation_log cel
        JOIN clients c ON c.id = cel.client_id
        ORDER BY cel.escalated_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def load_churn_log() -> list[dict]:
    if not CHURN_ESC_LOG.exists():
        return []
    records = []
    for line in CHURN_ESC_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return list(reversed(records))
