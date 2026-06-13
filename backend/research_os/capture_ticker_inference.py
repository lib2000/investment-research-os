"""Capture ticker and non-ticker research key inference helpers."""

from __future__ import annotations

from re import escape, search
from typing import Protocol


class CaptureTickerInferenceRuntime(Protocol):
    """Runtime callbacks supplied by research_os_main while this workflow is split out."""


def ticker_aliases(symbol: str, profile: dict) -> set[str]:
    aliases = {symbol.upper()}
    aliases.update(str(alias).upper() for alias in profile.get("aliases", []) if str(alias).strip())
    company_name = str(profile.get("company_name") or "")
    if company_name:
        aliases.add(company_name.upper())
        aliases.add(company_name.replace(",", "").replace(".", "").upper())
        for suffix in [" INC", " INCORPORATED", " CORPORATION", " CORP", " PBC", " CLASS A"]:
            cleaned = company_name.upper().replace(".", "").replace(",", "")
            if suffix in cleaned:
                aliases.add(cleaned.replace(suffix, "").strip())
    return {alias for alias in aliases if len(alias) >= 2}


def alias_matches_research_text(alias: str, raw_text: str) -> bool:
    normalized_alias = alias.strip().upper()
    if not normalized_alias:
        return False
    escaped_alias = escape(normalized_alias)
    if any("\uac00" <= char <= "\ud7a3" for char in normalized_alias):
        if len(normalized_alias) <= 3:
            return bool(
                search(
                    rf"(?<![\uac00-\ud7a3A-Z0-9]){escaped_alias}(?![\uac00-\ud7a3A-Z0-9])",
                    raw_text,
                )
            )
        return normalized_alias in raw_text
    if len(normalized_alias) <= 3:
        return bool(search(rf"(?<![A-Z0-9]){escaped_alias}(?![A-Z0-9])", raw_text))
    if search(rf"(?<![A-Z0-9]){escaped_alias}(?![A-Z0-9])", raw_text):
        return True
    return False


