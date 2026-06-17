"""DART filing watch status and formatting helpers."""

from __future__ import annotations

from datetime import datetime, timedelta


def dart_daily_check_status(runtime, cache: dict, settings) -> dict:
    today = runtime.current_storage_date().isoformat()
    daily_check = cache.get("daily_check") if isinstance(cache, dict) else {}
    if not isinstance(daily_check, dict):
        daily_check = {}
    checked_date = str(daily_check.get("date") or "")
    target_universe = runtime.dart_watch_universe(settings)
    missing_today = checked_date != today
    missing_targets = sorted(
        set(target_universe.get("target_tickers") or [])
        - set(daily_check.get("checked_tickers") or [])
    ) if not missing_today else list(target_universe.get("target_tickers") or [])
    target_ticker_set = {
        runtime.normalize_ticker(str(item))
        for item in (target_universe.get("target_tickers") or [])
        if runtime.normalize_ticker(str(item))
    }
    failed_tickers = sorted(
        {
            runtime.normalize_ticker(str(item))
            for item in (daily_check.get("failed_tickers") or [])
            if runtime.normalize_ticker(str(item)) and runtime.normalize_ticker(str(item)) in target_ticker_set
        }
    )
    excluded_tickers = target_universe.get("excluded_tickers") or daily_check.get("excluded_tickers") or []
    due = bool(missing_today or missing_targets)
    current_target_count = int(target_universe.get("target_count") or 0)
    checked_tickers = [
        runtime.normalize_ticker(str(item))
        for item in (daily_check.get("checked_tickers") or [])
        if runtime.normalize_ticker(str(item))
    ]
    checked_target_tickers = set(checked_tickers) & target_ticker_set
    checked_count = 0 if missing_today else len(checked_target_tickers - set(failed_tickers))
    coverage_rate = checked_count / current_target_count if current_target_count else 1.0
    if due:
        reliability_status = "점검 필요"
    elif failed_tickers:
        reliability_status = "부분 신뢰"
    else:
        reliability_status = "신뢰 가능"
    next_check_after = None
    checked_at = daily_check.get("checked_at")
    if checked_at:
        try:
            base_dt = datetime.fromisoformat(str(checked_at))
            next_check_after = (base_dt + timedelta(hours=max(settings.dart_filing_refresh_hours, 1))).isoformat()
        except ValueError:
            next_check_after = None
    return {
        "date": today,
        "status": "due" if due else "partial_success" if failed_tickers else "complete",
        "due": due,
        "last_checked_date": checked_date or None,
        "last_checked_at": checked_at,
        "next_check_after": next_check_after,
        "last_target_count": daily_check.get("target_count", 0),
        "current_target_count": current_target_count,
        "checked_count": checked_count,
        "coverage_rate": coverage_rate,
        "reliability_status": reliability_status,
        "reliability_message": (
            f"{today} 기준 {checked_count}/{current_target_count}개 종목 공시 점검 완료"
            if current_target_count
            else "점검 대상 국내 종목이 없습니다."
        ),
        "missing_tickers": missing_targets,
        "failed_tickers": failed_tickers,
        "failure_count": len(failed_tickers),
        "excluded_tickers": excluded_tickers,
        "excluded_count": len(excluded_tickers),
        "target_universe": target_universe,
    }


def active_dart_last_failures(runtime, cache: dict, target_universe: dict, limit: int = 10) -> list[dict]:
    """Return DART failures that still belong to the current watch universe."""
    if not isinstance(cache, dict):
        return []
    target_tickers = {
        runtime.normalize_ticker(str(item))
        for item in (target_universe.get("target_tickers") or [])
        if runtime.normalize_ticker(str(item))
    }
    excluded_tickers = {
        runtime.normalize_ticker(str((item or {}).get("ticker") or ""))
        for item in (target_universe.get("excluded_tickers") or [])
        if isinstance(item, dict) and runtime.normalize_ticker(str(item.get("ticker") or ""))
    }
    active_failures: list[dict] = []
    for item in cache.get("last_failures") or []:
        if not isinstance(item, dict):
            continue
        ticker = runtime.normalize_ticker(str(item.get("ticker") or ""))
        if ticker and ticker in excluded_tickers:
            continue
        if ticker and target_tickers and ticker not in target_tickers:
            continue
        active_failures.append(item)
        if len(active_failures) >= max(1, int(limit or 10)):
            break
    return active_failures


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


def dart_filing_cache_key(runtime, ticker: str, filing: dict) -> str:
    return f"{runtime.normalize_ticker(ticker)}:{filing.get('rcept_no') or ''}"


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