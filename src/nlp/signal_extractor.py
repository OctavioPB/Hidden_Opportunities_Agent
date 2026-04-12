"""
Sprint 6 — Text Signal Extractor.

Processes raw text (email, call transcript, CRM note) and extracts structured
signals that feed into the ML model and opportunity scoring pipeline.

Signals extracted
-----------------
  sentiment      : float -1.0 to 1.0 — overall emotional tone
  mentions_price : 1 if budget/cost concern detected
  asks_for_results: 1 if asking about ROI, benchmarks, case studies
  churn_risk     : 1 if leaving / competitor / cancel signals present
  urgency_signal : 1 if urgent language ("ASAP", "critical", "today")
  interest_signal: 1 if clear buying intent / positive interest

Two extraction modes (selected automatically)
---------------------------------------------
  1. Keyword-based (always available): deterministic, zero-latency, no API calls.
     Good for demo and as a fallback in production.
  2. LLM-based (optional, richer): structured JSON prompt to GPT or Claude.
     Falls back to keyword mode if no API key is configured.

In production
-------------
  The LLM mode runs on all new emails/calls nightly. Keyword mode is used as
  a real-time early-warning system during the day. Results are stored in the
  text_signals table and joined into the ML feature matrix at training time.
"""

from __future__ import annotations

import re
from typing import Any

import config

# ── Keyword lexicons ──────────────────────────────────────────────────────────

_PRICE_KWORDS = {
    "expensive", "cost", "budget", "cheaper", "price", "afford",
    "too much", "pricing", "invoice", "billing", "fee", "reduce costs",
    "cut the", "overspend", "not worth",
}

_RESULTS_KWORDS = {
    "results", "roi", "case study", "case studies", "benchmark", "benchmarks",
    "performance", "what did", "prove", "show me", "report", "metrics",
    "how are we doing", "what are the numbers", "q3 review", "q4 review",
}

_CHURN_KWORDS = {
    "cancel", "leaving", "competitor", "unhappy", "disappointed",
    "switching", "another agency", "reconsider", "worth continuing",
    "if things don't", "not engaged", "worth it", "evaluate other",
    "if we don't see", "pull the plug",
}

_URGENCY_KWORDS = {
    "urgent", "urgency", "asap", "immediately", "critical", "emergency",
    "right now", "today", "by end of day", "eod", "by tomorrow",
    "cannot wait", "time-sensitive",
}

_INTEREST_KWORDS = {
    "interested", "when can we", "let's do it", "proceed", "sounds good",
    "definitely", "absolutely", "impressed", "love what", "can we talk",
    "expand", "next steps", "schedule a call", "move forward", "great work",
    "more of", "add more", "more campaigns",
}

_POSITIVE_WORDS = {
    "great", "excellent", "impressed", "happy", "satisfied", "love",
    "amazing", "fantastic", "wonderful", "brilliant", "thrilled",
    "fantastic", "perfect", "awesome", "delighted",
}

_NEGATIVE_WORDS = {
    "bad", "poor", "worst", "terrible", "hate", "awful", "disappointed",
    "frustrated", "upset", "unhappy", "not happy", "not good", "failure",
    "failing", "wrong", "disaster",
}


# ── Keyword-based extractor ───────────────────────────────────────────────────

def _normalize(text: str) -> str:
    return text.lower()


def _match_any(text_lower: str, kwords: set[str]) -> bool:
    return any(kw in text_lower for kw in kwords)


def _sentiment_score(text: str) -> float:
    """
    Simple sentiment score in [-1, 1] based on positive/negative word counts.

    In production: replaced by a fine-tuned transformer model
    (e.g., cardiffnlp/twitter-roberta-base-sentiment) for higher accuracy.
    """
    words = re.findall(r"\b\w+\b", text.lower())
    total = max(len(words), 1)
    pos = sum(1 for w in words if w in _POSITIVE_WORDS)
    neg = sum(1 for w in words if w in _NEGATIVE_WORDS)
    raw = (pos - neg) / total * 10          # scale to [-10, 10]
    return round(max(-1.0, min(1.0, raw)), 4)


def extract_signals_keyword(text: str) -> dict[str, Any]:
    """
    Extract signals using keyword matching.
    Fast, deterministic, works offline.
    """
    t = _normalize(text)
    return {
        "sentiment":       _sentiment_score(text),
        "mentions_price":  int(_match_any(t, _PRICE_KWORDS)),
        "asks_for_results": int(_match_any(t, _RESULTS_KWORDS)),
        "churn_risk":      int(_match_any(t, _CHURN_KWORDS)),
        "urgency_signal":  int(_match_any(t, _URGENCY_KWORDS)),
        "interest_signal": int(_match_any(t, _INTEREST_KWORDS)),
    }


