"""Naver domestic market-close journal automation orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from re import search
from typing import Any, Callable

from research_os.models import MarketCloseReviewRequest, ResearchMemoryArchiveRequest
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
    clean_naver_research_text: Callable[[Any], str]
    resolve_vault_dir: Callable[[str], Path]
    read_manifest: Callable[[Path], list[dict]]
    is_archived_research_entry: Callable[[dict], bool]
    read_manifest_entry_payload: Callable[[dict | None, Path], dict]
    set_research_memory_archive_status: Callable[[str, str, ResearchMemoryArchiveRequest, Path], Any]
    provider_error_message: Callable[[Exception, Settings], str]
    repair_mojibake_log_line: Callable[[str], str]
    should_run_naver_market_close_journal_fn: Callable[[Settings], bool]


def naver_market_close_duplicate_key(
    runtime: NaverMarketCloseAutomationRuntime,
    entry: dict,
    payload: dict,
) -> tuple[str, str, str]:
    journal_entry = payload.get("entry") if isinstance(payload.get("entry"), dict) else {}
    source_processing = (
        payload.get("source_url_processing")
        if isinstance(payload.get("source_url_processing"), dict)
        else {}
    )
    market = runtime.clean_naver_research_text(
        journal_entry.get("market") or entry.get("market") or "KR"
    ).upper()
    session_date = runtime.clean_naver_research_text(
        journal_entry.get("session_date")
        or entry.get("session_date")
        or entry.get("date")
    )
    source_url = runtime.clean_naver_research_text(
        source_processing.get("url")
        or payload.get("source_url")
        or entry.get("source_url")
    )
    raw_summary = runtime.clean_naver_research_text(journal_entry.get("raw_summary") or "")
    first_summary_line = raw_summary.splitlines()[0] if raw_summary else ""
    source_title = runtime.clean_naver_research_text(
        source_processing.get("title")
        or payload.get("source_title")
        or first_summary_line
    )
    source_identity = source_url or source_title or runtime.clean_naver_research_text(entry.get("summary"))
    return market, session_date, source_identity


def naver_market_close_entry_sort_key(item: dict) -> tuple[str, str]:
    entry = item.get("entry") if isinstance(item.get("entry"), dict) else {}
    payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
    return (
        str(entry.get("created_at") or entry.get("updated_at") or payload.get("updated_at") or entry.get("date") or ""),
        str(entry.get("file_name") or ""),
    )


def archive_duplicate_naver_market_close_reports(
    runtime: NaverMarketCloseAutomationRuntime,
    settings: Settings,
    apply: bool = False,
) -> dict:
    vault_dir = runtime.resolve_vault_dir(settings.research_vault_dir)
    groups: dict[tuple[str, str, str], list[dict]] = {}
    skipped = 0
    for entry in runtime.read_manifest(vault_dir):
        if str(entry.get("type") or "") != "market-close-review":
            continue
        if runtime.is_archived_research_entry(entry):
            continue
        ticker = str(entry.get("ticker") or "")
        if ticker not in {"MARKET-KR", "MARKET"}:
            continue
        payload = runtime.read_manifest_entry_payload(entry, vault_dir)
        key = naver_market_close_duplicate_key(runtime, entry, payload)
        if not key[1] or not key[2]:
            skipped += 1
            continue
        groups.setdefault(key, []).append({"entry": entry, "payload": payload})

    duplicate_groups: list[dict] = []
    duplicate_candidates: list[dict] = []
    archived_files: list[dict] = []
    errors: list[dict] = []
    for key, items in groups.items():
        if len(items) <= 1:
            continue
        ordered = sorted(items, key=naver_market_close_entry_sort_key, reverse=True)
        keep = ordered[0]["entry"]
        candidates = [item["entry"] for item in ordered[1:]]
        duplicate_groups.append(
            {
                "market": key[0],
                "session_date": key[1],
                "source": key[2],
                "keep_file": keep.get("file_name"),
                "duplicate_count": len(candidates),
                "duplicates": [candidate.get("file_name") for candidate in candidates],
            }
        )
        duplicate_candidates.extend(candidates)

    if apply:
        reason = "네이버 국내 마감 시황 자동 반영 중복 후보라 삭제하지 않고 소프트 보관 처리했습니다."
        for candidate in duplicate_candidates:
            try:
                result = runtime.set_research_memory_archive_status(
                    str(candidate.get("ticker") or ""),
                    str(candidate.get("file_name") or ""),
                    ResearchMemoryArchiveRequest(archived=True, reason=reason),
                    vault_dir,
                )
                archived_files.append(
                    {
                        "file_name": result.file_name,
                        "relative_path": result.relative_path,
                        "archived_at": result.archived_at,
                    }
                )
            except Exception as exc:
                errors.append({"file_name": candidate.get("file_name"), "error": str(exc)})

    return {
        "status": "success" if not errors else "partial_success",
        "policy": "soft_archive",
        "applied": apply,
        "duplicate_group_count": len(duplicate_groups),
        "duplicate_candidate_count": len(duplicate_candidates),
        "archived_count": len(archived_files),
        "skipped_count": skipped,
        "groups": duplicate_groups,
        "archived_files": archived_files,
        "errors": errors,
    }


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