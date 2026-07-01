param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp",
  [string]$BaseUrl = "http://127.0.0.1:8001",
  [string]$DevUserToken = "dev-local-token",
  [int]$PortfolioRefreshTimeoutSeconds = 120,
  [int]$RecommendationRunTimeoutSeconds = 600,
  [switch]$SkipPortfolioRefresh,
  [switch]$SkipRecommendationRun,
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

if (-not $SkipPortfolioRefresh) {
  Invoke-DailyResearchStep "포트폴리오 가격 갱신" {
    python tools\refresh_portfolio_prices.py `
      --base-url $BaseUrl `
      --token $DevUserToken `
      --timeout $PortfolioRefreshTimeoutSeconds
  }
}

if (-not $SkipRecommendationRun) {
  Invoke-DailyResearchStep "오늘 추천 강제 재분석" {
    $headers = @{
      Authorization = "Bearer $DevUserToken"
      "Content-Type" = "application/json"
    }
    $uri = "$($BaseUrl.TrimEnd('/'))/api/v1/daily-recommendations/run?force=true&save_result=true"
    $result = Invoke-RestMethod -Method Post -Uri $uri -Headers $headers -TimeoutSec $RecommendationRunTimeoutSeconds
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

if (-not $SkipVerification) {
  Invoke-DailyResearchStep "운영 검증" {
    & (Join-Path $PSScriptRoot "verify_research_console.ps1") `
      -ProjectRoot $ProjectRootPath `
      -SkipLiveSmoke `
      -SkipWriteSmoke `
      -CheckPortfolioStore `
      -CheckNpsDomesticEquityAllocation `
      -CheckDailyRecommendationStore
  }
}

Write-Host ""
Write-Host "일일 리서치 운영 루틴 완료"
