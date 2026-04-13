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
        "subject": "Proposal: Landing Page Optimization for {client_name}",
        "body": dedent("""\
            Dear {client_name},

            We have been monitoring your campaign performance and identified
            a concrete opportunity to improve results in the {industry} sector.

            **What we see in your data:**
            - Current CTR: **{ctr:.1%}** (excellent — your ads are working)
            - Bounce rate: **{bounce_rate:.0%}** (above the 55% ideal average)
            - Pages per session: **{pages_per_session:.1f}** (visitors are not exploring further)

            {insight_paragraph}

            **Our proposal:** Optimized landing page A/B test
            - Price: **${suggested_price:,.0f} USD**
            - Duration: 3 weeks (design + implementation + analysis)
            - Guarantee: if we do not improve your conversion rate by 20%, we refund
              50% of the fee.

            Do you have 15 minutes this week to review a mockup?

            Best regards,
            OPB Marketing

            ---
            *This proposal was generated automatically by the opportunities agent
            and reviewed by your account manager before being sent.*
        """),
    },

    "seo_content": {
        "subject": "Proposal: SEO Content Strategy for {client_name}",
        "body": dedent("""\
            Dear {client_name},

            Your website in the {industry} sector has a solid organic foundation
            that is not yet being fully leveraged.

            **What we see in your data:**
            - Monthly organic traffic: **{organic_traffic:,} visits**
            - Ranked keywords: **{keyword_rankings}** (significant room to grow)
            - Organic conversion rate: **{conversion_rate:.1%}**

            {insight_paragraph}

            **Our proposal:** SEO Content Package — 4 articles/month
            - Price: **${suggested_price:,.0f} USD / month**
            - Includes: keyword research, copywriting, on-page optimization
            - Expected result: +40% organic traffic within 90 days

            Would you like to see the editorial calendar we have prepared for you?

            Best regards,
            OPB Marketing
        """),
    },

    "retargeting_campaign": {
        "subject": "Proposal: Retargeting Campaign for {client_name}",
        "body": dedent("""\
            Dear {client_name},

            Your advertising campaigns in {industry} are generating traffic,
            but there is a significant opportunity to re-engage visitors
            who did not convert on their first visit.

            **What we see in your data:**
            - Estimated monthly ad spend: **${monthly_ad_spend:,.0f} USD**
            - Current ROAS: **{roas:.1f}x** (target: ≥ 3.5x)
            - Opportunity: warm audiences with no active retargeting

            {insight_paragraph}

            **Our proposal:** Multi-Channel Retargeting Campaign
            - Price: **${suggested_price:,.0f} USD** (setup + first-month management)
            - Channels: Meta Ads + Google Display
            - Expected result: 30–50% reduction in cost per acquisition

            Can we schedule a 20-minute call to review the strategy?

            Best regards,
            OPB Marketing
        """),
    },

    "email_automation": {
        "subject": "Proposal: Email Marketing Automation for {client_name}",
        "body": dedent("""\
            Dear {client_name},

            Your subscriber base in {industry} is a valuable asset that is
            currently not generating its full revenue potential.

            **What we see in your data:**
            - Current open rate: **{email_open_rate:.1%}** (industry average: 21%)
            - Opportunity: automated flows can 2–3x current metrics

            {insight_paragraph}

            **Our proposal:** Email Automation Setup — 3 flows
            - Price: **${suggested_price:,.0f} USD** (one-time implementation)
            - Flows: Welcome → Nurture → Reactivation
            - Platform: your current ESP (Mailchimp / ActiveCampaign / Klaviyo)
            - Expected result: open rate ≥ 30% within 60 days

            Shall we send you examples of the flows we would implement?

            Best regards,
            OPB Marketing
        """),
    },

    "reactivation": {
        "subject": "We have something for you, {client_name}",
        "body": dedent("""\
            Dear {client_name},

            It has been {days_inactive} days since we last worked together actively,
            and we would like to reconnect with a tailored proposal for your
            business in {industry}.

            {insight_paragraph}

            **Express Reactivation Offer — valid for 7 days:**
            - Full digital presence audit: **FREE**
            - Personalized action plan: included
            - First month of service with **20% discount** (saving
              ${savings:,.0f} USD off the standard price)
            - Discounted price: **${discounted_price:,.0f} USD**

            This is our way of saying we value the relationship we have built
            and want to keep delivering results for you.

            Do you have 15 minutes this week to catch up?

            Warm regards,
            OPB Marketing

            ---
            *Offer valid until {offer_expiry}.*
        """),
    },

    "conversion_rate_audit": {
        "subject": "Proposal: Conversion Rate Audit for {client_name}",
        "body": dedent("""\
            Dear {client_name},

            We detected a significant gap in your funnel in the {industry} sector
            that is costing you sales every day.

            **What we see in your data:**
            - Ad CTR: **{ctr:.1%}** (excellent — people are clicking)
            - Conversion rate: **{conversion_rate:.2%}** (well below benchmark)
            - Improvement opportunity: for every 1,000 visitors you could gain
              {potential_conversions:.0f} additional conversions

            {insight_paragraph}

            **Our proposal:** CRO Audit + Action Plan
            - Price: **${suggested_price:,.0f} USD**
            - Deliverable: report with 5–10 prioritized recommendations
            - Timeline: 1 week of analysis + executive presentation
            - Guarantee: we identify at least 3 implementable quick wins

            Shall we schedule a diagnostic session this week?

            Best regards,
            OPB Marketing
        """),
    },

    "upsell_ad_budget": {
        "subject": "Proposal: Scale Your Ad Investment — {client_name}",
        "body": dedent("""\
            Dear {client_name},

            We have great news: your campaigns in {industry} are outperforming
            expectations, and there is a concrete opportunity to scale results further.

            **What we see in your data:**
            - Current ROAS: **{roas:.1f}x** (above the 4x benchmark)
            - Monthly spend: **${monthly_ad_spend:,.0f} USD**
            - Projected ROI at scale: every additional $1 generates ${roas:.2f} in revenue

            {insight_paragraph}

            **Our proposal:** Ad Scale Plan — 60 days
            - Management fee: **${suggested_price:,.0f} USD / month**
            - Recommended budget: ${recommended_budget:,.0f} USD/month
            - Strategy: scale top-performing ad sets + expand to lookalike audiences
            - Expected result: +{projected_revenue_increase:.0f}% revenue
              without degrading ROAS

            Would you like to review the campaigns we plan to scale together?

            Best regards,
            OPB Marketing
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
        "client_name":       client.get("name", "Client"),
        "industry":          client.get("industry", "your sector"),
        "account_manager":   client.get("account_manager", "Your account manager"),
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
        You are a digital marketing expert writing a personalized commercial proposal
        for an agency client.

        CLIENT DATA:
        - Name: {ctx['client_name']}
        - Industry: {ctx['industry']}
        - Detected opportunity: {label}
        - Agent analysis: {rationale}

        KEY METRICS:
        {json.dumps({k: v for k, v in ctx.items()
                     if k not in ('client_name', 'industry', 'insight_paragraph',
                                  'contact_email', 'account_manager', 'offer_expiry')
                     and isinstance(v, (int, float))}, indent=2, ensure_ascii=False)}

        TASK:
        Write ONE paragraph (3–4 sentences) that:
        1. References a specific insight using the client's actual numbers (not generic).
        2. Connects the detected problem to the business impact in the {ctx['industry']} sector.
        3. Uses a professional yet approachable tone, in English.
        4. Does NOT repeat information already mentioned in the email — this is an additional analysis paragraph.

        Reply with ONLY the paragraph — no title, no quotes, no extra formatting.
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
            f"To be specific: with a CTR of {ctx['ctr']:.1%}, "
            f"{client} is paying to bring visitors to the page, "
            f"yet {ctx['bounce_rate']:.0%} of them leave within seconds. "
            f"In the {industry} sector, this translates to potential revenue left on the table "
            f"every day the funnel remains unoptimized. "
            f"A conversion-focused landing page with a single clear CTA "
            f"typically cuts bounce rate by 15–25 percentage points."
        ),
        "seo_content": (
            f"With {ctx['organic_traffic']:,} monthly organic visits and only "
            f"{ctx['keyword_rankings']} ranked keywords, {client} is capturing "
            f"a fraction of the available traffic in {industry}. "
            f"Competitors with structured content strategies typically rank for "
            f"80–150 keywords in the same niche. "
            f"A blog publishing 4 optimized articles per month can triple organic reach "
            f"within 6 months without increasing ad spend."
        ),
        "retargeting_campaign": (
            f"With a monthly spend of ~${ctx['monthly_ad_spend']:,.0f} and a ROAS "
            f"of {ctx['roas']:.1f}x, there is real room to improve efficiency. "
            f"Retargeting reaches visitors who already know {client}'s brand "
            f"but did not convert — these audiences convert 2–3x more than cold traffic "
            f"at the same CPC. "
            f"In {industry}, retargeting cost per conversion is typically "
            f"40–60% lower than prospecting campaigns."
        ),
        "email_automation": (
            f"An open rate of {ctx['email_open_rate']:.1%} indicates that the majority "
            f"of {client}'s subscribers are not seeing the messages. "
            f"In {industry}, automated welcome sequences achieve open rates of 45–60% "
            f"because they arrive at the exact moment the contact is most engaged with the brand. "
            f"Setting up 3 basic flows can recover that engagement "
            f"without requiring continuous manual effort from the team."
        ),
        "reactivation": (
            f"After {ctx['days_inactive']} days of inactivity, the probability "
            f"of closing a sale with {client} is still significantly higher "
            f"than with a cold prospect — they already know the agency and trusted us before. "
            f"In {industry}, personalized reactivation campaigns with a clear incentive "
            f"recover 20–35% of dormant accounts. "
            f"The cost of reactivation is 5–8x lower than acquiring a new client."
        ),
        "conversion_rate_audit": (
            f"The contrast between a CTR of {ctx['ctr']:.1%} and a conversion rate of "
            f"{ctx['conversion_rate']:.2%} is a clear signal that the problem "
            f"is not in the ads — it is in the post-click funnel. "
            f"For {client} in {industry}, this means that for every 1,000 people "
            f"who click, only {ctx['conversion_rate']*10:.1f} convert, "
            f"while the sector benchmark is 20–40. "
            f"A CRO audit typically identifies 3–5 friction points that, "
            f"once resolved, double the conversion rate without increasing spend."
        ),
        "upsell_ad_budget": (
            f"A ROAS of {ctx['roas']:.1f}x on a spend of "
            f"${ctx['monthly_ad_spend']:,.0f}/month means every dollar invested "
            f"is generating ${ctx['roas']:.2f} in revenue for {client}. "
            f"Scaling this budget in {industry} on already-proven campaigns "
            f"is the lowest-risk path to immediate revenue growth. "
            f"At a budget of ${ctx['recommended_budget']:,.0f}/month, "
            f"the model projects a {ctx['projected_revenue_increase']:.0f}% increase "
            f"in revenue without degrading ROAS."
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
        subject = f"Proposal: {OPPORTUNITY_LABELS.get(opp_type, opp_type)} for {ctx['client_name']}"
        body = (
            f"Dear {ctx['client_name']},\n\n"
            f"{ctx['insight_paragraph']}\n\n"
            f"Suggested price: ${ctx['suggested_price']:,.0f} USD\n\n"
            f"Best regards,\nOPB Marketing"
        )
        return subject, body

    try:
        subject = tmpl["subject"].format(**ctx)
        body    = tmpl["body"].format(**ctx)
    except KeyError as e:
        # Missing placeholder — use safe fallback
        subject = f"Proposal for {ctx['client_name']}"
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

        **Proposal ID:** `{proposal_id}`
        **Client:** {client_name}
        **Opportunity type:** {OPPORTUNITY_LABELS.get(opp_type, opp_type)}
        **Suggested price:** ${ctx['suggested_price']:,.0f} USD
        **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
        **Status:** Draft — pending approval

        ---

        {body}

        ---

        ## Data that triggered this proposal

        | Metric | Value |
        |--------|-------|
    """)

    metric_map = {
        "CTR":              f"{ctx.get('ctr', 0):.1%}",
        "Bounce rate":      f"{ctx.get('bounce_rate', 0):.0%}",
        "Organic traffic":  f"{ctx.get('organic_traffic', 0):,}",
        "ROAS":             f"{ctx.get('roas', 0):.1f}x",
        "Monthly spend":    f"${ctx.get('monthly_ad_spend', 0):,.0f}",
        "Email open rate":  f"{ctx.get('email_open_rate', 0):.1%}",
        "Conversion rate":  f"{ctx.get('conversion_rate', 0):.2%}",
        "Days inactive":    str(ctx.get('days_inactive', 0)),
    }
    for k, v in metric_map.items():
        content += f"| {k} | {v} |\n"

    content += dedent(f"""
        ---

        ## Production notes

        > **In production:** This file is automatically uploaded to the client's
        > Google Drive folder. The account manager receives a Slack notification
        > with Approve / Reject / Edit buttons.
        > Clicking "Approve" triggers the agent to send the email to the client contact
        > ({ctx.get('contact_email', 'client@example.com')}) via the SendGrid API.
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
    client = crm.get_client(client_id) or {"name": "Client", "industry": ""}

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
