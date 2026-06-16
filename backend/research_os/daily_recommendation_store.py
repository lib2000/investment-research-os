"""Storage and schedule helpers for daily recommendations."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from re import search
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from research_os.research_memory import resolve_vault_dir
from research_os.settings import Settings


def daily_recommendation_store_path(settings: Settings) -> Path:
    return resolve_vault_dir(settings.research_vault_dir) / "_system" / "daily_recommendations.json"


def daily_recommendation_state_path(settings: Settings) -> Path:
    return resolve_vault_dir(settings.research_vault_dir) / "_system" / "daily_recommendations_state.json"


def current_recommendation_datetime() -> datetime:
    try:
        korea_timezone = ZoneInfo("Asia/Seoul")
    except ZoneInfoNotFoundError:
        return datetime.now().replace(microsecond=0)
    return datetime.now(korea_timezone).replace(microsecond=0)


def parse_daily_recommendations_time(settings: Settings) -> tuple[int, int]:
    match = search(r"^(\d{1,2}):(\d{2})$", str(settings.daily_recommendations_time or "08:00").strip())
    if not match:
        return 8, 0
    hour = min(max(int(match.group(1)), 0), 23)
    minute = min(max(int(match.group(2)), 0), 59)
    return hour, minute


def should_run_daily_recommendations(settings: Settings, now: datetime | None = None) -> bool:
    if not settings.daily_recommendations_enabled:
        return False
    now = now or current_recommendation_datetime()
    hour, minute = parse_daily_recommendations_time(settings)
    if now.time() < now.replace(hour=hour, minute=minute, second=0, microsecond=0).time():
        return False
    state = read_json_payload(daily_recommendation_state_path(settings), {})
    return state.get("last_run_date") != now.date().isoformat()


def read_json_payload(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default
    return payload if isinstance(payload, dict) else default


def write_json_payload(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_daily_recommendation_store(settings: Settings) -> dict:
    return read_json_payload(
        daily_recommendation_store_path(settings),
        {
            "module": "daily_stock_recommendations",
            "records": [],
        },
    )


def write_daily_recommendation_store(settings: Settings, payload: dict) -> None:
    payload["module"] = "daily_stock_recommendations"
    write_json_payload(daily_recommendation_store_path(settings), payload)


def parse_date(value: object) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value or "").strip()[:10]
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def recommendation_record_id(recommendation_date: date, rank: int, ticker: str) -> str:
    return f"{recommendation_date.isoformat()}-{rank:02d}-{str(ticker or '').upper()}"
