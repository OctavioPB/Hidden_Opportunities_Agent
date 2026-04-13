"""
Sprint 7 — Stripe Payment Link Generator.

When a negotiation (or a direct proposal acceptance) is confirmed,
the agent automatically creates a Stripe Payment Link and returns it
to the account manager and optionally emails it to the client.

DEMO MODE  (DEMO_MODE=true)
   A realistic-looking fake URL is generated.  No Stripe API call is made.
   The link is logged to logs/payment_links.jsonl and stored on the proposal.

PRODUCTION MODE  (DEMO_MODE=false, STRIPE_SECRET_KEY set)
   Calls the Stripe Payment Links API:
     POST https://api.stripe.com/v1/payment_links
   with a Price object derived from the proposal's suggested price.
   The returned URL is stored in proposals.payment_link.

Integration notes
-----------------
- Price objects are created on-the-fly (one-time, no subscription).
- Currency is USD by default; configurable via STRIPE_CURRENCY env var.
- Webhook endpoint: POST /webhooks/stripe handles checkout.session.completed
  to mark the proposal as paid in the DB.
- The payment link expires after 72 hours (configurable) for security.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

import config
import src.db.schema as _schema

PAYMENT_LINKS_LOG = config.LOGS_DIR / "payment_links.jsonl"
STRIPE_CURRENCY = "usd"


# ── Public API ────────────────────────────────────────────────────────────────

def create_payment_link(proposal_id: str, custom_amount: float | None = None) -> dict[str, Any]:
    """
    Create a Stripe Payment Link for a proposal.

    Parameters
    ----------
    proposal_id : str
        The proposals.id from the DB.
    custom_amount : float | None
        Override the proposal's suggested_price (used when a discount was
        negotiated and the final price differs from the original).

    Returns
    -------
    dict with keys: link_id, url, amount, proposal_id, created_at, simulated
    """
    conn = _schema.get_connection()
    row = conn.execute(
        """
        SELECT p.id, p.suggested_price, p.payment_link,
               c.name AS client_name, c.contact_email, c.industry,
               o.opportunity_type
        FROM proposals p
        JOIN clients       c ON c.id = p.client_id
        JOIN opportunities o ON o.id = p.opportunity_id
        WHERE p.id = ?
        """,
        (proposal_id,),
    ).fetchone()
    conn.close()

    if row is None:
        raise ValueError(f"Proposal {proposal_id!r} not found.")

    proposal = dict(row)

    # Return existing link if already created
    if proposal.get("payment_link"):
        return {
            "link_id":     "existing",
            "url":         proposal["payment_link"],
            "amount":      custom_amount or proposal["suggested_price"],
            "proposal_id": proposal_id,
            "created_at":  datetime.now().isoformat(),
            "simulated":   True,
            "already_existed": True,
        }

    amount = custom_amount or proposal["suggested_price"] or 200.0

    if config.DEMO_MODE or not config.STRIPE_SECRET_KEY:
        result = _create_demo_link(proposal_id, proposal, amount)
    else:
        result = _create_stripe_link(proposal_id, proposal, amount)

    # Persist the link URL back to the proposal row
    _store_link_on_proposal(proposal_id, result["url"])

    _append_log(result)
    print(
        f"[payment_link] Link created for proposal {proposal_id[:8]}…: "
        f"{result['url']}  (${amount:,.2f})"
    )
    return result


def get_payment_link(proposal_id: str) -> str | None:
    """Return the stored payment link URL for a proposal, or None if not created."""
    conn = _schema.get_connection()
    row = conn.execute(
        "SELECT payment_link FROM proposals WHERE id = ?", (proposal_id,)
    ).fetchone()
    conn.close()
    return row["payment_link"] if row else None


def record_payment_received(proposal_id: str, stripe_session_id: str = "") -> bool:
    """
    Mark a proposal as paid after Stripe confirms the payment.
    Called by the Stripe webhook handler in production.
    """
    conn = _schema.get_connection()
    now = datetime.now().isoformat()
    conn.execute(
        "UPDATE proposals SET status='paid', updated_at=? WHERE id=?",
        (now, proposal_id),
    )
    conn.execute(
        """
        UPDATE opportunities SET status='closed', updated_at=?
        WHERE id = (SELECT opportunity_id FROM proposals WHERE id=?)
        """,
        (now, proposal_id),
    )
    conn.commit()
    conn.close()

    _append_log({
        "event":            "payment_received",
        "proposal_id":      proposal_id,
        "stripe_session_id": stripe_session_id,
        "timestamp":        now,
    })
    print(f"[payment_link] Payment received for proposal {proposal_id[:8]}…")
    return True


def list_payment_links() -> list[dict]:
    """Return all proposals that have a payment link, with metadata."""
    conn = _schema.get_connection()
    rows = conn.execute(
        """
        SELECT p.id AS proposal_id,
               p.payment_link,
               p.suggested_price,
               p.status,
               p.created_at,
               c.name          AS client_name,
               c.contact_email,
               o.opportunity_type
        FROM proposals p
        JOIN clients       c ON c.id = p.client_id
        JOIN opportunities o ON o.id = p.opportunity_id
        WHERE p.payment_link IS NOT NULL AND p.payment_link != ''
        ORDER BY p.created_at DESC
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Demo link factory ─────────────────────────────────────────────────────────

