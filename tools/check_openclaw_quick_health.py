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
    "today_answer": PROJECT_ROOT / "tools" / "check_openclaw_today_answer_readiness.py",
    "today_answer_quality": PROJECT_ROOT / "tools" / "check_openclaw_today_answer_quality.py",
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
        lambda: check_today_answer(openclaw_dir),
        lambda: check_today_answer_quality(openclaw_dir),
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
