param(
  [string]$ProjectRoot = "",
  [string]$TaskName = "InvestmentResearchOS-DailyStrategyValidation-0845",
  [string]$At = "08:45",
  [string]$CredentialTarget = "InvestmentResearchOS/DEV_USER_TOKEN"
)

$ErrorActionPreference = "Stop"
$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
$Runner = Join-Path $ProjectRootPath "tools\run_daily_strategy_validation.ps1"
if (-not (Test-Path -LiteralPath $Runner)) { throw "Daily strategy validation runner not found: $Runner" }
. (Join-Path $ProjectRootPath "tools\investment_research_credential.ps1")
if (-not (Test-InvestmentResearchCredential -Target $CredentialTarget)) {
  throw "Windows Credential Manager credential is missing: $CredentialTarget"
}

$arguments = @(
  "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass",
  "-File", "`"$Runner`"",
  "-ProjectRoot", "`"$ProjectRootPath`"",
  "-CredentialTarget", "`"$CredentialTarget`"",
  "-StartServicesIfNeeded"
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

$description = "Validates the daily SMA strategy design, runs one simulation backtest, and stores the result in Research OS. Never places live orders."
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered: $TaskName"
Write-Host "Trigger: daily $At, start when available"
Write-Host "Retry: up to 2 times at 15-minute intervals after failure"
Write-Host "Runner: $Runner"
