from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from re import findall, fullmatch
from typing import Iterable

from research_os.models import PortfolioHolding


DEFAULT_NPS_DOMESTIC_EQUITY_TARGET = 0.14
DEFAULT_NPS_DOMESTIC_EQUITY_TOLERANCE = 0.01

_CASH_TICKERS = {"CASH", "KRW", "USD", "예수금", "현금"}
_DOMESTIC_ETF_MARKERS = ("KODEX", "TIGER", "SOL", "ACE", "RISE", "KBSTAR", "KIWOOM", "HANARO", "TIMEFOLIO")
_OVERSEAS_EXPOSURE_TERMS = (
    "미국",
    "S&P",
    "SNP",
    "NASDAQ",
    "나스닥",
    "중국",
    "차이나",
    "CHINA",
    "인도",
    "INDIA",
    "NIFTY",
    "STAR50",
    "글로벌",
    "GLOBAL",
    "일본",
    "JAPAN",
)
_OVERSEAS_EXPOSURE_TOKENS = {"US", "USA", "CHINA", "INDIA", "NIFTY", "JAPAN", "GLOBAL"}
_NON_EQUITY_TERMS = ("채권", "BOND", "리츠", "REIT", "인프라", "INFRA", "원자재", "GOLD", "금선물")


@dataclass(frozen=True)
class DomesticEquityClassification:
    bucket: str
    is_domestic_equity: bool
    reason: str


def _text_blob(holding: PortfolioHolding) -> str:
    values = [
        holding.ticker,
        holding.name or "",
        holding.sector or "",
        " ".join(holding.theme_tags or []),
        holding.currency or "",
    ]
    return " ".join(str(value) for value in values if value).upper()


def _ticker(holding: PortfolioHolding) -> str:
    return str(holding.ticker or "").strip().upper()


def _has_overseas_exposure(text: str) -> bool:
    if any(term in text for term in _OVERSEAS_EXPOSURE_TERMS):
        return True
    tokens = set(findall(r"[A-Z0-9]+", text))
    return bool(tokens & _OVERSEAS_EXPOSURE_TOKENS)


def classify_domestic_equity_holding(holding: PortfolioHolding) -> DomesticEquityClassification:
    ticker = _ticker(holding)
    name = str(holding.name or "").strip()
    currency = str(holding.currency or "").strip().upper()
    text = _text_blob(holding)

    if not ticker:
        return DomesticEquityClassification("missing_ticker", False, "티커가 없어 국내주식 비중 계산에서 제외")
    if ticker in _CASH_TICKERS or name.upper() in _CASH_TICKERS:
        return DomesticEquityClassification("cash", False, "현금/예수금 항목은 비중의 분모에는 포함하되 국내주식 노출에서는 제외")
    if currency and currency != "KRW":
        return DomesticEquityClassification("overseas_listed", False, f"{currency} 표시 해외 상장 종목")
    if any(term in text for term in _NON_EQUITY_TERMS):
        return DomesticEquityClassification("domestic_non_equity", False, "국내 상장이라도 채권/리츠/인프라/원자재 성격은 국내주식에서 제외")
    if _has_overseas_exposure(text):
        return DomesticEquityClassification("domestic_listed_overseas_exposure", False, "한국 상장 해외 노출 ETF/상품으로 분류")
    if fullmatch(r"\d{6}", ticker):
        if any(marker in text for marker in _DOMESTIC_ETF_MARKERS):
            return DomesticEquityClassification("domestic_equity_etf", True, "한국 상장 국내주식형 ETF로 분류")
        return DomesticEquityClassification("domestic_equity", True, "한국 개별주로 분류")
    if currency == "KRW":
        return DomesticEquityClassification("domestic_equity_candidate", True, "KRW 표시 국내주식 후보로 분류")
    return DomesticEquityClassification("unknown", False, "국내주식 여부를 보수적으로 확인하지 못해 제외")


def _holding_value(holding: PortfolioHolding) -> float:
    value = holding.market_value
    if value is None and holding.quantity is not None and holding.current_price is not None:
        value = holding.quantity * holding.current_price
    try:
        return max(float(value or 0), 0.0)
    except (TypeError, ValueError):
        return 0.0


