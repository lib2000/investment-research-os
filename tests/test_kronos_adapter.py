import sys
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.kronos_adapter import (  # noqa: E402
    KronosAdapterError,
    KronosForecastAdapter,
    evaluate_model_benchmark_gate,
    evaluate_walk_forward,
    iter_walk_forward_windows,
    log_return_drift_forecast,
    sanitise_forecast_rows,
)


def _rows(count=8):
    return [
        {
            "timestamp": f"2026-01-{index + 1:02d}",
            "open": 100 + index,
            "high": 101 + index,
            "low": 99 + index,
            "close": 100.5 + index,
            "volume": 10,
        }
        for index in range(count)
    ]


class StubPredictor:
    def __init__(self):
        self.calls = []

    def predict(self, **kwargs):
        self.calls.append(kwargs)
        return [
            {"open": 108, "high": 107, "low": 109, "close": 108, "volume": -4},
            {"open": 109, "high": 110, "low": 108, "close": 109, "volume": 2},
        ]


def test_adapter_trims_context_and_records_safe_output_repairs():
    predictor = StubPredictor()
    result = KronosForecastAdapter(predictor, max_context=4).predict(
        _rows(6),
        y_timestamp=["2026-01-07", "2026-01-08"],
        pred_len=2,
    )

    assert result.diagnostics["context_rows_trimmed"] == 2
    assert result.diagnostics["output_repair_count"] == 3
    assert result.rows[0]["high"] == 108
    assert result.rows[0]["low"] == 108
    assert result.rows[0]["volume"] == 0
    assert len(predictor.calls[0]["df"]) == 4


def test_strict_output_mode_rejects_negative_volume():
    with pytest.raises(KronosAdapterError, match="negative"):
        sanitise_forecast_rows(
            [{"open": 1, "high": 2, "low": 0, "close": 1, "volume": -1}],
            ["2026-01-01"],
            pred_len=1,
            strict=True,
        )


def test_walk_forward_windows_are_chronological_and_non_overlapping_by_default():
    windows = list(iter_walk_forward_windows(_rows(9), lookback=3, horizon=2))
    assert len(windows) == 3
    assert windows[0][0][-1]["timestamp"] == "2026-01-03"
    assert windows[0][1][0]["timestamp"] == "2026-01-04"
    assert windows[1][0][0]["timestamp"] == "2026-01-03"
    assert windows[-1][1][-1]["timestamp"] == "2026-01-09"


def test_walk_forward_evaluation_compares_with_last_close_baseline():
    rows = _rows(9)

    def forecaster(history, timestamps):
        return [
            {
                "timestamp": timestamp,
                "open": history[-1]["close"],
                "high": history[-1]["close"] + 1,
                "low": history[-1]["close"] - 1,
                "close": history[-1]["close"],
            }
            for timestamp in timestamps
        ]

    metrics = evaluate_walk_forward(rows, forecaster, lookback=3, horizon=2)
    assert metrics.windows == 3
    assert metrics.observations == 6
    assert metrics.forecast_mae == metrics.naive_mae
    assert metrics.improvement_vs_naive_pct == 0


def test_log_return_drift_forecast_preserves_ohlc_invariants():
    forecast = log_return_drift_forecast(_rows(4), ["2026-02-01", "2026-02-02"])
    assert len(forecast) == 2
    assert forecast[0]["high"] >= max(forecast[0]["open"], forecast[0]["close"])
    assert forecast[0]["low"] <= min(forecast[0]["open"], forecast[0]["close"])
    assert forecast[0]["volume"] == 0.0


def test_benchmark_gate_keeps_underperforming_model_research_only():
    gate = evaluate_model_benchmark_gate(
        model_id="kronos-small",
        mean_improvement_vs_baseline_pct=-8.36,
        strict_failures=2,
        output_repairs=4,
        observations=30,
    )
    assert gate.decision == "hold_research_only"
    assert not gate.eligible_for_human_review
    assert gate.as_dict()["repair_rate"] == 4 / 30


def test_adapter_rejects_non_research_deployment_mode():
    with pytest.raises(KronosAdapterError, match="research_only"):
        KronosForecastAdapter(StubPredictor(), deployment_mode="live")
