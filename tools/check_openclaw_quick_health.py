from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OPENCLAW_DIR = Path.home() / ".openclaw" / "workspace" / "data" / "investment_research"
EXPECTED_HASH_COUNT = 14
CHECK_MODULES = {
    "status_summary": PROJECT_ROOT / "tools" / "show_openclaw_bridge_status.py",
    "context_bundle": PROJECT_ROOT / "tools" / "check_openclaw_investment_context.py",
    "completion_audit": PROJECT_ROOT / "tools" / "check_openclaw_bridge_completion.py",
    "consumer_smoke": PROJECT_ROOT / "tools" / "check_openclaw_consumer_smoke.py",
    "question_read_order": PROJECT_ROOT / "tools" / "check_openclaw_question_read_order.py",
    "today_answer": PROJECT_ROOT / "tools" / "check_openclaw_today_answer_readiness.py",
    "today_answer_quality": PROJECT_ROOT / "tools" / "check_openclaw_today_answer_quality.py",
    "priority_answer_quality": PROJECT_ROOT / "tools" / "check_openclaw_priority_answer_quality.py",
    "answer_samples": PROJECT_ROOT / "tools" / "check_openclaw_answer_samples.py",
    "actual_answer_audit": PROJECT_ROOT / "tools" / "check_openclaw_actual_answer_audit.py",
    "answer_capture_cycle": PROJECT_ROOT / "tools" / "check_openclaw_answer_capture_cycle.py",
    "answer_capture_task": PROJECT_ROOT / "tools" / "check_openclaw_answer_capture_task_status.py",
    "actual_answer_capture_status": PROJECT_ROOT / "tools" / "check_openclaw_actual_answer_capture_status.py",
}


