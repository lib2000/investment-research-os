"""Naver domestic market-close journal automation orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from re import search
from typing import Any, Callable

from research_os.models import MarketCloseReviewRequest
from research_os.settings import Settings


@dataclass(frozen=True)
class NaverMarketCloseAutomationRuntime:
    current_storage_date: Callable[[], Any]
    current_storage_timestamp: Callable[[], str]
    current_storage_datetime: Callable[[], datetime]
    read_json_store: Callable[[Path, Any], Any]
    write_json_store: Callable[[Path, Any], None]
    refresh_naver_research_cache: Callable[..., dict]
    latest_naver_domestic_market_close_report: Callable[[Settings], dict | None]
    normalize_naver_research_date: Callable[[Any], str | None]
    naver_market_close_source_metadata: Callable[[str | None], dict]
    save_market_close_review: Callable[[MarketCloseReviewRequest, Settings], Any]
    naver_market_close_journal_state_path: Callable[[Settings], Path]
    naver_market_close_journal_task_log_path: Callable[[Settings], Path]
    archive_duplicate_naver_market_close_reports: Callable[..., dict]
    provider_error_message: Callable[[Exception, Settings], str]
    repair_mojibake_log_line: Callable[[str], str]
    should_run_naver_market_close_journal_fn: Callable[[Settings], bool]


def naver_market_close_report_summary(item: dict) -> str:
    pdf_analysis = item.get("pdf_analysis") if isinstance(item.get("pdf_analysis"), dict) else {}
    snippets = pdf_analysis.get("snippets") if isinstance(pdf_analysis.get("snippets"), list) else []
    lines = [
        "[네이버 금융 시황정보 자동 반영]",
        f"제목: {item.get('title') or '제목 미확인'}",
        f"증권사: {item.get('broker') or '미확인'}",
        f"발행일: {item.get('published_at') or '미확인'}",
        f"원문 링크: {item.get('url') or '미확인'}",
        f"PDF 링크: {item.get('pdf_url') or '미확인'}",
        f"PDF 분석 상태: {pdf_analysis.get('status') or '미확인'}",
        "",
        "활용 정책:",
        "- 네이버 금융 시황정보의 원문 전체는 저장하지 않고 메타데이터, 구조화 신호, 짧은 검증 스니펫만 시장일지에 반영합니다.",
        "- 이 시장일지는 보유/관심종목 리스크 스캔과 다음 장 체크포인트 생성에 활용합니다.",
    ]
    if snippets:
        lines.extend(["", "검증 스니펫:"])
        lines.extend(f"- {snippet}" for snippet in snippets[:5])
    return "\n".join(lines)


def refresh_naver_market_close_journal(
    runtime: NaverMarketCloseAutomationRuntime,
    settings: Settings,
    force: bool = False,
) -> dict:
    item = runtime.latest_naver_domestic_market_close_report(settings)
    if not item or force:
        runtime.refresh_naver_research_cache(settings, force=force, save_result=True)
        item = runtime.latest_naver_domestic_market_close_report(settings)
    state_path = runtime.naver_market_close_journal_state_path(settings)
    if not item:
        state = {
            **runtime.read_json_store(state_path, {}),
            "status": "not_found",
            "last_attempt_at": runtime.current_storage_timestamp(),
            "last_attempt_date": runtime.current_storage_date().isoformat(),
            "last_attempt_message": "네이버 시황정보에서 국내 마감 시황 리포트를 찾지 못했습니다.",
        }
        runtime.write_json_store(state_path, state)
        return {
            "status": "not_found",
            "module": "naver_market_close_journal",
            "message": "네이버 시황정보에서 국내 마감 시황 리포트를 찾지 못했습니다.",
            "state_path": str(state_path),
        }
    published_at = runtime.normalize_naver_research_date(item.get("published_at")) or runtime.current_storage_date().isoformat()
    previous_state = runtime.read_json_store(state_path, {})
    if (
        not force
        and previous_state.get("source_item_id") == item.get("item_id")
        and previous_state.get("source_published_at") == item.get("published_at")
    ):
        state = {
            **previous_state,
            "status": "skipped_duplicate",
            "last_attempt_at": runtime.current_storage_timestamp(),
            "last_attempt_date": runtime.current_storage_date().isoformat(),
            "last_attempt_message": "같은 네이버 국내 마감 시황 리포트라 중복 저장하지 않았습니다.",
        }
        runtime.write_json_store(state_path, state)
        return {
            "status": "skipped",
            "module": "naver_market_close_journal",
            "message": "이미 같은 네이버 국내 마감 시황 리포트를 시장일지에 반영했습니다.",
            "source": item,
            "previous_state": state,
            "state_path": str(state_path),
        }
    source_metadata = runtime.naver_market_close_source_metadata(item.get("title"))
    request = MarketCloseReviewRequest(
        market="KR",
        session_date=published_at,
        raw_summary=naver_market_close_report_summary(item),
        **source_metadata,
        save_result=True,
    )
    response = runtime.save_market_close_review(request, settings)
    run_at = runtime.current_storage_timestamp()
    run_date = runtime.current_storage_date().isoformat()
    state = {
        "status": "success",
        "last_run_at": run_at,
        "last_run_date": run_date,
        "last_attempt_at": run_at,
        "last_attempt_date": run_date,
        "last_attempt_message": "네이버 국내 마감 시황 리포트를 시장일지에 반영했습니다.",
        "source_item_id": item.get("item_id"),
        "source_title": item.get("title"),
        "source_origin": source_metadata["source_origin"],
        "source_provider": source_metadata["source_provider"],
        "source_published_at": item.get("published_at"),
        "market_journal_entry_id": response.entry.entry_id,
        "storage": response.storage.model_dump(mode="json") if response.storage else None,
    }
    runtime.write_json_store(state_path, state)
    return {
        "status": "success",
        "module": "naver_market_close_journal",
        "source": item,
        "entry": response.entry.model_dump(mode="json"),
        "storage": response.storage.model_dump(mode="json") if response.storage else None,
        "state_path": str(state_path),
    }


def parse_naver_market_close_journal_time(settings: Settings) -> tuple[int, int]:
    match = search(r"^(\d{1,2}):(\d{2})$", str(settings.naver_market_close_journal_time or "08:30").strip())
    if not match:
        return 8, 30
    hour = min(max(int(match.group(1)), 0), 23)
    minute = min(max(int(match.group(2)), 0), 59)
    return hour, minute


def should_run_naver_market_close_journal(
    runtime: NaverMarketCloseAutomationRuntime,
    settings: Settings,
    now: datetime | None = None,
) -> bool:
    if not settings.naver_market_close_auto_journal:
        return False
    now = now or runtime.current_storage_datetime()
    hour, minute = parse_naver_market_close_journal_time(settings)
    if now.time() < now.replace(hour=hour, minute=minute, second=0, microsecond=0).time():
        return False
    state = runtime.read_json_store(runtime.naver_market_close_journal_state_path(settings), {})
    today = now.date().isoformat()
    return state.get("last_run_date") != today and state.get("last_attempt_date") != today


def read_naver_market_close_task_log(
    runtime: NaverMarketCloseAutomationRuntime,
    settings: Settings,
    limit: int = 20,
) -> dict:
    log_path = runtime.naver_market_close_journal_task_log_path(settings)
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


def build_naver_market_close_task_status(
    runtime: NaverMarketCloseAutomationRuntime,
    settings: Settings,
    log_limit: int = 20,
) -> dict:
    state = runtime.read_json_store(runtime.naver_market_close_journal_state_path(settings), {})
    log = read_naver_market_close_task_log(runtime, settings, limit=log_limit)
    duplicate_archive = runtime.archive_duplicate_naver_market_close_reports(settings, apply=False)
    enabled = bool(settings.naver_market_close_auto_journal)
    if not enabled:
        next_action = "자동 반영이 비활성화되어 있습니다."
        status = "disabled"
    elif duplicate_archive.get("duplicate_candidate_count"):
        next_action = "중복 시장일지 후보가 있어 네이버 리서치 정리로 soft_archive 처리하세요."
        status = "needs_attention"
    elif not log.get("exists"):
        next_action = "작업 스케줄러 첫 실행 전입니다. 08:30 이후 로그가 생성되는지 확인하세요."
        status = "waiting_for_first_run"
    elif runtime.should_run_naver_market_close_journal_fn(settings):
        next_action = "오늘 자동 반영이 아직 실행되지 않았습니다. 스케줄러 또는 수동 반영을 확인하세요."
        status = "due"
    elif state.get("status") == "skipped_duplicate":
        next_action = "오늘 자동 점검이 실행됐고 같은 원본은 중복 저장하지 않았습니다."
        status = "ok_duplicate_skipped"
    elif state.get("status") == "not_found":
        next_action = "오늘 자동 점검이 실행됐지만 신규 국내 마감 시황 리포트가 없어 저장하지 않았습니다."
        status = "ok_no_new_report"
    else:
        next_action = "최근 상태가 정상입니다. 같은 원본은 중복 저장하지 않습니다."
        status = "ok"
    return {
        "status": status,
        "module": "naver_market_close_task_status",
        "enabled": enabled,
        "daily_time": settings.naver_market_close_journal_time,
        "scheduled_task_name": "InvestmentResearchOS-NaverMarketCloseJournal-0830",
        "due_now": runtime.should_run_naver_market_close_journal_fn(settings) if enabled else False,
        "state": state,
        "task_log": log,
        "duplicate_archive": duplicate_archive,
        "next_action": next_action,
    }