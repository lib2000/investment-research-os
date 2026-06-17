import csv
import io
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from re import findall, search
from xml.etree import ElementTree

from research_os import file_attachment_utils
from research_os import file_image_metadata
from research_os import file_spreadsheet_extraction


def safe_attachment_file_name(file_name: str | None) -> str:
    return file_attachment_utils.safe_attachment_file_name(file_name)


def decode_attachment_base64(content_base64: str | None) -> bytes | None:
    return file_attachment_utils.decode_attachment_base64(content_base64)


PDF_TEXT_MAX_CHARS = 120_000
PDF_OCR_TEXT_MAX_CHARS = 80_000
PDF_OCR_MAX_PAGES = 20
IMAGE_OCR_TEXT_MAX_CHARS = 80_000
IMAGE_EXTENSIONS = file_attachment_utils.IMAGE_EXTENSIONS
IMAGE_MIME_PREFIXES = file_attachment_utils.IMAGE_MIME_PREFIXES


def is_pdf_attachment(file_name: str | None, mime_type: str | None) -> bool:
    return file_attachment_utils.is_pdf_attachment(file_name, mime_type)


def is_image_attachment(file_name: str | None, mime_type: str | None) -> bool:
    return file_attachment_utils.is_image_attachment(file_name, mime_type)


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


def extract_pdf_text_with_ocr(file_bytes: bytes) -> tuple[str, str]:
    tesseract_cmd = resolve_tesseract_executable()
    if not tesseract_cmd:
        return "", "Tesseract OCR 실행 파일을 찾지 못했습니다."
    tessdata_dir = resolve_tessdata_dir()
    if not tessdata_dir:
        return "", "한국어/영어 OCR 언어팩(kor+eng)을 찾지 못했습니다."

    try:
        import fitz
    except Exception as exc:
        return "", f"PDF 이미지 렌더링 라이브러리(PyMuPDF)를 불러오지 못했습니다: {exc}"

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        return "", f"PDF를 OCR 이미지로 여는 데 실패했습니다: {exc}"

    page_count = len(doc)
    pages_to_process = min(page_count, PDF_OCR_MAX_PAGES)
    page_texts: list[str] = []

    try:
        with tempfile.TemporaryDirectory(prefix="research-ocr-") as temp_dir:
            temp_path = Path(temp_dir)
            for page_index in range(pages_to_process):
                page = doc.load_page(page_index)
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image_path = temp_path / f"page-{page_index + 1}.png"
                pixmap.save(str(image_path))

                command = [
                    tesseract_cmd,
                    str(image_path),
                    "stdout",
                    "-l",
                    "kor+eng",
                    "--tessdata-dir",
                    str(tessdata_dir),
                    "--psm",
                    "6",
                ]
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=90,
                )
                if completed.returncode != 0:
                    page_text = f"[{page_index + 1}페이지 OCR 실패: {completed.stderr.strip() or 'unknown error'}]"
                else:
                    page_text = completed.stdout.strip()
                if page_text:
                    page_texts.append(f"[{page_index + 1}페이지 OCR]\n{page_text}")

                if len("\n\n".join(page_texts)) >= PDF_OCR_TEXT_MAX_CHARS:
                    break
    finally:
        doc.close()

    extracted_text = "\n\n".join(page_texts).strip()
    if not extracted_text:
        return "", "OCR을 실행했지만 인식 가능한 텍스트를 찾지 못했습니다."

    if len(extracted_text) > PDF_OCR_TEXT_MAX_CHARS:
        extracted_text = (
            f"{extracted_text[:PDF_OCR_TEXT_MAX_CHARS]}\n\n"
            f"[OCR 본문이 길어 앞부분 {PDF_OCR_TEXT_MAX_CHARS:,}자만 분석에 사용했습니다. 원본 PDF는 별도로 저장했습니다.]"
        )
    page_note = f"{pages_to_process}/{page_count}페이지"
    return extracted_text, f"OCR 텍스트 추출 완료: {page_note}, {len(extracted_text):,}자"


def detect_image_dimensions(file_bytes: bytes) -> dict:
    return file_image_metadata.detect_image_dimensions(file_bytes)


