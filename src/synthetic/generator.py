"""
Synthetic data generator for the Hidden Opportunities Agent demo.

Produces a consistent, realistic dataset of 50–100 fake marketing agency
clients, their metrics, emails, call transcripts, and CRM notes.

All randomness is seeded via config.SYNTHETIC_SEED for reproducibility —
the same seed always produces the same clients and the same demo scenarios.
"""

import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from faker import Faker

import config

fake = Faker("en_US")
rng = np.random.default_rng(config.SYNTHETIC_SEED)
random.seed(config.SYNTHETIC_SEED)
Faker.seed(config.SYNTHETIC_SEED)

# ── Industry profiles ─────────────────────────────────────────────────────────
# Each profile shapes the realistic metric ranges for that type of client.
INDUSTRY_PROFILES = {
    "Restaurant": {
        "monthly_spend": (300, 1500),
        "bounce_rate": (0.55, 0.85),
        "ctr": (0.02, 0.06),
        "conversion_rate": (0.01, 0.04),
        "email_open_rate": (0.15, 0.35),
        "organic_traffic": (500, 5000),
    },
    "E-commerce": {
        "monthly_spend": (800, 5000),
        "bounce_rate": (0.40, 0.70),
        "ctr": (0.03, 0.08),
        "conversion_rate": (0.02, 0.07),
        "email_open_rate": (0.18, 0.40),
        "organic_traffic": (2000, 30000),
    },
    "Law Firm": {
        "monthly_spend": (500, 3000),
        "bounce_rate": (0.50, 0.75),
        "ctr": (0.01, 0.04),
        "conversion_rate": (0.005, 0.02),
        "email_open_rate": (0.12, 0.28),
        "organic_traffic": (200, 3000),
    },
    "Real Estate": {
        "monthly_spend": (600, 4000),
        "bounce_rate": (0.45, 0.72),
        "ctr": (0.02, 0.05),
        "conversion_rate": (0.01, 0.03),
        "email_open_rate": (0.14, 0.30),
        "organic_traffic": (500, 8000),
    },
    "Fitness / Wellness": {
        "monthly_spend": (200, 1200),
        "bounce_rate": (0.48, 0.78),
        "ctr": (0.03, 0.07),
        "conversion_rate": (0.015, 0.05),
        "email_open_rate": (0.20, 0.45),
        "organic_traffic": (300, 6000),
    },
    "Healthcare": {
        "monthly_spend": (400, 2500),
        "bounce_rate": (0.50, 0.72),
        "ctr": (0.015, 0.04),
        "conversion_rate": (0.008, 0.025),
        "email_open_rate": (0.16, 0.32),
        "organic_traffic": (400, 5000),
    },
    "Tech / SaaS": {
        "monthly_spend": (1000, 8000),
        "bounce_rate": (0.38, 0.65),
        "ctr": (0.04, 0.09),
        "conversion_rate": (0.03, 0.10),
        "email_open_rate": (0.22, 0.48),
        "organic_traffic": (3000, 50000),
    },
}

INDUSTRIES = list(INDUSTRY_PROFILES.keys())
COMPANY_SIZES = ["small", "medium", "large"]
ACCOUNT_MANAGERS = ["Sofia Reyes", "Marcus Chen", "Priya Patel", "Jordan Smith"]

# ── Opportunity types ─────────────────────────────────────────────────────────
OPPORTUNITY_TYPES = [
    "landing_page_optimization",
    "seo_content",
    "retargeting_campaign",
    "email_automation",
    "reactivation",
]

# ── Demo scenario clients (fixed — used in all live presentations) ─────────────
DEMO_SCENARIOS = [
    {
        "id": "demo-001",
        "name": "Bella Cucina Restaurant",
        "industry": "Restaurant",
        "story": "High CTR but terrible bounce rate — classic landing page opportunity.",
        "force_metrics": {"ctr": 0.052, "bounce_rate": 0.78, "conversion_rate": 0.013,
                          "pages_per_session": 1.4, "days_inactive": 5, "days_since_last_contact": 5},
    },
    {
        "id": "demo-002",
        "name": "LexGroup Law Firm",
        "industry": "Law Firm",
        "story": "High organic traffic, zero blog, strong SEO content upsell.",
        "force_metrics": {"organic_traffic": 4200, "keyword_rankings": 12, "conversion_rate": 0.006,
                          "days_inactive": 5, "days_since_last_contact": 5},
    },
    {
        "id": "demo-003",
        "name": "FitZone Studio",
        "industry": "Fitness / Wellness",
        "story": "Spending $2400/month on Google Ads with no retargeting in place.",
        # ad_spend is stored as DAILY in the DB: $2400/month / 30 = $80/day
        "force_metrics": {"ad_spend": 80, "roas": 1.8, "ctr": 0.035, "days_inactive": 3, "days_since_last_contact": 3},
    },
    {
        "id": "demo-004",
        "name": "MediCare Clinic",
        "industry": "Healthcare",
        "story": "Email list of 3,000 but open rate of 9% — email automation opportunity.",
        "force_metrics": {"email_open_rate": 0.09, "email_click_rate": 0.01,
                          "days_inactive": 5, "days_since_last_contact": 5},
    },
    {
        "id": "demo-005",
        "name": "Urban Nest Realty",
        "industry": "Real Estate",
        "story": "Inactive for 52 days — perfect candidate for express reactivation offer.",
        "force_metrics": {"days_inactive": 52, "days_since_last_contact": 52},
    },
]


