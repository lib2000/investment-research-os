"""Offline contract for the Market Signal Graph portfolio pipeline."""

from __future__ import annotations

from typing import Any

from research_os.deepseek_ir_analysis import (
    DESIGN_NAME as DEEPSEEK_IR_ANALYSIS_DESIGN,
    build_deepseek_ir_analysis_batch_result,
)
from research_os.earnings_transcript_collector import (
    DESIGN_NAME as EARNINGS_TRANSCRIPT_DESIGN,
    build_earnings_transcript_batch_result,
)
from research_os.firecrawl_earnings_collector import (
    DESIGN_NAME as FIRECRAWL_EARNINGS_DESIGN,
    build_firecrawl_earnings_batch_result,
)
from research_os.firecrawl_ir_collector import (
    DESIGN_NAME as FIRECRAWL_IR_DESIGN,
    build_firecrawl_ir_signal_payload,
)
from research_os.portfolio_change_detection import (
    DESIGN_NAME as PORTFOLIO_CHANGE_DESIGN,
    detect_portfolio_changes,
)
from research_os.portfolio_signal_score import (
    DESIGN_NAME as PORTFOLIO_SIGNAL_SCORE_DESIGN,
    build_portfolio_signal_scores,
)
from research_os.telegram_brief_sender import (
    DESIGN_NAME as TELEGRAM_BRIEF_DESIGN,
    build_telegram_brief_payload,
)


DESIGN_NAME = "market_signal_graph_pipeline_contract_v1"


def sample_firecrawl_ir_inputs() -> list[dict[str, Any]]:
    return [
        {
            "company": "Planet Labs",
            "ticker": "PL",
            "raw_url": "https://investors.planet.com/",
            "page_title": "Planet Labs Investor Relations",
            "markdown": "Investor relations page with earnings releases, SEC filings, presentations, and governance materials.",
        },
        {
            "company": "Joby Aviation",
            "ticker": "JOBY",
            "raw_url": "https://ir.jobyaviation.com/",
            "page_title": "Joby Aviation Investor Relations",
            "markdown": "Investor relations page with shareholder updates, financial results, and regulatory filings.",
        },
    ]


def sample_earnings_transcript_inputs() -> list[dict[str, Any]]:
    return [
        {
            "company": "Planet Labs",
            "ticker": "PL",
            "raw_url": "https://investors.planet.com/events-and-presentations/",
            "title": "Planet Labs Q1 FY2027 earnings call transcript",
            "fiscal_period": "Q1 FY2027",
            "event_date": "2026-06-04",
            "transcript_text": "Revenue growth, retention, and margin discipline were discussed.",
            "speaker_count": 4,
        },
        {
            "company": "Joby Aviation",
            "ticker": "JOBY",
            "raw_url": "https://ir.jobyaviation.com/news-events/events-presentations/",
            "title": "Joby Aviation Q1 2026 earnings call transcript",
            "fiscal_period": "Q1 2026",
            "event_date": "2026-05-07",
            "transcript_text": "Certification progress and commercialization milestones were discussed alongside operating costs.",
            "speaker_count": 5,
        },
    ]


def sample_firecrawl_earnings_inputs() -> list[dict[str, Any]]:
    return [
        {
            "company": "Planet Labs",
            "ticker": "PL",
            "raw_url": "https://investors.planet.com/events-and-presentations/",
            "title": "Planet Labs Q1 FY2027 earnings release",
            "fiscal_period": "Q1 FY2027",
            "event_date": "2026-06-04",
            "markdown": "Revenue growth, customer retention, and margin discipline were reported.",
        },
        {
            "company": "Joby Aviation",
            "ticker": "JOBY",
            "raw_url": "https://ir.jobyaviation.com/news-events/events-presentations/",
            "title": "Joby Aviation Q1 2026 shareholder letter",
            "fiscal_period": "Q1 2026",
            "event_date": "2026-05-07",
            "markdown": "Certification progress, manufacturing readiness, and operating runway were highlighted.",
        },
    ]


