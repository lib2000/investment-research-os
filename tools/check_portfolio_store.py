"""Validate portfolio holdings stored on disk without a running backend."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_STORE = Path("research_vault/_system/user_portfolios.json")
DEFAULT_EXPECTED = "PL=100:USD,JOBY=208:USD,CHPT=22:USD,ABSI=29:USD,GOTU=50:USD,OTLY=8:USD,RXRX=9:USD,253450=36:KRW"


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (
            candidate / "research_vault"
        ).exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def load_store(path: Path) -> dict[str, Any]:
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


def parse_expected(value: str) -> dict[str, tuple[float, str | None]]:
    expected: dict[str, tuple[float, str | None]] = {}
    for chunk in [part.strip() for part in value.split(",") if part.strip()]:
        if "=" not in chunk:
            raise SystemExit(f"기대 보유 형식 오류: {chunk}")
        ticker, rest = chunk.split("=", 1)
        currency = None
        if ":" in rest:
            qty_text, currency = rest.split(":", 1)
            currency = currency.strip().upper() or None
        else:
            qty_text = rest
        try:
            quantity = float(qty_text)
        except ValueError as exc:
            raise SystemExit(f"기대 수량 숫자 변환 실패: {chunk}") from exc
        expected[ticker.strip().upper()] = (quantity, currency)
    return expected


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


def main() -> int:
    parser = argparse.ArgumentParser(description="포트폴리오 저장 파일의 수량 보호 상태를 점검합니다.")
    parser.add_argument("--store", type=Path, default=None, help="user_portfolios.json 경로")
    parser.add_argument("--portfolio", default="이형주", help="확인할 포트폴리오 이름 또는 키")
    parser.add_argument("--expected", default=DEFAULT_EXPECTED, help="예: PL=100:USD,253450=36:KRW")
    parser.add_argument("--min-holdings", type=int, default=1, help="최소 보유 종목 수")
    parser.add_argument("--forbid-zero", action="store_true", help="수량 0 종목이 있으면 실패")
    parser.add_argument("--allow-cash", action="store_true", help="CASH/예수금 항목을 허용합니다")
    parser.add_argument("--require-price-fields", action="store_true", default=True, help="평단/현재가/평가금액/가격 출처를 강제합니다")
    parser.add_argument("--max-price-age-hours", type=float, default=96.0, help="가격 확인 시각 최신성 기준")
    parser.add_argument("--max-portfolio-age-hours", type=float, default=96.0, help="포트폴리오 자체 updated_at 최신성 기준")
    parser.add_argument("--max-sync-age-hours", type=float, default=168.0, help="해외/수동 수량 sync_checked_at 최신성 기준")
    parser.add_argument("--value-tolerance", type=float, default=1.0, help="저장 총액과 종목 평가금액 합계 허용 오차")
    parser.add_argument("--weight-tolerance", type=float, default=0.02, help="보유 종목 weight 합계 허용 오차")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    store = args.store if args.store else root / DEFAULT_STORE
    if not store.is_absolute():
        store = root / store
    portfolios = load_store(store)

    selected_key = None
    selected = None
    for key, portfolio in portfolios.items():
        if key == args.portfolio or (isinstance(portfolio, dict) and portfolio.get("portfolio_name") == args.portfolio):
            selected_key = key
            selected = portfolio
            break
    if not isinstance(selected, dict):
        raise SystemExit(f"포트폴리오를 찾지 못했습니다: {args.portfolio}")

    holdings = selected.get("holdings") or []
    if not isinstance(holdings, list):
        raise SystemExit(f"{args.portfolio} holdings 구조가 배열이 아닙니다.")
    holding_rows = [item for item in holdings if isinstance(item, dict)]
    by_ticker = {holding_ticker(item): item for item in holding_rows}

    errors: list[str] = []
    if len(holding_rows) != len(holdings):
        errors.append("보유 종목 배열에 객체가 아닌 항목이 있습니다.")
    if len(holding_rows) < args.min_holdings:
        errors.append(f"보유 종목 수 부족: {len(holding_rows)}개 / 필요 {args.min_holdings}개")
    if selected.get("holding_count") not in (None, len(holding_rows)):
        errors.append(f"holding_count 불일치: {selected.get('holding_count')} / 실제 {len(holding_rows)}")

    portfolio_updated_age = age_hours(selected.get("updated_at"))
    if portfolio_updated_age is None or portfolio_updated_age > args.max_portfolio_age_hours:
        errors.append(f"포트폴리오 updated_at 오래됨/누락: {selected.get('updated_at')}")

    tickers = [holding_ticker(item) for item in holding_rows]
    duplicate_tickers = sorted({ticker for ticker in tickers if ticker and tickers.count(ticker) > 1})
    if duplicate_tickers:
        errors.append(f"중복 보유 종목: {', '.join(duplicate_tickers)}")

    cash_like = [item for item in holding_rows if holding_ticker(item) in {"CASH", "예수금"} or str(item.get("name") or "").strip().upper() in {"CASH", "예수금"}]
    if cash_like and not args.allow_cash:
        for item in cash_like:
            errors.append(f"예수금/CASH 항목 혼입: {item.get('name') or item.get('ticker')}")

    if args.forbid_zero:
        zero_items = [item for item in holding_rows if number(item.get("quantity")) == 0]
        for item in zero_items:
            errors.append(f"수량 0 종목 잔존: {item.get('name') or item.get('ticker')}")

    if args.require_price_fields:
        for item in holding_rows:
            ticker = holding_ticker(item)
            if not ticker:
                errors.append(f"티커 누락 보유 종목: {item.get('name')}")
                continue
            for field in ("name", "quantity", "average_cost", "current_price", "market_value", "cost_basis", "price_source", "price_checked_at", "currency"):
                if item.get(field) in (None, ""):
                    errors.append(f"{ticker} {field} 누락")
            checked_age = age_hours(item.get("price_checked_at"))
            if checked_age is None or checked_age > args.max_price_age_hours:
                errors.append(f"{ticker} 가격 확인 시각 오래됨/누락: {item.get('price_checked_at')}")
            currency = str(item.get("currency") or "").upper()
            sync_status = str(item.get("sync_status") or "")
            if currency != "KRW" and sync_status != "manual_or_overseas_protected":
                errors.append(f"{ticker} 해외/수동 수량 보호 상태 누락: {sync_status or '없음'}")
            if sync_status in {"manual", "manual_or_overseas_protected"}:
                sync_age = age_hours(item.get("sync_checked_at"))
                if sync_age is None or sync_age > args.max_sync_age_hours:
                    errors.append(f"{ticker} 수량 동기화 확인 시각 오래됨/누락: {item.get('sync_checked_at')}")

    market_sum = sum(number(item.get("market_value")) or 0 for item in holding_rows)
    stored_value = number(selected.get("portfolio_value"))
    if stored_value is not None and abs(stored_value - market_sum) > args.value_tolerance:
        errors.append(f"포트폴리오 총액 불일치: 저장 {stored_value:,.2f} / 합계 {market_sum:,.2f}")

    weight_sum = sum(number(item.get("weight")) or 0 for item in holding_rows)
    if holding_rows and abs(weight_sum - 1.0) > args.weight_tolerance:
        errors.append(f"포트폴리오 비중 합계 불일치: {weight_sum:.4f} / 기대 1.0")

    price_ages = [age_hours(item.get("price_checked_at")) for item in holding_rows]
    valid_price_ages = [value for value in price_ages if value is not None]
    newest_price = min(valid_price_ages) if valid_price_ages else None
    oldest_price = max(valid_price_ages) if valid_price_ages else None

    for ticker, (expected_qty, expected_currency) in parse_expected(args.expected).items():
        item = by_ticker.get(ticker)
        if not item:
            errors.append(f"기대 종목 누락: {ticker}")
            continue
        actual_qty = number(item.get("quantity"))
        if actual_qty != expected_qty:
            errors.append(f"{ticker} 수량 불일치: {actual_qty} / 기대 {expected_qty}")
        actual_currency = str(item.get("currency") or "").upper() or None
        if expected_currency and actual_currency != expected_currency:
            errors.append(f"{ticker} 통화 불일치: {actual_currency} / 기대 {expected_currency}")

    newest_price_label = f"{newest_price:.1f}" if newest_price is not None else "-"
    oldest_price_label = f"{oldest_price:.1f}" if oldest_price is not None else "-"
    print(f"저장 파일: {store}")
    print(f"포트폴리오: {selected.get('portfolio_name') or selected_key} | 보유 {len(holding_rows)}개 | 총액 {stored_value if stored_value is not None else '-'}")
    print(f"포트폴리오 갱신: {selected.get('updated_at') or '미확인'} | 비중 합계 {weight_sum:.4f} | 가격 확인 범위 {newest_price_label}~{oldest_price_label}시간")
    for ticker in parse_expected(args.expected):
        item = by_ticker.get(ticker)
        if item:
            print(f"{ticker} {item.get('name')} | 수량 {item.get('quantity')} | 통화 {item.get('currency')} | 동기화 {item.get('sync_status')}")

    if errors:
        for error in errors:
            print(f"오류: {error}")
        return 1
    print("포트폴리오 저장 수량 상태 정상")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