# ── Helper functions ──────────────────────────────────────────────────────────

def _rand(lo: float, hi: float) -> float:
    return float(rng.uniform(lo, hi))


def _rand_int(lo: int, hi: int) -> int:
    return int(rng.integers(lo, hi + 1))


def _metric(profile: dict, key: str, force: dict | None = None) -> float:
    if force and key in force:
        return force[key]
    lo, hi = profile[key]
    return _rand(lo, hi)


def _generate_client(client_id: str, name: str | None = None,
                     industry: str | None = None,
                     force_metrics: dict | None = None,
                     is_demo: bool = False) -> dict:
    industry = industry or random.choice(INDUSTRIES)
    profile = INDUSTRY_PROFILES[industry]
    size = random.choice(COMPANY_SIZES)

    return {
        "id": client_id,
        "name": name or fake.company(),
        "industry": industry,
        "company_size": size,
        "account_age_days": _rand_int(30, 900),
        "monthly_spend": round(_metric(profile, "monthly_spend", force_metrics), 2),
        "contact_email": fake.company_email(),
        "account_manager": random.choice(ACCOUNT_MANAGERS),
        "is_demo_scenario": int(is_demo),
        "_force_metrics": force_metrics or {},
    }


def _generate_metrics_history(client: dict, days: int = 90) -> list[dict]:
    """Generate daily metrics for the past N days."""
    industry = client["industry"]
    profile = INDUSTRY_PROFILES[industry]
    force = client.get("_force_metrics", {})
    rows = []
    base_date = datetime.now().date()

    for offset in range(days, 0, -1):
        date = base_date - timedelta(days=offset)
        # Add slight day-to-day variation for non-forced values only.
        # Forced values are used exactly — noise must not push them past thresholds.
        noise = lambda v: round(v * _rand(0.85, 1.15), 4)

        def fon(key: str, base: float) -> float:
            """Return forced value as-is, or apply noise to the base."""
            return force[key] if key in force else noise(base)

        rows.append({
            "client_id": client["id"],
            "date": str(date),
            "bounce_rate":            fon("bounce_rate",     _metric(profile, "bounce_rate", {})),
            "pages_per_session":      force.get("pages_per_session", round(_rand(1.2, 4.5), 2)),
            "conversion_rate":        fon("conversion_rate", _metric(profile, "conversion_rate", {})),
            "organic_traffic":        int(force["organic_traffic"] if "organic_traffic" in force
                                          else _metric(profile, "organic_traffic", {}) * _rand(0.8, 1.2)),
            "ctr":                    fon("ctr",              _metric(profile, "ctr", {})),
            "cpc":                    force.get("cpc",        round(_rand(0.30, 3.50), 2)),
            "roas":                   force.get("roas",       round(_rand(0.8, 5.0), 2)),
            "ad_spend":               force.get("ad_spend",   round(client["monthly_spend"] / 30 * _rand(0.7, 1.3), 2)),
            "email_open_rate":        fon("email_open_rate",  _metric(profile, "email_open_rate", {})),
            "email_click_rate":       round(_rand(0.005, 0.12), 4),
            "keyword_rankings":       force.get("keyword_rankings",       _rand_int(5, 80)),
            "days_since_last_contact": force.get("days_since_last_contact", _rand_int(1, 60)),
            "days_inactive":          force.get("days_inactive",           _rand_int(0, 60)),
        })
    return rows


