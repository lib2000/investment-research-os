from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TODAY_TOOL = PROJECT_ROOT / "tools" / "check_openclaw_today_answer_readiness.py"
QUESTION_READ_ORDER_TOOL = PROJECT_ROOT / "tools" / "check_openclaw_question_read_order.py"
ANSWER_SAMPLES_TOOL = PROJECT_ROOT / "tools" / "check_openclaw_answer_samples.py"
ACTUAL_ANSWER_AUDIT_TOOL = PROJECT_ROOT / "tools" / "check_openclaw_actual_answer_audit.py"
ACTUAL_ANSWER_CAPTURE_STATUS_TOOL = PROJECT_ROOT / "tools" / "check_openclaw_actual_answer_capture_status.py"
DEFAULT_SESSION_KEYS = ["agent:pa:main", "agent:pa:main2"]
REQUIRED_TEXT = [
    "오늘 시스템에서 구현한 작업",
    "오늘 구현 작업 없음",
    "특별히 새로 구현된 작업 기록 없음",
    "today_work_report",
    "answer_correction",
    "next_schedule",
    "data/investment_research/bridge_status.json",
    "data/investment_research/openclaw_first_read.json",
    "check_openclaw_question_read_order.py --json",
    "check_openclaw_answer_samples.py --json",
    "capture_openclaw_actual_answer.py --route-id today_work_report --answer-file <path> --audit --json",
    "check_openclaw_actual_answer_capture_status.py --json",
    "check_openclaw_actual_answer_audit.py --json",
]


def windows_to_wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    if not drive:
        return str(resolved).replace("\\", "/")
    rest = str(resolved)[2:].replace("\\", "/")
    return f"/mnt/{drive}{rest}"


def run_wsl_json(script: str) -> dict[str, Any]:
    if shutil.which("wsl.exe") is None and shutil.which("wsl") is None:
        raise AssertionError("wsl.exe is not available")
    command = ["wsl.exe", "python3", "-"] if shutil.which("wsl.exe") else ["wsl", "python3", "-"]
    completed = subprocess.run(command, input=script.encode("utf-8"), capture_output=True, check=False)
    stdout = completed.stdout.decode("utf-8", errors="replace")
    stderr = completed.stderr.decode("utf-8", errors="replace")
    if completed.returncode != 0:
        raise AssertionError((stderr or stdout or "WSL command failed").strip())
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"WSL command returned invalid JSON: {stdout[:500]}") from exc
    if not isinstance(payload, dict):
        raise AssertionError("WSL command JSON root must be object")
    return payload


