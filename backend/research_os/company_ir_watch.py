"""Company IR and SEC source watch payload workflows."""

from __future__ import annotations

from typing import Protocol


class CompanyIrWatchRuntime(Protocol):
    """Runtime callbacks supplied by research_os_main while this workflow is split out."""


def read_company_ir_sources_watch(runtime: CompanyIrWatchRuntime, settings) -> dict:
    return runtime.read_json_store(runtime.company_ir_sources_watch_path(settings), {})


def write_company_ir_sources_watch(runtime: CompanyIrWatchRuntime, settings, payload: dict) -> None:
    runtime.write_json_store(runtime.company_ir_sources_watch_path(settings), payload)


def company_ir_item_matches_targets(runtime: CompanyIrWatchRuntime, item: dict, target_terms: dict) -> bool:
    ticker = runtime.normalize_ticker(str(item.get("ticker") or ""))
    ticker_set = target_terms.get("ticker_set") or set(target_terms.get("tickers") or [])
    if ticker and ticker in ticker_set:
        return True
    text = " ".join(
        str(item.get(key) or "")
        for key in ["company_name", "title", "detail_url", "source_provider", "source_scope"]
    ).lower()
    for name in target_terms.get("names") or []:
        cleaned = str(name or "").strip().lower()
        if cleaned and cleaned in text:
            return True
    return False


def build_company_ir_sources_next_actions(
    related_items: list[dict],
    warnings: list[str],
    *,
    fallback_covered_count: int = 0,
) -> list[str]:
    actions = [
        "회사 IR/SEC 자료는 보유·관심 종목과 연결되면 공개 IR 저장 데이터와 RAG에 자동 반영됩니다.",
        "본문 추출이 짧은 항목은 URL-only/본문 보강 필요로 남기고 추천 점수 가산에서 제외합니다.",
    ]
    if fallback_covered_count:
        actions.append(
            f"직접 IR 원천 장애 {fallback_covered_count}건은 공식 SEC EDGAR 제출자료로 대체되어 미해결 실패에서 제외됩니다."
        )
    if warnings:
        actions.append("목록 확인 실패가 있으면 기존 캐시를 기준으로 최근 1주 자료를 유지하고 다음 주기에 재시도하세요.")
    if related_items:
        actions.append(f"관련 IR 보도자료 {len(related_items)}건을 최근 1주 자료와 JOBY Dossier 검토에 활용하세요.")
    return actions


