from __future__ import annotations

import argparse
import hashlib
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
CHECK_KNOWLEDGE_GRAPH_SCRIPT = PROJECT_ROOT / "tools" / "check_openclaw_knowledge_graph.py"


def load_context_checker():
    spec = importlib.util.spec_from_file_location("check_openclaw_investment_context", CHECK_CONTEXT_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load context checker: {CHECK_CONTEXT_SCRIPT}")
    spec.loader.exec_module(module)
    return module


def load_knowledge_graph_checker():
    spec = importlib.util.spec_from_file_location("check_openclaw_knowledge_graph", CHECK_KNOWLEDGE_GRAPH_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load knowledge graph checker: {CHECK_KNOWLEDGE_GRAPH_SCRIPT}")
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


def sha256_hex(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def validate_bridge_status(
    openclaw_dir: Path,
    git_state: dict,
    *,
    max_age_hours: float,
    require_report_hashes: bool = False,
) -> tuple[dict, list[str]]:
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
    expected_hashes = {
        "first_read_json": openclaw_dir / "openclaw_first_read.json",
        "first_read_markdown": openclaw_dir / "openclaw_first_read.md",
        "context_json": openclaw_dir / "investment_research_context.json",
        "context_markdown": openclaw_dir / "investment_research_context.md",
        "knowledge_graph_blueprint_json": openclaw_dir / "openclaw_knowledge_graph_blueprint.json",
        "knowledge_graph_blueprint_markdown": openclaw_dir / "openclaw_knowledge_graph_blueprint.md",
        "knowledge_graph_nodes": openclaw_dir / "openclaw_knowledge_graph_nodes.json",
        "knowledge_graph_edges": openclaw_dir / "openclaw_knowledge_graph_edges.json",
        "knowledge_graph_master_index": openclaw_dir / "openclaw_knowledge_graph_master_index.md",
        "knowledge_graph_glossary": openclaw_dir / "openclaw_knowledge_graph_glossary.md",
        "knowledge_graph_marginalia": openclaw_dir / "openclaw_knowledge_graph_marginalia_queue.md",
        "bridge_manifest": openclaw_dir / "openclaw_bridge_manifest.json",
    }
    file_hashes = status.get("file_sha256") or {}
    for hash_key, hash_path in expected_hashes.items():
        recorded_hash = file_hashes.get(hash_key)
        if not recorded_hash:
            errors.append(f"bridge status missing file_sha256: {hash_key}")
            continue
        if not hash_path.exists():
            errors.append(f"OpenClaw bridge hash target missing: {hash_path}")
            continue
        if recorded_hash.lower() != sha256_hex(hash_path):
            errors.append(f"bridge status file_sha256 mismatch: {hash_key}")
    expected_report_hashes = {
        "completion_report_json": openclaw_dir / "openclaw_bridge_completion_report.json",
        "completion_report_markdown": openclaw_dir / "openclaw_bridge_completion_report.md",
    }
    report_hashes = status.get("completion_report_sha256") or {}
    for hash_key, hash_path in expected_report_hashes.items():
        recorded_hash = report_hashes.get(hash_key)
        if not recorded_hash:
            if require_report_hashes:
                errors.append(f"bridge status missing completion_report_sha256: {hash_key}")
            continue
        if not hash_path.exists():
            errors.append(f"OpenClaw completion report hash target missing: {hash_path}")
            continue
        if recorded_hash.lower() != sha256_hex(hash_path):
            errors.append(f"bridge status completion_report_sha256 mismatch: {hash_key}")
    return status, errors


def infer_daily_memory_date(bridge_status: dict | None) -> str:
    if bridge_status:
        for key in ("context_generated_at", "copied_at"):
            value = bridge_status.get(key)
            if value:
                return parse_datetime(value).date().isoformat()
    return datetime.now(timezone.utc).date().isoformat()


def validate_openclaw_workspace(workspace: Path, bridge_status: dict | None = None) -> list[str]:
    errors: list[str] = []
    startup_paths = [workspace / "AGENTS.md", workspace / "MEMORY.md", workspace / "HEARTBEAT.md"]
    required_items = [
        "data/investment_research",
        "bridge_status.json",
        "openclaw_first_read.md",
        "openclaw_first_read.json",
        "Read order:",
        "openclaw_bridge_manifest.json",
        "investment_research_context.md",
        "investment_research_context.json",
        "openclaw_knowledge_graph_blueprint.md",
        "openclaw_knowledge_graph_blueprint.json",
        "openclaw_knowledge_graph_nodes.json",
        "openclaw_knowledge_graph_edges.json",
        "openclaw_knowledge_graph_master_index.md",
        "openclaw_knowledge_graph_glossary.md",
        "openclaw_knowledge_graph_marginalia_queue.md",
        "openclaw_bridge_completion_report.json",
        "openclaw_bridge_completion_report.md",
        "completion_report_sha256",
        "sync_openclaw_investment_context.ps1 -RequireCompletionAudit",
        "check_openclaw_bridge_completion.py --max-age-hours 24",
        "check_openclaw_bridge_completion.py --max-age-hours 24 --require-report-hashes",
        "check_openclaw_knowledge_graph.py --max-age-hours 24",
        "show_openclaw_bridge_status.py --json",
        "check_openclaw_quick_health.py --json",
        "check_openclaw_today_answer_readiness.py --json",
        "check_openclaw_today_answer_quality.py --json",
        "sync_openclaw_wsl_investment_context.ps1",
        "check_openclaw_wsl_answer_context.py --json",
        "check_offline_readiness.py --json",
        "today_work_report",
        "answer_correction",
        "next_schedule",
        "오늘 시스템에서 구현한 작업",
        "오늘 구현 작업 없음",
        "특별히 새로 구현된 작업 기록 없음",
    ]
    source_git = ""
    if bridge_status:
        source_git = f"{bridge_status.get('source_git_branch')} {bridge_status.get('source_git_commit')}"
        if "None" in source_git:
            source_git = ""
    for path in startup_paths:
        if not path.exists():
            errors.append(f"OpenClaw startup note missing: {path}")
            continue
        text = path.read_text(encoding="utf-8-sig")
        for required in required_items:
            if required not in text:
                errors.append(f"OpenClaw startup note missing {required}: {path}")
        if source_git and source_git not in text:
            errors.append(f"OpenClaw startup note missing source git {source_git}: {path}")

    daily_date = infer_daily_memory_date(bridge_status)
    daily_path = workspace / "memory" / f"{daily_date}.md"
    daily_required = [
        "today_work_report",
        "answer_correction",
        "next_schedule",
        "오늘 시스템에서 구현한 작업",
        "오늘 구현 작업 없음",
        "특별히 새로 구현된 작업 기록 없음",
        "check_openclaw_today_answer_readiness.py --json",
        "data/investment_research/bridge_status.json",
        "data/investment_research/openclaw_first_read.json",
    ]
    if not daily_path.exists():
        errors.append(f"OpenClaw daily investment memory missing: {daily_path}")
    else:
        daily_text = daily_path.read_text(encoding="utf-8-sig")
        for required in daily_required:
            if required not in daily_text:
                errors.append(f"OpenClaw daily investment memory missing {required}: {daily_path}")
        if source_git and source_git not in daily_text:
            errors.append(f"OpenClaw daily investment memory missing source git {source_git}: {daily_path}")
    return errors


def build_result(
    *,
    project_root: Path = PROJECT_ROOT,
    source_dir: Path = DEFAULT_SOURCE_DIR,
    openclaw_workspace: Path = DEFAULT_OPENCLAW_WORKSPACE,
    openclaw_dir: Path = DEFAULT_OPENCLAW_DIR,
    max_age_hours: float = 1.0,
    require_report_hashes: bool = False,
) -> dict:
    errors: list[str] = []
    details: dict = {
        "project_root": str(project_root),
        "source_dir": str(source_dir),
        "openclaw_workspace": str(openclaw_workspace),
        "openclaw_dir": str(openclaw_dir),
        "audit_generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "max_age_hours": max_age_hours,
        "operational_commands": {
            "safe_refresh": "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\sync_openclaw_investment_context.ps1",
            "strict_refresh": "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\sync_openclaw_investment_context.ps1 -RequireCompletionAudit",
            "validation": "python tools\\check_openclaw_investment_context.py --max-age-hours 24",
            "completion_audit": "python tools\\check_openclaw_bridge_completion.py --max-age-hours 24",
            "knowledge_graph_validation": "python tools\\check_openclaw_knowledge_graph.py --max-age-hours 24",
            "final_completion_audit": "python tools\\check_openclaw_bridge_completion.py --max-age-hours 24 --require-report-hashes",
            "status_summary": "python tools\\show_openclaw_bridge_status.py --json",
            "quick_health": "python tools\\check_openclaw_quick_health.py --json",
            "today_answer_readiness": "python tools\\check_openclaw_today_answer_readiness.py --json",
            "today_answer_quality": "python tools\\check_openclaw_today_answer_quality.py --json",
            "wsl_refresh": "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\sync_openclaw_wsl_investment_context.ps1",
            "wsl_answer_context": "python tools\\check_openclaw_wsl_answer_context.py --json",
            "offline_readiness": "python tools\\check_offline_readiness.py --json",
        },
    }

    checker = load_context_checker()
    try:
        source_messages = checker.validate_bundle(source_dir, max_age_hours=max_age_hours)
        openclaw_messages = checker.validate_bundle(openclaw_dir, max_age_hours=max_age_hours)
        details["bundle_checks"] = {"source": source_messages, "openclaw": openclaw_messages}
    except AssertionError as exc:
        errors.append(str(exc))

    kg_checker = load_knowledge_graph_checker()
    try:
        kg_source_messages = kg_checker.validate_graph_bundle(source_dir, max_age_hours=max_age_hours)
        kg_openclaw_messages = kg_checker.validate_graph_bundle(openclaw_dir, max_age_hours=max_age_hours)
        details["knowledge_graph_checks"] = {"source": kg_source_messages, "openclaw": kg_openclaw_messages}
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
                require_report_hashes=require_report_hashes,
            )
            details["bridge_status"] = bridge_status
            errors.extend(bridge_errors)
        except AssertionError as exc:
            errors.append(str(exc))
        try:
            details["first_read"] = load_json(openclaw_dir / "openclaw_first_read.json")
        except AssertionError as exc:
            errors.append(str(exc))

    errors.extend(validate_openclaw_workspace(openclaw_workspace, details.get("bridge_status")))
    details["completion_requirements"] = [
        "source and OpenClaw bundles validate",
        "OpenClaw first-read packet validates before larger context ingestion",
        "source git branch is main",
        "source git is clean and synced with upstream",
        "OpenClaw bridge_status references current clean commit",
        "OpenClaw bridge_status file hashes match copied files",
        "OpenClaw personal knowledge graph artifacts validate",
        "OpenClaw completion report hashes match completion report files",
        "OpenClaw startup notes point to bridge files, status summary, final audit command, today answer readiness, today answer quality smoke, WSL PA answer context, and current source git",
        "OpenClaw daily memory tells agents to use today_work_report and next_schedule before answering today-work questions",
    ]
    return {
        "status": "ok" if not errors else "failure",
        "errors": errors,
        **details,
    }


def render_markdown_report(result: dict) -> str:
    git_state = result.get("git") or {}
    bridge_status = result.get("bridge_status") or {}
    first_read = result.get("first_read") or {}
    errors = result.get("errors") or []
    lines = [
        "# OpenClaw Investment Research Bridge Completion Report",
        "",
        f"- status: {result.get('status')}",
        f"- project: `{result.get('project_root')}`",
        f"- source dir: `{result.get('source_dir')}`",
        f"- OpenClaw dir: `{result.get('openclaw_dir')}`",
        f"- audit generated: {result.get('audit_generated_at')}",
        f"- git: {git_state.get('branch')} {git_state.get('commit')} / upstream {git_state.get('upstream')}",
        f"- git synced: ahead={git_state.get('ahead')} behind={git_state.get('behind')} dirty={git_state.get('dirty')}",
        f"- bridge copied: {bridge_status.get('copied_at')}",
        f"- bridge max age hours: {bridge_status.get('max_age_hours', result.get('max_age_hours'))}",
        f"- context generated: {bridge_status.get('context_generated_at')}",
        f"- latest recommendation date: {bridge_status.get('latest_recommendation_date')}",
        f"- market counts: {bridge_status.get('latest_market_counts')}",
        f"- telegram saved: {bridge_status.get('telegram_saved_count')}",
        f"- secrets excluded: {bridge_status.get('secrets_excluded')}",
        "",
        "## Completion Requirements",
        "",
    ]
    for item in result.get("completion_requirements") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## First-Read Packet", ""])
    if first_read:
        first_read_counts = first_read.get("latest_market_counts") or {}
        first_read_rows = first_read.get("latest_recommendations") or []
        lines.append(f"- schema: `{first_read.get('schema')}`")
        lines.append(f"- generated_at: {first_read.get('generated_at')}")
        lines.append(f"- read_this_first: {first_read.get('read_this_first')}")
        lines.append(f"- latest recommendation date: {first_read.get('latest_recommendation_date')}")
        lines.append(f"- market counts: {first_read_counts}")
        lines.append(f"- recommendation rows: {len(first_read_rows) if isinstance(first_read_rows, list) else 0}")
    else:
        lines.append("- none")
    lines.extend(["", "## Read Order", ""])
    read_order = bridge_status.get("read_order") or []
    if read_order:
        for index, item in enumerate(read_order, start=1):
            lines.append(f"{index}. `{item}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Latest Recommendations", ""])
    latest_recommendations = bridge_status.get("latest_recommendations") or []
    if latest_recommendations:
        for item in latest_recommendations:
            lines.append(
                "- {market}#{rank} `{ticker}` {name} | score {score} | baseline {baseline} {currency}".format(
                    market=item.get("market"),
                    rank=item.get("rank"),
                    ticker=item.get("ticker"),
                    name=item.get("company_name"),
                    score=item.get("score"),
                    baseline=item.get("baseline_price"),
                    currency=item.get("currency"),
                )
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Status Summary Health", ""])
    lines.append("- command: `python tools\\show_openclaw_bridge_status.py --json`")
    lines.append("- expected hash_status: `ok`")
    lines.append("- expected hash_checked_count: `14`")
    lines.append("- expected hash_mismatches: `[]`")
    lines.extend(["", "## Operational Commands", ""])
    commands = result.get("operational_commands") or {}
    for label in (
        "safe_refresh",
        "strict_refresh",
        "validation",
        "completion_audit",
        "knowledge_graph_validation",
        "final_completion_audit",
        "status_summary",
        "quick_health",
        "today_answer_readiness",
        "today_answer_quality",
        "wsl_refresh",
        "wsl_answer_context",
        "offline_readiness",
    ):
        command = commands.get(label)
        if command:
            lines.append(f"- {label}: `{command}`")
    lines.extend(["", "## File Hashes", ""])
    file_hashes = bridge_status.get("file_sha256") or {}
    if file_hashes:
        for label in (
            "first_read_json",
            "first_read_markdown",
            "context_json",
            "context_markdown",
            "knowledge_graph_blueprint_json",
            "knowledge_graph_blueprint_markdown",
            "knowledge_graph_nodes",
            "knowledge_graph_edges",
            "knowledge_graph_master_index",
            "knowledge_graph_glossary",
            "knowledge_graph_marginalia",
            "bridge_manifest",
        ):
            file_hash = file_hashes.get(label)
            if file_hash:
                lines.append(f"- {label}: `{file_hash}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Bundle Checks", ""])
    bundle_checks = result.get("bundle_checks") or {}
    for label in ("source", "openclaw"):
        messages = bundle_checks.get(label) or []
        for message in messages:
            lines.append(f"- {label}: {message}")
    lines.extend(["", "## Knowledge Graph Checks", ""])
    kg_checks = result.get("knowledge_graph_checks") or {}
    for label in ("source", "openclaw"):
        messages = kg_checks.get(label) or []
        for message in messages:
            lines.append(f"- {label}: {message}")
    lines.extend(["", "## Errors", ""])
    if errors:
        for error in errors:
            lines.append(f"- {error}")
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def write_completion_report(result: dict, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "openclaw_bridge_completion_report.json"
    markdown_path = output_dir / "openclaw_bridge_completion_report.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown_report(result), encoding="utf-8")
    report_hashes = {
        "completion_report_json": sha256_hex(json_path),
        "completion_report_markdown": sha256_hex(markdown_path),
    }
    status_path = output_dir / "bridge_status.json"
    if status_path.exists():
        status = load_json(status_path)
        status["completion_report_sha256"] = report_hashes
        status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"json_path": str(json_path), "markdown_path": str(markdown_path), "report_sha256": report_hashes}


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit final Investment Research OS to OpenClaw bridge completion.")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--openclaw-workspace", type=Path, default=DEFAULT_OPENCLAW_WORKSPACE)
    parser.add_argument("--openclaw-dir", type=Path, default=DEFAULT_OPENCLAW_DIR)
    parser.add_argument("--max-age-hours", type=float, default=1.0)
    parser.add_argument("--json", action="store_true", help="감사 결과를 JSON으로 출력합니다.")
    parser.add_argument("--write-report", action="store_true", help="OpenClaw 브리지 폴더에 완료 감사 리포트를 저장합니다.")
    parser.add_argument(
        "--require-report-hashes",
        action="store_true",
        help="bridge_status.json의 completion_report_sha256 항목을 필수로 검증합니다.",
    )
    args = parser.parse_args()

    result = build_result(
        project_root=args.project_root.resolve(),
        source_dir=args.source_dir.resolve(),
        openclaw_workspace=args.openclaw_workspace.resolve(),
        openclaw_dir=args.openclaw_dir.resolve(),
        max_age_hours=args.max_age_hours,
        require_report_hashes=args.require_report_hashes,
    )
    report_paths = None
    if args.write_report:
        report_paths = write_completion_report(result, args.openclaw_dir.resolve())
        result["report_paths"] = report_paths
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"[{result['status']}] openclaw_bridge_completion")
        if report_paths:
            print(f"- report: {report_paths['markdown_path']}")
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
