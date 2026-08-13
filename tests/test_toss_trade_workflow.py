from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.toss_trade_workflow import (
    apply_price_snapshot,
    analyze_news_items,
    build_evidence_review,
    build_trade_review,
    build_paper_evaluation,
    build_workflow_result,
    dedupe_paper_fill_history,
    refresh_paper_fill_marks,
    simulate_paper_fills,
)


def test_price_snapshot_populates_review_reference_prices() -> None:
    result = analyze_news_items(
        [{"id": "snapshot", "title": "SK하이닉스 성장 호재", "summary": "호실적"}],
        [{"ticker": "000660", "name": "SK하이닉스", "source": "interest"}],
    )
    apply_price_snapshot(
        result,
        {"000660": {"price": 1504000, "source": "read_only_market_provider", "as_of_date": "2026-08-12"}},
    )
    assert result["proposals"][0]["reference_prices"] == {"000660": 1504000}
    assert result["analyzed"][0]["matched_context"][0]["price_as_of"] == "2026-08-12"


def test_refresh_paper_fill_marks_updates_existing_records() -> None:
    records, updated = refresh_paper_fill_marks(
        [
            {
                "run_at": "2026-08-11T16:10:00+09:00",
                "paper_fills": [
                    {
                        "paper_order_id": "p1",
                        "symbol": "000660",
                        "status": "awaiting_price",
                    }
                ],
            }
        ],
        {"000660": {"price": 110, "source": "eod_price_snapshot"}},
        as_of_date="2026-08-12",
    )
    assert updated == 1
    assert records[0]["paper_fills"][0]["status"] == "simulated_filled"
    assert records[0]["paper_fills"][0]["reference_price"] == 110
    assert records[0]["paper_fills"][0]["mark_price"] == 110
    assert records[0]["paper_fills"][0]["mark_as_of"] == "2026-08-12"


def test_dedupe_paper_fill_history_keeps_newest_mark() -> None:
    records, removed = dedupe_paper_fill_history(
        [
            {"run_at": "2026-08-11", "paper_fills": [{"paper_order_id": "p1", "mark_price": 100}]},
            {"run_at": "2026-08-12", "paper_fills": [{"paper_order_id": "p1", "mark_price": 110}]},
        ]
    )
    assert removed == 1
    assert len(records[0]["paper_fills"]) == 0
    assert records[1]["paper_fills"][0]["mark_price"] == 110


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


def test_news_analysis_matches_korean_company_name_without_ticker() -> None:
    result = analyze_news_items(
        [
            {
                "id": "name-match",
                "title": "삼양식품 해외 매출 증가와 라면 수출 호조",
                "summary": "호실적 성장",
                "source_url": "https://example.com/name-match",
                "confidence": 0.8,
            }
        ],
        [{"ticker": "003230", "name": "삼양식품", "quantity": 18}],
    )
    assert result["matched_news_count"] == 1
    assert result["proposals"][0]["symbols"] == ["003230"]
    assert result["analyzed"][0]["matched_entities"][0]["matches"][0][0] == "company_name"


def test_news_analysis_matches_english_legal_name_alias() -> None:
    result = analyze_news_items(
        [{"id": "english-name", "title": "Planet Labs reports growth", "summary": "positive growth"}],
        [{"ticker": "PL", "name": "Planet Labs PBC", "quantity": 100}],
    )
    assert result["matched_news_count"] == 1
    assert result["proposals"][0]["action"] == "BUY_REVIEW"


def test_negative_interest_match_does_not_create_sell_proposal() -> None:
    result = analyze_news_items(
        [{"id": "interest-risk", "title": "SK하이닉스 규제 우려", "summary": "하향 악재"}],
        [{"ticker": "000660", "name": "SK하이닉스", "source": "interest", "source_types": ["interest"]}],
    )
    assert result["matched_news_count"] == 1
    assert result["proposals"] == []
    assert result["analyzed"][0]["action"] == "WATCH"


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


