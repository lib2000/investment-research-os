"""Code knowledge graph API helpers and operational signal summaries."""

from __future__ import annotations

import json
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from research_os.daily_recommendations import daily_recommendation_state_path
from research_os.research_memory import resolve_vault_dir
from research_os.settings import Settings



BODY_TAGS = {"needs_body_copy", "url_text_unavailable"}
OCR_MARKERS = {"ocr_needed", "ocr_required", "ocr_unavailable", "needs_ocr"}


def _tags_from(item: dict[str, Any]) -> set[str]:
    captured = item.get("captured_item") if isinstance(item.get("captured_item"), dict) else {}
    tags = captured.get("tags") or item.get("tags") or []
    if not isinstance(tags, list):
        return set()
    return {str(tag) for tag in tags}


def _is_body_supplemented(item: dict[str, Any]) -> bool:
    quality = item.get("capture_quality") if isinstance(item.get("capture_quality"), dict) else {}
    supplements = item.get("body_supplements") or []
    return bool(quality.get("body_supplemented") or item.get("body_supplemented_at") or supplements)


def _is_indexed_or_stored(item: dict[str, Any]) -> bool:
    return bool(item.get("storage") or item.get("rag_document"))


def _iter_vault_json(vault_dir: Path):
    for path in vault_dir.glob("*/*.json"):
        payload = read_json_file(path, {})
        if payload:
            yield path, payload

