"""
SQLite schema definition and connection helper.

Tables created here span all sprints — columns used in later sprints
are nullable so earlier sprints can run without migration headaches.
"""

import sqlite3
from pathlib import Path

import config


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create all tables if they do not exist."""
    conn = get_connection()
    cur = conn.cursor()

    # ── clients ───────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id              TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            industry        TEXT,
            company_size    TEXT,          -- 'small' | 'medium' | 'large'
            account_age_days INTEGER,
            monthly_spend   REAL,
            contact_email   TEXT,
            account_manager TEXT,
            is_demo_scenario INTEGER DEFAULT 0,  -- 1 = featured in live demo
            created_at      TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── client_metrics (structured data — Sprint 1–2) ─────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS client_metrics (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id       TEXT NOT NULL REFERENCES clients(id),
            date            TEXT NOT NULL,
            -- Google Analytics
            bounce_rate     REAL,
            pages_per_session REAL,
            conversion_rate REAL,
            organic_traffic INTEGER,
            -- Meta Ads
            ctr             REAL,
            cpc             REAL,
            roas            REAL,
            ad_spend        REAL,
            -- Email marketing
            email_open_rate REAL,
            email_click_rate REAL,
            -- SEO
            keyword_rankings INTEGER,
            -- Activity
            days_since_last_contact INTEGER,
            days_inactive   INTEGER
        )
    """)

    # ── opportunities (Sprint 2+) ─────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS opportunities (
            id              TEXT PRIMARY KEY,
            client_id       TEXT NOT NULL REFERENCES clients(id),
            opportunity_type TEXT NOT NULL,  -- e.g. 'landing_page_optimization'
            score           REAL,            -- 0–100 heuristic score (Sprint 2)
            ml_probability  REAL,            -- 0–1 ML probability (Sprint 5)
            status          TEXT DEFAULT 'detected',
                                             -- detected | proposal_generated | sent
                                             -- | accepted | rejected | escalated | closed
            detected_at     TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── proposals (Sprint 3+) ─────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS proposals (
            id              TEXT PRIMARY KEY,
            opportunity_id  TEXT NOT NULL REFERENCES opportunities(id),
            client_id       TEXT NOT NULL REFERENCES clients(id),
            subject         TEXT,
            body            TEXT,
            suggested_price REAL,
            status          TEXT DEFAULT 'draft',
                                             -- draft | pending_approval | approved
                                             -- | sent | accepted | rejected | paid
            approved_by     TEXT,
            sent_at         TEXT,
            payment_link    TEXT,            -- Stripe Payment Link URL (Sprint 7)
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── negotiation_log (Sprint 7) ────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS negotiation_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            proposal_id     TEXT NOT NULL REFERENCES proposals(id),
            turn            INTEGER NOT NULL,
            role            TEXT NOT NULL,   -- 'agent' | 'client'
            message         TEXT NOT NULL,
            intent          TEXT,            -- extracted intent (Sprint 7)
            offer_price     REAL,
            timestamp       TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── feedback_log (Sprint 4 — raw interaction outcomes) ───────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            opportunity_id  TEXT REFERENCES opportunities(id),
            proposal_id     TEXT REFERENCES proposals(id),
            outcome         TEXT,            -- 'accepted' | 'rejected' | 'ignored' | 'escalated'
            revenue         REAL,
            notes           TEXT,
            logged_at       TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── text_signals (Sprint 6 — NLP pipeline output) ─────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS text_signals (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id       TEXT NOT NULL REFERENCES clients(id),
            source          TEXT,            -- 'email' | 'call_transcript' | 'crm_note'
            raw_text        TEXT,
            sentiment       REAL,            -- -1.0 to 1.0
            mentions_price  INTEGER DEFAULT 0,
            asks_for_results INTEGER DEFAULT 0,
            churn_risk      INTEGER DEFAULT 0,
            urgency_signal  INTEGER DEFAULT 0,
            interest_signal INTEGER DEFAULT 0,
            processed_at    TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── follow_up_queue (Feature 1 — automated follow-up sequences) ──────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS follow_up_queue (
            id             TEXT PRIMARY KEY,
            proposal_id    TEXT NOT NULL REFERENCES proposals(id),
            client_id      TEXT NOT NULL REFERENCES clients(id),
            sequence_turn  INTEGER DEFAULT 1,
            scheduled_at   TEXT NOT NULL,
            status         TEXT DEFAULT 'pending',
            angle          TEXT,
            subject        TEXT,
            body           TEXT,
            sent_at        TEXT,
            created_at     TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── churn_escalation_log (Feature 3 — churn prevention) ──────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS churn_escalation_log (
            id               TEXT PRIMARY KEY,
            client_id        TEXT NOT NULL REFERENCES clients(id),
            account_manager  TEXT,
            churn_signal     TEXT,
            escalated_at     TEXT DEFAULT (datetime('now')),
            proposal_id      TEXT,
            slack_sent       INTEGER DEFAULT 0,
            email_draft_id   TEXT
        )
    """)

    # ── analytics_snapshots (Feature 2 — ROI dashboard) ──────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS analytics_snapshots (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date   TEXT NOT NULL,
            pipeline_value  REAL DEFAULT 0,
            revenue_realized REAL DEFAULT 0,
            proposals_sent  INTEGER DEFAULT 0,
            proposals_accepted INTEGER DEFAULT 0,
            acceptance_rate REAL DEFAULT 0,
            time_saved_hours REAL DEFAULT 0,
            created_at      TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()
    print(f"[db] Schema initialized at {config.DB_PATH}")


def migrate_db() -> None:
    """
    Apply additive schema migrations to an existing database.

    Safe to call repeatedly — uses ALTER TABLE IF NOT EXISTS semantics.
    Run this after init_db() when upgrading an existing database to a newer
    sprint without dropping tables.
    """
    conn = get_connection()
    cur = conn.cursor()

    # Sprint 6: add interest_signal column to text_signals if missing
    ts_cols = {row[1] for row in cur.execute("PRAGMA table_info(text_signals)").fetchall()}
    if "interest_signal" not in ts_cols:
        cur.execute(
            "ALTER TABLE text_signals ADD COLUMN interest_signal INTEGER DEFAULT 0"
        )

    # Sprint 7: add payment_link column to proposals if the table exists
    proposals_exists = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='proposals'"
    ).fetchone()
    if proposals_exists:
        p_cols = {row[1] for row in cur.execute("PRAGMA table_info(proposals)").fetchall()}
        if "payment_link" not in p_cols:
            cur.execute("ALTER TABLE proposals ADD COLUMN payment_link TEXT")

    # Feature 4 + 5 + 7: new columns on clients
    tables_existing = {r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}

    if "clients" in tables_existing:
        c_cols = {row[1] for row in cur.execute("PRAGMA table_info(clients)").fetchall()}
        for col, defn in [
            ("propensity_score",    "REAL"),
            ("propensity_tier",     "TEXT"),
            ("propensity_updated_at","TEXT"),
            ("whatsapp_number",     "TEXT"),
            ("whatsapp_opted_in",   "INTEGER DEFAULT 0"),
            ("preferred_channel",   "TEXT DEFAULT 'email'"),
            ("crm_contact_id",      "TEXT"),
            ("crm_deal_id",         "TEXT"),
        ]:
            if col not in c_cols:
                cur.execute(f"ALTER TABLE clients ADD COLUMN {col} {defn}")

    # Feature 1: follow_up_queue
    cur.execute("""
        CREATE TABLE IF NOT EXISTS follow_up_queue (
            id             TEXT PRIMARY KEY,
            proposal_id    TEXT NOT NULL,
            client_id      TEXT NOT NULL,
            sequence_turn  INTEGER DEFAULT 1,
            scheduled_at   TEXT NOT NULL,
            status         TEXT DEFAULT 'pending',
            angle          TEXT,
            subject        TEXT,
            body           TEXT,
            sent_at        TEXT,
            created_at     TEXT DEFAULT (datetime('now'))
        )
    """)

    # Feature 2: analytics_snapshots
    cur.execute("""
        CREATE TABLE IF NOT EXISTS analytics_snapshots (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date    TEXT NOT NULL,
            pipeline_value   REAL DEFAULT 0,
            revenue_realized REAL DEFAULT 0,
            proposals_sent   INTEGER DEFAULT 0,
            proposals_accepted INTEGER DEFAULT 0,
            acceptance_rate  REAL DEFAULT 0,
            time_saved_hours REAL DEFAULT 0,
            created_at       TEXT DEFAULT (datetime('now'))
        )
    """)

    # Feature 3: churn_escalation_log
    cur.execute("""
        CREATE TABLE IF NOT EXISTS churn_escalation_log (
            id               TEXT PRIMARY KEY,
            client_id        TEXT NOT NULL,
            account_manager  TEXT,
            churn_signal     TEXT,
            escalated_at     TEXT DEFAULT (datetime('now')),
            proposal_id      TEXT,
            slack_sent       INTEGER DEFAULT 0,
            email_draft_id   TEXT
        )
    """)

    # Feature 5: crm_sync_log
    cur.execute("""
        CREATE TABLE IF NOT EXISTS crm_sync_log (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            proposal_id    TEXT,
            client_id      TEXT,
            action         TEXT,
            crm_deal_id    TEXT,
            revenue        REAL,
            synced_at      TEXT DEFAULT (datetime('now')),
            demo_mode      INTEGER DEFAULT 1
        )
    """)

    conn.commit()
    conn.close()
