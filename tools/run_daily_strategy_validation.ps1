param(
  [string]$ProjectRoot = "",
  [string]$CredentialTarget = "InvestmentResearchOS/DEV_USER_TOKEN",
  [string]$ResearchApiBase = "http://127.0.0.1:8001",
  [string]$BuilderApiBase = "http://127.0.0.1:8000",
  [string]$BacktesterApiBase = "http://127.0.0.1:8002",
  [string]$StrategyId = "sma_crossover",
  [int]$LookbackCalendarDays = 210,
  [double]$InitialCapital = 100000000,
  [switch]$Force,
  [switch]$StartServicesIfNeeded,
  [switch]$StartDockerIfNeeded,
  [int]$DockerStartupTimeoutSeconds = 180
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$ProjectRootPath = & (Join-Path $PSScriptRoot "assert_project_root.ps1") -ProjectRoot $ProjectRoot -PassThru
. (Join-Path $ProjectRootPath "tools\investment_research_credential.ps1")

$SystemDir = Join-Path $ProjectRootPath "research_vault\_system"
$RuntimeDir = Join-Path $ProjectRootPath "tmp"
$RecommendationPath = Join-Path $SystemDir "daily_recommendations.json"
$StatePath = Join-Path $RuntimeDir "daily_strategy_validation_state.json"
$LogPath = Join-Path $RuntimeDir "daily_strategy_validation.log"
$Launcher = Join-Path $ProjectRootPath "scripts\start-integrated-investment-workbench.ps1"
$RunDate = Get-Date -Format "yyyy-MM-dd"

New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

function Write-TaskLog {
  param([string]$Message)
  $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"
  Add-Content -LiteralPath $LogPath -Value "[$timestamp] $Message" -Encoding UTF8
}

function Save-TaskState {
  param([System.Collections.IDictionary]$State)
  $tempPath = "$StatePath.tmp"
  $State | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $tempPath -Encoding UTF8
  Move-Item -LiteralPath $tempPath -Destination $StatePath -Force
}

function Test-ApiEndpoint {
  param([string]$Uri)
  try {
    Invoke-RestMethod -Uri $Uri -TimeoutSec 5 | Out-Null
    return $true
  } catch {
    return $false
  }
}

function Test-AllServices {
  return (
    (Test-ApiEndpoint -Uri "$ResearchApiBase/") -and
    (Test-ApiEndpoint -Uri "$BuilderApiBase/api/strategies") -and
    (Test-ApiEndpoint -Uri "$BacktesterApiBase/api/strategies")
  )
}

function Invoke-BoundedDocker {
  param([string[]]$Arguments, [int]$TimeoutSeconds = 5)
  $docker = Get-Command docker -ErrorAction SilentlyContinue
  if (-not $docker) { return -1 }
  $process = New-Object System.Diagnostics.Process
  $process.StartInfo = New-Object System.Diagnostics.ProcessStartInfo
  $process.StartInfo.FileName = $docker.Source
  $process.StartInfo.Arguments = ($Arguments -join " ")
  $process.StartInfo.UseShellExecute = $false
  $process.StartInfo.CreateNoWindow = $true
  $process.StartInfo.RedirectStandardOutput = $true
  $process.StartInfo.RedirectStandardError = $true
  try {
    if (-not $process.Start()) { return -1 }
    if (-not $process.WaitForExit([Math]::Max($TimeoutSeconds, 1) * 1000)) {
      try { $process.Kill() } catch { }
      return -1
    }
    return $process.ExitCode
  } finally {
    $process.Dispose()
  }
}

function Test-DockerEngine {
  return (Invoke-BoundedDocker -Arguments @("info", "--format", "{{.ServerVersion}}")) -eq 0
}

function Test-LeanImage {
  if (-not (Test-DockerEngine)) { return $false }
  # Full inspect JSON can fill the redirected pipe while the caller waits.
  # Ask Docker for one short field so the bounded probe cannot deadlock.
  return (Invoke-BoundedDocker -Arguments @("image", "inspect", "quantconnect/lean:latest", "--format", "{{.Id}}")) -eq 0
}

function Start-DockerRequirement {
  if (Test-DockerEngine) { return }
  if (-not $StartDockerIfNeeded) {
    throw "Docker Desktop Linux engine is unavailable. Use -StartDockerIfNeeded or start Docker Desktop first."
  }

  $candidates = @()
  if ($env:ProgramFiles) {
    $candidates += Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
  }
  $programFilesX86 = [Environment]::GetEnvironmentVariable("ProgramFiles(x86)")
  if ($programFilesX86) {
    $candidates += Join-Path $programFilesX86 "Docker\Docker\Docker Desktop.exe"
  }
  $candidates = @($candidates | Where-Object { Test-Path -LiteralPath $_ })
  $dockerDesktop = $candidates | Select-Object -First 1
  if (-not $dockerDesktop) { throw "Docker Desktop executable was not found." }

  Write-TaskLog "docker_start_requested"
  Start-Process -FilePath $dockerDesktop -WindowStyle Hidden
  $deadline = (Get-Date).AddSeconds([Math]::Max($DockerStartupTimeoutSeconds, 30))
  while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 5
    if (Test-DockerEngine) {
      Write-TaskLog "docker_start_ready"
      return
    }
  }
  throw "Docker Desktop Linux engine did not become ready within $DockerStartupTimeoutSeconds seconds."
}