def infer_non_ticker_research_key(raw_content: str) -> tuple[str, str]:
    text = raw_content.lower()
    keyword_groups = {
        "POLICY": {
            "source_type": "policy_research",
            "keywords": {
                "policy",
                "regulation",
                "regulatory",
                "tariff",
                "fiscal",
                "subsidy",
                "election",
                "sanction",
                "government",
                "white house",
                "congress",
                "central bank",
                "정책",
                "활성화",
                "규제",
                "관세",
                "재정",
                "보조금",
                "선거",
                "정부",
                "거래소",
                "제도",
                "의회",
                "중앙은행",
                "한국은행",
                "연준 발언",
                "지정학",
                "제재",
            },
        },
        "RATES": {
            "source_type": "rates_research",
            "keywords": {
                "rates",
                "rate cut",
                "rate hike",
                "yield",
                "treasury",
                "bond",
                "duration",
                "inflation",
                "cpi",
                "ppi",
                "pce",
                "dollar",
                "credit spread",
                "금리",
                "금리 인하",
                "금리 인상",
                "국채",
                "채권",
                "물가",
                "인플레이션",
                "달러",
                "환율",
                "장단기 금리",
                "신용 스프레드",
            },
        },
        "FLOWS": {
            "source_type": "flows_research",
            "keywords": {
                "flows",
                "fund flow",
                "etf flow",
                "positioning",
                "breadth",
                "rotation",
                "risk appetite",
                "net buying",
                "net selling",
                "foreign buying",
                "institutional buying",
                "수급",
                "자금 흐름",
                "펀드 플로우",
                "순매수",
                "순매도",
                "외국인",
                "기관",
                "개인",
                "포지셔닝",
                "시장 폭",
                "로테이션",
                "위험선호",
            },
        },
        "MACRO": {
            "source_type": "macro_research",
            "keywords": {
                "macro",
                "economy",
                "economic outlook",
                "fed",
                "fomc",
                "inflation",
                "cpi",
                "ppi",
                "rates",
                "rate cut",
                "yield",
                "treasury",
                "dollar",
                "currency",
                "recession",
                "gdp",
                "employment",
                "payroll",
                "금리",
                "물가",
                "인플레이션",
                "환율",
                "달러",
                "경기",
                "중앙은행",
                "연준",
                "한국은행",
                "고용",
                "경제 전망",
                "거시",
                "통화정책",
                "재정정책",
                "국채",
                "장단기 금리",
            },
        },
        "SECTOR": {
            "source_type": "sector_research",
            "keywords": {
                "sector",
                "industry",
                "semiconductor",
                "software",
                "cloud",
                "energy",
                "healthcare",
                "drug discovery",
                "drug design",
                "therapeutic",
                "pipeline",
                "clinical",
                "financials",
                "consumer",
                "ai capex",
                "infrastructure",
                "utilities",
                "defense",
                "aerospace",
                "biotech",
                "materials",
                "섹터",
                "산업",
                "업종",
                "반도체",
                "소프트웨어",
                "클라우드",
                "에너지",
                "헬스케어",
                "바이오",
                "신약",
                "신약개발",
                "신약 설계",
                "치료제",
                "파이프라인",
                "임상",
                "금융",
                "소비재",
                "인프라",
                "방산",
                "항공우주",
                "유틸리티",
                "소재",
                "테마",
                "ai 투자",
                "데이터센터",
            },
        },
        "MARKET": {
            "source_type": "market_research",
            "keywords": {
                "market",
                "equity market",
                "flows",
                "fund flow",
                "positioning",
                "risk appetite",
                "breadth",
                "volatility",
                "vix",
                "rotation",
                "liquidity",
                "sentiment",
                "시장",
                "증시",
                "수급",
                "자금 흐름",
                "펀드 플로우",
                "포지셔닝",
                "위험선호",
                "위험 회피",
                "변동성",
                "시장 폭",
                "로테이션",
                "투자 동향",
                "유동성",
                "투자심리",
                "리스크온",
                "리스크오프",
            },
        },
    }
    scores = {}
    for key, config in keyword_groups.items():
        scores[key] = sum(1 for keyword in config["keywords"] if keyword in text)
    if scores.get("RATES", 0) and scores.get("MACRO", 0):
        scores["RATES"] += 1
    if scores.get("FLOWS", 0) and scores.get("MARKET", 0):
        scores["FLOWS"] += 1
    if scores.get("POLICY", 0) and scores.get("MACRO", 0):
        scores["POLICY"] += 1
    if scores.get("POLICY", 0) and scores.get("MARKET", 0):
        scores["POLICY"] += 1
    best_key, best_score = max(scores.items(), key=lambda item: item[1])
    if best_score > 0:
        return best_key, str(keyword_groups[best_key]["source_type"])
    return "INBOX", "unassigned_inbox"


def infer_capture_ticker(runtime: CaptureTickerInferenceRuntime, raw_content: str, settings=None) -> tuple[str, str]:
    active_settings = settings or runtime.get_settings()
    upper_text = raw_content.upper()
    special_research_keys = {"CASH", *runtime.special_research_keys}
    explicit = search(r"(?:TICKER|SYMBOL|티커|심볼)\s*[:=]\s*\$?([A-Z0-9._-]{1,10})", upper_text)
    if explicit:
        candidate = runtime.normalize_ticker(explicit.group(1))
        if runtime.verify_ticker_symbol(candidate, active_settings).verified:
            return candidate, "explicit_symbol"

    registry = {
        **runtime.official_ticker_registry,
        **runtime.read_dynamic_ticker_registry(active_settings),
    }
    symbol_hits = []
    for symbol in registry:
        if symbol in special_research_keys:
            continue
        if not runtime.is_plausible_equity_symbol(symbol):
            continue
        if search(rf"(?<![A-Z0-9])\$?{escape(symbol)}(?![A-Z0-9])", upper_text):
            symbol_hits.append(symbol)
    if len(symbol_hits) == 1:
        return symbol_hits[0], "symbol_match"

    alias_hits = []
    for symbol, profile in registry.items():
        if symbol in special_research_keys:
            continue
        if not runtime.is_plausible_equity_symbol(symbol):
            continue
        aliases = ticker_aliases(symbol, profile) - {symbol.upper()}
        if any(alias_matches_research_text(alias, upper_text) for alias in aliases):
            alias_hits.append(symbol)
    unique_alias_hits = sorted(set(alias_hits))
    if len(unique_alias_hits) == 1:
        return unique_alias_hits[0], "company_alias_match"

    return infer_non_ticker_research_key(raw_content)
