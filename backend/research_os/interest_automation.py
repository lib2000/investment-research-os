"""Interest and portfolio automation target board workflows."""

from __future__ import annotations

from re import sub
from typing import Protocol


class InterestAutomationRuntime(Protocol):
    """Runtime callbacks supplied by research_os_main while this workflow is split out."""


def compact_interest_text(value: object, max_length: int = 180) -> str:
    text = sub(r"\s+", " ", str(value or "")).strip()
    return text[:max_length].rstrip() + ("..." if len(text) > max_length else "")


def target_keyword_candidates(*values: object) -> list[str]:
    keywords: list[str] = []
    seen: set[str] = set()
    for value in values:
        if isinstance(value, list):
            iterable = value
        else:
            iterable = [value]
        for item in iterable:
            text = str(item or "").strip()
            if not text:
                continue
            for piece in [text, *[part.strip() for part in text.replace("/", ",").split(",")]]:
                if len(piece) < 2:
                    continue
                key = piece.lower()
                if key not in seen:
                    seen.add(key)
                    keywords.append(piece)
    return keywords[:12]


def manifest_entries_matching_keywords(entries: list[dict], keywords: list[str], limit: int = 30) -> list[dict]:
    normalized_keywords = [keyword.lower() for keyword in keywords if keyword]
    matched: list[dict] = []
    for entry in entries:
        haystack = " ".join(
            str(entry.get(field) or "")
            for field in ["ticker", "title", "summary", "source_url", "type"]
        ).lower()
        tags = " ".join(str(tag or "") for tag in (entry.get("tags") or [])).lower()
        if any(keyword in haystack or keyword in tags for keyword in normalized_keywords):
            matched.append(entry)
        if len(matched) >= limit:
            break
    return matched


def market_journal_matches_for_keywords(runtime: InterestAutomationRuntime, settings, keywords: list[str], limit: int = 5) -> list[dict]:
    payload = runtime.read_market_close_journal(settings)
    normalized_keywords = [keyword.lower() for keyword in keywords if keyword]
    results: list[dict] = []
    for item in sorted(
        [entry for entry in payload.get("entries", []) if isinstance(entry, dict)],
        key=lambda entry: (entry.get("session_date") or "", entry.get("updated_at") or ""),
        reverse=True,
    ):
        text = " ".join(
            [
                str(item.get("raw_summary") or ""),
                " ".join(str(value or "") for value in item.get("key_drivers", []) or []),
                " ".join(str(value or "") for value in item.get("sector_implications", []) or []),
                " ".join(str(value or "") for value in item.get("interest_implications", []) or []),
                " ".join(str(value or "") for value in item.get("tags", []) or []),
            ]
        ).lower()
        if any(keyword in text for keyword in normalized_keywords):
            results.append(
                {
                    "market": item.get("market"),
                    "session_date": item.get("session_date"),
                    "sentiment": item.get("sentiment"),
                    "risk_level": item.get("risk_level"),
                    "summary": compact_interest_text(item.get("raw_summary"), 220),
                }
            )
        if len(results) >= limit:
            break
    return results


