"""Telegram US market close journal automation orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from re import search
from typing import Any, Callable

from research_os.models import MarketCloseReviewRequest
from research_os.settings import Settings


@dataclass(frozen=True)
class TelegramMarketCloseAutomationRuntime:
    current_storage_date: Callable[[], Any]
    current_storage_timestamp: Callable[[], str]
    current_storage_datetime: Callable[[], datetime]
    read_json_store: Callable[[Path, Any], Any]
    write_json_store: Callable[[Path, Any], None]
    read_market_close_journal: Callable[[Settings], dict]
    save_market_close_review: Callable[[MarketCloseReviewRequest, Settings], Any]
    normalize_market_code: Callable[[str | None], str]
    provider_error_message: Callable[[Exception, Settings], str]
    repair_mojibake_log_line: Callable[[str], str]
    telegram_market_close_journal_state_path: Callable[[Settings], Path]
    telegram_market_close_journal_task_log_path: Callable[[Settings], Path]
    fetch_telegram_public_channel_posts: Callable[..., tuple[list[Any], list[str]]]
    fetch_telegram_public_channel_posts_backfill: Callable[..., tuple[list[Any], list[str]]]
    latest_telegram_us_market_close_candidate: Callable[..., Any | None]
    telegram_market_close_source_metadata: Callable[[str], dict]
    telegram_us_market_close_candidates: Callable[..., list[Any]]


def existing_market_close_session_dates(
    runtime: TelegramMarketCloseAutomationRuntime,
    settings: Settings,
    market: str,
) -> set[str]:
    normalized_market = runtime.normalize_market_code(market)
    payload = runtime.read_market_close_journal(settings)
    dates: set[str] = set()
    for item in payload.get("entries", []):
        if not isinstance(item, dict):
            continue
        if runtime.normalize_market_code(str(item.get("market") or "")) != normalized_market:
            continue
        session_date = str(item.get("session_date") or "").strip()
        if session_date:
            dates.add(session_date)
    return dates


def save_telegram_us_market_close_candidate(
    runtime: TelegramMarketCloseAutomationRuntime,
    candidate: Any,
    settings: Settings,
):
    source_metadata = runtime.telegram_market_close_source_metadata(candidate.source_title)
    request = MarketCloseReviewRequest(
        market="US",
        session_date=candidate.session_date,
        raw_summary=candidate.raw_summary,
        **source_metadata,
        save_result=True,
    )
    return runtime.save_market_close_review(request, settings)


def _skipped_response(state_path: Path, state: dict, candidate: Any, message: str) -> dict:
    return {
        "status": "skipped",
        "module": "telegram_market_close_journal",
        "message": message,
        "source": candidate.__dict__,
        "previous_state": state,
        "state_path": str(state_path),
    }


def refresh_telegram_us_market_close_journal(
    runtime: TelegramMarketCloseAutomationRuntime,
    settings: Settings,
    force: bool = False,
) -> dict:
    state_path = runtime.telegram_market_close_journal_state_path(settings)
    try:
        posts, warnings = runtime.fetch_telegram_public_channel_posts(
            channel_username=settings.telegram_market_close_channel_username,
            channel_url=settings.telegram_market_close_channel_url,
            timeout_seconds=settings.telegram_market_close_timeout_seconds,
            user_agent=settings.telegram_market_close_user_agent,
            max_posts=settings.telegram_market_close_max_posts,
        )
        candidate = runtime.latest_telegram_us_market_close_candidate(
            posts,
            today=runtime.current_storage_date(),
            max_summary_chars=settings.telegram_market_close_max_summary_chars,
        )
    except Exception as exc:
        state = {
            **runtime.read_json_store(state_path, {}),
            "status": "error",
            "last_attempt_at": runtime.current_storage_timestamp(),
            "last_attempt_date": runtime.current_storage_date().isoformat(),
            "last_attempt_message": runtime.provider_error_message(exc, settings),
        }
        runtime.write_json_store(state_path, state)
        return {
            "status": "error",
            "module": "telegram_market_close_journal",
            "message": state["last_attempt_message"],
            "state_path": str(state_path),
        }
    if not candidate:
        state = {
            **runtime.read_json_store(state_path, {}),
            "status": "not_found",
            "last_attempt_at": runtime.current_storage_timestamp(),
            "last_attempt_date": runtime.current_storage_date().isoformat(),
            "last_attempt_message": "텔레그램 @ehdwl 공개 채널에서 미국 시장일지 후보를 찾지 못했습니다.",
            "warnings": warnings,
        }
        runtime.write_json_store(state_path, state)
        return {
            "status": "not_found",
            "module": "telegram_market_close_journal",
            "message": state["last_attempt_message"],
            "warnings": warnings,
            "state_path": str(state_path),
        }
    previous_state = runtime.read_json_store(state_path, {})
    if (
        not force
        and previous_state.get("source_item_id") == candidate.source_item_id
        and previous_state.get("source_published_at") == candidate.source_published_at
        and previous_state.get("session_date") == candidate.session_date
    ):
        state = {
            **previous_state,
            "status": "skipped_duplicate",
            "last_attempt_at": runtime.current_storage_timestamp(),
            "last_attempt_date": runtime.current_storage_date().isoformat(),
            "last_attempt_message": "같은 텔레그램 미국 시장일지 원본이라 중복 저장하지 않았습니다.",
            "warnings": warnings,
        }
        runtime.write_json_store(state_path, state)
        return _skipped_response(state_path, state, candidate, "이미 같은 텔레그램 미국 시장일지를 반영했습니다.")
    if not force and candidate.session_date in existing_market_close_session_dates(runtime, settings, "US"):
        source_metadata = runtime.telegram_market_close_source_metadata(candidate.source_title)
        state = {
            **previous_state,
            "status": "skipped_duplicate",
            "last_attempt_at": runtime.current_storage_timestamp(),
            "last_attempt_date": runtime.current_storage_date().isoformat(),
            "last_attempt_message": "같은 미국 시장일지 날짜가 이미 있어 중복 저장하지 않았습니다.",
            "source_item_id": candidate.source_item_id,
            "source_url": candidate.source_url,
            "source_title": candidate.source_title,
            "source_origin": source_metadata["source_origin"],
            "source_provider": source_metadata["source_provider"],
            "source_published_at": candidate.source_published_at,
            "session_date": candidate.session_date,
            "included_post_count": candidate.included_post_count,
            "warnings": warnings,
        }
        runtime.write_json_store(state_path, state)
        return _skipped_response(state_path, state, candidate, "이미 같은 날짜의 텔레그램 미국 시장일지를 반영했습니다.")
    source_metadata = runtime.telegram_market_close_source_metadata(candidate.source_title)
    response = save_telegram_us_market_close_candidate(runtime, candidate, settings)
    run_at = runtime.current_storage_timestamp()
    run_date = runtime.current_storage_date().isoformat()
    state = {
        "status": "success",
        "last_run_at": run_at,
        "last_run_date": run_date,
        "last_attempt_at": run_at,
        "last_attempt_date": run_date,
        "last_attempt_message": "텔레그램 @ehdwl 미국 시장일지를 시장일지에 반영했습니다.",
        "source_item_id": candidate.source_item_id,
        "source_url": candidate.source_url,
        "source_title": candidate.source_title,
        "source_origin": source_metadata["source_origin"],
        "source_provider": source_metadata["source_provider"],
        "source_published_at": candidate.source_published_at,
        "session_date": candidate.session_date,
        "included_post_count": candidate.included_post_count,
        "market_journal_entry_id": response.entry.entry_id,
        "storage": response.storage.model_dump(mode="json") if response.storage else None,
        "warnings": warnings,
    }
    runtime.write_json_store(state_path, state)
    return {
        "status": "success",
        "module": "telegram_market_close_journal",
        "source": candidate.__dict__,
        "entry": response.entry.model_dump(mode="json"),
        "storage": response.storage.model_dump(mode="json") if response.storage else None,
        "warnings": warnings,
        "state_path": str(state_path),
    }


def backfill_telegram_us_market_close_journal(
    runtime: TelegramMarketCloseAutomationRuntime,
    settings: Settings,
    *,
    max_pages: int = 4,
    force: bool = False,
) -> dict:
    state_path = runtime.telegram_market_close_journal_state_path(settings)
    try:
        posts, warnings = runtime.fetch_telegram_public_channel_posts_backfill(
            channel_username=settings.telegram_market_close_channel_username,
            channel_url=settings.telegram_market_close_channel_url,
            timeout_seconds=settings.telegram_market_close_timeout_seconds,
            user_agent=settings.telegram_market_close_user_agent,
            max_pages=max_pages,
        )
        candidates = runtime.telegram_us_market_close_candidates(
            posts,
            today=runtime.current_storage_date(),
            max_summary_chars=settings.telegram_market_close_max_summary_chars,
        )
    except Exception as exc:
        state = {
            **runtime.read_json_store(state_path, {}),
            "status": "error",
            "last_attempt_at": runtime.current_storage_timestamp(),
            "last_attempt_date": runtime.current_storage_date().isoformat(),
            "last_attempt_message": runtime.provider_error_message(exc, settings),
        }
        runtime.write_json_store(state_path, state)
        return {
            "status": "error",
            "module": "telegram_market_close_journal_backfill",
            "message": state["last_attempt_message"],
            "state_path": str(state_path),
        }
    existing_dates = existing_market_close_session_dates(runtime, settings, "US")
    selected = [candidate for candidate in candidates if force or candidate.session_date not in existing_dates]
    selected.sort(key=lambda item: item.session_date)
    stored: list[dict] = []
    failed: list[dict] = []
    for candidate in selected:
        try:
            response = save_telegram_us_market_close_candidate(runtime, candidate, settings)
            stored.append(
                {
                    "session_date": candidate.session_date,
                    "source_item_id": candidate.source_item_id,
                    "source_url": candidate.source_url,
                    "source_title": candidate.source_title,
                    "source_published_at": candidate.source_published_at,
                    "entry_id": response.entry.entry_id,
                    "storage": response.storage.model_dump(mode="json") if response.storage else None,
                }
            )
            existing_dates.add(candidate.session_date)
        except Exception as exc:
            failed.append(
                {
                    "session_date": candidate.session_date,
                    "source_item_id": candidate.source_item_id,
                    "error": runtime.provider_error_message(exc, settings),
                }
            )
    run_at = runtime.current_storage_timestamp()
    run_date = runtime.current_storage_date().isoformat()
    stored_dates = {item["session_date"] for item in stored}
    failed_dates = {item["session_date"] for item in failed}
    skipped_existing = [
        {
            "session_date": candidate.session_date,
            "source_item_id": candidate.source_item_id,
            "source_url": candidate.source_url,
            "source_title": candidate.source_title,
            "source_published_at": candidate.source_published_at,
        }
        for candidate in candidates
        if candidate.session_date not in stored_dates and candidate.session_date not in failed_dates
    ]
    state = {
        **runtime.read_json_store(state_path, {}),
        "status": "success" if not failed else "error",
        "last_attempt_at": run_at,
        "last_attempt_date": run_date,
        "last_attempt_message": (
            f"텔레그램 @ehdwl 미국 시장일지 소급 저장 {len(stored)}건, 기존/스킵 {len(skipped_existing)}건, 실패 {len(failed)}건"
        ),
        "backfill_last_run_at": run_at,
        "backfill_candidate_count": len(candidates),
        "backfill_stored_count": len(stored),
        "backfill_skipped_existing_count": len(skipped_existing),
        "backfill_failed_count": len(failed),
        "backfill_stored": stored,
        "backfill_failed": failed,
        "backfill_skipped_existing": skipped_existing,
        "warnings": warnings,
    }
    if stored:
        latest_stored = stored[-1]
        state.update(
            {
                "last_run_at": run_at,
                "last_run_date": run_date,
                "source_item_id": latest_stored.get("source_item_id"),
                "source_url": latest_stored.get("source_url"),
                "source_title": latest_stored.get("source_title"),
                "source_origin": "telegram_auto",
                "source_provider": "telegram_ehdwl",
                "source_published_at": latest_stored.get("source_published_at"),
                "session_date": latest_stored.get("session_date"),
                "market_journal_entry_id": latest_stored.get("entry_id"),
                "storage": latest_stored.get("storage"),
            }
        )
    runtime.write_json_store(state_path, state)
    return {
        "status": "success" if not failed else "error",
        "module": "telegram_market_close_journal_backfill",
        "candidate_count": len(candidates),
        "stored_count": len(stored),
        "skipped_existing_count": len(skipped_existing),
        "failed_count": len(failed),
        "stored": stored,
        "skipped_existing": skipped_existing,
        "failed": failed,
        "warnings": warnings,
        "state_path": str(state_path),
    }


def parse_telegram_market_close_journal_time(settings: Settings) -> tuple[int, int]:
    match = search(r"^(\d{1,2}):(\d{2})$", str(settings.telegram_market_close_journal_time or "07:20").strip())
    if not match:
        return 7, 20
    hour = min(max(int(match.group(1)), 0), 23)
    minute = min(max(int(match.group(2)), 0), 59)
    return hour, minute


def should_run_telegram_us_market_close_journal(
    runtime: TelegramMarketCloseAutomationRuntime,
    settings: Settings,
    now: datetime | None = None,
) -> bool:
    if not settings.telegram_market_close_auto_journal:
        return False
    now = now or runtime.current_storage_datetime()
    hour, minute = parse_telegram_market_close_journal_time(settings)
    if now.time() < now.replace(hour=hour, minute=minute, second=0, microsecond=0).time():
        return False
    state = runtime.read_json_store(runtime.telegram_market_close_journal_state_path(settings), {})
    today = now.date().isoformat()
    return state.get("last_run_date") != today and state.get("last_attempt_date") != today


def read_telegram_market_close_task_log(
    runtime: TelegramMarketCloseAutomationRuntime,
    settings: Settings,
    limit: int = 20,
) -> dict:
    log_path = runtime.telegram_market_close_journal_task_log_path(settings)
    normalized_limit = min(max(int(limit or 20), 1), 100)
    if not log_path.exists():
        return {
            "exists": False,
            "path": str(log_path),
            "line_count": 0,
            "recent_lines": [],
            "last_line": "",
        }
    try:
        with log_path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            lines = [line.rstrip("\r\n") for line in handle if line.strip()]
    except Exception as exc:
        return {
            "exists": True,
            "path": str(log_path),
            "line_count": 0,
            "recent_lines": [],
            "last_line": "",
            "read_error": runtime.provider_error_message(exc, settings),
        }
    recent_lines = lines[-normalized_limit:]
    return {
        "exists": True,
        "path": str(log_path),
        "line_count": len(lines),
        "recent_lines": [runtime.repair_mojibake_log_line(line) for line in recent_lines],
        "last_line": runtime.repair_mojibake_log_line(recent_lines[-1]) if recent_lines else "",
    }


def build_telegram_market_close_task_status(
    runtime: TelegramMarketCloseAutomationRuntime,
    settings: Settings,
    log_limit: int = 20,
) -> dict:
    state = runtime.read_json_store(runtime.telegram_market_close_journal_state_path(settings), {})
    log = read_telegram_market_close_task_log(runtime, settings, limit=log_limit)
    enabled = bool(settings.telegram_market_close_auto_journal)
    if not enabled:
        next_action = "텔레그램 미국 시장일지 자동 반영이 비활성화되어 있습니다."
        status = "disabled"
    elif not log.get("exists") and not state:
        next_action = "작업 스케줄러 첫 실행 전입니다. 07:20 이후 로그가 생성되는지 확인하세요."
        status = "waiting_for_first_run"
    elif should_run_telegram_us_market_close_journal(runtime, settings):
        next_action = "오늘 텔레그램 미국 시장일지 자동 반영이 아직 실행되지 않았습니다."
        status = "due"
    elif state.get("status") == "skipped_duplicate":
        next_action = "오늘 자동 점검이 실행됐고 같은 원본은 중복 저장하지 않았습니다."
        status = "ok_duplicate_skipped"
    elif state.get("status") == "not_found":
        next_action = "오늘 자동 점검이 실행됐지만 신규 미국 시장일지 후보가 없어 저장하지 않았습니다."
        status = "ok_no_new_report"
    elif state.get("status") == "error":
        next_action = "텔레그램 공개 채널 확인 중 오류가 발생했습니다. 네트워크 또는 t.me 접근 상태를 확인하세요."
        status = "needs_attention"
    else:
        next_action = "최근 상태가 정상입니다. 같은 텔레그램 원본은 중복 저장하지 않습니다."
        status = "ok"
    return {
        "status": status,
        "module": "telegram_market_close_task_status",
        "enabled": enabled,
        "daily_time": settings.telegram_market_close_journal_time,
        "channel_username": settings.telegram_market_close_channel_username,
        "channel_url": settings.telegram_market_close_channel_url,
        "scheduled_task_name": "InvestmentResearchOS-TelegramUSMarketCloseJournal-0720",
        "due_now": should_run_telegram_us_market_close_journal(runtime, settings) if enabled else False,
        "state": state,
        "task_log": log,
        "next_action": next_action,
    }