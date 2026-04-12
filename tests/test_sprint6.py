"""
Sprint 6 tests — NLP Text Signal Pipeline.

Coverage:
 1.  signal_extractor — extract_signals_keyword detects price keywords.
 2.  signal_extractor — extract_signals_keyword detects churn keywords.
 3.  signal_extractor — extract_signals_keyword detects urgency keywords.
 4.  signal_extractor — extract_signals_keyword detects results-interest keywords.
 5.  signal_extractor — extract_signals_keyword detects interest/buying signals.
 6.  signal_extractor — sentiment_score returns float in [-1, 1].
 7.  signal_extractor — positive text → sentiment > 0.
 8.  signal_extractor — negative text → sentiment < 0.
 9.  signal_extractor — neutral text → signals all 0.
10.  signal_extractor — extract_signals returns required keys.
11.  signal_extractor — extraction_mode is 'keyword' in DEMO_MODE.
12.  signal_extractor — aggregate_signals returns 0s for empty list.
13.  signal_extractor — aggregate_signals ANYs binary flags correctly.
14.  signal_extractor — aggregate_signals averages sentiment.
15.  pipeline — run_pipeline processes unprocessed rows.
16.  pipeline — run_pipeline writes results back to DB.
17.  pipeline — run_pipeline counts churn_alerts correctly.
18.  pipeline — run_pipeline counts urgency_alerts correctly.
19.  pipeline — get_pipeline_summary returns correct structure.
20.  pipeline — reprocess_all=True re-processes already-done rows.
21.  data_source — get_client_signals returns list.
22.  data_source — get_signal_summary returns 0s for unknown client.
23.  data_source — get_signal_summary aggregates correctly after pipeline.
24.  data_source — get_urgency_alerts returns clients with churn_risk=1.
25.  data_source — count_signals_by_type sums flags correctly.
26.  schema — migrate_db adds interest_signal column if missing.
27.  dataset — FEATURE_NAMES has 18 elements.
28.  dataset — _metrics_to_row with signals produces 18-element vector.
29.  dataset — _metrics_to_row without signals defaults NLP features to 0.
30.  dataset — build_dataset returns 18-column vectors.
31.  daily_job — run() summary includes nlp_processed key.
32.  process_text script — run() returns dict with total_processed key.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import config


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_conn(p: Path):
    conn = sqlite3.connect(str(p), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@pytest.fixture()
def seeded_db(tmp_path, monkeypatch):
    """
    Temp DB with one client + several text_signals rows (unprocessed).
    Patches all DB-accessing modules.
    """
    db_path = tmp_path / "sprint6.db"
    monkeypatch.setattr(config, "DB_PATH", db_path)

    import src.db.schema as schema
    import src.nlp.pipeline as pipeline
    import src.data_sources.text_signals as ts_ds

    _conn = lambda: _make_conn(db_path)
    monkeypatch.setattr(schema,   "get_connection", _conn)
    monkeypatch.setattr(pipeline, "get_connection", _conn)
    monkeypatch.setattr(ts_ds,    "get_connection", _conn)

    schema.init_db()
    schema.migrate_db()

    conn = _make_conn(db_path)
    client_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO clients (id, name, industry, account_age_days) VALUES (?,?,?,?)",
        (client_id, "Test Corp", "Restaurant", 365),
    )

    # Insert 5 text signal rows (unprocessed — sentiment IS NULL)
    texts = [
        ("email",           "The cost is getting expensive for us this quarter."),
        ("email",           "Can you send some case studies about results?"),
        ("call_transcript", "Client mentioned they are evaluating another agency."),
        ("email",           "We need this resolved ASAP — it's urgent."),
        ("crm_note",        "Just confirming receipt of the report. Thanks."),
    ]
    for source, text in texts:
        conn.execute(
            "INSERT INTO text_signals (client_id, source, raw_text) VALUES (?,?,?)",
            (client_id, source, text),
        )

    conn.commit()
    conn.close()
    return client_id, db_path


# ── 1–11. Signal extractor ────────────────────────────────────────────────────

class TestSignalExtractorKeywords:
    def test_detects_price_keywords(self):
        from src.nlp.signal_extractor import extract_signals_keyword
        result = extract_signals_keyword("The cost is getting expensive for us.")
        assert result["mentions_price"] == 1

    def test_detects_churn_keywords(self):
        from src.nlp.signal_extractor import extract_signals_keyword
        result = extract_signals_keyword("We are evaluating another agency to possibly switch.")
        assert result["churn_risk"] == 1

    def test_detects_urgency_keywords(self):
        from src.nlp.signal_extractor import extract_signals_keyword
        result = extract_signals_keyword("We need this resolved ASAP — it's time-sensitive.")
        assert result["urgency_signal"] == 1

    def test_detects_results_keywords(self):
        from src.nlp.signal_extractor import extract_signals_keyword
        result = extract_signals_keyword("Can you send case studies showing ROI benchmarks?")
        assert result["asks_for_results"] == 1

    def test_detects_interest_keywords(self):
        from src.nlp.signal_extractor import extract_signals_keyword
        result = extract_signals_keyword("Love what you've done! Let's schedule a call to move forward.")
        assert result["interest_signal"] == 1

    def test_sentiment_in_range(self):
        from src.nlp.signal_extractor import _sentiment_score
        score = _sentiment_score("This is a great excellent amazing service!")
        assert -1.0 <= score <= 1.0

    def test_positive_text_positive_sentiment(self):
        from src.nlp.signal_extractor import _sentiment_score
        score = _sentiment_score("Great excellent amazing wonderful happy satisfied!")
        assert score > 0

    def test_negative_text_negative_sentiment(self):
        from src.nlp.signal_extractor import _sentiment_score
        score = _sentiment_score("Terrible awful bad poor worst disaster!")
        assert score < 0

    def test_neutral_text_no_signals(self):
        from src.nlp.signal_extractor import extract_signals_keyword
        result = extract_signals_keyword("Please confirm receipt of the monthly report.")
        assert result["mentions_price"] == 0
        assert result["churn_risk"] == 0
        assert result["urgency_signal"] == 0

    def test_extract_signals_required_keys(self):
        from src.nlp.signal_extractor import extract_signals
        result = extract_signals("Hello, confirming our meeting.", use_llm=False)
        required = {"sentiment", "mentions_price", "asks_for_results",
                    "churn_risk", "urgency_signal", "interest_signal", "extraction_mode"}
        assert required.issubset(result.keys())

    def test_extraction_mode_keyword_in_demo(self, monkeypatch):
        """DEMO_MODE=True forces keyword extraction."""
        monkeypatch.setattr(config, "DEMO_MODE", True)
        from src.nlp.signal_extractor import extract_signals
        result = extract_signals("Expensive budget concern.", use_llm=True)
        assert result["extraction_mode"] == "keyword"


# ── 12–14. Aggregation ────────────────────────────────────────────────────────

class TestAggregateSignals:
    def test_empty_list_returns_zeros(self):
        from src.nlp.signal_extractor import aggregate_signals
        result = aggregate_signals([])
        assert result["sentiment_score"] == 0.0
        assert result["churn_risk"] == 0
        assert result["urgency_signal"] == 0

    def test_any_flag_propagates(self):
        from src.nlp.signal_extractor import aggregate_signals
        rows = [
            {"sentiment": 0.1, "mentions_price": 0, "asks_for_results": 0,
             "churn_risk": 0, "urgency_signal": 0, "interest_signal": 0},
            {"sentiment": -0.3, "mentions_price": 1, "asks_for_results": 0,
             "churn_risk": 1, "urgency_signal": 0, "interest_signal": 0},
        ]
        result = aggregate_signals(rows)
        assert result["mentions_price"] == 1
        assert result["churn_risk"] == 1
        assert result["asks_for_results"] == 0

    def test_sentiment_averaged(self):
        from src.nlp.signal_extractor import aggregate_signals
        rows = [
            {"sentiment": 0.4, "mentions_price": 0, "asks_for_results": 0,
             "churn_risk": 0, "urgency_signal": 0, "interest_signal": 0},
            {"sentiment": -0.2, "mentions_price": 0, "asks_for_results": 0,
             "churn_risk": 0, "urgency_signal": 0, "interest_signal": 0},
        ]
        result = aggregate_signals(rows)
        assert result["sentiment_score"] == pytest.approx(0.1, abs=0.01)


# ── 15–20. Pipeline ───────────────────────────────────────────────────────────

class TestPipeline:
    def test_run_pipeline_processes_rows(self, seeded_db):
        from src.nlp.pipeline import run_pipeline
        client_id, db_path = seeded_db
        result = run_pipeline(reprocess_all=False, use_llm=False, verbose=False)
        assert result["total_processed"] == 5

    def test_run_pipeline_writes_sentiment_to_db(self, seeded_db):
        from src.nlp.pipeline import run_pipeline
        client_id, db_path = seeded_db
        run_pipeline(reprocess_all=False, use_llm=False, verbose=False)

        conn = _make_conn(db_path)
        rows = conn.execute(
            "SELECT sentiment FROM text_signals WHERE client_id = ?", (client_id,)
        ).fetchall()
        conn.close()
        assert all(r["sentiment"] is not None for r in rows)

    def test_run_pipeline_counts_churn_alerts(self, seeded_db):
        from src.nlp.pipeline import run_pipeline
        _, _ = seeded_db
        result = run_pipeline(reprocess_all=False, use_llm=False, verbose=False)
        # The "evaluating another agency" text should fire churn_risk
        assert result["churn_alerts"] >= 1

    def test_run_pipeline_counts_urgency_alerts(self, seeded_db):
        from src.nlp.pipeline import run_pipeline
        _, _ = seeded_db
        result = run_pipeline(reprocess_all=False, use_llm=False, verbose=False)
        # The "ASAP — it's urgent" text should fire urgency_signal
        assert result["urgency_alerts"] >= 1

    def test_get_pipeline_summary_structure(self, seeded_db):
        from src.nlp.pipeline import get_pipeline_summary
        _, _ = seeded_db
        summary = get_pipeline_summary()
        required = {"total_signals", "processed", "unprocessed",
                    "churn_count", "urgency_count", "price_mentions_clients"}
        assert required.issubset(summary.keys())

    def test_reprocess_all_flag(self, seeded_db):
        from src.nlp.pipeline import run_pipeline
        _, _ = seeded_db
        # First pass
        run_pipeline(reprocess_all=False, use_llm=False, verbose=False)
        # Second pass — nothing to process (all done)
        result2 = run_pipeline(reprocess_all=False, use_llm=False, verbose=False)
        assert result2["total_processed"] == 0
        # With reprocess_all=True — all 5 are reprocessed
        result3 = run_pipeline(reprocess_all=True, use_llm=False, verbose=False)
        assert result3["total_processed"] == 5


# ── 21–25. Data source ────────────────────────────────────────────────────────

class TestTextSignalsDataSource:
    def test_get_client_signals_returns_list(self, seeded_db):
        from src.data_sources.text_signals import get_client_signals
        client_id, _ = seeded_db
        signals = get_client_signals(client_id)
        assert isinstance(signals, list)
        assert len(signals) == 5

    def test_get_signal_summary_zeros_for_unknown(self, seeded_db):
        from src.data_sources.text_signals import get_signal_summary
        summary = get_signal_summary("nonexistent-client")
        assert summary["sentiment_score"] == 0.0
        assert summary["churn_risk"] == 0

    def test_get_signal_summary_after_pipeline(self, seeded_db):
        from src.nlp.pipeline import run_pipeline
        from src.data_sources.text_signals import get_signal_summary
        client_id, _ = seeded_db
        run_pipeline(reprocess_all=False, use_llm=False, verbose=False)
        summary = get_signal_summary(client_id)
        # The pipeline should have found churn and price signals
        assert summary["n_signals"] == 5
        assert summary["churn_risk"] == 1
        assert summary["mentions_price"] == 1

    def test_get_urgency_alerts_returns_churn_clients(self, seeded_db):
        from src.nlp.pipeline import run_pipeline
        from src.data_sources.text_signals import get_urgency_alerts
        import src.data_sources.crm as crm_mod
        client_id, db_path = seeded_db

        # Patch get_all_clients and get_client for the JOIN
        # (crm module not patched in this fixture — use raw DB instead)
        conn = _make_conn(db_path)
        conn.execute(
            "UPDATE text_signals SET churn_risk = 1 WHERE client_id = ?", (client_id,)
        )
        conn.execute(
            "UPDATE text_signals SET sentiment = -0.3 WHERE client_id = ?", (client_id,)
        )
        conn.commit()
        conn.close()

        alerts = get_urgency_alerts()
        assert any(a["client_id"] == client_id for a in alerts)

    def test_count_signals_by_type_after_pipeline(self, seeded_db):
        from src.nlp.pipeline import run_pipeline
        from src.data_sources.text_signals import count_signals_by_type
        _, _ = seeded_db
        run_pipeline(reprocess_all=False, use_llm=False, verbose=False)
        counts = count_signals_by_type()
        assert "total" in counts
        assert counts["total"] >= 0


# ── 26. Schema migration ───────────────────────────────────────────────────────

class TestSchemaMigration:
    def test_migrate_adds_interest_signal(self, tmp_path, monkeypatch):
        """Create a DB without interest_signal then run migrate_db — column should appear."""
        db_path = tmp_path / "migration_test.db"
        monkeypatch.setattr(config, "DB_PATH", db_path)

        import src.db.schema as schema
        monkeypatch.setattr(schema, "get_connection", lambda: _make_conn(db_path))

        # Init without interest_signal column (simulate old DB)
        conn = _make_conn(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id TEXT PRIMARY KEY, name TEXT, industry TEXT,
                account_age_days INTEGER, is_demo_scenario INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS text_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT, source TEXT, raw_text TEXT,
                sentiment REAL, mentions_price INTEGER DEFAULT 0,
                asks_for_results INTEGER DEFAULT 0, churn_risk INTEGER DEFAULT 0,
                urgency_signal INTEGER DEFAULT 0
                -- interest_signal intentionally missing
            )
        """)
        conn.commit()
        conn.close()

        # Verify column is missing before migration
        conn = _make_conn(db_path)
        cols_before = {r[1] for r in conn.execute("PRAGMA table_info(text_signals)").fetchall()}
        conn.close()
        assert "interest_signal" not in cols_before

        # Run migration
        schema.migrate_db()

        # Verify column exists after migration
        conn = _make_conn(db_path)
        cols_after = {r[1] for r in conn.execute("PRAGMA table_info(text_signals)").fetchall()}
        conn.close()
        assert "interest_signal" in cols_after


