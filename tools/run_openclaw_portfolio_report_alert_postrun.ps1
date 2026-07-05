param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp",
  [int]$MaxStateAgeHours = 2,
  [switch]$Enabled,
  [switch]$Submit,
  [switch]$NotifyOk,
  [switch]$Repeat,
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
  "tools\check_portfolio_report_alert_postrun.py",
  "--max-state-age-hours",
  "$MaxStateAgeHours",
  "--json"
)

if ($Enabled.IsPresent) {
  $argsList += "--enabled"
}
if ($Submit.IsPresent) {
  $argsList += "--submit"
}
if ($NotifyOk.IsPresent) {
  $argsList += "--notify-ok"
}
if ($Repeat.IsPresent) {
  $argsList += "--repeat"
}
if ($WriteState.IsPresent) {
  $argsList += "--write-state"
}

python @argsList
if ($LASTEXITCODE -ne 0) {
  throw "OpenClaw portfolio report Telegram post-run check failed: $LASTEXITCODE"
}
