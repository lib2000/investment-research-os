from datetime import datetime
from pathlib import Path
import sys

import pytest
from pydantic import ValidationError


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.chart_copilot_evaluation import (  # noqa: E402
    ChartCopilotEvaluationRequest,
    build_chart_copilot_evaluation,
    build_chart_copilot_pilot_status,
)


def valid_request(**overrides):
    payload = {
        "ticker": "005930",
        "market": "KR",
        "analysis_as_of": "2026-08-01T15:30:00+09:00",
        "timeframes": ["1D", "4H"],
        "regime": "trending",
        "decision": "long",
        "confidence": 0.65,
        "support_levels": [95, 90],
        "resistance_levels": [115],
        "entry_price": 100,
        "stop_price": 95,
        "target_price": 115,
        "evidence": ["일봉 SMA 5가 SMA 20 위", "4H 스윙 저점 95"],
        "invalidation": "일봉 종가가 95 아래에서 마감",
        "alternate_scenario": "저항 115 돌파 실패 후 횡보",
        "missing_data": ["실시간 호가와 슬리피지"],
        "human_verdict": "accepted",
    }
    payload.update(overrides)
    return ChartCopilotEvaluationRequest(**payload)


def test_evaluation_calculates_rr_and_links_secret_free_backtest():
    evaluation = build_chart_copilot_evaluation(
        valid_request(),
        backtest_runs=[
            {
                "run_id": "sma-005930",
                "symbols": ["005930"],
                "strategy_name": "SMA 5/20",
                "total_return": 7.2,
                "max_drawdown": 4.5,
                "win_rate": 58,
                "trades_count": 8,
            }
        ],
        captured_at=datetime.fromisoformat("2026-08-01T16:00:00+09:00"),
    )

    assert evaluation["risk_reward"] == 3.0
    assert evaluation["baseline"]["run_id"] == "sma-005930"
    assert evaluation["evidence_strength"] == "medium"
    assert evaluation["score_meaning"] == "documentation_quality_not_prediction_confidence"
    assert evaluation["investment_use"] == "research_only"
    assert evaluation["live_order_allowed"] is False
    assert "account" not in evaluation
    assert "order" not in evaluation


def test_no_trade_is_a_first_class_result_without_inferred_prices():
    evaluation = build_chart_copilot_evaluation(
        valid_request(
            decision="no_trade",
            entry_price=None,
            stop_price=None,
            target_price=None,
            human_verdict="pending",
        )
    )

    assert evaluation["risk_reward"] is None
    assert evaluation["baseline"]["status"] == "unlinked"
    assert "사람 검토가 아직 완료되지 않았습니다." in evaluation["issues"]


def test_payload_rejects_credential_like_text_and_unknown_fields():
    with pytest.raises(ValidationError):
        valid_request(evidence=["Authorization: Bearer secret-value"])

    with pytest.raises(ValidationError):
        valid_request(evidence=["123456789:abcdefghijklmnopqrstuvwxyzABCDE12345"])

    with pytest.raises(ValidationError):
        ChartCopilotEvaluationRequest(**{**valid_request().model_dump(mode="json"), "account_number": "123"})


def test_pilot_requires_twenty_symbols_both_timeframes_fourteen_days_and_review():
    targets = [{"ticker": f"{index:06d}", "name": f"종목 {index}"} for index in range(1, 21)]
    evaluations = [
        {
            "ticker": target["ticker"],
            "timeframes": ["1D", "4H"],
            "analysis_as_of": "2026-08-01T16:00:00+09:00",
            "captured_at": "2026-08-01T16:01:00+09:00",
            "human_verdict": "accepted",
        }
        for target in targets
    ]

    status = build_chart_copilot_pilot_status(
        evaluations,
        target_tickers=targets,
        now=datetime.fromisoformat("2026-08-15T09:00:00+09:00"),
    )

    assert status["ready_for_review"] is True
    assert status["status"] == "ready_for_review"
    assert status["complete_ticker_count"] == 20
    assert status["captured_pair_count"] == 40
    assert status["reviewed_pair_count"] == 40
    assert status["elapsed_days"] == 15


def test_classic_console_exposes_safe_manual_pilot_without_order_action():
    root = Path(__file__).resolve().parents[1]
    html = (root / "mobile_app" / "research_console" / "index.html").read_text(encoding="utf-8")
    js = (root / "mobile_app" / "research_console" / "console.js").read_text(encoding="utf-8")
    api = (root / "mobile_app" / "research_console" / "api.js").read_text(encoding="utf-8")
    css = (root / "mobile_app" / "research_console" / "styles.css").read_text(encoding="utf-8")

    assert 'id="chartCopilotEvaluationForm"' in html
    assert "연구 전용·주문 연결 없음" in js
    assert "/api/v1/chart-copilot-pilot/evaluations" in api
    assert ".chart-copilot-evaluation-form" in css
    assert "chart-copilot-pilot/evaluations/order" not in api
