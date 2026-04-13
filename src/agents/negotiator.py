"""
Sprint 7 — Autonomous Negotiation Engine.

When a client responds "too expensive", the agent enters a structured
multi-turn negotiation loop rather than simply logging the rejection:

  Turn 1 (agent):  Counter-offer at 10% discount + value re-framing.
  Client reply A:  Client accepts  → close deal, generate payment link.
  Client reply B:  Client counter  → Turn 2: escalate discount to 15%.
  Client reply C:  Client rejects  → Turn 2: final appeal at 15%.
  Turn 3 (agent):  Final offer at 20% discount — take it or leave it.
  Turn 4+:         Auto-escalate to human account manager.

The full conversation is stored in the ``negotiation_log`` table
(already defined in schema.py Sprint 7 stub).  Each row has a role
('agent' | 'client'), the message text, the extracted intent, and
the price offered in that turn.

DEMO MODE
  LLM calls fall back to templated responses so no API key is needed.
  "Client" replies are simulated in the UI demo panel.

PRODUCTION MODE
  LLM (Claude Haiku or GPT-3.5) generates context-aware counter-offers.
  Client replies arrive via the SendGrid inbound-parse webhook, are
  matched to open negotiations by thread-id email header, and flow into
  ``process_client_reply()``.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from textwrap import dedent
from typing import Any

import config
import src.db.schema as _schema
from src.agents.rules import OPPORTUNITY_LABELS, SUGGESTED_PRICES


# ── Negotiation constants ─────────────────────────────────────────────────────

MAX_AGENT_TURNS = 3          # after this many agent turns → escalate to human
DISCOUNT_BY_TURN = {1: 0.10, 2: 0.15, 3: 0.20}   # cumulative discount per turn

# Intent labels returned by _extract_intent()
NEG_INTENT_ACCEPT   = "accepted"
NEG_INTENT_COUNTER  = "counter_offer"
NEG_INTENT_REJECT   = "rejected"
NEG_INTENT_INFO     = "needs_info"
NEG_INTENT_ESCALATE = "escalated"

# Negotiation status
STATUS_ACTIVE    = "active"
STATUS_ACCEPTED  = "accepted"
STATUS_REJECTED  = "rejected"
STATUS_ESCALATED = "escalated"

NEGOTIATION_LOG = config.LOGS_DIR / "negotiations.jsonl"


# ── Public API ────────────────────────────────────────────────────────────────

def start_negotiation(proposal_id: str) -> dict[str, Any]:
    """
    Open a negotiation thread for a proposal that received a 'too_expensive'
    reply.  Writes the agent's opening counter-offer (Turn 1, 10% off) to
    ``negotiation_log`` and returns the message dict.

    Called automatically from feedback_loop.record_client_reply() when
    intent == INTENT_TOO_EXPENSIVE.
    """
    conn = _schema.get_connection()
    proposal = _load_proposal(conn, proposal_id)
    conn.close()

    if proposal is None:
        raise ValueError(f"Proposal {proposal_id!r} not found.")

    # Check if a negotiation is already active for this proposal
    existing = get_thread(proposal_id)
    if existing:
        return existing[-1]   # return last agent message

    base_price    = proposal["suggested_price"] or 200.0
    discount      = DISCOUNT_BY_TURN[1]
    offer_price   = round(base_price * (1 - discount), 2)
    opp_type      = proposal["opportunity_type"]
    client_name   = proposal["client_name"]
    industry      = proposal["industry"]

    message = _build_agent_message(
        turn=1,
        client_name=client_name,
        industry=industry,
        opp_type=opp_type,
        base_price=base_price,
        offer_price=offer_price,
        discount=discount,
        use_llm=True,
    )

    row_id = _write_turn(
        proposal_id=proposal_id,
        turn=1,
        role="agent",
        message=message,
        intent=None,
        offer_price=offer_price,
    )

    _append_log({
        "event":       "negotiation_started",
        "proposal_id": proposal_id,
        "client_name": client_name,
        "turn":        1,
        "offer_price": offer_price,
        "discount_pct": int(discount * 100),
    })

    return {
        "id":          row_id,
        "proposal_id": proposal_id,
        "turn":        1,
        "role":        "agent",
        "message":     message,
        "offer_price": offer_price,
        "status":      STATUS_ACTIVE,
    }


def process_client_reply(
    proposal_id: str,
    client_message: str,
    simulated: bool = False,
) -> dict[str, Any]:
    """
    Handle a client reply within an active negotiation.

    1. Write the client turn to ``negotiation_log``.
    2. Extract the client's intent (LLM or keyword).
    3. Generate and write the agent's next response.
    4. If the client accepts → mark proposal accepted, generate payment link.
    5. If max turns exceeded → escalate to human.

    Returns a dict with 'agent_message', 'intent', 'status', 'offer_price'.
    """
    conn = _schema.get_connection()
    proposal = _load_proposal(conn, proposal_id)
    conn.close()

    if proposal is None:
        raise ValueError(f"Proposal {proposal_id!r} not found.")

    thread = get_thread(proposal_id)
    agent_turns = sum(1 for t in thread if t["role"] == "agent")
    next_agent_turn = agent_turns + 1

    # ── Write client turn ─────────────────────────────────────────────────────
    client_intent = _extract_intent(client_message)
    _write_turn(
        proposal_id=proposal_id,
        turn=len(thread) + 1,
        role="client",
        message=client_message,
        intent=client_intent,
        offer_price=None,
    )

    # ── Handle accept ─────────────────────────────────────────────────────────
    if client_intent == NEG_INTENT_ACCEPT:
        _close_negotiation(proposal_id, STATUS_ACCEPTED)
        # Find the last offer price from the thread
        last_offer = next(
            (t["offer_price"] for t in reversed(thread) if t.get("offer_price")),
            proposal["suggested_price"],
        )
        _append_log({
            "event":       "negotiation_accepted",
            "proposal_id": proposal_id,
            "final_price": last_offer,
            "simulated":   simulated,
        })
        return {
            "agent_message": None,
            "intent":        client_intent,
            "status":        STATUS_ACCEPTED,
            "offer_price":   last_offer,
        }

    # ── Handle explicit reject ────────────────────────────────────────────────
    if client_intent in (NEG_INTENT_REJECT, NEG_INTENT_ESCALATE):
        _close_negotiation(proposal_id, STATUS_REJECTED if client_intent == NEG_INTENT_REJECT else STATUS_ESCALATED)
        _append_log({
            "event":       "negotiation_closed",
            "proposal_id": proposal_id,
            "reason":      client_intent,
            "simulated":   simulated,
        })
        return {
            "agent_message": None,
            "intent":        client_intent,
            "status":        STATUS_REJECTED if client_intent == NEG_INTENT_REJECT else STATUS_ESCALATED,
            "offer_price":   None,
        }

    # ── Escalate when max turns reached ──────────────────────────────────────
    if next_agent_turn > MAX_AGENT_TURNS:
        _close_negotiation(proposal_id, STATUS_ESCALATED)
        _escalate(proposal_id, proposal["client_name"], proposal["account_manager"])
        return {
            "agent_message": (
                f"Hemos escalado esta negociación a tu account manager "
                f"{proposal['account_manager']} quien se pondrá en contacto contigo "
                f"directamente para encontrar la mejor solución."
            ),
            "intent":       "escalated_max_turns",
            "status":       STATUS_ESCALATED,
            "offer_price":  None,
        }

    # ── Generate next agent counter-offer ─────────────────────────────────────
    base_price  = proposal["suggested_price"] or 200.0
    discount    = DISCOUNT_BY_TURN.get(next_agent_turn, 0.20)
    offer_price = round(base_price * (1 - discount), 2)

    agent_msg = _build_agent_message(
        turn=next_agent_turn,
        client_name=proposal["client_name"],
        industry=proposal["industry"],
        opp_type=proposal["opportunity_type"],
        base_price=base_price,
        offer_price=offer_price,
        discount=discount,
        use_llm=True,
        client_last_message=client_message,
    )

    _write_turn(
        proposal_id=proposal_id,
        turn=len(thread) + 2,
        role="agent",
        message=agent_msg,
        intent=None,
        offer_price=offer_price,
    )

    _append_log({
        "event":        "agent_counter_offer",
        "proposal_id":  proposal_id,
        "turn":         next_agent_turn,
        "offer_price":  offer_price,
        "discount_pct": int(discount * 100),
        "simulated":    simulated,
    })

    return {
        "agent_message": agent_msg,
        "intent":        client_intent,
        "status":        STATUS_ACTIVE,
        "offer_price":   offer_price,
    }


def kill_negotiation(proposal_id: str, reason: str = "manual_kill_switch") -> bool:
    """
    Immediately halt a negotiation and escalate to the human account manager.
    Called from the kill-switch UI button.
    """
    conn = _schema.get_connection()
    proposal = _load_proposal(conn, proposal_id)
    conn.close()

    _close_negotiation(proposal_id, STATUS_ESCALATED)

    if proposal:
        _escalate(proposal_id, proposal.get("client_name", ""), proposal.get("account_manager", ""))

    _append_log({
        "event":       "kill_switch_activated",
        "proposal_id": proposal_id,
        "reason":      reason,
        "timestamp":   datetime.now().isoformat(),
    })

    print(f"[negotiator] Kill switch activated for proposal {proposal_id[:8]}… — {reason}")
    return True


def get_thread(proposal_id: str) -> list[dict]:
    """Return the full conversation thread for a proposal, ordered by turn."""
    conn = _schema.get_connection()
    rows = conn.execute(
        """
        SELECT id, proposal_id, turn, role, message, intent, offer_price, timestamp
        FROM negotiation_log
        WHERE proposal_id = ?
        ORDER BY turn ASC, id ASC
        """,
        (proposal_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_active_negotiations() -> list[dict]:
    """
    Return all proposals currently in active negotiation status.
    A proposal is in negotiation if it has entries in negotiation_log
    but no terminal status (accepted / rejected / escalated) recorded.
    """
    conn = _schema.get_connection()
    rows = conn.execute(
        """
        SELECT
            p.id            AS proposal_id,
            p.client_id,
            p.suggested_price,
            p.status        AS proposal_status,
            c.name          AS client_name,
            c.account_manager,
            c.industry,
            o.opportunity_type,
            o.score,
            COUNT(nl.id)    AS turn_count,
            MAX(nl.timestamp) AS last_activity
        FROM negotiation_log nl
        JOIN proposals      p  ON p.id  = nl.proposal_id
        JOIN clients        c  ON c.id  = p.client_id
        JOIN opportunities  o  ON o.id  = p.opportunity_id
        WHERE nl.proposal_id NOT IN (
            SELECT DISTINCT proposal_id FROM negotiation_log
            WHERE intent IN ('accepted', 'rejected', 'escalated',
                             'escalated_max_turns', 'manual_kill_switch')
        )
        GROUP BY p.id
        ORDER BY last_activity DESC
        """,
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_negotiation_summary() -> dict:
    """Aggregate statistics for the Sprint 7 dashboard KPI cards."""
    conn = _schema.get_connection()

    total = conn.execute(
        "SELECT COUNT(DISTINCT proposal_id) FROM negotiation_log"
    ).fetchone()[0]

    accepted = conn.execute(
        """SELECT COUNT(DISTINCT proposal_id) FROM negotiation_log
           WHERE intent = 'accepted'"""
    ).fetchone()[0]

    escalated = conn.execute(
        """SELECT COUNT(DISTINCT proposal_id) FROM negotiation_log
           WHERE intent IN ('escalated', 'escalated_max_turns', 'manual_kill_switch')"""
    ).fetchone()[0]

    rejected = conn.execute(
        """SELECT COUNT(DISTINCT proposal_id) FROM negotiation_log
           WHERE intent = 'rejected'"""
    ).fetchone()[0]

    active = total - accepted - escalated - rejected

    # Average discount given on accepted deals
    avg_discount_row = conn.execute(
        """
        SELECT AVG(
            CAST(REPLACE(SUBSTR(message, INSTR(message,'%')-2, 2), ' ', '') AS REAL)
        )
        FROM negotiation_log
        WHERE role = 'agent' AND offer_price IS NOT NULL
        """
    ).fetchone()[0]

    conn.close()

    return {
        "total_negotiations": total,
        "active":             max(0, active),
        "accepted":           accepted,
        "rejected":           rejected,
        "escalated":          escalated,
        "auto_resolution_rate": round(accepted / total * 100, 1) if total > 0 else 0.0,
    }


# ── DB helpers ────────────────────────────────────────────────────────────────

def _load_proposal(conn, proposal_id: str) -> dict | None:
    row = conn.execute(
        """
        SELECT p.*, o.opportunity_type, o.score,
               c.name AS client_name, c.account_manager, c.industry
        FROM proposals p
        JOIN opportunities o ON o.id = p.opportunity_id
        JOIN clients       c ON c.id = p.client_id
        WHERE p.id = ?
        """,
        (proposal_id,),
    ).fetchone()
    return dict(row) if row else None


def _write_turn(
    proposal_id: str,
    turn: int,
    role: str,
    message: str,
    intent: str | None,
    offer_price: float | None,
) -> int:
    conn = _schema.get_connection()
    cur = conn.execute(
        """
        INSERT INTO negotiation_log (proposal_id, turn, role, message, intent, offer_price)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (proposal_id, turn, role, message, intent, offer_price),
    )
    row_id = cur.lastrowid
    conn.commit()
    conn.close()
    return row_id


