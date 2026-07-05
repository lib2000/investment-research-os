param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp",
  [int]$LookbackDays = 3,
  [int]$MaxItems = 8,
  [string]$ChatId = "",
  [switch]$Enabled,
  [switch]$Submit,
  [switch]$SendEmpty,
  [switch]$IncludePreviouslySent,
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
  "tools\check_portfolio_report_alert.py",
  "--lookback-days",
  "$LookbackDays",
  "--max-items",
  "$MaxItems",
  "--json"
)

if ($ChatId.Trim()) {
  $argsList += @("--chat-id", $ChatId.Trim())
}
if ($Enabled.IsPresent) {
  $argsList += "--enabled"
}
if ($Submit.IsPresent) {
  $argsList += "--submit"
}
if ($SendEmpty.IsPresent) {
  $argsList += "--send-empty"
}
if ($IncludePreviouslySent.IsPresent) {
  $argsList += "--include-previously-sent"
}
if ($WriteState.IsPresent) {
  $argsList += "--write-state"
}

python @argsList
if ($LASTEXITCODE -ne 0) {
  throw "OpenClaw portfolio report Telegram alert failed: $LASTEXITCODE"
}
