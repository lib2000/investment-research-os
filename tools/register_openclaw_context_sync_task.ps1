param(
  [string]$ProjectRoot = "",
  [string]$TaskName = "InvestmentJournalApp OpenClaw Context Sync After Recommendations",
  [string]$At = "07:20"
)

$ErrorActionPreference = "Stop"
$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
$runner = Join-Path $ProjectRootPath "tools\sync_openclaw_investment_context.ps1"
if (-not (Test-Path -LiteralPath $runner)) { throw "OpenClaw sync runner not found: $runner" }

$arguments = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$runner`"") -join " "
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 15)
$settings.DisallowStartIfOnBatteries = $false
$settings.StopIfGoingOnBatteries = $false

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "Refreshes OpenClaw investment context after daily recommendations and catches up when the PC was off." -Force | Out-Null
Write-Host "Registered: $TaskName"
Write-Host "Trigger: daily $At, start when available"