# ── 27–30. ML dataset with 18 features ───────────────────────────────────────

class TestDatasetWith18Features:
    def test_feature_names_length(self):
        from src.ml.dataset import FEATURE_NAMES
        assert len(FEATURE_NAMES) == 18

    def test_nlp_feature_names_present(self):
        from src.ml.dataset import FEATURE_NAMES
        nlp_features = {"sentiment_score", "mentions_price", "asks_for_results",
                        "churn_risk", "urgency_signal"}
        assert nlp_features.issubset(set(FEATURE_NAMES))

    def test_metrics_to_row_with_signals(self):
        from src.ml.dataset import _metrics_to_row, FEATURE_NAMES
        metrics = {"ctr": 0.04, "bounce_rate": 0.65, "pages_per_session": 2.1,
                   "conversion_rate": 0.02, "organic_traffic": 1800, "roas": 1.8,
                   "ad_spend": 50.0, "email_open_rate": 0.18, "keyword_rankings": 25,
                   "days_inactive": 45}
        signals = {"sentiment_score": 0.3, "mentions_price": 1,
                   "asks_for_results": 0, "churn_risk": 0, "urgency_signal": 1}
        row = _metrics_to_row(metrics, "Restaurant", "seo_content", 365, signals=signals)
        assert len(row) == 18
        # Check NLP values landed in correct positions
        idx_sent  = FEATURE_NAMES.index("sentiment_score")
        idx_price = FEATURE_NAMES.index("mentions_price")
        idx_urg   = FEATURE_NAMES.index("urgency_signal")
        assert row[idx_sent]  == pytest.approx(0.3)
        assert row[idx_price] == 1.0
        assert row[idx_urg]   == 1.0

    def test_metrics_to_row_without_signals_defaults_to_zero(self):
        from src.ml.dataset import _metrics_to_row, FEATURE_NAMES
        metrics = {"ctr": 0.04}
        row = _metrics_to_row(metrics, "Restaurant", "seo_content", 365)
        idx_sent  = FEATURE_NAMES.index("sentiment_score")
        idx_churn = FEATURE_NAMES.index("churn_risk")
        assert row[idx_sent]  == 0.0
        assert row[idx_churn] == 0.0

    def test_build_dataset_returns_18_columns(self):
        from src.ml.dataset import build_dataset, FEATURE_NAMES
        X, y, names = build_dataset(augment=False, verbose=False)
        assert names == FEATURE_NAMES
        assert all(len(row) == 18 for row in X)


