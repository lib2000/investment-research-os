"""DART filing watch status and formatting helpers."""

from __future__ import annotations

from datetime import datetime, timedelta
from re import fullmatch

from research_os import dart_watch_universe as dart_watch_universe_helpers
from research_os import dart_filing_metadata


def recent_dart_cache_entries(runtime, cache: dict, ticker: str | None = None, limit: int = 5) -> list[dict]:
    normalized_ticker = runtime.normalize_ticker(ticker) if ticker else ""
    entries = list((cache.get("entries") or {}).values())
    if normalized_ticker:
        entries = [
            entry
            for entry in entries
            if runtime.normalize_ticker(entry.get("ticker") or "") == normalized_ticker
        ]
    entries.sort(
        key=lambda entry: (
            str(((entry.get("filing") or {}).get("receipt_date")) or ""),
            str(entry.get("detected_at") or ""),
        ),
        reverse=True,
    )
    return entries[:limit]


def build_dart_filing_signal(runtime, ticker: str, settings) -> dict:
    cache = runtime.read_dart_filing_cache(settings)
    normalized_ticker = runtime.normalize_ticker(ticker)
    recent_entries = recent_dart_cache_entries(runtime, cache, normalized_ticker, limit=3)
    failures = [
        item
        for item in (cache.get("last_failures") or [])
        if runtime.normalize_ticker(str((item or {}).get("ticker") or "")) == normalized_ticker
    ]
    latest_entry = recent_entries[0] if recent_entries else {}
    filing = latest_entry.get("filing") or {}
    latest_failure = failures[0] if failures else {}
    important_count = sum(1 for entry in recent_entries if entry.get("importance") == "높음")
    ownership_count = sum(
        1
        for entry in recent_entries
        if any(tag in (entry.get("tags") or []) for tag in ["ownership", "flows"])
    )
    periodic_count = sum(
        1
        for entry in recent_entries
        if any(tag in (entry.get("tags") or []) for tag in ["earnings", "financials"])
    )
    if recent_entries:
        tone = "warning" if important_count else "ok"
        headline = f"{filing.get('report_name') or '공시명 미확인'}"
        signal_bits = []
        if important_count:
            signal_bits.append(f"중요 공시 {important_count}건")
        if periodic_count:
            signal_bits.append(f"정기보고서/재무 {periodic_count}건")
        if ownership_count:
            signal_bits.append(f"지분·수급 {ownership_count}건")
        summary = (
            f"{', '.join(signal_bits)} 감지. {latest_entry.get('action') or '최근 DART 공시를 투자 논거와 리스크에 반영하세요.'}"
            if signal_bits
            else latest_entry.get("action") or "최근 DART 공시가 감지되었습니다."
        )
    elif latest_failure:
        tone = "warning"
        headline = "최근 조회 실패"
        summary = runtime.provider_error_message(latest_failure.get("error") or "DART 접속 실패", settings)
    else:
        tone = "neutral"
        headline = "신규 공시 없음"
        summary = "최근 자동 감시 캐시에 이 종목의 신규 DART 공시가 없습니다."
    return {
        "enabled": bool(settings.dart_filing_auto_refresh and settings.dart_api_key),
        "configured": bool(settings.dart_api_key),
        "ticker": normalized_ticker,
        "tone": tone,
        "headline": headline,
        "summary": summary,
        "updated_at": cache.get("updated_at"),
        "last_run": cache.get("last_run"),
        "lookback_days": settings.dart_filing_lookback_days,
        "refresh_hours": settings.dart_filing_refresh_hours,
        "recent_count": len(recent_entries),
        "important_count": important_count,
        "ownership_count": ownership_count,
        "periodic_count": periodic_count,
        "failure_count": len(failures),
        "recent_entries": recent_entries,
        "latest_failure": latest_failure,
    }


