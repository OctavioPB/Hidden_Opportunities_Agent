"""
Feature 2 — Executive ROI Analytics Engine.

Computes pipeline value, revenue, acceptance rate, and time-saved
across configurable time windows. Also manages weekly analytics snapshots
for trend charts.

All data comes from the existing opportunities, proposals, and feedback_log tables.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from src.db.schema import get_connection


def get_analytics_summary(period_days: int = 30) -> dict:
    """
    Return ROI metrics for the given lookback period.
    period_days=0 means all-time.
    """
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(days=period_days)).isoformat() if period_days else "2000-01-01"

    # Pipeline value: sum of suggested_price for proposals sent/in-flight in window
    pipeline_value = conn.execute(
        "SELECT COALESCE(SUM(p.suggested_price),0) FROM proposals p "
        "WHERE COALESCE(p.sent_at, p.created_at) >= ?",
        (cutoff,),
    ).fetchone()[0]

    # Revenue realized: sum of revenue for accepted proposals
    revenue = conn.execute(
        "SELECT COALESCE(SUM(revenue),0) FROM feedback_log "
        "WHERE outcome='accepted' AND logged_at >= ?",
        (cutoff,),
    ).fetchone()[0]

    # Proposals sent / accepted — use sent_at for recency; fall back to created_at
    sent = conn.execute(
        "SELECT COUNT(*) FROM proposals WHERE status IN ('sent','accepted','rejected') "
        "AND COALESCE(sent_at, created_at) >= ?",
        (cutoff,),
    ).fetchone()[0]

    accepted = conn.execute(
        "SELECT COUNT(*) FROM proposals WHERE status='accepted' "
        "AND COALESCE(sent_at, created_at) >= ?",
        (cutoff,),
    ).fetchone()[0]

    generated = conn.execute(
        "SELECT COUNT(*) FROM proposals WHERE COALESCE(sent_at, created_at) >= ?",
        (cutoff,),
    ).fetchone()[0]

    ignored = conn.execute(
        "SELECT COUNT(*) FROM feedback_log WHERE outcome='ignored' AND logged_at >= ?",
        (cutoff,),
    ).fetchone()[0]

    rejected = conn.execute(
        "SELECT COUNT(*) FROM feedback_log "
        "WHERE outcome IN ('rejected','too_expensive') AND logged_at >= ?",
        (cutoff,),
    ).fetchone()[0]

    escalations = conn.execute(
        "SELECT COUNT(*) FROM feedback_log WHERE outcome='escalated' AND logged_at >= ?",
        (cutoff,),
    ).fetchone()[0]

    clients_reached = conn.execute(
        "SELECT COUNT(DISTINCT client_id) FROM proposals "
        "WHERE COALESCE(sent_at, created_at) >= ?",
        (cutoff,),
    ).fetchone()[0]

    follow_ups_sent = conn.execute(
        "SELECT COUNT(*) FROM follow_up_queue WHERE status='sent' AND sent_at >= ?",
        (cutoff,),
    ).fetchone()[0] if _table_exists(conn, "follow_up_queue") else 0

    # By opportunity type
    by_type = conn.execute(
        """
        SELECT o.opportunity_type,
               COUNT(*)                                                AS proposals,
               SUM(CASE WHEN p.status='accepted' THEN 1 ELSE 0 END)  AS accepted,
               COALESCE(SUM(fl.revenue),0)                            AS revenue
        FROM proposals p
        JOIN opportunities o ON o.id = p.opportunity_id
        LEFT JOIN feedback_log fl ON fl.proposal_id = p.id AND fl.outcome='accepted'
        WHERE COALESCE(p.sent_at, p.created_at) >= ?
        GROUP BY o.opportunity_type
        ORDER BY revenue DESC
        """,
        (cutoff,),
    ).fetchall()

    # Weekly acceptance trend (last 8 weeks)
    trend = _weekly_trend(conn)

    conn.close()

    acceptance_rate = round(accepted / sent * 100, 1) if sent else 0.0
    time_saved_h    = round(generated * 18 / 60, 1)  # 18 min saved per proposal
    roi_ratio       = round(revenue / max(pipeline_value, 1) * 100, 1)

    return {
        "period_days":       period_days,
        "pipeline_value":    float(pipeline_value),
        "revenue_realized":  float(revenue),
        "roi_pct":           roi_ratio,
        "proposals_generated": generated,
        "proposals_sent":    sent,
        "proposals_accepted": accepted,
        "proposals_ignored": ignored,
        "proposals_rejected": rejected,
        "escalations":       escalations,
        "acceptance_rate":   acceptance_rate,
        "clients_reached":   clients_reached,
        "follow_ups_sent":   follow_ups_sent,
        "time_saved_hours":  time_saved_h,
        "by_type":           [dict(r) for r in by_type],
        "weekly_trend":      trend,
    }


def _weekly_trend(conn) -> list[dict]:
    """Compute acceptance rate for each of the last 8 weeks."""
    trend = []
    now = datetime.now()
    for w in range(7, -1, -1):
        week_start = (now - timedelta(weeks=w + 1)).isoformat()
        week_end   = (now - timedelta(weeks=w)).isoformat()
        sent = conn.execute(
            "SELECT COUNT(*) FROM proposals WHERE status IN ('sent','accepted','rejected') "
            "AND COALESCE(sent_at, created_at) >= ? AND COALESCE(sent_at, created_at) < ?",
            (week_start, week_end),
        ).fetchone()[0]
        acc = conn.execute(
            "SELECT COUNT(*) FROM proposals WHERE status='accepted' "
            "AND COALESCE(sent_at, created_at) >= ? AND COALESCE(sent_at, created_at) < ?",
            (week_start, week_end),
        ).fetchone()[0]
        revenue = conn.execute(
            "SELECT COALESCE(SUM(revenue),0) FROM feedback_log "
            "WHERE outcome='accepted' AND logged_at >= ? AND logged_at < ?",
            (week_start, week_end),
        ).fetchone()[0]
        trend.append({
            "week_start":      week_start[:10],
            "sent":            sent,
            "accepted":        acc,
            "acceptance_rate": round(acc / sent * 100, 1) if sent else 0.0,
            "revenue":         float(revenue),
        })
    return trend


def save_analytics_snapshot() -> dict:
    """
    Persist today's analytics summary to analytics_snapshots.
    Called weekly by the daily job (Fridays).
    """
    summary = get_analytics_summary(period_days=7)
    today   = datetime.now().strftime("%Y-%m-%d")

    conn = get_connection()
    # Avoid duplicate snapshots for the same day
    existing = conn.execute(
        "SELECT id FROM analytics_snapshots WHERE snapshot_date=?", (today,)
    ).fetchone()

    if not existing:
        conn.execute(
            """
            INSERT INTO analytics_snapshots
                (snapshot_date, pipeline_value, revenue_realized,
                 proposals_sent, proposals_accepted, acceptance_rate, time_saved_hours)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (today, summary["pipeline_value"], summary["revenue_realized"],
             summary["proposals_sent"], summary["proposals_accepted"],
             summary["acceptance_rate"], summary["time_saved_hours"]),
        )
        conn.commit()
        print(f"[analytics] Snapshot saved for {today}")

    conn.close()
    return summary


def get_snapshots(limit: int = 12) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM analytics_snapshots ORDER BY snapshot_date DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _table_exists(conn, name: str) -> bool:
    return conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()[0] > 0