def extract_image_text_with_ocr(
    file_bytes: bytes,
    file_name: str | None,
    mime_type: str | None,
    source_path: Path | None = None,
) -> tuple[str, str, dict]:
    image_profile = detect_image_dimensions(file_bytes)
    tesseract_cmd = resolve_tesseract_executable()
    if not tesseract_cmd:
        return (
            "",
            "이미지 OCR 미실행: Tesseract OCR 실행 파일을 찾지 못했습니다.",
            {
                **image_profile,
                "ocr_engine": "tesseract",
                "ocr_available": False,
                "ocr_status": "unavailable",
                "ocr_missing_reason": "tesseract_not_found",
            },
        )

    suffix = Path(str(file_name or "")).suffix.lower()
    if suffix not in IMAGE_EXTENSIONS:
        suffix = ".png" if "png" in str(mime_type or "").lower() else ".jpg"

    try:
        if source_path and source_path.exists():
            image_path = source_path
            cleanup_context = None
        else:
            cleanup_context = tempfile.TemporaryDirectory(prefix="research-image-ocr-")
            temp_dir = cleanup_context.__enter__()
            image_path = Path(temp_dir) / f"input{suffix}"
            image_path.write_bytes(file_bytes)
        try:
            command = [
                tesseract_cmd,
                str(image_path),
                "stdout",
                "-l",
                "kor+eng",
                "--psm",
                "6",
            ]
            tessdata_dir = resolve_tessdata_dir()
            if tessdata_dir:
                command.extend(["--tessdata-dir", str(tessdata_dir)])
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=90,
            )
            if completed.returncode != 0:
                fallback_command = [
                    tesseract_cmd,
                    str(image_path),
                    "stdout",
                    "-l",
                    "eng",
                    "--psm",
                    "6",
                ]
                fallback = subprocess.run(
                    fallback_command,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=90,
                )
                if fallback.returncode != 0:
                    return (
                        "",
                        f"이미지 OCR 실패: {completed.stderr.strip() or fallback.stderr.strip() or 'unknown error'}",
                        {
                            **image_profile,
                            "ocr_engine": "tesseract",
                            "ocr_available": True,
                            "ocr_status": "error",
                            "ocr_language": "kor+eng",
                            "ocr_error": completed.stderr.strip() or fallback.stderr.strip(),
                        },
                    )
                text = fallback.stdout.strip()
                language_note = "eng"
            else:
                text = completed.stdout.strip()
                language_note = "kor+eng"
        finally:
            if cleanup_context is not None:
                cleanup_context.__exit__(None, None, None)
    except Exception as exc:
        return (
            "",
            f"이미지 OCR 미실행: OCR 임시 파일을 처리하지 못했습니다: {exc}",
            {
                **image_profile,
                "ocr_engine": "tesseract",
                "ocr_available": False,
                "ocr_status": "error",
                "ocr_language": "kor+eng",
                "ocr_missing_reason": "ocr_runtime_error",
                "ocr_error": str(exc),
            },
        )

    if not text:
        return (
            "",
            "이미지 OCR을 실행했지만 인식 가능한 텍스트를 찾지 못했습니다.",
            {
                **image_profile,
                "ocr_engine": "tesseract",
                "ocr_available": True,
                "ocr_status": "empty",
                "ocr_language": language_note,
            },
        )
    if len(text) > IMAGE_OCR_TEXT_MAX_CHARS:
        text = (
            f"{text[:IMAGE_OCR_TEXT_MAX_CHARS]}\n\n"
            f"[이미지 OCR 본문이 길어 앞부분 {IMAGE_OCR_TEXT_MAX_CHARS:,}자만 분석에 사용했습니다. 원본 이미지는 별도로 저장했습니다.]"
        )
    return (
        text,
        f"이미지 OCR 텍스트 추출 완료: {language_note}, {len(text):,}자",
        {
            **image_profile,
            "ocr_engine": "tesseract",
            "ocr_available": True,
            "ocr_status": "success",
            "ocr_language": language_note,
        },
    )


