"""News inbox promotion into market journal entries."""

from __future__ import annotations

from typing import Protocol

from research_os import market_journal_analysis
from research_os import market_journal_rendering
from research_os.market_journal_patterns import cumulative_market_patterns


def keyword_hits(text: str, keywords: list[str]) -> int:
    return market_journal_analysis.keyword_hits(text, keywords)


def clean_market_summary_text(raw_summary: str) -> str:
    return market_journal_analysis.clean_market_summary_text(raw_summary)


def infer_market_close_sentiment(raw_summary: str) -> tuple[str, str, str]:
    return market_journal_analysis.infer_market_close_sentiment(raw_summary)


def infer_market_tags(raw_summary: str) -> list[str]:
    return market_journal_analysis.infer_market_tags(raw_summary)


def summarize_market_lines(raw_summary: str, limit: int = 5) -> list[str]:
    return market_journal_analysis.summarize_market_lines(raw_summary, limit)


def build_sector_implications(raw_summary: str, tags: list[str]) -> list[str]:
    return market_journal_analysis.build_sector_implications(raw_summary, tags)


def build_market_portfolio_actions(sentiment: str, risk_level: str, regime: str) -> list[str]:
    return market_journal_analysis.build_market_portfolio_actions(sentiment, risk_level, regime)


def build_market_next_watch(tags: list[str], market: str) -> list[str]:
    return market_journal_analysis.build_market_next_watch(tags, market)


def market_tag_aliases(tags: list[str]) -> list[str]:
    return market_journal_analysis.market_tag_aliases(tags)


def text_matches_market_tags(value: str, tag_terms: list[str]) -> bool:
    return market_journal_analysis.text_matches_market_tags(value, tag_terms)


def append_unique(items: list[str], value: str, limit: int = 8) -> None:
    market_journal_analysis.append_unique(items, value, limit)


def build_auto_market_utilization_focus(
    runtime,
    *,
    market: str,
    tags: list[str],
    sentiment: str,
    risk_level: str,
    regime: str,
    settings,
) -> list[str]:
    focus: list[str] = []
    tag_terms = market_tag_aliases(tags)
    tag_label = ", ".join(tags) or "시장 전반"

    portfolio_store = runtime.read_portfolio_store(settings)
    portfolios = [
        runtime.SavedPortfolio.model_validate(item)
        for item in portfolio_store.get("portfolios", {}).values()
        if isinstance(item, dict)
    ]
    if portfolios:
        portfolio_names = ", ".join(item.portfolio_name for item in portfolios[:3])
        append_unique(
            focus,
            f"저장 포트폴리오({portfolio_names})의 보유 종목·섹터 노출을 오늘 시장 태그({tag_label})와 자동 대조합니다.",
        )
        matched_exposures: list[str] = []
        for portfolio in portfolios:
            for holding in portfolio.holdings:
                candidates = [
                    holding.ticker,
                    holding.name or "",
                    holding.sector,
                    *holding.theme_tags,
                ]
                if any(text_matches_market_tags(item, tag_terms) for item in candidates):
                    exposure = f"{portfolio.portfolio_name}:{holding.ticker}"
                    if holding.sector and holding.sector != "Unknown":
                        exposure += f"({holding.sector})"
                    append_unique(matched_exposures, exposure, limit=6)
        if matched_exposures:
            append_unique(
                focus,
                "오늘 시장 태그와 겹치는 보유 노출: "
                + ", ".join(matched_exposures)
                + "를 우선 점검합니다.",
            )
        else:
            append_unique(
                focus,
                "직접 겹치는 보유 노출이 없으면 지수·금리·환율 변화가 전체 포트폴리오 베타에 미치는 영향을 우선 확인합니다.",
            )
    else:
        append_unique(
            focus,
            "저장 포트폴리오가 없으므로 장세 판정과 리스크 레벨을 기본 리스크 예산 가이드로 활용합니다.",
        )

    interest_store = runtime.read_interest_list(settings)
    interest_tickers = [
        runtime.InterestTicker.model_validate(item)
        for item in interest_store.get("tickers", [])
        if isinstance(item, dict)
    ]
    interest_sectors = [
        runtime.InterestSector.model_validate(item)
        for item in interest_store.get("sectors", [])
        if isinstance(item, dict)
    ]
    matched_sectors = [
        item.name
        for item in interest_sectors
        if text_matches_market_tags(item.name, tag_terms)
        or any(text_matches_market_tags(tag, tag_terms) for tag in item.tags)
    ]
    matched_tickers = [
        item.ticker
        for item in interest_tickers
        if any(text_matches_market_tags(tag, tag_terms) for tag in item.tags)
        or text_matches_market_tags(item.thesis or "", tag_terms)
        or text_matches_market_tags(item.notes or "", tag_terms)
    ]
    if matched_sectors:
        append_unique(
            focus,
            "관심 섹터 중 오늘 시장 태그와 연결된 영역: "
            + ", ".join(matched_sectors[:5])
            + "를 다음 후보 발굴에 반영합니다.",
        )
    elif interest_sectors:
        append_unique(
            focus,
            "관심 섹터 목록은 유지하되 오늘 태그와 직접 겹치는 섹터가 적어 상대 강도 변화만 관찰합니다.",
        )

    if matched_tickers:
        append_unique(
            focus,
            "관심 종목 중 오늘 이슈와 연결된 종목: "
            + ", ".join(matched_tickers[:8])
            + "의 논거 변화와 다음 장 가격 반응을 우선 확인합니다.",
        )
    elif interest_tickers:
        append_unique(
            focus,
            "관심 종목은 가격보다 오늘 장세가 기존 투자 논거를 강화/약화했는지부터 업데이트합니다.",
        )

    if risk_level == "높음":
        append_unique(
            focus,
            "리스크 레벨이 높아 다음 장 신규 진입보다 기존 노출 축소·손절 기준·현금 비중 점검에 우선순위를 둡니다.",
        )
    elif sentiment == "긍정" and regime == "위험 선호":
        append_unique(
            focus,
            "위험 선호 장세로 분류되어 관심 섹터와 주도주 확산 여부를 다음 매매 후보 필터로 사용합니다.",
        )
    else:
        append_unique(
            focus,
            "방향성이 완전히 확정되지 않았으므로 누적 시장일지의 반복 태그와 다음 장 확인 지표를 함께 비교합니다.",
        )

    if market == "KR":
        append_unique(focus, "한국 시장 기록은 외국인/기관 수급, 원달러 환율, 반도체 대형주 상대 강도를 자동 추적합니다.")
    elif market == "US":
        append_unique(focus, "미국 시장 기록은 10년물 금리, 달러, 나스닥/러셀2000 상대 강도와 연결해 누적합니다.")
    else:
        append_unique(focus, "글로벌 시장 기록은 지역 간 자금 이동과 달러/금리/원자재 변화의 공통 신호로 누적합니다.")
    return focus[:8]


