from __future__ import annotations

from datetime import date
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _record(
    ticker: str,
    *,
    score: int,
    blocked: bool = False,
    company_name: str | None = None,
) -> dict:
    return {
        "ticker": ticker,
        "company_name": company_name or ticker,
        "market": "US",
        "market_label": "미국",
        "currency": "USD",
        "recommendation_date": date.today().isoformat(),
        "generated_at": "2026-09-01T08:00:00+09:00",
        "rank": 1,
        "score": score,
        "baseline_price": 12.34,
        "baseline_price_checked_at": "2026-09-01",
        "reasons": ["저장된 실적 근거가 우선 검토 기준을 충족했습니다."],
        "risk_notes": ["실적 발표 전 원문과 가격 조건을 사람이 다시 확인해야 합니다."],
        "evidence_sources": ["공시 원문", "리서치 노트"],
        "evidence_documents": [{"id": f"evidence-{ticker}"}],
        "tracking_milestones": [
            {"key": "earnings", "label": "다음 실적 확인", "target_date": "2026-10-15", "status": "pending"}
        ],
        "evidence_quality_summary": {
            "grade": "B",
            "score": 82,
            "label": "근거 보통",
            "summary": "최근 근거 문서와 추적 일정이 저장되었습니다.",
            "guardrail_label": "사람 검토 후 판단",
            "guardrail_action": "원문·가격·리스크를 재확인",
            "document_count": 2,
            "recent_30d_count": 1,
            "blocks_buy_decision": blocked,
        },
    }


def _write_scope(settings) -> None:
    from research_os.state_store import interest_list_path, portfolio_store_path, write_json_store

    write_json_store(
        portfolio_store_path(settings),
        {
            "portfolios": {
                "family-a": {
                    "portfolio_name": "가족 A",
                    "holdings": [{"ticker": "HELD", "name": "Held Company", "currency": "USD"}],
                }
            }
        },
    )
    write_json_store(
        interest_list_path(settings),
        {"tickers": [{"ticker": "WATCH"}], "sectors": []},
    )


def test_top_pick_selects_only_eligible_family_scope_and_writes_svg(tmp_path) -> None:
    from research_os.daily_family_top_pick import (
        build_daily_family_top_pick_card,
        read_daily_family_top_pick_card,
        read_daily_family_top_pick_svg,
        run_daily_family_top_pick_card,
    )
    from research_os.daily_recommendation_store import daily_recommendation_store_path, write_json_payload
    from research_os.settings import Settings

    settings = Settings(research_vault_dir=str(tmp_path / "research_vault"))
    _write_scope(settings)
    write_json_payload(
        daily_recommendation_store_path(settings),
        {
            "latest_recommendation_date": date.today().isoformat(),
            "records": [
                _record("HELD", score=170, company_name="Alpha & <Science>"),
                _record("WATCH", score=210, blocked=True),
                _record("OUTSIDE", score=300),
            ],
        },
    )

    preview = build_daily_family_top_pick_card(settings)
    assert preview["status"] == "ready"
    assert preview["selection"]["selected_ticker"] == "HELD"
    assert preview["selection"]["eligible_count"] == 1
    assert preview["selection"]["excluded_review_hold_count"] == 1
    assert preview["selection"]["excluded_out_of_scope_count"] == 1
    assert preview["card"]["scope_status"] == "가족 보유 종목"
    assert preview["card"]["disclaimer"].startswith("투자 리서치용")
    assert "holding_tickers" not in preview["scope"]
    assert "interest_tickers" not in preview["scope"]

    saved = run_daily_family_top_pick_card(settings, force=True)
    svg, filename = read_daily_family_top_pick_svg(settings)
    assert saved["generation_status"] == "generated"
    assert filename == f"family-top-pick-{date.today().isoformat()}.svg"
    assert svg is not None
    assert "Alpha &amp; &lt;Science&gt;" in svg
    assert "storage_path" not in saved["asset"]
    assert read_daily_family_top_pick_card(settings)["selection"]["selected_ticker"] == "HELD"


def test_top_pick_fails_closed_to_review_hold_when_every_scoped_candidate_is_blocked(tmp_path) -> None:
    from research_os.daily_family_top_pick import build_daily_family_top_pick_card
    from research_os.daily_recommendation_store import daily_recommendation_store_path, write_json_payload
    from research_os.settings import Settings

    settings = Settings(research_vault_dir=str(tmp_path / "research_vault"))
    _write_scope(settings)
    write_json_payload(
        daily_recommendation_store_path(settings),
        {
            "latest_recommendation_date": date.today().isoformat(),
            "records": [_record("WATCH", score=210, blocked=True)],
        },
    )

    payload = build_daily_family_top_pick_card(settings)
    assert payload["status"] == "review_hold"
    assert payload["selection"]["selected_ticker"] == "WATCH"
    assert payload["card"]["research_stance"] == "근거 보강 전 검토 보류"


def test_console_and_daily_runner_contract_keep_the_card_local_and_non_ordering() -> None:
    backend_source = (PROJECT_ROOT / "backend" / "research_os_main.py").read_text(encoding="utf-8")
    api_source = (PROJECT_ROOT / "mobile_app" / "research_console" / "api.js").read_text(encoding="utf-8")
    console_source = (PROJECT_ROOT / "mobile_app" / "research_console" / "console.js").read_text(encoding="utf-8")
    card_source = (PROJECT_ROOT / "backend" / "research_os" / "daily_family_top_pick.py").read_text(encoding="utf-8")

    assert "run_daily_family_top_pick_card(settings" in backend_source
    assert '"/api/v1/daily-top-pick"' in api_source
    assert '"/api/v1/daily-top-pick/card.svg"' in api_source
    assert "dailyTopPickQuickButton" in console_source
    assert "매수·매도 지시나 자동 주문이 아닙니다" in card_source
    assert "submit_order" not in card_source
