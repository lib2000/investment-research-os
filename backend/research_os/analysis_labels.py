"""Display labels and research key helpers for analysis outputs."""

from __future__ import annotations

from .models import ChecklistItemStatus


def source_type_value(item) -> str:
    value = item.source_type
    return enum_or_str_value(value)


def enum_or_str_value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def translate_source_type_label(value: object) -> str:
    labels = {
        "official_filing": "공식 공시",
        "earnings_release": "실적 발표",
        "ir_presentation": "IR 자료",
        "market_price": "시장 가격",
        "financial_data": "재무 데이터",
        "news": "뉴스",
        "analyst_report": "애널리스트 리포트",
        "user_memo": "직접 메모",
        "macro_research": "거시/경제 전망",
        "sector_research": "섹터/산업 전망",
        "market_research": "전체 시황/투자 동향",
        "research_memory": "리서치 메모리",
        "other": "기타",
    }
    raw_value = enum_or_str_value(value)
    return labels.get(raw_value, raw_value)


def translate_data_label(value: str) -> str:
    labels = {
        "linked_workspace_reports": "연결 가능한 저장 리포트",
        "last_price": "최근 가격",
        "average_volume": "평균 거래량",
        "estimated_volatility": "추정 변동성",
        "market_cap": "시가총액",
        "revenue_growth": "매출 성장률",
        "gross_margin": "매출총이익률",
        "operating_margin": "영업이익률",
        "free_cash_flow_margin": "잉여현금흐름 마진",
        "net_debt_to_ebitda": "순부채/EBITDA",
        "pe_ratio": "PER",
        "eps": "주당순이익",
        "revenue": "매출",
        "guidance": "가이던스",
    }
    return labels.get(value, value)


def translate_trade_style_label(value: str) -> str:
    labels = {
        "scalp": "아주 짧게 매매",
        "day": "하루 안에 매매",
        "swing": "단기 보유(며칠~몇 주)",
        "position": "중기 보유(몇 주~몇 달)",
    }
    return labels.get(value, value)


def sector_research_key(runtime, region: str, style: str) -> str:
    style_labels = {
        "성장": "GROWTH",
        "growth": "GROWTH",
        "균형형": "BALANCED",
        "balanced": "BALANCED",
        "가치": "VALUE",
        "value": "VALUE",
        "방어": "DEFENSIVE",
        "defensive": "DEFENSIVE",
    }
    region_key = "KR" if region.upper().startswith(("KR", "KOREA", "한국")) else "US"
    style_key = style_labels.get(style.strip(), runtime.normalize_ticker(style))
    return f"SECTOR-{region_key}-{style_key}"


def compounder_research_key(runtime, region: str, sector: str, style: str) -> str:
    sector_labels = {
        "전체": "ALL",
        "all": "ALL",
        "기술": "TECH",
        "technology": "TECH",
        "헬스케어": "HEALTHCARE",
        "healthcare": "HEALTHCARE",
        "소비재": "CONSUMER",
        "consumer": "CONSUMER",
        "금융": "FINANCIALS",
        "financials": "FINANCIALS",
        "산업재": "INDUSTRIALS",
        "industrials": "INDUSTRIALS",
    }
    style_labels = {
        "퀄리티 성장": "QUALITY-GROWTH",
        "quality growth": "QUALITY-GROWTH",
        "고성장": "HIGH-GROWTH",
        "high growth": "HIGH-GROWTH",
        "방어 성장": "DEFENSIVE-GROWTH",
        "defensive growth": "DEFENSIVE-GROWTH",
    }
    region_key = "KR" if region.upper().startswith(("KR", "KOREA", "한국")) else "US"
    sector_key = sector_labels.get(sector.strip().lower(), sector_labels.get(sector.strip(), runtime.normalize_ticker(sector)))
    style_key = style_labels.get(style.strip().lower(), style_labels.get(style.strip(), runtime.normalize_ticker(style)))
    return f"COMPOUNDER-{region_key}-{sector_key}-{style_key}"


def build_checklist_statuses(checked_items: list[str], checklist_items: list[tuple[str, str]]) -> list[ChecklistItemStatus]:
    checked = {item.strip() for item in checked_items}
    return [
        ChecklistItemStatus(key=key, label=label, completed=key in checked)
        for key, label in checklist_items
    ]