def build_market_interest_implications(
    runtime,
    *,
    raw_summary: str,
    tags: list[str],
    settings,
) -> list[str]:
    interest_store = runtime.read_interest_list(settings)
    interest_tickers = [
        runtime.InterestTicker.model_validate(item)
        for item in interest_store.get("tickers", [])
        if isinstance(item, dict)
    ]
    interest_sectors = [
        runtime.InterestSector.model_validate(item)
        for item in interest_store.get("sectors", [])
        if isinstance(item, dict)
    ]
    implications: list[str] = []
    tag_terms = market_tag_aliases(tags)
    summary_text = raw_summary.upper()

    for item in interest_tickers[:20]:
        profile_name = ""
        if item.verification and item.verification.company_name:
            profile_name = item.verification.company_name
        candidates = [item.ticker, profile_name, item.thesis or "", item.notes or "", *item.tags]
        direct_match = any(
            candidate and (
                candidate.upper() in summary_text
                or text_matches_market_tags(candidate, tag_terms)
            )
            for candidate in candidates
        )
        if direct_match:
            implications.append(
                f"관심종목 {item.ticker}: 오늘 시장 태그({', '.join(tags)})와 연결됩니다. 다음 장 가격 반응보다 기존 매수 후보 논거가 강화/약화됐는지 먼저 업데이트하세요."
            )

    for item in interest_sectors[:20]:
        candidates = [item.name, item.thesis or "", item.notes or "", *item.tags]
        direct_match = any(
            candidate and (
                candidate.upper() in summary_text
                or text_matches_market_tags(candidate, tag_terms)
            )
            for candidate in candidates
        )
        if direct_match:
            implications.append(
                f"관심섹터 {item.name}: 오늘 시장 태그({', '.join(tags)})와 겹칩니다. 섹터 발굴 후보와 관련 종목의 상대 강도를 다음 관찰 목록에 올리세요."
            )

    if not implications and (interest_tickers or interest_sectors):
        implications.append(
            "현재 관심목록과 오늘 시장 태그의 직접 연결은 약합니다. 관심종목은 개별 촉매가 확인될 때까지 관찰 상태로 유지하세요."
        )
    if not implications:
        implications.append(
            "저장된 관심종목/관심섹터가 없어 시장일지의 관심목록 영향 분석을 건너뜁니다."
        )
    return implications[:10]



def render_market_close_markdown(runtime, response, storage_date) -> str:
    return market_journal_rendering.render_market_close_markdown(runtime, response, storage_date)


