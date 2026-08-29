param(
  [string]$ProjectRoot = "",
  [string]$TaskName = "InvestmentResearchOS-PensionRebalancingReview-1900",
  [string]$At = "19:00"
)

$ErrorActionPreference = "Stop"
$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
$Runner = Join-Path $ProjectRootPath "tools\run_pension_rebalancing.ps1"
if (-not (Test-Path -LiteralPath $Runner)) { throw "Pension rebalancing runner not found: $Runner" }

$arguments = @(
  "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass",
  "-File", "`"$Runner`"",
  "-ProjectRoot", "`"$ProjectRootPath`"",
  "-DueOnly"
) -join " "
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments
# A daily trigger plus the runner's period ledger covers missed month/quarter
# checks after a shutdown, unlike a monthly trigger that can be skipped forever.
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet `
  -StartWhenAvailable `
  -MultipleInstances IgnoreNew `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 20) `
  -RestartCount 2 `
  -RestartInterval (New-TimeSpan -Minutes 15) `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal `
  -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) `
  -LogonType Interactive `
  -RunLevel Limited

$description = "Checks monthly/quarterly pension allocation drift after 19:00, catches up after missed runs, saves a manual-review report, and never calls a broker order endpoint."
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered: $TaskName"
Write-Host "Trigger: daily $At (monthly/quarterly ledger decides when to run)"
Write-Host "Catch-up: StartWhenAvailable enabled"
Write-Host "Runner: $Runner"
