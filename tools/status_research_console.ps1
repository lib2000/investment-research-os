param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp",
  [string]$BaseUrl = "http://127.0.0.1:8001",
  [string]$DevUserToken = "dev-local-token",
  [int]$MaxMarketJournalSessionAgeDays = 7,
  [double]$MaxRecommendationPreviewAgeHours = 12.0,
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

function Limit-StatusText {
  param(
    [string]$Text,
    [int]$MaxLength = 120
  )

  if ([string]::IsNullOrWhiteSpace($Text)) {
    return ""
  }
  $normalized = ($Text -replace "\s+", " ").Trim()
  if ($normalized.Length -le $MaxLength) {
    return $normalized
  }
  return "$($normalized.Substring(0, $MaxLength))..."
}

function Read-OptionalJsonFile {
  param(
    [string]$Name,
    [string]$Path
  )

  if (-not (Test-Path -LiteralPath $Path)) {
    Write-Host "선택 건너뜀 $Name - $Path"
    return $null
  }
  try {
    return (Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json)
  } catch {
    Write-Host "주의 $Name JSON 파싱 실패: $($_.Exception.Message)"
    Add-StatusFailure "$Name JSON 파싱 실패: $($_.Exception.Message)"
    return $null
  }
}

function Get-SessionAgeDays {
  param([string]$SessionDate)

  if ([string]::IsNullOrWhiteSpace($SessionDate)) {
    return $null
  }
  try {
    $parsed = [datetime]::Parse($SessionDate).Date
    return [int](([datetime]::Today - $parsed).TotalDays)
  } catch {
    return $null
  }
}

