from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.insider_trading import (
    InsiderAnalysisRequest,
    InsiderBatchRequest,
    InsiderTransaction,
    PriceBar,
    _save_report,
    build_flow_history,
    build_historical_reactions,
    build_insider_report,
    build_price_context,
    build_signal_strength,
    classify_source_url,
    parse_dart_elestock_payload,
    parse_insider_summary_text,
    parse_sec_form4_xml,
    render_insider_report_markdown,
    run_insider_trading_batch,
)
from research_os.settings import Settings


SEC_FORM4_XML = """<?xml version="1.0"?>
<ownershipDocument>
  <issuer>
    <issuerCik>0001341766</issuerCik>
    <issuerName>Celsius Holdings, Inc.</issuerName>
    <issuerTradingSymbol>CELH</issuerTradingSymbol>
  </issuer>
  <reportingOwner>
    <reportingOwnerId><rptOwnerName>Jane Researcher</rptOwnerName></reportingOwnerId>
    <reportingOwnerRelationship>
      <isDirector>0</isDirector><isOfficer>1</isOfficer><officerTitle>CFO</officerTitle>
    </reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <securityTitle><value>Common Stock</value></securityTitle>
      <transactionDate><value>2026-09-11</value></transactionDate>
      <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
      <transactionAmounts>
        <transactionShares><value>5000</value></transactionShares>
        <transactionPricePerShare><value>42.5</value></transactionPricePerShare>
        <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
      </transactionAmounts>
      <postTransactionAmounts><sharesOwnedFollowingTransaction><value>120000</value></sharesOwnedFollowingTransaction></postTransactionAmounts>
      <ownershipNature><directOrIndirectOwnership><value>D</value></directOrIndirectOwnership></ownershipNature>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
  <footnotes><footnote id="F1">Open-market purchase. Not pursuant to a Rule 10b5-1 plan.</footnote></footnotes>
</ownershipDocument>
"""


def _bars(start: date, count: int = 100, start_price: float = 20.0) -> list[PriceBar]:
    rows = []
    for index in range(count):
        price = start_price + index * 0.25 + (2.0 if index % 13 == 0 else 0.0)
        rows.append(
            PriceBar(
                date=start + timedelta(days=index),
                open=price - 0.2,
                high=price + 0.6,
                low=price - 0.6,
                close=price,
            )
        )
    return rows


def test_parse_sec_form4_preserves_official_fields() -> None:
    events = parse_sec_form4_xml(
        SEC_FORM4_XML,
        source_url="https://www.sec.gov/Archives/edgar/data/1341766/test.xml",
        filing_date=date(2026, 9, 12),
        accession_number="0000000000-26-000001",
    )
    assert len(events) == 1
    event = events[0]
    assert event.ticker == "CELH"
    assert event.insider_name == "Jane Researcher"
    assert event.title == "CFO"
    assert event.relationship == "임원"
    assert event.tx_code == "P"
    assert event.shares == 5000
    assert event.avg_price == 42.5
    assert event.transaction_value == 212500
    assert event.post_shares == 120000
    assert event.is_10b5_1 is False


def test_parse_dart_keeps_unreported_price_missing() -> None:
    events = parse_dart_elestock_payload(
        {
            "status": "000",
            "list": [
                {
                    "rcept_no": "20260912000001",
                    "rcept_dt": "20260912",
                    "corp_name": "테스트전자",
                    "repror": "홍길동",
                    "isu_exctv_ofcps": "대표이사",
                    "isu_exctv_rgist_at": "등기",
                    "isu_main_shrholdr": "-",
                    "sp_stock_lmp_cnt": "120,000",
                    "sp_stock_lmp_irds_cnt": "5,000",
                }
            ],
        },
        ticker="005930",
        corp={"corp_code": "00126380", "corp_name": "테스트전자"},
    )
    assert len(events) == 1
    event = events[0]
    assert event.tx_code == "ACQUIRE"
    assert event.shares == 5000
    assert event.post_shares == 120000
    assert event.avg_price is None
    assert event.transaction_value is None
    assert "거래단가" in event.notes[0]


