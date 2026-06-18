"""DeepSeek IR analysis payload helpers for Market Signal Graph."""

from __future__ import annotations

from hashlib import sha256
from typing import Any


DESIGN_NAME = "deepseek_ir_analysis_contract_v1"
SOURCE_PLATFORM = "deepseek_ir_analysis"
ANALYSIS_TYPE = "firecrawl_ir_signal_analysis_v2"


def sha256_hex(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


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


def _safe_list(values: Any, *, max_items: int = 8) -> list[str]:
    if isinstance(values, str):
        values = [part.strip() for part in values.replace(";", "\n").splitlines()]
    return [_safe_text(item) for item in _list_value(values) if _safe_text(item)][:max_items]


def _bounded_score(value: Any, *, default: float = 5.0) -> float:
    score = _safe_float(value)
    if score is None:
        return default
    return round(max(0.0, min(10.0, score)), 2)


def _bounded_confidence(value: Any, *, default: float = 0.65) -> float:
    confidence = _safe_float(value)
    if confidence is None:
        return default
    if confidence > 1.0:
        confidence = confidence / 100.0
    return round(max(0.0, min(1.0, confidence)), 4)


def build_deepseek_ir_analysis_payload(signal_payload: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    metadata = _dict_value(signal_payload.get("metadata"))
    analysis_metadata = _dict_value(analysis.get("metadata"))
    ticker = _safe_ticker(_first_non_empty(analysis.get("ticker"), signal_payload.get("ticker"), metadata.get("ticker")))
    company = _safe_text(_first_non_empty(analysis.get("company"), signal_payload.get("company"), metadata.get("company")))
    source_external_id = _safe_text(signal_payload.get("external_id"))
    source_platform = _safe_text(signal_payload.get("source_platform"))
    source_kind = _safe_text(signal_payload.get("source_kind"))
    title = _safe_text(_first_non_empty(analysis.get("title"), signal_payload.get("title")))
    summary = _safe_text(_first_non_empty(analysis.get("summary"), analysis.get("thesis"), analysis.get("text")))
    if not summary:
        summary = f"DeepSeek analysis pending summary for {ticker or company or 'signal'}."
    stance = _safe_text(_first_non_empty(analysis.get("stance"), analysis.get("rating"), analysis.get("signal"))) or "neutral"
    score = _bounded_score(_first_non_empty(analysis.get("score"), analysis.get("signal_score"), analysis.get("impact_score")))
    confidence = _bounded_confidence(_first_non_empty(analysis.get("confidence"), analysis.get("confidence_score")))
    analysis_id_seed = "|".join([ANALYSIS_TYPE, source_platform, source_external_id, ticker, title])
    return {
        "analysis_id": sha256_hex(analysis_id_seed),
        "source_platform": SOURCE_PLATFORM,
        "analysis_type": ANALYSIS_TYPE,
        "source_signal_external_id": source_external_id,
        "source_signal_platform": source_platform,
        "source_signal_kind": source_kind,
        "ticker": ticker,
        "company": company,
        "title": title,
        "summary": summary,
        "stance": stance,
        "score": score,
        "confidence": confidence,
        "key_points": _safe_list(_first_non_empty(analysis.get("key_points"), analysis.get("drivers"))),
        "risks": _safe_list(analysis.get("risks")),
        "catalysts": _safe_list(analysis.get("catalysts")),
        "metadata": {
            "collector_design": DESIGN_NAME,
            "model_provider": "deepseek",
            "source_url": signal_payload.get("url"),
            "source_title": signal_payload.get("title"),
            "source_metadata": metadata,
            **analysis_metadata,
        },
        "needs_review": bool(analysis.get("needs_review", False)),
        "analysis_status": _safe_text(analysis.get("analysis_status")) or "completed",
    }


def build_deepseek_ir_analysis_batch_result(items: list[dict[str, Any]]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        try:
            signal_payload = _dict_value(item.get("signal") or item.get("signal_payload") or item.get("source"))
            analysis = _dict_value(item.get("analysis") or item.get("llm") or item)
            if not signal_payload:
                raise ValueError("DeepSeek analysis payload requires signal or signal_payload.")
            payload = build_deepseek_ir_analysis_payload(signal_payload, analysis)
            errors: list[str] = []
        except Exception as exc:
            payload = None
            errors = [str(exc)]
        results.append({"index": index, "status": "valid" if payload else "failed", "payload": payload, "errors": errors})
    failed_count = sum(1 for item in results if item["status"] == "failed")
    return {
        "status": "failed" if failed_count else "success",
        "design": DESIGN_NAME,
        "source_platform": SOURCE_PLATFORM,
        "analysis_type": ANALYSIS_TYPE,
        "item_count": len(items),
        "valid_count": len(items) - failed_count,
        "failed_count": failed_count,
        "results": results,
    }