def _close_negotiation(proposal_id: str, final_status: str) -> None:
    """Update the proposal status in DB to reflect the negotiation outcome."""
    conn = _schema.get_connection()
    now = datetime.now().isoformat()
    new_status = {
        STATUS_ACCEPTED:  "accepted",
        STATUS_REJECTED:  "rejected",
        STATUS_ESCALATED: "escalated",
    }.get(final_status, "rejected")

    conn.execute(
        "UPDATE proposals SET status=?, updated_at=? WHERE id=?",
        (new_status, now, proposal_id),
    )
    # Mirror on the opportunity
    conn.execute(
        """
        UPDATE opportunities SET status=?, updated_at=?
        WHERE id = (SELECT opportunity_id FROM proposals WHERE id=?)
        """,
        (new_status if new_status != "accepted" else "closed", now, proposal_id),
    )
    conn.commit()
    conn.close()


def _escalate(proposal_id: str, client_name: str, manager: str) -> None:
    """Write an escalation record (mirrors feedback_loop escalation path)."""
    NEGOTIATION_LOG.parent.mkdir(parents=True, exist_ok=True)
    _append_log({
        "event":       "escalated_to_human",
        "proposal_id": proposal_id,
        "client_name": client_name,
        "manager":     manager,
        "timestamp":   datetime.now().isoformat(),
        "_production_integration": (
            "POST to SLACK_WEBHOOK_URL with @manager mention and link to negotiation thread."
        ),
    })
    print(f"[negotiator] Escalated {proposal_id[:8]}… to {manager or 'account manager'}")


