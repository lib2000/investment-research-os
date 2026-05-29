param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp",
  [string]$BaseUrl = "http://127.0.0.1:8001",
  [string]$DevUserToken = "dev-local-token",
  [string]$StartYymm = "202605",
  [string]$EndYymm = "202605",
  [switch]$RequireTotalTrendAuthorized
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
$customsDir = Join-Path $ProjectRootPath "research_vault\CUSTOMS"

function Get-CustomsVaultFileCount {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) {
    return 0
  }
  return @(Get-ChildItem -LiteralPath $Path -Force).Count
}

$headers = @{ Authorization = "Bearer $DevUserToken" }
$customsDirExistsBefore = Test-Path -LiteralPath $customsDir
$beforeCount = Get-CustomsVaultFileCount -Path $customsDir

$latestUri = "$BaseUrl/api/v1/macro/customs-trade/latest?start_yymm=$StartYymm&end_yymm=$EndYymm&save_result=true"
$totalTrendUri = "$BaseUrl/api/v1/macro/customs-trade/total-trend/status?start_yymm=$StartYymm&end_yymm=$EndYymm"

try {
  $latest = Invoke-RestMethod -Headers $headers -Uri $latestUri -TimeoutSec 45
  $totalTrend = Invoke-RestMethod -Headers $headers -Uri $totalTrendUri -TimeoutSec 30
} catch {
  $afterCount = Get-CustomsVaultFileCount -Path $customsDir
  $customsDirExistsAfter = Test-Path -LiteralPath $customsDir
  $customsDirCreatedDuringCheck = (-not $customsDirExistsBefore) -and $customsDirExistsAfter
  $customsFileCountChanged = $afterCount -ne $beforeCount
  $result = [pscustomobject]@{
    Status = "warning"
    BaseUrl = $BaseUrl
    Period = "$StartYymm~$EndYymm"
    Reason = "provider_timeout_or_unavailable"
    Error = $_.Exception.Message
    CustomsDirExistsBefore = [bool]$customsDirExistsBefore
    CustomsDirExistsAfter = [bool]$customsDirExistsAfter
    CustomsDirCreatedDuringCheck = [bool]$customsDirCreatedDuringCheck
    CustomsFilesBefore = $beforeCount
    CustomsFilesAfter = $afterCount
    CustomsFileCountChanged = [bool]$customsFileCountChanged
    NextAction = "관세청 제공자 지연으로 품질 점검을 보류했습니다. 기존 CUSTOMS 저장 파일 수가 바뀌지 않았는지만 확인하고 다음 자동 점검에서 재시도하세요."
  }
  if ($customsFileCountChanged -or $customsDirCreatedDuringCheck) {
    $result.Status = "failed"
    $result | ConvertTo-Json -Depth 6
    throw "관세청 수출입 데이터 품질 점검 중 저장소 변경이 감지되었습니다."
  }
  $result | ConvertTo-Json -Depth 6
  return
}

$afterCount = Get-CustomsVaultFileCount -Path $customsDir
$customsDirExistsAfter = Test-Path -LiteralPath $customsDir
$customsDirCreatedDuringCheck = (-not $customsDirExistsBefore) -and $customsDirExistsAfter
$customsFileCountChanged = $afterCount -ne $beforeCount
$latestHasTotalTrendStatus = $latest.PSObject.Properties.Name -contains "total_trend_status"
$totalHasStorage = $totalTrend.PSObject.Properties.Name -contains "storage"
$latestNextAction = if ($latestHasTotalTrendStatus) { $latest.total_trend_status.next_action } else { $null }

$result = [pscustomobject]@{
  Status = "success"
  BaseUrl = $BaseUrl
  Period = "$StartYymm~$EndYymm"
  CustomsDirExistsBefore = [bool]$customsDirExistsBefore
  CustomsDirExistsAfter = [bool]$customsDirExistsAfter
  CustomsDirCreatedDuringCheck = [bool]$customsDirCreatedDuringCheck
  CustomsFilesBefore = $beforeCount
  CustomsFilesAfter = $afterCount
  CustomsFileCountChanged = [bool]$customsFileCountChanged
  LatestStatus = $latest.status
  LatestDataQuality = $latest.data_quality
  LatestStorageSkipped = [bool]$latest.storage_skipped
  LatestHasTotalTrendStatus = [bool]$latestHasTotalTrendStatus
  LatestNextAction = $latestNextAction
  TotalTrendStatus = $totalTrend.status
  TotalTrendAuthorized = [bool]$totalTrend.authorized
  TotalTrendHttpStatusCode = $totalTrend.http_status_code
  TotalTrendNextAction = $totalTrend.next_action
  TotalTrendHasStorage = [bool]$totalHasStorage
  RequireTotalTrendAuthorized = [bool]$RequireTotalTrendAuthorized
}

$failures = @()
if ($customsFileCountChanged) {
  $failures += "CUSTOMS 파일 수가 바뀌었습니다: $beforeCount -> $afterCount"
}
if ($customsDirCreatedDuringCheck) {
  $failures += "점검 중 CUSTOMS 폴더가 새로 생성되었습니다."
}
if (-not $latest.storage_skipped -and $latest.data_quality -eq "no_valid_trade_rows") {
  $failures += "실제 수치가 없는 최신 조회가 저장 건너뜀으로 표시되지 않았습니다."
}
if (-not $latestHasTotalTrendStatus) {
  $failures += "최신 조회 결과에 total_trend_status가 없습니다."
}
if ($totalHasStorage) {
  $failures += "총괄 진단 라우트가 storage 필드를 반환했습니다."
}
if ([string]::IsNullOrWhiteSpace([string]$totalTrend.next_action)) {
  $failures += "총괄 진단 next_action이 비어 있습니다."
}
if ($latestHasTotalTrendStatus -and [string]::IsNullOrWhiteSpace([string]$latestNextAction)) {
  $failures += "최신 조회 total_trend_status.next_action이 비어 있습니다."
}
if ($RequireTotalTrendAuthorized -and -not [bool]$totalTrend.authorized) {
  $failures += "수출입총괄(GW) API가 아직 승인 상태가 아닙니다. HTTP=$($totalTrend.http_status_code)"
}

if ($failures.Count -gt 0) {
  $result.Status = "failed"
  $result | Add-Member -NotePropertyName Failures -NotePropertyValue $failures
  $result | ConvertTo-Json -Depth 6
  throw "관세청 수출입 데이터 품질 점검 실패"
}

$result | ConvertTo-Json -Depth 6
