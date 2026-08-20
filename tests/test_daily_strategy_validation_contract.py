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
    assert "quantconnect/lean:latest" in source
    assert '"--format", "{{.Id}}"' in source
    assert "-WindowStyle Hidden" in source


def test_scheduled_task_catches_up_and_does_not_expose_token() -> None:
    source = read_script("register_daily_strategy_validation_task.ps1")

    assert "-StartWhenAvailable" in source
    assert "-MultipleInstances IgnoreNew" in source
    assert "-RestartCount 2" in source
    assert '"-StartDockerIfNeeded"' in source
    assert "Get-InvestmentResearchCredentialSecret" not in source
    assert "DEV_USER_TOKEN=" not in source
