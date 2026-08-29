from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from research_os.company_ir_sources import (  # noqa: E402
    COMPANY_IR_SOURCES,
    CompanyIrSource,
    fetch_krx_etf_product_source,
    krx_etf_product_summary_url,
)
from research_os.public_ir_sec import _is_official_portfolio_source_entry  # noqa: E402


class _Response:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


class _KrxClient:
    def __init__(self, landing: str, detail: str) -> None:
        self.landing = landing
        self.detail = detail
        self.urls: list[str] = []

    def get(self, url: str) -> _Response:
        self.urls.append(url)
        return _Response(self.landing if len(self.urls) == 1 else self.detail)


def test_default_sources_cover_remaining_us_and_krx_etf_targets() -> None:
    source_by_key = {source.source_key: source for source in COMPANY_IR_SOURCES}

    assert source_by_key["gaotu_sec_submissions"].source_url.endswith("CIK0001768259.json")
    assert source_by_key["ocean_power_sec_submissions"].source_url.endswith("CIK0001378140.json")
    assert source_by_key["krx_tiger_us_sp500_product"].source_url == krx_etf_product_summary_url("360750")
    assert source_by_key["krx_tiger_korea_ai_power_product"].source_url == krx_etf_product_summary_url("0117V0")
    assert source_by_key["krx_kodex_construction_product"].source_scope == "krx_etf_product"


def test_krx_etf_source_uses_detail_get_and_checks_returned_ticker() -> None:
    source = CompanyIrSource(
        source_key="krx_test",
        ticker="360750",
        company_name="TIGER 미국S&P500 ETF",
        provider="KRX KIND",
        source_url=krx_etf_product_summary_url("360750"),
        source_scope="krx_etf_product",
    )
    landing = '''<input type="hidden" name="isuCd" value="KR7360750004" />
    <input type="hidden" name="isSynthEtf" value="N" />'''
    detail = '''<table><tr><th>종목코드</th><td>360750</td><th>기초지수명</th><td>S&amp;P 500</td></tr></table>'''
    client = _KrxClient(landing, detail)

    result = fetch_krx_etf_product_source(source, client=client)

    assert result["status"] == "success"
    item = result["items"][0]
    assert item["ticker"] == "360750"
    assert item["source_scope"] == "krx_etf_product"
    assert item["published_at"] == date.today().isoformat()
    assert item["detail_url"].startswith("https://kind.krx.co.kr/disclosure/etfisudetail.do?method=searchEftIsuDetail")
    assert "S&P 500" in item["title"]


def test_krx_etf_source_rejects_mismatched_product_code() -> None:
    source = CompanyIrSource(
        source_key="krx_test",
        ticker="360750",
        company_name="TIGER 미국S&P500 ETF",
        provider="KRX KIND",
        source_url=krx_etf_product_summary_url("360750"),
        source_scope="krx_etf_product",
    )
    landing = '<input type="hidden" name="isuCd" value="KR7360750004" />'
    detail = '<table><tr><th>종목코드</th><td>395160</td></tr></table>'

    with pytest.raises(RuntimeError, match="상품코드 불일치"):
        fetch_krx_etf_product_source(source, client=_KrxClient(landing, detail))


def test_only_exact_krx_kind_product_entries_are_auto_bound_to_portfolio_ticker() -> None:
    trusted = {
        "source_type": "krx_etf_product",
        "source_url": "https://kind.krx.co.kr/disclosure/etfisudetail.do?method=searchEftIsuDetail",
    }
    untrusted = {
        "source_type": "krx_etf_product",
        "source_url": "https://kind.krx.co.kr.evil.invalid/disclosure/etfisudetail.do",
    }

    assert _is_official_portfolio_source_entry(trusted) is True
    assert _is_official_portfolio_source_entry(untrusted) is False
