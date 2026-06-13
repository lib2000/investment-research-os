"""News inbox promotion into market journal entries."""

from __future__ import annotations

from typing import Protocol


class NewsMarketJournalRuntime(Protocol):
    """Runtime callbacks supplied by research_os_main while this workflow is split out."""


def market_journal_existing_summary(
    runtime: NewsMarketJournalRuntime,
    settings,
    market: str,
    session_date: str,
) -> str:
    payload = runtime.read_market_close_journal(settings)
    for raw_entry in payload.get("entries", []):
        if not isinstance(raw_entry, dict):
            continue
        if raw_entry.get("market") == market and raw_entry.get("session_date") == session_date:
            return str(raw_entry.get("raw_summary") or "").strip()
    return ""


def save_news_item_to_market_journal(
    runtime: NewsMarketJournalRuntime,
    item: dict,
    settings,
):
    item = runtime.news_item_safe_view(item)
    market = runtime.infer_market_from_news_item(item)
    session_date = runtime.current_storage_date().isoformat()
    report_date = runtime.current_storage_date()
    title = runtime.compact_interest_text(item.get("title") or "뉴스 인박스 자료", 90)
    source_url = str(item.get("source_url") or "").strip()
    summary = str(item.get("raw_content") or item.get("summary") or "").strip()
    existing_summary = market_journal_existing_summary(runtime, settings, market, session_date)
    source_line = f"출처: {source_url}" if source_url else "출처: 뉴스 인박스"
    news_block = "\n".join(
        value
        for value in [
            f"[뉴스 인박스 반영] {title}",
            source_line,
            summary,
        ]
        if value
    )
    combined_summary = "\n\n".join(
        value for value in [existing_summary, news_block] if value
    )

    cleaned_summary = runtime.clean_market_summary_text(combined_summary)
    sentiment, risk_level, regime = runtime.infer_market_close_sentiment(cleaned_summary)
    tags = sorted(set([*runtime.infer_market_tags(cleaned_summary), "news_inbox_market_journal"]))
    auto_utilization_focus = runtime.build_auto_market_utilization_focus(
        market=market,
        tags=tags,
        sentiment=sentiment,
        risk_level=risk_level,
        regime=regime,
        settings=settings,
    )
    interest_implications = runtime.build_market_interest_implications(
        raw_summary=cleaned_summary,
        tags=tags,
        settings=settings,
    )
    now = runtime.current_storage_timestamp()
    entry = runtime.MarketCloseEntry(
        entry_id=f"{market}-{session_date}",
        market=market,
        session_date=session_date,
        raw_summary=cleaned_summary,
        sentiment=sentiment,
        risk_level=risk_level,
        regime=regime,
        auto_utilization_focus=auto_utilization_focus,
        interest_implications=interest_implications,
        market_index_snapshot=[],
        key_drivers=runtime.summarize_market_lines(cleaned_summary),
        sector_implications=runtime.build_sector_implications(cleaned_summary, tags),
        portfolio_actions=runtime.build_market_portfolio_actions(sentiment, risk_level, regime),
        next_session_watch=runtime.build_market_next_watch(tags, market),
        tags=tags,
        attachment=None,
        created_at=now,
        updated_at=now,
    )
    store = runtime.read_market_close_journal(settings)
    existing_entries = [
        runtime.MarketCloseEntry.model_validate(raw_entry)
        for raw_entry in store.get("entries", [])
        if isinstance(raw_entry, dict)
    ]
    prior_entries = [existing for existing in existing_entries if existing.entry_id != entry.entry_id]
    all_entries = prior_entries + [entry]
    all_entries.sort(key=lambda entry_item: (entry_item.session_date, entry_item.market, entry_item.entry_id))
    patterns, regime_summary = runtime.cumulative_market_patterns(all_entries, market)
    response = runtime.MarketCloseReviewResponse(
        entry=entry,
        history_count=len([entry_item for entry_item in all_entries if entry_item.market == market]),
        cumulative_patterns=patterns,
        recent_regime_summary=regime_summary,
        storage_path=str(runtime.market_close_journal_path(settings)),
        saved_to_research_memory=True,
        attachment=None,
        source_url_processing=None,
        capture_quality=runtime.capture_quality_status(raw_content=cleaned_summary),
    )
    runtime.write_json_store(
        runtime.market_close_journal_path(settings),
        {
            "entries": [entry_item.model_dump(mode="json") for entry_item in all_entries],
            "updated_at": runtime.current_storage_timestamp(),
        },
    )
    vault_dir = runtime.resolve_vault_dir(settings.research_vault_dir)
    response.storage = runtime.save_research_markdown(
        vault_dir=vault_dir,
        ticker=runtime.market_research_key(entry.market),
        report_type="market-close-review",
        markdown=runtime.render_market_close_markdown(response, report_date),
        structured_payload={
            "status": response.status,
            "module": response.module,
            "entry": entry.model_dump(mode="json"),
            "history_count": response.history_count,
            "cumulative_patterns": response.cumulative_patterns,
            "recent_regime_summary": response.recent_regime_summary,
            "source": "news_inbox",
        },
        manifest_entry={
            "summary": f"{entry.market} {entry.session_date} 뉴스 반영 시장일지: {entry.regime}, 심리 {entry.sentiment}, 리스크 {entry.risk_level}",
            "market": entry.market,
            "session_date": entry.session_date,
            "sentiment": entry.sentiment,
            "risk_level": entry.risk_level,
            "regime": entry.regime,
            "tags": entry.tags,
            "source": "news_inbox",
            "source_title": title,
            "auto_utilization_focus": entry.auto_utilization_focus,
            "interest_implications": entry.interest_implications,
        },
        report_date=report_date,
        file_suffix="news-inbox",
    )
    return response