def summarize_dart_filing_context(signal: dict | None) -> str:
    if not isinstance(signal, dict) or not signal.get("recent_count"):
        return ""
    entries = signal.get("recent_entries") or []
    snippets: list[str] = []
    for entry in entries[:3]:
        filing = entry.get("filing") or {}
        report_name = filing.get("report_name") or "공시명 미확인"
        receipt_date = filing.get("receipt_date") or "날짜 미확인"
        importance = entry.get("importance") or "보통"
        action = entry.get("action") or "기존 투자 논거와 관련성을 확인하세요."
        snippets.append(f"{receipt_date} {report_name}({importance}) - {action}")
    return " / ".join(snippets)


def dart_cache_needs_ticker_refresh(runtime, cache: dict, ticker: str, settings) -> bool:
    normalized_ticker = runtime.normalize_ticker(ticker)
    updated_at = runtime.parse_iso_datetime(cache.get("updated_at"))
    if not updated_at:
        return True
    max_age = timedelta(minutes=max(float(settings.live_data_max_age_minutes), 1.0))
    if runtime.current_storage_datetime() - updated_at > max_age:
        return True
    return not recent_dart_cache_entries(runtime, cache, normalized_ticker, limit=1)


def refresh_dart_filing_for_ticker_if_stale(runtime, ticker: str, settings) -> dict:
    normalized_ticker = runtime.normalize_ticker(ticker)
    if not (settings.dart_filing_auto_refresh and settings.dart_api_key):
        return {"status": "skipped", "ticker": normalized_ticker, "reason": "dart_disabled"}
    if not fullmatch(r"\d{6}", normalized_ticker):
        return {"status": "skipped", "ticker": normalized_ticker, "reason": "non_kr_ticker"}
    cache = runtime.read_dart_filing_cache(settings)
    if not dart_cache_needs_ticker_refresh(runtime, cache, normalized_ticker, settings):
        return {"status": "fresh", "ticker": normalized_ticker, "updated_at": cache.get("updated_at")}
    try:
        return runtime.refresh_dart_filing_watch(
            settings,
            [normalized_ticker],
            force=False,
            save_result=False,
        )
    except Exception as exc:
        return {
            "status": "failed",
            "ticker": normalized_ticker,
            "error": runtime.provider_error_message(exc, settings),
        }


def dart_periodic_quarter_label(report_name: str, receipt_date: str | None) -> str | None:
    return dart_filing_metadata.dart_periodic_quarter_label(report_name, receipt_date)


def korean_earnings_neighbor_dates(quarter_label: str | None) -> tuple[str | None, str | None]:
    return dart_filing_metadata.korean_earnings_neighbor_dates(quarter_label)


