"""
Sprint 3 — Daily Job Runner (updated).

Orchestrates the full daily detection + proposal pipeline:
  1. Pull latest metrics from all data sources (demo: SQLite)
  2. Apply rules engine to every client
  3. Persist new opportunities to the DB
  4. Format and dispatch alerts (demo: log file; production: Slack/Telegram)
  5. Generate proposals for high-confidence opportunities (Sprint 3)
  6. Print a run summary

In production this script would be triggered by a cron job or a scheduler
(e.g., crontab, GitHub Actions schedule, n8n, or Make).

  Production cron (every morning at 8am):
      0 8 * * * cd /app && python scripts/daily_job.py >> logs/cron.log 2>&1

Usage:
    python scripts/daily_job.py                         # run for all clients
    python scripts/daily_job.py --demo-only             # run only for demo scenario clients
    python scripts/daily_job.py --channel telegram      # dispatch to telegram instead
    python scripts/daily_job.py --dry-run               # detect + format but do not persist/dispatch
    python scripts/daily_job.py --no-proposals          # skip proposal generation
    python scripts/daily_job.py --proposal-min-score 80 # generate proposals only for score >= 80
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from src.agents.scorer import score_all_clients, persist_opportunities
from src.agents.alerts import dispatch
from src.agents.proposal_generator import generate_proposals_for_all
from src.data_sources.crm import get_demo_clients


_PRODUCTION_NOTE = (
    "In production this script runs daily via cron (0 8 * * *) on the agency server. "
    "Data sources are live API calls. Alerts are POSTed to Slack and/or Telegram."
)


def run(
    demo_only: bool = False,
    channel: str = "slack",
    dry_run: bool = False,
    generate_proposals: bool = True,
    proposal_min_score: float = 70.0,
) -> dict:
    start = datetime.now()
    print(f"\n{'='*60}")
    print(f"  Hidden Opportunities Agent -- Daily Job")
    print(f"  {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Demo mode  : {config.DEMO_MODE}")
    print(f"  Dry run    : {dry_run}")
    print(f"  Channel    : {channel}")
    print(f"  Production : {_PRODUCTION_NOTE}")
    print(f"{'='*60}\n")

    # ── Step 1: Score all clients ─────────────────────────────────────────────
    print("[1/4] Running detection engine...")
    all_results = score_all_clients()

    if demo_only:
        demo_ids = {c["id"] for c in get_demo_clients()}
        results = [r for r in all_results if r["client_id"] in demo_ids]
        print(f"      Filtered to demo clients: {len(results)} opportunities")
    else:
        results = all_results
        print(f"      Total opportunities detected: {len(results)}")

    # Summarise by type
    from collections import Counter
    by_type = Counter(r["opportunity_type"] for r in results)
    for opp_type, count in by_type.most_common():
        from src.agents.rules import OPPORTUNITY_LABELS
        print(f"        {OPPORTUNITY_LABELS.get(opp_type, opp_type):<32} {count:>3}")

    # ── Step 2: Persist to DB ─────────────────────────────────────────────────
    print("\n[2/4] Persisting to database...")
    if dry_run:
        print("      [dry-run] Skipped.")
        n_new = 0
    else:
        n_new = persist_opportunities(all_results)
        print(f"      {n_new} new opportunities inserted.")

    # ── Step 3: Dispatch alerts ───────────────────────────────────────────────
    # Only alert on HIGH and MEDIUM confidence opportunities
    alertable = [r for r in results if r["score"] >= 60]
    print(f"\n[3/4] Dispatching alerts for {len(alertable)} high/medium-confidence opportunities...")

    if dry_run:
        print("      [dry-run] Skipped.")
        dispatched = []
    else:
        dispatched = dispatch(alertable, channel=channel)
        if config.DEMO_MODE:
            print(f"      [DEMO] {len(dispatched)} alerts written to logs/alerts.jsonl")
        else:
            print(f"      {len(dispatched)} alerts sent to {channel}.")

    # ── Step 3b: Generate proposals ──────────────────────────────────────────
    n_proposals = 0
    if generate_proposals and not dry_run:
        print(f"\n[3b/4] Generating proposals for opportunities with score >= {proposal_min_score}...")
        proposal_results = generate_proposals_for_all(min_score=proposal_min_score)
        new_proposals    = [r for r in proposal_results if not r.get("already_existed")]
        n_proposals      = len(new_proposals)
        if config.DEMO_MODE:
            print(f"      [DEMO] {n_proposals} new proposal(s) saved to data/exports/proposals/")
        else:
            print(f"      {n_proposals} new proposal(s) generated. Account managers notified.")
    elif dry_run:
        print("\n[3b/4] [dry-run] Proposal generation skipped.")
    else:
        print("\n[3b/4] Proposal generation disabled (--no-proposals).")

    # ── Step 4: Summary ───────────────────────────────────────────────────────
    elapsed = (datetime.now() - start).total_seconds()
    summary = {
        "run_at":              start.isoformat(),
        "elapsed_seconds":     round(elapsed, 2),
        "clients_scanned":     len({r["client_id"] for r in all_results}),
        "opportunities_found": len(results),
        "new_in_db":           n_new,
        "alerts_dispatched":   len(dispatched),
        "proposals_generated": n_proposals,
        "by_type":             dict(by_type),
        "demo_mode":           config.DEMO_MODE,
        "dry_run":             dry_run,
    }

    print(f"\n[4/4] Summary")
    print(f"      Clients scanned        : {summary['clients_scanned']}")
    print(f"      Opportunities found    : {summary['opportunities_found']}")
    print(f"      New in DB              : {summary['new_in_db']}")
    print(f"      Alerts dispatched      : {summary['alerts_dispatched']}")
    print(f"      Proposals generated    : {summary['proposals_generated']}")
    print(f"      Elapsed                : {summary['elapsed_seconds']}s")
    print(f"\n{'='*60}\n")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the daily detection and alert pipeline.")
    parser.add_argument("--demo-only",           action="store_true",  help="Only process demo scenario clients.")
    parser.add_argument("--channel",             default="slack",      choices=["slack", "telegram", "both"])
    parser.add_argument("--dry-run",             action="store_true",  help="Detect but do not persist or dispatch.")
    parser.add_argument("--no-proposals",        action="store_true",  help="Skip proposal generation step.")
    parser.add_argument("--proposal-min-score",  type=float, default=70.0,
                        help="Minimum opportunity score to generate a proposal (default: 70).")
    args = parser.parse_args()
    run(
        demo_only          = args.demo_only,
        channel            = args.channel,
        dry_run            = args.dry_run,
        generate_proposals = not args.no_proposals,
        proposal_min_score = args.proposal_min_score,
    )