def build_nps_domestic_equity_allocation_monitor(
    *,
    portfolio_name: str,
    holdings: Iterable[PortfolioHolding],
    portfolio_value: float | None = None,
    target_weight: float = DEFAULT_NPS_DOMESTIC_EQUITY_TARGET,
    warn_tolerance: float = DEFAULT_NPS_DOMESTIC_EQUITY_TOLERANCE,
    checked_at: str | None = None,
) -> dict:
    holding_rows = list(holdings)
    classified: list[dict] = []
    domestic_value = 0.0
    inferred_total = 0.0
    included_count = 0
    excluded_count = 0

    for holding in holding_rows:
        value = _holding_value(holding)
        inferred_total += value
        classification = classify_domestic_equity_holding(holding)
        if classification.is_domestic_equity:
            domestic_value += value
            included_count += 1
        else:
            excluded_count += 1
        classified.append(
            {
                "ticker": _ticker(holding),
                "holding_name": holding.name,
                "market_value": round(value, 2),
                "currency": str(holding.currency or "").upper() or None,
                "bucket": classification.bucket,
                "is_domestic_equity": classification.is_domestic_equity,
                "reason": classification.reason,
            }
        )

    total_value = float(portfolio_value or 0)
    if total_value <= 0:
        total_value = inferred_total
    current_weight = domestic_value / total_value if total_value > 0 else 0.0
    gap_weight = target_weight - current_weight
    gap_pct_points = gap_weight * 100
    gap_value = gap_weight * total_value
    tolerance = max(float(warn_tolerance), 0.0)

    if total_value <= 0 or not holding_rows:
        status = "needs_data"
        severity = "medium"
        action = "보유 종목 평가금액을 먼저 동기화한 뒤 국민연금 국내주식 14% 기준을 다시 확인하세요."
    elif current_weight < target_weight - tolerance:
        status = "below_target"
        severity = "high" if current_weight < target_weight - (tolerance * 2) else "medium"
        action = f"국내주식 노출이 목표보다 {abs(gap_pct_points):.2f}%p 낮습니다. 약 {abs(gap_value):,.0f}원 증액 여지가 있습니다."
    elif current_weight > target_weight + tolerance:
        status = "above_target"
        severity = "high" if current_weight > target_weight + (tolerance * 2) else "medium"
        action = f"국내주식 노출이 목표보다 {abs(gap_pct_points):.2f}%p 높습니다. 약 {abs(gap_value):,.0f}원 축소 검토 구간입니다."
    else:
        status = "within_band"
        severity = "low"
        action = f"국내주식 노출이 {target_weight * 100:.1f}% 목표 허용 범위 안에 있습니다."

    top_included = sorted(
        [item for item in classified if item["is_domestic_equity"]],
        key=lambda item: float(item.get("market_value") or 0),
        reverse=True,
    )[:12]
    top_excluded = sorted(
        [item for item in classified if not item["is_domestic_equity"]],
        key=lambda item: float(item.get("market_value") or 0),
        reverse=True,
    )[:12]

    return {
        "status": status,
        "module": "nps_domestic_equity_allocation_monitor",
        "portfolio_name": portfolio_name,
        "policy_source": "국민연금 공시 포트폴리오 국내주식 비중 14% 기준",
        "target_domestic_equity_weight": round(target_weight, 6),
        "warn_tolerance": round(tolerance, 6),
        "current_domestic_equity_weight": round(current_weight, 6),
        "gap_weight": round(gap_weight, 6),
        "gap_pct_points": round(gap_pct_points, 4),
        "gap_value": round(gap_value, 2),
        "domestic_equity_value": round(domestic_value, 2),
        "total_portfolio_value": round(total_value, 2),
        "holding_count": len(holding_rows),
        "included_domestic_equity_count": included_count,
        "excluded_count": excluded_count,
        "severity": severity,
        "recommended_action": action,
        "checked_at": checked_at or datetime.now(timezone.utc).isoformat(),
        "top_domestic_equity_holdings": top_included,
        "top_excluded_holdings": top_excluded,
        "classification_rows": classified,
        "next_actions": [
            "포트폴리오 가격 동기화 후 이 모니터를 다시 실행해 14% 비중을 확인하세요.",
            "국내주식 목표와 실제 비중의 차이가 1%p를 넘으면 리밸런싱 후보를 먼저 점검하세요.",
            "한국 상장 해외 ETF와 인프라/리츠/채권형 상품은 국내주식 14% 계산에서 제외됩니다.",
        ],
        "summary": (
            f"{portfolio_name} 국내주식 비중 {current_weight * 100:.2f}% "
            f"/ 목표 {target_weight * 100:.1f}%"
        ),
    }
