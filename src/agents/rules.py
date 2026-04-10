"""
Sprint 1 — Business Rules Engine.

Translates the 7 opportunity types defined in the internal workshop into
explicit IF/THEN rules with numerical thresholds.

Each rule takes a flat dict of client metrics (latest snapshot) and returns
an OpportunityResult if the rule fires, or None if it does not.

Thresholds are derived from agency historical averages documented in Sprint 1.
They are defined as module-level constants so they are easy to tune.

In Sprint 5 this module is replaced by the ML model, but the rules are kept
as a fallback when the model has insufficient training data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


# ── Opportunity types ─────────────────────────────────────────────────────────
LANDING_PAGE_OPTIMIZATION = "landing_page_optimization"
SEO_CONTENT               = "seo_content"
RETARGETING_CAMPAIGN      = "retargeting_campaign"
EMAIL_AUTOMATION          = "email_automation"
REACTIVATION              = "reactivation"
CONVERSION_RATE_AUDIT     = "conversion_rate_audit"
UPSELL_AD_BUDGET          = "upsell_ad_budget"

ALL_OPPORTUNITY_TYPES = [
    LANDING_PAGE_OPTIMIZATION,
    SEO_CONTENT,
    RETARGETING_CAMPAIGN,
    EMAIL_AUTOMATION,
    REACTIVATION,
    CONVERSION_RATE_AUDIT,
    UPSELL_AD_BUDGET,
]

# ── Friendly display names ─────────────────────────────────────────────────────
OPPORTUNITY_LABELS = {
    LANDING_PAGE_OPTIMIZATION: "Landing Page Optimization",
    SEO_CONTENT:               "SEO Content Package",
    RETARGETING_CAMPAIGN:      "Retargeting Campaign",
    EMAIL_AUTOMATION:          "Email Automation",
    REACTIVATION:              "Express Reactivation",
    CONVERSION_RATE_AUDIT:     "Conversion Rate Audit",
    UPSELL_AD_BUDGET:          "Ad Budget Expansion",
}

# ── Suggested prices per opportunity type (USD) ────────────────────────────────
SUGGESTED_PRICES = {
    LANDING_PAGE_OPTIMIZATION: 350,
    SEO_CONTENT:               500,
    RETARGETING_CAMPAIGN:      400,
    EMAIL_AUTOMATION:          300,
    REACTIVATION:              150,
    CONVERSION_RATE_AUDIT:     250,
    UPSELL_AD_BUDGET:          200,
}

# ── Thresholds (agency historical averages) ────────────────────────────────────
# Tune these per agency. Values are intentionally documented here so they
# can be turned into a config file in a later sprint.
T = {
    # Rule 1 — Landing page optimization
    "ctr_high":                 0.04,   # CTR > 4%
    "bounce_high":              0.70,   # Bounce rate > 70%
    "pages_low":                2.0,    # Pages per session < 2

    # Rule 2 — SEO content
    "organic_traffic_medium":   1000,   # Organic traffic > 1000/month
    "keyword_rankings_weak":    20,     # Ranking for fewer than 20 keywords
    "conversion_rate_low":      0.015,  # Conversion rate < 1.5%

    # Rule 3 — Retargeting campaign
    "ad_spend_high":            2000,   # Ad spend > $2000/month
    "roas_weak":                2.5,    # ROAS < 2.5 (not profitable enough)

    # Rule 4 — Email automation
    "email_open_low":           0.15,   # Open rate < 15%

    # Rule 5 — Reactivation
    "days_inactive":            45,     # Inactive for 45+ days

    # Rule 6 — Conversion rate audit
    "ctr_very_high":            0.05,   # CTR > 5% (traffic is there)
    "conversion_very_low":      0.01,   # But conversion < 1%

    # Rule 7 — Ad budget expansion
    "roas_excellent":           4.0,    # ROAS > 4.0 — scaling would be profitable
    "ad_spend_low":             800,    # But spending < $800 — leaving money on table
}


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class OpportunityResult:
    """The output of a single rule evaluation."""
    opportunity_type:   str
    label:              str
    score:              float           # 0–100 confidence score
    suggested_price:    float
    rationale:          str             # Human-readable explanation
    triggered_signals:  list[str] = field(default_factory=list)
    # In-production note shown in the UI
    production_note:    str = (
        "In production this score is computed daily by the rule engine "
        "using data pulled from Google Analytics, Meta Ads Manager, and the CRM API."
    )


# ── Individual rules ──────────────────────────────────────────────────────────
# Each rule is a function: dict -> OpportunityResult | None

def rule_landing_page_optimization(m: dict) -> OpportunityResult | None:
    """
    Rule 1 — Landing Page Optimization
    IF CTR > 4% AND bounce_rate > 70% AND pages_per_session < 2
    THEN opportunity = landing_page_optimization (score ~ 0.7)

    Interpretation: Ads are working (high CTR) but visitors leave immediately
    without converting — the landing page is the bottleneck.
    """
    ctr     = m.get("ctr", 0)
    bounce  = m.get("bounce_rate", 0)
    pages   = m.get("pages_per_session", 99)

    if ctr > T["ctr_high"] and bounce > T["bounce_high"] and pages < T["pages_low"]:
        # Score increases with stronger signals
        score = min(100, round(
            50
            + (ctr   - T["ctr_high"])  / T["ctr_high"]   * 20
            + (bounce - T["bounce_high"]) / 0.30          * 20
            + (T["pages_low"] - pages) / T["pages_low"]   * 10
        , 1))
        return OpportunityResult(
            opportunity_type  = LANDING_PAGE_OPTIMIZATION,
            label             = OPPORTUNITY_LABELS[LANDING_PAGE_OPTIMIZATION],
            score             = score,
            suggested_price   = SUGGESTED_PRICES[LANDING_PAGE_OPTIMIZATION],
            rationale         = (
                f"CTR is {ctr:.1%} (>{T['ctr_high']:.0%}) but bounce rate is "
                f"{bounce:.0%} and visitors view only {pages:.1f} pages. "
                f"Strong ad traffic is not converting — the landing page is the bottleneck."
            ),
            triggered_signals = ["high_ctr", "high_bounce", "low_pages_per_session"],
        )
    return None


def rule_seo_content(m: dict) -> OpportunityResult | None:
    """
    Rule 2 — SEO Content Package
    IF organic_traffic > 1000 AND keyword_rankings < 20 AND conversion_rate < 1.5%
    THEN opportunity = seo_content

    Interpretation: Some organic presence but thin content — structured blog/content
    strategy would capture more search intent.
    """
    traffic   = m.get("organic_traffic", 0)
    rankings  = m.get("keyword_rankings", 0)
    conv      = m.get("conversion_rate", 1)

    if traffic > T["organic_traffic_medium"] and rankings < T["keyword_rankings_weak"] and conv < T["conversion_rate_low"]:
        score = min(100, round(
            45
            + (traffic   - T["organic_traffic_medium"]) / 5000   * 25
            + (T["keyword_rankings_weak"] - rankings)   / 20     * 20
            + (T["conversion_rate_low"]  - conv)        / 0.015  * 10
        , 1))
        return OpportunityResult(
            opportunity_type  = SEO_CONTENT,
            label             = OPPORTUNITY_LABELS[SEO_CONTENT],
            score             = score,
            suggested_price   = SUGGESTED_PRICES[SEO_CONTENT],
            rationale         = (
                f"Organic traffic is {traffic:,}/month with only {rankings} keyword rankings "
                f"and {conv:.1%} conversion. A structured content strategy could "
                f"capture high-intent searches currently going to competitors."
            ),
            triggered_signals = ["medium_organic_traffic", "weak_keyword_coverage", "low_conversion"],
        )
    return None


def rule_retargeting_campaign(m: dict) -> OpportunityResult | None:
    """
    Rule 3 — Retargeting Campaign
    IF ad_spend > $2000 AND roas < 2.5
    THEN opportunity = retargeting_campaign

    Interpretation: Significant ad investment but poor return — retargeting warm
    audiences (visitors who didn't convert) typically 3–5x cheaper per conversion.
    """
    spend = m.get("ad_spend", 0)
    roas  = m.get("roas", 99)

    # ad_spend in the DB is daily; annualize to monthly for the threshold
    monthly_spend = spend * 30

    if monthly_spend > T["ad_spend_high"] and roas < T["roas_weak"]:
        score = min(100, round(
            55
            + (monthly_spend - T["ad_spend_high"]) / 5000   * 25
            + (T["roas_weak"] - roas)              / 2.5    * 20
        , 1))
        return OpportunityResult(
            opportunity_type  = RETARGETING_CAMPAIGN,
            label             = OPPORTUNITY_LABELS[RETARGETING_CAMPAIGN],
            score             = score,
            suggested_price   = SUGGESTED_PRICES[RETARGETING_CAMPAIGN],
            rationale         = (
                f"Monthly ad spend ~${monthly_spend:,.0f} with ROAS of {roas:.1f}x. "
                f"No retargeting in place — re-engaging warm audiences typically "
                f"reduces cost per acquisition by 30–50%."
            ),
            triggered_signals = ["high_ad_spend", "weak_roas"],
        )
    return None


def rule_email_automation(m: dict) -> OpportunityResult | None:
    """
    Rule 4 — Email Automation
    IF email_open_rate < 15%
    THEN opportunity = email_automation

    Interpretation: Email list is underperforming — automated sequences
    (welcome, re-engagement, abandoned cart) can significantly lift open rates.
    """
    open_rate = m.get("email_open_rate", 1)

    if open_rate < T["email_open_low"]:
        score = min(100, round(
            50 + (T["email_open_low"] - open_rate) / T["email_open_low"] * 50
        , 1))
        return OpportunityResult(
            opportunity_type  = EMAIL_AUTOMATION,
            label             = OPPORTUNITY_LABELS[EMAIL_AUTOMATION],
            score             = score,
            suggested_price   = SUGGESTED_PRICES[EMAIL_AUTOMATION],
            rationale         = (
                f"Email open rate is {open_rate:.1%} (industry average: 21%). "
                f"Automated welcome and re-engagement sequences typically "
                f"lift open rates to 25–35%."
            ),
            triggered_signals = ["low_email_open_rate"],
        )
    return None


def rule_reactivation(m: dict) -> OpportunityResult | None:
    """
    Rule 5 — Express Reactivation
    IF days_inactive >= 45
    THEN opportunity = reactivation

    Interpretation: Client has gone dark — a time-limited offer with a personal
    touch has a higher close rate than a standard proposal.
    """
    inactive = m.get("days_inactive", 0)

    if inactive >= T["days_inactive"]:
        score = min(100, round(
            60 + min(inactive - T["days_inactive"], 60) / 60 * 40
        , 1))
        return OpportunityResult(
            opportunity_type  = REACTIVATION,
            label             = OPPORTUNITY_LABELS[REACTIVATION],
            score             = score,
            suggested_price   = SUGGESTED_PRICES[REACTIVATION],
            rationale         = (
                f"Client has been inactive for {inactive} days. "
                f"A personalized reactivation offer with a time-limited incentive "
                f"typically recovers 20–30% of dormant accounts."
            ),
            triggered_signals = ["high_days_inactive"],
        )
    return None


def rule_conversion_rate_audit(m: dict) -> OpportunityResult | None:
    """
    Rule 6 — Conversion Rate Audit
    IF ctr > 5% AND conversion_rate < 1%
    THEN opportunity = conversion_rate_audit

    Interpretation: Very high ad CTR but near-zero conversion — something in the
    funnel (form, checkout, CTA) is broken. A CRO audit typically uncovers quick wins.
    """
    ctr  = m.get("ctr", 0)
    conv = m.get("conversion_rate", 1)

    if ctr > T["ctr_very_high"] and conv < T["conversion_very_low"]:
        score = min(100, round(
            65
            + (ctr  - T["ctr_very_high"])      / 0.05  * 15
            + (T["conversion_very_low"] - conv) / 0.01  * 20
        , 1))
        return OpportunityResult(
            opportunity_type  = CONVERSION_RATE_AUDIT,
            label             = OPPORTUNITY_LABELS[CONVERSION_RATE_AUDIT],
            score             = score,
            suggested_price   = SUGGESTED_PRICES[CONVERSION_RATE_AUDIT],
            rationale         = (
                f"CTR is {ctr:.1%} but conversion rate is only {conv:.2%}. "
                f"High click-through with near-zero conversion indicates a funnel "
                f"breakdown — a CRO audit typically identifies 3–5 quick fixes."
            ),
            triggered_signals = ["very_high_ctr", "very_low_conversion"],
        )
    return None


def rule_upsell_ad_budget(m: dict) -> OpportunityResult | None:
    """
    Rule 7 — Ad Budget Expansion Upsell
    IF roas > 4.0 AND monthly_ad_spend < $800
    THEN opportunity = upsell_ad_budget

    Interpretation: The client's campaigns are highly efficient but underfunded.
    Scaling spend on a proven campaign is one of the easiest sales to close.
    """
    roas  = m.get("roas", 0)
    spend = m.get("ad_spend", 0)
    monthly_spend = spend * 30

    if roas > T["roas_excellent"] and monthly_spend < T["ad_spend_low"]:
        score = min(100, round(
            55
            + (roas - T["roas_excellent"])          / 4.0  * 25
            + (T["ad_spend_low"] - monthly_spend)   / 800  * 20
        , 1))
        return OpportunityResult(
            opportunity_type  = UPSELL_AD_BUDGET,
            label             = OPPORTUNITY_LABELS[UPSELL_AD_BUDGET],
            score             = score,
            suggested_price   = SUGGESTED_PRICES[UPSELL_AD_BUDGET],
            rationale         = (
                f"ROAS is {roas:.1f}x on a monthly spend of ~${monthly_spend:,.0f}. "
                f"Campaigns are highly efficient — doubling the budget on these "
                f"ad sets would generate positive returns immediately."
            ),
            triggered_signals = ["excellent_roas", "low_ad_spend"],
        )
    return None


# ── Rule registry ─────────────────────────────────────────────────────────────
# Order matters: higher-confidence rules first.
RULES: list[Callable[[dict], OpportunityResult | None]] = [
    rule_reactivation,           # Rule 5 — clearest signal, highest confidence
    rule_email_automation,       # Rule 4
    rule_conversion_rate_audit,  # Rule 6
    rule_landing_page_optimization,  # Rule 1
    rule_retargeting_campaign,   # Rule 3
    rule_upsell_ad_budget,       # Rule 7
    rule_seo_content,            # Rule 2 — weakest signal, evaluated last
]


def evaluate(metrics: dict) -> list[OpportunityResult]:
    """
    Apply all rules to a single client's latest metrics snapshot.

    Returns all opportunities that fired, sorted by score descending.
    A client can have multiple opportunities simultaneously.
    """
    results = []
    for rule in RULES:
        result = rule(metrics)
        if result is not None:
            results.append(result)
    return sorted(results, key=lambda r: r.score, reverse=True)


def evaluate_top(metrics: dict) -> OpportunityResult | None:
    """Return only the highest-scoring opportunity, or None."""
    results = evaluate(metrics)
    return results[0] if results else None
