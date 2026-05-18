from datetime import date
import json
import os
from pathlib import Path
from re import sub
from typing import Any

from pydantic import BaseModel


class ResearchStorageInfo(BaseModel):
    file_name: str
    relative_path: str
    absolute_path: str
    json_file_name: str | None = None
    json_relative_path: str | None = None
    json_absolute_path: str | None = None
    content_type: str = "text/markdown"


def _safe_part(value: str) -> str:
    cleaned = sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return cleaned.strip("-") or "UNKNOWN"


def _read_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y"}


def _contains_onedrive(path: Path) -> bool:
    return any(part.lower() == "onedrive" for part in path.parts)


def resolve_vault_dir(configured_dir: str) -> Path:
    base_dir = Path(__file__).resolve().parents[1]
    configured_path = Path(configured_dir)
    resolved = (
        configured_path if configured_path.is_absolute() else base_dir / configured_path
    ).resolve()
    if _read_bool_env("BLOCK_ONEDRIVE_PATHS", True) and _contains_onedrive(resolved):
        raise RuntimeError(
            "OneDrive 경로는 리서치 저장소/작업 폴더로 사용할 수 없습니다. "
            "RESEARCH_VAULT_DIR를 C:\\Users\\lib20\\InvestmentJournalApp\\research_vault "
            "같은 로컬 전용 경로로 지정하세요."
        )
    return resolved


def build_research_file_name(ticker: str, report_type: str, report_date: date) -> str:
    safe_ticker = _safe_part(ticker.upper())
    safe_type = _safe_part(report_type.lower())
    return f"{safe_ticker}-{safe_type}-{report_date.isoformat()}.md"


def build_research_file_name_with_suffix(
    ticker: str,
    report_type: str,
    report_date: date,
    suffix: str | None,
) -> str:
    base_name = build_research_file_name(ticker, report_type, report_date)
    if not suffix:
        return base_name

    safe_suffix = _safe_part(suffix.lower())
    if safe_suffix == "UNKNOWN":
        return base_name
    return base_name.replace(".md", f"-{safe_suffix}.md")


def build_research_json_file_name(
    ticker: str,
    report_type: str,
    report_date: date,
    suffix: str | None = None,
) -> str:
    return build_research_file_name_with_suffix(
        ticker, report_type, report_date, suffix
    ).replace(
        ".md", ".json"
    )


def _add_sequence_suffix(file_name: str, sequence: int) -> str:
    stem, extension = file_name.rsplit(".", 1)
    return f"{stem}-{sequence:03d}.{extension}"


def _next_available_file_names(
    ticker_dir: Path,
    file_name: str,
    json_file_name: str,
) -> tuple[str, str]:
    if not (ticker_dir / file_name).exists() and not (ticker_dir / json_file_name).exists():
        return file_name, json_file_name

    for sequence in range(2, 1000):
        candidate_file_name = _add_sequence_suffix(file_name, sequence)
        candidate_json_file_name = _add_sequence_suffix(json_file_name, sequence)
        if not (ticker_dir / candidate_file_name).exists() and not (
            ticker_dir / candidate_json_file_name
        ).exists():
            return candidate_file_name, candidate_json_file_name

    raise RuntimeError("No available research file name remains for this report.")


def _read_manifest(vault_dir: Path) -> list[dict[str, Any]]:
    manifest_path = vault_dir / "manifest.json"
    if not manifest_path.exists():
        return []

    try:
        content = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    if not isinstance(content, list):
        return []
    return content


def _write_manifest(vault_dir: Path, entries: list[dict[str, Any]]) -> None:
    manifest_path = vault_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def update_manifest(
    *,
    vault_dir: Path,
    entry: dict[str, Any],
) -> None:
    vault_dir.mkdir(parents=True, exist_ok=True)
    entries = _read_manifest(vault_dir)

    entry_key = (
        entry.get("ticker"),
        entry.get("type"),
        entry.get("date"),
        entry.get("file_name"),
    )
    filtered_entries = [
        existing
        for existing in entries
        if (
            existing.get("ticker"),
            existing.get("type"),
            existing.get("date"),
            existing.get("file_name"),
        )
        != entry_key
    ]
    filtered_entries.append(entry)
    filtered_entries.sort(
        key=lambda item: (
            item.get("ticker", ""),
            item.get("date", ""),
            item.get("type", ""),
        )
    )
    _write_manifest(vault_dir, filtered_entries)


def save_research_markdown(
    *,
    vault_dir: Path,
    ticker: str,
    report_type: str,
    markdown: str,
    structured_payload: dict[str, Any] | None = None,
    manifest_entry: dict[str, Any] | None = None,
    report_date: date | None = None,
    file_suffix: str | None = None,
) -> ResearchStorageInfo:
    selected_date = report_date or date.today()
    file_name = build_research_file_name_with_suffix(
        ticker, report_type, selected_date, file_suffix
    )
    json_file_name = build_research_json_file_name(
        ticker, report_type, selected_date, file_suffix
    )
    ticker_dir = vault_dir / _safe_part(ticker.upper())
    ticker_dir.mkdir(parents=True, exist_ok=True)
    file_name, json_file_name = _next_available_file_names(
        ticker_dir, file_name, json_file_name
    )

    file_path = ticker_dir / file_name
    file_path.write_text(markdown, encoding="utf-8")
    json_path = ticker_dir / json_file_name

    if structured_payload is not None:
        json_path.write_text(
            json.dumps(structured_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    storage_info = ResearchStorageInfo(
        file_name=file_name,
        relative_path=file_path.relative_to(vault_dir.parent).as_posix(),
        absolute_path=str(file_path),
        json_file_name=json_file_name if structured_payload is not None else None,
        json_relative_path=(
            json_path.relative_to(vault_dir.parent).as_posix()
            if structured_payload is not None
            else None
        ),
        json_absolute_path=str(json_path) if structured_payload is not None else None,
    )

    if manifest_entry is not None:
        update_manifest(
            vault_dir=vault_dir,
            entry={
                **manifest_entry,
                "ticker": _safe_part(ticker.upper()),
                "type": _safe_part(report_type.lower()),
                "date": selected_date.isoformat(),
                "file_name": file_name,
                "relative_path": storage_info.relative_path,
                "json_file_name": storage_info.json_file_name,
                "json_relative_path": storage_info.json_relative_path,
            },
        )

    return storage_info


def read_manifest(vault_dir: Path) -> list[dict[str, Any]]:
    return _read_manifest(vault_dir)
