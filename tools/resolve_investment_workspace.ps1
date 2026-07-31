function Get-InvestmentWorkspacePaths {
  param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot
  )

  $resolvedProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
  $workspaceRoot = if ([string]::IsNullOrWhiteSpace($env:INVESTMENT_WORKSPACE_ROOT)) {
    Split-Path -Parent $resolvedProjectRoot
  } else {
    (Resolve-Path -LiteralPath $env:INVESTMENT_WORKSPACE_ROOT).Path
  }
  $openClawWorkspace = if ([string]::IsNullOrWhiteSpace($env:INVESTMENT_OPENCLAW_WORKSPACE)) {
    Join-Path $workspaceRoot "openclaw"
  } else {
    $env:INVESTMENT_OPENCLAW_WORKSPACE
  }
  $tradingApiRoot = if ([string]::IsNullOrWhiteSpace($env:INVESTMENT_TRADING_API_ROOT)) {
    Join-Path $workspaceRoot "open-trading-api"
  } else {
    $env:INVESTMENT_TRADING_API_ROOT
  }

  [pscustomobject]@{
    WorkspaceRoot = $workspaceRoot
    OpenClawWorkspace = $openClawWorkspace
    TradingApiRoot = $tradingApiRoot
  }
}