def build_company_ir_sources_watch_payload(
    runtime: CompanyIrWatchRuntime,
    settings,
    *,
    limit: int = 20,
    force: bool = False,
    save_result: bool = True,
) -> dict:
    cache = read_company_ir_sources_watch(runtime, settings)
    normalized_limit = max(1, min(int(limit or settings.company_ir_sources_max_items or 20), 100))
    warnings: list[str] = []
    source_results: list[dict] = []
    items: list[dict] = []
    source_status = "cached"
    if not settings.company_ir_sources_enabled:
        payload = {
            "status": "disabled",
            "module": "company_ir_sources_watch",
            "updated_at": runtime.current_storage_timestamp(),
            "items": [],
            "related_items": [],
            "source_results": [],
            "warnings": ["COMPANY_IR_SOURCES_ENABLED=false 상태입니다."],
            "source_status": "disabled",
            "policy": runtime.company_ir_copyright_policy(),
            "next_actions": ["회사 IR 자동 소스를 사용하려면 COMPANY_IR_SOURCES_ENABLED=true로 설정하세요."],
        }
        if save_result:
            write_company_ir_sources_watch(runtime, settings, payload)
        return payload
    should_fetch = force or runtime.should_refresh_company_ir_cache(
        cache,
        refresh_hours=settings.company_ir_sources_refresh_hours,
    )
    if should_fetch:
        try:
            items, warnings, source_results = runtime.fetch_company_ir_sources(
                limit=normalized_limit,
                timeout=settings.company_ir_sources_timeout_seconds,
                user_agent=settings.company_ir_sources_user_agent,
                sources=runtime.configured_company_ir_sources(settings.company_ir_sources_json),
            )
            source_status = "success"
        except Exception as exc:
            warnings.append(f"회사 IR 목록 확인 실패: {runtime.provider_error_message(exc, settings)}")
            items = cache.get("items") or [] if isinstance(cache, dict) else []
            source_results = cache.get("source_results") or [] if isinstance(cache, dict) else []
            source_status = "cache_fallback" if items else "failed"
    else:
        items = cache.get("items") or [] if isinstance(cache, dict) else []
        source_results = cache.get("source_results") or [] if isinstance(cache, dict) else []
    target_terms = runtime.recent_activity_target_terms(settings)
    related_items = [item for item in items if company_ir_item_matches_targets(runtime, item, target_terms)]
    fallback_sources = [
        item
        for item in source_results
        if isinstance(item, dict)
        and (item.get("status") == "fallback_success" or item.get("fallback_status") == "success")
    ]
    unresolved_sources = [
        item
        for item in source_results
        if isinstance(item, dict)
        and item.get("status") not in {None, "success", "fallback_success"}
        and item.get("fallback_status") != "success"
    ]
    direct_failure_count = sum(
        1
        for item in source_results
        if isinstance(item, dict)
        and (item.get("primary_status") == "failed" or item.get("status") == "failed")
    )
    capture_results: list[dict] = []
    if save_result and related_items:
        for item in related_items[:normalized_limit]:
            detail_url = str(item.get("detail_url") or "").strip()
            ticker = runtime.normalize_ticker(str(item.get("ticker") or ""))
            if not detail_url or not ticker:
                continue
            try:
                result = runtime.collect_public_ir_sec_url(
                    runtime.PublicIrSecCollectRequest(
                        url=detail_url,
                        target_key=ticker,
                        save_result=True,
                        force=False,
                        no_screenshot=True,
                        source_title=str(item.get("title") or ""),
                        source_provider=str(item.get("source_provider") or ""),
                        source_type=str(item.get("source_scope") or ""),
                        source_category=str(item.get("category") or ""),
                        filing_form=str(item.get("filing_form") or ""),
                        filing_group=str(item.get("filing_group") or ""),
                        published_at=str(item.get("published_at") or ""),
                    ),
                    settings,
                )
                capture_results.append(
                    {
                        "ticker": ticker,
                        "title": item.get("title"),
                        "detail_url": detail_url,
                        "status": result.get("status"),
                        "storage": (result.get("storage") or {}).get("relative_path"),
                        "quality": (result.get("capture_quality") or {}).get("status"),
                        "needs_body_copy": (result.get("capture_quality") or {}).get("needs_body_copy"),
                    }
                )
            except Exception as exc:
                capture_results.append(
                    {
                        "ticker": ticker,
                        "title": item.get("title"),
                        "detail_url": detail_url,
                        "status": "failed",
                        "error": str(exc),
                    }
                )
    payload = {
        "status": "success" if source_status in {"success", "cached", "cache_fallback"} else "warning",
        "module": "company_ir_sources_watch",
        "updated_at": runtime.current_storage_timestamp(),
        "source_status": source_status,
        "items": items[:normalized_limit],
        "item_count": len(items),
        "related_items": related_items[:normalized_limit],
        "related_count": len(related_items),
        "capture_results": capture_results,
        "captured_count": sum(1 for item in capture_results if item.get("status") in {"success", "skipped_existing", "url_only_saved"}),
        "source_results": source_results,
        "source_count": len(source_results),
        "source_health_status": "degraded" if unresolved_sources else "fallback_covered" if fallback_sources else "healthy",
        "direct_source_failure_count": direct_failure_count,
        "fallback_covered_count": len(fallback_sources),
        "unresolved_source_failure_count": len(unresolved_sources),
        "warnings": warnings,
        "policy": runtime.company_ir_copyright_policy(),
        "next_actions": build_company_ir_sources_next_actions(
            related_items,
            warnings,
            fallback_covered_count=len(fallback_sources),
        ),
    }
    if save_result:
        payload["storage_path"] = str(runtime.company_ir_sources_watch_path(settings))
        write_company_ir_sources_watch(runtime, settings, payload)
    return payload
