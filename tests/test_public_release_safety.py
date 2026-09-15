"""Regression tests for public-source ZIP and authentication safety guards."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import HTTPException


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def load_public_safety_tool():
    path = PROJECT_ROOT / "tools" / "check_public_repo_safety.py"
    spec = importlib.util.spec_from_file_location("public_repo_safety_tool", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("공개 저장소 안전 점검 도구를 불러오지 못했습니다.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PublicReleaseSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tool = load_public_safety_tool()

    def test_real_sensitive_assignment_is_reported_without_exposing_value(self):
        secret_value = "Q7d4uG2vN8mR5sK9"
        self.assertTrue(self.tool.contains_secret_like_content(f"TOSS_CLIENT_SECRET={secret_value}"))
        self.assertFalse(self.tool.contains_secret_like_content("TOSS_CLIENT_SECRET=replace-with-client-secret"))

    def test_archive_scan_blocks_attachments_and_secret_values(self):
        secret_value = "Q7d4uG2vN8mR5sK9"
        with TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "public.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("dawn-desk/attachments/chat-export.md", "private attachment")
                archive.writestr("dawn-desk/notes/credentials.md", f"TOSS_CLIENT_SECRET={secret_value}")
                archive.writestr("dawn-desk/README.md", "safe text")

            result = self.tool.scan_archive(archive_path)

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertEqual(result["status"], "error")
        self.assertIn("dawn-desk/attachments/chat-export.md", result["path_issues"])
        self.assertIn("dawn-desk/notes/credentials.md", result["content_issues"])
        self.assertNotIn(secret_value, serialized)

    def test_safe_archive_accepts_example_environment_file(self):
        self.assertTrue(self.tool.is_forbidden_path("attachments/.env.example"))
        with TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "public.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("InvestmentJournalApp/README.md", "safe text")
                archive.writestr(
                    "InvestmentJournalApp/backend/.env.example",
                    "TOSS_CLIENT_SECRET=replace-with-client-secret\n",
                )

            result = self.tool.scan_archive(archive_path)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["path_issue_count"], 0)
        self.assertEqual(result["content_issue_count"], 0)


class AuthenticationSafetyTests(unittest.TestCase):
    def test_research_os_rejects_blank_configured_token(self):
        from research_os.security import verify_user_token
        from research_os.settings import Settings

        with self.assertRaises(HTTPException) as captured:
            verify_user_token(authorization="Bearer anything", settings=Settings(dev_user_token=""))

        self.assertEqual(captured.exception.status_code, 503)

    def test_legacy_app_rejects_blank_configured_token(self):
        from app.security import verify_user_token
        from app.settings import Settings

        with self.assertRaises(HTTPException) as captured:
            verify_user_token(authorization="Bearer anything", settings=Settings(dev_user_token=""))

        self.assertEqual(captured.exception.status_code, 503)
