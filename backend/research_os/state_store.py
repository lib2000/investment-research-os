"""Shared state-store paths and JSON helpers for Investment Research OS."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from research_os.research_memory import resolve_vault_dir
from research_os.settings import Settings


def _korea_timezone():
    try:
        return ZoneInfo("Asia/Seoul")
    except ZoneInfoNotFoundError:
        return timezone(timedelta(hours=9))


def current_storage_datetime() -> datetime:
    return datetime.now(_korea_timezone())


def current_storage_date() -> date:
    return current_storage_datetime().date()


def current_storage_timestamp() -> str:
    return current_storage_datetime().isoformat(timespec="seconds")


def user_state_dir(settings: Settings) -> Path:
    state_dir = resolve_vault_dir(settings.research_vault_dir) / "_system"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def portfolio_store_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "user_portfolios.json"


def interest_list_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "interest_list.json"


def market_close_journal_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "market_close_journal.json"


def latest_daily_brief_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "latest_daily_brief.json"


def news_inbox_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "news_inbox.json"


def kcif_reports_watch_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "kcif_reports_watch.json"


def regional_business_sources_watch_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "regional_business_sources_watch.json"


def company_ir_sources_watch_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "company_ir_sources_watch.json"


def research_automation_status_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "research_automation_status.json"


def storage_duplicate_review_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "storage_duplicate_review.json"


def dossier_refresh_queue_status_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "dossier_refresh_queue_status.json"


def backend_health_alert_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "backend_health_alerts.jsonl"


def read_json_store(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default
    return payload if isinstance(payload, dict) else default


def write_json_store(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False))
        file.write("\n")
