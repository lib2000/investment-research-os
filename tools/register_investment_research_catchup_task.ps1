param(
  [string]$ProjectRoot = "",
  [string]$TaskName = "InvestmentResearchOS Boot Catch-up",
  [string]$CredentialTarget = "InvestmentResearchOS/DEV_USER_TOKEN",
  [int]$DelayMinutes = 2
)

$ErrorActionPreference = "Stop"
$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
$runner = Join-Path $ProjectRootPath "tools\run_investment_research_catchup.ps1"
if (-not (Test-Path -LiteralPath $runner)) { throw "Catch-up runner not found: $runner" }

$arguments = @(
  "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass",
  "-File", "`"$runner`"",
  "-ProjectRoot", "`"$ProjectRootPath`"",
  "-CredentialTarget", "`"$CredentialTarget`""
) -join " "
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments
$trigger = New-ScheduledTaskTrigger -AtLogOn -User ([Environment]::UserName)
$trigger.Delay = "PT$([Math]::Max($DelayMinutes, 0))M"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 15)
$settings.DisallowStartIfOnBatteries = $false
$settings.StopIfGoingOnBatteries = $false
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "After sign-in, safely catches up missed Investment Research OS data work without sending messages or placing trades." -Force | Out-Null
Write-Host "Registered: $TaskName"
Write-Host "Trigger: current user logon + $DelayMinutes minute delay"
Write-Host "Runner: $runner"
