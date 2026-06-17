"""Pure metadata helpers for DART filing watch entries."""

from __future__ import annotations

from datetime import date
from re import fullmatch, search


def dart_periodic_quarter_label(report_name: str, receipt_date: str | None) -> str | None:
    name = str(report_name or "")
    if not any(keyword in name for keyword in ["사업보고서", "반기보고서", "분기보고서"]):
        return None
    period_match = search(r"\((20\d{2})[.\-/년\s]*(0?[369]|1[012])", name)
    report_year = None
    report_month = None
    if period_match:
        report_year = int(period_match.group(1))
        report_month = int(period_match.group(2))
    elif receipt_date and fullmatch(r"\d{8}", receipt_date):
        receipt_year = int(receipt_date[:4])
        if "사업보고서" in name:
            report_year = receipt_year - 1
            report_month = 12
        else:
            report_year = receipt_year
            report_month = 6 if "반기보고서" in name else 3
    if not report_year or not report_month:
        return None
    if "사업보고서" in name or report_month == 12:
        return f"FY{report_year} Annual"
    if "반기보고서" in name or report_month == 6:
        return f"FY{report_year} Q2"
    if report_month == 9:
        return f"FY{report_year} Q3"
    return f"FY{report_year} Q1"


def korean_earnings_neighbor_dates(quarter_label: str | None) -> tuple[str | None, str | None]:
    if not quarter_label:
        return None, None
    match = search(r"FY(\d{4})\s+(Annual|Q[123])", quarter_label)
    if not match:
        return None, None
    year = int(match.group(1))
    period = match.group(2)
    if period == "Annual":
        return date(year, 11, 14).isoformat(), date(year + 1, 5, 15).isoformat()
    if period == "Q1":
        return date(year, 3, 31).isoformat(), date(year, 8, 14).isoformat()
    if period == "Q2":
        return date(year, 5, 15).isoformat(), date(year, 11, 14).isoformat()
    if period == "Q3":
        return date(year, 8, 14).isoformat(), date(year + 1, 3, 31).isoformat()
    return None, None


def dart_filing_importance(report_name: str) -> tuple[str, str, list[str]]:
    name = report_name or ""
    tags = ["dart", "official_filing", "공시"]
    if any(keyword in name for keyword in ["사업보고서", "반기보고서", "분기보고서"]):
        return "높음", "정기보고서: 실적/재무/사업 리스크 업데이트 필요", tags + ["earnings", "financials"]
    if "주요사항보고서" in name:
        return "높음", "주요사항보고서: 투자 판단 변화 가능성이 큰 이벤트", tags + ["event", "risk"]
    if any(keyword in name for keyword in ["대량보유", "임원", "최대주주", "소유상황"]):
        return "중간", "지분/임원/주주 변화: 수급과 지배구조 확인 필요", tags + ["ownership", "flows"]
    if any(keyword in name for keyword in ["증권신고서", "투자설명서", "유상증자", "전환사채"]):
        return "높음", "자금조달/희석 가능성: 밸류에이션과 리스크 재점검 필요", tags + ["financing", "dilution"]
    return "보통", "일반 공시: 기존 투자 논거와 관련성 확인", tags


def dart_filing_cache_key(normalized_ticker: str, filing: dict) -> str:
    return f"{normalized_ticker}:{filing.get('rcept_no') or ''}"


def render_dart_filing_markdown(ticker: str, filing: dict, importance: str, action: str) -> str:
    company = filing.get("corp_name") or ticker
    report_name = filing.get("report_name") or "공시명 미확인"
    receipt_date = filing.get("receipt_date") or "날짜 미확인"
    source_url = filing.get("source_url") or "https://dart.fss.or.kr/"
    return f"""# DART 신규 공시 감시

티커: {ticker}
회사: {company}
공시명: {report_name}
접수일: {receipt_date}
중요도: {importance}
원문: {source_url}

## 자동 판단
- {action}
- 보유종목/관심종목에 포함된 한국 종목에서 신규 공시가 감지되었습니다.
- 다음 팀 리포트, 리스크 스캔, 실적 분석 실행 시 공식 공시 근거로 함께 활용합니다.

## 확인할 것
- 이번 공시가 매출, 마진, 현금흐름, 지분 구조, 자금조달, 경영 리스크 중 어느 항목을 바꾸는지 확인
- 기존 강세/약세 논거와 충돌하는 내용이 있는지 확인
- 주가 반응과 수급 변화를 다음 거래일에 점검
"""


def classify_dart_filing_refresh_error(exc: Exception) -> dict:
    error_text = str(exc)
    lowered = error_text.lower()
    if "corp_code를 찾지 못했습니다" in error_text:
        return {
            "category": "needs_mapping_review",
            "retryable": False,
            "message": error_text,
            "next_action": "OpenDART corp_code 매칭 대상인지 확인하세요. ETF/ETN이면 DART 감시 대상에서 제외해야 합니다.",
        }
    retryable = any(
        keyword in lowered
        for keyword in [
            "timeout",
            "timed out",
            "connection",
            "temporarily",
            "429",
            "rate",
            "too many",
            "service unavailable",
            "bad gateway",
        ]
    )
    return {
        "category": "transient_provider_error" if retryable else "provider_error",
        "retryable": retryable,
        "message": error_text,
        "next_action": "일시 오류로 판단되면 공시 재점검을 다시 실행하세요." if retryable else "오류 메시지와 OpenDART 응답 상태를 확인하세요.",
    }