def extract_pdf_text(file_bytes: bytes) -> tuple[str, str]:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        ocr_text, ocr_note = extract_pdf_text_with_ocr(file_bytes)
        if ocr_text:
            return ocr_text, f"PDF 텍스트 추출 라이브러리 오류 후 OCR 사용: {ocr_note}"
        return "", f"PDF 텍스트 추출 라이브러리를 불러오지 못했습니다: {exc}; {ocr_note}"

    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        if getattr(reader, "is_encrypted", False):
            try:
                reader.decrypt("")
            except Exception:
                return "", "암호화된 PDF라서 본문 텍스트를 추출하지 못했습니다."

        page_texts = []
        for page_index, page in enumerate(reader.pages, start=1):
            try:
                text = (page.extract_text() or "").strip()
            except Exception as page_exc:
                text = f"[{page_index}페이지 텍스트 추출 실패: {page_exc}]"
            if text:
                page_texts.append(f"[{page_index}페이지]\n{text}")

        extracted_text = "\n\n".join(page_texts).strip()
        if not extracted_text:
            ocr_text, ocr_note = extract_pdf_text_with_ocr(file_bytes)
            if ocr_text:
                return ocr_text, f"PDF 텍스트 레이어 없음. OCR 사용: {ocr_note}"
            return "", f"PDF에서 추출 가능한 텍스트를 찾지 못했습니다. 스캔 이미지 PDF일 수 있습니다. {ocr_note}"

        page_count = len(reader.pages)
        if len(extracted_text) > PDF_TEXT_MAX_CHARS:
            extracted_text = (
                f"{extracted_text[:PDF_TEXT_MAX_CHARS]}\n\n"
                f"[PDF 본문이 길어 앞부분 {PDF_TEXT_MAX_CHARS:,}자만 분석에 사용했습니다. 원본 PDF는 별도로 저장했습니다.]"
            )
        return extracted_text, f"PDF 본문 텍스트 추출 완료: {page_count}페이지, {len(extracted_text):,}자"
    except Exception as exc:
        ocr_text, ocr_note = extract_pdf_text_with_ocr(file_bytes)
        if ocr_text:
            return ocr_text, f"PDF 본문 텍스트 추출 실패 후 OCR 사용: {ocr_note}"
        return "", f"PDF 본문 텍스트 추출 실패: {exc}; {ocr_note}"


def decode_document_bytes(file_bytes: bytes) -> tuple[str, str]:
    encodings = ["utf-8-sig", "utf-8", "cp949", "euc-kr", "latin-1"]
    for encoding in encodings:
        try:
            return file_bytes.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return file_bytes.decode("utf-8", errors="replace"), "utf-8-replace"


def extract_office_xml_text(file_bytes: bytes, xml_prefix: str) -> str:
    texts: list[str] = []
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as archive:
            names = [
                name
                for name in archive.namelist()
                if name.startswith(xml_prefix) and name.endswith(".xml")
            ]
            if xml_prefix == "word/":
                allowed_prefixes = (
                    "word/document.xml",
                    "word/header",
                    "word/footer",
                    "word/footnotes",
                    "word/endnotes",
                    "word/comments",
                )
                names = [name for name in names if name.startswith(allowed_prefixes)]
            for name in sorted(names):
                try:
                    root = ElementTree.fromstring(archive.read(name))
                except Exception:
                    continue
                slide_texts: list[str] = []
                for node in root.iter():
                    if node.tag.endswith("}t") and node.text:
                        clean = " ".join(node.text.split())
                        if clean:
                            slide_texts.append(clean)
                if slide_texts:
                    label = Path(name).stem
                    texts.append(f"[{label}]\n" + "\n".join(slide_texts))
    except Exception:
        return ""
    return "\n\n".join(texts).strip()


def extract_docx_text(file_bytes: bytes) -> tuple[str, str]:
    text = extract_office_xml_text(file_bytes, "word/")
    if not text:
        return "", "DOCX 문서에서 본문 텍스트를 찾지 못했습니다."
    return text, f"DOCX 본문 텍스트 추출 완료: {len(text):,}자"


def extract_pptx_text(file_bytes: bytes) -> tuple[str, str]:
    text = extract_office_xml_text(file_bytes, "ppt/slides/")
    if not text:
        return "", "PPTX 문서에서 슬라이드 텍스트를 찾지 못했습니다."
    return text, f"PPTX 슬라이드 텍스트 추출 완료: {len(text):,}자"


