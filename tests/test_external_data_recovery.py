from __future__ import annotations

from io import BytesIO
from pathlib import Path
import sys
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _xlsx_fixture() -> bytes:
    shared = ["No", "발행기관", "발행기관명", "보고서\n작성기준일", "지분율", "1", "017670", "SK텔레콤(주)", "8.46"]
    shared_xml = "".join(f"<si><t>{value}</t></si>" for value in shared)
    sheet_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>
      <row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c><c r="C1" t="s"><v>2</v></c><c r="D1" t="s"><v>3</v></c><c r="E1" t="s"><v>4</v></c></row>
      <row r="2"><c r="A2" t="s"><v>5</v></c><c r="B2" t="s"><v>6</v></c><c r="C2" t="s"><v>7</v></c><c r="D2"><v>46230</v></c><c r="E2" t="s"><v>8</v></c></row>
    </sheetData></worksheet>"""
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("xl/sharedStrings.xml", f"<?xml version='1.0' encoding='UTF-8'?><sst xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'>{shared_xml}</sst>")
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buffer.getvalue()


def test_nps_official_xlsx_parser_normalizes_headers_and_excel_date() -> None:
    from research_os.nps_official_disclosure import parse_nps_large_holding_xlsx

    rows = parse_nps_large_holding_xlsx(_xlsx_fixture())

    assert rows == [
        {
            "번호": "1",
            "종목코드": "017670",
            "발행기관명": "SK텔레콤(주)",
            "보고서 작성기준일": "2026-07-27",
            "지분율(퍼센트)": "8.46",
        }
    ]


def test_sec_index_resolver_selects_official_exhibit_99_1() -> None:
    from research_os.public_ir_sec import find_sec_exhibit_99_1_url

    index_url = "https://www.sec.gov/Archives/edgar/data/1/000000000126000001/0000000001-26-000001-index.html"
    response = httpx.Response(
        200,
        request=httpx.Request("GET", index_url),
        text='<table><tr><td>EX-99.1</td><td><a href="press-release.htm">Document</a></td></tr></table>',
    )
    with patch("research_os.public_ir_sec.fetch_url_with_retry", return_value=(response, ["test"])):
        result = find_sec_exhibit_99_1_url(index_url)

    assert result["status"] == "success"
    assert result["exhibit_url"] == "https://www.sec.gov/Archives/edgar/data/1/000000000126000001/press-release.htm"


def test_naver_close_report_requires_both_indices_closed() -> None:
    from research_os.naver_index_close import fetch_naver_korea_index_close_report
    from research_os.settings import Settings

    payloads = {
        "KOSPI": {"stockName": "KOSPI", "closePrice": "6,625.93", "compareToPreviousClosePrice": "-177.97", "fluctuationsRatio": "-2.62", "compareToPreviousPrice": {"text": "하락"}, "marketStatus": "CLOSE", "localTradedAt": "2026-10-08 오후 08:15:00"},
        "KOSDAQ": {"stockName": "KOSDAQ", "closePrice": "892.27", "compareToPreviousClosePrice": "-6.16", "fluctuationsRatio": "-0.69", "compareToPreviousPrice": {"text": "하락"}, "marketStatus": "CLOSE", "localTradedAt": "2026-10-08 오후 08:15:00"},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        code = request.url.path.split("/")[-2]
        return httpx.Response(200, request=request, json=payloads[code])

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    with patch("research_os.naver_index_close.httpx.Client", side_effect=client_factory):
        report = fetch_naver_korea_index_close_report(Settings())

    assert report is not None
    assert report["published_at"] == "2026-10-08"
    assert report["source_analysis"]["status"] == "verified_close"
    assert len(report["indices"]) == 2
