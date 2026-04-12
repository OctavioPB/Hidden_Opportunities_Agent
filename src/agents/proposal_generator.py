"""
Sprint 3 — Automated Proposal Generator.

Workflow
--------
1. Load opportunity + client data from the DB.
2. Pull the latest metrics snapshot for the client (same data sources used by
   the detection engine).
3. Fill a structured template specific to the opportunity type (subject line,
   opening hook, value proposition, call to action).
4. Call the configured LLM (OpenAI / Anthropic / local fallback) to generate
   a personalized insight paragraph grounded in the client's specific numbers.
5. Persist the assembled proposal in the `proposals` DB table (status='draft').
6. Export the proposal as a Markdown file under data/exports/proposals/.
7. Return the proposal ID.

In production
-------------
- LLM call: OpenAI GPT-3.5/4 or Claude Haiku via API.
- Export: uploaded to a shared Google Drive folder named after the client.
- Notification: Slack message to the account manager's DM with an Approve /
  Reject button (incoming webhook + interactive block).
- Approval command: /approve <proposal_id> in Slack triggers the send.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import Any

import config
from src.db.schema import get_connection
from src.data_sources import crm
from src.data_sources import google_analytics as ga
from src.data_sources import meta_ads
from src.data_sources import email_marketing
from src.data_sources import seo
from src.agents.rules import OPPORTUNITY_LABELS, SUGGESTED_PRICES


# ── Export directory ──────────────────────────────────────────────────────────
PROPOSALS_DIR = config.EXPORTS_DIR / "proposals"
PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)


# ── Proposal templates (one per opportunity type) ─────────────────────────────
# Each template uses {placeholders} that are filled from client+metric data.
# The {{insight_paragraph}} placeholder is replaced by the LLM-generated text.

PROPOSAL_TEMPLATES: dict[str, dict[str, str]] = {
    "landing_page_optimization": {
        "subject": "Propuesta: Optimización de Landing Page para {client_name}",
        "body": dedent("""\
            Estimado/a {client_name},

            Hemos estado monitoreando el rendimiento de tus campañas y encontramos
            una oportunidad concreta para mejorar tus resultados en {industry}.

            **Lo que vemos en tus datos:**
            - CTR actual: **{ctr:.1%}** (excelente — tus anuncios están funcionando)
            - Tasa de rebote: **{bounce_rate:.0%}** (por encima del promedio ideal de 55%)
            - Páginas por sesión: **{pages_per_session:.1f}** (los visitantes no están explorando)

            {insight_paragraph}

            **Nuestra propuesta:** A/B test de landing page optimizada
            - Precio: **${suggested_price:,.0f} USD**
            - Duración: 3 semanas (diseño + implementación + análisis)
            - Garantía: si no mejoramos la tasa de conversión en un 20%, te devolvemos
              el 50% del valor.

            ¿Tienes 15 minutos esta semana para ver un mockup?

            Saludos,
            El equipo de Hidden Opportunities Agency

            ---
            *Esta propuesta fue generada automáticamente por el agente de oportunidades.
            Fue revisada y aprobada por tu account manager antes de enviarse.*
        """),
    },

    "seo_content": {
        "subject": "Propuesta: Estrategia de Contenido SEO para {client_name}",
        "body": dedent("""\
            Estimado/a {client_name},

            Tu sitio web en el sector {industry} tiene una base orgánica interesante
            que no está siendo aprovechada al máximo.

            **Lo que vemos en tus datos:**
            - Tráfico orgánico mensual: **{organic_traffic:,} visitas**
            - Keywords posicionadas: **{keyword_rankings}** (hay margen de crecimiento)
            - Tasa de conversión orgánica: **{conversion_rate:.1%}**

            {insight_paragraph}

            **Nuestra propuesta:** Paquete de Contenido SEO — 4 artículos/mes
            - Precio: **${suggested_price:,.0f} USD / mes**
            - Incluye: investigación de keywords, redacción, optimización on-page
            - Resultado esperado: +40% tráfico orgánico en 90 días

            ¿Te gustaría ver el calendario editorial que preparamos para ti?

            Saludos,
            El equipo de Hidden Opportunities Agency
        """),
    },

    "retargeting_campaign": {
        "subject": "Propuesta: Campaña de Retargeting para {client_name}",
        "body": dedent("""\
            Estimado/a {client_name},

            Tus campañas publicitarias en {industry} están generando tráfico,
            pero existe una oportunidad significativa para recuperar a los visitantes
            que no convirtieron en su primera visita.

            **Lo que vemos en tus datos:**
            - Inversión mensual estimada: **${monthly_ad_spend:,.0f} USD**
            - ROAS actual: **{roas:.1f}x** (objetivo: ≥ 3.5x)
            - Oportunidad: audiencias cálidas sin retargeting activo

            {insight_paragraph}

            **Nuestra propuesta:** Campaña de Retargeting Multi-Canal
            - Precio: **${suggested_price:,.0f} USD** (setup + gestión del primer mes)
            - Canales: Meta Ads + Google Display
            - Resultado esperado: reducción del 30–50% en costo por adquisición

            ¿Coordinamos una llamada de 20 minutos para revisar la estrategia?

            Saludos,
            El equipo de Hidden Opportunities Agency
        """),
    },

    "email_automation": {
        "subject": "Propuesta: Automatización de Email Marketing para {client_name}",
        "body": dedent("""\
            Estimado/a {client_name},

            Tu base de suscriptores en {industry} es un activo valioso que
            actualmente no está generando su potencial máximo de ingresos.

            **Lo que vemos en tus datos:**
            - Tasa de apertura actual: **{email_open_rate:.1%}** (promedio industria: 21%)
            - Oportunidad: flujos automatizados pueden 2–3x las métricas actuales

            {insight_paragraph}

            **Nuestra propuesta:** Setup de Email Automation en 3 flujos
            - Precio: **${suggested_price:,.0f} USD** (implementación única)
            - Flujos: Bienvenida → Nutrición → Reactivación
            - Plataforma: tu ESP actual (Mailchimp / ActiveCampaign / Klaviyo)
            - Resultado esperado: tasa de apertura ≥ 30% en 60 días

            ¿Te enviamos ejemplos de los flujos que implementaríamos?

            Saludos,
            El equipo de Hidden Opportunities Agency
        """),
    },

    "reactivation": {
        "subject": "¡Hola {client_name}! Tenemos algo especial para ti",
        "body": dedent("""\
            Estimado/a {client_name},

            Han pasado {days_inactive} días desde que trabajamos juntos activamente,
            y queremos reconectar con una propuesta especial diseñada para tu negocio
            en {industry}.

            {insight_paragraph}

            **Oferta de Reactivación Express — válida por 7 días:**
            - Auditoría completa de tu presencia digital: **GRATIS**
            - Plan de acción personalizado: incluido
            - Primer mes de servicio con **20% de descuento** (ahorro de
              ${savings:,.0f} USD sobre el precio estándar)
            - Precio con descuento: **${discounted_price:,.0f} USD**

            Esta es nuestra forma de decirte que valoramos la relación que
            construimos y queremos seguir generando resultados para ti.

            ¿Tienes 15 minutos esta semana para ponernos al día?

            Con gusto,
            El equipo de Hidden Opportunities Agency

            ---
            *Oferta válida hasta {offer_expiry}.*
        """),
    },

    "conversion_rate_audit": {
        "subject": "Propuesta: Auditoría de Tasa de Conversión para {client_name}",
        "body": dedent("""\
            Estimado/a {client_name},

            Detectamos una discrepancia importante en el funnel de tu negocio
            en {industry} que está costándote ventas todos los días.

            **Lo que vemos en tus datos:**
            - CTR de anuncios: **{ctr:.1%}** (excelente — la gente hace clic)
            - Tasa de conversión: **{conversion_rate:.2%}** (muy por debajo del esperado)
            - Oportunidad de mejora: por cada 1,000 visitantes, podrías tener
              {potential_conversions:.0f} conversiones adicionales

            {insight_paragraph}

            **Nuestra propuesta:** Auditoría CRO + Plan de Acción
            - Precio: **${suggested_price:,.0f} USD**
            - Entregable: reporte con 5–10 recomendaciones priorizadas
            - Tiempo: 1 semana de análisis + presentación ejecutiva
            - Garantía: identificamos al menos 3 quick wins implementables

            ¿Agendamos una sesión de diagnóstico esta semana?

            Saludos,
            El equipo de Hidden Opportunities Agency
        """),
    },

    "upsell_ad_budget": {
        "subject": "Propuesta: Escalar tu Inversión Publicitaria — {client_name}",
        "body": dedent("""\
            Estimado/a {client_name},

            Tenemos una noticia muy positiva: tus campañas en {industry}
            están funcionando mejor de lo esperado, y existe una oportunidad
            concreta para escalar los resultados.

            **Lo que vemos en tus datos:**
            - ROAS actual: **{roas:.1f}x** (por encima del benchmark de 4x)
            - Inversión mensual: **${monthly_ad_spend:,.0f} USD**
            - ROI proyectado con escala: cada $1 adicional genera ${roas:.2f} en ingresos

            {insight_paragraph}

            **Nuestra propuesta:** Plan de Escala Publicitaria — 60 días
            - Precio de gestión: **${suggested_price:,.0f} USD / mes**
            - Presupuesto recomendado: ${recommended_budget:,.0f} USD/mes
            - Estrategia: escalar los ad sets de mejor rendimiento + expansión
              a nuevas audiencias similares
            - Resultado esperado: +{projected_revenue_increase:.0f}% en ingresos
              sin degradar el ROAS

            ¿Revisamos juntos las campañas que queremos escalar?

            Saludos,
            El equipo de Hidden Opportunities Agency
        """),
    },
}


# ── Context builder ───────────────────────────────────────────────────────────

def _build_context(client: dict, metrics: dict, opp_type: str) -> dict:
    """
    Build the template rendering context from client data and metrics.
    All computed fields are added here so templates stay clean.
    """
    ad_spend_daily = metrics.get("ad_spend", 0) or 0
    monthly_spend  = ad_spend_daily * 30
    roas           = metrics.get("roas", 0) or 0
    price          = SUGGESTED_PRICES.get(opp_type, 200)
    ctr            = metrics.get("ctr", 0) or 0
    conv_rate      = metrics.get("conversion_rate", 0.01) or 0.01
    days_inactive  = metrics.get("days_inactive", 0) or 0

    # Offer expiry (7 days from today — demo: uses static date)
    from datetime import timedelta
    offer_expiry = (datetime.now() + timedelta(days=7)).strftime("%d/%m/%Y")

    return {
        # Client basics
        "client_name":       client.get("name", "Cliente"),
        "industry":          client.get("industry", "su sector"),
        "account_manager":   client.get("account_manager", "Tu account manager"),
        "contact_email":     client.get("contact_email", ""),

        # Metrics
        "ctr":               ctr,
        "bounce_rate":       metrics.get("bounce_rate", 0) or 0,
        "pages_per_session": metrics.get("pages_per_session", 1) or 1,
        "conversion_rate":   conv_rate,
        "organic_traffic":   metrics.get("organic_traffic", 0) or 0,
        "keyword_rankings":  metrics.get("keyword_rankings", 0) or 0,
        "email_open_rate":   metrics.get("email_open_rate", 0) or 0,
        "roas":              roas,
        "monthly_ad_spend":  monthly_spend,
        "days_inactive":     days_inactive,

        # Derived
        "suggested_price":           price,
        "savings":                   round(price * 0.20),
        "discounted_price":          round(price * 0.80),
        "offer_expiry":              offer_expiry,
        "potential_conversions":     (0.03 - conv_rate) * 1000 if conv_rate < 0.03 else 10,
        "recommended_budget":        monthly_spend * 2,
        "projected_revenue_increase": (roas / 4.0 - 1) * 100 if roas > 0 else 25,

        # Placeholder for LLM paragraph
        "insight_paragraph": "",
    }


# ── LLM integration ───────────────────────────────────────────────────────────

def _build_llm_prompt(ctx: dict, opp_type: str, rationale: str) -> str:
    """
    Build the prompt sent to the LLM to generate the personalized paragraph.
    The paragraph grounds the proposal in specific client numbers.
    """
    label = OPPORTUNITY_LABELS.get(opp_type, opp_type.replace("_", " ").title())
    return dedent(f"""\
        Eres un experto en marketing digital escribiendo una propuesta comercial
        personalizada para un cliente de agencia.

        DATOS DEL CLIENTE:
        - Nombre: {ctx['client_name']}
        - Industria: {ctx['industry']}
        - Oportunidad detectada: {label}
        - Análisis del agente: {rationale}

        MÉTRICAS CLAVE:
        {json.dumps({k: v for k, v in ctx.items()
                     if k not in ('client_name', 'industry', 'insight_paragraph',
                                  'contact_email', 'account_manager', 'offer_expiry')
                     and isinstance(v, (int, float))}, indent=2, ensure_ascii=False)}

        TAREA:
        Escribe UN párrafo (3–4 oraciones) que:
        1. Mencione un insight específico usando los números del cliente (no genérico).
        2. Conecte el problema detectado con el impacto en su negocio ({ctx['industry']}).
        3. Use un tono profesional pero cercano, en español.
        4. NO repita información ya mencionada en el email — es un párrafo de análisis adicional.

        Responde SOLO con el párrafo, sin título, sin comillas, sin formato extra.
    """)


def _call_llm(prompt: str) -> str | None:
    """
    Call the configured LLM. Returns the insight paragraph or None on failure.

    Tries in order:
      1. Anthropic (Claude) — if ANTHROPIC_API_KEY is set
      2. OpenAI — if OPENAI_API_KEY is set
      3. Returns None → caller uses template fallback
    """
    # ── Anthropic ──────────────────────────────────────────────────────────────
    if config.ANTHROPIC_API_KEY and config.LLM_PROVIDER in ("anthropic", "auto"):
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
            msg = client.messages.create(
                model=config.LLM_MODEL if "claude" in config.LLM_MODEL else "claude-haiku-4-5-20251001",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text.strip()
        except Exception as e:
            print(f"[proposal_generator] Anthropic call failed: {e}")

    # ── OpenAI ─────────────────────────────────────────────────────────────────
    if config.OPENAI_API_KEY and config.LLM_PROVIDER in ("openai", "auto"):
        try:
            import openai
            client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
            resp = client.chat.completions.create(
                model=config.LLM_MODEL if config.LLM_MODEL.startswith("gpt") else "gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.7,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"[proposal_generator] OpenAI call failed: {e}")

    return None  # no LLM available


def _template_insight(ctx: dict, opp_type: str, rationale: str) -> str:
    """
    Deterministic fallback when no LLM is configured.
    Returns a richly formatted paragraph derived from the rule rationale.
    """
    client   = ctx["client_name"]
    industry = ctx["industry"]

    insights = {
        "landing_page_optimization": (
            f"Para ser más concretos: con un CTR de {ctx['ctr']:.1%}, "
            f"{client} está pagando para que visitantes lleguen a la página, "
            f"pero el {ctx['bounce_rate']:.0%} de ellos se va en los primeros segundos. "
            f"En el sector {industry}, esto equivale a dejar ingresos potenciales "
            f"sobre la mesa cada día que pasa sin optimización. "
            f"Una landing enfocada en conversión, con un solo CTA claro, "
            f"típicamente reduce la tasa de rebote entre 15 y 25 puntos porcentuales."
        ),
        "seo_content": (
            f"Con {ctx['organic_traffic']:,} visitas mensuales orgánicas y solo "
            f"{ctx['keyword_rankings']} keywords posicionadas, {client} está captando "
            f"una fracción del tráfico disponible en {industry}. "
            f"Competidores con estrategias de contenido estructuradas suelen rankear "
            f"para 80–150 keywords en el mismo nicho. "
            f"Un blog con 4 artículos optimizados al mes puede triplicar el alcance "
            f"orgánico en 6 meses sin incrementar el presupuesto publicitario."
        ),
        "retargeting_campaign": (
            f"Con una inversión mensual de ~${ctx['monthly_ad_spend']:,.0f} y un ROAS "
            f"de {ctx['roas']:.1f}x, hay margen real para mejorar la eficiencia. "
            f"El retargeting captura a los visitantes que ya conocen la marca de {client} "
            f"pero no convirtieron — estas audiencias convierten 2–3x más que el "
            f"tráfico frío al mismo CPC. "
            f"En {industry}, el costo por conversión de retargeting suele ser "
            f"40–60% menor que el de campañas de prospección."
        ),
        "email_automation": (
            f"Una tasa de apertura de {ctx['email_open_rate']:.1%} indica que la "
            f"mayoría de los suscriptores de {client} no está viendo los mensajes. "
            f"En {industry}, las secuencias automatizadas de bienvenida tienen tasas "
            f"de apertura de 45–60% porque llegan en el momento exacto en que el "
            f"contacto está más comprometido con la marca. "
            f"Implementar 3 flujos básicos puede recuperar ese engagement sin "
            f"requerir esfuerzo manual continuo del equipo."
        ),
        "reactivation": (
            f"Después de {ctx['days_inactive']} días sin actividad, la probabilidad "
            f"de cerrar una venta con {client} sigue siendo significativamente mayor "
            f"que con un prospecto frío — el cliente ya conoce nuestra agencia y "
            f"confió en nosotros antes. "
            f"En {industry}, las campañas de reactivación personalizadas con un incentivo "
            f"claro recuperan entre el 20 y el 35% de cuentas dormidas. "
            f"El costo de reactivar es 5–8x menor que el de adquirir un cliente nuevo."
        ),
        "conversion_rate_audit": (
            f"El contraste entre un CTR de {ctx['ctr']:.1%} y una conversión de "
            f"{ctx['conversion_rate']:.2%} es una señal clara de que el problema "
            f"no está en los anuncios — está en el funnel post-clic. "
            f"Para {client} en {industry}, esto significa que por cada 1,000 personas "
            f"que hacen clic, solo {ctx['conversion_rate']*10:.1f} convierten, "
            f"cuando el estándar del sector es 20–40. "
            f"Una auditoría CRO típicamente identifica 3–5 fricciones que, "
            f"al resolverse, duplican la tasa de conversión sin aumentar el gasto."
        ),
        "upsell_ad_budget": (
            f"Un ROAS de {ctx['roas']:.1f}x sobre una inversión de "
            f"${ctx['monthly_ad_spend']:,.0f}/mes significa que cada dólar invertido "
            f"está generando ${ctx['roas']:.2f} en ingresos para {client}. "
            f"Escalar este presupuesto en {industry} sobre campañas ya probadas "
            f"es el camino de menor riesgo hacia un crecimiento de ingresos inmediato. "
            f"Con un presupuesto de ${ctx['recommended_budget']:,.0f}/mes, "
            f"el modelo proyecta un incremento del "
            f"{ctx['projected_revenue_increase']:.0f}% en ingresos sin degradar el ROAS."
        ),
    }
    return insights.get(opp_type, rationale)


# ── Template renderer ─────────────────────────────────────────────────────────

def _render_template(opp_type: str, ctx: dict) -> tuple[str, str]:
    """
    Fill subject + body templates with context values.
    Returns (subject, body).
    """
    tmpl = PROPOSAL_TEMPLATES.get(opp_type)
    if tmpl is None:
        # Generic fallback for unknown types
        subject = f"Propuesta: {OPPORTUNITY_LABELS.get(opp_type, opp_type)} para {ctx['client_name']}"
        body = (
            f"Estimado/a {ctx['client_name']},\n\n"
            f"{ctx['insight_paragraph']}\n\n"
            f"Precio sugerido: ${ctx['suggested_price']:,.0f} USD\n\n"
            f"Saludos,\nEl equipo de Hidden Opportunities Agency"
        )
        return subject, body

    try:
        subject = tmpl["subject"].format(**ctx)
        body    = tmpl["body"].format(**ctx)
    except KeyError as e:
        # Missing placeholder — use safe fallback
        subject = f"Propuesta para {ctx['client_name']}"
        body    = tmpl["body"].replace("{" + str(e).strip("'") + "}", "N/A")
        try:
            body = body.format(**ctx)
        except Exception:
            pass

    return subject, body


# ── Persistence ───────────────────────────────────────────────────────────────

def _persist_proposal(
    opportunity_id: str,
    client_id: str,
    subject: str,
    body: str,
    suggested_price: float,
) -> str:
    """Insert proposal into the DB and return its ID."""
    proposal_id = str(uuid.uuid4())
    conn = get_connection()
    now  = datetime.now().isoformat()

    conn.execute(
        """
        INSERT INTO proposals
            (id, opportunity_id, client_id, subject, body, suggested_price,
             status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 'draft', ?, ?)
        """,
        (proposal_id, opportunity_id, client_id, subject, body, suggested_price, now, now),
    )

    # Update the parent opportunity status
    conn.execute(
        "UPDATE opportunities SET status='proposal_generated', updated_at=? WHERE id=?",
        (now, opportunity_id),
    )

    conn.commit()
    conn.close()
    return proposal_id


def _export_markdown(
    proposal_id: str,
    client_name: str,
    opp_type: str,
    subject: str,
    body: str,
    ctx: dict,
) -> Path:
    """Save the proposal as a Markdown file and return the path."""
    date_str  = datetime.now().strftime("%Y-%m-%d")
    safe_name = re.sub(r"[^\w\-]", "_", client_name)
    filename  = f"{safe_name}_{opp_type}_{date_str}_{proposal_id[:8]}.md"
    filepath  = PROPOSALS_DIR / filename

    content = dedent(f"""\
        # {subject}

        **Propuesta ID:** `{proposal_id}`
        **Cliente:** {client_name}
        **Tipo de oportunidad:** {OPPORTUNITY_LABELS.get(opp_type, opp_type)}
        **Precio sugerido:** ${ctx['suggested_price']:,.0f} USD
        **Generado:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
        **Estado:** Borrador — pendiente de aprobación

        ---

        {body}

        ---

        ## Datos que motivaron esta propuesta

        | Métrica | Valor |
        |---------|-------|
    """)

    metric_map = {
        "CTR":                f"{ctx.get('ctr', 0):.1%}",
        "Tasa de rebote":     f"{ctx.get('bounce_rate', 0):.0%}",
        "Tráfico orgánico":   f"{ctx.get('organic_traffic', 0):,}",
        "ROAS":               f"{ctx.get('roas', 0):.1f}x",
        "Gasto mensual":      f"${ctx.get('monthly_ad_spend', 0):,.0f}",
        "Apertura email":     f"{ctx.get('email_open_rate', 0):.1%}",
        "Conversión":         f"{ctx.get('conversion_rate', 0):.2%}",
        "Días inactivo":      str(ctx.get('days_inactive', 0)),
    }
    for k, v in metric_map.items():
        content += f"| {k} | {v} |\n"

    content += dedent(f"""
        ---

        ## Notas de producción

        > **En producción:** Este archivo se sube automáticamente a la carpeta de
        > Google Drive del cliente. El account manager recibe una notificación en
        > Slack con botones de Aprobar / Rechazar / Editar.
        > Al hacer clic en "Aprobar", el agente envía el email al contacto del cliente
        > ({ctx.get('contact_email', 'email@cliente.com')}) vía SendGrid API.
    """)

    filepath.write_text(content, encoding="utf-8")
    return filepath


# ── Public API ────────────────────────────────────────────────────────────────

def generate_proposal(opportunity_id: str, rationale: str = "") -> dict[str, Any]:
    """
    Generate a personalized proposal for a detected opportunity.

    Parameters
    ----------
    opportunity_id : str
        The opportunity.id from the DB.
    rationale : str
        The human-readable rationale from the rule that fired (used as LLM context).

    Returns
    -------
    dict with keys: proposal_id, client_name, subject, body, filepath, status
    """
    conn = get_connection()

    # ── Load opportunity ──────────────────────────────────────────────────────
    opp_row = conn.execute(
        "SELECT * FROM opportunities WHERE id = ?", (opportunity_id,)
    ).fetchone()

    if opp_row is None:
        conn.close()
        raise ValueError(f"Opportunity {opportunity_id!r} not found.")

    opp = dict(opp_row)

    # If a proposal already exists (non-rejected), return the existing one
    existing = conn.execute(
        """
        SELECT id, subject, body, status FROM proposals
        WHERE opportunity_id = ? AND status NOT IN ('rejected')
        ORDER BY created_at DESC LIMIT 1
        """,
        (opportunity_id,),
    ).fetchone()

    if existing:
        conn.close()
        return {
            "proposal_id":  existing["id"],
            "client_name":  "",
            "subject":      existing["subject"],
            "body":         existing["body"],
            "filepath":     None,
            "status":       existing["status"],
            "already_existed": True,
        }

    conn.close()

    opp_type  = opp["opportunity_type"]
    client_id = opp["client_id"]

    # ── Load client ───────────────────────────────────────────────────────────
    client = crm.get_client(client_id) or {"name": "Cliente", "industry": ""}

    # ── Load metrics ──────────────────────────────────────────────────────────
    metrics: dict = {}
    for fetcher, fields in [
        (ga.get_latest_metrics,                     ["bounce_rate", "pages_per_session", "conversion_rate", "organic_traffic"]),
        (meta_ads.get_latest_ad_metrics,            ["ctr", "cpc", "roas", "ad_spend"]),
        (email_marketing.get_latest_email_metrics,  ["email_open_rate", "email_click_rate"]),
        (seo.get_latest_seo_metrics,                ["organic_traffic", "keyword_rankings"]),
    ]:
        snapshot = fetcher(client_id)
        if snapshot:
            for f in fields:
                if f in snapshot:
                    metrics[f] = snapshot[f]

    activity = crm.get_client_activity(client_id)
    if activity:
        metrics["days_inactive"]           = activity.get("days_inactive", 0) or 0
        metrics["days_since_last_contact"] = activity.get("days_since_last_contact", 0) or 0

    # ── Build context ─────────────────────────────────────────────────────────
    ctx = _build_context(client, metrics, opp_type)

    # ── Generate insight paragraph ────────────────────────────────────────────
    llm_prompt = _build_llm_prompt(ctx, opp_type, rationale)
    insight    = _call_llm(llm_prompt)

    if insight:
        ctx["insight_paragraph"] = insight
        generation_method = "llm"
    else:
        ctx["insight_paragraph"] = _template_insight(ctx, opp_type, rationale)
        generation_method = "template"

    # ── Render template ───────────────────────────────────────────────────────
    subject, body = _render_template(opp_type, ctx)

    # ── Persist to DB ─────────────────────────────────────────────────────────
    proposal_id = _persist_proposal(
        opportunity_id,
        client_id,
        subject,
        body,
        ctx["suggested_price"],
    )

    # ── Export markdown ───────────────────────────────────────────────────────
    filepath = _export_markdown(proposal_id, client["name"], opp_type, subject, body, ctx)

    print(
        f"[proposal_generator] Generated proposal {proposal_id[:8]}… "
        f"for {client['name']} ({opp_type}) via {generation_method}. "
        f"File: {filepath.name}"
    )

    return {
        "proposal_id":      proposal_id,
        "client_name":      client["name"],
        "subject":          subject,
        "body":             body,
        "filepath":         str(filepath),
        "status":           "draft",
        "generation_method": generation_method,
        "already_existed":  False,
    }


def generate_proposals_for_all(min_score: float = 70.0) -> list[dict]:
    """
    Generate proposals for all opportunities with score >= min_score
    that do not yet have a non-rejected proposal.

    Returns a list of result dicts from generate_proposal().
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT o.id, o.opportunity_type, o.score
        FROM opportunities o
        LEFT JOIN proposals p
               ON p.opportunity_id = o.id AND p.status NOT IN ('rejected')
        WHERE o.score >= ?
          AND o.status IN ('detected', 'proposal_generated')
          AND p.id IS NULL
        ORDER BY o.score DESC
        """,
        (min_score,),
    ).fetchall()
    conn.close()

    results = []
    for row in rows:
        try:
            result = generate_proposal(row["id"])
            results.append(result)
        except Exception as e:
            print(f"[proposal_generator] ERROR for opportunity {row['id']}: {e}")

    return results


# ── Approval actions ──────────────────────────────────────────────────────────

def approve_proposal(proposal_id: str, approved_by: str = "account_manager") -> bool:
    """Mark a proposal as approved (pending send)."""
    conn = get_connection()
    now  = datetime.now().isoformat()
    conn.execute(
        "UPDATE proposals SET status='approved', approved_by=?, updated_at=? WHERE id=?",
        (approved_by, now, proposal_id),
    )
    conn.commit()
    conn.close()
    print(f"[proposal_generator] Proposal {proposal_id[:8]}… approved by {approved_by}.")
    return True


def reject_proposal(proposal_id: str, reason: str = "") -> bool:
    """Mark a proposal as rejected and reset the opportunity to 'detected'."""
    conn = get_connection()
    now  = datetime.now().isoformat()

    # Reset opportunity so it can generate a new proposal next run
    opp = conn.execute(
        "SELECT opportunity_id FROM proposals WHERE id=?", (proposal_id,)
    ).fetchone()

    conn.execute(
        "UPDATE proposals SET status='rejected', updated_at=? WHERE id=?",
        (now, proposal_id),
    )

    if opp:
        conn.execute(
            "UPDATE opportunities SET status='detected', updated_at=? WHERE id=?",
            (now, opp["opportunity_id"]),
        )

    conn.commit()
    conn.close()
    print(f"[proposal_generator] Proposal {proposal_id[:8]}… rejected. Reason: {reason or 'none'}")
    return True


def update_proposal_body(proposal_id: str, new_body: str) -> bool:
    """Replace the body text of a draft proposal (inline edit)."""
    conn = get_connection()
    now  = datetime.now().isoformat()
    conn.execute(
        "UPDATE proposals SET body=?, updated_at=? WHERE id=? AND status='draft'",
        (new_body, now, proposal_id),
    )
    conn.commit()
    conn.close()
    return True


def get_all_proposals() -> list[dict]:
    """Return all proposals with joined client and opportunity data."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            p.id,
            p.opportunity_id,
            p.client_id,
            p.subject,
            p.body,
            p.suggested_price,
            p.status,
            p.approved_by,
            p.sent_at,
            p.created_at,
            p.updated_at,
            c.name         AS client_name,
            c.industry,
            c.contact_email,
            c.account_manager,
            c.is_demo_scenario,
            o.opportunity_type,
            o.score
        FROM proposals p
        JOIN clients     c ON c.id = p.client_id
        JOIN opportunities o ON o.id = p.opportunity_id
        ORDER BY p.created_at DESC
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
