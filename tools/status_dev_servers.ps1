param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp",
  [string]$ApiBaseUrl = "http://127.0.0.1:8010",
  [string]$AppUrl = "http://localhost:8085",
  [string]$DevUserToken = "dev-local-token",
  [int]$ApiPort = 8010,
  [int[]]$FallbackApiPorts = @(8020, 8021, 8022),
  [int]$AppPort = 8085,
  [switch]$RequirePortfolio,
  [switch]$Strict
)

$ErrorActionPreference = "Stop"

$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
Set-Location -LiteralPath $ProjectRootPath

if (-not $PSBoundParameters.ContainsKey("ApiBaseUrl") -and $PSBoundParameters.ContainsKey("ApiPort")) {
  $ApiBaseUrl = "http://127.0.0.1:$ApiPort"
}
if (-not $PSBoundParameters.ContainsKey("AppUrl") -and $PSBoundParameters.ContainsKey("AppPort")) {
  $AppUrl = "http://localhost:$AppPort"
}

$script:StatusFailures = @()

function Write-Section {
  param([string]$Title)
  Write-Host ""
  Write-Host "== $Title =="
}

function Add-StatusFailure {
  param([string]$Message)
  $script:StatusFailures += $Message
}

function Get-PortOwningProcessIds {
  param([int]$Port)

  $processIds = @()

  $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
    Where-Object { $_.OwningProcess -and $_.OwningProcess -gt 0 }
  if ($connections) {
    $processIds += @($connections | Select-Object -ExpandProperty OwningProcess)
  }

  $netstatLines = netstat -ano 2>$null | Select-String -Pattern "[:.]$Port\s"
  foreach ($line in $netstatLines) {
    $parts = ($line.Line.Trim() -split "\s+") | Where-Object { $_ }
    if ($parts.Count -lt 4) {
      continue
    }

    $localAddress = $parts[1]
    $ownerText = $parts[-1]
    if ($localAddress -notmatch "[:.]$Port$") {
      continue
    }

    $ownerProcessId = 0
    if ([int]::TryParse($ownerText, [ref]$ownerProcessId) -and $ownerProcessId -gt 0) {
      $processIds += $ownerProcessId
    }
  }

  return @($processIds | Sort-Object -Unique)
}

function Get-PortOwnerSummary {
  param([int]$Port)

  $processIds = @(Get-PortOwningProcessIds -Port $Port)

  if (-not $processIds -or $processIds.Count -eq 0) {
    return "닫힘"
  }

  $items = @()
  foreach ($processId in $processIds) {
    try {
      $process = Get-Process -Id $processId -ErrorAction Stop
      $items += "PID $processId ($($process.ProcessName))"
    } catch {
      $items += "PID $processId (이름 확인 불가)"
    }
  }
  return ($items -join ", ")
}

function Test-JsonEndpoint {
  param(
    [string]$Name,
    [string]$Uri,
    [hashtable]$Headers = @{},
    [bool]$Required = $true,
    [string]$OptionalHint = "선택 점검 실패로 처리합니다."
  )

  try {
    $response = Invoke-WebRequest -Uri $Uri -Method Get -Headers $Headers -UseBasicParsing
    $contentText = $response.Content
    if ($response.RawContentStream) {
      $stream = $response.RawContentStream
      if ($stream.CanSeek) {
        $stream.Position = 0
      }
      $reader = [System.IO.StreamReader]::new($stream, [System.Text.Encoding]::UTF8)
      $contentText = $reader.ReadToEnd()
      $reader.Dispose()
    }
    Write-Host "정상 $Name - $Uri"
    return ($contentText | ConvertFrom-Json)
  } catch {
    if ($Required) {
      Write-Host "실패 $Name - $Uri"
      Write-Host "  $($_.Exception.Message)"
      Add-StatusFailure "$Name 실패: $($_.Exception.Message)"
    } else {
      Write-Host "선택 건너뜀 $Name - $Uri"
      Write-Host "  $OptionalHint"
    }
    return $null
  }
}

function Test-TextEndpoint {
  param(
    [string]$Name,
    [string]$Uri,
    [hashtable]$Headers = @{},
    [string]$RequiredText = ""
  )

  try {
    $response = Invoke-WebRequest -Uri $Uri -Method Get -Headers $Headers -UseBasicParsing
    Write-Host "정상 $Name - $Uri"
    if ($RequiredText -and $response.Content -notlike "*$RequiredText*") {
      Write-Host "주의 $Name 응답에 기대 문구가 없습니다: $RequiredText"
      Add-StatusFailure "$Name 응답에 기대 문구가 없습니다: $RequiredText"
    }
    return $response
  } catch {
    Write-Host "실패 $Name - $Uri"
    Write-Host "  $($_.Exception.Message)"
    Add-StatusFailure "$Name 실패: $($_.Exception.Message)"
    return $null
  }
}

Write-Section "포트 상태"
Write-Host "API $ApiPort : $(Get-PortOwnerSummary -Port $ApiPort)"
foreach ($fallbackApiPort in $FallbackApiPorts) {
  if ($fallbackApiPort -ne $ApiPort) {
    Write-Host "API fallback $fallbackApiPort : $(Get-PortOwnerSummary -Port $fallbackApiPort)"
  }
}
Write-Host "APP $AppPort : $(Get-PortOwnerSummary -Port $AppPort)"

