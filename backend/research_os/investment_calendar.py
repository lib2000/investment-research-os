"""Helpers for investment calendar payloads used by the research console."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from re import fullmatch
from zoneinfo import ZoneInfo


def calendar_week_name_for_date(value: str) -> str:
    """Return a Korean week bucket label such as 1주 for an ISO date string."""
    try:
        parsed = datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return "기타"
    return f"{((parsed.day - 1) // 7) + 1}주"


def build_investment_calendar_earnings_events(
    payload: dict,
    *,
    universe: dict[str, str],
    earnings_cache: dict,
) -> list[dict]:
    """Build holding/watchlist earnings events for the visible calendar month."""
    calendar_month = str(payload.get("calendar_month") or "")
    if not fullmatch(r"\d{4}-\d{2}", calendar_month) or not universe:
        return []
    entries = earnings_cache.get("entries") if isinstance(earnings_cache.get("entries"), dict) else {}
    events: list[dict] = []
    for ticker, company_name in universe.items():
        entry = entries.get(ticker) if isinstance(entries, dict) else None
        if not isinstance(entry, dict):
            continue
        candidate_events = [
            event
            for event in entry.get("events") or []
            if isinstance(event, dict) and str(event.get("date") or "").startswith(calendar_month)
        ]
        next_date = str(entry.get("next_earnings_date") or "")[:10]
        if next_date.startswith(calendar_month) and not any(
            str(event.get("date") or "")[:10] == next_date for event in candidate_events
        ):
            candidate_events.append({"date": next_date, "symbol": ticker})
        for event in candidate_events:
            event_date = str(event.get("date") or "")[:10]
            if not event_date:
                continue
            source = str(entry.get("source") or "실적 캘린더 캐시")
            title = f"{company_name} 실적발표"
            time_label = str(event.get("time") or "").strip()
            if time_label:
                title = f"{title}({time_label})"
            details = []
            if event.get("eps_estimated") not in (None, ""):
                details.append(f"예상 EPS {event.get('eps_estimated')}")
            if event.get("revenue_estimated") not in (None, ""):
                details.append(f"예상 매출 {event.get('revenue_estimated')}")
            events.append(
                {
                    "date": event_date,
                    "week": calendar_week_name_for_date(event_date),
                    "market": "KR" if str(ticker).isdigit() else "US",
                    "category": "실적발표",
                    "title": title,
                    "impact": "보유/관심 종목 실적 발표 전후 가이던스, 매출, 마진, 주가 반응을 점검",
                    "related": [company_name],
                    "action": "발표 전 컨센서스와 발표 후 가격 반응을 저장 데이터와 추천 추적에 반영",
                    "source": source,
                    "ticker": ticker,
                    "event_type": "earnings",
                    "details": details,
                }
            )
    return events


def merge_investment_calendar_events(payload: dict, extra_events: list[dict]) -> dict:
    """Merge generated events into monthly and weekly calendar buckets."""
    if not extra_events:
        payload["earnings_event_count"] = 0
        return payload
    monthly = payload.setdefault("monthly", {})
    weekly = payload.setdefault("weekly", {})
    seen = {
        (str(event.get("date") or ""), str(event.get("market") or ""), str(event.get("title") or ""))
        for market_events in monthly.values()
        if isinstance(market_events, list)
        for event in market_events
        if isinstance(event, dict)
    }
    inserted = 0
    for event in extra_events:
        key = (str(event.get("date") or ""), str(event.get("market") or ""), str(event.get("title") or ""))
        if key in seen:
            continue
        seen.add(key)
        market = str(event.get("market") or "KR")
        week = str(event.get("week") or calendar_week_name_for_date(str(event.get("date") or "")))
        monthly.setdefault(market, []).append(event)
        weekly.setdefault(week, {}).setdefault(market, []).append(event)
        inserted += 1
    for events in monthly.values():
        if isinstance(events, list):
            events.sort(
                key=lambda item: (
                    str(item.get("date") or ""),
                    str(item.get("category") or ""),
                    str(item.get("title") or ""),
                )
            )
    for markets in weekly.values():
        if not isinstance(markets, dict):
            continue
        for events in markets.values():
            if isinstance(events, list):
                events.sort(
                    key=lambda item: (
                        str(item.get("date") or ""),
                        str(item.get("category") or ""),
                        str(item.get("title") or ""),
                    )
                )
    payload["earnings_event_count"] = inserted
    return payload


def load_latest_calendar_file_payload(calendar_dir: Path, vault_dir: Path) -> dict:
    """Read the newest generated investment calendar JSON from the vault."""
    candidates = sorted(
        calendar_dir.glob("MARKET-CALENDAR-investment-calendar-*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return {
            "module": "investment_calendar",
            "status": "missing",
            "message": "생성된 투자 캘린더가 없습니다. 먼저 월간 투자 캘린더 자료를 생성하세요.",
            "calendar_month": None,
            "weekly": {},
            "monthly": {"KR": [], "US": []},
        }
    latest_path = candidates[0]
    try:
        payload = json.loads(latest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"투자 캘린더 JSON을 읽지 못했습니다: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("투자 캘린더 JSON 형식이 올바르지 않습니다.")
    payload.setdefault("module", "investment_calendar")
    payload.setdefault("status", "ok")
    payload["source_file"] = str(latest_path.relative_to(vault_dir))
    payload["updated_at"] = datetime.fromtimestamp(latest_path.stat().st_mtime, ZoneInfo("Asia/Seoul")).isoformat()
    return payload
