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
                                             -- | sent | accepted | rejected
            approved_by     TEXT,
            sent_at         TEXT,
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
    existing_cols = {
        row[1] for row in cur.execute("PRAGMA table_info(text_signals)").fetchall()
    }
    if "interest_signal" not in existing_cols:
        cur.execute(
            "ALTER TABLE text_signals ADD COLUMN interest_signal INTEGER DEFAULT 0"
        )

    conn.commit()
    conn.close()
