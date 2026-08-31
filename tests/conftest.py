"""Pytest guards for user-owned local state.

Some legacy regression tests construct a Settings instance that resolves to the
checked-out research vault.  Keep those tests useful without allowing a test
fixture to replace the user's saved portfolios.
"""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
USER_PORTFOLIO_STORE = PROJECT_ROOT / "research_vault" / "_system" / "user_portfolios.json"


@pytest.fixture(autouse=True)
def preserve_user_portfolio_store():
    """Restore the user portfolio store after each test that touches it."""
    original = USER_PORTFOLIO_STORE.read_bytes() if USER_PORTFOLIO_STORE.exists() else None
    yield
    if original is None:
        USER_PORTFOLIO_STORE.unlink(missing_ok=True)
        return

    USER_PORTFOLIO_STORE.parent.mkdir(parents=True, exist_ok=True)
    temporary = USER_PORTFOLIO_STORE.with_name(
        f"{USER_PORTFOLIO_STORE.name}.pytest-restore-{uuid4().hex}.tmp"
    )
    temporary.write_bytes(original)
    os.replace(temporary, USER_PORTFOLIO_STORE)
