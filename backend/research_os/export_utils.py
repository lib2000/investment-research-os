import io
import json
import zipfile
from re import sub


def excel_column_name(index: int) -> str:
    name = ""
    current = max(1, int(index))
    while current:
        current, remainder = divmod(current - 1, 26)
        name = chr(65 + remainder) + name
    return name


def xml_text(value) -> str:
    text = "" if value is None else str(value)
    text = "".join(ch for ch in text if ch in "\t\n\r" or ord(ch) >= 32)
    if len(text) > 32000:
        text = f"{text[:32000]}\n... (긴 내용은 엑셀 셀 제한 때문에 일부 생략됨)"
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def sanitize_excel_sheet_name(name: str, fallback: str) -> str:
    cleaned = sub(r"[\[\]\:\*\?\/\\]", " ", str(name or fallback)).strip()
    cleaned = sub(r"\s+", " ", cleaned)
    return (cleaned or fallback)[:31]


def worksheet_xml(rows: list[list[object]]) -> str:
    row_xml = []
    for row_index, row in enumerate(rows[:5000], start=1):
        cell_xml = []
        for col_index, value in enumerate((row or [])[:50], start=1):
            ref = f"{excel_column_name(col_index)}{row_index}"
            cell_xml.append(
                f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">'
                f"{xml_text(value)}</t></is></c>"
            )
        row_xml.append(f'<row r="{row_index}">{"".join(cell_xml)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        "</worksheet>"
    )


def build_simple_xlsx(sheets: list[tuple[str, list[list[object]]]]) -> bytes:
    safe_sheets = []
    used_names: set[str] = set()
    for index, (name, rows) in enumerate(sheets[:12], start=1):
        base_name = sanitize_excel_sheet_name(name, f"Sheet{index}")
        sheet_name = base_name
        suffix = 2
        while sheet_name in used_names:
            tail = f" {suffix}"
            sheet_name = f"{base_name[:31 - len(tail)]}{tail}"
            suffix += 1
        used_names.add(sheet_name)
        safe_sheets.append((sheet_name, rows or []))

    if not safe_sheets:
        safe_sheets = [("분석 결과", [["내용"], ["내보낼 결과가 없습니다."]])]

    content_types = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
    ]
    for index, _sheet in enumerate(safe_sheets, start=1):
        content_types.append(
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    content_types.append("</Types>")

    workbook_sheets = "".join(
        f'<sheet name="{xml_text(name)}" sheetId="{index}" r:id="rId{index}"/>'
        for index, (name, _rows) in enumerate(safe_sheets, start=1)
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{workbook_sheets}</sheets></workbook>"
    )

    workbook_rels = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
    ]
    for index, _sheet in enumerate(safe_sheets, start=1):
        workbook_rels.append(
            f'<Relationship Id="rId{index}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{index}.xml"/>'
        )
    workbook_rels.append(
        f'<Relationship Id="rId{len(safe_sheets) + 1}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    workbook_rels.append("</Relationships>")

    styles_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
        "</styleSheet>"
    )

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "".join(content_types))
        archive.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml"/></Relationships>',
        )
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", "".join(workbook_rels))
        archive.writestr("xl/styles.xml", styles_xml)
        for index, (_name, rows) in enumerate(safe_sheets, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", worksheet_xml(rows))
    return output.getvalue()


def flatten_export_value(value, prefix: str = "", depth: int = 0) -> list[list[object]]:
    if depth > 3:
        return [[prefix or "value", json.dumps(value, ensure_ascii=False, default=str)]]
    if isinstance(value, dict):
        rows = []
        for key, item in value.items():
            label = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(item, (dict, list)):
                rows.extend(flatten_export_value(item, label, depth + 1))
            else:
                rows.append([label, item])
        return rows
    if isinstance(value, list):
        rows = []
        for index, item in enumerate(value[:200], start=1):
            label = f"{prefix}[{index}]"
            if isinstance(item, (dict, list)):
                rows.extend(flatten_export_value(item, label, depth + 1))
            else:
                rows.append([label, item])
        return rows
    return [[prefix or "value", value]]


def rows_from_dict_list(items: list[dict]) -> list[list[object]]:
    keys: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        for key in item.keys():
            if key not in keys:
                keys.append(key)
    rows = [keys or ["값"]]
    for item in items[:1000]:
        if isinstance(item, dict):
            rows.append(
                [
                    json.dumps(item.get(key), ensure_ascii=False, default=str)
                    if isinstance(item.get(key), (dict, list))
                    else item.get(key)
                    for key in keys
                ]
            )
        else:
            rows.append([item])
    return rows


def collect_result_export_sheets(
    payload: dict,
    generated_at_fallback: str | None = None,
) -> list[tuple[str, list[list[object]]]]:
    title = str(payload.get("title") or "분석 결과").strip() or "분석 결과"
    module = str(payload.get("module") or "").strip()
    result_text = str(payload.get("result_text") or "").replace("\r\n", "\n").strip()
    generated_at = payload.get("generated_at") or generated_at_fallback or ""
    result_json = payload.get("result_json")

    sheets: list[tuple[str, list[list[object]]]] = [
        (
            "요약",
            [
                ["항목", "내용"],
                ["제목", title],
                ["모듈", module or "화면 결과"],
                ["생성 시각", generated_at],
                ["원문 줄 수", len([line for line in result_text.split("\n") if line.strip()])],
            ],
        ),
        (
            "화면 결과",
            [["순번", "내용"]]
            + [
                [index, line]
                for index, line in enumerate(result_text.split("\n"), start=1)
                if line.strip()
            ],
        ),
    ]

    if isinstance(result_json, dict):
        scalar_rows = [["항목", "내용"]]
        for key, value in result_json.items():
            if not isinstance(value, (dict, list)):
                scalar_rows.append([key, value])
        if len(scalar_rows) > 1:
            sheets.append(("구조화 요약", scalar_rows))

        added = 0
        for key, value in result_json.items():
            if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
                sheets.append((str(key), rows_from_dict_list(value)))
                added += 1
            elif isinstance(value, dict) and added < 4:
                rows = [["항목", "내용"]] + flatten_export_value(value)
                if len(rows) > 1:
                    sheets.append((str(key), rows))
                    added += 1
            if added >= 8:
                break
    elif result_json is not None:
        sheets.append(
            (
                "원본 JSON",
                [["내용"], [json.dumps(result_json, ensure_ascii=False, indent=2, default=str)]],
            )
        )

    return sheets
