"""Validate saved interest tickers/sectors without a running browser."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_STORE = Path("research_vault/_system/interest_list.json")
DEFAULT_REQUIRED_NAMES = "성호전자,RF머트리얼즈,LG디스플레이"


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (
            candidate / "research_vault"
        ).exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"관심종목 저장 파일을 찾지 못했습니다: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"관심종목 저장 파일 JSON 파싱 실패: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("관심종목 저장 파일 최상위 구조가 객체가 아닙니다.")
    return payload


def item_company_name(item: dict[str, Any]) -> str:
    verification = item.get("verification") if isinstance(item.get("verification"), dict) else {}
    return str(verification.get("company_name") or item.get("company_name") or item.get("name") or "").strip()


def item_ticker(item: dict[str, Any]) -> str:
    verification = item.get("verification") if isinstance(item.get("verification"), dict) else {}
    return str(verification.get("official_symbol") or item.get("ticker") or "").strip().upper()


def normalized(value: Any) -> str:
    return str(value or "").replace(" ", "").strip().lower()


def main() -> int:
    parser = argparse.ArgumentParser(description="관심종목/관심섹터 저장 품질을 점검합니다.")
    parser.add_argument("--store", type=Path, default=None, help="interest_list.json 경로")
    parser.add_argument("--min-tickers", type=int, default=1, help="최소 관심종목 수")
    parser.add_argument("--min-sectors", type=int, default=0, help="최소 관심섹터 수")
    parser.add_argument("--required-names", default=DEFAULT_REQUIRED_NAMES, help="쉼표로 구분한 필수 회사명")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    store = args.store if args.store else root / DEFAULT_STORE
    if not store.is_absolute():
        store = root / store
    payload = load_json(store)
    tickers = [item for item in payload.get("tickers", []) if isinstance(item, dict)]
    sectors = [item for item in payload.get("sectors", []) if isinstance(item, dict)]

    errors: list[str] = []
    if len(tickers) < args.min_tickers:
        errors.append(f"관심종목 수 부족: {len(tickers)}개 / 필요 {args.min_tickers}개")
    if len(sectors) < args.min_sectors:
        errors.append(f"관심섹터 수 부족: {len(sectors)}개 / 필요 {args.min_sectors}개")

    ticker_values = [item_ticker(item) for item in tickers]
    duplicate_tickers = sorted({ticker for ticker in ticker_values if ticker and ticker_values.count(ticker) > 1})
    if duplicate_tickers:
        errors.append(f"중복 관심종목 티커: {', '.join(duplicate_tickers)}")

    for item in tickers:
        ticker = item_ticker(item)
        company_name = item_company_name(item)
        verification = item.get("verification") if isinstance(item.get("verification"), dict) else {}
        if not ticker:
            errors.append(f"티커 누락 관심종목: {company_name or item}")
        if not company_name:
            errors.append(f"회사명 누락 관심종목: {ticker or item}")
        if verification and verification.get("verified") is not True:
            errors.append(f"인증 실패 관심종목: {ticker or item.get('ticker')} {company_name}")
        if not item.get("updated_at"):
            errors.append(f"updated_at 누락 관심종목: {ticker or company_name}")

    company_names = {normalized(item_company_name(item)) for item in tickers}
    required_names = [name.strip() for name in args.required_names.split(",") if name.strip()]
    missing_names = [name for name in required_names if normalized(name) not in company_names]
    if missing_names:
        errors.append(f"필수 관심종목 누락: {', '.join(missing_names)}")

    for item in sectors:
        name = str(item.get("name") or "").strip()
        if not name:
            errors.append("이름 누락 관심섹터가 있습니다.")
        if not str(item.get("region") or "").strip():
            errors.append(f"지역 누락 관심섹터: {name or item}")
        if not item.get("updated_at"):
            errors.append(f"updated_at 누락 관심섹터: {name or item}")

    print(f"저장 파일: {store}")
    print(f"관심종목: {len(tickers)}개 | 관심섹터: {len(sectors)}개")
    for item in tickers[:12]:
        print(f"- {item_company_name(item) or '회사명 미확인'} | {item_ticker(item) or '티커 미확인'} | {item.get('priority') or '우선순위 없음'}")
    if errors:
        for error in errors:
            print(f"오류: {error}")
        return 1
    print("관심종목/섹터 저장 품질 상태 정상")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
