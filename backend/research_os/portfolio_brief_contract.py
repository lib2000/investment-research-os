"""Portfolio brief payload helpers for Market Signal Graph."""

from __future__ import annotations

from hashlib import sha256
from typing import Any


DESIGN_NAME = "portfolio_brief_contract_v1"
CHANNEL = "portfolio"
PORTFOLIO_IR_BRIEF_TYPE = "portfolio_ir"
PORTFOLIO_HEALTH_BRIEF_TYPE = "portfolio_health"


def sha256_hex(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _safe_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.replace("%", "").replace(",", "").strip()
        if not value:
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _ticker_from_item(item: dict[str, Any]) -> str:
    metadata = _dict_value(item.get("metadata"))
    return _safe_text(item.get("ticker") or metadata.get("ticker")).upper()


def _brief_id(brief_type: str, as_of: str, seed: str) -> str:
    return sha256_hex("|".join([brief_type, CHANNEL, as_of, seed]))


def build_portfolio_ir_brief_payload(
    analysis_payloads: list[dict[str, Any]],
    *,
    as_of: str,
    title: str = "Portfolio IR Brief",
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for payload in analysis_payloads:
        if not isinstance(payload, dict):
            continue
        ticker = _ticker_from_item(payload)
        if not ticker:
            continue
        items.append(
            {
                "ticker": ticker,
                "company": _safe_text(payload.get("company")),
                "stance": _safe_text(payload.get("stance")) or "neutral",
                "score": _safe_float(payload.get("score")),
                "confidence": _safe_float(payload.get("confidence")),
                "summary": _safe_text(payload.get("summary")),
                "analysis_type": _safe_text(payload.get("analysis_type")),
                "analysis_id": _safe_text(payload.get("analysis_id")),
            }
        )
    tickers = sorted({item["ticker"] for item in items})
    seed = ",".join(tickers) or title
    return {
        "brief_id": _brief_id(PORTFOLIO_IR_BRIEF_TYPE, as_of, seed),
        "brief_type": PORTFOLIO_IR_BRIEF_TYPE,
        "channel": CHANNEL,
        "title": title,
        "summary": f"{len(items)} IR analysis items across {len(tickers)} tickers.",
        "content": {
            "as_of": as_of,
            "items": items,
            "tickers": tickers,
        },
        "metadata": {
            "collector_design": DESIGN_NAME,
            "analysis_count": len(items),
            "ticker_count": len(tickers),
        },
        "generated_at": as_of,
    }


def build_portfolio_health_brief_payload(
    score_result: dict[str, Any],
    *,
    as_of: str,
    title: str = "Portfolio Health Score",
) -> dict[str, Any]:
    tickers = [item for item in _list_value(score_result.get("tickers")) if isinstance(item, dict)]
    holdings: list[dict[str, Any]] = []
    for item in tickers:
        holdings.append(
            {
                "ticker": _safe_text(item.get("ticker")).upper(),
                "company": _safe_text(item.get("company_name")),
                "stance": _safe_text(item.get("label")) or "neutral",
                "score": _safe_float(item.get("score")),
                "confidence": _safe_float(item.get("average_confidence")),
                "source_families": _list_value(item.get("source_families")),
                "signal_count": item.get("signal_count"),
            }
        )
    total_score = _safe_float(score_result.get("portfolio_score"))
    seed = ",".join(item["ticker"] for item in holdings) or title
    return {
        "brief_id": _brief_id(PORTFOLIO_HEALTH_BRIEF_TYPE, as_of, seed),
        "brief_type": PORTFOLIO_HEALTH_BRIEF_TYPE,
        "channel": CHANNEL,
        "title": title,
        "summary": f"Portfolio health score {total_score if total_score is not None else 'n/a'} across {len(holdings)} tickers.",
        "content": {
            "as_of": as_of,
            "health": {"total_score": total_score},
            "holdings": holdings,
            "strengthened": _list_value(score_result.get("strengthened")),
            "watch_items": _list_value(score_result.get("watch_items")),
        },
        "metadata": {
            "collector_design": DESIGN_NAME,
            "ticker_count": len(holdings),
            "signal_count": score_result.get("signal_count"),
            "source_family_counts": _dict_value(score_result.get("source_family_counts")),
        },
        "generated_at": as_of,
    }


def build_portfolio_brief_batch_result(
    *,
    analysis_payloads: list[dict[str, Any]],
    score_result: dict[str, Any],
    as_of: str,
) -> dict[str, Any]:
    briefs = [
        build_portfolio_ir_brief_payload(analysis_payloads, as_of=as_of),
        build_portfolio_health_brief_payload(score_result, as_of=as_of),
    ]
    return {
        "status": "success",
        "design": DESIGN_NAME,
        "brief_count": len(briefs),
        "brief_types": [brief["brief_type"] for brief in briefs],
        "briefs": briefs,
    }