$authHeaders = @{ Authorization = "Bearer $DevUserToken" }
function Invoke-BackendStatusCheck {
  param(
    [string]$BaseUrl,
    [int]$Port,
    [string]$Label = "백엔드 상태"
  )

  Write-Section $Label
  $failureStartCount = $script:StatusFailures.Count
  $root = Test-JsonEndpoint -Name "backend root" -Uri "$BaseUrl/"
  $systemHealth = Test-JsonEndpoint `
    -Name "system health" `
    -Uri "$BaseUrl/api/v1/system/health" `
    -Required:$false `
    -OptionalHint "연구 콘솔 백엔드에는 있는 경로이며, 모바일 API 백엔드에서는 없을 수 있습니다."
  $portfolio = Test-JsonEndpoint `
    -Name "portfolio" `
    -Uri "$BaseUrl/api/v1/portfolio" `
    -Headers $authHeaders `
    -Required:$RequirePortfolio `
    -OptionalHint "키움 인증 정보가 없거나 장중 API가 불안정하면 portfolio는 실패할 수 있습니다."
  $analytics = Test-JsonEndpoint -Name "analytics" -Uri "$BaseUrl/api/v1/journal/analytics" -Headers $authHeaders
  $csvTemplate = Test-TextEndpoint -Name "manual CSV template" -Uri "$BaseUrl/api/v1/manual-transactions/import.csv/template" -Headers $authHeaders -RequiredText "거래일,증권사,계좌"

  if ($root -and $root.message) {
    Write-Host "백엔드 메시지: $($root.message)"
  }
  if ($systemHealth -and $systemHealth.message) {
    Write-Host "시스템 상태: $($systemHealth.message)"
  }
  if ($systemHealth -and $null -ne $systemHealth.onedrive_excluded) {
    Write-Host "OneDrive 제외: $($systemHealth.onedrive_excluded)"
  }
  if ($portfolio -and $null -ne $portfolio.holdings_count) {
    Write-Host "포트폴리오 보유 수: $($portfolio.holdings_count)"
  }
  if ($analytics -and $null -ne $analytics.total_entries) {
    Write-Host "분석 데이터 수: $($analytics.total_entries)"
  }
  if ($csvTemplate -and $csvTemplate.Headers["Content-Disposition"]) {
    Write-Host "CSV 템플릿 파일명: $($csvTemplate.Headers["Content-Disposition"])"
  }

  return [pscustomobject]@{
    Ok = ($script:StatusFailures.Count -eq $failureStartCount)
    FailureStartCount = $failureStartCount
    BaseUrl = $BaseUrl
    Port = $Port
  }
}

$backendResult = Invoke-BackendStatusCheck -BaseUrl $ApiBaseUrl -Port $ApiPort
$apiBaseUrlExplicit = $PSBoundParameters.ContainsKey("ApiBaseUrl")
if (-not $backendResult.Ok -and -not $apiBaseUrlExplicit) {
  $initialFailureCount = $backendResult.FailureStartCount
  foreach ($fallbackApiPort in $FallbackApiPorts) {
    if ($fallbackApiPort -eq $ApiPort) {
      continue
    }
    $fallbackBaseUrl = "http://127.0.0.1:$fallbackApiPort"
    $fallbackResult = Invoke-BackendStatusCheck -BaseUrl $fallbackBaseUrl -Port $fallbackApiPort -Label "백엔드 fallback 상태 ($fallbackApiPort)"
    if ($fallbackResult.Ok) {
      $script:StatusFailures = @($script:StatusFailures | Select-Object -First $initialFailureCount)
      $ApiBaseUrl = $fallbackBaseUrl
      $ApiPort = $fallbackApiPort
      Write-Host "정상 fallback API 사용: $ApiBaseUrl"
      break
    }
  }
}

Write-Section "모바일 웹 상태"
try {
  $app = Invoke-WebRequest -Uri $AppUrl -UseBasicParsing
  Write-Host "정상 mobile web HTTP $($app.StatusCode) - $AppUrl"
  if ($app.Content -like "*<div id=`"root`"*") {
    Write-Host "정상 mobile root element"
  } else {
    Write-Host "주의 mobile root element not found"
    Add-StatusFailure "mobile root element not found"
  }
} catch {
  Write-Host "실패 mobile web - $AppUrl"
  Write-Host "  $($_.Exception.Message)"
  Add-StatusFailure "mobile web 실패: $($_.Exception.Message)"
}

Write-Section "점검 요약"
if ($script:StatusFailures.Count -eq 0) {
  Write-Host "정상 모든 상태 점검 통과"
} else {
  foreach ($failure in $script:StatusFailures) {
    Write-Host "주의 $failure"
  }
  if ($Strict) {
    throw "상태 점검 실패: $($script:StatusFailures.Count)건"
  }
}

Write-Section "복구 명령"
Write-Host "백엔드 재시작: .\tools\restart_backend_verified.ps1 -Port $ApiPort -FallbackPorts @(8020,8021,8022)"
Write-Host "모바일 재시작: .\tools\start_mobile_web.ps1 -Port $AppPort -ApiBaseUrl $ApiBaseUrl -StopExistingPortProcess -ClearCache"
Write-Host "통합 검증: .\tools\verify_mobile_stack.ps1"
