"""Portfolio health brief change detection helpers."""

from __future__ import annotations

from typing import Any


DESIGN_NAME = "portfolio_change_detection_v1"
PORTFOLIO_HEALTH_BRIEF_TYPE = "portfolio_health"
PORTFOLIO_CHANNEL = "portfolio"


def _dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


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


def _safe_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _safe_ticker(value: Any) -> str:
    return _safe_text(value).upper()


def _payload_container(brief: dict[str, Any]) -> dict[str, Any]:
    for key in ("content", "payload", "data", "metadata"):
        nested = _dict_value(brief.get(key))
        if nested:
            return nested
    return brief


def _score_payload(brief: dict[str, Any]) -> dict[str, Any]:
    payload = _payload_container(brief)
    for key in ("health", "portfolio_health", "score", "summary"):
        nested = _dict_value(payload.get(key))
        if nested and any(field in nested for field in ("total_score", "health_score", "score")):
            return nested
    return payload


def _brief_date(brief: dict[str, Any], payload: dict[str, Any]) -> str:
    value = _first_non_empty(
        payload.get("as_of"),
        payload.get("date"),
        payload.get("generated_at"),
        brief.get("as_of"),
        brief.get("created_at"),
        brief.get("updated_at"),
    )
    return _safe_text(value)


def _item_candidates(payload: dict[str, Any]) -> list[Any]:
    for key in ("holdings", "items", "positions", "signals", "components", "tickers", "companies"):
        items = _list_value(payload.get(key))
        if items:
            return items
    nested = _dict_value(payload.get("portfolio"))
    for key in ("holdings", "items", "positions"):
        items = _list_value(nested.get(key))
        if items:
            return items
    return []


def _normalize_item(item: dict[str, Any]) -> dict[str, Any] | None:
    ticker = _safe_ticker(_first_non_empty(item.get("ticker"), item.get("symbol"), item.get("external_id")))
    if not ticker:
        return None
    confidence = _safe_float(_first_non_empty(item.get("confidence"), item.get("confidence_score")))
    score = _safe_float(_first_non_empty(item.get("score"), item.get("health_score"), item.get("signal_score")))
    return {
        "ticker": ticker,
        "company_name": _safe_text(_first_non_empty(item.get("company_name"), item.get("company"), item.get("name"))),
        "stance": _safe_text(_first_non_empty(item.get("stance"), item.get("rating"), item.get("status"))),
        "confidence": confidence,
        "score": score,
        "summary": _safe_text(_first_non_empty(item.get("summary"), item.get("reason"), item.get("note"))),
    }


def _stance_rank(value: str) -> int:
    text = value.strip().lower()
    if not text:
        return 0
    positive_terms = ("bullish", "positive", "strengthen", "upgrade", "강화", "긍정", "상향")
    negative_terms = ("bearish", "negative", "weaken", "downgrade", "risk", "약화", "부정", "하향", "위험")
    neutral_terms = ("neutral", "hold", "watch", "중립", "관망")
    if any(term in text for term in positive_terms):
        return 1
    if any(term in text for term in negative_terms):
        return -1
    if any(term in text for term in neutral_terms):
        return 0
    return 0


def _delta_label(delta: float | None, threshold: float) -> str:
    if delta is None:
        return "unknown"
    if delta >= threshold:
        return "up"
    if delta <= -threshold:
        return "down"
    return "flat"


def normalize_portfolio_health_brief(brief: dict[str, Any]) -> dict[str, Any]:
    payload = _payload_container(brief)
    score_payload = _score_payload(brief)
    items: dict[str, dict[str, Any]] = {}
    for item in _item_candidates(payload):
        if not isinstance(item, dict):
            continue
        normalized = _normalize_item(item)
        if normalized:
            items[normalized["ticker"]] = normalized
    return {
        "brief_type": _safe_text(_first_non_empty(brief.get("brief_type"), payload.get("brief_type"), PORTFOLIO_HEALTH_BRIEF_TYPE)),
        "channel": _safe_text(_first_non_empty(brief.get("channel"), payload.get("channel"), PORTFOLIO_CHANNEL)),
        "as_of": _brief_date(brief, payload),
        "total_score": _safe_float(
            _first_non_empty(score_payload.get("total_score"), score_payload.get("health_score"), score_payload.get("score"))
        ),
        "items": items,
    }