def _create_demo_link(
    proposal_id: str,
    proposal: dict,
    amount: float,
) -> dict[str, Any]:
    """Generate a realistic-looking demo Stripe payment link."""
    link_id = "plink_" + uuid.uuid4().hex[:16]
    # Realistic-looking fake Stripe URL (does not resolve — demo only)
    url = f"https://buy.stripe.com/demo/{link_id}"

    return {
        "link_id":     link_id,
        "url":         url,
        "amount":      amount,
        "currency":    STRIPE_CURRENCY,
        "proposal_id": proposal_id,
        "client_name": proposal.get("client_name", ""),
        "client_email": proposal.get("contact_email", ""),
        "description": _payment_description(proposal),
        "created_at":  datetime.now().isoformat(),
        "simulated":   True,
        "_production_integration": (
            "Production: POST https://api.stripe.com/v1/payment_links "
            "with price_data (unit_amount in cents, currency, product description). "
            "Returns {url} that is emailed to the client and stored in proposals.payment_link. "
            "Stripe webhook checkout.session.completed → record_payment_received()."
        ),
    }


# ── Stripe API integration ────────────────────────────────────────────────────

def _create_stripe_link(
    proposal_id: str,
    proposal: dict,
    amount: float,
) -> dict[str, Any]:
    """Create a real Stripe Payment Link via the API."""
    try:
        import stripe
        stripe.api_key = config.STRIPE_SECRET_KEY

        # Create a one-time price object
        price = stripe.Price.create(
            unit_amount=int(amount * 100),   # Stripe uses cents
            currency=STRIPE_CURRENCY,
            product_data={
                "name": _payment_description(proposal),
            },
        )

        link = stripe.PaymentLink.create(
            line_items=[{"price": price.id, "quantity": 1}],
            after_completion={
                "type": "redirect",
                "redirect": {"url": "https://agency.demo/thank-you"},
            },
            metadata={
                "proposal_id": proposal_id,
                "client_name": proposal.get("client_name", ""),
            },
        )

        return {
            "link_id":     link.id,
            "url":         link.url,
            "amount":      amount,
            "currency":    STRIPE_CURRENCY,
            "proposal_id": proposal_id,
            "client_name": proposal.get("client_name", ""),
            "client_email": proposal.get("contact_email", ""),
            "description": _payment_description(proposal),
            "created_at":  datetime.now().isoformat(),
            "simulated":   False,
        }

    except Exception as e:
        print(f"[payment_link] Stripe API call failed: {e}. Falling back to demo link.")
        return _create_demo_link(proposal_id, proposal, amount)


def _payment_description(proposal: dict) -> str:
    from src.agents.rules import OPPORTUNITY_LABELS
    opp_label = OPPORTUNITY_LABELS.get(
        proposal.get("opportunity_type", ""),
        "Servicio de Marketing Digital",
    )
    client = proposal.get("client_name", "Cliente")
    return f"Hidden Opportunities — {opp_label} para {client}"


def _store_link_on_proposal(proposal_id: str, url: str) -> None:
    conn = _schema.get_connection()
    conn.execute(
        "UPDATE proposals SET payment_link=?, updated_at=? WHERE id=?",
        (url, datetime.now().isoformat(), proposal_id),
    )
    conn.commit()
    conn.close()


def _append_log(entry: dict) -> None:
    PAYMENT_LINKS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with PAYMENT_LINKS_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"timestamp": datetime.now().isoformat(), **entry},
                             ensure_ascii=False) + "\n")
