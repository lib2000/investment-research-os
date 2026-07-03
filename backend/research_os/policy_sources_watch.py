"""Official policy source watch payload, cache, and news-inbox sync workflows."""

from __future__ import annotations

from typing import Protocol

from research_os.news_inbox import canonical_news_url


class PolicySourcesWatchRuntime(Protocol):
    """Runtime callbacks supplied by research_os_main while this workflow is split out."""


def read_policy_sources_watch(runtime: PolicySourcesWatchRuntime, settings) -> dict:
    return runtime.read_json_store(runtime.policy_sources_watch_path(settings), {})


def write_policy_sources_watch(runtime: PolicySourcesWatchRuntime, settings, payload: dict) -> None:
    runtime.write_json_store(runtime.policy_sources_watch_path(settings), payload)


def build_policy_sources_next_actions(related_items: list[dict], warnings: list[str]) -> list[str]:
    actions: list[str] = []
    if warnings:
        actions.append("공식 정책 소스 확인이 지연되면 기존 캐시 기준으로 정책/규제 신호만 먼저 검토하세요.")
    if related_items:
        top = related_items[0]
        provider = top.get("source_provider") or "공식 정책 소스"
        themes = ", ".join(top.get("matched_themes") or []) or "정책/규제"
        actions.append(f"{provider} `{top.get('title')}`를 {themes} 관점의 투자 메모 후보로 확인하세요.")
        actions.append("정책 적용 시점, 대상 업종, 수혜/피해 종목을 원문 링크에서 직접 확인한 뒤 투자 판단에 반영하세요.")
    else:
        actions.append("보유·관심종목과 직접 매칭되는 공식 정책자료는 아직 낮습니다. 정책/법령 필터에서 방향성만 확인하세요.")
    actions.append("저작권 보호를 위해 원문 본문은 자동 저장하지 않고 메타데이터와 자체 분류·관련성 점수만 보관합니다.")
    return actions[:5]


def _policy_item_source_url(item: dict) -> str:
    return str(item.get("detail_url") or item.get("source_url") or "").strip()


def _policy_item_fingerprint(runtime: PolicySourcesWatchRuntime, item: dict) -> str:
    return runtime.news_item_fingerprint(
        str(item.get("title") or ""),
        "",
        _policy_item_source_url(item),
    )


def sync_policy_items_to_news_inbox(
    runtime: PolicySourcesWatchRuntime,
    settings,
    items: list[dict],
    *,
    limit: int = 40,
) -> int:
    inbox = runtime.read_news_inbox(settings)
    existing_items = list(inbox.get("items") or []) if isinstance(inbox, dict) else []
    existing_keys = {
        str(item.get("fingerprint") or item.get("id") or item.get("source_url") or "")
        for item in existing_items
        if isinstance(item, dict)
    }
    existing_keys.update(
        str(item.get("source_url") or "")
        for item in existing_items
        if isinstance(item, dict) and str(item.get("source_url") or "")
    )
    existing_by_source_url = {
        str(item.get("source_url") or ""): item
        for item in existing_items
        if isinstance(item, dict) and str(item.get("source_url") or "")
    }
    existing_by_canonical_url = {
        canonical_news_url(item.get("source_url")): item
        for item in existing_items
        if isinstance(item, dict) and canonical_news_url(item.get("source_url"))
    }
    now = runtime.current_storage_timestamp()
    created: list[dict] = []
    changed_existing = False
    for item in items[: max(1, int(limit or 40))]:
        if not isinstance(item, dict):
            continue
        source_url = _policy_item_source_url(item)
        title = str(item.get("title") or "").strip()
        if not source_url or not title:
            continue
        fingerprint = _policy_item_fingerprint(runtime, item)
        source_canonical_url = canonical_news_url(source_url)
        if (
            fingerprint in existing_keys
            or source_url in existing_keys
            or (source_canonical_url and source_canonical_url in existing_by_canonical_url)
        ):
            existing = existing_by_source_url.get(source_url) or existing_by_canonical_url.get(source_canonical_url)
            if isinstance(existing, dict) and len(title) < len(str(existing.get("title") or title)):
                existing["title"] = title
                existing["summary"] = f"{item.get('source_provider') or item.get('agency') or '공식기관'} {item.get('published_at') or ''} {title}".strip()
                existing["raw_content"] = "\n".join(
                    [
                        "공식 정책자료 메타데이터",
                        f"기관: {item.get('source_provider') or item.get('agency') or '기관 미확인'}",
                        f"제목: {title}",
                        f"발행일: {item.get('published_at') or '일자 미확인'}",
                        f"링크: {source_url}",
                        "본문 저장 정책: 공식 원문 본문은 자동 저장하지 않고 링크와 자체 분류만 보관합니다.",
                    ]
                )
                existing["updated_at"] = now
                changed_existing = True
            continue
        classification = runtime.infer_news_policy_law_classification(
            " ".join(
                [
                    title,
                    str(item.get("source_provider") or ""),
                    str(item.get("source_scope") or ""),
                    " ".join(item.get("matched_themes") or []),
                ]
            )
        )
        tags = sorted(
            set(
                [
                    "news_inbox",
                    "official_policy_source",
                    "policy_law",
                    "policy_or_regulation",
                    "research_scope:policy",
                    *(classification.get("tags") or []),
                    *(f"policy_theme:{theme}" for theme in (item.get("matched_themes") or [])[:5]),
                ]
            )
        )
        raw_content = "\n".join(
            [
                "공식 정책자료 메타데이터",
                f"기관: {item.get('source_provider') or item.get('agency') or '기관 미확인'}",
                f"제목: {title}",
                f"발행일: {item.get('published_at') or '일자 미확인'}",
                f"링크: {source_url}",
                "본문 저장 정책: 공식 원문 본문은 자동 저장하지 않고 링크와 자체 분류만 보관합니다.",
            ]
        )
        news_item = {
            "id": fingerprint[:16],
            "fingerprint": fingerprint,
            "title": title,
            "scope": "POLICY",
            "scope_label": runtime.news_scope_label("POLICY"),
            "scope_reason": "official_policy_source",
            "source_type": "news",
            "source_url": source_url,
            "raw_content": raw_content,
            "summary": f"{item.get('source_provider') or item.get('agency') or '공식기관'} {item.get('published_at') or ''} {title}".strip(),
            "safe_user_note": "공식 정책자료 메타데이터 기반 항목입니다. 원문 링크에서 세부 내용과 적용 시점을 직접 확인하세요.",
            "confidence": 0.84,
            "tags": tags,
            "policy_law_classification": classification,
            "policy_law": classification,
            "is_policy_law": True,
            "official_policy_source": True,
            "matched_themes": item.get("matched_themes") or [],
            "target_matches": item.get("target_matches") or [],
            "relevance_score": item.get("relevance_score") or 0,
            "copyright_policy": runtime.policy_sources_copyright_policy(),
            "capture_quality": {"status": "정상", "readiness": "공식 정책자료 메타데이터 저장", "warnings": []},
            "source_url_processing": {
                "status": "metadata_only",
                "full_text_stored": False,
                "source_family": "official_policy_source",
            },
            "needs_body_copy": False,
            "url_text_unavailable": False,
            "created_at": now,
            "updated_at": now,
            "promoted": False,
            "promoted_storage": None,
        }
        created.append(news_item)
        existing_keys.add(fingerprint)
        existing_keys.add(source_url)
        if source_canonical_url:
            existing_by_canonical_url[source_canonical_url] = news_item
    if created or changed_existing:
        runtime.write_news_inbox(settings, {"items": created + existing_items})
    return len(created)


