"""
Sprint 7 — Autonomous Negotiation Dashboard.

This page visualises and controls the negotiation engine:

  ┌─────────────────────────────────────────────────────────────────┐
  │  KPI row:  Active  |  Auto-resolved  |  Escalated  |  Rate     │
  ├─────────────────────────────────────────────────────────────────┤
  │  Active Negotiations panel                                      │
  │    For each negotiation: client name, turn count, last offer,   │
  │    conversation thread, ⚡ Kill Switch  / ✅ Mark Accepted      │
  ├─────────────────────────────────────────────────────────────────┤
  │  Demo simulation panel                                          │
  │    Pick a client → trigger 'too_expensive' reply → watch turns  │
  ├─────────────────────────────────────────────────────────────────┤
  │  Payment Links panel                                            │
  │    Proposals with accepted/paid status; generate / view links   │
  └─────────────────────────────────────────────────────────────────┘

"In Production" annotations explain the real-world integrations at every step.
"""

from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import streamlit as st

from src.agents.negotiator import (
    start_negotiation,
    process_client_reply,
    kill_negotiation,
    get_thread,
    get_active_negotiations,
    get_negotiation_summary,
    STATUS_ACTIVE, STATUS_ACCEPTED, STATUS_REJECTED, STATUS_ESCALATED,
    NEG_INTENT_ACCEPT, NEG_INTENT_REJECT, NEG_INTENT_COUNTER, NEG_INTENT_INFO,
)
from src.agents.payment_link import create_payment_link, list_payment_links, get_payment_link
from src.agents.feedback_loop import record_client_reply, INTENT_TOO_EXPENSIVE, INTENT_ACCEPTED
from src.agents.proposal_generator import get_all_proposals
from src.data_sources.crm import get_all_clients
from src.ui.components import page_header, section_header, production_badge, score_bar


# ── Simulated client replies for the demo ─────────────────────────────────────
_SIM_REPLIES = {
    "Acepta la oferta (Turn 1)":    "Perfecto, acepto. Procedamos con el descuento ofrecido.",
    "Pide más descuento":           "Gracias, pero sería posible llegar a un poco más de descuento?",
    "Rechaza definitivamente":      "Lo siento, no nos interesa en este momento.",
    "Ignora — sin respuesta clara": "Mmm, déjame pensarlo y te aviso.",
    "Pide hablar con una persona":  "Por favor detengan los emails automáticos, quiero hablar con alguien.",
}

_INTENT_BADGE = {
    NEG_INTENT_ACCEPT:   ("✅", "#1b5e20"),
    NEG_INTENT_REJECT:   ("❌", "#b71c1c"),
    NEG_INTENT_COUNTER:  ("🔄", "#e65100"),
    NEG_INTENT_INFO:     ("❓", "#1a237e"),
    "escalated":         ("🚨", "#880e4f"),
    None:                ("⚙️",  "#424242"),
}


# ── Main render ───────────────────────────────────────────────────────────────

def render() -> None:
    page_header(
        "Negociación Autónoma",
        "El agente negocia precio con clientes en múltiples turnos usando LLM.",
        sprint="Sprint 7",
    )

    production_badge(
        "Las respuestas del cliente llegan vía SendGrid Inbound Parse. "
        "El agente responde en &lt; 2 min. Stripe genera el link de pago al cierre.",
    )

    summary = get_negotiation_summary()
    _render_kpis(summary)

    st.divider()

    tab_active, tab_demo, tab_payments, tab_history = st.tabs([
        "⚡ Negociaciones Activas",
        "🎭 Demo Simulación",
        "💳 Links de Pago",
        "📜 Historial",
    ])

    with tab_active:
        _render_active_negotiations()

    with tab_demo:
        _render_demo_panel()

    with tab_payments:
        _render_payment_links()

    with tab_history:
        _render_history()


# ── KPI row ───────────────────────────────────────────────────────────────────

def _render_kpis(summary: dict) -> None:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Negociaciones totales",  summary["total_negotiations"])
    c2.metric("Activas",                summary["active"],
              delta=None if summary["active"] == 0 else f"{summary['active']} en curso")
    c3.metric("Auto-resueltas",         summary["accepted"],
              delta=f"{summary['auto_resolution_rate']}%" if summary["total_negotiations"] > 0 else None,
              delta_color="normal")
    c4.metric("Rechazadas",             summary["rejected"])
    c5.metric("Escaladas a humano",     summary["escalated"])


