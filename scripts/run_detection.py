"""
Sprint 1 — Detection CLI.

Applies the rules engine to all clients and prints a ranked opportunity table.
Optionally persists results to the database.

Usage:
    python scripts/run_detection.py                     # show all opportunities
    python scripts/run_detection.py --demo-only         # show only demo scenario clients
    python scripts/run_detection.py --save              # persist to DB as well
    python scripts/run_detection.py --client demo-001   # single client
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.scorer import score_all_clients, score_client, persist_opportunities
from src.agents.rules import OPPORTUNITY_LABELS


# ── Formatting helpers ────────────────────────────────────────────────────────

def _bar(score: float, width: int = 20) -> str:
    filled = int(score / 100 * width)
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def _score_color(score: float) -> str:
    if score >= 80:
        return "HIGH "
    if score >= 60:
        return "MED  "
    return "LOW  "


def _print_opportunity(r: dict, rank: int) -> None:
    demo_tag = " [DEMO]" if r.get("is_demo_scenario") else ""
    print(f"\n  #{rank:02d}  {r['client_name']}{demo_tag}  ({r['industry']})")
    print(f"       Opportunity : {r['label']}")
    print(f"       Score       : {_score_color(r['score'])}{_bar(r['score'])} {r['score']:.1f}/100")
    print(f"       Price       : ${r['suggested_price']:,.0f}")
    print(f"       Signals     : {', '.join(r['triggered_signals'])}")
    print(f"       Rationale   : {r['rationale']}")


def _print_summary(results: list[dict]) -> None:
    from collections import Counter
    type_counts = Counter(r["opportunity_type"] for r in results)
    print("\n  -- Opportunity breakdown --")
    for opp_type, count in type_counts.most_common():
        print(f"     {OPPORTUNITY_LABELS[opp_type]:<30} {count:>3} clients")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Hidden Opportunities detection engine.")
    parser.add_argument("--demo-only",  action="store_true", help="Show only demo scenario clients.")
    parser.add_argument("--save",       action="store_true", help="Persist opportunities to the database.")
    parser.add_argument("--client",     type=str,            help="Score a single client by ID.")
    parser.add_argument("--min-score",  type=float, default=0, help="Only show opportunities above this score.")
    args = parser.parse_args()

    print("\n" + "=" * 65)
    print("  Hidden Opportunities Agent -- Detection Engine (Sprint 1)")
    print("  Mode: Rule-based heuristics")
    print("=" * 65)

    if args.client:
        from src.data_sources.crm import get_client
        client = get_client(args.client)
        name = client["name"] if client else args.client
        print(f"\n  Scoring client: {name} ({args.client})")
        opps = score_client(args.client)
        if not opps:
            print("  No opportunities detected.")
            return
        for i, opp in enumerate(opps, 1):
            r = {
                "client_id":        args.client,
                "client_name":      name,
                "industry":         client.get("industry", "?") if client else "?",
                "opportunity_type": opp.opportunity_type,
                "label":            opp.label,
                "score":            opp.score,
                "suggested_price":  opp.suggested_price,
                "rationale":        opp.rationale,
                "triggered_signals": opp.triggered_signals,
                "is_demo_scenario": client.get("is_demo_scenario", 0) if client else 0,
            }
            _print_opportunity(r, i)
        return

    print("\n  Scanning all clients...\n")
    all_results = score_all_clients()

    if args.demo_only:
        results = [r for r in all_results if r["is_demo_scenario"]]
        print(f"  Showing demo scenario clients only ({len(results)} opportunities)")
    else:
        results = [r for r in all_results if r["score"] >= args.min_score]
        print(f"  Total opportunities detected: {len(results)} across {len({r['client_id'] for r in results})} clients")

    print(f"  Min score filter: {args.min_score}")
    print("-" * 65)

    for i, r in enumerate(results, 1):
        _print_opportunity(r, i)

    _print_summary(results)

    if args.save:
        n = persist_opportunities(all_results)
        print(f"\n  [db] Persisted {n} new opportunities to the database.")

    print("\n" + "=" * 65 + "\n")


if __name__ == "__main__":
    main()