def test_parse_korean_summary_example() -> None:
    event = parse_insider_summary_text(
        "$TSLA 내부자 매수 공시: CFO, 2026-09-11, 5,000 주, $210, 거래 후 보유 120,000 주"
    )
    assert event is not None
    assert event.ticker == "TSLA"
    assert event.title == "CFO"
    assert event.tx_code == "P"
    assert event.shares == 5000
    assert event.avg_price == 210
    assert event.post_shares == 120000


@pytest.mark.parametrize(
    "url,tier",
    [
        ("https://www.sec.gov/Archives/edgar/data/1/form4.xml", "primary"),
        ("https://opendart.fss.or.kr/api/elestock.json", "primary"),
        ("https://www.secform4.com/insider-trading/XXXX.htm", "secondary"),
    ],
)
def test_source_url_allowlist(url: str, tier: str) -> None:
    assert classify_source_url(url)["source_tier"] == tier


@pytest.mark.parametrize(
    "url",
    [
        "http://www.sec.gov/test.xml",
        "https://127.0.0.1/form4.xml",
        "https://192.168.0.10/form4.xml",
        "https://example.com/form4.xml",
        "https://user:password@www.sec.gov/test.xml",
    ],
)
def test_source_url_rejects_unsafe_or_unknown_hosts(url: str) -> None:
    with pytest.raises(ValueError):
        classify_source_url(url)


def test_price_context_calculates_range_volatility_and_event_move() -> None:
    bars = _bars(date(2026, 5, 1), count=120)
    context = build_price_context(bars, date(2026, 8, 1))
    assert context["status"] == "available"
    assert context["bar_count"] == 120
    assert 0 <= context["week52_percentile"] <= 100
    assert context["event_day_change_pct"] is not None
    assert context["volatility"]["one_month_avg_abs_daily_pct"] > 0
    assert len(context["representative_moves"]) == 3


def test_flow_windows_keep_partial_coverage_visible() -> None:
    current = date(2026, 9, 12)
    events = [
        InsiderTransaction(ticker="CELH", market="US", tx_date=current - timedelta(days=20), tx_code="P", shares=100, avg_price=20, transaction_value=2000, source_type="sec_form4"),
        InsiderTransaction(ticker="CELH", market="US", tx_date=current - timedelta(days=200), tx_code="S", shares=40, avg_price=30, transaction_value=1200, source_type="sec_form4"),
        InsiderTransaction(ticker="CELH", market="US", tx_date=current - timedelta(days=500), tx_code="P", shares=10, avg_price=None, source_type="sec_form4"),
    ]
    history = build_flow_history(events, as_of=current, coverage_complete=False)
    assert history["windows"]["6m"]["net_shares"] == 100
    assert history["windows"]["12m"]["net_shares"] == 60
    assert history["windows"]["24m"]["net_shares"] == 70
    assert history["windows"]["24m"]["coverage_complete"] is False
    assert "확인 필요" in history["windows"]["24m"]["coverage_note"]


def test_signal_rewards_discretionary_large_low_zone_purchase() -> None:
    event = InsiderTransaction(
        ticker="CELH",
        market="US",
        tx_date=date(2026, 9, 11),
        tx_code="P",
        shares=50_000,
        avg_price=25,
        transaction_value=1_250_000,
        post_shares=200_000,
        is_10b5_1=False,
        source_type="sec_form4",
    )
    signal = build_signal_strength(
        event,
        {
            "week52_percentile": 18.0,
            "volatility": {"three_month_avg_abs_daily_pct": 3.1},
        },
    )
    assert signal["direction"] == "긍정"
    assert signal["strength"] == "강함"
    assert any(item["rule"] == "discretionary_buy_combo" for item in signal["contributions"])
    assert "백테스트된 매매 확률이 아닙니다" in signal["calibration_note"]


def test_historical_reaction_uses_one_and_three_month_trading_windows() -> None:
    bars = _bars(date(2026, 1, 1), count=250)
    current = InsiderTransaction(ticker="CELH", market="US", tx_date=date(2026, 8, 20), tx_code="P", shares=100, source_type="sec_form4")
    previous = InsiderTransaction(ticker="CELH", market="US", tx_date=date(2026, 2, 1), filing_date=date(2026, 2, 2), tx_code="P", shares=100, source_type="sec_form4")
    result = build_historical_reactions([current, previous], bars, current)
    assert result["summary"]["sample_size"] == 1
    assert result["cases"][0]["one_month"]["return_pct"] is not None
    assert result["cases"][0]["three_month"]["return_pct"] is not None


