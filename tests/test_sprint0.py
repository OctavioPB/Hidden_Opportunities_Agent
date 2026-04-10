"""
Sprint 0 smoke tests.

Verifies that the seed script produced a valid database and that all
data source modules return expected data for the demo scenario clients.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import config
from src.db.schema import get_connection


DEMO_IDS = ["demo-001", "demo-002", "demo-003", "demo-004", "demo-005"]


# ── Database ──────────────────────────────────────────────────────────────────

def test_db_exists():
    assert config.DB_PATH.exists(), f"DB not found at {config.DB_PATH}"


def test_clients_seeded():
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    conn.close()
    assert count >= 80, f"Expected >= 80 clients, got {count}"


def test_demo_clients_present():
    conn = get_connection()
    ids = [r[0] for r in conn.execute("SELECT id FROM clients WHERE is_demo_scenario = 1").fetchall()]
    conn.close()
    for demo_id in DEMO_IDS:
        assert demo_id in ids, f"Demo client {demo_id} not found in DB"


def test_metrics_seeded():
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM client_metrics").fetchone()[0]
    conn.close()
    assert count >= 7000, f"Expected >= 7000 metric rows, got {count}"


def test_text_signals_seeded():
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM text_signals").fetchone()[0]
    conn.close()
    assert count >= 400, f"Expected >= 400 text signal rows, got {count}"


# ── Data sources ──────────────────────────────────────────────────────────────

def test_google_analytics_returns_data():
    from src.data_sources import google_analytics as ga
    rows = ga.get_client_metrics("demo-001", days=7)
    assert len(rows) == 7
    assert "_production_integration" in rows[0]
    assert "bounce_rate" in rows[0]


def test_meta_ads_returns_data():
    from src.data_sources import meta_ads
    row = meta_ads.get_latest_ad_metrics("demo-003")
    assert row is not None
    assert "ctr" in row
    assert "ad_spend" in row


def test_crm_returns_client():
    from src.data_sources import crm
    client = crm.get_client("demo-001")
    assert client is not None
    assert client["name"] == "Bella Cucina Restaurant"


def test_crm_demo_clients():
    from src.data_sources import crm
    clients = crm.get_demo_clients()
    assert len(clients) == 5


def test_email_marketing_returns_data():
    from src.data_sources import email_marketing
    rows = email_marketing.get_email_metrics("demo-004", days=14)
    assert len(rows) == 14
    assert "email_open_rate" in rows[0]


def test_seo_returns_data():
    from src.data_sources import seo
    row = seo.get_latest_seo_metrics("demo-002")
    assert row is not None
    assert "organic_traffic" in row
    assert "keyword_rankings" in row


def test_all_sources_have_production_note():
    """Every data source must annotate records with a production integration note."""
    from src.data_sources import google_analytics, meta_ads, crm, email_marketing, seo

    checks = [
        google_analytics.get_all_clients_latest(),
        meta_ads.get_all_clients_latest(),
        crm.get_all_clients(),
        email_marketing.get_all_clients_latest(),
        seo.get_all_clients_latest(),
    ]
    for result in checks:
        assert len(result) > 0
        assert "_production_integration" in result[0], (
            f"Missing _production_integration in {result[0]}"
        )
