param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp",
  [string]$ApiBaseUrl = "http://127.0.0.1:8010",
  [int]$ApiPort = 8010,
  [int[]]$FallbackApiPorts = @(8020, 8021, 8022),
  [string]$DevUserToken = "dev-local-token",
  [string]$StartDate = (Get-Date -Day 1).ToString("yyyy-MM-dd"),
  [string]$EndDate = (Get-Date).ToString("yyyy-MM-dd"),
  [int]$MaxRangeDays = 31,
  [int]$MaxPollSeconds = 900,
  [int]$PollIntervalSeconds = 5,
  [switch]$ConfirmLiveApi,
  [switch]$CheckTokenFirst,
  [switch]$NoCancelOnTimeout
)

$ErrorActionPreference = "Stop"

$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
Set-Location -LiteralPath $ProjectRootPath

function Assert-Condition {
  param(
    [bool]$Condition,
    [string]$Message
  )

  if (-not $Condition) {
    throw $Message
  }
}

function Convert-ToKiwoomDate {
  param([string]$Value)

  $text = if ($null -ne $Value) { $Value.Trim() } else { "" }
  if ($text -match "^\d{8}$") {
    return $text
  }
  if ($text -match "^\d{4}-\d{2}-\d{2}$") {
    return $text.Replace("-", "")
  }
  throw "StartDate/EndDate는 YYYY-MM-DD 또는 YYYYMMDD 형식이어야 합니다: $Value"
}

function Convert-ToDisplayDate {
  param([string]$Yyyymmdd)

  return "$($Yyyymmdd.Substring(0, 4))-$($Yyyymmdd.Substring(4, 2))-$($Yyyymmdd.Substring(6, 2))"
}

function Convert-ToDateOnly {
  param([string]$Yyyymmdd)

  return [datetime]::ParseExact($Yyyymmdd, "yyyyMMdd", [System.Globalization.CultureInfo]::InvariantCulture).Date
}

function Invoke-ApiJson {
  param(
    [string]$Name,
    [string]$Method,
    [string]$Uri,
    [hashtable]$Headers = @{}
  )

  try {
    return Invoke-RestMethod -Uri $Uri -Method $Method -Headers $Headers -TimeoutSec 30
  } catch {
    throw "$Name 호출 실패: $($_.Exception.Message)"
  }
}

function Test-KiwoomHistoryApi {
  param([string]$BaseUrl)

  $root = Invoke-ApiJson -Name "backend root" -Method Get -Uri "$BaseUrl/"
  if ($root.message -notlike "*정상 작동*") {
    throw "백엔드 루트 응답이 예상과 다릅니다."
  }
  $status = Invoke-ApiJson -Name "brokerage status" -Method Get -Uri "$BaseUrl/api/v1/brokerage/status"
  if ([string]$status.first_integration_target -ne "KIWOOM") {
    throw "첫 연동 증권사가 KIWOOM이 아닙니다."
  }
  return $true
}

function Resolve-ApiBaseUrl {
  $apiBaseUrlExplicit = $PSBoundParameters.ContainsKey("ApiBaseUrl")
  try {
    Test-KiwoomHistoryApi -BaseUrl $ApiBaseUrl | Out-Null
    return $ApiBaseUrl
  } catch {
    if ($apiBaseUrlExplicit) {
      throw
    }
    $primaryError = $_.Exception.Message
    foreach ($fallbackApiPort in $FallbackApiPorts) {
      if ($fallbackApiPort -eq $ApiPort) {
        continue
      }
      $fallbackBaseUrl = "http://127.0.0.1:$fallbackApiPort"
      Write-Host "WARN primary API 확인 실패: $primaryError"
      Write-Host "fallback API 확인: $fallbackBaseUrl"
      try {
        Test-KiwoomHistoryApi -BaseUrl $fallbackBaseUrl | Out-Null
        Write-Host "OK fallback API 사용: $fallbackBaseUrl"
        return $fallbackBaseUrl
      } catch {
        Write-Host "WARN fallback API 실패: $($_.Exception.Message)"
      }
    }
    throw "기본 API와 fallback API를 확인하지 못했습니다. 기본 오류: $primaryError"
  }
}

if (-not $ConfirmLiveApi) {
  throw @"
키움 라이브 범위 과거 거래 스모크는 실제 키움 API와 로컬 DB를 사용합니다.
실행하려면 명시적으로 -ConfirmLiveApi 를 붙이세요.

예:
  .\tools\smoke_kiwoom_history_range_live.ps1 -StartDate 2026-05-01 -EndDate 2026-05-31 -ConfirmLiveApi

출력에는 토큰 원문과 계좌번호를 표시하지 않습니다.
기본 최대 범위는 $MaxRangeDays 일입니다.
"@
}

$startKiwoomDate = Convert-ToKiwoomDate -Value $StartDate
$endKiwoomDate = Convert-ToKiwoomDate -Value $EndDate
$startDateOnly = Convert-ToDateOnly -Yyyymmdd $startKiwoomDate
$endDateOnly = Convert-ToDateOnly -Yyyymmdd $endKiwoomDate
Assert-Condition ($startDateOnly -le $endDateOnly) "StartDate는 EndDate보다 늦을 수 없습니다."
$rangeDays = [int](($endDateOnly - $startDateOnly).TotalDays + 1)
Assert-Condition ($rangeDays -le $MaxRangeDays) "범위 스모크는 최대 $MaxRangeDays 일까지만 허용합니다: 현재 $rangeDays 일"

