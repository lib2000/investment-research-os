"""News inbox promotion into market journal entries."""

from __future__ import annotations

from re import sub
from typing import Protocol


def keyword_hits(text: str, keywords: list[str]) -> int:
    upper_text = text.upper()
    return sum(upper_text.count(keyword.upper()) for keyword in keywords)


def clean_market_summary_text(raw_summary: str) -> str:
    cleaned_lines: list[str] = []
    for chunk in (raw_summary or "").replace("\r\n", "\n").split("\n"):
        line = chunk.strip()
        if not line:
            continue
        line = sub(r"([\(（\s])\+([0-9]+(?:\.[0-9]+)?)\s*%", r"\1상승 \2퍼센트", line)
        line = sub(r"([\(（\s])-([0-9]+(?:\.[0-9]+)?)\s*%", r"\1하락 \2퍼센트", line)
        line = sub(r"(?<=\d),(?=\d)", "", line)
        line = sub(r"^[\s\-*•●○■□▪▫◆◇▶▷►▸]+", "", line)
        line = sub(r"[\[\]\(\)（）{}<>〈〉《》■□●○◆◇▶▷►▸▪▫•※*#_`~|^=]+", " ", line)
        line = sub(r"[▲▼△▽↑↓→←↗↘+%]", " ", line)
        line = sub(r"[^0-9A-Za-z가-힣ㄱ-ㅎㅏ-ㅣ\s.,:;!?/·-]", " ", line)
        line = sub(r"[,;:/·]", " ", line)
        line = sub(r"\s+", " ", line).strip(" .!?-")
        if line:
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def infer_market_close_sentiment(raw_summary: str) -> tuple[str, str, str]:
    positive = keyword_hits(
        raw_summary,
        [
            "상승",
            "강세",
            "반등",
            "랠리",
            "돌파",
            "위험 선호",
            "매수",
            "완화",
            "실적 호조",
            "상회",
            "rally",
            "rebound",
            "risk-on",
            "beat",
        ],
    )
    negative = keyword_hits(
        raw_summary,
        [
            "하락",
            "약세",
            "급락",
            "매도",
            "조정",
            "위험 회피",
            "금리 상승",
            "인플레이션",
            "부진",
            "하회",
            "selloff",
            "risk-off",
            "miss",
        ],
    )
    risk_hits = keyword_hits(
        raw_summary,
        [
            "변동성",
            "vix",
            "금리 상승",
            "달러 강세",
            "유가 상승",
            "신용",
            "침체",
            "지정학",
            "관세",
            "급락",
            "risk-off",
        ],
    )
    if positive > negative + 1:
        sentiment = "긍정"
    elif negative > positive + 1:
        sentiment = "부정"
    else:
        sentiment = "혼합"

    if risk_hits >= 4 or negative >= positive + 3:
        risk_level = "높음"
    elif risk_hits >= 2 or sentiment == "혼합":
        risk_level = "보통"
    else:
        risk_level = "낮음"

    if sentiment == "긍정" and risk_level != "높음":
        regime = "위험 선호"
    elif sentiment == "부정" and risk_level == "높음":
        regime = "위험 회피"
    elif keyword_hits(raw_summary, ["순환매", "rotation", "섹터 로테이션"]):
        regime = "섹터 순환"
    else:
        regime = "방향성 확인 필요"
    return sentiment, risk_level, regime


def infer_market_tags(raw_summary: str) -> list[str]:
    tag_keywords = {
        "AI": ["AI", "인공지능", "데이터센터", "GPU"],
        "반도체": ["반도체", "semiconductor", "chip"],
        "금리": ["금리", "국채", "yield", "treasury"],
        "환율": ["환율", "달러", "원화", "엔화", "FX"],
        "에너지": ["유가", "원유", "가스", "energy", "oil"],
        "금융": ["은행", "금융", "credit", "bank"],
        "헬스케어": ["헬스케어", "바이오", "제약", "healthcare"],
        "중국": ["중국", "china"],
        "한국 수출": ["수출", "반도체 수출", "무역수지"],
        "정책": ["연준", "FOMC", "한국은행", "BOJ", "정책", "관세"],
    }
    tags = [
        tag
        for tag, keywords in tag_keywords.items()
        if keyword_hits(raw_summary, keywords)
    ]
    return tags or ["시장 전반"]


def summarize_market_lines(raw_summary: str, limit: int = 5) -> list[str]:
    raw_summary = clean_market_summary_text(raw_summary)
    lines = []
    for chunk in raw_summary.replace("\r\n", "\n").split("\n"):
        normalized = chunk.strip(" -•\t")
        if normalized:
            lines.append(normalized)
    if len(lines) < 3:
        lines = [
            item.strip()
            for item in sub(r"([.!?。])", r"\1\n", raw_summary).split("\n")
            if item.strip()
        ]
    return lines[:limit] or ["입력 요약에서 핵심 문장을 추출하지 못했습니다."]