# ── Active negotiations panel ─────────────────────────────────────────────────

def _render_active_negotiations() -> None:
    section_header("Negociaciones en Curso")

    active = get_active_negotiations()

    if not active:
        st.info(
            "No hay negociaciones activas. "
            "Ve a la pestaña **Demo Simulación** para iniciar una.",
            icon="ℹ️",
        )
        return

    for neg in active:
        pid    = neg["proposal_id"]
        thread = get_thread(pid)

        with st.expander(
            f"**{neg['client_name']}** — {neg['opportunity_type'].replace('_',' ').title()} "
            f"| Turno {neg['turn_count']} | Última actividad: {neg['last_activity'][:10]}",
            expanded=True,
        ):
            col_info, col_actions = st.columns([3, 1])

            with col_info:
                st.caption(
                    f"Score: {neg['score'] or 0:.0f} · "
                    f"Precio original: ${neg['suggested_price'] or 0:,.0f} · "
                    f"Sector: {neg['industry']}"
                )

                # Chat thread
                _render_thread(thread)

            with col_actions:
                st.markdown("**Acciones**")

                # Manual reply input
                client_reply = st.text_area(
                    "Simular respuesta del cliente",
                    key=f"reply_{pid}",
                    height=80,
                    placeholder="El cliente responde…",
                )
                if st.button("Enviar respuesta", key=f"send_{pid}", use_container_width=True):
                    if client_reply.strip():
                        with st.spinner("El agente está procesando…"):
                            result = process_client_reply(pid, client_reply.strip())
                        st.success(f"Intent detectado: **{result['intent']}**")
                        if result.get("offer_price"):
                            st.info(f"Nueva oferta: **${result['offer_price']:,.0f}**")
                        if result["status"] == STATUS_ACCEPTED:
                            st.balloons()
                        st.rerun()
                    else:
                        st.warning("Escribe una respuesta primero.")

                st.markdown("---")

                # Kill switch
                if st.button(
                    "🚨 Kill Switch — Escalar a humano",
                    key=f"kill_{pid}",
                    use_container_width=True,
                    type="primary",
                ):
                    kill_negotiation(pid, reason="manual_kill_switch_ui")
                    st.warning(
                        f"Negociación escalada al account manager "
                        f"**{neg['account_manager']}**."
                    )
                    st.rerun()

                st.caption(
                    "⚠️ El kill switch detiene la negociación automática "
                    "y notifica al account manager vía Slack en producción."
                )


def _render_thread(thread: list[dict]) -> None:
    """Render a negotiation conversation as a chat-style display."""
    if not thread:
        st.caption("Sin mensajes aún.")
        return

    for turn in thread:
        role        = turn["role"]
        msg         = turn["message"] or ""
        intent      = turn.get("intent")
        offer_price = turn.get("offer_price")
        ts          = (turn.get("timestamp") or "")[:16]

        icon_char, color = _INTENT_BADGE.get(intent, _INTENT_BADGE[None])
        price_tag  = f" · Oferta: **${offer_price:,.0f}**" if offer_price else ""
        intent_tag = f" · {icon_char} `{intent}`" if intent else ""

        if role == "agent":
            st.html(
                f"<div style='"
                f"background:#E8EFF8;border-radius:8px;"
                f"padding:10px 14px;margin:6px 0;"
                f"border-left:3px solid #003366;"
                f"font-family:Plus Jakarta Sans,sans-serif;'>"
                f"<div style='font-size:10px;font-weight:700;letter-spacing:.8px;"
                f"text-transform:uppercase;color:#003366;margin-bottom:4px;'>"
                f"Agente&nbsp;&nbsp;<span style='font-weight:400;color:#6B7280;"
                f"text-transform:none;letter-spacing:0;'>{ts}{price_tag}</span>"
                f"</div>"
                f"<div style='font-size:13px;color:#0D1B2E;line-height:1.6;'>"
                f"{msg[:400]}{'…' if len(msg)>400 else ''}</div>"
                f"</div>"
            )
        else:
            st.html(
                f"<div style='"
                f"background:#FBF5E6;border-radius:8px;"
                f"padding:10px 14px;margin:6px 0;"
                f"border-left:3px solid #C8982A;"
                f"font-family:Plus Jakarta Sans,sans-serif;'>"
                f"<div style='font-size:10px;font-weight:700;letter-spacing:.8px;"
                f"text-transform:uppercase;color:#92400E;margin-bottom:4px;'>"
                f"Cliente&nbsp;&nbsp;<span style='font-weight:400;color:#6B7280;"
                f"text-transform:none;letter-spacing:0;'>{ts}{intent_tag}</span>"
                f"</div>"
                f"<div style='font-size:13px;color:#0D1B2E;line-height:1.6;'>"
                f"{msg[:300]}{'…' if len(msg)>300 else ''}</div>"
                f"</div>"
            )


