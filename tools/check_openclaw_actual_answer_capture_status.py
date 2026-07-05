from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_OPENCLAW_DIR = Path.home() / ".openclaw" / "workspace" / "data" / "investment_research"
DEFAULT_ANSWERS_DIR_NAME = "actual_answers"
DEFAULT_PENDING_DIR_NAME = "pending_actual_answers"
DEFAULT_MAX_AGE_HOURS = 24.0
ROUTE_IDS = {
    "today_work_report",
    "recommendations_priority",
    "bridge_status_completion",
    "knowledge_graph_context",
}


def route_from_filename(path: Path) -> str:
    stem = path.stem
    for route_id in ROUTE_IDS:
        if stem == route_id or stem.startswith(f"{route_id}.") or stem.startswith(f"{route_id}_"):
            return route_id
    return stem


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise AssertionError(f"JSON root must be an object: {path}")
    return payload


def parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.astimezone()
    return parsed


def record_from_file(path: Path) -> dict[str, Any] | None:
    suffix = path.suffix.lower()
    if suffix not in {".json", ".jsonl", ".md", ".txt"}:
        return None
    if suffix == ".json":
        payload = load_json(path)
        route_id = payload.get("route_id") or payload.get("route") or payload.get("id") or payload.get("question_id")
        captured_at = parse_datetime(payload.get("captured_at"))
        answer = payload.get("answer") or payload.get("text") or payload.get("content") or payload.get("response")
    elif suffix == ".jsonl":
        records = []
        for index, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise AssertionError(f"JSONL row must be object: {path}:{index}")
            route_id = payload.get("route_id") or payload.get("route") or payload.get("id") or payload.get("question_id")
            records.append(
                {
                    "path": f"{path}:{index}",
                    "route_id": route_id,
                    "captured_at": parse_datetime(payload.get("captured_at")),
                    "answer_length": len(str(payload.get("answer") or payload.get("text") or "")),
                }
            )
        if not records:
            return None
        return {"jsonl_records": records}
    else:
        route_id = route_from_filename(path)
        captured_at = None
        answer = path.read_text(encoding="utf-8-sig")
    return {
        "path": str(path),
        "route_id": route_id if isinstance(route_id, str) else None,
        "captured_at": captured_at,
        "answer_length": len(str(answer or "")),
    }


def iter_records(answers_dir: Path) -> list[dict[str, Any]]:
    if not answers_dir.exists():
        return []
    if not answers_dir.is_dir():
        raise AssertionError(f"answers path must be a directory: {answers_dir}")
    records: list[dict[str, Any]] = []
    for path in sorted(answers_dir.iterdir()):
        if not path.is_file():
            continue
        record = record_from_file(path)
        if not record:
            continue
        if "jsonl_records" in record:
            records.extend(record["jsonl_records"])
        else:
            records.append(record)
    return records


