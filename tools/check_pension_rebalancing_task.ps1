param(
  [string]$TaskName = "InvestmentResearchOS-PensionRebalancingReview-1900",
  [switch]$Json
)

$ErrorActionPreference = "Stop"
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$settings = $task.Settings
$action = $task.Actions | Select-Object -First 1
$result = [ordered]@{
  status = "ok"
  task_name = $task.TaskName
  state = $task.State.ToString()
  start_when_available = [bool]$settings.StartWhenAvailable
  multiple_instances = $settings.MultipleInstances.ToString()
  command = $action.Execute
  arguments = $action.Arguments
  safe_manual_only = (($action.Arguments -match "run_pension_rebalancing\.ps1") -and ($action.Arguments -match "-DueOnly"))
}
if (-not $result.start_when_available -or -not $result.safe_manual_only) {
  $result.status = "needs_action"
}
if ($Json.IsPresent) {
  $result | ConvertTo-Json -Depth 5
} else {
  $result.GetEnumerator() | ForEach-Object { "{0}: {1}" -f $_.Key, $_.Value }
}
if ($result.status -ne "ok") { exit 1 }
