"""Unattended verification: ruff, mypy, import-linter, pytest, and TypeScript typecheck."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOBILE_APP = ROOT / "apps" / "mobile"
PYTEST_EXTRA: tuple[str, ...] = (
    "--ignore",
    "tests/test_backtest_result_store.py",
    "--ignore",
    "tests/test_investment_workbench_status.py",
    "--deselect",
    "tests/test_backend_regressions.py::ConsoleSmokeToolTests::test_daily_research_operations_syncs_openclaw_bridge",
)
LINT_IMPORTS = (
    "from importlinter.cli import lint_imports; "
    "raise SystemExit(lint_imports(no_logo=True, no_cache=True))"
)


def _pythonpath_env() -> dict[str, str]:
    env = os.environ.copy()
    backend = str(ROOT / "backend")
    current = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = backend if not current else os.pathsep.join((backend, current))
    return env


def _npm_executable() -> str:
    if os.name == "nt":
        return "npm.cmd"
    return "npm"


def _run(
    command: list[str],
    *,
    env: dict[str, str] | None = None,
    cwd: Path = ROOT,
) -> int:
    print("+ " + " ".join(command), flush=True)
    completed = subprocess.run(command, cwd=cwd, env=env, check=False)
    return completed.returncode


def _npm_typecheck() -> int:
    npm = _npm_executable()
    install_code = _run([npm, "ci"], cwd=MOBILE_APP)
    if install_code != 0:
        return install_code
    return _run([npm, "run", "typecheck"], cwd=MOBILE_APP)


def main() -> int:
    print(
        "verify: ruff check, mypy, import-linter, pytest, apps/mobile typecheck",
        flush=True,
    )
    env = _pythonpath_env()
    steps: tuple[tuple[list[str], dict[str, str] | None], ...] = (
        ([sys.executable, "-m", "ruff", "check", "backend", "tools", "tests"], None),
        ([sys.executable, "-m", "mypy"], env),
        ([sys.executable, "-c", LINT_IMPORTS], env),
        (
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests",
                "-m",
                "not live_server and not network",
                *PYTEST_EXTRA,
            ],
            None,
        ),
    )
    for command, command_env in steps:
        code = _run(command, env=command_env)
        if code != 0:
            return code
    return _npm_typecheck()


if __name__ == "__main__":
    raise SystemExit(main())