# Sample email templates per signal type
_EMAIL_TEMPLATES = {
    "budget_concern": [
        "Hi, I wanted to check in — the current spend is feeling a bit high for us this quarter. "
        "Is there a way to reduce costs without losing too much reach?",
        "Just reviewing our invoices. Honestly, it's getting expensive and I'm not sure we're seeing the ROI.",
        "Between us, the board is asking me to cut the marketing budget by 20%. Let's talk options.",
    ],
    "results_interest": [
        "Hey, can you send over some case studies? I want to show the team what results we can expect.",
        "I'd love to see how other clients in our space have done. Do you have any benchmarks?",
        "We're preparing our Q3 review — could you put together a report on our campaign performance?",
    ],
    "churn_risk": [
        "I haven't heard from anyone in over a month. Starting to wonder if this partnership is worth continuing.",
        "We've been evaluating other agencies. Just want to be transparent about where we're at.",
        "If things don't improve in the next few weeks, we'll probably need to reconsider.",
    ],
    "positive_interest": [
        "Love what you've done with the Google Ads! Can we talk about expanding to Instagram?",
        "The new landing page is converting really well. What else can we do to keep momentum?",
        "Our CEO saw the report and was impressed. Let's schedule a call to discuss next steps.",
    ],
    "neutral": [
        "Just confirming receipt of the latest report. We'll review it this week.",
        "Can we move our monthly call to Thursday instead of Wednesday?",
        "Please update the billing contact to finance@company.com going forward.",
    ],
}

_CALL_TRANSCRIPT_TEMPLATES = [
    "Client mentioned they are happy with the current results but want to explore retargeting options.",
    "Client expressed concern about the cost per click increasing over the last month.",
    "Client asked about SEO content packages and whether we could handle blog writing.",
    "Client said they'll think about it and get back to us next week. Third time they've said this.",
    "Client is very enthusiastic — wants to expand budget by 30% and add two new campaigns.",
    "Client flagged that a competitor is offering similar services for less. Asked us to match.",
    "Client mentioned they haven't opened our last three emails. Not sure if they're still engaged.",
]

_CRM_NOTE_TEMPLATES = [
    "Follow-up call scheduled for next Tuesday.",
    "Sent Q2 performance report. Client seemed satisfied.",
    "Client requested a discount. Escalated to account manager.",
    "Onboarding complete. First campaign live.",
    "Client paused campaigns for two weeks due to internal budget review.",
    "Upsell conversation started — client interested in email automation add-on.",
    "Client renewed for another 6 months. Happy with results.",
]


def _generate_text_signals(client: dict) -> list[dict]:
    signals = []
    # 2-5 emails per client
    for _ in range(_rand_int(2, 5)):
        signal_type = random.choice(list(_EMAIL_TEMPLATES.keys()))
        text = random.choice(_EMAIL_TEMPLATES[signal_type])
        signals.append({
            "client_id": client["id"],
            "source": "email",
            "raw_text": text,
            "signal_type_hint": signal_type,
        })
    # 1-2 call transcripts
    for _ in range(_rand_int(1, 2)):
        signals.append({
            "client_id": client["id"],
            "source": "call_transcript",
            "raw_text": random.choice(_CALL_TRANSCRIPT_TEMPLATES),
            "signal_type_hint": "call",
        })
    # 1-3 CRM notes
    for _ in range(_rand_int(1, 3)):
        signals.append({
            "client_id": client["id"],
            "source": "crm_note",
            "raw_text": random.choice(_CRM_NOTE_TEMPLATES),
            "signal_type_hint": "note",
        })
    return signals


# ── Public API ────────────────────────────────────────────────────────────────

def generate_all(n_random: int | None = None) -> dict:
    """
    Generate the full synthetic dataset.

    Returns a dict with keys: clients, metrics, text_signals.
    Always includes the 5 fixed demo scenario clients.
    Random clients fill the rest up to n_random (default: config value).
    """
    n_random = n_random if n_random is not None else config.SYNTHETIC_CLIENT_COUNT

    clients = []
    metrics = []
    text_signals = []

    # Fixed demo scenario clients (always first)
    for scenario in DEMO_SCENARIOS:
        client = _generate_client(
            client_id=scenario["id"],
            name=scenario["name"],
            industry=scenario["industry"],
            force_metrics=scenario["force_metrics"],
            is_demo=True,
        )
        clients.append(client)
        metrics.extend(_generate_metrics_history(client))
        text_signals.extend(_generate_text_signals(client))

    # Random clients
    for _ in range(n_random):
        client = _generate_client(client_id=str(uuid.uuid4()))
        clients.append(client)
        metrics.extend(_generate_metrics_history(client))
        text_signals.extend(_generate_text_signals(client))

    return {
        "clients": clients,
        "metrics": metrics,
        "text_signals": text_signals,
    }


def save_to_json(dataset: dict, output_dir: Path | None = None) -> None:
    """Persist the dataset as JSON files in the synthetic data directory."""
    output_dir = output_dir or config.SYNTHETIC_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    for key, records in dataset.items():
        path = output_dir / f"{key}.json"
        # Strip internal _force_metrics before saving
        clean = [{k: v for k, v in r.items() if not k.startswith("_")} for r in records]
        path.write_text(json.dumps(clean, indent=2, default=str))
        print(f"[synthetic] Saved {len(clean):>5} {key} records -> {path}")


if __name__ == "__main__":
    dataset = generate_all()
    save_to_json(dataset)
