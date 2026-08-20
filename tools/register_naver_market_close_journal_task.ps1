param(
  [string]$ProjectRoot = "",
  [string]$TaskName = "InvestmentResearchOS-NaverMarketCloseJournal-0830",
  [string]$At = "08:30",
  [string]$CredentialTarget = "InvestmentResearchOS/DEV_USER_TOKEN"
)

$ErrorActionPreference = "Stop"
$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
$runner = Join-Path $ProjectRootPath "tools\run_naver_market_close_journal.ps1"
if (-not (Test-Path -LiteralPath $runner)) { throw "Naver market-close runner not found: $runner" }
. (Join-Path $ProjectRootPath "tools\investment_research_credential.ps1")
if (-not (Test-InvestmentResearchCredential -Target $CredentialTarget)) {
  throw "Windows Credential Manager 자격 증명이 없습니다: $CredentialTarget"
}

$arguments = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$runner`"", "-Port", "8001", "-CredentialTarget", "`"$CredentialTarget`"", "-StartBackendIfNeeded") -join " "
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
$settings.DisallowStartIfOnBatteries = $false
$settings.StopIfGoingOnBatteries = $false
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Creates the daily Naver market-close journal and catches up after the next sign-in when the PC was off." -Force | Out-Null
Write-Host "Registered: $TaskName"
Write-Host "Trigger: daily $At, start when available"
