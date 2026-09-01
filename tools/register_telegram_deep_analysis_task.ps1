param(
  [string]$ProjectRoot = "",
  [string]$TaskName = "InvestmentResearchOS-TelegramDeepAnalysis-0700",
  [string]$At = "07:00",
  [string]$EnvFile = "",
  [switch]$Enable
)

$ErrorActionPreference = "Stop"
$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
$Runner = Join-Path $ProjectRootPath "tools\check_telegram_deep_analysis.py"
if (-not (Test-Path -LiteralPath $Runner)) { throw "Telegram deep-analysis runner not found: $Runner" }
if ([string]::IsNullOrWhiteSpace($EnvFile)) { $EnvFile = Join-Path $ProjectRootPath "backend\.env" }
if (-not [IO.Path]::IsPathRooted($EnvFile)) { $EnvFile = Join-Path $ProjectRootPath $EnvFile }
if (-not (Test-Path -LiteralPath $EnvFile)) { throw "Telegram env file not found: $EnvFile" }
$resultPath = Join-Path $ProjectRootPath "research_vault\_system\telegram_deep_analysis_latest.json"

# The runner's --submit preflight is intentional: a scheduled task must never
# silently downgrade a requested live channel post into a dry-run.
$python = Join-Path $ProjectRootPath ".venv-win\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) { throw "Project Python not found: $python" }
$arguments = @(
  "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass",
  "-Command", "& '$python' '$Runner' --env-file '$EnvFile' --live-fetch --submit --output-json '$resultPath'"
) -join " "
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet `
  -StartWhenAvailable `
  -MultipleInstances IgnoreNew `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 45) `
  -RestartCount 2 `
  -RestartInterval (New-TimeSpan -Minutes 15) `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal `
  -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) `
  -LogonType Interactive `
  -RunLevel Limited
$description = "Publishes the 07:00 Telegram deep-analysis report from explicitly configured channels. It stops on missing live-delivery configuration and never places trades."
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $description -Force | Out-Null
if (-not $Enable.IsPresent) {
  Disable-ScheduledTask -TaskName $TaskName | Out-Null
}

Write-Host "Registered: $TaskName"
Write-Host "Trigger: daily $At, start when available"
Write-Host "Runner: $Runner"
Write-Host "Env file: $EnvFile"
Write-Host "Result: $resultPath"
if ($Enable.IsPresent) {
  Write-Host "State: enabled for live delivery"
} else {
  Write-Host "State: disabled by default. Review a dry-run first; use -Enable only after approving live delivery."
}
