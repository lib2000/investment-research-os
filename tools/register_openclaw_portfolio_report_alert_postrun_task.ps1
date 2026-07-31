param(
  [string]$ProjectRoot = "",
  [string]$TaskName = "InvestmentJournalApp OpenClaw Portfolio Report Alert Postrun",
  [string]$At = "07:10",
  [int]$MaxStateAgeHours = 2,
  [switch]$Enabled,
  [switch]$Submit,
  [switch]$NotifyOk
)

$ErrorActionPreference = "Stop"
$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
$runner = Join-Path $ProjectRootPath "tools\run_openclaw_portfolio_report_alert_postrun.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
  throw "Portfolio report alert post-run runner not found: $runner"
}

$argumentParts = @(
  "-NoProfile",
  "-ExecutionPolicy",
  "Bypass",
  "-File",
  "`"$runner`"",
  "-ProjectRoot",
  "`"$ProjectRootPath`"",
  "-MaxStateAgeHours",
  "$MaxStateAgeHours",
  "-WriteState"
)
if ($Enabled.IsPresent) {
  $argumentParts += "-Enabled"
}
if ($Submit.IsPresent) {
  $argumentParts += "-Submit"
}
if ($NotifyOk.IsPresent) {
  $argumentParts += "-NotifyOk"
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument ($argumentParts -join " ")
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

Register-ScheduledTask `
  -TaskName $TaskName `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Description "OpenClaw verifies the 07:00 portfolio report alert and sends Telegram failure notices to @lib20_bot." `
  -Force | Out-Null

Write-Host "등록 완료: $TaskName"
Write-Host "실행 시각: 매일 $At"
Write-Host "실행 파일: $runner"
Write-Host "실패 알림: Enabled=$($Enabled.IsPresent), Submit=$($Submit.IsPresent), NotifyOk=$($NotifyOk.IsPresent)"
