"""Pure capture summarization, tagging, and source inference helpers."""

from __future__ import annotations

from re import escape, search
from typing import Callable

from research_os.models import DataSourceType


def enum_or_str_value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def summarize_capture(raw_content: str) -> str:
    compact = " ".join(raw_content.split())
    if len(compact) <= 240:
        return compact
    return f"{compact[:237]}..."


def infer_capture_tags(raw_content: str, provided_tags: list[str]) -> list[str]:
    text = raw_content.lower()
    inferred = set(provided_tags)
    tag_rules = {
        "earnings": {"earnings", "eps", "revenue", "guidance", "실적", "가이던스"},
        "valuation": {"valuation", "multiple", "pe", "ev/ebitda", "밸류에이션"},
        "risk": {"risk", "regulation", "lawsuit", "downside", "리스크", "규제"},
        "growth": {"growth", "demand", "capex", "성장", "수요", "투자"},
        "margin": {"margin", "gross margin", "operating margin", "마진"},
        "macro": {
            "rate",
            "inflation",
            "oil",
            "dollar",
            "fed",
            "fomc",
            "cpi",
            "금리",
            "유가",
            "달러",
            "연준",
            "물가",
            "거시",
        },
        "policy": {
            "policy",
            "regulation",
            "tariff",
            "fiscal",
            "election",
            "sanction",
            "government",
            "central bank",
            "정책",
            "규제",
            "관세",
            "재정",
            "선거",
            "정부",
            "중앙은행",
            "한국은행",
            "지정학",
        },
        "rates": {
            "rate",
            "rates",
            "yield",
            "treasury",
            "bond",
            "duration",
            "cpi",
            "pce",
            "inflation",
            "credit spread",
            "금리",
            "국채",
            "채권",
            "물가",
            "인플레이션",
            "장단기",
            "신용 스프레드",
        },
        "flows": {
            "flows",
            "fund flow",
            "etf flow",
            "positioning",
            "breadth",
            "rotation",
            "net buying",
            "net selling",
            "수급",
            "자금 흐름",
            "순매수",
            "순매도",
            "외국인",
            "기관",
            "개인",
            "포지셔닝",
            "시장 폭",
            "로테이션",
        },
        "sector": {
            "sector",
            "industry",
            "semiconductor",
            "energy",
            "healthcare",
            "섹터",
            "산업",
            "반도체",
            "에너지",
            "헬스케어",
            "테마",
        },
        "market": {
            "market",
            "flows",
            "positioning",
            "breadth",
            "rotation",
            "시장",
            "수급",
            "자금 흐름",
            "포지셔닝",
            "로테이션",
            "투자 동향",
        },
        "ai": {"ai", "artificial intelligence", "gpu", "hbm", "데이터센터", "인공지능", "반도체", "가속기"},
        "energy": {"energy", "oil", "gas", "lng", "power", "grid", "전력", "에너지", "유가", "천연가스", "lng"},
        "space": {"space", "satellite", "launch", "earth observation", "우주", "위성", "발사체", "지구관측"},
        "defense": {"defense", "aerospace", "military", "방산", "국방", "항공우주", "드론"},
        "biotech": {"biotech", "drug", "clinical", "fda", "바이오", "임상", "신약", "허가"},
        "consumer": {"consumer", "brand", "food", "retail", "소비", "브랜드", "식품", "유통"},
        "institution": {"reuters", "bloomberg", "federal reserve", "sec", "정부", "기관", "증권사", "거래소", "공시"},
        "person": {"ceo", "cfo", "chair", "founder", "대표", "회장", "창업자", "경영진"},
    }
    for tag, keywords in tag_rules.items():
        matched = False
        for keyword in keywords:
            keyword_text = str(keyword).lower().strip()
            if not keyword_text:
                continue
            if search(r"[a-z0-9]", keyword_text):
                if search(rf"(?<![a-z0-9]){escape(keyword_text)}(?![a-z0-9])", text):
                    matched = True
                    break
            elif keyword_text in text:
                matched = True
                break
        if matched:
            inferred.add(tag)
    return sorted(inferred)


def infer_capture_source_type(
    raw_content: str,
    file_name: str | None = None,
    allow_non_ticker_scope: bool = False,
    *,
    infer_non_ticker_research_key_fn: Callable[[str], tuple[str, str]] | None = None,
    special_research_keys: set[str] | None = None,
) -> str:
    text = f"{file_name or ''} {raw_content}".lower()
    if allow_non_ticker_scope and infer_non_ticker_research_key_fn:
        non_ticker_key, non_ticker_source = infer_non_ticker_research_key_fn(raw_content)
        allowed_keys = (special_research_keys or set()) - {"INBOX"}
        if non_ticker_key in allowed_keys:
            return non_ticker_source
    if any(keyword in text for keyword in ["10-k", "10-q", "sec filing", "annual report", "분기보고서", "사업보고서"]):
        return enum_or_str_value(DataSourceType.OFFICIAL_FILING)
    if any(keyword in text for keyword in ["기사본문", "기자", "news", "press release", "article", "뉴스", "기사", "보도"]):
        return enum_or_str_value(DataSourceType.NEWS)
    if any(keyword in text for keyword in ["earnings", "eps", "guidance", "실적", "가이던스", "컨퍼런스콜"]):
        return enum_or_str_value(DataSourceType.EARNINGS_RELEASE)
    if any(keyword in text for keyword in ["analyst", "initiation", "upgrade", "downgrade", "target price", "애널리스트", "리포트"]):
        return enum_or_str_value(DataSourceType.ANALYST_REPORT)
    if any(keyword in text for keyword in ["revenue", "gross margin", "ebitda", "cash flow", "매출", "마진", "현금흐름"]):
        return enum_or_str_value(DataSourceType.FINANCIAL_DATA)
    return enum_or_str_value(DataSourceType.USER_MEMO)


def infer_capture_confidence(source_type: str, has_file: bool = False) -> float:
    confidence_by_source = {
        enum_or_str_value(DataSourceType.OFFICIAL_FILING): 0.9,
        enum_or_str_value(DataSourceType.EARNINGS_RELEASE): 0.86,
        enum_or_str_value(DataSourceType.ANALYST_REPORT): 0.82,
        enum_or_str_value(DataSourceType.FINANCIAL_DATA): 0.8,
        enum_or_str_value(DataSourceType.NEWS): 0.75,
        enum_or_str_value(DataSourceType.USER_MEMO): 0.7,
        "macro_research": 0.78,
        "sector_research": 0.78,
        "market_research": 0.76,
        "policy_research": 0.78,
        "rates_research": 0.78,
        "flows_research": 0.76,
    }
    base = confidence_by_source.get(source_type, 0.72)
    return min(base + (0.03 if has_file else 0), 0.95)
