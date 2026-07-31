from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = PROJECT_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import workspace_paths


class WorkspacePathsTest(unittest.TestCase):
    def test_defaults_follow_project_workspace(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(workspace_paths.workspace_root(), PROJECT_ROOT.parent)
            self.assertEqual(workspace_paths.trading_api_root(), PROJECT_ROOT.parent / "open-trading-api")
            self.assertEqual(workspace_paths.openclaw_workspace_root(), PROJECT_ROOT.parent / "openclaw")
            self.assertEqual(
                workspace_paths.openclaw_investment_dir(),
                PROJECT_ROOT.parent / "openclaw" / "data" / "investment_research",
            )

    def test_environment_overrides_are_respected(self) -> None:
        with patch.dict(
            os.environ,
            {
                "INVESTMENT_WORKSPACE_ROOT": str(PROJECT_ROOT.parent / "alternate-workspace"),
                "INVESTMENT_TRADING_API_ROOT": str(PROJECT_ROOT.parent / "alternate-trading"),
                "INVESTMENT_OPENCLAW_WORKSPACE": str(PROJECT_ROOT.parent / "alternate-openclaw"),
            },
            clear=True,
        ):
            self.assertEqual(workspace_paths.workspace_root(), (PROJECT_ROOT.parent / "alternate-workspace").resolve())
            self.assertEqual(workspace_paths.trading_api_root(), (PROJECT_ROOT.parent / "alternate-trading").resolve())
            self.assertEqual(workspace_paths.openclaw_workspace_root(), (PROJECT_ROOT.parent / "alternate-openclaw").resolve())


if __name__ == "__main__":
    unittest.main()
