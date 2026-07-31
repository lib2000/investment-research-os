param(
  [string]$ProjectRoot = "",
  [string]$TaskName = "InvestmentResearchOS Local Cleanup",
  [string]$At = "03:30",
  [int]$TempRetentionDays = 14,
  [int]$LogRetentionDays = 30
)

$ErrorActionPreference = "Stop"
$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
$runner = Join-Path $ProjectRootPath "tools\cleanup_local_artifacts.ps1"
if (-not (Test-Path -LiteralPath $runner)) { throw "Local cleanup runner not found: $runner" }

$arguments = @(
  "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass",
  "-File", "`"$runner`"",
  "-ProjectRoot", "`"$ProjectRootPath`"",
  "-TempRetentionDays", "$TempRetentionDays",
  "-LogRetentionDays", "$LogRetentionDays",
  "-Apply"
) -join " "
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 15)
$settings.DisallowStartIfOnBatteries = $false
$settings.StopIfGoingOnBatteries = $false
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Safely removes only regenerable Investment Research OS caches and expired local temporary artifacts." -Force | Out-Null
Write-Host "Registered: $TaskName"
Write-Host "Trigger: daily $At, start when available"
Write-Host "Retention: temp $TempRetentionDays days / logs $LogRetentionDays days"
