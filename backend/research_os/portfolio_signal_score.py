"""Integrated portfolio signal scoring across IR, earnings, SEC, and DART."""

from __future__ import annotations

from typing import Any


DESIGN_NAME = "portfolio_signal_score_v1"

SOURCE_FAMILY_WEIGHTS = {
    "ir": 1.0,
    "earnings": 1.15,
    "sec": 1.1,
    "dart": 1.1,
    "other": 0.7,
}


def _safe_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _safe_ticker(value: Any) -> str:
    return _safe_text(value).upper()


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


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def source_family(item: dict[str, Any]) -> str:
    metadata = _dict_value(item.get("metadata"))
    text = " ".join(
        [
            _safe_text(item.get("source_family")),
            _safe_text(item.get("source_platform")),
            _safe_text(item.get("source_kind")),
            _safe_text(item.get("analysis_type")),
            _safe_text(metadata.get("target_type")),
            _safe_text(metadata.get("page_type")),
            " ".join(_safe_text(tag) for tag in _list_value(item.get("tags"))),
        ]
    ).lower()
    if "dart" in text or "opendart" in text:
        return "dart"
    if "sec" in text or "10-k" in text or "10-q" in text or "8-k" in text:
        return "sec"
    if "earnings" in text or "transcript" in text:
        return "earnings"
    if "ir" in text or "investor_relations" in text:
        return "ir"
    return "other"


def _stance_rank(value: Any) -> float:
    text = _safe_text(value).lower()
    if not text:
        return 0.0
    positive_terms = ("bullish", "positive", "strengthen", "upgrade", "beat", "강화", "긍정", "상향", "호조")
    negative_terms = ("bearish", "negative", "weaken", "downgrade", "miss", "risk", "약화", "부정", "하향", "위험")
    neutral_terms = ("neutral", "hold", "watch", "inline", "중립", "관망")
    if any(term in text for term in positive_terms):
        return 1.0
    if any(term in text for term in negative_terms):
        return -1.0
    if any(term in text for term in neutral_terms):
        return 0.0
    return 0.0


def _normalized_score(value: Any) -> float | None:
    score = _safe_float(value)
    if score is None:
        return None
    if -1.0 <= score <= 1.0:
        return max(-1.0, min(1.0, score))
    if 0.0 <= score <= 10.0:
        return max(-1.0, min(1.0, (score - 5.0) / 5.0))
    if 0.0 <= score <= 100.0:
        return max(-1.0, min(1.0, (score - 50.0) / 50.0))
    return max(-1.0, min(1.0, score / 100.0))


def normalize_signal_item(item: dict[str, Any]) -> dict[str, Any] | None:
    metadata = _dict_value(item.get("metadata"))
    ticker = _safe_ticker(_first_non_empty(item.get("ticker"), item.get("symbol"), metadata.get("ticker")))
    if not ticker:
        return None
    family = source_family(item)
    stance = _safe_text(_first_non_empty(item.get("stance"), item.get("rating"), item.get("signal"), item.get("status")))
    stance_score = _stance_rank(stance)
    numeric_score = _normalized_score(
        _first_non_empty(item.get("score"), item.get("signal_score"), item.get("impact_score"), item.get("health_score"))
    )
    if numeric_score is None:
        signal_score = stance_score
    elif stance:
        signal_score = 0.65 * stance_score + 0.35 * numeric_score
    else:
        signal_score = numeric_score
    confidence = _safe_float(_first_non_empty(item.get("confidence"), item.get("confidence_score"), item.get("weight")))
    if confidence is None:
        confidence = 0.65
    confidence = max(0.0, min(1.0, confidence))
    weight = SOURCE_FAMILY_WEIGHTS.get(family, SOURCE_FAMILY_WEIGHTS["other"]) * confidence
    return {
        "ticker": ticker,
        "company_name": _safe_text(_first_non_empty(item.get("company_name"), item.get("company"), metadata.get("company"))),
        "source_family": family,
        "source_platform": _safe_text(item.get("source_platform")),
        "source_kind": _safe_text(item.get("source_kind")),
        "stance": stance,
        "confidence": round(confidence, 4),
        "signal_score": round(signal_score, 4),
        "weight": round(weight, 4),
        "title": _safe_text(item.get("title")),
    }


def _score_label(value: float) -> str:
    if value >= 7.0:
        return "strengthened"
    if value <= 3.5:
        return "watch"
    return "neutral"


def build_portfolio_signal_scores(items: list[dict[str, Any]]) -> dict[str, Any]:
    normalized = [item for item in (normalize_signal_item(item) for item in items) if item]
    by_ticker: dict[str, list[dict[str, Any]]] = {}
    for item in normalized:
        by_ticker.setdefault(item["ticker"], []).append(item)
    ticker_scores: list[dict[str, Any]] = []
    for ticker, signals in sorted(by_ticker.items()):
        weight_sum = sum(float(item["weight"]) for item in signals)
        weighted_score = sum(float(item["signal_score"]) * float(item["weight"]) for item in signals)
        aggregate = weighted_score / weight_sum if weight_sum else 0.0
        score = round(5.0 + 5.0 * aggregate, 2)
        families = sorted({item["source_family"] for item in signals})
        company_name = next((item["company_name"] for item in signals if item["company_name"]), "")
        ticker_scores.append(
            {
                "ticker": ticker,
                "company_name": company_name,
                "score": score,
                "label": _score_label(score),
                "signal_count": len(signals),
                "source_families": families,
                "source_family_count": len(families),
                "average_confidence": round(sum(float(item["confidence"]) for item in signals) / len(signals), 4),
                "signals": signals,
            }
        )
    ticker_scores.sort(key=lambda item: (item["score"], item["source_family_count"], item["signal_count"]), reverse=True)
    family_counts: dict[str, int] = {}
    for item in normalized:
        family = item["source_family"]
        family_counts[family] = family_counts.get(family, 0) + 1
    portfolio_score = round(sum(item["score"] for item in ticker_scores) / len(ticker_scores), 2) if ticker_scores else None
    return {
        "design": DESIGN_NAME,
        "status": "success",
        "signal_count": len(normalized),
        "ticker_count": len(ticker_scores),
        "source_family_counts": family_counts,
        "portfolio_score": portfolio_score,
        "tickers": ticker_scores,
        "strengthened": [item for item in ticker_scores if item["label"] == "strengthened"][:10],
        "watch_items": [item for item in sorted(ticker_scores, key=lambda item: item["score"]) if item["label"] == "watch"][:10],
    }
