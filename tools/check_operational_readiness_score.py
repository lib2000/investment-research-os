"""Backend-free operational readiness score for the Investment Research OS."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

BODY_TAGS = {"needs_body_copy", "url_text_unavailable"}
OCR_MARKERS = {"ocr_needed", "ocr_required", "ocr_unavailable", "needs_ocr"}


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (candidate / "research_vault").exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def kst_now() -> datetime:
    return datetime.now(ZoneInfo("Asia/Seoul"))


def parse_iso_date(value: Any) -> datetime.date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.strip()[:10]).date()
    except ValueError:
        return None


def parse_hhmm(value: str, default: time) -> time:
    try:
        hour, minute = [int(part) for part in str(value).split(":", 1)]
        return time(hour=hour, minute=minute)
    except (TypeError, ValueError):
        return default


def signal(signal_id: str, label: str, score: float, message: str, next_action: str) -> dict[str, Any]:
    bounded = max(0.0, min(100.0, float(score)))
    status = "ok" if bounded >= 95.0 else "warning" if bounded >= 70.0 else "error"
    return {
        "id": signal_id,
        "label": label,
        "status": status,
        "score": round(bounded, 1),
        "message": message,
        "next_action": next_action,
    }


def graph_signal(system_dir: Path) -> dict[str, Any]:
    graph = load_json(system_dir / "code_knowledge_graph.json", {})
    flows = graph.get("flows") if isinstance(graph.get("flows"), list) else []
    needing = [flow for flow in flows if flow.get("status") != "ok"]
    score = 0.0 if not flows else (len(flows) - len(needing)) / len(flows) * 100.0
    return signal(
        "code_graph_flow_integrity",
        "운영 흐름 연결",
        score,
        f"운영 흐름 {len(flows) - len(needing)}/{len(flows)}개 정상",
        "python tools\\check_code_knowledge_graph.py --strict",
    )


def recommendation_signal(system_dir: Path, daily_time: str) -> dict[str, Any]:
    state = load_json(system_dir / "daily_recommendations_state.json", {})
    selected = state.get("selected_count")
    selected_count = selected if isinstance(selected, int) else len(state.get("selected") or [])
    now = kst_now()
    expected = {now.date().isoformat()}
    if now.time() < parse_hhmm(daily_time, time(hour=8)):
        expected.add((now.date() - timedelta(days=1)).isoformat())
    last_run = str(state.get("last_run_date") or state.get("last_run_at") or "")
    date_ok = last_run[:10] in expected
    expected_count = 6
    score = (50.0 if date_ok else 0.0) + min(selected_count, expected_count) / expected_count * 50.0
    return signal(
        "daily_recommendations_latest",
        "오늘 한국/미국 추천 1~3위",
        score,
        f"선택 {selected_count}개, 마지막 실행 {last_run or '미확인'}",
        "python tools\\check_daily_recommendations_store.py --require-milestones --require-quality --expected-latest-count 6 --max-latest-age-days 1",
    )


def tags_from(item: dict[str, Any]) -> set[str]:
    captured = item.get("captured_item") if isinstance(item.get("captured_item"), dict) else {}
    tags = captured.get("tags") or item.get("tags") or []
    return {str(tag) for tag in tags} if isinstance(tags, list) else set()


def is_body_supplemented(item: dict[str, Any]) -> bool:
    quality = item.get("capture_quality") if isinstance(item.get("capture_quality"), dict) else {}
    return bool(quality.get("body_supplemented") or item.get("body_supplemented_at") or item.get("body_supplements"))


def is_active(item: dict[str, Any]) -> bool:
    return bool(item.get("storage") or item.get("rag_document"))


def recommendation_citations_signal(root: Path, system_dir: Path) -> dict[str, Any]:
    store = load_json(system_dir / "daily_recommendations.json", {"records": []})
    records = store.get("records") if isinstance(store.get("records"), list) else []
    if not records:
        return signal(
            "daily_recommendation_citations",
            "추천 근거 문서 연결",
            0.0,
            "추천 기록 없음",
            "python tools\\check_daily_recommendation_citations.py --strict",
        )
    usable = 0
    for record in records:
        rows = record.get("evidence_documents") if isinstance(record, dict) else []
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            relative = str(row.get("source_relative_path") or "").strip()
            if relative and (root / relative).exists():
                usable += 1
                break
    score = usable / len(records) * 100.0
    return signal(
        "daily_recommendation_citations",
        "추천 근거 문서 연결",
        score,
        f"추천 기록 {len(records)}개 중 근거 문서 연결 {usable}개",
        "python tools\\check_daily_recommendation_citations.py --strict",
    )


def latest_recommendation_payload(system_dir: Path) -> dict[str, Any]:
    store = load_json(system_dir / "daily_recommendations.json", {"records": []})
    records = store.get("records") if isinstance(store.get("records"), list) else []
    dated_records = [record for record in records if isinstance(record, dict) and record.get("recommendation_date")]
    if not dated_records:
        return {"latest_records": [], "latest_recommendation_date": ""}
    latest_date = max(str(record.get("recommendation_date") or "") for record in dated_records)
    latest_records = [record for record in dated_records if str(record.get("recommendation_date") or "") == latest_date]
    return {
        "latest_recommendation_date": latest_date,
        "latest_records": latest_records,
    }


def recommendation_policy_signal(system_dir: Path) -> dict[str, Any]:
    backend_dir = system_dir.parents[1] / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    from research_os.daily_recommendation_policy import build_policy_signal_quality_dashboard

    payload = latest_recommendation_payload(system_dir)
    dashboard = build_policy_signal_quality_dashboard(payload)
    record_count = int(dashboard.get("record_count") or 0)
    review_count = int(dashboard.get("review_count") or 0)
    score_applied_count = int(dashboard.get("score_applied_count") or 0)
    level_counts = dashboard.get("level_counts") if isinstance(dashboard.get("level_counts"), dict) else {}
    direct_count = int(level_counts.get("direct") or 0)
    theme_count = int(level_counts.get("theme") or 0)
    market_count = int(level_counts.get("market") or 0)
    if not record_count:
        score = 0.0
        message = "최신 추천 기록 없음"
    elif score_applied_count == 0 and review_count == 0:
        score = 100.0
        message = f"직접 매칭 없음, 테마/시장 신호는 참고 처리, 추천 {record_count}개"
    else:
        score = 95.0 if review_count else 100.0
        message = (
            f"추천 {record_count}개, 점수 반영 {score_applied_count}개, 검토 {review_count}개, "
            f"직접 {direct_count} / 테마 {theme_count} / 시장 {market_count}"
        )
    return signal(
        "daily_recommendation_policy_signals",
        "추천 정책 신호 품질",
        score,
        message,
        "python tools\\check_daily_recommendation_policy_signals.py --strict",
    )


def storage_signal(vault_dir: Path) -> dict[str, Any]:
    body_missing = 0
    ocr_needed = 0
    inspected_count = 0
    for path in vault_dir.glob("*/*.json"):
        item = load_json(path, {})
        if not isinstance(item, dict):
            continue
        inspected_count += 1
        active = is_active(item)
        tags = tags_from(item)
        text = json.dumps(item, ensure_ascii=False).lower()
        if active and (tags & BODY_TAGS or "needs_body_copy" in text or "url_text_unavailable" in text) and not is_body_supplemented(item):
            body_missing += 1
        if active and (tags & OCR_MARKERS or any(marker in text for marker in OCR_MARKERS)):
            ocr_needed += 1
    issues = body_missing + ocr_needed
    score = max(0.0, 100.0 - issues * 20.0)
    return signal(
        "storage_quality_open_issues",
        "저장/RAG 품질",
        score,
        f"검사 JSON {inspected_count}개, 활성 본문 보강 {body_missing}개, 활성 OCR 보강 {ocr_needed}개",
        "python tools\\check_storage_quality_store.py --strict",
    )



def rag_diagnostics_signal(vault_dir: Path) -> dict[str, Any]:
    manifest = load_json(vault_dir / "manifest.json", [])
    active: list[dict[str, Any]] = []
    if isinstance(manifest, list):
        for entry in manifest:
            if not isinstance(entry, dict):
                continue
            tags = {str(tag).lower() for tag in entry.get("tags", [])} if isinstance(entry.get("tags"), list) else set()
            archived = bool(entry.get("archived") or entry.get("status") == "archived" or "archived" in tags)
            research_entry = bool(
                entry.get("type") == "research-capture"
                or entry.get("module") == "research_quick_capture"
                or entry.get("rag_document")
                or entry.get("storage")
            )
            if research_entry and not archived:
                active.append(entry)

    db_path = vault_dir / "_system" / "research_memory.sqlite3"
    rag_paths: set[str] = set()
    if db_path.exists():
        try:
            with sqlite3.connect(db_path) as connection:
                rows = connection.execute("SELECT source_relative_path FROM research_memory_documents").fetchall()
            rag_paths = {str(row[0] or "") for row in rows}
        except sqlite3.Error:
            rag_paths = set()

    linked = sum(1 for entry in active if str(entry.get("relative_path") or "") in rag_paths)
    score = 0.0 if not active else linked / len(active) * 100.0
    return signal(
        "rag_failure_diagnostics",
        "저장/RAG 실패 진단",
        score,
        f"활성 리서치 {len(active)}개, RAG 연결 {linked}개",
        r"python tools\check_rag_failure_diagnostics.py --strict",
    )

def source_signal(system_dir: Path) -> dict[str, Any]:
    state = load_json(system_dir / "research_automation_status.json", {})
    failures = int(state.get("failed_count") or state.get("failure_count") or 0)
    duplicate = state.get("last_deduped_dossier_refresh") if isinstance(state.get("last_deduped_dossier_refresh"), dict) else {}
    duplicate_failures = int(duplicate.get("failed_count") or 0)
    score = max(0.0, 100.0 - (failures + duplicate_failures) * 25.0)
    return signal(
        "source_automation_failures",
        "외부 소스 자동화",
        score,
        f"최근 실패 {failures}개, Dossier 실패 {duplicate_failures}개",
        "python tools\\check_research_source_store.py --strict",
    )


def investment_calendar_signal(vault_dir: Path) -> dict[str, Any]:
    calendar_dir = vault_dir / "MARKET-CALENDAR"
    candidates = sorted(
        calendar_dir.glob("MARKET-CALENDAR-investment-calendar-*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return signal(
            "investment_calendar_store",
            "투자 캘린더/실적 일정",
            0.0,
            "생성된 투자 캘린더 없음",
            "python tools\\check_investment_calendar_store.py --strict",
        )
    latest = candidates[0]
    payload = load_json(latest, {})
    monthly = payload.get("monthly") if isinstance(payload.get("monthly"), dict) else {}
    kr_events = monthly.get("KR") if isinstance(monthly.get("KR"), list) else []
    us_events = monthly.get("US") if isinstance(monthly.get("US"), list) else []
    weekly = payload.get("weekly") if isinstance(payload.get("weekly"), dict) else {}
    earnings_cache = load_json(vault_dir / "_system" / "earnings_calendar_cache.json", {"entries": {}})
    entries = earnings_cache.get("entries") if isinstance(earnings_cache.get("entries"), dict) else {}
    month = str(payload.get("calendar_month") or "")
    earnings_candidates = 0
    future_earnings_candidates = 0
    today = kst_now().date()
    if month:
        for entry in entries.values():
            if not isinstance(entry, dict):
                continue
            if str(entry.get("next_earnings_date") or "").startswith(month):
                earnings_candidates += 1
            next_date = parse_iso_date(entry.get("next_earnings_date"))
            counted_future = bool(next_date and next_date >= today)
            if counted_future:
                future_earnings_candidates += 1
                continue
            for event in entry.get("events") or []:
                if not isinstance(event, dict):
                    continue
                if str(event.get("date") or "").startswith(month):
                    earnings_candidates += 1
                event_date = parse_iso_date(event.get("date"))
                if event_date and event_date >= today and not counted_future:
                    future_earnings_candidates += 1
                    counted_future = True
                if counted_future:
                    break
    score = 0.0
    # Generated calendar JSON files may omit status; successful loading plus a valid month is enough.
    if month and payload.get("status", "ok") == "ok":
        score += 30.0
    if kr_events:
        score += 20.0
    if us_events:
        score += 20.0
    if weekly:
        score += 10.0
    if earnings_candidates or future_earnings_candidates:
        score += 20.0
    return signal(
        "investment_calendar_store",
        "투자 캘린더/실적 일정",
        score,
        (
            f"{month or '월 미확인'}, 한국 {len(kr_events)}개, 미국 {len(us_events)}개, "
            f"실적 후보 {earnings_candidates}개, 향후 실적 후보 {future_earnings_candidates}개"
        ),
        "python tools\\check_investment_calendar_store.py --strict",
    )


def portfolio_signal(system_dir: Path) -> dict[str, Any]:
    payload = load_json(system_dir / "user_portfolios.json", {"portfolios": {}})
    portfolios = payload.get("portfolios") if isinstance(payload.get("portfolios"), dict) else {}
    holdings_count = 0
    protected_count = 0
    for portfolio in portfolios.values():
        holdings = portfolio.get("holdings") if isinstance(portfolio, dict) else []
        if not isinstance(holdings, list):
            continue
        holdings_count += len(holdings)
        protected_count += sum(
            1
            for item in holdings
            if str(item.get("sync_status") or item.get("sync_state") or "").lower() == "manual_or_overseas_protected"
        )
    score = 100.0 if holdings_count else 30.0
    return signal(
        "portfolio_quantity_guard",
        "포트폴리오 실시간/수량 보호",
        score,
        f"포트폴리오 {len(portfolios)}개, 보유 {holdings_count}개, 수동/해외 보호 {protected_count}개",
        "python tools\\check_portfolio_store.py --portfolio 이형주 --expected-holdings-count 17 --forbid-zero",
    )


def nps_allocation_signal(root: Path, system_dir: Path, *, enforce: bool) -> dict[str, Any]:
    backend_dir = root / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    from research_os.nps_allocation_monitor import (
        build_nps_domestic_equity_monitor_from_saved_portfolios,
        select_saved_portfolios_for_nps_allocation,
    )

    payload = load_json(system_dir / "user_portfolios.json", {"portfolios": {}})
    portfolios = payload.get("portfolios") if isinstance(payload.get("portfolios"), dict) else {}
    selected_name, selected = select_saved_portfolios_for_nps_allocation(portfolios, "__all__")
    if not selected:
        return signal(
            "nps_domestic_equity_allocation",
            "국민연금 국내주식 14%",
            0.0 if enforce else 100.0,
            "저장 포트폴리오 없음",
            "포트폴리오를 저장한 뒤 python tools\\check_nps_domestic_equity_allocation.py --portfolio-name __all__",
        )
    monitor = build_nps_domestic_equity_monitor_from_saved_portfolios(
        selected,
        portfolio_name=selected_name,
        checked_at=kst_now().isoformat(timespec="seconds"),
    )
    breached = monitor.get("status") in {"above_target", "below_target", "needs_data"}
    score = 75.0 if enforce and breached else 100.0
    guard_label = (
        "비중 이탈 감시 중"
        if breached and not enforce
        else "비중 이탈"
        if breached
        else "허용 범위"
    )
    return signal(
        "nps_domestic_equity_allocation",
        "국민연금 국내주식 14%",
        score,
        (
            f"{guard_label}: {monitor.get('portfolio_name')} 현재 {float(monitor.get('current_domestic_equity_weight') or 0) * 100:.2f}% "
            f"/ 목표 {float(monitor.get('target_domestic_equity_weight') or 0) * 100:.1f}% "
            f"/ 상태 {monitor.get('status')} / 조치 {monitor.get('recommended_action')} "
            "/ 경보 모드: --fail-on-breach 또는 readiness --enforce-nps-allocation"
        ),
        "python tools\\check_nps_domestic_equity_allocation.py --portfolio-name __all__ --rebalance-plan",
    )


def investment_insight_hub_signal(root: Path) -> dict[str, Any]:
    tools_dir = root / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    from check_investment_insight_hub import build_dashboard, strict_errors

    payload = build_dashboard(root, portfolio_name="__all__", days=7, limit=12)
    readiness = payload.get("readiness") if isinstance(payload.get("readiness"), dict) else {}
    coverage = payload.get("coverage") if isinstance(payload.get("coverage"), dict) else {}
    errors = strict_errors(payload, min_insights=4, min_coverage_score=100.0)
    score = 100.0 if not errors else max(0.0, float(readiness.get("coverage_score") or 0.0) - len(errors) * 10.0)
    return signal(
        "investment_insight_hub",
        "시장·공시·법령·뉴스·심리 통합",
        score,
        (
            f"시장 데이터 {int(coverage.get('market_data_items') or 0)}, "
            f"시장일지·심리 {int(coverage.get('market_journal_items') or 0)}, "
            f"공시 {int(coverage.get('official_filing_items') or 0)}, "
            f"뉴스 {int(coverage.get('news_items') or 0)}, "
            f"정책·법령 {int(coverage.get('policy_law_items') or 0)}, "
            f"인사이트 {int(readiness.get('insight_count') or 0)}"
        ),
        "python tools\\check_investment_insight_hub.py --strict",
    )


def local_ai_survival_signal(root: Path) -> dict[str, Any]:
    backend_dir = root / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    from research_os.local_ai_survival import build_local_ai_survival_status
    from research_os.settings import Settings

    payload = build_local_ai_survival_status(Settings(research_vault_dir=str(root / "research_vault")))
    critical_count = int(payload.get("critical_check_count") or 0)
    critical_ready = int(payload.get("critical_ready_count") or 0)
    score = 0.0 if not critical_count else critical_ready / critical_count * 100.0
    return signal(
        "local_ai_survival_mode",
        "로컬 AI 생존 모드",
        score,
        (
            f"핵심 {critical_ready}/{critical_count} ready, "
            f"외부 고급 AI 의존도 {payload.get('retail_advanced_ai_dependency') or 'optional'}"
        ),
        "python tools\\check_local_ai_survival.py --json --strict",
    )


def agent_operating_foundation_signal(root: Path) -> dict[str, Any]:
    backend_dir = root / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    from research_os.agent_operating_foundation import build_agent_operating_foundation_status
    from research_os.settings import Settings

    payload = build_agent_operating_foundation_status(Settings(research_vault_dir=str(root / "research_vault")))
    return signal(
        "agent_operating_foundation",
        "에이전트 운영 기반",
        float(payload.get("score") or 0.0),
        (
            f"점수 {payload.get('score')}, "
            f"핵심 {payload.get('critical_ready_count')}/{payload.get('critical_check_count')} ready"
        ),
        "python tools\\check_agent_operating_foundation.py --json --strict",
    )


def openclaw_bridge_signal(root: Path) -> dict[str, Any]:
    tools_dir = root / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    from check_openclaw_investment_context import DEFAULT_OPENCLAW_DIR, DEFAULT_SOURCE_DIR, validate_bundle

    try:
        source_messages = validate_bundle(DEFAULT_SOURCE_DIR, max_age_hours=24.0)
        openclaw_messages = validate_bundle(DEFAULT_OPENCLAW_DIR, max_age_hours=24.0)
    except AssertionError as exc:
        return signal(
            "openclaw_investment_bridge",
            "OpenClaw 투자리서치 브리지",
            0.0,
            f"검증 실패: {exc}",
            "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\sync_openclaw_investment_context.ps1",
        )
    message = " / ".join((source_messages + openclaw_messages)[:2])
    return signal(
        "openclaw_investment_bridge",
        "OpenClaw 투자리서치 브리지",
        100.0,
        message or "source/openclaw 번들 검증 정상",
        "python tools\\check_openclaw_investment_context.py --max-age-hours 24",
    )


def openclaw_completion_signal(root: Path) -> dict[str, Any]:
    tools_dir = root / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    from check_openclaw_bridge_completion import build_result as build_openclaw_completion_result

    result = build_openclaw_completion_result(
        project_root=root,
        max_age_hours=24.0,
        require_report_hashes=True,
    )
    if result.get("status") != "ok":
        errors = result.get("errors") or []
        message = "; ".join(str(error) for error in errors[:3]) or "완료 감사 실패"
        return signal(
            "openclaw_completion_audit",
            "OpenClaw 완료 감사",
            0.0,
            message,
            "python tools\\check_openclaw_bridge_completion.py --max-age-hours 24 --require-report-hashes",
        )
    git_state = result.get("git") or {}
    bridge_status = result.get("bridge_status") or {}
    return signal(
        "openclaw_completion_audit",
        "OpenClaw 완료 감사",
        100.0,
        f"{git_state.get('branch')} {git_state.get('commit')} synced / bridge {bridge_status.get('context_generated_at')}",
        "python tools\\check_openclaw_bridge_completion.py --max-age-hours 24 --require-report-hashes",
    )


def openclaw_status_summary_signal(root: Path) -> dict[str, Any]:
    tools_dir = root / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    from show_openclaw_bridge_status import build_status_summary

    summary = build_status_summary()
    if summary.get("status") != "ok":
        errors = summary.get("errors") or []
        message = "; ".join(str(error) for error in errors[:3]) or "상태 요약 실패"
        return signal(
            "openclaw_status_summary",
            "OpenClaw 상태 요약",
            0.0,
            message,
            "python tools\\show_openclaw_bridge_status.py --json",
        )
    source_git = summary.get("source_git") or {}
    first_read = summary.get("first_read") or {}
    hash_status = summary.get("hash_status") or "unknown"
    hash_checked_count = summary.get("hash_checked_count")
    return signal(
        "openclaw_status_summary",
        "OpenClaw 상태 요약",
        100.0,
        (
            f"{source_git.get('branch')} {source_git.get('commit')} / "
            f"age {summary.get('context_age_hours')}h / latest {summary.get('latest_recommendation_date')} / "
            f"first-read rows {first_read.get('latest_recommendation_count')} / hashes {hash_status}/{hash_checked_count}"
        ),
        "python tools\\show_openclaw_bridge_status.py --json",
    )


def openclaw_answer_capture_canary_signal(root: Path) -> dict[str, Any]:
    tools_dir = root / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    from check_openclaw_answer_capture_canary import DEFAULT_OPENCLAW_DIR, build_result as build_canary_result

    try:
        result = build_canary_result(DEFAULT_OPENCLAW_DIR)
    except (AssertionError, OSError, ValueError, json.JSONDecodeError) as exc:
        return signal(
            "openclaw_answer_capture_canary",
            "OpenClaw 답변 캡처 canary",
            0.0,
            f"카나리 실패: {exc}",
            "python tools\\check_openclaw_answer_capture_canary.py --json",
        )
    if result.get("status") != "ok":
        errors = result.get("errors") or []
        message = "; ".join(str(error) for error in errors[:3]) or "카나리 실패"
        return signal(
            "openclaw_answer_capture_canary",
            "OpenClaw 답변 캡처 canary",
            0.0,
            message,
            "python tools\\check_openclaw_answer_capture_canary.py --json",
        )
    return signal(
        "openclaw_answer_capture_canary",
        "OpenClaw 답변 캡처 canary",
        100.0,
        (
            f"route {result.get('route_id')} / processed {len(result.get('processed_files') or [])} / "
            f"answers {len(result.get('answer_files') or [])} / live pollution false"
        ),
        "python tools\\check_openclaw_answer_capture_canary.py --json",
    )


def build_result(
    root: Path,
    *,
    min_score: float,
    daily_time: str,
    enforce_nps_allocation: bool,
) -> dict[str, Any]:
    vault_dir = root / "research_vault"
    system_dir = vault_dir / "_system"
    signals = [
        graph_signal(system_dir),
        recommendation_signal(system_dir, daily_time),
        recommendation_citations_signal(root, system_dir),
        recommendation_policy_signal(system_dir),
        storage_signal(vault_dir),
        rag_diagnostics_signal(vault_dir),
        source_signal(system_dir),
        investment_calendar_signal(vault_dir),
        portfolio_signal(system_dir),
        nps_allocation_signal(root, system_dir, enforce=enforce_nps_allocation),
        investment_insight_hub_signal(root),
        local_ai_survival_signal(root),
        agent_operating_foundation_signal(root),
        openclaw_bridge_signal(root),
        openclaw_completion_signal(root),
        openclaw_status_summary_signal(root),
        openclaw_answer_capture_canary_signal(root),
    ]
    score = round(sum(item["score"] for item in signals) / len(signals), 1) if signals else 0.0
    warnings = [item for item in signals if item["status"] != "ok"]
    return {
        "status": "ok" if score >= min_score and not warnings else "warning",
        "project_root": str(root),
        "score": score,
        "min_score": float(min_score),
        "signals": signals,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="운영 완성도 95% 기준을 백엔드 없이 점검합니다.")
    parser.add_argument("--min-score", type=float, default=95.0)
    parser.add_argument("--daily-time", default="08:00")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true", help="운영 완성도 결과를 JSON으로 출력합니다.")
    parser.add_argument(
        "--enforce-nps-allocation",
        action="store_true",
        help="국민연금 국내주식 14%% 허용 범위 이탈을 운영 점검 실패로 처리합니다.",
    )
    args = parser.parse_args()

    root = project_root(Path.cwd())
    result = build_result(
        root,
        min_score=args.min_score,
        daily_time=args.daily_time,
        enforce_nps_allocation=args.enforce_nps_allocation,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if args.strict and result["status"] != "ok" else 0

    signals = result["signals"]
    score = float(result["score"])
    warnings = result["warnings"]

    print(f"프로젝트 루트: {root}")
    print(f"운영 완성도 점수: {score:.1f}% / 목표 {args.min_score:.1f}%")
    for item in signals:
        status = "정상" if item["status"] == "ok" else "주의" if item["status"] == "warning" else "오류"
        print(f"- {item['label']}: {status} {item['score']:.1f}% | {item['message']}")
    if warnings:
        print("보강 필요 항목:")
        for item in warnings:
            print(f"  - {item['label']}: {item['next_action']}")
    if args.strict and (score < args.min_score or warnings):
        print("운영 완성도 점검 실패")
        return 1
    print("운영 완성도 점검 정상")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
