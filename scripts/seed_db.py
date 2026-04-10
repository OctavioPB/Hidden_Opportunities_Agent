"""
Seed script — Sprint 0.

Note: on Windows terminals set PYTHONIOENCODING=utf-8 or use
  python -X utf8 scripts/seed_db.py
to avoid cp1252 encoding errors with Unicode characters.

Initializes the SQLite schema and populates it with synthetic data.
Run this once before starting the app, or whenever you want a fresh dataset.

Usage:
    python scripts/seed_db.py           # use defaults from config
    python scripts/seed_db.py --reset   # drop and recreate all tables first
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from src.db.schema import get_connection, init_db
from src.synthetic.generator import generate_all, save_to_json


def _drop_all(conn: sqlite3.Connection) -> None:
    tables = [
        "text_signals", "feedback_log", "negotiation_log",
        "proposals", "opportunities", "client_metrics", "clients",
    ]
    for t in tables:
        conn.execute(f"DROP TABLE IF EXISTS {t}")
    conn.commit()
    print("[seed] All tables dropped.")


def _insert_clients(conn: sqlite3.Connection, clients: list[dict]) -> None:
    conn.executemany(
        """
        INSERT OR REPLACE INTO clients
            (id, name, industry, company_size, account_age_days,
             monthly_spend, contact_email, account_manager, is_demo_scenario)
        VALUES
            (:id, :name, :industry, :company_size, :account_age_days,
             :monthly_spend, :contact_email, :account_manager, :is_demo_scenario)
        """,
        clients,
    )
    print(f"[seed] Inserted {len(clients)} clients.")


def _insert_metrics(conn: sqlite3.Connection, metrics: list[dict]) -> None:
    conn.executemany(
        """
        INSERT INTO client_metrics
            (client_id, date, bounce_rate, pages_per_session, conversion_rate,
             organic_traffic, ctr, cpc, roas, ad_spend,
             email_open_rate, email_click_rate, keyword_rankings,
             days_since_last_contact, days_inactive)
        VALUES
            (:client_id, :date, :bounce_rate, :pages_per_session, :conversion_rate,
             :organic_traffic, :ctr, :cpc, :roas, :ad_spend,
             :email_open_rate, :email_click_rate, :keyword_rankings,
             :days_since_last_contact, :days_inactive)
        """,
        metrics,
    )
    print(f"[seed] Inserted {len(metrics)} metric rows.")


def _insert_text_signals(conn: sqlite3.Connection, signals: list[dict]) -> None:
    # Strip the hint key before inserting — it's a generator artifact
    clean = [
        {k: v for k, v in s.items() if k != "signal_type_hint"}
        for s in signals
    ]
    conn.executemany(
        """
        INSERT INTO text_signals (client_id, source, raw_text)
        VALUES (:client_id, :source, :raw_text)
        """,
        clean,
    )
    print(f"[seed] Inserted {len(clean)} text signal rows.")


def seed(reset: bool = False) -> None:
    print(f"\n{'='*50}")
    print(f"  Hidden Opportunities Agent — DB Seed")
    print(f"  DB path   : {config.DB_PATH}")
    print(f"  Demo mode : {config.DEMO_MODE}")
    print(f"  Seed      : {config.SYNTHETIC_SEED}")
    print(f"  Clients   : {config.SYNTHETIC_CLIENT_COUNT} random + 5 demo scenarios")
    print(f"{'='*50}\n")

    conn = get_connection()

    if reset:
        _drop_all(conn)

    init_db()

    print("[seed] Generating synthetic dataset...")
    dataset = generate_all()
    save_to_json(dataset)

    # Strip internal keys before DB insert
    clients_clean = [
        {k: v for k, v in c.items() if not k.startswith("_")}
        for c in dataset["clients"]
    ]

    _insert_clients(conn, clients_clean)
    _insert_metrics(conn, dataset["metrics"])
    _insert_text_signals(conn, dataset["text_signals"])

    conn.commit()
    conn.close()

    print(f"\n[seed] Done. Database ready at {config.DB_PATH}")
    print("[seed] Demo scenario client IDs:")
    for c in clients_clean:
        if c["is_demo_scenario"]:
            print(f"         {c['id']}  ->  {c['name']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the Hidden Opportunities Agent database.")
    parser.add_argument("--reset", action="store_true", help="Drop all tables before seeding.")
    args = parser.parse_args()
    seed(reset=args.reset)
