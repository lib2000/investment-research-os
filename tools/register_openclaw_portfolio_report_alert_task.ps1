param(
  [string]$ProjectRoot = "",
  [string]$TaskName = "InvestmentJournalApp OpenClaw Portfolio Report Alert",
  [string]$At = "07:00",
  [int]$LookbackDays = 3,
  [int]$MaxItems = 8,
  [switch]$Enabled,
  [switch]$Submit,
  [switch]$SendEmpty
)

$ErrorActionPreference = "Stop"
$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
$runner = Join-Path $ProjectRootPath "tools\run_openclaw_portfolio_report_alert.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
  throw "Portfolio report alert runner not found: $runner"
}

$argumentParts = @(
  "-NoProfile",
  "-ExecutionPolicy",
  "Bypass",
  "-File",
  "`"$runner`"",
  "-ProjectRoot",
  "`"$ProjectRootPath`"",
  "-LookbackDays",
  "$LookbackDays",
  "-MaxItems",
  "$MaxItems",
  "-WriteState"
)
if ($SendEmpty.IsPresent) {
  $argumentParts += "-SendEmpty"
}
if ($Enabled.IsPresent) {
  $argumentParts += "-Enabled"
}
if ($Submit.IsPresent) {
  $argumentParts += "-Submit"
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument ($argumentParts -join " ")
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 20)
$settings.DisallowStartIfOnBatteries = $false
$settings.StopIfGoingOnBatteries = $false

Register-ScheduledTask `
  -TaskName $TaskName `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Description "OpenClaw sends Telegram alerts only when new current-portfolio holding reports are found." `
  -Force | Out-Null

Write-Host "등록 완료: $TaskName"
Write-Host "실행 시각: 매일 $At"
Write-Host "실행 파일: $runner"
Write-Host "빈 결과 알림: Enabled=$($SendEmpty.IsPresent)"
Write-Host "실제 전송: Enabled=$($Enabled.IsPresent), Submit=$($Submit.IsPresent)"