def build_result(
    *,
    wsl_workspace: str = "~/.openclaw/workspace",
    session_keys: list[str] | None = None,
    today_tool: Path = TODAY_TOOL,
    question_read_order_tool: Path = QUESTION_READ_ORDER_TOOL,
    answer_samples_tool: Path = ANSWER_SAMPLES_TOOL,
    actual_answer_audit_tool: Path = ACTUAL_ANSWER_AUDIT_TOOL,
    actual_answer_capture_status_tool: Path = ACTUAL_ANSWER_CAPTURE_STATUS_TOOL,
    require_fresh_bootstrap: bool = False,
) -> dict[str, Any]:
    session_keys = session_keys or list(DEFAULT_SESSION_KEYS)
    today_tool_wsl = windows_to_wsl_path(today_tool)
    question_read_order_tool_wsl = windows_to_wsl_path(question_read_order_tool)
    answer_samples_tool_wsl = windows_to_wsl_path(answer_samples_tool)
    actual_answer_audit_tool_wsl = windows_to_wsl_path(actual_answer_audit_tool)
    actual_answer_capture_status_tool_wsl = windows_to_wsl_path(actual_answer_capture_status_tool)
    script = f"""
import json
import pathlib
import subprocess
import sys

workspace = pathlib.Path({wsl_workspace!r}).expanduser()
session_keys = {session_keys!r}
required_text = {REQUIRED_TEXT!r}
require_fresh_bootstrap = {require_fresh_bootstrap!r}
today_tool = pathlib.Path({today_tool_wsl!r})
question_read_order_tool = pathlib.Path({question_read_order_tool_wsl!r})
answer_samples_tool = pathlib.Path({answer_samples_tool_wsl!r})
actual_answer_audit_tool = pathlib.Path({actual_answer_audit_tool_wsl!r})
actual_answer_capture_status_tool = pathlib.Path({actual_answer_capture_status_tool_wsl!r})
errors = []
startup = {{}}
for name in ['AGENTS.md', 'MEMORY.md', 'HEARTBEAT.md']:
    path = workspace / name
    item = {{'path': str(path), 'exists': path.exists(), 'missing': []}}
    if not path.exists():
        errors.append(f'missing startup note: {{path}}')
    else:
        text = path.read_text(encoding='utf-8-sig', errors='replace')
        for token in required_text:
            if token not in text:
                item['missing'].append(token)
                errors.append(f'startup note {{name}} missing {{token}}')
    startup[name] = item

first_read_dir = workspace / 'data' / 'investment_research'
completed = subprocess.run(
    [sys.executable, str(today_tool), '--openclaw-dir', str(first_read_dir), '--json'],
    capture_output=True,
    text=True,
    check=False,
)
try:
    today = json.loads(completed.stdout) if completed.stdout else {{}}
except json.JSONDecodeError:
    today = {{'status': 'failure', 'errors': ['invalid today readiness JSON'], 'stdout': completed.stdout, 'stderr': completed.stderr}}
if completed.returncode != 0 or today.get('status') != 'ok':
    errors.append('WSL today answer readiness failed')

def run_bridge_tool(label, tool_path):
    completed = subprocess.run(
        [sys.executable, str(tool_path), '--openclaw-dir', str(first_read_dir), '--json'],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        payload = json.loads(completed.stdout) if completed.stdout else {{}}
    except json.JSONDecodeError:
        payload = {{'status': 'failure', 'errors': [f'invalid {{label}} JSON'], 'stdout': completed.stdout, 'stderr': completed.stderr}}
    if completed.returncode != 0 or payload.get('status') != 'ok':
        errors.append(f'WSL {{label}} failed')
    return payload

question_read_order = run_bridge_tool('question read-order', question_read_order_tool)
answer_samples = run_bridge_tool('answer samples', answer_samples_tool)
actual_answer_audit = run_bridge_tool('actual answer audit', actual_answer_audit_tool)
actual_answer_capture_status = run_bridge_tool('actual answer capture status', actual_answer_capture_status_tool)

daily_date = str(today.get('generated_at') or '')[:10]
if not daily_date:
    daily_date = pathlib.Path('/tmp').joinpath('x').name  # impossible marker, keeps type simple

daily_path = workspace / 'memory' / f'{{daily_date}}.md'
daily = {{'path': str(daily_path), 'exists': daily_path.exists(), 'missing': []}}
if not daily_path.exists():
    errors.append(f'missing daily memory: {{daily_path}}')
else:
    text = daily_path.read_text(encoding='utf-8-sig', errors='replace')
    for token in required_text:
        if token not in text:
            daily['missing'].append(token)
            errors.append(f'daily memory missing {{token}}')

sessions_path = pathlib.Path.home() / '.openclaw' / 'agents' / 'pa' / 'sessions' / 'sessions.json'
sessions = {{'path': str(sessions_path), 'exists': sessions_path.exists(), 'items': {{}}}}
if not sessions_path.exists():
    errors.append(f'missing PA sessions file: {{sessions_path}}')
else:
    data = json.loads(sessions_path.read_text(encoding='utf-8'))
    for key in session_keys:
        entry = data.get(key)
        item = {{'exists': entry is not None}}
        if entry is None:
            errors.append(f'missing session key: {{key}}')
        else:
            report = entry.get('systemPromptReport') or {{}}
            injected = {{row.get('name'): row for row in report.get('injectedWorkspaceFiles') or []}}
            item.update({{
                'sessionId': entry.get('sessionId'),
                'systemSent': entry.get('systemSent'),
                'hasSystemPromptReport': 'systemPromptReport' in entry,
                'workspaceDir': report.get('workspaceDir'),
                'injectedWorkspaceFiles': {{
                    name: {{
                        'missing': injected.get(name, {{}}).get('missing'),
                        'rawChars': injected.get(name, {{}}).get('rawChars'),
                        'truncated': injected.get(name, {{}}).get('truncated'),
                    }}
                    for name in ['AGENTS.md', 'MEMORY.md', 'HEARTBEAT.md']
                }},
            }})
            if entry.get('systemSent') is False:
                pass
            elif require_fresh_bootstrap:
                errors.append(f'session {{key}} systemPromptReport must be absent before next PA answer')
            elif 'systemPromptReport' not in entry:
                errors.append(f'session {{key}} systemPromptReport missing after systemSent=true')
            else:
                if report.get('workspaceDir') != str(workspace):
                    errors.append(f'session {{key}} workspaceDir mismatch: {{report.get("workspaceDir")}}')
                for name, minimum in [('AGENTS.md', 1000), ('MEMORY.md', 1000), ('HEARTBEAT.md', 1000)]:
                    row = injected.get(name)
                    if not row:
                        errors.append(f'session {{key}} missing injected {{name}}')
                        continue
                    if row.get('missing'):
                        errors.append(f'session {{key}} injected {{name}} is marked missing')
                    if row.get('truncated'):
                        errors.append(f'session {{key}} injected {{name}} is truncated')
                    if int(row.get('rawChars') or 0) < minimum:
                        errors.append(f'session {{key}} injected {{name}} too small: {{row.get("rawChars")}}')
        sessions['items'][key] = item

print(json.dumps({{
    'status': 'ok' if not errors else 'failure',
    'errors': errors,
    'workspace': str(workspace),
    'startup': startup,
    'daily_memory': daily,
    'today_answer': today,
    'question_read_order': question_read_order,
    'answer_samples': answer_samples,
    'actual_answer_audit': actual_answer_audit,
    'actual_answer_capture_status': actual_answer_capture_status,
    'sessions': sessions,
}}, ensure_ascii=False))
"""
    payload = run_wsl_json(script)
    return payload


