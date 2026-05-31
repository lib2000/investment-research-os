"""Small helpers for portfolio performance calculations."""

from __future__ import annotations

from re import fullmatch, sub
from typing import Any


def build_price_refresh_summary(
    holdings: list[Any],
    *,
    enabled: bool = True,
    force_price_refresh: bool = True,
    description: str | None = None,
) -> dict:
    """Summarize current-price refresh status across portfolio holdings."""
    status_counts: dict[str, int] = {}
    checked_at_values: list[str] = []
    for holding in holdings:
        status = getattr(holding, "price_refresh_status", None) or "unknown"
        status_counts[status] = status_counts.get(status, 0) + 1
        checked_at = getattr(holding, "price_checked_at", None)
        if checked_at:
            checked_at_values.append(str(checked_at))
    return {
        "enabled": enabled,
        "force_price_refresh": force_price_refresh,
        "status_counts": status_counts,
        "updated": status_counts.get("updated", 0),
        "confirmed": status_counts.get("confirmed", 0),
        "unavailable": status_counts.get("unavailable", 0),
        "skipped": status_counts.get("skipped", 0),
        "latest_checked_at": sorted(checked_at_values)[-1] if checked_at_values else None,
        "description": description
        or "기간 수익 비교를 계산하기 전에 저장 포트폴리오의 현재가를 가능한 원천에서 강제 갱신합니다.",
    }


def target_price_currency(symbol: str | None, unit: str | None, holding_currency: str) -> str:
    unit_text = str(unit or "").upper()
    symbol_text = str(symbol or "")
    if "$" in symbol_text or "USD" in unit_text or "달러" in unit_text:
        return "USD"
    if "₩" in symbol_text or "KRW" in unit_text or "원" in unit_text:
        return "KRW"
    normalized_currency = (holding_currency or "KRW").upper()
    return normalized_currency if normalized_currency in {"USD", "KRW"} else "KRW"


def is_plausible_target_price(value: float, currency: str) -> bool:
    if value <= 0:
        return False
    if currency == "KRW":
        return 100 <= value <= 5_000_000
    if currency == "USD":
        return 0.01 <= value <= 5_000
    return True


def filter_target_price_outliers(values: list[float]) -> list[float]:
    if len(values) < 4:
        return values
    sorted_values = sorted(values)
    midpoint = len(sorted_values) // 2
    median = (
        sorted_values[midpoint]
        if len(sorted_values) % 2
        else (sorted_values[midpoint - 1] + sorted_values[midpoint]) / 2
    )
    if median <= 0:
        return values
    filtered = [value for value in values if median * 0.35 <= value <= median * 2.8]
    return filtered if len(filtered) >= 2 else values


def _normalize_target_ticker(value: object) -> str:
    return sub(r"[^A-Za-z0-9._-]+", "-", str(value or "").strip().upper()).strip("-") or "UNKNOWN"


def is_probable_year_or_metadata_number(
    raw_value: object,
    symbol: str | None,
    unit: str | None,
    context: str,
    ticker_context: str | None = None,
) -> bool:
    raw_text = str(raw_value or "").strip().replace(",", "")
    unit_text = str(unit or "").strip()
    symbol_text = str(symbol or "").strip()
    context_text = context.lower()
    metadata_blockers = [
        "mime",
        "bytes",
        "파일명",
        "파일 이름",
        "파일 크기",
        "크기:",
        "pdf 링크",
        "원문 링크",
        "nid=",
        "page=",
        "종목코드",
        "발행일",
        "저장 범위",
        "분류 근거",
        "as of",
        "quarter 20",
        "fy20",
        "fiscal",
        "financial results",
    ]
    if any(blocker in context_text for blocker in metadata_blockers):
        return True
    if not unit_text and not symbol_text and raw_text.isdigit() and len(raw_text) == 4:
        year_value = int(raw_text)
        if 1900 <= year_value <= 2100:
            return True
    normalized_ticker_context = _normalize_target_ticker(ticker_context)
    if raw_text.isdigit() and fullmatch(r"\d{6}", normalized_ticker_context):
        try:
            if int(raw_text) == int(normalized_ticker_context):
                return True
        except ValueError:
            pass
    return False