def _append_log(entry: dict) -> None:
    NEGOTIATION_LOG.parent.mkdir(parents=True, exist_ok=True)
    with NEGOTIATION_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"timestamp": datetime.now().isoformat(), **entry},
                             ensure_ascii=False) + "\n")


# ── Intent extraction ─────────────────────────────────────────────────────────

import re as _re

# Each entry is a tuple (pattern, use_word_boundary).
# Phrases are matched as substrings; single tokens use \b word boundary.
_ACCEPT_PATTERNS = [
    "acepto", "de acuerdo", "trato hecho", r"\bok\b", r"\bsí\b",
    "perfecto", "agreed", "accept", "deal", "let's do it", "sounds good",
    "adelante", "procedamos", "me parece bien", r"\blisto\b", r"\bvamos\b",
]
_REJECT_PATTERNS = [
    "no me interesa", "no gracias", "rechaz", "no es para nosotros",
    "not interested", "no thanks", r"\bpass\b", r"\bdecline\b",
    "lo siento", "por ahora no",
]
_COUNTER_PATTERNS = [
    "podría ser", "qué tal si", "si bajas", "si llegas a",
    r"\bcounter\b", "¿podrías", "podemos hablar", "sería posible",
    r"\bnegociar\b",
]
_ESCALATE_PATTERNS = [
    "hablar con alguien", "persona real", "quiero hablar",
    r"\bstop\b", r"\bescalat", "complaint", "queja",
    "no más emails", "automated",
]


