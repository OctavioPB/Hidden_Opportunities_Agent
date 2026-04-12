"""
Sprint 6 — Standalone Text Signal Processing Script.

Runs the NLP pipeline over all unprocessed text in the database:
  1. Loads raw emails / call transcripts / CRM notes from text_signals table.
  2. Extracts sentiment, price mentions, churn risk, and other signals.
  3. Writes results back to the DB.
  4. Prints a summary of alerts detected.

Usage:
    python scripts/process_text.py
    python scripts/process_text.py --reprocess   # reprocess already-done rows
    python scripts/process_text.py --use-llm     # enable LLM extraction

In production this script is triggered:
  1. Nightly by the daily job (after new emails are ingested from Gmail/CRM API).
  2. Immediately when a new email is received (webhook → trigger).
  3. Manually from the "Process Emails" button in the Text Signals dashboard.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.schema import migrate_db
from src.nlp.pipeline import run_pipeline, get_pipeline_summary


def run(
    reprocess: bool = False,
    use_llm: bool = False,
    verbose: bool = True,
) -> dict:
    start = datetime.now()

    print(f"\n{'='*55}")
    print(f"  Hidden Opportunities Agent — Text Processing")
    print(f"  {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*55}\n")

    # Ensure schema is up to date (adds interest_signal if missing)
    migrate_db()

    # Run pipeline
    summary = run_pipeline(
        reprocess_all=reprocess,
        use_llm=use_llm,
        verbose=verbose,
    )

    elapsed = (datetime.now() - start).total_seconds()

    # Print results
    print(f"\n[3/3] Processing complete in {elapsed:.1f}s")
    print(f"      Rows processed : {summary['total_processed']}")
    print(f"      Clients updated: {summary['clients_updated']}")
    print(f"      Churn alerts   : {summary['churn_alerts']}")
    print(f"      Urgency alerts : {summary['urgency_alerts']}")
    print(f"      Mode           : {summary['extraction_mode']}")

    # Full DB summary
    db_summary = get_pipeline_summary()
    print(f"\n      DB totals:")
    print(f"        Total signals   : {db_summary['total_signals']}")
    print(f"        Processed       : {db_summary['processed']}")
    print(f"        Unprocessed     : {db_summary['unprocessed']}")
    print(f"        Churn flags     : {db_summary['churn_count']}")
    print(f"        Urgency flags   : {db_summary['urgency_count']}")
    print(f"\n{'='*55}\n")

    return {**summary, "elapsed_seconds": round(elapsed, 2)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process text signals with NLP pipeline.")
    parser.add_argument("--reprocess", action="store_true",
                        help="Reprocess rows that already have signals.")
    parser.add_argument("--use-llm", action="store_true",
                        help="Use LLM for richer extraction (requires API key).")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress verbose logging.")
    args = parser.parse_args()
    run(reprocess=args.reprocess, use_llm=args.use_llm, verbose=not args.quiet)
