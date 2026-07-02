param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp",
  [string]$BaseUrl = "http://127.0.0.1:8001",
  [string]$DevUserToken = "dev-local-token",
  [switch]$Strict
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
Set-Location -LiteralPath $ProjectRootPath

$script:StatusFailures = @()
$authHeaders = @{ Authorization = "Bearer $DevUserToken" }

function Write-Section {
  param([string]$Title)
  Write-Host ""
  Write-Host "== $Title =="
}

function Add-StatusFailure {
  param([string]$Message)
  $script:StatusFailures += $Message
}

function Get-Utf8ResponseContent {
  param($Response)

  if ($Response -and $Response.RawContentStream) {
    try {
      if ($Response.RawContentStream.CanSeek) {
        $Response.RawContentStream.Position = 0
      }
      $reader = [System.IO.StreamReader]::new(
        $Response.RawContentStream,
        [System.Text.UTF8Encoding]::new($false),
        $true
      )
      try {
        return $reader.ReadToEnd()
      } finally {
        $reader.Dispose()
      }
    } catch {
      return [string]$Response.Content
    }
  }

  return [string]$Response.Content
}

function Invoke-JsonStatus {
  param(
    [string]$Name,
    [string]$Path,
    [hashtable]$Headers = @{},
    [bool]$Required = $true
  )

  $uri = "$BaseUrl$Path"
  try {
    $response = Invoke-WebRequest -Uri $uri -Method Get -Headers $Headers -UseBasicParsing -TimeoutSec 10
    Write-Host "정상 $Name - $uri"
    return (Get-Utf8ResponseContent $response | ConvertFrom-Json)
  } catch {
    if ($Required) {
      Write-Host "실패 $Name - $uri"
      Write-Host "  $($_.Exception.Message)"
      Add-StatusFailure "$Name 실패: $($_.Exception.Message)"
    } else {
      Write-Host "선택 건너뜀 $Name - $uri"
      Write-Host "  $($_.Exception.Message)"
    }
    return $null
  }
}

function Invoke-TextStatus {
  param(
    [string]$Name,
    [string]$Path,
    [string]$RequiredText = ""
  )

  $uri = "$BaseUrl$Path"
  try {
    $response = Invoke-WebRequest -Uri $uri -Method Get -UseBasicParsing -TimeoutSec 10
    $content = Get-Utf8ResponseContent $response
    $response | Add-Member -NotePropertyName DecodedContentLength -NotePropertyValue $content.Length -Force
    Write-Host "정상 $Name - $uri"
    if ($RequiredText -and $content -notlike "*$RequiredText*") {
      Write-Host "주의 $Name 응답에 기대 문구가 없습니다: $RequiredText"
      Add-StatusFailure "$Name 응답에 기대 문구가 없습니다: $RequiredText"
    }
    return $response
  } catch {
    Write-Host "실패 $Name - $uri"
    Write-Host "  $($_.Exception.Message)"
    Add-StatusFailure "$Name 실패: $($_.Exception.Message)"
    return $null
  }
}

Write-Section "연구 콘솔 백엔드 상태"
$root = Invoke-JsonStatus -Name "backend root" -Path "/"
$systemHealth = Invoke-JsonStatus -Name "system health" -Path "/api/v1/system/health"
$provider = Invoke-JsonStatus -Name "data providers" -Path "/api/v1/data-providers/status"
$ocr = Invoke-JsonStatus -Name "ocr status" -Path "/api/v1/ocr/status"
$storageQuality = Invoke-JsonStatus -Name "storage quality" -Path "/api/v1/storage/quality-dashboard" -Headers $authHeaders
$dailyRecommendations = Invoke-JsonStatus -Name "daily recommendations" -Path "/api/v1/daily-recommendations/status" -Headers $authHeaders
$researchAutomation = Invoke-JsonStatus -Name "research automation" -Path "/api/v1/research-automation/status" -Headers $authHeaders
$publicIrSecStatus = Invoke-JsonStatus -Name "public IR/SEC status" -Path "/api/v1/public-ir-sec/status" -Headers $authHeaders
$console = Invoke-TextStatus -Name "classic console" -Path "/console/index.html" -RequiredText "리서치 콘솔"