def sample_sec_dart_signals() -> list[dict[str, Any]]:
    return [
        {
            "ticker": "PL",
            "company": "Planet Labs",
            "source_platform": "sec_edgar",
            "source_kind": "8-k",
            "stance": "neutral",
            "confidence": 0.56,
            "score": 5.6,
            "title": "Planet Labs SEC 8-K update",
        },
        {
            "ticker": "005930",
            "company": "Samsung Electronics",
            "source_platform": "opendart",
            "source_kind": "dart_quarterly",
            "stance": "positive",
            "confidence": 0.74,
            "score": 6.8,
            "title": "Samsung Electronics DART quarterly filing",
        },
    ]


def _signal_from_payload(
    payload: dict[str, Any],
    *,
    stance: str,
    confidence: float,
    score: float,
) -> dict[str, Any]:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    return {
        "ticker": metadata.get("ticker"),
        "company": metadata.get("company"),
        "source_platform": payload.get("source_platform"),
        "source_kind": payload.get("source_kind"),
        "stance": stance,
        "confidence": confidence,
        "score": score,
        "title": payload.get("title"),
        "metadata": metadata,
    }


def _analysis_item_from_signal(signal_payload: dict[str, Any]) -> dict[str, Any]:
    metadata = signal_payload.get("metadata") if isinstance(signal_payload.get("metadata"), dict) else {}
    ticker = metadata.get("ticker")
    return {
        "signal": signal_payload,
        "analysis": {
            "ticker": ticker,
            "company": metadata.get("company"),
            "stance": "positive",
            "confidence": 0.78,
            "score": 7.2,
            "summary": f"DeepSeek dry-run analysis for {ticker or 'signal'} based on captured IR material.",
            "key_points": ["source captured", "analysis payload shape verified"],
            "risks": ["requires live LLM review before production use"],
        },
    }


def _score_label_to_stance(label: Any) -> str:
    if label == "strengthened":
        return "positive"
    if label == "watch":
        return "risk"
    return "neutral"


def build_portfolio_health_brief_from_scores(score_result: dict[str, Any], *, as_of: str) -> dict[str, Any]:
    holdings: list[dict[str, Any]] = []
    for item in score_result.get("tickers") or []:
        if not isinstance(item, dict):
            continue
        holdings.append(
            {
                "ticker": item.get("ticker"),
                "company": item.get("company_name"),
                "stance": _score_label_to_stance(item.get("label")),
                "confidence": item.get("average_confidence"),
                "score": item.get("score"),
                "summary": f"{item.get('source_family_count', 0)} source families, {item.get('signal_count', 0)} signals",
            }
        )
    return {
        "brief_type": "portfolio_health",
        "channel": "portfolio",
        "created_at": as_of,
        "content": {
            "health": {"total_score": score_result.get("portfolio_score")},
            "holdings": holdings,
        },
    }


def sample_previous_portfolio_health_brief() -> dict[str, Any]:
    return {
        "brief_type": "portfolio_health",
        "channel": "portfolio",
        "created_at": "2026-06-18T08:00:00+09:00",
        "content": {
            "health": {"total_score": 5.85},
            "holdings": [
                {"ticker": "PL", "company": "Planet Labs", "stance": "neutral", "confidence": 0.6, "score": 5.9},
                {"ticker": "JOBY", "company": "Joby Aviation", "stance": "positive", "confidence": 0.68, "score": 6.6},
                {"ticker": "005930", "company": "Samsung Electronics", "stance": "neutral", "confidence": 0.62, "score": 5.8},
            ],
        },
    }


