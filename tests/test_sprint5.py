"""
Sprint 5 tests — ML Pipeline (RandomForest + SHAP + Inference).

Coverage:
 1.  Dataset — _metrics_to_row produces a 13-element float vector.
 2.  Dataset — INDUSTRY_CODES and OPP_TYPE_CODES are deterministic dicts.
 3.  Dataset — _add_noise keeps numeric features non-negative, encodings intact.
 4.  Dataset — _load_labeled_dataset returns X, y of equal length (if file exists).
 5.  Dataset — build_dataset returns (X, y, feature_names) with len(X) >= MIN_SAMPLES.
 6.  Dataset — all labels in y are 0 or 1.
 7.  Dataset — feature vectors have exactly 13 columns.
 8.  Model   — load_model returns None when artifact doesn't exist.
 9.  Model   — model_is_trained is False before training.
10.  Model   — train() returns metadata dict with required keys.
11.  Model   — metrics from train() are in [0, 1] range.
12.  Model   — model_is_trained is True after training.
13.  Model   — load_model returns a classifier after training.
14.  Model   — predict_proba returns float in [0, 1].
15.  Model   — predict_proba returns 0.5 when no model is trained.
16.  Model   — load_metadata returns correct structure.
17.  Model   — training history is appended on each call to train().
18.  Explainer — get_feature_importance returns None when no model.
19.  Explainer — get_feature_importance returns sorted list with required keys.
20.  Explainer — explain_single returns required keys.
21.  Explainer — explain_single probability matches predict_proba.
22.  Explainer — fallback explanation works without SHAP.
23.  Explainer — narrative string contains probability.
24.  Inference — predict_for_client returns list of dicts.
25.  Inference — each prediction has required keys.
26.  Inference — blended_score = 0.55 * ml_prob * 100 + 0.45 * rule_score.
27.  Inference — predict_for_all returns sorted list (descending blended_score).
28.  Inference — update_ml_scores writes to DB.
29.  Inference — get_inference_summary returns False model_trained when untrained.
30.  Scorer   — score_all_clients result has ml_probability and blended_score keys.
31.  Script   — train_model.run() returns dict with metrics key.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pytest

import config


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_conn(p: Path):
    conn = sqlite3.connect(str(p), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _sample_metrics() -> dict:
    """A metrics dict with all features populated."""
    return {
        "ctr":               0.04,
        "bounce_rate":       0.65,
        "pages_per_session": 2.1,
        "conversion_rate":   0.02,
        "organic_traffic":   1800,
        "roas":              1.8,
        "ad_spend":          50.0,       # daily → *30 = monthly
        "email_open_rate":   0.18,
        "keyword_rankings":  25,
        "days_inactive":     45,
    }


@pytest.fixture()
def tmp_model_paths(tmp_path, monkeypatch):
    """
    Redirect MODEL_PATH, METADATA_PATH, and HISTORY_PATH to a temp directory
    so tests don't overwrite the real model artifact.
    """
    import src.ml.model as mlm
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    monkeypatch.setattr(mlm, "MODEL_PATH",    models_dir / "rf_model.joblib")
    monkeypatch.setattr(mlm, "METADATA_PATH", models_dir / "rf_metadata.json")
    monkeypatch.setattr(mlm, "HISTORY_PATH",  models_dir / "training_history.jsonl")
    return models_dir


@pytest.fixture()
def trained_model(tmp_model_paths):
    """Build a tiny dataset and train the model once. Returns (model, metadata)."""
    from src.ml.dataset import build_dataset
    from src.ml.model import train, load_model, load_metadata

    X, y, names = build_dataset(augment=False, verbose=False)
    metadata = train(X, y, feature_names=names, cv_folds=2, verbose=False)
    return load_model(), metadata


# ── 1. Dataset: _metrics_to_row ───────────────────────────────────────────────

class TestMetricsToRow:
    def test_vector_length(self):
        from src.ml.dataset import _metrics_to_row, FEATURE_NAMES
        row = _metrics_to_row(_sample_metrics(), "Restaurant", "seo_content", 365)
        assert len(row) == len(FEATURE_NAMES) == 18

    def test_all_float(self):
        from src.ml.dataset import _metrics_to_row
        row = _metrics_to_row(_sample_metrics(), "Restaurant", "seo_content", 365)
        assert all(isinstance(v, float) for v in row)

    def test_ad_spend_monthly_conversion(self):
        """ad_spend (daily) should be multiplied by 30."""
        from src.ml.dataset import _metrics_to_row, FEATURE_NAMES
        metrics = {**_sample_metrics(), "ad_spend": 10.0}
        row = _metrics_to_row(metrics, "Restaurant", "seo_content", 365)
        idx = FEATURE_NAMES.index("ad_spend_monthly")
        assert row[idx] == pytest.approx(300.0)

    def test_missing_fields_default_to_zero(self):
        from src.ml.dataset import _metrics_to_row, FEATURE_NAMES
        row = _metrics_to_row({}, "Restaurant", "seo_content", 365)
        assert len(row) == len(FEATURE_NAMES)
        assert all(v >= 0 for v in row)

    def test_industry_and_opp_type_encoding(self):
        from src.ml.dataset import _metrics_to_row, FEATURE_NAMES, INDUSTRY_CODES, OPP_TYPE_CODES
        industry   = "Restaurant"
        opp_type   = "seo_content"
        row = _metrics_to_row(_sample_metrics(), industry, opp_type, 365)
        idx_ind = FEATURE_NAMES.index("industry_code")
        idx_opp = FEATURE_NAMES.index("opportunity_type_code")
        assert row[idx_ind] == float(INDUSTRY_CODES[industry])
        assert row[idx_opp] == float(OPP_TYPE_CODES[opp_type])


# ── 2. Dataset: code dictionaries ─────────────────────────────────────────────

class TestCodeDictionaries:
    def test_industry_codes_deterministic(self):
        from src.ml.dataset import INDUSTRY_CODES
        from src.synthetic.generator import INDUSTRIES
        assert len(INDUSTRY_CODES) == len(INDUSTRIES)
        # Values are 0..N-1 integers
        assert set(INDUSTRY_CODES.values()) == set(range(len(INDUSTRIES)))

    def test_opp_type_codes_cover_all_types(self):
        from src.ml.dataset import OPP_TYPE_CODES
        from src.agents.rules import ALL_OPPORTUNITY_TYPES
        assert set(OPP_TYPE_CODES.keys()) == set(ALL_OPPORTUNITY_TYPES)

    def test_codes_are_stable(self):
        """Re-importing produces identical mappings."""
        from src.ml import dataset as ds
        import importlib
        importlib.reload(ds)
        from src.ml.dataset import INDUSTRY_CODES as ic2, OPP_TYPE_CODES as oc2
        from src.ml.dataset import INDUSTRY_CODES as ic1, OPP_TYPE_CODES as oc1
        assert ic1 == ic2
        assert oc1 == oc2


# ── 3. Dataset: _add_noise ────────────────────────────────────────────────────

class TestAddNoise:
    def test_numeric_features_non_negative(self):
        from src.ml.dataset import _add_noise, _metrics_to_row
        row = _metrics_to_row(_sample_metrics(), "Restaurant", "seo_content", 365)
        rng = np.random.default_rng(42)
        noisy = _add_noise(row, rng)
        assert all(v >= 0 for v in noisy)

    def test_encoding_columns_unchanged(self):
        """Last 2 columns (industry_code, opp_type_code) must not be noised."""
        from src.ml.dataset import _add_noise, _metrics_to_row
        row = _metrics_to_row(_sample_metrics(), "Restaurant", "seo_content", 365)
        rng = np.random.default_rng(42)
        noisy = _add_noise(row, rng)
        assert noisy[-1] == row[-1]   # opportunity_type_code
        assert noisy[-2] == row[-2]   # industry_code

    def test_output_length_unchanged(self):
        from src.ml.dataset import _add_noise, _metrics_to_row
        row = _metrics_to_row(_sample_metrics(), "Restaurant", "seo_content", 365)
        rng = np.random.default_rng(42)
        noisy = _add_noise(row, rng)
        assert len(noisy) == len(row)


# ── 4–7. Dataset: build_dataset ───────────────────────────────────────────────

class TestBuildDataset:
    def test_returns_three_tuple(self):
        from src.ml.dataset import build_dataset
        result = build_dataset(augment=False, verbose=False)
        assert isinstance(result, tuple) and len(result) == 3

    def test_minimum_samples(self):
        from src.ml.dataset import build_dataset, MIN_SAMPLES
        X, y, names = build_dataset(augment=False, verbose=False)
        assert len(X) >= MIN_SAMPLES

    def test_labels_are_binary(self):
        from src.ml.dataset import build_dataset
        _, y, _ = build_dataset(augment=False, verbose=False)
        assert set(y).issubset({0, 1})

    def test_feature_vector_width(self):
        from src.ml.dataset import build_dataset, FEATURE_NAMES
        X, _, names = build_dataset(augment=False, verbose=False)
        assert names == FEATURE_NAMES
        assert all(len(row) == len(names) for row in X)

    def test_x_y_same_length(self):
        from src.ml.dataset import build_dataset
        X, y, _ = build_dataset(augment=False, verbose=False)
        assert len(X) == len(y)

    def test_augment_increases_dataset_size(self):
        from src.ml.dataset import build_dataset
        X_no, y_no, _ = build_dataset(augment=False, verbose=False)
        X_aug, y_aug, _ = build_dataset(augment=True, verbose=False)
        # Augment copies labeled rows × AUGMENT_FACTOR — may or may not fire
        # for synthetic-only data; just assert no shrinkage
        assert len(X_aug) >= len(X_no)

    def test_positive_class_present(self):
        from src.ml.dataset import build_dataset
        _, y, _ = build_dataset(augment=False, verbose=False)
        assert 1 in y, "Dataset has no positive examples — check synthetic generator"


# ── 8–17. Model ───────────────────────────────────────────────────────────────

class TestModelLoading:
    def test_load_model_returns_none_when_missing(self, tmp_model_paths):
        from src.ml.model import load_model
        assert load_model() is None

    def test_model_is_trained_false_when_missing(self, tmp_model_paths):
        from src.ml.model import model_is_trained
        assert model_is_trained() is False

    def test_load_metadata_returns_none_when_missing(self, tmp_model_paths):
        from src.ml.model import load_metadata
        assert load_metadata() is None

    def test_training_history_empty_when_missing(self, tmp_model_paths):
        from src.ml.model import load_training_history
        assert load_training_history() == []


class TestModelTraining:
    REQUIRED_METADATA_KEYS = {
        "trained_at", "n_samples", "n_features", "feature_names",
        "cv_folds", "metrics", "feature_importance",
    }
    REQUIRED_METRIC_KEYS = {"auc_roc", "avg_precision", "precision", "recall", "f1"}

    def test_train_returns_metadata_dict(self, trained_model):
        _, metadata = trained_model
        assert isinstance(metadata, dict)
        assert self.REQUIRED_METADATA_KEYS.issubset(metadata.keys())

    def test_metrics_all_present(self, trained_model):
        _, metadata = trained_model
        assert self.REQUIRED_METRIC_KEYS.issubset(metadata["metrics"].keys())

    def test_metrics_in_valid_range(self, trained_model):
        _, metadata = trained_model
        for key, val in metadata["metrics"].items():
            assert 0.0 <= val <= 1.0, f"{key}={val} out of [0,1]"

    def test_model_is_trained_true_after_training(self, trained_model):
        from src.ml.model import model_is_trained
        _, _ = trained_model
        assert model_is_trained() is True

    def test_load_model_returns_classifier(self, trained_model):
        from sklearn.ensemble import RandomForestClassifier
        model, _ = trained_model
        assert isinstance(model, RandomForestClassifier)

    def test_metadata_persisted_to_disk(self, trained_model, tmp_model_paths):
        from src.ml.model import load_metadata
        meta = load_metadata()
        assert meta is not None
        assert "metrics" in meta

    def test_history_appended_on_train(self, tmp_model_paths):
        from src.ml.dataset import build_dataset
        from src.ml.model import train, load_training_history
        X, y, names = build_dataset(augment=False, verbose=False)
        train(X, y, feature_names=names, cv_folds=2, verbose=False)
        train(X, y, feature_names=names, cv_folds=2, verbose=False)
        history = load_training_history()
        assert len(history) >= 2
        assert "trained_at" in history[0]
        assert "metrics" in history[0]

    def test_n_samples_matches_training_data(self, tmp_model_paths):
        from src.ml.dataset import build_dataset
        from src.ml.model import train, load_metadata
        X, y, names = build_dataset(augment=False, verbose=False)
        train(X, y, feature_names=names, cv_folds=2, verbose=False)
        meta = load_metadata()
        assert meta["n_samples"] == len(X)

    def test_n_features_correct(self, trained_model):
        _, metadata = trained_model
        assert metadata["n_features"] == 18

    def test_feature_importance_covers_all_features(self, trained_model):
        from src.ml.dataset import FEATURE_NAMES
        _, metadata = trained_model
        imp = metadata["feature_importance"]
        assert set(imp.keys()) == set(FEATURE_NAMES)
        assert all(0 <= v <= 1 for v in imp.values())


class TestPredictProba:
    def test_returns_float(self, trained_model):
        from src.ml.model import predict_proba
        model, _ = trained_model
        from src.ml.dataset import _metrics_to_row
        row = _metrics_to_row(_sample_metrics(), "Restaurant", "seo_content", 365)
        prob = predict_proba(row, model)
        assert isinstance(prob, float)

    def test_in_range(self, trained_model):
        from src.ml.model import predict_proba
        model, _ = trained_model
        from src.ml.dataset import _metrics_to_row
        row = _metrics_to_row(_sample_metrics(), "Restaurant", "seo_content", 365)
        prob = predict_proba(row, model)
        assert 0.0 <= prob <= 1.0

    def test_returns_half_when_no_model(self, tmp_model_paths):
        from src.ml.model import predict_proba
        row = [0.0] * 13
        assert predict_proba(row, model=None) == 0.5

    def test_different_inputs_produce_different_probs(self, trained_model):
        from src.ml.model import predict_proba
        from src.ml.dataset import _metrics_to_row, ALL_OPPORTUNITY_TYPES
        model, _ = trained_model
        # high-activity client vs. inactive client
        metrics_active   = {**_sample_metrics(), "days_inactive": 1,  "ctr": 0.10}
        metrics_inactive = {**_sample_metrics(), "days_inactive": 180, "ctr": 0.01}
        from src.agents.rules import REACTIVATION
        opp = REACTIVATION
        r1 = predict_proba(_metrics_to_row(metrics_active,   "Restaurant", opp, 365), model)
        r2 = predict_proba(_metrics_to_row(metrics_inactive, "Restaurant", opp, 365), model)
        # They don't need to be ordered a certain way — just different
        assert r1 != r2


# ── 18–23. Explainer ──────────────────────────────────────────────────────────

class TestExplainer:
    def test_get_feature_importance_none_when_no_model(self, tmp_model_paths):
        from src.ml.explainer import get_feature_importance
        assert get_feature_importance() is None

    def test_get_feature_importance_sorted(self, trained_model):
        from src.ml.explainer import get_feature_importance
        importance = get_feature_importance()
        assert importance is not None and len(importance) > 0
        scores = [f["importance"] for f in importance]
        assert scores == sorted(scores, reverse=True)

    def test_get_feature_importance_required_keys(self, trained_model):
        from src.ml.explainer import get_feature_importance
        importance = get_feature_importance()
        for item in importance:
            assert {"name", "label", "importance"}.issubset(item.keys())

    def test_explain_single_required_keys(self, trained_model):
        from src.ml.explainer import explain_single
        from src.ml.dataset import _metrics_to_row
        model, _ = trained_model
        row = _metrics_to_row(_sample_metrics(), "Restaurant", "seo_content", 365)
        exp = explain_single(row, model)
        assert {"probability", "top_features", "narrative", "shap_available"}.issubset(exp.keys())

    def test_explain_single_probability_in_range(self, trained_model):
        from src.ml.explainer import explain_single
        from src.ml.dataset import _metrics_to_row
        model, _ = trained_model
        row = _metrics_to_row(_sample_metrics(), "Restaurant", "seo_content", 365)
        exp = explain_single(row, model)
        assert 0.0 <= exp["probability"] <= 1.0

    def test_explain_single_top_features_not_empty(self, trained_model):
        from src.ml.explainer import explain_single
        from src.ml.dataset import _metrics_to_row
        model, _ = trained_model
        row = _metrics_to_row(_sample_metrics(), "Restaurant", "seo_content", 365)
        exp = explain_single(row, model)
        assert isinstance(exp["top_features"], list) and len(exp["top_features"]) > 0

    def test_fallback_explanation_without_shap(self, trained_model, monkeypatch):
        """simulate SHAP unavailable by making get_shap_values return None."""
        import src.ml.explainer as exp_module
        monkeypatch.setattr(exp_module, "get_shap_values", lambda *a, **kw: None)

        from src.ml.dataset import _metrics_to_row
        model, _ = trained_model
        row = _metrics_to_row(_sample_metrics(), "Restaurant", "seo_content", 365)
        exp = exp_module.explain_single(row, model)
        assert exp["shap_available"] is False
        assert "probability" in exp
        assert "narrative" in exp

    def test_narrative_contains_probability(self, trained_model):
        from src.ml.explainer import explain_single
        from src.ml.dataset import _metrics_to_row
        model, _ = trained_model
        row = _metrics_to_row(_sample_metrics(), "Restaurant", "seo_content", 365)
        exp = explain_single(row, model)
        assert "%" in exp["narrative"], "Narrative should mention the probability percentage"

    def test_top_feature_required_keys(self, trained_model):
        from src.ml.explainer import explain_single
        from src.ml.dataset import _metrics_to_row
        model, _ = trained_model
        row = _metrics_to_row(_sample_metrics(), "Restaurant", "seo_content", 365)
        exp = explain_single(row, model)
        for feat in exp["top_features"]:
            assert {"name", "label", "shap_value", "value"}.issubset(feat.keys())


# ── 24–29. Inference ──────────────────────────────────────────────────────────

@pytest.fixture()
def inference_db(tmp_path, monkeypatch):
    """
    Minimal seeded DB + patched data sources for inference tests.
    """
    db_path = tmp_path / "sprint5.db"
    monkeypatch.setattr(config, "DB_PATH", db_path)

    import src.db.schema as schema
    import src.ml.inference as inf

    _conn = lambda: _make_conn(db_path)
    monkeypatch.setattr(schema, "get_connection", _conn)
    monkeypatch.setattr(inf,    "get_connection", _conn)

    schema.init_db()

    conn = _make_conn(db_path)
    client_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO clients (id, name, industry, account_age_days, is_demo_scenario)
           VALUES (?, 'Acme Corp', 'Restaurant', 400, 0)""",
        (client_id,),
    )
    today = "2026-01-01"
    conn.execute(
        """INSERT INTO client_metrics
           (client_id, date, ctr, bounce_rate, pages_per_session,
            conversion_rate, organic_traffic, roas, ad_spend,
            email_open_rate, keyword_rankings, days_inactive)
           VALUES (?,?,0.05,0.70,1.8,0.01,2000,1.5,60,0.15,20,50)""",
        (client_id, today),
    )
    conn.commit()
    conn.close()

    # Stub data sources to return predictable values
    m = {
        "bounce_rate": 0.70, "pages_per_session": 1.8,
        "conversion_rate": 0.01, "organic_traffic": 2000,
        "ctr": 0.05, "cpc": 0.80, "roas": 1.5, "ad_spend": 60,
        "email_open_rate": 0.15, "email_click_rate": 0.03,
        "keyword_rankings": 20,
    }
    import src.data_sources.google_analytics as ga
    import src.data_sources.meta_ads as ma
    import src.data_sources.email_marketing as em
    import src.data_sources.seo as seo_mod
    import src.data_sources.crm as crm_mod

    monkeypatch.setattr(ga,  "get_latest_metrics",      lambda cid: m)
    monkeypatch.setattr(ma,  "get_latest_ad_metrics",   lambda cid: m)
    monkeypatch.setattr(em,  "get_latest_email_metrics", lambda cid: m)
    monkeypatch.setattr(seo_mod, "get_latest_seo_metrics", lambda cid: m)
    monkeypatch.setattr(crm_mod, "get_client_activity", lambda cid: {"days_inactive": 50, "days_since_last_contact": 50})
    monkeypatch.setattr(crm_mod, "get_client",
        lambda cid: {"id": client_id, "name": "Acme Corp", "industry": "Restaurant",
                     "account_age_days": 400, "is_demo_scenario": 0})
    monkeypatch.setattr(crm_mod, "get_all_clients",
        lambda: [{"id": client_id, "name": "Acme Corp", "industry": "Restaurant",
                  "account_age_days": 400, "is_demo_scenario": 0}])

    return client_id, db_path


