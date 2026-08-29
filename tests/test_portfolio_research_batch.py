from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.portfolio_research_batch import (  # noqa: E402
    build_portfolio_research_batch,
    build_portfolio_research_item,
    render_portfolio_research_batch_markdown,
    write_portfolio_research_batch,
)


def _record(*, ticker: str = "005930", company_name: str = "삼성전자") -> dict:
    return {
        "ticker": ticker,
        "official_symbol": ticker,
        "company_name": company_name,
        "portfolios": ["가족 합산"],
        "market_value": 1_000_000,
        "completion_rate": 1.0,
        "review_completion_rate": 0.5,
        "missing_modules": [],
        "review_missing_modules": ["체크리스트"],
        "checklist_status": {"completion_rate": 0.5, "review_ready": False},
    }


def _entry(report_type: str, *, report_date: str = "2026-08-20", summary: str = "검증된 저장 자료") -> dict:
    return {
        "ticker": "005930",
        "type": report_type,
        "file_name": f"005930-{report_type}-{report_date}.md",
        "date": report_date,
        "summary": summary,
        "tags": [report_type],
    }


def test_stock_research_item_combines_business_and_financial_evidence():
    item = build_portfolio_research_item(
        _record(),
        [
            _entry("dossier-synthesis"),
            _entry("earnings-reaction", report_date="2026-08-21"),
        ],
        as_of=date(2026, 8, 29),
    )

    assert item["instrument_kind"] == "company"
    assert item["research_status"] == "two_track_ready"
    assert item["tracks"]["business_industry"]["label"] == "사업·산업"
    assert item["tracks"]["financial_valuation"]["label"] == "실적·밸류에이션"
    assert item["evidence_strength"] >= 90
    assert item["safety"]["broker_order_endpoint_called"] is False


def test_fund_like_research_uses_exposure_and_structure_labels():
    item = build_portfolio_research_item(
        _record(ticker="360750", company_name="TIGER 미국S&P500 ETF"),
        [_entry("dossier-synthesis")],
        as_of=date(2026, 8, 29),
    )

    assert item["instrument_kind"] == "fund_like"
    assert item["tracks"]["business_industry"]["label"] == "기초지수·편입·산업 노출"
    assert item["tracks"]["financial_valuation"]["label"] == "추적 구조·보수·유동성"


def test_korean_etf_brands_without_literal_etf_suffix_use_fund_tracks():
    for ticker, company_name in (("396500", "TIGER 반도체TOP10"), ("117700", "KODEX 건설")):
        item = build_portfolio_research_item(
            _record(ticker=ticker, company_name=company_name),
            [_entry("dossier-synthesis")],
            as_of=date(2026, 8, 29),
        )

        assert item["instrument_kind"] == "fund_like"
        assert item["tracks"]["business_industry"]["label"] == "기초지수·편입·산업 노출"


def test_evidence_gap_is_prioritized_without_turning_into_order_instruction():
    item = build_portfolio_research_item(_record(), [], as_of=date(2026, 8, 29))

    assert item["research_status"] == "evidence_gap"
    assert item["review_priority"] == "high"
    assert item["safety"]["automated_order"] is False
    assert "매수" not in item["next_human_action"]
    assert "매도" not in item["next_human_action"]


def test_core_document_gap_is_high_priority_even_when_both_tracks_have_evidence():
    record = _record()
    record["missing_modules"] = ["기준 리포트", "매매 전략", "체크리스트"]
    item = build_portfolio_research_item(
        record,
        [_entry("dossier-synthesis"), _entry("earnings-reaction")],
        as_of=date(2026, 8, 29),
    )

    assert item["research_status"] == "two_track_ready"
    assert item["review_priority"] == "high"
    assert "표준 리서치 문서 공백" in item["review_priority_reason"]
    assert "자동으로 완료하지 않습니다" in item["next_human_action"]


def test_batch_sorts_evidence_gaps_before_ready_items():
    batch = build_portfolio_research_batch(
        [_record(ticker="005930", company_name="삼성전자"), _record(ticker="000660", company_name="SK하이닉스")],
        {
            "005930": [_entry("dossier-synthesis")],
            "000660": [],
        },
        as_of=date(2026, 8, 29),
    )

    assert batch["holding_count"] == 2
    assert batch["items"][0]["ticker"] == "000660"
    assert batch["safety"]["llm_called"] is False
    assert batch["safety"]["broker_order_endpoint_called"] is False


def test_markdown_and_json_batch_persist_to_local_directory(tmp_path: Path):
    batch = build_portfolio_research_batch(
        [_record()],
        {"005930": [_entry("dossier-synthesis"), _entry("earnings-reaction")]},
        as_of=date(2026, 8, 29),
    )

    markdown = render_portfolio_research_batch_markdown(batch)
    paths = write_portfolio_research_batch(batch, tmp_path)

    assert "자동 주문 없음" in markdown
    assert paths["markdown"].exists()
    assert json.loads(paths["json"].read_text(encoding="utf-8"))["holding_count"] == 1