def merge_dart_latest_earnings_calendar(
    runtime,
    ticker: str,
    profile: dict,
    settings,
    *,
    refresh_if_stale: bool = True,
) -> dict:
    asset_type = str((profile or {}).get("asset_type") or "equity").strip().lower()
    if (
        not settings
        or not profile
        or profile.get("country") != "KR"
        or asset_type in {"cash", "etf", "fund", "infrastructure_fund", "mutual_fund"}
    ):
        return profile
    normalized_ticker = runtime.normalize_ticker(ticker)
    if refresh_if_stale:
        runtime.refresh_dart_filing_for_ticker_if_stale(normalized_ticker, settings)
    signal = runtime.build_dart_filing_signal(normalized_ticker, settings)
    entries = []
    for entry in signal.get("recent_entries") or []:
        filing = entry.get("filing") or {}
        report_name = str(filing.get("report_name") or "")
        quarter_label = dart_periodic_quarter_label(report_name, filing.get("receipt_date"))
        receipt_date = str(filing.get("receipt_date") or "")
        if quarter_label and fullmatch(r"\d{8}", receipt_date):
            entries.append((receipt_date, quarter_label, filing))
    if not entries:
        return profile
    receipt_date, quarter_label, filing = sorted(entries, key=lambda item: item[0], reverse=True)[0]
    latest_date = datetime.strptime(receipt_date, "%Y%m%d").date().isoformat()
    current_latest = runtime.parse_iso_date(profile.get("latest_reported_earnings_date"))
    latest_parsed = runtime.parse_iso_date(latest_date)
    current_source = str(profile.get("earnings_calendar_source") or "")
    current_quarter = runtime.normalize_quarter_label(profile.get("latest_reported_quarter"))
    dart_quarter = runtime.normalize_quarter_label(quarter_label)
    schedule_fallback = "DART 정기보고서 제출 기한 기준" in current_source
    if (
        current_latest
        and latest_parsed
        and latest_parsed < current_latest
        and not (schedule_fallback and current_quarter == dart_quarter)
    ):
        return profile
    previous_date, next_date = korean_earnings_neighbor_dates(quarter_label)
    enriched = dict(profile)
    enriched["latest_reported_quarter"] = quarter_label
    enriched["latest_reported_earnings_date"] = latest_date
    if previous_date:
        enriched["previous_earnings_date"] = previous_date
    if next_date:
        enriched["next_earnings_date"] = next_date
    source_url = filing.get("source_url") or "https://dart.fss.or.kr/"
    enriched["earnings_calendar_source"] = (
        f"OpenDART 신규 공시 목록 · {filing.get('report_name') or '정기보고서'} "
        f"접수일 {latest_date}"
    )
    latest_profile = dict(enriched.get("latest_earnings_profile") or {})
    latest_profile.update(
        {
            "quarter": quarter_label,
            "earnings_report_date": latest_date,
            "previous_earnings_summary": (
                f"DART에서 {filing.get('report_name') or '정기보고서'} 접수가 확인되어 "
                f"최신 실적 기준을 {quarter_label}로 갱신했습니다."
            ),
            "next_earnings_guidance": (
                "다음 실적 전 확인할 KPI: "
                + ", ".join(str(item) for item in (enriched.get("watch_kpis") or [])[:5])
            ),
            "source_url": source_url,
        }
    )
    enriched["latest_earnings_profile"] = latest_profile
    limitations = [
        item for item in enriched.get("data_limitations", [])
        if "DART 정기보고서 제출 기한 기준" not in str(item)
    ]
    limitations.append("DART 신규 공시 목록으로 최신 실적 기준일을 보정했습니다.")
    enriched["data_limitations"] = limitations
    return enriched


def dart_watch_universe(runtime, settings) -> dict:
    return dart_watch_universe_helpers.dart_watch_universe(runtime, settings)


def dart_watch_tickers(runtime, settings) -> list[str]:
    return dart_watch_universe_helpers.dart_watch_tickers(runtime, settings)


def dart_daily_check_status(runtime, cache: dict, settings) -> dict:
    return dart_watch_universe_helpers.dart_daily_check_status(runtime, cache, settings)


def active_dart_last_failures(runtime, cache: dict, target_universe: dict, limit: int = 10) -> list[dict]:
    return dart_watch_universe_helpers.active_dart_last_failures(runtime, cache, target_universe, limit)


def dart_filing_importance(report_name: str) -> tuple[str, str, list[str]]:
    return dart_filing_metadata.dart_filing_importance(report_name)


def dart_filing_cache_key(runtime, ticker: str, filing: dict) -> str:
    return dart_filing_metadata.dart_filing_cache_key(runtime.normalize_ticker(ticker), filing)


def render_dart_filing_markdown(ticker: str, filing: dict, importance: str, action: str) -> str:
    return dart_filing_metadata.render_dart_filing_markdown(ticker, filing, importance, action)


def classify_dart_filing_refresh_error(exc: Exception) -> dict:
    return dart_filing_metadata.classify_dart_filing_refresh_error(exc)


