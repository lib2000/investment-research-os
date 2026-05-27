param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp",
  [string]$BaseUrl = "http://127.0.0.1:8001",
  [string]$DevUserToken = "dev-local-token",
  [string]$CustomsStartYymm = "202605",
  [string]$CustomsEndYymm = "202605",
  [switch]$RequireCustomsTotalTrendAuthorized,
  [string]$PortfolioName = "이형주",
  [string]$PortfolioTicker = "PL",
  [double]$PortfolioExpectedQuantity = 100,
  [string]$PortfolioExpectedCurrency = "USD",
  [string]$PortfolioExpectedHoldings = "PL=100:USD,JOBY=208:USD,CHPT=22:USD,ABSI=29:USD,GOTU=50:USD,OTLY=8:USD,RXRX=9:USD,253450=36:KRW",
  [int]$MaxBodyMissing = 0,
  [int]$MaxOcrNeeded = 0,
  [switch]$Strict
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
Set-Location -LiteralPath $ProjectRootPath

$customsJson = & (Join-Path $PSScriptRoot "check_customs_trade_quality.ps1") `
  -ProjectRoot $ProjectRootPath `
  -BaseUrl $BaseUrl `
  -DevUserToken $DevUserToken `
  -StartYymm $CustomsStartYymm `
  -EndYymm $CustomsEndYymm `
  -RequireTotalTrendAuthorized:$RequireCustomsTotalTrendAuthorized
$customs = $customsJson | ConvertFrom-Json

$portfolioJson = & (Join-Path $PSScriptRoot "check_portfolio_quantity_protection.ps1") `
  -ProjectRoot $ProjectRootPath `
  -BaseUrl $BaseUrl `
  -DevUserToken $DevUserToken `
  -PortfolioName $PortfolioName `
  -Ticker $PortfolioTicker `
  -ExpectedQuantity $PortfolioExpectedQuantity `
  -ExpectedCurrency $PortfolioExpectedCurrency `
  -ExpectedHoldings $PortfolioExpectedHoldings `
  -Strict
$portfolio = $portfolioJson | ConvertFrom-Json

$storageJson = & (Join-Path $PSScriptRoot "check_storage_quality_safeguards.ps1") `
  -ProjectRoot $ProjectRootPath `
  -BaseUrl $BaseUrl `
  -DevUserToken $DevUserToken `
  -MaxBodyMissing $MaxBodyMissing `
  -MaxOcrNeeded $MaxOcrNeeded `
  -Strict
$storage = $storageJson | ConvertFrom-Json

$allOk = (
  $customs.Status -eq "success" -and
  $portfolio.Status -eq "success" -and
  $storage.Status -eq "success"
)

$result = [pscustomobject]@{
  Status = if ($allOk) { "success" } else { "warning" }
  BaseUrl = $BaseUrl
  Customs = [pscustomobject]@{
    Status = $customs.Status
    Period = $customs.Period
    LatestStorageSkipped = $customs.LatestStorageSkipped
    TotalTrendHttpStatusCode = $customs.TotalTrendHttpStatusCode
    TotalTrendHasStorage = $customs.TotalTrendHasStorage
  }
  PortfolioQuantity = [pscustomobject]@{
    Status = $portfolio.Status
    PortfolioName = $portfolio.PortfolioName
    Ticker = $portfolio.Ticker
    Quantity = $portfolio.Quantity
    ExpectedQuantity = $portfolio.ExpectedQuantity
    CheckedCount = $portfolio.CheckedCount
    FailedCount = $portfolio.FailedCount
    Currency = $portfolio.Currency
    SyncProtected = $portfolio.SyncProtected
    Items = @($portfolio.Items)
  }
  StorageQuality = [pscustomobject]@{
    Status = $storage.Status
    BodyMissingCount = $storage.BodyMissingCount
    BodyMissingItems = @($storage.BodyMissingItems)
    OcrNeededCount = $storage.OcrNeededCount
    ArchivedCount = $storage.ArchivedCount
    LegacyOrDuplicateCount = $storage.LegacyOrDuplicateCount
    NewsBodyStoragePolicy = $storage.NewsBodyStoragePolicy
    NextActions = @($storage.NextActions)
  }
  Message = if ($allOk) {
    "핵심 안전장치 확인 완료"
  } else {
    "핵심 안전장치 확인 필요"
  }
}

$json = $result | ConvertTo-Json -Depth 6
Write-Output $json

if ($Strict -and -not $allOk) {
  throw $result.Message
}
