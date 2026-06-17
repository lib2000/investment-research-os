"""Attachment filename, decoding, and MIME helpers."""

from __future__ import annotations

import base64
from pathlib import Path
from re import sub

from fastapi import HTTPException


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
IMAGE_MIME_PREFIXES = ("image/",)


def safe_attachment_file_name(file_name: str | None) -> str:
    original = Path(file_name or "uploaded-file").name.strip() or "uploaded-file"
    stem = sub(r"[^0-9A-Za-z가-힣._-]+", "-", Path(original).stem).strip("-_.")
    suffix = sub(r"[^0-9A-Za-z.]+", "", Path(original).suffix)[:20]
    if not stem:
        stem = "uploaded-file"
    return f"{stem[:80]}{suffix}"


def decode_attachment_base64(content_base64: str | None) -> bytes | None:
    if not content_base64:
        return None
    try:
        return base64.b64decode(content_base64, validate=True)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="첨부 파일 인코딩을 해석하지 못했습니다.") from exc


def is_pdf_attachment(file_name: str | None, mime_type: str | None) -> bool:
    normalized_mime = (mime_type or "").lower()
    normalized_name = (file_name or "").lower()
    return normalized_mime == "application/pdf" or normalized_name.endswith(".pdf")


def is_image_attachment(file_name: str | None, mime_type: str | None) -> bool:
    normalized_mime = (mime_type or "").lower()
    extension = Path(str(file_name or "")).suffix.lower()
    return normalized_mime.startswith(IMAGE_MIME_PREFIXES) or extension in IMAGE_EXTENSIONS
