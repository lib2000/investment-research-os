"""Market journal focus and interest implication helpers."""

from __future__ import annotations

from research_os import market_journal_analysis


def _market_tag_aliases(tags: list[str]) -> list[str]:
    return market_journal_analysis.market_tag_aliases(tags)


def _text_matches_market_tags(value: str, tag_terms: list[str]) -> bool:
    return market_journal_analysis.text_matches_market_tags(value, tag_terms)


def _append_unique(items: list[str], value: str, limit: int = 8) -> None:
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
    tag_terms = _market_tag_aliases(tags)
    tag_label = ", ".join(tags) or "시장 전반"

    portfolio_store = runtime.read_portfolio_store(settings)
    portfolios = [
        runtime.SavedPortfolio.model_validate(item)
        for item in portfolio_store.get("portfolios", {}).values()
        if isinstance(item, dict)
    ]
    if portfolios:
        portfolio_names = ", ".join(item.portfolio_name for item in portfolios[:3])
        _append_unique(
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
                if any(_text_matches_market_tags(item, tag_terms) for item in candidates):
                    exposure = f"{portfolio.portfolio_name}:{holding.ticker}"
                    if holding.sector and holding.sector != "Unknown":
                        exposure += f"({holding.sector})"
                    _append_unique(matched_exposures, exposure, limit=6)
        if matched_exposures:
            _append_unique(
                focus,
                "오늘 시장 태그와 겹치는 보유 노출: "
                + ", ".join(matched_exposures)
                + "를 우선 점검합니다.",
            )
        else:
            _append_unique(
                focus,
                "직접 겹치는 보유 노출이 없으면 지수·금리·환율 변화가 전체 포트폴리오 베타에 미치는 영향을 우선 확인합니다.",
            )
    else:
        _append_unique(
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
        if _text_matches_market_tags(item.name, tag_terms)
        or any(_text_matches_market_tags(tag, tag_terms) for tag in item.tags)
    ]
    matched_tickers = [
        item.ticker
        for item in interest_tickers
        if any(_text_matches_market_tags(tag, tag_terms) for tag in item.tags)
        or _text_matches_market_tags(item.thesis or "", tag_terms)
        or _text_matches_market_tags(item.notes or "", tag_terms)
    ]
    if matched_sectors:
        _append_unique(
            focus,
            "관심 섹터 중 오늘 시장 태그와 연결된 영역: "
            + ", ".join(matched_sectors[:5])
            + "를 다음 후보 발굴에 반영합니다.",
        )
    elif interest_sectors:
        _append_unique(
            focus,
            "관심 섹터 목록은 유지하되 오늘 태그와 직접 겹치는 섹터가 적어 상대 강도 변화만 관찰합니다.",
        )

    if matched_tickers:
        _append_unique(
            focus,
            "관심 종목 중 오늘 이슈와 연결된 종목: "
            + ", ".join(matched_tickers[:8])
            + "의 논거 변화와 다음 장 가격 반응을 우선 확인합니다.",
        )
    elif interest_tickers:
        _append_unique(
            focus,
            "관심 종목은 가격보다 오늘 장세가 기존 투자 논거를 강화/약화했는지부터 업데이트합니다.",
        )

    if risk_level == "높음":
        _append_unique(
            focus,
            "리스크 레벨이 높아 다음 장 신규 진입보다 기존 노출 축소·손절 기준·현금 비중 점검에 우선순위를 둡니다.",
        )
    elif sentiment == "긍정" and regime == "위험 선호":
        _append_unique(
            focus,
            "위험 선호 장세로 분류되어 관심 섹터와 주도주 확산 여부를 다음 매매 후보 필터로 사용합니다.",
        )
    else:
        _append_unique(
            focus,
            "방향성이 완전히 확정되지 않았으므로 누적 시장일지의 반복 태그와 다음 장 확인 지표를 함께 비교합니다.",
        )

    if market == "KR":
        _append_unique(focus, "한국 시장 기록은 외국인/기관 수급, 원달러 환율, 반도체 대형주 상대 강도를 자동 추적합니다.")
    elif market == "US":
        _append_unique(focus, "미국 시장 기록은 10년물 금리, 달러, 나스닥/러셀2000 상대 강도와 연결해 누적합니다.")
    else:
        _append_unique(focus, "글로벌 시장 기록은 지역 간 자금 이동과 달러/금리/원자재 변화의 공통 신호로 누적합니다.")
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
    tag_terms = _market_tag_aliases(tags)
    summary_text = raw_summary.upper()

    for item in interest_tickers[:20]:
        profile_name = ""
        if item.verification and item.verification.company_name:
            profile_name = item.verification.company_name
        candidates = [item.ticker, profile_name, item.thesis or "", item.notes or "", *item.tags]
        direct_match = any(
            candidate and (
                candidate.upper() in summary_text
                or _text_matches_market_tags(candidate, tag_terms)
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
                or _text_matches_market_tags(candidate, tag_terms)
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
