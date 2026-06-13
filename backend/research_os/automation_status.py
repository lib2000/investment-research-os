"""Research automation status, dashboard digest, and pipeline workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class AutomationStatusRuntime(Protocol):
    """Runtime callbacks supplied by research_os_main while this workflow is split out."""


def safe_rag_memory_status(runtime: AutomationStatusRuntime, vault_dir: Path) -> dict:
    try:
        return runtime.rag_memory_status(vault_dir)
    except Exception as exc:
        return {
            "document_count": 0,
            "snapshot_count": 0,
            "warning": f"RAG 색인 상태 확인 실패: {exc}",
        }


def build_research_automation_feature_status(runtime: AutomationStatusRuntime, settings) -> dict:
    vault_dir = runtime.resolve_vault_dir(settings.research_vault_dir)
    manifest_entries = runtime.read_manifest(vault_dir)
    rag_status_payload = safe_rag_memory_status(runtime, vault_dir)
    news_payload = runtime.read_news_inbox(settings)
    news_items = [
        item for item in news_payload.get("items", []) if isinstance(item, dict)
    ]
    news_unpromoted_count = sum(1 for item in news_items if not item.get("promoted"))
    news_quality_issue_count = sum(
        1
        for item in news_items
        if (item.get("capture_quality") or {}).get("status") not in {None, "정상"}
    )
    latest_brief = runtime.read_latest_daily_brief(settings)
    last_run = runtime.read_json_store(runtime.research_automation_status_path(settings), {})
    duplicate_review = runtime.read_json_store(runtime.storage_duplicate_review_path(settings), {})
    refresh_queue = runtime.read_json_store(runtime.dossier_refresh_queue_status_path(settings), {})
    latest_interest_targets = runtime.read_json_store(runtime.interest_collection_targets_path(settings), {})
    interest_payload = latest_interest_targets.get("payload") if isinstance(latest_interest_targets, dict) else {}
    if not isinstance(interest_payload, dict):
        interest_payload = {}
    latest_brief_payload = latest_brief.get("payload") if isinstance(latest_brief, dict) else {}
    if not isinstance(latest_brief_payload, dict):
        latest_brief_payload = {}
    source_schedule = runtime.build_external_source_schedule_status(settings)
    source_tags = {
        tag
        for entry in manifest_entries
        for tag in (entry.get("tags") or [])
        if isinstance(tag, str)
    }
    duplicate_count = (
        sum(1 for entry in manifest_entries if entry.get("duplicate_reason"))
        + int(latest_brief_payload.get("duplicate_recent_entry_count") or 0)
        + int(latest_brief_payload.get("duplicate_market_entry_count") or 0)
    )
    if isinstance(duplicate_review, dict):
        duplicate_count = max(duplicate_count, int(duplicate_review.get("duplicate_entry_count") or 0))
    dossier_count = sum(1 for entry in manifest_entries if entry.get("type") == "dossier-synthesis")
    daily_brief_count = sum(1 for entry in manifest_entries if entry.get("type") == "daily-dossier-brief")
    rag_document_count = rag_status_payload.get("document_count")
    if not rag_document_count and isinstance(last_run, dict):
        rag_document_count = last_run.get("rag_updated_count")
    rag_snapshot_count = rag_status_payload.get("snapshot_count")
    if not rag_snapshot_count and isinstance(last_run, dict):
        rag_snapshot_count = last_run.get("rag_ticker_count")
    payload = {
        "status": "success",
        "module": "research_automation_feature_status",
        "as_of": runtime.current_storage_timestamp(),
        "features": [
            {
                "name": "Pulls",
                "status": "active",
                "detail": "신한/네이버 리서치, 웹사이트 입력, 파일 입력, 시장일지, 보유/관심 종목 후보를 수집 흐름에 연결했습니다.",
                "interest_target_count": interest_payload.get("target_count", 0),
            },
            {
                "name": "De-dupes",
                "status": "active",
                "detail": "source_url/content_hash exact match와 제목·본문 토큰 유사도 기반 중복 제거를 Dossier/일일 브리핑에 적용했습니다.",
                "duplicate_count": duplicate_count,
            },
            {
                "name": "Embeds",
                "status": "active",
                "detail": "SQLite RAG 메모리 색인으로 티커, 태그, 요약, 본문 검색을 지원합니다.",
                "document_count": rag_document_count,
                "snapshot_count": rag_snapshot_count,
            },
            {
                "name": "Tags",
                "status": "active",
                "detail": "종목/섹터/테마/리스크/실적/수급/금리/기관/인물/AI/에너지/우주/방산/바이오/소비재 태그를 자동 부여합니다.",
                "tag_count": len(source_tags),
            },
            {
                "name": "Syntheses",
                "status": "active",
                "detail": "7개 스킬의 리포트와 저장 자료를 Dossier 합성 보고서로 통합합니다.",
                "dossier_count": dossier_count,
            },
            {
                "name": "Consensus facts",
                "status": "active",
                "detail": "여러 자료에서 반복 등장하는 매출, 마진, 현금흐름, 계약, 정책, 시장 사실을 합의된 사실로 추출합니다.",
            },
            {
                "name": "Bull thesis",
                "status": "active",
                "detail": "성장, 수요, 마진, 수주, 가이던스 상향 등 긍정 신호를 강세 논거로 정리합니다.",
            },
            {
                "name": "Bear thesis",
                "status": "active",
                "detail": "둔화, 리스크, 마진 압박, 규제, 현금 소진 등 부정 신호를 약세 논거로 정리하되 부정 문맥은 제외합니다.",
            },
            {
                "name": "Cruxes",
                "status": "active",
                "detail": "투자 판단을 좌우할 핵심 KPI, 밸류에이션, 신규 자료 검증 질문을 생성합니다.",
            },
            {
                "name": "Observables",
                "status": "active",
                "detail": "다음 실적/공시/뉴스에서 확인할 KPI와 이벤트를 추적 항목으로 저장합니다.",
            },
            {
                "name": "Delivers",
                "status": "active",
                "detail": "일일 브리핑을 저장 데이터에 적재하고 최신 브리핑 상태를 대시보드 추천 액션에서 참조합니다.",
                "daily_brief_count": daily_brief_count,
                "latest_daily_brief_date": latest_brief_payload.get("date"),
            },
        ],
        "last_run": last_run,
        "source_schedule": source_schedule,
        "duplicate_review": duplicate_review if isinstance(duplicate_review, dict) else {},
        "dossier_refresh_queue": refresh_queue if isinstance(refresh_queue, dict) else {},
        "storage_quality_dashboard": runtime.build_storage_quality_dashboard(settings),
    }
    try:
        payload["dashboard_digest"] = build_research_automation_dashboard_digest(runtime, settings)
    except Exception as exc:
        payload["dashboard_digest"] = {
            "status": "warning",
            "headline": "자동화 요약 확인 필요",
            "error": runtime.provider_error_message(exc, settings),
        }
    return payload


def build_research_automation_dashboard_digest(runtime: AutomationStatusRuntime, settings) -> dict:
    vault_dir = runtime.resolve_vault_dir(settings.research_vault_dir)
    latest_targets = runtime.read_json_store(runtime.interest_collection_targets_path(settings), {})
    board = latest_targets.get("payload") if isinstance(latest_targets, dict) else {}
    if not isinstance(board, dict) or not board:
        try:
            board = runtime.build_interest_automation_board(settings, save_result=False)
        except Exception as exc:
            board = {"status": "warning", "error": runtime.provider_error_message(exc, settings)}

    status = runtime.read_json_store(runtime.research_automation_status_path(settings), {})
    duplicate_review = runtime.read_json_store(runtime.storage_duplicate_review_path(settings), {})
    refresh_queue = runtime.read_json_store(runtime.dossier_refresh_queue_status_path(settings), {})
    latest_brief = runtime.read_latest_daily_brief(settings)
    brief_payload = latest_brief.get("payload") if isinstance(latest_brief, dict) else {}
    if not isinstance(brief_payload, dict):
        brief_payload = {}
    rag_status_payload = safe_rag_memory_status(runtime, vault_dir)

    targets = [
        *[item for item in board.get("ticker_targets", []) if isinstance(item, dict)],
        *[item for item in board.get("sector_targets", []) if isinstance(item, dict)],
    ]
    priority_targets = sorted(
        targets,
        key=lambda item: (
            {"high": 3, "medium": 2, "low": 1}.get(str(item.get("priority")), 2),
            int(item.get("recent_document_count") or 0),
            int(item.get("rag_document_count") or 0),
        ),
        reverse=True,
    )[:5]
    duplicate_count = max(
        int(board.get("duplicate_suspected_count") or 0),
        int(duplicate_review.get("duplicate_entry_count") or 0) if isinstance(duplicate_review, dict) else 0,
    )
    failed_count = int(status.get("failed_count") or 0)
    target_count = int(board.get("target_count") or 0)
    dossier_count = int(status.get("dossier_count") or 0)
    target_rag_count = sum(int(item.get("rag_document_count") or 0) for item in targets)
    rag_document_count = max(
        int(rag_status_payload.get("document_count") or 0),
        int(status.get("rag_updated_count") or 0),
        target_rag_count,
    )
    news_payload = runtime.build_news_inbox_payload(settings, limit=10)
    source_schedule = runtime.build_external_source_schedule_status(settings)
    daily_recommendations = runtime.summarize_daily_recommendation_store(settings, limit=10)
    daily_recommendation_state = runtime.read_json_store(runtime.daily_recommendation_state_path(settings), {})
    daily_recommendations_due = runtime.should_run_daily_recommendations(settings)
    kcif_watch = runtime.read_kcif_reports_watch(settings)
    kcif_related_count = 0
    kcif_due = True
    if isinstance(kcif_watch, dict) and kcif_watch:
        kcif_related_count = len(kcif_watch.get("related_reports") or [])
        kcif_due = runtime.should_refresh_kcif_cache(kcif_watch)
    regional_sources_watch = runtime.read_regional_business_sources_watch(settings)
    regional_sources_related_count = 0
    regional_sources_due = True
    if isinstance(regional_sources_watch, dict) and regional_sources_watch:
        regional_sources_related_count = len(regional_sources_watch.get("related_items") or [])
        regional_sources_due = runtime.should_refresh_regional_business_cache(regional_sources_watch)
    dart_cache = runtime.read_dart_filing_cache(settings)
    dart_daily = runtime.dart_daily_check_status(dart_cache, settings)
    news_items = news_payload.get("items") if isinstance(news_payload, dict) else []
    if not isinstance(news_items, list):
        news_items = []
    news_unpromoted_count = int(news_payload.get("unpromoted_count") or 0) if isinstance(news_payload, dict) else 0
    news_quality_issue_count = (
        int(news_payload.get("quality_issue_count") or 0) if isinstance(news_payload, dict) else 0
    )
    daily_brief_date = status.get("daily_brief_date") or brief_payload.get("date")
    source_quality_dashboard = [
        {
            "source": "DART 공시",
            "status": "점검 필요" if dart_daily.get("due") else ("주의" if dart_daily.get("failure_count") else "정상"),
            "copyright_policy": "공시 원문/메타데이터 저장",
            "duplicate_guard": "공시번호 기준 중복 제외",
            "related_count": int(dart_daily.get("target_count") or dart_daily.get("coverage_count") or 0),
            "last_checked_at": dart_daily.get("last_checked_at") or dart_daily.get("checked_at"),
            "detail": dart_daily.get("summary") or f"실패 {dart_daily.get('failure_count') or 0}건",
        },
        {
            "source": "네이버 리서치/시장일지",
            "status": "주의" if news_quality_issue_count else "정상",
            "copyright_policy": "저작권 안전 요약/메타데이터 중심",
            "duplicate_guard": "source_url/content_hash/제목 유사도 중복 제외",
            "related_count": len(news_items),
            "last_checked_at": status.get("naver_research_checked_at") or status.get("updated_at"),
            "detail": f"뉴스 인박스 {len(news_items)}개 · 품질 확인 {news_quality_issue_count}개",
        },
        {
            "source": "KIEP/KCIF 매크로",
            "status": "점검 필요" if kcif_due else "정상",
            "copyright_policy": "제목·발행일·링크·요약 메타데이터 활용",
            "duplicate_guard": "보고서 URL/제목 기준 중복 제외",
            "related_count": kcif_related_count,
            "last_checked_at": kcif_watch.get("updated_at") if isinstance(kcif_watch, dict) else None,
            "detail": "매크로 보고서 일일 점검",
        },
        {
            "source": "EMERiCs/CSF/지역자료",
            "status": "점검 필요" if regional_sources_due else "정상",
            "copyright_policy": "제목·링크·발행기관·요약 메타데이터 활용",
            "duplicate_guard": "URL/제목 기준 중복 제외",
            "related_count": regional_sources_related_count,
            "last_checked_at": regional_sources_watch.get("updated_at")
            if isinstance(regional_sources_watch, dict)
            else None,
            "detail": "지역·중국·신흥국 리스크 소스 일일 점검",
        },
    ]

    tone = "ok"
    headline = "자동화 정상"
    if failed_count or news_quality_issue_count:
        tone = "warning"
        headline = "확인 필요"
    if not target_count or not daily_brief_date:
        tone = "needs_action"
        headline = "업데이트 필요"

    next_actions = []
    if not target_count:
        next_actions.append("포트폴리오나 관심목록을 저장해 자동 수집 대상을 먼저 구성하세요.")
    if not daily_brief_date:
        next_actions.append("오늘 리서치 업데이트를 실행해 일일 브리핑을 생성하세요.")
    if duplicate_count:
        next_actions.append(f"중복 의심 자료 {duplicate_count}개를 Dossier 합성에서 묶어 확인하세요.")
    if failed_count:
        next_actions.append(f"자동화 실패 {failed_count}건의 API/소스 상태를 점검하세요.")
    if news_unpromoted_count:
        next_actions.append(f"뉴스 인박스 미승격 자료 {news_unpromoted_count}개를 논거/시장일지 반영 여부로 분류하세요.")
    if news_quality_issue_count:
        next_actions.append(f"뉴스 본문 추출 품질 경고 {news_quality_issue_count}개를 원문 링크나 본문 붙여넣기로 보강하세요.")
    if kcif_due:
        next_actions.append("KCIF 매크로 보고서 목록 일일 점검이 필요합니다.")
    elif kcif_related_count:
        next_actions.append(f"KCIF 관련 매크로 보고서 {kcif_related_count}개를 시장일지/보유종목 리스크 메모와 연결하세요.")
    if regional_sources_due:
        next_actions.append("EMERiCs/CSF/KIEP 지역·매크로 자료 일일 점검이 필요합니다.")
    elif regional_sources_related_count:
        next_actions.append(
            f"EMERiCs/CSF/KIEP 관련 자료 {regional_sources_related_count}개를 시장일지/보유종목 리스크 메모와 연결하세요."
        )
    if dart_daily.get("due"):
        next_actions.append("보유·관심 종목 DART 신규 공시 일일 점검이 필요합니다.")
    elif dart_daily.get("failure_count"):
        next_actions.append(f"DART 공시 점검 실패 {dart_daily.get('failure_count')}개 종목을 확인하세요.")
    if daily_recommendations_due:
        next_actions.append("오늘의 추천 후보 1~3위 생성과 사후 추적 저장이 필요합니다.")
    elif daily_recommendations.get("latest_recommendation_date"):
        next_actions.append(
            f"{daily_recommendations.get('latest_recommendation_date')} 추천 후보 1~3위가 별도 항목에 저장되어 있습니다."
        )
    if not next_actions:
        next_actions.append("보유·관심 대상의 새 자료를 수집하고 Dossier/일일 브리핑에 반영할 준비가 되어 있습니다.")

    return {
        "status": "success",
        "module": "research_automation_dashboard_digest",
        "tone": tone,
        "headline": headline,
        "as_of": runtime.current_storage_timestamp(),
        "target_count": target_count,
        "ticker_target_count": int(board.get("ticker_target_count") or 0),
        "sector_target_count": int(board.get("sector_target_count") or 0),
        "portfolio_linked_count": int(board.get("portfolio_linked_count") or 0),
        "rag_connected_count": int(board.get("rag_connected_count") or 0),
        "rag_document_count": rag_document_count,
        "duplicate_suspected_count": duplicate_count,
        "duplicate_group_count": int(duplicate_review.get("duplicate_group_count") or 0)
        if isinstance(duplicate_review, dict)
        else 0,
        "last_deduped_dossier_refresh": refresh_queue
        if isinstance(refresh_queue, dict) and refresh_queue
        else status.get("last_deduped_dossier_refresh"),
        "dossier_count": dossier_count,
        "failed_count": failed_count,
        "daily_brief_date": daily_brief_date,
        "news_inbox_count": len(news_items),
        "news_unpromoted_count": news_unpromoted_count,
        "news_quality_issue_count": news_quality_issue_count,
        "kcif_related_count": kcif_related_count,
        "kcif_due": bool(kcif_due),
        "kcif_last_checked_at": kcif_watch.get("updated_at") if isinstance(kcif_watch, dict) else None,
        "regional_sources_related_count": regional_sources_related_count,
        "regional_sources_due": bool(regional_sources_due),
        "regional_sources_last_checked_at": regional_sources_watch.get("updated_at")
        if isinstance(regional_sources_watch, dict)
        else None,
        "source_schedule": source_schedule,
        "source_schedule_due_count": sum(1 for item in source_schedule if item.get("due")),
        "source_quality_dashboard": source_quality_dashboard,
        "dart_daily_check": dart_daily,
        "dart_due": bool(dart_daily.get("due")),
        "dart_failure_count": int(dart_daily.get("failure_count") or 0),
        "daily_recommendations": {
            "enabled": settings.daily_recommendations_enabled,
            "daily_time": settings.daily_recommendations_time,
            "due": daily_recommendations_due,
            "latest_recommendation_date": daily_recommendations.get("latest_recommendation_date"),
            "record_count": daily_recommendations.get("record_count"),
            "state": daily_recommendation_state,
        },
        "last_run_at": status.get("updated_at"),
        "priority_targets": [
            {
                "label": item.get("company_name") or item.get("name") or item.get("ticker") or "대상 미확인",
                "key": item.get("ticker") or item.get("name") or "",
                "source": item.get("source") or item.get("scope") or "interest",
                "priority": item.get("priority") or "medium",
                "recent_document_count": item.get("recent_document_count") or 0,
                "rag_document_count": item.get("rag_document_count") or 0,
                "duplicate_suspected_count": item.get("duplicate_suspected_count") or 0,
                "next_action": item.get("next_action"),
            }
            for item in priority_targets
        ],
        "next_actions": next_actions[:5],
        "automation_steps": board.get("automation_steps") or [
            "Pulls: 보유·관심 대상의 뉴스, 공시, 리포트, 시장일지를 수집합니다.",
            "De-dupes: 중복 기사와 리포트를 제목·본문 유사도로 묶습니다.",
            "Embeds/Tags: 저장 데이터를 RAG 색인과 자동 태그에 연결합니다.",
            "Syntheses/Delivers: Dossier와 일일 브리핑으로 합성해 대시보드에 반영합니다.",
        ],
    }


def run_research_automation_pipeline(
    runtime: AutomationStatusRuntime,
    settings,
    *,
    limit: int = 30,
    save_result: bool = True,
) -> dict:
    vault_dir = runtime.resolve_vault_dir(settings.research_vault_dir)
    source_results: list[dict] = []
    for name, refresh_func in [
        ("shinhan_research", runtime.refresh_shinhan_research_cache),
        ("naver_research", runtime.refresh_naver_research_cache),
    ]:
        try:
            source_results.append(
                {
                    "source": name,
                    "result": refresh_func(settings, limit=5, force=False, save_result=save_result),
                }
            )
        except Exception as exc:
            source_results.append({"source": name, "status": "failed", "error": str(exc)})
    try:
        source_results.append(
            {
                "source": "kcif_reports_watch",
                "result": runtime.build_kcif_reports_watch_payload(
                    settings,
                    limit=min(limit, 30),
                    force=False,
                    save_result=save_result,
                ),
            }
        )
    except Exception as exc:
        source_results.append({"source": "kcif_reports_watch", "status": "failed", "error": str(exc)})
    try:
        source_results.append(
            {
                "source": "regional_business_sources_watch",
                "result": runtime.build_regional_business_sources_watch_payload(
                    settings,
                    limit=min(limit, 40),
                    force=False,
                    save_result=save_result,
                ),
            }
        )
    except Exception as exc:
        source_results.append({"source": "regional_business_sources_watch", "status": "failed", "error": str(exc)})

    rag_backfill = runtime.backfill_research_memory_documents_from_manifest(vault_dir)
    dossier_results: list[dict] = []
    failed: list[dict] = []
    for ticker in runtime.dossier_candidate_tickers(settings, limit=limit):
        try:
            dossier = runtime.synthesize_and_save_dossier(ticker, settings, save_result=save_result)
            dossier_results.append(
                {
                    "ticker": ticker,
                    "source_count": dossier.get("source_count"),
                    "duplicate_count": dossier.get("duplicate_count"),
                    "confidence": dossier.get("confidence"),
                    "storage": dossier.get("storage"),
                }
            )
        except Exception as exc:
            failed.append({"ticker": ticker, "error": str(exc)})

    daily_payload = runtime.build_daily_brief_payload(settings)
    daily_brief = runtime.save_daily_brief(daily_payload, settings) if save_result else daily_payload
    interest_board = runtime.build_interest_automation_board(settings, save_result=save_result)
    automation_digest = build_research_automation_dashboard_digest(runtime, settings)
    result = {
        "status": "success",
        "module": "research_automation_pipeline",
        "ran_at": runtime.current_storage_timestamp(),
        "source_results": source_results,
        "rag_backfill": {
            "updated_count": rag_backfill.get("updated_count"),
            "ticker_count": len(rag_backfill.get("tickers", [])),
        },
        "dossier_count": len(dossier_results),
        "dossiers": dossier_results,
        "failed": failed,
        "daily_brief": daily_brief,
        "interest_board": {
            "target_count": interest_board.get("target_count"),
            "ticker_target_count": interest_board.get("ticker_target_count"),
            "sector_target_count": interest_board.get("sector_target_count"),
            "portfolio_linked_count": interest_board.get("portfolio_linked_count"),
            "rag_connected_count": interest_board.get("rag_connected_count"),
            "thesis_connected_count": interest_board.get("thesis_connected_count"),
            "duplicate_suspected_count": interest_board.get("duplicate_suspected_count"),
            "automation_steps": interest_board.get("automation_steps"),
            "next_actions": interest_board.get("next_actions"),
        },
        "automation_digest": automation_digest,
        "news_inbox": runtime.build_news_inbox_payload(settings, limit=10),
    }
    result["automation_digest"].update(
        {
            "dossier_count": result["dossier_count"],
            "failed_count": len(failed),
            "daily_brief_date": daily_brief.get("date") if isinstance(daily_brief, dict) else None,
            "last_run_at": result["ran_at"],
        }
    )
    runtime.write_json_store(
        runtime.research_automation_status_path(settings),
        {
            "updated_at": result["ran_at"],
            "dossier_count": result["dossier_count"],
            "failed_count": len(failed),
            "rag_updated_count": result["rag_backfill"]["updated_count"],
            "rag_ticker_count": result["rag_backfill"]["ticker_count"],
            "daily_brief_date": daily_brief.get("date") if isinstance(daily_brief, dict) else None,
            "pull_target_count": interest_board.get("target_count"),
            "duplicate_suspected_count": interest_board.get("duplicate_suspected_count"),
            "rag_connected_count": interest_board.get("rag_connected_count"),
            "save_result": save_result,
            "news_inbox_count": result["news_inbox"].get("count"),
            "news_unpromoted_count": result["news_inbox"].get("unpromoted_count"),
        },
    )
    return result
