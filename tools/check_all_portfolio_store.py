"""Validate common storage invariants across every saved portfolio."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_STORE = Path("research_vault/_system/user_portfolios.json")
CASH_TICKERS = {"CASH", "예수금"}


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (
            candidate / "research_vault"
        ).exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def load_portfolios(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"포트폴리오 저장 파일을 찾지 못했습니다: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"포트폴리오 저장 파일 JSON 파싱 실패: {exc}") from exc
    portfolios = data.get("portfolios") if isinstance(data, dict) else None
    if not isinstance(portfolios, dict):
        raise SystemExit("포트폴리오 저장 파일에 portfolios 객체가 없습니다.")
    return portfolios


def number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def parse_dt(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def age_hours(value: Any) -> float | None:
    parsed = parse_dt(value)
    if not parsed:
        return None
    return (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds() / 3600


def holding_ticker(item: dict[str, Any]) -> str:
    return str(item.get("ticker") or "").strip().upper()


def portfolio_name(key: str, portfolio: dict[str, Any]) -> str:
    return str(portfolio.get("portfolio_name") or key)


def validate_portfolio(
    key: str,
    portfolio: dict[str, Any],
    *,
    min_holdings: int,
    forbid_zero: bool,
    allow_cash: bool,
    require_price_fields: bool,
    require_overseas_protection: bool,
    max_portfolio_age_hours: float,
) -> tuple[list[str], dict[str, Any]]:
    label = portfolio_name(key, portfolio)
    errors: list[str] = []
    holdings = portfolio.get("holdings") or []
    if not isinstance(holdings, list):
        return [f"{label}: holdings 구조가 배열이 아닙니다."], {"name": label, "holdings": 0}

    rows = [item for item in holdings if isinstance(item, dict)]
    if len(rows) != len(holdings):
        errors.append(f"{label}: 보유 종목 배열에 객체가 아닌 항목이 있습니다.")
    if len(rows) < min_holdings:
        errors.append(f"{label}: 보유 종목 수 부족 {len(rows)}개 / 필요 {min_holdings}개")
    if portfolio.get("holding_count") not in (None, len(rows)):
        errors.append(f"{label}: holding_count 불일치 {portfolio.get('holding_count')} / 실제 {len(rows)}")

    updated_age = age_hours(portfolio.get("updated_at"))
    if updated_age is None:
        errors.append(f"{label}: updated_at 누락/파싱 실패")
    elif updated_age > max_portfolio_age_hours:
        errors.append(f"{label}: updated_at 오래됨 {updated_age:.1f}시간 / 기준 {max_portfolio_age_hours:.1f}시간")

    tickers = [holding_ticker(item) for item in rows]
    duplicate_tickers = sorted({ticker for ticker in tickers if ticker and tickers.count(ticker) > 1})
    if duplicate_tickers:
        errors.append(f"{label}: 중복 보유 종목 {', '.join(duplicate_tickers)}")

    protected_count = 0
    overseas_count = 0
    for item in rows:
        ticker = holding_ticker(item)
        name = str(item.get("name") or "").strip()
        ticker_or_name = ticker or name or "(이름 없음)"
        if not ticker:
            errors.append(f"{label}: 티커 누락 보유 종목 {name or '(이름 없음)'}")
        if not name:
            errors.append(f"{label}: 회사명 누락 보유 종목 {ticker_or_name}")

        quantity = number(item.get("quantity"))
        if quantity is None:
            errors.append(f"{label}: {ticker_or_name} 수량 숫자 변환 실패")
        elif forbid_zero and quantity == 0:
            errors.append(f"{label}: {ticker_or_name} 수량 0 종목 잔존")

        upper_name = name.upper()
        if not allow_cash and (ticker in CASH_TICKERS or upper_name in CASH_TICKERS):
            errors.append(f"{label}: {ticker_or_name} 예수금/CASH 항목 혼입")

        currency = str(item.get("currency") or "").strip().upper()
        sync_status = str(item.get("sync_status") or item.get("sync_state") or "").strip()
        if currency and currency != "KRW":
            overseas_count += 1
            if sync_status == "manual_or_overseas_protected":
                protected_count += 1
            elif require_overseas_protection:
                errors.append(f"{label}: {ticker_or_name} 해외/수동 수량 보호 상태 누락: {sync_status or '없음'}")

        if require_price_fields:
            for field in ("average_cost", "current_price", "market_value", "cost_basis", "currency"):
                if item.get(field) in (None, ""):
                    errors.append(f"{label}: {ticker_or_name} {field} 누락")
            if number(item.get("market_value")) is None:
                errors.append(f"{label}: {ticker_or_name} 평가금액 숫자 변환 실패")
            if number(item.get("cost_basis")) is None:
                errors.append(f"{label}: {ticker_or_name} 투자금 숫자 변환 실패")

    market_sum = sum(number(item.get("market_value")) or 0 for item in rows)
    stored_value = number(portfolio.get("portfolio_value"))
    if stored_value is not None and abs(stored_value - market_sum) > 1.0:
        errors.append(f"{label}: 포트폴리오 총액 불일치 저장 {stored_value:,.2f} / 합계 {market_sum:,.2f}")

    return errors, {
        "name": label,
        "holdings": len(rows),
        "updated_age": updated_age,
        "value": stored_value,
        "overseas": overseas_count,
        "protected": protected_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="전체 저장 포트폴리오의 공통 구조와 수량 보호 상태를 점검합니다.")
    parser.add_argument("--store", type=Path, default=None, help="user_portfolios.json 경로")
    parser.add_argument("--min-holdings", type=int, default=1, help="포트폴리오별 최소 보유 종목 수")
    parser.add_argument("--forbid-zero", action="store_true", help="수량 0 종목이 있으면 실패")
    parser.add_argument("--allow-cash", action="store_true", help="CASH/예수금 항목을 허용합니다")
    parser.add_argument("--require-price-fields", action="store_true", default=True, help="가격/평가 필드를 강제합니다")
    parser.add_argument("--require-overseas-protection", action="store_true", default=True, help="해외 통화 보유 종목의 manual_or_overseas_protected 상태를 강제합니다")
    parser.add_argument("--max-portfolio-age-hours", type=float, default=240.0, help="포트폴리오 updated_at 최신성 기준")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    store = args.store if args.store else root / DEFAULT_STORE
    if not store.is_absolute():
        store = root / store
    portfolios = load_portfolios(store)

    errors: list[str] = []
    summaries: list[dict[str, Any]] = []
    for key, portfolio in portfolios.items():
        if not isinstance(portfolio, dict):
            errors.append(f"{key}: 포트폴리오 구조가 객체가 아닙니다.")
            continue
        portfolio_errors, summary = validate_portfolio(
            key,
            portfolio,
            min_holdings=args.min_holdings,
            forbid_zero=args.forbid_zero,
            allow_cash=args.allow_cash,
            require_price_fields=args.require_price_fields,
            require_overseas_protection=args.require_overseas_protection,
            max_portfolio_age_hours=args.max_portfolio_age_hours,
        )
        errors.extend(portfolio_errors)
        summaries.append(summary)

    print(f"저장 파일: {store}")
    print(f"포트폴리오 수: {len(summaries)}개")
    for summary in summaries:
        age = summary.get("updated_age")
        age_label = f"{age:.1f}시간" if age is not None else "미확인"
        value = summary.get("value")
        value_label = f"{value:,.0f}" if isinstance(value, (int, float)) else "-"
        print(f"- {summary['name']} | 보유 {summary['holdings']}개 | 해외 보호 {summary.get('protected', 0)}/{summary.get('overseas', 0)}개 | 총액 {value_label} | 갱신 {age_label}")

    if errors:
        for error in errors:
            print(f"오류: {error}")
        return 1
    print("전체 포트폴리오 저장 구조 상태 정상")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
