param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp",
  [switch]$SkipExpoInstallCheck,
  [switch]$SkipPortRegistryCheck,
  [switch]$SkipLiveSmoke
)

$ErrorActionPreference = "Stop"

$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru

function Invoke-VerifyStep {
  param(
    [string]$Name,
    [scriptblock]$Block
  )

  Write-Host ""
  Write-Host "==> $Name"
  $global:LASTEXITCODE = 0
  & $Block
  if ($LASTEXITCODE -ne 0) {
    throw "$Name failed with exit code $LASTEXITCODE"
  }
  Write-Host "OK $Name"
}

function Remove-SafeDirectory {
  param(
    [string]$PathToRemove,
    [string]$AllowedRoot
  )

  if (-not (Test-Path -LiteralPath $PathToRemove)) {
    return
  }

  $resolvedPath = (Resolve-Path -LiteralPath $PathToRemove).Path
  $resolvedRoot = (Resolve-Path -LiteralPath $AllowedRoot).Path
  if (-not $resolvedPath.StartsWith($resolvedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "검증 산출물 정리를 거부합니다. 허용 루트 밖입니다: $resolvedPath"
  }

  Remove-Item -LiteralPath $resolvedPath -Recurse -Force
}

$mobilePath = Join-Path $ProjectRootPath "apps\mobile"
$exportDir = Join-Path $mobilePath ".expo-export-check"

Set-Location -LiteralPath $ProjectRootPath

if (-not $SkipPortRegistryCheck) {
  Invoke-VerifyStep "예약 포트 레지스트리 점검" {
    & (Join-Path $PSScriptRoot "show_dev_server_ports.ps1") -OnlyConflicts
  }
}

Invoke-VerifyStep "백엔드 수동 CSV/분석 회귀 테스트" {
  python -m unittest tests.test_backend_regressions.InvestmentJournalManualImportTests
}

Invoke-VerifyStep "백엔드 전체 회귀 테스트" {
  python -m unittest tests.test_backend_regressions
}

Invoke-VerifyStep "모바일 TypeScript 타입체크" {
  Push-Location -LiteralPath $mobilePath
  try {
    npm run typecheck
  } finally {
    Pop-Location
  }
}

Invoke-VerifyStep "모바일 testID 정적 검증" {
  & (Join-Path $PSScriptRoot "assert_mobile_testids.ps1") -ProjectRoot $ProjectRootPath
}

Invoke-VerifyStep "개발 스크립트 계약 검증" {
  & (Join-Path $PSScriptRoot "assert_dev_scripts_contract.ps1") -ProjectRoot $ProjectRootPath
}

Invoke-VerifyStep "모바일 npm audit high 이상" {
  Push-Location -LiteralPath $mobilePath
  try {
    $auditOutput = npm audit --json
    $audit = $auditOutput | ConvertFrom-Json
    $vulnerabilities = $audit.metadata.vulnerabilities
    $critical = if ($null -ne $vulnerabilities.critical) { [int]$vulnerabilities.critical } else { 0 }
    $high = if ($null -ne $vulnerabilities.high) { [int]$vulnerabilities.high } else { 0 }
    $moderate = if ($null -ne $vulnerabilities.moderate) { [int]$vulnerabilities.moderate } else { 0 }
    $low = if ($null -ne $vulnerabilities.low) { [int]$vulnerabilities.low } else { 0 }
    Write-Host "npm audit summary: critical=$critical, high=$high, moderate=$moderate, low=$low"
    if (($critical + $high) -gt 0) {
      throw "high 이상 npm audit 취약점이 있습니다. critical=$critical, high=$high"
    }
    $global:LASTEXITCODE = 0
  } finally {
    Pop-Location
  }
  Write-Host "참고: Expo 내부 개발 도구 체인의 moderate 경고가 표시될 수 있습니다. 강제 fix는 Expo 버전 다운그레이드를 유발하므로 적용하지 않습니다."
}

if (-not $SkipExpoInstallCheck) {
  Invoke-VerifyStep "Expo 의존성 정합성 확인" {
    Push-Location -LiteralPath $mobilePath
    try {
      npx expo install --check
    } finally {
      Pop-Location
    }
  }
}

Invoke-VerifyStep "Expo web export" {
  Push-Location -LiteralPath $mobilePath
  try {
    npx expo export --platform web --output-dir .expo-export-check
  } finally {
    Pop-Location
    Remove-SafeDirectory -PathToRemove $exportDir -AllowedRoot $mobilePath
  }
}

if (-not $SkipLiveSmoke) {
  Invoke-VerifyStep "모바일 웹/백엔드 스모크" {
    & (Join-Path $PSScriptRoot "smoke_mobile_web.ps1") -ProjectRoot $ProjectRootPath
  }

  Invoke-VerifyStep "분석 샘플 CSV 스모크" {
    & (Join-Path $PSScriptRoot "smoke_mobile_analytics_sample.ps1") -ProjectRoot $ProjectRootPath
  }
}

Write-Host ""
Write-Host "모바일 스택 검증 통과"
