param(
  [string]$ProjectRoot = "",
  [string]$TaskName = "InvestmentJournalApp OpenClaw Answer Capture Cycle",
  [string]$At = "00:05",
  [int]$EveryMinutes = 15,
  [switch]$Collect,
  [switch]$ArchiveFailures
)

$ErrorActionPreference = "Stop"
$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
$runner = Join-Path $ProjectRootPath "tools\run_openclaw_answer_capture_cycle.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
  throw "OpenClaw answer capture cycle runner not found: $runner"
}

$argumentParts = @(
  "-NoProfile",
  "-ExecutionPolicy",
  "Bypass",
  "-File",
  "`"$runner`"",
  "-ProjectRoot",
  "`"$ProjectRootPath`"",
  "-WriteState"
)
if ($Collect.IsPresent) {
  $argumentParts += "-Collect"
}
if ($ArchiveFailures.IsPresent) {
  $argumentParts += "-ArchiveFailures"
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument ($argumentParts -join " ")
$trigger = New-ScheduledTaskTrigger -Once -At $At `
  -RepetitionInterval (New-TimeSpan -Minutes $EveryMinutes) `
  -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
$settings.DisallowStartIfOnBatteries = $false
$settings.StopIfGoingOnBatteries = $false

Register-ScheduledTask `
  -TaskName $TaskName `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Description "OpenClaw collects pending actual-answer files into audited Investment Research captures." `
  -Force | Out-Null

Write-Host "Registered: $TaskName"
Write-Host "Start: $At"
Write-Host "RepeatMinutes: $EveryMinutes"
Write-Host "Runner: $runner"
Write-Host Collect $Collect.IsPresent ArchiveFailures $ArchiveFailures.IsPresent