def _match_patterns(text_lower: str, patterns: list[str]) -> bool:
    """Return True if any pattern matches the (already lower-cased) text."""
    for pat in patterns:
        if pat.startswith(r"\b") or pat.startswith("(") or "|" in pat:
            if _re.search(pat, text_lower):
                return True
        elif pat in text_lower:
            return True
    return False


def _extract_intent(text: str) -> str:
    """Keyword-based intent classifier. LLM upgrade available in production."""
    lower = text.lower()

    if config.ANTHROPIC_API_KEY and config.LLM_PROVIDER in ("anthropic", "auto"):
        intent = _llm_extract_intent(text)
        if intent:
            return intent

    if _match_patterns(lower, _ESCALATE_PATTERNS):
        return NEG_INTENT_ESCALATE
    if _match_patterns(lower, _ACCEPT_PATTERNS):
        return NEG_INTENT_ACCEPT
    if _match_patterns(lower, _REJECT_PATTERNS):
        return NEG_INTENT_REJECT
    if _match_patterns(lower, _COUNTER_PATTERNS):
        return NEG_INTENT_COUNTER
    return NEG_INTENT_INFO


def _llm_extract_intent(text: str) -> str | None:
    """Use the LLM to classify the client's negotiation intent."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        prompt = dedent(f"""\
            Clasifica la siguiente respuesta de un cliente a una propuesta de precio
            en UNA de estas categorías:
              accepted      — acepta la propuesta o precio ofrecido
              rejected      — rechaza sin posibilidad de negociar
              counter_offer — propone un precio diferente o pide más descuento
              needs_info    — solicita más información antes de decidir
              escalated     — pide hablar con un humano o se queja del trato automatizado

            Respuesta del cliente: "{text}"

            Responde SOLO con la categoría exacta en minúsculas, sin más texto.
        """)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=20,
            messages=[{"role": "user", "content": prompt}],
        )
        result = msg.content[0].text.strip().lower()
        valid = {NEG_INTENT_ACCEPT, NEG_INTENT_REJECT, NEG_INTENT_COUNTER,
                 NEG_INTENT_INFO, NEG_INTENT_ESCALATE}
        return result if result in valid else None
    except Exception as e:
        print(f"[negotiator] LLM intent extraction failed: {e}")
        return None


# ── Agent message builder ─────────────────────────────────────────────────────

_TURN_TEMPLATES = {
    1: dedent("""\
        Dear {client_name},

        We completely understand that budget is a key factor in your decision,
        and we want to do everything we can to find a point that works for both sides.

        As a sign of our commitment to your success in {industry}, we are pleased
        to offer a special reduction of **{discount_pct}%** off the original price:

        ~~${base_price:,.0f} USD~~ → **${offer_price:,.0f} USD**

        This price includes exactly the same deliverables and the same results
        guarantee. The reduction is possible because we value building a long-term
        relationship with {client_name}.

        Does this revised proposal work for you?

        Warm regards,
        OPB Marketing
    """),

    2: dedent("""\
        Dear {client_name},

        We appreciate your willingness to keep the conversation going. We have
        reviewed our margins internally and are able to offer an additional reduction:

        Revised final price: **${offer_price:,.0f} USD** ({discount_pct}% discount)

        To be completely transparent: this is our flexibility limit for this type
        of project in the {industry} sector. At this price we guarantee the same
        quality and the same timelines originally committed.

        I would like to suggest a 15-minute call to walk through the deliverables
        together and confirm this price makes sense for your business.
        Do you have availability this week?

        Best regards,
        OPB Marketing
    """),

    3: dedent("""\
        Dear {client_name},

        This is our final offer: **${offer_price:,.0f} USD** — a {discount_pct}%
        discount off the list price, which is the maximum we can offer without
        compromising the quality of the work.

        If this price does not fit your current budget, I completely understand.
        What I would like is to keep the door open: if your situation changes in
        the next 30 days, this price will still be available to you.

        Alternatively, I can connect you directly with your account manager
        to explore a payment plan or other options.

        Would you like {manager_note} to give you a call to discuss this?

        Sincerely,
        OPB Marketing
    """),
}


def _build_agent_message(
    turn: int,
    client_name: str,
    industry: str,
    opp_type: str,
    base_price: float,
    offer_price: float,
    discount: float,
    use_llm: bool = True,
    client_last_message: str | None = None,
) -> str:
    """Generate the agent's negotiation message for a given turn."""
    # Try LLM first
    if use_llm and not config.DEMO_MODE:
        msg = _llm_build_message(
            turn, client_name, industry, opp_type,
            base_price, offer_price, discount, client_last_message,
        )
        if msg:
            return msg

    # Template fallback
    template = _TURN_TEMPLATES.get(turn, _TURN_TEMPLATES[3])
    return template.format(
        client_name=client_name,
        industry=industry,
        base_price=base_price,
        offer_price=offer_price,
        discount_pct=int(discount * 100),
        manager_note="su account manager",
    )