def refresh_dart_filing_watch(runtime, settings, tickers: list[str] | None = None, *, force: bool = False, save_result: bool = True) -> dict:
    cache = runtime.read_dart_filing_cache(settings)
    entries = cache.setdefault("entries", {})
    full_universe_refresh = tickers is None
    target_universe = runtime.dart_watch_universe(settings)
    selected_tickers = [
        runtime.normalize_ticker(item)
        for item in (tickers or target_universe.get("target_tickers") or [])
        if fullmatch(r"\d{6}", runtime.normalize_ticker(item))
    ]
    selected_tickers = list(dict.fromkeys(selected_tickers))
    client = runtime.OpenDartClient(settings)
    saved: list[dict] = []
    skipped: list[dict] = []
    failed: list[dict] = []
    if not client.is_configured:
        return {
            "status": "skipped",
            "module": "dart_filing_watch",
            "reason": "DART_API_KEY가 없어 DART 신규 공시 자동 감시를 건너뜁니다.",
            "target_count": len(selected_tickers),
            "target_universe": target_universe,
            "daily_check": runtime.dart_daily_check_status(cache, settings),
            "cache_path": str(runtime.dart_filing_cache_path(settings)),
        }

    for ticker in selected_tickers:
        attempts = 0
        try:
            while True:
                attempts += 1
                try:
                    corp, filings = client.fetch_recent_filings(
                        ticker,
                        lookback_days=settings.dart_filing_lookback_days,
                        page_count=settings.dart_filing_max_items_per_ticker,
                    )
                    break
                except Exception as exc:
                    failure_info = runtime.classify_dart_filing_refresh_error(exc)
                    if attempts < 2 and failure_info.get("retryable"):
                        continue
                    raise
            for filing in filings:
                key = runtime.dart_filing_cache_key(ticker, filing)
                if key in entries and not force:
                    skipped.append({"ticker": ticker, "rcept_no": filing.get("rcept_no")})
                    continue
                importance, action, tags = runtime.dart_filing_importance(str(filing.get("report_name") or ""))
                storage = runtime.save_dart_filing_watch_item(ticker, filing, settings) if save_result else None
                entry = {
                    "ticker": ticker,
                    "corp_name": corp.get("corp_name"),
                    "filing": filing,
                    "importance": importance,
                    "action": action,
                    "tags": tags,
                    "detected_at": runtime.current_storage_timestamp(),
                    "storage": storage.model_dump(mode="json") if storage else None,
                }
                entries[key] = entry
                saved.append(entry)
        except Exception as exc:
            failure_info = runtime.classify_dart_filing_refresh_error(exc)
            failed.append(
                {
                    "ticker": ticker,
                    "error": runtime.provider_error_message(exc, settings),
                    "category": failure_info.get("category"),
                    "retryable": failure_info.get("retryable"),
                    "attempts": attempts or 1,
                    "next_action": failure_info.get("next_action"),
                }
            )

    cache["updated_at"] = runtime.current_storage_timestamp()
    cache["last_run"] = runtime.current_storage_timestamp()
    cache["target_tickers"] = selected_tickers
    cache["target_universe"] = target_universe
    cache["source"] = "OpenDART list.json"
    cache["last_failures"] = failed
    cache["entries"] = dict(list(entries.items())[-800:])
    if full_universe_refresh:
        cache["daily_check"] = {
            "date": runtime.current_storage_date().isoformat(),
            "checked_at": runtime.current_storage_timestamp(),
            "target_count": len(selected_tickers),
            "checked_tickers": selected_tickers,
            "failed_tickers": [item.get("ticker") for item in failed if item.get("ticker")],
            "excluded_tickers": target_universe.get("excluded_tickers") or [],
            "saved_count": len(saved),
            "skipped_count": len(skipped),
            "lookback_days": settings.dart_filing_lookback_days,
            "source": "portfolio_and_interest_daily_watch",
        }
    runtime.write_dart_filing_cache(settings, cache)
    return {
        "status": "success" if not failed else "partial_success",
        "module": "dart_filing_watch",
        "target_count": len(selected_tickers),
        "target_universe": target_universe,
        "daily_check": runtime.dart_daily_check_status(cache, settings),
        "saved_count": len(saved),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "saved": saved,
        "skipped": skipped[:20],
        "failed": failed,
        "cache_path": str(runtime.dart_filing_cache_path(settings)),
    }