# ── Demo simulation panel ─────────────────────────────────────────────────────

def _render_demo_panel() -> None:
    section_header("Demo: Simulación de Negociación Completa")
    st.caption(
        "Elige una propuesta existente (o crea una nueva vía la página Proposals), "
        "simula una respuesta 'precio muy alto' y observa cómo el agente negocia."
    )

    # Pick a proposal
    all_proposals = get_all_proposals()
    sent_proposals = [
        p for p in all_proposals
        if p["status"] in ("sent", "draft", "approved", "rejected")
    ]

    if not sent_proposals:
        st.warning("No hay propuestas disponibles. Genera una en la página **Proposals**.")
        return

    options = {
        f"{p['client_name']} — {p['opportunity_type'].replace('_',' ').title()} "
        f"(${p['suggested_price']:,.0f}) [{p['status']}]": p["id"]
        for p in sent_proposals
    }

    col_select, col_btn = st.columns([3, 1])
    with col_select:
        selected_label = st.selectbox(
            "Propuesta a negociar",
            list(options.keys()),
            key="demo_proposal_select",
        )
    selected_pid = options[selected_label]

    # Step 1: trigger too_expensive
    st.markdown("**Paso 1 — El cliente dice: 'Precio muy alto'**")
    if st.button(
        "▶ Simular respuesta 'Too Expensive'",
        key="sim_too_expensive",
        type="primary",
    ):
        with st.spinner("Registrando respuesta del cliente e iniciando negociación…"):
            try:
                # Trigger through feedback_loop so all integrations fire
                record_client_reply(
                    selected_pid,
                    intent=INTENT_TOO_EXPENSIVE,
                    notes="[DEMO] Cliente indicó que el precio es demasiado alto.",
                    simulated=True,
                )
                st.success(
                    "✅ Respuesta registrada. El agente ha abierto una negociación "
                    "con un 10% de descuento. Ve a la pestaña **Negociaciones Activas**."
                )
            except Exception as e:
                # Fallback: call negotiator directly if proposal is in wrong state
                try:
                    neg = start_negotiation(selected_pid)
                    st.success(
                        f"✅ Negociación iniciada directamente. "
                        f"Oferta: **${neg.get('offer_price', 0):,.0f}**"
                    )
                except Exception as e2:
                    st.error(f"Error: {e2}")
        st.rerun()

    st.divider()
    st.markdown("**Paso 2 — Simular respuesta del cliente al counter-offer**")

    thread = get_thread(selected_pid)
    if thread:
        _render_thread(thread)

        reply_choice = st.selectbox(
            "Tipo de respuesta del cliente",
            list(_SIM_REPLIES.keys()),
            key="sim_reply_choice",
        )
        sim_text = _SIM_REPLIES[reply_choice]
        st.info(f"Texto de la respuesta: *\"{sim_text}\"*")

        if st.button("▶ Enviar respuesta simulada", key="sim_reply_btn", type="primary"):
            with st.spinner("El agente procesa la respuesta…"):
                result = process_client_reply(selected_pid, sim_text, simulated=True)
            st.success(f"Intent detectado: **{result['intent']}** | Status: **{result['status']}**")
            if result.get("offer_price"):
                st.info(f"Nueva oferta del agente: **${result['offer_price']:,.0f}**")
            if result["status"] == STATUS_ACCEPTED:
                st.balloons()
                link = get_payment_link(selected_pid)
                if not link:
                    link_result = create_payment_link(selected_pid)
                    link = link_result["url"]
                st.success(f"💳 Link de pago generado: `{link}`")
            st.rerun()
    else:
        st.caption("Primero ejecuta el Paso 1 para iniciar la negociación.")

    production_badge(
        "En producción, las respuestas del cliente llegan vía SendGrid Inbound Parse "
        "webhook. El agente identifica el thread por el header Message-ID, extrae el "
        "intent con el LLM y envía la respuesta en menos de 2 minutos.",
    )


