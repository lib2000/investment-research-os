param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp",
  [string]$BaseUrl = "http://127.0.0.1:8001",
  [string]$DevUserToken = "dev-local-token",
  [string]$PortfolioName = "이형주",
  [string]$Ticker = "PL",
  [double]$ExpectedQuantity = 100,
  [string]$ExpectedCurrency = "USD",
  [switch]$Strict
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
Set-Location -LiteralPath $ProjectRootPath

$headers = @{ Authorization = "Bearer $DevUserToken" }
$encodedPortfolioName = [uri]::EscapeDataString($PortfolioName)
$uri = "$BaseUrl/api/v1/portfolios/${encodedPortfolioName}?refresh_prices=false&persist_refresh=false"

try {
  $response = Invoke-RestMethod -Uri $uri -Method Get -Headers $headers -TimeoutSec 20
} catch {
  throw "포트폴리오 조회 실패: $($_.Exception.Message)"
}

$portfolio = $response.active_portfolio
if (-not $portfolio) {
  throw "포트폴리오 응답에 active_portfolio가 없습니다. 단건 포트폴리오 API 응답 구조를 확인하세요."
}

$holding = @($portfolio.holdings | Where-Object { $_.ticker -eq $Ticker } | Select-Object -First 1)
if (-not $holding) {
  throw "$PortfolioName 포트폴리오에서 $Ticker 보유 종목을 찾지 못했습니다."
}

$quantityOk = [math]::Abs(([double]$holding.quantity) - $ExpectedQuantity) -lt 0.000001
$currencyOk = ([string]$holding.currency) -eq $ExpectedCurrency
$syncStatus = [string]$holding.sync_status
$syncSource = [string]$holding.sync_source
$syncProtected = $syncStatus -in @("", "manual_or_overseas_protected", $null) -or $syncSource -in @("manual_quantity_protected")
$priceStatus = [string]$holding.price_refresh_status

$result = [pscustomobject]@{
  Status = if ($quantityOk -and $currencyOk -and $syncProtected) { "success" } else { "warning" }
  PortfolioName = $portfolio.portfolio_name
  HoldingCount = @($portfolio.holdings).Count
  Ticker = $holding.ticker
  Name = $holding.name
  Quantity = [double]$holding.quantity
  ExpectedQuantity = $ExpectedQuantity
  QuantityOk = $quantityOk
  Currency = $holding.currency
  ExpectedCurrency = $ExpectedCurrency
  CurrencyOk = $currencyOk
  SyncStatus = $holding.sync_status
  SyncSource = $holding.sync_source
  SyncProtected = $syncProtected
  PriceRefreshStatus = $priceStatus
  UpdatedAt = $portfolio.updated_at
  Message = if ($quantityOk -and $currencyOk -and $syncProtected) {
    "$PortfolioName $Ticker 수량 보호 확인 완료"
  } else {
    "$PortfolioName $Ticker 수량/통화/동기화 보호 상태 확인 필요"
  }
}

$json = $result | ConvertTo-Json -Depth 4
Write-Output $json

if ($Strict -and $result.Status -ne "success") {
  throw $result.Message
}