$displayStartDate = Convert-ToDisplayDate -Yyyymmdd $startKiwoomDate
$displayEndDate = Convert-ToDisplayDate -Yyyymmdd $endKiwoomDate
$safePollInterval = [Math]::Max($PollIntervalSeconds, 1)
$safeMaxPollSeconds = [Math]::Max($MaxPollSeconds, $safePollInterval)
$baseUrl = Resolve-ApiBaseUrl
$authHeaders = @{ Authorization = "Bearer $DevUserToken" }
$encodedStartDate = [uri]::EscapeDataString($displayStartDate)
$encodedEndDate = [uri]::EscapeDataString($displayEndDate)

Write-Host "키움 라이브 범위 과거 거래 스모크를 시작합니다."
Write-Host "API: $baseUrl"
Write-Host "조회 기간: $displayStartDate ~ $displayEndDate ($rangeDays 일)"
Write-Host "주의: 이 스크립트는 최대 $MaxRangeDays 일 범위만 실행합니다."

$tokenSummary = $null
if ($CheckTokenFirst) {
  $token = Invoke-ApiJson `
    -Name "kiwoom token-test" `
    -Method Post `
    -Uri "$baseUrl/api/v1/brokerage/kiwoom/token-test" `
    -Headers $authHeaders
  $tokenSummary = [pscustomobject]@{
    Source = $token.source
    TokenType = $token.token_type
    ExpiresDt = $token.expires_dt
    HasRefreshToken = [bool]$token.has_refresh_token
    ReturnCode = $token.return_code
    ReturnMessage = $token.return_msg
  }
  Write-Host "OK token-test: source=$($token.source), expires_dt=$($token.expires_dt), has_refresh_token=$($token.has_refresh_token)"
}

$beforeDrafts = Invoke-ApiJson `
  -Name "journal drafts before" `
  -Method Get `
  -Uri "$baseUrl/api/v1/journal/drafts?page=1&page_size=1" `
  -Headers $authHeaders
$draftTotalBefore = if ($null -ne $beforeDrafts.total) { [int]$beforeDrafts.total } else { 0 }

$startResponse = Invoke-ApiJson `
  -Name "kiwoom history start" `
  -Method Post `
  -Uri "$baseUrl/api/v1/sync/kiwoom/history/start?start_date=$encodedStartDate&end_date=$encodedEndDate" `
  -Headers $authHeaders

$jobId = [int]$startResponse.job.id
Assert-Condition ($jobId -gt 0) "과거 거래 job id를 받지 못했습니다."
Write-Host "OK history job accepted: job_id=$jobId"

$deadline = (Get-Date).AddSeconds($safeMaxPollSeconds)
$terminalStatuses = @("success", "failed", "cancelled", "paused")
$jobResponse = $null
while ((Get-Date) -lt $deadline) {
  $jobResponse = Invoke-ApiJson `
    -Name "kiwoom history job" `
    -Method Get `
    -Uri "$baseUrl/api/v1/sync/kiwoom/history/jobs/$jobId" `
    -Headers $authHeaders
  $status = [string]$jobResponse.job.status
  Write-Host ("job {0}: status={1}, processed={2}/{3}, retry={4}, next={5}" -f `
    $jobId,
    $status,
    $jobResponse.job.processed_days,
    $jobResponse.job.total_days,
    $jobResponse.job.retry_count,
    $jobResponse.job.next_date)
  if ($terminalStatuses -contains $status) {
    break
  }
  Start-Sleep -Seconds $safePollInterval
}

if (-not $jobResponse) {
  throw "job 상태를 확인하지 못했습니다: $jobId"
}

if (-not ($terminalStatuses -contains [string]$jobResponse.job.status)) {
  if (-not $NoCancelOnTimeout) {
    Write-Host "WARN 제한 시간 내 완료되지 않아 cancel 요청을 보냅니다: job_id=$jobId"
    $jobResponse = Invoke-ApiJson `
      -Name "kiwoom history cancel" `
      -Method Post `
      -Uri "$baseUrl/api/v1/sync/kiwoom/history/jobs/$jobId/cancel" `
      -Headers $authHeaders
  }
}

$afterDrafts = Invoke-ApiJson `
  -Name "journal drafts after" `
  -Method Get `
  -Uri "$baseUrl/api/v1/journal/drafts?page=1&page_size=1" `
  -Headers $authHeaders
$draftTotalAfter = if ($null -ne $afterDrafts.total) { [int]$afterDrafts.total } else { 0 }

$summary = [pscustomobject]@{
  Status = "completed"
  ApiBaseUrl = $baseUrl
  StartDate = $displayStartDate
  EndDate = $displayEndDate
  RangeDays = $rangeDays
  JobId = $jobId
  JobStatus = $jobResponse.job.status
  ProcessedDays = $jobResponse.job.processed_days
  TotalDays = $jobResponse.job.total_days
  ProgressRate = $jobResponse.job.progress_rate
  JournalItems = $jobResponse.job.total_journal_items_count
  OrderExecutions = $jobResponse.job.total_order_executions_count
  NeedsReview = $jobResponse.job.total_needs_review_count
  RetryCount = $jobResponse.job.retry_count
  LastBackoffSeconds = $jobResponse.job.last_backoff_seconds
  LastSuccessDate = $jobResponse.job.last_success_date
  NextDate = $jobResponse.job.next_date
  DraftTotalBefore = $draftTotalBefore
  DraftTotalAfter = $draftTotalAfter
  DraftDelta = ($draftTotalAfter - $draftTotalBefore)
  Token = $tokenSummary
}

Write-Host ""
Write-Host "키움 라이브 범위 과거 거래 스모크 결과"
$summary | ConvertTo-Json -Depth 6

if ($jobResponse.job.status -eq "failed") {
  throw "키움 과거 거래 job 실패: $($jobResponse.job.error_message)"
}

Write-Host "스모크 완료"