def render_text(result: dict[str, Any]) -> str:
    today = result.get("today_answer") or {}
    lines = [
        f"OpenClaw WSL answer context: {result.get('status')}",
        f"- workspace: {result.get('workspace')}",
        f"- today commits: {today.get('today_commit_count')}",
        f"- next schedule count: {today.get('next_schedule_count')}",
        f"- question read-order: {(result.get('question_read_order') or {}).get('status')}",
        f"- answer samples: {(result.get('answer_samples') or {}).get('status')}",
        f"- actual answer audit: {(result.get('actual_answer_audit') or {}).get('status')}",
        f"- actual answer capture status: {(result.get('actual_answer_capture_status') or {}).get('status')}",
    ]
    sessions = ((result.get("sessions") or {}).get("items") or {})
    for key, item in sessions.items():
        lines.append(
            f"- {key}: systemSent={item.get('systemSent')} hasSystemPromptReport={item.get('hasSystemPromptReport')}"
        )
    if result.get("errors"):
        lines.append("- errors:")
        for error in result["errors"]:
            lines.append(f"  - {error}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate WSL OpenClaw PA answer context and session bootstrap state.")
    parser.add_argument("--wsl-workspace", default="~/.openclaw/workspace")
    parser.add_argument("--session-key", action="append", dest="session_keys")
    parser.add_argument(
        "--require-fresh-bootstrap",
        action="store_true",
        help="Fail if a PA session has already sent its system prompt; use before asking OpenClaw for a fresh answer.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        result = build_result(
            wsl_workspace=args.wsl_workspace,
            session_keys=args.session_keys,
            require_fresh_bootstrap=args.require_fresh_bootstrap,
        )
    except AssertionError as exc:
        result = {"status": "failure", "errors": [str(exc)]}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
