import json
from pathlib import Path
from fastapi import APIRouter
from src.agents.rules import evaluate, OPPORTUNITY_LABELS

router = APIRouter(tags=["accuracy"])

_LABELED_PATH = Path(__file__).parent.parent.parent / "data" / "synthetic" / "labeled_test_dataset.json"


@router.get("/accuracy")
def get_accuracy() -> dict:
    cases = json.loads(_LABELED_PATH.read_text())
    rows = []
    tp = fp = fn = 0

    for case in cases:
        detected = {r.opportunity_type for r in evaluate(case["metrics"])}
        expected = set(case["expected_opportunities"])

        case_tp = len(detected & expected)
        case_fp = len(detected - expected)
        case_fn = len(expected - detected)
        tp += case_tp
        fp += case_fp
        fn += case_fn

        rows.append({
            "client":   case["client_name"],
            "expected": ", ".join(OPPORTUNITY_LABELS.get(o, o) for o in sorted(expected)) or "—",
            "detected": ", ".join(OPPORTUNITY_LABELS.get(o, o) for o in sorted(detected)) or "—",
            "tp": case_tp,
            "fp": case_fp,
            "fn": case_fn,
            "status": (
                "Perfect" if detected == expected
                else ("Extra" if case_fp > 0 else "Missed")
            ),
        })

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return {
        "rows": rows,
        "metrics": {
            "precision": round(precision, 4),
            "recall":    round(recall, 4),
            "f1":        round(f1, 4),
            "tp": tp, "fp": fp, "fn": fn,
        },
    }
