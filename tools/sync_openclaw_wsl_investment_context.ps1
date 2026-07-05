param(
  [string]$WslDistro = "",
  [string]$WslWorkspace = ""
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$projectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$windowsBridgeRoot = Join-Path $env:USERPROFILE ".openclaw\workspace"
$sourceDir = Join-Path $windowsBridgeRoot "data\investment_research"
$dailyMemory = Join-Path $windowsBridgeRoot "memory\$(Get-Date -Format 'yyyy-MM-dd').md"

if (-not (Test-Path -LiteralPath $sourceDir)) {
  throw "Windows OpenClaw bridge source not found: $sourceDir"
}
if (-not (Test-Path -LiteralPath (Join-Path $windowsBridgeRoot "AGENTS.md"))) {
  throw "Windows OpenClaw startup note not found. Run sync_openclaw_investment_context.ps1 first."
}

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

$wslSourceDir = Convert-ToWslPath $sourceDir
$wslStartupRoot = Convert-ToWslPath $windowsBridgeRoot
$wslProjectRoot = Convert-ToWslPath $projectRoot
$wslHome = (& wsl.exe bash -lc 'printf %s "$HOME"').Trim()
if ([string]::IsNullOrWhiteSpace($wslHome)) { throw "Cannot resolve WSL HOME" }

$bash = @"
set -euo pipefail
workspace="$WslWorkspace"
if [ -z "`$workspace" ]; then workspace="$wslHome/.openclaw/workspace"; fi
mkdir -p "`$workspace/data/investment_research" "`$workspace/memory"
cp -f "$wslSourceDir"/* "`$workspace/data/investment_research/"
cp -f "$wslStartupRoot/AGENTS.md" "`$workspace/AGENTS.md"
cp -f "$wslStartupRoot/MEMORY.md" "`$workspace/MEMORY.md"
cp -f "$wslStartupRoot/HEARTBEAT.md" "`$workspace/HEARTBEAT.md"
if [ -f "$wslStartupRoot/memory/$(Get-Date -Format 'yyyy-MM-dd').md" ]; then
  cp -f "$wslStartupRoot/memory/$(Get-Date -Format 'yyyy-MM-dd').md" "`$workspace/memory/$(Get-Date -Format 'yyyy-MM-dd').md"
fi
python3 "$wslProjectRoot/tools/check_openclaw_today_answer_readiness.py" --openclaw-dir "`$workspace/data/investment_research" --json >/tmp/openclaw_wsl_today_answer_readiness.json
python3 "$wslProjectRoot/tools/check_openclaw_question_read_order.py" --openclaw-dir "`$workspace/data/investment_research" --json >/tmp/openclaw_wsl_question_read_order.json
python3 "$wslProjectRoot/tools/check_openclaw_answer_samples.py" --openclaw-dir "`$workspace/data/investment_research" --json >/tmp/openclaw_wsl_answer_samples.json
python3 "$wslProjectRoot/tools/check_openclaw_actual_answer_capture_status.py" --openclaw-dir "`$workspace/data/investment_research" --json >/tmp/openclaw_wsl_actual_answer_capture_status.json
python3 "$wslProjectRoot/tools/check_openclaw_actual_answer_audit.py" --openclaw-dir "`$workspace/data/investment_research" --json >/tmp/openclaw_wsl_actual_answer_audit.json
python3 - <<'PY'
import json, pathlib
for path in [
    '/tmp/openclaw_wsl_today_answer_readiness.json',
    '/tmp/openclaw_wsl_question_read_order.json',
    '/tmp/openclaw_wsl_answer_samples.json',
    '/tmp/openclaw_wsl_actual_answer_capture_status.json',
    '/tmp/openclaw_wsl_actual_answer_audit.json',
]:
    p = pathlib.Path(path)
    print(p.read_text())
    data = json.loads(p.read_text())
    if data.get('status') != 'ok':
        raise SystemExit(1)
PY
"@

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
    throw "WSL OpenClaw sync failed: $LASTEXITCODE"
  }
  $output
} finally {
  if (Test-Path -LiteralPath $tempScript) {
    Remove-Item -LiteralPath $tempScript -Force
  }
}
