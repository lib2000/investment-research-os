"""Regional business source watch payload and cache workflows."""

from __future__ import annotations

from typing import Protocol


class RegionalBusinessWatchRuntime(Protocol):
    """Runtime callbacks supplied by research_os_main while this workflow is split out."""


def read_regional_business_sources_watch(runtime: RegionalBusinessWatchRuntime, settings) -> dict:
    return runtime.read_json_store(runtime.regional_business_sources_watch_path(settings), {})


def write_regional_business_sources_watch(runtime: RegionalBusinessWatchRuntime, settings, payload: dict) -> None:
    runtime.write_json_store(runtime.regional_business_sources_watch_path(settings), payload)


def build_regional_business_watch_next_actions(related_items: list[dict], warnings: list[str]) -> list[str]:
    actions: list[str] = []
    if warnings:
        actions.append("EMERiCs/CSF/KIEP 목록 확인이 지연되면 이전 캐시 기준으로 관련 테마만 먼저 확인하세요.")
    if related_items:
        top = related_items[0]
        provider = top.get("source_provider") or "지역 포털"
        themes = ", ".join(top.get("matched_themes") or []) or "해외 비즈니스"
        actions.append(f"{provider} `{top.get('title')}`를 {themes} 관점의 시장일지/매크로 분석 후보로 검토하세요.")
        actions.append("보유종목과 직접 연결되는 경우 원문 링크를 열어 핵심 투자 메모만 정보입력에 별도로 남기세요.")
    else:
        actions.append(
            "보유·관심종목과 직접 매칭되는 EMERiCs/CSF/KIEP 자료는 아직 낮습니다. 중국/신흥국/세계경제 테마 변화만 참고하세요."
        )
    actions.append("저작권 보호를 위해 원문 본문은 자동 저장하지 않고 제목·기관·발행일·링크·관련성 점수만 보관합니다.")
    return actions[:5]


def merge_cached_regional_items_for_failed_sources(
    fetched_items: list[dict],
    source_results: list[dict],
    cache: dict,
) -> tuple[list[dict], list[dict], int]:
    if not isinstance(cache, dict) or not isinstance(source_results, list):
        return fetched_items, source_results, 0
    failed_providers = {
        str(item.get("provider") or "")
        for item in source_results
        if isinstance(item, dict) and item.get("status") != "success"
    }
    failed_providers.discard("")
    if not failed_providers:
        return fetched_items, source_results, 0
    merged_items = list(fetched_items)
    seen_ids = {str(item.get("item_id") or "") for item in merged_items if isinstance(item, dict)}
    cached_count_by_provider: dict[str, int] = {provider: 0 for provider in failed_providers}
    for item in cache.get("items") or []:
        if not isinstance(item, dict):
            continue
        provider = str(item.get("source_provider") or "")
        item_id = str(item.get("item_id") or "")
        if provider not in failed_providers or not item_id or item_id in seen_ids:
            continue
        merged_items.append(item)
        seen_ids.add(item_id)
        cached_count_by_provider[provider] = cached_count_by_provider.get(provider, 0) + 1
    merged_results = []
    for item in source_results:
        if not isinstance(item, dict):
            continue
        provider = str(item.get("provider") or "")
        cached_count = cached_count_by_provider.get(provider, 0)
        if cached_count and item.get("status") != "success":
            merged_results.append({**item, "status": "cache_fallback", "cached_item_count": cached_count})
        else:
            merged_results.append(item)
    return merged_items, merged_results, sum(cached_count_by_provider.values())


def build_regional_business_sources_watch_payload(
    runtime: RegionalBusinessWatchRuntime,
    settings,
    *,
    limit: int = 40,
    force: bool = False,
    save_result: bool = True,
) -> dict:
    cache = read_regional_business_sources_watch(runtime, settings)
    target_limit = max(1, min(int(limit or 40), 100))
    source_status = "cached"
    warnings: list[str] = []
    source_results = cache.get("source_results", []) if isinstance(cache, dict) else []
    items = cache.get("items", []) if isinstance(cache, dict) else []
    if not settings.regional_business_sources_enabled:
        warnings.append("REGIONAL_BUSINESS_SOURCES_ENABLED가 꺼져 있어 캐시만 표시합니다.")
        source_status = "disabled"
    else:
        should_fetch = force or runtime.should_refresh_regional_business_cache(cache)
        if should_fetch:
            try:
                items, fetch_warnings, source_results = runtime.fetch_regional_business_sources(
                    limit=target_limit,
                    timeout=settings.regional_business_sources_timeout_seconds,
                    user_agent=settings.regional_business_sources_user_agent,
                )
                items, source_results, restored_count = merge_cached_regional_items_for_failed_sources(
                    items,
                    source_results,
                    cache if isinstance(cache, dict) else {},
                )
                if restored_count:
                    warnings.append(f"일부 소스 실패로 기존 캐시 {restored_count}건을 보존했습니다.")
                    source_status = "cache_fallback"
                warnings.extend(fetch_warnings)
                if source_status != "cache_fallback":
                    source_status = "refreshed"
            except Exception as exc:
                source_status = "cache_fallback" if items else "failed"
                warnings.append(f"EMERiCs/CSF/KIEP 목록 확인 실패: {runtime.provider_error_message(exc, settings)}")
    portfolio_payload = runtime.portfolio_store_response(settings)
    interest_payload = runtime.read_interest_list(settings)
    targets = runtime.build_kcif_watch_targets(portfolio_payload, interest_payload)
    enriched_items = runtime.match_regional_business_items_to_targets(
        [item for item in items if isinstance(item, dict)],
        targets,
    )
    related_items = [item for item in enriched_items if int(item.get("relevance_score") or 0) > 0]
    top_related = related_items[: min(target_limit, 30)]
    payload = {
        "status": "success" if source_status != "failed" else "warning",
        "module": "regional_business_sources_watch",
        "source_status": source_status,
        "as_of": runtime.current_storage_timestamp(),
        "source_results": source_results,
        "item_count": len(enriched_items),
        "related_count": len(related_items),
        "target_count": len(targets),
        "items": enriched_items[:target_limit],
        "related_items": top_related,
        "policy": runtime.regional_business_copyright_policy(),
        "warnings": warnings,
        "next_actions": build_regional_business_watch_next_actions(top_related, warnings),
    }
    if save_result:
        write_regional_business_sources_watch(
            runtime,
            settings,
            {
                "updated_at": payload["as_of"],
                "source_status": source_status,
                "source_results": source_results,
                "items": enriched_items[:100],
                "related_items": top_related,
                "policy": payload["policy"],
                "warnings": warnings,
            },
        )
        payload["storage_path"] = str(runtime.regional_business_sources_watch_path(settings))
    return payload
