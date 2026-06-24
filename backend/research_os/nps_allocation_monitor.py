from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from re import findall, fullmatch
from typing import Any, Iterable

from research_os.models import PortfolioHolding, SavedPortfolio


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


def select_saved_portfolios_for_nps_allocation(
    portfolios_payload: dict[str, Any],
    portfolio_name: str = "__all__",
) -> tuple[str, list[SavedPortfolio]]:
    normalized = str(portfolio_name or "__all__").strip()
    portfolios = portfolios_payload if isinstance(portfolios_payload, dict) else {}
    if normalized in {"__all__", "all", "전체"}:
        selected = [SavedPortfolio.model_validate(item) for item in portfolios.values() if isinstance(item, dict)]
        if not selected:
            return "__all__", []
        aggregate_candidates = [
            item
            for item in selected
            if "합산" in item.portfolio_name.lower()
            or "aggregate" in item.portfolio_name.lower()
            or "consolidated" in item.portfolio_name.lower()
        ]
        if aggregate_candidates:
            aggregate = sorted(
                aggregate_candidates,
                key=lambda item: float(item.portfolio_value or 0),
                reverse=True,
            )[0]
            return aggregate.portfolio_name, [aggregate]
        return "__all__", selected

    for key, payload in portfolios.items():
        if not isinstance(payload, dict):
            continue
        saved = SavedPortfolio.model_validate(payload)
        if str(key) == normalized or saved.portfolio_name == normalized:
            return saved.portfolio_name, [saved]
    return normalized, []


def build_nps_domestic_equity_monitor_from_saved_portfolios(
    portfolios: list[SavedPortfolio],
    *,
    portfolio_name: str,
    target_weight: float = DEFAULT_NPS_DOMESTIC_EQUITY_TARGET,
    warn_tolerance: float = DEFAULT_NPS_DOMESTIC_EQUITY_TOLERANCE,
    checked_at: str | None = None,
) -> dict:
    holdings: list[PortfolioHolding] = []
    total_value = 0.0
    for portfolio in portfolios:
        holdings.extend(portfolio.holdings)
        if portfolio.portfolio_value is not None:
            total_value += float(portfolio.portfolio_value or 0)
        else:
            total_value += sum(float(item.market_value or 0) for item in portfolio.holdings)
    return build_nps_domestic_equity_allocation_monitor(
        portfolio_name=portfolio_name,
        holdings=holdings,
        portfolio_value=total_value,
        target_weight=target_weight,
        warn_tolerance=warn_tolerance,
        checked_at=checked_at,
    )


def _candidate_priority(row: dict, total_value: float) -> tuple[int, float]:
    bucket = str(row.get("bucket") or "")
    value = float(row.get("market_value") or 0)
    weight = value / total_value if total_value > 0 else 0.0
    if bucket in {"domestic_equity_etf", "domestic_equity_candidate"}:
        return (3, value)
    if weight >= 0.05:
        return (2, value)
    return (1, value)


def _rebalance_candidate(row: dict, total_value: float) -> dict:
    value = float(row.get("market_value") or 0)
    priority, _ = _candidate_priority(row, total_value)
    if priority >= 3:
        bucket = "축소 후보"
        rationale = "국내주식형 ETF/후보 자산이라 목표 비중 조정 시 먼저 금액 단위로 조절하기 쉽습니다."
    elif priority == 2:
        bucket = "추가 검토"
        rationale = "평가금액 비중이 커서 14% 목표에는 영향이 크지만, 개별 종목 논거 확인 후 조정이 필요합니다."
    else:
        bucket = "유지 후보"
        rationale = "소액 개별주로 14% 초과 해소 효과는 제한적입니다."
    return {
        "ticker": row.get("ticker"),
        "holding_name": row.get("holding_name"),
        "market_value": round(value, 2),
        "portfolio_weight": round(value / total_value, 6) if total_value > 0 else 0,
        "bucket": bucket,
        "source_bucket": row.get("bucket"),
        "reason": row.get("reason"),
        "rationale": rationale,
    }


def _allocate_reductions(rows: list[dict], reduction_needed: float, *, max_fraction: float = 1.0) -> list[dict]:
    remaining = max(float(reduction_needed or 0), 0.0)
    reductions: list[dict] = []
    for row in rows:
        if remaining <= 0:
            break
        value = float(row.get("market_value") or 0)
        if value <= 0:
            continue
        amount = min(value * max_fraction, remaining)
        remaining -= amount
        reductions.append(
            {
                "ticker": row.get("ticker"),
                "holding_name": row.get("holding_name"),
                "current_value": round(value, 2),
                "suggested_reduction_value": round(amount, 2),
                "suggested_reduction_pct_of_position": round(amount / value, 6) if value > 0 else 0,
                "remaining_value_after_reduction": round(max(value - amount, 0), 2),
                "rationale": row.get("rationale") or row.get("reason"),
            }
        )
    return reductions


def _scenario(
    *,
    title: str,
    strategy: str,
    rows: list[dict],
    reduction_needed: float,
    domestic_value: float,
    total_value: float,
    max_fraction: float = 1.0,
) -> dict:
    reductions = _allocate_reductions(rows, reduction_needed, max_fraction=max_fraction)
    reduced = sum(float(item.get("suggested_reduction_value") or 0) for item in reductions)
    remaining_domestic_value = max(domestic_value - reduced, 0.0)
    return {
        "title": title,
        "strategy": strategy,
        "suggested_reduction_value": round(reduced, 2),
        "remaining_gap_value": round(max(reduction_needed - reduced, 0.0), 2),
        "estimated_domestic_equity_value_after": round(remaining_domestic_value, 2),
        "estimated_domestic_equity_weight_after": round(remaining_domestic_value / total_value, 6)
        if total_value > 0
        else 0,
        "actions": reductions,
    }


