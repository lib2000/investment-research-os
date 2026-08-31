from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_script(name: str) -> str:
    return (ROOT / "tools" / name).read_text(encoding="utf-8")


def test_runner_uses_design_backtest_and_research_store_contracts() -> None:
    source = read_script("run_daily_strategy_validation.ps1")

    assert "/api/strategies/preview" in source
    assert "/api/backtest/run" in source
    assert "/api/v1/backtest-runs" in source
    assert "already_succeeded_today" in source
    assert '[string]$RunDate = ""' in source
    assert "RunDate must use YYYY-MM-DD format." in source
    assert "recommendation_date -le $RunDate" in source
    assert 'live_order_endpoint_called = $false' in source
    assert "[IO.File]::ReadAllText($RecommendationPath" in source
    assert 'strategy_name = "SMA 5/20 Golden/Death Cross"' in source


def test_runner_never_calls_strategy_execution_endpoint() -> None:
    source = read_script("run_daily_strategy_validation.ps1")

    assert "/api/strategies/execute" not in source
    assert "/api/order" not in source


def test_runner_recovers_docker_and_requires_lean_image() -> None:
    source = read_script("run_daily_strategy_validation.ps1")

    assert "[switch]$StartDockerIfNeeded" in source
    assert "Start-DockerRequirement" in source
    assert "Test-DockerRuntimeSocketFailure" in source
    assert "Move-DockerRuntimeSocketDirectories" in source
    assert "docker_runtime_socket_recovery_ready" in source
    assert "run.stale" in source
    assert "quantconnect/lean:latest" in source
    assert '"--format", "{{.Id}}"' in source
    assert "-WindowStyle Hidden" in source


def test_runner_retries_only_transient_backtester_transport_failures() -> None:
    source = read_script("run_daily_strategy_validation.ps1")

    assert "[int]$BacktestRetryCount = 2" in source
    assert "Test-TransientBacktestTransportFailure" in source
    assert "Invoke-BacktestWithRetry" in source
    assert "backtest_transport_retry" in source
    assert "backtest_complete: attempts=" in source
    assert "[System.Net.WebException]" in source
    assert "ConnectionClosed" in source
    assert "System.Net.Http.HttpRequestException" in source
    assert "$backtestAttempt = Invoke-BacktestWithRetry" in source
    assert '"$BacktesterApiBase/api/strategies"' in source


def test_daily_operations_uses_exit_codes_when_capturing_native_diagnostics() -> None:
    source = read_script("run_daily_research_operations.ps1")

    assert '$previousErrorActionPreference = $ErrorActionPreference' in source
    assert '$ErrorActionPreference = "Continue"' in source
    assert "$stepOutput = @(& $Block 2>&1)" in source
    assert "$stepExitCode = $LASTEXITCODE" in source


def test_verify_console_uses_exit_codes_when_capturing_native_diagnostics() -> None:
    source = read_script("verify_research_console.ps1")

    assert '$previousErrorActionPreference = $ErrorActionPreference' in source
    assert '$ErrorActionPreference = "Continue"' in source
    assert "$stepOutput = @(& $Block 2>&1)" in source
    assert "$stepExitCode = $LASTEXITCODE" in source


def test_boot_catchup_uses_explicit_project_python_for_family_audit() -> None:
    source = read_script("run_investment_research_catchup.ps1")

    assert "Set-Location -LiteralPath $ProjectRootPath" in source
    assert '$ProjectPython = Join-Path $ProjectRootPath ".venv-win\\Scripts\\python.exe"' in source
    assert "& $ProjectPython $FamilyAggregateAudit --write-state --strict --json" in source
    assert "Task Scheduler does not guarantee that a global Python PATH is present." in source


def test_scheduled_task_catches_up_and_does_not_expose_token() -> None:
    source = read_script("register_daily_strategy_validation_task.ps1")

    assert "-StartWhenAvailable" in source
    assert "-MultipleInstances IgnoreNew" in source
    assert "-RestartCount 2" in source
    assert '"-StartDockerIfNeeded"' in source
    assert "Get-InvestmentResearchCredentialSecret" not in source
    assert "DEV_USER_TOKEN=" not in source