def test_six_axis_report_and_storage_contract(tmp_path: Path) -> None:
    settings = Settings(research_vault_dir=str(tmp_path / "research_vault"))
    event = parse_sec_form4_xml(
        SEC_FORM4_XML,
        source_url="https://www.sec.gov/Archives/edgar/data/1341766/test.xml",
        filing_date=date(2026, 9, 12),
    )[0]
    report = build_insider_report(
        event=event,
        events=[event],
        price_rows=_bars(date(2026, 5, 1), count=140),
        source_status={"provider": "SEC EDGAR", "coverage_complete": True},
        checkpoints={
            "valuation_band": "공식 수치 확인 필요",
            "fundamental_catalysts": ["다음 분기 실적"],
            "linked_research": [],
            "risk_management": ["변동성 점검"],
        },
    )
    assert list(report["axes"]) == [
        "transaction_context",
        "price_and_volatility",
        "insider_flow_history",
        "signal_strength",
        "historical_pattern",
        "investment_checkpoints",
    ]
    markdown = render_insider_report_markdown(report)
    for heading in (
        "## 1. 거래 맥락",
        "## 2. 가격·변동성 위치",
        "## 3. 내부자 수급 히스토리",
        "## 4. 신호 강도 평가",
        "## 5. 역사적 패턴",
        "## 6. 투자 체크포인트",
    ):
        assert heading in markdown
    saved = _save_report(report, settings)
    assert Path(saved["storage"]["absolute_path"]).exists()
    assert Path(saved["storage"]["json_absolute_path"]).exists()
    assert saved["rag_document"]["document_id"]


def test_manual_summary_report_does_not_claim_official_source() -> None:
    event = parse_insider_summary_text(
        "$TSLA 내부자 매수 공시: CFO, 2026-09-11, 5,000주, $210, 거래 후 보유 120,000주",
        ticker_hint="TSLA",
    )
    report = build_insider_report(
        event=event,
        events=[event],
        price_rows=[],
        source_status={"provider": "manual", "coverage_complete": False},
        checkpoints={
            "valuation_band": "확인 필요",
            "fundamental_catalysts": [],
            "linked_research": [],
            "risk_management": [],
        },
    )
    assert "사용자 입력 요약 기준" in report["summary"]
    assert "공식 공시 우선" not in report["summary"]
    assert "텍스트 요약에서 추출" in report["axes"]["transaction_context"]["transaction_code_note"]
    assert report["safety"] == {"orders": False, "messages": False, "account_changes": False}


def test_batch_request_rejects_unbounded_work() -> None:
    with pytest.raises(ValueError):
        InsiderBatchRequest(max_tickers=101)
    with pytest.raises(ValueError):
        InsiderBatchRequest(max_filings=0)


def test_batch_skips_non_ticker_portfolio_labels(tmp_path: Path) -> None:
    settings = Settings(research_vault_dir=str(tmp_path / "research_vault"))
    result = run_insider_trading_batch(
        settings,
        tickers=["BAD TICKER"],
        max_tickers=1,
        save_result=False,
    )
    assert result["last_run"]["selected_count"] == 0
    assert result["last_run"]["counts"]["not_applicable"] == 1
    assert result["skipped_candidates"][0]["ticker"] == "BAD TICKER"


def test_console_and_daily_automation_contracts() -> None:
    root = Path(__file__).resolve().parents[1]
    html = (root / "mobile_app" / "research_console" / "index.html").read_text(encoding="utf-8")
    api = (root / "mobile_app" / "research_console" / "api.js").read_text(encoding="utf-8")
    console = (root / "mobile_app" / "research_console" / "console.js").read_text(encoding="utf-8")
    daily = (root / "tools" / "run_daily_research_operations.ps1").read_text(encoding="utf-8")
    main = (root / "backend" / "research_os_main.py").read_text(encoding="utf-8")
    assert 'data-tab="insider"' in html
    assert 'id="insiderForm"' in html
    assert "fetchInsiderTradingStatus" in api
    assert "renderInsiderTradingReport" in console
    assert '"/api/v1/insider-trading/analyze"' in main
    assert "SkipInsiderTradingResearch" in daily
    assert "run_insider_trading_research.py" in daily
    assert "never sends a message" in daily