function Format-LocalDateTime {
  param([string]$DateTimeText)

  if ([string]::IsNullOrWhiteSpace($DateTimeText)) {
    return ""
  }
  try {
    return ([datetimeoffset]::Parse($DateTimeText).ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss zzz"))
  } catch {
    return $DateTimeText
  }
}

function Get-DateTimeAgeHours {
  param([string]$DateTimeText)

  if ([string]::IsNullOrWhiteSpace($DateTimeText)) {
    return $null
  }
  try {
    $parsed = [datetimeoffset]::Parse($DateTimeText)
    return [double](([datetimeoffset]::Now - $parsed).TotalHours)
  } catch {
    return $null
  }
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
$marketJournal = Read-OptionalJsonFile -Name "market close journal" -Path (Join-Path $ProjectRootPath "research_vault\_system\market_close_journal.json")
$naverKrMarketJournalState = Read-OptionalJsonFile -Name "naver KR market journal state" -Path (Join-Path $ProjectRootPath "research_vault\_system\naver_market_close_journal_state.json")
$telegramUsMarketJournalState = Read-OptionalJsonFile -Name "telegram US market journal state" -Path (Join-Path $ProjectRootPath "research_vault\_system\telegram_market_close_journal_state.json")
$storageDuplicateReview = Read-OptionalJsonFile -Name "storage duplicate review" -Path (Join-Path $ProjectRootPath "research_vault\_system\storage_duplicate_review.json")
$dailyCandidatePolicyPreviewPath = Join-Path $ProjectRootPath "tmp\daily_recommendation_candidate_policy_preview.json"
$dailyCandidatePolicyPreview = if (Test-Path -LiteralPath $dailyCandidatePolicyPreviewPath) {
  Read-OptionalJsonFile -Name "daily recommendation candidate policy preview" -Path $dailyCandidatePolicyPreviewPath
} else {
  $null
}

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
if ($storageDuplicateReview) {
  Write-Host "저장 중복 리뷰: $($storageDuplicateReview.status), 그룹 $($storageDuplicateReview.duplicate_group_count)개, 중복 항목 $($storageDuplicateReview.duplicate_entry_count)개"
  $duplicateGroups = if ($storageDuplicateReview.groups) { @($storageDuplicateReview.groups | ForEach-Object { $_ }) } else { @() }
  foreach ($group in $duplicateGroups | Select-Object -First 1) {
    $representative = $group.representative
    $firstDuplicate = @($group.duplicates | ForEach-Object { $_ } | Select-Object -First 1)
    if ($representative -and $firstDuplicate) {
      $similarity = if ($firstDuplicate.similarity) { "{0:P0}" -f [double]$firstDuplicate.similarity } else { "유사도 미확인" }
      Write-Host "저장 중복 대표 후보: $($group.ticker) | 대표 $($representative.file_name) | 후보 $($firstDuplicate.file_name) | $similarity"
    }
  }
  if ($storageDuplicateReview.status -and $storageDuplicateReview.status -ne "success") {
    Add-StatusFailure "저장 중복 리뷰 상태가 success가 아닙니다: $($storageDuplicateReview.status)"
  }
}
if ($dailyRecommendations) {
  Write-Host "일일 추천 최신일: $($dailyRecommendations.latest_recommendation_date)"
  Write-Host "일일 추천 저장 건수: $($dailyRecommendations.record_count)"
  Write-Host "일일 추천 실행 시각: $($dailyRecommendations.daily_time)"
  $todayRecords = if ($dailyRecommendations.today_records) { @($dailyRecommendations.today_records | ForEach-Object { $_ }) } else { @() }
  Write-Host "오늘 추천 실행 필요: $($dailyRecommendations.due_now), 대상일 $($dailyRecommendations.today_recommendation_date), 오늘 저장 $($todayRecords.Count)개"
  $latestRecommendationRecords = if ($dailyRecommendations.latest_records) { @($dailyRecommendations.latest_records | ForEach-Object { $_ }) } else { @() }
  foreach ($market in @("KR", "US")) {
    $marketLabel = if ($market -eq "KR") { "한국" } else { "미국" }
    $topRecords = @(
      $latestRecommendationRecords |
        Where-Object { ([string]$_.market).ToUpperInvariant() -eq $market -and [int]$_.rank -le 3 } |
        Sort-Object -Property rank |
        Select-Object -First 3
    )
    if ($topRecords.Count -gt 0) {
      $topLabels = @()
      foreach ($record in $topRecords) {
        $companyName = if ($record.company_name) { $record.company_name } else { $record.ticker }
        $topLabels += "$($record.rank)위 $companyName($($record.ticker), $($record.score)점)"
      }
      Write-Host "오늘 추천 $($marketLabel) 1~3위: $($topLabels -join ' / ')"
    }
  }
  if ($dailyCandidatePolicyPreview) {
    if ($dailyCandidatePolicyPreview.generated_at) {
      $previewAgeHours = Get-DateTimeAgeHours -DateTimeText $dailyCandidatePolicyPreview.generated_at
      $previewAgeLabel = if ($null -ne $previewAgeHours) { "{0:N1}시간 전" -f $previewAgeHours } else { "경과 미확인" }
      Write-Host "추천 재계산 프리뷰 생성: $(Format-LocalDateTime -DateTimeText $dailyCandidatePolicyPreview.generated_at) ($previewAgeLabel)"
      if ($Strict -and ($null -eq $previewAgeHours -or $previewAgeHours -gt $MaxRecommendationPreviewAgeHours)) {
        Add-StatusFailure "추천 재계산 프리뷰 최신성 확인 필요: $previewAgeLabel"
      }
    }
    $previewMismatches = if ($dailyCandidatePolicyPreview.stored_preview_mismatches) {
      @($dailyCandidatePolicyPreview.stored_preview_mismatches | ForEach-Object { $_ })
    } else {
      @()
    }
    if ($previewMismatches.Count -gt 0) {
      $previewMismatchLabels = @()
      foreach ($item in ($previewMismatches | Select-Object -First 6)) {
        $storedTicker = if ($item.stored_ticker) { $item.stored_ticker } else { "-" }
        $previewTicker = if ($item.preview_ticker) { $item.preview_ticker } else { "-" }
        $storedScore = if ($item.stored_score) { $item.stored_score } else { "-" }
        $previewScore = if ($item.preview_score) { $item.preview_score } else { "-" }
        $previewMismatchLabels += "$($item.market) $($item.rank)위 저장 $storedTicker($storedScore) / 재계산 $previewTicker($previewScore)"
      }
      Write-Host "추천 저장/재계산 차이: $($previewMismatchLabels -join ', ')"
    } else {
      Write-Host "추천 저장/재계산 차이: 없음"
    }
    if ($dailyCandidatePolicyPreview.status -and $dailyCandidatePolicyPreview.status -ne "success") {
      Add-StatusFailure "추천 후보 정책 프리뷰 상태가 success가 아닙니다: $($dailyCandidatePolicyPreview.status)"
    }
  }
}
if ($marketJournal) {
  $marketJournalEntries = if ($marketJournal.entries) { @($marketJournal.entries | ForEach-Object { $_ }) } else { @() }
  foreach ($market in @("KR", "US")) {
    $marketEntries = @($marketJournalEntries | Where-Object { ([string]$_.market).ToUpperInvariant() -eq $market })
    $autoEntries = @($marketEntries | Where-Object { ([string]$_.source_origin).ToLowerInvariant() -ne "manual" })
    $latestSession = ($marketEntries | Sort-Object -Property session_date -Descending | Select-Object -First 1).session_date
    $ageDays = Get-SessionAgeDays -SessionDate $latestSession
    $ageLabel = if ($null -ne $ageDays) { ", 경과 $($ageDays)일" } else { "" }
    Write-Host "시장일지 $($market): $($marketEntries.Count)개, 자동 $($autoEntries.Count)개, 최신 세션 $($latestSession)$ageLabel"
    if ([string]::IsNullOrWhiteSpace($latestSession) -or $null -eq $ageDays -or $ageDays -gt $MaxMarketJournalSessionAgeDays) {
      Add-StatusFailure "시장일지 $market 최신 세션 확인 필요: $($latestSession)"
    }
  }
}
if ($naverKrMarketJournalState) {
  $savedPath = if ($naverKrMarketJournalState.storage -and $naverKrMarketJournalState.storage.relative_path) {
    $naverKrMarketJournalState.storage.relative_path
  } else {
    "저장 경로 미확인"
  }
  $sourcePublishedAt = if ($naverKrMarketJournalState.source_published_at) {
    $naverKrMarketJournalState.source_published_at
  } else {
    "원천 발행일 미확인"
  }
  $attemptMessage = if ($naverKrMarketJournalState.last_attempt_message) {
    $naverKrMarketJournalState.last_attempt_message
  } else {
    "시도 메시지 없음"
  }
  Write-Host "국내 시장일지 자동 시도: $($naverKrMarketJournalState.status), 시도일 $($naverKrMarketJournalState.last_attempt_date), 원천 발행일 $sourcePublishedAt, 저장 $savedPath"
  if ($naverKrMarketJournalState.status -eq "skipped_duplicate" -and $naverKrMarketJournalState.source_published_at) {
    Write-Host "국내 시장일지 원천 상태: $attemptMessage"
  }
}
if ($telegramUsMarketJournalState) {
  $savedPath = if ($telegramUsMarketJournalState.storage -and $telegramUsMarketJournalState.storage.relative_path) {
    $telegramUsMarketJournalState.storage.relative_path
  } else {
    "저장 경로 미확인"
  }
  Write-Host "미국 시장일지 자동 시도: $($telegramUsMarketJournalState.status), 시도일 $($telegramUsMarketJournalState.last_attempt_date), 세션 $($telegramUsMarketJournalState.session_date), 포함 섹션 $($telegramUsMarketJournalState.included_post_count)개, 저장 $savedPath"
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
      $groupTitle = Limit-StatusText -Text $groupTitle -MaxLength 120
      $groupIds = @($group.ids) | Where-Object { $_ } | ForEach-Object { "$_" }
      $groupIdLabel = if ($groupIds.Count -gt 0) { " | ids " + (($groupIds | Select-Object -First 5) -join ", ") } else { "" }
      Write-Host "우선 뉴스 중복 후보: $($group.count)개 | $($group.canonical_url) | $groupTitle$groupIdLabel"
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
      $reduceCandidateTotal = 0.0
      foreach ($candidate in $reduceCandidates) {
        if ($candidate.market_value) {
          $reduceCandidateTotal += [double]$candidate.market_value
        }
      }
      $reduceCandidateTotalText = "{0:N0}" -f $reduceCandidateTotal
      $reductionNeeded = if ($npsPlan.reduction_needed_value) {
        "{0:N0}" -f [double]$npsPlan.reduction_needed_value
      } else {
        "0"
      }
      $currentWeight = "{0:P2}" -f [double]$npsPlan.current_domestic_equity_weight
      $targetWeight = "{0:P2}" -f [double]$npsPlan.target_domestic_equity_weight
      Write-Host "국민연금 14% 계획: $($npsPlan.status), 현재 $($currentWeight)/목표 $($targetWeight), 축소 필요 $($reductionNeeded)원, 축소 후보 $($reduceCandidateCount)개(합계 $($reduceCandidateTotalText)원)"
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
    $npsChangeSnapshot = $dashboardDigest.nps_portfolio_change_snapshot
    if ($npsChangeSnapshot) {
      $matchedCount = if ($npsChangeSnapshot.portfolio_matches) { @($npsChangeSnapshot.portfolio_matches).Count } else { 0 }
      Write-Host "국민연금 변동 스냅샷: $($npsChangeSnapshot.status), 기준 $($npsChangeSnapshot.as_of), 최신 이벤트 $($npsChangeSnapshot.latest_event_date), 포트폴리오 매칭 $($matchedCount)건"
      if ($npsChangeSnapshot.public_rebalancing_context -and $npsChangeSnapshot.public_rebalancing_context.data_policy) {
        Write-Host "국민연금 리밸런싱 데이터 정책: 주문흐름 $($npsChangeSnapshot.public_rebalancing_context.data_policy.order_flow_access), 실시간탐지 $($npsChangeSnapshot.public_rebalancing_context.data_policy.realtime_rebalancing_detection)"
      }
      foreach ($warning in (@($npsChangeSnapshot.warnings) | Select-Object -First 2)) {
        Write-Host "국민연금 변동 경고: $warning"
      }
    }
  }
  if ($researchAutomation.status -and $researchAutomation.status -ne "success") {
    Add-StatusFailure "research automation 상태가 success가 아닙니다: $($researchAutomation.status)"
  }
}
if ($publicIrSecStatus) {
  $firecrawlIr = $publicIrSecStatus.firecrawl_ir
  if ($firecrawlIr) {
    $firecrawlMcp = $firecrawlIr.mcp
    $firecrawlHostedApi = $firecrawlIr.hosted_api
    $firecrawlRpc = $firecrawlIr.rpc
    Write-Host "Firecrawl IR: $($firecrawlIr.status), enabled $($firecrawlIr.enabled), dry_run $($firecrawlIr.dry_run), api_key $($firecrawlHostedApi.api_key_configured), rpc_submit_ready $($firecrawlRpc.submit_ready), mcp $($firecrawlMcp.configured_version)/$($firecrawlMcp.expected_version)"
    if ($firecrawlIr.next_action) {
      Write-Host "Firecrawl IR 다음 조치: $($firecrawlIr.next_action)"
    }
    if ($firecrawlMcp -and $firecrawlMcp.version_ok -eq $false) {
      Add-StatusFailure "Firecrawl IR MCP 버전 확인 필요: $($firecrawlMcp.configured_version)"
    }
  }
  $firecrawlMonitor = $publicIrSecStatus.firecrawl_monitor
  if ($firecrawlMonitor) {
    $firecrawlMonitorHostedApi = $firecrawlMonitor.hosted_api
    $firecrawlMonitorSample = $firecrawlMonitor.sample_monitor
    Write-Host "Firecrawl Monitor: $($firecrawlMonitor.status), enabled $($firecrawlMonitor.enabled), dry_run $($firecrawlMonitor.dry_run), api_key $($firecrawlMonitorHostedApi.api_key_configured), create_ready $($firecrawlMonitor.create_ready), sample_targets $($firecrawlMonitorSample.target_count)"
    if ($firecrawlMonitor.next_action) {
      Write-Host "Firecrawl Monitor 다음 조치: $($firecrawlMonitor.next_action)"
    }
  }
  $needsBodyEntries = if ($publicIrSecStatus.needs_body_copy_entries) { @($publicIrSecStatus.needs_body_copy_entries) } else { @() }
  $needsBodyDuplicateTitleGroups = if ($publicIrSecStatus.needs_body_duplicate_title_groups) {
    @($publicIrSecStatus.needs_body_duplicate_title_groups | ForEach-Object { $_ })
  } else {
    @()
  }
  $needsBodyDuplicateTitleGroupCount = if ($publicIrSecStatus.needs_body_duplicate_title_group_count) {
    $publicIrSecStatus.needs_body_duplicate_title_group_count
  } else {
    0
  }
  Write-Host "공개 IR/SEC: 전체 $($publicIrSecStatus.entry_count)건, 본문 보강 플래그 $($publicIrSecStatus.needs_body_copy_count)건, 동일 제목 그룹 $($needsBodyDuplicateTitleGroupCount)개"
  foreach ($group in $needsBodyDuplicateTitleGroups | Select-Object -First 3) {
    $groupTitle = Limit-StatusText -Text $group.title -MaxLength 80
    $groupFiles = @($group.file_names) | Where-Object { $_ } | ForEach-Object { Limit-StatusText -Text $_ -MaxLength 80 }
    $groupFileLabel = if ($groupFiles.Count -gt 0) { " | files " + (($groupFiles | Select-Object -First 2) -join ", ") } else { "" }
    Write-Host "공개 IR/SEC 동일 제목: $($group.ticker) | $($group.count)건 | $groupTitle$groupFileLabel"
  }
  foreach ($entry in $needsBodyEntries | Select-Object -First 3) {
    $entryTitle = if ($entry.title) { $entry.title } elseif ($entry.file_name) { $entry.file_name } else { "제목 미확인" }
    $entryPath = if ($entry.relative_path) { $entry.relative_path } elseif ($entry.source_url) { $entry.source_url } else { "경로 미확인" }
    $followupLabel = if ($entry.body_followup -and $entry.body_followup.label) { " | $($entry.body_followup.label)" } else { "" }
    Write-Host "공개 IR/SEC 보강 대상: $($entry.ticker) | $entryTitle | $entryPath$followupLabel"
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