def interest_ticker_target(
    runtime: InterestAutomationRuntime,
    item: dict,
    *,
    settings,
    manifest_entries: list[dict],
    rag_counts: dict[str, int],
    source_label: str,
) -> dict:
    raw_symbol = str(item.get("ticker") or "").strip()
    verification = runtime.verify_ticker_symbol_local_cached(raw_symbol, settings)
    ticker = runtime.normalize_ticker(verification.official_symbol or raw_symbol)
    profile = runtime.official_ticker_profile(ticker, settings, refresh_external=False) if verification.verified else {}
    company_name = (
        verification.company_name
        or item.get("company_name")
        or item.get("companyName")
        or profile.get("company_name")
        or ticker
    )
    tags = [str(tag) for tag in (item.get("tags") or []) if str(tag).strip()]
    keywords = target_keyword_candidates(
        ticker,
        company_name,
        profile.get("sector"),
        profile.get("industry"),
        profile.get("business_context"),
        item.get("thesis"),
        item.get("notes"),
        tags,
    )
    target_entries = [
        entry
        for entry in manifest_entries
        if runtime.normalize_ticker(str(entry.get("ticker") or "")) == ticker
    ]
    if not target_entries:
        target_entries = manifest_entries_matching_keywords(manifest_entries, keywords, limit=30)
    unique_entries, duplicate_entries = runtime.dedupe_manifest_entries_by_similarity(
        target_entries,
        runtime.resolve_vault_dir(settings.research_vault_dir),
        limit=20,
    )
    rag_count = rag_counts.get(ticker) or 0
    snapshot = None
    try:
        snapshot = runtime.read_ticker_thesis_snapshot(runtime.resolve_vault_dir(settings.research_vault_dir), ticker)
    except Exception:
        snapshot = None
    return {
        "scope": "ticker",
        "source": source_label,
        "ticker": ticker,
        "company_name": company_name,
        "priority": item.get("priority") or "medium",
        "verified": verification.verified,
        "exchange": verification.exchange,
        "country": verification.country,
        "sector": profile.get("sector") or "미분류",
        "keywords": keywords,
        "tags": sorted(set([*tags, profile.get("sector") or "", profile.get("industry") or ""]))[:12],
        "collection_sources": [
            "신한/네이버 리서치",
            "DART/Finnhub/Tiingo/KIS 데이터",
            "정보입력 URL·파일",
            "시장일지",
        ],
        "rag_query_examples": [
            f"{company_name} 최근 악재",
            f"{company_name} 강세 논거",
            f"{company_name} 실적 수급",
            f"{company_name} 리스크와 밸류에이션",
        ],
        "recent_document_count": len(target_entries),
        "unique_document_count": len(unique_entries),
        "duplicate_suspected_count": len(duplicate_entries),
        "rag_document_count": rag_count,
        "thesis_snapshot_connected": bool(snapshot),
        "market_journal_matches": market_journal_matches_for_keywords(runtime, settings, keywords),
        "next_action": (
            "Dossier/팀 리포트 갱신으로 최신 투자 논거를 합성하세요."
            if rag_count or target_entries
            else "관련 뉴스·리포트·시장일지를 먼저 정보입력 또는 자동수집으로 적재하세요."
        ),
    }


def interest_sector_target(
    runtime: InterestAutomationRuntime,
    item: dict,
    *,
    settings,
    manifest_entries: list[dict],
) -> dict:
    name = str(item.get("name") or "").strip()
    tags = [str(tag) for tag in (item.get("tags") or []) if str(tag).strip()]
    keywords = target_keyword_candidates(
        name,
        item.get("region"),
        item.get("thesis"),
        item.get("notes"),
        tags,
    )
    target_entries = manifest_entries_matching_keywords(manifest_entries, keywords, limit=40)
    unique_entries, duplicate_entries = runtime.dedupe_manifest_entries_by_similarity(
        target_entries,
        runtime.resolve_vault_dir(settings.research_vault_dir),
        limit=20,
    )
    return {
        "scope": "sector",
        "source": "interest_sector",
        "name": name,
        "region": item.get("region") or "GLOBAL",
        "priority": item.get("priority") or "medium",
        "keywords": keywords,
        "tags": sorted(set([*tags, name]))[:12],
        "collection_sources": [
            "신한/네이버 산업 리포트",
            "Tavily/Brave 웹 검색",
            "시장일지",
            "정보입력 URL·파일",
        ],
        "rag_query_examples": [
            f"{name} 수혜 종목",
            f"{name} 최근 리스크",
            f"{name} 정책과 수급",
            f"{name} 장기 성장 논거",
        ],
        "recent_document_count": len(target_entries),
        "unique_document_count": len(unique_entries),
        "duplicate_suspected_count": len(duplicate_entries),
        "market_journal_matches": market_journal_matches_for_keywords(runtime, settings, keywords),
        "next_action": "시장일지와 저장 데이터를 함께 검색해 섹터 강세/약세 논거를 재합성하세요.",
    }


