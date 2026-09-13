from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.dart_annual_report_lab import (
    DartQuotaExceeded,
    begin_dart_request,
    build_dart_annual_report_lab_status,
    classify_dart_response,
    complete_dart_request,
    dart_lab_db_path,
    refresh_dart_annual_report_index,
)
from research_os import dart_filing_watch
from research_os.opendart_data_provider import OpenDartClient
from research_os.settings import Settings


def _settings(tmp_path: Path, *, cap: int = 15_000, reference: int = 20_000) -> Settings:
    return Settings(
        research_vault_dir=str(tmp_path / "research_vault"),
        dart_api_key="A" * 40,
        dart_corp_code_cache_file=str(tmp_path / "corp_codes.json"),
        dart_daily_self_cap=cap,
        dart_provider_limit_reference=reference,
    )


def test_body_status_is_independent_from_http_status() -> None:
    assert classify_dart_response(http_status=200, dart_status="000") == "ok"
    assert classify_dart_response(http_status=200, dart_status="013") == "empty"
    assert classify_dart_response(http_status=200, dart_status="010") == "dart_err"
    assert classify_dart_response(http_status=503, dart_status=None) == "http_err"


def test_quota_stops_before_network_and_ledger_does_not_store_secret(tmp_path: Path) -> None:
    settings = _settings(tmp_path, cap=1, reference=2)
    event_id = begin_dart_request(
        settings,
        job_name="test_probe",
        api_name="list.json",
        target="005930",
    )
    complete_dart_request(
        settings,
        event_id,
        outcome="dart_err",
        http_status=200,
        dart_status="010",
        message=f"https://opendart.fss.or.kr/api/list.json?crtfc_key={settings.dart_api_key}",
        secret=settings.dart_api_key,
    )
    with pytest.raises(DartQuotaExceeded):
        begin_dart_request(
            settings,
            job_name="test_probe",
            api_name="list.json",
            target="000660",
        )

    status = build_dart_annual_report_lab_status(
        settings,
        dart_cache={"entries": {}},
        target_universe={"target_tickers": ["005930"], "target_count": 1},
    )
    assert status["quota"]["recorded_requests"] == 1
    assert status["quota"]["quota_stopped"] is True
    assert status["activity_30d"][-1]["status"] == "quota_stopped"
    assert all(settings.dart_api_key not in str(item) for item in status["recent_failures"])
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(f"{dart_lab_db_path(settings)}{suffix}")
        if candidate.exists():
            assert settings.dart_api_key.encode("utf-8") not in candidate.read_bytes()


def test_misconfigured_cap_is_clamped_to_seventy_five_percent(tmp_path: Path) -> None:
    settings = _settings(tmp_path, cap=99_999, reference=20_000)
    status = build_dart_annual_report_lab_status(
        settings,
        dart_cache={"entries": {}},
        target_universe={"target_tickers": [], "target_count": 0},
    )

    assert status["quota"]["configured_self_cap"] == 99_999
    assert status["quota"]["self_cap"] == 15_000
    assert status["quota"]["self_cap_clamped"] is True
    quota_policy = next(
        item for item in status["policy_checks"] if item["key"] == "quota_preemption"
    )
    assert quota_policy["passed"] is True


def test_existing_daily_filing_watch_skips_duplicate_full_universe_run(tmp_path: Path) -> None:
    cache = {"daily_check": {"date": "2026-09-14"}}
    runtime = SimpleNamespace(
        read_dart_filing_cache=lambda _settings: cache,
        dart_daily_check_status=lambda _cache, _settings: {
            "due": False,
            "current_target_count": 93,
            "target_universe": {"target_count": 93},
        },
        dart_filing_cache_path=lambda _settings: tmp_path / "dart-cache.json",
    )

    result = dart_filing_watch.refresh_dart_filing_watch(runtime, object())

    assert result["status"] == "skipped"
    assert "중복 호출" in result["reason"]
    assert result["target_count"] == 93
    assert result["saved_count"] == 0


