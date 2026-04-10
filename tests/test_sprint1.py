"""
Sprint 1 tests.

1. Rules engine unit tests — each rule fires (and only fires) on the right inputs.
2. Labeled dataset validation — rules produce the expected opportunities for all 10 test clients.
3. Demo scenario validation — the 5 demo clients trigger the opportunities they were designed for.
4. Scorer integration — scorer fetches data from DB and calls the rules correctly.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.agents import rules as R
from src.agents.rules import evaluate, evaluate_top


# ── Fixtures ──────────────────────────────────────────────────────────────────

HEALTHY = {
    "ctr": 0.031, "bounce_rate": 0.52, "pages_per_session": 3.3,
    "conversion_rate": 0.045, "organic_traffic": 3000, "keyword_rankings": 48,
    "email_open_rate": 0.29, "email_click_rate": 0.065,
    "ad_spend": 55.0, "roas": 3.8,
    "days_inactive": 3, "days_since_last_contact": 3,
}


# ── Rule 1: Landing Page Optimization ─────────────────────────────────────────

def test_rule1_fires_on_trigger():
    m = {**HEALTHY, "ctr": 0.052, "bounce_rate": 0.78, "pages_per_session": 1.3}
    result = R.rule_landing_page_optimization(m)
    assert result is not None
    assert result.opportunity_type == R.LANDING_PAGE_OPTIMIZATION
    assert result.score > 0


def test_rule1_no_fire_healthy():
    assert R.rule_landing_page_optimization(HEALTHY) is None


def test_rule1_no_fire_low_ctr():
    m = {**HEALTHY, "ctr": 0.02, "bounce_rate": 0.80, "pages_per_session": 1.5}
    assert R.rule_landing_page_optimization(m) is None


def test_rule1_no_fire_low_bounce():
    m = {**HEALTHY, "ctr": 0.06, "bounce_rate": 0.50, "pages_per_session": 1.5}
    assert R.rule_landing_page_optimization(m) is None


# ── Rule 2: SEO Content ────────────────────────────────────────────────────────

def test_rule2_fires_on_trigger():
    m = {**HEALTHY, "organic_traffic": 2500, "keyword_rankings": 9, "conversion_rate": 0.011}
    result = R.rule_seo_content(m)
    assert result is not None
    assert result.opportunity_type == R.SEO_CONTENT


def test_rule2_no_fire_high_traffic_good_rankings():
    m = {**HEALTHY, "organic_traffic": 5000, "keyword_rankings": 60, "conversion_rate": 0.01}
    assert R.rule_seo_content(m) is None


# ── Rule 3: Retargeting Campaign ──────────────────────────────────────────────

def test_rule3_fires_on_trigger():
    m = {**HEALTHY, "ad_spend": 90.0, "roas": 1.6}   # monthly ~$2700
    result = R.rule_retargeting_campaign(m)
    assert result is not None
    assert result.opportunity_type == R.RETARGETING_CAMPAIGN


def test_rule3_no_fire_good_roas():
    m = {**HEALTHY, "ad_spend": 90.0, "roas": 3.5}
    assert R.rule_retargeting_campaign(m) is None


def test_rule3_no_fire_low_spend():
    m = {**HEALTHY, "ad_spend": 20.0, "roas": 1.5}   # monthly ~$600 < $2000
    assert R.rule_retargeting_campaign(m) is None


# ── Rule 4: Email Automation ──────────────────────────────────────────────────

def test_rule4_fires_on_trigger():
    m = {**HEALTHY, "email_open_rate": 0.09}
    result = R.rule_email_automation(m)
    assert result is not None
    assert result.opportunity_type == R.EMAIL_AUTOMATION


def test_rule4_score_increases_with_lower_open_rate():
    r_low  = R.rule_email_automation({**HEALTHY, "email_open_rate": 0.05})
    r_mid  = R.rule_email_automation({**HEALTHY, "email_open_rate": 0.12})
    assert r_low.score > r_mid.score


def test_rule4_no_fire_good_open_rate():
    m = {**HEALTHY, "email_open_rate": 0.25}
    assert R.rule_email_automation(m) is None


# ── Rule 5: Reactivation ──────────────────────────────────────────────────────

def test_rule5_fires_on_trigger():
    m = {**HEALTHY, "days_inactive": 52}
    result = R.rule_reactivation(m)
    assert result is not None
    assert result.opportunity_type == R.REACTIVATION


def test_rule5_boundary_at_45():
    assert R.rule_reactivation({**HEALTHY, "days_inactive": 44}) is None
    assert R.rule_reactivation({**HEALTHY, "days_inactive": 45}) is not None


# ── Rule 6: Conversion Rate Audit ─────────────────────────────────────────────

def test_rule6_fires_on_trigger():
    m = {**HEALTHY, "ctr": 0.072, "conversion_rate": 0.005}
    result = R.rule_conversion_rate_audit(m)
    assert result is not None
    assert result.opportunity_type == R.CONVERSION_RATE_AUDIT


def test_rule6_no_fire_decent_conversion():
    m = {**HEALTHY, "ctr": 0.072, "conversion_rate": 0.025}
    assert R.rule_conversion_rate_audit(m) is None


# ── Rule 7: Upsell Ad Budget ──────────────────────────────────────────────────

def test_rule7_fires_on_trigger():
    m = {**HEALTHY, "roas": 5.2, "ad_spend": 18.0}   # monthly ~$540
    result = R.rule_upsell_ad_budget(m)
    assert result is not None
    assert result.opportunity_type == R.UPSELL_AD_BUDGET


def test_rule7_no_fire_high_spend_already():
    m = {**HEALTHY, "roas": 5.2, "ad_spend": 40.0}   # monthly ~$1200 > $800
    assert R.rule_upsell_ad_budget(m) is None


# ── evaluate() multi-rule ─────────────────────────────────────────────────────

def test_evaluate_returns_multiple_opportunities():
    # test-010 profile: landing page + email + retargeting
    m = {
        "ctr": 0.051, "bounce_rate": 0.76, "pages_per_session": 1.7,
        "conversion_rate": 0.008, "organic_traffic": 400, "keyword_rankings": 6,
        "email_open_rate": 0.11, "email_click_rate": 0.015,
        "ad_spend": 80.0, "roas": 1.5,
        "days_inactive": 15, "days_since_last_contact": 15,
    }
    results = evaluate(m)
    types = [r.opportunity_type for r in results]
    assert R.LANDING_PAGE_OPTIMIZATION in types
    assert R.EMAIL_AUTOMATION in types
    assert R.RETARGETING_CAMPAIGN in types


def test_evaluate_sorted_by_score():
    m = {**HEALTHY, "ctr": 0.052, "bounce_rate": 0.78, "pages_per_session": 1.3,
         "email_open_rate": 0.09}
    results = evaluate(m)
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_evaluate_top_returns_best():
    m = {**HEALTHY, "ctr": 0.052, "bounce_rate": 0.78, "pages_per_session": 1.3,
         "email_open_rate": 0.09}
    top = evaluate_top(m)
    all_results = evaluate(m)
    assert top.opportunity_type == all_results[0].opportunity_type


def test_evaluate_healthy_client_no_opportunities():
    results = evaluate(HEALTHY)
    assert results == []


# ── Labeled dataset validation ────────────────────────────────────────────────

LABELED_PATH = Path(__file__).parent.parent / "data" / "synthetic" / "labeled_test_dataset.json"

def _load_labeled():
    return json.loads(LABELED_PATH.read_text())

@pytest.mark.parametrize("case", _load_labeled())
def test_labeled_dataset(case):
    """For each labeled test client, the detected opportunities must match exactly."""
    results = evaluate(case["metrics"])
    detected = set(r.opportunity_type for r in results)
    expected = set(case["expected_opportunities"])
    assert detected == expected, (
        f"Client '{case['client_name']}'\n"
        f"  Expected : {expected}\n"
        f"  Detected : {detected}\n"
        f"  Notes    : {case['notes']}"
    )


# ── Demo scenario validation ──────────────────────────────────────────────────

def test_demo_clients_trigger_expected_opportunities():
    """
    The 5 demo scenario clients should each trigger their designed opportunity
    when the rules engine is run against their DB metrics.
    """
    from src.agents.scorer import score_client

    expected_map = {
        "demo-001": "landing_page_optimization",
        "demo-002": "seo_content",
        "demo-003": "retargeting_campaign",
        "demo-004": "email_automation",
        "demo-005": "reactivation",
    }

    for client_id, expected_type in expected_map.items():
        results = score_client(client_id)
        types = [r.opportunity_type for r in results]
        assert expected_type in types, (
            f"Demo client {client_id}: expected '{expected_type}' but got {types}"
        )


# ── OpportunityResult structure ───────────────────────────────────────────────

def test_result_has_production_note():
    m = {**HEALTHY, "email_open_rate": 0.09}
    result = R.rule_email_automation(m)
    assert result.production_note
    assert "production" in result.production_note.lower()


def test_result_has_rationale():
    m = {**HEALTHY, "days_inactive": 60}
    result = R.rule_reactivation(m)
    assert result.rationale
    assert "60" in result.rationale  # days should appear in the explanation


def test_result_score_in_range():
    for rule_fn in R.RULES:
        # Feed a metric dict that should trigger every rule
        m = {
            "ctr": 0.06, "bounce_rate": 0.80, "pages_per_session": 1.5,
            "conversion_rate": 0.005, "organic_traffic": 2000, "keyword_rankings": 8,
            "email_open_rate": 0.08, "email_click_rate": 0.01,
            "ad_spend": 90.0, "roas": 1.4,
            "days_inactive": 60, "days_since_last_contact": 60,
        }
        result = rule_fn(m)
        if result is not None:
            assert 0 <= result.score <= 100, (
                f"Rule {rule_fn.__name__} returned score {result.score} out of range"
            )