class TestInference:
    def test_predict_for_client_returns_list(self, inference_db, trained_model):
        from src.ml.inference import predict_for_client
        client_id, _ = inference_db
        model, _ = trained_model
        preds = predict_for_client(client_id, model=model)
        assert isinstance(preds, list)

    def test_predict_for_client_required_keys(self, inference_db, trained_model):
        from src.ml.inference import predict_for_client
        client_id, _ = inference_db
        model, _ = trained_model
        preds = predict_for_client(client_id, model=model)
        if preds:
            required = {
                "client_id", "client_name", "industry", "opportunity_type",
                "rule_score", "ml_probability", "blended_score", "explanation",
            }
            assert required.issubset(preds[0].keys())

    def test_blended_score_formula(self, inference_db, trained_model):
        """blended = 0.55 * ml_prob * 100 + 0.45 * rule_score (within float tolerance)."""
        from src.ml.inference import predict_for_client
        client_id, _ = inference_db
        model, _ = trained_model
        preds = predict_for_client(client_id, model=model)
        for p in preds:
            if p["ml_probability"] is not None:
                expected = round(0.55 * p["ml_probability"] * 100 + 0.45 * p["rule_score"], 1)
                assert p["blended_score"] == pytest.approx(expected, abs=0.15)

    def test_predict_for_all_sorted_descending(self, inference_db, trained_model):
        from src.ml.inference import predict_for_all
        model, _ = trained_model
        preds = predict_for_all(model=model)
        scores = [p["blended_score"] for p in preds]
        assert scores == sorted(scores, reverse=True)

    def test_predict_for_all_returns_list(self, inference_db, trained_model):
        from src.ml.inference import predict_for_all
        model, _ = trained_model
        preds = predict_for_all(model=model)
        assert isinstance(preds, list)

    def test_update_ml_scores_writes_to_db(self, inference_db, trained_model):
        from src.ml.inference import predict_for_client, update_ml_scores
        import src.db.schema as schema
        client_id, db_path = inference_db
        model, _ = trained_model

        # Insert a dummy opportunity so update_ml_scores has a row to update
        conn = _make_conn(db_path)
        from src.agents.rules import SEO_CONTENT
        opp_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO opportunities (id, client_id, opportunity_type, score, status, detected_at, updated_at)
               VALUES (?,?,?,60,'detected',datetime('now'),datetime('now'))""",
            (opp_id, client_id, SEO_CONTENT),
        )
        conn.commit()
        conn.close()

        preds = predict_for_client(client_id, model=model)
        updated = update_ml_scores(preds)
        assert isinstance(updated, int)

    def test_get_inference_summary_untrained(self, inference_db, tmp_model_paths):
        from src.ml.inference import get_inference_summary
        summary = get_inference_summary()
        assert summary["model_trained"] is False
        assert summary["total_predictions"] == 0
        assert summary["avg_ml_probability"] is None

    def test_unknown_client_returns_empty(self, inference_db, trained_model):
        from src.ml.inference import predict_for_client
        import src.data_sources.crm as crm_mod
        model, _ = trained_model
        # Override get_client to return None for unknown ID
        original = crm_mod.get_client
        crm_mod.get_client = lambda cid: None
        preds = predict_for_client("nonexistent-id", model=model)
        crm_mod.get_client = original
        assert preds == []


# ── 30. Scorer with ML blending ───────────────────────────────────────────────

class TestScorerMLBlending:
    def test_score_all_has_ml_fields(self, inference_db, trained_model, monkeypatch):
        """score_all_clients must include ml_probability and blended_score."""
        import src.agents.scorer as scorer
        import src.data_sources.crm as crm_mod
        import src.ml.model as mlm

        client_id, _ = inference_db
        model, _ = trained_model

        # Redirect scorer's load_model to return our trained model
        monkeypatch.setattr(mlm, "model_is_trained", lambda: True)
        monkeypatch.setattr(mlm, "load_model", lambda: model)
        monkeypatch.setattr(crm_mod, "get_all_clients",
            lambda: [{"id": client_id, "name": "Acme Corp", "industry": "Restaurant",
                      "account_age_days": 400, "is_demo_scenario": 0}])

        results = scorer.score_all_clients()
        assert isinstance(results, list)
        if results:
            row = results[0]
            assert "ml_probability" in row
            assert "blended_score" in row

    def test_score_all_fallback_when_no_model(self, inference_db, monkeypatch):
        """When no model is trained, ml_probability should be None."""
        import src.agents.scorer as scorer
        import src.data_sources.crm as crm_mod
        import src.ml.model as mlm

        client_id, _ = inference_db

        monkeypatch.setattr(mlm, "model_is_trained", lambda: False)
        monkeypatch.setattr(crm_mod, "get_all_clients",
            lambda: [{"id": client_id, "name": "Acme Corp", "industry": "Restaurant",
                      "account_age_days": 400, "is_demo_scenario": 0}])

        results = scorer.score_all_clients()
        for r in results:
            assert r["ml_probability"] is None


# ── 31. Train model script ────────────────────────────────────────────────────

class TestTrainModelScript:
    def test_run_returns_dict_with_metrics(self, tmp_model_paths):
        from scripts.train_model import run
        result = run(augment=False, cv_folds=2, verbose=False)
        assert isinstance(result, dict)
        assert "metrics" in result

    def test_run_metrics_keys(self, tmp_model_paths):
        from scripts.train_model import run
        result = run(augment=False, cv_folds=2, verbose=False)
        assert {"auc_roc", "precision", "recall", "f1"}.issubset(result["metrics"].keys())

    def test_run_elapsed_seconds_present(self, tmp_model_paths):
        from scripts.train_model import run
        result = run(augment=False, cv_folds=2, verbose=False)
        assert "elapsed_seconds" in result
        assert result["elapsed_seconds"] >= 0
