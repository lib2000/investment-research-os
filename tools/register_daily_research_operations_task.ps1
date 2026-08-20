param(
  [string]$ProjectRoot = "",
  [string]$TaskName = "InvestmentResearchOS-DailyResearchOperations-1830",
  [string]$At = "18:30",
  [string]$CredentialTarget = "InvestmentResearchOS/DEV_USER_TOKEN"
)

$ErrorActionPreference = "Stop"
$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
$Runner = Join-Path $ProjectRootPath "tools\run_daily_research_operations.ps1"
if (-not (Test-Path -LiteralPath $Runner)) { throw "Daily research operations runner not found: $Runner" }
. (Join-Path $ProjectRootPath "tools\investment_research_credential.ps1")
if (-not (Test-InvestmentResearchCredential -Target $CredentialTarget)) {
  throw "Windows Credential Manager credential is missing: $CredentialTarget"
}

$arguments = @(
  "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass",
  "-File", "`"$Runner`"",
  "-ProjectRoot", "`"$ProjectRootPath`"",
  "-CredentialTarget", "`"$CredentialTarget`""
) -join " "
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet `
  -StartWhenAvailable `
  -MultipleInstances IgnoreNew `
  -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
  -RestartCount 2 `
  -RestartInterval (New-TimeSpan -Minutes 20) `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal `
  -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) `
  -LogonType Interactive `
  -RunLevel Limited

$description = "Refreshes persisted end-of-day portfolio prices and daily research data without sending Telegram messages or placing live orders; catches up after the next sign-in when missed."
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered: $TaskName"
Write-Host "Trigger: daily $At, start when available"
Write-Host "Runner: $Runner"
