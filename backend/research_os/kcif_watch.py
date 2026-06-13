"""KCIF macro report watch payload and cache workflows."""

from __future__ import annotations

from typing import Protocol


class KcifWatchRuntime(Protocol):
    """Runtime callbacks supplied by research_os_main while this workflow is split out."""


def read_kcif_reports_watch(runtime: KcifWatchRuntime, settings) -> dict:
    return runtime.read_json_store(runtime.kcif_reports_watch_path(settings), {})


def write_kcif_reports_watch(runtime: KcifWatchRuntime, settings, payload: dict) -> None:
    runtime.write_json_store(runtime.kcif_reports_watch_path(settings), payload)


def build_kcif_reports_watch_payload(
    runtime: KcifWatchRuntime,
    settings,
    *,
    limit: int = 30,
    force: bool = False,
    save_result: bool = True,
) -> dict:
    cache = read_kcif_reports_watch(runtime, settings)
    target_limit = max(1, min(int(limit or 30), 100))
    should_fetch = force or runtime.should_refresh_kcif_cache(cache)
    source_status = "cached"
    auth_status = "not_configured"
    connection_mode = None
    detail_status = "not_checked"
    warnings: list[str] = []
    reports = cache.get("reports", []) if isinstance(cache, dict) else []
    if should_fetch:
        try:
            fetched = runtime.fetch_kcif_report_list_with_status(
                url=settings.kcif_report_list_url,
                limit=target_limit,
                timeout=settings.kcif_timeout_seconds,
                username=settings.kcif_username if settings.kcif_use_login else "",
                password=settings.kcif_password if settings.kcif_use_login else "",
                login_proc_url=settings.kcif_login_proc_url,
            )
            reports = fetched.get("reports") or []
            auth_status = fetched.get("auth_status") or auth_status
            connection_mode = fetched.get("connection_mode")
            source_status = "refreshed"
        except Exception as exc:
            source_status = "cache_fallback" if reports else "failed"
            warnings.append(f"KCIF 목록 확인 실패: {runtime.provider_error_message(exc, settings)}")
    elif isinstance(cache, dict):
        auth_status = cache.get("auth_status") or auth_status
        connection_mode = cache.get("connection_mode")
        detail_status = cache.get("detail_status") or detail_status
    portfolio_payload = runtime.portfolio_store_response(settings)
    interest_payload = runtime.read_interest_list(settings)
    targets = runtime.build_kcif_watch_targets(portfolio_payload, interest_payload)
    enriched_reports = runtime.match_kcif_reports_to_targets(
        [item for item in reports if isinstance(item, dict)],
        targets,
    )
    if source_status == "refreshed" and enriched_reports:
        detail_result = runtime.fetch_kcif_detail_analyses(
            enriched_reports,
            timeout=settings.kcif_timeout_seconds,
            username=settings.kcif_username if settings.kcif_use_login else "",
            password=settings.kcif_password if settings.kcif_use_login else "",
            login_proc_url=settings.kcif_login_proc_url,
            max_reports=min(target_limit, 10),
        )
        detail_status = detail_result.get("detail_status") or "not_checked"
        if detail_result.get("auth_status"):
            auth_status = detail_result.get("auth_status")
        if detail_result.get("connection_mode"):
            connection_mode = detail_result.get("connection_mode")
        detail_analyses = detail_result.get("analyses") or {}
        if detail_status == "failed":
            warnings.append("KCIF 상세 화면 확인 실패: 목록 메타데이터만 저장했습니다.")
        for report in enriched_reports:
            analysis = detail_analyses.get(str(report.get("report_id")))
            if not isinstance(analysis, dict):
                continue
            report["detail_analysis"] = analysis
            combined_themes = list(
                dict.fromkeys(
                    [
                        *(report.get("matched_themes") or []),
                        *(analysis.get("matched_themes") or []),
                    ]
                )
            )
            report["matched_themes"] = combined_themes[:8]
            if analysis.get("source_summary_available"):
                report["relevance_score"] = min(100, int(report.get("relevance_score") or 0) + 6)
    if settings.kcif_use_login and not (settings.kcif_username and settings.kcif_password):
        warnings.append("KCIF_LOGIN 설정은 켜져 있지만 KCIF_USERNAME/KCIF_PASSWORD가 없어 비로그인 목록만 확인했습니다.")
    related_reports = [item for item in enriched_reports if item.get("relevance_score", 0) > 0]
    top_related = related_reports[: min(target_limit, 30)]
    payload = {
        "status": "success" if source_status != "failed" else "warning",
        "module": "kcif_reports_watch",
        "source_status": source_status,
        "auth_status": auth_status,
        "connection_mode": connection_mode,
        "detail_status": detail_status,
        "as_of": runtime.current_storage_timestamp(),
        "source_url": settings.kcif_report_list_url or runtime.kcif_report_list_url_default,
        "report_count": len(enriched_reports),
        "related_count": len(related_reports),
        "target_count": len(targets),
        "reports": enriched_reports[:target_limit],
        "related_reports": top_related,
        "policy": runtime.kcif_copyright_policy(),
        "warnings": warnings,
        "next_actions": build_kcif_watch_next_actions(top_related, warnings),
    }
    if save_result:
        write_kcif_reports_watch(
            runtime,
            settings,
            {
                "updated_at": payload["as_of"],
                "source_status": source_status,
                "auth_status": auth_status,
                "connection_mode": connection_mode,
                "detail_status": detail_status,
                "reports": enriched_reports[:100],
                "related_reports": top_related,
                "policy": payload["policy"],
                "warnings": warnings,
            },
        )
        payload["storage_path"] = str(runtime.kcif_reports_watch_path(settings))
    return payload


def build_kcif_watch_next_actions(related_reports: list[dict], warnings: list[str]) -> list[str]:
    actions = []
    if warnings:
        actions.append("KCIF 목록 확인이 지연되면 이전 캐시를 기준으로 관련성만 먼저 점검하세요.")
    if related_reports:
        top = related_reports[0]
        themes = ", ".join(top.get("matched_themes") or []) or "매크로"
        actions.append(f"최상위 관련 보고서 `{top.get('title')}`를 {themes} 관점의 시장일지 후보로 검토하세요.")
        actions.append("필요한 경우 KCIF 사이트에서 사용자가 직접 원문을 열람한 뒤 핵심 메모만 정보입력에 붙여넣으세요.")
    else:
        actions.append("새 KCIF 보고서와 보유·관심종목 간 직접 매칭은 낮습니다. 금리/환율/유가 같은 테마만 시장일지에 참고하세요.")
    actions.append("KCIF 원문/PDF는 자동 저장하지 않고 제목·분류·날짜·링크·자체 관련성 분석만 보관합니다.")
    return actions[:5]
