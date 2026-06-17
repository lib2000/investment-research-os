"""Utility helpers for RAG memory records."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def json_load_list(value: str | None) -> list[Any]:
    if not value:
        return []
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return []
    return payload if isinstance(payload, list) else []


def json_load_dict(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def safe_text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    return str(value).strip()


def safe_float(value: Any, fallback: float = 0.7) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return fallback


def document_id_from_entry(entry: dict[str, Any]) -> str:
    relative_path = safe_text(entry.get("relative_path"))
    if relative_path:
        return relative_path
    return "|".join(
        [
            safe_text(entry.get("ticker"), "UNKNOWN"),
            safe_text(entry.get("type") or entry.get("report_type"), "unknown"),
            safe_text(entry.get("date"), "undated"),
            safe_text(entry.get("file_name"), "missing-file"),
        ]
    )


def resolve_manifest_file(vault_dir: Path, relative_path: str | None) -> Path | None:
    if not relative_path:
        return None
    candidate = (vault_dir.parent / relative_path).resolve()
    try:
        candidate.relative_to(vault_dir.parent.resolve())
    except ValueError:
        return None
    return candidate


def read_manifest_text(
    vault_dir: Path,
    entry: dict[str, Any],
    max_chars: int = 12000,
) -> str:
    path = resolve_manifest_file(vault_dir, entry.get("relative_path"))
    if path and path.exists() and path.is_file():
        try:
            return path.read_text(encoding="utf-8")[:max_chars]
        except OSError:
            pass
    return safe_text(entry.get("summary") or entry.get("title") or "")


def entry_tags(entry: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    for key in ("tags", "theme_tags", "categories"):
        value = entry.get(key)
        if isinstance(value, list):
            tags.extend(safe_text(item) for item in value if safe_text(item))
    for key in ("type", "report_type", "source_type"):
        value = safe_text(entry.get(key))
        if value:
            tags.append(value)
    return sorted(set(tags))


def document_quality(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = json_load_dict(payload.get("metadata_json"))

    text = " ".join(
        [
            safe_text(payload.get("summary")),
            safe_text(payload.get("content_excerpt")),
            safe_text(metadata.get("reaction_type")),
            safe_text(metadata.get("evidence_status")),
        ]
    )
    flags: list[str] = []
    score = int(round(safe_float(payload.get("confidence"), 0.7) * 100))

    if metadata.get("data_quality") == "low":
        score -= 10
        flags.append("low_data_quality")

    missing_inputs = metadata.get("missing_inputs")
    if isinstance(missing_inputs, list) and missing_inputs:
        score -= min(25, 8 * len(missing_inputs))
        flags.append("missing_inputs")

    if "입력 데이터가 부족" in text or "데이터 부족" in text:
        score -= 35
        flags.append("insufficient_data")

    if "판정 보류" in text:
        score -= 20
        flags.append("deferred_judgement")

    if metadata.get("evidence_status") == "충분":
        score += 25
        flags.append("sufficient_evidence")

    if metadata.get("is_deleted") or safe_text(metadata.get("status")).lower() == "archived":
        score -= 80
        flags.append("archived")

    report_type = safe_text(payload.get("report_type"))
    if report_type == "earnings-reaction":
        if metadata.get("earnings_report_date"):
            score += 8
        else:
            score -= 15
            flags.append("missing_earnings_date")
        if safe_text(metadata.get("price_reaction")):
            score += 8
        else:
            score -= 10
            flags.append("missing_price_reaction")
        if safe_text(metadata.get("next_earnings_guidance")) and "입력되지 않았습니다" not in safe_text(
            metadata.get("next_earnings_guidance")
        ):
            score += 8
        else:
            score -= 10
            flags.append("missing_next_guidance")

    return {
        "quality_score": max(0, min(150, score)),
        "quality_flags": sorted(set(flags)),
        "is_injectable": score >= 55 and "insufficient_data" not in flags and "archived" not in flags,
    }
