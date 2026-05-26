"""Portfolio file import parsing helpers."""

from __future__ import annotations

import csv
import io
import json
import zipfile
from re import fullmatch, sub
from xml.etree import ElementTree

from research_os.models import PortfolioHolding


PORTFOLIO_IMPORT_HEADERS = {
    "ticker": {"ticker", "symbol", "종목", "종목코드", "티커", "코드"},
    "name": {"name", "company", "company_name", "종목명", "회사명", "이름"},
    "quantity": {"quantity", "qty", "shares", "수량", "보유수량", "주식수"},
    "average_cost": {"average_cost", "avg_cost", "avg price", "평단", "평균단가", "매입가"},
    "current_price": {"current_price", "price", "last", "현재가", "가격"},
    "market_value": {"market_value", "value", "amount", "평가금액", "평가액", "금액"},
    "weight": {"weight", "비중", "비율"},
    "sector": {"sector", "섹터", "업종"},
    "theme_tags": {"theme_tags", "tags", "tag", "테마", "태그"},
}


def normalize_import_ticker(ticker: str) -> str:
    normalized = sub(r"[^A-Za-z0-9._-]+", "-", str(ticker or "").strip().upper()).strip("-")
    return normalized or "UNKNOWN"


def is_domestic_sync_like_ticker(ticker: str) -> bool:
    normalized = normalize_import_ticker(ticker)
    if normalized in {"", "UNKNOWN", "CASH"}:
        return False
    return bool(fullmatch(r"[0-9A-Z]{6}", normalized)) and any(ch.isdigit() for ch in normalized)


def portfolio_currency_for_ticker(ticker: str, preferred_currency: object | None = None) -> str:
    normalized = normalize_import_ticker(ticker)
    preferred = str(preferred_currency or "").strip().upper()
    if normalized == "CASH":
        return "KRW"
    if fullmatch(r"\d{6}", normalized):
        return "KRW"
    if preferred in {"KRW", "USD"}:
        return preferred
    return "KRW" if is_domestic_sync_like_ticker(normalized) else "USD"


def normalize_import_header(value: str) -> str:
    cleaned = sub(r"[\s_\-()/%]+", "", str(value or "").strip().lower())
    for target, aliases in PORTFOLIO_IMPORT_HEADERS.items():
        if cleaned in {sub(r"[\s_\-()/%]+", "", alias.lower()) for alias in aliases}:
            return target
    return cleaned