if ($root -and $root.message) {
  Write-Host "백엔드 메시지: $($root.message)"
}
if ($systemHealth) {
  Write-Host "시스템 상태: $($systemHealth.message)"
  Write-Host "OneDrive 제외: $($systemHealth.onedrive_excluded)"
  Write-Host "OCR 준비: $($systemHealth.ocr_ready)"
}
if ($provider) {
  Write-Host "데이터 프로바이더 모드: $($provider.mode)"
  Write-Host "프로바이더 수: $(@($provider.providers).Count)"
}
if ($ocr) {
  Write-Host "OCR 런타임 상태: $($ocr.status)"
}
if ($storageQuality) {
  Write-Host "저장 데이터 본문 누락: $($storageQuality.body_missing_count)"
  Write-Host "저장 데이터 OCR 필요: $($storageQuality.ocr_needed_count)"
  Write-Host "보관 처리 건수: $($storageQuality.archived_count)"
}
if ($dailyRecommendations) {
  Write-Host "일일 추천 최신일: $($dailyRecommendations.latest_recommendation_date)"
  Write-Host "일일 추천 저장 건수: $($dailyRecommendations.record_count)"
  Write-Host "일일 추천 실행 시각: $($dailyRecommendations.daily_time)"
}
if ($researchAutomation) {
  $dashboardDigest = $researchAutomation.dashboard_digest
  $nextActions = if ($researchAutomation.next_actions) { @($researchAutomation.next_actions) } else { @() }
  if ($dashboardDigest -and $dashboardDigest.next_actions) {
    $nextActions = @($dashboardDigest.next_actions)
  }
  $nextActionCount = $nextActions.Count
  Write-Host "자동화 상태: $($researchAutomation.status)"
  Write-Host "자동화 다음 조치: $nextActionCount"
  foreach ($nextAction in ($nextActions | Select-Object -First 5)) {
    Write-Host "자동화 조치: $nextAction"
  }
  if ($dashboardDigest) {
    $priorityNewsCount = if ($dashboardDigest.news_priority_preview) { @($dashboardDigest.news_priority_preview).Count } else { 0 }
    $totalPriorityNewsCount = if ($dashboardDigest.news_priority_count) { $dashboardDigest.news_priority_count } else { $priorityNewsCount }
    Write-Host "우선 뉴스: 표시 $($priorityNewsCount)개/전체 $($totalPriorityNewsCount)개, 중복 후보 $($dashboardDigest.news_duplicate_priority_group_count)묶음/$($dashboardDigest.news_duplicate_priority_entry_count)개"
    $duplicatePriorityGroups = if ($dashboardDigest.news_duplicate_priority_groups) { @($dashboardDigest.news_duplicate_priority_groups) } else { @() }
    foreach ($group in $duplicatePriorityGroups | Select-Object -First 3) {
      $groupTitle = "제목 미확인"
      if ($group.titles) {
        $firstTitle = $group.titles | Select-Object -First 1
        if ($firstTitle) {
          $groupTitle = [string]$firstTitle
        }
      }
      Write-Host "우선 뉴스 중복 후보: $($group.count)개 | $($group.canonical_url) | $groupTitle"
    }
    $npsPlan = $dashboardDigest.nps_domestic_equity_rebalance_plan
    if ($npsPlan) {
      $reduceCandidates = if ($npsPlan.candidates -and $npsPlan.candidates.reduce) {
        @($npsPlan.candidates.reduce)
      } elseif ($npsPlan.reduce_candidates) {
        @($npsPlan.reduce_candidates)
      } else {
        @()
      }
      $reduceCandidateCount = $reduceCandidates.Count
      $reductionNeeded = if ($npsPlan.reduction_needed_value) {
        "{0:N0}" -f [double]$npsPlan.reduction_needed_value
      } else {
        "0"
      }
      Write-Host "국민연금 14% 계획: $($npsPlan.status), 축소 필요 $($reductionNeeded)원, 축소 후보 $($reduceCandidateCount)개"
      foreach ($candidate in ($reduceCandidates | Select-Object -First 3)) {
        $candidateValue = if ($candidate.market_value) {
          "{0:N0}" -f [double]$candidate.market_value
        } else {
          "0"
        }
        $candidateName = if ($candidate.holding_name) {
          $candidate.holding_name
        } elseif ($candidate.name) {
          $candidate.name
        } else {
          "-"
        }
        Write-Host "국민연금 축소 후보: $($candidate.ticker) | $($candidateName) | $($candidateValue)원"
      }
    }
  }
  if ($researchAutomation.status -and $researchAutomation.status -ne "success") {
    Add-StatusFailure "research automation 상태가 success가 아닙니다: $($researchAutomation.status)"
  }
}
if ($publicIrSecStatus) {
  $needsBodyEntries = if ($publicIrSecStatus.needs_body_copy_entries) { @($publicIrSecStatus.needs_body_copy_entries) } else { @() }
  Write-Host "공개 IR/SEC: 전체 $($publicIrSecStatus.entry_count)건, 본문 보강 플래그 $($publicIrSecStatus.needs_body_copy_count)건"
  foreach ($entry in $needsBodyEntries | Select-Object -First 3) {
    $entryTitle = if ($entry.title) { $entry.title } elseif ($entry.file_name) { $entry.file_name } else { "제목 미확인" }
    $entryPath = if ($entry.relative_path) { $entry.relative_path } elseif ($entry.source_url) { $entry.source_url } else { "경로 미확인" }
    Write-Host "공개 IR/SEC 보강 대상: $($entry.ticker) | $entryTitle | $entryPath"
  }
  if ($publicIrSecStatus.status -and $publicIrSecStatus.status -ne "success") {
    Add-StatusFailure "public IR/SEC 상태가 success가 아닙니다: $($publicIrSecStatus.status)"
  }
}
if ($console) {
  $consoleSize = if ($console.RawContentLength) { $console.RawContentLength } else { $console.DecodedContentLength }
  Write-Host "콘솔 HTML 크기: $consoleSize bytes"
}

Write-Section "점검 요약"
if ($script:StatusFailures.Count -eq 0) {
  Write-Host "정상 연구 콘솔 상태 점검 통과"
} else {
  foreach ($failure in $script:StatusFailures) {
    Write-Host "주의 $failure"
  }
  if ($Strict) {
    throw "연구 콘솔 상태 점검 실패: $($script:StatusFailures.Count)건"
  }
}
