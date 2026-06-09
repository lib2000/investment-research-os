param(
  [string]$BaseUrl = "http://127.0.0.1:8001",
  [string]$DevUserToken = "dev-local-token",
  [string]$ProjectRoot = "C:\Users\lib20\InvestmentJournalApp",
  [string[]]$PortfolioNames = @(),
  [switch]$SkipCheck,
  [string]$ExpectedMainHoldings = "PL=100:USD,JOBY=208:USD,CHPT=22:USD,ABSI=29:USD,GOTU=50:USD,OTLY=8:USD,RXRX=9:USD,253450=36:KRW"
)

$ErrorActionPreference = "Stop"
Set-Location $ProjectRoot

$storePath = Join-Path $ProjectRoot "research_vault\_system\user_portfolios.json"
if (-not (Test-Path $storePath)) {
  throw "포트폴리오 저장 파일을 찾지 못했습니다: $storePath"
}

if (-not $PortfolioNames -or $PortfolioNames.Count -eq 0) {
  $store = Get-Content $storePath -Raw -Encoding UTF8 | ConvertFrom-Json
  $PortfolioNames = @(
    $store.portfolios.PSObject.Properties | ForEach-Object {
      if ($_.Value.portfolio_name) { [string]$_.Value.portfolio_name } else { [string]$_.Name }
    }
  )
}

$headers = @{ Authorization = "Bearer $DevUserToken" }
$refreshed = @()
$failed = @()

foreach ($portfolioName in $PortfolioNames) {
  $encodedName = [uri]::EscapeDataString($portfolioName)
  $uri = "$($BaseUrl.TrimEnd('/'))/api/v1/portfolios/${encodedName}?refresh_prices=true&persist_refresh=true"
  try {
    $response = Invoke-RestMethod -Method Get -Uri $uri -Headers $headers
    $active = $response.active_portfolio
    $refreshed += [pscustomobject]@{
      portfolio_name = $active.portfolio_name
      holding_count = $active.holding_count
      updated_at = $active.updated_at
      storage_path = $response.storage_path
    }
  } catch {
    $failed += [pscustomobject]@{
      portfolio_name = $portfolioName
      error = $_.Exception.Message
    }
  }
}

$result = [pscustomobject]@{
  status = if ($failed.Count -eq 0) { "success" } else { "partial" }
  refreshed = $refreshed
  failures = $failed
}
$result | ConvertTo-Json -Depth 6

if ($failed.Count -gt 0) {
  exit 1
}

if (-not $SkipCheck) {
  $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
  if ($null -eq $pythonCommand) {
    Write-Host "검증용 python 명령을 찾지 못했습니다. 가격 갱신은 완료됐고, 검증은 Codex/WSL에서 tools\check_all_portfolio_store.py로 이어서 실행하세요."
  } else {
    & $pythonCommand.Source tools\check_all_portfolio_store.py --min-holdings 1 --forbid-zero
    & $pythonCommand.Source tools\check_portfolio_store.py --portfolio "이형주" --expected-holdings-count 17 --expected $ExpectedMainHoldings --forbid-zero
  }
}
