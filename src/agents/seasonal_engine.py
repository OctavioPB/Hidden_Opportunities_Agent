"""
Feature 6 — Seasonal Opportunity Calendar.

Applies time-aware score multipliers to detected opportunities based on the
current calendar month. Also returns a list of upcoming marketing events for
the next 8 weeks so account managers can plan outreach timing.

No external dependencies — all logic is purely temporal.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

# Opportunity type constants (mirrors rules.py to avoid circular imports)
_LPO  = "landing_page_optimization"
_SEO  = "seo_content"
_RTG  = "retargeting_campaign"
_EML  = "email_automation"
_RAC  = "reactivation"
_CRA  = "conversion_rate_audit"
_UAB  = "upsell_ad_budget"

# (opportunity_type, [months]) → score multiplier
# Month numbers: 1=Jan … 12=Dec
SEASONAL_BOOSTS: dict[tuple[str, tuple[int, ...]], float] = {
    (_UAB,  (9, 10)):     1.20,   # Q4 ramp-up: brands scaling ad spend
    (_LPO,  (9, 10)):     1.15,   # Pre-peak: landing pages must convert before BFCM
    (_CRA,  (9, 10)):     1.12,   # Same pre-peak window
    (_EML,  (1, 2)):      1.15,   # New-year CRM reset + planning season
    (_RAC,  (1, 8)):      1.12,   # Jan: post-holiday reactivation; Aug: summer wake-up
    (_SEO,  (2, 3, 6)):   1.10,   # Q1 content planning + mid-year sprint
    (_RTG,  (7, 10, 11)): 1.18,   # Summer campaigns + Black Friday / Cyber Monday
    (_LPO,  (3, 4, 7)):   1.08,   # Spring + summer campaign prep
    (_CRA,  (6,)):        1.10,   # Mid-year conversion audit
    (_EML,  (6,)):        1.08,   # Mid-year CRM refresh
    (_UAB,  (7,)):        1.12,   # Summer ad budget expansion
}

# Marketing calendar events for the next 8 weeks
_ANNUAL_EVENTS: list[dict] = [
    {"name": "Mid-Year Growth Sprint",      "month": 6,  "day": 1,  "types": [_SEO, _CRA, _EML]},
    {"name": "Summer Campaign Launch",      "month": 7,  "day": 1,  "types": [_RTG, _UAB, _LPO]},
    {"name": "Q4 Budget Season",           "month": 9,  "day": 1,  "types": [_UAB, _LPO, _CRA]},
    {"name": "Black Friday / Cyber Monday","month": 11, "day": 1,  "types": [_RTG, _LPO, _UAB]},
    {"name": "Year-End Planning",          "month": 12, "day": 1,  "types": [_EML, _RAC]},
    {"name": "New Year Kickoff",           "month": 1,  "day": 7,  "types": [_EML, _RAC, _SEO]},
    {"name": "Q1 Content Push",            "month": 2,  "day": 1,  "types": [_SEO, _LPO]},
    {"name": "Spring Campaign Prep",       "month": 3,  "day": 15, "types": [_LPO, _CRA]},
    {"name": "Summer Reactivation",        "month": 8,  "day": 1,  "types": [_RAC, _EML]},
    {"name": "Back-to-School Season",      "month": 8,  "day": 20, "types": [_UAB, _RTG]},
]


def get_seasonal_multiplier(opportunity_type: str, target_date: date | None = None) -> float:
    """Return the seasonal score multiplier for an opportunity type on a given date."""
    if target_date is None:
        target_date = date.today()
    month = target_date.month

    best = 1.0
    for (opp_type, months), multiplier in SEASONAL_BOOSTS.items():
        if opp_type == opportunity_type and month in months:
            best = max(best, multiplier)
    return best


def get_upcoming_events(n_weeks: int = 8) -> list[dict]:
    """Return marketing calendar events falling in the next n_weeks weeks."""
    today = date.today()
    cutoff = today + timedelta(weeks=n_weeks)
    upcoming = []

    for year in [today.year, today.year + 1]:
        for ev in _ANNUAL_EVENTS:
            try:
                ev_date = date(year, ev["month"], ev["day"])
            except ValueError:
                continue
            if today <= ev_date <= cutoff:
                days_away = (ev_date - today).days
                upcoming.append({
                    "name":       ev["name"],
                    "date":       ev_date.isoformat(),
                    "days_away":  days_away,
                    "types":      ev["types"],
                    "current_boost": max(
                        get_seasonal_multiplier(t, ev_date) for t in ev["types"]
                    ),
                })

    upcoming.sort(key=lambda e: e["date"])
    return upcoming


def apply_seasonal_boosts(results: list[dict]) -> list[dict]:
    """
    Given a list of opportunity dicts (from score_all_clients), multiply each
    blended_score by the appropriate seasonal multiplier and annotate with
    seasonal_boost field.
    """
    today = date.today()
    for r in results:
        mult  = get_seasonal_multiplier(r["opportunity_type"], today)
        if mult > 1.0:
            r["blended_score"]  = min(100, round(r.get("blended_score", r["score"]) * mult, 1))
            r["score"]          = min(100, round(r["score"] * mult, 1))
        r["seasonal_boost"] = mult
    return results


def get_current_boosts() -> list[dict]:
    """Return all opportunity types with their current month's boost."""
    today = date.today()
    boosts = []
    seen = set()
    for (opp_type, months), mult in SEASONAL_BOOSTS.items():
        if opp_type not in seen:
            seen.add(opp_type)
            m = get_seasonal_multiplier(opp_type, today)
            if m > 1.0:
                boosts.append({"opportunity_type": opp_type, "multiplier": m, "months": list(months)})
    boosts.sort(key=lambda b: b["multiplier"], reverse=True)
    return boosts