def _item_change(previous: dict[str, Any] | None, current: dict[str, Any] | None, *, confidence_threshold: float) -> dict[str, Any]:
    base = current or previous or {}
    previous_confidence = previous.get("confidence") if previous else None
    current_confidence = current.get("confidence") if current else None
    previous_score = previous.get("score") if previous else None
    current_score = current.get("score") if current else None
    confidence_delta = (
        round(float(current_confidence) - float(previous_confidence), 4)
        if current_confidence is not None and previous_confidence is not None
        else None
    )
    score_delta = (
        round(float(current_score) - float(previous_score), 4)
        if current_score is not None and previous_score is not None
        else None
    )
    previous_stance = _safe_text(previous.get("stance")) if previous else ""
    current_stance = _safe_text(current.get("stance")) if current else ""
    event_types: list[str] = []
    if previous is None:
        event_types.append("added")
    elif current is None:
        event_types.append("removed")
    else:
        if previous_stance != current_stance:
            event_types.append("stance_changed")
        if confidence_delta is not None and abs(confidence_delta) >= confidence_threshold:
            event_types.append("confidence_changed")
        if score_delta is not None and abs(score_delta) >= confidence_threshold:
            event_types.append("score_changed")
    previous_rank = _stance_rank(previous_stance)
    current_rank = _stance_rank(current_stance)
    stance_direction = "flat"
    if current is None:
        stance_direction = "removed"
    elif previous is None:
        stance_direction = "added"
    elif current_rank > previous_rank:
        stance_direction = "improved"
    elif current_rank < previous_rank:
        stance_direction = "weakened"
    return {
        "ticker": base.get("ticker"),
        "company_name": base.get("company_name"),
        "previous_stance": previous_stance,
        "current_stance": current_stance,
        "stance_direction": stance_direction,
        "previous_confidence": previous_confidence,
        "current_confidence": current_confidence,
        "confidence_delta": confidence_delta,
        "previous_score": previous_score,
        "current_score": current_score,
        "score_delta": score_delta,
        "event_types": event_types,
        "watch_item": stance_direction in {"removed", "weakened"}
        or (confidence_delta is not None and confidence_delta <= -confidence_threshold)
        or (score_delta is not None and score_delta <= -confidence_threshold),
    }


def detect_portfolio_changes(
    previous_brief: dict[str, Any],
    current_brief: dict[str, Any],
    *,
    score_threshold: float = 0.3,
    confidence_threshold: float = 0.1,
) -> dict[str, Any]:
    previous = normalize_portfolio_health_brief(previous_brief)
    current = normalize_portfolio_health_brief(current_brief)
    previous_score = previous.get("total_score")
    current_score = current.get("total_score")
    score_delta = (
        round(float(current_score) - float(previous_score), 4)
        if current_score is not None and previous_score is not None
        else None
    )
    ticker_changes = [
        _item_change(
            previous["items"].get(ticker),
            current["items"].get(ticker),
            confidence_threshold=confidence_threshold,
        )
        for ticker in sorted(set(previous["items"]) | set(current["items"]))
    ]
    changed = [item for item in ticker_changes if item["event_types"]]
    top_movers = sorted(
        changed,
        key=lambda item: max(
            abs(float(item.get("confidence_delta") or 0)),
            abs(float(item.get("score_delta") or 0)),
            1.0 if "stance_changed" in item.get("event_types", []) else 0.0,
        ),
        reverse=True,
    )
    watch_items = [item for item in top_movers if item.get("watch_item")]
    return {
        "design": DESIGN_NAME,
        "status": "success",
        "previous_as_of": previous.get("as_of"),
        "current_as_of": current.get("as_of"),
        "health_score": {
            "previous": previous_score,
            "current": current_score,
            "delta": score_delta,
            "direction": _delta_label(score_delta, score_threshold),
        },
        "change_counts": {
            "ticker_count": len(current["items"]),
            "changed_count": len(changed),
            "stance_changed_count": sum(1 for item in changed if "stance_changed" in item["event_types"]),
            "confidence_changed_count": sum(1 for item in changed if "confidence_changed" in item["event_types"]),
            "watch_item_count": len(watch_items),
        },
        "ticker_changes": changed,
        "top_movers": top_movers[:10],
        "watch_items": watch_items[:10],
    }