def build_sector_implications(raw_summary: str, tags: list[str]) -> list[str]:
    implications = []
    if "AI" in tags or "반도체" in tags:
        implications.append("AI/반도체 노출은 수요 지속성과 밸류에이션 부담을 함께 점검하세요.")
    if "금리" in tags:
        implications.append("금리 민감 성장주와 금융/방어 섹터의 상대 강도를 비교하세요.")
    if "에너지" in tags:
        implications.append("유가 변동은 에너지·항공·운송·소비재 마진에 반대 방향으로 작용할 수 있습니다.")
    if "환율" in tags:
        implications.append("환율 변화가 수출주, 해외 매출 비중 높은 종목, 원화 자산에 미치는 영향을 점검하세요.")
    if "정책" in tags:
        implications.append("중앙은행·규제·관세 뉴스는 단기 멀티플과 섹터 로테이션을 흔들 수 있습니다.")
    return implications or ["특정 섹터보다 지수 방향성, 시장 폭, 주도주 지속 여부를 우선 확인하세요."]


def build_market_portfolio_actions(sentiment: str, risk_level: str, regime: str) -> list[str]:
    if risk_level == "높음":
        return [
            "신규 매수는 분할 접근하고 손절/무효화 조건을 먼저 확정하세요.",
            "고집중 포지션과 고베타 성장주 비중이 의도한 리스크 예산 안에 있는지 확인하세요.",
            "다음 장 시작 전 시장 폭, 금리, 환율이 악화되는지 재확인하세요.",
        ]
    if sentiment == "긍정":
        return [
            "주도 섹터가 넓어지는지 확인하면서 기존 강한 논거 종목의 추가 진입 후보를 선별하세요.",
            "급등 추격보다 전일 저항 돌파 후 지지 확인 구간을 우선 관찰하세요.",
        ]
    if regime == "섹터 순환":
        return [
            "기존 주도주와 새로 강해지는 섹터의 상대 강도를 비교해 일부 리밸런싱 후보를 정리하세요.",
            "순환매가 단기 기술적 반등인지 실적/수급 변화인지 분리해서 판단하세요.",
        ]
    return [
        "확신이 낮은 장에서는 현금 비중과 관찰 목록을 유지하고, 다음 촉매 확인 후 행동하세요.",
        "관심 종목은 가격보다 논거 변화와 데이터 확인 여부를 먼저 업데이트하세요.",
    ]


def build_market_next_watch(tags: list[str], market: str) -> list[str]:
    items = ["시장 폭: 상승/하락 종목 수와 주도주 확산 여부"]
    if market == "US":
        items.extend(["미국 10년물 금리와 달러 지수", "나스닥/러셀2000 상대 강도"])
    if market == "KR":
        items.extend(["외국인/기관 수급과 원달러 환율", "코스피 대형주와 코스닥 성장주의 상대 강도"])
    if "AI" in tags or "반도체" in tags:
        items.append("AI/반도체 주도주의 거래대금과 실적 기대 변화")
    if "에너지" in tags:
        items.append("유가와 에너지/운송/소비재 마진 민감도")
    if "정책" in tags:
        items.append("중앙은행 발언, 정책 일정, 규제/관세 뉴스")
    return items



def market_tag_aliases(tags: list[str]) -> list[str]:
    aliases = {
        "AI": ["AI", "GPU", "데이터센터", "DATACENTER", "DATA CENTER", "TECHNOLOGY", "CLOUD"],
        "반도체": ["반도체", "SEMICONDUCTOR", "CHIP", "GPU", "TECHNOLOGY"],
        "금리": ["금리", "국채", "YIELD", "TREASURY", "BANK", "FINANCIAL"],
        "환율": ["환율", "달러", "FX", "USD", "EXPORT", "수출"],
        "에너지": ["에너지", "ENERGY", "OIL", "GAS", "운송", "항공"],
        "금융": ["금융", "BANK", "FINANCIAL", "CREDIT"],
        "헬스케어": ["헬스케어", "HEALTHCARE", "BIO", "제약"],
        "중국": ["중국", "CHINA", "수출"],
        "한국 수출": ["한국 수출", "수출", "반도체", "EXPORT", "KOREA"],
        "정책": ["정책", "FOMC", "연준", "규제", "관세", "POLICY"],
    }
    terms = set(tags)
    for tag in tags:
        terms.update(aliases.get(tag, []))
    return [term for term in terms if term]


def text_matches_market_tags(value: str, tag_terms: list[str]) -> bool:
    normalized = value.strip().upper()
    if not normalized:
        return False
    for term in tag_terms:
        tag = term.strip().upper()
        if tag and (tag in normalized or normalized in tag):
            return True
    return False


def append_unique(items: list[str], value: str, limit: int = 8) -> None:
    if value and value not in items and len(items) < limit:
        items.append(value)

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