def excel_column_index(cell_ref: str) -> int:
    return file_spreadsheet_extraction.excel_column_index(cell_ref)


def extract_xlsx_text(file_bytes: bytes, max_sheets: int = 5, max_rows: int = 80) -> tuple[str, str]:
    return file_spreadsheet_extraction.extract_xlsx_text(file_bytes, max_sheets=max_sheets, max_rows=max_rows)

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


def build_file_extraction_profile(
    document_type: str,
    extracted_text: str,
    extraction_note: str,
    warnings: list[str],
) -> dict:
    text = (extracted_text or "").strip()
    note = extraction_note or ""
    char_count = len(text)
    lines = [line for line in text.splitlines() if line.strip()]
    line_count = len(lines)
    numeric_token_count = len(findall(r"[-+]?\d[\d,]*(?:\.\d+)?%?", text))
    table_like_line_count = sum(
        1
        for line in lines
        if "\t" in line or "|" in line or line.count(",") >= 3
    )
    used_ocr = "OCR" in note.upper()
    truncated = "앞부분" in text or "앞부분" in note
    warning_count = len([warning for warning in warnings if warning])
    has_korean = bool(search(r"[가-힣]", text))
    has_english = bool(search(r"[A-Za-z]", text))
    quality_drivers: list[str] = []

    if char_count >= 2_000 and warning_count == 0:
        readiness = "높음"
        use_case = "본문을 투자 논거, RAG 검색, 리포트 합성에 바로 사용할 수 있습니다."
        quality = 0.92
        quality_drivers.append("본문 길이 충분")
    elif char_count >= 600:
        readiness = "보통"
        use_case = "핵심 문장 중심으로 분석 가능하며, 표·숫자 누락 여부를 확인하면 좋습니다."
        quality = 0.78
        quality_drivers.append("본문 일부 확보")
    elif char_count > 0:
        readiness = "낮음"
        use_case = "요약 신호로만 제한 활용하고 원문 확인 또는 추가 입력을 병행하세요."
        quality = 0.55
        quality_drivers.append("본문 짧음")
    else:
        readiness = "본문 없음"
        use_case = "파일명과 메타데이터만 분류에 사용됩니다."
        quality = 0.35
        quality_drivers.append("본문 없음")

    if document_type == "Excel 문서" and table_like_line_count:
        quality = max(quality, 0.86)
        readiness = "높음" if char_count >= 600 else "보통"
        use_case = "표 형태의 수치와 항목을 추출했으므로 피어 비교, 포트폴리오, KPI 정리에 활용할 수 있습니다."
        quality_drivers.append("표형 데이터 감지")
    elif document_type == "텍스트/표 문서" and table_like_line_count >= 2:
        quality = max(quality, 0.74)
        readiness = "보통" if char_count >= 40 else readiness
        use_case = "짧은 표형 텍스트라도 수치·보유종목·KPI 후보 추출에 활용할 수 있습니다."
        quality_drivers.append("표형 텍스트 감지")
    elif document_type in {"Word 문서", "PowerPoint 문서"} and char_count >= 600:
        use_case = "문장형 리서치 메모와 발표자료 요약, 핵심 논거 추출에 활용할 수 있습니다."
        quality_drivers.append("문장형 문서")
    elif document_type in {"Word 문서", "PowerPoint 문서"} and char_count >= 50 and numeric_token_count >= 2:
        quality = max(quality, 0.68)
        readiness = "보통"
        use_case = "짧은 문서지만 핵심 문장과 수치가 있어 투자 메모 초안과 체크포인트 생성에 활용할 수 있습니다."
        quality_drivers.append("짧은 문장형 KPI 메모")
    elif document_type == "PDF" and char_count >= 600:
        quality_drivers.append("PDF 본문 추출")
    elif document_type in {"PDF", "텍스트/표 문서", "Word 문서", "PowerPoint 문서"} and char_count >= 120 and has_korean:
        quality = max(quality, 0.64)
        readiness = "보통"
        use_case = "짧은 본문이지만 종목·산업 메모로 활용 가능하며, 추가 수치가 있으면 리포트 논거로 확장할 수 있습니다."
        quality_drivers.append("짧은 문장형 투자 메모")
    if numeric_token_count >= 5:
        quality_drivers.append("수치 신호 충분")
    if used_ocr and quality > 0.82:
        quality = 0.82
        quality_drivers.append("OCR 결과라 보수 판정")
    if truncated:
        quality = min(quality, 0.82)
        quality_drivers.append("본문 길이 제한")
    if warning_count:
        quality = min(quality, 0.72)
        quality_drivers.append("추출 경고 존재")

    quality_label = "좋음" if quality >= 0.85 else "보통" if quality >= 0.6 else "확인 필요"
    next_action = "바로 저장/RAG 반영 가능"
    if warning_count or char_count < 600:
        next_action = "원문 미리보기에서 핵심 수치·표·본문 누락 여부 확인"
    if not char_count:
        next_action = "OCR 가능 파일 또는 본문 텍스트를 추가 입력"

    return {
        "quality_label": quality_label,
        "analysis_readiness": readiness,
        "use_case": use_case,
        "next_action": next_action,
        "char_count": char_count,
        "line_count": line_count,
        "numeric_token_count": numeric_token_count,
        "table_like_line_count": table_like_line_count,
        "has_korean": has_korean,
        "has_english": has_english,
        "used_ocr": used_ocr,
        "truncated": truncated,
        "warning_count": warning_count,
        "quality_drivers": quality_drivers,
        "recommended_quality": round(quality, 2),
    }