def _llm_build_message(
    turn: int,
    client_name: str,
    industry: str,
    opp_type: str,
    base_price: float,
    offer_price: float,
    discount: float,
    client_last_message: str | None,
) -> str | None:
    """Generate a negotiation message using the LLM."""
    label = OPPORTUNITY_LABELS.get(opp_type, opp_type.replace("_", " ").title())
    context = (
        f"El cliente respondió: '{client_last_message}'" if client_last_message
        else "El cliente indicó que el precio es demasiado alto."
    )

    prompt = dedent(f"""\
        Eres un especialista en ventas de una agencia de marketing digital
        escribiendo un email de negociación de precio en español.

        CONTEXTO:
        - Cliente: {client_name} (sector: {industry})
        - Servicio ofrecido: {label}
        - Precio original: ${base_price:,.0f} USD
        - Precio que ofrecemos ahora: ${offer_price:,.0f} USD ({int(discount*100)}% descuento)
        - Turno de negociación: {turn} de {MAX_AGENT_TURNS}
        - {context}

        TAREA:
        Escribe un email de negociación corto (máx. 150 palabras) que:
        1. Reconozca la preocupación del cliente sin ser defensivo.
        2. Presente el precio reducido de forma clara: ${offer_price:,.0f} USD.
        3. Justifique el valor con 1 argumento específico del sector {industry}.
        4. Termine con una pregunta abierta para mantener el diálogo.
        5. Tono profesional y cercano, en español.

        Responde SOLO con el cuerpo del email, sin asunto, sin formato markdown.
    """)

    for provider, key_attr, call_fn in [
        ("anthropic", "ANTHROPIC_API_KEY", _call_anthropic),
        ("openai",    "OPENAI_API_KEY",    _call_openai),
    ]:
        if getattr(config, key_attr) and config.LLM_PROVIDER in (provider, "auto"):
            result = call_fn(prompt)
            if result:
                return result
    return None


def _call_anthropic(prompt: str) -> str | None:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        print(f"[negotiator] Anthropic call failed: {e}")
        return None


def _call_openai(prompt: str) -> str | None:
    try:
        import openai
        client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[negotiator] OpenAI call failed: {e}")
        return None
