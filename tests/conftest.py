"""Pytest guards for user-owned local state.

Legacy tests often construct ``Settings(research_vault_dir="../research_vault")``.
That value resolves to the live checkout vault, so a seemingly isolated unit test
can overwrite scheduler state or portfolio data. Redirect only that exact live
vault to a per-test temporary vault while leaving explicitly supplied temporary
paths alone.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
PRODUCTION_VAULT = (PROJECT_ROOT / "research_vault").resolve()

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture(autouse=True)
def isolate_project_research_vault(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Redirect accidental live-vault access to a disposable test vault.

    Explicit ``tmp_path``-backed vaults used by focused tests are preserved.
    The portfolio snapshot is copied as read-only input because several legacy
    regression tests validate the current schema before replacing it locally.
    """

    from research_os import research_memory

    # Keep this name distinct from the conventional ``tmp_path/research_vault``
    # used by focused tests that intentionally create that directory themselves.
    test_vault = (tmp_path / "_isolated_live_research_vault").resolve()
    test_system_dir = test_vault / "_system"
    test_system_dir.mkdir(parents=True, exist_ok=True)

    portfolio_source = PRODUCTION_VAULT / "_system" / "user_portfolios.json"
    if portfolio_source.exists():
        shutil.copy2(portfolio_source, test_system_dir / portfolio_source.name)

    original_resolve_vault_dir = research_memory.resolve_vault_dir

    def isolated_resolve_vault_dir(configured_dir: str) -> Path:
        resolved = original_resolve_vault_dir(configured_dir)
        if resolved == PRODUCTION_VAULT:
            return test_vault
        return resolved

    monkeypatch.setenv("INVESTMENTJOURNALAPP_PYTEST_VAULT", str(test_vault))
    monkeypatch.setattr(
        research_memory,
        "resolve_vault_dir",
        isolated_resolve_vault_dir,
    )

    # Modules imported during collection may already hold the original function
    # through ``from research_memory import resolve_vault_dir``.
    for module in tuple(sys.modules.values()):
        if module is None:
            continue
        if getattr(module, "resolve_vault_dir", None) is original_resolve_vault_dir:
            monkeypatch.setattr(
                module,
                "resolve_vault_dir",
                isolated_resolve_vault_dir,
            )

    yield
