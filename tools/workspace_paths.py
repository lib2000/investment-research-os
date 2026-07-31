"""Shared local workspace paths for Investment Research OS tools.

The workspace can be moved between drives without changing source code.  A
specific location may be supplied with environment variables when necessary,
otherwise paths are derived from this checked-out project.
"""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _environment_path(name: str) -> Path | None:
    value = os.getenv(name, "").strip()
    return Path(value).expanduser().resolve() if value else None


def workspace_root() -> Path:
    """Return the common workspace root, independent of the drive letter."""
    return _environment_path("INVESTMENT_WORKSPACE_ROOT") or PROJECT_ROOT.parent.resolve()


def trading_api_root() -> Path:
    """Return the strategy-builder/backtester checkout location."""
    return _environment_path("INVESTMENT_TRADING_API_ROOT") or (workspace_root() / "open-trading-api")


def openclaw_workspace_root() -> Path:
    """Return the shared OpenClaw workspace location."""
    return _environment_path("INVESTMENT_OPENCLAW_WORKSPACE") or (workspace_root() / "openclaw")


def openclaw_investment_dir() -> Path:
    """Return the sanitized Investment Research bridge directory."""
    return openclaw_workspace_root() / "data" / "investment_research"
