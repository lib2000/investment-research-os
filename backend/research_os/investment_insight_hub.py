"""Integrated investment insight synthesis across market, filings, news, and sentiment."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from re import search
from typing import Any

from research_os.models import PortfolioHolding


DESIGN_NAME = "investment_insight_hub_v1"

POLICY_TERMS = (
    "policy",
    "regulation",
    "regulatory",
    "law",
    "legal",
    "legislation",
    "rule",
    "법령",
    "규제",
    "정책",
    "감독",
    "제재",
)
POSITIVE_TERMS = ("긍정", "호조", "상승", "개선", "강화", "수혜", "positive", "beat", "upgrade")
NEGATIVE_TERMS = ("부정", "하락", "악화", "위험", "리스크", "약화", "negative", "miss", "downgrade", "risk")


def _safe_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _safe_ticker(value: Any) -> str:
    return _safe_text(value).upper()


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.replace("%", "").replace(",", "").strip()
        if not value:
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = _safe_text(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text[:10]).date()
    except ValueError:
        return None


def _recent_enough(value: Any, today: date, days: int) -> bool:
    item_date = _parse_date(value)
    if not item_date:
        return True
    return item_date >= today - timedelta(days=max(1, int(days or 7)))


def _sentiment_score(*values: Any) -> float:
    text = " ".join(_safe_text(value).lower() for value in values)
    score = 0.0
    if any(term.lower() in text for term in POSITIVE_TERMS):
        score += 1.0
    if any(term.lower() in text for term in NEGATIVE_TERMS):
        score -= 1.0
    if "혼합" in text or "neutral" in text or "중립" in text:
        score *= 0.5
    return max(-1.0, min(1.0, score))


def _sentiment_label(score: float) -> str:
    if score >= 0.35:
        return "긍정 우위"
    if score <= -0.35:
        return "위험 우위"
    return "혼합/중립"


def _holding_terms(holdings: list[PortfolioHolding]) -> tuple[set[str], dict[str, str], set[str]]:
    tickers: set[str] = set()
    names: dict[str, str] = {}
    sectors: set[str] = set()
    for holding in holdings:
        ticker = _safe_ticker(holding.ticker)
        if ticker and ticker not in {"CASH", "UNKNOWN"}:
            tickers.add(ticker)
            names[ticker] = _safe_text(holding.name) or ticker
        if holding.sector and holding.sector != "Unknown":
            sectors.add(_safe_text(holding.sector))
        for tag in holding.theme_tags or []:
            if _safe_text(tag):
                sectors.add(_safe_text(tag))
    return tickers, names, sectors


def _matches_targets(text: str, tickers: set[str], names: dict[str, str], sectors: set[str]) -> list[str]:
    haystack = _safe_text(text).upper()
    matches: list[str] = []
    for ticker in sorted(tickers):
        if ticker and ticker in haystack:
            matches.append(ticker)
    lower_text = _safe_text(text).lower()
    for ticker, name in names.items():
        if name and name.lower() in lower_text and ticker not in matches:
            matches.append(ticker)
    for sector in sorted(sectors):
        if sector and sector.lower() in lower_text:
            matches.append(sector)
    return matches[:8]


def _market_entries(market_journal: dict, today: date, days: int, limit: int) -> list[dict]:
    entries = market_journal.get("entries") if isinstance(market_journal, dict) else []
    if not isinstance(entries, list):
        return []
    rows: list[dict] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if not _recent_enough(entry.get("session_date") or entry.get("date"), today, days):
            continue
        summary = _safe_text(entry.get("summary") or entry.get("raw_summary") or entry.get("headline"))
        rows.append(
            {
                "source": "market_journal",
                "market": entry.get("market") or "GLOBAL",
                "date": entry.get("session_date") or entry.get("date"),
                "sentiment": entry.get("sentiment") or "미확인",
                "risk_level": entry.get("risk_level") or "미확인",
                "regime": entry.get("regime") or "",
                "tags": entry.get("tags") or [],
                "summary": summary,
                "score": _sentiment_score(entry.get("sentiment"), entry.get("risk_level"), summary),
            }
        )
    rows.sort(key=lambda item: str(item.get("date") or ""), reverse=True)
    return rows[:limit]


def _news_items(news_inbox: dict, today: date, days: int, tickers: set[str], names: dict[str, str], sectors: set[str], limit: int) -> list[dict]:
    items = news_inbox.get("items") if isinstance(news_inbox, dict) else []
    if not isinstance(items, list):
        return []
    rows: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_date = item.get("created_at") or item.get("updated_at") or item.get("source_published_at") or item.get("date")
        if not _recent_enough(item_date, today, days):
            continue
        tags = [str(tag) for tag in item.get("tags") or []]
        text = " ".join(
            _safe_text(item.get(key))
            for key in ["title", "summary", "safe_user_note", "raw_content", "scope", "review_status"]
        )
        related = _matches_targets(text + " " + " ".join(tags), tickers, names, sectors)
        is_policy = bool(item.get("is_policy_law")) or str(item.get("scope") or "").upper() == "POLICY" or any(
            term.lower() in (text + " " + " ".join(tags)).lower() for term in POLICY_TERMS
        )
        rows.append(
            {
                "source": "news_inbox",
                "date": str(item_date or ""),
                "title": _safe_text(item.get("title") or item.get("source_title") or "뉴스"),
                "scope": item.get("scope") or "INBOX",
                "is_policy_or_law": is_policy,
                "related_targets": related,
                "summary": _safe_text(item.get("summary") or item.get("safe_user_note") or item.get("raw_content")),
                "score": _sentiment_score(text, tags),
            }
        )
    rows.sort(key=lambda item: (bool(item["related_targets"]), bool(item["is_policy_or_law"]), item["date"]), reverse=True)
    return rows[:limit]


def _filing_items(dart_cache: dict, today: date, days: int, tickers: set[str], limit: int) -> list[dict]:
    entries = (dart_cache.get("entries") or {}) if isinstance(dart_cache, dict) else {}
    rows: list[dict] = []
    for entry in entries.values() if isinstance(entries, dict) else []:
        if not isinstance(entry, dict):
            continue
        filing = entry.get("filing") if isinstance(entry.get("filing"), dict) else {}
        ticker = _safe_ticker(entry.get("ticker") or filing.get("stock_code"))
        receipt_date = filing.get("receipt_date") or filing.get("rcept_dt") or entry.get("detected_at")
        if tickers and ticker and ticker not in tickers:
            continue
        if not _recent_enough(receipt_date, today, days):
            continue
        report_name = _safe_text(filing.get("report_name") or filing.get("report_nm") or "공시")
        importance = _safe_text(entry.get("importance") or "보통")
        tags = [str(tag) for tag in entry.get("tags") or []]
        rows.append(
            {
                "source": "dart_filing",
                "date": str(receipt_date or ""),
                "ticker": ticker,
                "company_name": filing.get("corp_name") or entry.get("corp_name") or ticker,
                "title": report_name,
                "importance": importance,
                "tags": tags,
                "summary": _safe_text(entry.get("action") or report_name),
                "score": -0.6 if search(r"소송|제재|불성실|전환사채|유상증자|위험", report_name) else 0.2,
            }
        )
    rows.sort(key=lambda item: (item["importance"] == "높음", item["date"]), reverse=True)
    return rows[:limit]


def _market_data_items(holdings: list[PortfolioHolding], limit: int) -> list[dict]:
    rows: list[dict] = []
    for holding in holdings:
        ticker = _safe_ticker(holding.ticker)
        if not ticker or ticker in {"CASH", "UNKNOWN"}:
            continue
        return_rate = _safe_float(holding.unrealized_return)
        market_value = _safe_float(holding.market_value) or 0.0
        rows.append(
            {
                "source": "portfolio_market_data",
                "ticker": ticker,
                "company_name": _safe_text(holding.name) or ticker,
                "market_value": market_value,
                "unrealized_return": return_rate,
                "price_checked_at": holding.price_checked_at,
                "price_source": holding.price_source,
                "summary": f"평가액 {market_value:,.0f}원 / 미실현 수익률 {return_rate:.2f}%" if return_rate is not None else f"평가액 {market_value:,.0f}원",
                "score": max(-1.0, min(1.0, (return_rate or 0.0) / 20.0)),
            }
        )
    rows.sort(key=lambda item: abs(float(item.get("unrealized_return") or 0.0)), reverse=True)
    return rows[:limit]


def _insight(priority: int, family: str, title: str, summary: str, action: str, evidence: list[dict], score: float = 0.0) -> dict:
    severity = "높음" if priority >= 80 else "중간" if priority >= 50 else "낮음"
    return {
        "priority": priority,
        "severity": severity,
        "source_family": family,
        "title": title,
        "summary": summary,
        "recommended_action": action,
        "sentiment_score": round(score, 3),
        "evidence": evidence[:5],
    }


def build_investment_insight_hub(
    *,
    portfolio_name: str,
    holdings: list[PortfolioHolding],
    market_journal: dict | None = None,
    news_inbox: dict | None = None,
    dart_cache: dict | None = None,
    recent_weekly: dict | None = None,
    generated_at: str | None = None,
    today: date | None = None,
    days: int = 7,
    limit: int = 12,
) -> dict:
    today = today or date.today()
    normalized_days = max(1, min(int(days or 7), 30))
    normalized_limit = max(3, min(int(limit or 12), 30))
    tickers, names, sectors = _holding_terms(holdings)
    market_rows = _market_entries(market_journal or {}, today, normalized_days, normalized_limit)
    news_rows = _news_items(news_inbox or {}, today, normalized_days, tickers, names, sectors, normalized_limit)
    filing_rows = _filing_items(dart_cache or {}, today, normalized_days, tickers, normalized_limit)
    market_data_rows = _market_data_items(holdings, normalized_limit)
    policy_rows = [item for item in news_rows if item.get("is_policy_or_law")]
    related_news_rows = [item for item in news_rows if item.get("related_targets")]
    scores = [float(item.get("score") or 0.0) for item in [*market_rows, *news_rows, *filing_rows, *market_data_rows]]
    aggregate_score = round(sum(scores) / len(scores), 3) if scores else 0.0
    insights: list[dict] = []
    if market_rows:
        latest = market_rows[0]
        insights.append(
            _insight(
                75 if latest.get("risk_level") == "높음" else 60,
                "market_data_sentiment",
                f"{latest.get('market')} 시장 심리 {latest.get('sentiment')} / 리스크 {latest.get('risk_level')}",
                latest.get("summary") or "최근 시장일지 신호를 확인했습니다.",
                "시장 심리와 리스크 레벨을 포트폴리오 신규매수/비중확대 판단의 상단 필터로 사용하세요.",
                [latest],
                float(latest.get("score") or 0.0),
            )
        )
    if filing_rows:
        high_filings = [item for item in filing_rows if item.get("importance") == "높음"] or filing_rows[:3]
        insights.append(
            _insight(
                85 if any(item.get("importance") == "높음" for item in filing_rows) else 65,
                "official_filings",
                f"공시 신호 {len(filing_rows)}건 감지",
                " / ".join(f"{item.get('ticker')} {item.get('title')}" for item in high_filings[:3]),
                "중요 공시는 실적 모델, 지분 변화, 리스크 가정에 먼저 반영하세요.",
                high_filings,
                sum(float(item.get("score") or 0.0) for item in high_filings) / len(high_filings),
            )
        )
    if policy_rows:
        insights.append(
            _insight(
                80,
                "policy_law_news",
                f"정책·법령·규제 관련 뉴스 {len(policy_rows)}건",
                " / ".join(item.get("title") or "정책 뉴스" for item in policy_rows[:3]),
                "정책/규제 뉴스는 수혜·피해 섹터를 나눠 보유 종목 노출도를 확인하세요.",
                policy_rows,
                sum(float(item.get("score") or 0.0) for item in policy_rows) / len(policy_rows),
            )
        )
    if related_news_rows:
        insights.append(
            _insight(
                70,
                "news_flow",
                f"보유/관심 연결 뉴스 {len(related_news_rows)}건",
                " / ".join(item.get("title") or "뉴스" for item in related_news_rows[:3]),
                "관련 뉴스는 시장일지 후보로 승격하거나 해당 종목 Dossier에 반영하세요.",
                related_news_rows,
                sum(float(item.get("score") or 0.0) for item in related_news_rows) / len(related_news_rows),
            )
        )
    volatile = [item for item in market_data_rows if abs(float(item.get("unrealized_return") or 0.0)) >= 10.0]
    if volatile:
        insights.append(
            _insight(
                65,
                "portfolio_market_data",
                f"손익 변동 큰 보유 종목 {len(volatile)}개",
                " / ".join(f"{item.get('company_name')} {item.get('unrealized_return'):.2f}%" for item in volatile[:3]),
                "수익률 변동이 큰 종목은 최신 공시·뉴스·시장 심리와 함께 익절/추가매수 조건을 재점검하세요.",
                volatile,
                sum(float(item.get("score") or 0.0) for item in volatile) / len(volatile),
            )
        )
    weekly_counts = recent_weekly.get("counts") if isinstance(recent_weekly, dict) else {}
    if isinstance(weekly_counts, dict) and sum(int(value or 0) for value in weekly_counts.values() if isinstance(value, int | float)) > 0:
        insights.append(
            _insight(
                55,
                "research_memory",
                "최근 저장 리서치 흐름 확인",
                f"최근 {normalized_days}일 저장 신호: " + ", ".join(f"{key} {value}" for key, value in list(weekly_counts.items())[:5]),
                "저장 리서치가 많은 종목은 추천/리밸런싱 판단 전에 근거 중복과 최신성을 같이 확인하세요.",
                [{"source": "recent_weekly", "counts": weekly_counts}],
                0.0,
            )
        )
    insights.sort(key=lambda item: (item["priority"], abs(item["sentiment_score"])), reverse=True)
    coverage = {
        "market_data_items": len(market_data_rows),
        "market_journal_items": len(market_rows),
        "official_filing_items": len(filing_rows),
        "news_items": len(news_rows),
        "policy_law_items": len(policy_rows),
        "related_news_items": len(related_news_rows),
        "holding_count": len(holdings),
        "ticker_count": len(tickers),
    }
    next_actions = [
        "높음/중간 우선순위 인사이트를 종목 Dossier 또는 시장일지에 반영하세요.",
        "정책·법령·규제 뉴스는 수혜/피해 섹터와 보유 종목 노출도를 분리해 확인하세요.",
        "공시 신호가 있는 종목은 실적 모델, 지분 변화, 리스크 가정을 먼저 업데이트하세요.",
    ]
    if not market_rows:
        next_actions.append("시장일지가 비어 있으면 한국/미국 마감 일지를 먼저 갱신하세요.")
    if not policy_rows:
        next_actions.append("정책/법령 뉴스 분류가 부족하면 뉴스 인박스에서 POLICY/규제 태그를 보강하세요.")
    return {
        "module": "investment_insight_hub",
        "design": DESIGN_NAME,
        "status": "success",
        "portfolio_name": portfolio_name,
        "generated_at": generated_at,
        "lookback_days": normalized_days,
        "headline": f"{portfolio_name} 통합 투자 인사이트: {_sentiment_label(aggregate_score)}",
        "aggregate_sentiment_score": aggregate_score,
        "aggregate_sentiment_label": _sentiment_label(aggregate_score),
        "coverage": coverage,
        "insights": insights[:normalized_limit],
        "market_context": market_rows[:5],
        "filing_context": filing_rows[:8],
        "policy_law_context": policy_rows[:8],
        "news_context": news_rows[:8],
        "market_data_context": market_data_rows[:8],
        "next_actions": next_actions,
        "summary": (
            f"시장 데이터 {coverage['market_data_items']}개, 시장일지 {coverage['market_journal_items']}개, "
            f"공시 {coverage['official_filing_items']}개, 뉴스 {coverage['news_items']}개, "
            f"정책·법령 {coverage['policy_law_items']}개를 통합했습니다."
        ),
    }
