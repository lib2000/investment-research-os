from __future__ import annotations

import csv
import io
from pathlib import Path


def decode_document_bytes(file_bytes: bytes) -> tuple[str, str]:
    encodings = ["utf-8-sig", "utf-8", "cp949", "euc-kr", "latin-1"]
    for encoding in encodings:
        try:
            return file_bytes.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return file_bytes.decode("utf-8", errors="replace"), "utf-8-replace"


def extract_text_like_file(file_bytes: bytes, file_name: str | None) -> tuple[str, str]:
    decoded, encoding = decode_document_bytes(file_bytes)
    extension = Path(str(file_name or "")).suffix.lower()
    if extension in {".csv", ".tsv"}:
        delimiter = "\t" if extension == ".tsv" else ","
        rows = list(csv.reader(io.StringIO(decoded), delimiter=delimiter))
        preview_rows = rows[:120]
        preview = "\n".join("\t".join(cell.strip() for cell in row[:30]) for row in preview_rows)
        if len(rows) > len(preview_rows):
            preview += f"\n[표가 길어 앞부분 {len(preview_rows):,}행만 미리보기로 추출했습니다.]"
        return preview, f"{extension.upper().lstrip('.')} 표 텍스트 추출 완료: {len(preview_rows):,}/{len(rows):,}행, 인코딩 {encoding}"
    return decoded, f"텍스트 본문 추출 완료: 인코딩 {encoding}, {len(decoded):,}자"