def read_json_file(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default.copy()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default.copy()
    return payload if isinstance(payload, dict) else default.copy()


def code_knowledge_graph_path(settings: Settings) -> Path:
    return resolve_vault_dir(settings.research_vault_dir) / "_system" / "code_knowledge_graph.json"


def _signal(
    *,
    signal_id: str,
    label: str,
    status: str,
    message: str,
    flow_id: str,
    next_action: str | None = None,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": signal_id,
        "label": label,
        "status": status,
        "message": message,
        "flow_id": flow_id,
        "next_action": next_action or "",
        "detail": detail or {},
    }


def _kst_now() -> datetime:
    try:
        return datetime.now(ZoneInfo("Asia/Seoul"))
    except ZoneInfoNotFoundError:
        return datetime.now().astimezone()


def _parse_hhmm(value: str | None, default: time) -> time:
    if not value:
        return default
    try:
        hour, minute = [int(part) for part in str(value).split(":", 1)]
        return time(hour=hour, minute=minute)
    except (TypeError, ValueError):
        return default


def _recommendation_expected_dates(settings: Settings) -> set[str]:
    now = _kst_now()
    expected = {now.date().isoformat()}
    if now.time() < _parse_hhmm(settings.daily_recommendations_time, time(hour=9)):
        expected.add((now.date() - timedelta(days=1)).isoformat())
    return expected


def _recommendation_signal(settings: Settings) -> dict[str, Any]:
    state = read_json_file(daily_recommendation_state_path(settings), {})
    selected_count_value = state.get("selected_count")
    selected_count = selected_count_value if isinstance(selected_count_value, int) else len(state.get("selected") or [])
    last_run_date = str(state.get("last_run_date") or state.get("last_run_at") or "")
    expected_dates = _recommendation_expected_dates(settings)
    ok = selected_count == 3 and last_run_date[:10] in expected_dates
    return _signal(
        signal_id="daily_recommendations_latest",
        label="오늘 추천 최신성",
        status="ok" if ok else "warning",
        message=(
            f"추천 3개가 준비되어 있습니다. 마지막 실행: {last_run_date or '확인 안 됨'}"
            if ok
            else f"추천 최신성 확인 필요: 선택 {selected_count}개, 마지막 실행 {last_run_date or '확인 안 됨'}"
        ),
        flow_id="daily_recommendations",
        next_action="python tools\\check_daily_recommendations_store.py --require-milestones --require-quality --expected-latest-count 3 --max-latest-age-days 1",
        detail={"selected_count": selected_count, "last_run_date": last_run_date, "expected_dates": sorted(expected_dates)},
    )


def _storage_quality_signal(settings: Settings) -> dict[str, Any]:
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    body_missing: list[str] = []
    ocr_needed: list[str] = []
    advisory_body: list[str] = []
    active_count = 0
    for path, item in _iter_vault_json(vault_dir):
        tags = _tags_from(item)
        text = json.dumps(item, ensure_ascii=False).lower()
        has_body_issue = bool(tags & BODY_TAGS) or "needs_body_copy" in text or "url_text_unavailable" in text
        has_ocr_issue = bool(tags & OCR_MARKERS) or any(marker in text for marker in OCR_MARKERS)
        active = _is_indexed_or_stored(item)
        if active:
            active_count += 1
        rel = path.relative_to(vault_dir).as_posix()
        if has_body_issue and not _is_body_supplemented(item):
            if active:
                body_missing.append(rel)
            else:
                advisory_body.append(rel)
        if has_ocr_issue and active:
            ocr_needed.append(rel)
    issue_count = len(body_missing) + len(ocr_needed)
    return _signal(
        signal_id="storage_quality_open_issues",
        label="저장 자료 품질",
        status="ok" if issue_count == 0 else "warning",
        message=(
            "활성 저장자료의 본문/OCR 보강 필요 항목이 없습니다."
            if issue_count == 0
            else f"본문 보강 {len(body_missing)}개, OCR 보강 {len(ocr_needed)}개를 확인하세요."
        ),
        flow_id="research_storage_rag",
        next_action="python tools\\check_storage_quality_store.py --strict",
        detail={
            "active_count": active_count,
            "body_missing_count": len(body_missing),
            "ocr_needed_count": len(ocr_needed),
            "advisory_body_count": len(advisory_body),
            "sample_body_missing": body_missing[:5],
            "sample_ocr_needed": ocr_needed[:5],
        },
    )


def _source_automation_signal(settings: Settings) -> dict[str, Any]:
    state_dir = resolve_vault_dir(settings.research_vault_dir) / "_system"
    automation = read_json_file(state_dir / "research_automation_status.json", {})
    failures = int(automation.get("failed_count") or automation.get("failure_count") or 0)
    duplicate = automation.get("last_deduped_dossier_refresh") or {}
    duplicate_failures = int(duplicate.get("failed_count") or 0) if isinstance(duplicate, dict) else 0
    status = str(automation.get("status") or "").lower()
    ok = failures == 0 and duplicate_failures == 0 and status not in {"error", "failed"}
    return _signal(
        signal_id="source_automation_failures",
        label="소스 자동화 실패",
        status="ok" if ok else "warning",
        message=(
            "외부 리포트/소스 자동화의 최근 실패가 없습니다."
            if ok
            else f"소스 자동화 실패 확인 필요: 실패 {failures}개, Dossier 실패 {duplicate_failures}개"
        ),
        flow_id="source_automation",
        next_action="python tools\\check_research_source_store.py --strict",
        detail={"status": status or "unknown", "failed_count": failures, "dossier_failed_count": duplicate_failures},
    )


def _portfolio_signal(settings: Settings) -> dict[str, Any]:
    state_dir = resolve_vault_dir(settings.research_vault_dir) / "_system"
    payload = read_json_file(state_dir / "user_portfolios.json", {"portfolios": {}})
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
    ok = holdings_count > 0
    return _signal(
        signal_id="portfolio_quantity_guard",
        label="포트폴리오 수량 보호",
        status="ok" if ok else "warning",
        message=(
            f"저장 포트폴리오 {len(portfolios)}개, 보유 {holdings_count}개, 수동/해외 보호 {protected_count}개를 확인했습니다."
            if ok
            else "저장 포트폴리오를 찾지 못했습니다."
        ),
        flow_id="portfolio_realtime",
        next_action="python tools\\check_portfolio_store.py --portfolio 이형주 --expected-holdings-count 17 --forbid-zero",
        detail={"portfolio_count": len(portfolios), "holdings_count": holdings_count, "protected_count": protected_count},
    )


def _graph_flow_signal(flows: list[dict[str, Any]]) -> dict[str, Any]:
    needing = [flow for flow in flows if flow.get("status") != "ok"]
    return _signal(
        signal_id="code_graph_flow_integrity",
        label="운영 흐름 연결",
        status="ok" if not needing else "warning",
        message=(
            f"운영 흐름 {len(flows)}/{len(flows)}개가 정상 연결되어 있습니다."
            if not needing
            else f"운영 흐름 {len(needing)}개가 확인 필요 상태입니다."
        ),
        flow_id="backend_module_health",
        next_action="python tools\\check_code_knowledge_graph.py --strict",
        detail={"flow_count": len(flows), "needing_review": [flow.get("id") for flow in needing]},
    )


def build_code_knowledge_graph_payload(settings: Settings) -> dict[str, Any]:
    graph_path = code_knowledge_graph_path(settings)
    if not graph_path.exists():
        return {
            "status": "warning",
            "module": "code_knowledge_graph",
            "message": "코드 지식 그래프가 아직 생성되지 않았습니다.",
            "storage_path": str(graph_path),
            "next_action": "python tools\\build_code_knowledge_graph.py",
            "operation_signals": [],
            "signal_summary": {"ok": 0, "warning": 1, "error": 0},
        }
    graph = read_json_file(graph_path, {})
    flows = graph.get("flows") if isinstance(graph.get("flows"), list) else []
    signals = [
        _graph_flow_signal(flows),
        _recommendation_signal(settings),
        _storage_quality_signal(settings),
        _source_automation_signal(settings),
        _portfolio_signal(settings),
    ]
    signal_summary = {
        "ok": sum(1 for item in signals if item.get("status") == "ok"),
        "warning": sum(1 for item in signals if item.get("status") == "warning"),
        "error": sum(1 for item in signals if item.get("status") == "error"),
    }
    return {
        "status": "success" if signal_summary["error"] == 0 else "warning",
        "module": "code_knowledge_graph",
        "generated_at": graph.get("generated_at"),
        "node_count": graph.get("node_count", 0),
        "edge_count": graph.get("edge_count", 0),
        "summary": graph.get("summary") or {},
        "flows": flows,
        "operation_signals": signals,
        "signal_summary": signal_summary,
        "storage_path": str(graph_path),
        "message": f"운영 흐름 {sum(1 for item in flows if item.get('status') == 'ok')}/{len(flows)}개가 코드 그래프에 연결되어 있습니다. 운영 신호 {signal_summary['ok']}/{len(signals)}개 정상입니다.",
    }
