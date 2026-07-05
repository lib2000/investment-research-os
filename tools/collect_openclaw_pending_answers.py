from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_OPENCLAW_DIR = Path.home() / ".openclaw" / "workspace" / "data" / "investment_research"
DEFAULT_PENDING_DIR_NAME = "pending_actual_answers"
DEFAULT_PROCESSED_DIR_NAME = "processed_actual_answers"
DEFAULT_FAILED_DIR_NAME = "failed_actual_answers"
TOOLS_DIR = Path(__file__).resolve().parent
ROUTE_IDS = {
    "today_work_report",
    "recommendations_priority",
    "bridge_status_completion",
    "knowledge_graph_context",
}


def load_capture_tool():
    path = TOOLS_DIR / "capture_openclaw_actual_answer.py"
    spec = importlib.util.spec_from_file_location("capture_openclaw_actual_answer", path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load capture tool: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


capture_tool = load_capture_tool()


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


def answer_from_json(payload: dict[str, Any]) -> str:
    for key in ("answer", "text", "content", "response", "reply", "message"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    raise AssertionError("pending answer JSON must include one of: answer, text, content, response, reply, message")


def route_from_json(payload: dict[str, Any], fallback: str) -> str:
    for key in ("route_id", "route", "id", "question_id"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return fallback


def pending_record_from_file(path: Path) -> dict[str, Any] | None:
    suffix = path.suffix.lower()
    if suffix not in {".json", ".md", ".txt"}:
        return None
    fallback = route_from_filename(path)
    if suffix == ".json":
        payload = load_json(path)
        route_id = route_from_json(payload, fallback)
        answer = answer_from_json(payload)
    else:
        route_id = fallback
        answer = path.read_text(encoding="utf-8-sig")
    if route_id not in ROUTE_IDS:
        raise AssertionError(f"unknown route_id for pending answer {path.name}: {route_id}")
    if not answer.strip():
        raise AssertionError(f"pending answer is empty: {path}")
    return {"path": path, "route_id": route_id, "answer": answer}


def iter_pending_records(pending_dir: Path) -> list[dict[str, Any]]:
    if not pending_dir.exists():
        return []
    if not pending_dir.is_dir():
        raise AssertionError(f"pending path must be a directory: {pending_dir}")
    records: list[dict[str, Any]] = []
    for path in sorted(pending_dir.iterdir()):
        if not path.is_file():
            continue
        record = pending_record_from_file(path)
        if record:
            records.append(record)
    return records


def archive_path(target_dir: Path, source_path: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z")
    candidate = target_dir / f"{source_path.stem}.{stamp}{source_path.suffix}"
    index = 1
    while candidate.exists():
        candidate = target_dir / f"{source_path.stem}.{stamp}.{index}{source_path.suffix}"
        index += 1
    return candidate


def collect_pending_answers(
    openclaw_dir: Path = DEFAULT_OPENCLAW_DIR,
    *,
    pending_dir: Path | None = None,
    processed_dir: Path | None = None,
    failed_dir: Path | None = None,
    audit: bool = True,
    dry_run: bool = False,
    archive_failures: bool = False,
) -> dict[str, Any]:
    openclaw_dir = openclaw_dir.resolve()
    pending_dir = (pending_dir or (openclaw_dir / DEFAULT_PENDING_DIR_NAME)).resolve()
    processed_dir = (processed_dir or (openclaw_dir / DEFAULT_PROCESSED_DIR_NAME)).resolve()
    failed_dir = (failed_dir or (openclaw_dir / DEFAULT_FAILED_DIR_NAME)).resolve()
    records = iter_pending_records(pending_dir)
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    captured_count = 0
    failed_count = 0
    for record in records:
        path = Path(record["path"])
        item: dict[str, Any] = {
            "pending_file": str(path),
            "route_id": record["route_id"],
            "status": "dry_run" if dry_run else "pending",
        }
        try:
            if dry_run:
                item["answer_length"] = len(record["answer"])
            else:
                capture = capture_tool.build_result(
                    route_id=record["route_id"],
                    answer=record["answer"],
                    openclaw_dir=openclaw_dir,
                    source=f"pending_actual_answers:{path.name}",
                    audit=audit,
                )
                item["capture"] = capture
                if capture.get("status") != "ok":
                    raise AssertionError("; ".join(capture.get("errors") or ["capture failed"]))
                destination = archive_path(processed_dir, path)
                shutil.move(str(path), str(destination))
                item["status"] = "ok"
                item["processed_file"] = str(destination)
                item["output_file"] = capture.get("output_file")
                captured_count += 1
        except (AssertionError, OSError, json.JSONDecodeError) as exc:
            failed_count += 1
            item["status"] = "failure"
            item["errors"] = [str(exc)]
            errors.append(f"{path}: {exc}")
            if archive_failures and not dry_run and path.exists():
                destination = archive_path(failed_dir, path)
                shutil.move(str(path), str(destination))
                item["failed_file"] = str(destination)
        results.append(item)
    return {
        "status": "ok" if not errors else "failure",
        "errors": errors,
        "openclaw_dir": str(openclaw_dir),
        "pending_dir": str(pending_dir),
        "processed_dir": str(processed_dir),
        "failed_dir": str(failed_dir),
        "dry_run": dry_run,
        "audit": audit,
        "pending_count": len(records),
        "captured_count": captured_count,
        "failed_count": failed_count,
        "results": results,
    }


def render_text(result: dict[str, Any]) -> str:
    lines = [
        f"OpenClaw pending-answer collector: {result.get('status')}",
        f"- pending_dir: {result.get('pending_dir')}",
        f"- pending_count: {result.get('pending_count')}",
        f"- captured_count: {result.get('captured_count')}",
        f"- failed_count: {result.get('failed_count')}",
    ]
    for item in result.get("results") or []:
        lines.append(f"  - {item.get('route_id')}: {item.get('status')} | {item.get('pending_file')}")
    if result.get("errors"):
        lines.append("- errors:")
        for error in result["errors"]:
            lines.append(f"  - {error}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect pending OpenClaw answer files into audited captures.")
    parser.add_argument("--openclaw-dir", type=Path, default=DEFAULT_OPENCLAW_DIR)
    parser.add_argument("--pending-dir", type=Path)
    parser.add_argument("--processed-dir", type=Path)
    parser.add_argument("--failed-dir", type=Path)
    parser.add_argument("--no-audit", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--archive-failures", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = collect_pending_answers(
            args.openclaw_dir,
            pending_dir=args.pending_dir,
            processed_dir=args.processed_dir,
            failed_dir=args.failed_dir,
            audit=not args.no_audit,
            dry_run=args.dry_run,
            archive_failures=args.archive_failures,
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
