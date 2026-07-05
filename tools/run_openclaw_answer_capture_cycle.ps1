param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp",
  [string]$OpenClawDir = "",
  [switch]$Collect,
  [switch]$ArchiveFailures,
  [switch]$WriteState
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
Set-Location -LiteralPath $ProjectRootPath

$argsList = @(
  "tools\check_openclaw_answer_capture_cycle.py",
  "--json"
)

if ($OpenClawDir.Trim()) {
  $argsList += @("--openclaw-dir", $OpenClawDir.Trim())
}
if ($Collect.IsPresent) {
  $argsList += "--collect"
}
if ($ArchiveFailures.IsPresent) {
  $argsList += "--archive-failures"
}
if ($WriteState.IsPresent) {
  $argsList += "--write-state"
}

python @argsList
if ($LASTEXITCODE -ne 0) {
  throw "OpenClaw answer capture cycle failed: $LASTEXITCODE"
}