def extract_uploaded_file_text(
    file_bytes: bytes,
    file_name: str | None,
    mime_type: str | None,
    source_path: Path | None = None,
) -> dict:
    lower_mime = str(mime_type or "").lower()
    extension = Path(str(file_name or "")).suffix.lower()
    document_type = "원본 파일"
    extracted_text = ""
    extraction_note = "원본 파일만 저장했습니다."
    warnings: list[str] = []
    image_profile: dict = {}

    if is_pdf_attachment(file_name, mime_type):
        document_type = "PDF"
        extracted_text, extraction_note = extract_pdf_text(file_bytes)
    elif is_image_attachment(file_name, mime_type):
        document_type = "이미지"
        extracted_text, extraction_note, image_profile = extract_image_text_with_ocr(
            file_bytes,
            file_name,
            mime_type,
            source_path,
        )
        if not extracted_text:
            if image_profile.get("ocr_status") == "unavailable":
                warnings.append(
                    "이미지 OCR 미연결: 원본 이미지는 저장했지만 이미지 속 글자는 분석 본문으로 쓰지 않았습니다. "
                    "Tesseract 설치 후 다시 업로드하거나 본문을 직접 입력하세요."
                )
            else:
                warnings.append(
                    "이미지 본문을 읽지 못했습니다. OCR 실행 파일 또는 이미지 선명도를 확인하세요."
                )
    elif extension == ".docx" or lower_mime.endswith("wordprocessingml.document"):
        document_type = "Word 문서"
        extracted_text, extraction_note = extract_docx_text(file_bytes)
    elif extension == ".pptx" or lower_mime.endswith("presentationml.presentation"):
        document_type = "PowerPoint 문서"
        extracted_text, extraction_note = extract_pptx_text(file_bytes)
    elif extension == ".xlsx" or lower_mime.endswith("spreadsheetml.sheet"):
        document_type = "Excel 문서"
        extracted_text, extraction_note = extract_xlsx_text(file_bytes)
    elif extension in {".txt", ".md", ".csv", ".tsv", ".json", ".html", ".htm", ".xml"} or lower_mime.startswith("text/") or lower_mime in {
        "application/json",
        "application/csv",
        "application/xml",
        "text/csv",
        "text/tab-separated-values",
    }:
        document_type = "텍스트/표 문서"
        extracted_text, extraction_note = extract_text_like_file(file_bytes, file_name)
    elif extension in {".xls", ".ods", ".doc", ".ppt"}:
        document_type = "구형 Office 문서"
        warnings.append("구형 Office 형식은 서버에서 안정적으로 본문을 추출하지 못할 수 있습니다. XLSX/DOCX/PPTX로 저장해 올리면 정확도가 높아집니다.")
    else:
        warnings.append("지원 형식이 아니어서 원본 저장과 파일 메타데이터만 분석에 사용했습니다.")

    extracted_text = (extracted_text or "").strip()
    if extracted_text and len(extracted_text) > PDF_TEXT_MAX_CHARS:
        extracted_text = (
            f"{extracted_text[:PDF_TEXT_MAX_CHARS]}\n\n"
            f"[본문이 길어 앞부분 {PDF_TEXT_MAX_CHARS:,}자만 분석에 사용했습니다. 원본 파일은 별도로 저장했습니다.]"
        )
        warnings.append("본문 길이 제한으로 앞부분만 분석 컨텍스트에 주입했습니다.")
    if not extracted_text:
        warnings.append("본문 텍스트가 비어 있어 제목, 파일명, 메타데이터 중심으로만 분류합니다.")

    extraction_profile = build_file_extraction_profile(
        document_type,
        extracted_text,
        extraction_note,
        warnings,
    )
    if document_type == "PDF":
        if extracted_text and "OCR" in extraction_note.upper():
            extraction_profile["ocr_available"] = True
            extraction_profile["ocr_status"] = "success"
            extraction_profile["ocr_language"] = "kor+eng"
            extraction_profile["ocr_next_action"] = "OCR 본문이 저장 데이터와 RAG 색인에 반영되었습니다."
        elif "Tesseract OCR 실행 파일을 찾지 못" in extraction_note:
            extraction_profile["ocr_available"] = False
            extraction_profile["ocr_status"] = "unavailable"
            extraction_profile["ocr_missing_reason"] = "tesseract_not_found"
            extraction_profile["ocr_next_action"] = "Tesseract 설치 또는 TESSERACT_CMD 지정 후 다시 업로드"
        elif "언어팩" in extraction_note or "kor+eng" in extraction_note:
            extraction_profile["ocr_available"] = False
            extraction_profile["ocr_status"] = "unavailable"
            extraction_profile["ocr_missing_reason"] = "language_pack_missing"
            extraction_profile["ocr_next_action"] = "kor.traineddata와 eng.traineddata가 있는 tessdata 경로를 TESSDATA_PREFIX로 지정"
        elif "인식 가능한 텍스트를 찾지 못" in extraction_note:
            extraction_profile["ocr_available"] = True
            extraction_profile["ocr_status"] = "empty"
            extraction_profile["ocr_next_action"] = "스캔 품질을 확인하거나 본문 텍스트를 직접 입력"
        elif "OCR" in extraction_note.upper():
            extraction_profile["ocr_available"] = False
            extraction_profile["ocr_status"] = "error"
            extraction_profile["ocr_error"] = extraction_note
            extraction_profile["ocr_next_action"] = "OCR 런타임과 PDF 렌더링 환경 확인"
    if image_profile:
        extraction_profile["image_profile"] = image_profile
        extraction_profile["ocr_available"] = image_profile.get("ocr_available")
        extraction_profile["ocr_status"] = image_profile.get("ocr_status")
        extraction_profile["ocr_language"] = image_profile.get("ocr_language")
        extraction_profile["ocr_missing_reason"] = image_profile.get("ocr_missing_reason")
        extraction_profile["ocr_next_action"] = (
            "Tesseract 설치 또는 TESSERACT_CMD 지정 후 다시 업로드"
            if image_profile.get("ocr_status") == "unavailable"
            else None
        )
        if image_profile.get("width") and image_profile.get("height"):
            extraction_profile["image_size"] = f"{image_profile.get('width')}x{image_profile.get('height')}"
    quality = float(extraction_profile.get("recommended_quality") or 0.35)
    preview = extracted_text[:1200].strip()
    return {
        "document_type": document_type,
        "text_extraction": extraction_note,
        "extracted_text": extracted_text,
        "extraction_quality": quality,
        "extraction_char_count": len(extracted_text),
        "extraction_preview": preview,
        "extraction_warnings": warnings,
        "extraction_profile": extraction_profile,
    }
