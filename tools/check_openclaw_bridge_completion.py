from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "research_vault" / "_system" / "openclaw_integration"
DEFAULT_OPENCLAW_WORKSPACE = Path.home() / ".openclaw" / "workspace"
DEFAULT_OPENCLAW_DIR = DEFAULT_OPENCLAW_WORKSPACE / "data" / "investment_research"
CHECK_CONTEXT_SCRIPT = PROJECT_ROOT / "tools" / "check_openclaw_investment_context.py"


def load_context_checker():
    spec = importlib.util.spec_from_file_location("check_openclaw_investment_context", CHECK_CONTEXT_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load context checker: {CHECK_CONTEXT_SCRIPT}")
    spec.loader.exec_module(module)
    return module


def run_git(project_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(project_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def load_json(path: Path) -> dict:
    if not path.exists():
        raise AssertionError(f"JSON file not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise AssertionError(f"JSON file is invalid: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise AssertionError(f"JSON root must be object: {path}")
    return payload


def parse_datetime(value: object) -> datetime:
    if not value:
        raise AssertionError("timestamp is missing")
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise AssertionError(f"timestamp is invalid: {value}") from exc
    if parsed.tzinfo is None:
        raise AssertionError(f"timestamp must include timezone: {value}")
    return parsed


def get_git_state(project_root: Path) -> dict:
    branch = run_git(project_root, "rev-parse", "--abbrev-ref", "HEAD")
    commit = run_git(project_root, "rev-parse", "--short", "HEAD")
    upstream = run_git(project_root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    ahead_behind = run_git(project_root, "rev-list", "--left-right", "--count", f"{upstream}...HEAD")
    behind_text, ahead_text = ahead_behind.split()
    status = run_git(project_root, "status", "--short")
    return {
        "branch": branch,
        "commit": commit,
        "upstream": upstream,
        "ahead": int(ahead_text),
        "behind": int(behind_text),
        "dirty": bool(status.strip()),
        "status_short": status,
    }


def validate_git_state(git_state: dict) -> list[str]:
    errors: list[str] = []
    if git_state["branch"] != "main":
        errors.append(f"source branch must be main: {git_state['branch']}")
    if git_state["dirty"]:
        errors.append("source git worktree must be clean")
    if git_state["ahead"] != 0 or git_state["behind"] != 0:
        errors.append(f"source git must be synced with upstream: ahead={git_state['ahead']} behind={git_state['behind']}")
    return errors


def validate_bridge_status(openclaw_dir: Path, git_state: dict, *, max_age_hours: float) -> tuple[dict, list[str]]:
    errors: list[str] = []
    status = load_json(openclaw_dir / "bridge_status.json")
    copied_at = parse_datetime(status.get("copied_at"))
    age_hours = (datetime.now(timezone.utc) - copied_at.astimezone(timezone.utc)).total_seconds() / 3600
    if age_hours > max_age_hours:
        errors.append(f"OpenClaw bridge copy is stale: {age_hours:.2f}h > {max_age_hours:.2f}h")
    if status.get("status") != "ok":
        errors.append(f"bridge status must be ok: {status.get('status')}")
    if status.get("source_git_commit") != git_state["commit"]:
        errors.append(f"bridge source commit mismatch: {status.get('source_git_commit')} != {git_state['commit']}")
    if status.get("source_git_branch") != git_state["branch"]:
        errors.append(f"bridge source branch mismatch: {status.get('source_git_branch')} != {git_state['branch']}")
    if status.get("source_git_dirty") is not False:
        errors.append("bridge source_git_dirty must be false after final sync")
    if status.get("secrets_excluded") is not True:
        errors.append("bridge status must confirm secrets_excluded=true")
    return status, errors


def validate_openclaw_workspace(workspace: Path) -> list[str]:
    errors: list[str] = []
    memory = workspace / "MEMORY.md"
    heartbeat = workspace / "HEARTBEAT.md"
    for path in (memory, heartbeat):
        if not path.exists():
            errors.append(f"OpenClaw startup note missing: {path}")
            continue
        text = path.read_text(encoding="utf-8-sig")
        for required in ["data/investment_research", "bridge_status.json"]:
            if required not in text:
                errors.append(f"OpenClaw startup note missing {required}: {path}")
    return errors


def build_result(
    *,
    project_root: Path = PROJECT_ROOT,
    source_dir: Path = DEFAULT_SOURCE_DIR,
    openclaw_workspace: Path = DEFAULT_OPENCLAW_WORKSPACE,
    openclaw_dir: Path = DEFAULT_OPENCLAW_DIR,
    max_age_hours: float = 1.0,
) -> dict:
    errors: list[str] = []
    details: dict = {
        "project_root": str(project_root),
        "source_dir": str(source_dir),
        "openclaw_workspace": str(openclaw_workspace),
        "openclaw_dir": str(openclaw_dir),
        "max_age_hours": max_age_hours,
    }

    checker = load_context_checker()
    try:
        source_messages = checker.validate_bundle(source_dir, max_age_hours=max_age_hours)
        openclaw_messages = checker.validate_bundle(openclaw_dir, max_age_hours=max_age_hours)
        details["bundle_checks"] = {"source": source_messages, "openclaw": openclaw_messages}
    except AssertionError as exc:
        errors.append(str(exc))

    try:
        git_state = get_git_state(project_root)
        details["git"] = git_state
        errors.extend(validate_git_state(git_state))
    except (subprocess.CalledProcessError, ValueError) as exc:
        errors.append(f"source git state check failed: {exc}")
        git_state = None

    if git_state is not None:
        try:
            bridge_status, bridge_errors = validate_bridge_status(
                openclaw_dir,
                git_state,
                max_age_hours=max_age_hours,
            )
            details["bridge_status"] = bridge_status
            errors.extend(bridge_errors)
        except AssertionError as exc:
            errors.append(str(exc))

    errors.extend(validate_openclaw_workspace(openclaw_workspace))
    details["completion_requirements"] = [
        "source and OpenClaw bundles validate",
        "source git branch is main",
        "source git is clean and synced with upstream",
        "OpenClaw bridge_status references current clean commit",
        "OpenClaw startup notes point to bridge files",
    ]
    return {
        "status": "ok" if not errors else "failure",
        "errors": errors,
        **details,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit final Investment Research OS to OpenClaw bridge completion.")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--openclaw-workspace", type=Path, default=DEFAULT_OPENCLAW_WORKSPACE)
    parser.add_argument("--openclaw-dir", type=Path, default=DEFAULT_OPENCLAW_DIR)
    parser.add_argument("--max-age-hours", type=float, default=1.0)
    parser.add_argument("--json", action="store_true", help="감사 결과를 JSON으로 출력합니다.")
    args = parser.parse_args()

    result = build_result(
        project_root=args.project_root.resolve(),
        source_dir=args.source_dir.resolve(),
        openclaw_workspace=args.openclaw_workspace.resolve(),
        openclaw_dir=args.openclaw_dir.resolve(),
        max_age_hours=args.max_age_hours,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"[{result['status']}] openclaw_bridge_completion")
        if result["errors"]:
            for error in result["errors"]:
                print(f"- {error}")
        else:
            git_state = result["git"]
            print(f"- git: {git_state['branch']} {git_state['commit']} synced with {git_state['upstream']}")
            print(f"- bridge: {result['bridge_status']['context_generated_at']}")
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
