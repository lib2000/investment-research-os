param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp",
  [string]$AppUrl = "http://localhost:8085",
  [string]$ApiBaseUrl = "http://127.0.0.1:8010",
  [int]$ApiPort = 8010,
  [int[]]$FallbackApiPorts = @(8020, 8021, 8022),
  [string]$DevUserToken = "dev-local-token",
  [switch]$RequirePortfolio
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

function Invoke-RequiredJson {
  param(
    [string]$Name,
    [string]$Uri,
    [hashtable]$Headers = @{}
  )

  try {
    return Invoke-RestMethod -Uri $Uri -Method Get -Headers $Headers
  } catch {
    throw "$Name 호출 실패: $($_.Exception.Message)"
  }
}

function Invoke-RequiredText {
  param(
    [string]$Name,
    [string]$Uri,
    [hashtable]$Headers = @{}
  )

  try {
    return Invoke-WebRequest -Uri $Uri -Method Get -Headers $Headers -UseBasicParsing
  } catch {
    $message = "$Name 호출 실패: $($_.Exception.Message)"
    if ($Uri -like "*/api/v1/manual-transactions/import.csv/template") {
      $message += "`nCSV 템플릿 API만 404라면 오래된 백엔드가 8010 포트를 잡고 있을 수 있습니다."
      $message += "`n확인: .\tools\status_dev_servers.ps1 -Strict"
      $message += "`n복구: .\tools\start_backend.ps1 -StopExistingPortProcess"
    }
    throw $message
  }
}

Write-Host "모바일 웹 스모크 테스트를 시작합니다."
Write-Host "APP: $AppUrl"
Write-Host "API: $ApiBaseUrl"

function Invoke-BackendSmoke {
  param([string]$BaseUrl)

  $root = Invoke-RequiredJson -Name "backend root" -Uri "$BaseUrl/"
  Assert-Condition ($root.message -like "*정상 작동*") "백엔드 루트 응답이 올바르지 않습니다."
  Write-Host "OK backend root"

  $headers = @{ Authorization = "Bearer $DevUserToken" }
  try {
    $portfolio = Invoke-RequiredJson -Name "portfolio API" -Uri "$BaseUrl/api/v1/portfolio" -Headers $headers
    Assert-Condition ($portfolio.status -eq "success") "포트폴리오 API 응답 상태가 success가 아닙니다."
    Assert-Condition ($null -ne $portfolio.holdings_count) "포트폴리오 API에 holdings_count가 없습니다."
    Write-Host "OK portfolio API"
  } catch {
    if ($RequirePortfolio) {
      throw
    }
    Write-Host "WARN portfolio API 선택 점검 실패: $($_.Exception.Message)"
  }

  $analytics = Invoke-RequiredJson -Name "analytics API" -Uri "$BaseUrl/api/v1/journal/analytics" -Headers $headers
  Assert-Condition ($analytics.status -eq "success") "분석 API 응답 상태가 success가 아닙니다."
  Assert-Condition ($null -ne $analytics.total_entries) "분석 API에 total_entries가 없습니다."
  Write-Host "OK analytics API"

  $csvTemplate = Invoke-RequiredText -Name "manual CSV template API" -Uri "$BaseUrl/api/v1/manual-transactions/import.csv/template" -Headers $headers
  $contentDisposition = [string]($csvTemplate.Headers["Content-Disposition"] -join ",")
  Assert-Condition ($csvTemplate.StatusCode -eq 200) "CSV 템플릿 API HTTP 상태가 200이 아닙니다."
  Assert-Condition ($csvTemplate.Content -like "*거래일,증권사,계좌*") "CSV 템플릿 API에 한글 헤더가 없습니다."
  Assert-Condition ($contentDisposition -like "*manual-transactions-template.csv*") "CSV 템플릿 파일명이 올바르지 않습니다."
  Write-Host "OK manual CSV template API"
}

$apiBaseUrlExplicit = $PSBoundParameters.ContainsKey("ApiBaseUrl")
try {
  Invoke-BackendSmoke -BaseUrl $ApiBaseUrl
} catch {
  if ($apiBaseUrlExplicit) {
    throw
  }
  $primaryError = $_.Exception.Message
  $fallbackSucceeded = $false
  foreach ($fallbackApiPort in $FallbackApiPorts) {
    if ($fallbackApiPort -eq $ApiPort) {
      continue
    }
    $fallbackBaseUrl = "http://127.0.0.1:$fallbackApiPort"
    Write-Host "WARN primary API smoke failed: $primaryError"
    Write-Host "fallback API 확인: $fallbackBaseUrl"
    try {
      Invoke-BackendSmoke -BaseUrl $fallbackBaseUrl
      $ApiBaseUrl = $fallbackBaseUrl
      $fallbackSucceeded = $true
      Write-Host "OK fallback API smoke: $ApiBaseUrl"
      break
    } catch {
      Write-Host "WARN fallback API 실패: $($_.Exception.Message)"
    }
  }
  if (-not $fallbackSucceeded) {
    throw "기본 API와 fallback API 스모크가 모두 실패했습니다. 기본 오류: $primaryError"
  }
}

$app = Invoke-RequiredText -Name "mobile web" -Uri $AppUrl
Assert-Condition ($app.StatusCode -eq 200) "모바일 웹 페이지 HTTP 상태가 200이 아닙니다."
Assert-Condition ($app.Content -like "*<div id=`"root`"*") "모바일 웹 root 엘리먼트를 찾지 못했습니다."
Write-Host "OK mobile web HTML"

Write-Host "스모크 테스트 통과"
