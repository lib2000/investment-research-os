"""Backend-free operational readiness score for the Investment Research OS."""

from __future__ import annotations

import argparse
import json
import sqlite3
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
    if now.time() < parse_hhmm(daily_time, time(hour=9)):
        expected.add((now.date() - timedelta(days=1)).isoformat())
    last_run = str(state.get("last_run_date") or state.get("last_run_at") or "")
    date_ok = last_run[:10] in expected
    score = (50.0 if date_ok else 0.0) + min(selected_count, 3) / 3 * 50.0
    return signal(
        "daily_recommendations_latest",
        "오늘 추천 1~3위",
        score,
        f"선택 {selected_count}개, 마지막 실행 {last_run or '미확인'}",
        "python tools\\check_daily_recommendations_store.py --require-milestones --require-quality --expected-latest-count 3 --max-latest-age-days 1",
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
    if month:
        for entry in entries.values():
            if not isinstance(entry, dict):
                continue
            if str(entry.get("next_earnings_date") or "").startswith(month):
                earnings_candidates += 1
                continue
            for event in entry.get("events") or []:
                if isinstance(event, dict) and str(event.get("date") or "").startswith(month):
                    earnings_candidates += 1
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
    if earnings_candidates:
        score += 20.0
    return signal(
        "investment_calendar_store",
        "투자 캘린더/실적 일정",
        score,
        f"{month or '월 미확인'}, 한국 {len(kr_events)}개, 미국 {len(us_events)}개, 실적 후보 {earnings_candidates}개",
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


def main() -> int:
    parser = argparse.ArgumentParser(description="운영 완성도 95% 기준을 백엔드 없이 점검합니다.")
    parser.add_argument("--min-score", type=float, default=95.0)
    parser.add_argument("--daily-time", default="09:00")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    vault_dir = root / "research_vault"
    system_dir = vault_dir / "_system"
    signals = [
        graph_signal(system_dir),
        recommendation_signal(system_dir, args.daily_time),
        recommendation_citations_signal(root, system_dir),
        storage_signal(vault_dir),
        rag_diagnostics_signal(vault_dir),
        source_signal(system_dir),
        investment_calendar_signal(vault_dir),
        portfolio_signal(system_dir),
    ]
    score = round(sum(item["score"] for item in signals) / len(signals), 1) if signals else 0.0
    warnings = [item for item in signals if item["status"] != "ok"]

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