def build_nps_domestic_equity_rebalance_plan(
    monitor: dict,
) -> dict:
    domestic_rows = [
        _rebalance_candidate(row, float(monitor.get("total_portfolio_value") or 0))
        for row in monitor.get("classification_rows", [])
        if isinstance(row, dict) and row.get("is_domestic_equity")
    ]
    total_value = float(monitor.get("total_portfolio_value") or 0)
    domestic_value = float(monitor.get("domestic_equity_value") or 0)
    target_weight = float(monitor.get("target_domestic_equity_weight") or DEFAULT_NPS_DOMESTIC_EQUITY_TARGET)
    target_value = total_value * target_weight
    reduction_needed = max(domestic_value - target_value, 0.0)
    add_needed = max(target_value - domestic_value, 0.0)
    sorted_by_priority = sorted(
        domestic_rows,
        key=lambda row: (_candidate_priority(row, total_value)[0], float(row.get("market_value") or 0)),
        reverse=True,
    )
    etf_first = sorted(
        domestic_rows,
        key=lambda row: (
            0 if row.get("source_bucket") in {"domestic_equity_etf", "domestic_equity_candidate"} else 1,
            -float(row.get("market_value") or 0),
        ),
    )
    large_first = sorted(domestic_rows, key=lambda row: float(row.get("market_value") or 0), reverse=True)
    proportional_rows = [
        {
            **row,
            "rationale": "국내주식 전체를 같은 비율로 줄여 종목 선택 편향을 낮추는 방식입니다.",
        }
        for row in large_first
    ]
    proportional_fraction = min(reduction_needed / domestic_value, 1.0) if domestic_value > 0 else 0.0

    if monitor.get("status") == "below_target":
        plan_status = "needs_increase"
        summary = (
            f"{monitor.get('portfolio_name')} 국내주식이 목표보다 낮아 약 {add_needed:,.0f}원 증액 후보 검토가 필요합니다."
        )
        scenarios: list[dict] = []
    elif reduction_needed <= 0:
        plan_status = "within_band"
        summary = f"{monitor.get('portfolio_name')} 국내주식 비중이 목표 범위 안에 있어 축소 시나리오가 필요하지 않습니다."
        scenarios = []
    else:
        plan_status = "needs_reduction"
        summary = (
            f"{monitor.get('portfolio_name')} 국내주식 14% 목표까지 약 {reduction_needed:,.0f}원 축소 검토가 필요합니다."
        )
        scenarios = [
            _scenario(
                title="ETF/테마 우선 축소",
                strategy="국내주식형 ETF와 후보 자산을 먼저 줄여 개별주 논거 훼손을 줄입니다.",
                rows=etf_first,
                reduction_needed=reduction_needed,
                domestic_value=domestic_value,
                total_value=total_value,
            ),
            _scenario(
                title="대형 보유 우선 축소",
                strategy="평가금액이 큰 국내주식부터 줄여 14% 목표에 가장 빠르게 접근합니다.",
                rows=large_first,
                reduction_needed=reduction_needed,
                domestic_value=domestic_value,
                total_value=total_value,
            ),
            _scenario(
                title="비례 축소",
                strategy="모든 국내주식 보유를 같은 비율로 낮춰 특정 종목 판단을 최소화합니다.",
                rows=proportional_rows,
                reduction_needed=reduction_needed,
                domestic_value=domestic_value,
                total_value=total_value,
                max_fraction=proportional_fraction,
            ),
        ]

    return {
        "status": plan_status,
        "module": "nps_domestic_equity_rebalance_plan",
        "portfolio_name": monitor.get("portfolio_name"),
        "policy_source": monitor.get("policy_source"),
        "target_domestic_equity_weight": round(target_weight, 6),
        "current_domestic_equity_weight": monitor.get("current_domestic_equity_weight"),
        "total_portfolio_value": round(total_value, 2),
        "domestic_equity_value": round(domestic_value, 2),
        "target_domestic_equity_value": round(target_value, 2),
        "reduction_needed_value": round(reduction_needed, 2),
        "increase_needed_value": round(add_needed, 2),
        "candidate_count": len(domestic_rows),
        "candidates": {
            "reduce": [row for row in sorted_by_priority if row.get("bucket") == "축소 후보"],
            "review": [row for row in sorted_by_priority if row.get("bucket") == "추가 검토"],
            "keep": [row for row in sorted_by_priority if row.get("bucket") == "유지 후보"],
        },
        "scenarios": scenarios,
        "summary": summary,
        "next_actions": [
            "이 표는 주문 지시가 아니라 14% 정책 비중을 맞추기 위한 검토 후보입니다.",
            "축소 전 최신 가격, 세금/수수료, 기존 투자 논거, 당일 유동성을 다시 확인하세요.",
            "ETF 우선/대형 보유 우선/비례 축소 중 투자 논거 훼손이 가장 작은 시나리오를 선택하세요.",
        ],
    }
