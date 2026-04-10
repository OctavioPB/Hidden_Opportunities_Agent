"""
Central configuration for the Hidden Opportunities Agent.

DEMO_MODE (default: True) routes all external I/O to local files/stubs.
Set DEMO_MODE=false in .env only when connecting to real production services.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"
DB_PATH = ROOT_DIR / os.getenv("DB_PATH", "data/db/opportunities.db")
SYNTHETIC_DIR = DATA_DIR / "synthetic"
EXPORTS_DIR = DATA_DIR / "exports"
LOGS_DIR = ROOT_DIR / "logs"

for _dir in (DATA_DIR / "db", SYNTHETIC_DIR, EXPORTS_DIR, LOGS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# ── Demo toggle ───────────────────────────────────────────────────────────────
DEMO_MODE: bool = os.getenv("DEMO_MODE", "true").lower() == "true"

# ── LLM ───────────────────────────────────────────────────────────────────────
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

# ── Notifications ─────────────────────────────────────────────────────────────
SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

# ── Email ─────────────────────────────────────────────────────────────────────
SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
EMAIL_FROM: str = os.getenv("EMAIL_FROM", "agent@demo.local")

# ── Payments ──────────────────────────────────────────────────────────────────
STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")

# ── Synthetic data ────────────────────────────────────────────────────────────
SYNTHETIC_CLIENT_COUNT: int = int(os.getenv("SYNTHETIC_CLIENT_COUNT", "75"))
SYNTHETIC_SEED: int = int(os.getenv("SYNTHETIC_SEED", "42"))  # reproducible data

# ── Demo scenario ─────────────────────────────────────────────────────────────
# Fixed client IDs used in all demos and presentations (set during seeding).
DEMO_CLIENT_IDS: list[str] = []  # populated at runtime by seed script


def summary() -> dict:
    """Return a non-sensitive config summary for logging/UI display."""
    return {
        "demo_mode": DEMO_MODE,
        "llm_provider": LLM_PROVIDER,
        "llm_model": LLM_MODEL,
        "db_path": str(DB_PATH),
        "synthetic_clients": SYNTHETIC_CLIENT_COUNT,
        "synthetic_seed": SYNTHETIC_SEED,
    }
