"""Spreadsheet attachment text extraction helpers."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from xml.etree import ElementTree


def excel_column_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha()).upper()
    index = 0
    for ch in letters:
        index = index * 26 + (ord(ch) - ord("A") + 1)
    return max(index - 1, 0)


def extract_xlsx_text(file_bytes: bytes, max_sheets: int = 5, max_rows: int = 80) -> tuple[str, str]:
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as archive:
            shared_strings: list[str] = []
            if "xl/sharedStrings.xml" in archive.namelist():
                try:
                    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
                    for item in root.iter():
                        if item.tag.endswith("}si"):
                            parts = [
                                node.text or ""
                                for node in item.iter()
                                if node.tag.endswith("}t") and node.text
                            ]
                            shared_strings.append("".join(parts))
                except Exception:
                    shared_strings = []

            sheet_names = [
                name
                for name in archive.namelist()
                if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
            ][:max_sheets]
            sheet_outputs: list[str] = []
            total_rows = 0
            for sheet_name in sheet_names:
                try:
                    root = ElementTree.fromstring(archive.read(sheet_name))
                except Exception:
                    continue
                rows: list[str] = []
                for row in root.iter():
                    if not row.tag.endswith("}row"):
                        continue
                    values: dict[int, str] = {}
                    for cell in list(row):
                        if not cell.tag.endswith("}c"):
                            continue
                        cell_type = cell.attrib.get("t")
                        cell_ref = cell.attrib.get("r", "")
                        column_index = excel_column_index(cell_ref)
                        value = ""
                        if cell_type == "inlineStr":
                            value = " ".join(
                                node.text or ""
                                for node in cell.iter()
                                if node.tag.endswith("}t") and node.text
                            ).strip()
                        else:
                            value_node = next((node for node in cell if node.tag.endswith("}v")), None)
                            raw_value = value_node.text if value_node is not None else ""
                            if cell_type == "s" and raw_value.isdigit():
                                string_index = int(raw_value)
                                value = shared_strings[string_index] if string_index < len(shared_strings) else raw_value
                            else:
                                value = raw_value or ""
                        if value:
                            values[column_index] = " ".join(str(value).split())
                    if values:
                        max_col = min(max(values.keys()), 30)
                        rows.append("\t".join(values.get(index, "") for index in range(max_col + 1)).rstrip())
                        total_rows += 1
                    if len(rows) >= max_rows:
                        rows.append(f"[표가 길어 앞부분 {max_rows:,}행만 미리보기로 추출했습니다.]")
                        break
                if rows:
                    sheet_outputs.append(f"[{Path(sheet_name).stem}]\n" + "\n".join(rows))
            text = "\n\n".join(sheet_outputs).strip()
            if not text:
                return "", "XLSX 파일에서 읽을 수 있는 셀 값을 찾지 못했습니다."
            return text, f"XLSX 표 데이터 추출 완료: {len(sheet_outputs)}개 시트, {total_rows:,}행"
    except Exception as exc:
        return "", f"XLSX 표 데이터 추출 실패: {exc}"