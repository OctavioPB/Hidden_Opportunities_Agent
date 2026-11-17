from fastapi import APIRouter
from pydantic import BaseModel
from src.nlp.pipeline import run_pipeline, get_pipeline_summary
from src.data_sources.text_signals import (
    get_client_signals, get_signal_summary,
    get_all_signal_summaries, get_urgency_alerts, count_signals_by_type,
)

router = APIRouter(tags=["text_signals"])


class ProcessRequest(BaseModel):
    reprocess_all: bool = False


@router.get("/text-signals/summary")
def text_summary() -> dict:
    pipeline = get_pipeline_summary()
    counts   = count_signals_by_type()
    return {**pipeline, "counts_by_type": counts}


@router.get("/text-signals/client/{client_id}")
def client_signals(client_id: str) -> dict:
    return {
        "signals": get_client_signals(client_id),
        "summary": get_signal_summary(client_id),
    }


@router.get("/text-signals/all-summaries")
def all_summaries() -> list[dict]:
    return get_all_signal_summaries()


@router.get("/text-signals/urgency")
def urgency_alerts() -> list[dict]:
    return get_urgency_alerts()


@router.post("/text-signals/process")
def process_signals(req: ProcessRequest) -> dict:
    result = run_pipeline(
        reprocess_all=req.reprocess_all,
        use_llm=False,
        verbose=False,
    )
    return result
