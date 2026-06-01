"""Validate investment calendar storage and earnings merge without a running backend."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (candidate / "research_vault").exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def load_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise SystemExit(f"JSON 파일을 찾지 못했습니다: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"JSON 파싱 실패: {path}: {exc}") from exc


def parse_dt(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
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


def add_issue(issues: list[str], condition: bool, message: str) -> None:
    if condition:
        issues.append(message)


def normalize_ticker(value: Any) -> str:
    return str(value or "").strip().upper()


def universe_from_system(system_dir: Path) -> dict[str, str]:
    universe: dict[str, str] = {}
    portfolios = load_json(system_dir / "user_portfolios.json", {"portfolios": {}}).get("portfolios") or {}
    if isinstance(portfolios, dict):
        for portfolio in portfolios.values():
            holdings = portfolio.get("holdings") if isinstance(portfolio, dict) else []
            if not isinstance(holdings, list):
                continue
            for holding in holdings:
                if not isinstance(holding, dict):
                    continue
                ticker = normalize_ticker(holding.get("ticker"))
                name = str(holding.get("name") or holding.get("company_name") or ticker).strip()
                if ticker:
                    universe.setdefault(ticker, name or ticker)
    interests = load_json(system_dir / "interest_list.json", {"tickers": []}).get("tickers") or []
    if isinstance(interests, list):
        for item in interests:
            if not isinstance(item, dict):
                continue
            ticker = normalize_ticker(item.get("ticker"))
            verification = item.get("verification") if isinstance(item.get("verification"), dict) else {}
            name = str(
                verification.get("company_name")
                or item.get("company_name")
                or item.get("name")
                or ticker
            ).strip()
            if ticker:
                universe.setdefault(ticker, name or ticker)
    return universe


def main() -> int:
    parser = argparse.ArgumentParser(description="투자 캘린더 저장 파일과 보유/관심종목 실적발표 병합 상태를 점검합니다.")
    parser.add_argument("--strict", action="store_true", help="경고가 있으면 실패 코드로 종료")
    parser.add_argument("--min-kr-events", type=int, default=1)
    parser.add_argument("--min-us-events", type=int, default=1)
    parser.add_argument("--min-earnings-events", type=int, default=1)
    parser.add_argument("--max-age-hours", type=float, default=24 * 45)
    args = parser.parse_args()

    root = project_root(Path.cwd())
    sys.path.insert(0, str(root / "backend"))
    from research_os.investment_calendar import (  # noqa: PLC0415
        build_investment_calendar_earnings_events,
        load_latest_calendar_file_payload,
        merge_investment_calendar_events,
    )

    vault_dir = root / "research_vault"
    system_dir = vault_dir / "_system"
    calendar_dir = vault_dir / "MARKET-CALENDAR"
    earnings_cache = load_json(system_dir / "earnings_calendar_cache.json", {"entries": {}})
    universe = universe_from_system(system_dir)
    issues: list[str] = []

    try:
        payload = load_latest_calendar_file_payload(calendar_dir, vault_dir)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    earnings = build_investment_calendar_earnings_events(payload, universe=universe, earnings_cache=earnings_cache)
    merge_investment_calendar_events(payload, earnings)

    calendar_month = str(payload.get("calendar_month") or "")
    monthly = payload.get("monthly") if isinstance(payload.get("monthly"), dict) else {}
    weekly = payload.get("weekly") if isinstance(payload.get("weekly"), dict) else {}
    kr_events = monthly.get("KR") if isinstance(monthly.get("KR"), list) else []
    us_events = monthly.get("US") if isinstance(monthly.get("US"), list) else []
    all_events = [event for rows in monthly.values() if isinstance(rows, list) for event in rows if isinstance(event, dict)]
    earnings_events = [event for event in all_events if event.get("event_type") == "earnings" or event.get("category") == "실적발표"]
    source_age = age_hours(payload.get("updated_at"))

    add_issue(issues, payload.get("status") != "ok", f"투자 캘린더 상태 확인 필요: {payload.get('status') or '미확인'}")
    add_issue(issues, not calendar_month, "calendar_month 누락")
    add_issue(issues, source_age is None or source_age > args.max_age_hours, "투자 캘린더 최신성 확인 필요")
    add_issue(issues, len(weekly) < 1, "주간 캘린더 버킷 누락")
    add_issue(issues, len(kr_events) < args.min_kr_events, f"한국 시장 일정 부족: {len(kr_events)}개")
    add_issue(issues, len(us_events) < args.min_us_events, f"미국 시장 일정 부족: {len(us_events)}개")
    add_issue(issues, len(earnings_events) < args.min_earnings_events, f"실적발표 일정 부족: {len(earnings_events)}개")
    add_issue(
        issues,
        any("실적발표" not in str(event.get("title") or "") for event in earnings_events),
        "실적발표 이벤트 제목 표기 누락",
    )
    add_issue(
        issues,
        any(not event.get("related") for event in earnings_events),
        "실적발표 이벤트 관련 종목 누락",
    )
    add_issue(issues, not universe, "보유/관심종목 유니버스가 비어 있음")

    print(f"투자 캘린더 파일: {payload.get('source_file')}")
    print(f"캘린더 월: {calendar_month} | 갱신 {payload.get('updated_at')} | 유니버스 {len(universe)}개")
    print(f"시장 일정: 한국 {len(kr_events)}개 | 미국 {len(us_events)}개 | 주간 버킷 {len(weekly)}개")
    print(f"실적발표: {len(earnings_events)}개")
    for event in earnings_events[:5]:
        related = event.get("related") if isinstance(event.get("related"), list) else []
        print(f"- {event.get('date')} {event.get('market')} {event.get('title')} | {' · '.join(str(x) for x in related)}")

    if issues:
        for issue in issues:
            print(f"주의: {issue}")
        if args.strict:
            return 1
    else:
        print("투자 캘린더 저장/실적발표 상태 정상")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