def build_market_close_entry(runtime, request, settings, attachment_info: dict | None = None):
    market = runtime.normalize_market_code(request.market)
    session_date = request.session_date or runtime.current_storage_date().isoformat()
    raw_summary = clean_market_summary_text(request.raw_summary)
    sentiment, risk_level, regime = infer_market_close_sentiment(raw_summary)
    tags = infer_market_tags(raw_summary)
    market_index_snapshot = (
        runtime.fetch_naver_korea_index_snapshot(settings) if market == "KR" else []
    )
    key_drivers = summarize_market_lines(raw_summary)
    sector_implications = build_sector_implications(raw_summary, tags)
    auto_utilization_focus = build_auto_market_utilization_focus(
        runtime,
        market=market,
        tags=tags,
        sentiment=sentiment,
        risk_level=risk_level,
        regime=regime,
        settings=settings,
    )
    interest_implications = build_market_interest_implications(
        runtime,
        raw_summary=raw_summary,
        tags=tags,
        settings=settings,
    )
    portfolio_actions = build_market_portfolio_actions(sentiment, risk_level, regime)
    next_session_watch = build_market_next_watch(tags, market)
    now = runtime.current_storage_timestamp()
    entry_id = f"{market}-{session_date}"
    entry = runtime.MarketCloseEntry(
        entry_id=entry_id,
        market=market,
        session_date=session_date,
        raw_summary=raw_summary,
        source_origin=str(request.source_origin or "manual").strip() or "manual",
        source_provider=str(request.source_provider or "").strip() or None,
        source_title=str(request.source_title or "").strip() or None,
        sentiment=sentiment,
        risk_level=risk_level,
        regime=regime,
        auto_utilization_focus=auto_utilization_focus,
        interest_implications=interest_implications,
        market_index_snapshot=market_index_snapshot,
        key_drivers=key_drivers,
        sector_implications=sector_implications,
        portfolio_actions=portfolio_actions,
        next_session_watch=next_session_watch,
        tags=tags,
        attachment=attachment_info,
        created_at=now,
        updated_at=now,
    )
    store = runtime.read_market_close_journal(settings)
    existing_entries = [
        hydrate_market_close_auto_focus(runtime, runtime.MarketCloseEntry.model_validate(item), settings)
        for item in store.get("entries", [])
        if isinstance(item, dict)
    ]
    prior_without_same_id = [
        item for item in existing_entries if item.entry_id != entry_id
    ]
    patterns, regime_summary = cumulative_market_patterns(prior_without_same_id + [entry], market)
    return entry, prior_without_same_id, patterns, regime_summary


def hydrate_market_close_auto_focus(runtime, entry, settings):
    updates: dict[str, object] = {}
    cleaned_summary = clean_market_summary_text(entry.raw_summary)
    if cleaned_summary and cleaned_summary != entry.raw_summary:
        updates["raw_summary"] = cleaned_summary
        updates["key_drivers"] = summarize_market_lines(cleaned_summary)
    if not entry.interest_implications:
        updates["interest_implications"] = build_market_interest_implications(
            runtime,
            raw_summary=cleaned_summary or entry.raw_summary,
            tags=entry.tags,
            settings=settings,
        )
    if entry.market == "KR" and not entry.market_index_snapshot:
        updates["market_index_snapshot"] = runtime.fetch_naver_korea_index_snapshot(settings)
    if entry.auto_utilization_focus:
        if updates:
            return entry.model_copy(update=updates)
        return entry
    updates["auto_utilization_focus"] = build_auto_market_utilization_focus(
        runtime,
        market=entry.market,
        tags=entry.tags,
        sentiment=entry.sentiment,
        risk_level=entry.risk_level,
        regime=entry.regime,
        settings=settings,
    )
    return entry.model_copy(update=updates)



def infer_policy_market_regime(runtime, market_state: str, settings) -> tuple[str, list[str]]:
    text = clean_market_summary_text(market_state)
    if text:
        sentiment, risk_level, regime = infer_market_close_sentiment(text)
        tags = infer_market_tags(text)
        return f"{regime} / 심리 {sentiment} / 리스크 {risk_level}", tags

    store = runtime.read_market_close_journal(settings)
    entries = [
        runtime.MarketCloseEntry.model_validate(item)
        for item in store.get("entries", [])
        if isinstance(item, dict)
    ]
    if not entries:
        return "누적 시장 상태 부족", []
    latest = sorted(entries, key=lambda item: (item.session_date, item.updated_at or ""), reverse=True)[0]
    return (
        f"{latest.market} 최근 시장일지: {latest.regime} / 심리 {latest.sentiment} / 리스크 {latest.risk_level}",
        latest.tags,
    )

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


def save_market_close_review_response(
    runtime: NewsMarketJournalRuntime,
    *,
    response,
    entry,
    vault_dir,
    report_date,
):
    response.storage = runtime.save_research_markdown(
        vault_dir=vault_dir,
        ticker=runtime.market_research_key(entry.market),
        report_type="market-close-review",
        markdown=runtime.render_market_close_markdown(response, report_date),
        structured_payload=response.model_dump(mode="json"),
        manifest_entry={
            "summary": (
                f"{entry.market} {entry.session_date} 폐장 리뷰: {entry.regime}, "
                f"심리 {entry.sentiment}, 리스크 {entry.risk_level}"
            ),
            "market": entry.market,
            "session_date": entry.session_date,
            "sentiment": entry.sentiment,
            "risk_level": entry.risk_level,
            "regime": entry.regime,
            "tags": entry.tags,
            "auto_utilization_focus": entry.auto_utilization_focus,
            "interest_implications": entry.interest_implications,
        },
        report_date=report_date,
    )
    return response


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