def build_policy_sources_watch_payload(
    runtime: PolicySourcesWatchRuntime,
    settings,
    *,
    limit: int = 40,
    force: bool = False,
    save_result: bool = True,
) -> dict:
    cache = read_policy_sources_watch(runtime, settings)
    target_limit = max(1, min(int(limit or 40), 100))
    source_status = "cached"
    warnings: list[str] = []
    source_results = cache.get("source_results", []) if isinstance(cache, dict) else []
    items = cache.get("items", []) if isinstance(cache, dict) else []
    if not settings.policy_sources_enabled:
        warnings.append("POLICY_SOURCES_ENABLED가 꺼져 있어 캐시만 표시합니다.")
        source_status = "disabled"
    else:
        should_fetch = force or runtime.should_refresh_policy_sources_cache(
            cache,
            refresh_hours=settings.policy_sources_refresh_hours,
        )
        if should_fetch:
            try:
                items, fetch_warnings, source_results = runtime.fetch_policy_sources(
                    limit=target_limit,
                    timeout=settings.policy_sources_timeout_seconds,
                    user_agent=settings.policy_sources_user_agent,
                )
                warnings.extend(fetch_warnings)
                source_status = "refreshed"
            except Exception as exc:
                source_status = "cache_fallback" if items else "failed"
                warnings.append(f"공식 정책 소스 확인 실패: {runtime.provider_error_message(exc, settings)}")
    portfolio_payload = runtime.portfolio_store_response(settings)
    interest_payload = runtime.read_interest_list(settings)
    targets = runtime.build_kcif_watch_targets(portfolio_payload, interest_payload)
    enriched_items = runtime.match_policy_items_to_targets(
        [item for item in items if isinstance(item, dict)],
        targets,
    )
    related_items = [item for item in enriched_items if int(item.get("relevance_score") or 0) > 0]
    top_related = related_items[: min(target_limit, 30)]
    synced_count = 0
    if save_result and source_status != "failed":
        synced_count = sync_policy_items_to_news_inbox(runtime, settings, top_related or enriched_items, limit=target_limit)
    payload = {
        "status": "success" if source_status != "failed" else "warning",
        "module": "policy_sources_watch",
        "source_status": source_status,
        "as_of": runtime.current_storage_timestamp(),
        "source_results": source_results,
        "item_count": len(enriched_items),
        "related_count": len(related_items),
        "target_count": len(targets),
        "news_inbox_synced_count": synced_count,
        "items": enriched_items[:target_limit],
        "related_items": top_related,
        "policy": runtime.policy_sources_copyright_policy(),
        "warnings": warnings,
        "next_actions": build_policy_sources_next_actions(top_related, warnings),
    }
    if save_result:
        write_policy_sources_watch(
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
                "news_inbox_synced_count": synced_count,
            },
        )
        payload["storage_path"] = str(runtime.policy_sources_watch_path(settings))
    return payload