def parse_import_number(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    is_percent = "%" in text
    cleaned = sub(r"[^0-9.\-]+", "", text)
    if cleaned in {"", "-", "."}:
        return None
    try:
        number = float(cleaned)
    except ValueError:
        return None
    if is_percent:
        return number / 100
    return number


def portfolio_holding_from_row(row: dict[str, object]) -> PortfolioHolding | None:
    normalized = {normalize_import_header(key): value for key, value in row.items()}
    ticker = normalize_import_ticker(str(normalized.get("ticker") or normalized.get("symbol") or ""))
    if not ticker or ticker == "UNKNOWN":
        return None
    quantity = parse_import_number(normalized.get("quantity"))
    current_price = parse_import_number(normalized.get("current_price"))
    market_value = parse_import_number(normalized.get("market_value"))
    if market_value is None and quantity is not None and current_price is not None:
        market_value = quantity * current_price
    if ticker == "CASH" and market_value is None:
        market_value = current_price or parse_import_number(normalized.get("average_cost"))
    tags = [
        tag.strip()
        for tag in str(normalized.get("theme_tags") or "").replace(";", ",").split(",")
        if tag.strip()
    ]
    return PortfolioHolding(
        ticker=ticker,
        name=str(normalized.get("name") or "").strip() or None,
        quantity=quantity,
        average_cost=parse_import_number(normalized.get("average_cost")),
        current_price=current_price,
        market_value=market_value,
        weight=parse_import_number(normalized.get("weight")),
        sector=str(normalized.get("sector") or "Unknown").strip() or "Unknown",
        theme_tags=tags,
        currency=portfolio_currency_for_ticker(ticker),
    )


def parse_portfolio_delimited_text(text: str) -> tuple[list[PortfolioHolding], int, list[str]]:
    warnings: list[str] = []
    rows = [line for line in text.splitlines() if line.strip()]
    if not rows:
        return [], 0, ["파일에서 읽을 수 있는 행이 없습니다."]
    sample = "\n".join(rows[:8])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        reader = csv.DictReader(io.StringIO("\n".join(rows)), dialect=dialect)
    except csv.Error:
        delimiter = "\t" if "\t" in sample else ","
        reader = csv.DictReader(io.StringIO("\n".join(rows)), delimiter=delimiter)
    holdings = [holding for record in reader if (holding := portfolio_holding_from_row(record))]
    if not holdings:
        warnings.append("헤더 기반 표를 찾지 못했습니다. 첫 행에 티커, 수량, 현재가, 평가금액 같은 열 이름을 넣어주세요.")
    return holdings, max(0, len(rows) - 1), warnings


def parse_portfolio_json_text(text: str) -> tuple[list[PortfolioHolding], int, list[str]]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return [], 0, ["JSON 파일 형식을 읽지 못했습니다."]
    records = payload.get("holdings") if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        return [], 0, ["JSON은 보유 종목 배열이거나 holdings 배열을 포함해야 합니다."]
    holdings = [
        holding
        for record in records
        if isinstance(record, dict) and (holding := portfolio_holding_from_row(record))
    ]
    warnings = [] if holdings else ["JSON에서 보유 종목을 인식하지 못했습니다."]
    return holdings, len(records), warnings


def parse_xlsx_shared_strings(zip_file: zipfile.ZipFile) -> list[str]:
    try:
        xml_bytes = zip_file.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ElementTree.fromstring(xml_bytes)
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    values = []
    for item in root.findall("x:si", namespace):
        texts = [node.text or "" for node in item.findall(".//x:t", namespace)]
        values.append("".join(texts))
    return values


def xlsx_cell_value(cell: ElementTree.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    value_node = cell.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
    if value_node is None or value_node.text is None:
        inline = cell.find(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
        return inline.text if inline is not None and inline.text else ""
    value = value_node.text
    if cell_type == "s":
        try:
            return shared_strings[int(value)]
        except (ValueError, IndexError):
            return ""
    return value


def xlsx_column_index(cell_ref: str) -> int:
    letters = "".join(char for char in cell_ref.upper() if char.isalpha())
    index = 0
    for char in letters:
        index = index * 26 + (ord(char) - ord("A") + 1)
    return max(index - 1, 0)


def parse_portfolio_xlsx(content: bytes) -> tuple[list[PortfolioHolding], int, list[str]]:
    warnings: list[str] = []
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as workbook:
            shared_strings = parse_xlsx_shared_strings(workbook)
            sheet_names = [
                name
                for name in workbook.namelist()
                if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
            ]
            if not sheet_names:
                return [], 0, ["엑셀 파일에서 워크시트를 찾지 못했습니다."]
            sheet_xml = workbook.read(sorted(sheet_names)[0])
    except zipfile.BadZipFile:
        return [], 0, ["지원하지 않는 엑셀 형식입니다. .xlsx 또는 CSV로 다시 저장해 주세요."]
    root = ElementTree.fromstring(sheet_xml)
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    table_rows: list[list[str]] = []
    for row in root.findall(".//x:sheetData/x:row", namespace):
        values_by_column: dict[int, str] = {}
        for cell in row.findall("x:c", namespace):
            values_by_column[xlsx_column_index(cell.attrib.get("r", ""))] = xlsx_cell_value(
                cell,
                shared_strings,
            )
        max_column = max(values_by_column.keys(), default=-1)
        values = [values_by_column.get(index, "") for index in range(max_column + 1)]
        if any(str(value).strip() for value in values):
            table_rows.append(values)
    if len(table_rows) < 2:
        return [], len(table_rows), ["엑셀 파일에 헤더와 보유 종목 행이 필요합니다."]
    headers = [normalize_import_header(value) for value in table_rows[0]]
    holdings = []
    for values in table_rows[1:]:
        record = {headers[index]: value for index, value in enumerate(values) if index < len(headers)}
        holding = portfolio_holding_from_row(record)
        if holding:
            holdings.append(holding)
    if not holdings:
        warnings.append("엑셀에서 보유 종목을 인식하지 못했습니다. 첫 행에 티커/수량/평가금액 등의 열 이름을 넣어주세요.")
    return holdings, len(table_rows) - 1, warnings
