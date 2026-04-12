"""
Sprint 5 — Standalone Model Training Script.

Builds the training dataset, trains a RandomForestClassifier with
cross-validation, computes SHAP explanations, and saves the artifact.

Usage:
    python scripts/train_model.py
    python scripts/train_model.py --no-augment    # skip noise augmentation
    python scripts/train_model.py --cv-folds 3    # fewer folds for speed

In production this script is triggered:
  1. By the daily job (scripts/daily_job.py) when ≥ 10 new feedback rows exist.
  2. Manually via CI/CD pipeline after a large batch of new client data arrives.
  3. From the "Retrain" button in the ML dashboard UI.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ml.dataset import build_dataset, MIN_SAMPLES
from src.ml.model import train, MODEL_PATH, METADATA_PATH


def run(augment: bool = True, cv_folds: int = 5, verbose: bool = True) -> dict:
    start = datetime.now()

    print(f"\n{'='*55}")
    print(f"  Hidden Opportunities Agent — Model Training")
    print(f"  {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*55}\n")

    # ── Build dataset ─────────────────────────────────────────────────────────
    print("[1/3] Building dataset…")
    X, y, feature_names = build_dataset(augment=augment, verbose=verbose)

    if len(X) < MIN_SAMPLES:
        print(
            f"\n[WARN] Only {len(X)} training samples (minimum: {MIN_SAMPLES}). "
            f"Training anyway, but metrics may be unreliable.\n"
        )

    # ── Train ─────────────────────────────────────────────────────────────────
    print(f"\n[2/3] Training RandomForest (cv_folds={cv_folds})…")
    metadata = train(X, y, feature_names=feature_names, cv_folds=cv_folds, verbose=verbose)

    # ── Summary ───────────────────────────────────────────────────────────────
    elapsed = (datetime.now() - start).total_seconds()
    m = metadata["metrics"]

    print(f"\n[3/3] Training complete in {elapsed:.1f}s")
    print(f"      Artifact  : {MODEL_PATH}")
    print(f"      Metadata  : {METADATA_PATH}")
    print(f"\n      AUC-ROC   : {m['auc_roc']:.4f}")
    print(f"      Precision : {m['precision']:.4f}")
    print(f"      Recall    : {m['recall']:.4f}")
    print(f"      F1        : {m['f1']:.4f}")
    print(f"\n      Top features by importance:")
    top5 = sorted(metadata["feature_importance"].items(), key=lambda kv: kv[1], reverse=True)[:5]
    for name, imp in top5:
        print(f"        {name:<28} {imp:.4f}")
    print(f"\n{'='*55}\n")

    return {**metadata, "elapsed_seconds": round(elapsed, 2)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train the Random Forest model.")
    parser.add_argument("--no-augment", action="store_true",
                        help="Skip noise augmentation of labeled data.")
    parser.add_argument("--cv-folds", type=int, default=5,
                        help="Number of cross-validation folds (default: 5).")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress verbose logging.")
    args = parser.parse_args()
    run(augment=not args.no_augment, cv_folds=args.cv_folds, verbose=not args.quiet)