def test_no_filing_result_uses_per_ticker_check_freshness() -> None:
    now = datetime(2026, 9, 14, 7, 0, tzinfo=timezone.utc)
    runtime = SimpleNamespace(
        normalize_ticker=lambda value: str(value).strip(),
        parse_iso_datetime=lambda value: datetime.fromisoformat(str(value)) if value else None,
        current_storage_date=lambda: now.date(),
        current_storage_datetime=lambda: now,
    )
    settings = SimpleNamespace(dart_filing_refresh_hours=6)
    cache = {
        "updated_at": now.isoformat(),
        "entries": {},
        "ticker_checks": {
            "005930": {
                "checked_at": now.isoformat(),
                "status": "success",
                "filing_count": 0,
            }
        },
    }

    assert dart_filing_watch.dart_cache_needs_ticker_refresh(
        runtime,
        cache,
        "005930",
        settings,
    ) is False


def test_earnings_scheduler_skips_fresh_cache_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    import research_os_main as main

    now = main.current_storage_timestamp()
    settings = SimpleNamespace(earnings_calendar_refresh_hours=12)
    monkeypatch.setattr(main, "portfolio_calendar_tickers", lambda _settings: ["005930", "000660"])
    monkeypatch.setattr(
        main,
        "read_earnings_calendar_cache",
        lambda _settings: {
            "entries": {
                "005930": {"updated_at": now, "status": "success"},
                "000660": {"updated_at": now, "status": "success"},
            }
        },
    )
    monkeypatch.setattr(
        main,
        "refresh_earnings_calendar_cache",
        lambda *_args, **_kwargs: pytest.fail("fresh scheduler entries must not refresh"),
    )
    monkeypatch.setattr(main, "earnings_calendar_cache_path", lambda _settings: Path("cache.json"))

    result = main.refresh_due_earnings_calendar_cache(settings)

    assert result["status"] == "skipped"
    assert result["requested_count"] == 0


