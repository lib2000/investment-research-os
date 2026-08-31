"""Summarize backend-managed investment research schedules without running them."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.daily_recommendations import daily_recommendation_status_payload  # noqa: E402
from research_os.daily_family_top_pick import (  # noqa: E402
    parse_daily_family_top_pick_time,
    read_daily_family_top_pick_card,
)
from research_os.dossier_text import content_fingerprint  # noqa: E402
from research_os.settings import Settings  # noqa: E402
from research_os.state_store import (  # noqa: E402
    current_storage_date,
    current_storage_datetime,
    current_storage_timestamp,
    market_close_journal_path,
    news_inbox_path,
    read_json_store,
    user_state_dir,
    write_json_store,
)
from research_os.telegram_favorite_posts import (  # noqa: E402
    TelegramFavoritePostsRuntime,
    build_telegram_favorite_posts_task_status,
)
from research_os.telegram_market_close_automation import (  # noqa: E402
    TelegramMarketCloseAutomationRuntime,
    build_telegram_market_close_task_status,
)
from research_os.telegram_market_journal import telegram_market_close_source_metadata  # noqa: E402


DESIGN_NAME = "operational_schedule_status_v1"


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _market_group_count(value: Any) -> int:
    if isinstance(value, dict):
        return sum(len(items or []) for items in value.values())
    if isinstance(value, list):
        total = 0
        for item in value:
            if isinstance(item, dict):
                if isinstance(item.get("count"), int):
                    total += int(item["count"])
                elif isinstance(item.get("records"), list):
                    total += len(item["records"])
        return total
    return 0


def _normalize_market_code(value: str | None) -> str:
    text = str(value or "").strip().upper()
    if text in {"US", "USA", "미국"}:
        return "US"
    return "KR"


def _state_path(settings: Settings, filename: str) -> Path:
    return user_state_dir(settings) / filename


def _read_market_close_journal(settings: Settings) -> dict:
    return read_json_store(market_close_journal_path(settings), {"entries": []})


def _provider_error_message(exc: Exception, _settings: Settings) -> str:
    return _compact_text(exc)


def _not_available_fetch(*_args: Any, **_kwargs: Any) -> tuple[list[Any], list[str]]:
    return [], ["schedule status check does not fetch network sources"]


def _not_available_candidate(*_args: Any, **_kwargs: Any) -> Any | None:
    return None


def _not_available_candidates(*_args: Any, **_kwargs: Any) -> list[Any]:
    return []


def _not_available_save(*_args: Any, **_kwargs: Any) -> Any:
    raise RuntimeError("schedule status check does not save market journal entries")


def telegram_market_close_runtime() -> TelegramMarketCloseAutomationRuntime:
    return TelegramMarketCloseAutomationRuntime(
        current_storage_date=current_storage_date,
        current_storage_timestamp=current_storage_timestamp,
        current_storage_datetime=current_storage_datetime,
        read_json_store=read_json_store,
        write_json_store=write_json_store,
        read_market_close_journal=_read_market_close_journal,
        save_market_close_review=_not_available_save,
        normalize_market_code=_normalize_market_code,
        provider_error_message=_provider_error_message,
        repair_mojibake_log_line=lambda value: str(value or ""),
        telegram_market_close_journal_state_path=lambda settings: _state_path(
            settings, "telegram_market_close_journal_state.json"
        ),
        telegram_market_close_journal_task_log_path=lambda settings: _state_path(
            settings, "telegram_market_close_journal_task.log"
        ),
        fetch_telegram_public_channel_posts=_not_available_fetch,
        fetch_telegram_public_channel_posts_backfill=_not_available_fetch,
        latest_telegram_us_market_close_candidate=_not_available_candidate,
        telegram_market_close_source_metadata=telegram_market_close_source_metadata,
        telegram_us_market_close_candidates=_not_available_candidates,
    )


def telegram_favorite_posts_runtime() -> TelegramFavoritePostsRuntime:
    return TelegramFavoritePostsRuntime(
        current_storage_date=current_storage_date,
        current_storage_timestamp=current_storage_timestamp,
        current_storage_datetime=current_storage_datetime,
        read_json_store=read_json_store,
        write_json_store=write_json_store,
        read_news_inbox=lambda settings: read_json_store(news_inbox_path(settings), {"items": []}),
        write_news_inbox=lambda settings, payload: write_json_store(news_inbox_path(settings), payload),
        content_fingerprint=content_fingerprint,
        provider_error_message=_provider_error_message,
        telegram_favorite_posts_state_path=lambda settings: _state_path(
            settings, "telegram_favorite_posts_state.json"
        ),
        fetch_telegram_public_channel_posts=_not_available_fetch,
    )


def build_daily_recommendation_schedule(settings: Settings) -> dict[str, Any]:
    status = daily_recommendation_status_payload(settings, today=current_storage_date().isoformat())
    daily_time = status.get("daily_time") or settings.daily_recommendations_time
    market_groups = status.get("today_market_groups") or {}
    today_count = _market_group_count(market_groups)
    has_today = bool(status.get("has_today_recommendations"))
    if not status.get("enabled"):
        schedule_status = "disabled"
        next_action = f"DAILY_RECOMMENDATIONS_ENABLED=true 설정 후 {daily_time} 자동 추천을 켜세요."
    elif status.get("due_now") and not has_today:
        schedule_status = "due"
        next_action = f"오늘 추천 저장이 아직 없어 {daily_time} 이후 재분석이 필요합니다."
    elif has_today and today_count >= 6:
        schedule_status = "ok"
        next_action = "오늘 한국/미국 추천 1~3위가 저장되어 있습니다."
    elif has_today:
        schedule_status = "needs_attention"
        next_action = "오늘 추천은 있으나 한국/미국 3개씩 구성이 맞는지 확인하세요."
    else:
        schedule_status = "waiting"
        next_action = f"{daily_time} 전 대기 상태입니다."
    return {
        "id": "daily_recommendations",
        "time": daily_time,
        "task": "한국/미국 오늘 추천 1~3위 생성/저장",
        "status": schedule_status,
        "enabled": bool(status.get("enabled")),
        "scheduler": "backend_daily_gate",
        "due_now": bool(status.get("due_now")),
        "command": "python tools\\check_daily_recommendations_store.py --require-milestones --require-quality",
        "today_count": today_count,
        "latest_recommendation_date": status.get("latest_recommendation_date"),
        "has_today_recommendations": has_today,
        "next_action": next_action,
    }


def build_daily_family_top_pick_schedule(settings: Settings) -> dict[str, Any]:
    """Report the local 07:10 card gate without generating a card."""
    now = current_storage_datetime()
    card_payload = read_daily_family_top_pick_card(settings)
    schedule = card_payload.get("schedule") if isinstance(card_payload.get("schedule"), dict) else {}
    hour, minute = parse_daily_family_top_pick_time(settings)
    scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    last_run_date = str(schedule.get("last_scheduled_run_date") or "")
    is_current = bool(card_payload.get("is_current"))
    has_card = isinstance(card_payload.get("card"), dict)
    if not settings.daily_recommendations_enabled:
        status = "disabled"
        next_action = "일일 추천이 비활성화되어 가족 한 종목 카드도 생성하지 않습니다."
    elif last_run_date == now.date().isoformat() and has_card and is_current:
        status = "ok"
        next_action = "오늘 카드가 07:00 추천 결과와 연결되어 저장되었습니다."
    elif now >= scheduled:
        status = "due"
        next_action = "오늘 카드가 아직 생성되지 않았습니다. 07:00 추천 상태를 먼저 확인하세요."
    else:
        status = "waiting"
        next_action = f"{settings.daily_family_top_pick_time} 카드 생성 대기 상태입니다."
    return {
        "id": "daily_family_top_pick_card",
        "time": settings.daily_family_top_pick_time,
        "task": "가족 전체 보유·관심종목 한 종목 리서치 카드 생성",
        "status": status,
        "enabled": bool(settings.daily_recommendations_enabled),
        "scheduler": "backend_daily_gate",
        "due_now": now >= scheduled and last_run_date != now.date().isoformat(),
        "command": "GET /api/v1/daily-top-pick",
        "latest_recommendation_date": card_payload.get("recommendation_date"),
        "last_scheduled_run_at": schedule.get("last_scheduled_run_at"),
        "last_scheduled_status": schedule.get("last_scheduled_status"),
        "next_action": next_action,
    }


def build_market_close_schedule(settings: Settings) -> dict[str, Any]:
    status = build_telegram_market_close_task_status(telegram_market_close_runtime(), settings)
    return {
        "id": "telegram_us_market_close_journal",
        "time": status.get("daily_time") or settings.telegram_market_close_journal_time,
        "task": "미국 시장 일지 자동 반영",
        "status": status.get("status"),
        "enabled": bool(status.get("enabled")),
        "scheduler": "backend_daily_gate",
        "due_now": bool(status.get("due_now")),
        "command": "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\run_telegram_us_market_close_journal.ps1",
        "state_status": (status.get("state") or {}).get("status"),
        "last_run_date": (status.get("state") or {}).get("last_run_date"),
        "last_attempt_date": (status.get("state") or {}).get("last_attempt_date"),
        "log_exists": bool((status.get("task_log") or {}).get("exists")),
        "next_action": status.get("next_action"),
    }


def build_favorite_posts_schedule(settings: Settings) -> dict[str, Any]:
    status = build_telegram_favorite_posts_task_status(telegram_favorite_posts_runtime(), settings)
    return {
        "id": "telegram_favorite_posts",
        "time": status.get("daily_time") or settings.telegram_favorite_posts_time,
        "task": "텔레그램 즐겨찾기 채널 인기글 수집 및 뉴스/심리 반영",
        "status": status.get("status"),
        "enabled": bool(status.get("enabled")),
        "scheduler": "backend_daily_gate",
        "due_now": bool(status.get("due_now")),
        "command": "python tools\\check_telegram_favorite_posts.py --use-env --config-only --json",
        "configured_channel_count": status.get("configured_channel_count"),
        "state_status": (status.get("state") or {}).get("status"),
        "last_run_date": (status.get("state") or {}).get("last_run_date"),
        "last_attempt_date": (status.get("state") or {}).get("last_attempt_date"),
        "warnings": status.get("warnings") or [],
        "next_action": status.get("next_action"),
    }


def build_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    checks = [
        build_market_close_schedule(settings),
        build_daily_recommendation_schedule(settings),
        build_daily_family_top_pick_schedule(settings),
        build_favorite_posts_schedule(settings),
    ]
    errors: list[str] = []
    warnings: list[str] = []
    for check in checks:
        if check.get("status") in {"needs_attention", "needs_configuration"}:
            errors.append(f"{check.get('id')}: {check.get('next_action')}")
        elif check.get("status") in {"disabled", "due", "waiting_for_first_run", "waiting"}:
            warnings.append(f"{check.get('id')}: {check.get('next_action')}")
    return {
        "module": "operational_schedule_status",
        "design": DESIGN_NAME,
        "status": "error" if errors else "ok",
        "generated_at": current_storage_timestamp(),
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
    }


def render_text(result: dict[str, Any]) -> str:
    lines = [f"[{result.get('status')}] {DESIGN_NAME}", f"- generated_at: {result.get('generated_at')}"]
    for check in result.get("checks") or []:
        lines.append(
            "- {time} {task}: {status} / enabled={enabled} / scheduler={scheduler}".format(
                time=check.get("time"),
                task=check.get("task"),
                status=check.get("status"),
                enabled=check.get("enabled"),
                scheduler=check.get("scheduler"),
            )
        )
        lines.append(f"  next_action: {check.get('next_action')}")
    for warning in result.get("warnings") or []:
        lines.append(f"- warning: {warning}")
    for error in result.get("errors") or []:
        lines.append(f"- error: {error}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check backend-managed operational schedule status.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--allow-warnings", action="store_true")
    args = parser.parse_args()

    result = build_status()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))
    if result["status"] != "ok":
        return 1
    if result.get("warnings") and not args.allow_warnings:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
