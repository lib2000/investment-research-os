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
) -> dict[str, Any]:
    session_keys = session_keys or list(DEFAULT_SESSION_KEYS)
    today_tool_wsl = windows_to_wsl_path(today_tool)
    script = f"""
import json
import pathlib
import subprocess
import sys

workspace = pathlib.Path({wsl_workspace!r}).expanduser()
session_keys = {session_keys!r}
required_text = {REQUIRED_TEXT!r}
today_tool = pathlib.Path({today_tool_wsl!r})
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
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        result = build_result(wsl_workspace=args.wsl_workspace, session_keys=args.session_keys)
    except AssertionError as exc:
        result = {"status": "failure", "errors": [str(exc)]}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
