param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp",
  [string]$BaseUrl = "http://127.0.0.1:8001",
  [string]$DevUserToken = "dev-local-token",
  [int]$PortfolioRefreshTimeoutSeconds = 120,
  [int]$RecommendationRunTimeoutSeconds = 600,
  [int]$ResearchAutomationTimeoutSeconds = 300,
  [switch]$SkipPortfolioRefresh,
  [switch]$SkipRecommendationRun,
  [switch]$SkipRecommendationPreview,
  [switch]$SkipResearchAutomationRefresh,
  [switch]$SkipOpenClawSync,
  [switch]$SkipVerification
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONIOENCODING = "utf-8"

$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
Set-Location -LiteralPath $ProjectRootPath

function Invoke-DailyResearchStep {
  param(
    [string]$Name,
    [scriptblock]$Block
  )

  Write-Host ""
  Write-Host "==> $Name"
  $global:LASTEXITCODE = 0
  & $Block
  if ($LASTEXITCODE -ne 0) {
    throw "$Name 실패: 종료 코드 $LASTEXITCODE"
  }
  Write-Host "정상 $Name"
}

if (-not $SkipPortfolioRefresh.IsPresent) {
  Invoke-DailyResearchStep "포트폴리오 가격 갱신" {
    python tools\refresh_portfolio_prices.py `
      --base-url $BaseUrl `
      --token $DevUserToken `
      --timeout $PortfolioRefreshTimeoutSeconds
    if ($LASTEXITCODE -ne 0) {
      Write-Warning "포트폴리오 가격 갱신 응답은 실패했지만 저장 상태 검증을 시도합니다."
      python tools\check_portfolio_store.py `
        --portfolio "이형주" `
        --min-holdings 17 `
        --expected-holdings-count 17 `
        --forbid-zero `
        --max-price-age-hours 24 `
        --max-portfolio-age-hours 24
      if ($LASTEXITCODE -ne 0) {
        return
      }
      python tools\check_all_portfolio_store.py `
        --min-holdings 1 `
        --forbid-zero `
        --max-price-age-hours 24 `
        --max-sync-age-hours 168
      if ($LASTEXITCODE -eq 0) {
        Write-Warning "포트폴리오 저장 상태 검증이 통과해 운영 루틴을 계속합니다."
      }
    }
  }
}

if (-not $SkipRecommendationRun.IsPresent) {
  Invoke-DailyResearchStep "오늘 추천 강제 재분석" {
    $headers = @{
      Authorization = "Bearer $DevUserToken"
      "Content-Type" = "application/json"
    }
    $query = "force=true" + [char]38 + "save_result=true"
    $uri = "$($BaseUrl.TrimEnd('/'))/api/v1/daily-recommendations/run?$query"
    try {
      $result = Invoke-RestMethod -Method Post -Uri $uri -Headers $headers -TimeoutSec $RecommendationRunTimeoutSeconds
    } catch {
      Write-Warning "오늘 추천 API 응답 실패/타임아웃: $($_.Exception.Message)"
      python tools\check_daily_recommendations_store.py `
        --require-milestones `
        --require-quality `
        --expected-latest-count 6 `
        --max-latest-age-days 0
      if ($LASTEXITCODE -eq 0) {
        Write-Warning "오늘 추천 저장 검증이 통과해 운영 루틴을 계속합니다."
        return
      }
      throw
    }
    Write-Host (
      "상태={0}; 추천일={1}; 최신추천일={2}; 전체기록={3}; 저장={4}" -f
      $result.status,
      $result.recommendation_date,
      $result.latest_recommendation_date,
      $result.record_count,
      $result.storage_path
    )
  }
}

if (-not $SkipRecommendationPreview.IsPresent) {
  Invoke-DailyResearchStep "추천 저장/재계산 프리뷰 저장" {
    python tools\check_daily_recommendation_candidate_policy.py `
      --require-hold-warning `
      --expected-held-ticker 112610 `
      --output-json tmp\daily_recommendation_candidate_policy_preview.json
  }
}

if (-not $SkipResearchAutomationRefresh.IsPresent) {
  Invoke-DailyResearchStep "리서치 중복/Dossier 상태 갱신" {
    $headers = @{
      Authorization = "Bearer $DevUserToken"
      "Content-Type" = "application/json"
    }
    $base = $BaseUrl.TrimEnd("/")
    try {
      $reviewUri = "$base/api/v1/research-automation/dedupes/review?limit=80" + [char]38 + "save_result=true"
      $review = Invoke-RestMethod -Method Post -Uri $reviewUri -Headers $headers -TimeoutSec $ResearchAutomationTimeoutSeconds
      $reviewGroupCount = $review.duplicate_group_count
      if ($null -eq $reviewGroupCount) {
        $reviewGroupCount = $review.group_count
      }
      Write-Host (
        "중복 리뷰 상태={0}; 그룹={1}; 갱신={2}" -f
        $review.status,
        $reviewGroupCount,
        $review.as_of
      )
      $refreshUri = "$base/api/v1/research-automation/dedupes/refresh-dossiers?limit=8" + [char]38 + "save_result=true"
      $refresh = Invoke-RestMethod -Method Post -Uri $refreshUri -Headers $headers -TimeoutSec $ResearchAutomationTimeoutSeconds
      Write-Host (
        "Dossier 큐 상태={0}; 후보={1}; 갱신={2}; 실패={3}; 기준={4}" -f
        $refresh.status,
        $refresh.candidate_count,
        $refresh.refreshed_count,
        $refresh.failed_count,
        $refresh.as_of
      )
    } catch {
      Write-Warning "리서치 중복/Dossier 상태 갱신 응답 실패/타임아웃: $($_.Exception.Message)"
      python tools\check_research_source_store.py --strict
      if ($LASTEXITCODE -eq 0) {
        Write-Warning "리서치 소스 저장 상태 검증이 통과해 운영 루틴을 계속합니다."
        return
      }
      throw
    }
  }
}

if (-not $SkipOpenClawSync.IsPresent) {
  Invoke-DailyResearchStep "OpenClaw 투자리서치 브리지 동기화" {
    & (Join-Path $PSScriptRoot "sync_openclaw_investment_context.ps1") -RequireCompletionAudit
  }
}

if (-not $SkipVerification.IsPresent) {
  Invoke-DailyResearchStep "운영 검증" {
    & (Join-Path $PSScriptRoot "verify_research_console.ps1") `
      -ProjectRoot $ProjectRootPath `
      -SkipLiveSmoke `
      -SkipWriteSmoke `
      -CheckPortfolioStore `
      -CheckNpsDomesticEquityAllocation `
      -CheckDailyRecommendationStore `
      -CheckInvestmentInsightHub
  }
}

Write-Host ""
Write-Host "일일 리서치 운영 루틴 완료"
