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
    return ($response.Content | ConvertFrom-Json)
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
    Write-Host "정상 $Name - $uri"
    if ($RequiredText -and $response.Content -notlike "*$RequiredText*") {
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
if ($console) {
  Write-Host "콘솔 HTML 크기: $($console.RawContentLength) bytes"
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
