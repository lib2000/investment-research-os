"""Official NPS quarterly large-holding disclosure downloader and XLSX parser."""

from __future__ import annotations

from datetime import datetime, timedelta
from io import BytesIO
import re
from urllib.parse import urlencode, urljoin
from zipfile import ZipFile
from xml.etree import ElementTree as ET

import httpx


_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _column_index(reference: str) -> int:
    letters = "".join(ch for ch in reference if ch.isalpha()).upper()
    value = 0
    for ch in letters:
        value = value * 26 + ord(ch) - 64
    return max(value - 1, 0)


def _shared_strings(archive: ZipFile) -> list[str]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return ["".join(node.text or "" for node in item.findall(".//m:t", _NS)) for item in root.findall("m:si", _NS)]


def parse_nps_large_holding_xlsx(content: bytes) -> list[dict]:
    """Parse the small official workbook without adding an Excel dependency."""
    with ZipFile(BytesIO(content)) as archive:
        shared = _shared_strings(archive)
        sheet_names = sorted(name for name in archive.namelist() if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"))
        if not sheet_names:
            return []
        root = ET.fromstring(archive.read(sheet_names[0]))
    rows: list[list[str]] = []
    for row_node in root.findall(".//m:sheetData/m:row", _NS):
        cells: dict[int, str] = {}
        for cell in row_node.findall("m:c", _NS):
            index = _column_index(cell.attrib.get("r", "A1"))
            cell_type = cell.attrib.get("t", "")
            value_node = cell.find("m:v", _NS)
            if cell_type == "inlineStr":
                value = "".join(node.text or "" for node in cell.findall(".//m:t", _NS))
            else:
                value = value_node.text if value_node is not None and value_node.text is not None else ""
                if cell_type == "s" and value.isdigit() and int(value) < len(shared):
                    value = shared[int(value)]
            cells[index] = value.strip()
        if cells:
            width = max(cells) + 1
            rows.append([cells.get(index, "") for index in range(width)])
    normalized_rows = [[re.sub(r"\s+", "", value) for value in row] for row in rows]
    header_index = next(
        (
            i
            for i, row in enumerate(normalized_rows)
            if ("종목코드" in row or "발행기관" in row) and "발행기관명" in row
        ),
        None,
    )
    if header_index is None:
        return []
    header_aliases = {
        "발행기관": "종목코드",
        "종목코드": "종목코드",
        "발행기관명": "발행기관명",
        "보고서작성기준일": "보고서 작성기준일",
        "지분율": "지분율(퍼센트)",
        "No": "번호",
    }
    headers = [header_aliases.get(value, value) for value in normalized_rows[header_index]]
    parsed: list[dict] = []
    for row in rows[header_index + 1 :]:
        values = row + [""] * max(0, len(headers) - len(row))
        item = {str(header).strip(): values[index].strip() for index, header in enumerate(headers) if str(header).strip()}
        code = str(item.get("종목코드") or "").strip()
        issuer = str(item.get("발행기관명") or "").strip()
        if not code or not issuer:
            continue
        raw_date = str(item.get("보고서 작성기준일") or "").strip()
        if re.fullmatch(r"\d+(?:\.\d+)?", raw_date):
            serial = float(raw_date)
            if 30000 <= serial <= 80000:
                item["보고서 작성기준일"] = (datetime(1899, 12, 30) + timedelta(days=serial)).date().isoformat()
        parsed.append(item)
    return parsed


def fetch_nps_large_holding_disclosure(page_url: str, timeout_seconds: float = 8.0) -> tuple[list[dict], list[str], str | None]:
    if not page_url:
        return [], ["국민연금 공식 대량보유 공시 페이지가 설정되지 않았습니다."], None
    headers = {
        "User-Agent": "Mozilla/5.0 InvestmentResearchOS/1.0",
        "Accept": "text/html,application/xhtml+xml,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,*/*",
    }
    try:
        with httpx.Client(timeout=timeout_seconds, headers=headers, trust_env=False, follow_redirects=True) as client:
            page = client.get(page_url)
            page.raise_for_status()
            match = re.search(r"fncAtchFileDownload\(['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]\)", page.text)
            if not match:
                return [], ["국민연금 공식 공시에서 XLSX 첨부 링크를 찾지 못했습니다."], page_url
            download_url = urljoin(page_url, "/fileDown.do") + "?" + urlencode(
                {"atchFileId": match.group(1), "atchFileSn": match.group(2)}
            )
            workbook = client.get(download_url)
            workbook.raise_for_status()
        rows = parse_nps_large_holding_xlsx(workbook.content)
        if not rows:
            return [], ["국민연금 공식 XLSX에서 대량보유 행을 읽지 못했습니다."], page_url
        for row in rows:
            row["_source_url"] = page_url
            row["_download_url"] = download_url
            row["_source_type"] = "nps_official_quarterly_large_holding"
        return rows, [], page_url
    except Exception as exc:
        return [], [f"국민연금 공식 대량보유 공시 수집 실패: {type(exc).__name__}: {exc}"], page_url
