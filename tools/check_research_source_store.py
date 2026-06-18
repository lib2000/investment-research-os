"""Validate cached research source automation state without a running backend."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


SYSTEM_DIR = Path("research_vault/_system")


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (
            candidate / "research_vault"
        ).exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def load_json(system_dir: Path, name: str) -> dict[str, Any]:
    path = system_dir / name
    if not path.exists():
        raise SystemExit(f"소스 상태 파일을 찾지 못했습니다: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{name} JSON 파싱 실패: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"{name} 최상위 구조가 객체가 아닙니다.")
    return data


def load_optional_json(system_dir: Path, name: str) -> dict[str, Any]:
    path = system_dir / name
    if not path.exists():
        return {}
    return load_json(system_dir, name)


def parse_dt(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def age_hours(value: Any) -> float | None:
    parsed = parse_dt(value)
    if not parsed:
        return None
    return (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds() / 3600


def market_journal_session_age_days(value: Any, now: date | None = None) -> int | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        session_date = date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None
    today = now or date.today()
    return (today - session_date).days


def add_issue(issues: list[str], condition: bool, message: str) -> None:
    if condition:
        issues.append(message)


def non_empty_rows(rows: Any, *fields: str) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    result = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if all(str(row.get(field) or "").strip() for field in fields):
            result.append(row)
    return result


def metadata_policy_ok(policy: Any) -> bool:
    if not isinstance(policy, dict):
        return False
    return (
        policy.get("full_text_stored") is False
        and policy.get("mode") in {"metadata_only", "metadata_and_derived_signals_only"}
    )


def rows_from_mapping_or_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        rows = value.values()
    elif isinstance(value, list):
        rows = value
    else:
        return []
    return [row for row in rows if isinstance(row, dict)]


def rows_with_storage(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        storage = row.get("storage")
        if isinstance(storage, dict) and str(storage.get("relative_path") or "").strip():
            result.append(row)
    return result


def missing_storage_files(root: Path, rows: list[dict[str, Any]]) -> list[str]:
    missing: list[str] = []
    for row in rows:
        storage = row.get("storage")
        if not isinstance(storage, dict):
            continue
        title = str(row.get("title") or "제목 미확인")
        for key in ("relative_path", "json_relative_path"):
            relative_path = str(storage.get(key) or "").strip()
            if not relative_path:
                continue
            candidate = root / relative_path
            if not candidate.exists():
                missing.append(f"{title}: {relative_path}")
    return missing


def normalize_market(value: Any) -> str:
    return str(value or "").strip().upper()


def market_journal_market_summaries(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    summaries: dict[str, dict[str, Any]] = {}
    for row in rows:
        market = normalize_market(row.get("market"))
        if not market:
            continue
        summary = summaries.setdefault(
            market,
            {
                "entry_count": 0,
                "auto_entry_count": 0,
                "auto_complete_count": 0,
                "latest_session_date": "",
            },
        )
        summary["entry_count"] += 1
        session_date = str(row.get("session_date") or "").strip()
        if session_date > str(summary["latest_session_date"] or ""):
            summary["latest_session_date"] = session_date
        if str(row.get("source_origin") or "").strip().lower() != "manual":
            summary["auto_entry_count"] += 1
            if all(str(row.get(field) or "").strip() for field in ("source_provider", "source_title")):
                summary["auto_complete_count"] += 1
    return dict(sorted(summaries.items()))


def format_market_journal_summary(market: str, summary: dict[str, Any]) -> str:
    latest_session_date = str(summary.get("latest_session_date") or "").strip()
    age_days = market_journal_session_age_days(latest_session_date)
    age_label = f", 경과 {age_days}일" if age_days is not None else ""
    return (
        f"{market}={summary['entry_count']}개"
        f"(auto {summary['auto_entry_count']}개, latest {latest_session_date or '미확인'}{age_label})"
    )


def market_journal_impact_summary(payload: dict[str, Any]) -> dict[str, Any]:
    target_rows = [
        row
        for row in [
            *(payload.get("ticker_targets") or []),
            *(payload.get("sector_targets") or []),
        ]
        if isinstance(row, dict)
    ]
    market_counts: Counter[str] = Counter()
    latest_session_date = ""
    linked_target_count = 0
    match_count = 0
    samples: list[str] = []
    for row in target_rows:
        matches = [match for match in (row.get("market_journal_matches") or []) if isinstance(match, dict)]
        if not matches:
            continue
        linked_target_count += 1
        match_count += len(matches)
        label = str(row.get("ticker") or row.get("name") or "").strip()
        if label and len(samples) < 5:
            samples.append(label)
        for match in matches:
            market = normalize_market(match.get("market"))
            if market:
                market_counts[market] += 1
            session_date = str(match.get("session_date") or "").strip()
            if session_date > latest_session_date:
                latest_session_date = session_date
    return {
        "target_count": len(target_rows),
        "linked_target_count": linked_target_count,
        "match_count": match_count,
        "market_counts": dict(sorted(market_counts.items())),
        "latest_session_date": latest_session_date,
        "sample_targets": samples,
    }


def format_market_journal_impact(summary: dict[str, Any]) -> str:
    market_counts = summary.get("market_counts") if isinstance(summary.get("market_counts"), dict) else {}
    market_label = ", ".join(f"{market}={count}" for market, count in market_counts.items()) or "시장 미확인"
    samples = summary.get("sample_targets") if isinstance(summary.get("sample_targets"), list) else []
    sample_label = ", ".join(str(item) for item in samples[:5]) or "없음"
    return (
        f"대상 {summary.get('target_count', 0)}개 중 {summary.get('linked_target_count', 0)}개 연결 | "
        f"매칭 {summary.get('match_count', 0)}건({market_label}) | "
        f"최신 세션 {summary.get('latest_session_date') or '미확인'} | 샘플 {sample_label}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="리서치 소스 캐시/상태 파일을 백엔드 없이 점검합니다.")
    parser.add_argument("--strict", action="store_true", help="경고가 있으면 실패 코드로 종료")
    parser.add_argument("--max-source-age-hours", type=float, default=72.0, help="KCIF/지역 소스 최신성 기준")
    parser.add_argument("--max-registry-age-hours", type=float, default=168.0, help="티커 레지스트리 최신성 기준")
    parser.add_argument("--min-kcif-reports", type=int, default=10, help="KCIF 관련 보고서 최소 건수")
    parser.add_argument("--min-regional-provider-count", type=int, default=3, help="지역 소스별 최소 관련 자료 수")
    parser.add_argument("--min-naver-reports", type=int, default=20, help="네이버 리서치 캐시 최소 건수")
    parser.add_argument("--min-shinhan-reports", type=int, default=20, help="신한 리서치 캐시 최소 건수")
    parser.add_argument("--min-market-journal-entries", type=int, default=1, help="시장일지 최소 저장 건수")
    parser.add_argument("--max-naver-missing-storage", type=int, default=0, help="네이버 리서치 캐시의 저장 경로 누락 허용 건수")
    parser.add_argument("--max-market-journal-age-hours", type=float, default=72.0, help="시장일지 최신성 기준")
    parser.add_argument("--max-market-journal-session-age-days", type=int, default=7, help="시장별 최신 세션일 허용 경과일")
    parser.add_argument("--max-market-journal-attempt-age-hours", type=float, default=72.0, help="마감 시황 자동 수집 시도 최신성 기준")
    parser.add_argument("--min-market-journal-impact-links", type=int, default=1, help="관심/보유 자동화 보드에 필요한 시장일지 연결 최소 건수")
    parser.add_argument("--min-market-journal-linked-targets", type=int, default=1, help="시장일지가 연결되어야 하는 관심/보유 자동화 대상 최소 수")
    parser.add_argument("--max-dossier-queue-age-hours", type=float, default=72.0, help="중복 Dossier 큐 갱신 최신성 기준")
    parser.add_argument(
        "--required-market-journal-market",
        action="append",
        default=None,
        help="시장일지에 반드시 있어야 하는 시장 코드. 기본값: KR, US",
    )
    args = parser.parse_args()
    required_market_journal_markets = [
        normalize_market(value)
        for value in (args.required_market_journal_market or ["KR", "US"])
        if normalize_market(value)
    ]

    root = project_root(Path.cwd())
    system_dir = root / SYSTEM_DIR
    issues: list[str] = []

    kcif = load_json(system_dir, "kcif_reports_watch.json")
    kcif_rows = kcif.get("related_reports") or []
    kcif_related = len(kcif_rows)
    kcif_complete_rows = non_empty_rows(kcif_rows, "title", "published_at", "detail_url", "source_url")
    kcif_age = age_hours(kcif.get("updated_at"))
    add_issue(issues, kcif.get("source_status") not in {"success", "cached", "refreshed", "cache_fallback"}, "KCIF source_status 확인 필요")
    add_issue(issues, kcif_related < args.min_kcif_reports, f"KCIF related_reports 부족: {kcif_related}개")
    add_issue(issues, len(kcif_complete_rows) != kcif_related, "KCIF 관련 보고서 메타데이터 누락")
    add_issue(issues, kcif_age is None or kcif_age > args.max_source_age_hours, "KCIF 상태 파일 최신성 확인 필요")
    add_issue(issues, not metadata_policy_ok(kcif.get("policy")), "KCIF 저작권/메타데이터 저장 정책 확인 필요")
    add_issue(issues, bool(kcif.get("warnings")), f"KCIF 경고 {len(kcif.get('warnings') or [])}건")

    regional = load_json(system_dir, "regional_business_sources_watch.json")
    regional_rows = regional.get("related_items") or []
    regional_related = len(regional_rows)
    regional_complete_rows = non_empty_rows(regional_rows, "title", "published_at", "detail_url", "source_url", "source_provider")
    regional_age = age_hours(regional.get("updated_at"))
    source_results = regional.get("source_results") or []
    failed_sources = [
        item
        for item in source_results
        if isinstance(item, dict) and item.get("status") not in {"success", "cache_fallback"}
    ]
    provider_counts = Counter(str(item.get("source_provider") or "미확인") for item in regional_rows if isinstance(item, dict))
    expected_providers = {"EMERiCs", "CSF", "KIEP"}
    missing_providers = expected_providers - set(provider_counts)
    thin_providers = {provider: count for provider, count in provider_counts.items() if provider in expected_providers and count < args.min_regional_provider_count}
    add_issue(issues, regional.get("source_status") not in {"success", "cached", "refreshed", "cache_fallback"}, "지역/중국/대외 소스 source_status 확인 필요")
    add_issue(issues, regional_related < args.min_regional_provider_count * len(expected_providers), "지역/중국/대외 소스 related_items가 부족함")
    add_issue(issues, len(regional_complete_rows) != regional_related, "지역/중국/대외 소스 메타데이터 누락")
    add_issue(issues, bool(failed_sources), f"지역/중국/대외 소스 실패 {len(failed_sources)}건")
    add_issue(issues, bool(missing_providers), f"지역/중국/대외 소스 제공자 누락: {', '.join(sorted(missing_providers))}")
    add_issue(issues, bool(thin_providers), "지역/중국/대외 소스 제공자별 수집량 부족: " + ", ".join(f"{k}={v}" for k, v in sorted(thin_providers.items())))
    add_issue(issues, regional_age is None or regional_age > args.max_source_age_hours, "지역/중국/대외 소스 상태 파일 최신성 확인 필요")
    add_issue(issues, not metadata_policy_ok(regional.get("policy")), "지역/중국/대외 소스 저작권/메타데이터 저장 정책 확인 필요")
    add_issue(issues, bool(regional.get("warnings")), f"지역/중국/대외 소스 경고 {len(regional.get('warnings') or [])}건")

    registry = load_json(system_dir, "ticker_registry_source_status.json")
    registry_age = age_hours(registry.get("updated_at"))
    add_issue(issues, registry.get("status") != "success", "티커 레지스트리 status가 success가 아님")
    add_issue(issues, int(registry.get("success_count") or 0) < int(registry.get("source_count") or 0), "티커 레지스트리 일부 소스 실패")
    add_issue(issues, int(registry.get("entry_count") or 0) < 10000, "티커 레지스트리 종목 수가 비정상적으로 적음")
    add_issue(issues, registry_age is None or registry_age > args.max_registry_age_hours, "티커 레지스트리 최신성 확인 필요")

    dossier = load_json(system_dir, "dossier_refresh_queue_status.json")
    dossier_timestamp = dossier.get("updated_at") or dossier.get("as_of")
    dossier_age = age_hours(dossier_timestamp)
    add_issue(issues, dossier.get("status") != "success", "중복 Dossier 큐 status가 success가 아님")
    add_issue(issues, int(dossier.get("failed_count") or 0) > 0, "중복 Dossier 큐 실패 건 존재")
    add_issue(issues, dossier_age is None or dossier_age > args.max_dossier_queue_age_hours, "중복 Dossier 큐 최신성 확인 필요")

    automation = load_json(system_dir, "research_automation_status.json")
    automation_timestamp = automation.get("updated_at")
    automation_age = age_hours(automation_timestamp)
    deduped_refresh = automation.get("last_deduped_dossier_refresh")
    deduped_refresh_timestamp = (
        deduped_refresh.get("updated_at") or deduped_refresh.get("as_of")
        if isinstance(deduped_refresh, dict)
        else None
    )
    deduped_refresh_age = age_hours(deduped_refresh_timestamp)
    add_issue(issues, not isinstance(deduped_refresh, dict), "리서치 자동화 Dossier 갱신 상태 누락")
    add_issue(issues, automation_age is None or automation_age > args.max_dossier_queue_age_hours, "리서치 자동화 상태 상위 updated_at 최신성 확인 필요")
    add_issue(issues, automation.get("save_result") is not True, "리서치 자동화 저장 결과 확인 필요")
    add_issue(issues, int(automation.get("failed_count") or 0) > 0, "리서치 자동화 실패 건 존재")
    add_issue(issues, int(automation.get("dossier_count") or 0) < 1, "리서치 자동화 Dossier 결과 부족")
    add_issue(issues, int(automation.get("rag_connected_count") or 0) < 1, "리서치 자동화 RAG 연결 결과 부족")
    add_issue(issues, int(automation.get("news_unpromoted_count") or 0) > 0, "리서치 자동화 뉴스 미승격 항목 존재")
    if isinstance(deduped_refresh, dict):
        add_issue(issues, int(deduped_refresh.get("failed_count") or 0) > 0, "리서치 자동화 Dossier 갱신 실패 건 존재")
        add_issue(issues, deduped_refresh_age is None or deduped_refresh_age > args.max_dossier_queue_age_hours, "리서치 자동화 Dossier 갱신 최신성 확인 필요")
        add_issue(
            issues,
            bool(automation_timestamp and deduped_refresh_timestamp and automation_timestamp != deduped_refresh_timestamp),
            "리서치 자동화 상위 updated_at과 Dossier 갱신 updated_at 불일치",
        )

    naver = load_json(system_dir, "naver_research_cache.json")
    naver_rows = rows_from_mapping_or_list(naver.get("entries"))
    naver_complete_rows = non_empty_rows(naver_rows, "title", "published_at", "url", "source", "summary")
    naver_storage_rows = rows_with_storage(naver_rows)
    naver_missing_files = missing_storage_files(root, naver_storage_rows)
    naver_age = age_hours(naver.get("updated_at"))
    naver_category_counts = Counter(str(item.get("category") or "미확인") for item in naver_rows)
    add_issue(issues, len(naver_rows) < args.min_naver_reports, f"네이버 리서치 캐시 부족: {len(naver_rows)}개")
    naver_missing_storage = len(naver_rows) - len(naver_storage_rows)
    add_issue(issues, len(naver_complete_rows) != len(naver_rows), "네이버 리서치 메타데이터 누락")
    add_issue(
        issues,
        naver_missing_storage > args.max_naver_missing_storage,
        f"네이버 리서치 저장 경로 누락 허용 초과: {naver_missing_storage}개 / 허용 {args.max_naver_missing_storage}개",
    )
    add_issue(issues, bool(naver_missing_files), f"네이버 리서치 저장 파일 누락 {len(naver_missing_files)}개")
    add_issue(issues, naver_age is None or naver_age > args.max_source_age_hours, "네이버 리서치 캐시 최신성 확인 필요")
    add_issue(issues, naver_category_counts.get("시황정보", 0) < 1, "네이버 시황정보 리포트 캐시 확인 필요")

    shinhan = load_json(system_dir, "shinhan_research_cache.json")
    shinhan_rows = rows_from_mapping_or_list(shinhan.get("entries"))
    shinhan_complete_rows = non_empty_rows(shinhan_rows, "title", "published_at", "url", "source", "summary")
    shinhan_storage_rows = rows_with_storage(shinhan_rows)
    shinhan_missing_files = missing_storage_files(root, shinhan_storage_rows)
    shinhan_age = age_hours(shinhan.get("updated_at"))
    add_issue(issues, len(shinhan_rows) < args.min_shinhan_reports, f"신한 리서치 캐시 부족: {len(shinhan_rows)}개")
    add_issue(issues, len(shinhan_complete_rows) != len(shinhan_rows), "신한 리서치 메타데이터 누락")
    add_issue(issues, len(shinhan_storage_rows) != len(shinhan_rows), "신한 리서치 저장 경로 누락")
    add_issue(issues, bool(shinhan_missing_files), f"신한 리서치 저장 파일 누락 {len(shinhan_missing_files)}개")
    add_issue(issues, shinhan_age is None or shinhan_age > args.max_source_age_hours, "신한 리서치 캐시 최신성 확인 필요")

    market_close_state = load_json(system_dir, "naver_market_close_journal_state.json")
    market_close_attempt_age = age_hours(market_close_state.get("last_attempt_at"))
    market_close_status = str(market_close_state.get("status") or "").strip()
    add_issue(issues, market_close_status not in {"success", "stored", "skipped_duplicate", "no_source"}, f"마감 시황 자동 수집 상태 확인 필요: {market_close_status or '미확인'}")
    add_issue(issues, not str(market_close_state.get("last_attempt_date") or "").strip(), "마감 시황 자동 수집 시도일 누락")
    add_issue(issues, market_close_attempt_age is None or market_close_attempt_age > args.max_market_journal_attempt_age_hours, "마감 시황 자동 수집 시도 최신성 확인 필요")
    if market_close_status == "skipped_duplicate":
        add_issue(issues, not str(market_close_state.get("source_item_id") or "").strip(), "마감 시황 중복 판정 source_item_id 누락")
        add_issue(issues, not str(market_close_state.get("last_attempt_message") or "").strip(), "마감 시황 중복 판정 설명 누락")

    telegram_market_close_state = load_json(system_dir, "telegram_market_close_journal_state.json")
    telegram_market_close_status = str(telegram_market_close_state.get("status") or "").strip()
    if telegram_market_close_state:
        telegram_market_close_attempt_age = age_hours(telegram_market_close_state.get("last_attempt_at"))
        add_issue(
            issues,
            telegram_market_close_status not in {"success", "skipped_duplicate", "not_found"},
            f"텔레그램 미국 시장일지 자동 수집 상태 확인 필요: {telegram_market_close_status or '미확인'}",
        )
        add_issue(issues, not str(telegram_market_close_state.get("last_attempt_date") or "").strip(), "텔레그램 미국 시장일지 자동 수집 시도일 누락")
        add_issue(
            issues,
            telegram_market_close_attempt_age is None or telegram_market_close_attempt_age > args.max_market_journal_attempt_age_hours,
            "텔레그램 미국 시장일지 자동 수집 시도 최신성 확인 필요",
        )
        if telegram_market_close_status in {"success", "skipped_duplicate"}:
            add_issue(issues, not str(telegram_market_close_state.get("source_item_id") or "").strip(), "텔레그램 미국 시장일지 source_item_id 누락")
            add_issue(issues, not str(telegram_market_close_state.get("source_provider") or "").strip(), "텔레그램 미국 시장일지 출처 제공자 누락")

    market_journal = load_json(system_dir, "market_close_journal.json")
    market_journal_rows = rows_from_mapping_or_list(market_journal.get("entries"))
    market_journal_complete_rows = []
    market_journal_auto_rows = []
    market_journal_auto_complete_rows = []
    for row in market_journal_rows:
        if all(str(row.get(field) or "").strip() for field in ("market", "session_date", "raw_summary")):
            market_journal_complete_rows.append(row)
        if str(row.get("source_origin") or "").strip().lower() != "manual":
            market_journal_auto_rows.append(row)
            if all(str(row.get(field) or "").strip() for field in ("source_provider", "source_title")):
                market_journal_auto_complete_rows.append(row)
    market_journal_age = age_hours(market_journal.get("updated_at"))
    add_issue(issues, len(market_journal_rows) < args.min_market_journal_entries, "마감 시황 시장일지 저장 건수 부족")
    add_issue(issues, len(market_journal_complete_rows) != len(market_journal_rows), "마감 시황 시장일지 기본 메타데이터 누락")
    add_issue(issues, len(market_journal_auto_complete_rows) != len(market_journal_auto_rows), "자동 마감 시황 시장일지 출처 메타데이터 누락")
    add_issue(
        issues,
        market_journal_age is None or market_journal_age > args.max_market_journal_age_hours,
        "마감 시황 시장일지 최신성 확인 필요",
    )
    market_journal_by_market = market_journal_market_summaries(market_journal_rows)
    for market in required_market_journal_markets:
        summary = market_journal_by_market.get(market, {})
        add_issue(
            issues,
            int(summary.get("entry_count") or 0) < 1,
            f"마감 시황 시장일지 {market} 저장 항목 누락",
        )
        add_issue(
            issues,
            int(summary.get("auto_entry_count") or 0) < 1,
            f"마감 시황 시장일지 {market} 자동 출처 항목 누락",
        )
        latest_session_date = str(summary.get("latest_session_date") or "").strip()
        latest_session_age_days = market_journal_session_age_days(latest_session_date)
        add_issue(
            issues,
            latest_session_age_days is None
            or latest_session_age_days > max(1, int(args.max_market_journal_session_age_days)),
            f"마감 시황 시장일지 {market} 최신 세션 확인 필요: {latest_session_date or '미확인'}",
        )

    interest_targets = load_optional_json(system_dir, "interest_collection_targets.json")
    interest_payload = interest_targets.get("payload") if isinstance(interest_targets.get("payload"), dict) else interest_targets
    market_journal_impact = market_journal_impact_summary(interest_payload if isinstance(interest_payload, dict) else {})
    add_issue(
        issues,
        int(market_journal_impact.get("match_count") or 0) < args.min_market_journal_impact_links,
        "시장일지 관심/보유 자동화 연결 건수 부족",
    )
    add_issue(
        issues,
        int(market_journal_impact.get("linked_target_count") or 0) < args.min_market_journal_linked_targets,
        "시장일지 관심/보유 자동화 연결 대상 부족",
    )

    print(f"소스 상태 폴더: {system_dir}")
    print(f"KCIF 관련 보고서: {kcif_related}개 | 상태 {kcif.get('source_status')} | 갱신 {kcif.get('updated_at')}")
    provider_summary = ", ".join(
        [
            f"CSF={provider_counts.get('CSF', 0)}",
            f"EMERiCs={provider_counts.get('EMERiCs', 0)}",
            f"KIEP={provider_counts.get('KIEP', 0)}",
        ]
    )
    print(f"EMERiCs/CSF/KIEP 관련 자료: {regional_related}개 | {provider_summary} | 실패 소스 {len(failed_sources)}개 | 갱신 {regional.get('updated_at')}")
    print(f"티커 레지스트리: {registry.get('entry_count')}개 | 성공 {registry.get('success_count')}/{registry.get('source_count')} | 갱신 {registry.get('updated_at')}")
    print(f"중복 Dossier 큐: 후보 {dossier.get('candidate_count')}개 | 갱신 {dossier.get('refreshed_count')}개 | 실패 {dossier.get('failed_count')}개 | 갱신 {dossier_timestamp}")
    print(
        f"리서치 자동화 상태: 저장 {automation.get('save_result')} | Dossier {automation.get('dossier_count')}개 | "
        f"RAG 연결 {automation.get('rag_connected_count')}개 | 실패 {automation.get('failed_count')}개 | "
        f"뉴스 미승격 {automation.get('news_unpromoted_count')}개 | 갱신 {automation_timestamp}"
    )
    if isinstance(deduped_refresh, dict):
        print(f"리서치 자동화 Dossier 갱신: 후보 {deduped_refresh.get('candidate_count')}개 | 갱신 {deduped_refresh.get('refreshed_count')}개 | 실패 {deduped_refresh.get('failed_count')}개 | 갱신 {deduped_refresh.get('updated_at')}")
    naver_category_summary = ", ".join(f"{name}={count}" for name, count in naver_category_counts.most_common(4))
    print(f"네이버 리서치: {len(naver_rows)}개 | 저장 {len(naver_storage_rows)}개 | 저장경로 누락 {naver_missing_storage}개 | 파일 누락 {len(naver_missing_files)}개 | {naver_category_summary} | 갱신 {naver.get('updated_at')}")
    print(f"신한 리서치: {len(shinhan_rows)}개 | 저장 {len(shinhan_storage_rows)}개 | 파일 누락 {len(shinhan_missing_files)}개 | 갱신 {shinhan.get('updated_at')}")
    print(f"마감 시황 자동 시도: 상태 {market_close_status or '미확인'} | 시도일 {market_close_state.get('last_attempt_date') or '미확인'} | 시각 {market_close_state.get('last_attempt_at') or '미확인'}")
    print(f"텔레그램 미국 시장일지 자동 시도: 상태 {telegram_market_close_status or '미확인'} | 시도일 {telegram_market_close_state.get('last_attempt_date') or '미확인'} | 시각 {telegram_market_close_state.get('last_attempt_at') or '미확인'}")
    print(f"마감 시황 시장일지: {len(market_journal_rows)}개 | 자동 출처 {len(market_journal_auto_complete_rows)}/{len(market_journal_auto_rows)}개 | 갱신 {market_journal.get('updated_at')}")
    market_summary = ", ".join(
        format_market_journal_summary(market, summary)
        for market, summary in market_journal_by_market.items()
    )
    print(f"마감 시황 시장별 커버리지: {market_summary or '없음'}")
    print(f"시장일지 시스템 반영: {format_market_journal_impact(market_journal_impact)}")

    if issues:
        for issue in issues:
            print(f"주의: {issue}")
        if args.strict:
            return 1
    else:
        print("리서치 소스 저장 상태 정상")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