function Start-RequiredServices {
  if (-not $StartServicesIfNeeded) {
    throw "One or more analysis services are unavailable. Use -StartServicesIfNeeded or start the integrated workbench first."
  }
  if (-not (Test-Path -LiteralPath $Launcher)) {
    throw "Integrated workbench launcher not found: $Launcher"
  }

  Write-TaskLog "service_start_requested"
  $launcherArguments = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$Launcher`""
  Start-Process -FilePath "powershell.exe" -ArgumentList $launcherArguments -WorkingDirectory $ProjectRootPath -WindowStyle Hidden

  $deadline = (Get-Date).AddMinutes(4)
  while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 5
    if (Test-AllServices) {
      Write-TaskLog "service_start_ready"
      return
    }
  }
  throw "Integrated workbench services did not become ready within four minutes."
}

$previousState = $null
if (Test-Path -LiteralPath $StatePath) {
  try {
    $previousState = [IO.File]::ReadAllText($StatePath, [Text.UTF8Encoding]::new($false)) | ConvertFrom-Json
  } catch {
    $previousState = $null
  }
}
if (-not $Force -and $previousState -and $previousState.status -eq "success" -and $previousState.run_date -eq $RunDate) {
  $skip = [ordered]@{
    status = "skipped"
    reason = "already_succeeded_today"
    run_date = $RunDate
    previous_completed_at = $previousState.completed_at
    previous_run_id = $previousState.backtest.run_id
  }
  Write-TaskLog "skip_already_succeeded_today: run_id=$($previousState.backtest.run_id)"
  $skip | ConvertTo-Json -Depth 6
  exit 0
}

$startedAt = (Get-Date).ToString("o")
$accessToken = $null
$state = [ordered]@{
  status = "running"
  run_date = $RunDate
  started_at = $startedAt
  completed_at = $null
  target = $null
  design_validation = $null
  backtest = $null
  research_store = $null
  safety = [ordered]@{
    live_order_endpoint_called = $false
    purpose = "research_and_simulation_only"
  }
  prerequisites = [ordered]@{
    docker_engine = $false
    lean_image = $false
  }
  error = $null
}
Save-TaskState -State $state

try {
  Start-DockerRequirement
  $state.prerequisites.docker_engine = Test-DockerEngine
  $state.prerequisites.lean_image = Test-LeanImage
  Save-TaskState -State $state
  if (-not $state.prerequisites.lean_image) {
    throw "Required Docker image is missing: quantconnect/lean:latest"
  }
  if (-not (Test-AllServices)) {
    Start-RequiredServices
  }
  if (-not (Test-AllServices)) {
    throw "Integrated workbench service health check failed."
  }

  if (-not (Test-Path -LiteralPath $RecommendationPath)) {
    throw "Daily recommendation store not found: $RecommendationPath"
  }
  # Task Scheduler launches Windows PowerShell 5.1, whose default file
  # encoding is not UTF-8. Read explicitly so Korean JSON remains valid.
  $recommendationJson = [IO.File]::ReadAllText($RecommendationPath, [Text.UTF8Encoding]::new($false))
  $recommendationStore = $recommendationJson | ConvertFrom-Json
  $target = $recommendationStore.records |
    Where-Object { $_.market -eq "KR" -and $_.ticker -match "^\d{6}$" } |
    Sort-Object -Property @{ Expression = "recommendation_date"; Descending = $true }, @{ Expression = "rank"; Descending = $false } |
    Select-Object -First 1
  if (-not $target) {
    throw "No valid Korean daily recommendation is available for strategy validation."
  }

  $state.target = [ordered]@{
    ticker = [string]$target.ticker
    company_name = [string]$target.company_name
    recommendation_date = [string]$target.recommendation_date
    rank = [int]$target.rank
    record_id = [string]$target.record_id
  }

  $designRequest = [ordered]@{
    name = "daily_sma_validation_$RunDate"
    buy_condition = "ma(5) crosses_above ma(20)"
    sell_condition = "ma(5) crosses_below ma(20)"
  }
  $designResult = Invoke-RestMethod `
    -Method Post `
    -Uri "$BuilderApiBase/api/strategies/preview" `
    -ContentType "application/json; charset=utf-8" `
    -Body ($designRequest | ConvertTo-Json -Depth 6) `
    -TimeoutSec 30
  if ($designResult.status -ne "success") {
    throw "Strategy design validation failed: $($designResult.message)"
  }
  $state.design_validation = [ordered]@{
    status = [string]$designResult.status
    required_days = [int]$designResult.required_days
    strategy_id = $StrategyId
    fast_period = 5
    slow_period = 20
    generated_code_persisted = $false
  }

  $endDate = (Get-Date).Date.AddDays(-1)
  $startDate = $endDate.AddDays(-1 * [Math]::Max($LookbackCalendarDays, 120))
  $backtestRequest = [ordered]@{
    strategy_id = $StrategyId
    symbols = @([string]$target.ticker)
    start_date = $startDate.ToString("yyyy-MM-dd")
    end_date = $endDate.ToString("yyyy-MM-dd")
    initial_capital = $InitialCapital
    commission_rate = 0.00015
    tax_rate = 0.002
    slippage = 0.0
    param_overrides = [ordered]@{
      fast_period = 5
      slow_period = 20
      stop_loss_pct = 5.0
      take_profit_pct = 10.0
    }
  }
  Write-TaskLog "backtest_start: ticker=$($target.ticker), start=$($backtestRequest.start_date), end=$($backtestRequest.end_date)"
  $backtestResult = Invoke-RestMethod `
    -Method Post `
    -Uri "$BacktesterApiBase/api/backtest/run" `
    -ContentType "application/json; charset=utf-8" `
    -Body ($backtestRequest | ConvertTo-Json -Depth 8) `
    -TimeoutSec 1800
  if (-not $backtestResult.success -or -not $backtestResult.data) {
    throw "Backtest API returned an unsuccessful result."
  }

  $data = $backtestResult.data
  $storedRunId = ("daily_{0}_{1}_{2}" -f $RunDate.Replace("-", ""), $StrategyId, $target.ticker)
  $storeRequest = [ordered]@{
    run_id = $storedRunId
    symbols = @([string]$target.ticker)
    # Keep the persisted label stable even when Windows PowerShell 5.1
    # misdetects the API response charset for non-ASCII text.
    strategy_name = "SMA 5/20 Golden/Death Cross"
    start_date = [string]$data.start_date
    end_date = [string]$data.end_date
    initial_capital = [double]$data.initial_capital
    final_capital = [double]$data.final_capital
    total_return = [double]$data.net_profit_percent
    max_drawdown = [double]$data.metrics.basic.max_drawdown
    win_rate = [double]$data.metrics.trading.win_rate
    trades_count = [int]$data.trades_count
    sharpe_ratio = [double]$data.metrics.risk.sharpe_ratio
  }

  $accessToken = Get-InvestmentResearchCredentialSecret -Target $CredentialTarget
  if ([string]::IsNullOrWhiteSpace($accessToken)) {
    throw "Windows Credential Manager credential is missing: $CredentialTarget"
  }
  $storeResult = Invoke-RestMethod `
    -Method Post `
    -Uri "$ResearchApiBase/api/v1/backtest-runs" `
    -Headers @{ Authorization = "Bearer $accessToken" } `
    -ContentType "application/json; charset=utf-8" `
    -Body ($storeRequest | ConvertTo-Json -Depth 8) `
    -TimeoutSec 30

  $state.backtest = [ordered]@{
    run_id = $storedRunId
    engine_run_id = [string]$data.run_id
    strategy_name = "SMA 5/20 Golden/Death Cross"
    start_date = [string]$data.start_date
    end_date = [string]$data.end_date
    total_return = [double]$data.net_profit_percent
    max_drawdown = [double]$data.metrics.basic.max_drawdown
    win_rate = [double]$data.metrics.trading.win_rate
    trades_count = [int]$data.trades_count
    sharpe_ratio = [double]$data.metrics.risk.sharpe_ratio
  }
  $state.research_store = [ordered]@{
    status = [string]$storeResult.status
    source = [string]$storeResult.run.source
    captured_at = [string]$storeResult.run.captured_at
  }
  $state.status = "success"
  $state.completed_at = (Get-Date).ToString("o")
  Save-TaskState -State $state
  Write-TaskLog "success: run_id=$storedRunId, ticker=$($target.ticker), return=$($data.net_profit_percent)"
  $state | ConvertTo-Json -Depth 12
} catch {
  $state.status = "failed"
  $state.completed_at = (Get-Date).ToString("o")
  $safeError = [string]$_.Exception.Message
  if ($safeError.Length -gt 1000) { $safeError = $safeError.Substring(0, 1000) }
  $state.error = $safeError
  Save-TaskState -State $state
  Write-TaskLog "failed: $($state.error)"
  throw
} finally {
  $accessToken = $null
}