# ── LLM-based extractor (optional) ───────────────────────────────────────────

_LLM_SYSTEM_PROMPT = """\
You are a marketing agency signal analyst. Analyze the text and respond ONLY
with a valid JSON object (no markdown) with these exact keys:
  sentiment        (float, -1.0 negative to 1.0 positive)
  mentions_price   (0 or 1 — client mentioned cost, budget, or pricing concerns)
  asks_for_results (0 or 1 — client asked about ROI, metrics, or case studies)
  churn_risk       (0 or 1 — client mentioned leaving, competitors, or canceling)
  urgency_signal   (0 or 1 — urgent or time-sensitive language detected)
  interest_signal  (0 or 1 — clear buying intent or positive interest in upsells)
  summary          (str, one sentence describing the client's state of mind)
"""


def _call_llm(text: str) -> dict | None:
    """
    Call the configured LLM for richer signal extraction.
    Returns None if API is unavailable or call fails.
    """
    import json

    provider = config.LLM_PROVIDER
    prompt = f"Analyze this client communication:\n\n{text}"

    try:
        if provider == "anthropic" and config.ANTHROPIC_API_KEY:
            import anthropic
            client_obj = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
            msg = client_obj.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
                system=_LLM_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()

        elif provider == "openai" and config.OPENAI_API_KEY:
            import openai
            client_obj = openai.OpenAI(api_key=config.OPENAI_API_KEY)
            resp = client_obj.chat.completions.create(
                model=config.LLM_MODEL,
                max_tokens=300,
                messages=[
                    {"role": "system", "content": _LLM_SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
            )
            raw = resp.choices[0].message.content.strip()
        else:
            return None

        parsed = json.loads(raw)
        return {
            "sentiment":        float(parsed.get("sentiment", 0.0)),
            "mentions_price":   int(bool(parsed.get("mentions_price", 0))),
            "asks_for_results": int(bool(parsed.get("asks_for_results", 0))),
            "churn_risk":       int(bool(parsed.get("churn_risk", 0))),
            "urgency_signal":   int(bool(parsed.get("urgency_signal", 0))),
            "interest_signal":  int(bool(parsed.get("interest_signal", 0))),
            "llm_summary":      parsed.get("summary", ""),
        }

    except Exception:
        return None


# ── Main entry point ──────────────────────────────────────────────────────────

def extract_signals(
    text: str,
    source: str = "email",
    use_llm: bool = True,
) -> dict[str, Any]:
    """
    Extract structured signals from raw text.

    Parameters
    ----------
    text     : raw email / call transcript / CRM note
    source   : 'email' | 'call_transcript' | 'crm_note'
    use_llm  : try LLM extraction first; fall back to keyword mode

    Returns
    -------
    dict with keys: sentiment, mentions_price, asks_for_results,
                    churn_risk, urgency_signal, interest_signal,
                    extraction_mode ('llm' or 'keyword'),
                    llm_summary (optional)
    """
    if use_llm and not config.DEMO_MODE:
        result = _call_llm(text)
        if result:
            result["extraction_mode"] = "llm"
            return result

    # Keyword fallback (always used in DEMO_MODE)
    result = extract_signals_keyword(text)
    result["extraction_mode"] = "keyword"
    return result


# ── Signal aggregation ────────────────────────────────────────────────────────

def aggregate_signals(signal_rows: list[dict]) -> dict[str, Any]:
    """
    Aggregate multiple text_signals rows into a single client-level summary.

    Used to produce the feature vector values for the ML model:
      - sentiment_score    : mean sentiment across all rows
      - mentions_price     : 1 if ANY row has mentions_price=1
      - asks_for_results   : 1 if ANY row has asks_for_results=1
      - churn_risk         : 1 if ANY row has churn_risk=1
      - urgency_signal     : 1 if ANY row has urgency_signal=1
      - interest_signal    : 1 if ANY row has interest_signal=1
    """
    if not signal_rows:
        return {
            "sentiment_score":  0.0,
            "mentions_price":   0,
            "asks_for_results": 0,
            "churn_risk":       0,
            "urgency_signal":   0,
            "interest_signal":  0,
        }

    sentiments = [r.get("sentiment", 0) or 0 for r in signal_rows]

    return {
        "sentiment_score":  round(sum(sentiments) / len(sentiments), 4),
        "mentions_price":   int(any(r.get("mentions_price",   0) for r in signal_rows)),
        "asks_for_results": int(any(r.get("asks_for_results", 0) for r in signal_rows)),
        "churn_risk":       int(any(r.get("churn_risk",       0) for r in signal_rows)),
        "urgency_signal":   int(any(r.get("urgency_signal",   0) for r in signal_rows)),
        "interest_signal":  int(any(r.get("interest_signal",  0) for r in signal_rows)),
    }
