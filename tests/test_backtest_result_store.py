import sys
from pathlib import Path
from types import SimpleNamespace

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import research_os_main as main
from research_os.models import BacktestResultSaveRequest


def test_confirmed_backtest_result_is_deduplicated_and_calibrated(monkeypatch):
    writes = []
    monkeypatch.setattr(
        main,
        "read_json_store",
        lambda path, default: {"results": [{"run_id": "same", "symbols": ["005930"]}]},
    )
    monkeypatch.setattr(main, "write_json_store", lambda path, payload: writes.append(payload))
    monkeypatch.setattr(main, "backtest_result_store_path", lambda settings: "unused")
    monkeypatch.setattr(main, "current_storage_timestamp", lambda: "2026-07-13T00:00:00+09:00")

    response = main.save_confirmed_backtest_result(
        BacktestResultSaveRequest(
            run_id="same",
            status="success",
            symbols=["005930"],
            strategy_name="regression",
            trades_count=4,
        ),
        settings=SimpleNamespace(),
    )

    assert response.saved_count == 1
    assert response.results[0]["evidence_strength"] == "low"
    assert writes[0]["results"][0]["run_id"] == "same"


def test_list_backtest_results_filters_ticker(monkeypatch):
    monkeypatch.setattr(
        main,
        "read_json_store",
        lambda path, default: {
            "results": [
                {"run_id": "a", "symbols": ["005930"], "saved_at": "2026-07-13T01:00:00+09:00"},
                {"run_id": "b", "symbols": ["AAPL"], "saved_at": "2026-07-13T02:00:00+09:00"},
            ]
        },
    )
    monkeypatch.setattr(main, "backtest_result_store_path", lambda settings: "unused")

    response = main.list_backtest_results("005930", 20, settings=SimpleNamespace())

    assert response.saved_count == 1
    assert response.results[0]["run_id"] == "a"


def test_read_backtest_runs_adds_local_company_names_without_external_lookup(monkeypatch):
    monkeypatch.setattr(
        main,
        "_read_backtest_runs",
        lambda settings: [{"run_id": "daily", "symbols": ["005940", "UNKNOWN", "005940"]}],
    )
    monkeypatch.setattr(
        main,
        "read_dynamic_ticker_registry",
        lambda settings: {"005940": {"company_name": "NH투자증권"}},
    )

    response = main.read_backtest_runs(limit=20, settings=SimpleNamespace())

    assert response["count"] == 1
    assert response["runs"][0]["symbols"] == ["005940", "UNKNOWN", "005940"]
    assert response["runs"][0]["symbol_details"] == [
        {"ticker": "005940", "company_name": "NH투자증권"},
        {"ticker": "UNKNOWN", "company_name": ""},
    ]
