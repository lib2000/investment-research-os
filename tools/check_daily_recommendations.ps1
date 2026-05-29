param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp",
  [string]$BaseUrl = "http://127.0.0.1:8001",
  [string]$DevUserToken = "dev-local-token",
  [int]$MinimumLatestRecords = 3,
  [switch]$Strict
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
Set-Location -LiteralPath $ProjectRootPath

$headers = @{ Authorization = "Bearer $DevUserToken" }
$uri = "$BaseUrl/api/v1/daily-recommendations/status"

try {
  $status = Invoke-RestMethod -Uri $uri -Method Get -Headers $headers -TimeoutSec 30
} catch {
  throw "일일 추천 상태 조회 실패: $($_.Exception.Message)"
}

function Get-ValueOrDefault {
  param(
    [object]$Value,
    [object]$DefaultValue
  )
  if ($null -eq $Value) {
    return $DefaultValue
  }
  return $Value
}

$latestRecords = @($status.latest_records)
$records = @($status.records)
$milestones = @(
  foreach ($record in $latestRecords) {
    foreach ($milestone in @($record.tracking_milestones)) {
      if ($null -ne $milestone) {
        $milestone
      }
    }
  }
)
$missingCoreFields = @(
  foreach ($record in $latestRecords) {
    $missing = @()
    if ([string]::IsNullOrWhiteSpace([string]$record.company_name)) { $missing += "company_name" }
    if (-not $record.rank) { $missing += "rank" }
    if (@($record.reasons).Count -eq 0) { $missing += "reasons" }
    if (@($record.evidence_sources).Count -eq 0) { $missing += "evidence_sources" }
    if ($missing.Count -gt 0) {
      [pscustomobject]@{
        CompanyName = [string](Get-ValueOrDefault $record.company_name "")
        Ticker = [string](Get-ValueOrDefault $record.ticker "")
        Missing = @($missing)
      }
    }
  }
)

$enabledOk = [bool]$status.enabled
$latestCountOk = $latestRecords.Count -ge $MinimumLatestRecords
$storageOk = -not [string]::IsNullOrWhiteSpace([string]$status.storage_path)
$milestoneOk = $milestones.Count -ge ($MinimumLatestRecords * 5)
$coreFieldsOk = $missingCoreFields.Count -eq 0
$trackingConfigOk = [bool]$status.tracking_enabled

$allOk = $enabledOk -and $latestCountOk -and $storageOk -and $milestoneOk -and $coreFieldsOk -and $trackingConfigOk

$result = [pscustomobject]@{
  Status = if ($allOk) { "success" } else { "warning" }
  Module = $status.module
  Enabled = [bool]$status.enabled
  TrackingEnabled = [bool]$status.tracking_enabled
  DailyTime = [string](Get-ValueOrDefault $status.daily_time "")
  DueNow = [bool]$status.due_now
  LatestRecommendationDate = [string](Get-ValueOrDefault $status.latest_recommendation_date "")
  RecordCount = [int](Get-ValueOrDefault $status.record_count 0)
  LatestRecordCount = $latestRecords.Count
  MinimumLatestRecords = $MinimumLatestRecords
  MilestoneCount = $milestones.Count
  StoragePath = [string](Get-ValueOrDefault $status.storage_path "")
  MissingCoreFields = @($missingCoreFields)
  State = $status.state
  Message = if ($allOk) {
    "일일 추천 1~3위와 사후 추적 저장 상태 확인 완료"
  } else {
    "일일 추천/추적 저장 상태 확인 필요"
  }
}

$json = $result | ConvertTo-Json -Depth 6
Write-Output $json

if ($Strict -and -not $allOk) {
  throw $result.Message
}