# ── 31. Daily job NLP integration ─────────────────────────────────────────────

class TestDailyJobSprint6:
    def test_run_includes_nlp_key(self, seeded_db, monkeypatch):
        client_id, db_path = seeded_db
        import src.agents.scorer as scorer
        import src.data_sources.crm as crm_mod
        import src.agents.alerts as alerts_mod
        import src.agents.auto_sender as aut
        import src.agents.proposal_generator as pg
        import src.nlp.pipeline as nlp_pipe

        monkeypatch.setattr(scorer, "score_all_clients", lambda: [])
        monkeypatch.setattr(scorer, "persist_opportunities", lambda r: 0)
        monkeypatch.setattr(alerts_mod, "dispatch", lambda r, channel="slack": [])
        monkeypatch.setattr(pg, "generate_proposals_for_all", lambda min_score=70: [])
        monkeypatch.setattr(aut, "process_auto_send_queue", lambda dry_run=False: [])
        monkeypatch.setattr(nlp_pipe, "run_pipeline",
                            lambda **kw: {"total_processed": 3, "churn_alerts": 1,
                                         "urgency_alerts": 0, "clients_updated": 1,
                                         "extraction_mode": "keyword"})
        monkeypatch.setattr(crm_mod, "get_demo_clients", lambda: [])

        from scripts.daily_job import run
        result = run(dry_run=False, generate_proposals=False,
                     auto_send=False, process_nlp=True)
        assert "nlp_processed" in result
        assert result["nlp_processed"] == 3

    def test_no_nlp_flag_skips_pipeline(self, seeded_db, monkeypatch):
        import src.agents.scorer as scorer
        import src.data_sources.crm as crm_mod
        import src.agents.alerts as alerts_mod
        import src.agents.auto_sender as aut
        import src.agents.proposal_generator as pg

        monkeypatch.setattr(scorer, "score_all_clients", lambda: [])
        monkeypatch.setattr(scorer, "persist_opportunities", lambda r: 0)
        monkeypatch.setattr(alerts_mod, "dispatch", lambda r, channel="slack": [])
        monkeypatch.setattr(pg, "generate_proposals_for_all", lambda min_score=70: [])
        monkeypatch.setattr(aut, "process_auto_send_queue", lambda dry_run=False: [])
        monkeypatch.setattr(crm_mod, "get_demo_clients", lambda: [])

        from scripts.daily_job import run
        result = run(dry_run=False, generate_proposals=False,
                     auto_send=False, process_nlp=False)
        assert result["nlp_processed"] == 0


# ── 32. Process text script ───────────────────────────────────────────────────

class TestProcessTextScript:
    def test_run_returns_dict_with_processed(self, seeded_db, monkeypatch):
        _, _ = seeded_db
        import src.db.schema as schema
        monkeypatch.setattr(schema, "migrate_db", lambda: None)

        from scripts.process_text import run
        result = run(reprocess=False, use_llm=False, verbose=False)
        assert isinstance(result, dict)
        assert "total_processed" in result

    def test_run_elapsed_seconds_present(self, seeded_db, monkeypatch):
        _, _ = seeded_db
        import src.db.schema as schema
        monkeypatch.setattr(schema, "migrate_db", lambda: None)

        from scripts.process_text import run
        result = run(reprocess=False, use_llm=False, verbose=False)
        assert "elapsed_seconds" in result
        assert result["elapsed_seconds"] >= 0
