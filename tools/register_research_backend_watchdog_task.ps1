param(
  [string]$ProjectRoot = "",
  [string]$TaskName = "InvestmentJournalApp Research Backend Watchdog",
  [string]$At = "00:02",
  [int]$EveryMinutes = 10,
  [int]$Port = 8001
)

$ErrorActionPreference = "Stop"
$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
$Runner = Join-Path $ProjectRootPath "scripts\ensure-research-backend.ps1"
if (-not (Test-Path -LiteralPath $Runner)) {
  throw "Research backend watchdog runner not found: $Runner"
}

$argumentParts = @(
  "-NoProfile",
  "-ExecutionPolicy",
  "Bypass",
  "-File",
  "`"$Runner`"",
  "-ProjectRoot",
  "`"$ProjectRootPath`"",
  "-Port",
  "$Port"
)

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument ($argumentParts -join " ")
$trigger = New-ScheduledTaskTrigger -Once -At $At `
  -RepetitionInterval (New-TimeSpan -Minutes $EveryMinutes) `
  -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 3)

Register-ScheduledTask `
  -TaskName $TaskName `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Description "Keeps the Investment Research OS backend on 127.0.0.1:8001 available for the local console." `
  -Force | Out-Null

Write-Host "Registered: $TaskName"
Write-Host "Start: $At"
Write-Host "RepeatMinutes: $EveryMinutes"
Write-Host "Runner: $Runner"
