"""Safely soft-archive byte-identical duplicate DART filing captures."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from research_os.rag_memory import (
    delete_research_memory_documents_by_relative_paths,
    upsert_research_memory_document,
)
from research_os.research_memory import read_manifest, update_manifest
from research_os.storage_quality import is_archived_research_entry


DART_REPORT_TYPE = "dart-filing-watch"
ARCHIVE_REASON = "동일한 DART 접수번호와 내용의 중복 저장본이라 삭제하지 않고 소프트 보관 처리했습니다."


@dataclass(frozen=True)
class DartFilingStoredItem:
    ticker: str
    receipt_no: str
    receipt_date: str
    report_name: str
    source_url: str
    md_path: Path
    json_path: Path
    relative_path: str
    json_relative_path: str
    content_hash: str
    manifest_entry: dict[str, Any] | None


def _normalize_relative_path(value: object) -> str:
    return str(value or "").replace("\\", "/").strip()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _write_bytes_atomically(path, json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))


def _write_bytes_atomically(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("wb") as file:
            file.write(payload)
            file.flush()
            os.fsync(file.fileno())
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink(missing_ok=True)


def _copy_json_atomically(source: Path, destination: Path) -> None:
    _write_bytes_atomically(destination, source.read_bytes())


def _hash_pair(markdown_path: Path, json_path: Path) -> str:
    digest = sha256()
    digest.update(markdown_path.read_bytes())
    digest.update(b"\x00")
    digest.update(json_path.read_bytes())
    return digest.hexdigest()


def _payload_without_filing_remark(item: DartFilingStoredItem) -> tuple[dict[str, Any], str] | None:
    """Return comparable filing metadata and the raw DART remark value."""
    payload = _read_json(item.json_path)
    filing = payload.get("filing")
    if not isinstance(filing, dict) or not isinstance(filing.get("remark"), str):
        return None
    comparable = json.loads(json.dumps(payload, ensure_ascii=False))
    comparable_filing = comparable.get("filing")
    if not isinstance(comparable_filing, dict):
        return None
    remark = str(comparable_filing.pop("remark"))
    return comparable, remark


def _build_remark_prefix_refinement(
    canonical: DartFilingStoredItem,
    conflicting: list[DartFilingStoredItem],
) -> dict[str, Any] | None:
    """Recognize one narrowly safe DART metadata refinement.

    Some historic captures split the DART market/filing marker across runs
    (for example ``코`` then ``코정``), while the official filing body and every
    other field stay unchanged. This is not an alternate filing. It is safe to
    reuse the more complete duplicate JSON only when all duplicate JSON bytes
    are identical and their sole semantic difference is a strict remark prefix
    extension. Any other difference remains a human-review case.
    """
    if not conflicting:
        return None
    try:
        canonical_markdown = canonical.md_path.read_bytes()
        if any(item.md_path.read_bytes() != canonical_markdown for item in conflicting):
            return None
        duplicate_json = conflicting[0].json_path.read_bytes()
        if any(item.json_path.read_bytes() != duplicate_json for item in conflicting):
            return None
    except OSError:
        return None

    canonical_value = _payload_without_filing_remark(canonical)
    if canonical_value is None:
        return None
    canonical_payload, canonical_remark = canonical_value
    duplicate_values = [_payload_without_filing_remark(item) for item in conflicting]
    if any(value is None for value in duplicate_values):
        return None
    comparable_payloads = [value[0] for value in duplicate_values if value is not None]
    duplicate_remarks = {value[1] for value in duplicate_values if value is not None}
    if any(payload != canonical_payload for payload in comparable_payloads) or len(duplicate_remarks) != 1:
        return None

    source_value = canonical_remark.strip()
    target_value = next(iter(duplicate_remarks)).strip()
    if not source_value or len(target_value) <= len(source_value) or not target_value.startswith(source_value):
        return None
    source = conflicting[0]
    return {
        "kind": "filing_remark_strict_prefix_refinement",
        "field": "filing.remark",
        "from_value": canonical_remark,
        "to_value": next(iter(duplicate_remarks)),
        "source_json_relative_path": source.json_relative_path,
        "source_relative_path": source.relative_path,
        "verification": "same_markdown_and_all_metadata_except_filing_remark",
    }


def _receipt_date_iso(receipt_date: str) -> str | None:
    value = str(receipt_date or "").strip()
    if len(value) != 8 or not value.isdigit():
        return None
    return f"{value[:4]}-{value[4:6]}-{value[6:]}"


def _canonical_file_names(ticker: str, receipt_no: str, receipt_date: str) -> tuple[str, str] | None:
    receipt_date_iso = _receipt_date_iso(receipt_date)
    if not receipt_date_iso or not receipt_no:
        return None
    stem = f"{ticker}-dart-filing-watch-{receipt_date_iso}-{receipt_no}"
    return f"{stem}.md", f"{stem}.json"


def _manifest_maps(manifest: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    by_relative_path: dict[str, dict[str, Any]] = {}
    by_ticker_file_name: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in manifest:
        if not isinstance(entry, dict):
            continue
        relative_path = _normalize_relative_path(entry.get("relative_path"))
        if relative_path:
            by_relative_path[relative_path] = entry
        ticker = str(entry.get("ticker") or "").upper().strip()
        file_name = str(entry.get("file_name") or "").strip()
        if ticker and file_name:
            by_ticker_file_name[(ticker, file_name)] = entry
    return by_relative_path, by_ticker_file_name


def recent_dart_manifest_tickers(
    vault_dir: Path,
    *,
    hours: float,
    max_tickers: int | None = None,
) -> set[str]:
    """Return active DART tickers whose manifest-backed source changed recently.

    This keeps the scheduled maintenance bounded even when a long-lived vault
    contains years of historic DART captures. A fresh forced capture updates
    its canonical file's mtime, so its ticker is included on the next run.
    """
    cutoff = datetime.now().astimezone().timestamp() - max(float(hours), 0.0) * 3600
    root = vault_dir.parent
    latest_mtime_by_ticker: dict[str, float] = {}
    for entry in read_manifest(vault_dir):
        if not isinstance(entry, dict) or is_archived_research_entry(entry):
            continue
        if str(entry.get("type") or "") != DART_REPORT_TYPE and str(entry.get("module") or "") != "dart_filing_watch":
            continue
        relative_path = _normalize_relative_path(entry.get("relative_path"))
        if not relative_path:
            continue
        try:
            modified_at = (root / relative_path).stat().st_mtime
            if modified_at >= cutoff:
                ticker = str(entry.get("ticker") or "").upper().strip()
                if ticker:
                    latest_mtime_by_ticker[ticker] = max(latest_mtime_by_ticker.get(ticker, 0.0), modified_at)
        except OSError:
            continue
    ordered = sorted(latest_mtime_by_ticker.items(), key=lambda item: (-item[1], item[0]))
    if max_tickers is not None:
        ordered = ordered[: max(int(max_tickers), 0)]
    return {ticker for ticker, _modified_at in ordered}


def collect_active_dart_filing_items(vault_dir: Path, tickers: set[str] | None = None) -> list[DartFilingStoredItem]:
    """Collect only active, paired DART storage items with a stable receipt number."""
    manifest = read_manifest(vault_dir)
    by_relative_path, by_ticker_file_name = _manifest_maps(manifest)
    has_ticker_scope = tickers is not None
    selected_tickers = {str(ticker).upper().strip() for ticker in (tickers or set()) if str(ticker).strip()}
    root = vault_dir.parent
    items: list[DartFilingStoredItem] = []
    if has_ticker_scope:
        json_paths = (
            json_path
            for ticker in sorted(selected_tickers)
            for json_path in sorted((vault_dir / ticker).glob("*dart-filing-watch*.json"))
            if (vault_dir / ticker).is_dir()
        )
    else:
        json_paths = iter(sorted(vault_dir.glob("*/*dart-filing-watch*.json")))
    for json_path in json_paths:
        markdown_path = json_path.with_suffix(".md")
        if not markdown_path.exists():
            continue
        payload = _read_json(json_path)
        if str(payload.get("module") or "") != "dart_filing_watch":
            continue
        if is_archived_research_entry(None, payload):
            continue
        filing = payload.get("filing") if isinstance(payload.get("filing"), dict) else {}
        ticker = str(payload.get("ticker") or json_path.parent.name).upper().strip()
        if ticker != json_path.parent.name.upper():
            continue
        if selected_tickers and ticker not in selected_tickers:
            continue
        receipt_no = str(filing.get("rcept_no") or "").strip()
        receipt_date = str(filing.get("receipt_date") or "").strip()
        if not receipt_no or not _receipt_date_iso(receipt_date):
            continue
        relative_path = _normalize_relative_path(markdown_path.relative_to(root).as_posix())
        json_relative_path = _normalize_relative_path(json_path.relative_to(root).as_posix())
        manifest_entry = by_relative_path.get(relative_path) or by_ticker_file_name.get((ticker, markdown_path.name))
        items.append(
            DartFilingStoredItem(
                ticker=ticker,
                receipt_no=receipt_no,
                receipt_date=receipt_date,
                report_name=str(filing.get("report_name") or "").strip(),
                source_url=str(filing.get("source_url") or "").strip(),
                md_path=markdown_path,
                json_path=json_path,
                relative_path=relative_path,
                json_relative_path=json_relative_path,
                content_hash=_hash_pair(markdown_path, json_path),
                manifest_entry=manifest_entry,
            )
        )
    return items


def _serialize_item(item: DartFilingStoredItem) -> dict[str, Any]:
    return {
        "ticker": item.ticker,
        "rcept_no": item.receipt_no,
        "receipt_date": item.receipt_date,
        "report_name": item.report_name,
        "source_url": item.source_url,
        "file_name": item.md_path.name,
        "json_file_name": item.json_path.name,
        "relative_path": item.relative_path,
        "json_relative_path": item.json_relative_path,
        "content_hash": item.content_hash,
        "in_manifest": bool(item.manifest_entry),
    }


def _canonical_item(items: list[DartFilingStoredItem]) -> DartFilingStoredItem | None:
    if not items:
        return None
    expected = _canonical_file_names(items[0].ticker, items[0].receipt_no, items[0].receipt_date)
    if not expected:
        return None
    expected_markdown, expected_json = expected
    return next(
        (
            item
            for item in items
            if item.md_path.name == expected_markdown and item.json_path.name == expected_json
        ),
        None,
    )


def build_dart_filing_duplicate_cleanup_plan(
    vault_dir: Path,
    *,
    tickers: set[str] | None = None,
) -> dict[str, Any]:
    """Build a no-write plan; only byte-identical copies with a canonical source qualify."""
    items = collect_active_dart_filing_items(vault_dir, tickers=tickers)
    groups: dict[tuple[str, str], list[DartFilingStoredItem]] = {}
    for item in items:
        groups.setdefault((item.ticker, item.receipt_no), []).append(item)

    actionable_groups: list[dict[str, Any]] = []
    skipped_groups: list[dict[str, Any]] = []
    candidate_count = 0
    for (ticker, receipt_no), group_items in sorted(groups.items()):
        if len(group_items) <= 1:
            continue
        canonical = _canonical_item(group_items)
        if canonical is None:
            skipped_groups.append(
                {
                    "ticker": ticker,
                    "rcept_no": receipt_no,
                    "reason": "canonical_file_missing",
                    "items": [_serialize_item(item) for item in group_items],
                }
            )
            continue
        identical = [item for item in group_items if item != canonical and item.content_hash == canonical.content_hash]
        conflicting = [item for item in group_items if item != canonical and item.content_hash != canonical.content_hash]
        if conflicting:
            # A raw-pair mismatch normally remains review-only. The one
            # exception is a fully verified DART ``filing.remark`` prefix
            # refinement; keep this deliberately narrower than a generic
            # metadata merge.
            refinement = _build_remark_prefix_refinement(canonical, conflicting) if not identical else None
            if refinement is not None:
                candidate_count += len(conflicting)
                actionable_groups.append(
                    {
                        "ticker": ticker,
                        "rcept_no": receipt_no,
                        "canonical": _serialize_item(canonical),
                        "duplicates": [_serialize_item(item) for item in conflicting],
                        "metadata_refinement": refinement,
                    }
                )
                continue
            skipped_groups.append(
                {
                    "ticker": ticker,
                    "rcept_no": receipt_no,
                    "reason": "content_hash_mismatch",
                    "canonical": _serialize_item(canonical),
                    "conflicting_items": [_serialize_item(item) for item in conflicting],
                    "identical_candidate_count": len(identical),
                }
            )
            continue
        if not identical:
            continue
        candidate_count += len(identical)
        actionable_groups.append(
            {
                "ticker": ticker,
                "rcept_no": receipt_no,
                "canonical": _serialize_item(canonical),
                "duplicates": [_serialize_item(item) for item in identical],
            }
        )

    return {
        "status": "success",
        "module": "dart_filing_duplicate_cleanup",
        "policy": "soft_archive_only",
        "hard_delete_allowed": False,
        "scanned_active_file_pair_count": len(items),
        "duplicate_group_count": len(actionable_groups),
        "duplicate_candidate_count": candidate_count,
        "skipped_group_count": len(skipped_groups),
        "groups": actionable_groups,
        "skipped_groups": skipped_groups,
    }


def _build_canonical_manifest_entry(
    item: DartFilingStoredItem,
    now: str,
    source_entry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source = dict(source_entry or item.manifest_entry or {})
    tags = [tag for tag in (source.get("tags") or []) if str(tag).lower() != "archived"]
    date_value = _receipt_date_iso(item.receipt_date) or source.get("date")
    summary = source.get("summary") or f"{item.ticker} DART 신규 공시: {item.report_name or '공시명 미확인'}"
    return {
        **source,
        "ticker": item.ticker,
        "type": DART_REPORT_TYPE,
        "date": date_value,
        "file_name": item.md_path.name,
        "relative_path": item.relative_path,
        "json_file_name": item.json_path.name,
        "json_relative_path": item.json_relative_path,
        "module": "dart_filing_watch",
        "summary": summary,
        "source_type": source.get("source_type") or "official_filing",
        "source_url": source.get("source_url") or item.source_url,
        "rcept_no": source.get("rcept_no") or item.receipt_no,
        "confidence": source.get("confidence") or 0.96,
        "tags": list(dict.fromkeys(tags)),
        "status": "active",
        "is_deleted": False,
        "archived_at": None,
        "archive_reason": None,
        "updated_at": now,
    }


def _build_archived_manifest_entry(entry: dict[str, Any], now: str) -> dict[str, Any]:
    tags = list(dict.fromkeys([*(entry.get("tags") or []), "archived"]))
    return {
        **entry,
        "status": "archived",
        "is_deleted": True,
        "archived_at": now,
        "archive_reason": ARCHIVE_REASON,
        "updated_at": now,
        "tags": tags,
    }


def _find_item_by_relative_path(items: list[DartFilingStoredItem], relative_path: str) -> DartFilingStoredItem | None:
    normalized = _normalize_relative_path(relative_path)
    return next((item for item in items if item.relative_path == normalized), None)


def apply_dart_filing_duplicate_cleanup(vault_dir: Path, plan: dict[str, Any]) -> dict[str, Any]:
    """Archive approved duplicates without deleting source files or calling external services."""
    plan_tickers = {
        str(group.get("ticker") or "").upper().strip()
        for group in (plan.get("groups") or [])
        if isinstance(group, dict) and str(group.get("ticker") or "").strip()
    }
    # Never expand a targeted/recency-bounded plan back into a full historical vault scan.
    current_items = collect_active_dart_filing_items(vault_dir, tickers=plan_tickers)
    now = datetime.now().astimezone().replace(microsecond=0).isoformat()
    archived: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    rag_deleted_count = 0
    canonical_count = 0
    metadata_refinement_count = 0

    for group in plan.get("groups", []):
        canonical = _find_item_by_relative_path(current_items, str((group.get("canonical") or {}).get("relative_path") or ""))
        duplicates = [
            _find_item_by_relative_path(current_items, str(item.get("relative_path") or ""))
            for item in (group.get("duplicates") or [])
            if isinstance(item, dict)
        ]
        duplicates = [item for item in duplicates if item is not None]
        if canonical is None or not duplicates:
            errors.append(
                {
                    "ticker": group.get("ticker"),
                    "rcept_no": group.get("rcept_no"),
                    "error": "cleanup_plan_is_stale_or_incomplete",
                }
            )
            continue
        refinement = group.get("metadata_refinement")
        if isinstance(refinement, dict):
            source_json_relative_path = _normalize_relative_path(refinement.get("source_json_relative_path"))
            source = next((item for item in duplicates if item.json_relative_path == source_json_relative_path), None)
            rechecked = _build_remark_prefix_refinement(canonical, duplicates)
            if (
                source is None
                or rechecked is None
                or rechecked.get("from_value") != refinement.get("from_value")
                or rechecked.get("to_value") != refinement.get("to_value")
                or rechecked.get("source_json_relative_path") != source_json_relative_path
            ):
                errors.append(
                    {
                        "ticker": canonical.ticker,
                        "rcept_no": canonical.receipt_no,
                        "error": "metadata_refinement_no_longer_safe",
                    }
                )
                continue
            _copy_json_atomically(source.json_path, canonical.json_path)
            metadata_refinement_count += 1

        canonical_hash = _hash_pair(canonical.md_path, canonical.json_path)
        if any(_hash_pair(item.md_path, item.json_path) != canonical_hash for item in duplicates):
            errors.append(
                {
                    "ticker": canonical.ticker,
                    "rcept_no": canonical.receipt_no,
                    "error": "content_hash_changed_since_plan",
                }
            )
            continue

        try:
            # Historic sequence copies may be the only manifest-backed row.
            # Reuse that verified metadata while moving the active reference to
            # the stable, unsuffixed canonical source file.
            manifest_source = canonical.manifest_entry or next(
                (item.manifest_entry for item in duplicates if item.manifest_entry),
                None,
            )
            canonical_entry = _build_canonical_manifest_entry(canonical, now, manifest_source)
            upsert_research_memory_document(
                vault_dir=vault_dir,
                entry=canonical_entry,
                full_text=canonical.md_path.read_text(encoding="utf-8"),
            )
            rag_result = delete_research_memory_documents_by_relative_paths(
                vault_dir=vault_dir,
                relative_paths=[item.relative_path for item in duplicates],
            )
            rag_deleted_count += int(rag_result.get("deleted_count") or 0)

            update_manifest(vault_dir=vault_dir, entry=canonical_entry)
            canonical_count += 1
            for duplicate in duplicates:
                payload = _read_json(duplicate.json_path)
                payload.update(
                    {
                        "status": "archived",
                        "is_deleted": True,
                        "archived_at": now,
                        "archive_reason": ARCHIVE_REASON,
                        "updated_at": now,
                    }
                )
                _write_json(duplicate.json_path, payload)
                if duplicate.manifest_entry:
                    update_manifest(
                        vault_dir=vault_dir,
                        entry=_build_archived_manifest_entry(duplicate.manifest_entry, now),
                    )
                archived.append(
                    {
                        "ticker": duplicate.ticker,
                        "rcept_no": duplicate.receipt_no,
                        "relative_path": duplicate.relative_path,
                        "json_relative_path": duplicate.json_relative_path,
                        "archived_at": now,
                    }
                )
        except Exception as exc:  # Keep other independent filing groups auditable.
            errors.append(
                {
                    "ticker": canonical.ticker,
                    "rcept_no": canonical.receipt_no,
                    "error": str(exc),
                }
            )

    return {
        **plan,
        "applied": True,
        "canonical_upsert_count": canonical_count,
        "metadata_refinement_count": metadata_refinement_count,
        "archived_count": len(archived),
        "archived_files": archived,
        "rag_deleted_count": rag_deleted_count,
        "errors": errors,
        "status": "success" if not errors else "partial_success",
    }


def write_dart_filing_duplicate_cleanup_state(vault_dir: Path, result: dict[str, Any]) -> Path:
    path = vault_dir / "_system" / "dart_filing_duplicate_cleanup.json"
    _write_json(path, result)
    return path
