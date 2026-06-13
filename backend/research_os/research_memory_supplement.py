"""Research-memory manual body supplement helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from fastapi import HTTPException

from research_os.models import ResearchMemoryContentResponse, ResearchMemorySupplementRequest


class ResearchMemorySupplementRuntime(Protocol):
    """Runtime callbacks supplied by research_os_main while supplement handling is split out."""


def supplement_research_memory_file(
    runtime: ResearchMemorySupplementRuntime,
    ticker: str,
    file_name: str,
    request: ResearchMemorySupplementRequest,
    vault_dir: Path,
) -> ResearchMemoryContentResponse:
    safe_name = Path(file_name).name
    if safe_name != file_name or not safe_name.endswith(".md"):
        raise HTTPException(status_code=400, detail="수정할 수 없는 파일명입니다.")

    body_text = request.body_text.strip()
    if not body_text:
        raise HTTPException(status_code=422, detail="보강할 본문 텍스트가 비어 있습니다.")

    ticker_dir = (vault_dir / ticker).resolve()
    target_path = (ticker_dir / safe_name).resolve()
    if target_path.parent != ticker_dir:
        raise HTTPException(status_code=400, detail="허용되지 않은 파일 경로입니다.")
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="저장된 리포트 파일을 찾을 수 없습니다.")

    supplemented_at = runtime.current_storage_timestamp()
    note = (request.note or "").strip()
    current_content = target_path.read_text(encoding="utf-8")
    supplement_section = [
        "",
        "",
        "## 본문 보강",
        "",
        f"- 보강 일시: {supplemented_at}",
        "- 보강 방식: 사용자 직접 입력",
    ]
    if note:
        supplement_section.append(f"- 메모: {note}")
    supplement_section.extend(["", body_text])
    updated_content = current_content.rstrip() + "\n".join(supplement_section) + "\n"
    target_path.write_text(updated_content, encoding="utf-8")

    supplement_meta = {
        "supplemented_at": supplemented_at,
        "source": "user_body_copy",
        "char_count": len(body_text),
        "note": note or None,
    }
    json_path = target_path.with_suffix(".json")
    json_payload = {}
    if json_path.exists():
        try:
            json_payload = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            json_payload = {}
    if isinstance(json_payload, dict):
        supplements = json_payload.get("body_supplements")
        if not isinstance(supplements, list):
            supplements = []
        supplements.append(supplement_meta)
        json_payload["body_supplements"] = supplements
        json_payload["body_supplemented_at"] = supplemented_at
        json_payload["raw_content"] = "\n\n".join(
            value
            for value in [
                str(json_payload.get("raw_content") or "").strip(),
                "[사용자 보강 본문]",
                body_text,
            ]
            if value
        )
        capture_quality = json_payload.get("capture_quality")
        if isinstance(capture_quality, dict):
            capture_quality["status"] = "정상"
            capture_quality["body_supplemented"] = True
            capture_quality["supplemented_at"] = supplemented_at
            capture_quality["readiness"] = "사용자 보강 본문으로 분석 활용 가능"
        json_path.write_text(
            json.dumps(json_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    manifest_entry = next(
        (
            entry
            for entry in runtime.read_manifest(vault_dir)
            if entry.get("ticker") == ticker and entry.get("file_name") == target_path.name
        ),
        None,
    )
    if manifest_entry:
        updated_entry = {**manifest_entry}
        tags = list(dict.fromkeys([*(updated_entry.get("tags") or []), "body_supplemented"]))
        updated_entry["tags"] = tags
        updated_entry["body_supplemented_at"] = supplemented_at
        updated_entry["body_supplement_count"] = int(updated_entry.get("body_supplement_count") or 0) + 1
        updated_entry["content_hash"] = runtime.content_fingerprint(updated_content)
        capture_quality = updated_entry.get("capture_quality")
        if isinstance(capture_quality, dict):
            capture_quality = {**capture_quality}
            capture_quality["status"] = "정상"
            capture_quality["body_supplemented"] = True
            capture_quality["supplemented_at"] = supplemented_at
            capture_quality["readiness"] = "사용자 보강 본문으로 분석 활용 가능"
            updated_entry["capture_quality"] = capture_quality
        runtime.update_manifest(vault_dir=vault_dir, entry=updated_entry)
        runtime.upsert_research_memory_document(
            vault_dir=vault_dir,
            entry=updated_entry,
            full_text=updated_content,
        )

    return runtime.read_research_memory_file(ticker, safe_name, vault_dir)
