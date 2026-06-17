from __future__ import annotations

import os
import shutil
from pathlib import Path


PDF_TEXT_MAX_CHARS = 120_000
PDF_OCR_TEXT_MAX_CHARS = 80_000
PDF_OCR_MAX_PAGES = 20
IMAGE_OCR_TEXT_MAX_CHARS = 80_000


def resolve_tesseract_executable() -> str | None:
    candidates = [
        Path(value)
        for value in [
            os.environ.get("TESSERACT_CMD"),
            shutil.which("tesseract"),
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        if value
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def resolve_tessdata_dir() -> Path | None:
    candidates = [
        Path(value)
        for value in [
            os.environ.get("TESSDATA_PREFIX"),
            str(Path(__file__).resolve().parent.parent / "tessdata"),
            r"C:\Program Files\Tesseract-OCR\tessdata",
        ]
        if value
    ]
    for candidate in candidates:
        if (candidate / "kor.traineddata").exists() and (candidate / "eng.traineddata").exists():
            return candidate
    return None


def ocr_runtime_status() -> dict:
    tesseract_cmd = resolve_tesseract_executable()
    tessdata_dir = resolve_tessdata_dir()
    languages_ready = bool(tessdata_dir)
    ready = bool(tesseract_cmd and languages_ready)
    if ready:
        message = "Tesseract OCR 실행 파일과 kor+eng 언어팩이 연결되어 있습니다."
        next_action = "이미지와 스캔 PDF 본문 추출을 사용할 수 있습니다."
    elif not tesseract_cmd:
        message = "Tesseract OCR 실행 파일을 찾지 못했습니다."
        next_action = "Windows용 Tesseract를 설치하거나 TESSERACT_CMD 환경변수로 실행 파일 경로를 지정하세요."
    else:
        message = "Tesseract 실행 파일은 있지만 kor+eng 언어팩을 찾지 못했습니다."
        next_action = "kor.traineddata와 eng.traineddata가 있는 tessdata 경로를 TESSDATA_PREFIX로 지정하세요."
    return {
        "status": "success" if ready else "warning",
        "ready": ready,
        "engine": "tesseract",
        "executable_found": bool(tesseract_cmd),
        "executable_path": tesseract_cmd,
        "languages_ready": languages_ready,
        "required_languages": ["kor", "eng"],
        "tessdata_dir": str(tessdata_dir) if tessdata_dir else None,
        "message": message,
        "next_action": next_action,
        "limits": {
            "pdf_text_max_chars": PDF_TEXT_MAX_CHARS,
            "pdf_ocr_max_pages": PDF_OCR_MAX_PAGES,
            "pdf_ocr_text_max_chars": PDF_OCR_TEXT_MAX_CHARS,
            "image_ocr_text_max_chars": IMAGE_OCR_TEXT_MAX_CHARS,
            "message": (
                f"긴 PDF OCR은 앞부분 {PDF_OCR_MAX_PAGES:,}페이지, "
                f"OCR 본문은 앞부분 {PDF_OCR_TEXT_MAX_CHARS:,}자까지 분석에 사용합니다. "
                "누락 가능성이 있으면 원문 텍스트를 함께 저장하세요."
            ),
        },
        "image_upload_behavior": (
            "OCR 미연결 상태에서 이미지를 업로드하면 원본 파일과 파일명/크기/이미지 크기 메타데이터는 저장하지만, "
            "이미지 속 글자는 분석 본문으로 쓰지 않습니다. 결과에는 OCR 미연결과 보강 필요 경고가 표시됩니다."
        ),
    }