# ── Payment links panel ───────────────────────────────────────────────────────

def _render_payment_links() -> None:
    section_header("Links de Pago Stripe")

    production_badge(
        "POST /v1/payment_links con price_data. El cliente recibe el link "
        "por email. Webhook checkout.session.completed → estado 'paid' en DB.",
    )

    links = list_payment_links()

    if not links:
        st.info("No hay links de pago generados aún.", icon="ℹ️")
        _render_manual_link_generator()
        return

    for link in links:
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.markdown(f"**{link['client_name']}**")
                st.caption(
                    f"{link['opportunity_type'].replace('_',' ').title()} · "
                    f"Estado: `{link['status']}` · "
                    f"{link['created_at'][:10]}"
                )
            with col2:
                st.metric("Monto", f"${link['suggested_price']:,.0f}")
            with col3:
                st.link_button(
                    "Abrir link",
                    url=link["payment_link"],
                    use_container_width=True,
                )
            st.code(link["payment_link"], language=None)

    st.divider()
    _render_manual_link_generator()


def _render_manual_link_generator() -> None:
    st.markdown("**Generar link de pago manualmente**")

    accepted_proposals = [
        p for p in get_all_proposals()
        if p["status"] in ("accepted", "sent", "approved") and not get_payment_link(p["id"])
    ]

    if not accepted_proposals:
        st.caption("No hay propuestas aceptadas/enviadas sin link de pago.")
        return

    options = {
        f"{p['client_name']} — ${p['suggested_price']:,.0f} [{p['status']}]": p["id"]
        for p in accepted_proposals
    }

    col_sel, col_price, col_btn = st.columns([3, 1, 1])
    with col_sel:
        label = st.selectbox("Propuesta", list(options.keys()), key="payment_proposal_select")
    pid = options[label]
    base_price = next(p["suggested_price"] for p in accepted_proposals if p["id"] == pid)

    with col_price:
        custom = st.number_input(
            "Monto (USD)", value=float(base_price), min_value=1.0, key="payment_amount"
        )
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💳 Generar Link", key="gen_payment_link", use_container_width=True):
            with st.spinner("Generando link…"):
                result = create_payment_link(pid, custom_amount=custom)
            st.success("Link generado:")
            st.code(result["url"])
            st.rerun()


# ── History panel ─────────────────────────────────────────────────────────────

def _render_history() -> None:
    section_header("Historial de Negociaciones")

    from src.db.schema import get_connection
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT nl.proposal_id, nl.turn, nl.role, nl.message,
               nl.intent, nl.offer_price, nl.timestamp,
               c.name AS client_name,
               o.opportunity_type
        FROM negotiation_log nl
        JOIN proposals      p  ON p.id  = nl.proposal_id
        JOIN clients        c  ON c.id  = p.client_id
        JOIN opportunities  o  ON o.id  = p.opportunity_id
        ORDER BY nl.timestamp DESC
        LIMIT 200
        """
    ).fetchall()
    conn.close()

    if not rows:
        st.info("No hay historial de negociaciones.", icon="ℹ️")
        return

    import pandas as pd
    df = pd.DataFrame([dict(r) for r in rows])
    df["message_preview"] = df["message"].str[:80] + "…"
    df = df[["timestamp", "client_name", "opportunity_type",
             "turn", "role", "intent", "offer_price", "message_preview"]]
    df.columns = ["Timestamp", "Cliente", "Tipo", "Turno", "Rol", "Intent",
                  "Precio oferta", "Mensaje (preview)"]
    st.dataframe(df, use_container_width=True, hide_index=True)
