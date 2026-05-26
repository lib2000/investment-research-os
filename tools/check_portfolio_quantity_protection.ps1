param(
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp",
  [string]$BaseUrl = "http://127.0.0.1:8001",
  [string]$DevUserToken = "dev-local-token",
  [string]$PortfolioName = "이형주",
  [string]$Ticker = "PL",
  [double]$ExpectedQuantity = 100,
  [string]$ExpectedCurrency = "USD",
  [string]$ExpectedHoldings = "",
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

function New-ExpectedHoldingCheck {
  param(
    [Parameter(Mandatory = $true)][string]$Ticker,
    [Parameter(Mandatory = $true)][double]$Quantity,
    [Parameter(Mandatory = $true)][string]$Currency
  )
  [pscustomobject]@{
    Ticker = $Ticker.Trim().ToUpperInvariant()
    ExpectedQuantity = $Quantity
    ExpectedCurrency = $Currency.Trim().ToUpperInvariant()
  }
}

$expectedChecks = @()
if ($ExpectedHoldings.Trim()) {
  foreach ($rawItem in $ExpectedHoldings.Split(",", [System.StringSplitOptions]::RemoveEmptyEntries)) {
    $item = $rawItem.Trim()
    if ($item -notmatch "^(?<ticker>[^=]+)=(?<quantity>-?\d+(\.\d+)?)(:(?<currency>[A-Za-z]{3}))?$") {
      throw "ExpectedHoldings 항목 형식이 잘못되었습니다: $item. 예: PL=100:USD,JOBY=208:USD"
    }
    $currency = if ($Matches.currency) { $Matches.currency } else { $ExpectedCurrency }
    $expectedChecks += New-ExpectedHoldingCheck -Ticker $Matches.ticker -Quantity ([double]$Matches.quantity) -Currency $currency
  }
} else {
  $expectedChecks += New-ExpectedHoldingCheck -Ticker $Ticker -Quantity $ExpectedQuantity -Currency $ExpectedCurrency
}

$items = foreach ($check in $expectedChecks) {
  $holding = @($portfolio.holdings | Where-Object { $_.ticker -eq $check.Ticker } | Select-Object -First 1)
  if (-not $holding) {
    [pscustomobject]@{
      Status = "warning"
      Ticker = $check.Ticker
      Name = $null
      Quantity = $null
      ExpectedQuantity = $check.ExpectedQuantity
      QuantityOk = $false
      Currency = $null
      ExpectedCurrency = $check.ExpectedCurrency
      CurrencyOk = $false
      SyncStatus = $null
      SyncSource = $null
      SyncProtected = $false
      PriceRefreshStatus = $null
      Message = "$PortfolioName 포트폴리오에서 $($check.Ticker) 보유 종목을 찾지 못했습니다."
    }
    continue
  }

  $quantityOk = [math]::Abs(([double]$holding.quantity) - $check.ExpectedQuantity) -lt 0.000001
  $currencyOk = ([string]$holding.currency).ToUpperInvariant() -eq $check.ExpectedCurrency
  $syncStatus = [string]$holding.sync_status
  $syncSource = [string]$holding.sync_source
  $syncProtected = $syncStatus -eq "manual_or_overseas_protected" -or $syncSource -eq "manual_quantity_protected"
  $priceStatus = [string]$holding.price_refresh_status

  [pscustomobject]@{
    Status = if ($quantityOk -and $currencyOk -and $syncProtected) { "success" } else { "warning" }
    Ticker = $holding.ticker
    Name = $holding.name
    Quantity = [double]$holding.quantity
    ExpectedQuantity = $check.ExpectedQuantity
    QuantityOk = $quantityOk
    Currency = $holding.currency
    ExpectedCurrency = $check.ExpectedCurrency
    CurrencyOk = $currencyOk
    SyncStatus = $holding.sync_status
    SyncSource = $holding.sync_source
    SyncProtected = $syncProtected
    PriceRefreshStatus = $priceStatus
    Message = if ($quantityOk -and $currencyOk -and $syncProtected) {
      "$PortfolioName $($holding.ticker) 수량 보호 확인 완료"
    } else {
      "$PortfolioName $($check.Ticker) 수량/통화/동기화 보호 상태 확인 필요"
    }
  }
}

$allOk = @($items | Where-Object { $_.Status -ne "success" }).Count -eq 0
$first = @($items | Select-Object -First 1)

$result = [pscustomobject]@{
  Status = if ($allOk) { "success" } else { "warning" }
  PortfolioName = $portfolio.portfolio_name
  HoldingCount = @($portfolio.holdings).Count
  CheckedCount = @($items).Count
  FailedCount = @($items | Where-Object { $_.Status -ne "success" }).Count
  Ticker = $first.Ticker
  Name = $first.Name
  Quantity = $first.Quantity
  ExpectedQuantity = $first.ExpectedQuantity
  QuantityOk = $first.QuantityOk
  Currency = $first.Currency
  ExpectedCurrency = $first.ExpectedCurrency
  CurrencyOk = $first.CurrencyOk
  SyncStatus = $first.SyncStatus
  SyncSource = $first.SyncSource
  SyncProtected = $first.SyncProtected
  PriceRefreshStatus = $first.PriceRefreshStatus
  Items = @($items)
  UpdatedAt = $portfolio.updated_at
  Message = if ($allOk) {
    "$PortfolioName 수량 보호 확인 완료: $(@($items).Count)개"
  } else {
    "$PortfolioName 수량/통화/동기화 보호 상태 확인 필요: $(@($items | Where-Object { $_.Status -ne "success" }).Count)개"
  }
}

$json = $result | ConvertTo-Json -Depth 4
Write-Output $json

if ($Strict -and $result.Status -ne "success") {
  throw $result.Message
}