def summarize_pending_records(pending_dir: Path) -> dict[str, Any]:
    if not pending_dir.exists():
        return {
            "pending_dir": str(pending_dir),
            "pending_count": 0,
            "pending_route_counts": {},
            "pending_files": [],
        }
    if not pending_dir.is_dir():
        raise AssertionError(f"pending answers path must be a directory: {pending_dir}")
    pending_records: list[dict[str, Any]] = []
    for path in sorted(pending_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() not in {".json", ".md", ".txt"}:
            continue
        route_id = route_from_filename(path)
        if path.suffix.lower() == ".json":
            try:
                payload = load_json(path)
            except json.JSONDecodeError:
                payload = {}
            route_id = str(payload.get("route_id") or payload.get("route") or route_id)
        pending_records.append({"path": str(path), "route_id": route_id})
    route_counts: dict[str, int] = {}
    for record in pending_records:
        route_id = record.get("route_id")
        if route_id:
            route_counts[str(route_id)] = route_counts.get(str(route_id), 0) + 1
    return {
        "pending_dir": str(pending_dir),
        "pending_count": len(pending_records),
        "pending_route_counts": route_counts,
        "pending_files": pending_records[:10],
    }


def latest_record(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    dated = [record for record in records if isinstance(record.get("captured_at"), datetime)]
    if dated:
        return max(dated, key=lambda item: item["captured_at"])
    return records[-1] if records else None


def build_result(
    openclaw_dir: Path = DEFAULT_OPENCLAW_DIR,
    answers_dir: Path | None = None,
    pending_dir: Path | None = None,
    *,
    max_age_hours: float = DEFAULT_MAX_AGE_HOURS,
    require_recent: bool = False,
    require_pending_clear: bool = False,
    require_routes: list[str] | None = None,
) -> dict[str, Any]:
    openclaw_dir = openclaw_dir.resolve()
    answers_dir = (answers_dir or (openclaw_dir / DEFAULT_ANSWERS_DIR_NAME)).resolve()
    pending_dir = (pending_dir or (openclaw_dir / DEFAULT_PENDING_DIR_NAME)).resolve()
    records = iter_records(answers_dir)
    pending_summary = summarize_pending_records(pending_dir)
    now = datetime.now().astimezone()
    errors: list[str] = []
    route_counts: dict[str, int] = {}
    for record in records:
        route_id = record.get("route_id")
        if route_id:
            route_counts[str(route_id)] = route_counts.get(str(route_id), 0) + 1
    latest = latest_record(records)
    latest_age_hours = None
    latest_route_id = None
    latest_path = None
    if latest:
        latest_route_id = latest.get("route_id")
        latest_path = latest.get("path")
        captured_at = latest.get("captured_at")
        if isinstance(captured_at, datetime):
            latest_age_hours = round((now - captured_at.astimezone()).total_seconds() / 3600, 3)
    if require_recent and not records:
        errors.append(f"no actual answer captures found: {answers_dir}")
    if require_recent and latest_age_hours is None:
        errors.append("latest actual answer capture has no captured_at timestamp")
    if require_recent and latest_age_hours is not None and latest_age_hours > max_age_hours:
        errors.append(f"latest actual answer capture is stale: {latest_age_hours}h > {max_age_hours}h")
    if require_pending_clear and pending_summary["pending_count"] > 0:
        errors.append(f"pending actual answers waiting: {pending_summary['pending_count']}")
    for route_id in require_routes or []:
        if route_id not in ROUTE_IDS:
            errors.append(f"unknown required route_id: {route_id}")
        elif route_counts.get(route_id, 0) < 1:
            errors.append(f"missing actual answer capture for route: {route_id}")
    if pending_summary["pending_count"] > 0:
        capture_state = "pending_answers_waiting"
        capture_state_message = f"pending 답변 {pending_summary['pending_count']}건이 수집 대기 중입니다."
    elif not records:
        capture_state = "no_pending_answers"
        capture_state_message = "수집할 pending 답변이 없어 actual answer 0건은 정상 상태입니다."
    else:
        capture_state = "captured"
        capture_state_message = f"actual answer {len(records)}건이 저장되어 있습니다."
    return {
        "status": "ok" if not errors else "failure",
        "errors": errors,
        "openclaw_dir": str(openclaw_dir),
        "answers_dir": str(answers_dir),
        "pending_dir": pending_summary["pending_dir"],
        "capture_count": len(records),
        "pending_count": pending_summary["pending_count"],
        "pending_route_counts": pending_summary["pending_route_counts"],
        "pending_files": pending_summary["pending_files"],
        "needs_capture": pending_summary["pending_count"] > 0,
        "capture_state": capture_state,
        "capture_state_message": capture_state_message,
        "route_counts": route_counts,
        "latest_capture": {
            "path": latest_path,
            "route_id": latest_route_id,
            "age_hours": latest_age_hours,
        },
        "max_age_hours": max_age_hours,
        "require_recent": require_recent,
        "require_pending_clear": require_pending_clear,
        "required_routes": require_routes or [],
    }


def render_text(result: dict[str, Any]) -> str:
    latest = result.get("latest_capture") or {}
    lines = [
        f"OpenClaw actual-answer capture status: {result.get('status')}",
        f"- answers_dir: {result.get('answers_dir')}",
        f"- pending_dir: {result.get('pending_dir')}",
        f"- capture_count: {result.get('capture_count')}",
        f"- pending_count: {result.get('pending_count')}",
        f"- capture_state: {result.get('capture_state')}",
        f"- capture_state_message: {result.get('capture_state_message')}",
        f"- latest_route: {latest.get('route_id')}",
        f"- latest_age_hours: {latest.get('age_hours')}",
    ]
    if result.get("errors"):
        lines.append("- errors:")
        for error in result["errors"]:
            lines.append(f"  - {error}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check OpenClaw actual-answer capture freshness and route coverage.")
    parser.add_argument("--openclaw-dir", type=Path, default=DEFAULT_OPENCLAW_DIR)
    parser.add_argument("--answers-dir", type=Path)
    parser.add_argument("--pending-dir", type=Path)
    parser.add_argument("--max-age-hours", type=float, default=DEFAULT_MAX_AGE_HOURS)
    parser.add_argument("--require-recent", action="store_true")
    parser.add_argument("--require-pending-clear", action="store_true")
    parser.add_argument("--require-route", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = build_result(
            args.openclaw_dir,
            args.answers_dir,
            args.pending_dir,
            max_age_hours=args.max_age_hours,
            require_recent=args.require_recent,
            require_pending_clear=args.require_pending_clear,
            require_routes=args.require_route,
        )
    except (AssertionError, OSError, json.JSONDecodeError) as exc:
        result = {"status": "failure", "errors": [str(exc)], "openclaw_dir": str(args.openclaw_dir.resolve())}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
