"""
Sprint 5 — Random Forest Model: Training, Evaluation & Persistence.

Model choice: RandomForestClassifier
  - Robust to outliers and missing features (common in agency data).
  - Natively produces probability estimates (predict_proba).
  - Compatible with SHAP TreeExplainer (fast, exact Shapley values).
  - Explainable to non-technical stakeholders via feature_importances_.

Persistence
-----------
  Model artifact : data/models/rf_model.joblib
  Metadata       : data/models/rf_metadata.json
  (both checked in via git LFS in production; in demo they live in the repo)

In production
-------------
  Training runs nightly if the feedback_log gained ≥ 10 new rows since last run.
  The retrain trigger is checked in the daily job (Sprint 4 extension).
  Model versioning: each retrain overwrites the artifact but appends a row to
  data/models/training_history.jsonl for audit.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    roc_auc_score, precision_score, recall_score, f1_score,
    average_precision_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.preprocessing import label_binarize

import config
from src.ml.dataset import FEATURE_NAMES

# ── Paths ─────────────────────────────────────────────────────────────────────
MODELS_DIR     = config.ROOT_DIR / "data" / "models"
MODEL_PATH     = MODELS_DIR / "rf_model.joblib"
METADATA_PATH  = MODELS_DIR / "rf_metadata.json"
HISTORY_PATH   = MODELS_DIR / "training_history.jsonl"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# ── Hyper-parameters ──────────────────────────────────────────────────────────
RF_PARAMS = {
    "n_estimators":     200,
    "max_depth":        8,
    "min_samples_leaf": 5,
    "class_weight":     "balanced",   # handles class imbalance automatically
    "random_state":     config.SYNTHETIC_SEED,
    "n_jobs":           -1,
}


# ── Training ──────────────────────────────────────────────────────────────────

def train(
    X: list[list[float]],
    y: list[int],
    feature_names: list[str] | None = None,
    cv_folds: int = 5,
    verbose: bool = True,
) -> dict[str, Any]:
    """
    Train a RandomForestClassifier with stratified cross-validation.

    Returns a metadata dict with evaluation metrics.
    The trained model is saved to MODEL_PATH.
    """
    if len(X) < 10:
        raise ValueError(
            f"Training requires at least 10 samples (got {len(X)}). "
            "Run `python scripts/seed_db.py` to populate the database."
        )

    Xarr = np.array(X, dtype=float)
    yarr = np.array(y, dtype=int)
    feature_names = feature_names or FEATURE_NAMES

    if verbose:
        print(f"[model] Training on {len(Xarr)} samples, {Xarr.shape[1]} features.")
        print(f"[model] Class balance: {yarr.sum()} positive / {(1-yarr).sum()} negative")

    # ── Cross-validation ──────────────────────────────────────────────────────
    clf = RandomForestClassifier(**RF_PARAMS)
    cv  = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)

    oof_proba = cross_val_predict(clf, Xarr, yarr, cv=cv, method="predict_proba")[:, 1]
    oof_pred  = (oof_proba >= 0.5).astype(int)

    metrics = {
        "auc_roc":          round(float(roc_auc_score(yarr, oof_proba)), 4),
        "avg_precision":    round(float(average_precision_score(yarr, oof_proba)), 4),
        "precision":        round(float(precision_score(yarr, oof_pred, zero_division=0)), 4),
        "recall":           round(float(recall_score(yarr, oof_pred, zero_division=0)), 4),
        "f1":               round(float(f1_score(yarr, oof_pred, zero_division=0)), 4),
    }

    if verbose:
        print(f"[model] CV AUC-ROC        : {metrics['auc_roc']:.4f}")
        print(f"[model] CV Avg Precision  : {metrics['avg_precision']:.4f}")
        print(f"[model] CV Precision      : {metrics['precision']:.4f}")
        print(f"[model] CV Recall         : {metrics['recall']:.4f}")
        print(f"[model] CV F1             : {metrics['f1']:.4f}")

    # ── Final fit on full dataset ─────────────────────────────────────────────
    clf.fit(Xarr, yarr)

    # ── Feature importance ────────────────────────────────────────────────────
    importances = {
        name: round(float(imp), 6)
        for name, imp in zip(feature_names, clf.feature_importances_)
    }

    # ── Metadata ──────────────────────────────────────────────────────────────
    metadata = {
        "trained_at":    datetime.now().isoformat(),
        "n_samples":     int(len(Xarr)),
        "n_features":    int(Xarr.shape[1]),
        "feature_names": feature_names,
        "cv_folds":      cv_folds,
        "rf_params":     RF_PARAMS,
        "metrics":       metrics,
        "feature_importance": importances,
        "_production_note": (
            "Production: model is retrained nightly if ≥ 10 new feedback rows "
            "since last training run. Artifact stored in S3 (versioned). "
            "Inference uses the latest artifact; rollback is available via "
            "METADATA_PATH → trained_at timestamp."
        ),
    }

    # ── Persist ───────────────────────────────────────────────────────────────
    joblib.dump(clf, MODEL_PATH)
    METADATA_PATH.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    # Append to training history
    with HISTORY_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "trained_at": metadata["trained_at"],
            "n_samples":  metadata["n_samples"],
            "metrics":    metrics,
        }) + "\n")

    if verbose:
        print(f"[model] Model saved to {MODEL_PATH}")

    return metadata


# ── Load ──────────────────────────────────────────────────────────────────────

def load_model() -> RandomForestClassifier | None:
    """Return the trained model, or None if not yet trained."""
    if not MODEL_PATH.exists():
        return None
    return joblib.load(MODEL_PATH)


def load_metadata() -> dict | None:
    """Return the last training metadata, or None."""
    if not METADATA_PATH.exists():
        return None
    return json.loads(METADATA_PATH.read_text())


def load_training_history() -> list[dict]:
    """Return all training run records (for audit / dashboard)."""
    if not HISTORY_PATH.exists():
        return []
    records = []
    for line in HISTORY_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records


# ── Predict ───────────────────────────────────────────────────────────────────

def predict_proba(
    feature_row: list[float],
    model: RandomForestClassifier | None = None,
) -> float:
    """
    Return the acceptance probability (0–1) for a single feature vector.
    Returns 0.5 if the model is not yet trained (neutral prior).
    """
    if model is None:
        model = load_model()
    if model is None:
        return 0.5

    X = np.array([feature_row], dtype=float)
    return float(model.predict_proba(X)[0, 1])


def model_is_trained() -> bool:
    return MODEL_PATH.exists()
