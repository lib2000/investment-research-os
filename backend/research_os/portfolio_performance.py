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


def target_price_result(
    value: float,
    currency: str,
    memory_file,
    source_label: str,
    confidence: float,
) -> dict | None:
    if not is_plausible_target_price(value, currency):
        return None
    return {
        "target_price": round(value, 4),
        "target_price_currency": currency,
        "target_price_source_file": memory_file.file_name,
        "target_price_source_type": source_label,
        "target_price_confidence": round(confidence, 2),
    }


def target_price_context_source_type(text: str) -> tuple[str, float]:
    normalized = text.lower()
    if any(keyword in text for keyword in ["컨센서스", "평균 목표", "증권사 평균", "시장 평균"]):
        return "증권사 컨센서스 목표주가", 0.95
    if any(keyword in text for keyword in ["증권사", "투자의견", "리포트", "목표주가", "목표가"]):
        return "증권사 리포트 목표주가", 0.88
    if "target price" in normalized or "analyst" in normalized:
        return "애널리스트 목표주가", 0.86
    return "저장 리포트 목표주가", 0.78

def historical_close_on_or_before(rows: list[dict], target_date, parse_float) -> tuple[float | None, str | None]:
    target = target_date.isoformat()
    for row in reversed(rows):
        row_date = str(row.get("date") or "")
        close = parse_float(row.get("close"))
        if row_date and row_date <= target and close is not None and close > 0:
            return close, row_date
    return None, None


def portfolio_holding_current_value(
    holding,
    current_price: float | None,
    infer_fx_rate,
    *,
    prefer_market_value: bool = True,
) -> float | None:
    if prefer_market_value and holding.market_value is not None and holding.market_value > 0:
        return holding.market_value
    if holding.quantity is None or holding.quantity <= 0 or current_price is None:
        return None
    return holding.quantity * current_price * infer_fx_rate(holding)


def build_period_accumulators(period_definitions: list[tuple[str, str, int]]) -> dict:
    return {
        key: {
            "key": key,
            "label": label,
            "days": days,
            "target_date": None,
            "price_as_of": None,
            "target_dates": [],
            "price_as_of_dates": [],
            "current_value": 0.0,
            "base_value": 0.0,
            "net_profit": 0.0,
            "return_rate": None,
            "included_count": 0,
            "covered_market_value": 0.0,
            "top_gainers": [],
            "top_losers": [],
        }
        for key, label, days in period_definitions
    }


def finalize_period_accumulators(
    period_definitions: list[tuple[str, str, int]],
    period_accumulators: dict,
    current_portfolio_value: float,
) -> list[dict]:
    periods = []
    for key, _label, _days in period_definitions:
        period = period_accumulators[key]
        base_value = period["base_value"]
        return_rate = period["net_profit"] / base_value if base_value > 0 else None
        period["current_value"] = round(period["current_value"], 2)
        period["base_value"] = round(period["base_value"], 2)
        period["net_profit"] = round(period["net_profit"], 2)
        period["return_rate"] = round(return_rate, 4) if return_rate is not None else None
        target_dates = sorted(date_text for date_text in period.pop("target_dates", []) if date_text)
        price_as_of_period_dates = sorted(date_text for date_text in period.pop("price_as_of_dates", []) if date_text)
        period["target_date"] = target_dates[-1] if target_dates else None
        period["price_as_of"] = price_as_of_period_dates[-1] if price_as_of_period_dates else None
        period["coverage_rate"] = (
            round(period["covered_market_value"] / current_portfolio_value, 4)
            if current_portfolio_value > 0
            else None
        )
        period["top_gainers"] = sorted(
            period["top_gainers"],
            key=lambda item: item.get("net_profit") or 0,
            reverse=True,
        )[:3]
        period["top_losers"] = sorted(
            period["top_losers"],
            key=lambda item: item.get("net_profit") or 0,
        )[:3]
        periods.append(period)
    return periods

def build_performance_quality_summary(
    periods: list[dict],
    price_comparisons: list[dict],
    *,
    excluded_holding_count: int,
    latest_stored_price_checked_at: str | None,
    price_basis: str,
) -> dict:
    coverage_rates = [
        period.get("coverage_rate")
        for period in periods
        if period.get("coverage_rate") is not None
    ]
    min_coverage_rate = min(coverage_rates) if coverage_rates else None
    avg_coverage_rate = (
        sum(coverage_rates) / len(coverage_rates)
        if coverage_rates
        else None
    )
    if min_coverage_rate is None:
        confidence_label = "계산 보류"
    elif min_coverage_rate >= 0.8 and not price_comparisons:
        confidence_label = "높음"
    elif min_coverage_rate >= 0.5:
        confidence_label = "보통"
    else:
        confidence_label = "제한적"
    if price_comparisons and confidence_label == "높음":
        confidence_label = "확인 필요"
    return {
        "confidence_label": confidence_label,
        "min_coverage_rate": round(min_coverage_rate, 4) if min_coverage_rate is not None else None,
        "average_coverage_rate": round(avg_coverage_rate, 4) if avg_coverage_rate is not None else None,
        "covered_holding_count": max((period.get("included_count") or 0 for period in periods), default=0),
        "excluded_holding_count": excluded_holding_count,
        "domestic_price_difference_count": len(price_comparisons),
        "latest_stored_price_checked_at": latest_stored_price_checked_at,
        "price_basis": price_basis,
    }
