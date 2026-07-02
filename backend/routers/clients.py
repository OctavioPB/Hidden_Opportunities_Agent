from fastapi import APIRouter, HTTPException
from src.data_sources.crm import get_all_clients, get_demo_clients, get_client, get_client_activity, get_feedback_history
from src.data_sources import google_analytics as ga
from src.data_sources import meta_ads
from src.data_sources import email_marketing
from src.data_sources import seo
from src.data_sources.text_signals import get_client_signals, get_signal_summary
from src.db.schema import get_connection

router = APIRouter(tags=["clients"])


@router.get("/clients")
def all_clients() -> list[dict]:
    return get_all_clients()


@router.get("/clients/demo")
def demo_clients() -> list[dict]:
    return get_demo_clients()


@router.get("/clients/{client_id}/detail")
def client_detail(client_id: str) -> dict:
    client = get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Strip internal annotation key before returning
    client.pop("_production_integration", None)

    # Merge all latest metric snapshots
    metrics: dict = {}
    for src in [
        ga.get_latest_metrics(client_id) or {},
        meta_ads.get_latest_ad_metrics(client_id) or {},
        email_marketing.get_latest_email_metrics(client_id) or {},
        seo.get_latest_seo_metrics(client_id) or {},
        get_client_activity(client_id) or {},
    ]:
        src.pop("_production_integration", None)
        src.pop("date", None)
        metrics.update(src)

    # Opportunities for this client (filter cached scoring run)
    from src.agents.scorer import score_all_clients
    opportunities = [o for o in score_all_clients() if o["client_id"] == client_id]

    # Text signals
    signals_summary = get_signal_summary(client_id)
    raw_signals = [
        {k: v for k, v in dict(s).items() if k != "_production_integration"}
        for s in get_client_signals(client_id)
    ]

    # Proposals with opportunity type via join
    conn = get_connection()
    proposal_rows = conn.execute(
        """
        SELECT p.id, o.opportunity_type, p.subject, p.status,
               p.suggested_price, p.sent_at, p.payment_link
        FROM proposals p
        JOIN opportunities o ON o.id = p.opportunity_id
        WHERE p.client_id = ?
        ORDER BY p.sent_at DESC
        LIMIT 10
        """,
        (client_id,),
    ).fetchall()
    conn.close()
    proposals = [dict(r) for r in proposal_rows]

    # Feedback history
    feedback = [
        {k: v for k, v in dict(f).items() if k != "_production_integration"}
        for f in get_feedback_history(client_id)
    ]

    return {
        "client":          client,
        "metrics":         metrics,
        "opportunities":   opportunities,
        "signals_summary": signals_summary,
        "signals":         raw_signals,
        "proposals":       proposals,
        "feedback":        feedback,
    }