def build_market_signal_graph_pipeline_contract(
    *,
    ir_inputs: list[dict[str, Any]] | None = None,
    firecrawl_earnings_inputs: list[dict[str, Any]] | None = None,
    earnings_inputs: list[dict[str, Any]] | None = None,
    sec_dart_signals: list[dict[str, Any]] | None = None,
    previous_health_brief: dict[str, Any] | None = None,
    current_as_of: str = "2026-06-19T08:00:00+09:00",
    telegram_chat_id: str | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    effective_ir_inputs = ir_inputs if ir_inputs is not None else sample_firecrawl_ir_inputs()
    ir_payloads: list[dict[str, Any]] = []
    for item in effective_ir_inputs:
        try:
            ir_payloads.append(build_firecrawl_ir_signal_payload(item))
        except Exception as exc:
            errors.append(f"firecrawl_ir: {exc}")

    firecrawl_earnings_batch = build_firecrawl_earnings_batch_result(
        firecrawl_earnings_inputs if firecrawl_earnings_inputs is not None else sample_firecrawl_earnings_inputs()
    )
    if firecrawl_earnings_batch.get("status") != "success":
        errors.append("firecrawl_earnings: batch validation failed")
    firecrawl_earnings_payloads = [
        item.get("payload")
        for item in firecrawl_earnings_batch.get("results", [])
        if isinstance(item, dict) and isinstance(item.get("payload"), dict)
    ]

    earnings_batch = build_earnings_transcript_batch_result(
        earnings_inputs if earnings_inputs is not None else sample_earnings_transcript_inputs()
    )
    if earnings_batch.get("status") != "success":
        errors.append("earnings_transcript: batch validation failed")
    earnings_payloads = [
        item.get("payload")
        for item in earnings_batch.get("results", [])
        if isinstance(item, dict) and isinstance(item.get("payload"), dict)
    ]
    deepseek_batch = build_deepseek_ir_analysis_batch_result([_analysis_item_from_signal(payload) for payload in ir_payloads])
    if deepseek_batch.get("status") != "success":
        errors.append("deepseek_ir_analysis: batch validation failed")
    deepseek_payloads = [
        item.get("payload")
        for item in deepseek_batch.get("results", [])
        if isinstance(item, dict) and isinstance(item.get("payload"), dict)
    ]

    signal_inputs: list[dict[str, Any]] = []
    signal_inputs.extend(_signal_from_payload(payload, stance="positive", confidence=0.82, score=7.4) for payload in ir_payloads)
    signal_inputs.extend(
        _signal_from_payload(payload, stance="positive", confidence=0.76, score=7.0) for payload in firecrawl_earnings_payloads
    )
    signal_inputs.extend(
        _signal_from_payload(payload, stance="positive", confidence=0.72, score=7.1) for payload in earnings_payloads
    )
    signal_inputs.extend(deepseek_payloads)
    signal_inputs.extend(sec_dart_signals if sec_dart_signals is not None else sample_sec_dart_signals())

    score_result = build_portfolio_signal_scores(signal_inputs)
    if score_result.get("status") != "success":
        errors.append("portfolio_signal_score: scoring failed")

    current_health_brief = build_portfolio_health_brief_from_scores(score_result, as_of=current_as_of)
    change_result = detect_portfolio_changes(previous_health_brief or sample_previous_portfolio_health_brief(), current_health_brief)
    if change_result.get("status") != "success":
        errors.append("portfolio_change_detection: change detection failed")

    telegram_payload = build_telegram_brief_payload(change_result, chat_id=telegram_chat_id)
    if telegram_payload.get("status") != "success":
        errors.append("telegram_brief_sender: payload rendering failed")

    return {
        "design": DESIGN_NAME,
        "status": "failed" if errors else "success",
        "contracts": [
            FIRECRAWL_IR_DESIGN,
            FIRECRAWL_EARNINGS_DESIGN,
            EARNINGS_TRANSCRIPT_DESIGN,
            DEEPSEEK_IR_ANALYSIS_DESIGN,
            PORTFOLIO_SIGNAL_SCORE_DESIGN,
            PORTFOLIO_CHANGE_DESIGN,
            TELEGRAM_BRIEF_DESIGN,
        ],
        "errors": errors,
        "source_payload_counts": {
            "firecrawl_ir": len(ir_payloads),
            "firecrawl_earnings": len(firecrawl_earnings_payloads),
            "earnings_transcript": len(earnings_payloads),
            "deepseek_ir_analysis": len(deepseek_payloads),
        },
        "deepseek_analysis": deepseek_batch,
        "score": score_result,
        "current_health_brief": current_health_brief,
        "change_detection": change_result,
        "telegram": telegram_payload,
        "summary": {
            "signal_count": score_result.get("signal_count"),
            "ticker_count": score_result.get("ticker_count"),
            "portfolio_score": score_result.get("portfolio_score"),
            "top_mover_count": len(change_result.get("top_movers") or []),
            "watch_item_count": len(change_result.get("watch_items") or []),
            "telegram_message_count": telegram_payload.get("message_count"),
        },
    }