def build_interest_automation_board(runtime: InterestAutomationRuntime, settings, *, save_result: bool = True) -> dict:
    vault_dir = runtime.resolve_vault_dir(settings.research_vault_dir)
    manifest_entries = sorted(
        [entry for entry in runtime.read_manifest(vault_dir) if isinstance(entry, dict)],
        key=runtime.manifest_entry_sort_key,
        reverse=True,
    )
    interest_payload = runtime.read_interest_list(settings)
    portfolio_payload = runtime.portfolio_store_response(settings)
    portfolio_items: dict[str, dict] = {}
    for portfolio in portfolio_payload.portfolios:
        for holding in portfolio.holdings:
            ticker = runtime.normalize_ticker(holding.ticker)
            if not ticker or ticker in {"UNKNOWN", "CASH"}:
                continue
            portfolio_items.setdefault(
                ticker,
                {
                    "ticker": ticker,
                    "company_name": holding.name,
                    "priority": "high" if (holding.market_value or 0) > 0 else "medium",
                    "thesis": "보유 포트폴리오 종목으로 자동 수집 대상",
                    "tags": holding.theme_tags,
                },
            )

    interest_ticker_items = [
        item for item in interest_payload.get("tickers", []) if isinstance(item, dict)
    ]
    explicit_symbols = {runtime.normalize_ticker(str(item.get("ticker") or "")) for item in interest_ticker_items}
    merged_ticker_items = [
        {**item, "_source_label": "interest_ticker"} for item in interest_ticker_items
    ]
    for ticker, item in portfolio_items.items():
        if ticker not in explicit_symbols:
            merged_ticker_items.append({**item, "_source_label": "portfolio_holding"})

    rag_counts = runtime.count_research_memory_documents_by_ticker(
        vault_dir,
        [runtime.normalize_ticker(str(item.get("ticker") or "")) for item in merged_ticker_items],
    )
    ticker_targets = [
        interest_ticker_target(
            runtime,
            item,
            settings=settings,
            manifest_entries=manifest_entries,
            rag_counts=rag_counts,
            source_label=item.get("_source_label") or "interest_ticker",
        )
        for item in merged_ticker_items
        if item.get("ticker")
    ]
    sector_targets = [
        interest_sector_target(runtime, item, settings=settings, manifest_entries=manifest_entries)
        for item in interest_payload.get("sectors", [])
        if isinstance(item, dict) and item.get("name")
    ]
    unique_recent, duplicate_recent = runtime.dedupe_manifest_entries_by_similarity(
        manifest_entries,
        vault_dir,
        limit=40,
    )
    all_queries = []
    for target in [*ticker_targets, *sector_targets]:
        for query in target.get("rag_query_examples", []):
            if query not in all_queries:
                all_queries.append(query)
    payload = {
        "status": "success",
        "module": "interest_automation_board",
        "as_of": runtime.current_storage_timestamp(),
        "target_count": len(ticker_targets) + len(sector_targets),
        "ticker_target_count": len(ticker_targets),
        "sector_target_count": len(sector_targets),
        "portfolio_linked_count": sum(1 for item in ticker_targets if item.get("source") == "portfolio_holding"),
        "rag_connected_count": sum(1 for item in ticker_targets if item.get("rag_document_count", 0) > 0),
        "thesis_connected_count": sum(1 for item in ticker_targets if item.get("thesis_snapshot_connected")),
        "duplicate_suspected_count": len(duplicate_recent),
        "recent_unique_document_count": len(unique_recent),
        "ticker_targets": sorted(
            ticker_targets,
            key=lambda item: (
                {"high": 2, "medium": 1, "low": 0}.get(str(item.get("priority")), 1),
                item.get("recent_document_count", 0),
                item.get("rag_document_count", 0),
            ),
            reverse=True,
        ),
        "sector_targets": sorted(
            sector_targets,
            key=lambda item: (
                {"high": 2, "medium": 1, "low": 0}.get(str(item.get("priority")), 1),
                item.get("recent_document_count", 0),
            ),
            reverse=True,
        ),
        "rag_search_prompts": all_queries[:30],
        "automation_steps": [
            "Pulls: 보유종목·관심종목·관심섹터 키워드로 뉴스/공시/리포트/시장일지 후보를 수집합니다.",
            "De-dupes: source_url, content_hash, 제목·본문 유사도로 중복 자료를 묶습니다.",
            "Embeds: 저장 데이터는 RAG 색인으로 들어가 자연어 검색과 재합성에 사용됩니다.",
            "Tags: 종목, 섹터, 테마, 실적, 수급, 금리, 정책, 리스크 태그를 자동 부여합니다.",
            "Syntheses/Delivers: 검색 결과와 Dossier를 합성해 일일 브리핑·대시보드·시장일지에 반영합니다.",
        ],
        "next_actions": [
            "관심목록을 저장한 뒤 자동화 보드를 다시 생성하면 새 수집 대상이 즉시 반영됩니다.",
            "RAG 검색어 예시를 저장 데이터 화면에서 실행하면 강세/약세/핵심 쟁점 합성 보고서로 이어집니다.",
            "시장일지에 같은 키워드가 들어오면 관심섹터와 관심종목의 확인 포인트로 자동 연결됩니다.",
        ],
    }
    if save_result:
        runtime.write_json_store(
            runtime.interest_collection_targets_path(settings),
            {
                "updated_at": payload["as_of"],
                "payload": payload,
            },
        )
        payload["storage_path"] = str(runtime.interest_collection_targets_path(settings))
    return payload