def load_tool(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load OpenClaw quick health module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_status_summary(openclaw_dir: Path) -> dict[str, Any]:
    module = load_tool("show_openclaw_bridge_status", CHECK_MODULES["status_summary"])
    summary = module.build_status_summary(openclaw_dir)
    errors = list(summary.get("errors") or [])
    if summary.get("status") != "ok":
        errors.append(f"status summary is not ok: {summary.get('status')}")
    if summary.get("hash_status") != "ok":
        errors.append(f"status summary hashes are not ok: {summary.get('hash_status')}")
    if int(summary.get("hash_checked_count") or 0) != EXPECTED_HASH_COUNT:
        errors.append(f"status summary hash count mismatch: {summary.get('hash_checked_count')} != {EXPECTED_HASH_COUNT}")
    if summary.get("hash_mismatches"):
        errors.append(f"status summary hash mismatches: {summary.get('hash_mismatches')}")
    return {
        "label": "status_summary",
        "status": "ok" if not errors else "failure",
        "errors": errors,
        "summary": {
            "hash_status": summary.get("hash_status"),
            "hash_checked_count": summary.get("hash_checked_count"),
            "source_git": summary.get("source_git"),
            "latest_recommendation_date": summary.get("latest_recommendation_date"),
            "latest_market_counts": summary.get("latest_market_counts"),
            "telegram_saved_count": summary.get("telegram_saved_count"),
        },
    }


def check_context_bundle(openclaw_dir: Path, *, max_age_hours: float) -> dict[str, Any]:
    module = load_tool("check_openclaw_investment_context", CHECK_MODULES["context_bundle"])
    try:
        messages = module.validate_bundle(openclaw_dir, max_age_hours=max_age_hours)
    except AssertionError as exc:
        return {"label": "context_bundle", "status": "failure", "errors": [str(exc)], "summary": {}}
    return {"label": "context_bundle", "status": "ok", "errors": [], "summary": {"messages": messages}}


def check_completion_audit(
    project_root: Path,
    openclaw_dir: Path,
    *,
    max_age_hours: float,
) -> dict[str, Any]:
    module = load_tool("check_openclaw_bridge_completion", CHECK_MODULES["completion_audit"])
    result = module.build_result(
        project_root=project_root,
        openclaw_dir=openclaw_dir,
        max_age_hours=max_age_hours,
        require_report_hashes=True,
    )
    return {
        "label": "completion_audit",
        "status": result.get("status"),
        "errors": list(result.get("errors") or []),
        "summary": {
            "git": result.get("git"),
            "bridge_status": result.get("bridge_status"),
            "openclaw_workspace": result.get("openclaw_workspace"),
        },
    }


def check_consumer_smoke(
    openclaw_dir: Path,
    *,
    max_age_hours: float,
    expected_latest_count: int,
) -> dict[str, Any]:
    module = load_tool("check_openclaw_consumer_smoke", CHECK_MODULES["consumer_smoke"])
    result = module.build_result(
        openclaw_dir,
        max_age_hours=max_age_hours,
        expected_latest_count=expected_latest_count,
    )
    return {
        "label": "consumer_smoke",
        "status": result.get("status"),
        "errors": list(result.get("errors") or []),
        "summary": {
            "loaded_files": result.get("loaded_files"),
            "latest_recommendation_count": result.get("latest_recommendation_count"),
            "hash_checked_count": result.get("hash_checked_count"),
        },
    }


def check_question_read_order(openclaw_dir: Path) -> dict[str, Any]:
    module = load_tool("check_openclaw_question_read_order", CHECK_MODULES["question_read_order"])
    try:
        result = module.build_result(openclaw_dir)
    except AssertionError as exc:
        return {"label": "question_read_order", "status": "failure", "errors": [str(exc)], "summary": {}}
    return {
        "label": "question_read_order",
        "status": result.get("status"),
        "errors": list(result.get("errors") or []),
        "summary": {
            "route_count": result.get("route_count"),
            "first_read_declared_route_count": result.get("first_read_declared_route_count"),
        },
    }


def check_today_answer(openclaw_dir: Path) -> dict[str, Any]:
    module = load_tool("check_openclaw_today_answer_readiness", CHECK_MODULES["today_answer"])
    try:
        result = module.build_result(openclaw_dir)
    except AssertionError as exc:
        return {"label": "today_answer", "status": "failure", "errors": [str(exc)], "summary": {}}
    return {
        "label": "today_answer",
        "status": result.get("status"),
        "errors": list(result.get("errors") or []),
        "summary": {
            "today_commit_count": result.get("today_commit_count"),
            "next_schedule_count": result.get("next_schedule_count"),
            "today_categories": result.get("today_categories"),
        },
    }


def check_today_answer_quality(openclaw_dir: Path) -> dict[str, Any]:
    module = load_tool("check_openclaw_today_answer_quality", CHECK_MODULES["today_answer_quality"])
    try:
        result = module.build_result(openclaw_dir)
    except AssertionError as exc:
        return {"label": "today_answer_quality", "status": "failure", "errors": [str(exc)], "summary": {}}
    return {
        "label": "today_answer_quality",
        "status": result.get("status"),
        "errors": list(result.get("errors") or []),
        "summary": {
            "today_commit_count": result.get("today_commit_count"),
            "next_schedule_count": result.get("next_schedule_count"),
            "answer_source": result.get("answer_source"),
        },
    }


def check_priority_answer_quality(openclaw_dir: Path) -> dict[str, Any]:
    module = load_tool("check_openclaw_priority_answer_quality", CHECK_MODULES["priority_answer_quality"])
    try:
        result = module.build_result(openclaw_dir)
    except AssertionError as exc:
        return {"label": "priority_answer_quality", "status": "failure", "errors": [str(exc)], "summary": {}}
    return {
        "label": "priority_answer_quality",
        "status": result.get("status"),
        "errors": list(result.get("errors") or []),
        "summary": {
            "recommendation_count": result.get("recommendation_count"),
            "latest_market_counts": result.get("latest_market_counts"),
            "telegram_saved_count": result.get("telegram_saved_count"),
            "answer_source": result.get("answer_source"),
        },
    }


def check_answer_samples(openclaw_dir: Path) -> dict[str, Any]:
    module = load_tool("check_openclaw_answer_samples", CHECK_MODULES["answer_samples"])
    try:
        result = module.build_result(openclaw_dir)
    except AssertionError as exc:
        return {"label": "answer_samples", "status": "failure", "errors": [str(exc)], "summary": {}}
    return {
        "label": "answer_samples",
        "status": result.get("status"),
        "errors": list(result.get("errors") or []),
        "summary": {
            "sample_count": result.get("sample_count"),
            "generated_at": result.get("generated_at"),
        },
    }


def check_actual_answer_audit(openclaw_dir: Path) -> dict[str, Any]:
    module = load_tool("check_openclaw_actual_answer_audit", CHECK_MODULES["actual_answer_audit"])
    try:
        result = module.build_result(openclaw_dir)
    except AssertionError as exc:
        return {"label": "actual_answer_audit", "status": "failure", "errors": [str(exc)], "summary": {}}
    return {
        "label": "actual_answer_audit",
        "status": result.get("status"),
        "errors": list(result.get("errors") or []),
        "summary": {
            "audited_count": result.get("audited_count"),
            "answers_dir": result.get("answers_dir"),
        },
    }


def check_answer_capture_cycle(openclaw_dir: Path) -> dict[str, Any]:
    module = load_tool("check_openclaw_answer_capture_cycle", CHECK_MODULES["answer_capture_cycle"])
    try:
        result = module.build_result(openclaw_dir, collect=False)
    except AssertionError as exc:
        return {"label": "answer_capture_cycle", "status": "failure", "errors": [str(exc)], "summary": {}}
    collector = result.get("collector") or {}
    capture_status = result.get("capture_status") or {}
    return {
        "label": "answer_capture_cycle",
        "status": result.get("status"),
        "errors": list(result.get("errors") or []),
        "summary": {
            "pending_count": collector.get("pending_count"),
            "captured_count": collector.get("captured_count"),
            "failed_count": collector.get("failed_count"),
            "total_capture_count": capture_status.get("capture_count"),
            "collect": result.get("collect"),
        },
    }


def check_answer_capture_task(project_root: Path) -> dict[str, Any]:
    module = load_tool("check_openclaw_answer_capture_task_status", CHECK_MODULES["answer_capture_task"])
    state_file = project_root / "research_vault" / "_system" / "openclaw_answer_capture_cycle_state.json"
    try:
        result = module.evaluate_task_status(
            module.read_scheduled_task(module.DEFAULT_TASK_NAME),
            state_file=state_file,
            max_state_age_hours=24.0,
            require_state_fresh=False,
        )
    except (AssertionError, OSError, ValueError) as exc:
        return {"label": "answer_capture_task", "status": "failure", "errors": [str(exc)], "summary": {}}
    task = result.get("task") or {}
    return {
        "label": "answer_capture_task",
        "status": result.get("status"),
        "errors": list(result.get("errors") or []),
        "summary": {
            "task_name": task.get("TaskName"),
            "next_run": task.get("NextRunTime"),
            "last_run": task.get("LastRunTime"),
            "last_result": task.get("LastTaskResult"),
            "repetition_interval": task.get("RepetitionInterval"),
            "state_file_exists": result.get("state_file_exists"),
            "state_file_age_hours": result.get("state_file_age_hours"),
            "warnings": result.get("warnings") or [],
        },
    }


def check_actual_answer_capture_status(openclaw_dir: Path) -> dict[str, Any]:
    module = load_tool(
        "check_openclaw_actual_answer_capture_status",
        CHECK_MODULES["actual_answer_capture_status"],
    )
    try:
        result = module.build_result(openclaw_dir)
    except AssertionError as exc:
        return {"label": "actual_answer_capture_status", "status": "failure", "errors": [str(exc)], "summary": {}}
    return {
        "label": "actual_answer_capture_status",
        "status": result.get("status"),
        "errors": list(result.get("errors") or []),
        "summary": {
            "capture_count": result.get("capture_count"),
            "latest_capture": result.get("latest_capture"),
            "route_counts": result.get("route_counts"),
        },
    }


def build_result(
    *,
    project_root: Path = PROJECT_ROOT,
    openclaw_dir: Path = DEFAULT_OPENCLAW_DIR,
    max_age_hours: float = 24.0,
    expected_latest_count: int = 6,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    errors: list[str] = []
    for check in (
        lambda: check_status_summary(openclaw_dir),
        lambda: check_context_bundle(openclaw_dir, max_age_hours=max_age_hours),
        lambda: check_completion_audit(project_root, openclaw_dir, max_age_hours=max_age_hours),
        lambda: check_consumer_smoke(
            openclaw_dir,
            max_age_hours=max_age_hours,
            expected_latest_count=expected_latest_count,
        ),
        lambda: check_question_read_order(openclaw_dir),
        lambda: check_today_answer(openclaw_dir),
        lambda: check_today_answer_quality(openclaw_dir),
        lambda: check_priority_answer_quality(openclaw_dir),
        lambda: check_answer_samples(openclaw_dir),
        lambda: check_actual_answer_audit(openclaw_dir),
        lambda: check_answer_capture_cycle(openclaw_dir),
        lambda: check_answer_capture_task(project_root),
        lambda: check_actual_answer_capture_status(openclaw_dir),
    ):
        try:
            result = check()
        except Exception as exc:
            result = {"label": "unknown", "status": "failure", "errors": [str(exc)], "summary": {}}
        checks.append(result)
        if result.get("status") != "ok":
            label = result.get("label") or "unknown"
            for error in result.get("errors") or [f"{label} failed without detail"]:
                errors.append(f"{label}: {error}")

    status_summary = next((item for item in checks if item.get("label") == "status_summary"), {})
    status_details = status_summary.get("summary") or {}
    return {
        "status": "ok" if not errors else "failure",
        "errors": errors,
        "project_root": str(project_root),
        "openclaw_dir": str(openclaw_dir),
        "max_age_hours": max_age_hours,
        "expected_latest_count": expected_latest_count,
        "checks": checks,
        "source_git": status_details.get("source_git"),
        "latest_recommendation_date": status_details.get("latest_recommendation_date"),
        "latest_market_counts": status_details.get("latest_market_counts"),
        "telegram_saved_count": status_details.get("telegram_saved_count"),
        "hash_status": status_details.get("hash_status"),
        "hash_checked_count": status_details.get("hash_checked_count"),
    }


def render_text(result: dict[str, Any]) -> str:
    lines = [
        f"OpenClaw quick health: {result.get('status')}",
        f"- project_root: {result.get('project_root')}",
        f"- openclaw_dir: {result.get('openclaw_dir')}",
        f"- latest_recommendation_date: {result.get('latest_recommendation_date')}",
        f"- latest_market_counts: {json.dumps(result.get('latest_market_counts') or {}, ensure_ascii=False, separators=(',', ':'))}",
        f"- telegram_saved_count: {result.get('telegram_saved_count')}",
        f"- hashes: {result.get('hash_status')} checked={result.get('hash_checked_count')}",
        "- checks:",
    ]
    for check in result.get("checks") or []:
        lines.append(f"  - {check.get('label')}: {check.get('status')}")
    if result.get("errors"):
        lines.append("- errors:")
        for error in result["errors"]:
            lines.append(f"  - {error}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a compact OpenClaw Investment Research bridge health check.")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--openclaw-dir", type=Path, default=DEFAULT_OPENCLAW_DIR)
    parser.add_argument("--max-age-hours", type=float, default=24.0)
    parser.add_argument("--expected-latest-count", type=int, default=6)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = build_result(
        project_root=args.project_root.resolve(),
        openclaw_dir=args.openclaw_dir.resolve(),
        max_age_hours=args.max_age_hours,
        expected_latest_count=args.expected_latest_count,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
