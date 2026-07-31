param(
  [string]$ProjectRoot = "C:\Users\lib20\projects\InvestmentJournalApp",
  [string]$TaskName = "InvestmentResearchOS-Autostart",
  [string]$CredentialTarget = "InvestmentResearchOS/DEV_USER_TOKEN",
  [switch]$StartNow
)

$ErrorActionPreference = "Stop"
$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
$CredentialHelper = Join-Path $ProjectRootPath "tools\investment_research_credential.ps1"
$Runner = Join-Path $ProjectRootPath "scripts\start-investment-research-autostart.ps1"
. $CredentialHelper

if (-not (Test-InvestmentResearchCredential -Target $CredentialTarget)) {
  if ([string]::IsNullOrWhiteSpace($env:DEV_USER_TOKEN)) { throw "DEV_USER_TOKEN이 없습니다. 먼저 안전한 토큰을 설정한 뒤 다시 실행하세요." }
  $plainToken = $env:DEV_USER_TOKEN.Trim()
  $secureToken = ConvertTo-SecureString $plainToken -AsPlainText -Force
  try {
    Set-InvestmentResearchCredential -Target $CredentialTarget -Secret $secureToken
  } finally {
    $plainToken = $null
    $secureToken.Dispose()
  }
}

$argumentParts = @(
  "-NoProfile",
  "-WindowStyle", "Hidden",
  "-ExecutionPolicy", "Bypass",
  "-File", "`"$Runner`"",
  "-ProjectRoot", "`"$ProjectRootPath`"",
  "-CredentialTarget", "`"$CredentialTarget`""
)
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument ($argumentParts -join " ")
$trigger = New-ScheduledTaskTrigger -AtLogOn -User ([Environment]::UserName)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited

Register-ScheduledTask `
  -TaskName $TaskName `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Principal $principal `
  -Description "Starts the local Investment Research OS workbench after the current Windows user signs in. Secrets remain in Windows Credential Manager." `
  -Force | Out-Null

if ($StartNow) {
  Start-ScheduledTask -TaskName $TaskName
}

Write-Host "Registered: $TaskName"
Write-Host "CredentialConfigured: $(Test-InvestmentResearchCredential -Target $CredentialTarget)"
Write-Host "Trigger: current user logon"
Write-Host "Runner: $Runner"
