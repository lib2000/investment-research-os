"""Research-memory file listing, path, and markdown update helpers."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from .models import ResearchMemoryFile


def list_research_memory_files(
    runtime: SimpleNamespace,
    ticker: str,
    vault_dir: Path,
    include_archived: bool = False,
    manifest_entries: list[dict] | None = None,
) -> list[ResearchMemoryFile]:
    ticker_dir = vault_dir / ticker
    if not ticker_dir.exists():
        return []
    manifest_source = manifest_entries if manifest_entries is not None else runtime.read_manifest(vault_dir)
    manifest_by_file = {
        entry.get("file_name"): entry
        for entry in manifest_source
        if entry.get("ticker") == ticker and entry.get("file_name")
    }

    files = sorted(
        ticker_dir.glob(f"{ticker}-*.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    memory_files = [
        build_research_memory_file(runtime, file_path, ticker, vault_dir, manifest_by_file.get(file_path.name))
        for file_path in files
    ]
    if include_archived:
        return memory_files
    return [file for file in memory_files if not file.archived and not file.is_deleted]


def build_research_memory_file(
    runtime: SimpleNamespace,
    file_path: Path,
    ticker: str,
    vault_dir: Path,
    manifest_entry: dict | None,
) -> ResearchMemoryFile:
    json_path = file_path.with_suffix(".json")
    json_payload = {}
    if json_path.exists():
        try:
            json_payload = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            json_payload = {}
    captured_item = json_payload.get("captured_item") if isinstance(json_payload, dict) else {}
    if not isinstance(captured_item, dict):
        captured_item = {}
    archived = runtime.is_archived_research_entry(manifest_entry, json_payload)
    archive_reason = (
        manifest_entry.get("archive_reason")
        if manifest_entry
        else json_payload.get("archive_reason")
    )
    archived_at = (
        manifest_entry.get("archived_at")
        if manifest_entry
        else json_payload.get("archived_at")
    )
    sidecar_verified = bool(
        ticker in runtime.special_research_keys
        and isinstance(json_payload, dict)
        and json_payload.get("status") == "success"
        and runtime.normalize_ticker(captured_item.get("ticker") or ticker) == ticker
    )
    verified = bool(
        (manifest_entry and runtime.is_verified_manifest_entry(manifest_entry, ticker))
        or sidecar_verified
    )
    status_label = "보관됨" if archived else "저장 메타 확인" if sidecar_verified else "공식 인증" if verified else "레거시/검증 전"
    quality_metadata = runtime.research_memory_entry_quality_metadata(
        manifest_entry,
        json_payload,
        captured_item,
    )
    return ResearchMemoryFile(
        file_name=file_path.name,
        relative_path=file_path.relative_to(vault_dir.parent).as_posix(),
        absolute_path=str(file_path),
        json_file_name=json_path.name if json_path.exists() else None,
        json_relative_path=json_path.relative_to(vault_dir.parent).as_posix()
        if json_path.exists()
        else None,
        modified_at=datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
        report_type=(
            manifest_entry.get("type")
            if manifest_entry
            else "research-capture"
            if json_payload.get("module") == "research_quick_capture"
            else runtime.infer_report_type_from_file(file_path.name)
        ),
        summary=(
            manifest_entry.get("summary")
            if manifest_entry
            else captured_item.get("summary") or json_payload.get("summary")
        ),
        verified=verified,
        legacy=not verified,
        status_label=status_label,
        tags=quality_metadata["tags"],
        source_url_processing=quality_metadata["source_url_processing"],
        capture_quality=quality_metadata["capture_quality"],
        data_quality_status=quality_metadata["data_quality_status"],
        needs_body_copy=quality_metadata["needs_body_copy"],
        url_text_unavailable=quality_metadata["url_text_unavailable"],
        attachment=(
            manifest_entry.get("attachment")
            if manifest_entry and manifest_entry.get("attachment")
            else json_payload.get("attachment")
        ),
        archived=archived,
        is_deleted=archived,
        archived_at=archived_at,
        archive_reason=archive_reason,
    )


def read_manifest_entry_payload(entry: dict | None, vault_dir: Path) -> dict:
    if not entry:
        return {}
    candidate_paths: list[Path] = []
    json_relative_path = entry.get("json_relative_path")
    if json_relative_path:
        candidate_paths.append((vault_dir.parent / str(json_relative_path)).resolve())
    relative_path = entry.get("relative_path")
    if relative_path:
        candidate_paths.append((vault_dir.parent / str(relative_path)).with_suffix(".json").resolve())
    file_name = entry.get("file_name")
    ticker = entry.get("ticker")
    if file_name and ticker:
        candidate_paths.append((vault_dir / str(ticker) / str(file_name)).with_suffix(".json").resolve())
    for path in candidate_paths:
        try:
            if path.exists() and path.is_file():
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    return payload
        except (OSError, json.JSONDecodeError):
            continue
    return {}


def manifest_entry_json_path(entry: dict | None, vault_dir: Path) -> Path | None:
    if not entry:
        return None
    candidates: list[Path] = []
    json_relative_path = entry.get("json_relative_path")
    if json_relative_path:
        candidates.append((vault_dir.parent / str(json_relative_path)).resolve())
    relative_path = entry.get("relative_path")
    if relative_path:
        candidates.append((vault_dir.parent / str(relative_path)).with_suffix(".json").resolve())
    file_name = entry.get("file_name")
    ticker = entry.get("ticker")
    if file_name and ticker:
        candidates.append((vault_dir / str(ticker) / str(file_name)).with_suffix(".json").resolve())
    root = vault_dir.parent.resolve()
    for path in candidates:
        try:
            resolved = path.resolve()
            if not str(resolved).startswith(str(root)):
                continue
            return resolved
        except OSError:
            continue
    return None


def manifest_entry_markdown_path(entry: dict | None, vault_dir: Path) -> Path | None:
    if not entry:
        return None
    candidates: list[Path] = []
    relative_path = entry.get("relative_path")
    if relative_path:
        candidates.append((vault_dir.parent / str(relative_path)).resolve())
    file_name = entry.get("file_name")
    ticker = entry.get("ticker")
    if file_name and ticker:
        candidates.append((vault_dir / str(ticker) / str(file_name)).resolve())
    root = vault_dir.parent.resolve()
    for path in candidates:
        try:
            resolved = path.resolve()
            if not str(resolved).startswith(str(root)):
                continue
            if resolved.exists() and resolved.is_file():
                return resolved
        except OSError:
            continue
    return None


def upsert_markdown_tail_section(
    markdown_path: Path | None,
    marker: str,
    section_text: str,
) -> bool:
    if not markdown_path:
        return False
    try:
        current = markdown_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    cleaned_section = section_text.strip()
    if marker in current:
        prefix = current.split(marker, 1)[0].rstrip()
        next_text = (
            f"{prefix}\n\n{marker}\n\n{cleaned_section}\n"
            if cleaned_section
            else f"{prefix}\n"
        )
    else:
        if not cleaned_section:
            return False
        next_text = f"{current.rstrip()}\n\n{marker}\n\n{cleaned_section}\n"
    if next_text == current:
        return False
    markdown_path.write_text(next_text, encoding="utf-8")
    return True


def resolve_attachment_file_path(vault_dir: Path, attachment: dict | None) -> Path | None:
    if not isinstance(attachment, dict):
        return None
    relative_path = str(attachment.get("relative_path") or "").strip()
    if not relative_path:
        return None
    root = vault_dir.resolve()
    candidate = (vault_dir / relative_path).resolve()
    try:
        if not str(candidate).startswith(str(root)):
            return None
        if candidate.exists() and candidate.is_file():
            return candidate
    except OSError:
        return None
    return None
