"""
Feature 4 — Client Propensity Tiers (Intelligent Prioritization).

Computes a propensity score (0–1) per client based on their historical
acceptance rate from feedback_log. Assigns a tier: high / medium / low.

Falls back to a rule-based tier when a client has fewer than 3 feedback rows.

Updates clients.propensity_score, .propensity_tier, .propensity_updated_at.
"""

from __future__ import annotations

from datetime import datetime

from src.db.schema import get_connection

# Minimum feedback rows before using acceptance-rate tier (below → 'medium' default)
MIN_FEEDBACK_ROWS = 3

# Only the most recent replies count, so tiers follow a client's current behaviour
RECENT_FEEDBACK_ROWS = 20

# Acceptance-rate thresholds
HIGH_THRESHOLD   = 0.50   # ≥ 50% → high
MEDIUM_THRESHOLD = 0.20   # 20–49% → medium; < 20% → low


def update_client_propensity_tiers() -> dict:
    """
    Recompute propensity for all clients and write back to the clients table.
    Returns a summary dict.
    """
    conn = get_connection()

    client_ids = [r[0] for r in conn.execute("SELECT id FROM clients").fetchall()]
    counts     = {"high": 0, "medium": 0, "low": 0}
    now        = datetime.now().isoformat()

    # One pass over feedback_log: outcomes of each client's 20 most recent replies
    stats = {
        r[0]: (r[1], r[2])
        for r in conn.execute(
            f"""
            SELECT client_id,
                   COUNT(*)                                             AS n_total,
                   SUM(CASE WHEN outcome = 'accepted' THEN 1 ELSE 0 END) AS n_accepted
            FROM (
                SELECT p.client_id, fl.outcome,
                       ROW_NUMBER() OVER (
                           PARTITION BY p.client_id ORDER BY fl.logged_at DESC
                       ) AS rn
                FROM feedback_log fl
                JOIN proposals p ON p.id = fl.proposal_id
            )
            WHERE rn <= {RECENT_FEEDBACK_ROWS}
            GROUP BY client_id
            """
        ).fetchall()
    }

    updates = []
    for client_id in client_ids:
        score, tier = _tier_for(*stats.get(client_id, (0, 0)))
        updates.append((score, tier, now, client_id))
        counts[tier] += 1

    conn.executemany(
        "UPDATE clients SET propensity_score=?, propensity_tier=?, propensity_updated_at=? WHERE id=?",
        updates,
    )
    conn.commit()
    conn.close()

    # Tiers drive the sort order of the cached opportunity list
    from src.agents.scorer import invalidate_cache
    invalidate_cache()
    print(f"[propensity] Updated {sum(counts.values())} clients — "
          f"high:{counts['high']} medium:{counts['medium']} low:{counts['low']}")
    return counts


def _tier_for(n_total: int, n_accepted: int) -> tuple[float, str]:
    """Return (score 0–1, tier str) from a client's recent feedback counts."""
    if n_total < MIN_FEEDBACK_ROWS:
        return 0.5, "medium"

    rate = n_accepted / n_total

    if rate >= HIGH_THRESHOLD:
        return round(rate, 3), "high"
    if rate >= MEDIUM_THRESHOLD:
        return round(rate, 3), "medium"
    return round(rate, 3), "low"


def get_client_propensity(client_id: str) -> dict:
    conn = get_connection()
    row = conn.execute(
        "SELECT propensity_score, propensity_tier, propensity_updated_at FROM clients WHERE id=?",
        (client_id,),
    ).fetchone()
    conn.close()
    if not row:
        return {"score": 0.5, "tier": "medium", "updated_at": None}
    return {
        "score":      row[0] if row[0] is not None else 0.5,
        "tier":       row[1] or "medium",
        "updated_at": row[2],
    }


def get_all_propensities() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT id, name, industry, propensity_score, propensity_tier, propensity_updated_at
        FROM clients
        ORDER BY propensity_score DESC NULLS LAST
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
