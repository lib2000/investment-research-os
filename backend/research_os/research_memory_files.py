"""Research-memory file path and markdown update helpers."""

from __future__ import annotations

import json
from pathlib import Path


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
