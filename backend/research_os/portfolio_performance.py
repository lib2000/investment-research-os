"""Small helpers for portfolio performance calculations."""

from __future__ import annotations

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