def test_evidence_review_combines_purchase_macro_pattern_and_strategy_metrics() -> None:
    strategy = {
        "status": "completed",
        "window_days": 7,
        "window_start": "2026-08-07",
        "as_of_date": "2026-08-13",
        "days_observed": 7,
        "sample_size": 14,
        "wins": 9,
        "losses": 5,
        "win_rate": 0.642857,
        "return_rate": 0.031,
        "max_drawdown": 1200,
        "evidence_strength": "medium",
        "message": "모의체결 평가",
    }
    evidence = build_evidence_review(
        owner_portfolio={
            "portfolio_name": "이형주",
            "holdings": [
                {
                    "ticker": "300080",
                    "name": "플리토",
                    "sync_source": "toss_holdings",
                    "latest_reports": [
                        {
                            "type": "earnings",
                            "file_name": "300080.md",
                            "relative_path": "300080/earnings.md",
                            "date": "2026-08-12",
                            "summary": "매출 성장 확인",
                            "impact_label": "긍정",
                            "impact_reason": "수익성 개선",
                        }
                    ],
                }
            ],
        },
        news_result={
            "proposals": [{"action": "BUY_REVIEW", "symbols": ["300080"]}],
            "analyzed": [],
        },
        orders=[],
        market_journal_entries=[
            {
                "entry_id": "kr-20260813",
                "market": "KR",
                "session_date": "2026-08-13",
                "regime": "risk_on",
                "sentiment": "positive",
                "risk_level": "medium",
                "portfolio_actions": ["추격 매수 금지"],
            }
        ],
        history=[
            {
                "run_at": "2026-08-12T16:10:00+09:00",
                "proposals": [{"action": "BUY_REVIEW", "symbols": ["300080"]}],
                "paper_fills": [
                    {
                        "symbol": "300080",
                        "side": "BUY",
                        "quantity": 1,
                        "reference_price": 8000,
                        "mark_price": 8500,
                        "simulated_at": "2026-08-12T16:10:00+09:00",
                    }
                ],
            }
        ],
        strategy_evaluation=strategy,
    )

    assert evidence["owner_portfolio_name"] == "이형주"
    assert evidence["purchase_rationale"]["status"] == "available"
    assert evidence["macro_evidence"]["by_market"][0]["regime"] == "risk_on"
    assert evidence["recurring_pattern"]["by_symbol"][0]["same_side_count"] == 2
    assert evidence["strategy_success"]["win_rate"] == 0.642857
    assert evidence["review_status"] == "evidence_complete"
    assert evidence["evidence_strength"] == "medium"


def test_evidence_review_exposes_missing_evidence_and_insufficient_strategy_sample() -> None:
    evidence = build_evidence_review(
        owner_portfolio={
            "portfolio_name": "이형주",
            "holdings": [{"ticker": "JOBY", "name": "Joby", "sync_source": "toss_holdings"}],
        },
        news_result={"proposals": [], "analyzed": []},
        orders=[],
        market_journal_entries=[],
        history=[],
        strategy_evaluation={
            "status": "insufficient_sample",
            "days_observed": 1,
            "sample_size": 14,
            "win_rate": 0.785714,
            "evidence_strength": "medium",
        },
    )

    assert evidence["purchase_rationale"]["status"] == "missing"
    assert evidence["macro_evidence"]["status"] == "missing"
    assert evidence["recurring_pattern"]["status"] == "first_observation"
    assert evidence["strategy_success"]["win_rate"] == 0.785714
    assert evidence["strategy_success"]["status"] == "insufficient_sample"
    assert evidence["review_status"] == "needs_evidence"
    assert evidence["evidence_strength"] == "low"


def test_workflow_result_carries_structured_evidence_without_enabling_live_orders() -> None:
    evidence = {"review_status": "needs_evidence", "evidence_strength": "low"}
    result = build_workflow_result(
        run_at="2026-08-13T16:10:00+09:00",
        news_result={"news_count": 0, "proposals": []},
        orders=[],
        evidence_review=evidence,
    )

    assert result["evidence_review"] == evidence
    assert result["review"]["evidence_review_status"] == "needs_evidence"
    assert result["stages"]["trade"]["status"] == "blocked_live_order"
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
