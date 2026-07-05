param(
  [string]$WslDistro = "",
  [string]$SessionKey = "agent:pa:main2"
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$bash = @"
set -euo pipefail
sessions="`$HOME/.openclaw/agents/pa/sessions/sessions.json"
if [ ! -f "`$sessions" ]; then
  echo "OpenClaw WSL pa sessions file not found: `$sessions" >&2
  exit 1
fi
python3 - <<'PY'
import json
import pathlib
import time

session_key = "$SessionKey"
sessions_path = pathlib.Path.home() / ".openclaw" / "agents" / "pa" / "sessions" / "sessions.json"
data = json.loads(sessions_path.read_text(encoding="utf-8"))
if session_key not in data:
    raise SystemExit(f"session key not found: {session_key}; known={list(data)}")
backup = sessions_path.with_name(sessions_path.name + f".bak.{time.strftime('%Y%m%d-%H%M%S')}")
backup.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
entry = data[session_key]
entry["systemSent"] = False
for key in ("systemPromptReport", "workspaceBootstrapReport", "bootstrapReport"):
    entry.pop(key, None)
entry["updatedAt"] = int(time.time() * 1000)
sessions_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({
    "status": "ok",
    "sessions_path": str(sessions_path),
    "backup_path": str(backup),
    "session_key": session_key,
    "session_id": entry.get("sessionId"),
    "system_sent": entry.get("systemSent"),
    "has_system_prompt_report": "systemPromptReport" in entry,
}, ensure_ascii=False, indent=2))
PY
"@

function Convert-ToWslPath {
  param([string]$Path)
  $resolved = (Resolve-Path -LiteralPath $Path).Path
  if ($resolved -notmatch '^[A-Za-z]:\\') {
    throw "Only local Windows drive paths are supported for WSL conversion: $resolved"
  }
  $drive = $resolved.Substring(0, 1).ToLowerInvariant()
  $rest = $resolved.Substring(2).Replace('\', '/')
  return "/mnt/$drive$rest"
}

$tempScript = [System.IO.Path]::GetTempFileName() + ".sh"
try {
  [System.IO.File]::WriteAllText($tempScript, $bash.Replace("`r`n", "`n"), [System.Text.UTF8Encoding]::new($false))
  $wslTempScript = Convert-ToWslPath $tempScript
  if ([string]::IsNullOrWhiteSpace($WslDistro)) {
    $output = & wsl.exe bash $wslTempScript
  } else {
    $output = & wsl.exe -d $WslDistro bash $wslTempScript
  }
  if ($LASTEXITCODE -ne 0) {
    throw "WSL OpenClaw pa session refresh failed: $LASTEXITCODE"
  }
  $output
} finally {
  if (Test-Path -LiteralPath $tempScript) {
    Remove-Item -LiteralPath $tempScript -Force
  }
}
