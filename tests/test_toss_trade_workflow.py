from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.toss_trade_workflow import (
    analyze_news_items,
    build_trade_review,
    build_paper_evaluation,
    build_workflow_result,
    simulate_paper_fills,
)


def test_news_analysis_creates_review_only_proposal_for_existing_holding() -> None:
    result = analyze_news_items(
        [
            {
                "id": "news-1",
                "title": "플리토 신규 계약으로 성장 전망 상향",
                "summary": "호실적과 수주 증가",
                "source_url": "https://example.com/news-1",
                "scope": "300080",
                "confidence": 0.9,
            }
        ],
        [{"ticker": "300080", "quantity": 279}],
    )
    assert result["matched_news_count"] == 1
    assert result["proposals"][0]["action"] == "BUY_REVIEW"
    assert result["proposals"][0]["status"] == "manual_review_required"
    assert result["proposals"][0]["execution"] == "blocked_live_order"
    assert result["proposals"][0]["quantity"] is None


def test_trade_review_counts_partial_and_canceled_orders() -> None:
    review = build_trade_review(
        [
            {"side": "BUY", "status": "FILLED", "quantity": 43, "execution": {"filled_quantity": 43, "filled_amount": 371520}},
            {"side": "BUY", "status": "CANCELED", "quantity": 279, "execution": {"filled_quantity": 236, "filled_amount": 2027240}},
        ]
    )
    assert review["order_count"] == 2
    assert review["canceled_count"] == 1
    assert review["partial_fill_count"] == 1
    assert review["filled_quantity"] == 279
    assert review["filled_amount"] == 2398760


def test_workflow_result_blocks_live_trade_stage() -> None:
    result = build_workflow_result(
        run_at="2026-08-12T16:10:00+09:00",
        news_result={"news_count": 1, "proposals": [{"proposal_id": "p1"}]},
        orders=[],
    )
    assert result["stages"]["trade"]["status"] == "blocked_live_order"
    assert result["stages"]["trade"]["created_order_count"] == 0
    assert result["human_gate"]["required"] is True


def test_paper_simulation_is_deterministic_and_has_no_live_execution_marker() -> None:
    news = analyze_news_items(
        [{"id": "news-1", "title": "플리토 성장 호재", "scope": "300080"}],
        [{"ticker": "300080", "current_price": 8640}],
    )
    first = simulate_paper_fills(news, run_at="2026-08-12T16:10:00+09:00")
    second = simulate_paper_fills(news, run_at="2026-08-12T16:10:00+09:00")
    assert first == second
    assert first[0]["status"] == "simulated_filled"
    assert first[0]["quantity"] == 1
    assert first[0]["execution"] == "paper_only"
    assert "order_id" not in first[0]


def test_paper_evaluation_calculates_marked_pnl_and_drawdown() -> None:
    evaluation = build_paper_evaluation(
        [
            {
                "run_at": "2026-08-10T16:10:00+09:00",
                "paper_fills": [
                    {
                        "paper_order_id": "p1",
                        "symbol": "AAA",
                        "side": "BUY",
                        "status": "simulated_filled",
                        "quantity": 1,
                        "reference_price": 100,
                        "mark_price": 110,
                        "simulated_at": "2026-08-10T16:10:00+09:00",
                    }
                ],
            },
            {
                "run_at": "2026-08-11T16:10:00+09:00",
                "paper_fills": [
                    {
                        "paper_order_id": "p2",
                        "symbol": "BBB",
                        "side": "BUY",
                        "status": "simulated_filled",
                        "quantity": 1,
                        "reference_price": 100,
                        "mark_price": 90,
                        "simulated_at": "2026-08-11T16:10:00+09:00",
                    }
                ],
            },
        ],
        window_days=7,
        as_of_date="2026-08-11",
    )
    assert evaluation["sample_size"] == 2
    assert evaluation["pnl"] == 0
    assert evaluation["wins"] == 1
    assert evaluation["losses"] == 1
    assert evaluation["win_rate"] == 0.5
    assert evaluation["max_drawdown"] == 10
    assert evaluation["status"] == "insufficient_sample"
