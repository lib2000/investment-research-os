"""Validate portfolio holdings stored on disk without a running backend."""

from __future__ import annotations

import argparse
import json
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


def main() -> int:
    parser = argparse.ArgumentParser(description="포트폴리오 저장 파일의 수량 보호 상태를 점검합니다.")
    parser.add_argument("--store", type=Path, default=None, help="user_portfolios.json 경로")
    parser.add_argument("--portfolio", default="이형주", help="확인할 포트폴리오 이름 또는 키")
    parser.add_argument("--expected", default=DEFAULT_EXPECTED, help="예: PL=100:USD,253450=36:KRW")
    parser.add_argument("--min-holdings", type=int, default=1, help="최소 보유 종목 수")
    parser.add_argument("--forbid-zero", action="store_true", help="수량 0 종목이 있으면 실패")
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
    by_ticker = {str(item.get("ticker", "")).upper(): item for item in holdings if isinstance(item, dict)}

    errors: list[str] = []
    if len(holdings) < args.min_holdings:
        errors.append(f"보유 종목 수 부족: {len(holdings)}개 / 필요 {args.min_holdings}개")
    if args.forbid_zero:
        zero_items = [item for item in holdings if number(item.get("quantity")) == 0]
        for item in zero_items:
            errors.append(f"수량 0 종목 잔존: {item.get('name') or item.get('ticker')}")

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

    print(f"저장 파일: {store}")
    print(f"포트폴리오: {selected.get('portfolio_name') or selected_key} | 보유 {len(holdings)}개")
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