class _Response:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.content = json.dumps(payload).encode("utf-8")

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if not 200 <= self.status_code < 300:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_fresh_corp_code_cache_is_a_negative_cache_for_non_dart_security(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    Path(settings.dart_corp_code_cache_file).write_text(
        json.dumps(
            {
                "by_stock_code": {
                    "005930": {
                        "corp_code": "00126380",
                        "corp_name": "삼성전자",
                        "stock_code": "005930",
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    client = OpenDartClient(settings)
    monkeypatch.setattr(
        client,
        "_download_corp_codes",
        lambda: pytest.fail("fresh full corp-code cache must not be downloaded again"),
    )

    assert client.find_corp_by_stock_code("360750") is None
    assert client.find_corp_by_stock_code("360750") is None


def test_a001_request_uses_official_filters_and_records_http_200_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    Path(settings.dart_corp_code_cache_file).write_text(
        json.dumps(
            {
                "by_stock_code": {
                    "005930": {
                        "corp_code": "00126380",
                        "corp_name": "삼성전자",
                        "stock_code": "005930",
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    captured: dict = {}

    def fake_get(url, *, params, timeout, trust_env):
        captured.update({"url": url, "params": params, "timeout": timeout, "trust_env": trust_env})
        return _Response({"status": "010", "message": "등록되지 않은 인증키입니다."})

    monkeypatch.setattr("research_os.opendart_data_provider.httpx.get", fake_get)
    client = OpenDartClient(settings, job_name="a001_test")
    with pytest.raises(RuntimeError, match="등록되지 않은 인증키"):
        client.fetch_recent_filings(
            "005930",
            lookback_days=800,
            page_count=10,
            detail_type="A001",
            final_reports_only=True,
        )

    assert captured["params"]["pblntf_detail_ty"] == "A001"
    assert captured["params"]["last_reprt_at"] == "Y"
    status = build_dart_annual_report_lab_status(
        settings,
        dart_cache={"entries": {}},
        target_universe={"target_tickers": ["005930"], "target_count": 1},
    )
    failure = status["recent_failures"][0]
    assert failure["outcome"] == "dart_err"
    assert failure["http_status"] == 200
    assert failure["dart_status"] == "010"


def test_no_data_status_is_an_empty_result_not_a_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    Path(settings.dart_corp_code_cache_file).write_text(
        json.dumps(
            {
                "by_stock_code": {
                    "005930": {
                        "corp_code": "00126380",
                        "corp_name": "삼성전자",
                        "stock_code": "005930",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "research_os.opendart_data_provider.httpx.get",
        lambda *args, **kwargs: _Response({"status": "013", "message": "조회된 데이타가 없습니다."}),
    )
    _, filings = OpenDartClient(settings).fetch_recent_filings(
        "005930",
        detail_type="A001",
        final_reports_only=True,
    )
    assert filings == []
    status = build_dart_annual_report_lab_status(
        settings,
        dart_cache={"entries": {}},
        target_universe={"target_tickers": ["005930"], "target_count": 1},
    )
    assert status["activity_30d"][-1]["empty_count"] == 1
    assert status["recent_failures"] == []


def test_bounded_refresh_rotates_family_universe_and_marks_a001(tmp_path: Path) -> None:
    settings = _settings(tmp_path)

    class FakeClient:
        is_configured = True

        def __init__(self) -> None:
            self.calls: list[tuple[str, dict]] = []

        def fetch_recent_filings(self, ticker: str, **kwargs):
            self.calls.append((ticker, kwargs))
            return (
                {"corp_name": f"회사-{ticker}"},
                [
                    {
                        "rcept_no": f"20260913{ticker}",
                        "report_name": "사업보고서 (2025.12)",
                        "receipt_date": "20260331",
                        "source_url": f"https://dart.fss.or.kr/{ticker}",
                    }
                ],
            )

    class FakeStorage:
        def model_dump(self, mode="json"):
            return {"relative_path": "saved.md", "mode": mode}

    client = FakeClient()
    cache: dict = {"entries": {}}
    writes: list[dict] = []
    result = refresh_dart_annual_report_index(
        settings,
        dart_cache=cache,
        target_universe={
            "target_tickers": ["005930", "000660", "035420"],
            "target_count": 3,
        },
        client=client,
        normalize_ticker=lambda value: value.strip(),
        cache_key=lambda ticker, filing: f"{ticker}:{filing['rcept_no']}",
        filing_importance=lambda _name: ("높음", "사업보고서 검토", ["earnings"]),
        save_item=lambda _ticker, _filing, _settings: FakeStorage(),
        write_cache=lambda _settings, payload: writes.append(payload.copy()),
        max_tickers=2,
    )
    assert result["status"] == "success"
    assert result["selected_tickers"] == ["005930", "000660"]
    assert result["next_cursor"] == 2
    assert result["saved_count"] == 2
    assert all(call[1]["detail_type"] == "A001" for call in client.calls)
    assert all(call[1]["final_reports_only"] is True for call in client.calls)
    assert all(entry["filing"]["detail_type"] == "A001" for entry in cache["entries"].values())
    assert writes
    assert result["safety"] == {"orders": False, "messages": False, "account_changes": False}


def test_console_and_daily_pipeline_contracts() -> None:
    html = (PROJECT_ROOT / "mobile_app" / "research_console" / "index.html").read_text(
        encoding="utf-8"
    )
    api = (PROJECT_ROOT / "mobile_app" / "research_console" / "api.js").read_text(
        encoding="utf-8"
    )
    console = (PROJECT_ROOT / "mobile_app" / "research_console" / "console.js").read_text(
        encoding="utf-8"
    )
    daily = (PROJECT_ROOT / "tools" / "run_daily_research_operations.ps1").read_text(
        encoding="utf-8"
    )
    assert 'data-tab="dartAnnualLab"' in html
    assert 'id="dartAnnualLabContent"' in html
    assert "투자 권유나 매매 신호가 아닙니다" in html
    assert "fetchDartAnnualReportLabStatus" in api
    assert "refreshDartAnnualReportLab" in api
    assert "renderDartAnnualReportLab" in console
    assert "NO RUN" in console
    assert "SkipDartAnnualReportLab" in daily
    assert "/api/v1/dart/annual-report-lab/refresh" in daily
