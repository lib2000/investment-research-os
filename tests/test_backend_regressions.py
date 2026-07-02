import sys
import unittest
import ast
import base64
import copy
import json
import os
import subprocess
from datetime import date
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def load_console_hash_tool():
    tool_path = PROJECT_ROOT / "tools" / "update_console_asset_hashes.py"
    spec = spec_from_file_location("update_console_asset_hashes", tool_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def load_code_knowledge_graph_check_tool():
    tools_dir = PROJECT_ROOT / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    tool_path = tools_dir / "check_code_knowledge_graph.py"
    spec = spec_from_file_location("check_code_knowledge_graph", tool_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def load_code_knowledge_graph_builder_tool():
    tools_dir = PROJECT_ROOT / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    tool_path = tools_dir / "build_code_knowledge_graph.py"
    spec = spec_from_file_location("build_code_knowledge_graph", tool_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_code_diff_impact_tool():
    tools_dir = PROJECT_ROOT / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    tool_path = tools_dir / "analyze_code_diff_impact.py"
    spec = spec_from_file_location("analyze_code_diff_impact", tool_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def load_firecrawl_ir_check_tool():
    tools_dir = PROJECT_ROOT / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    tool_path = tools_dir / "check_firecrawl_ir_collector.py"
    spec = spec_from_file_location("check_firecrawl_ir_collector", tool_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def load_public_ir_sec_store_check_tool():
    tools_dir = PROJECT_ROOT / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    tool_path = tools_dir / "check_public_ir_sec_store.py"
    spec = spec_from_file_location("check_public_ir_sec_store", tool_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def load_offline_readiness_tool():
    tools_dir = PROJECT_ROOT / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    tool_path = tools_dir / "check_offline_readiness.py"
    spec = spec_from_file_location("check_offline_readiness", tool_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def load_operational_readiness_tool():
    tools_dir = PROJECT_ROOT / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    tool_path = tools_dir / "check_operational_readiness_score.py"
    spec = spec_from_file_location("check_operational_readiness_score", tool_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def load_policy_signal_check_tool():
    tools_dir = PROJECT_ROOT / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    tool_path = tools_dir / "check_daily_recommendation_policy_signals.py"
    spec = spec_from_file_location("check_daily_recommendation_policy_signals", tool_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def load_investment_insight_hub_check_tool():
    tools_dir = PROJECT_ROOT / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    tool_path = tools_dir / "check_investment_insight_hub.py"
    spec = spec_from_file_location("check_investment_insight_hub", tool_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def load_daily_recommendation_render_layout_tool():
    tools_dir = PROJECT_ROOT / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    tool_path = tools_dir / "check_daily_recommendation_render_layout.py"
    spec = spec_from_file_location("check_daily_recommendation_render_layout", tool_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def load_news_inbox_priority_queue_tool():
    tools_dir = PROJECT_ROOT / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    tool_path = tools_dir / "check_news_inbox_priority_queue.py"
    spec = spec_from_file_location("check_news_inbox_priority_queue", tool_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def load_storage_duplicate_review_tool():
    tools_dir = PROJECT_ROOT / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    tool_path = tools_dir / "check_storage_duplicate_review.py"
    spec = spec_from_file_location("check_storage_duplicate_review", tool_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def load_macro_source_signal_linkage_tool():
    tools_dir = PROJECT_ROOT / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    tool_path = tools_dir / "check_macro_source_signal_linkage.py"
    spec = spec_from_file_location("check_macro_source_signal_linkage", tool_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def load_daily_recommendation_citations_tool():
    tools_dir = PROJECT_ROOT / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    tool_path = tools_dir / "check_daily_recommendation_citations.py"
    spec = spec_from_file_location("check_daily_recommendation_citations", tool_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def load_telegram_brief_check_tool():
    tools_dir = PROJECT_ROOT / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    tool_path = tools_dir / "check_telegram_brief_sender.py"
    spec = spec_from_file_location("check_telegram_brief_sender", tool_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def load_write_actions_smoke_tool():
    tools_dir = PROJECT_ROOT / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    tool_path = tools_dir / "smoke_research_console_write_actions.py"
    spec = spec_from_file_location("smoke_research_console_write_actions", tool_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def load_clicks_smoke_tool():
    tools_dir = PROJECT_ROOT / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    tool_path = tools_dir / "smoke_research_console_clicks.py"
    spec = spec_from_file_location("smoke_research_console_clicks", tool_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class ConsoleSmokeToolTests(unittest.TestCase):
    def test_click_smoke_exposes_ordered_partial_stages(self):
        tool = load_clicks_smoke_tool()

        self.assertEqual(
            tool.STOP_AFTER_STAGE_ORDER,
            (
                "dashboard",
                "analysis-forms",
                "portfolio",
                "system-automation",
                "public-ir-sec",
                "memory-sources",
                "recommendations-calendar",
            ),
        )
        self.assertEqual(tool.STOP_AFTER_STAGES, set(tool.STOP_AFTER_STAGE_ORDER))

    def test_smoke_tools_allocate_bindable_devtools_port(self):
        import socket

        tool = load_clicks_smoke_tool()
        port = tool.free_devtools_port()

        self.assertIsInstance(port, int)
        self.assertGreater(port, 0)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", port))

    def test_click_smoke_normalizes_progress_heartbeat_interval(self):
        tool = load_clicks_smoke_tool()

        self.assertEqual(tool.normalize_progress_heartbeat_seconds(None), 30.0)
        self.assertEqual(tool.normalize_progress_heartbeat_seconds("0"), 1.0)
        self.assertEqual(tool.normalize_progress_heartbeat_seconds("2.5"), 2.5)
        self.assertEqual(tool.normalize_progress_heartbeat_seconds("bad"), 30.0)

    def test_click_smoke_covers_firecrawl_ir_dry_run_button(self):
        smoke_source = (PROJECT_ROOT / "tools" / "smoke_research_console_clicks.py").read_text(encoding="utf-8")

        self.assertIn("#publicIrSecFirecrawlDryRunButton", smoke_source)
        self.assertIn('"public-ir-sec"', smoke_source)
        self.assertIn("--only-public-ir-sec", smoke_source)
        self.assertIn("publicIrSecFirecrawlDryRunShowsSafeStatus", smoke_source)
        self.assertIn("firecrawl_api_key_missing", smoke_source)
        self.assertIn("publicIrSecStatusApiFallback", smoke_source)
        self.assertIn("clickAndWaitForStart", smoke_source)
        self.assertIn("needs_body_copy_entries", smoke_source)
        self.assertIn("needs_body_duplicate_title_groups", smoke_source)
        self.assertIn("동일 제목 보강 그룹", smoke_source)

    def test_console_public_ir_sec_status_lists_body_followups(self):
        console_source = (PROJECT_ROOT / "mobile_app" / "research_console" / "console.js").read_text(
            encoding="utf-8"
        )

        self.assertIn("needs_body_copy_entries", console_source)
        self.assertIn("needs_body_duplicate_title_groups", console_source)
        self.assertIn("본문 보강 대상", console_source)
        self.assertIn("동일 제목 보강 그룹", console_source)

    def test_windows_smoke_wrapper_exposes_public_ir_sec_utf8_mode(self):
        smoke_path = PROJECT_ROOT / "tools" / "smoke_research_console_windows.ps1"
        smoke_source = smoke_path.read_text(encoding="utf-8-sig")

        self.assertEqual(smoke_path.read_bytes()[:3], b"\xef\xbb\xbf")
        self.assertIn("[switch]$PublicIrSecClicks", smoke_source)
        self.assertIn("--only-public-ir-sec", smoke_source)
        self.assertIn('PYTHONIOENCODING = "utf-8"', smoke_source)
        self.assertIn('PYTHONUTF8 = "1"', smoke_source)

    def test_research_source_automation_wrapper_checks_policy_and_ir_sources(self):
        script_source = (PROJECT_ROOT / "tools" / "check_research_source_automation.ps1").read_text(
            encoding="utf-8-sig"
        )

        self.assertIn("policy_sources_watch", script_source)
        self.assertIn("company_ir_sources_watch", script_source)
        self.assertIn("Official policy/law/regulation sources", script_source)
        self.assertIn("Company IR public sources", script_source)

    def test_status_research_console_summarizes_automation_digest(self):
        script_source = (PROJECT_ROOT / "tools" / "status_research_console.ps1").read_text(
            encoding="utf-8-sig"
        )

        self.assertIn("/api/v1/research-automation/status", script_source)
        self.assertIn("dashboard_digest", script_source)
        self.assertIn("news_priority_preview", script_source)
        self.assertIn("news_priority_count", script_source)
        self.assertIn("우선 뉴스: 표시", script_source)
        self.assertIn("자동화 조치", script_source)
        self.assertIn("latest_records", script_source)
        self.assertIn("오늘 추천 $($marketLabel) 1~3위", script_source)
        self.assertIn("market_close_journal.json", script_source)
        self.assertIn("telegram_market_close_journal_state.json", script_source)
        self.assertIn('foreach ($market in @("KR", "US"))', script_source)
        self.assertIn("시장일지 $($market)", script_source)
        self.assertIn("MaxMarketJournalSessionAgeDays", script_source)
        self.assertIn("시장일지 $market 최신 세션 확인 필요", script_source)
        self.assertIn("미국 시장일지 자동 시도", script_source)
        self.assertIn("storage_duplicate_review.json", script_source)
        self.assertIn("저장 중복 리뷰", script_source)
        self.assertIn("저장 중복 대표 후보", script_source)
        self.assertIn("daily_recommendation_candidate_policy_preview.json", script_source)
        self.assertIn("stored_preview_mismatches", script_source)
        self.assertIn("stored_score", script_source)
        self.assertIn("preview_score", script_source)
        self.assertIn("generated_at", script_source)
        self.assertIn("Format-LocalDateTime", script_source)
        self.assertIn("Get-DateTimeAgeHours", script_source)
        self.assertIn("MaxRecommendationPreviewAgeHours", script_source)
        self.assertIn("추천 재계산 프리뷰 최신성 확인 필요", script_source)
        self.assertIn("ToLocalTime()", script_source)
        self.assertIn("추천 재계산 프리뷰 생성", script_source)
        self.assertIn("추천 저장/재계산 차이", script_source)
        self.assertIn("news_duplicate_priority_group_count", script_source)
        self.assertIn("news_duplicate_priority_groups", script_source)
        self.assertIn("Limit-StatusText", script_source)
        self.assertIn("MaxLength 120", script_source)
        self.assertIn("우선 뉴스 중복 후보", script_source)
        self.assertIn("$group.ids", script_source)
        self.assertIn("ids ", script_source)
        self.assertIn("nps_domestic_equity_rebalance_plan", script_source)
        self.assertIn("current_domestic_equity_weight", script_source)
        self.assertIn("target_domestic_equity_weight", script_source)
        self.assertIn("reduction_needed_value", script_source)
        self.assertIn("candidates.reduce", script_source)
        self.assertIn("reduceCandidateTotal", script_source)
        self.assertIn("합계", script_source)
        self.assertIn("국민연금 축소 후보", script_source)
        self.assertIn("/api/v1/public-ir-sec/status", script_source)
        self.assertIn("Firecrawl IR:", script_source)
        self.assertIn("firecrawl_ir", script_source)
        self.assertIn("Firecrawl IR MCP 버전 확인 필요", script_source)
        self.assertIn("needs_body_copy_entries", script_source)
        self.assertIn("needs_body_duplicate_title_group_count", script_source)
        self.assertIn("needs_body_duplicate_title_groups", script_source)
        self.assertIn("$group.file_names", script_source)
        self.assertIn("files ", script_source)
        self.assertIn("ForEach-Object", script_source)
        self.assertIn("본문 보강 플래그", script_source)
        self.assertIn("공개 IR/SEC 동일 제목", script_source)
        self.assertIn("공개 IR/SEC 보강 대상", script_source)
        console_source = (PROJECT_ROOT / "mobile_app" / "research_console" / "console.js").read_text(encoding="utf-8")
        style_source = (PROJECT_ROOT / "mobile_app" / "research_console" / "styles.css").read_text(encoding="utf-8")
        self.assertIn("automation-news-duplicate", console_source)
        self.assertIn("중복 ID", console_source)
        self.assertIn("news_duplicate_priority_groups", console_source)
        self.assertIn(".automation-news-duplicate", style_source)

    def test_enter_research_os_script_prints_recovery_commands(self):
        script_source = (PROJECT_ROOT / "scripts" / "enter-investment-research-os.ps1").read_text(
            encoding="utf-8-sig"
        )
        readme_source = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("[switch]$RestartBackend", script_source)
        self.assertIn("restart-research-backend.ps1 -Port 8001", script_source)
        self.assertIn("-RestartBackend -OpenConsole", script_source)
        self.assertIn("status_research_console.ps1 -Strict", script_source)
        self.assertIn("http://127.0.0.1:8001/console/index.html", script_source)
        self.assertIn("-RestartBackend -OpenConsole", readme_source)

    def test_backend_runtime_env_recommends_research_backend_restart(self):
        script_source = (PROJECT_ROOT / "tools" / "check_backend_runtime_env.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("restart-research-backend.ps1 -Port 8001", script_source)
        self.assertIn("status_research_console.ps1 -Strict", script_source)

    def test_verify_wrapper_exposes_public_ir_sec_click_mode(self):
        verify_source = (PROJECT_ROOT / "tools" / "verify_research_console.ps1").read_text(encoding="utf-8")

        self.assertIn("[switch]$ClickSmokeOnlyPublicIrSec", verify_source)
        self.assertIn("if (-not $ClickSmokeOnlyPublicIrSec)", verify_source)
        self.assertIn("$clickSmokeArgs += \"--only-public-ir-sec\"", verify_source)
        self.assertIn("$clickSmokeArgs += @(\"--progress-heartbeat-seconds\", \"$ClickSmokeProgressHeartbeatSeconds\")", verify_source)

    def test_verify_wrapper_exposes_investment_insight_hub_check(self):
        verify_source = (PROJECT_ROOT / "tools" / "verify_research_console.ps1").read_text(encoding="utf-8")

        self.assertIn("[switch]$CheckInvestmentInsightHub", verify_source)
        self.assertIn("tools\\check_investment_insight_hub.py", verify_source)
        self.assertIn("backend\\research_os\\investment_insight_hub.py", verify_source)
        self.assertIn("통합 투자 인사이트 허브 오프라인 확인", verify_source)

    def test_daily_research_operations_is_windows_powershell_utf8_bom(self):
        script_bytes = (PROJECT_ROOT / "tools" / "run_daily_research_operations.ps1").read_bytes()

        self.assertTrue(script_bytes.startswith(b"\xef\xbb\xbf"))

    def test_daily_research_operations_refreshes_recommendation_preview(self):
        script_source = (PROJECT_ROOT / "tools" / "run_daily_research_operations.ps1").read_text(
            encoding="utf-8-sig"
        )

        self.assertIn("[switch]$SkipRecommendationPreview", script_source)
        self.assertIn("추천 저장/재계산 프리뷰 저장", script_source)
        self.assertIn("tools\\check_daily_recommendation_candidate_policy.py", script_source)
        self.assertIn("--require-hold-warning", script_source)
        self.assertIn("--expected-held-ticker", script_source)
        self.assertIn("112610", script_source)
        self.assertIn("--output-json", script_source)
        self.assertIn("tmp\\daily_recommendation_candidate_policy_preview.json", script_source)

    def test_cleanup_only_reports_single_skip_when_backend_unreachable(self):
        import urllib.error

        tool = load_write_actions_smoke_tool()
        with patch.object(tool, "assert_project_root", return_value=None), patch.object(
            tool.urllib.request, "urlopen", side_effect=urllib.error.URLError("connection refused")
        ):
            result = tool.cleanup_qa_artifacts()

        self.assertFalse(result["backendReachable"])
        self.assertEqual(result["skippedReason"], "backend_unreachable")
        self.assertIn("connection refused", result["backendMessage"])
        self.assertNotIn("portfolioCleanupError", result)
        self.assertNotIn("interestCleanupError", result)
        self.assertNotIn("newsCleanupError", result)
        self.assertNotIn("researchArchiveError", result)


class PublicIrSecStoreCheckToolTests(unittest.TestCase):
    def test_public_ir_sec_store_check_uses_clear_body_followup_label(self):
        tool_source = (PROJECT_ROOT / "tools" / "check_public_ir_sec_store.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("URL-only 원문 제한", tool_source)
        self.assertIn("본문 보강 플래그", tool_source)
        self.assertNotIn("URL-only/본문 보강", tool_source)

    def test_load_manifest_retries_during_transient_empty_write(self):
        tool = load_public_ir_sec_store_check_tool()

        with TemporaryDirectory() as tmp:
            vault_dir = Path(tmp)
            manifest_path = vault_dir / "manifest.json"
            manifest_path.write_text("[]", encoding="utf-8")
            reads = iter(["", '[{"scope": "public_ir_sec", "title": "Oatly 6-K"}]'])

            with patch.object(Path, "read_text", side_effect=lambda *_, **__: next(reads)), patch.object(
                tool.time, "sleep", return_value=None
            ) as sleep:
                entries = tool.load_manifest(vault_dir, retries=2, retry_delay_seconds=0)

        self.assertEqual(entries[0]["title"], "Oatly 6-K")
        sleep.assert_called_once()


class OfflineReadinessToolTests(unittest.TestCase):
    def test_offline_readiness_checks_firecrawl_registry_sample(self):
        tool = load_offline_readiness_tool()

        checks = {label: args for label, args in tool.CHECKS}

        self.assertIn("Firecrawl IR registry 샘플 payload", checks)
        self.assertEqual(
            checks["Firecrawl IR registry 샘플 payload"],
            [
                "tools/check_firecrawl_ir_collector.py",
                "--input-json",
                "docs/examples/firecrawl_ir_registry.sample.json",
            ],
        )

    def test_offline_readiness_checks_daily_recommendation_policy_signals(self):
        tool = load_offline_readiness_tool()

        checks = {label: args for label, args in tool.CHECKS}

        self.assertIn("매일 추천 정책 신호 품질", checks)
        self.assertEqual(
            checks["매일 추천 정책 신호 품질"],
            ["tools/check_daily_recommendation_policy_signals.py", "--strict"],
        )

    def test_offline_readiness_checks_investment_insight_hub(self):
        tool = load_offline_readiness_tool()

        checks = {label: args for label, args in tool.CHECKS}

        self.assertIn("통합 투자 인사이트 허브", checks)
        self.assertEqual(checks["통합 투자 인사이트 허브"], ["tools/check_investment_insight_hub.py", "--strict"])

    def test_offline_readiness_prints_nps_rebalance_plan(self):
        tool = load_offline_readiness_tool()

        checks = {label: args for label, args in tool.CHECKS}

        self.assertIn("국민연금 국내주식 14%", checks)
        self.assertEqual(
            checks["국민연금 국내주식 14%"],
            ["tools/check_nps_domestic_equity_allocation.py", "--rebalance-plan"],
        )

    def test_offline_readiness_checks_news_inbox_priority_queue(self):
        tool = load_offline_readiness_tool()

        checks = {label: args for label, args in tool.CHECKS}

        self.assertIn("뉴스 인박스 우선 분류", checks)
        self.assertEqual(checks["뉴스 인박스 우선 분류"], ["tools/check_news_inbox_priority_queue.py", "--strict"])

    def test_offline_readiness_checks_storage_duplicate_review(self):
        tool = load_offline_readiness_tool()

        checks = {label: args for label, args in tool.CHECKS}

        self.assertIn("저장 자료 중복 리뷰", checks)
        self.assertEqual(checks["저장 자료 중복 리뷰"], ["tools/check_storage_duplicate_review.py", "--strict"])

    def test_offline_readiness_saves_daily_candidate_policy_preview(self):
        tool = load_offline_readiness_tool()

        checks = {label: args for label, args in tool.CHECKS}

        self.assertIn("매일 추천 후보 정책", checks)
        self.assertEqual(
            checks["매일 추천 후보 정책"],
            [
                "tools/check_daily_recommendation_candidate_policy.py",
                "--require-hold-warning",
                "--expected-held-ticker",
                "112610",
                "--output-json",
                "tmp/daily_recommendation_candidate_policy_preview.json",
            ],
        )

    def test_offline_readiness_checks_macro_source_signal_linkage(self):
        tool = load_offline_readiness_tool()

        checks = {label: args for label, args in tool.CHECKS}

        self.assertIn("매크로/지역 소스 연결 신호", checks)
        self.assertEqual(checks["매크로/지역 소스 연결 신호"], ["tools/check_macro_source_signal_linkage.py", "--strict"])


class OperationalReadinessToolTests(unittest.TestCase):
    def test_policy_signal_quality_is_part_of_operational_readiness(self):
        tool = load_operational_readiness_tool()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "backend").mkdir()
            (root / "backend" / "research_os_main.py").write_text("", encoding="utf-8")
            system_dir = root / "research_vault" / "_system"
            system_dir.mkdir(parents=True)
            store = {
                "records": [
                    {
                        "recommendation_date": "2026-06-24",
                        "market": "KR",
                        "rank": 1,
                        "ticker": "005930",
                        "policy_signal_summary": {
                            "match_level": "theme",
                            "match_level_label": "테마",
                            "score_applied": True,
                            "direct_count": 0,
                            "theme_count": 3,
                        },
                        "score_components": [{"label": "정책 테마 모멘텀", "points": 4}],
                    }
                ]
            }
            (system_dir / "daily_recommendations.json").write_text(json.dumps(store, ensure_ascii=False), encoding="utf-8")

            result = tool.recommendation_policy_signal(system_dir)

        self.assertEqual(result["id"], "daily_recommendation_policy_signals")
        self.assertEqual(result["status"], "ok")
        self.assertIn("검토 1개", result["message"])

    def test_investment_insight_hub_is_part_of_operational_readiness(self):
        tool = load_operational_readiness_tool()
        fake_payload = {
            "coverage": {
                "market_data_items": 3,
                "market_journal_items": 1,
                "official_filing_items": 2,
                "news_items": 4,
                "policy_law_items": 1,
            },
            "readiness": {
                "coverage_score": 100.0,
                "insight_count": 5,
                "source_families": ["market_data_sentiment", "official_filings", "policy_law_news"],
            },
        }
        fake_module = SimpleNamespace(
            build_dashboard=lambda *_args, **_kwargs: fake_payload,
            strict_errors=lambda *_args, **_kwargs: [],
        )

        with TemporaryDirectory() as tmp, patch.dict(sys.modules, {"check_investment_insight_hub": fake_module}):
            result = tool.investment_insight_hub_signal(Path(tmp))

        self.assertEqual(result["id"], "investment_insight_hub")
        self.assertEqual(result["status"], "ok")
        self.assertIn("시장일지·심리 1", result["message"])
        self.assertIn("정책·법령 1", result["message"])

    def test_nps_allocation_signal_is_advisory_until_enforced(self):
        tool = load_operational_readiness_tool()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "backend").mkdir()
            (root / "backend" / "research_os_main.py").write_text("", encoding="utf-8")
            system_dir = root / "research_vault" / "_system"
            system_dir.mkdir(parents=True)
            payload = {
                "portfolios": {
                    "가족-합산": {
                        "portfolio_name": "가족 합산",
                        "portfolio_value": 1000,
                        "holdings": [
                            {"ticker": "005930", "name": "삼성전자", "market_value": 600, "currency": "KRW"},
                            {"ticker": "PL", "name": "Planet Labs", "market_value": 400, "currency": "USD"},
                        ],
                    }
                }
            }
            (system_dir / "user_portfolios.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            advisory = tool.nps_allocation_signal(root, system_dir, enforce=False)
            enforced = tool.nps_allocation_signal(root, system_dir, enforce=True)

        self.assertEqual(advisory["status"], "ok")
        self.assertIn("비중 이탈 감시 중", advisory["message"])
        self.assertIn("상태 above_target", advisory["message"])
        self.assertEqual(enforced["status"], "warning")
        self.assertIn("비중 이탈", enforced["message"])
        self.assertLess(enforced["score"], 95.0)


class InvestmentInsightHubCheckToolTests(unittest.TestCase):
    def test_strict_errors_require_market_filings_news_policy_and_sentiment(self):
        tool = load_investment_insight_hub_check_tool()
        payload = {
            "coverage": {
                "market_data_items": 1,
                "market_journal_items": 0,
                "official_filing_items": 0,
                "news_items": 1,
                "policy_law_items": 0,
            },
            "readiness": {
                "insight_count": 1,
                "coverage_score": 40.0,
                "source_families": ["news_flow"],
            },
            "aggregate_sentiment_label": "",
        }

        errors = tool.strict_errors(payload, min_insights=4, min_coverage_score=95.0)

        self.assertIn("시장일지/투자심리 커버리지가 없습니다.", errors)
        self.assertIn("공시 커버리지가 없습니다.", errors)
        self.assertIn("정책·법령·규제 커버리지가 없습니다.", errors)
        self.assertIn("market_data_sentiment 인사이트 패밀리가 없습니다.", errors)
        self.assertIn("종합 투자심리 라벨이 없습니다.", errors)


class DailyRecommendationRenderLayoutCheckToolTests(unittest.TestCase):
    def test_strict_errors_require_two_markets_six_cards_and_no_clipping(self):
        tool = load_daily_recommendation_render_layout_tool()
        result = {
            "marketSectionCount": 1,
            "recommendationCardCount": 5,
            "marketLabels": ["한국 추천 1~3위"],
            "pageHasHorizontalOverflow": True,
            "scrolledToDailyRecommendationCards": False,
            "clippedTextElements": [{"text": "long clipped text"}],
        }

        errors = tool.strict_errors(result)

        self.assertIn("한국/미국 시장 섹션이 모두 렌더링되지 않았습니다.", errors)
        self.assertIn("한국/미국 추천 카드 6개가 모두 렌더링되지 않았습니다.", errors)
        self.assertIn("시장 섹션 라벨에 한국/미국이 모두 보이지 않습니다.", errors)
        self.assertIn("페이지 전체에 가로 스크롤 오버플로가 있습니다.", errors)
        self.assertIn("추천 결과 스크린샷 대상이 카드 영역으로 스크롤되지 않았습니다.", errors)
        self.assertIn("추천 결과 텍스트 클리핑 1개", errors)


class DailyRecommendationPolicySignalCheckToolTests(unittest.TestCase):
    def test_strict_errors_can_fail_on_review(self):
        tool = load_policy_signal_check_tool()
        dashboard = {
            "record_count": 1,
            "score_applied_count": 1,
            "review_count": 1,
            "level_counts": {"direct": 0, "theme": 1, "market": 0, "none": 0},
            "rows": [{"policy_signal_summary": {"match_level": "theme"}}],
        }

        advisory = tool.strict_errors(dashboard, fail_on_review=False, require_metadata=True)
        enforced = tool.strict_errors(dashboard, fail_on_review=True, require_metadata=True)

        self.assertEqual(advisory, [])
        self.assertEqual(enforced, ["정책 신호 검토 필요 1개"])

    def test_strict_errors_allow_theme_reference_without_score(self):
        tool = load_policy_signal_check_tool()
        dashboard = {
            "record_count": 1,
            "score_applied_count": 0,
            "review_count": 0,
            "level_counts": {"direct": 0, "theme": 1, "market": 0, "none": 0},
            "rows": [{"policy_signal_summary": {"match_level": "theme", "score_applied": False}}],
        }

        self.assertEqual(tool.strict_errors(dashboard, fail_on_review=True, require_metadata=True), [])


class DailyRecommendationCitationCheckToolTests(unittest.TestCase):
    def test_policy_source_url_citation_is_usable(self):
        tool = load_daily_recommendation_citations_tool()

        self.assertTrue(
            tool.citation_is_usable(
                {
                    "source_relative_path": "https://www.fsc.go.kr/policy/example",
                    "source_type": "policy_law",
                    "report_type": "official_policy_source",
                    "citation_label": "정책 신호 근거",
                },
                PROJECT_ROOT,
            )
        )
        self.assertFalse(
            tool.citation_is_usable(
                {"source_relative_path": "https://example.com/unclassified"},
                PROJECT_ROOT,
            )
        )


class WebCaptureRenderingTests(unittest.TestCase):
    def test_web_article_cleaning_strips_navigation_noise(self):
        from research_os.web_article_cleaning import clean_web_article_text
        from research_os.web_article_cleaning import clean_web_article_title

        text = clean_web_article_text(
            "로그인\n"
            "입력 2026.06.18 09:00\n"
            "반도체 장비 수요가 증가했다. 매출은 12% 늘었다.\n"
            "관련기사\n"
            "추천기사"
        )

        self.assertEqual(clean_web_article_title("테스트 기사 제목 - 디일렉"), "테스트 기사 제목")
        self.assertNotIn("로그인", text)
        self.assertIn("반도체 장비 수요", text)
        self.assertNotIn("관련기사", text)

    def test_sec_capture_headers_use_public_project_user_agent(self):
        from research_os.web_capture import capture_url_headers

        headers = capture_url_headers("https://www.sec.gov/Archives/example.htm")

        self.assertIn("investment-research-os", headers["User-Agent"])
        self.assertIn("lib2000@gmail.com", headers["User-Agent"])
        self.assertEqual(headers["Referer"], "https://www.sec.gov/")
        self.assertIn("text/html", headers["Accept"])

    def test_sec_fetch_falls_back_to_urllib_after_httpx_failure(self):
        from research_os import web_fetch

        class FailingClient:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def get(self, url):
                raise RuntimeError("403 Forbidden")

        class FakeHeaders(dict):
            def items(self):
                return [("content-type", "text/html")]

        class FakeUrlopenResponse:
            status = 200
            headers = FakeHeaders()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def getcode(self):
                return 200

            def geturl(self):
                return "https://www.sec.gov/Archives/example.htm"

            def read(self, limit):
                return b"<html><title>SEC fallback</title><body>ChargePoint revenue 101.8 million</body></html>"

        with patch.object(web_fetch.httpx, "Client", FailingClient), patch.object(
            web_fetch.urllib.request,
            "urlopen",
            return_value=FakeUrlopenResponse(),
        ):
            response, attempts = web_fetch.fetch_url_with_retry("https://www.sec.gov/Archives/example.htm")

        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response.status_code, 200)
        self.assertIn("sec_urllib: success 200", attempts)
        self.assertIn(b"ChargePoint revenue", response.content)

    def test_official_url_fallback_summary_is_separate_payload_helper(self):
        from research_os.web_capture import official_url_fallback_summary as web_capture_fallback
        from research_os.web_capture_fallbacks import official_url_fallback_summary

        payload = official_url_fallback_summary(
            "https://www.isomorphiclabs.com/news/isomorphic-labs-announces-series-b-investment-round",
            ["direct: 403 Forbidden"],
        )

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["fetch_attempts"][0], "direct: 403 Forbidden")
        self.assertEqual(payload["status"], "official_fallback_summary")
        self.assertEqual(payload["translation_status"], "official_korean_summary")
        self.assertIn("21억 달러", payload["text"])
        self.assertIn("재시도 로그", payload["note"])
        self.assertIsNone(official_url_fallback_summary("https://example.com/article", []))
        self.assertEqual(web_capture_fallback, official_url_fallback_summary)

    def test_webpage_text_extracts_plain_ir_paragraphs(self):
        from research_os.web_capture import extract_webpage_text

        html = """
        <html><head><title>Joby Reports First Quarter 2026 Financial Results :: Joby Aero, Inc. (JOBY)</title></head>
        <body>
          <header><nav>Press Subscribe Contact</nav></header>
          <p>SANTA CRUZ, Calif.--(BUSINESS WIRE)-- Joby Aviation, Inc. (NYSE:JOBY), a company developing electric air taxis for commercial passenger service, today issued its First Quarter 2026 Shareholder Letter detailing the company’s operational and financial results for the quarter ended March 31, 2026.</p>
          <ul class="bwlistdisc"><li><b>Initial operations expected to begin in 2026:</b> Joby was named a partner in multiple winning applications under the White House-backed eVTOL Integration Pilot Program.</li></ul>
          <p><b>About Joby</b></p>
          <p>Joby Aviation, Inc. is developing an all-electric, vertical take-off and landing air taxi.</p>
        </body></html>
        """

        title, text = extract_webpage_text(html)

        self.assertEqual(title, "Joby Reports First Quarter 2026 Financial Results")
        self.assertIn("Joby Aviation, Inc. (NYSE:JOBY)", text)
        self.assertIn("Initial operations expected to begin in 2026", text)
        self.assertGreater(len(text), 300)

    def test_webpage_text_extracts_ir_sec_listing_rows(self):
        from research_os.web_capture import extract_webpage_text

        html = """
        <html><head><title>Quarterly Reports :: Joby Aero, Inc. (JOBY)</title></head>
        <body>
          <table class="content-table spr-ir-sec-filings">
            <tr><th>Date</th><th>Form</th><th>Description</th><th>PDF</th><th>XBRL</th><th>Pages</th></tr>
            <tr><td>05/06/26</td><td><a href="/sec-filings/all-sec-filings/content/0001819848-26-000324/joby-20260331.htm">10-Q</a></td><td><a>Quarterly report [Sections 13 or 15(d)]</a></td><td><a>PDF</a></td><td><a>XBRL</a></td><td>143</td></tr>
            <tr><td>02/27/26</td><td><a>10-K</a></td><td><a>Annual report [Section 13 and 15(d)]</a></td><td><a>PDF</a></td><td></td><td>121</td></tr>
          </table>
        </body></html>
        """

        title, text = extract_webpage_text(html)

        self.assertEqual(title, "Quarterly Reports")
        self.assertIn("05/06/26 | 10-Q | Quarterly report", text)
        self.assertIn("02/27/26 | 10-K | Annual report", text)
        self.assertIn("Date | Form | Description | PDF | XBRL | Pages", text)
        self.assertGreater(len(text), 120)

    def test_webpage_text_extracts_ir_result_lines(self):
        from research_os.web_capture import extract_webpage_text

        html = """
        <html><head><title>Financial Results :: Joby Aero, Inc. (JOBY)</title></head>
        <body>
          <h2>2026</h2><h3>Q1 2026</h3>
          <div class="result-line"><a href="/news-events/press-releases/detail/182/joby-reports-first-quarter-2026-financial-results">Financial Results Release</a><div><a>PDF</a><a>HTML</a></div></div>
          <div class="result-line"><a>Financial Results Webcast</a><div><a>Audio</a></div></div>
          <div class="result-line"><a>Shareholder Letter</a><div><a>PDF</a></div></div>
          <div class="result-line"><a>10-Q Filing</a><div><a>PDF</a><a>HTML</a><a>XBRL</a></div></div>
        </body></html>
        """

        title, text = extract_webpage_text(html)

        self.assertEqual(title, "Financial Results")
        self.assertIn("Financial Results Release", text)
        self.assertIn("10-Q Filing", text)
        self.assertIn("Q1 2026 | Financial Results Release", text)
        self.assertGreater(len(text), 120)

    def test_source_url_context_includes_translation_metadata(self):
        from research_os.web_capture import render_source_url_context

        rendered = render_source_url_context(
            {
                "source_url": "https://example.com/original",
                "final_url": "https://example.com/final",
                "status": "success",
                "note": "본문 추출 완료",
                "title": "Foreign article",
                "language": "en",
                "translation_status": "translated",
                "translation_note": "영어 본문을 한국어 요약으로 변환했습니다.",
                "content_type": "text/html",
                "text": "Revenue growth accelerated.",
            }
        )

        self.assertIn("[웹사이트 입력]", rendered)
        self.assertIn("원본 URL: https://example.com/original", rendered)
        self.assertIn("원문 언어: 영어", rendered)
        self.assertIn("한국어 변환: translated", rendered)
        self.assertIn("[웹사이트 본문 추출]", rendered)

    def test_url_only_context_preserves_next_action(self):
        from research_os.web_capture import render_url_only_capture_context

        rendered = render_url_only_capture_context(
            "https://paywalled.example/article",
            {
                "final_url": "https://paywalled.example/article",
                "status": "empty_text",
                "note": "본문 텍스트를 충분히 추출하지 못했습니다.",
                "title": "구독자 전용",
                "content_type": "text/html",
            },
        )

        self.assertIn("[웹사이트 URL 보관]", rendered)
        self.assertIn("처리 상태: empty_text", rendered)
        self.assertIn("링크, 제목, 처리 로그는 저장 데이터와 RAG 메타데이터에 남겨", rendered)
        self.assertIn("원문 본문을 직접 복사해 다시 저장", rendered)

    def test_source_url_preview_builder_is_separate_from_api_route(self):
        from research_os import source_url_preview

        with patch.object(
            source_url_preview,
            "fetch_capture_source_url",
            return_value={
                "source_url": "https://example.com/a",
                "final_url": "https://example.com/a",
                "status": "success",
                "title": "Preview",
                "language": "en",
                "translation_status": "translated",
                "translation_note": "한국어 요약으로 변환했습니다.",
                "content_type": "text/html",
                "text": "Revenue growth accelerated. " * 20,
                "original_text": "Revenue growth accelerated.",
                "note": "본문 추출 완료",
            },
        ):
            payload = source_url_preview.build_source_url_preview_response("https://example.com/a")

        self.assertEqual(payload["module"], "source_url_preview")
        self.assertEqual(payload["source_url"], "https://example.com/a")
        self.assertIn("Revenue growth", payload["preview"])
        self.assertIn("[웹사이트 입력]", payload["context"])

    def test_web_capture_translation_module_builds_local_korean_digest(self):
        from research_os import web_capture_translation

        digest = web_capture_translation.foreign_text_korean_digest(
            "Acme Bio announces it raised $12 million in Series A funding. "
            "The company aims to accelerate drug discovery with AI.",
            title="Acme Bio funding",
        )

        self.assertEqual(digest["language"], "en")
        self.assertEqual(digest["status"], "local_digest")
        self.assertIn("한국어 분석용 변환", digest["text"])
        self.assertIn("12백만 달러", digest["text"])
        self.assertIn("신약개발", digest["text"])


class FirecrawlIrCollectorTests(unittest.TestCase):
    @staticmethod
    def write_firecrawl_submit_items(tmpdir: str) -> Path:
        input_path = Path(tmpdir) / "firecrawl-ir-items.json"
        input_path.write_text(
            json.dumps(
                {
                    "items": [
                        {"company": "Apple", "ticker": "AAPL", "raw_url": "https://investor.apple.com/"},
                        {"company": "Joby Aviation", "ticker": "JOBY", "raw_url": "https://ir.jobyaviation.com/"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        return input_path

    @staticmethod
    def firecrawl_submit_test_env() -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "FIRECRAWL_IR_ENABLED": "true",
                "FIRECRAWL_IR_DRY_RUN": "false",
                "FIRECRAWL_IR_MCP_VERSION": "3.17.0",
                "MARKET_SIGNAL_GRAPH_ENABLED": "true",
                "MARKET_SIGNAL_GRAPH_RPC_URL": "http://127.0.0.1:9/rest/v1/rpc/upsert_external_signal",
                "MARKET_SIGNAL_GRAPH_SUPABASE_URL": "",
                "MARKET_SIGNAL_GRAPH_SERVICE_ROLE_KEY": "test-service-role-key",
                "MARKET_SIGNAL_GRAPH_TIMEOUT_SECONDS": "0.2",
                "SUPABASE_URL": "",
                "SUPABASE_SERVICE_ROLE_KEY": "",
            }
        )
        return env

    def test_firecrawl_ir_payload_matches_market_signal_graph_contract(self):
        from research_os.firecrawl_ir_collector import build_firecrawl_ir_signal_payload, sha256_hex

        payload = build_firecrawl_ir_signal_payload(
            {
                "company": "Apple",
                "ticker": "AAPL",
                "raw_url": "https://investor.apple.com/",
                "resolved_url": "https://investor.apple.com/",
                "page_title": "Apple Investor Relations",
                "markdown": "Apple Investor Relations provides earnings releases and shareholder information.",
            }
        )

        self.assertEqual(payload["source_name"], "Apple_ir")
        self.assertEqual(payload["source_platform"], "firecrawl_ir")
        self.assertEqual(payload["source_kind"], "ir")
        self.assertEqual(payload["channel"], "web")
        self.assertEqual(payload["external_id"], sha256_hex("https://investor.apple.com/"))
        self.assertEqual(
            payload["canonical_hash"],
            sha256_hex("firecrawl_irhttps://investor.apple.com/Apple Investor Relations"),
        )
        self.assertTrue(payload["needs_enrichment"])
        self.assertEqual(payload["analysis_status"], "pending")
        self.assertEqual(payload["metadata"]["collector"], "firecrawl")
        self.assertEqual(payload["metadata"]["target_type"], "company_ir")
        self.assertEqual(payload["metadata"]["ticker"], "AAPL")

    def test_firecrawl_ir_payload_accepts_nested_firecrawl_scrape_result(self):
        from research_os.firecrawl_ir_collector import build_firecrawl_ir_signal_payload, sha256_hex

        payload = build_firecrawl_ir_signal_payload(
            {
                "company": "Apple",
                "ticker": "AAPL",
                "firecrawl": {
                    "markdown": "# Apple Investor Relations\nQuarterly results and SEC filings.",
                    "metadata": {
                        "title": "Apple Investor Relations",
                        "sourceURL": "https://investor.apple.com/",
                        "language": "en",
                    },
                },
            }
        )

        self.assertEqual(payload["url"], "https://investor.apple.com/")
        self.assertEqual(payload["title"], "Apple Investor Relations")
        self.assertEqual(payload["external_id"], sha256_hex("https://investor.apple.com/"))
        self.assertIn("Quarterly results", payload["text"])
        self.assertEqual(payload["language"], "en")
        self.assertEqual(payload["metadata"]["raw_url"], "https://investor.apple.com/")
        self.assertEqual(payload["metadata"]["ticker"], "AAPL")

    def test_firecrawl_ir_payload_prefers_explicit_registry_fields(self):
        from research_os.firecrawl_ir_collector import build_firecrawl_ir_signal_payload

        payload = build_firecrawl_ir_signal_payload(
            {
                "company": "Apple",
                "ticker": "AAPL",
                "raw_url": "https://investor.apple.com/",
                "resolved_url": "https://investor.apple.com/newsroom/",
                "page_title": "Apple Investor Newsroom",
                "markdown": "Explicit registry summary.",
                "data": {
                    "markdown": "Nested Firecrawl summary.",
                    "metadata": {
                        "title": "Nested Title",
                        "sourceURL": "https://nested.example.com/",
                    },
                },
            }
        )

        self.assertEqual(payload["url"], "https://investor.apple.com/newsroom/")
        self.assertEqual(payload["title"], "Apple Investor Newsroom")
        self.assertEqual(payload["text"], "Explicit registry summary.")
        self.assertEqual(payload["metadata"]["raw_url"], "https://investor.apple.com/")

    def test_firecrawl_ir_readiness_reports_safe_disabled_defaults(self):
        from research_os.firecrawl_ir_collector import build_firecrawl_ir_readiness_status

        settings = SimpleNamespace(
            firecrawl_ir_enabled=False,
            firecrawl_ir_dry_run=True,
            firecrawl_api_key="",
            firecrawl_base_url="https://api.firecrawl.dev/v2",
            firecrawl_timeout_seconds=30,
            firecrawl_ir_mcp_version="3.17.0",
            firecrawl_ir_sources_json="",
            market_signal_graph_enabled=False,
            market_signal_graph_rpc_url="",
            market_signal_graph_service_role_key="",
        )

        status = build_firecrawl_ir_readiness_status(settings)

        self.assertEqual(status["status"], "disabled")
        self.assertFalse(status["hosted_api"]["api_key_configured"])
        self.assertEqual(status["source_registry"]["input_source"], "sample")
        self.assertEqual(status["dry_run_sample"]["source_platform"], "firecrawl_ir")
        self.assertEqual(status["dry_run_sample"]["ticker"], "AAPL")
        self.assertNotIn("firecrawl_api_key", json.dumps(status).lower())

    def test_firecrawl_ir_readiness_uses_env_registry_without_exposing_key(self):
        from research_os.firecrawl_ir_collector import build_firecrawl_ir_readiness_status

        settings = SimpleNamespace(
            firecrawl_ir_enabled=True,
            firecrawl_ir_dry_run=True,
            firecrawl_api_key="fc-secret-value",
            firecrawl_base_url="https://api.firecrawl.dev/v2",
            firecrawl_timeout_seconds=15,
            firecrawl_ir_mcp_version="3.17.0",
            firecrawl_ir_sources_json=json.dumps(
                [
                    {
                        "company": "Planet Labs",
                        "ticker": "PL",
                        "raw_url": "https://investors.planet.com/",
                        "page_title": "Planet Labs Investor Relations",
                        "markdown": "Planet Labs IR page.",
                    }
                ]
            ),
            market_signal_graph_enabled=False,
            market_signal_graph_rpc_url="",
            market_signal_graph_service_role_key="",
        )

        status = build_firecrawl_ir_readiness_status(settings)

        self.assertEqual(status["status"], "ready")
        self.assertTrue(status["hosted_api"]["api_key_configured"])
        self.assertEqual(status["source_registry"]["item_count"], 1)
        self.assertEqual(status["source_registry"]["input_source"], "env_registry")
        self.assertEqual(status["dry_run_sample"]["ticker"], "PL")
        self.assertNotIn("fc-secret-value", json.dumps(status))

    def test_firecrawl_ir_hosted_scrape_dry_run_normalizes_response_without_exposing_key(self):
        from research_os import firecrawl_ir_collector

        class FakeResponse:
            status_code = 200
            text = '{"success":true}'

            def json(self):
                return {
                    "success": True,
                    "data": {
                        "markdown": "Planet Labs investor relations page with filings and shareholder materials.",
                        "metadata": {
                            "title": "Planet Labs Investor Relations",
                            "sourceURL": "https://investors.planet.com/",
                            "language": "en",
                        },
                    },
                }

        class FakeClient:
            def __init__(self, *args, **kwargs):
                self.args = args
                self.kwargs = kwargs

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def post(self, url, headers, json):
                self.post_url = url
                self.headers = headers
                self.request_json = json
                return FakeResponse()

        settings = SimpleNamespace(
            firecrawl_api_key="fc-secret-value",
            firecrawl_base_url="https://api.firecrawl.dev/v2",
            firecrawl_timeout_seconds=12,
        )

        with patch.object(firecrawl_ir_collector.httpx, "Client", FakeClient):
            result = firecrawl_ir_collector.scrape_firecrawl_ir_item(
                {"company": "Planet Labs", "ticker": "PL", "raw_url": "https://investors.planet.com/"},
                settings,
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["http_status"], 200)
        self.assertEqual(result["ticker"], "PL")
        self.assertEqual(result["company"], "Planet Labs")
        self.assertEqual(result["payload"]["source_platform"], "firecrawl_ir")
        self.assertEqual(result["payload"]["title"], "Planet Labs Investor Relations")
        self.assertGreater(result["content_chars"], 20)
        self.assertNotIn("fc-secret-value", json.dumps(result))

    def test_firecrawl_ir_hosted_scrape_dry_run_skips_without_key(self):
        from research_os.firecrawl_ir_collector import scrape_firecrawl_ir_item

        result = scrape_firecrawl_ir_item(
            {"company": "Apple", "ticker": "AAPL", "raw_url": "https://investor.apple.com/"},
            SimpleNamespace(firecrawl_api_key="", firecrawl_base_url="https://api.firecrawl.dev/v2"),
        )

        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "firecrawl_api_key_missing")

    def test_firecrawl_ir_hosted_dry_run_result_reports_next_action_without_key(self):
        from research_os.firecrawl_ir_collector import build_firecrawl_ir_hosted_dry_run_result

        result = build_firecrawl_ir_hosted_dry_run_result(
            SimpleNamespace(
                firecrawl_api_key="",
                firecrawl_base_url="https://api.firecrawl.dev/v2",
                firecrawl_timeout_seconds=30,
                firecrawl_ir_sources_json=json.dumps(
                    {"items": [{"company": "Joby Aviation", "ticker": "JOBY", "raw_url": "https://ir.jobyaviation.com/"}]}
                ),
            )
        )

        self.assertEqual(result["module"], "firecrawl_ir_hosted_dry_run")
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["hosted_scrape"]["reason"], "firecrawl_api_key_missing")
        self.assertEqual(result["source_registry"]["input_source"], "env_registry")
        self.assertIn("FIRECRAWL_API_KEY", result["next_action"])
        self.assertNotIn("fc-secret", json.dumps(result))

    def test_public_ir_sec_firecrawl_dry_run_route_returns_safe_result(self):
        import research_os_main as main
        from fastapi.testclient import TestClient

        fake_result = {
            "status": "skipped",
            "module": "firecrawl_ir_hosted_dry_run",
            "design": "firecrawl_ir_collector_v1",
            "hosted_scrape": {"status": "skipped", "reason": "firecrawl_api_key_missing"},
            "next_action": "FIRECRAWL_API_KEY를 backend secret env에 설정한 뒤 다시 실행하세요.",
        }

        with patch.object(main, "build_firecrawl_ir_hosted_dry_run_result", return_value=fake_result):
            response = TestClient(main.app).post(
                "/api/v1/public-ir-sec/firecrawl/dry-run",
                headers={"Authorization": "Bearer dev-local-token"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["module"], "firecrawl_ir_hosted_dry_run")
        self.assertEqual(payload["hosted_scrape"]["reason"], "firecrawl_api_key_missing")

    def test_firecrawl_ir_collection_skips_rpc_when_key_missing(self):
        from types import SimpleNamespace

        from research_os.firecrawl_ir_collector import build_firecrawl_ir_collection_result

        settings = SimpleNamespace(
            firecrawl_ir_dry_run=False,
            market_signal_graph_rpc_url="https://example.supabase.co/rest/v1/rpc/upsert_external_signal",
            market_signal_graph_service_role_key="",
            market_signal_graph_timeout_seconds=1,
        )

        result = build_firecrawl_ir_collection_result(
            {
                "company": "Apple",
                "ticker": "AAPL",
                "raw_url": "https://investor.apple.com/",
                "page_title": "Apple Investor Relations",
                "markdown": "Apple IR.",
            },
            settings,
            dry_run=False,
        )

        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["rpc"]["reason"], "market_signal_graph_service_role_key_missing")

    def test_firecrawl_ir_rpc_posts_payload_wrapper_and_reports_success(self):
        from research_os import firecrawl_ir_collector

        captured = {}

        class FakeResponse:
            status_code = 200
            content = b'{"id": 12}'
            text = '{"id": 12}'

            def json(self):
                return {"id": 12}

        class FakeClient:
            def __init__(self, *args, **kwargs):
                captured["init"] = kwargs

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def post(self, url, headers, json):
                captured["url"] = url
                captured["headers"] = headers
                captured["json"] = json
                return FakeResponse()

        payload = {"source_platform": "firecrawl_ir", "external_id": "x"}
        with patch.object(firecrawl_ir_collector.httpx, "Client", FakeClient):
            result = firecrawl_ir_collector.upsert_external_signal_payload(
                payload,
                rpc_url="https://example.supabase.co/rest/v1/rpc/upsert_external_signal",
                service_role_key="service-secret",
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["result"], {"id": 12})
        self.assertEqual(captured["json"], {"payload": payload})
        self.assertEqual(captured["headers"]["apikey"], "service-secret")
        self.assertEqual(captured["headers"]["authorization"], "Bearer service-secret")
        self.assertTrue(captured["init"]["trust_env"] is False)

    def test_firecrawl_ir_rpc_paused_project_is_skipped(self):
        from research_os import firecrawl_ir_collector

        class FakeResponse:
            status_code = 503
            content = b"project paused"
            text = "project paused"

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def post(self, url, headers, json):
                return FakeResponse()

        with patch.object(firecrawl_ir_collector.httpx, "Client", FakeClient):
            result = firecrawl_ir_collector.upsert_external_signal_payload(
                {"source_platform": "firecrawl_ir"},
                rpc_url="https://example.supabase.co/rest/v1/rpc/upsert_external_signal",
                service_role_key="service-secret",
            )

        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "supabase_project_paused")

    def test_firecrawl_ir_collection_propagates_rpc_failure(self):
        from research_os.firecrawl_ir_collector import batch_status_from_counts, collection_status_from_rpc_result

        self.assertEqual(collection_status_from_rpc_result({"status": "success"}), "success")
        self.assertEqual(collection_status_from_rpc_result({"status": "skipped"}), "skipped")
        self.assertEqual(collection_status_from_rpc_result({"status": "failed"}), "failed")
        self.assertEqual(batch_status_from_counts({"success": 2}), "success")
        self.assertEqual(batch_status_from_counts({"success": 1, "skipped": 1}), "success")
        self.assertEqual(batch_status_from_counts({"skipped": 2}), "skipped")
        self.assertEqual(batch_status_from_counts({"dry_run": 2}), "dry_run")
        self.assertEqual(batch_status_from_counts({"failed": 1, "success": 1}), "failed")

    def test_market_signal_graph_rpc_url_derives_from_supabase_url(self):
        from research_os.settings import _resolve_market_signal_graph_rpc_url

        self.assertEqual(
            _resolve_market_signal_graph_rpc_url("", "https://example.supabase.co/"),
            "https://example.supabase.co/rest/v1/rpc/upsert_external_signal",
        )
        self.assertEqual(
            _resolve_market_signal_graph_rpc_url(
                "https://custom.example/rest/v1/rpc/upsert_external_signal",
                "https://example.supabase.co",
            ),
            "https://custom.example/rest/v1/rpc/upsert_external_signal",
        )

    def test_firecrawl_ir_env_example_documents_safe_defaults(self):
        env_example = (PROJECT_ROOT / "backend" / ".env.example").read_text(encoding="utf-8")

        for name in [
            "FIRECRAWL_IR_ENABLED",
            "FIRECRAWL_IR_DRY_RUN",
            "FIRECRAWL_API_KEY",
            "FIRECRAWL_BASE_URL",
            "FIRECRAWL_TIMEOUT_SECONDS",
            "FIRECRAWL_IR_MCP_VERSION",
            "FIRECRAWL_IR_SOURCES_JSON",
            "MARKET_SIGNAL_GRAPH_ENABLED",
            "MARKET_SIGNAL_GRAPH_SUPABASE_URL",
            "MARKET_SIGNAL_GRAPH_RPC_URL",
            "MARKET_SIGNAL_GRAPH_SERVICE_ROLE_KEY",
            "MARKET_SIGNAL_GRAPH_TIMEOUT_SECONDS",
        ]:
            self.assertIn(f"{name}=", env_example)
        self.assertIn("FIRECRAWL_IR_ENABLED=false", env_example)
        self.assertIn("FIRECRAWL_IR_DRY_RUN=true", env_example)
        self.assertIn("MARKET_SIGNAL_GRAPH_ENABLED=false", env_example)
        self.assertIn("MARKET_SIGNAL_GRAPH_SERVICE_ROLE_KEY=", env_example)

    def test_firecrawl_ir_rpc_env_example_documents_submit_preflight(self):
        env_example = (PROJECT_ROOT / "docs" / "examples" / "firecrawl_ir_rpc.env.example").read_text(encoding="utf-8")

        for expected in [
            "FIRECRAWL_IR_ENABLED=true",
            "FIRECRAWL_IR_DRY_RUN=false",
            "FIRECRAWL_IR_MCP_VERSION=3.17.0",
            "FIRECRAWL_IR_SOURCES_JSON=",
            "MARKET_SIGNAL_GRAPH_ENABLED=true",
            "MARKET_SIGNAL_GRAPH_RPC_URL=",
            "MARKET_SIGNAL_GRAPH_SERVICE_ROLE_KEY=",
        ]:
            self.assertIn(expected, env_example)
        self.assertNotIn("test-secret", env_example)

    def test_firecrawl_ir_rpc_preflight_wrapper_uses_secret_env_without_printing_values(self):
        wrapper = (PROJECT_ROOT / "tools" / "run_firecrawl_ir_rpc_preflight.ps1").read_text(encoding="utf-8")

        for expected in [
            "[Parameter(Mandatory = $true)]",
            "[ValidateSet(\"Preflight\", \"Submit\")]",
            "[System.IO.Path]::IsPathRooted($EnvFile)",
            "Join-Path $ProjectRootPath $EnvFile",
            "--env-file",
            "--require-env-registry",
            "--require-rpc-ready",
            "--submit",
            "firecrawl-ir-rpc-preflight.json",
            "firecrawl-ir-rpc-submit.json",
        ]:
            self.assertIn(expected, wrapper)
        self.assertNotIn("FIRECRAWL_API_KEY=", wrapper)
        self.assertNotIn("SERVICE_ROLE_KEY=", wrapper)

    def test_firecrawl_ir_operations_docs_describe_submit_status_contract(self):
        operations_doc = (PROJECT_ROOT / "docs" / "operations-readiness.md").read_text(encoding="utf-8")

        for expected in [
            "--submit",
            "exit 0",
            "exit 1",
            "`skipped`/`failed`",
            "--hosted-scrape-dry-run",
            "FIRECRAWL_API_KEY",
            "POST https://api.firecrawl.dev/v2/scrape",
            "FIRECRAWL_IR_MCP_VERSION=3.17.0",
            "docs\\examples\\firecrawl_ir_registry.sample.json",
            "run_firecrawl_ir_rpc_preflight.ps1",
            "docs\\examples\\firecrawl_ir_rpc.env.example",
            "full offline readiness",
            "batch_counts: success=N failed=N skipped=N dry_run=N",
        ]:
            self.assertIn(expected, operations_doc)

    def test_operations_docs_describe_openclaw_market_signal_graph_contract(self):
        operations_doc = (PROJECT_ROOT / "docs" / "operations-readiness.md").read_text(encoding="utf-8")

        for expected in [
            "/home/lib2000/market_signal_graph",
            "run_portfolio_ir_pipeline.sh",
            "portfolio-ir-pipeline.timer",
            "source_platform=firecrawl_earnings",
            "analysis_type=firecrawl_ir_signal_analysis_v2",
            "source_platform=deepseek_ir_analysis",
            "brief_type=portfolio_ir",
            "brief_type=portfolio_health",
            "portfolio_change_detection_v1",
            "telegram_brief_sender_v1",
        ]:
            self.assertIn(expected, operations_doc)

    def test_firecrawl_ir_registry_inputs_support_items_wrappers(self):
        from research_os.firecrawl_ir_collector import normalize_firecrawl_ir_inputs

        wrapped = normalize_firecrawl_ir_inputs(
            {
                "items": [
                    {"company": "Apple", "ticker": "AAPL", "raw_url": "https://investor.apple.com/"},
                    "skip-me",
                    {"company": "Joby", "ticker": "JOBY", "raw_url": "https://ir.jobyaviation.com/"},
                ]
            }
        )

        self.assertEqual(len(wrapped), 2)
        self.assertEqual(wrapped[0]["ticker"], "AAPL")
        self.assertEqual(wrapped[1]["ticker"], "JOBY")

    def test_firecrawl_ir_registry_sample_builds_valid_payloads(self):
        from research_os.firecrawl_ir_collector import (
            build_firecrawl_ir_signal_payload,
            normalize_firecrawl_ir_inputs,
        )

        sample_path = PROJECT_ROOT / "docs" / "examples" / "firecrawl_ir_registry.sample.json"
        sample = json.loads(sample_path.read_text(encoding="utf-8"))
        items = normalize_firecrawl_ir_inputs(sample)
        payloads = [build_firecrawl_ir_signal_payload(item) for item in items]

        self.assertGreaterEqual(len(payloads), 2)
        self.assertEqual({payload["source_platform"] for payload in payloads}, {"firecrawl_ir"})
        self.assertEqual({payload["source_kind"] for payload in payloads}, {"ir"})
        self.assertTrue(all(payload["needs_enrichment"] for payload in payloads))
        self.assertTrue(all(payload["analysis_status"] == "pending" for payload in payloads))
        self.assertTrue(all(len(payload["external_id"]) == 64 for payload in payloads))

    def test_firecrawl_ir_pilot_env_example_loads_registry_without_secret(self):
        tool = load_firecrawl_ir_check_tool()
        env_path = PROJECT_ROOT / "docs" / "examples" / "firecrawl_ir_pilot.env.example"
        env_text = env_path.read_text(encoding="utf-8")

        self.assertIn("FIRECRAWL_API_KEY=", env_text)
        self.assertNotIn("fc-", env_text)

        with patch.dict(os.environ, {}, clear=True):
            loaded = tool._load_env_file(env_path)
            settings = SimpleNamespace(firecrawl_ir_sources_json=os.environ.get("FIRECRAWL_IR_SOURCES_JSON", ""))
            items, source = tool._load_items(
                SimpleNamespace(input_json=None, use_env_registry=True, require_env_registry=False),
                settings,
            )

        self.assertGreaterEqual(loaded["loaded_count"], 7)
        self.assertEqual(source, "env_registry")
        self.assertEqual([item["ticker"] for item in items], ["AAPL", "JOBY"])

    def test_firecrawl_ir_batch_result_summarizes_dry_run_items(self):
        from types import SimpleNamespace

        from research_os.firecrawl_ir_collector import build_firecrawl_ir_batch_result

        settings = SimpleNamespace(
            firecrawl_ir_dry_run=True,
            market_signal_graph_rpc_url="",
            market_signal_graph_service_role_key="",
            market_signal_graph_timeout_seconds=1,
        )
        result = build_firecrawl_ir_batch_result(
            [
                {"company": "Apple", "ticker": "AAPL", "raw_url": "https://investor.apple.com/"},
                {"company": "Bad URL", "ticker": "BAD", "raw_url": "not-a-url"},
            ],
            settings,
            dry_run=True,
        )

        self.assertEqual(result["item_count"], 2)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["status_counts"]["dry_run"], 1)
        self.assertEqual(result["status_counts"]["failed"], 1)

    def test_firecrawl_ir_batch_result_reports_all_skipped_items(self):
        from types import SimpleNamespace

        from research_os.firecrawl_ir_collector import build_firecrawl_ir_batch_result

        settings = SimpleNamespace(
            firecrawl_ir_dry_run=False,
            market_signal_graph_rpc_url="https://example.supabase.co/rest/v1/rpc/upsert_external_signal",
            market_signal_graph_service_role_key="",
            market_signal_graph_timeout_seconds=1,
        )
        result = build_firecrawl_ir_batch_result(
            [
                {"company": "Apple", "ticker": "AAPL", "raw_url": "https://investor.apple.com/"},
                {"company": "Joby Aviation", "ticker": "JOBY", "raw_url": "https://ir.jobyaviation.com/"},
            ],
            settings,
            dry_run=False,
        )

        self.assertEqual(result["item_count"], 2)
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["success_count"], 0)
        self.assertEqual(result["failed_count"], 0)
        self.assertEqual(result["skipped_count"], 2)
        self.assertEqual(result["status_counts"]["skipped"], 2)

    def test_firecrawl_ir_check_tool_loads_env_registry(self):
        from types import SimpleNamespace

        tool = load_firecrawl_ir_check_tool()
        args = SimpleNamespace(input_json=None, use_env_registry=True, require_env_registry=False)
        settings = SimpleNamespace(
            firecrawl_ir_sources_json=json.dumps(
                {"items": [{"company": "Apple", "ticker": "AAPL", "raw_url": "https://investor.apple.com/"}]}
            )
        )

        items, source = tool._load_items(args, settings)

        self.assertEqual(source, "env_registry")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["ticker"], "AAPL")

    def test_firecrawl_ir_check_tool_loads_env_file_without_printing_values(self):
        tool = load_firecrawl_ir_check_tool()

        with TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / "firecrawl.env"
            env_path.write_text(
                "\n".join(
                    [
                        "FIRECRAWL_IR_ENABLED=true",
                        "export FIRECRAWL_IR_DRY_RUN=false",
                        "MARKET_SIGNAL_GRAPH_SERVICE_ROLE_KEY='test-secret'",
                    ]
                ),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"FIRECRAWL_IR_ENABLED": "false"}, clear=False):
                loaded = tool._load_env_file(env_path, override=False)
                self.assertEqual(os.environ["FIRECRAWL_IR_ENABLED"], "false")
                self.assertEqual(os.environ["FIRECRAWL_IR_DRY_RUN"], "false")
                self.assertEqual(os.environ["MARKET_SIGNAL_GRAPH_SERVICE_ROLE_KEY"], "test-secret")
                self.assertEqual(loaded["loaded_count"], 2)
                self.assertEqual(loaded["skipped_existing_count"], 1)

                overridden = tool._load_env_file(env_path, override=True)
                self.assertEqual(os.environ["FIRECRAWL_IR_ENABLED"], "true")
                self.assertEqual(overridden["loaded_count"], 3)

    def test_firecrawl_ir_check_tool_requires_env_registry_input(self):
        from types import SimpleNamespace

        tool = load_firecrawl_ir_check_tool()
        args = SimpleNamespace(input_json=None, use_env_registry=False, require_env_registry=True)
        settings = SimpleNamespace(
            firecrawl_ir_sources_json=json.dumps(
                {"items": [{"company": "Apple", "ticker": "AAPL", "raw_url": "https://investor.apple.com/"}]}
            )
        )

        items, source = tool._load_items(args, settings)

        self.assertEqual(source, "env_registry")
        self.assertEqual(len(items), 1)

    def test_firecrawl_ir_check_tool_requires_rpc_config_for_submit(self):
        from types import SimpleNamespace

        tool = load_firecrawl_ir_check_tool()

        missing = tool._rpc_submit_readiness_errors(
            SimpleNamespace(
                firecrawl_ir_enabled=False,
                firecrawl_ir_dry_run=True,
                market_signal_graph_enabled=False,
                market_signal_graph_rpc_url="",
                market_signal_graph_service_role_key="",
            )
        )
        ready = tool._rpc_submit_readiness_errors(
            SimpleNamespace(
                firecrawl_ir_enabled=True,
                firecrawl_ir_dry_run=False,
                market_signal_graph_enabled=True,
                market_signal_graph_rpc_url="https://example.supabase.co/rest/v1/rpc/upsert_external_signal",
                market_signal_graph_service_role_key="secret",
            )
        )

        self.assertEqual(len(missing), 5)
        self.assertEqual(ready, [])
        self.assertTrue(all("--submit" in error for error in missing))
        self.assertTrue(any("FIRECRAWL_IR_DRY_RUN" in error for error in missing))

    def test_firecrawl_ir_check_tool_labels_rpc_preflight_errors(self):
        from types import SimpleNamespace

        tool = load_firecrawl_ir_check_tool()

        missing = tool._rpc_preflight_readiness_errors(
            SimpleNamespace(
                firecrawl_api_key="",
                firecrawl_ir_enabled=False,
                firecrawl_ir_dry_run=True,
                market_signal_graph_enabled=False,
                market_signal_graph_rpc_url="",
                market_signal_graph_service_role_key="",
            )
        )

        self.assertTrue(all("--require-rpc-ready" in error for error in missing))
        self.assertTrue(any("FIRECRAWL_API_KEY" in error for error in missing))

    def test_firecrawl_ir_check_tool_lists_rpc_production_checklist_without_secret_values(self):
        tool = load_firecrawl_ir_check_tool()

        checklist = tool._rpc_production_checklist()
        joined = "\n".join(checklist)

        self.assertIn("FIRECRAWL_API_KEY configured in backend secret env", joined)
        self.assertIn("FIRECRAWL_IR_DRY_RUN=false", joined)
        self.assertIn("--require-rpc-ready", joined)
        self.assertNotIn("FIRECRAWL_API_KEY=", joined)
        self.assertNotIn("SERVICE_ROLE_KEY=", joined)

    def test_firecrawl_ir_check_tool_enforces_pinned_mcp_version(self):
        from types import SimpleNamespace

        tool = load_firecrawl_ir_check_tool()

        self.assertEqual(
            tool._mcp_version_errors(SimpleNamespace(firecrawl_ir_mcp_version="3.17.0")),
            [],
        )
        self.assertIn(
            "FIRECRAWL_IR_MCP_VERSION must be 3.17.0",
            tool._mcp_version_errors(SimpleNamespace(firecrawl_ir_mcp_version="3.18.0"))[0],
        )

    def test_firecrawl_ir_check_tool_reports_rpc_preflight_status(self):
        tool = load_firecrawl_ir_check_tool()

        not_ready = tool._rpc_preflight_result(["FIRECRAWL_IR_DRY_RUN must be false for --require-rpc-ready"])
        ready = tool._rpc_preflight_result([])

        self.assertEqual(not_ready["status"], "skipped")
        self.assertEqual(not_ready["reason"], "rpc_not_ready")
        self.assertEqual(
            not_ready["readiness_errors"],
            ["FIRECRAWL_IR_DRY_RUN must be false for --require-rpc-ready"],
        )
        self.assertEqual(ready, {"status": "ready"})

    def test_firecrawl_ir_check_tool_writes_rpc_preflight_status_to_output_json(self):
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "firecrawl-ir-preflight.json"
            env = os.environ.copy()
            env.update(
                {
                    "FIRECRAWL_IR_ENABLED": "false",
                    "FIRECRAWL_IR_DRY_RUN": "true",
                    "FIRECRAWL_API_KEY": "",
                    "FIRECRAWL_IR_MCP_VERSION": "3.17.0",
                    "MARKET_SIGNAL_GRAPH_ENABLED": "false",
                    "MARKET_SIGNAL_GRAPH_RPC_URL": "",
                    "MARKET_SIGNAL_GRAPH_SUPABASE_URL": "",
                    "MARKET_SIGNAL_GRAPH_SERVICE_ROLE_KEY": "",
                    "SUPABASE_URL": "",
                    "SUPABASE_SERVICE_ROLE_KEY": "",
                }
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(PROJECT_ROOT / "tools" / "check_firecrawl_ir_collector.py"),
                    "--input-json",
                    str(PROJECT_ROOT / "docs" / "examples" / "firecrawl_ir_registry.sample.json"),
                    "--require-rpc-ready",
                    "--output-json",
                    str(output_path),
                    "--json",
                ],
                cwd=PROJECT_ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            saved = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(saved["rpc"]["status"], "skipped")
        self.assertEqual(saved["rpc"]["reason"], "rpc_not_ready")
        self.assertFalse(saved["rpc_submit_ready"])
        self.assertTrue(saved["rpc_readiness_errors"])
        self.assertTrue(saved["rpc"]["readiness_errors"])
        self.assertIn("FIRECRAWL_API_KEY", " ".join(saved["rpc_preflight_readiness_errors"]))
        self.assertIn("rpc_production_checklist", saved)
        self.assertIn("--require-rpc-ready", " ".join(saved["rpc_production_checklist"]))

    def test_firecrawl_ir_check_tool_writes_output_json(self):
        tool = load_firecrawl_ir_check_tool()

        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "firecrawl-ir-result.json"
            tool._write_output_json({"status": "success", "payload": {"ticker": "AAPL"}}, output_path)

            saved = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(saved["status"], "success")
        self.assertEqual(saved["payload"]["ticker"], "AAPL")

    def test_firecrawl_ir_check_tool_formats_batch_counts(self):
        tool = load_firecrawl_ir_check_tool()

        summary = tool._batch_counts_summary(
            {
                "success_count": 1,
                "failed_count": 0,
                "skipped_count": 2,
                "status_counts": {"success": 1, "skipped": 2, "dry_run": 3},
            }
        )

        self.assertEqual(summary, "success=1 failed=0 skipped=2 dry_run=3")

    def test_firecrawl_ir_check_tool_refreshes_top_level_submit_status(self):
        tool = load_firecrawl_ir_check_tool()

        skipped = {"status": "success", "errors": [], "batch": {"status": "skipped"}}
        failed = {"status": "success", "errors": [], "rpc": {"status": "failed"}}
        success = {"status": "success", "errors": [], "batch": {"status": "success"}}

        self.assertEqual(tool._refresh_result_status(skipped), "skipped")
        self.assertEqual(skipped["status"], "skipped")
        self.assertEqual(tool._refresh_result_status(failed), "failed")
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(tool._refresh_result_status(success), "success")

    def test_firecrawl_ir_check_tool_prints_stable_batch_counts(self):
        with TemporaryDirectory() as tmpdir:
            input_path = self.write_firecrawl_submit_items(tmpdir)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(PROJECT_ROOT / "tools" / "check_firecrawl_ir_collector.py"),
                    "--input-json",
                    str(input_path),
                    "--submit",
                ],
                cwd=PROJECT_ROOT,
                env=self.firecrawl_submit_test_env(),
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 1)
        self.assertIn("[skipped] firecrawl_ir_collector_v1", completed.stdout)
        self.assertIn("- batch_status: skipped", completed.stdout)
        self.assertIn("- batch_counts: success=0 failed=0 skipped=2 dry_run=0", completed.stdout)

    def test_firecrawl_ir_check_tool_prints_rpc_readiness_errors(self):
        env = os.environ.copy()
        env.update(
            {
                "FIRECRAWL_IR_ENABLED": "false",
                "FIRECRAWL_IR_DRY_RUN": "true",
                "FIRECRAWL_IR_MCP_VERSION": "3.17.0",
                "MARKET_SIGNAL_GRAPH_ENABLED": "false",
                "MARKET_SIGNAL_GRAPH_RPC_URL": "",
                "MARKET_SIGNAL_GRAPH_SUPABASE_URL": "",
                "MARKET_SIGNAL_GRAPH_SERVICE_ROLE_KEY": "",
                "SUPABASE_URL": "",
                "SUPABASE_SERVICE_ROLE_KEY": "",
            }
        )
        completed = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "tools" / "check_firecrawl_ir_collector.py")],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0)
        self.assertIn("- firecrawl_ir_mcp_version: 3.17.0", completed.stdout)
        self.assertIn("- rpc_submit_ready: False", completed.stdout)
        self.assertIn("- rpc_readiness_errors: 5", completed.stdout)
        self.assertIn("- rpc_production_checklist:", completed.stdout)
        self.assertIn("FIRECRAWL_IR_DRY_RUN=false", completed.stdout)
        self.assertIn("FIRECRAWL_IR_DRY_RUN must be false for RPC readiness", completed.stdout)

    def test_firecrawl_ir_check_tool_hosted_scrape_requires_api_key_without_printing_secret(self):
        env = os.environ.copy()
        env.update(
            {
                "FIRECRAWL_API_KEY": "",
                "FIRECRAWL_BASE_URL": "https://api.firecrawl.dev/v2",
                "FIRECRAWL_IR_MCP_VERSION": "3.17.0",
            }
        )
        completed = subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "tools" / "check_firecrawl_ir_collector.py"),
                "--hosted-scrape-dry-run",
                "--json",
            ],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 1)
        self.assertIn("FIRECRAWL_API_KEY must be configured", completed.stdout)
        self.assertIn('"firecrawl_api_key_configured": false', completed.stdout)
        self.assertNotIn("fc-", completed.stdout)

    def test_firecrawl_ir_check_tool_writes_submit_batch_status_to_output_json(self):
        with TemporaryDirectory() as tmpdir:
            input_path = self.write_firecrawl_submit_items(tmpdir)
            output_path = Path(tmpdir) / "firecrawl-ir-submit.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(PROJECT_ROOT / "tools" / "check_firecrawl_ir_collector.py"),
                    "--input-json",
                    str(input_path),
                    "--submit",
                    "--output-json",
                    str(output_path),
                    "--json",
                ],
                cwd=PROJECT_ROOT,
                env=self.firecrawl_submit_test_env(),
                capture_output=True,
                text=True,
                check=False,
            )

            saved = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(saved["status"], "skipped")
        self.assertTrue(saved["rpc_submit_ready"])
        self.assertEqual(saved["rpc_readiness_errors"], [])
        self.assertEqual(saved["batch"]["status"], "skipped")
        self.assertEqual(saved["batch"]["skipped_count"], 2)
        self.assertEqual(saved["batch"]["status_counts"]["skipped"], 2)

    def test_firecrawl_ir_check_tool_writes_submit_validation_failure_to_output_json(self):
        with TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "firecrawl-ir-invalid.json"
            output_path = Path(tmpdir) / "firecrawl-ir-invalid-submit.json"
            input_path.write_text(
                json.dumps({"items": [{"company": "Bad URL", "ticker": "BAD", "raw_url": "not-a-url"}]}),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(PROJECT_ROOT / "tools" / "check_firecrawl_ir_collector.py"),
                    "--input-json",
                    str(input_path),
                    "--submit",
                    "--output-json",
                    str(output_path),
                    "--json",
                ],
                cwd=PROJECT_ROOT,
                env=self.firecrawl_submit_test_env(),
                capture_output=True,
                text=True,
                check=False,
            )

            saved = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(saved["status"], "failed")
        self.assertEqual(saved["rpc"]["status"], "skipped")
        self.assertEqual(saved["rpc"]["reason"], "payload_validation_failed")
        self.assertTrue(saved["errors"])

    def test_firecrawl_ir_check_tool_summarizes_batch_payloads(self):
        tool = load_firecrawl_ir_check_tool()

        summary = tool._payload_summary(
            {
                "index": 2,
                "payload": {
                    "url": "https://investor.apple.com/",
                    "external_id": "a" * 64,
                    "metadata": {"ticker": "AAPL", "company": "Apple"},
                },
                "errors": [],
            }
        )
        failed = tool._payload_summary({"index": 3, "payload": None, "errors": ["bad url"]})

        self.assertEqual(summary["index"], 2)
        self.assertEqual(summary["ticker"], "AAPL")
        self.assertEqual(summary["company"], "Apple")
        self.assertEqual(summary["external_id_prefix"], "a" * 12)
        self.assertEqual(summary["status"], "valid")
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["errors"], ["bad url"])

    def test_firecrawl_ir_check_tool_marks_duplicate_payload_keys(self):
        tool = load_firecrawl_ir_check_tool()
        from research_os.firecrawl_ir_collector import build_firecrawl_ir_signal_payload

        payload = build_firecrawl_ir_signal_payload(
            {"company": "Apple", "ticker": "AAPL", "raw_url": "https://investor.apple.com/"}
        )
        payload_results = [
            {"index": 1, "payload": payload, "errors": []},
            {"index": 2, "payload": dict(payload), "errors": []},
        ]

        errors = tool._mark_duplicate_payload_errors(payload_results)

        self.assertEqual(len(errors), 1)
        self.assertIn("duplicate source_platform/external_id with item 1", errors[0])
        self.assertEqual(payload_results[0]["errors"], [])
        self.assertEqual(payload_results[1]["errors"], errors)
        self.assertEqual(tool._payload_summary(payload_results[1])["status"], "failed")

    def test_firecrawl_ir_check_tool_marks_canonical_hash_fallback_duplicates(self):
        tool = load_firecrawl_ir_check_tool()
        payload_results = [
            {
                "index": 1,
                "payload": {
                    "source_platform": "firecrawl_ir",
                    "external_id": "a" * 64,
                    "canonical_hash": "c" * 64,
                },
                "errors": [],
            },
            {
                "index": 2,
                "payload": {
                    "source_platform": "firecrawl_ir",
                    "external_id": "b" * 64,
                    "canonical_hash": "c" * 64,
                },
                "errors": [],
            },
        ]

        errors = tool._mark_duplicate_payload_errors(payload_results)

        self.assertEqual(len(errors), 1)
        self.assertIn("duplicate source_platform/canonical_hash with item 1", errors[0])
        self.assertEqual(payload_results[0]["errors"], [])
        self.assertEqual(payload_results[1]["errors"], errors)


class PortfolioChangeDetectionTests(unittest.TestCase):
    def test_portfolio_change_detection_tracks_health_stance_and_confidence_changes(self):
        from research_os.portfolio_change_detection import detect_portfolio_changes

        previous = {
            "brief_type": "portfolio_health",
            "channel": "portfolio",
            "created_at": "2026-06-17T08:00:00+09:00",
            "content": {
                "total_score": 6.4,
                "holdings": [
                    {"ticker": "PL", "company": "Planet Labs", "stance": "neutral", "confidence": 0.54, "score": 6.0},
                    {"ticker": "JOBY", "company": "Joby Aviation", "stance": "positive", "confidence": 0.72, "score": 7.2},
                    {"ticker": "INTC", "company": "Intel", "stance": "neutral", "confidence": 0.44, "score": 5.7},
                ],
            },
        }
        current = {
            "brief_type": "portfolio_health",
            "channel": "portfolio",
            "created_at": "2026-06-18T08:00:00+09:00",
            "content": {
                "health": {"total_score": 6.9},
                "holdings": [
                    {"ticker": "PL", "company": "Planet Labs", "stance": "positive", "confidence": 0.78, "score": 7.1},
                    {"ticker": "JOBY", "company": "Joby Aviation", "stance": "risk", "confidence": 0.58, "score": 6.4},
                    {"ticker": "ABSI", "company": "Absci", "stance": "positive", "confidence": 0.62, "score": 6.8},
                ],
            },
        }

        result = detect_portfolio_changes(previous, current)

        self.assertEqual(result["design"], "portfolio_change_detection_v1")
        self.assertEqual(result["health_score"]["delta"], 0.5)
        self.assertEqual(result["health_score"]["direction"], "up")
        self.assertEqual(result["change_counts"]["changed_count"], 4)
        self.assertEqual(result["change_counts"]["stance_changed_count"], 2)
        self.assertEqual(result["change_counts"]["watch_item_count"], 2)
        by_ticker = {item["ticker"]: item for item in result["ticker_changes"]}
        self.assertEqual(by_ticker["PL"]["stance_direction"], "improved")
        self.assertIn("confidence_changed", by_ticker["PL"]["event_types"])
        self.assertEqual(by_ticker["JOBY"]["stance_direction"], "weakened")
        self.assertTrue(by_ticker["JOBY"]["watch_item"])
        self.assertIn("added", by_ticker["ABSI"]["event_types"])
        self.assertIn("removed", by_ticker["INTC"]["event_types"])

    def test_portfolio_change_detection_accepts_payload_level_briefs(self):
        from research_os.portfolio_change_detection import normalize_portfolio_health_brief

        result = normalize_portfolio_health_brief(
            {
                "as_of": "2026-06-18",
                "score": 6.7,
                "items": [
                    {"symbol": "VRT", "name": "Vertiv", "rating": "강화", "confidence_score": "0.81"},
                ],
            }
        )

        self.assertEqual(result["brief_type"], "portfolio_health")
        self.assertEqual(result["total_score"], 6.7)
        self.assertEqual(result["items"]["VRT"]["stance"], "강화")
        self.assertEqual(result["items"]["VRT"]["confidence"], 0.81)


class TelegramBriefSenderTests(unittest.TestCase):
    def test_telegram_brief_check_tool_uses_env_chat_id(self):
        tool = load_telegram_brief_check_tool()

        with patch.dict(
            os.environ,
            {
                "MARKET_SIGNAL_GRAPH_TELEGRAM_CHAT_ID": "",
                "TELEGRAM_CHAT_ID": "12345",
            },
        ):
            chat_id, source = tool.default_telegram_chat_id()

        self.assertEqual(chat_id, "12345")
        self.assertEqual(source, "TELEGRAM_CHAT_ID")

    def test_telegram_brief_sender_renders_portfolio_change_sections(self):
        from research_os.portfolio_change_detection import detect_portfolio_changes
        from research_os.telegram_brief_sender import build_telegram_brief_payload

        change_result = detect_portfolio_changes(
            {
                "created_at": "2026-06-17T08:00:00+09:00",
                "content": {
                    "total_score": 6.4,
                    "holdings": [
                        {"ticker": "PL", "company": "Planet Labs", "stance": "neutral", "confidence": 0.54, "score": 6.0},
                        {"ticker": "JOBY", "company": "Joby Aviation", "stance": "positive", "confidence": 0.72, "score": 7.2},
                    ],
                },
            },
            {
                "created_at": "2026-06-18T08:00:00+09:00",
                "content": {
                    "health": {"total_score": 6.9},
                    "holdings": [
                        {"ticker": "PL", "company": "Planet Labs", "stance": "positive", "confidence": 0.78, "score": 7.1},
                        {"ticker": "JOBY", "company": "Joby Aviation", "stance": "risk", "confidence": 0.58, "score": 6.4},
                    ],
                },
            },
        )

        payload = build_telegram_brief_payload(change_result, chat_id="12345")

        self.assertEqual(payload["design"], "telegram_brief_sender_v1")
        self.assertTrue(payload["chat_id_configured"])
        self.assertEqual(payload["message_count"], 1)
        self.assertIn("Portfolio Health", payload["text"])
        self.assertIn("Top Movers", payload["text"])
        self.assertIn("Watch Items", payload["text"])
        self.assertIn("PL Planet Labs", payload["text"])
        self.assertIn("JOBY Joby Aviation", payload["text"])
        self.assertEqual(payload["messages"][0]["chat_id"], "12345")
        self.assertTrue(payload["messages"][0]["disable_web_page_preview"])

    def test_telegram_brief_sender_chunks_long_messages(self):
        from research_os.telegram_brief_sender import build_telegram_brief_payload

        change_result = {
            "current_as_of": "2026-06-18",
            "health_score": {"previous": 6.1, "current": 6.7, "delta": 0.6, "direction": "up"},
            "change_counts": {"changed_count": 30, "stance_changed_count": 30, "confidence_changed_count": 0, "watch_item_count": 0},
            "top_movers": [
                {
                    "ticker": f"T{i:02d}",
                    "company_name": "Very Long Company Name " + ("x" * 80),
                    "previous_stance": "neutral",
                    "current_stance": "positive",
                    "event_types": ["stance_changed"],
                }
                for i in range(30)
            ],
            "watch_items": [],
        }

        payload = build_telegram_brief_payload(change_result, max_items=30, max_message_chars=500)

        self.assertGreater(payload["message_count"], 1)
        self.assertTrue(all(len(message["text"]) <= 500 for message in payload["messages"]))


class EarningsTranscriptCollectorTests(unittest.TestCase):
    def test_earnings_transcript_payload_matches_market_signal_contract(self):
        from research_os.earnings_transcript_collector import build_earnings_transcript_signal_payload, sha256_hex

        payload = build_earnings_transcript_signal_payload(
            {
                "company": "Planet Labs",
                "ticker": "PL",
                "raw_url": "https://investors.planet.com/events-and-presentations/",
                "title": "Planet Labs Q1 FY2027 earnings call transcript",
                "fiscal_period": "Q1 FY2027",
                "event_date": "2026-06-04",
                "transcript_text": "Revenue growth and margin discipline were discussed.",
                "speaker_count": 4,
            }
        )

        self.assertEqual(payload["source_platform"], "earnings_transcript")
        self.assertEqual(payload["source_kind"], "earnings_transcript")
        self.assertEqual(payload["channel"], "web")
        self.assertEqual(
            payload["external_id"],
            sha256_hex("https://investors.planet.com/events-and-presentations/|Q1 FY2027|2026-06-04"),
        )
        self.assertTrue(payload["needs_enrichment"])
        self.assertEqual(payload["analysis_status"], "pending")
        self.assertEqual(payload["metadata"]["collector_design"], "earnings_transcript_collector_v1")
        self.assertEqual(payload["metadata"]["target_type"], "earnings_call_transcript")
        self.assertEqual(payload["metadata"]["ticker"], "PL")
        self.assertEqual(payload["metadata"]["fiscal_period"], "Q1 FY2027")

    def test_earnings_transcript_inputs_accept_wrappers_and_report_failures(self):
        from research_os.earnings_transcript_collector import (
            build_earnings_transcript_batch_result,
            normalize_earnings_transcript_inputs,
        )

        items = normalize_earnings_transcript_inputs(
            {
                "transcripts": [
                    {
                        "company": "Absci",
                        "ticker": "ABSI",
                        "raw_url": "https://ir.absci.com/events",
                        "quarter": "Q1 2026",
                        "markdown": "Transcript body",
                    },
                    {"company": "Broken", "ticker": "BAD", "raw_url": "not-a-url"},
                ]
            }
        )
        result = build_earnings_transcript_batch_result(items)

        self.assertEqual(len(items), 2)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["valid_count"], 1)
        self.assertEqual(result["failed_count"], 1)
        self.assertEqual(result["results"][0]["payload"]["metadata"]["ticker"], "ABSI")
        self.assertIn("public http/https URL", result["results"][1]["errors"][0])


class FirecrawlEarningsCollectorTests(unittest.TestCase):
    def test_firecrawl_earnings_payload_matches_market_signal_contract(self):
        from research_os.firecrawl_earnings_collector import build_firecrawl_earnings_signal_payload, sha256_hex

        payload = build_firecrawl_earnings_signal_payload(
            {
                "company": "Planet Labs",
                "ticker": "PL",
                "raw_url": "https://investors.planet.com/events-and-presentations/",
                "title": "Planet Labs Q1 FY2027 earnings release",
                "fiscal_period": "Q1 FY2027",
                "event_date": "2026-06-04",
                "markdown": "Revenue growth and margin discipline were reported.",
            }
        )

        self.assertEqual(payload["source_platform"], "firecrawl_earnings")
        self.assertEqual(payload["source_kind"], "earnings")
        self.assertEqual(payload["channel"], "web")
        self.assertEqual(
            payload["external_id"],
            sha256_hex("https://investors.planet.com/events-and-presentations/|Q1 FY2027|2026-06-04"),
        )
        self.assertTrue(payload["needs_enrichment"])
        self.assertEqual(payload["analysis_status"], "pending")
        self.assertEqual(payload["metadata"]["collector_design"], "firecrawl_earnings_collector_v1")
        self.assertEqual(payload["metadata"]["target_type"], "company_earnings")
        self.assertEqual(payload["metadata"]["ticker"], "PL")

    def test_firecrawl_earnings_batch_accepts_wrappers_and_reports_failures(self):
        from research_os.firecrawl_earnings_collector import (
            build_firecrawl_earnings_batch_result,
            normalize_firecrawl_earnings_inputs,
        )

        items = normalize_firecrawl_earnings_inputs(
            {
                "earnings": [
                    {
                        "company": "Joby Aviation",
                        "ticker": "JOBY",
                        "raw_url": "https://ir.jobyaviation.com/news-events/events-presentations/",
                        "quarter": "Q1 2026",
                        "markdown": "Shareholder letter body",
                    },
                    {"company": "Broken", "ticker": "BAD", "raw_url": "not-a-url"},
                ]
            }
        )
        result = build_firecrawl_earnings_batch_result(items)

        self.assertEqual(len(items), 2)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["valid_count"], 1)
        self.assertEqual(result["failed_count"], 1)
        self.assertEqual(result["results"][0]["payload"]["metadata"]["ticker"], "JOBY")
        self.assertIn("public http/https URL", result["results"][1]["errors"][0])


class DeepSeekIrAnalysisTests(unittest.TestCase):
    def test_deepseek_ir_analysis_payload_matches_signal_analysis_contract(self):
        from research_os.deepseek_ir_analysis import build_deepseek_ir_analysis_payload, sha256_hex
        from research_os.firecrawl_ir_collector import build_firecrawl_ir_signal_payload

        signal = build_firecrawl_ir_signal_payload(
            {
                "company": "Planet Labs",
                "ticker": "PL",
                "raw_url": "https://investors.planet.com/",
                "page_title": "Planet Labs Investor Relations",
                "markdown": "IR material",
            }
        )
        payload = build_deepseek_ir_analysis_payload(
            signal,
            {
                "stance": "positive",
                "score": 7.4,
                "confidence": 0.82,
                "summary": "Constructive IR read-through.",
                "key_points": ["IR captured"],
                "risks": ["Execution risk"],
                "catalysts": ["Earnings update"],
            },
        )

        self.assertEqual(payload["source_platform"], "deepseek_ir_analysis")
        self.assertEqual(payload["analysis_type"], "firecrawl_ir_signal_analysis_v2")
        self.assertEqual(payload["source_signal_platform"], "firecrawl_ir")
        self.assertEqual(payload["source_signal_external_id"], signal["external_id"])
        self.assertEqual(payload["ticker"], "PL")
        self.assertEqual(payload["stance"], "positive")
        self.assertEqual(payload["score"], 7.4)
        self.assertEqual(payload["confidence"], 0.82)
        self.assertEqual(payload["metadata"]["collector_design"], "deepseek_ir_analysis_contract_v1")
        self.assertEqual(
            payload["analysis_id"],
            sha256_hex(
                "|".join(
                    [
                        "firecrawl_ir_signal_analysis_v2",
                        "firecrawl_ir",
                        signal["external_id"],
                        "PL",
                        "Planet Labs Investor Relations",
                    ]
                )
            ),
        )

    def test_deepseek_ir_analysis_batch_requires_source_signal(self):
        from research_os.deepseek_ir_analysis import build_deepseek_ir_analysis_batch_result

        result = build_deepseek_ir_analysis_batch_result([{"analysis": {"summary": "missing signal"}}])

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed_count"], 1)
        self.assertIn("requires signal", result["results"][0]["errors"][0])


class PortfolioBriefContractTests(unittest.TestCase):
    def test_portfolio_brief_contract_builds_ir_and_health_payloads(self):
        from research_os.deepseek_ir_analysis import build_deepseek_ir_analysis_payload
        from research_os.firecrawl_ir_collector import build_firecrawl_ir_signal_payload
        from research_os.portfolio_brief_contract import build_portfolio_brief_batch_result
        from research_os.portfolio_signal_score import build_portfolio_signal_scores

        signal = build_firecrawl_ir_signal_payload(
            {
                "company": "Planet Labs",
                "ticker": "PL",
                "raw_url": "https://investors.planet.com/",
                "page_title": "Planet Labs Investor Relations",
                "markdown": "IR material",
            }
        )
        analysis = build_deepseek_ir_analysis_payload(
            signal,
            {"stance": "positive", "score": 7.4, "confidence": 0.82, "summary": "Constructive IR read-through."},
        )
        score_result = build_portfolio_signal_scores([analysis])
        result = build_portfolio_brief_batch_result(
            analysis_payloads=[analysis],
            score_result=score_result,
            as_of="2026-06-19T08:00:00+09:00",
        )

        self.assertEqual(result["design"], "portfolio_brief_contract_v1")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["brief_types"], ["portfolio_ir", "portfolio_health"])
        by_type = {brief["brief_type"]: brief for brief in result["briefs"]}
        self.assertEqual(by_type["portfolio_ir"]["channel"], "portfolio")
        self.assertEqual(by_type["portfolio_health"]["channel"], "portfolio")
        self.assertEqual(by_type["portfolio_ir"]["content"]["items"][0]["ticker"], "PL")
        self.assertEqual(by_type["portfolio_health"]["content"]["holdings"][0]["ticker"], "PL")
        self.assertEqual(by_type["portfolio_ir"]["metadata"]["collector_design"], "portfolio_brief_contract_v1")


class PortfolioSignalScoreTests(unittest.TestCase):
    def test_portfolio_signal_score_integrates_ir_earnings_sec_and_dart(self):
        from research_os.portfolio_signal_score import build_portfolio_signal_scores

        result = build_portfolio_signal_scores(
            [
                {"ticker": "PL", "company": "Planet Labs", "source_platform": "firecrawl_ir", "source_kind": "ir", "stance": "positive", "confidence": 0.82, "score": 7.4},
                {"ticker": "PL", "company": "Planet Labs", "source_platform": "earnings_transcript", "source_kind": "earnings_transcript", "stance": "positive", "confidence": 0.72, "score": 7.1},
                {"ticker": "PL", "company": "Planet Labs", "source_platform": "sec_edgar", "source_kind": "8-k", "stance": "neutral", "confidence": 0.56, "score": 5.6},
                {"ticker": "JOBY", "company": "Joby Aviation", "source_platform": "sec_edgar", "source_kind": "10-q", "stance": "risk", "confidence": 0.8, "score": 3.1},
                {"ticker": "005930", "company": "삼성전자", "source_platform": "opendart", "source_kind": "dart_quarterly", "stance": "positive", "confidence": 0.74, "score": 6.8},
            ]
        )

        self.assertEqual(result["design"], "portfolio_signal_score_v1")
        self.assertEqual(result["signal_count"], 5)
        self.assertEqual(result["ticker_count"], 3)
        self.assertEqual(result["source_family_counts"]["ir"], 1)
        self.assertEqual(result["source_family_counts"]["earnings"], 1)
        self.assertEqual(result["source_family_counts"]["sec"], 2)
        self.assertEqual(result["source_family_counts"]["dart"], 1)
        by_ticker = {item["ticker"]: item for item in result["tickers"]}
        self.assertEqual(by_ticker["PL"]["source_families"], ["earnings", "ir", "sec"])
        self.assertEqual(by_ticker["JOBY"]["label"], "watch")
        self.assertEqual(by_ticker["005930"]["label"], "strengthened")
        self.assertGreater(by_ticker["PL"]["score"], by_ticker["JOBY"]["score"])
        self.assertTrue(result["watch_items"])

    def test_portfolio_signal_score_uses_metadata_and_numeric_scores(self):
        from research_os.portfolio_signal_score import normalize_signal_item, source_family

        item = {
            "metadata": {"ticker": "RXRX", "company": "Recursion", "target_type": "company_ir"},
            "source_platform": "deepseek_ir_analysis",
            "score": 82,
            "confidence_score": "0.7",
        }

        self.assertEqual(source_family(item), "ir")
        normalized = normalize_signal_item(item)
        self.assertEqual(normalized["ticker"], "RXRX")
        self.assertEqual(normalized["company_name"], "Recursion")
        self.assertEqual(normalized["confidence"], 0.7)
        self.assertGreater(normalized["signal_score"], 0)


class MarketSignalGraphPipelineContractTests(unittest.TestCase):
    def test_pipeline_contract_links_collect_score_change_and_telegram(self):
        from research_os.market_signal_graph_pipeline_contract import build_market_signal_graph_pipeline_contract

        result = build_market_signal_graph_pipeline_contract(telegram_chat_id="dry-run-chat")

        self.assertEqual(result["design"], "market_signal_graph_pipeline_contract_v1")
        self.assertEqual(result["status"], "success")
        self.assertIn("firecrawl_ir_collector_v1", result["contracts"])
        self.assertIn("firecrawl_earnings_collector_v1", result["contracts"])
        self.assertIn("earnings_transcript_collector_v1", result["contracts"])
        self.assertIn("deepseek_ir_analysis_contract_v1", result["contracts"])
        self.assertIn("portfolio_signal_score_v1", result["contracts"])
        self.assertIn("portfolio_brief_contract_v1", result["contracts"])
        self.assertIn("portfolio_change_detection_v1", result["contracts"])
        self.assertIn("telegram_brief_sender_v1", result["contracts"])
        self.assertEqual(result["source_payload_counts"]["firecrawl_ir"], 2)
        self.assertEqual(result["source_payload_counts"]["firecrawl_earnings"], 2)
        self.assertEqual(result["source_payload_counts"]["earnings_transcript"], 2)
        self.assertEqual(result["source_payload_counts"]["deepseek_ir_analysis"], 2)
        self.assertEqual(result["source_payload_counts"]["portfolio_briefs"], 2)
        self.assertGreaterEqual(result["summary"]["signal_count"], 10)
        self.assertGreaterEqual(result["summary"]["ticker_count"], 3)
        self.assertGreater(result["summary"]["portfolio_score"], 0)
        self.assertTrue(result["change_detection"]["top_movers"])
        self.assertTrue(result["telegram"]["chat_id_configured"])
        self.assertIn("Portfolio Health", result["telegram"]["text"])

    def test_pipeline_contract_reports_payload_validation_errors(self):
        from research_os.market_signal_graph_pipeline_contract import build_market_signal_graph_pipeline_contract

        result = build_market_signal_graph_pipeline_contract(
            ir_inputs=[{"company": "Broken", "ticker": "BAD", "raw_url": "not-a-url"}],
            earnings_inputs=[{"company": "Broken", "ticker": "BAD", "raw_url": "not-a-url"}],
        )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["source_payload_counts"]["firecrawl_ir"], 0)
        self.assertEqual(result["source_payload_counts"]["earnings_transcript"], 0)
        self.assertTrue(result["errors"])
        self.assertIn("firecrawl_ir", result["errors"][0])
        self.assertTrue(any("earnings_transcript" in error for error in result["errors"]))

    def test_pipeline_contract_reports_duplicate_source_payload_keys(self):
        from research_os.market_signal_graph_pipeline_contract import build_market_signal_graph_pipeline_contract

        duplicated = {
            "company": "Planet Labs",
            "ticker": "PL",
            "raw_url": "https://investors.planet.com/",
            "page_title": "Planet Labs Investor Relations",
            "markdown": "IR material",
        }
        result = build_market_signal_graph_pipeline_contract(ir_inputs=[duplicated, duplicated])

        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["duplicate_source_keys"])
        key_types = {item["key_type"] for item in result["duplicate_source_keys"]}
        self.assertIn("source_platform_external_id", key_types)
        self.assertIn("source_platform_canonical_hash", key_types)
        self.assertTrue(any("source_payload_dedup" in error for error in result["errors"]))


class BackendModuleBoundaryTests(unittest.TestCase):
    def test_portfolio_analysis_coverage_uses_file_and_tag_markers(self):
        from research_os.portfolio_analysis_coverage import portfolio_analysis_module_state

        state = portfolio_analysis_module_state(
            [
                {"file_name": "003230-collaborative-team-report-2026-06-01.json"},
                {"file_name": "003230-smart-trade-setup-2026-06-01.json"},
                {"file_name": "003230-public-ir-sec-2026-06-05-sec-exhibit-99.1.json", "tags": ["earnings_release"]},
                {"file_name": "003230-dossier-synthesis-2026-06-01.json"},
                {"file_name": "003230-research-checklist-2026-06-01.json"},
                {"file_name": "003230-dart-filing-watch-2026-06-01.json"},
            ]
        )

        self.assertTrue(all(state.values()))

    def test_code_diff_impact_maps_legacy_api_gateway(self):
        tool = load_code_diff_impact_tool()

        self.assertEqual(tool.fallback_flow_ids("docs/new-note.md"), {"backend_module_health"})
        self.assertEqual(tool.fallback_flow_ids("backend/main.py"), {"portfolio_realtime", "backend_module_health"})
        self.assertEqual(tool.fallback_flow_ids("backend/.env.example"), {"source_automation", "backend_module_health"})

    def test_backend_module_health_flags_missing_simplenamespace_dependency(self):
        from tools import check_backend_module_health

        tree = ast.parse(
            "from types import SimpleNamespace\n"
            "known = object()\n"
            "def runtime():\n"
            "    return SimpleNamespace(ok=known, broken=missing_name)\n"
        )

        self.assertEqual(
            check_backend_module_health.simple_namespace_missing_dependencies(tree),
            [(4, "broken", "missing_name")],
        )

    def test_code_knowledge_graph_check_uses_existing_graph_when_refresh_write_is_blocked(self):
        tool = load_code_knowledge_graph_check_tool()

        with TemporaryDirectory() as tmp:
            graph_path = Path(tmp) / "code_knowledge_graph.json"
            graph_path.write_text(json.dumps({"schema_version": 1, "existing": True}), encoding="utf-8")
            with patch.object(tool, "build_graph", return_value={"schema_version": 1, "existing": False}), patch.object(
                Path,
                "write_text",
                side_effect=OSError("Read-only file system"),
            ):
                graph = tool.load_or_refresh(Path(tmp), graph_path, refresh=True)

        self.assertTrue(graph["existing"])

    def test_code_knowledge_graph_tracks_news_inbox_priority_queue(self):
        tool = load_code_knowledge_graph_builder_tool()

        source_flow = tool.FLOW_DEFINITIONS["source_automation"]

        self.assertIn("뉴스 인박스", source_flow["keywords"])
        self.assertIn("backend/research_os/news_inbox.py", source_flow["expected_files"])
        self.assertIn("tools/check_macro_source_signal_linkage.py", source_flow["expected_files"])
        self.assertIn("tools/check_news_inbox_priority_queue.py", source_flow["expected_files"])

    def test_code_knowledge_graph_tracks_storage_duplicate_review_guard(self):
        tool = load_code_knowledge_graph_builder_tool()

        storage_flow = tool.FLOW_DEFINITIONS["research_storage_rag"]

        self.assertIn("중복 리뷰", storage_flow["keywords"])
        self.assertIn("backend/research_os/dossier_queue.py", storage_flow["expected_files"])
        self.assertIn("tools/check_storage_duplicate_review.py", storage_flow["expected_files"])

    def test_system_health_payload_builder_is_in_backend_module(self):
        from research_os.settings import Settings
        from research_os.system_health import build_system_health_payload

        payload = build_system_health_payload(
            Settings(research_vault_dir="research_vault"),
            {"status": "success", "ready": True},
        )

        self.assertEqual(payload["module"], "system_health")
        self.assertTrue(payload["ocr_ready"])
        self.assertIn("storage_quality_route", payload["checks"])
        self.assertNotIn("api_key", json.dumps(payload).lower())
        self.assertNotIn("token", json.dumps(payload).lower())

    def test_llm_bridge_status_uses_rag_db_paths_not_search_result_window(self):
        from research_os.llm_bridge_status import build_llm_bridge_storage_status
        from research_os.rag_memory import connect_rag_db, initialize_rag_db
        from research_os.settings import Settings

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault_dir = root / "research_vault"
            capture_dir = vault_dir / "SECTOR"
            capture_dir.mkdir(parents=True)
            relative_path = "research_vault/SECTOR/SECTOR-research-capture-llm.md"
            json_relative_path = "research_vault/SECTOR/SECTOR-research-capture-llm.json"
            (root / relative_path).write_text("# LLM", encoding="utf-8")
            (root / json_relative_path).write_text(
                json.dumps(
                    {
                        "raw_content": "[수동 LLM 분석 응답]\n[원 프롬프트]\n질문\n[LLM 응답]\n답변",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (vault_dir / "manifest.json").write_text(
                json.dumps(
                    [
                        {
                            "type": "research-capture",
                            "ticker": "SECTOR",
                            "date": "2026-05-31",
                            "file_name": "SECTOR-research-capture-llm.md",
                            "relative_path": relative_path,
                            "json_relative_path": json_relative_path,
                            "tags": ["research_scope:sector"],
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            initialize_rag_db(vault_dir)
            with connect_rag_db(vault_dir) as connection:
                connection.execute(
                    """
                    INSERT INTO research_memory_documents (
                        document_id,
                        ticker,
                        source_relative_path,
                        tags_json,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        "llm-sector-doc",
                        "SECTOR",
                        relative_path,
                        "[]",
                        "2026-05-31T09:00:00+09:00",
                    ),
                )

            payload = build_llm_bridge_storage_status(
                Settings(research_vault_dir=str(vault_dir)),
                limit=1,
            )

        self.assertEqual(payload["saved_count"], 1)
        self.assertEqual(payload["active_count"], 1)
        self.assertEqual(payload["rag_connected_count"], 1)
        self.assertEqual(payload["active_rag_connected_count"], 1)
        self.assertTrue(payload["latest_entries"][0]["rag_connected"])
        self.assertEqual(payload["latest_entries"][0]["display_label"], "섹터/산업 자료")

    def test_research_manifest_reader_ignores_corrupt_trailing_bytes(self):
        from research_os.research_memory import read_manifest

        with TemporaryDirectory() as tmp:
            vault_dir = Path(tmp) / "research_vault"
            vault_dir.mkdir(parents=True)
            manifest = [
                {
                    "ticker": "005930",
                    "type": "research-capture",
                    "date": "2026-07-01",
                    "file_name": "005930-research-capture.md",
                }
            ]
            payload = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
            (vault_dir / "manifest.json").write_bytes(payload + b"\x8b\x88broken tail")

            self.assertEqual(read_manifest(vault_dir), manifest)

    def test_data_provider_status_payload_builder_is_in_backend_module(self):
        from research_os.settings import Settings
        from research_os.system_health import build_data_provider_status_payload

        payload = build_data_provider_status_payload(
            Settings(research_vault_dir="research_vault", data_provider_mode="kis"),
            {"status": "success", "ready": True},
            {"kis": {"status": "active"}},
        )

        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["mode"], "kis")
        self.assertTrue(payload["onedrive_excluded"])
        self.assertEqual(payload["ocr"]["status"], "success")
        self.assertEqual(payload["providers"]["kis"]["status"], "active")
        self.assertNotIn("api_key", json.dumps(payload).lower())
        self.assertNotIn("token", json.dumps(payload).lower())

    def test_safety_config_payload_builder_masks_secrets(self):
        from research_os.settings import Settings
        from research_os.system_health import build_safety_config_payload

        payload = build_safety_config_payload(
            Settings(
                research_vault_dir="research_vault",
                brokerage_api_key="short-secret",
                brokerage_api_secret="very-long-secret-value",
                kis_app_key="kis-key",
                kis_access_token="kis-access-token-value",
                dart_api_key="dart-key",
            )
        )

        serialized = json.dumps(payload).lower()
        self.assertTrue(payload["secrets_are_masked"])
        self.assertEqual(payload["brokerage_api_key"], "shor****cret")
        self.assertEqual(payload["dart_api_key"], "********")
        self.assertTrue(payload["credential_policy"]["configured_secrets"]["kis_access_token"])
        self.assertNotIn("very-long-secret-value", serialized)
        self.assertNotIn("kis-access-token-value", serialized)
        self.assertNotIn("dart-key", serialized)

    def test_system_health_route_is_lightweight_and_secret_free(self):
        import research_os_main as main
        from fastapi.testclient import TestClient

        response = TestClient(main.app).get("/api/v1/system/health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["module"], "system_health")
        self.assertTrue(payload["onedrive_excluded"])
        self.assertIn("data_providers_status_route", payload["checks"])
        self.assertIn("storage_quality_route", payload["checks"])
        self.assertNotIn("api_key", json.dumps(payload).lower())
        self.assertNotIn("token", json.dumps(payload).lower())

        for alias in ("/health", "/api/v1/health"):
            alias_response = TestClient(main.app).get(alias)
            self.assertEqual(alias_response.status_code, 200)
            alias_payload = alias_response.json()
            self.assertEqual(alias_payload["module"], "system_health")
            self.assertTrue(alias_payload["onedrive_excluded"])
            self.assertNotIn("api_key", json.dumps(alias_payload).lower())
            self.assertNotIn("token", json.dumps(alias_payload).lower())

    def test_safety_config_route_masks_configured_secrets(self):
        import research_os_main as main
        from fastapi.testclient import TestClient

        response = TestClient(main.app).get("/api/v1/config/safety")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["secrets_are_masked"])
        self.assertTrue(payload["onedrive_excluded"])
        self.assertIn("credential_policy", payload)
        self.assertNotIn("dev-local-token", json.dumps(payload).lower())

    def test_data_provider_status_route_is_secret_free(self):
        import research_os_main as main
        from fastapi.testclient import TestClient

        response = TestClient(main.app).get("/api/v1/data-providers/status")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "success")
        self.assertTrue(payload["onedrive_excluded"])
        self.assertIn("ocr", payload)
        self.assertIn("providers", payload)
        serialized = json.dumps(payload).lower()
        self.assertNotIn("api_key", serialized)
        self.assertNotIn("api_secret", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("refresh_token", serialized)
        self.assertNotIn("dev-local-token", serialized)

    def test_portfolio_import_module_owns_currency_and_domestic_sync_classification(self):
        from research_os.portfolio_import import (
            is_domestic_sync_like_ticker,
            portfolio_currency_for_ticker,
            portfolio_holding_from_row,
        )

        self.assertTrue(is_domestic_sync_like_ticker("003230"))
        self.assertTrue(is_domestic_sync_like_ticker("0117V0"))
        self.assertFalse(is_domestic_sync_like_ticker("PL"))
        self.assertEqual(portfolio_currency_for_ticker("003230"), "KRW")
        self.assertEqual(portfolio_currency_for_ticker("PL"), "USD")

        holding = portfolio_holding_from_row(
            {"종목코드": "003230", "종목명": "삼양식품", "수량": "18", "현재가": "1,357,000"}
        )

        self.assertIsNotNone(holding)
        self.assertEqual(holding.currency, "KRW")
        self.assertEqual(holding.market_value, 24426000)

    def test_storage_quality_module_classifies_archive_and_ocr_problem_only(self):
        from research_os.storage_quality import (
            is_archived_research_entry,
            research_memory_entry_quality_metadata,
            research_memory_legacy_policy,
            storage_quality_entry_needs_ocr,
        )

        self.assertTrue(is_archived_research_entry({"status": "archived"}))
        self.assertTrue(is_archived_research_entry({}, {"is_deleted": True}))
        policy = research_memory_legacy_policy(ticker="003230", legacy_file_count=2, archived_file_count=1)
        self.assertEqual(policy["policy"], "soft_archive")
        self.assertFalse(policy["hard_delete_allowed"])
        self.assertFalse(
            storage_quality_entry_needs_ocr(
                {
                    "tags": ["ocr_completed"],
                    "summary": "OCR/추출 완료",
                    "attachment": {"ocr_status": "success", "ocr_available": True},
                }
            )
        )
        self.assertTrue(storage_quality_entry_needs_ocr({"tags": ["ocr_needed"]}))
        metadata = research_memory_entry_quality_metadata(
            {"tags": ["url_text_unavailable"]},
            {"source_url_processing": {"status": "empty_text"}},
        )
        self.assertTrue(metadata["needs_body_copy"])
        self.assertTrue(metadata["url_text_unavailable"])

    def test_portfolio_sync_module_preserves_overseas_and_updates_domestic(self):
        from research_os.models import PortfolioHolding, SavedPortfolio
        from research_os.portfolio_sync import apply_kiwoom_domestic_balance_to_portfolio

        portfolio = SavedPortfolio(
            portfolio_name="테스트",
            holdings=[
                PortfolioHolding(ticker="033500", name="동성화인텍", quantity=167, currency="KRW"),
                PortfolioHolding(ticker="PL", name="Planet Labs PBC", quantity=100, average_cost=1.84, currency="USD"),
            ],
        )
        balance = {
            "api_id": "kt00018",
            "holdings": [
                {"ticker": "033500", "name": "동성화인텍", "quantity": 170, "average_cost": 29700},
                {"ticker": "PL", "name": "잘못 들어온 국내 잔고", "quantity": 1, "average_cost": 999},
            ],
        }

        synced, summary = apply_kiwoom_domestic_balance_to_portfolio(
            portfolio,
            balance,
            checked_at="2026-05-25T00:58:00+09:00",
        )
        by_ticker = {holding.ticker: holding for holding in synced.holdings}

        self.assertEqual(by_ticker["033500"].quantity, 170)
        self.assertEqual(by_ticker["033500"].sync_status, "account_synced")
        self.assertEqual(by_ticker["PL"].quantity, 100)
        self.assertEqual(by_ticker["PL"].average_cost, 1.84)
        self.assertEqual(by_ticker["PL"].sync_status, "manual_or_overseas_protected")
        self.assertEqual(summary["updated_count"], 1)
        self.assertEqual(summary["skipped"][0]["ticker"], "PL")

    def test_portfolio_sync_module_guards_manual_or_overseas_without_live_sync(self):
        from research_os.models import PortfolioHolding
        from research_os.portfolio_sync import protect_manual_or_overseas_holding_sync_state

        overseas = protect_manual_or_overseas_holding_sync_state(
            PortfolioHolding(ticker="JOBY", name="Joby Aviation", quantity=208, currency="USD"),
            checked_at="2026-05-26T10:00:00+09:00",
        )
        domestic = protect_manual_or_overseas_holding_sync_state(
            PortfolioHolding(ticker="003230", name="삼양식품", quantity=18, currency="KRW"),
            checked_at="2026-05-26T10:00:00+09:00",
        )

        self.assertEqual(overseas.quantity, 208)
        self.assertEqual(overseas.currency, "USD")
        self.assertEqual(overseas.sync_status, "manual_or_overseas_protected")
        self.assertEqual(overseas.sync_source, "portfolio_state_guard")
        self.assertEqual(overseas.sync_checked_at, "2026-05-26T10:00:00+09:00")
        self.assertIsNone(domestic.sync_status)

    def test_portfolio_sync_module_summarizes_current_status_and_latest_apply(self):
        from research_os.models import PortfolioHolding, SavedPortfolio
        from research_os.portfolio_sync import portfolio_sync_status_summary

        portfolio = SavedPortfolio(
            portfolio_name="테스트",
            holdings=[
                PortfolioHolding(
                    ticker="033500",
                    sync_status="account_synced",
                    sync_checked_at="2026-05-25T01:00:00+09:00",
                ),
                PortfolioHolding(
                    ticker="PL",
                    sync_status="manual_or_overseas_protected",
                    sync_checked_at="2026-05-25T01:01:00+09:00",
                ),
                PortfolioHolding(ticker="CASH"),
            ],
        )
        history = [
            {"mode": "preview", "created_at": "2026-05-25T00:50:00+09:00"},
            {
                "mode": "apply",
                "created_at": "2026-05-25T00:55:00+09:00",
                "checked_at": "2026-05-25T00:54:00+09:00",
                "message": "수량 확인 완료",
            },
        ]

        summary = portfolio_sync_status_summary(portfolio, history)

        self.assertEqual(summary["holding_count"], 3)
        self.assertEqual(summary["counts"]["account_synced"], 1)
        self.assertEqual(summary["counts"]["manual_or_overseas_protected"], 1)
        self.assertEqual(summary["counts"]["unknown"], 1)
        self.assertEqual(summary["latest_checked_at"], "2026-05-25T01:01:00+09:00")
        self.assertEqual(summary["last_history_checked_at"], "2026-05-25T00:54:00+09:00")
        self.assertEqual(summary["last_history_message"], "수량 확인 완료")


class RagMemoryUtilsModuleTests(unittest.TestCase):
    def test_rag_memory_utils_resolves_manifest_text_and_quality_flags(self):
        from tempfile import TemporaryDirectory
        from research_os import rag_memory_utils

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault_dir = root / "research_vault"
            doc_path = vault_dir / "003230" / "note.md"
            doc_path.parent.mkdir(parents=True)
            doc_path.write_text("본문 내용", encoding="utf-8")
            text = rag_memory_utils.read_manifest_text(
                vault_dir,
                {"relative_path": "research_vault/003230/note.md"},
            )
            escaped = rag_memory_utils.resolve_manifest_file(vault_dir, "../secret.txt")

        quality = rag_memory_utils.document_quality(
            {
                "confidence": 0.9,
                "summary": "입력 데이터가 부족",
                "metadata": {"status": "archived", "missing_inputs": ["매출"]},
            }
        )

        self.assertEqual(text, "본문 내용")
        self.assertIsNone(escaped)
        self.assertIn("archived", quality["quality_flags"])
        self.assertIn("insufficient_data", quality["quality_flags"])
        self.assertFalse(quality["is_injectable"])


class ProviderUsageModuleTests(unittest.TestCase):
    def test_provider_usage_records_counts_and_blocks_daily_limit(self):
        from tempfile import TemporaryDirectory
        from research_os import provider_usage

        with TemporaryDirectory() as temp_dir:
            usage_file = str(Path(temp_dir) / "provider_usage.json")
            allowed, message = provider_usage.consume_external_provider_quota(
                provider_name="tavily",
                usage_file=usage_file,
                daily_limit=2,
                monthly_limit=5,
                units=2,
                unit_label="credits",
            )
            blocked, blocked_message = provider_usage.consume_external_provider_quota(
                provider_name="tavily",
                usage_file=usage_file,
                daily_limit=2,
                monthly_limit=5,
                units=1,
                unit_label="credits",
            )
            payload = json.loads(Path(usage_file).read_text(encoding="utf-8"))

        self.assertTrue(allowed)
        self.assertIn("오늘 2/2", message)
        self.assertFalse(blocked)
        self.assertIn("무료 한도 보호", blocked_message)
        self.assertEqual(payload["tavily"]["day_count"], 2)
        self.assertEqual(payload["tavily"]["month_count"], 2)

class DataProviderStatusMessagesModuleTests(unittest.TestCase):
    def test_data_provider_status_messages_cover_kis_and_external_modes(self):
        from types import SimpleNamespace

        from research_os import data_provider_status_messages

        self.assertIn("FMP 무료 API", data_provider_status_messages.provider_status_message("fmp", True))
        self.assertIn("FMP_API_KEY", data_provider_status_messages.provider_status_message("fmp", False))
        self.assertIn("프로바이더가 설정", data_provider_status_messages.external_provider_status_message("Brave", True))
        self.assertIn("API 키가 없어", data_provider_status_messages.external_provider_status_message("Brave", False))
        self.assertIn(
            "기존 접근 토큰 재사용",
            data_provider_status_messages.kis_status_message(
                SimpleNamespace(uses_external_token=True, can_issue_token=False, app_key=None, app_secret=None)
            ),
        )
        self.assertIn(
            "자동매매 보호",
            data_provider_status_messages.kis_status_message(
                SimpleNamespace(uses_external_token=False, can_issue_token=False, app_key="key", app_secret="secret")
            ),
        )


class DataProviderStatusModuleTests(unittest.TestCase):
    def test_supplemental_provider_statuses_include_quota_and_customs_total_trend(self):
        from types import SimpleNamespace

        from research_os.data_provider_status import (
            build_financial_datasets_status,
            build_finnhub_market_status,
            build_kis_market_status,
            build_supplemental_provider_statuses,
            build_tiingo_market_status,
        )
        from research_os.settings import Settings

        settings = Settings(
            tavily_daily_credit_limit=7,
            tavily_monthly_credit_limit=70,
            brave_daily_request_limit=9,
            brave_monthly_request_limit=90,
            naver_finance_enabled=True,
        )
        statuses = {
            status.name: status.to_dict()
            for status in build_supplemental_provider_statuses(
                settings,
                finnhub_client=SimpleNamespace(is_configured=False),
                alpha_supplemental=SimpleNamespace(is_configured=True),
                tavily_supplemental=SimpleNamespace(is_configured=True),
                brave_supplemental=SimpleNamespace(is_configured=True),
                nps_client=SimpleNamespace(is_configured=False, status_message=lambda: "nps disabled"),
                customs_client=SimpleNamespace(
                    is_configured=True,
                    is_total_trend_configured=True,
                    status_message=lambda: "품목별 수출입 사용 가능",
                    total_trend_status_message=lambda: "수출입총괄 사용 가능",
                ),
            )
        }

        self.assertIn("일 7 credits", statuses["tavily_finance_search"]["message"])
        self.assertIn("월 90 requests", statuses["brave_search"]["message"])
        self.assertTrue(statuses["naver_finance_korea_indices"]["ready"])
        self.assertTrue(statuses["korea_customs_trade_total_trend"]["ready"])
        self.assertIn("수출입총괄", statuses["korea_customs_trade_total_trend"]["message"])

        kis_status = build_kis_market_status(
            SimpleNamespace(
                is_configured=False,
                uses_external_token=False,
                can_issue_token=False,
                app_key="key",
                app_secret="secret",
            )
        ).to_dict()
        self.assertEqual(kis_status["name"], "kis_overseas_market_data")
        self.assertIn("자동매매 보호", kis_status["message"])

        financial_status = build_financial_datasets_status(SimpleNamespace(is_configured=True)).to_dict()
        finnhub_market_status = build_finnhub_market_status(SimpleNamespace(is_configured=False)).to_dict()
        tiingo_status = build_tiingo_market_status(SimpleNamespace(is_configured=True)).to_dict()
        self.assertEqual(financial_status["name"], "financial_datasets_financials")
        self.assertIn("Financial Datasets", financial_status["message"])
        self.assertEqual(finnhub_market_status["name"], "finnhub_market_data")
        self.assertIn("API 키가 없어", finnhub_market_status["message"])
        self.assertEqual(tiingo_status["name"], "tiingo_market_data")
        self.assertIn("Tiingo", tiingo_status["message"])


class RagSearchResultsModuleTests(unittest.TestCase):
    def test_rag_search_results_compacts_related_generated_reports(self):
        from research_os import rag_search_results

        documents = [
            {
                "ticker": "PL",
                "report_type": "dossier-synthesis",
                "title": "latest",
                "source_file_name": "latest.md",
                "source_date": "2026-06-18",
            },
            {
                "ticker": "PL",
                "report_type": "dossier-synthesis",
                "title": "older",
                "source_file_name": "older.md",
                "source_date": "2026-06-17",
                "matched_terms": ["growth"],
            },
            {"ticker": "PL", "report_type": "broker-report", "title": "broker"},
        ]

        compacted, grouped = rag_search_results.compact_related_search_documents(documents, limit=5)

        self.assertEqual(grouped, 1)
        self.assertEqual(len(compacted), 2)
        self.assertEqual(compacted[0]["related_version_count"], 1)
        self.assertEqual(compacted[0]["related_versions"][0]["title"], "older")
        self.assertEqual(rag_search_results.match_strength(2, 2), "완전")
        self.assertEqual(rag_search_results.match_strength(1, 2), "부분")
        self.assertEqual(rag_search_results.match_strength(0, 0), "전체")
class FinancialDatasetsDataProviderModuleTests(unittest.TestCase):
    def test_financial_datasets_provider_maps_financial_payload_without_network(self):
        from research_os.financial_datasets_data_provider import FinancialDatasetsFinancialDataProvider

        class FakeClient:
            is_configured = True
            base_url = "https://financial.test"

            def get(self, endpoint, params):
                self.endpoint = endpoint
                self.params = params
                return {
                    "financials": {
                        "income_statements": [
                            {
                                "report_period": "2026-Q1",
                                "revenue": 100,
                                "gross_profit": 60,
                                "operating_income": 30,
                            }
                        ],
                        "balance_sheets": [{"cash_and_equivalents": 25}],
                        "cash_flow_statements": [{"free_cash_flow": 12}],
                    }
                }

        points = FinancialDatasetsFinancialDataProvider(FakeClient()).fetch_financial_snapshot("PL")

        self.assertEqual(len(points), 5)
        self.assertEqual(points[0].label, "financial_datasets_revenue")
        self.assertEqual(points[0].value, "100")
        self.assertEqual(points[-1].label, "financial_datasets_free_cash_flow")
        self.assertEqual(FinancialDatasetsFinancialDataProvider(FakeClient()).fetch_financial_snapshot("005930"), [])

class FmpDataProviderModuleTests(unittest.TestCase):
    def test_fmp_providers_map_quote_and_financial_payload_without_network(self):
        from research_os.data_provider_core import EmptyFinancialDataProvider, EmptyMarketDataProvider
        from research_os.fmp_data_provider import FmpFinancialDataProvider, FmpMarketDataProvider

        class FakeClient:
            is_configured = True
            base_url = "https://fmp.test"

            def get(self, endpoint, params=None):
                if endpoint == "quote":
                    return [{"price": 10.5, "marketCap": 1000000, "volume": 12345}]
                if endpoint == "income-statement":
                    return [
                        {
                            "date": "2026-03-31",
                            "revenue": 100,
                            "grossProfit": 60,
                            "operatingIncome": 25,
                            "netIncome": 10,
                        }
                    ]
                if endpoint == "ratios":
                    return [{"priceEarningsRatio": 14.2}]
                return {}

        market_points = FmpMarketDataProvider(FakeClient(), EmptyMarketDataProvider()).fetch_market_snapshot("PL")
        financial_points = FmpFinancialDataProvider(FakeClient(), EmptyFinancialDataProvider()).fetch_financial_snapshot("PL")

        self.assertEqual([point.label for point in market_points], ["last_price", "market_cap", "volume"])
        self.assertEqual(market_points[0].value, "10.5")
        self.assertEqual(financial_points[0].label, "revenue")
        self.assertEqual(financial_points[1].value, "60.0%")
        self.assertEqual(financial_points[-1].label, "pe_ratio")

    def test_fmp_market_provider_uses_fallback_and_warning_on_quote_failure(self):
        from research_os.data_provider_core import MarketDataProvider
        from research_os.fmp_data_provider import FmpMarketDataProvider
        from research_os.models import DataSourceType, InjectedDataPoint

        class FailingClient:
            base_url = "https://fmp.test"

            def get(self, endpoint, params=None):
                raise RuntimeError("empty quote")

        class FallbackMarket(MarketDataProvider):
            def fetch_market_snapshot(self, ticker):
                return [
                    InjectedDataPoint(
                        source_type=DataSourceType.MARKET_PRICE,
                        label="fallback_price",
                        value="9.5",
                        as_of="2026-06-18T00:00:00Z",
                        confidence=0.7,
                    )
                ]

        points = FmpMarketDataProvider(FailingClient(), FallbackMarket()).fetch_market_snapshot("PL")

        self.assertEqual(points[0].label, "fallback_price")
        self.assertEqual(points[-1].label, "market_data_provider_warning")
        self.assertIn("대체 프로바이더", points[-1].value)


class FinnhubDataProviderModuleTests(unittest.TestCase):
    def test_finnhub_providers_map_quote_news_and_earnings_without_network(self):
        from research_os.finnhub_data_provider import FinnhubMarketDataProvider, FinnhubSupplementalDataProvider

        class FakeClient:
            is_configured = True
            base_url = "https://finnhub.test"

            def get(self, endpoint, params=None):
                if endpoint == "quote":
                    return {"c": 10.5, "pc": 9.8}
                if endpoint == "calendar/earnings":
                    return {"earningsCalendar": [{"date": "2026-07-20", "epsEstimate": 0.1}]}
                if endpoint == "company-news":
                    return [{"datetime": 1, "headline": "Planet launches new contract"}]
                return {}

        market_points = FinnhubMarketDataProvider(FakeClient()).fetch_market_snapshot("PL")
        supplemental_points = FinnhubSupplementalDataProvider(FakeClient()).fetch_supplemental_snapshot("PL")

        self.assertEqual([point.label for point in market_points], ["finnhub_last_price", "finnhub_previous_close"])
        self.assertEqual(market_points[0].value, "10.5")
        self.assertIn("finnhub_next_earnings_event", [point.label for point in supplemental_points])
        self.assertIn("finnhub_recent_news", [point.label for point in supplemental_points])
        self.assertEqual(FinnhubMarketDataProvider(FakeClient()).fetch_market_snapshot("005930"), [])


class AlphaVantageDataProviderModuleTests(unittest.TestCase):
    def test_alpha_vantage_provider_maps_company_overview_without_network(self):
        from research_os.alpha_vantage_data_provider import AlphaVantageSupplementalDataProvider
        from research_os.settings import Settings

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "Symbol": "PL",
                    "Sector": "Industrials",
                    "Industry": "Aerospace",
                    "MarketCapitalization": "1200000000",
                    "PERatio": "15.2",
                    "ProfitMargin": "0.12",
                }

        settings = Settings(
            alpha_vantage_api_key="test-alpha-key",
            alpha_vantage_base_url="https://alpha.test/query",
        )

        with patch("research_os.alpha_vantage_data_provider.httpx.get", return_value=FakeResponse()) as get_mock:
            points = AlphaVantageSupplementalDataProvider(settings).fetch_supplemental_snapshot("PL")

        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].label, "alpha_vantage_company_overview")
        self.assertIn("Sector=Industrials", points[0].value)
        self.assertEqual(points[0].source_url, "https://alpha.test/query")
        self.assertEqual(get_mock.call_args.kwargs["params"]["symbol"], "PL")
        self.assertEqual(AlphaVantageSupplementalDataProvider(settings).fetch_supplemental_snapshot("005930"), [])


class TiingoDataProviderModuleTests(unittest.TestCase):
    def test_tiingo_provider_maps_price_payload_without_network(self):
        from research_os.settings import Settings
        from research_os.tiingo_data_provider import TiingoMarketDataProvider

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return [{"close": 10.75, "date": "2026-06-18T00:00:00Z"}]

        settings = Settings(
            tiingo_api_key="test-tiingo-key",
            tiingo_base_url="https://tiingo.test",
        )

        with patch("research_os.tiingo_data_provider.httpx.get", return_value=FakeResponse()) as get_mock:
            points = TiingoMarketDataProvider(settings).fetch_market_snapshot("PL")

        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].label, "tiingo_last_price")
        self.assertEqual(points[0].value, "10.75")
        self.assertEqual(points[0].source_url, "https://tiingo.test/tiingo/daily/PL/prices")
        self.assertEqual(get_mock.call_args.args[0], "https://tiingo.test/tiingo/daily/PL/prices")
        self.assertEqual(TiingoMarketDataProvider(settings).fetch_market_snapshot("005930"), [])


class WebSearchDataProviderModuleTests(unittest.TestCase):
    def test_web_search_data_providers_return_quota_guard_without_network(self):
        from tempfile import TemporaryDirectory
        from research_os.settings import Settings
        from research_os.web_search_data_provider import BraveSupplementalDataProvider, TavilySupplementalDataProvider

        with TemporaryDirectory() as temp_dir:
            settings = Settings(
                research_vault_dir="research_vault",
                tavily_api_key="test-tavily-key",
                tavily_daily_credit_limit=0,
                brave_api_key="test-brave-key",
                brave_daily_request_limit=0,
                provider_usage_file=str(Path(temp_dir) / "provider_usage.json"),
            )
            tavily_points = TavilySupplementalDataProvider(settings).fetch_supplemental_snapshot("PL")
            brave_points = BraveSupplementalDataProvider(settings).fetch_supplemental_snapshot("PL")

        self.assertEqual(tavily_points[0].label, "tavily_quota_guard")
        self.assertIn("무료 한도 보호", tavily_points[0].value)
        self.assertEqual(brave_points[0].label, "brave_quota_guard")
        self.assertIn("무료 한도 보호", brave_points[0].value)


class KcifReportsWatchTests(unittest.TestCase):
    def test_kcif_report_list_parser_extracts_metadata_without_body(self):
        from research_os.kcif_reports import parse_kcif_report_list

        html = """
        <ul>
          <li>
            <h5>주간보고서 &gt; Global Fund Flow</h5>
            <a href="/annual/reportView?no=1">[Fund Flow] 북미를 중심으로 주식펀드 유입 지속, 채권펀드 유입 확대</a>
            <span>조회수 161</span>
            <span>배기원,박승민</span>
            <span>2026.05.22</span>
            <a>미리보기</a>
            <span>260522-Weekly Fund Flow.pdf</span>
            <a>다운로드</a>
            <a href="javascript:;">260522-Weekly Fund Flow.pdf</a>
          </li>
        </ul>
        """

        reports = parse_kcif_report_list(html, limit=5)

        self.assertEqual(len(reports), 1)
        report = reports[0]
        self.assertIn("Fund Flow", report["title"])
        self.assertEqual(report["published_at"], "2026.05.22")
        self.assertIn("주간보고서", report["category"])
        self.assertEqual(report["file_name"], "260522-Weekly Fund Flow.pdf")
        self.assertNotIn("body", report)
        self.assertNotIn("pdf_content", report)

    def test_kcif_report_parsing_module_keeps_metadata_contract(self):
        from research_os.kcif_report_parsing import parse_kcif_report_list

        html = """
        <article>
          <strong>국제금융속보</strong>
          <a href="/annual/reportView?no=2">미국 금리 변동과 달러 유동성 점검</a>
          <span>KCIF</span>
          <span>2026.06.18</span>
          <span>260618-us-rates.pdf</span>
        </article>
        """

        reports = parse_kcif_report_list(html, base_url="https://www.kcif.or.kr/annual/reportList", limit=3)

        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["published_at"], "2026.06.18")
        self.assertEqual(reports[0]["file_name"], "260618-us-rates.pdf")
        self.assertTrue(reports[0]["detail_url"].startswith("https://www.kcif.or.kr/annual/reportView"))
        self.assertNotIn("body", reports[0])

    def test_kcif_detail_analysis_derives_signals_without_raw_text_or_pdf(self):
        from research_os.kcif_reports import analyze_kcif_detail_html

        html = """
        <section id="contents" class="report">
          <div class="view_top"><strong>글로벌 금리와 환율 변동 점검</strong></div>
          <div class="page_view">
            <div class="cont_area">
              <strong>금리는 12bp 상승했고 달러는 1.5% 강세를 보였습니다.<br/>
              환율 변동성이 확대되어 신흥국 자금 흐름을 점검해야 합니다.</strong>
            </div>
            <button>목록</button>
          </div>
        </section>
        """
        report = {"title": "글로벌 금리와 환율 변동 점검", "category": "주간보고서"}

        analysis = analyze_kcif_detail_html(html, report)

        self.assertEqual(analysis["detail_status"], "available")
        self.assertIn("금리/채권", analysis["matched_themes"])
        self.assertIn("환율/달러", analysis["matched_themes"])
        self.assertIn("12bp", analysis["numeric_signals"])
        self.assertFalse(analysis["raw_text_stored"])
        self.assertFalse(analysis["pdf_downloaded"])
        self.assertNotIn("금리는 12bp 상승", "\n".join(analysis["derived_points"]))

    def test_kcif_watch_matches_themes_and_keeps_metadata_only_policy(self):
        from research_os.kcif_reports import (
            kcif_copyright_policy,
            match_kcif_reports_to_targets,
        )

        reports = [
            {
                "report_id": "a",
                "title": "최근 글로벌 국채금리 급등에 대한 평가 및 전망",
                "category": "채권",
                "published_at": "2026.05.22",
                "author": "KCIF",
                "detail_url": "https://www.kcif.or.kr/annual/reportView?no=1",
                "file_name": "rates.pdf",
            }
        ]
        targets = [
            {
                "label": "삼양식품",
                "ticker": "003230",
                "source": "portfolio_holding",
                "keywords": ["삼양식품", "환율", "금리"],
                "weight_hint": 0.1,
            }
        ]

        matched = match_kcif_reports_to_targets(reports, targets)
        policy = kcif_copyright_policy()

        self.assertEqual(matched[0]["matched_themes"][0], "금리/채권")
        self.assertTrue(matched[0]["portfolio_related"])
        self.assertFalse(policy["full_text_stored"])
        self.assertFalse(policy["pdf_auto_download"])


class InterestListNormalizationTests(unittest.TestCase):
    def test_company_name_interest_aliases_resolve_to_korean_codes(self):
        import research_os_main as main
        from research_os.models import InterestListUpdateRequest, InterestTicker
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="research_vault")
        with patch.object(main, "read_interest_list", return_value={"tickers": [], "sectors": []}):
            response = main.normalize_interest_list(
                InterestListUpdateRequest(
                    tickers=[
                        InterestTicker(ticker="RF머트리얼즈"),
                        InterestTicker(ticker="성호전자"),
                    ]
                ),
                settings,
            )

        by_ticker = {item.ticker: item for item in response.tickers}
        self.assertIn("327260", by_ticker)
        self.assertIn("043260", by_ticker)
        self.assertEqual(by_ticker["327260"].verification.company_name, "RF머트리얼즈")
        self.assertEqual(by_ticker["043260"].verification.country, "KR")
        self.assertTrue(by_ticker["043260"].verification.verified)

    def test_bad_unknown_interest_verification_is_repaired_from_requested_symbol(self):
        import research_os_main as main
        from research_os.models import (
            InterestListUpdateRequest,
            InterestTicker,
            TickerVerificationResponse,
        )
        from research_os.settings import Settings

        bad_verification = TickerVerificationResponse(
            status="success",
            requested_symbol="성호전자",
            official_symbol="UNKNOWN",
            company_name="UNKNOWN (KIS 해외주식 공식 티커)",
            exchange="UNKNOWN",
            country="US",
            asset_type="equity",
            verified=True,
            verification_source="kis_overseas_quote",
            message="잘못된 해외주식 인증",
        )
        settings = Settings(research_vault_dir="research_vault")
        with patch.object(main, "read_interest_list", return_value={"tickers": [], "sectors": []}):
            response = main.normalize_interest_list(
                InterestListUpdateRequest(
                    tickers=[InterestTicker(ticker="UNKNOWN", verification=bad_verification)]
                ),
                settings,
            )

        self.assertEqual(response.tickers[0].ticker, "043260")
        self.assertEqual(response.tickers[0].verification.company_name, "성호전자")
        self.assertEqual(response.tickers[0].verification.verification_source, "local_official_registry")

    def test_short_numeric_values_are_not_treated_as_equity_tickers(self):
        import research_os_main as main

        self.assertFalse(main.is_plausible_equity_symbol("10"))
        self.assertTrue(main.is_plausible_equity_symbol("043260"))
        verification = main.verify_ticker_symbol("10")
        self.assertFalse(verification.verified)
        self.assertEqual(verification.verification_source, "symbol_sanity_check")

    def test_interest_sector_defaults_to_korea_region(self):
        import research_os_main as main
        from research_os.models import InterestListUpdateRequest, InterestSector
        from research_os.settings import Settings

        self.assertEqual(InterestSector(name="전력기기").region, "KR")

        settings = Settings(research_vault_dir="research_vault")
        with patch.object(main, "read_interest_list", return_value={"tickers": [], "sectors": []}):
            response = main.normalize_interest_list(
                InterestListUpdateRequest(sectors=[InterestSector(name="사이버 보안", region="")]),
                settings,
            )
        self.assertEqual(response.sectors[0].region, "KR")


class TickerRegistrySourceTests(unittest.TestCase):
    def test_nasdaq_symbol_directory_parsers_build_company_alias_profiles(self):
        from research_os.ticker_registry import (
            parse_nasdaq_listed_symbols,
            parse_nasdaq_other_symbols,
        )

        listed = parse_nasdaq_listed_symbols(
            "\n".join(
                [
                    "Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares",
                    "AAPL|Apple Inc. Common Stock|Q|N|N|100|N|N",
                    "ZZZZ|Test Company|Q|Y|N|100|N|N",
                    "File Creation Time: 0526202618|||||||",
                ]
            )
        )
        other = parse_nasdaq_other_symbols(
            "\n".join(
                [
                    "ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol",
                    "PL|Planet Labs PBC Class A Common Stock|N|PL|N|100|N|PL",
                    "TEST|Test Issue|N|TEST|N|100|Y|TEST",
                ]
            )
        )

        self.assertEqual(listed["AAPL"]["company_name"], "Apple Inc. Common Stock")
        self.assertEqual(listed["AAPL"]["exchange"], "NASDAQ")
        self.assertNotIn("ZZZZ", listed)
        self.assertEqual(other["PL"]["exchange"], "NYSE")
        self.assertIn("Planet Labs PBC", other["PL"]["aliases"])

    def test_kind_krx_parser_and_alias_resolution_support_company_name_input(self):
        import research_os_main as main
        from research_os.ticker_registry import parse_kind_krx_list

        registry = parse_kind_krx_list(
            """
            <table>
              <tr><th>회사명</th><th>종목코드</th><th>시장구분</th><th>업종</th></tr>
              <tr><td>성호전자</td><td>043260</td><td>코스닥</td><td>전자부품</td></tr>
            </table>
            """
        )

        self.assertEqual(registry["043260"]["company_name"], "성호전자")
        self.assertEqual(registry["043260"]["exchange"], "KOSDAQ")
        with patch.object(main, "read_dynamic_ticker_registry", return_value=registry):
            self.assertEqual(main.resolve_ticker_symbol_from_alias("성호전자"), "043260")


class RegionalBusinessSourcesWatchTests(unittest.TestCase):
    def test_regional_business_parser_extracts_metadata_without_body(self):
        from research_os.regional_sources import CSF_BUSINESS_URL, RegionalBusinessSource, parse_regional_business_list

        source = RegionalBusinessSource(
            source_key="csf_china_business",
            provider="CSF",
            source_url=CSF_BUSINESS_URL,
            source_scope="중국 비즈니스 정보",
        )
        html = """
        <div class="board">
          <a href="https://www.kita.net/article">中, 모바일 결제 해외 연동 확대로 환전 없는 결제 확산</a>
          <span>KITA</span>
          <span>2026-04-27</span>
        </div>
        """

        items = parse_regional_business_list(html, source=source, limit=5)

        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["source_provider"], "CSF")
        self.assertEqual(item["agency"], "KITA")
        self.assertEqual(item["published_at"], "2026-04-27")
        self.assertIn("모바일 결제", item["title"])
        self.assertNotIn("body", item)
        self.assertNotIn("raw_text", item)

    def test_policy_source_rss_parser_extracts_metadata_without_body(self):
        from research_os.policy_sources import PolicySource, parse_policy_source_rss

        source = PolicySource(
            source_key="fsc",
            provider="금융위원회",
            source_url="http://www.fsc.go.kr/about/fsc_bbs_rss/?fid=0111",
            source_scope="금융정책 보도자료 RSS",
            parser="rss",
        )
        xml = """
        <rss><channel>
          <item>
            <title>자본시장 제도 개선 방안 발표</title>
            <link>https://www.fsc.go.kr/no010101/1</link>
            <pubDate>Tue, 23 Jun 2026 09:00:00 +0900</pubDate>
          </item>
        </channel></rss>
        """

        items = parse_policy_source_rss(xml, source=source, limit=5)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["source_provider"], "금융위원회")
        self.assertEqual(items[0]["published_at"], "2026-06-23")
        self.assertEqual(items[0]["detail_url"], "https://www.fsc.go.kr/no010101/1")
        self.assertNotIn("body", items[0])

    def test_policy_source_html_parser_extracts_metadata_without_body(self):
        from research_os.policy_sources import PolicySource, parse_policy_source_html_list

        source = PolicySource(
            source_key="ftc",
            provider="공정거래위원회",
            source_url="https://www.ftc.go.kr/www/sub.do?key=12",
            source_scope="공정거래·플랫폼 규제 보도자료",
        )
        html = """
        <ul>
          <li><span>2026.06.23</span><span>시장감시국</span>
            <a href="/www/selectReportUserView.do?key=12&amp;rpttype=1&amp;report_data_no=100">
              온라인 플랫폼 공정화 정책 추진 계획
            </a>
          </li>
        </ul>
        """

        items = parse_policy_source_html_list(html, source=source, limit=5)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["source_provider"], "공정거래위원회")
        self.assertEqual(items[0]["agency"], "시장감시국")
        self.assertEqual(items[0]["published_at"], "2026-06-23")
        self.assertTrue(items[0]["detail_url"].startswith("https://www.ftc.go.kr/www/selectReportUserView.do"))
        self.assertNotIn("body", items[0])

    def test_policy_source_watch_matches_company_name_from_summary(self):
        from research_os.policy_sources import match_policy_items_to_targets

        items = [
            {
                "item_id": "absci-policy",
                "title": "바이오 AI 임상 데이터 규제 샌드박스 실증 확대",
                "summary": "Absci Corporation의 AI 신약개발 임상 데이터 활용 사례가 검토 대상에 포함됐다.",
                "source_provider": "대한민국 정책브리핑",
                "source_scope": "정부 부처 보도자료",
                "agency": "보건복지부",
                "published_at": "2026-06-24",
                "detail_url": "https://www.korea.kr/example",
                "source_url": "https://www.korea.kr/briefing/pressReleaseList.do",
            }
        ]
        targets = [
            {
                "label": "Absci Corporation",
                "ticker": "ABSI",
                "source": "portfolio_holding",
                "keywords": ["AI 신약개발", "임상 데이터"],
            }
        ]

        matched = match_policy_items_to_targets(items, targets)

        self.assertTrue(matched[0]["portfolio_related"])
        self.assertEqual(matched[0]["match_quality"], "target")
        self.assertEqual(matched[0]["reference_reason"], "target_keyword_match")
        self.assertEqual(matched[0]["target_matches"][0]["ticker"], "ABSI")
        self.assertIn("Absci", matched[0]["target_matches"][0]["matched_keywords"])

    def test_policy_source_watch_ignores_single_generic_target_keyword(self):
        from research_os.policy_sources import match_policy_items_to_targets

        items = [
            {
                "item_id": "generic-ai",
                "title": "AI 디지털 투자자문 규제 가이드라인 발표",
                "source_provider": "금융위원회",
                "source_scope": "금융정책 보도자료 RSS",
                "agency": "금융위원회",
                "published_at": "2026-06-24",
                "detail_url": "https://www.fsc.go.kr/example",
                "source_url": "http://www.fsc.go.kr/about/fsc_bbs_rss/?fid=0111",
            }
        ]
        targets = [
            {
                "label": "KODEX AI반도체 ETF",
                "ticker": "395160",
                "source": "portfolio_holding",
                "keywords": ["AI"],
            }
        ]

        matched = match_policy_items_to_targets(items, targets)

        self.assertIn("AI/디지털", matched[0]["matched_themes"])
        self.assertFalse(matched[0]["portfolio_related"])
        self.assertEqual(matched[0]["target_matches"], [])
        self.assertEqual(matched[0]["match_quality"], "theme")
        self.assertEqual(matched[0]["reference_reason"], "theme_keyword_reference")

    def test_policy_source_watch_ignores_single_generic_sector_keyword(self):
        from research_os.policy_sources import match_policy_items_to_targets

        items = [
            {
                "item_id": "generic-digital",
                "title": "디지털정부 데이터 개방 확대 방안 발표",
                "source_provider": "대한민국 정책브리핑",
                "source_scope": "정부 부처 보도자료",
                "agency": "행정안전부",
                "published_at": "2026-06-24",
                "detail_url": "https://www.korea.kr/example",
                "source_url": "https://www.korea.kr/briefing/pressReleaseList.do",
            }
        ]
        targets = [
            {
                "label": "의료기기/디지털 헬스",
                "ticker": None,
                "source": "interest_sector",
                "keywords": ["디지털"],
            }
        ]

        matched = match_policy_items_to_targets(items, targets)

        self.assertIn("AI/디지털", matched[0]["matched_themes"])
        self.assertFalse(matched[0]["portfolio_related"])
        self.assertEqual(matched[0]["target_matches"], [])
        self.assertEqual(matched[0]["match_quality"], "theme")

    def test_kiep_report_source_parser_keeps_metadata_only(self):
        from research_os.regional_sources import (
            KIEP_REPORTS_URL,
            REGIONAL_BUSINESS_SOURCES,
            RegionalBusinessSource,
            parse_regional_business_list,
            regional_business_copyright_policy,
        )

        source = RegionalBusinessSource(
            source_key="kiep_macro_reports",
            provider="KIEP",
            source_url=KIEP_REPORTS_URL,
            source_scope="대외경제정책연구원 전체보고서",
        )
        html = """
        <ul class="gallery-list">
          <li>
            <a href="/gallery.es?mid=a10101010000&bid=0001&list_no=12345">세계경제 전망과 공급망 재편 분석</a>
            <span>발간일 2026.05.27</span>
            <span>KIEP</span>
          </li>
        </ul>
        """

        items = parse_regional_business_list(html, source=source, limit=5)
        policy = regional_business_copyright_policy()

        self.assertIn("KIEP", {item.provider for item in REGIONAL_BUSINESS_SOURCES})
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["source_provider"], "KIEP")
        self.assertEqual(item["source_scope"], "대외경제정책연구원 전체보고서")
        self.assertEqual(item["published_at"], "2026-05-27")
        self.assertIn("세계경제", item["title"])
        self.assertTrue(item["detail_url"].startswith("https://www.kiep.go.kr/"))
        self.assertNotIn("body", item)
        self.assertNotIn("raw_text", item)
        self.assertIn("KIEP", policy["message"])
        self.assertFalse(policy["full_text_stored"])

    def test_regional_business_watch_matches_targets_and_keeps_metadata_only_policy(self):
        from research_os.regional_sources import (
            match_regional_business_items_to_targets,
            regional_business_copyright_policy,
        )

        items = [
            {
                "item_id": "a",
                "title": "중국 자동차 산업의 전기차 플랫폼 전환 가속",
                "source_provider": "CSF",
                "source_scope": "중국 비즈니스 정보",
                "agency": "KOTRA 베이징무역관",
                "published_at": "2026-04-20",
                "detail_url": "https://csf.kiep.go.kr/example",
                "source_url": "https://csf.kiep.go.kr/consultingInfo.es",
            }
        ]
        targets = [
            {
                "label": "TIGER 차이나과창판STAR50",
                "ticker": "414780",
                "source": "portfolio_holding",
                "keywords": ["중국", "전기차", "플랫폼"],
            }
        ]

        matched = match_regional_business_items_to_targets(items, targets)
        policy = regional_business_copyright_policy()

        self.assertTrue(matched[0]["portfolio_related"])
        self.assertIn("중국/아시아", matched[0]["matched_themes"])
        self.assertIn("전기차/배터리", matched[0]["matched_themes"])
        self.assertGreater(matched[0]["relevance_score"], 0)
        self.assertFalse(policy["full_text_stored"])
        self.assertFalse(policy["page_body_stored"])

    def test_regional_business_watch_ignores_single_generic_target_keyword(self):
        from research_os.regional_sources import match_regional_business_items_to_targets

        items = [
            {
                "item_id": "generic-ai",
                "title": "중국 전자상거래 기업의 대화형 AI 쇼핑 확산",
                "source_provider": "CSF",
                "source_scope": "중국 비즈니스 정보",
                "agency": "KOTRA",
                "published_at": "2026-05-20",
                "detail_url": "https://csf.kiep.go.kr/example",
                "source_url": "https://csf.kiep.go.kr/consultingInfo.es",
            }
        ]
        targets = [
            {
                "label": "KODEX AI반도체 ETF",
                "ticker": "395160",
                "source": "portfolio_holding",
                "keywords": ["AI"],
            }
        ]

        matched = match_regional_business_items_to_targets(items, targets)

        self.assertIn("AI/디지털", matched[0]["matched_themes"])
        self.assertFalse(matched[0]["portfolio_related"])
        self.assertEqual(matched[0]["target_matches"], [])


class CompanyIrSourcesWatchTests(unittest.TestCase):
    def test_public_ir_sec_request_preserves_company_ir_metadata(self):
        from research_os.public_ir_sec import PublicIrSecCollectRequest, collect_public_ir_sec_url

        settings = SimpleNamespace(research_vault_dir="unused")
        request = PublicIrSecCollectRequest(
            url="https://www.sec.gov/Archives/edgar/data/814676/000143774926015161/ex_957048.htm",
            target_key="CPSH",
            save_result=False,
            source_title="CPS Technologies 8-K EXHIBIT 99.1 PRESS RELEASE",
            source_provider="SEC EDGAR",
            source_type="sec_company_submissions",
            source_category="SEC 실적/보도자료",
            filing_form="8-K",
            filing_group="financial_release",
            published_at="2026-05-08",
        )

        with patch(
            "research_os.public_ir_sec.fetch_capture_source_url",
            return_value={
                "status": "success",
                "title": "Generic SEC Page",
                "final_url": str(request.url),
            },
        ), patch(
            "research_os.public_ir_sec.render_source_url_body",
            return_value="CPS Technologies financial results " * 30,
        ):
            result = collect_public_ir_sec_url(request, settings)

        self.assertEqual(result["title"], "CPS Technologies 8-K EXHIBIT 99.1 PRESS RELEASE")
        self.assertEqual(result["source_provider"], "SEC EDGAR")
        self.assertEqual(result["source_type"], "sec_company_submissions")
        self.assertEqual(result["source_category"], "SEC 실적/보도자료")
        self.assertEqual(result["filing_form"], "8-K")
        self.assertEqual(result["filing_group"], "financial_release")
        self.assertIn("financial_release", result["tags"])
        self.assertIn("8-K", result["tags"])

    def test_public_ir_sec_status_includes_firecrawl_readiness(self):
        from research_os.public_ir_sec import public_ir_sec_status_payload

        settings = SimpleNamespace(
            research_vault_dir="unused",
            firecrawl_ir_enabled=True,
            firecrawl_ir_dry_run=True,
            firecrawl_api_key="fc-secret-value",
            firecrawl_base_url="https://api.firecrawl.dev/v2",
            firecrawl_timeout_seconds=30,
            firecrawl_ir_mcp_version="3.17.0",
            firecrawl_ir_sources_json=json.dumps(
                [
                    {
                        "company": "Joby Aviation",
                        "ticker": "JOBY",
                        "raw_url": "https://ir.jobyaviation.com/",
                        "page_title": "Joby Aviation Investor Relations",
                        "markdown": "Joby investor relations.",
                    }
                ]
            ),
            market_signal_graph_enabled=False,
            market_signal_graph_rpc_url="",
            market_signal_graph_service_role_key="",
        )

        with (
            patch("research_os.public_ir_sec.resolve_vault_dir", return_value=PROJECT_ROOT / "research_vault"),
            patch("research_os.public_ir_sec.read_manifest", return_value=[]),
        ):
            status = public_ir_sec_status_payload(settings)

        self.assertEqual(status["module"], "public_ir_sec_status")
        self.assertEqual(status["firecrawl_ir"]["status"], "ready")
        self.assertTrue(status["firecrawl_ir"]["hosted_api"]["api_key_configured"])
        self.assertEqual(status["firecrawl_ir"]["dry_run_sample"]["ticker"], "JOBY")
        self.assertNotIn("fc-secret-value", json.dumps(status))

    def test_public_ir_sec_status_lists_needs_body_entries(self):
        from research_os.public_ir_sec import public_ir_sec_status_payload

        settings = SimpleNamespace(
            research_vault_dir="unused",
            firecrawl_ir_enabled=False,
            firecrawl_ir_dry_run=True,
            firecrawl_api_key="",
            firecrawl_base_url="https://api.firecrawl.dev/v2",
            firecrawl_timeout_seconds=30,
            firecrawl_ir_mcp_version="3.17.0",
            firecrawl_ir_sources_json="[]",
            market_signal_graph_enabled=False,
            market_signal_graph_rpc_url="",
            market_signal_graph_service_role_key="",
        )
        manifest = [
            {
                "scope": "public_ir_sec",
                "type": "public-ir-sec",
                "date": "2026-07-02",
                "file_name": "otly-6-k.md",
                "title": "Oatly Group 6-K SEC filing",
                "ticker": "OTLY",
                "source_url": "https://www.sec.gov/a",
                "published_at": "2026-05-20",
                "capture_quality": {"status": "보강 필요", "needs_body_copy": True},
            },
            {
                "scope": "public_ir_sec",
                "type": "public-ir-sec",
                "date": "2026-07-02",
                "file_name": "otly-6-k-002.md",
                "title": "Oatly Group 6-K SEC filing",
                "ticker": "OTLY",
                "source_url": "https://www.sec.gov/b",
                "published_at": "2026-05-20",
                "capture_quality": {"status": "보강 필요", "needs_body_copy": True},
            },
            {
                "scope": "public_ir_sec",
                "type": "public-ir-sec",
                "date": "2026-07-02",
                "file_name": "otly-6-k-different-date.md",
                "title": "Oatly Group 6-K SEC filing",
                "ticker": "OTLY",
                "source_url": "https://www.sec.gov/c",
                "published_at": "2026-04-27",
                "capture_quality": {"status": "보강 필요", "needs_body_copy": True},
            },
            {
                "scope": "public_ir_sec",
                "type": "public-ir-sec",
                "date": "2026-07-01",
                "file_name": "joby-ir.md",
                "title": "Joby investor release",
                "capture_quality": {"status": "정상", "needs_body_copy": False},
            },
        ]

        with (
            patch("research_os.public_ir_sec.resolve_vault_dir", return_value=PROJECT_ROOT / "research_vault"),
            patch("research_os.public_ir_sec.read_manifest", return_value=manifest),
        ):
            status = public_ir_sec_status_payload(settings)

        self.assertEqual(status["entry_count"], 4)
        self.assertEqual(status["needs_body_copy_count"], 3)
        self.assertEqual(status["needs_body_copy_entries"][0]["file_name"], "otly-6-k.md")
        self.assertEqual(status["needs_body_duplicate_title_group_count"], 1)
        self.assertEqual(status["needs_body_duplicate_title_groups"][0]["ticker"], "OTLY")
        self.assertEqual(status["needs_body_duplicate_title_groups"][0]["count"], 2)
        self.assertEqual(status["needs_body_duplicate_title_groups"][0]["filing_key"], "2026-05-20")
        self.assertEqual(
            status["needs_body_duplicate_title_groups"][0]["source_urls"],
            ["https://www.sec.gov/a", "https://www.sec.gov/b"],
        )
        self.assertEqual(status["recent_entries"][0]["file_name"], "otly-6-k.md")

    def test_company_ir_parser_extracts_joby_press_release_links(self):
        from research_os.company_ir_sources import COMPANY_IR_SOURCES, parse_company_ir_press_releases

        html = """
        <section>
          <a href="/news-events/press-releases/detail/182/joby-reports-first-quarter-2026-financial-results">
            Joby Reports First Quarter 2026 Financial Results
          </a>
          <time>May 7, 2026</time>
        </section>
        """

        items = parse_company_ir_press_releases(html, source=COMPANY_IR_SOURCES[0], limit=5)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["ticker"], "JOBY")
        self.assertEqual(items[0]["company_name"], "Joby Aviation")
        self.assertEqual(items[0]["published_at"], "2026-05-07")
        self.assertIn("joby-reports-first-quarter-2026-financial-results", items[0]["detail_url"])

    def test_company_ir_default_sources_cover_core_overseas_holdings(self):
        from research_os.company_ir_sources import COMPANY_IR_SOURCES

        tickers = {source.ticker for source in COMPANY_IR_SOURCES}

        self.assertTrue({"JOBY", "PL", "CHPT", "ABSI", "RXRX", "OTLY", "CPSH", "GOTU"}.issubset(tickers))
        sec_sources = {source.ticker for source in COMPANY_IR_SOURCES if source.source_scope == "sec_company_submissions"}
        self.assertTrue({"ABSI", "RXRX", "OTLY", "CPSH"}.issubset(sec_sources))

    def test_company_ir_parser_extracts_sec_submissions(self):
        from research_os.company_ir_sources import CompanyIrSource, parse_sec_company_submissions

        source = CompanyIrSource(
            source_key="cpsh_sec_submissions",
            ticker="CPSH",
            company_name="CPS Technologies",
            provider="SEC EDGAR",
            source_url="https://data.sec.gov/submissions/CIK0000814676.json",
            source_scope="sec_company_submissions",
        )
        payload = {
            "filings": {
                "recent": {
                    "form": ["4", "8-K", "S-8"],
                    "filingDate": ["2026-05-09", "2026-05-08", "2026-05-07"],
                    "reportDate": ["2026-05-09", "2026-05-04", "2026-05-07"],
                    "accessionNumber": ["0000000000-26-000004", "0001437749-26-015161", "0000000000-26-000001"],
                    "primaryDocument": ["form4.xml", "ex_957048.htm", "ignored.htm"],
                    "primaryDocDescription": ["FORM 4", "EXHIBIT 99.1 PRESS RELEASE", "Registration statement"],
                }
            }
        }

        items = parse_sec_company_submissions(payload, source=source, limit=10)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["ticker"], "CPSH")
        self.assertEqual(items[0]["category"], "SEC 실적/보도자료")
        self.assertEqual(items[0]["filing_form"], "8-K")
        self.assertEqual(items[0]["filing_group"], "financial_release")
        self.assertEqual(items[0]["published_at"], "2026-05-08")
        self.assertIn("CPS Technologies 8-K", items[0]["title"])
        self.assertEqual(
            items[0]["detail_url"],
            "https://www.sec.gov/Archives/edgar/data/814676/000143774926015161/ex_957048.htm",
        )

    def test_sec_filing_classifier_labels_financial_and_ownership_forms(self):
        from research_os.company_ir_sources import classify_sec_filing

        self.assertEqual(classify_sec_filing("10-Q"), ("SEC 실적 공시", "financial_report"))
        self.assertEqual(
            classify_sec_filing("8-K", "EXHIBIT 99.1 PRESS RELEASE"),
            ("SEC 실적/보도자료", "financial_release"),
        )
        self.assertEqual(classify_sec_filing("SC 13G/A"), ("SEC 지분 공시", "ownership_filing"))

    def test_company_ir_parser_accepts_common_news_detail_url_shapes(self):
        from research_os.company_ir_sources import CompanyIrSource, parse_company_ir_press_releases

        source = CompanyIrSource(
            source_key="planet_ir_press_releases",
            ticker="PL",
            company_name="Planet Labs PBC",
            provider="Planet Labs IR",
            source_url="https://investors.planet.com/news/default.aspx",
        )
        html = """
        <article>
          <a href="/news/news-details/2026/Planet-Reports-Financial-Results/default.aspx">
            Planet Reports Financial Results for Fiscal Fourth Quarter
          </a>
          <span>March 19, 2026</span>
        </article>
        <article>
          <a href="/news-releases/news-release-details/absci-participate-upcoming-investor-conferences">
            Absci to Participate in Upcoming Investor Conferences
          </a>
        </article>
        """

        items = parse_company_ir_press_releases(html, source=source, limit=5)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["ticker"], "PL")
        self.assertEqual(items[0]["published_at"], "2026-03-19")
        self.assertIn("Planet-Reports-Financial-Results", items[0]["detail_url"])

    def test_company_ir_parser_skips_generic_investor_navigation_links(self):
        from research_os.company_ir_sources import CompanyIrSource, parse_company_ir_press_releases

        source = CompanyIrSource(
            source_key="planet_ir_press_releases",
            ticker="PL",
            company_name="Planet Labs PBC",
            provider="Planet Labs IR",
            source_url="https://investors.planet.com/news/default.aspx",
        )
        html = """
        <nav>
          <a href="/financials/quarterly-results/default.aspx">Quarterly Results</a>
          <a href="/resources/investor-faqs/default.aspx">Investor FAQs</a>
          <a href="/events-and-presentations/default.aspx">Events & Presentations</a>
        </nav>
        """

        items = parse_company_ir_press_releases(html, source=source, limit=5)

        self.assertEqual(items, [])

    def test_company_ir_sources_can_be_extended_from_json_config(self):
        from research_os.company_ir_sources import configured_company_ir_sources

        config = json.dumps(
            [
                {
                    "ticker": "PL",
                    "company_name": "Planet Labs PBC",
                    "provider": "Planet Labs IR",
                    "source_url": "https://investors.planet.com/news-events/press-releases",
                }
            ]
        )

        sources = configured_company_ir_sources(config)
        by_ticker = {source.ticker: source for source in sources}

        self.assertIn("JOBY", by_ticker)
        self.assertIn("PL", by_ticker)
        self.assertEqual(by_ticker["PL"].company_name, "Planet Labs PBC")
        self.assertEqual(by_ticker["PL"].source_scope, "company_ir_press_releases")

    def test_company_ir_config_dedupes_custom_sources(self):
        from research_os import company_ir_config
        from research_os.company_ir_sources import CompanyIrSource

        base = [
            CompanyIrSource(
                source_key="joby_ir_press_releases",
                ticker="JOBY",
                company_name="Joby Aviation",
                provider="Joby IR",
                source_url="https://ir.jobyaviation.com/news-events/press-releases",
            )
        ]
        config = json.dumps(
            [
                {
                    "ticker": "JOBY",
                    "source_url": "https://ir.jobyaviation.com/news-events/press-releases",
                },
                {
                    "ticker": "PL",
                    "company_name": "Planet",
                    "source_url": "https://investors.planet.com/news",
                },
            ]
        )

        sources = company_ir_config.configured_company_ir_sources(base, config, CompanyIrSource)

        self.assertEqual(len(sources), 2)
        self.assertEqual(sources[1].ticker, "PL")
        self.assertEqual(sources[1].provider, "Planet IR")

    def test_company_ir_sec_parses_financial_release(self):
        from research_os import company_ir_sec
        from research_os.company_ir_sources import CompanyIrItem, CompanyIrSource, company_ir_item_id, normalize_ir_date

        source = CompanyIrSource(
            source_key="absci_sec_submissions",
            ticker="ABSI",
            company_name="Absci Corporation",
            provider="SEC EDGAR",
            source_url="https://data.sec.gov/submissions/CIK0001672688.json",
            source_scope="sec_company_submissions",
        )
        payload = {
            "filings": {
                "recent": {
                    "form": ["8-K", "4"],
                    "filingDate": ["2026-06-18", "2026-06-17"],
                    "reportDate": ["2026-06-18", "2026-06-17"],
                    "accessionNumber": ["0001672688-26-000001", "0001672688-26-000002"],
                    "primaryDocument": ["ex991.htm", "xslF345X05/doc4.xml"],
                    "primaryDocDescription": ["Exhibit 99.1 Earnings Release", "FORM 4"],
                }
            }
        }

        items = company_ir_sec.parse_sec_company_submissions(
            payload,
            source=source,
            item_factory=CompanyIrItem,
            item_id_factory=company_ir_item_id,
            normalize_date=normalize_ir_date,
        )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["filing_group"], "financial_release")
        self.assertEqual(items[0]["category"], "SEC 실적/보도자료")
        self.assertIn("/Archives/edgar/data/1672688/000167268826000001/ex991.htm", items[0]["detail_url"])


class ExternalSourceScheduleStatusTests(unittest.TestCase):
    def test_regional_source_failure_preserves_cached_provider_items(self):
        import research_os_main as main

        fetched_items = [
            {"item_id": "csf-1", "source_provider": "CSF", "title": "중국 통상 점검"},
        ]
        source_results = [
            {"provider": "CSF", "status": "success"},
            {"provider": "KIEP", "status": "failed", "error": "timeout"},
        ]
        cache = {
            "items": [
                {"item_id": "kiep-1", "source_provider": "KIEP", "title": "세계경제 보고서"},
                {"item_id": "csf-old", "source_provider": "CSF", "title": "중국 과거 자료"},
            ]
        }

        items, results, restored_count = main.merge_cached_regional_items_for_failed_sources(
            fetched_items,
            source_results,
            cache,
        )

        self.assertEqual(restored_count, 1)
        self.assertIn("kiep-1", {item["item_id"] for item in items})
        by_provider = {item["provider"]: item for item in results}
        self.assertEqual(by_provider["KIEP"]["status"], "cache_fallback")
        self.assertEqual(by_provider["KIEP"]["cached_item_count"], 1)

    def test_external_source_schedule_status_includes_regional_macro_sources(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(
            research_vault_dir="unused",
            regional_business_sources_auto_refresh=True,
            regional_business_sources_refresh_hours=24,
            naver_research_auto_refresh=True,
            shinhan_research_auto_refresh=True,
            dart_api_key="dummy",
        )

        with (
            patch.object(main, "read_kcif_reports_watch", return_value={"updated_at": "2026-05-27T09:00:00+09:00", "related_reports": [{"id": "k"}], "source_status": "cached"}),
            patch.object(main, "read_regional_business_sources_watch", return_value={"updated_at": "2026-05-27T09:00:00+09:00", "related_items": [{"id": "r"}], "source_status": "cached"}),
            patch.object(main, "read_policy_sources_watch", return_value={"updated_at": "2026-05-27T09:00:00+09:00", "related_items": [{"id": "p"}], "source_status": "cached"}),
            patch.object(main, "read_company_ir_sources_watch", return_value={"updated_at": "2026-05-27T09:00:00+09:00", "related_items": [{"id": "j", "ticker": "JOBY"}], "source_status": "cached"}),
            patch.object(main, "read_naver_research_cache", return_value={"updated_at": "2026-05-27T09:00:00+09:00", "entries": {"a": {}}, "status": "success"}),
            patch.object(main, "read_shinhan_research_cache", return_value={"updated_at": "2026-05-27T09:00:00+09:00", "entries": {"b": {}}, "status": "success"}),
            patch.object(main, "read_dart_filing_cache", return_value={"updated_at": "2026-05-27T09:00:00+09:00", "entries": {"d1": {}, "d2": {}}, "status": "success"}),
            patch.object(main, "dart_daily_check_status", return_value={"due": False, "checked_count": 2, "current_target_count": 2}),
        ):
            status = main.build_external_source_schedule_status(settings)

        by_key = {item["key"]: item for item in status}
        self.assertIn("regional_business_sources_watch", by_key)
        self.assertEqual(by_key["regional_business_sources_watch"]["label"], "EMERiCs/CSF/KIEP 지역·매크로 자료")
        self.assertTrue(by_key["regional_business_sources_watch"]["auto_refresh"])
        self.assertEqual(by_key["regional_business_sources_watch"]["related_count"], 1)
        self.assertIn("policy_sources_watch", by_key)
        self.assertEqual(by_key["policy_sources_watch"]["label"], "공식 정책·법령·규제 자료")
        self.assertEqual(by_key["policy_sources_watch"]["related_count"], 1)
        self.assertEqual(by_key["policy_sources_watch"]["policy"], "official_policy_metadata_only")
        self.assertIn("company_ir_sources_watch", by_key)
        self.assertEqual(by_key["company_ir_sources_watch"]["label"], "Joby IR 보도자료")
        self.assertEqual(by_key["company_ir_sources_watch"]["related_count"], 1)
        self.assertEqual(by_key["company_ir_sources_watch"]["policy"], "public_company_ir_capture_and_rag")
        self.assertEqual(by_key["dart_filing_watch"]["related_count"], 2)
        self.assertEqual(by_key["kcif_reports_watch"]["policy"], "metadata_and_derived_signals_only")


class PortfolioIntelligentTableHelperTests(unittest.TestCase):
    def test_price_position_metrics_calculates_target_and_52_week_position(self):
        from research_os import portfolio_intelligent_table

        metrics = portfolio_intelligent_table.build_price_position_metrics(
            current_price=100,
            holding_currency="KRW",
            week52={"week52_high": 125},
            target={"target_price": 150, "target_price_currency": "KRW"},
        )

        self.assertEqual(metrics["week52_high_proximity"], 0.8)
        self.assertEqual(metrics["week52_high_gap"], -0.2)
        self.assertEqual(metrics["target_price_proximity"], 0.6667)
        self.assertEqual(metrics["target_upside"], 0.5)
        self.assertEqual(metrics["target_status"], "계산 완료")

    def test_price_position_metrics_flags_currency_mismatch(self):
        from research_os import portfolio_intelligent_table

        metrics = portfolio_intelligent_table.build_price_position_metrics(
            current_price=100,
            holding_currency="KRW",
            week52={"week52_high": None},
            target={"target_price": 150, "target_price_currency": "USD"},
        )

        self.assertIsNone(metrics["target_price_proximity"])
        self.assertIsNone(metrics["target_upside"])
        self.assertEqual(metrics["target_status"], "목표주가 통화가 현재가 통화와 달라 근접도 계산 보류")

    def test_readiness_summary_prioritizes_target_proximity_action(self):
        from research_os import portfolio_intelligent_table

        summary = portfolio_intelligent_table.build_readiness_summary(
            verified=True,
            current_price=100,
            memory_count=4,
            thesis_connected=True,
            target_price=104,
            week52_high=120,
            target_upside=0.04,
            week52_proximity=0.83,
        )

        self.assertEqual(summary["data_readiness_score"], 1.0)
        self.assertEqual(summary["next_action"], "목표가 근접: 일부 이익실현 또는 목표 재점검")

    def test_readiness_summary_requires_thesis_before_memory_depth(self):
        from research_os import portfolio_intelligent_table

        summary = portfolio_intelligent_table.build_readiness_summary(
            verified=True,
            current_price=100,
            memory_count=1,
            thesis_connected=False,
            target_price=130,
            week52_high=150,
            target_upside=0.3,
            week52_proximity=0.67,
        )

        self.assertEqual(summary["data_readiness_score"], 0.8)
        self.assertEqual(summary["next_action"], "팀 리포트로 기준 투자 논거 생성")


class TargetPriceMemoryHelperTests(unittest.TestCase):
    def test_finalize_target_consensus_rows_sorts_and_summarizes_best(self):
        from research_os import target_price_memory

        finalized = target_price_memory.finalize_target_consensus_rows(
            [
                {"ticker": "A", "company_name": "알파", "target_upside": None, "source_count": 10},
                {"ticker": "B", "company_name": "베타", "target_upside": 0.2, "source_count": 2},
                {"ticker": "C", "company_name": "감마", "target_upside": 0.35, "source_count": 1},
            ],
            universe_count=3,
        )

        self.assertEqual([row["ticker"] for row in finalized["rows"]], ["C", "B", "A"])
        self.assertEqual(finalized["calculated_count"], 2)
        self.assertEqual(finalized["best_undervalued"]["ticker"], "C")
        self.assertIn("3개 보유/관심 종목 중 2개", finalized["summary"])
        self.assertIn("감마(C)", finalized["summary"])

    def test_target_upside_signal_labels_thresholds_and_missing_prices(self):
        from research_os import target_price_memory

        strong = target_price_memory.build_target_upside_signal(135, 100)
        near = target_price_memory.build_target_upside_signal(104, 100)
        over = target_price_memory.build_target_upside_signal(90, 100)
        missing = target_price_memory.build_target_upside_signal(None, 100)

        self.assertEqual(strong["target_upside"], 0.35)
        self.assertEqual(strong["target_gap"], 35)
        self.assertEqual(strong["valuation_signal"], "강한 저평가 후보")
        self.assertEqual(near["valuation_signal"], "목표가 근접")
        self.assertEqual(over["valuation_signal"], "목표가 초과")
        self.assertEqual(missing["valuation_signal"], "계산 보류")
        self.assertIsNone(missing["target_upside"])

    def test_target_price_memory_extracts_explicit_and_consensus_prices(self):
        from research_os import target_price_memory
        from research_os.portfolio_performance import (
            is_plausible_target_price,
            is_probable_year_or_metadata_number,
            target_price_context_source_type,
            target_price_currency,
            target_price_result,
        )

        def parse_float(value):
            try:
                return float(str(value).replace(",", ""))
            except (TypeError, ValueError):
                return None

        runtime = SimpleNamespace(
            infer_report_date_from_file=lambda file_name: "2026-06-13",
            is_plausible_target_price=is_plausible_target_price,
            is_probable_year_or_metadata_number=is_probable_year_or_metadata_number,
            parse_float_or_none=parse_float,
            target_price_context_source_type=target_price_context_source_type,
            target_price_currency=target_price_currency,
            target_price_result=target_price_result,
        )
        memory_file = SimpleNamespace(
            absolute_path=str(PROJECT_ROOT / ".test-tmp" / "target-price.md"),
            file_name="005930-research-capture-2026-06-13.md",
            modified_at="2026-06-13T09:00:00+09:00",
            report_type="research-capture",
        )

        explicit = target_price_memory.parse_explicit_analyst_target_from_text(
            runtime,
            "증권사 리포트는 목표주가 12만원을 제시했습니다.",
            memory_file,
            "KRW",
        )
        observations = target_price_memory.extract_target_price_observations_from_text(
            runtime,
            "증권사 평균 목표주가 150,000원, 핵심은 HBM 수요입니다.",
            memory_file,
            "KRW",
            ticker_context="005930",
        )
        ocr_observations = target_price_memory.extract_target_price_observations_from_text(
            runtime,
            "TPS) 목표주가\n업 © —123 (003230) PS) 옥표주가 1,250,008\n"
            "투자의견 및 목표주가 변경내역 2025.10.30 매수 2.000.000원",
            memory_file,
            "KRW",
            ticker_context="003230",
        )

        self.assertEqual(explicit["target_price"], 120000)
        self.assertEqual(explicit["target_price_currency"], "KRW")
        self.assertEqual(explicit["target_price_source_type"], "research-capture:명시 목표주가")
        self.assertEqual(observations[0]["target_price"], 150000)
        self.assertEqual(observations[0]["source_type"], "증권사 컨센서스 목표주가")
        self.assertEqual(observations[0]["source_date"], "2026-06-13")
        self.assertIn(1250008, [item["target_price"] for item in ocr_observations])
        self.assertEqual(
            target_price_memory.target_price_numeric_value(runtime, "1.850.000", "원"),
            1850000,
        )

    def test_target_price_memory_filters_allowed_reports_before_limit(self):
        from research_os import target_price_memory
        from research_os.portfolio_performance import (
            filter_target_price_outliers,
            is_plausible_target_price,
            is_probable_year_or_metadata_number,
            target_price_context_source_type,
            target_price_currency,
            target_price_result,
        )

        def parse_float(value):
            try:
                return float(str(value).replace(",", ""))
            except (TypeError, ValueError):
                return None

        test_tmp_dir = PROJECT_ROOT / ".test-tmp"
        test_tmp_dir.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=test_tmp_dir, ignore_cleanup_errors=True) as temp_dir:
            vault_dir = Path(temp_dir) / "research_vault"
            ticker_dir = vault_dir / "003230"
            ticker_dir.mkdir(parents=True)
            dart_path = ticker_dir / "003230-dart-filing-watch-2026-06-18.md"
            report_path = ticker_dir / "003230-thesis-impact-review-2026-05-24.md"
            dart_path.write_text("# 공시\n\n목표주가 없음", encoding="utf-8")
            report_path.write_text("PS) 옥표주가 1,250,008", encoding="utf-8")
            memory_files = [
                SimpleNamespace(
                    absolute_path=str(dart_path),
                    file_name=dart_path.name,
                    modified_at="2026-06-18T09:00:00+09:00",
                    report_type="saved-report",
                ),
                SimpleNamespace(
                    absolute_path=str(report_path),
                    file_name=report_path.name,
                    modified_at="2026-05-24T09:00:00+09:00",
                    report_type="saved-report",
                ),
            ]

            runtime = SimpleNamespace(
                filter_target_price_outliers=filter_target_price_outliers,
                infer_report_date_from_file=lambda file_name: "2026-05-24" if "05-24" in file_name else "2026-06-18",
                infer_report_type_from_file=lambda file_name: "thesis-impact-review"
                if "thesis-impact-review" in file_name
                else "dart-filing-watch",
                is_plausible_target_price=is_plausible_target_price,
                is_probable_year_or_metadata_number=is_probable_year_or_metadata_number,
                list_research_memory_files=lambda *_args, **_kwargs: memory_files,
                normalize_ticker=lambda value: str(value or "").upper(),
                parse_float_or_none=parse_float,
                target_price_context_source_type=target_price_context_source_type,
                target_price_currency=target_price_currency,
                target_price_result=target_price_result,
            )

            consensus = target_price_memory.build_target_price_consensus_from_memory(
                runtime,
                "003230",
                vault_dir,
                "KRW",
                limit_files=1,
            )

        self.assertEqual(consensus["target_price"], 1250008)
        self.assertEqual(consensus["latest_source_file"], report_path.name)


class TargetConsensusScanTests(unittest.TestCase):
    def test_target_consensus_scan_uses_stored_prices_by_default(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        universe = [
            {
                "ticker": "ABC",
                "company_name": "테스트",
                "currency": "KRW",
                "current_price": None,
                "sources": ["interest_ticker"],
            }
        ]
        consensus = {
            "target_price": 100,
            "target_price_currency": "KRW",
            "target_price_median": 100,
            "target_price_high": 120,
            "target_price_low": 80,
            "source_count": 1,
            "observation_count": 1,
            "confidence": 0.8,
        }

        with (
            patch.object(main, "target_consensus_universe", return_value=universe),
            patch.object(main, "build_target_price_consensus_from_memory", return_value=consensus),
            patch.object(main, "latest_provider_price", return_value=(50, "live-test")) as latest_price,
            patch.object(main, "resolve_vault_dir", return_value=PROJECT_ROOT / "research_vault"),
        ):
            result = main.build_target_consensus_scan(settings)

        latest_price.assert_not_called()
        self.assertEqual(result["price_refresh_mode"], "stored_prices_only")
        self.assertEqual(result["calculated_count"], 0)
        self.assertIn("현재가를 찾지 못했습니다", " ".join(result["warnings"]))

    def test_target_consensus_scan_can_refresh_missing_prices_when_requested(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        universe = [
            {
                "ticker": "ABC",
                "company_name": "테스트",
                "currency": "KRW",
                "current_price": None,
                "sources": ["interest_ticker"],
            }
        ]
        consensus = {
            "target_price": 100,
            "target_price_currency": "KRW",
            "target_price_median": 100,
            "target_price_high": 120,
            "target_price_low": 80,
            "source_count": 1,
            "observation_count": 1,
            "confidence": 0.8,
        }

        with (
            patch.object(main, "target_consensus_universe", return_value=universe),
            patch.object(main, "build_target_price_consensus_from_memory", return_value=consensus),
            patch.object(main, "latest_provider_price", return_value=(50, "live-test")) as latest_price,
            patch.object(main, "resolve_vault_dir", return_value=PROJECT_ROOT / "research_vault"),
        ):
            result = main.build_target_consensus_scan(settings, refresh_missing_prices=True)

        latest_price.assert_called_once_with("ABC", settings)
        self.assertEqual(result["price_refresh_mode"], "on_missing_prices")
        self.assertEqual(result["calculated_count"], 1)
        self.assertEqual(result["rows"][0]["current_price"], 50)

    def test_target_consensus_scan_does_not_warn_missing_broker_target_for_etf(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        universe = [
            {
                "ticker": "360750",
                "company_name": "TIGER 미국S&P500 ETF",
                "currency": "KRW",
                "asset_type": "etf",
                "current_price": 43500,
                "sources": ["portfolio"],
            }
        ]

        with (
            patch.object(main, "target_consensus_universe", return_value=universe),
            patch.object(main, "build_target_price_consensus_from_memory", return_value=None),
            patch.object(main, "resolve_vault_dir", return_value=PROJECT_ROOT / "research_vault"),
        ):
            result = main.build_target_consensus_scan(settings)

        self.assertEqual(result["rows"][0]["asset_type"], "etf")
        self.assertNotIn("증권사 목표주가", " ".join(result["warnings"]))


class NewsInboxPolicyTests(unittest.TestCase):
    def test_news_inbox_url_only_does_not_store_full_article_body(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        full_article = "독점 기사 본문 " * 200

        with (
            patch.object(main, "fetch_capture_source_url", return_value={
                "status": "success",
                "source_url": "https://example.com/news/1",
                "final_url": "https://example.com/news/1",
                "title": "회사 신규 수주",
                "text": full_article,
                "note": "본문 추출 완료",
            }),
            patch.object(main, "current_storage_timestamp", return_value="2026-05-20T09:00:00+09:00"),
        ):
            item = main.build_news_item_from_payload(
                {
                    "source_url": "https://example.com/news/1",
                    "raw_content": "투자 메모: 수주 규모와 마진 영향 확인",
                },
                settings,
            )

        self.assertNotIn(full_article[:120], item["raw_content"])
        self.assertNotIn("text", item["source_url_processing"])
        self.assertFalse(item["copyright_policy"]["full_article_body_stored"])
        self.assertIn("copyright_safe_metadata", item["tags"])
        self.assertIn("short_excerpt", item["source_url_processing"])

    def test_news_inbox_filters_body_missing_and_url_only_items(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        items = [
            {
                "id": "url-only",
                "title": "URL-only",
                "source_url": "https://example.com/a",
                "tags": ["url_only", "needs_body_copy"],
                "capture_quality": {"status": "보강 필요"},
                "created_at": "2026-05-20T09:00:00+09:00",
                "promoted": False,
            },
            {
                "id": "ok",
                "title": "OK",
                "tags": [],
                "capture_quality": {"status": "정상"},
                "created_at": "2026-05-20T08:00:00+09:00",
                "promoted": True,
            },
        ]
        with patch.object(main, "read_news_inbox", return_value={"items": items, "updated_at": "now"}):
            payload = main.build_news_inbox_payload(settings, filter_key="needs_body")

        self.assertEqual(payload["filtered_count"], 1)
        self.assertEqual(payload["items"][0]["id"], "url-only")
        self.assertEqual(payload["filter_counts"]["url_only"], 1)
        self.assertEqual(payload["filter_counts"]["unpromoted"], 1)


class NaverResearchIngestTests(unittest.TestCase):
    def test_naver_pdf_signal_extraction_keeps_full_text_out(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        text = (
            "투자의견 Buy를 유지합니다. 목표주가 120,000원, 현재주가 90,000원, "
            "상승여력 33.3%입니다. 핵심은 영업이익 개선입니다."
        )

        signals = main.extract_naver_report_signals(
            text,
            {"pdf_url": "https://example.com/a.pdf"},
            settings,
        )

        self.assertEqual(signals["status"], "success")
        self.assertFalse(signals["full_text_stored"])
        self.assertEqual(signals["target_price"], 120000)
        self.assertEqual(signals["current_price"], 90000)
        self.assertEqual(signals["upside_percent"], 33.3)
        self.assertTrue(signals["snippets"])
        self.assertNotIn("원문 전체", signals)

    def test_naver_priority_scores_holdings_before_generic_reports(self):
        import research_os_main as main

        context = {
            "holding_tickers": {"003230"},
            "holding_names": {"삼양식품"},
            "interest_tickers": set(),
            "interest_names": set(),
            "interest_sectors": {"반도체"},
        }

        holding_score = main.score_naver_research_priority(
            {"ticker": "003230", "company_name": "삼양식품", "title": "실적 개선"},
            context,
        )
        generic_score = main.score_naver_research_priority(
            {"ticker": "000000", "company_name": "기타", "title": "시장 점검"},
            context,
        )

        self.assertGreater(holding_score["score"], generic_score["score"])
        self.assertIn("보유종목", holding_score["reasons"])

    def test_domestic_market_close_report_detection(self):
        import research_os_main as main

        self.assertTrue(
            main.is_naver_domestic_market_close_report(
                {"category": "시황정보", "title": "국내주식 마감 시황"}
            )
        )
        self.assertFalse(
            main.is_naver_domestic_market_close_report(
                {"category": "시황정보", "title": "미국 증시 프리뷰"}
            )
        )

    def test_research_source_store_summarizes_market_journal_markets(self):
        from tools import check_research_source_store

        summaries = check_research_source_store.market_journal_market_summaries(
            [
                {
                    "market": "KR",
                    "session_date": "2026-06-17",
                    "source_origin": "naver_research_auto",
                    "source_provider": "naver_finance_research",
                    "source_title": "국내 주식 마감 시황",
                },
                {
                    "market": "US",
                    "session_date": "2026-06-16",
                    "source_origin": "manual",
                },
                {
                    "market": "US",
                    "session_date": "2026-06-17",
                    "source_origin": "telegram_auto",
                    "source_provider": "telegram_ehdwl",
                    "source_title": "Telegram @ehdwl: 06/17 미 증시",
                },
            ]
        )

        self.assertEqual(summaries["KR"]["entry_count"], 1)
        self.assertEqual(summaries["KR"]["auto_complete_count"], 1)
        self.assertEqual(summaries["US"]["entry_count"], 2)
        self.assertEqual(summaries["US"]["auto_entry_count"], 1)
        self.assertEqual(summaries["US"]["latest_session_date"], "2026-06-17")
        self.assertEqual(
            check_research_source_store.market_journal_session_age_days("2026-06-17", date(2026, 6, 19)),
            2,
        )
        self.assertIsNone(check_research_source_store.market_journal_session_age_days("날짜아님", date(2026, 6, 19)))

    def test_research_source_store_summarizes_market_journal_impact(self):
        from tools import check_research_source_store

        summary = check_research_source_store.market_journal_impact_summary(
            {
                "ticker_targets": [
                    {
                        "ticker": "AAPL",
                        "market_journal_matches": [
                            {"market": "US", "session_date": "2026-06-18"},
                            {"market": "KR", "session_date": "2026-06-17"},
                        ],
                    },
                    {"ticker": "MSFT", "market_journal_matches": []},
                ],
                "sector_targets": [
                    {
                        "name": "AI",
                        "market_journal_matches": [
                            {"market": "US", "session_date": "2026-06-16"},
                        ],
                    }
                ],
            }
        )

        self.assertEqual(summary["target_count"], 3)
        self.assertEqual(summary["ticker_target_count"], 2)
        self.assertEqual(summary["sector_target_count"], 1)
        self.assertEqual(summary["linked_target_count"], 2)
        self.assertEqual(summary["linked_ticker_count"], 1)
        self.assertEqual(summary["linked_sector_count"], 1)
        self.assertEqual(summary["unlinked_target_count"], 1)
        self.assertAlmostEqual(summary["linked_target_ratio"], 2 / 3)
        self.assertEqual(summary["match_count"], 3)
        self.assertEqual(summary["market_counts"], {"KR": 1, "US": 2})
        self.assertEqual(summary["latest_session_date"], "2026-06-18")
        self.assertEqual(summary["sample_targets"], ["AAPL", "AI"])
        formatted = check_research_source_store.format_market_journal_impact(summary)
        self.assertIn("매칭 3건", formatted)
        self.assertIn("연결률 66.7%", formatted)
        self.assertIn("미연결 1개", formatted)
        self.assertIn("티커 1/2, 섹터 1/1", formatted)
        self.assertIn(
            "설명 같은 원본이라 중복 저장하지 않았습니다.",
            check_research_source_store.format_market_journal_attempt(
                {
                    "status": "skipped_duplicate",
                    "last_attempt_date": "2026-06-19",
                    "last_attempt_at": "2026-06-19T08:30:01+09:00",
                    "last_attempt_message": "같은 원본이라 중복 저장하지 않았습니다.",
                }
            ),
        )
        telegram_attempt = check_research_source_store.format_telegram_market_journal_attempt(
            {
                "status": "skipped_duplicate",
                "last_attempt_date": "2026-06-21",
                "last_attempt_at": "2026-06-21T11:05:29+09:00",
                "last_attempt_message": "같은 텔레그램 미국 시장일지 원본이라 중복 저장하지 않았습니다.",
                "included_post_count": 4,
                "storage": {
                    "relative_path": "research_vault/MARKET-US/MARKET-US-market-close-review-2026-06-18-003.md"
                },
            }
        )
        self.assertIn("포함 섹션 4개", telegram_attempt)
        self.assertIn("MARKET-US-market-close-review-2026-06-18-003.md", telegram_attempt)

    def test_market_close_journal_daily_gate(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(
            research_vault_dir="../research_vault",
            naver_market_close_auto_journal=True,
            naver_market_close_journal_time="08:30",
        )
        now = main.datetime(2026, 5, 23, 8, 31)

        with patch.object(main, "read_json_store", return_value={"last_run_date": "2026-05-22"}):
            self.assertTrue(main.should_run_naver_market_close_journal(settings, now))
        with patch.object(main, "read_json_store", return_value={"last_run_date": "2026-05-23"}):
            self.assertFalse(main.should_run_naver_market_close_journal(settings, now))

    def test_market_close_refresh_skips_same_naver_source_without_force(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        item = {
            "item_id": "same-source",
            "category": "시황정보",
            "title": "국내 주식 마감 시황",
            "published_at": "2026-05-22",
        }
        state = {
            "source_item_id": "same-source",
            "source_published_at": "2026-05-22",
            "last_run_date": "2026-05-23",
        }

        with patch.object(main, "latest_naver_domestic_market_close_report", return_value=item), \
            patch.object(main, "read_json_store", return_value=state), \
            patch.object(main, "save_market_close_review") as save_review:
            result = main.refresh_naver_market_close_journal(settings, force=False)

        self.assertEqual(result["status"], "skipped")
        save_review.assert_not_called()

    def test_market_close_refresh_marks_auto_source(self):
        import research_os_main as main
        from research_os.models import MarketCloseEntry, MarketCloseReviewResponse
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        item = {
            "item_id": "new-source",
            "category": "시황정보",
            "title": "국내 주식 마감 시황",
            "summary": "코스피 마감 점검",
            "published_at": "2026-05-22",
        }
        response = MarketCloseReviewResponse(
            entry=MarketCloseEntry(
                entry_id="KR-2026-05-22",
                market="KR",
                session_date="2026-05-22",
                raw_summary="코스피 마감 점검",
                source_origin="naver_research_auto",
                source_provider="naver_finance_research",
                source_title="국내 주식 마감 시황",
                sentiment="중립",
                risk_level="보통",
                regime="혼조",
            ),
            recent_regime_summary="KR 최근 1회 누적",
        )

        with patch.object(main, "latest_naver_domestic_market_close_report", return_value=item), \
            patch.object(main, "read_json_store", return_value={}), \
            patch.object(main, "write_json_store") as write_store, \
            patch.object(main, "save_market_close_review", return_value=response) as save_review:
            result = main.refresh_naver_market_close_journal(settings, force=False)

        request = save_review.call_args.args[0]
        self.assertEqual(request.source_origin, "naver_research_auto")
        self.assertEqual(request.source_provider, "naver_finance_research")
        self.assertEqual(request.source_title, "국내 주식 마감 시황")
        self.assertEqual(result["entry"]["source_origin"], "naver_research_auto")
        written_state = write_store.call_args.args[1]
        self.assertEqual(written_state["status"], "success")
        self.assertTrue(written_state["last_attempt_at"])
        self.assertTrue(written_state["last_attempt_date"])
        self.assertIn("시장일지", written_state["last_attempt_message"])

    def test_telegram_market_journal_parses_public_channel_html(self):
        from research_os.telegram_market_journal import (
            latest_telegram_us_market_close_candidate,
            parse_telegram_public_channel_html,
        )

        html = """
        <div class="tgme_widget_message" data-post="ehdwl/99">
          <div class="tgme_widget_message_text">*특징 종목: 엔비디아, 마이크론 하락<br/>필라델피아 반도체 지수는 하락</div>
          <a class="tgme_widget_message_date" href="https://t.me/ehdwl/99"><time datetime="2026-06-17T01:25:00+00:00"></time></a>
        </div>
        <div class="tgme_widget_message" data-post="ehdwl/100">
          <div class="tgme_widget_message_text">06/16 미 증시, 물가와 반도체 이슈로 하락<br/>다우 -1.0%, 나스닥 -2.0%, S&amp;P500 -1.5%</div>
          <a class="tgme_widget_message_date" href="https://t.me/ehdwl/100"><time datetime="2026-06-17T01:20:00+00:00"></time></a>
        </div>
        """

        posts = parse_telegram_public_channel_html(html, channel_username="ehdwl", base_url="https://t.me/s/ehdwl")
        candidate = latest_telegram_us_market_close_candidate(posts, today=date(2026, 6, 17))

        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.source_item_id, "ehdwl/100")
        self.assertEqual(candidate.session_date, "2026-06-16")
        self.assertEqual(candidate.included_post_count, 2)
        self.assertIn("특징 종목", candidate.raw_summary)
        self.assertIn("06/16 미 증시", candidate.source_title)

    def test_telegram_market_journal_includes_sections_after_anchor(self):
        from research_os.telegram_market_journal import (
            latest_telegram_us_market_close_candidate,
            parse_telegram_public_channel_html,
        )

        html = """
        <div class="tgme_widget_message" data-post="ehdwl/10827">
          <div class="tgme_widget_message_text">06/18 미 증시, 옵션 만기일 영향과 반도체에 집중된 수급 영향에 상승<br/>다우 +0.14%, 나스닥 +1.91%, S&amp;P500 +1.09%</div>
          <a class="tgme_widget_message_date" href="https://t.me/ehdwl/10827"><time datetime="2026-06-18T20:32:08+00:00"></time></a>
        </div>
        <div class="tgme_widget_message" data-post="ehdwl/10828">
          <div class="tgme_widget_message_text">특징 종목: 마이크론, 엔비디아 상승 Vs. 스페이스X 하락 지속<br/>필라델피아 반도체 지수는 상승</div>
          <a class="tgme_widget_message_date" href="https://t.me/ehdwl/10828"><time datetime="2026-06-18T20:32:30+00:00"></time></a>
        </div>
        <div class="tgme_widget_message" data-post="ehdwl/10829">
          <div class="tgme_widget_message_text">원자력, 우라늄: 뉴스케일 파워, 계약 소식에 급등<br/>에너지 테마 강세</div>
          <a class="tgme_widget_message_date" href="https://t.me/ehdwl/10829"><time datetime="2026-06-18T20:32:30+00:00"></time></a>
        </div>
        <div class="tgme_widget_message" data-post="ehdwl/10830">
          <div class="tgme_widget_message_text">한국 증시 관련 수치: 야간선물 급등, FOMO<br/>나스닥과 반도체 수급 영향</div>
          <a class="tgme_widget_message_date" href="https://t.me/ehdwl/10830"><time datetime="2026-06-18T20:32:47+00:00"></time></a>
        </div>
        """

        posts = parse_telegram_public_channel_html(html, channel_username="ehdwl", base_url="https://t.me/s/ehdwl")
        candidate = latest_telegram_us_market_close_candidate(posts, today=date(2026, 6, 19))

        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.source_item_id, "ehdwl/10827")
        self.assertEqual(candidate.session_date, "2026-06-18")
        self.assertEqual(candidate.included_post_count, 4)
        self.assertIn("특징 종목", candidate.raw_summary)
        self.assertIn("원자력, 우라늄", candidate.raw_summary)
        self.assertIn("한국 증시 관련 수치", candidate.raw_summary)

    def test_telegram_market_close_refresh_marks_auto_source(self):
        import research_os_main as main
        from research_os.models import MarketCloseEntry, MarketCloseReviewResponse
        from research_os.settings import Settings
        from research_os.telegram_market_journal import TelegramMarketCloseCandidate

        settings = Settings(research_vault_dir="../research_vault")
        candidate = TelegramMarketCloseCandidate(
            source_item_id="ehdwl/100",
            source_url="https://t.me/ehdwl/100",
            source_title="Telegram @ehdwl: 06/16 미 증시, 반도체 하락",
            source_published_at="2026-06-17T01:20:00+00:00",
            session_date="2026-06-16",
            raw_summary="06/16 미 증시, 반도체 하락\n나스닥과 S&P500 하락",
            included_post_count=1,
        )
        response = MarketCloseReviewResponse(
            entry=MarketCloseEntry(
                entry_id="US-2026-06-16",
                market="US",
                session_date="2026-06-16",
                raw_summary=candidate.raw_summary,
                source_origin="telegram_auto",
                source_provider="telegram_ehdwl",
                source_title=candidate.source_title,
                sentiment="부정",
                risk_level="보통",
                regime="위험 관리",
            ),
            recent_regime_summary="US 최근 1회 누적",
        )

        with patch.object(main, "fetch_telegram_public_channel_posts", return_value=([], [])), \
            patch.object(main, "latest_telegram_us_market_close_candidate", return_value=candidate), \
            patch.object(main, "read_market_close_journal", return_value={"entries": []}), \
            patch.object(main, "read_json_store", return_value={}), \
            patch.object(main, "write_json_store") as write_store, \
            patch.object(main, "save_market_close_review", return_value=response) as save_review:
            result = main.refresh_telegram_us_market_close_journal(settings, force=False)

        request = save_review.call_args.args[0]
        self.assertEqual(request.market, "US")
        self.assertEqual(request.source_origin, "telegram_auto")
        self.assertEqual(request.source_provider, "telegram_ehdwl")
        self.assertEqual(request.source_title, candidate.source_title)
        self.assertEqual(result["entry"]["source_provider"], "telegram_ehdwl")
        written_state = write_store.call_args.args[1]
        self.assertEqual(written_state["status"], "success")
        self.assertEqual(written_state["source_item_id"], "ehdwl/100")
        self.assertEqual(written_state["session_date"], "2026-06-16")

    def test_telegram_market_close_refresh_skips_existing_session_date(self):
        import research_os_main as main
        from research_os.settings import Settings
        from research_os.telegram_market_journal import TelegramMarketCloseCandidate

        settings = Settings(research_vault_dir="../research_vault")
        candidate = TelegramMarketCloseCandidate(
            source_item_id="ehdwl/10818",
            source_url="https://t.me/ehdwl/10818",
            source_title="Telegram @ehdwl: 06/16 미 증시",
            source_published_at="2026-06-16T20:30:00+00:00",
            session_date="2026-06-16",
            raw_summary="06/16 미 증시",
            included_post_count=1,
        )
        existing = {"entries": [{"market": "US", "session_date": "2026-06-16"}]}

        with patch.object(main, "fetch_telegram_public_channel_posts", return_value=([], [])), \
            patch.object(main, "latest_telegram_us_market_close_candidate", return_value=candidate), \
            patch.object(main, "read_market_close_journal", return_value=existing), \
            patch.object(main, "read_json_store", return_value={}), \
            patch.object(main, "write_json_store") as write_store, \
            patch.object(main, "save_market_close_review") as save_review:
            result = main.refresh_telegram_us_market_close_journal(settings, force=False)

        self.assertEqual(result["status"], "skipped")
        save_review.assert_not_called()
        written_state = write_store.call_args.args[1]
        self.assertEqual(written_state["status"], "skipped_duplicate")
        self.assertEqual(written_state["source_published_at"], candidate.source_published_at)
        self.assertEqual(written_state["session_date"], "2026-06-16")

    def test_telegram_market_close_backfill_skips_existing_dates(self):
        import research_os_main as main
        from research_os.models import MarketCloseEntry, MarketCloseReviewResponse
        from research_os.settings import Settings
        from research_os.telegram_market_journal import TelegramMarketCloseCandidate

        settings = Settings(research_vault_dir="../research_vault")
        existing = {
            "entries": [
                {"market": "US", "session_date": "2026-06-11", "raw_summary": "already saved"}
            ]
        }
        candidates = [
            TelegramMarketCloseCandidate(
                source_item_id="ehdwl/10806",
                source_url="https://t.me/ehdwl/10806",
                source_title="Telegram @ehdwl: 06/11 미 증시",
                source_published_at="2026-06-11T20:30:00+00:00",
                session_date="2026-06-11",
                raw_summary="06/11 미 증시",
                included_post_count=1,
            ),
            TelegramMarketCloseCandidate(
                source_item_id="ehdwl/10818",
                source_url="https://t.me/ehdwl/10818",
                source_title="Telegram @ehdwl: 06/16 미 증시",
                source_published_at="2026-06-16T20:30:00+00:00",
                session_date="2026-06-16",
                raw_summary="06/16 미 증시",
                included_post_count=1,
            ),
        ]
        response = MarketCloseReviewResponse(
            entry=MarketCloseEntry(
                entry_id="US-2026-06-16",
                market="US",
                session_date="2026-06-16",
                raw_summary="06/16 미 증시",
                source_origin="telegram_auto",
                source_provider="telegram_ehdwl",
                source_title="Telegram @ehdwl: 06/16 미 증시",
                sentiment="중립",
                risk_level="보통",
                regime="혼조",
            ),
            recent_regime_summary="US 최근 1회 누적",
        )

        with patch.object(main, "fetch_telegram_public_channel_posts_backfill", return_value=([], [])), \
            patch.object(main, "telegram_us_market_close_candidates", return_value=candidates), \
            patch.object(main, "read_market_close_journal", return_value=existing), \
            patch.object(main, "read_json_store", return_value={}), \
            patch.object(main, "write_json_store") as write_store, \
            patch.object(main, "save_market_close_review", return_value=response) as save_review:
            result = main.backfill_telegram_us_market_close_journal(settings, max_pages=2)

        self.assertEqual(result["stored_count"], 1)
        self.assertEqual(result["skipped_existing_count"], 1)
        request = save_review.call_args.args[0]
        self.assertEqual(request.session_date, "2026-06-16")
        written_state = write_store.call_args.args[1]
        self.assertEqual(written_state["backfill_stored_count"], 1)
        self.assertEqual(written_state["backfill_skipped_existing_count"], 1)

    def test_portfolio_risk_warning_uses_company_name(self):
        import research_os_main as main
        from research_os.models import PortfolioHolding, PortfolioRiskScanRequest
        from research_os.settings import Settings

        holding = PortfolioHolding(
            ticker="360750",
            name="TIGER 미국S&P500 ETF",
            market_value=7000,
            weight=0.7,
        )
        warnings = main.build_portfolio_warnings(
            holdings=[holding],
            sector_concentration=[],
            theme_concentration=[],
            request=PortfolioRiskScanRequest(
                portfolio_name="테스트",
                holdings=[holding],
                max_single_position_weight=0.25,
            ),
            top_five_weight=0.7,
            settings=Settings(research_vault_dir="../research_vault"),
        )

        messages = "\n".join(item.message for item in warnings)
        self.assertIn("TIGER 미국S&P500 ETF", messages)
        self.assertNotIn("360750 비중", messages)

    def test_market_close_task_status_reads_scheduler_log(self):
        import research_os_main as main
        from research_os.settings import Settings

        test_tmp_root = PROJECT_ROOT / ".test-tmp"
        test_tmp_root.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=test_tmp_root) as temp_dir:
            vault_dir = Path(temp_dir) / "research_vault"
            settings = Settings(
                research_vault_dir=str(vault_dir),
                naver_market_close_auto_journal=True,
                naver_market_close_journal_time="08:30",
            )
            log_path = main.naver_market_close_journal_task_log_path(settings)
            log_path.write_text(
                "[2026-05-23T08:30:00+09:00] backend_ready\n"
                "[2026-05-23T08:30:01+09:00] market_close_journal_refresh: status=skipped\n",
                encoding="utf-8",
            )
            with (
                patch.object(main, "archive_duplicate_naver_market_close_reports", return_value={"duplicate_candidate_count": 0}),
                patch.object(main, "should_run_naver_market_close_journal", return_value=False),
            ):
                status = main.build_naver_market_close_task_status(settings, log_limit=1)

        self.assertEqual(status["status"], "ok")
        self.assertTrue(status["task_log"]["exists"])
        self.assertEqual(status["task_log"]["line_count"], 2)
        self.assertEqual(len(status["task_log"]["recent_lines"]), 1)
        self.assertIn("status=skipped", status["task_log"]["last_line"])

    def test_market_close_task_log_repairs_mojibake(self):
        import research_os_main as main
        from research_os import text_repair

        broken = "title=êµ­ë´ ì£¼ì ë§ê° ìí©"
        repaired = main.repair_mojibake_log_line(broken)

        self.assertIn("국내 주식 마감 시황", repaired)
        self.assertEqual(text_repair.repair_mojibake_log_line(broken), repaired)

    def test_recent_weekly_payload_repairs_mojibake(self):
        import research_os_main as main

        payload = {
            "target_digest": [
                {"target": "RFë¨¸í¸ë¦¬ì¼ì¦", "total": 1},
                {"target": "ì¼ììí", "total": 1},
            ],
            "category_groups": [
                {"label": "ìê¸/ëëë³´ì ", "target_names": ["ì±í¸ì ì"]}
            ],
        }

        repaired = main.repair_mojibake_payload(payload)

        self.assertEqual(repaired["target_digest"][0]["target"], "RF머트리얼즈")
        self.assertEqual(repaired["target_digest"][1]["target"], "삼양식품")
        self.assertEqual(repaired["category_groups"][0]["label"], "수급/대량보유")
        self.assertEqual(repaired["category_groups"][0]["target_names"], ["성호전자"])

    def test_market_close_task_status_flags_missing_log(self):
        import research_os_main as main
        from research_os.settings import Settings

        test_tmp_root = PROJECT_ROOT / ".test-tmp"
        test_tmp_root.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=test_tmp_root) as temp_dir:
            settings = Settings(
                research_vault_dir=str(Path(temp_dir) / "research_vault"),
                naver_market_close_auto_journal=True,
            )
            with (
                patch.object(main, "archive_duplicate_naver_market_close_reports", return_value={"duplicate_candidate_count": 0}),
                patch.object(main, "should_run_naver_market_close_journal", return_value=True),
            ):
                status = main.build_naver_market_close_task_status(settings)

        self.assertEqual(status["status"], "waiting_for_first_run")
        self.assertFalse(status["task_log"]["exists"])
        self.assertIn("첫 실행", status["next_action"])

    def test_naver_storage_path_accepts_research_vault_prefix(self):
        import research_os_main as main

        vault_dir = PROJECT_ROOT / "research_vault"
        resolved = main.normalize_naver_storage_path(
            vault_dir,
            "research_vault/MARKET-KR/sample.md",
        )

        self.assertEqual(resolved, vault_dir / "MARKET-KR" / "sample.md")
        self.assertEqual(
            main.normalize_naver_manifest_path("research_vault/MARKET-KR/sample.md"),
            "MARKET-KR/sample.md",
        )

    def test_naver_repair_updates_metadata_and_backfills_pdf_analysis(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        cache = {
            "updated_at": "old",
            "entries": {
                "old-key": {
                    "item_id": "old-key",
                    "url": "https://finance.naver.com/research/company_read.naver?nid=1",
                    "pdf_url": "https://example.com/report.pdf",
                    "nid": "1",
                    "title": "깨진 제목",
                    "broker": "깨진 증권사",
                    "published_at": "2026-05-22",
                    "ticker": "003230",
                    "company_name": "삼양식품",
                    "pdf_analysis": {"status": "unknown"},
                }
            },
        }
        fresh_item = {
            "item_id": "clean-key",
            "source": "naver_finance_research",
            "category": "종목분석",
            "scope": "company",
            "title": "삼양식품 목표가 상향",
            "broker": "테스트증권",
            "published_at": "2026-05-22",
            "url": "https://finance.naver.com/research/company_read.naver?nid=1",
            "pdf_url": "https://example.com/report.pdf",
            "ticker": "003230",
            "company_name": "삼양식품",
            "nid": "1",
        }
        enriched = {
            **fresh_item,
            "pdf_analysis": {
                "status": "success",
                "target_price": 120000,
                "investment_opinion": "BUY",
                "full_text_stored": False,
            },
        }
        written = {}

        with (
            patch.object(main, "read_naver_research_cache", return_value=cache),
            patch.object(main, "fetch_naver_research_items", return_value=([fresh_item], [])),
            patch.object(main, "apply_naver_research_priorities", return_value=[fresh_item]),
            patch.object(main, "enrich_naver_research_item_with_pdf_signals", return_value=enriched),
            patch.object(main, "build_naver_research_cache_status", return_value={"missing_storage_count": 0}),
            patch.object(main, "write_naver_research_cache", side_effect=lambda _settings, payload: written.update(payload)),
        ):
            result = main.repair_naver_research_cache(settings, pdf_backfill_limit=1)

        self.assertEqual(result["metadata_updated_count"], 1)
        self.assertEqual(result["pdf_backfilled_count"], 1)
        self.assertEqual(written["entries"]["old-key"]["title"], "삼양식품 목표가 상향")
        self.assertEqual(written["entries"]["old-key"]["pdf_analysis"]["status"], "success")
        self.assertFalse(written["entries"]["old-key"]["pdf_analysis"]["full_text_stored"])

    def test_naver_research_repair_saves_cache_entries_missing_storage(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(vault_dir=PROJECT_ROOT / ".test-tmp" / "naver-repair-storage")
        cache = {
            "entries": {
                "missing-storage": {
                    "title": "저장 경로 누락 리포트",
                    "category": "종목분석",
                    "published_at": "2026-05-08",
                    "url": "https://finance.naver.com/research/company_read.naver?nid=2",
                    "pdf_url": "https://example.com/report2.pdf",
                    "ticker": "007070",
                    "company_name": "GS리테일",
                    "nid": "2",
                    "pdf_analysis": {"status": "success"},
                }
            }
        }
        storage = SimpleNamespace(
            model_dump=lambda mode="json": {
                "relative_path": "research_vault/007070/007070-research-capture.md",
                "json_relative_path": "research_vault/007070/007070-research-capture.json",
            }
        )
        response = SimpleNamespace(storage=storage, linked_impact=None)
        written = {}

        with (
            patch.object(main, "read_naver_research_cache", return_value=cache),
            patch.object(main, "write_naver_research_cache", side_effect=lambda _settings, payload: written.update(payload)),
            patch.object(main, "build_naver_research_cache_status", return_value={"missing_storage_count": 0}),
            patch.object(main, "save_naver_research_item", return_value=response) as save_item,
        ):
            result = main.repair_naver_research_cache(
                settings,
                pdf_backfill_limit=0,
                refresh_metadata=False,
                save_result=True,
            )

        self.assertEqual(result["missing_storage_saved_count"], 1)
        self.assertEqual(save_item.call_count, 1)
        self.assertEqual(
            written["entries"]["missing-storage"]["storage"]["relative_path"],
            "research_vault/007070/007070-research-capture.md",
        )

    def test_naver_duplicate_market_close_reports_are_soft_archived(self):
        import research_os_main as main
        from research_os.settings import Settings

        test_tmp_root = PROJECT_ROOT / ".test-tmp"
        test_tmp_root.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=test_tmp_root) as temp_dir:
            vault_dir = Path(temp_dir) / "research_vault"
            settings = Settings(research_vault_dir=str(vault_dir))
            payload = {
                "entry": {
                    "market": "KR",
                    "session_date": "2026-05-22",
                    "raw_summary": "국내 주식 마감 시황",
                },
                "source_url_processing": {
                    "url": "https://finance.naver.com/research/market_info_read.naver?nid=1",
                    "title": "국내 주식 마감 시황",
                },
            }
            for index in range(2):
                main.save_research_markdown(
                    vault_dir=vault_dir,
                    ticker="MARKET-KR",
                    report_type="market-close-review",
                    markdown=f"# 중복 테스트 {index}",
                    structured_payload=payload,
                    manifest_entry={
                        "summary": "KR 2026-05-22 폐장 리뷰",
                        "market": "KR",
                        "session_date": "2026-05-22",
                    },
                    report_date=date(2026, 5, 22),
                )

            preview = main.archive_duplicate_naver_market_close_reports(settings, apply=False)
            self.assertEqual(preview["duplicate_candidate_count"], 1)
            self.assertEqual(preview["archived_count"], 0)

            with patch.object(main, "upsert_research_memory_document", return_value=None):
                applied = main.archive_duplicate_naver_market_close_reports(settings, apply=True)
            self.assertEqual(applied["policy"], "soft_archive")
            self.assertEqual(applied["archived_count"], 1)

            visible = main.list_research_memory_files("MARKET-KR", vault_dir, include_archived=False)
            all_files = main.list_research_memory_files("MARKET-KR", vault_dir, include_archived=True)
            self.assertEqual(len(visible), 1)
            self.assertEqual(len(all_files), 2)
            self.assertEqual(sum(1 for file in all_files if file.archived), 1)

    def test_save_research_markdown_can_overwrite_existing_file_name(self):
        import research_os_main as main

        test_tmp_root = PROJECT_ROOT / ".test-tmp"
        test_tmp_root.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=test_tmp_root) as temp_dir:
            vault_dir = Path(temp_dir) / "research_vault"
            first = main.save_research_markdown(
                vault_dir=vault_dir,
                ticker="MARKET-US",
                report_type="market-close-review",
                markdown="# first",
                structured_payload={"version": 1},
                report_date=date(2026, 6, 30),
                overwrite_existing=True,
            )
            second = main.save_research_markdown(
                vault_dir=vault_dir,
                ticker="MARKET-US",
                report_type="market-close-review",
                markdown="# second",
                structured_payload={"version": 2},
                report_date=date(2026, 6, 30),
                overwrite_existing=True,
            )

            self.assertEqual(first.file_name, second.file_name)
            self.assertEqual(first.json_file_name, second.json_file_name)
            duplicate_path = vault_dir / "MARKET-US" / "MARKET-US-market-close-review-2026-06-30-002.md"
            self.assertFalse(duplicate_path.exists())
            self.assertEqual((vault_dir / "MARKET-US" / first.file_name).read_text(encoding="utf-8"), "# second")

    def test_duplicate_market_journal_cleanup_keeps_state_referenced_file(self):
        from tools import cleanup_duplicate_market_journals as cleanup

        test_tmp_root = PROJECT_ROOT / ".test-tmp"
        test_tmp_root.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=test_tmp_root) as temp_dir:
            root = Path(temp_dir)
            (root / "backend").mkdir()
            (root / "backend" / "research_os_main.py").write_text("# marker", encoding="utf-8")
            market_dir = root / "research_vault" / "MARKET-US"
            system_dir = root / "research_vault" / "_system"
            market_dir.mkdir(parents=True)
            system_dir.mkdir(parents=True)
            names = [
                "MARKET-US-market-close-review-2026-06-30.md",
                "MARKET-US-market-close-review-2026-06-30-002.md",
                "MARKET-US-market-close-review-2026-06-30-003.md",
                "MARKET-US-market-close-review-2026-06-30-news-inbox.md",
            ]
            for name in names:
                (market_dir / name).write_text(f"# {name}", encoding="utf-8")
                (market_dir / name.replace(".md", ".json")).write_text(
                    json.dumps(
                        {
                            "entry": {
                                "entry_id": "US-2026-06-30",
                                "market": "US",
                                "session_date": "2026-06-30",
                                "updated_at": f"2026-07-02T00:0{names.index(name)}:00+09:00",
                            }
                        },
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
            (system_dir / "telegram_market_close_journal_state.json").write_text(
                json.dumps(
                    {
                        "storage": {
                            "relative_path": "research_vault/MARKET-US/MARKET-US-market-close-review-2026-06-30-003.md",
                            "json_relative_path": "research_vault/MARKET-US/MARKET-US-market-close-review-2026-06-30-003.json",
                        }
                    }
                ),
                encoding="utf-8",
            )
            (root / "research_vault" / "manifest.json").write_text("[]", encoding="utf-8")

            plan = cleanup.build_cleanup_plan(root)

            self.assertEqual(plan["duplicate_group_count"], 1)
            self.assertEqual(plan["duplicate_candidate_count"], 2)
            self.assertEqual(plan["groups"][0]["keep_file"], "MARKET-US-market-close-review-2026-06-30-003.md")

            applied = cleanup.apply_cleanup(root, plan)
            self.assertEqual(applied["archived_count"], 2)
            kept_payload = json.loads((market_dir / "MARKET-US-market-close-review-2026-06-30-003.json").read_text(encoding="utf-8"))
            archived_payload = json.loads((market_dir / "MARKET-US-market-close-review-2026-06-30.json").read_text(encoding="utf-8"))
            self.assertNotEqual(kept_payload.get("status"), "archived")
            self.assertEqual(archived_payload["status"], "archived")
            manifest = json.loads((root / "research_vault" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(sum(1 for item in manifest if item.get("status") == "archived"), 2)

    def test_naver_holding_interest_impact_marks_positive_linked_report(self):
        import research_os_main as main

        impact = main.build_naver_holding_interest_impact(
            {
                "company_name": "삼양식품",
                "priority": {"score": 100, "reasons": ["보유종목"]},
                "pdf_analysis": {
                    "investment_opinion": "Buy",
                    "upside_percent": 21.5,
                },
            }
        )

        self.assertEqual(impact["impact"], "긍정")
        self.assertTrue(impact["linked_to_user_universe"])
        self.assertIn("삼양식품", impact["affected"])


class PortfolioRiskStorageTests(unittest.TestCase):
    def test_portfolio_risk_storage_preserves_manifest_payload(self):
        from research_os import portfolio_risk_storage
        from research_os.research_memory import ResearchStorageInfo

        class DumpItem(SimpleNamespace):
            def model_dump(self, mode=None):
                return dict(self.__dict__)

        save_calls = []

        def fake_save_research_markdown(**kwargs):
            save_calls.append(kwargs)
            return ResearchStorageInfo(
                file_name=f"{kwargs['ticker']}-{kwargs['report_type']}.md",
                relative_path=f"research_vault/{kwargs['ticker']}/{kwargs['ticker']}-{kwargs['report_type']}.md",
                absolute_path=str(kwargs['vault_dir'] / kwargs['ticker'] / f"{kwargs['ticker']}-{kwargs['report_type']}.md"),
            )

        runtime = SimpleNamespace(
            current_storage_date=lambda: date(2026, 6, 13),
            normalize_ticker=lambda value: str(value).strip().upper().replace(" ", "-"),
            portfolio_store_key=lambda value: str(value).strip().upper().replace(" ", "-"),
            render_portfolio_risk_markdown=lambda scan, storage_date: f"portfolio risk {storage_date.isoformat()}",
            render_reinforcement_policy_markdown=lambda response, portfolio_value, report_date: f"policy {portfolio_value:.0f} {report_date.isoformat()}",
            resolve_vault_dir=lambda value: Path(value),
            save_research_markdown=fake_save_research_markdown,
        )
        vault_dir = PROJECT_ROOT / ".test-tmp" / "portfolio_risk_storage_vault"
        scan = SimpleNamespace(
            sector_concentration=[DumpItem(name="반도체", weight=0.62)],
            theme_concentration=[DumpItem(name="AI", weight=0.48)],
            warnings=[DumpItem(type="single_position", message="집중도 높음")],
            storage=None,
            model_dump=lambda mode=None: {"risk_score": 72},
        )
        policy_response = SimpleNamespace(
            allocation_adjustments=[DumpItem(ticker="005930"), DumpItem(ticker="000660")],
            objective="risk_adjusted_return",
            risk_profile="balanced",
            storage=None,
            model_dump=lambda mode=None: {"objective": "risk_adjusted_return"},
        )

        saved = portfolio_risk_storage.save_portfolio_risk_scan(
            runtime,
            scan=scan,
            portfolio_name="core portfolio",
            portfolio_value=1234567.891,
            risk_score=72,
            top_five_weight=0.83,
            settings=SimpleNamespace(research_vault_dir=str(vault_dir)),
        )

        self.assertEqual(saved.storage.file_name, "CORE-PORTFOLIO-portfolio-risk-scan.md")
        self.assertEqual(save_calls[0]["report_type"], "portfolio-risk-scan")
        self.assertEqual(save_calls[0]["ticker"], "CORE-PORTFOLIO")
        self.assertIn("리스크 점수 72/100", save_calls[0]["manifest_entry"]["summary"])
        self.assertEqual(save_calls[0]["manifest_entry"]["portfolio_value"], 1234567.89)
        self.assertEqual(save_calls[0]["manifest_entry"]["top_five_weight"], 0.83)
        self.assertEqual(save_calls[0]["manifest_entry"]["sector_concentration"][0]["name"], "반도체")
        self.assertEqual(save_calls[0]["manifest_entry"]["theme_concentration"][0]["name"], "AI")
        self.assertEqual(save_calls[0]["manifest_entry"]["warnings"][0]["type"], "single_position")

        saved_policy = portfolio_risk_storage.save_reinforcement_portfolio_policy(
            runtime,
            response=policy_response,
            portfolio_name="core portfolio",
            portfolio_value=1234567.891,
            settings=SimpleNamespace(research_vault_dir=str(vault_dir)),
        )

        self.assertEqual(saved_policy.storage.file_name, "CORE-PORTFOLIO-reinforcement-portfolio-optimizer.md")
        self.assertEqual(save_calls[1]["report_type"], "reinforcement-portfolio-optimizer")
        self.assertEqual(save_calls[1]["ticker"], "CORE-PORTFOLIO")
        self.assertIn("2개 조정 후보", save_calls[1]["manifest_entry"]["summary"])
        self.assertEqual(save_calls[1]["manifest_entry"]["portfolio_name"], "core portfolio")
        self.assertEqual(save_calls[1]["manifest_entry"]["objective"], "risk_adjusted_return")
        self.assertEqual(save_calls[1]["manifest_entry"]["risk_profile"], "balanced")


class PortfolioPolicyModuleTests(unittest.TestCase):
    def test_policy_adjustment_applies_risk_limits(self):
        from research_os import portfolio_policy
        from research_os.models import PortfolioHolding

        adjustment = portfolio_policy.policy_adjustment_for_holding(
            PortfolioHolding(
                ticker="PL",
                weight=0.3,
                unrealized_return=-0.22,
                sector="Space",
                theme_tags=["AI", "Space"],
            ),
            max_position_weight=0.2,
            risk_profile="balanced",
            market_tags=["AI"],
        )

        self.assertEqual(adjustment.ticker, "PL")
        self.assertEqual(adjustment.action, "리스크 축소")
        self.assertLessEqual(adjustment.suggested_weight, 0.2)
        self.assertIn("손실 확대", adjustment.rationale)

    def test_run_policy_builds_response_without_saving(self):
        from research_os import portfolio_policy
        from research_os.models import (
            PortfolioHolding,
            ReinforcementPortfolioOptimizationRequest,
            SavedPortfolio,
        )

        holding = PortfolioHolding(
            ticker="OTLY",
            weight=0.05,
            unrealized_return=0.12,
            sector="Consumer",
            theme_tags=["AI", "소비"],
        )
        runtime = SimpleNamespace(
            SavedPortfolio=SavedPortfolio,
            infer_policy_market_regime=lambda market_state, settings: ("상승/위험중립", ["AI"]),
            normalize_portfolio_holdings=lambda holdings, portfolio_value: (list(holdings), 1000.0),
            portfolio_risk_storage_runtime=lambda: SimpleNamespace(),
            portfolio_store_key=lambda value: str(value).strip().upper(),
            read_portfolio_store=lambda settings: {},
        )
        request = ReinforcementPortfolioOptimizationRequest(
            portfolio_name="test",
            holdings=[holding],
            market_state="AI 강세",
            max_position_weight=0.2,
            save_result=False,
        )

        response = portfolio_policy.run_reinforcement_portfolio_policy(
            runtime,
            request,
            SimpleNamespace(research_vault_dir=str(PROJECT_ROOT / ".test-tmp")),
        )

        self.assertEqual(response.learning_mode, "offline_policy_scaffold")
        self.assertFalse(response.saved_to_research_memory)
        self.assertIn("시장 상태: 상승/위험중립", response.state_features)
        self.assertEqual(response.allocation_adjustments[0].ticker, "OTLY")
        self.assertEqual(response.allocation_adjustments[0].action, "관찰 후 증액 후보")


class AnalysisContextModuleTests(unittest.TestCase):
    def test_collect_workspace_context_adds_reports_snapshot_and_rag(self):
        from research_os import analysis_context
        from research_os.models import InjectedDataPoint

        with TemporaryDirectory() as temp_dir:
            vault_dir = Path(temp_dir)
            ticker_dir = vault_dir / "OTLY"
            ticker_dir.mkdir(parents=True)
            (ticker_dir / "OTLY-test.md").write_text("memo", encoding="utf-8")

            def fake_search(_vault_dir, ticker, limit, refresh_index):
                if ticker == "OTLY":
                    return {
                        "documents": [
                            {
                                "source_date": "2026-06-18",
                                "report_type": "memo",
                                "summary": "RAG summary",
                                "source_relative_path": "research_vault/OTLY/memo.md",
                                "confidence": 0.9,
                            }
                        ]
                    }
                if ticker == "MARKET":
                    return {"documents": [{"source_date": "2026-06-18", "summary": "market context"}]}
                return {"documents": []}

            runtime = SimpleNamespace(
                current_storage_date=lambda: date(2026, 6, 18),
                read_ticker_thesis_snapshot=lambda _vault_dir, _ticker: {
                    "thesis_summary": "thesis",
                    "bull_triggers": ["margin"],
                    "bear_triggers": ["demand"],
                    "invalidation_conditions": ["cash"],
                    "source_date": "2026-06-17",
                    "source_relative_path": "research_vault/OTLY/thesis.json",
                    "confidence": 0.8,
                },
                search_research_memory_documents=fake_search,
            )
            provided = [InjectedDataPoint(source_type="user_memo", label="seed", value="seed", confidence=1.0)]

            result = analysis_context.collect_workspace_context(runtime, "OTLY", vault_dir, provided)

        labels = [item.label for item in result]
        self.assertEqual(labels[0], "seed")
        self.assertIn("linked_workspace_reports", labels)
        self.assertIn("latest_thesis_snapshot", labels)
        self.assertIn("rag_memory_document_1", labels)
        self.assertIn("rag_cross_scope_market", labels)
        self.assertTrue(any("저장 리포트 1개" in item.value for item in result))

    def test_collect_analysis_input_data_adds_profile_provider_and_mock_note(self):
        from research_os import analysis_context
        from research_os.models import InjectedDataPoint

        provider_point = InjectedDataPoint(
            source_type="market_price",
            label="last_price",
            value="10",
            confidence=0.7,
        )
        runtime = SimpleNamespace(
            build_ticker_profile=lambda ticker, settings, refresh_external=False: SimpleNamespace(
                company_name="Oatly",
                exchange="NASDAQ",
                business_context="plant milk",
                watch_kpis=["margin"],
            ),
            current_storage_date=lambda: date(2026, 6, 18),
            fetch_nps_institutional_context=lambda ticker, company_name, settings: [
                InjectedDataPoint(source_type="financial_data", label="nps", value=company_name, confidence=0.6)
            ],
            get_analysis_data_provider=lambda settings: SimpleNamespace(
                fetch_analysis_context=lambda ticker: [provider_point]
            ),
            latest_earnings_profile_for_ticker=lambda ticker, settings, refresh_external=False: {
                "earnings_report_date": "2026-06-17",
                "source_url": "https://example.com/earnings",
            },
            latest_earnings_profile_summary=lambda latest: "earnings summary",
            verify_ticker_symbol=lambda ticker, settings: SimpleNamespace(verified=True, verification_source="registry"),
        )
        settings = SimpleNamespace(auto_inject_analysis_data=True, data_provider_mode="mock")
        provided = [InjectedDataPoint(source_type="user_memo", label="memo", value="memo", confidence=1.0)]

        result = analysis_context.collect_analysis_input_data(
            runtime,
            ticker="OTLY",
            provided_data=provided,
            auto_inject_data=True,
            settings=settings,
        )

        labels = [item.label for item in result]
        self.assertIn("official_company_profile", labels)
        self.assertIn("official_latest_earnings_profile", labels)
        self.assertIn("last_price", labels)
        self.assertIn("nps", labels)
        self.assertIn("data_provider_limitation", labels)
        self.assertEqual(labels[-1], "memo")


class AnalysisLabelsModuleTests(unittest.TestCase):
    def test_analysis_labels_translate_values_and_build_keys(self):
        from research_os import analysis_labels
        from research_os.models import DataSourceType

        runtime = SimpleNamespace(normalize_ticker=lambda value: str(value).strip().upper().replace(" ", "-"))

        self.assertEqual(analysis_labels.enum_or_str_value(DataSourceType.NEWS), "news")
        self.assertEqual(analysis_labels.translate_source_type_label(DataSourceType.ANALYST_REPORT), "애널리스트 리포트")
        self.assertEqual(analysis_labels.translate_data_label("market_cap"), "시가총액")
        self.assertEqual(analysis_labels.translate_trade_style_label("swing"), "단기 보유(며칠~몇 주)")
        self.assertEqual(analysis_labels.sector_research_key(runtime, "한국", "균형형"), "SECTOR-KR-BALANCED")
        self.assertEqual(
            analysis_labels.compounder_research_key(runtime, "US", "technology", "quality growth"),
            "COMPOUNDER-US-TECH-QUALITY-GROWTH",
        )

    def test_analysis_labels_build_checklist_statuses(self):
        from research_os import analysis_labels

        statuses = analysis_labels.build_checklist_statuses(
            ["moat", "risk"],
            [("moat", "경쟁 우위"), ("risk", "리스크"), ("valuation", "밸류에이션")],
        )

        self.assertEqual([item.key for item in statuses], ["moat", "risk", "valuation"])
        self.assertEqual([item.completed for item in statuses], [True, True, False])


class AnalysisModuleStorageTests(unittest.TestCase):
    def test_analysis_module_storage_saves_analysis_module_manifest_payloads(self):
        from research_os import analysis_module_storage
        from research_os.research_memory import ResearchStorageInfo

        class DumpItem:
            def __init__(self, **payload):
                self.payload = payload

            def model_dump(self, mode=None):
                return dict(self.payload)

        class FakeReport(SimpleNamespace):
            def model_dump(self, mode=None):
                return dict(self.__dict__)

        class PriceItem(SimpleNamespace):
            def model_dump(self, mode=None):
                return dict(self.__dict__)

        save_calls = []
        rag_calls = []
        snapshot_calls = []
        dossier_calls = []
        error_logs = []

        def fake_save_research_markdown(**kwargs):
            save_calls.append(kwargs)
            return ResearchStorageInfo(
                file_name=f"{kwargs['ticker']}-{kwargs['report_type']}.md",
                relative_path=f"research_vault/{kwargs['ticker']}/{kwargs['ticker']}-{kwargs['report_type']}.md",
                absolute_path=str(kwargs['vault_dir'] / kwargs['ticker'] / f"{kwargs['ticker']}-{kwargs['report_type']}.md"),
            )

        runtime = SimpleNamespace(
            append_jsonl=lambda path, payload: error_logs.append({"path": path, "payload": payload}),
            current_storage_date=lambda: date(2026, 6, 13),
            current_storage_timestamp=lambda: "2026-06-13T09:00:00",
            manifest_with_ticker_verification=lambda ticker, entry: {**entry, "ticker": ticker, "verified": True},
            read_manifest=lambda vault_dir: [
                {
                    "file_name": "005930-collaborative-team-report.md",
                    "ticker": "005930",
                    "relative_path": "research_vault/005930/005930-collaborative-team-report.md",
                }
            ],
            render_checklist_markdown=lambda assessment, storage_date: f"checklist {storage_date.isoformat()}",
            render_earnings_reaction_markdown=lambda reaction, storage_date: f"earnings {storage_date.isoformat()}",
            render_institutional_markdown=lambda analysis, storage_date: f"institutional {storage_date.isoformat()}",
            render_sector_opportunity_markdown=lambda report, storage_date: f"sector {storage_date.isoformat()}",
            render_long_term_compounder_markdown=lambda report, storage_date: f"compounder {storage_date.isoformat()}",
            render_naver_chart_analysis_markdown=lambda analysis, storage_date: f"chart {storage_date.isoformat()}",
            render_smart_trade_markdown=lambda setup, storage_date: f"smart trade {storage_date.isoformat()}",
            render_team_analysis_markdown=lambda report, storage_date: f"team {storage_date.isoformat()}",
            resolve_vault_dir=lambda value: Path(value),
            save_research_markdown=fake_save_research_markdown,
            synthesize_and_save_dossier=lambda *args, **kwargs: dossier_calls.append({"args": args, "kwargs": kwargs}),
            ticker_company_name=lambda ticker: "삼성전자",
            upsert_research_memory_document=lambda **kwargs: rag_calls.append(kwargs),
            upsert_ticker_thesis_snapshot=lambda **kwargs: snapshot_calls.append(kwargs),
            user_state_dir=lambda settings: PROJECT_ROOT / ".test-tmp" / "state",
        )
        vault_dir = PROJECT_ROOT / ".test-tmp" / "analysis_storage_vault"
        sector_report = FakeReport(
            macro_summary="반도체 중심",
            period="3개월",
            region="KR",
            style="균형형",
            ranked_sectors=[DumpItem(sector="AI", score=90) for _ in range(4)],
            recommended_companies=[DumpItem(company_name="삼성전자")],
            sector_trends=[DumpItem(sector="AI", trend_label="강세")],
            sector_leaders=[DumpItem(company_name=f"리더{i}") for i in range(12)],
            analyst_report=["리포트"],
            watch_items=["실적"],
            key_risks=["변동성"],
            storage=None,
        )
        compounder_report = FakeReport(
            summary="복리 후보",
            screening_criteria="매출 성장",
            region="KR",
            sector="전체",
            style="퀄리티 성장",
            min_market_cap=3000,
            max_market_cap=None,
            candidates=[DumpItem(company_name="SK하이닉스")],
            next_actions=["추적"],
            storage=None,
        )
        checklist_assessment = FakeReport(
            readiness_summary="준비도 높음",
            completion_rate=0.875,
            readiness_level="높음",
            injected_data=[DumpItem(label="source")],
            next_steps=["시나리오 확인"],
            storage=None,
        )
        team_report = FakeReport(
            executive_summary="7개 스킬 종합",
            data_quality=SimpleNamespace(data_quality="높음", source_confidence=0.9),
            injected_data=[DumpItem(label="source")],
            consensus="강세 우위",
            conflicts=[DumpItem(type="valuation")],
            investment_thesis=DumpItem(summary="장기 논거"),
            watch_items=[DumpItem(label="실적")],
            invalidation_conditions=["마진 훼손"],
            storage=None,
            dossier_refresh_status=None,
        )
        chart_analysis = {
            "company_name": "삼성전자",
            "as_of": "2026-06-13",
            "overall_signal": "상승 추세 우위",
            "trade_bias": "눌림 매수",
            "latest_indicators": {"rsi14": 58.2},
            "support_resistance": {"recent_20d_support": 70000},
        }
        institutional_analysis = FakeReport(
            executive_summary="기관급 분석 요약",
            injected_data=[DumpItem(label="source-a"), DumpItem(label="source-b")],
            key_risks=["밸류에이션"],
            bull_case=SimpleNamespace(watch_items=["매출 성장률"]),
            base_case=SimpleNamespace(watch_items=["컨센서스 변화"]),
            bear_case=SimpleNamespace(watch_items=["마진 압박"]),
            storage=None,
        )
        smart_trade_setup = FakeReport(
            current_price=71000.0,
            style="swing",
            risk_tolerance="moderate",
            market_structure="상승 추세",
            setup_quality="양호",
            entry_zone=[PriceItem(price=70000.0, label="1차")],
            stop_loss=PriceItem(price=68000.0, label="손절"),
            targets=[PriceItem(price=76000.0, label="1차 목표")],
            risk_per_share=2000.0,
            storage=None,
        )
        earnings_reaction = FakeReport(
            headline_assessment="실적 반응 양호",
            quarter="2026Q1",
            official_latest_quarter="2026Q1",
            official_latest_earnings_report_date="2026-05-01",
            earnings_calendar_source="profile",
            earnings_reference_status="official",
            earnings_report_date="2026-05-01",
            previous_earnings_date="2026-02-01",
            previous_earnings_key_takeaways=["마진 개선"],
            next_earnings_date="2026-08-01",
            next_earnings_guidance="AI 수요 확인",
            price_reaction="상승",
            reaction_type="beat",
            sentiment_shift="positive",
            guidance_assessment="상향",
            evidence_status="sufficient",
            missing_inputs=[],
            watch_before_next_earnings=["가이던스"],
            thesis_implications=["논거 강화"],
            storage=None,
        )

        saved_sector = analysis_module_storage.save_sector_opportunity_report(
            runtime,
            report=sector_report,
            research_key="SECTOR-KR-BALANCED",
            vault_dir=vault_dir,
        )
        saved_compounder = analysis_module_storage.save_long_term_compounder_report(
            runtime,
            report=compounder_report,
            research_key="COMPOUNDER-KR-ALL-QUALITY",
            vault_dir=vault_dir,
        )
        saved_checklist = analysis_module_storage.save_research_checklist_assessment(
            runtime,
            assessment=checklist_assessment,
            ticker="005930",
            vault_dir=vault_dir,
        )
        saved_team = analysis_module_storage.save_collaborative_team_report(
            runtime,
            report=team_report,
            ticker="005930",
            vault_dir=vault_dir,
            settings=SimpleNamespace(),
            refresh_dossier=True,
        )
        saved_chart = analysis_module_storage.save_naver_chart_analysis(
            runtime,
            analysis=chart_analysis,
            code="005930",
            settings=SimpleNamespace(research_vault_dir=str(vault_dir)),
        )
        saved_institutional = analysis_module_storage.save_institutional_stock_breakdown(
            runtime,
            analysis=institutional_analysis,
            ticker="005930",
            vault_dir=vault_dir,
        )
        saved_smart_trade = analysis_module_storage.save_smart_trade_setup(
            runtime,
            setup=smart_trade_setup,
            ticker="005930",
            vault_dir=vault_dir,
        )
        saved_earnings = analysis_module_storage.save_earnings_reaction(
            runtime,
            reaction=earnings_reaction,
            ticker="005930",
            vault_dir=vault_dir,
        )

        self.assertEqual(saved_sector.storage.file_name, "SECTOR-KR-BALANCED-sector-opportunity.md")
        self.assertEqual(saved_compounder.storage.file_name, "COMPOUNDER-KR-ALL-QUALITY-long-term-compounder.md")
        self.assertEqual(save_calls[0]["report_type"], "sector-opportunity")
        self.assertEqual(save_calls[0]["manifest_entry"]["summary"], "반도체 중심")
        self.assertEqual(len(save_calls[0]["manifest_entry"]["top_sectors"]), 3)
        self.assertEqual(len(save_calls[0]["manifest_entry"]["sector_leaders"]), 10)
        self.assertEqual(save_calls[1]["report_type"], "long-term-compounder")
        self.assertEqual(save_calls[1]["manifest_entry"]["screening_criteria"], "매출 성장")
        self.assertEqual(save_calls[1]["manifest_entry"]["candidates"][0]["company_name"], "SK하이닉스")
        self.assertEqual(saved_checklist.storage.file_name, "005930-research-checklist.md")
        self.assertEqual(save_calls[2]["report_type"], "research-checklist")
        self.assertEqual(save_calls[2]["manifest_entry"]["readiness_level"], "높음")
        self.assertEqual(save_calls[2]["manifest_entry"]["source_count"], 1)
        self.assertTrue(save_calls[2]["manifest_entry"]["verified"])
        self.assertEqual(saved_team.storage.file_name, "005930-collaborative-team-report.md")
        self.assertEqual(save_calls[3]["report_type"], "collaborative-team-report")
        self.assertEqual(save_calls[3]["manifest_entry"]["ticker"], "005930")
        self.assertEqual(save_calls[3]["manifest_entry"]["source_confidence"], 0.9)
        self.assertTrue(save_calls[3]["manifest_entry"]["verified"])
        self.assertEqual(rag_calls[0]["entry"]["file_name"], "005930-collaborative-team-report.md")
        self.assertEqual(snapshot_calls[0]["company_name"], "삼성전자")
        self.assertEqual(snapshot_calls[0]["source_entry"]["type"], "collaborative-team-report")
        self.assertEqual(snapshot_calls[0]["source_entry"]["file_name"], "005930-collaborative-team-report.md")
        self.assertEqual(len(dossier_calls), 1)
        self.assertEqual(saved_team.dossier_refresh_status, "refreshed")
        self.assertEqual(saved_chart["storage"]["file_name"], "005930-chart-analysis.md")
        self.assertEqual(save_calls[4]["report_type"], "chart-analysis")
        self.assertEqual(save_calls[4]["manifest_entry"]["company_name"], "삼성전자")
        self.assertEqual(save_calls[4]["manifest_entry"]["overall_signal"], "상승 추세 우위")
        self.assertEqual(save_calls[4]["manifest_entry"]["latest_indicators"]["rsi14"], 58.2)
        self.assertEqual(saved_institutional.storage.file_name, "005930-institutional-stock-breakdown.md")
        self.assertEqual(save_calls[5]["report_type"], "institutional-stock-breakdown")
        self.assertEqual(save_calls[5]["manifest_entry"]["summary"], "기관급 분석 요약")
        self.assertEqual(save_calls[5]["manifest_entry"]["source_count"], 2)
        self.assertEqual(save_calls[5]["manifest_entry"]["key_risks"], ["밸류에이션"])
        self.assertEqual(
            save_calls[5]["manifest_entry"]["watch_items"],
            ["매출 성장률", "컨센서스 변화", "마진 압박"],
        )
        self.assertTrue(save_calls[5]["manifest_entry"]["verified"])
        self.assertEqual(saved_smart_trade.storage.file_name, "005930-smart-trade-setup.md")
        self.assertEqual(save_calls[6]["report_type"], "smart-trade-setup")
        self.assertIn("1차 진입 70000.00", save_calls[6]["manifest_entry"]["summary"])
        self.assertEqual(save_calls[6]["manifest_entry"]["current_price"], 71000.0)
        self.assertEqual(save_calls[6]["manifest_entry"]["setup_quality"], "양호")
        self.assertEqual(save_calls[6]["manifest_entry"]["entry_zone"][0]["price"], 70000.0)
        self.assertEqual(save_calls[6]["manifest_entry"]["stop_loss"]["price"], 68000.0)
        self.assertEqual(save_calls[6]["manifest_entry"]["targets"][0]["price"], 76000.0)
        self.assertTrue(save_calls[6]["manifest_entry"]["verified"])
        self.assertEqual(saved_earnings.storage.file_name, "005930-earnings-reaction.md")
        self.assertEqual(save_calls[7]["report_type"], "earnings-reaction")
        self.assertEqual(save_calls[7]["manifest_entry"]["summary"], "실적 반응 양호")
        self.assertEqual(save_calls[7]["manifest_entry"]["quarter"], "2026Q1")
        self.assertEqual(save_calls[7]["manifest_entry"]["earnings_calendar_source"], "profile")
        self.assertEqual(save_calls[7]["manifest_entry"]["price_reaction"], "상승")
        self.assertEqual(save_calls[7]["manifest_entry"]["evidence_status"], "sufficient")
        self.assertEqual(save_calls[7]["manifest_entry"]["thesis_implications"], ["논거 강화"])
        self.assertTrue(save_calls[7]["manifest_entry"]["verified"])
        self.assertEqual(error_logs, [])


class CompounderPresentationTests(unittest.TestCase):
    def test_compounder_report_uses_company_names_in_human_output(self):
        import research_os_main as main
        from research_os.models import LongTermCompounderRequest

        request = LongTermCompounderRequest(
            screening_criteria="강력한 매출 성장, 높은 매출총이익률, 높은 FCF 마진",
            min_market_cap=3000,
            region="KR",
            sector="전체",
            style="퀄리티 성장",
            save_result=False,
        )

        report = main.build_long_term_compounder_report(request, injected_data=[])
        rendered = main.render_long_term_compounder_markdown(report, date(2026, 5, 20))

        self.assertIn("SK하이닉스", report.summary)
        self.assertIn("삼성바이오로직스", rendered)
        self.assertNotIn("000660.KS", report.summary)
        self.assertNotIn("207940.KS", rendered)

    def test_compounder_request_defaults_to_korea(self):
        from research_os.models import LongTermCompounderRequest

        request = LongTermCompounderRequest(
            screening_criteria="강력한 매출 성장과 높은 FCF 마진",
        )

        self.assertEqual(request.region, "KR")


class SectorOpportunityPresentationTests(unittest.TestCase):
    def test_sector_markdown_uses_company_names_in_human_sections(self):
        import research_os_main as main
        from research_os.models import (
            SectorCompanyCandidate,
            SectorLeaderCandidate,
            SectorOpportunity,
            SectorOpportunityResponse,
            SectorPeerComparison,
            SectorTrendInsight,
        )

        samsung = SectorCompanyCandidate(
            ticker="005930.KS",
            company_name="삼성전자",
            sector="반도체/AI 인프라",
            thesis="AI 메모리와 파운드리 회복을 함께 확인합니다.",
            catalysts=["AI 투자"],
            risks=["가격 변동"],
            fit_score=82,
        )
        sk_hynix = SectorLeaderCandidate(
            ticker="000660.KS",
            company_name="SK하이닉스",
            sector="반도체/AI 인프라",
            source="테스트",
            leader_score=88,
            thesis="HBM 수요가 핵심입니다.",
            catalysts=["HBM"],
            risks=["공급 경쟁"],
            next_checkpoints=["실적"],
        )
        report = SectorOpportunityResponse(
            research_key="SECTOR-KR-BALANCED",
            macro_environment="환율과 반도체 수급을 점검합니다.",
            period="3개월",
            region="KR",
            style="균형형",
            focus_theme="반도체",
            macro_summary="반도체 중심으로 확인합니다.",
            industry_overview=["반도체 업황 확인"],
            competitive_landscape=["메모리 경쟁력 확인"],
            peer_comparison=[
                SectorPeerComparison(
                    ticker="005930.KS",
                    company_name="삼성전자",
                    sector="반도체/AI 인프라",
                    role="핵심 후보",
                    strengths=["규모"],
                    risks=["사이클"],
                    fit_score=82,
                )
            ],
            idea_shortlist=[samsung],
            ranked_sectors=[
                SectorOpportunity(
                    sector="반도체/AI 인프라",
                    score=84,
                    rationale="AI 수요를 반영합니다.",
                    preferred_tickers=["005930.KS", "000660.KS"],
                )
            ],
            recommended_companies=[samsung],
            sector_trends=[
                SectorTrendInsight(
                    sector="반도체/AI 인프라",
                    flow_score=86,
                    trend_label="강세",
                    market_flow="강한 흐름",
                    investment_solution="분할 접근",
                    leader_tickers=["005930.KS", "000660.KS"],
                    leader_companies=[sk_hynix],
                )
            ],
            sector_leaders=[sk_hynix],
            allocation_view="분할 접근",
            watch_items=["실적"],
            key_risks=["변동성"],
            next_actions=["추적"],
        )

        rendered = main.render_sector_opportunity_markdown(report, date(2026, 5, 21))

        self.assertIn("삼성전자", rendered)
        self.assertIn("SK하이닉스", rendered)
        self.assertIn("선호 기업", rendered)
        self.assertIn("주도 기업", rendered)
        self.assertNotIn("005930.KS", rendered)
        self.assertNotIn("000660.KS", rendered)
        self.assertNotIn("선호 티커", rendered)


class FileAttachmentUtilsModuleTests(unittest.TestCase):
    def test_file_attachment_utils_sanitize_decode_and_classify(self):
        from fastapi import HTTPException
        from research_os import file_attachment_utils

        safe_name = file_attachment_utils.safe_attachment_file_name("../위험 파일?.pdf")
        decoded = file_attachment_utils.decode_attachment_base64(base64.b64encode(b"hello").decode("ascii"))

        self.assertEqual(safe_name, "위험-파일.pdf")
        self.assertEqual(decoded, b"hello")
        self.assertTrue(file_attachment_utils.is_pdf_attachment("report.PDF", None))
        self.assertTrue(file_attachment_utils.is_image_attachment("chart.png", None))
        with self.assertRaises(HTTPException):
            file_attachment_utils.decode_attachment_base64("not-valid-base64")


class FileImageMetadataModuleTests(unittest.TestCase):
    def test_file_image_metadata_detects_png_dimensions(self):
        from research_os import file_image_metadata

        png_2x3 = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR"
            b"\x00\x00\x00\x02"
            b"\x00\x00\x00\x03"
            b"\x08\x06\x00\x00\x00"
        )

        self.assertEqual(
            file_image_metadata.detect_image_dimensions(png_2x3),
            {"format": "PNG", "width": 2, "height": 3},
        )
        self.assertEqual(file_image_metadata.detect_image_dimensions(b"not-image"), {})


class FileSpreadsheetExtractionModuleTests(unittest.TestCase):
    def test_file_spreadsheet_extraction_reads_shared_and_inline_strings(self):
        import io
        import zipfile

        from research_os import file_spreadsheet_extraction

        shared_strings = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<sst xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">
  <si><t>매출</t></si>
  <si><t>영업이익</t></si>
</sst>"""
        sheet = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">
  <sheetData>
    <row r=\"1\"><c r=\"A1\" t=\"s\"><v>0</v></c><c r=\"B1\" t=\"s\"><v>1</v></c></row>
    <row r=\"2\"><c r=\"A2\" t=\"inlineStr\"><is><t>2026</t></is></c><c r=\"B2\"><v>1234</v></c></row>
  </sheetData>
</worksheet>"""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("xl/sharedStrings.xml", shared_strings)
            archive.writestr("xl/worksheets/sheet1.xml", sheet)

        extracted, note = file_spreadsheet_extraction.extract_xlsx_text(buffer.getvalue())

        self.assertEqual(file_spreadsheet_extraction.excel_column_index("AA10"), 26)
        self.assertIn("매출\t영업이익", extracted)
        self.assertIn("2026\t1234", extracted)
        self.assertIn("1개 시트", note)

class FileExtractionProfileModuleTests(unittest.TestCase):
    def test_file_extraction_profile_scores_table_and_ocr_context(self):
        from research_os import file_extraction_profile

        profile = file_extraction_profile.build_file_extraction_profile(
            "Excel 문서",
            "매출\t100\n영업이익\t20\nFCF\t12",
            "XLSX 표 데이터 추출 완료",
            [],
        )
        ocr_profile = file_extraction_profile.build_file_extraction_profile(
            "PDF",
            "OCR 본문 " * 400,
            "OCR 추출 완료",
            [],
        )

        self.assertEqual(profile["analysis_readiness"], "보통")
        self.assertIn("표형 데이터 감지", profile["quality_drivers"])
        self.assertTrue(ocr_profile["used_ocr"])
        self.assertLessEqual(ocr_profile["recommended_quality"], 0.82)

class FileExtractionTests(unittest.TestCase):
    def test_file_ocr_runtime_status_exposes_limits_without_secret_paths(self):
        from research_os import file_ocr_runtime

        with (
            patch.object(file_ocr_runtime, "resolve_tesseract_executable", return_value=None),
            patch.object(file_ocr_runtime, "resolve_tessdata_dir", return_value=None),
        ):
            status = file_ocr_runtime.ocr_runtime_status()

        self.assertEqual(status["status"], "warning")
        self.assertFalse(status["ready"])
        self.assertIn("pdf_ocr_max_pages", status["limits"])
        self.assertIn("Tesseract OCR 실행 파일", status["message"])

    def test_file_text_extraction_extracts_csv_preview(self):
        from research_os.file_text_extraction import extract_text_like_file

        text, note = extract_text_like_file("종목,점수\nA,10\nB,20\n".encode("utf-8-sig"), "scores.csv")

        self.assertIn("종목\t점수", text)
        self.assertIn("A\t10", text)
        self.assertIn("CSV 표 텍스트 추출 완료", note)

    def test_ocr_runtime_status_exposes_processing_limits(self):
        from research_os.file_extraction import ocr_runtime_status

        status = ocr_runtime_status()

        self.assertIn("limits", status)
        self.assertGreater(status["limits"]["pdf_ocr_max_pages"], 0)
        self.assertGreater(status["limits"]["pdf_ocr_text_max_chars"], 0)
        self.assertIn("긴 PDF OCR", status["limits"]["message"])

    def test_pdf_without_text_marks_ocr_language_pack_missing(self):
        from research_os.file_extraction import extract_uploaded_file_text

        with patch(
            "research_os.file_extraction.extract_pdf_text",
            return_value=(
                "",
                "PDF에서 추출 가능한 텍스트를 찾지 못했습니다. 스캔 이미지 PDF일 수 있습니다. 한국어/영어 OCR 언어팩(kor+eng)을 찾지 못했습니다.",
            ),
        ):
            result = extract_uploaded_file_text(b"%PDF-1.4\n%%EOF", "policy.pdf", "application/pdf")

        profile = result["extraction_profile"]
        self.assertEqual(result["document_type"], "PDF")
        self.assertEqual(result["extraction_char_count"], 0)
        self.assertEqual(profile["ocr_status"], "unavailable")
        self.assertEqual(profile["ocr_missing_reason"], "language_pack_missing")
        self.assertIn("TESSDATA_PREFIX", profile["ocr_next_action"])

    def test_image_upload_without_tesseract_is_saved_with_clear_ocr_warning(self):
        from research_os.file_extraction import extract_uploaded_file_text

        png_1x1 = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
            b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
            b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        with patch("research_os.file_extraction.resolve_tesseract_executable", return_value=None):
            result = extract_uploaded_file_text(png_1x1, "capture.png", "image/png")

        self.assertEqual(result["document_type"], "이미지")
        self.assertEqual(result["extraction_char_count"], 0)
        self.assertIn("Tesseract OCR 실행 파일을 찾지 못했습니다", result["text_extraction"])
        self.assertIn("원본 이미지는 저장", " ".join(result["extraction_warnings"]))
        self.assertEqual(result["extraction_profile"]["ocr_status"], "unavailable")
        self.assertEqual(result["extraction_profile"]["ocr_missing_reason"], "tesseract_not_found")


class ResearchWorkflowFilesModuleTests(unittest.TestCase):
    def test_research_workflow_rendering_module_formats_file_processing(self):
        from research_os import research_workflow_rendering

        attachment = {
            "file_name": "upload.txt",
            "document_type": "text",
            "relative_path": "WORKFLOW/_attachments/upload.txt",
            "text_extraction": "extracted",
            "extraction_quality": "high",
            "extraction_char_count": 14,
            "extraction_warnings": ["sample warning"],
            "extraction_profile": {
                "analysis_readiness": "ready",
                "line_count": 1,
                "numeric_token_count": 2,
                "table_like_line_count": 0,
                "next_action": "review",
            },
        }

        updates = research_workflow_rendering.infer_model_update_items("Revenue and margin improved")
        markdown = research_workflow_rendering.render_file_processing_markdown(attachment)

        self.assertIn("매출", [item["item"] for item in updates])
        self.assertIn("마진", [item["item"] for item in updates])
        self.assertEqual(research_workflow_rendering.workflow_material_excerpt("  "), "입력 자료 없음")
        self.assertIn("- 분석 활용도: ready", markdown)
        self.assertIn("- 추출 경고: sample warning", markdown)

    def test_research_workflow_files_module_handles_attachments_and_rag_payloads(self):
        from research_os import research_workflow_files
        from research_os.research_memory import ResearchStorageInfo

        upsert_calls = []
        saved_calls = []

        def fake_extract_uploaded_file_text(file_bytes, file_name, mime_type, source_path=None):
            self.assertEqual(file_bytes, b"revenue margin")
            self.assertEqual(file_name, "upload.txt")
            self.assertEqual(mime_type, "text/plain")
            self.assertTrue(source_path.exists())
            return {
                "text_extraction": "extracted",
                "extracted_text": "revenue margin",
                "document_type": "text",
                "extraction_quality": "high",
                "extraction_char_count": 14,
                "extraction_preview": "revenue margin",
                "extraction_warnings": ["sample warning"],
                "extraction_profile": {
                    "analysis_readiness": "ready",
                    "line_count": 1,
                    "numeric_token_count": 0,
                    "table_like_line_count": 0,
                    "next_action": "review",
                },
            }

        def fake_upsert_research_memory_document(*, vault_dir, entry, full_text=None):
            upsert_calls.append({"vault_dir": vault_dir, "entry": entry, "full_text": full_text})
            return {"stored": True, "entry": entry}

        def fake_save_research_markdown(**kwargs):
            saved_calls.append(kwargs)
            return ResearchStorageInfo(
                file_name=f"{kwargs['ticker']}-{kwargs['report_type']}.md",
                relative_path=f"research_vault/{kwargs['ticker']}/{kwargs['ticker']}-{kwargs['report_type']}.md",
                absolute_path=str(kwargs['vault_dir'] / kwargs['ticker'] / f"{kwargs['ticker']}-{kwargs['report_type']}.md"),
                json_file_name=f"{kwargs['ticker']}-{kwargs['report_type']}.json",
                json_relative_path=f"research_vault/{kwargs['ticker']}/{kwargs['ticker']}-{kwargs['report_type']}.json",
                json_absolute_path=str(kwargs['vault_dir'] / kwargs['ticker'] / f"{kwargs['ticker']}-{kwargs['report_type']}.json"),
            )

        class FakeHttpException(Exception):
            def __init__(self, status_code, detail):
                super().__init__(detail)
                self.status_code = status_code
                self.detail = detail

        class FakeDataSourceType:
            OTHER = "other"
            RESEARCH_MEMORY = "research_memory"

        class FakeInjectedDataPoint:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

            def model_dump(self, mode=None):
                return dict(self.__dict__)

        runtime = SimpleNamespace(
            DataSourceType=FakeDataSourceType,
            HTTPException=FakeHttpException,
            InjectedDataPoint=FakeInjectedDataPoint,
            current_storage_date=lambda: date(2026, 6, 13),
            decode_attachment_base64=lambda value: base64.b64decode(value),
            extract_uploaded_file_text=fake_extract_uploaded_file_text,
            normalize_ticker=lambda value: str(value or "").upper().replace(" ", "-"),
            official_ticker_registry={
                "WORKFLOW": {
                    "company_name": "Workflow Inc",
                    "business_context": "automation",
                    "watch_kpis": ["ARR", "FCF"],
                }
            },
            read_dynamic_ticker_registry=lambda settings: {},
            resolve_ticker_symbol_from_alias=lambda value, settings: str(value or "").upper(),
            resolve_vault_dir=lambda research_vault_dir: Path(research_vault_dir),
            safe_attachment_file_name=lambda value: "upload.txt",
            save_research_markdown=fake_save_research_markdown,
            summarize_capture=lambda value: f"요약: {value[:20]}",
            upsert_research_memory_document=fake_upsert_research_memory_document,
        )
        test_tmp_dir = PROJECT_ROOT / ".test-tmp"
        test_tmp_dir.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=test_tmp_dir, ignore_cleanup_errors=True) as temp_dir:
            vault_dir = Path(temp_dir) / "research_vault"
            payload = {
                "file_content_base64": base64.b64encode(b"revenue margin").decode("ascii"),
                "file_name": "upload.txt",
                "file_mime_type": "text/plain",
            }
            attachment = research_workflow_files.prepare_workflow_attachment(
                runtime,
                vault_dir=vault_dir,
                storage_key="workflow",
                payload=payload,
                storage_date=date(2026, 6, 13),
            )
            storage = ResearchStorageInfo(
                file_name="WORKFLOW-note.md",
                relative_path="research_vault/WORKFLOW/WORKFLOW-note.md",
                absolute_path=str(vault_dir / "WORKFLOW" / "WORKFLOW-note.md"),
                json_file_name="WORKFLOW-note.json",
                json_relative_path="research_vault/WORKFLOW/WORKFLOW-note.json",
                json_absolute_path=str(vault_dir / "WORKFLOW" / "WORKFLOW-note.json"),
            )
            rag_result = research_workflow_files.upsert_saved_workflow_rag_document(
                runtime,
                vault_dir=vault_dir,
                storage=storage,
                storage_key="workflow",
                report_type="workflow-note",
                summary="요약",
                markdown="# Note",
                tags=["workflow"],
                metadata={"source": "test"},
            )
            settings = SimpleNamespace(research_vault_dir=str(vault_dir))
            earnings_response = research_workflow_files.build_earnings_filing_note_response(
                runtime,
                {
                    "ticker": "workflow",
                    "earnings_call": "Revenue and margin improved",
                    "file_content_base64": base64.b64encode(b"revenue margin").decode("ascii"),
                    "file_name": "upload.txt",
                    "file_mime_type": "text/plain",
                },
                settings,
            )
            lp_response = research_workflow_files.build_gp_lp_staging_response(
                runtime,
                {
                    "fund_name": "Workflow Fund",
                    "gp_package": "IPO exit with write-down risk",
                    "valuation_method": "DCF",
                    "base_case": "Base",
                    "file_content_base64": base64.b64encode(b"revenue margin").decode("ascii"),
                    "file_name": "upload.txt",
                    "file_mime_type": "text/plain",
                },
                settings,
            )
            saved_earnings_response = research_workflow_files.save_earnings_filing_note_response(
                runtime,
                dict(earnings_response),
                settings,
            )
            saved_lp_response = research_workflow_files.save_gp_lp_staging_response(
                runtime,
                dict(lp_response),
                settings,
            )

        self.assertEqual(attachment["file_name"], "upload.txt")
        self.assertEqual(attachment["text_extraction"], "extracted")
        self.assertEqual(attachment["extraction_profile"]["analysis_readiness"], "ready")
        self.assertIn("WORKFLOW/_attachments/WORKFLOW-workflow-attachment-2026-06-13", attachment["relative_path"])
        self.assertIn("매출", [item["item"] for item in research_workflow_files.infer_model_update_items("Revenue and margin improved")])
        self.assertEqual(research_workflow_files.workflow_material_excerpt("  "), "입력 자료 없음")
        self.assertIn("- 추출 경고: sample warning", research_workflow_files.render_file_processing_markdown(attachment))
        earnings_markdown = research_workflow_files.render_earnings_filing_note_markdown(
            {
                "ticker": "WORKFLOW",
                "company_name": "Workflow Inc",
                "model_updates": research_workflow_files.infer_model_update_items("Revenue and margin improved"),
                "note_draft": [{"title": "핵심 요약", "body": "본문"}],
                "open_questions": ["질문"],
                "next_actions": ["액션"],
                "file_processing": attachment,
            },
            date(2026, 6, 13),
        )
        lp_markdown = research_workflow_files.render_lp_report_staging_markdown(
            {
                "fund_name": "Workflow Fund",
                "gp_package_summary": "요약",
                "valuation_template_output": ["템플릿"],
                "valuation_template_rows": [
                    {
                        "line_item": "NAV",
                        "input_status": "확인",
                        "model_action": "입력",
                        "lp_note": "메모",
                    }
                ],
                "staging_checklist": ["체크"],
                "lp_risk_flags": ["리스크"],
                "lp_report_draft": [{"title": "초안", "body": "본문"}],
                "file_processing": attachment,
            },
            date(2026, 6, 13),
        )
        self.assertIn("# Workflow Inc 어닝 콜/공시 기반 노트 초안", earnings_markdown)
        self.assertIn("## 첨부 파일 처리", earnings_markdown)
        self.assertIn("# Workflow Fund LP 보고 스테이징", lp_markdown)
        self.assertIn("| NAV | 확인 | 입력 | 메모 |", lp_markdown)
        self.assertEqual(earnings_response["ticker"], "WORKFLOW")
        self.assertEqual(earnings_response["company_name"], "Workflow Inc")
        self.assertEqual(earnings_response["file_processing"]["file_name"], "upload.txt")
        self.assertEqual(earnings_response["injected_data"][0]["label"], "official_company_profile")
        self.assertEqual(lp_response["fund_name"], "Workflow Fund")
        self.assertIn("감액 신호", "\n".join(lp_response["valuation_template_output"]))
        self.assertIn("엑시트 이벤트", "\n".join(lp_response["valuation_template_output"]))
        self.assertEqual(lp_response["file_processing"]["file_name"], "upload.txt")
        self.assertIn("storage", saved_earnings_response)
        self.assertIn("rag_document", saved_earnings_response)
        self.assertIn("storage", saved_lp_response)
        self.assertIn("rag_document", saved_lp_response)
        self.assertEqual(saved_calls[0]["report_type"], "earnings-filing-note")
        self.assertEqual(saved_calls[1]["report_type"], "lp-report-staging")
        self.assertTrue(rag_result["stored"])
        self.assertEqual(upsert_calls[0]["entry"]["ticker"], "WORKFLOW")
        self.assertEqual(upsert_calls[0]["entry"]["date"], "2026-06-13")
        self.assertEqual(upsert_calls[0]["entry"]["source"], "test")
        self.assertEqual(upsert_calls[0]["full_text"], "# Note")
class DailyRecommendationEvidenceModuleTests(unittest.TestCase):
    def test_daily_recommendation_evidence_normalizes_and_matches_claims(self):
        from research_os import daily_recommendation_evidence

        documents = daily_recommendation_evidence.normalize_evidence_documents(
            [
                {
                    "source_relative_path": "research_vault/003230/report.md",
                    "title": "Team report",
                    "matched_claims": ["RAG 연결", "", "공시 확인", "추가"],
                },
                {
                    "relative_path": "research_vault/003230/report.md",
                    "title": "duplicate",
                },
            ]
        )
        claims = daily_recommendation_evidence.evidence_document_claims(
            {
                "report_type": "dart-filing-watch",
                "source_type": "filing",
                "title": "삼양식품 공시",
                "source_relative_path": "research_vault/003230/dart.md",
            },
            ["공시 확인", "RAG 연결", "무관한 단어"],
        )

        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0]["matched_claims"], ["RAG 연결", "공시 확인", "추가"])
        self.assertEqual(claims, ["공시 확인", "RAG 연결"])
        self.assertEqual(daily_recommendation_evidence.normalize_recommendation_ticker(" 003230 "), "003230")
        self.assertEqual(
            daily_recommendation_evidence.unique_text_items([" A ", "A", "", None, "B", "C"], 2),
            ["A", "B"],
        )


class DailyRecommendationCandidateModuleTests(unittest.TestCase):
    def test_daily_recommendation_candidates_normalize_and_score_rows(self):
        from research_os import daily_recommendation_candidates

        candidates: dict[str, dict] = {}
        domestic = daily_recommendation_candidates.ensure_daily_recommendation_candidate(
            candidates,
            " 003230 ",
            "삼양식품",
        )
        overseas = daily_recommendation_candidates.ensure_daily_recommendation_candidate(
            candidates,
            "joby",
            "Joby Aviation",
        )

        daily_recommendation_candidates.add_daily_recommendation_score(domestic, "5", "리포트")
        daily_recommendation_candidates.add_daily_recommendation_score(domestic, 0, "무시")
        daily_recommendation_candidates.add_daily_recommendation_penalty(domestic, "현재가 미확인", "2")
        normalized = daily_recommendation_candidates.normalize_candidate(
            {
                **domestic,
                "reasons": [" 이유 ", "", "추가"],
                "evidence_sources": [" 근거 ", None],
                "score_components": [{"label": "리포트", "points": 5}, {"points": 99}],
                "score_penalties": domestic["score_penalties"] + [""],
                "quality_flags": [" 점검 "],
            }
        )

        self.assertEqual(domestic["currency"], "KRW")
        self.assertEqual(overseas["currency"], "USD")
        self.assertEqual(domestic["score"], 3)
        self.assertEqual(normalized["ticker"], "003230")
        self.assertEqual(normalized["reasons"], ["이유", "추가"])
        self.assertEqual(normalized["evidence_sources"], ["근거"])
        self.assertEqual(normalized["score_components"], [{"label": "리포트", "points": 5}])
        self.assertEqual(normalized["score_penalties"], ["현재가 미확인 (-2)"])
        self.assertTrue(daily_recommendation_candidates.daily_recommendation_candidate_is_valid("003230", "삼양식품"))
        self.assertFalse(daily_recommendation_candidates.daily_recommendation_candidate_is_valid("123", "삼양식품"))

    def test_daily_recommendation_candidates_finalize_score_explanation(self):
        from research_os import daily_recommendation_candidates

        candidate = {
            "score": 11,
            "reasons": [" 이유 ", "이유", ""],
            "evidence_sources": [" 근거 "],
            "risk_notes": [" 리스크 "],
            "score_penalties": ["현재가 미확인 (-2)", "현재가 미확인 (-2)"],
            "quality_flags": [" 점검 "],
            "score_components": [{"label": "리포트", "points": 8}, {"label": "현재가", "points": 5}, {"points": 99}],
            "evidence_documents": [{"title": "문서", "source_relative_path": "research_vault/003230/doc.md"}],
        }

        finalized = daily_recommendation_candidates.finalize_daily_recommendation_candidate(candidate)

        self.assertIs(finalized, candidate)
        self.assertEqual(candidate["reasons"], ["이유"])
        self.assertEqual(candidate["score_penalties"], ["현재가 미확인 (-2)"])
        self.assertEqual(candidate["score_explanation"]["positive_points"], 13)
        self.assertEqual(candidate["score_explanation"]["penalty_points"], 2)
        self.assertEqual(candidate["score_explanation"]["top_component"]["label"], "리포트")
        self.assertEqual(candidate["evidence_documents"][0]["citation_label"], "근거 문서")

    def test_daily_recommendation_candidates_build_signal_breakdown(self):
        from research_os import daily_recommendation_candidates

        candidate = {
            "score": 31,
            "reasons": ["시장일지 연결"],
            "evidence_sources": ["시장일지 연결", "최근 1주 핵심 리포트 2건"],
            "score_components": [
                {"label": "시장일지 연결", "points": 10},
                {"label": "최근 중요 공시 반영", "points": 5},
                {"label": "최근 핵심 리포트 반영", "points": 3},
                {"label": "첨부 투자 방향: AI 반도체 2차 병목", "points": 8},
            ],
            "policy_signal_summary": {
                "count": 1,
                "match_level": "theme",
                "match_level_label": "테마",
                "score_applied": False,
            },
            "evidence_documents": [
                {"source_type": "filing", "report_type": "filing", "title": "DART 공시"},
                {"source_type": "analyst_report", "report_type": "report", "title": "증권사 리포트"},
            ],
        }

        finalized = daily_recommendation_candidates.finalize_daily_recommendation_candidate(candidate)
        breakdown = {item["key"]: item for item in finalized["signal_breakdown"]}

        self.assertEqual([item["key"] for item in finalized["signal_breakdown"]], ["market", "filing", "policy", "news", "sentiment"])
        self.assertTrue(breakdown["market"]["score_applied"])
        self.assertEqual(breakdown["filing"]["count"], 1)
        self.assertEqual(breakdown["policy"]["summary"], "테마 1건 · 참고만")
        self.assertFalse(breakdown["policy"]["score_applied"])
        self.assertTrue(breakdown["news"]["score_applied"])
        self.assertIn("AI 반도체", breakdown["sentiment"]["summary"])


class DailyRecommendationStoreModuleTests(unittest.TestCase):
    def test_daily_recommendation_store_builds_records_and_skips_existing_date(self):
        from datetime import date
        from tempfile import TemporaryDirectory

        from research_os import daily_recommendation_store
        from research_os.settings import Settings

        with TemporaryDirectory() as temp_dir:
            settings = Settings(research_vault_dir=str(Path(temp_dir) / "research_vault"))
            first = daily_recommendation_store.upsert_daily_recommendations(
                settings,
                candidates=[
                    {
                        "ticker": "003230",
                        "company_name": "삼양식품",
                        "score": 88,
                        "reasons": ["목표가 상승여력"],
                        "evidence_sources": ["리포트 근거"],
                        "score_components": [{"label": "목표가", "points": 35}],
                    }
                ],
                recommendation_date=date(2026, 6, 18),
                generated_at="2026-06-18T08:00:00+09:00",
            )
            second = daily_recommendation_store.upsert_daily_recommendations(
                settings,
                candidates=[{"ticker": "PL", "company_name": "Planet Labs", "score": 70}],
                recommendation_date=date(2026, 6, 18),
                generated_at="2026-06-18T09:00:00+09:00",
            )

        self.assertEqual(first["status"], "success")
        self.assertEqual(first["records"][0]["record_id"], "2026-06-18-KR-01-003230")
        self.assertEqual(first["records"][0]["market"], "KR")
        self.assertEqual(first["records"][0]["tracking_milestones"][0]["target_date"], "2026-06-25")
        self.assertEqual(first["records"][0]["signal_breakdown"][0]["key"], "market")
        self.assertEqual(second["status"], "skipped_existing")
        self.assertEqual(second["records"][0]["ticker"], "003230")

    def test_daily_recommendation_store_updates_tracking_and_summary(self):
        from datetime import date
        from tempfile import TemporaryDirectory

        from research_os import daily_recommendation_store
        from research_os.settings import Settings

        with TemporaryDirectory() as temp_dir:
            settings = Settings(research_vault_dir=str(Path(temp_dir) / "research_vault"))
            daily_recommendation_store.upsert_daily_recommendations(
                settings,
                candidates=[
                    {
                        "ticker": "003230",
                        "company_name": "삼양식품",
                        "score": 88,
                        "baseline_price": 100000,
                        "reasons": ["추적 테스트"],
                    }
                ],
                recommendation_date=date(2026, 6, 1),
                generated_at="2026-06-01T08:00:00+09:00",
            )

            tracking = daily_recommendation_store.update_recommendation_tracking(
                settings,
                as_of=date(2026, 6, 8),
                checked_at="2026-06-08T09:00:00+09:00",
                price_lookup=lambda _ticker: (110000, "unit_test"),
            )
            summary = daily_recommendation_store.summarize_daily_recommendation_store(settings)

        self.assertEqual(tracking["due_count"], 1)
        self.assertEqual(tracking["pending_count"], 4)
        self.assertEqual(summary["performance_summary"]["complete_count"], 1)
        self.assertEqual(summary["performance_summary"]["positive_count"], 1)
        self.assertEqual(summary["latest_records"][0]["tracking_milestones"][0]["status"], "complete")
        self.assertEqual(summary["latest_policy_alignment"]["status"], "ok")

    def test_daily_recommendation_store_reports_latest_policy_drift(self):
        from datetime import date
        from tempfile import TemporaryDirectory

        from research_os import daily_recommendation_store
        from research_os.settings import Settings

        with TemporaryDirectory() as temp_dir:
            settings = Settings(research_vault_dir=str(Path(temp_dir) / "research_vault"))
            daily_recommendation_store.upsert_daily_recommendations(
                settings,
                candidates=[
                    {
                        "ticker": "WEAK",
                        "company_name": "Weak Co",
                        "score": 80,
                        "baseline_price": 100,
                        "reasons": ["반복 추적 테스트"],
                    }
                ],
                recommendation_date=date(2026, 1, 1),
                generated_at="2026-01-01T08:00:00+09:00",
            )
            daily_recommendation_store.update_recommendation_tracking(
                settings,
                as_of=date(2026, 7, 1),
                checked_at="2026-07-01T09:00:00+09:00",
                price_lookup=lambda _ticker: (90, "unit_test"),
            )
            daily_recommendation_store.upsert_daily_recommendations(
                settings,
                candidates=[
                    {
                        "ticker": "WEAK",
                        "company_name": "Weak Co",
                        "score": 82,
                        "baseline_price": 91,
                        "reasons": ["최신 추천에 재진입"],
                    },
                    {
                        "ticker": "OK",
                        "company_name": "Okay Co",
                        "score": 76,
                        "baseline_price": 50,
                        "reasons": ["대체 후보"],
                    },
                ],
                recommendation_date=date(2026, 6, 18),
                generated_at="2026-06-18T08:00:00+09:00",
            )
            summary = daily_recommendation_store.summarize_daily_recommendation_store(settings)

        alignment = summary["latest_policy_alignment"]
        self.assertEqual(alignment["status"], "drift")
        self.assertEqual(alignment["review_hold_count"], 1)
        self.assertEqual(alignment["review_hold_records"][0]["ticker"], "WEAK")
        self.assertEqual(alignment["review_hold_records"][0]["penalty_points"], 12)


class DailyRecommendationQualityModuleTests(unittest.TestCase):
    def test_daily_recommendation_quality_counts_and_applies_storage_penalties(self):
        from research_os import daily_recommendation_quality

        quality = daily_recommendation_quality.daily_recommendation_manifest_quality_by_ticker(
            [
                {"ticker": " 003230 ", "summary": "정상 리포트", "date": "2026-06-18"},
                {"ticker": "003230", "duplicate_count": 1},
                {"ticker": "003230", "tags": ["url_text_unavailable", "needs_body_copy"]},
                {"ticker": "003230", "attachment": {"ocr_required": True}},
                {"ticker": "003230", "status": "archived"},
            ]
        )["003230"]
        candidate = {"score": 10, "score_components": [], "score_penalties": [], "quality_flags": [], "evidence_sources": []}

        daily_recommendation_quality.apply_daily_recommendation_storage_quality(candidate, quality)

        self.assertEqual(quality["active_count"], 4)
        self.assertEqual(quality["archived_count"], 1)
        self.assertEqual(quality["high_quality_count"], 1)
        self.assertEqual(quality["duplicate_suspected_count"], 1)
        self.assertEqual(quality["body_missing_count"], 1)
        self.assertEqual(quality["ocr_needed_count"], 1)
        self.assertEqual(candidate["score"], 5)
        self.assertEqual(candidate["score_components"][0]["label"], "검증 저장자료 품질")
        self.assertTrue(candidate["evidence_sources"][0].startswith("저장 품질:"))
        self.assertIn("중복 의심 자료는 대표 자료만 근거로 사용", candidate["quality_flags"])


class DailyRecommendationScoringModuleTests(unittest.TestCase):
    def test_daily_recommendation_scoring_applies_consensus_priority_and_price(self):
        from research_os import daily_recommendation_scoring

        candidate = {
            "score": 0,
            "score_components": [],
            "score_penalties": [],
            "reasons": [],
            "evidence_sources": [],
            "portfolio_context": [],
            "risk_notes": [],
            "quality_flags": [],
        }

        daily_recommendation_scoring.apply_daily_recommendation_consensus_row(
            candidate,
            {
                "currency": "KRW",
                "current_price": 100000,
                "price_source": "consensus",
                "target_upside": 0.24,
                "valuation_signal": "저평가",
                "source_count": 3,
                "market_value": 12_000_000,
                "interest": True,
            },
            as_of="2026-06-18T08:00:00+09:00",
        )
        daily_recommendation_scoring.apply_daily_recommendation_priority_target(
            candidate,
            {
                "priority": "high",
                "recent_document_count": 4,
                "rag_document_count": 6,
                "thesis_snapshot_connected": True,
                "market_journal_matches": [{"summary": "미국 시장일지 AI 전력 병목 점검"}],
                "next_action": "목표가 재확인",
            },
        )
        daily_recommendation_scoring.apply_daily_recommendation_price_check(
            candidate,
            price=None,
            source="provider-missing",
        )

        labels = [component["label"] for component in candidate["score_components"]]
        self.assertIn("증권사 목표가 상승여력", labels)
        self.assertIn("보유/관심 우선순위", labels)
        self.assertEqual(candidate["baseline_price"], 100000)
        self.assertEqual(candidate["baseline_price_source"], "consensus")
        self.assertEqual(candidate["portfolio_risk_connection"]["priority"], "high")
        self.assertTrue(any("시장일지 연결" in reason for reason in candidate["reasons"]))
        self.assertIn("목표가 재확인", candidate["risk_notes"])
        self.assertIn("현재가 미확인 (-5)", candidate["score_penalties"])
        self.assertIn("기준 현재가 미확인", candidate["quality_flags"])


class DailyRecommendationPolicyModuleTests(unittest.TestCase):
    def test_daily_recommendation_policy_signals_add_score_risk_and_evidence(self):
        from research_os import daily_recommendation_policy

        policy_watch = {
            "related_items": [
                {
                    "title": "AI 반도체 산업 육성 전략 발표",
                    "source_provider": "산업통상자원부",
                    "source_scope": "산업·통상 정책자료",
                    "published_at": "2026-06-23",
                    "detail_url": "https://www.motie.go.kr/policy/1",
                    "relevance_score": 90,
                    "matched_themes": ["AI/디지털", "산업/통상"],
                    "target_matches": [{"ticker": "005930", "label": "삼성전자"}],
                },
                {
                    "title": "플랫폼 공정화 규제 강화 및 조사 계획",
                    "source_provider": "공정거래위원회",
                    "source_scope": "공정거래·플랫폼 규제 보도자료",
                    "published_at": "2026-06-23",
                    "detail_url": "https://www.ftc.go.kr/policy/2",
                    "relevance_score": 75,
                    "matched_themes": ["공정거래/플랫폼"],
                    "target_matches": [{"ticker": "005930", "label": "삼성전자"}],
                },
            ]
        }
        index = daily_recommendation_policy.build_policy_signal_index(policy_watch)
        candidate = {
            "ticker": "005930",
            "score": 0,
            "score_components": [],
            "score_penalties": [],
            "quality_flags": [],
            "evidence_sources": ["기존 근거"],
            "evidence_documents": [],
            "reasons": [],
            "risk_notes": [],
        }

        daily_recommendation_policy.apply_daily_recommendation_policy_signals(candidate, index)

        labels = [component["label"] for component in candidate["score_components"]]
        self.assertIn("정책 수혜/제도 모멘텀", labels)
        self.assertIn("정책·규제 리스크 확인", " ".join(candidate["score_penalties"]))
        self.assertIn("정책·규제 리스크 확인 필요", candidate["quality_flags"])
        self.assertTrue(candidate["evidence_sources"][0].startswith("정책 신호 직접 2건"))
        self.assertEqual(candidate["policy_signal_summary"]["count"], 2)
        self.assertEqual(candidate["policy_signal_summary"]["match_level"], "direct")
        self.assertTrue(candidate["policy_signal_summary"]["score_applied"])
        self.assertEqual(candidate["policy_signal_summary"]["direct_count"], 2)
        self.assertEqual(candidate["policy_signal_summary"]["risk_count"], 1)
        self.assertEqual(candidate["evidence_documents"][0]["citation_label"], "정책 신호 근거")
        self.assertEqual(candidate["evidence_documents"][0]["source_type"], "policy_law")

    def test_daily_recommendation_policy_signals_match_theme_when_ticker_is_absent(self):
        from research_os import daily_recommendation_policy

        index = daily_recommendation_policy.build_policy_signal_index(
            {
                "related_items": [
                    {
                        "title": "AI 반도체 디지털 산업 전략 발표",
                        "source_provider": "대한민국 정책브리핑",
                        "published_at": "2026-06-24",
                        "detail_url": "https://www.korea.kr/briefing/1",
                        "relevance_score": 70,
                        "matched_themes": ["AI/디지털"],
                        "target_matches": [],
                    }
                ]
            }
        )
        candidate = {
            "ticker": "395160",
            "company_name": "KODEX AI반도체 ETF",
            "score": 0,
            "score_components": [],
            "score_penalties": [],
            "quality_flags": [],
            "evidence_sources": ["AI 반도체 시장일지 연결"],
            "evidence_documents": [],
            "reasons": [],
            "risk_notes": [],
        }

        daily_recommendation_policy.apply_daily_recommendation_policy_signals(candidate, index)

        self.assertEqual(candidate["policy_signal_summary"]["count"], 1)
        self.assertEqual(candidate["policy_signal_summary"]["match_level"], "theme")
        self.assertEqual(candidate["policy_signal_summary"]["theme_count"], 1)
        self.assertFalse(candidate["policy_signal_summary"]["score_applied"])
        self.assertFalse(any(component["label"] == "정책 테마 모멘텀" for component in candidate["score_components"]))
        self.assertTrue(candidate["evidence_sources"][0].startswith("정책 신호 테마 참고"))
        self.assertTrue(candidate["evidence_documents"])

    def test_daily_recommendation_policy_signals_demotes_weak_theme_overlap_to_market(self):
        from research_os import daily_recommendation_policy

        index = daily_recommendation_policy.build_policy_signal_index(
            {
                "related_items": [
                    {
                        "title": "산림청 디지털정부 데이터 개방 유공 수상",
                        "summary": "재난안전 데이터 개방과 행정 혁신 중심 보도자료",
                        "source_provider": "대한민국 정책브리핑",
                        "published_at": "2026-06-24",
                        "detail_url": "https://www.korea.kr/briefing/forest",
                        "relevance_score": 70,
                        "matched_themes": ["AI/디지털"],
                        "target_matches": [],
                    }
                ]
            }
        )
        candidate = {
            "ticker": "ABSI",
            "company_name": "Absci Corporation",
            "score": 0,
            "score_components": [],
            "score_penalties": [],
            "quality_flags": [],
            "evidence_sources": ["AI 신약개발 데이터 클라우드"],
            "evidence_documents": [],
            "reasons": [],
            "risk_notes": [],
        }

        daily_recommendation_policy.apply_daily_recommendation_policy_signals(candidate, index)

        self.assertEqual(candidate["policy_signal_summary"]["match_level"], "market")
        self.assertEqual(candidate["policy_signal_summary"]["theme_count"], 0)
        self.assertTrue(candidate["evidence_sources"][0].startswith("정책 신호 시장 참고"))

    def test_daily_recommendation_policy_signals_promote_company_name_to_direct_match(self):
        from research_os import daily_recommendation_policy

        index = daily_recommendation_policy.build_policy_signal_index(
            {
                "related_items": [
                    {
                        "title": "Absci Corporation AI 신약개발 규제지원 프로그램 선정",
                        "summary": "미국 바이오 AI 기업 Absci의 임상 데이터 인프라 지원",
                        "source_provider": "정책 브리핑",
                        "published_at": "2026-06-24",
                        "detail_url": "https://example.gov/policy/absci",
                        "relevance_score": 80,
                        "matched_themes": ["바이오/헬스케어", "AI/디지털"],
                        "target_matches": [],
                    }
                ]
            }
        )
        candidate = {
            "ticker": "ABSI",
            "company_name": "Absci Corporation",
            "score": 0,
            "score_components": [],
            "score_penalties": [],
            "quality_flags": [],
            "evidence_sources": ["바이오 임상 근거"],
            "evidence_documents": [],
            "reasons": [],
            "risk_notes": [],
        }

        daily_recommendation_policy.apply_daily_recommendation_policy_signals(candidate, index)

        self.assertEqual(candidate["policy_signal_summary"]["match_level"], "direct")
        self.assertEqual(candidate["policy_signal_summary"]["direct_count"], 1)
        self.assertTrue(any(component["label"] == "정책 수혜/제도 모멘텀" for component in candidate["score_components"]))

    def test_daily_recommendation_policy_signals_keep_market_reference_out_of_score(self):
        from research_os import daily_recommendation_policy

        index = daily_recommendation_policy.build_policy_signal_index(
            {
                "related_items": [
                    {
                        "title": "금융시장 안정 점검 회의",
                        "source_provider": "금융위원회",
                        "published_at": "2026-06-24",
                        "detail_url": "https://www.fsc.go.kr/policy/1",
                        "relevance_score": 60,
                        "matched_themes": ["금융/자본시장"],
                        "target_matches": [],
                    }
                ]
            }
        )
        candidate = {
            "ticker": "ABSI",
            "company_name": "Absci Corporation",
            "score": 10,
            "score_components": [],
            "score_penalties": [],
            "quality_flags": [],
            "evidence_sources": ["바이오 임상 근거"],
            "evidence_documents": [],
            "reasons": [],
            "risk_notes": [],
        }

        daily_recommendation_policy.apply_daily_recommendation_policy_signals(candidate, index)

        self.assertEqual(candidate["score"], 10)
        self.assertFalse(candidate["score_components"])
        self.assertFalse(candidate["score_penalties"])
        self.assertEqual(candidate["policy_signal_summary"]["match_level"], "market")
        self.assertFalse(candidate["policy_signal_summary"]["score_applied"])
        self.assertTrue(candidate["evidence_sources"][0].startswith("정책 신호 시장 참고"))

    def test_daily_recommendation_policy_signal_quality_dashboard_flags_theme_review(self):
        from research_os import daily_recommendation_policy

        payload = {
            "latest_recommendation_date": "2026-06-24",
            "latest_records": [
                {
                    "market": "KR",
                    "rank": 1,
                    "ticker": "005930",
                    "company_name": "삼성전자",
                    "score": 120,
                    "policy_signal_summary": {
                        "match_level": "theme",
                        "match_level_label": "테마",
                        "score_applied": True,
                        "direct_count": 0,
                        "theme_count": 3,
                        "market_count": 3,
                        "support_count": 1,
                        "risk_count": 2,
                        "top_title": "AI 반도체 정책",
                    },
                    "score_components": [{"label": "정책 테마 모멘텀", "points": 4}],
                    "score_penalties": ["정책 테마 규제 리스크 확인 (-2)"],
                    "evidence_documents": [
                        {
                            "title": "AI 반도체 정책",
                            "source_type": "policy_law",
                            "report_type": "official_policy_source",
                            "source_date": "2026-06-24",
                        }
                    ],
                },
                {
                    "market": "US",
                    "rank": 1,
                    "ticker": "ABSI",
                    "company_name": "Absci",
                    "score": 90,
                    "policy_signal_summary": {
                        "match_level": "market",
                        "match_level_label": "시장",
                        "score_applied": False,
                        "direct_count": 0,
                        "theme_count": 0,
                        "market_count": 3,
                        "support_count": 1,
                        "risk_count": 0,
                        "top_title": "시장 안정 정책",
                    },
                    "score_components": [],
                    "score_penalties": [],
                    "evidence_documents": [],
                },
            ],
        }

        dashboard = daily_recommendation_policy.build_policy_signal_quality_dashboard(payload)

        self.assertEqual(dashboard["module"], "daily_recommendation_policy_signal_quality")
        self.assertEqual(dashboard["level_counts"]["theme"], 1)
        self.assertEqual(dashboard["level_counts"]["market"], 1)
        self.assertEqual(dashboard["score_applied_count"], 1)
        self.assertEqual(dashboard["review_count"], 1)
        self.assertEqual(dashboard["total_policy_net_points"], 2)
        self.assertEqual(dashboard["rows"][0]["review_status"], "review")
        self.assertEqual(dashboard["rows"][1]["review_status"], "info")

    def test_daily_recommendation_policy_signal_quality_allows_theme_reference_without_review(self):
        from research_os import daily_recommendation_policy

        dashboard = daily_recommendation_policy.build_policy_signal_quality_dashboard(
            {
                "latest_recommendation_date": "2026-06-25",
                "latest_records": [
                    {
                        "market": "US",
                        "rank": 1,
                        "ticker": "ABSI",
                        "company_name": "Absci",
                        "policy_signal_summary": {
                            "match_level": "theme",
                            "match_level_label": "테마",
                            "score_applied": False,
                            "direct_count": 0,
                            "theme_count": 3,
                            "market_count": 3,
                        },
                        "score_components": [],
                        "score_penalties": [],
                    }
                ],
            }
        )

        self.assertEqual(dashboard["review_count"], 0)
        self.assertEqual(dashboard["rows"][0]["review_status"], "info")


class DailyRecommendationProfilesModuleTests(unittest.TestCase):
    def test_daily_recommendation_profiles_apply_freshness_and_overseas_tracking(self):
        from types import SimpleNamespace

        from research_os import daily_recommendation_profiles

        candidate = {
            "ticker": "PL",
            "company_name": "PL",
            "currency": "USD",
            "baseline_price": 5.7,
            "baseline_price_source": "finnhub",
            "baseline_price_checked_at": "2026-06-18T08:00:00+09:00",
            "score": 0,
            "score_components": [],
            "score_penalties": [],
            "quality_flags": [],
            "evidence_sources": [],
            "reasons": [],
        }

        daily_recommendation_profiles.apply_daily_recommendation_freshness_profile(
            candidate,
            ticker="PL",
            verification=SimpleNamespace(company_name="Planet Labs PBC"),
            profile={"analysis_focus": "위성 데이터 성장성"},
            freshness={"tone": "warning", "summary": "최근 자료 신선도 확인 필요"},
        )
        daily_recommendation_profiles.apply_daily_recommendation_overseas_tracking(candidate)
        domestic = daily_recommendation_profiles.apply_daily_recommendation_overseas_tracking({"currency": "KRW"})

        self.assertEqual(candidate["company_name"], "Planet Labs PBC")
        self.assertEqual(candidate["score"], 3)
        self.assertIn("저장자료 신선도 확인 필요", candidate["quality_flags"])
        self.assertIn("최근 자료 신선도 보강 필요 (-2)", candidate["score_penalties"])
        self.assertIn("분석 초점: 위성 데이터 성장성", candidate["reasons"])
        self.assertTrue(candidate["overseas_tracking"]["needs_fx_conversion"])
        self.assertEqual(candidate["overseas_tracking"]["price_source"], "finnhub")
        self.assertFalse(domestic["overseas_tracking"]["needs_fx_conversion"])


class DailyRecommendationRecentModuleTests(unittest.TestCase):
    def test_daily_recommendation_recent_module_indexes_and_renders_weekly_evidence(self):
        from research_os import daily_recommendation_recent

        recent_weekly = {
            "important_filings": [
                {
                    "ticker": "003230",
                    "title": "삼양식품 공시",
                    "relative_path": "research_vault/003230/filing.md",
                    "category": "filing",
                    "recommendation_usage_summary": "공시 확인",
                    "date": "2026-06-18",
                }
            ],
            "category_groups": [
                {
                    "key": "public_ir_sec",
                    "label": "공개 IR/SEC",
                    "tickers": ["003230"],
                    "count": 3,
                    "visible_count": 2,
                    "ticker_count": 1,
                    "items": [{"ticker": "003230", "summary": "수출 성장 자료"}],
                    "quality_summary": {
                        "usable_for_recommendation": 2,
                        "needs_body_copy": 1,
                        "source_families": {"sec.gov": 2},
                        "reliability_labels": {"신뢰 가능": 2},
                    },
                }
            ],
        }

        index = daily_recommendation_recent.daily_recommendation_recent_weekly_index(recent_weekly)
        document = daily_recommendation_recent.daily_recommendation_recent_item_evidence_document(
            recent_weekly["important_filings"][0]
        )
        group_text = daily_recommendation_recent.daily_recommendation_weekly_group_evidence_text(
            index["groups_by_ticker"]["003230"][0]
        )

        self.assertEqual(index["items_by_ticker"]["003230"][0]["category"], "filing")
        self.assertEqual(document["citation_label"], "최근 1주 추천 영향 자료")
        self.assertEqual(document["matched_claims"], ["공시 확인"])
        self.assertIn("공개 IR/SEC 3건", group_text)
        self.assertIn("추천 가능 2건", group_text)

    def test_daily_recommendation_recent_module_applies_recent_weekly_evidence(self):
        from research_os import daily_recommendation_recent

        candidate = {
            "score": 0,
            "score_components": [],
            "reasons": [],
            "evidence_sources": [],
            "risk_notes": [],
            "quality_flags": [],
            "evidence_documents": [],
        }

        updated = daily_recommendation_recent.apply_daily_recommendation_recent_weekly_evidence(
            candidate,
            [
                {
                    "category": "filing",
                    "title": "삼양식품 공시",
                    "relative_path": "research_vault/003230/filing.md",
                    "recommendation_usage_summary": "공시 확인",
                },
                {
                    "category": "report",
                    "title": "삼양식품 리포트",
                    "relative_path": "research_vault/003230/report.md",
                },
                {
                    "category": "public_ir_sec",
                    "usable_for_recommendation": True,
                    "title": "IR 자료",
                    "relative_path": "research_vault/003230/ir.md",
                },
                {"category": "public_ir_sec", "usable_for_recommendation": False},
            ],
            [
                {"key": "filing", "label": "중요 공시", "count": 1, "visible_count": 1, "ticker_count": 1},
                {"key": "filing", "label": "중요 공시 중복", "count": 1},
            ],
        )

        labels = [component["label"] for component in candidate["score_components"]]
        self.assertIs(updated, candidate)
        self.assertIn("최근 중요 공시 반영", labels)
        self.assertIn("최근 핵심 리포트 반영", labels)
        self.assertIn("최근 공개 IR/SEC 반영", labels)
        self.assertIn("공개 IR/SEC 본문 보강 필요", candidate["quality_flags"])
        self.assertEqual(len(candidate["evidence_documents"]), 3)
        self.assertEqual(len(candidate["weekly_evidence_groups"]), 1)
        self.assertTrue(any(item.startswith("최근 1주 자료 묶음:") for item in candidate["evidence_sources"]))

class DailyRecommendationTrackingModuleTests(unittest.TestCase):
    def test_daily_recommendation_tracking_builds_milestones_and_summary(self):
        from datetime import date

        from research_os import daily_recommendation_tracking

        milestones = daily_recommendation_tracking.build_tracking_milestones(date(2026, 6, 18))
        summary = daily_recommendation_tracking.summarize_tracking_performance(
            [
                {
                    "record_id": "20260618-1-003230",
                    "company_name": "삼양식품",
                    "ticker": "003230",
                    "rank": 1,
                    "recommendation_date": "2026-06-18",
                    "baseline_price": 100.0,
                    "tracking_milestones": [
                        {
                            "key": "7d",
                            "label": "추천 후 1주일",
                            "target_date": "2026-06-25",
                            "status": "complete",
                            "price": 112.0,
                            "price_change": 12.0,
                            "price_change_pct": 0.12,
                            "investment_situation": "상승",
                        },
                        {"key": "15d", "status": "pending"},
                    ],
                },
                {
                    "record_id": "20260618-2-071050",
                    "ticker": "071050",
                    "rank": 2,
                    "recommendation_date": "2026-06-18",
                    "baseline_price": 50.0,
                    "tracking_milestones": [
                        {
                            "key": "7d",
                            "label": "추천 후 1주일",
                            "target_date": "2026-06-25",
                            "status": "complete",
                            "price": 45.0,
                            "price_change": -5.0,
                            "price_change_pct": -0.1,
                        }
                    ],
                },
            ]
        )

        self.assertEqual(milestones[0]["target_date"], "2026-06-25")
        self.assertEqual(milestones[0]["status"], "pending")
        self.assertEqual(summary["total_milestones"], 3)
        self.assertEqual(summary["complete_count"], 2)
        self.assertEqual(summary["pending_count"], 1)
        self.assertEqual(summary["best"]["ticker"], "003230")
        self.assertEqual(summary["worst"]["ticker"], "071050")
        self.assertIn("강한 상승", daily_recommendation_tracking.investment_situation(0.16))
        self.assertEqual(
            daily_recommendation_tracking.saved_portfolio_price_lookup(
                {
                    "portfolios": [
                        {
                            "holdings": [
                                {
                                    "ticker": "absi",
                                    "current_price": "6.10",
                                    "price_source": "stale",
                                    "price_checked_at": "2026-06-17T08:00:00+09:00",
                                },
                                {
                                    "ticker": "ABSI",
                                    "current_price": "6.40",
                                    "price_source": "finnhub",
                                    "price_checked_at": "2026-06-18T08:00:00+09:00",
                                },
                                {"ticker": "PL", "current_price": ""},
                            ]
                        }
                    ]
                }
            ),
            {"ABSI": (6.4, "saved_portfolio:finnhub")},
        )

    def test_daily_recommendation_tracking_module_builds_and_applies_feedback(self):
        from research_os import daily_recommendation_tracking

        feedback = daily_recommendation_tracking.daily_recommendation_tracking_feedback(
            [
                {
                    "ticker": "OTLY",
                    "tracking_milestones": [
                        {"key": "7d", "label": "추천 후 1주일", "status": "complete", "price_change_pct": -0.12},
                        {"key": "15d", "label": "추천 후 15일", "status": "complete", "price_change_pct": -0.10},
                        {"key": "15d", "label": "추천 후 15일", "status": "complete", "price_change_pct": -0.08},
                    ],
                }
            ]
        )
        candidate = {"score": 20, "score_penalties": [], "risk_notes": [], "quality_flags": [], "evidence_sources": []}

        daily_recommendation_tracking.apply_daily_recommendation_tracking_feedback(candidate, feedback["OTLY"])

        self.assertEqual(feedback["OTLY"]["penalty_points"], 16)
        self.assertEqual(feedback["OTLY"]["horizon_penalty_points"], 4)
        self.assertTrue(candidate["tracking_feedback_profile"]["review_hold"])
        self.assertTrue(daily_recommendation_tracking.daily_recommendation_candidate_review_hold(candidate))
        self.assertEqual(candidate["score"], 4)
        self.assertIn("반복 부진 후보 top3 보류", candidate["quality_flags"])

    def test_daily_recommendation_tracking_hold_includes_low_hit_rate_repeat_underperformer(self):
        from research_os import daily_recommendation_tracking

        candidate = {"score": 30, "score_penalties": [], "risk_notes": [], "quality_flags": [], "evidence_sources": []}
        feedback = {
            "completed_count": 5,
            "hit_rate": 0.1,
            "average_change_pct": -0.085,
            "penalty_points": 12,
            "horizon_penalty_points": 0,
        }

        daily_recommendation_tracking.apply_daily_recommendation_tracking_feedback(candidate, feedback)

        self.assertTrue(candidate["tracking_feedback_profile"]["review_hold"])
        self.assertTrue(daily_recommendation_tracking.daily_recommendation_candidate_review_hold(candidate))

    def test_daily_recommendation_price_lookup_falls_back_to_naver_domestic_basic(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(naver_finance_enabled=True, naver_finance_timeout_seconds=6)

        with (
            patch.object(main, "latest_provider_price", return_value=(None, "provider-missing")),
            patch.object(main, "read_portfolio_store", return_value={"portfolios": {}}),
            patch.object(
                main,
                "fetch_naver_domestic_stock_basic",
                return_value={"stockName": "한국금융지주", "closePrice": "249,500"},
            ),
        ):
            price, source = main._daily_recommendation_price_lookup(settings)("071050")

        self.assertEqual(price, 249500.0)
        self.assertEqual(source, "https://m.stock.naver.com/api/stock/071050/basic")

    def test_daily_recommendation_price_lookup_prefers_naver_over_ambiguous_domestic_provider(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(naver_finance_enabled=True, naver_finance_timeout_seconds=6)

        with (
            patch.object(main, "latest_provider_price", return_value=(367.0, "data_provider")),
            patch.object(main, "fetch_naver_domestic_stock_basic", return_value={"stockName": "한국금융지주", "closePrice": "233,000"}),
        ):
            price, source = main._daily_recommendation_price_lookup(settings)("071050")

        self.assertEqual(price, 233000.0)
        self.assertEqual(source, "https://m.stock.naver.com/api/stock/071050/basic")

    def test_daily_recommendation_price_lookup_prefers_saved_over_ambiguous_overseas_provider(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings()

        with (
            patch.object(main, "latest_provider_price", return_value=(378.5, "data_provider")),
            patch.object(
                main,
                "read_portfolio_store",
                return_value={
                    "portfolios": {
                        "MAIN": {
                            "holdings": [
                                {
                                    "ticker": "OTLY",
                                    "current_price": 8.19,
                                    "price_source": "https://openapi.koreainvestment.com/overseas",
                                    "price_checked_at": "2026-06-18T16:23:39+09:00",
                                }
                            ]
                        }
                    }
                },
            ),
        ):
            price, source = main._daily_recommendation_price_lookup(settings)("OTLY")

        self.assertEqual(price, 8.19)
        self.assertEqual(source, "saved_portfolio:https://openapi.koreainvestment.com/overseas")


class RecentActivityGroupsModuleTests(unittest.TestCase):
    def test_recent_activity_groups_build_quality_summary_and_digest(self):
        from research_os import recent_activity_groups

        items = [
            {
                "ticker": "PL",
                "company_name": "Planet Labs",
                "related_targets": ["Space"],
                "source_provider": "https://ir.planet.com/releases",
                "source_reliability": "공식 IR",
                "usable_for_recommendation": True,
                "used_in_recommendation": True,
            },
            {
                "ticker": "JOBY",
                "company_name": "Joby Aviation",
                "source_provider": "www.example.co.kr/path",
                "needs_body_copy": True,
                "quality_status": "보강 필요",
            },
        ]

        group = recent_activity_groups.recent_weekly_category_group("공개 IR/SEC", "public_ir_sec", items, limit=1)
        digest = recent_activity_groups.build_recent_weekly_target_digest(
            sources=[("public_ir_sec", items), ("market", [{"summary": "macro"}])]
        )

        self.assertEqual(recent_activity_groups.recent_weekly_source_family("ir.jobyaviation.com"), "jobyaviation.com")
        self.assertEqual(group["visible_count"], 1)
        self.assertEqual(group["quality_summary"]["usable_for_recommendation"], 1)
        self.assertEqual(group["quality_summary"]["needs_body_copy"], 1)
        self.assertEqual(group["quality_summary"]["source_families"]["planet.com"], 1)
        self.assertEqual(group["quality_summary"]["source_families"]["example.co.kr"], 1)
        self.assertEqual(digest[0]["target"], "Joby Aviation")
        self.assertTrue(any(item["target"] == "시장/섹터 공통" for item in digest))


class RecentActivityNavigationModuleTests(unittest.TestCase):
    def test_recent_activity_navigation_links_recommendations_and_dedupes_items(self):
        from research_os import recent_activity_navigation

        items = [
            {
                "category": "report",
                "date": "2026-06-18",
                "ticker": "PL",
                "company_name": "Planet Labs",
                "report_type": "broker-report",
                "summary": "Planet Labs update",
                "relative_path": "research_vault/PL/report.md",
            },
            {
                "category": "report",
                "date": "2026-06-18",
                "ticker": "pl",
                "company_name": "Planet Labs",
                "report_type": "broker-report",
                "summary": "Planet Labs update",
                "relative_path": "research_vault/PL/report.md",
            },
        ]
        evidence_index = {
            "by_relative_path": {
                "research_vault/pl/report.md": [
                    {
                        "record_id": "r1",
                        "recommendation_date": "2026-06-18",
                        "rank": 1,
                        "ticker": "PL",
                        "company_name": "Planet Labs",
                        "is_latest": True,
                    }
                ]
            }
        }

        recent_activity_navigation.annotate_recent_weekly_recommendation_links(items, evidence_index)
        recent_activity_navigation.annotate_recent_weekly_navigation_hints(items)
        deduped = recent_activity_navigation.dedupe_recent_activity_items(items)

        self.assertEqual(len(deduped), 1)
        self.assertEqual(items[0]["recommendation_usage_label"], "오늘 추천 근거")
        self.assertEqual(items[0]["memory_lookup_key"], "PL")
        self.assertIn("저장 데이터 탭", items[0]["memory_navigation_hint"])
        self.assertIn("Planet Labs", items[0]["rag_search_query"])


class ThesisImpactModuleTests(unittest.TestCase):
    def test_thesis_impact_module_scores_positive_evidence_and_renders_markdown(self):
        from research_os import thesis_impact
        from research_os.models import DataSourceType, InjectedDataPoint, InvestmentThesis, ThesisImpact, WatchItem

        response = thesis_impact.evaluate_thesis_impact(
            "003230",
            [
                InjectedDataPoint(
                    source_type=DataSourceType.USER_MEMO,
                    label="earnings",
                    value="strong growth and margin expansion",
                    confidence=0.9,
                )
            ],
            [
                InvestmentThesis(
                    ticker="003230",
                    thesis="수출 성장",
                    time_horizon="12m",
                    last_updated="2026-06-18",
                )
            ],
            [
                WatchItem(
                    ticker="003230",
                    metric="growth",
                    condition="상승",
                    action="비중 유지",
                    priority="high",
                )
            ],
        )
        markdown = thesis_impact.render_thesis_impact_markdown(response, date(2026, 6, 18))

        self.assertEqual(response.overall_impact, ThesisImpact.STRENGTHENS)
        self.assertEqual(response.watch_item_signals[0].action, "비중 유지")
        self.assertIn("overall_impact: 강화", markdown)
        self.assertIn("투자 논거 영향도 분석", markdown)
    def test_thesis_impact_module_extracts_manifest_fallback_context(self):
        from research_os import thesis_impact

        runtime = SimpleNamespace(
            read_ticker_thesis_context=lambda _vault_dir, _ticker: ([], []),
            read_manifest=lambda _vault_dir: [
                {
                    "ticker": "003230",
                    "investment_thesis": {
                        "ticker": "003230",
                        "thesis": "수출 성장",
                        "time_horizon": "12m",
                        "last_updated": "2026-06-18",
                    },
                    "watch_items": [
                        {
                            "ticker": "003230",
                            "metric": "수출",
                            "condition": "증가",
                            "action": "비중 유지",
                            "priority": "high",
                        }
                    ],
                },
                {"ticker": "OTHER", "investment_thesis": {"ticker": "OTHER", "thesis": "제외", "time_horizon": "12m", "last_updated": "2026-06-18"}},
            ],
        )

        theses, watch_items = thesis_impact.extract_manifest_theses_and_watch_items(
            runtime,
            "003230",
            Path("vault"),
        )

        self.assertEqual([item.thesis for item in theses], ["수출 성장"])
        self.assertEqual([item.metric for item in watch_items], ["수출"])

class ThesisSignalWordsModuleTests(unittest.TestCase):
    def test_signal_words_match_korean_and_english_terms(self):
        from research_os import thesis_signal_words

        self.assertTrue(
            thesis_signal_words.text_has_any(
                "매출 성장과 margin expansion이 동시에 확인됩니다.",
                thesis_signal_words.POSITIVE_SIGNAL_WORDS,
            )
        )
        self.assertTrue(
            thesis_signal_words.text_has_any(
                "수요 둔화와 cost pressure가 이어집니다.",
                thesis_signal_words.NEGATIVE_SIGNAL_WORDS,
            )
        )
        self.assertFalse(
            thesis_signal_words.text_has_any(
                "특별한 방향성 없이 보합권입니다.",
                thesis_signal_words.POSITIVE_SIGNAL_WORDS,
            )
        )

class DashboardHelpersModuleTests(unittest.TestCase):
    def test_dashboard_helpers_render_report_summary_and_watch_items(self):
        from research_os import dashboard_helpers

        summary = dashboard_helpers.dashboard_report_summary(
            {
                "type": "thesis-impact-review",
                "file_name": "003230-thesis-impact-review-2026-06-18.md",
                "relative_path": "research_vault/003230/report.md",
                "date": "2026-06-18",
                "summary": "기존 논거를 강화하는 신규 수출 데이터",
                "overall_impact": "strengthens",
                "findings": [
                    {
                        "thesis_reference": "수출 성장",
                        "rationale": "미국 채널 주문 증가",
                    }
                ],
                "next_actions": ["다음 실적 발표 확인"],
            }
        )
        watch_item = dashboard_helpers.render_dashboard_watch_item(
            {
                "metric": "매출 성장률",
                "condition": "전년 대비 20% 이상",
                "action": "비중 유지",
                "priority": "high",
            }
        )
        report_type = dashboard_helpers.infer_report_type_from_file(
            "003230-portfolio-risk-scan-2026-06-18.md"
        )
        report_date = dashboard_helpers.infer_report_date_from_file(
            "003230-portfolio-risk-scan-2026-06-18.md"
        )

        self.assertEqual(summary.impact_label, "strengthens")
        self.assertIn("수출 성장", summary.impact_reason)
        self.assertEqual(watch_item, "[높음] 매출 성장률: 전년 대비 20% 이상 -> 비중 유지")
        self.assertEqual(report_type, "portfolio-risk-scan")
        self.assertEqual(report_date, "2026-06-18")
    def test_dashboard_helpers_build_reference_digests(self):
        from research_os import dashboard_helpers

        payloads = {
            "003230-dossier-synthesis-2026-06-18.md": {
                "company_name": "Samyang Foods",
                "thesis_summary": "수출 성장 논거 강화",
                "confidence": "high",
                "source_count": 5,
                "duplicate_count": 1,
                "consensus_facts": ["미국 매출 증가", "채널 확장"],
            },
            "003230-research-capture-2026-06-18.md": {
                "attachment": {
                    "file_name": "ir.pdf",
                    "document_type": "IR",
                    "extraction_quality": "0.8",
                    "extraction_profile": {"analysis_readiness": "ready"},
                    "extraction_char_count": 2400,
                }
            },
        }
        runtime = SimpleNamespace(
            read_manifest_entry_payload=lambda entry, _vault_dir: payloads.get(entry.get("file_name"), {}),
            read_market_close_journal=lambda _settings: {
                "entries": [
                    {"market": "US", "session_date": "2026-06-17", "sentiment": "neutral"},
                    {
                        "market": "US",
                        "session_date": "2026-06-18",
                        "sentiment": "positive",
                        "key_drivers": ["AI", "금리", "달러", "유가", "기타"],
                    },
                ]
            },
            ticker_company_name=lambda ticker: f"{ticker} Inc.",
        )
        entries = [
            {
                "type": "dossier-synthesis",
                "file_name": "003230-dossier-synthesis-2026-06-17.md",
                "date": "2026-06-17",
            },
            {
                "type": "dossier-synthesis",
                "file_name": "003230-dossier-synthesis-2026-06-18.md",
                "date": "2026-06-18",
            },
            {
                "type": "research-capture",
                "file_name": "003230-research-capture-2026-06-18.md",
                "date": "2026-06-18",
                "relative_path": "research_vault/003230/ir.md",
            },
            {
                "type": "team-report",
                "file_name": "003230-team-report-2026-06-18.md",
                "date": "2026-06-18",
                "investment_thesis": {"ticker": "003230", "thesis": "수출 성장"},
                "watch_items": [{"metric": "수출"}],
            },
        ]

        latest = dashboard_helpers.latest_manifest_entry(entries, "dossier-synthesis")
        dossier = dashboard_helpers.build_latest_dossier_preview(runtime, "003230", entries, Path("vault"))
        digest = dashboard_helpers.build_document_quality_digest(runtime, "003230", entries, Path("vault"))
        journal = dashboard_helpers.build_latest_market_journal_reference(runtime, SimpleNamespace())
        thesis = dashboard_helpers.latest_manifest_thesis_snapshot("003230", entries)

        self.assertEqual(latest["file_name"], "003230-dossier-synthesis-2026-06-18.md")
        self.assertEqual(dossier["company_name"], "Samyang Foods")
        self.assertEqual(digest["headline"], "추출 품질 양호")
        self.assertEqual(digest["latest"]["document_type"], "IR")
        self.assertEqual(journal["session_date"], "2026-06-18")
        self.assertEqual(journal["key_drivers"], ["AI", "금리", "달러", "유가"])
        self.assertEqual(thesis["thesis_summary"], "수출 성장")

class ResearchMemoryFilesModuleTests(unittest.TestCase):
    def test_research_memory_files_module_resolves_payload_paths_and_updates_tail_sections(self):
        from research_os import research_memory_files

        test_tmp_dir = PROJECT_ROOT / ".test-tmp"
        test_tmp_dir.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=test_tmp_dir, ignore_cleanup_errors=True) as temp_dir:
            vault_dir = Path(temp_dir) / "research_vault"
            ticker_dir = vault_dir / "POLICY"
            attachment_dir = ticker_dir / "_attachments"
            attachment_dir.mkdir(parents=True)
            markdown_path = ticker_dir / "POLICY-research-capture-2026-06-13-test.md"
            json_path = markdown_path.with_suffix(".json")
            attachment_path = attachment_dir / "policy.pdf"
            markdown_path.write_text("# 정책 자료\n\n본문", encoding="utf-8")
            json_path.write_text(json.dumps({"raw_content": "본문"}, ensure_ascii=False), encoding="utf-8")
            attachment_path.write_bytes(b"pdf")
            entry = {
                "ticker": "POLICY",
                "file_name": markdown_path.name,
                "relative_path": markdown_path.relative_to(vault_dir.parent).as_posix(),
                "json_relative_path": json_path.relative_to(vault_dir.parent).as_posix(),
            }

            payload = research_memory_files.read_manifest_entry_payload(entry, vault_dir)
            resolved_json = research_memory_files.manifest_entry_json_path(entry, vault_dir)
            resolved_markdown = research_memory_files.manifest_entry_markdown_path(entry, vault_dir)
            updated = research_memory_files.upsert_markdown_tail_section(
                markdown_path,
                "## OCR 재처리 결과",
                "- 처리 상태: 완료",
            )
            updated_again = research_memory_files.upsert_markdown_tail_section(
                markdown_path,
                "## OCR 재처리 결과",
                "- 처리 상태: 완료",
            )
            resolved_attachment = research_memory_files.resolve_attachment_file_path(
                vault_dir,
                {"relative_path": attachment_path.relative_to(vault_dir).as_posix()},
            )
            escaped_attachment = research_memory_files.resolve_attachment_file_path(
                vault_dir,
                {"relative_path": "../outside.pdf"},
            )

        self.assertEqual(payload["raw_content"], "본문")
        self.assertEqual(resolved_json, json_path.resolve())
        self.assertEqual(resolved_markdown, markdown_path.resolve())
        self.assertTrue(updated)
        self.assertFalse(updated_again)
        self.assertEqual(resolved_attachment, attachment_path.resolve())
        self.assertIsNone(escaped_attachment)

    def test_research_memory_files_module_lists_visible_and_archived_entries(self):
        from research_os import research_memory_files

        quality_metadata = {
            "tags": ["market-journal"],
            "source_url_processing": {},
            "capture_quality": {"status": "complete"},
            "data_quality_status": "ready",
            "needs_body_copy": False,
            "url_text_unavailable": False,
        }
        runtime = SimpleNamespace(
            infer_report_type_from_file=lambda _name: "saved-report",
            is_archived_research_entry=lambda entry, payload=None: bool(
                (entry or {}).get("status") == "archived"
                or (isinstance(payload, dict) and payload.get("is_deleted"))
            ),
            is_verified_manifest_entry=lambda entry, ticker: bool(
                (entry.get("ticker_verification") or {}).get("official_symbol") == ticker
                and (entry.get("ticker_verification") or {}).get("verified") is True
            ),
            normalize_ticker=lambda value: str(value or "").upper(),
            read_manifest=lambda _vault_dir: manifest_entries,
            research_memory_entry_quality_metadata=lambda *_args: quality_metadata,
            special_research_keys={"MARKET-US"},
        )

        test_tmp_dir = PROJECT_ROOT / ".test-tmp"
        test_tmp_dir.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=test_tmp_dir, ignore_cleanup_errors=True) as temp_dir:
            vault_dir = Path(temp_dir) / "research_vault"
            ticker_dir = vault_dir / "MARKET-US"
            ticker_dir.mkdir(parents=True)
            active_path = ticker_dir / "MARKET-US-research-capture-2026-06-16.md"
            active_json_path = active_path.with_suffix(".json")
            archived_path = ticker_dir / "MARKET-US-research-capture-2026-06-15.md"
            archived_json_path = archived_path.with_suffix(".json")
            active_path.write_text("# 미국 시장일지", encoding="utf-8")
            active_json_path.write_text(
                json.dumps(
                    {
                        "status": "success",
                        "module": "research_quick_capture",
                        "captured_item": {"ticker": "market-us", "summary": "미국장 마감"},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            archived_path.write_text("# 이전 시장일지", encoding="utf-8")
            archived_json_path.write_text(
                json.dumps({"captured_item": {"ticker": "MARKET-US"}}, ensure_ascii=False),
                encoding="utf-8",
            )
            manifest_entries = [
                {
                    "ticker": "MARKET-US",
                    "file_name": archived_path.name,
                    "type": "research-capture",
                    "status": "archived",
                    "archive_reason": "duplicate",
                    "archived_at": "2026-06-16T00:00:00+09:00",
                }
            ]

            visible = research_memory_files.list_research_memory_files(runtime, "MARKET-US", vault_dir)
            all_files = research_memory_files.list_research_memory_files(
                runtime,
                "MARKET-US",
                vault_dir,
                include_archived=True,
            )

        self.assertEqual([file.file_name for file in visible], [active_path.name])
        self.assertTrue(visible[0].verified)
        self.assertEqual(visible[0].status_label, "저장 메타 확인")
        self.assertEqual(visible[0].report_type, "research-capture")
        self.assertEqual(len(all_files), 2)
        archived = next(file for file in all_files if file.file_name == archived_path.name)
        self.assertTrue(archived.archived)
        self.assertTrue(archived.is_deleted)
        self.assertEqual(archived.archive_reason, "duplicate")

    def test_research_memory_files_module_infers_specific_type_from_saved_report_manifest(self):
        from research_os import dashboard_helpers, research_memory_files

        quality_metadata = {
            "tags": [],
            "source_url_processing": {},
            "capture_quality": {"status": "complete"},
            "data_quality_status": "ready",
            "needs_body_copy": False,
            "url_text_unavailable": False,
        }
        runtime = SimpleNamespace(
            infer_report_type_from_file=dashboard_helpers.infer_report_type_from_file,
            is_archived_research_entry=lambda entry, payload=None: False,
            is_verified_manifest_entry=lambda entry, ticker: True,
            normalize_ticker=lambda value: str(value or "").upper(),
            read_manifest=lambda _vault_dir: manifest_entries,
            research_memory_entry_quality_metadata=lambda *_args: quality_metadata,
            special_research_keys=set(),
        )

        test_tmp_dir = PROJECT_ROOT / ".test-tmp"
        test_tmp_dir.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=test_tmp_dir, ignore_cleanup_errors=True) as temp_dir:
            vault_dir = Path(temp_dir) / "research_vault"
            ticker_dir = vault_dir / "003230"
            ticker_dir.mkdir(parents=True)
            report_path = ticker_dir / "003230-thesis-impact-review-2026-05-24.md"
            report_path.write_text("# 삼양식품", encoding="utf-8")
            manifest_entries = [
                {
                    "ticker": "003230",
                    "file_name": report_path.name,
                    "type": "saved-report",
                    "ticker_verification": {"official_symbol": "003230", "verified": True},
                }
            ]

            files = research_memory_files.list_research_memory_files(runtime, "003230", vault_dir)

        self.assertEqual(files[0].report_type, "thesis-impact-review")

class ResearchMemoryQualityRebuildModuleTests(unittest.TestCase):
    def test_quality_rebuild_module_updates_manifest_sidecar_markdown_and_rag(self):
        from research_os import research_memory_quality_rebuild

        updated_entries = []
        rag_updates = []

        test_tmp_dir = PROJECT_ROOT / ".test-tmp"
        test_tmp_dir.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=test_tmp_dir, ignore_cleanup_errors=True) as temp_dir:
            vault_dir = Path(temp_dir) / "research_vault"
            ticker_dir = vault_dir / "POLICY"
            ticker_dir.mkdir(parents=True)
            markdown_path = ticker_dir / "POLICY-research-capture-2026-06-13-test.md"
            json_path = markdown_path.with_suffix(".json")
            markdown_path.write_text("# 정책 자료\n\n코스닥 정책 메모", encoding="utf-8")
            entry = {
                "ticker": "POLICY",
                "type": "research-capture",
                "file_name": markdown_path.name,
                "summary": "첨부 중심 저장",
                "tags": ["auto_classified"],
                "attachment": {"file_name": "kosdaq.pdf", "mime_type": "application/pdf"},
                "capture_quality": {"status": "실패"},
            }
            payload = {
                "raw_content": "코스닥 활성화 정책",
                "captured_item": {"summary": "첨부 중심 저장", "tags": ["auto_classified"]},
                "attachment": {"file_name": "kosdaq.pdf", "mime_type": "application/pdf"},
                "capture_quality": {"status": "실패"},
            }
            json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

            def merge_tags(*groups):
                merged = []
                for group in groups:
                    for tag in group or []:
                        if tag not in merged:
                            merged.append(tag)
                return merged

            runtime = SimpleNamespace(
                resolve_vault_dir=lambda value: Path(value),
                read_manifest=lambda _vault_dir: [entry],
                current_storage_timestamp=lambda: "2026-06-13T08:00:00+09:00",
                is_archived_research_entry=lambda _entry: False,
                read_manifest_entry_payload=lambda _entry, _vault_dir: json.loads(json_path.read_text(encoding="utf-8")),
                read_manifest_entry_text=lambda _vault_dir, _entry: markdown_path.read_text(encoding="utf-8"),
                render_attachment_signal_context=lambda file_name, _mime_type, _note: f"첨부 파일명: {file_name}",
                plain_research_lines=lambda value, limit=80: str(value).splitlines()[:limit],
                manifest_entry_markdown_path=lambda _entry, _vault_dir: markdown_path,
                infer_capture_investment_scope=lambda _context, _settings: {
                    "tags": ["theme:kosdaq"],
                    "theme_candidates": [{"label": "코스닥"}],
                    "matched_interest_tickers": [],
                    "matched_interest_sectors": [{"name": "코스닥"}],
                    "matched_portfolio_holdings": [],
                },
                render_investment_scope_context=lambda _scope: "관심 범위 후보: 코스닥",
                merge_research_tags=merge_tags,
                compact_representative_sentence=lambda text, _limit: text,
                update_manifest=lambda **kwargs: updated_entries.append(kwargs["entry"]),
                manifest_entry_json_path=lambda _entry, _vault_dir: json_path,
                upsert_research_memory_document=lambda **kwargs: rag_updates.append(kwargs),
                backfill_research_memory_documents_from_manifest=lambda _vault_dir: {"updated_count": 1},
                backfill_thesis_snapshots_from_manifest=lambda _vault_dir: {"updated_count": 1},
            )

            result = research_memory_quality_rebuild.rebuild_research_memory_quality_metadata(
                runtime,
                SimpleNamespace(research_vault_dir=str(vault_dir)),
            )
            updated_payload = json.loads(json_path.read_text(encoding="utf-8"))
            updated_markdown = markdown_path.read_text(encoding="utf-8")

        self.assertEqual(result["enriched_count"], 1)
        self.assertEqual(result["markdown_updated_count"], 1)
        self.assertEqual(result["sidecar_updated_count"], 1)
        self.assertIn("theme:kosdaq", updated_entries[0]["tags"])
        self.assertEqual(updated_entries[0]["capture_quality"]["status"], "보강 필요")
        self.assertTrue(updated_payload["capture_quality"]["metadata_enriched"])
        self.assertIn("theme:kosdaq", updated_payload["captured_item"]["tags"])
        self.assertIn("관심 범위 후보: 코스닥", updated_markdown)
        self.assertIn("관심 범위 후보: 코스닥", rag_updates[0]["full_text"])


class ResearchMemoryOcrModuleTests(unittest.TestCase):
    def test_research_memory_ocr_module_updates_attachment_sidecar_markdown_and_rag(self):
        from research_os import research_memory_ocr

        updated_entries = []
        markdown_updates = []
        rag_updates = []

        test_tmp_dir = PROJECT_ROOT / ".test-tmp"
        test_tmp_dir.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=test_tmp_dir, ignore_cleanup_errors=True) as temp_dir:
            vault_dir = Path(temp_dir) / "research_vault"
            ticker_dir = vault_dir / "POLICY"
            attachment_dir = ticker_dir / "_attachments"
            attachment_dir.mkdir(parents=True)
            attachment_path = attachment_dir / "policy-scan.pdf"
            attachment_path.write_bytes(b"%PDF-1.4 scan")
            markdown_path = ticker_dir / "POLICY-research-capture-2026-06-13-test.md"
            json_path = markdown_path.with_suffix(".json")
            markdown_path.write_text("# 정책 자료\n\n첨부 본문 없음", encoding="utf-8")
            attachment = {
                "file_name": "policy-scan.pdf",
                "mime_type": "application/pdf",
                "relative_path": attachment_path.relative_to(vault_dir).as_posix(),
                "text_extraction": "OCR 언어팩 누락",
                "extracted_text": "",
                "extraction_char_count": 0,
                "extraction_profile": {"ocr_status": "unavailable"},
            }
            entry = {
                "ticker": "POLICY",
                "file_name": markdown_path.name,
                "summary": "첨부 본문 없음",
                "tags": [],
                "attachment": attachment,
                "capture_quality": {"status": "보강 필요"},
            }
            json_path.write_text(
                json.dumps(
                    {
                        "raw_content": "코스닥 정책",
                        "attachment": attachment,
                        "capture_quality": {"status": "보강 필요"},
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            def merge_tags(*groups):
                merged = []
                for group in groups:
                    for tag in group or []:
                        if tag not in merged:
                            merged.append(tag)
                return merged

            runtime = SimpleNamespace(
                resolve_vault_dir=lambda value: Path(value),
                read_manifest=lambda _vault_dir: [entry],
                is_archived_research_entry=lambda _entry: False,
                is_pdf_attachment=lambda file_name, mime_type: str(file_name).endswith(".pdf") or mime_type == "application/pdf",
                is_image_attachment=lambda _file_name, _mime_type: False,
                resolve_attachment_file_path=lambda _vault_dir, _attachment: attachment_path,
                extract_uploaded_file_text=lambda *_args, **_kwargs: {
                    "text_extraction": "OCR 텍스트 추출 완료",
                    "extracted_text": "코스닥 활성화 정책 본문",
                    "document_type": "PDF",
                    "extraction_quality": 0.91,
                    "extraction_char_count": 14,
                    "extraction_preview": "코스닥 활성화",
                    "extraction_warnings": [],
                    "extraction_profile": {"ocr_status": "success", "ocr_language": "kor+eng"},
                },
                read_manifest_entry_payload=lambda _entry, _vault_dir: json.loads(json_path.read_text(encoding="utf-8")),
                render_attachment_signal_context=lambda file_name, _mime_type, note: f"첨부 파일명: {file_name}\n{note}",
                infer_capture_investment_scope=lambda _context, _settings: {"tags": ["theme:kosdaq"]},
                current_storage_timestamp=lambda: "2026-06-13T08:00:00+09:00",
                merge_research_tags=merge_tags,
                strip_quality_rebuild_tags=lambda tags: tags or [],
                update_manifest=lambda **kwargs: updated_entries.append(kwargs["entry"]),
                manifest_entry_json_path=lambda _entry, _vault_dir: json_path,
                manifest_entry_markdown_path=lambda _entry, _vault_dir: markdown_path,
                upsert_markdown_tail_section=lambda path, marker, section: markdown_updates.append((path, marker, section)),
                upsert_research_memory_document=lambda **kwargs: rag_updates.append(kwargs),
                read_manifest_entry_text=lambda _vault_dir, _entry: markdown_path.read_text(encoding="utf-8"),
                backfill_research_memory_documents_from_manifest=lambda _vault_dir: {"updated_count": 1},
                ocr_runtime_status=lambda: {"available": True},
                ocr_reprocess_marker="## OCR 재처리 결과",
            )

            result = research_memory_ocr.reprocess_research_memory_ocr(
                runtime,
                SimpleNamespace(research_vault_dir=str(vault_dir)),
            )
            payload = json.loads(json_path.read_text(encoding="utf-8"))

        self.assertEqual(result["reprocessed_count"], 1)
        self.assertEqual(result["rag_updated_count"], 1)
        self.assertEqual(updated_entries[0]["capture_quality"]["status"], "정상")
        self.assertIn("theme:kosdaq", updated_entries[0]["tags"])
        self.assertEqual(payload["capture_quality"]["status"], "정상")
        self.assertEqual(payload["attachment"]["extracted_text"], "코스닥 활성화 정책 본문")
        self.assertEqual(markdown_updates[0][1], "## OCR 재처리 결과")
        self.assertIn("OCR 텍스트 추출 완료", markdown_updates[0][2])
        self.assertIn("코스닥 활성화 정책 본문", rag_updates[0]["full_text"])

    def test_research_memory_ocr_module_classifies_ocr_needed_attachment(self):
        from research_os import research_memory_ocr

        runtime = SimpleNamespace(
            is_pdf_attachment=lambda file_name, mime_type: str(file_name).endswith(".pdf") or mime_type == "application/pdf",
            is_image_attachment=lambda _file_name, _mime_type: False,
        )

        self.assertTrue(
            research_memory_ocr.attachment_needs_ocr_reprocess(
                runtime,
                {
                    "file_name": "scan.pdf",
                    "mime_type": "application/pdf",
                    "extraction_char_count": 0,
                    "text_extraction": "Tesseract OCR 실행 파일을 찾지 못했습니다",
                },
            )
        )
        self.assertFalse(
            research_memory_ocr.attachment_needs_ocr_reprocess(
                runtime,
                {
                    "file_name": "scan.pdf",
                    "mime_type": "application/pdf",
                    "extraction_char_count": 120,
                    "extracted_text": "이미 추출됨",
                },
            )
        )


class ResearchMemorySupplementModuleTests(unittest.TestCase):
    def test_research_memory_supplement_module_updates_markdown_json_manifest_and_rag(self):
        from research_os import research_memory_supplement
        from research_os.models import ResearchMemoryContentResponse, ResearchMemorySupplementRequest

        updated_entries = []
        upsert_calls = []

        test_tmp_dir = PROJECT_ROOT / ".test-tmp"
        test_tmp_dir.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=test_tmp_dir, ignore_cleanup_errors=True) as temp_dir:
            vault_dir = Path(temp_dir) / "research_vault"
            ticker_dir = vault_dir / "POLICY"
            ticker_dir.mkdir(parents=True)
            markdown_path = ticker_dir / "POLICY-research-capture-2026-06-13-test.md"
            json_path = markdown_path.with_suffix(".json")
            markdown_path.write_text("# 정책 자료\n\nURL-only 저장", encoding="utf-8")
            json_path.write_text(
                json.dumps(
                    {
                        "raw_content": "",
                        "capture_quality": {"status": "보강 필요"},
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            manifest_entry = {
                "ticker": "POLICY",
                "file_name": markdown_path.name,
                "tags": ["needs_body_copy"],
                "capture_quality": {"status": "보강 필요"},
            }

            def read_response(ticker, file_name, _vault_dir):
                return ResearchMemoryContentResponse(
                    ticker=ticker,
                    file_name=file_name,
                    relative_path=f"research_vault/{ticker}/{file_name}",
                    content=markdown_path.read_text(encoding="utf-8"),
                    modified_at="2026-06-13T08:00:00+09:00",
                    json_payload=json.loads(json_path.read_text(encoding="utf-8")),
                    tags=updated_entries[-1]["tags"],
                    capture_quality=updated_entries[-1]["capture_quality"],
                )

            runtime = SimpleNamespace(
                current_storage_timestamp=lambda: "2026-06-13T08:00:00+09:00",
                read_manifest=lambda _vault_dir: [manifest_entry],
                content_fingerprint=lambda value: f"hash:{len(value)}",
                update_manifest=lambda **kwargs: updated_entries.append(kwargs["entry"]),
                upsert_research_memory_document=lambda **kwargs: upsert_calls.append(kwargs),
                read_research_memory_file=read_response,
            )

            response = research_memory_supplement.supplement_research_memory_file(
                runtime,
                "POLICY",
                markdown_path.name,
                ResearchMemorySupplementRequest(body_text="보강 본문입니다.", note="원문 확인"),
                vault_dir,
            )

            updated_markdown = markdown_path.read_text(encoding="utf-8")
            payload = json.loads(json_path.read_text(encoding="utf-8"))

        self.assertIn("## 본문 보강", updated_markdown)
        self.assertIn("보강 본문입니다.", updated_markdown)
        self.assertEqual(payload["body_supplements"][0]["source"], "user_body_copy")
        self.assertTrue(payload["capture_quality"]["body_supplemented"])
        self.assertEqual(payload["capture_quality"]["status"], "정상")
        self.assertIn("body_supplemented", updated_entries[0]["tags"])
        self.assertEqual(updated_entries[0]["body_supplement_count"], 1)
        self.assertTrue(updated_entries[0]["capture_quality"]["body_supplemented"])
        self.assertEqual(upsert_calls[0]["full_text"], updated_markdown)
        self.assertEqual(response.capture_quality["status"], "정상")


class CaptureAutoModuleTests(unittest.TestCase):
    def test_capture_auto_module_builds_url_based_special_scope_request(self):
        from research_os import capture_auto
        from research_os.models import AutoResearchCaptureRequest, CapturedResearchItem, ResearchCaptureResponse

        captured = {}

        def merge_tags(*groups):
            merged = []
            for group in groups:
                for tag in group or []:
                    if tag not in merged:
                        merged.append(tag)
            return merged

        def save_capture_request(auto_request, _settings, **kwargs):
            captured["request"] = auto_request
            captured["kwargs"] = kwargs
            return ResearchCaptureResponse(
                captured_item=CapturedResearchItem(
                    ticker=auto_request.ticker,
                    title=auto_request.title,
                    summary="요약",
                    source_type=auto_request.source_type,
                    source_url=auto_request.source_url,
                    confidence=auto_request.confidence,
                    tags=list(auto_request.tags),
                ),
                saved_to_research_memory=auto_request.save_result,
            )

        runtime = SimpleNamespace(
            foreign_text_korean_digest=lambda _raw, _note: {"status": "original", "text": ""},
            fetch_capture_source_url=lambda _url: {
                "title": "Rates Report",
                "final_url": "https://example.com/final",
                "text": "rates body",
                "note": "ok",
            },
            render_source_url_body=lambda info: f"본문: {info.get('text')}",
            is_unusable_source_url=lambda _info: False,
            render_url_only_capture_context=lambda url, _info: f"URL only: {url}",
            render_attachment_signal_context=lambda _file_name, _mime_type: "",
            is_pdf_attachment=lambda _file_name, _mime_type: False,
            decode_attachment_base64=lambda _value: b"",
            extract_pdf_text=lambda _payload: ("", ""),
            infer_capture_ticker=lambda _content, _settings: ("RATES", "rates_research"),
            resolve_vault_dir=lambda value: Path(value),
            current_storage_date=lambda: date(2026, 6, 13),
            save_capture_attachment=lambda *_args, **_kwargs: None,
            render_attachment_context=lambda _request, _attachment_info: "",
            infer_capture_investment_scope=lambda _content, _settings: {"tags": ["theme:rates"]},
            render_investment_scope_context=lambda _scope: "관심 범위 후보: rates",
            infer_capture_source_type=lambda _content, _file_name: "user_memo",
            merge_research_tags=merge_tags,
            classification_system_tags=lambda _ticker, source_type, reason: [
                f"source_type:{source_type}",
                f"auto_scope:{reason}",
            ],
            infer_capture_tags=lambda _content, tags: [*tags, "macro"],
            infer_capture_title=lambda _content, _file_name: "Fallback Title",
            prefix_capture_title=lambda title, ticker, reason: f"[{ticker}/{reason}] {title}",
            infer_capture_confidence=lambda _source_type, has_file: 0.91 if has_file else 0.8,
            save_capture_request=save_capture_request,
            special_research_keys={"INBOX", "MARKET", "MACRO", "POLICY", "RATES", "FLOWS", "SECTOR"},
        )
        request = AutoResearchCaptureRequest(
            raw_content="rate cut memo",
            source_url="https://example.com/report",
            run_thesis_impact=True,
            save_result=False,
        )

        response = capture_auto.auto_capture_research_item(
            runtime,
            request,
            SimpleNamespace(research_vault_dir=str(PROJECT_ROOT / ".test-tmp" / "capture-auto")),
        )

        auto_request = captured["request"]
        self.assertEqual(auto_request.ticker, "RATES")
        self.assertEqual(auto_request.title, "[RATES/rates_research] Rates Report")
        self.assertEqual(auto_request.source_type, "rates_research")
        self.assertEqual(auto_request.source_url, "https://example.com/final")
        self.assertFalse(auto_request.run_thesis_impact)
        self.assertIn("url_input", auto_request.tags)
        self.assertIn("web_capture", auto_request.tags)
        self.assertIn("theme:rates", auto_request.tags)
        self.assertEqual(captured["kwargs"]["source_url_processing"]["title"], "Rates Report")
        self.assertEqual(captured["kwargs"]["input_preview_override"], "rate cut memo\n웹사이트 주소: https://example.com/report")
        self.assertEqual(captured["kwargs"]["document_preview_override"], "rates body")
        self.assertIn("[RATES 자동 분류]", response.captured_item.summary)

    def test_capture_auto_module_rejects_empty_input(self):
        from fastapi import HTTPException
        from research_os import capture_auto
        from research_os.models import AutoResearchCaptureRequest

        with self.assertRaises(HTTPException) as raised:
            capture_auto.auto_capture_research_item(
                SimpleNamespace(render_source_url_body=lambda _info: ""),
                AutoResearchCaptureRequest(raw_content=""),
                SimpleNamespace(research_vault_dir="unused"),
            )

        self.assertEqual(raised.exception.status_code, 422)


class CaptureStorageModuleTests(unittest.TestCase):
    def test_capture_storage_module_builds_unsaved_response_with_previews(self):
        from research_os import capture_storage
        from research_os.models import ResearchCaptureRequest

        def merge_tags(*groups):
            merged = []
            for group in groups:
                for tag in group or []:
                    if tag not in merged:
                        merged.append(tag)
            return merged

        runtime = SimpleNamespace(
            ensure_verified_ticker=lambda ticker, _settings: str(ticker).upper(),
            resolve_vault_dir=lambda value: Path(value),
            current_storage_date=lambda: date(2026, 6, 13),
            merge_research_tags=merge_tags,
            infer_capture_tags=lambda _raw_content, tags: [*tags, "ai"],
            classification_system_tags=lambda _ticker, source_type: [f"source_type:{source_type}"],
            content_fingerprint=lambda raw_content: f"fp:{len(raw_content)}",
            detect_capture_duplicate=lambda **_kwargs: {"is_duplicate_suspected": False},
            summarize_capture=lambda _raw_content: "요약",
            capture_quality_status=lambda **_kwargs: {"status": "정상", "readiness": "usable"},
            capture_preview_text=lambda value: None if value is None else str(value)[:12],
        )
        request = ResearchCaptureRequest(
            ticker="msft",
            title="AI capex memo",
            raw_content="AI capex demand and margin expansion",
            source_type="user_memo",
            confidence=0.82,
            tags=["manual"],
            run_thesis_impact=False,
            save_result=False,
        )

        response = capture_storage.save_capture_request(
            runtime,
            request,
            SimpleNamespace(research_vault_dir=str(PROJECT_ROOT / ".test-tmp" / "capture-storage")),
            attachment_info={"extracted_text": "attached document text"},
        )

        self.assertEqual(response.captured_item.ticker, "MSFT")
        self.assertEqual(response.captured_item.summary, "요약")
        self.assertFalse(response.saved_to_research_memory)
        self.assertIsNone(response.storage)
        self.assertEqual(response.capture_quality["status"], "정상")
        self.assertEqual(response.duplicate_check, {"is_duplicate_suspected": False})
        self.assertEqual(response.input_preview, "AI capex dem")
        self.assertEqual(response.document_preview, "attached doc")
        self.assertIn("manual", response.captured_item.tags)
        self.assertIn("ai", response.captured_item.tags)
        self.assertIn("source_type:user_memo", response.captured_item.tags)

    def test_capture_storage_saves_thesis_impact_manifest_payload(self):
        from research_os import capture_storage
        from research_os.research_memory import ResearchStorageInfo

        class DumpItem(SimpleNamespace):
            def model_dump(self, mode=None):
                return dict(self.__dict__)

        class FakeImpact(SimpleNamespace):
            def model_dump(self, mode=None):
                return dict(self.__dict__)

        save_calls = []

        def fake_save_research_markdown(**kwargs):
            save_calls.append(kwargs)
            return ResearchStorageInfo(
                file_name=f"{kwargs['ticker']}-{kwargs['report_type']}.md",
                relative_path=f"research_vault/{kwargs['ticker']}/{kwargs['ticker']}-{kwargs['report_type']}.md",
                absolute_path=str(kwargs['vault_dir'] / kwargs['ticker'] / f"{kwargs['ticker']}-{kwargs['report_type']}.md"),
            )

        runtime = SimpleNamespace(
            current_storage_date=lambda: date(2026, 6, 13),
            manifest_with_ticker_verification=lambda ticker, entry: {**entry, "ticker": ticker, "verified": True},
            render_thesis_impact_markdown=lambda impact, storage_date: f"impact {storage_date.isoformat()}",
            save_research_markdown=fake_save_research_markdown,
        )
        impact = FakeImpact(
            summary="논거 강화",
            overall_impact=SimpleNamespace(value="strengthens"),
            source_count=2,
            findings=[DumpItem(label="margin", impact="strengthens")],
            watch_item_signals=[DumpItem(label="AI demand", signal="positive")],
            next_actions=["Dossier 갱신"],
            storage=None,
        )
        vault_dir = PROJECT_ROOT / ".test-tmp" / "capture-storage-impact"

        saved = capture_storage.save_thesis_impact_report(
            runtime,
            impact=impact,
            ticker="005930",
            vault_dir=vault_dir,
            linked_capture_file="005930-research-capture.md",
        )

        self.assertEqual(saved.storage.file_name, "005930-thesis-impact-review.md")
        self.assertEqual(save_calls[0]["report_type"], "thesis-impact-review")
        self.assertEqual(save_calls[0]["manifest_entry"]["summary"], "논거 강화")
        self.assertEqual(save_calls[0]["manifest_entry"]["overall_impact"], "strengthens")
        self.assertEqual(save_calls[0]["manifest_entry"]["source_count"], 2)
        self.assertEqual(save_calls[0]["manifest_entry"]["findings"][0]["label"], "margin")
        self.assertEqual(save_calls[0]["manifest_entry"]["watch_item_signals"][0]["label"], "AI demand")
        self.assertEqual(save_calls[0]["manifest_entry"]["linked_capture_file"], "005930-research-capture.md")
        self.assertTrue(save_calls[0]["manifest_entry"]["verified"])


class ResearchCaptureClassificationTagTests(unittest.TestCase):
    def test_classification_system_tags_include_scope_source_and_reason(self):
        import research_os_main as main

        tags = main.classification_system_tags("MARKET-KR", "market_research", "naver market research")

        self.assertIn("research_scope:market-kr", tags)
        self.assertIn("research_scope:market", tags)
        self.assertIn("source_type:market_research", tags)
        self.assertIn("auto_scope:naver_market_research", tags)

    def test_capture_request_adds_source_type_tag(self):
        import research_os_main as main
        from research_os.models import ResearchCaptureRequest
        from research_os.settings import Settings

        request = ResearchCaptureRequest(
            ticker="SECTOR",
            title="AI 전력 인프라 자료",
            raw_content="AI 데이터센터 전력 인프라 수요와 섹터 성장 자료입니다.",
            source_type="sector_research",
            confidence=0.78,
            tags=["auto_classified"],
            run_thesis_impact=False,
            save_result=True,
        )
        test_tmp_dir = PROJECT_ROOT / ".test-tmp"
        test_tmp_dir.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=test_tmp_dir, ignore_cleanup_errors=True) as temp_dir:
            settings = Settings(research_vault_dir=str(Path(temp_dir) / "research_vault"))
            response = main.save_capture_request(request, settings)
            manifest = json.loads((Path(temp_dir) / "research_vault" / "manifest.json").read_text(encoding="utf-8"))

        tags = manifest[0]["tags"]
        self.assertIn("research_scope:sector", tags)
        self.assertIn("source_type:sector_research", tags)
        self.assertIn("sector", tags)
        self.assertTrue(response.rag_document)


class CaptureAttachmentModuleTests(unittest.TestCase):
    def test_capture_attachment_module_renders_signal_and_attachment_context(self):
        from research_os import capture_attachment

        signal_context = capture_attachment.render_attachment_signal_context(
            "코스닥 중견중소_코스닥 활성화 정책.pdf",
            "application/pdf",
            "PDF OCR unavailable",
        )
        attachment_context = capture_attachment.render_attachment_context(
            SimpleNamespace(file_name="report.pdf", file_mime_type="application/pdf", file_size=123),
            {
                "file_name": "report.pdf",
                "mime_type": "application/pdf",
                "size": 123,
                "relative_path": "018260/_attachments/report.pdf",
                "document_type": "PDF",
                "extraction_quality": "partial",
                "text_extraction": "본문 텍스트 추출 포함",
                "extraction_profile": {
                    "analysis_readiness": "medium",
                    "char_count": 50,
                    "line_count": 2,
                    "numeric_token_count": 1,
                    "next_action": "원문 확인",
                },
                "fallback_analysis_context": signal_context,
                "inferred_investment_scope": {
                    "theme_candidates": [{"label": "코스닥"}],
                    "matched_interest_tickers": [{"company_name": "동성화인텍"}],
                    "matched_interest_sectors": [],
                    "matched_portfolio_holdings": [],
                    "next_action": "비교",
                },
                "extraction_warnings": ["OCR 제한"],
                "extracted_text": "코스닥 활성화 정책 본문",
            },
        )

        self.assertIn("첨부 신호 컨텍스트", signal_context)
        self.assertIn("코스닥", signal_context)
        self.assertIn("분석 활용도: medium", attachment_context)
        self.assertIn("관심종목 매칭: 동성화인텍", attachment_context)
        self.assertIn("추출 경고: OCR 제한", attachment_context)
        self.assertIn("코스닥 활성화 정책 본문", attachment_context)

    def test_capture_attachment_module_saves_file_and_extraction_metadata(self):
        from research_os import capture_attachment

        captured_contexts = []
        runtime = SimpleNamespace(
            decode_attachment_base64=lambda _value: b"hello attachment",
            extract_uploaded_file_text=lambda _bytes, _name, _mime, source_path=None: {
                "extracted_text": "코스닥 정책 자료",
                "text_extraction": "본문 텍스트 추출 포함",
                "document_type": "텍스트",
                "extraction_quality": "ready",
                "extraction_char_count": 8,
                "extraction_preview": "코스닥 정책",
                "extraction_warnings": [],
                "extraction_profile": {"analysis_readiness": "high"},
            },
            infer_capture_investment_scope=lambda context, _settings: captured_contexts.append(context) or {
                "tags": ["theme:kosdaq"]
            },
            normalize_ticker=lambda value: str(value or "").upper(),
            safe_attachment_file_name=lambda value: str(value or "upload.txt"),
        )
        request = SimpleNamespace(
            file_content_base64="aGVsbG8=",
            file_name="memo.txt",
            file_mime_type="text/plain",
            file_size=15,
            raw_content="코스닥 활성화 메모",
        )
        test_tmp_dir = PROJECT_ROOT / ".test-tmp"
        test_tmp_dir.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=test_tmp_dir, ignore_cleanup_errors=True) as temp_dir:
            vault_dir = Path(temp_dir) / "research_vault"
            result = capture_attachment.save_capture_attachment(
                runtime,
                vault_dir,
                "policy",
                date(2026, 6, 13),
                request,
                SimpleNamespace(),
            )
            saved_path = vault_dir / result["relative_path"]

        self.assertEqual(result["file_name"], "memo.txt")
        self.assertEqual(result["mime_type"], "text/plain")
        self.assertEqual(result["extracted_text"], "코스닥 정책 자료")
        self.assertEqual(result["inferred_investment_scope"], {"tags": ["theme:kosdaq"]})
        self.assertIn("코스닥 활성화 메모", captured_contexts[0])
        self.assertTrue(str(saved_path).endswith("memo.txt"))

    def test_capture_attachment_module_renders_markdown_and_preview(self):
        from research_os import capture_attachment

        captured_item = SimpleNamespace(
            ticker="MARKET",
            title="시장 메모",
            summary="요약",
            source_type="market_research",
            source_url="https://example.com",
            as_of=None,
            confidence=0.76,
            tags=["market", "manual"],
        )
        markdown = capture_attachment.render_research_capture_markdown(
            captured_item,
            "원문 본문",
            date(2026, 6, 13),
            {"file_name": "memo.txt", "mime_type": "text/plain", "size": 10, "relative_path": "MARKET/a.txt"},
        )
        preview = capture_attachment.capture_preview_text("abcdef", max_chars=3)

        self.assertIn("ticker: MARKET", markdown)
        self.assertIn("source_type: market_research", markdown)
        self.assertIn("## 첨부 파일", markdown)
        self.assertIn("앞부분 3자", preview)


class CaptureInferenceModuleTests(unittest.TestCase):
    def test_capture_inference_module_summarizes_and_tags_research_text(self):
        from research_os import capture_inference

        summary = capture_inference.summarize_capture(("AI capex demand growth " * 20).strip())
        tags = capture_inference.infer_capture_tags(
            "FOMC rate cut, AI capex demand growth, and gross margin improvement",
            ["manual"],
        )

        self.assertLessEqual(len(summary), 240)
        self.assertTrue(summary.endswith("..."))
        self.assertIn("manual", tags)
        self.assertIn("ai", tags)
        self.assertIn("growth", tags)
        self.assertIn("macro", tags)
        self.assertIn("margin", tags)

    def test_capture_inference_module_source_type_uses_non_ticker_scope_callback(self):
        from research_os import capture_inference

        source_type = capture_inference.infer_capture_source_type(
            "국채 금리와 CPI가 장단기 금리에 미치는 영향",
            allow_non_ticker_scope=True,
            infer_non_ticker_research_key_fn=lambda _text: ("RATES", "rates_research"),
            special_research_keys={"INBOX", "RATES", "MARKET"},
        )

        self.assertEqual(source_type, "rates_research")

    def test_capture_inference_module_source_type_and_confidence_defaults(self):
        from research_os import capture_inference

        filing_type = capture_inference.infer_capture_source_type("10-K annual report revenue details")
        news_type = capture_inference.infer_capture_source_type("press release article")
        confidence = capture_inference.infer_capture_confidence(news_type, has_file=True)

        self.assertEqual(filing_type, "official_filing")
        self.assertEqual(news_type, "news")
        self.assertAlmostEqual(confidence, 0.78)


class CaptureTickerInferenceModuleTests(unittest.TestCase):
    def test_capture_ticker_inference_module_matches_alias_boundaries(self):
        from research_os import capture_ticker_inference

        aliases = capture_ticker_inference.ticker_aliases(
            "JOBY",
            {"company_name": "Joby Aviation, Inc.", "aliases": ["Joby"]},
        )

        self.assertIn("JOBY AVIATION", aliases)
        self.assertTrue(capture_ticker_inference.alias_matches_research_text("JOBY", "JOBY reports"))
        self.assertFalse(capture_ticker_inference.alias_matches_research_text("JOBY", "JOBYQ reports"))
        self.assertTrue(capture_ticker_inference.alias_matches_research_text("코스닥", "코스닥 활성화 정책"))

    def test_capture_ticker_inference_module_detects_non_ticker_scope(self):
        from research_os import capture_ticker_inference

        ticker, source = capture_ticker_inference.infer_non_ticker_research_key(
            "국채 금리 인하와 CPI 물가, 장단기 금리 스프레드"
        )

        self.assertEqual(ticker, "RATES")
        self.assertEqual(source, "rates_research")

    def test_capture_ticker_inference_module_infers_explicit_symbol_and_alias(self):
        from research_os import capture_ticker_inference

        class FakeVerification:
            verified = True

        runtime = SimpleNamespace(
            get_settings=lambda: SimpleNamespace(),
            is_plausible_equity_symbol=lambda symbol: symbol not in {"CASH"},
            normalize_ticker=lambda value: str(value or "").upper(),
            official_ticker_registry={
                "JOBY": {"company_name": "Joby Aviation Inc", "aliases": ["Joby"]},
                "MSFT": {"company_name": "Microsoft Corporation", "aliases": ["Microsoft"]},
            },
            read_dynamic_ticker_registry=lambda _settings: {},
            special_research_keys={"INBOX", "MARKET", "MACRO", "POLICY", "RATES", "FLOWS", "SECTOR"},
            verify_ticker_symbol=lambda _candidate, _settings: FakeVerification(),
        )

        self.assertEqual(
            capture_ticker_inference.infer_capture_ticker(runtime, "Ticker: JOBY", SimpleNamespace()),
            ("JOBY", "explicit_symbol"),
        )
        self.assertEqual(
            capture_ticker_inference.infer_capture_ticker(
                runtime,
                "Microsoft Azure demand accelerates",
                SimpleNamespace(),
            ),
            ("MSFT", "company_alias_match"),
        )


class ResearchCaptureInferenceTests(unittest.TestCase):
    def test_empty_pdf_filename_context_infers_policy_and_investment_scope(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        context = main.render_attachment_signal_context(
            "코스닥 중견중소_코스닥 활성화 정책과 옥석 가리기.pdf",
            "application/pdf",
            "PDF에서 추출 가능한 텍스트를 찾지 못했습니다. 한국어/영어 OCR 언어팩(kor+eng)을 찾지 못했습니다.",
        )

        ticker, source = main.infer_capture_ticker(context, settings)
        self.assertEqual(ticker, "POLICY")
        self.assertEqual(source, "policy_research")
        self.assertIn("관심 범위 후보", context)

        with (
            patch.object(
                main,
                "read_interest_list",
                return_value={
                    "tickers": [],
                    "sectors": [
                        {
                            "name": "코스닥",
                            "region": "KR",
                            "tags": ["중소형"],
                            "thesis": "코스닥 정책 변화 수혜 가능성",
                        }
                    ],
                },
            ),
            patch.object(
                main,
                "read_portfolio_store",
                return_value={
                    "portfolios": {
                        "test": {
                            "portfolio_name": "테스트",
                            "holdings": [
                                {
                                    "ticker": "033500",
                                    "name": "동성화인텍",
                                    "sector": "코스닥",
                                    "theme_tags": ["중소형"],
                                }
                            ],
                        }
                    }
                },
            ),
        ):
            scope = main.infer_capture_investment_scope(context, settings)

        theme_labels = [item["label"] for item in scope["theme_candidates"]]
        self.assertIn("코스닥", theme_labels)
        self.assertIn("정책/규제", theme_labels)
        self.assertEqual(scope["matched_interest_sectors"][0]["name"], "코스닥")
        self.assertEqual(scope["matched_portfolio_holdings"], [])
        self.assertIn("theme:kosdaq", scope["tags"])
        rendered = main.render_investment_scope_context(scope)
        self.assertIn("관심섹터 매칭: 코스닥", rendered)

    def test_investment_scope_does_not_match_region_or_generic_terms(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        context = "KR 시장 전망과 증권사 리서치 요약입니다."
        with (
            patch.object(
                main,
                "read_interest_list",
                return_value={
                    "tickers": [],
                    "sectors": [
                        {"name": "전력", "region": "KR", "tags": ["AI"]},
                        {"name": "포토닉스", "region": "KR", "tags": ["시장"]},
                    ],
                },
            ),
            patch.object(
                main,
                "read_portfolio_store",
                return_value={
                    "portfolios": {
                        "test": {
                            "holdings": [
                                {
                                    "ticker": "033500",
                                    "name": "동성화인텍",
                                    "sector": "코스닥",
                                    "theme_tags": ["시장"],
                                }
                            ],
                        }
                    }
                },
            ),
        ):
            scope = main.infer_capture_investment_scope(context, settings)

        self.assertEqual(scope["matched_interest_sectors"], [])
        self.assertEqual(scope["matched_portfolio_holdings"], [])
        self.assertEqual(scope["theme_candidates"], [])

    def test_quality_rebuild_backfills_existing_attachment_scope(self):
        import json
        import research_os_main as main
        from research_os.settings import Settings

        test_tmp_dir = PROJECT_ROOT / ".test-tmp"
        test_tmp_dir.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=test_tmp_dir, ignore_cleanup_errors=True) as temp_dir:
            vault_dir = Path(temp_dir) / "research_vault"
            policy_dir = vault_dir / "POLICY"
            policy_dir.mkdir(parents=True)
            markdown_path = policy_dir / "POLICY-research-capture-2026-05-24-test.md"
            json_path = markdown_path.with_suffix(".json")
            markdown_path.write_text(
                "# 정책 자료\n\n코스닥 중견중소 활성화 정책 자료입니다.",
                encoding="utf-8",
            )
            json_path.write_text(
                json.dumps(
                    {
                        "status": "success",
                        "module": "research_quick_capture",
                        "captured_item": {
                            "ticker": "POLICY",
                            "title": "코스닥 활성화",
                            "summary": "첨부 중심 저장",
                            "tags": ["auto_classified"],
                        },
                        "raw_content": "",
                        "attachment": {
                            "file_name": "코스닥 중견중소_코스닥 활성화 정책과 옥석 가리기.pdf",
                            "mime_type": "application/pdf",
                            "text_extraction": "PDF에서 추출 가능한 텍스트를 찾지 못했습니다.",
                            "extraction_char_count": 0,
                        },
                        "capture_quality": {"status": "보강 필요"},
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (vault_dir / "manifest.json").write_text(
                json.dumps(
                    [
                        {
                            "ticker": "POLICY",
                            "type": "research-capture",
                            "date": "2026-05-24",
                            "file_name": markdown_path.name,
                            "relative_path": markdown_path.relative_to(vault_dir.parent).as_posix(),
                            "json_file_name": json_path.name,
                            "json_relative_path": json_path.relative_to(vault_dir.parent).as_posix(),
                            "summary": "첨부 중심 저장",
                            "tags": ["auto_classified"],
                            "attachment": {
                                "file_name": "코스닥 중견중소_코스닥 활성화 정책과 옥석 가리기.pdf",
                                "mime_type": "application/pdf",
                                "text_extraction": "PDF에서 추출 가능한 텍스트를 찾지 못했습니다.",
                                "extraction_char_count": 0,
                            },
                            "capture_quality": {"status": "보강 필요"},
                        }
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            settings = Settings(research_vault_dir=str(vault_dir))

            with (
                patch.object(main, "read_interest_list", return_value={"tickers": [], "sectors": []}),
                patch.object(main, "read_portfolio_store", return_value={"portfolios": {}}),
            ):
                result = main.rebuild_research_memory_quality_metadata(settings)

            self.assertEqual(result["checked_count"], 1)
            self.assertEqual(result["enriched_count"], 1)
            self.assertEqual(result["markdown_updated_count"], 1)
            manifest = json.loads((vault_dir / "manifest.json").read_text(encoding="utf-8"))
            entry = manifest[0]
            self.assertIn("theme:kosdaq", entry["tags"])
            self.assertIn("inferred_investment_scope", entry["attachment"])
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertIn("theme:policy", payload["captured_item"]["tags"])
            self.assertIn("품질 재점검/투자 반영 추론", markdown_path.read_text(encoding="utf-8"))

    def test_ocr_reprocess_updates_existing_zero_text_attachment(self):
        import json
        import research_os_main as main
        from research_os.settings import Settings

        test_tmp_dir = PROJECT_ROOT / ".test-tmp"
        test_tmp_dir.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=test_tmp_dir, ignore_cleanup_errors=True) as temp_dir:
            vault_dir = Path(temp_dir) / "research_vault"
            ticker_dir = vault_dir / "POLICY"
            attachment_dir = ticker_dir / "_attachments"
            attachment_dir.mkdir(parents=True)
            attachment_path = attachment_dir / "policy-scan.pdf"
            attachment_path.write_bytes(b"%PDF-1.4 scan")
            markdown_path = ticker_dir / "POLICY-research-capture-2026-05-24-test.md"
            json_path = markdown_path.with_suffix(".json")
            markdown_path.write_text("# 정책 자료\n\n첨부 본문 없음", encoding="utf-8")
            attachment = {
                "file_name": "코스닥 중견중소 정책.pdf",
                "mime_type": "application/pdf",
                "relative_path": attachment_path.relative_to(vault_dir).as_posix(),
                "text_extraction": "한국어/영어 OCR 언어팩(kor+eng)을 찾지 못했습니다.",
                "extracted_text": "",
                "extraction_char_count": 0,
                "extraction_profile": {
                    "ocr_status": "unavailable",
                    "ocr_missing_reason": "language_pack_missing",
                },
            }
            json_path.write_text(
                json.dumps(
                    {
                        "status": "success",
                        "captured_item": {"ticker": "POLICY", "tags": []},
                        "raw_content": "코스닥 정책 자료",
                        "attachment": attachment,
                        "capture_quality": {"status": "보강 필요"},
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (vault_dir / "manifest.json").write_text(
                json.dumps(
                    [
                        {
                            "ticker": "POLICY",
                            "type": "research-capture",
                            "date": "2026-05-24",
                            "file_name": markdown_path.name,
                            "relative_path": markdown_path.relative_to(vault_dir.parent).as_posix(),
                            "json_file_name": json_path.name,
                            "json_relative_path": json_path.relative_to(vault_dir.parent).as_posix(),
                            "summary": "첨부 본문 없음",
                            "tags": [],
                            "attachment": attachment,
                            "capture_quality": {"status": "보강 필요"},
                        }
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            settings = Settings(research_vault_dir=str(vault_dir))

            with (
                patch.object(
                    main,
                    "extract_uploaded_file_text",
                    return_value={
                        "text_extraction": "OCR 텍스트 추출 완료: 1/1페이지, 120자",
                        "extracted_text": "코스닥 활성화 정책과 중소형주 유동성 개선",
                        "document_type": "PDF",
                        "extraction_quality": 0.82,
                        "extraction_char_count": 24,
                        "extraction_preview": "코스닥 활성화 정책",
                        "extraction_warnings": [],
                        "extraction_profile": {
                            "ocr_status": "success",
                            "ocr_language": "kor+eng",
                            "ocr_available": True,
                        },
                    },
                ),
                patch.object(main, "read_interest_list", return_value={"tickers": [], "sectors": []}),
                patch.object(main, "read_portfolio_store", return_value={"portfolios": {}}),
            ):
                result = main.reprocess_research_memory_ocr(settings)

            self.assertEqual(result["candidate_count"], 1)
            self.assertEqual(result["reprocessed_count"], 1)
            manifest = json.loads((vault_dir / "manifest.json").read_text(encoding="utf-8"))
            updated_attachment = manifest[0]["attachment"]
            self.assertEqual(updated_attachment["extraction_profile"]["ocr_status"], "success")
            self.assertGreater(updated_attachment["extraction_char_count"], 0)
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertIn("코스닥 활성화", payload["attachment"]["extracted_text"])
            self.assertIn("OCR 재처리 결과", markdown_path.read_text(encoding="utf-8"))


class CompanyIrWatchModuleTests(unittest.TestCase):
    def test_company_ir_watch_module_disabled_payload_is_written(self):
        from research_os import company_ir_watch

        writes = []
        settings = SimpleNamespace(company_ir_sources_enabled=False)
        runtime = SimpleNamespace(
            company_ir_copyright_policy=lambda: {"mode": "metadata_only"},
            company_ir_sources_watch_path=lambda _settings: Path("company_ir.json"),
            current_storage_timestamp=lambda: "2026-06-13T09:00:00+09:00",
            read_json_store=lambda _path, _default=None: {},
            write_json_store=lambda path, payload: writes.append((path, payload)),
        )

        result = company_ir_watch.build_company_ir_sources_watch_payload(runtime, settings, save_result=True)

        self.assertEqual(result["status"], "disabled")
        self.assertEqual(result["source_status"], "disabled")
        self.assertEqual(result["policy"], {"mode": "metadata_only"})
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0][0], Path("company_ir.json"))

    def test_company_ir_watch_module_collects_related_public_ir_items(self):
        from research_os import company_ir_watch

        writes = []
        collect_requests = []

        class FakeRequest:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        settings = SimpleNamespace(
            company_ir_sources_enabled=True,
            company_ir_sources_max_items=20,
            company_ir_sources_refresh_hours=6,
            company_ir_sources_timeout_seconds=3,
            company_ir_sources_user_agent="agent",
            company_ir_sources_json="[]",
        )
        fetched_items = [
            {
                "ticker": "JOBY",
                "company_name": "Joby Aviation",
                "title": "Joby shareholder letter",
                "detail_url": "https://ir.jobyaviation.com/news",
                "source_provider": "Joby IR",
                "source_scope": "press_release",
                "category": "IR",
                "published_at": "2026-06-13",
            }
        ]
        runtime = SimpleNamespace(
            PublicIrSecCollectRequest=FakeRequest,
            collect_public_ir_sec_url=lambda request, _settings: collect_requests.append(request) or {
                "status": "success",
                "storage": {"relative_path": "research_vault/JOBY/a.md"},
                "capture_quality": {"status": "정상", "needs_body_copy": False},
            },
            company_ir_copyright_policy=lambda: {"mode": "metadata_only"},
            company_ir_sources_watch_path=lambda _settings: Path("company_ir.json"),
            configured_company_ir_sources=lambda _json: ["joby"],
            current_storage_timestamp=lambda: "2026-06-13T09:00:00+09:00",
            fetch_company_ir_sources=lambda **_kwargs: (fetched_items, [], [{"provider": "Joby IR", "status": "success"}]),
            normalize_ticker=lambda value: str(value or "").upper(),
            provider_error_message=lambda exc, _settings: str(exc),
            read_json_store=lambda _path, _default=None: {},
            recent_activity_target_terms=lambda _settings: {"ticker_set": {"JOBY"}, "names": ["Joby"]},
            should_refresh_company_ir_cache=lambda _cache, refresh_hours=6: True,
            write_json_store=lambda path, payload: writes.append((path, payload)),
        )

        result = company_ir_watch.build_company_ir_sources_watch_payload(runtime, settings, limit=5, save_result=True)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["source_status"], "success")
        self.assertEqual(result["related_count"], 1)
        self.assertEqual(result["captured_count"], 1)
        self.assertEqual(result["capture_results"][0]["storage"], "research_vault/JOBY/a.md")
        self.assertEqual(collect_requests[0].target_key, "JOBY")
        self.assertEqual(len(writes), 1)


class PolicySourcesWatchModuleTests(unittest.TestCase):
    def test_policy_sources_watch_module_disabled_payload_uses_cached_items(self):
        from research_os import policy_sources_watch

        writes = []
        settings = SimpleNamespace(policy_sources_enabled=False, policy_sources_refresh_hours=12)
        cached_items = [
            {
                "item_id": "policy-1",
                "source_provider": "금융위원회",
                "title": "자본시장 제도 개선",
                "relevance_score": 12,
                "matched_themes": ["금융/자본시장"],
            }
        ]
        runtime = SimpleNamespace(
            build_kcif_watch_targets=lambda _portfolio, _interest: [],
            current_storage_timestamp=lambda: "2026-06-23T09:00:00+09:00",
            infer_news_policy_law_classification=lambda _text: {"tags": ["policy_law:regulation"]},
            match_policy_items_to_targets=lambda items, _targets: items,
            news_item_fingerprint=lambda title, _raw, source_url: f"{title}:{source_url}",
            news_scope_label=lambda scope: scope,
            policy_sources_copyright_policy=lambda: {"mode": "official_policy_metadata_only"},
            policy_sources_watch_path=lambda _settings: Path("policy_sources.json"),
            portfolio_store_response=lambda _settings: SimpleNamespace(portfolios=[]),
            read_interest_list=lambda _settings: {},
            read_json_store=lambda _path, _default=None: {
                "items": cached_items,
                "source_results": [{"provider": "금융위원회", "status": "success"}],
            },
            read_news_inbox=lambda _settings: {"items": []},
            should_refresh_policy_sources_cache=lambda _cache, refresh_hours=12: False,
            write_json_store=lambda path, payload: writes.append((path, payload)),
            write_news_inbox=lambda _settings, _payload: None,
        )

        result = policy_sources_watch.build_policy_sources_watch_payload(runtime, settings, save_result=True)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["source_status"], "disabled")
        self.assertEqual(result["related_count"], 1)
        self.assertIn("POLICY_SOURCES_ENABLED", result["warnings"][0])
        self.assertEqual(writes[0][0], Path("policy_sources.json"))

    def test_policy_sources_watch_module_refreshes_and_syncs_news_inbox(self):
        from research_os import policy_sources_watch

        writes = []
        inbox_writes = []
        settings = SimpleNamespace(
            policy_sources_enabled=True,
            policy_sources_refresh_hours=12,
            policy_sources_timeout_seconds=3,
            policy_sources_user_agent="agent",
        )
        fetched_items = [
            {
                "item_id": "policy-1",
                "source_provider": "공정거래위원회",
                "source_scope": "공정거래·플랫폼 규제 보도자료",
                "agency": "시장감시국",
                "title": "온라인 플랫폼 공정화 정책 추진 계획",
                "published_at": "2026-06-23",
                "detail_url": "https://www.ftc.go.kr/policy/1",
                "source_url": "https://www.ftc.go.kr/www/sub.do?key=12",
            }
        ]

        def match_items(items, _targets):
            return [{**items[0], "relevance_score": 88, "matched_themes": ["공정거래/플랫폼"], "target_matches": []}]

        runtime = SimpleNamespace(
            build_kcif_watch_targets=lambda _portfolio, _interest: [{"label": "플랫폼", "keywords": ["플랫폼"]}],
            current_storage_timestamp=lambda: "2026-06-23T09:00:00+09:00",
            fetch_policy_sources=lambda **_kwargs: (
                fetched_items,
                [],
                [{"provider": "공정거래위원회", "status": "success"}],
            ),
            infer_news_policy_law_classification=lambda _text: {"tags": ["policy_law:regulation"]},
            match_policy_items_to_targets=match_items,
            news_item_fingerprint=lambda title, _raw, source_url: f"{title}:{source_url}",
            news_scope_label=lambda scope: "정책/법령" if scope == "POLICY" else scope,
            policy_sources_copyright_policy=lambda: {"mode": "official_policy_metadata_only"},
            policy_sources_watch_path=lambda _settings: Path("policy_sources.json"),
            portfolio_store_response=lambda _settings: SimpleNamespace(portfolios=[]),
            provider_error_message=lambda exc, _settings: str(exc),
            read_interest_list=lambda _settings: {},
            read_json_store=lambda _path, _default=None: {},
            read_news_inbox=lambda _settings: {"items": []},
            should_refresh_policy_sources_cache=lambda _cache, refresh_hours=12: True,
            write_json_store=lambda path, payload: writes.append((path, payload)),
            write_news_inbox=lambda _settings, payload: inbox_writes.append(payload),
        )

        result = policy_sources_watch.build_policy_sources_watch_payload(runtime, settings, limit=5, save_result=True)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["source_status"], "refreshed")
        self.assertEqual(result["related_count"], 1)
        self.assertEqual(result["news_inbox_synced_count"], 1)
        self.assertEqual(inbox_writes[0]["items"][0]["scope"], "POLICY")
        self.assertTrue(inbox_writes[0]["items"][0]["is_policy_law"])
        self.assertIn("official_policy_source", inbox_writes[0]["items"][0]["tags"])
        self.assertEqual(writes[0][0], Path("policy_sources.json"))


class RegionalBusinessWatchModuleTests(unittest.TestCase):
    def test_regional_business_watch_module_disabled_payload_uses_cached_items(self):
        from research_os import regional_business_watch

        writes = []
        settings = SimpleNamespace(regional_business_sources_enabled=False)
        cached_items = [
            {
                "item_id": "csf-1",
                "source_provider": "CSF",
                "title": "중국 소비 회복",
                "relevance_score": 12,
                "matched_themes": ["중국"],
            }
        ]
        runtime = SimpleNamespace(
            build_kcif_watch_targets=lambda _portfolio, _interest: {"themes": ["중국"]},
            current_storage_timestamp=lambda: "2026-06-13T09:00:00+09:00",
            match_regional_business_items_to_targets=lambda items, _targets: items,
            portfolio_store_response=lambda _settings: SimpleNamespace(portfolios=[]),
            read_interest_list=lambda _settings: {},
            read_json_store=lambda _path, _default=None: {
                "items": cached_items,
                "source_results": [{"provider": "CSF", "status": "success"}],
            },
            regional_business_copyright_policy=lambda: {"mode": "metadata_only"},
            regional_business_sources_watch_path=lambda _settings: Path("regional.json"),
            write_json_store=lambda path, payload: writes.append((path, payload)),
        )

        result = regional_business_watch.build_regional_business_sources_watch_payload(
            runtime,
            settings,
            save_result=True,
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["source_status"], "disabled")
        self.assertEqual(result["related_count"], 1)
        self.assertIn("REGIONAL_BUSINESS_SOURCES_ENABLED", result["warnings"][0])
        self.assertEqual(writes[0][0], Path("regional.json"))
        self.assertEqual(writes[0][1]["source_status"], "disabled")

    def test_regional_business_watch_module_merges_cached_failed_sources(self):
        from research_os import regional_business_watch

        fetched_items = [{"item_id": "emerics-1", "source_provider": "EMERiCs", "title": "India exports"}]
        source_results = [
            {"provider": "EMERiCs", "status": "success"},
            {"provider": "CSF", "status": "failed"},
        ]
        cache = {
            "items": [
                {"item_id": "csf-2", "source_provider": "CSF", "title": "중국 정책 브리프"},
                {"item_id": "emerics-1", "source_provider": "EMERiCs", "title": "duplicate"},
            ]
        }

        items, merged_results, restored_count = regional_business_watch.merge_cached_regional_items_for_failed_sources(
            fetched_items,
            source_results,
            cache,
        )

        self.assertEqual(restored_count, 1)
        self.assertEqual([item["item_id"] for item in items], ["emerics-1", "csf-2"])
        csf_result = next(item for item in merged_results if item["provider"] == "CSF")
        self.assertEqual(csf_result["status"], "cache_fallback")
        self.assertEqual(csf_result["cached_item_count"], 1)

    def test_regional_business_watch_module_refreshes_and_matches_related_items(self):
        from research_os import regional_business_watch

        writes = []
        settings = SimpleNamespace(
            regional_business_sources_enabled=True,
            regional_business_sources_timeout_seconds=3,
            regional_business_sources_user_agent="agent",
        )
        fetched_items = [
            {"item_id": "kiep-1", "source_provider": "KIEP", "title": "세계경제 중국 공급망"},
        ]

        def match_items(items, _targets):
            return [{**items[0], "relevance_score": 80, "matched_themes": ["중국", "공급망"]}]

        runtime = SimpleNamespace(
            build_kcif_watch_targets=lambda _portfolio, _interest: {"themes": ["중국"]},
            current_storage_timestamp=lambda: "2026-06-13T09:00:00+09:00",
            fetch_regional_business_sources=lambda **_kwargs: (
                fetched_items,
                [],
                [{"provider": "KIEP", "status": "success"}],
            ),
            match_regional_business_items_to_targets=match_items,
            portfolio_store_response=lambda _settings: SimpleNamespace(portfolios=[]),
            provider_error_message=lambda exc, _settings: str(exc),
            read_interest_list=lambda _settings: {},
            read_json_store=lambda _path, _default=None: {},
            regional_business_copyright_policy=lambda: {"mode": "metadata_only"},
            regional_business_sources_watch_path=lambda _settings: Path("regional.json"),
            should_refresh_regional_business_cache=lambda _cache: True,
            write_json_store=lambda path, payload: writes.append((path, payload)),
        )

        result = regional_business_watch.build_regional_business_sources_watch_payload(
            runtime,
            settings,
            limit=5,
            save_result=True,
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["source_status"], "refreshed")
        self.assertEqual(result["related_count"], 1)
        self.assertEqual(result["related_items"][0]["matched_themes"], ["중국", "공급망"])
        self.assertEqual(result["policy"], {"mode": "metadata_only"})
        self.assertEqual(len(writes), 1)


class KcifWatchModuleTests(unittest.TestCase):
    def test_kcif_watch_module_next_actions_preserve_copyright_policy(self):
        from research_os import kcif_watch

        actions = kcif_watch.build_kcif_watch_next_actions(
            [{"title": "Global Rates", "matched_themes": ["금리", "환율"]}],
            ["warning"],
        )

        self.assertIn("KCIF 목록 확인이 지연되면", actions[0])
        self.assertIn("Global Rates", actions[1])
        self.assertIn("KCIF 원문/PDF는 자동 저장하지 않고", actions[-1])

    def test_kcif_watch_module_builds_payload_and_writes_cache(self):
        from research_os import kcif_watch

        writes = []
        settings = SimpleNamespace(
            kcif_report_list_url="https://kcif.example/reports",
            kcif_timeout_seconds=3,
            kcif_username="",
            kcif_password="",
            kcif_use_login=False,
            kcif_login_proc_url="https://kcif.example/login",
        )
        runtime = SimpleNamespace(
            build_kcif_watch_targets=lambda _portfolio, _interest: {"themes": ["금리"]},
            current_storage_timestamp=lambda: "2026-06-13T09:00:00+09:00",
            fetch_kcif_detail_analyses=lambda reports, **_kwargs: {
                "detail_status": "success",
                "analyses": {
                    "r1": {"matched_themes": ["환율"], "source_summary_available": True},
                },
            },
            fetch_kcif_report_list_with_status=lambda **_kwargs: {
                "reports": [{"report_id": "r1", "title": "Rates report"}],
                "auth_status": "anonymous",
                "connection_mode": "public",
            },
            kcif_copyright_policy=lambda: {"mode": "metadata_only"},
            kcif_report_list_url_default="https://default.example/reports",
            kcif_reports_watch_path=lambda _settings: Path("kcif_watch.json"),
            match_kcif_reports_to_targets=lambda reports, _targets: [
                {**reports[0], "relevance_score": 80, "matched_themes": ["금리"]}
            ],
            portfolio_store_response=lambda _settings: SimpleNamespace(portfolios=[]),
            provider_error_message=lambda exc, _settings: str(exc),
            read_interest_list=lambda _settings: {},
            read_json_store=lambda _path, _default=None: {},
            should_refresh_kcif_cache=lambda _cache: True,
            write_json_store=lambda path, payload: writes.append((path, payload)),
        )

        result = kcif_watch.build_kcif_reports_watch_payload(runtime, settings, limit=5, force=False, save_result=True)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["source_status"], "refreshed")
        self.assertEqual(result["detail_status"], "success")
        self.assertEqual(result["related_count"], 1)
        self.assertEqual(result["related_reports"][0]["matched_themes"], ["금리", "환율"])
        self.assertEqual(result["related_reports"][0]["relevance_score"], 86)
        self.assertEqual(result["policy"], {"mode": "metadata_only"})
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0][0], Path("kcif_watch.json"))


class InterestAutomationModuleTests(unittest.TestCase):
    def test_interest_automation_module_dedupes_keyword_candidates(self):
        from research_os import interest_automation

        result = interest_automation.target_keyword_candidates(
            "AI/반도체",
            "AI",
            ["클라우드", "반도체"],
            "",
        )

        self.assertEqual(result[:4], ["AI/반도체", "AI", "반도체", "클라우드"])
        self.assertEqual(len(result), len(set(value.lower() for value in result)))

    def test_interest_automation_module_builds_board_from_interest_and_portfolio(self):
        from research_os import interest_automation

        writes = []
        settings = SimpleNamespace(research_vault_dir="research_vault")
        manifest_entries = [
            {
                "ticker": "018260",
                "title": "삼성에스디에스 클라우드",
                "summary": "클라우드 매출 성장",
                "tags": ["cloud"],
                "type": "research-capture",
            },
            {
                "ticker": "005930",
                "title": "삼성전자 반도체",
                "summary": "AI 반도체 수요",
                "tags": ["semiconductor"],
                "type": "research-capture",
            },
        ]

        def verify_symbol(symbol, _settings):
            return SimpleNamespace(
                verified=True,
                official_symbol=str(symbol).upper(),
                company_name={"018260": "삼성에스디에스", "005930": "삼성전자"}.get(str(symbol).upper(), str(symbol)),
                exchange="KRX",
                country="KR",
            )

        runtime = SimpleNamespace(
            count_research_memory_documents_by_ticker=lambda _vault, tickers: {ticker: 2 for ticker in tickers},
            current_storage_timestamp=lambda: "2026-06-13T09:00:00+09:00",
            dedupe_manifest_entries_by_similarity=lambda entries, _vault, limit=20: (entries[:limit], []),
            interest_collection_targets_path=lambda _settings: Path("interest_targets.json"),
            manifest_entry_sort_key=lambda entry: (entry.get("date") or "", entry.get("title") or ""),
            normalize_ticker=lambda value: str(value or "").strip().upper(),
            official_ticker_profile=lambda ticker, _settings, refresh_external=False: {
                "company_name": {"018260": "삼성에스디에스", "005930": "삼성전자"}.get(ticker, ticker),
                "sector": "IT",
                "industry": "Software",
                "business_context": "클라우드 AI",
            },
            portfolio_store_response=lambda _settings: SimpleNamespace(
                portfolios=[
                    SimpleNamespace(
                        portfolio_name="Core",
                        holdings=[
                            SimpleNamespace(ticker="005930", name="삼성전자", market_value=1000000, theme_tags=["AI"])
                        ],
                    )
                ]
            ),
            read_interest_list=lambda _settings: {
                "tickers": [{"ticker": "018260", "priority": "high", "tags": ["cloud"], "thesis": "클라우드 성장"}],
                "sectors": [{"name": "AI 반도체", "region": "KR", "tags": ["AI"]}],
            },
            read_manifest=lambda _vault: manifest_entries,
            read_market_close_journal=lambda _settings: {
                "entries": [
                    {
                        "market": "KR",
                        "session_date": "2026-06-12",
                        "raw_summary": "AI 반도체와 클라우드 강세",
                        "tags": ["AI"],
                    }
                ]
            },
            read_ticker_thesis_snapshot=lambda _vault, ticker: {"thesis_summary": f"{ticker} thesis"},
            resolve_vault_dir=lambda value: Path(value),
            verify_ticker_symbol_local_cached=verify_symbol,
            write_json_store=lambda path, payload: writes.append((path, payload)),
        )

        result = interest_automation.build_interest_automation_board(runtime, settings, save_result=True)

        self.assertEqual(result["target_count"], 3)
        self.assertEqual(result["ticker_target_count"], 2)
        self.assertEqual(result["sector_target_count"], 1)
        self.assertEqual(result["portfolio_linked_count"], 1)
        self.assertEqual(result["rag_connected_count"], 2)
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0][1]["payload"]["module"], "interest_automation_board")
        self.assertTrue(result["rag_search_prompts"])


class NewsBuilderModuleTests(unittest.TestCase):
    def test_news_inbox_policy_law_classification_detects_regulatory_news(self):
        from research_os import news_inbox

        item = {
            "title": "금융위원회 AI 투자자문 규제 가이드라인 발표",
            "summary": "시행령 개정안과 감독 기준이 함께 공개되었습니다.",
            "tags": ["news_inbox"],
        }

        classified = news_inbox.apply_news_policy_law_classification(dict(item))

        self.assertTrue(classified["is_policy_law"])
        self.assertEqual(classified["scope"], "POLICY")
        self.assertIn("policy_law", classified["tags"])
        self.assertIn("regulation", classified["tags"])
        self.assertIn("legislation", classified["tags"])

    def test_news_builder_module_builds_url_only_item_with_body_warning(self):
        from research_os import news_builder

        runtime = SimpleNamespace(
            capture_preview_text=lambda text: str(text or "")[:80],
            capture_quality_status=lambda **_kwargs: {"status": "실패", "warnings": ["웹사이트 본문 추출 실패"]},
            compact_news_safe_text=lambda value, max_length=900: str(value or "")[:max_length],
            current_storage_timestamp=lambda: "2026-06-13T09:00:00+09:00",
            data_source_type_news="news",
            enum_or_str_value=lambda value: str(value),
            fetch_capture_source_url=lambda _url: {
                "status": "empty_text",
                "title": "FOMC recap",
                "final_url": "https://example.com/fomc-final",
                "note": "본문 텍스트를 충분히 추출하지 못했습니다.",
            },
            http_exception=lambda status_code, detail: ValueError(detail),
            infer_capture_source_type=lambda _content, _attachment: "news",
            infer_capture_tags=lambda _content, tags: list(tags),
            infer_capture_ticker=lambda _content, _settings: ("MARKET", "market_keyword"),
            infer_capture_title=lambda _content, _attachment: "Fallback title",
            is_unusable_source_url=lambda info: info.get("status") == "empty_text",
            news_item_fingerprint=lambda title, content, source_url=None: "abcdef1234567890",
            news_safe_preview_limit=120,
            news_scope_label=lambda scope: {"MARKET": "시장 흐름"}.get(scope, scope),
            sanitize_news_source_url_processing=lambda info: {k: v for k, v in info.items() if k != "text"},
            summarize_capture=lambda content: content[:60],
        )

        item = news_builder.build_news_item_from_payload(
            runtime,
            {"source_url": "https://example.com/fomc", "confidence": 0.81},
            SimpleNamespace(),
        )

        self.assertEqual(item["id"], "abcdef1234567890")
        self.assertEqual(item["source_url"], "https://example.com/fomc-final")
        self.assertTrue(item["needs_body_copy"])
        self.assertTrue(item["url_text_unavailable"])
        self.assertEqual(item["capture_quality"]["status"], "보강 필요")
        self.assertIn("URL-only 저장", item["capture_quality"]["warnings"])
        self.assertIn("copyright_safe_metadata", item["tags"])

    def test_news_builder_module_marks_policy_law_news_as_policy_scope(self):
        from research_os import news_builder

        runtime = SimpleNamespace(
            capture_preview_text=lambda text: str(text or "")[:80],
            capture_quality_status=lambda **_kwargs: {"status": "정상", "warnings": []},
            compact_news_safe_text=lambda value, max_length=900: str(value or "")[:max_length],
            current_storage_timestamp=lambda: "2026-06-24T09:00:00+09:00",
            data_source_type_news="news",
            enum_or_str_value=lambda value: str(value),
            fetch_capture_source_url=lambda _url: {},
            http_exception=lambda status_code, detail: ValueError(detail),
            infer_capture_source_type=lambda _content, _attachment: "news",
            infer_capture_tags=lambda _content, tags: list(tags),
            infer_capture_ticker=lambda _content, _settings: ("MARKET", "market_keyword"),
            infer_capture_title=lambda _content, _attachment: "정책 뉴스",
            is_unusable_source_url=lambda _info: False,
            news_item_fingerprint=lambda title, content, source_url=None: "policyabcdef1234",
            news_safe_preview_limit=120,
            news_scope_label=lambda scope: {"POLICY": "정책/규제", "MARKET": "시장 흐름"}.get(scope, scope),
            sanitize_news_source_url_processing=lambda info: info,
            summarize_capture=lambda content: content[:60],
        )

        item = news_builder.build_news_item_from_payload(
            runtime,
            {
                "title": "공정위 플랫폼 규제 법안 논의",
                "raw_content": "공정거래위원회가 시행령 개정안과 과징금 기준을 발표했습니다.",
            },
            SimpleNamespace(),
        )

        self.assertEqual(item["scope"], "POLICY")
        self.assertEqual(item["scope_label"], "정책/규제")
        self.assertTrue(item["is_policy_law"])
        self.assertEqual(item["scope_reason"], "policy_law_keyword")
        self.assertIn("policy_law", item["tags"])
        self.assertIn("regulatory_risk", item["tags"])

    def test_news_inbox_filter_counts_include_policy_law(self):
        from research_os import news_inbox

        runtime = SimpleNamespace(storage_quality_entry_is_policy_url_only=lambda _item: False)
        items = [
            {
                "title": "산업부 반도체 보조금 정책 발표",
                "summary": "세액공제 확대와 수출통제 대응 지원책",
                "tags": [],
                "relevance_score": 35,
            },
            {"title": "일반 뉴스", "summary": "시장 소식", "tags": []},
        ]

        counts = news_inbox.news_filter_counts(runtime, items)
        filtered = news_inbox.filter_news_inbox_items(runtime, items, "정책")
        actionable = news_inbox.filter_news_inbox_items(runtime, items, "우선")

        self.assertEqual(counts["policy_law"], 1)
        self.assertEqual(counts["actionable"], 1)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(len(actionable), 1)

    def test_news_builder_module_rejects_empty_input(self):
        from research_os import news_builder

        runtime = SimpleNamespace(
            fetch_capture_source_url=lambda _url: {},
            sanitize_news_source_url_processing=lambda _info: {},
            is_unusable_source_url=lambda _info: False,
            compact_news_safe_text=lambda value, max_length=900: str(value or "")[:max_length],
            news_safe_preview_limit=120,
            http_exception=lambda status_code, detail: ValueError(detail),
        )

        with self.assertRaises(ValueError):
            news_builder.build_news_item_from_payload(runtime, {}, SimpleNamespace())


class MarketJournalAnalysisModuleTests(unittest.TestCase):
    def test_market_journal_analysis_cleans_tags_and_actions(self):
        from research_os import market_journal_analysis

        raw = "▲ AI 반도체 상승 +1.5%, 금리 안정으로 risk-on rally"
        sentiment, risk_level, regime = market_journal_analysis.infer_market_close_sentiment(raw)
        tags = market_journal_analysis.infer_market_tags(raw)
        lines = market_journal_analysis.summarize_market_lines(raw)
        actions = market_journal_analysis.build_market_portfolio_actions(sentiment, risk_level, regime)
        aliases = market_journal_analysis.market_tag_aliases(tags)

        self.assertEqual(sentiment, "긍정")
        self.assertEqual(regime, "위험 선호")
        self.assertIn("AI", tags)
        self.assertIn("반도체", tags)
        self.assertTrue(lines[0])
        self.assertTrue(actions)
        self.assertTrue(market_journal_analysis.text_matches_market_tags("GPU", aliases))



class MarketJournalRenderingModuleTests(unittest.TestCase):
    def test_market_journal_rendering_outputs_review_sections(self):
        from research_os import market_journal_rendering

        runtime = SimpleNamespace(market_research_key=lambda market: f"MARKET-{market}")
        entry = SimpleNamespace(
            market="US",
            session_date="2026-06-17",
            sentiment="긍정",
            risk_level="보통",
            regime="위험 선호",
            tags=["AI", "금리"],
            key_drivers=["나스닥 강세"],
            market_index_snapshot=[],
            sector_implications=["AI 주도주 확인"],
            auto_utilization_focus=["포트폴리오 베타 점검"],
            interest_implications=["관심종목 논거 업데이트"],
            portfolio_actions=["추격 매수 자제"],
            next_session_watch=["10년물 금리"],
            attachment={"source": "telegram", "extracted_text": "숨김"},
            raw_summary="미국 시장 요약",
        )
        response = SimpleNamespace(entry=entry, history_count=7, cumulative_patterns=["긍정 우세"])

        markdown = market_journal_rendering.render_market_close_markdown(runtime, response, date(2026, 6, 18))

        self.assertIn("ticker: MARKET-US", markdown)
        self.assertIn("# US 폐장 후 시장 리뷰: 2026-06-17", markdown)
        self.assertIn("- 누적 기록 수: 7", markdown)
        self.assertIn("- source: telegram", markdown)
        self.assertNotIn("숨김", markdown)
class NewsMarketJournalModuleTests(unittest.TestCase):
    def test_market_journal_patterns_summarize_recent_entries(self):
        from research_os.market_journal_patterns import cumulative_market_patterns

        entries = [
            SimpleNamespace(market="US", sentiment="긍정", risk_level="낮음", tags=["AI", "금리"]),
            SimpleNamespace(market="US", sentiment="긍정", risk_level="보통", tags=["AI"]),
            SimpleNamespace(market="US", sentiment="부정", risk_level="높음", tags=["달러"]),
        ]

        patterns, summary = cumulative_market_patterns(entries, "US")

        self.assertIn("긍정 2회", patterns[0])
        self.assertTrue(any("AI 2회" in item for item in patterns))
        self.assertIn("US 최근 3회 누적", summary)

    def test_news_market_journal_module_reads_existing_summary(self):
        from research_os import news_market_journal

        runtime = SimpleNamespace(
            read_market_close_journal=lambda _settings: {
                "entries": [
                    {"market": "US", "session_date": "2026-06-12", "raw_summary": "old"},
                    {"market": "KR", "session_date": "2026-06-13", "raw_summary": "국내 요약"},
                ]
            }
        )

        result = news_market_journal.market_journal_existing_summary(runtime, SimpleNamespace(), "KR", "2026-06-13")

        self.assertEqual(result, "국내 요약")

    def test_news_market_focus_builds_interest_implications(self):
        from research_os import news_market_focus

        class FakeTicker:
            @classmethod
            def model_validate(cls, raw_item):
                return SimpleNamespace(
                    ticker=raw_item["ticker"],
                    thesis=raw_item.get("thesis"),
                    notes=raw_item.get("notes"),
                    tags=raw_item.get("tags", []),
                    verification=SimpleNamespace(company_name=raw_item.get("company_name")),
                )

        class FakeSector:
            @classmethod
            def model_validate(cls, raw_item):
                return SimpleNamespace(
                    name=raw_item["name"],
                    thesis=raw_item.get("thesis"),
                    notes=raw_item.get("notes"),
                    tags=raw_item.get("tags", []),
                )

        runtime = SimpleNamespace(
            InterestTicker=FakeTicker,
            InterestSector=FakeSector,
            read_interest_list=lambda _settings: {
                "tickers": [{"ticker": "NVDA", "company_name": "NVIDIA", "tags": ["AI"]}],
                "sectors": [{"name": "반도체", "tags": ["AI", "GPU"]}],
            },
        )

        implications = news_market_focus.build_market_interest_implications(
            runtime,
            raw_summary="NVIDIA GPU demand lifted AI semiconductor sentiment.",
            tags=["AI"],
            settings=SimpleNamespace(),
        )

        self.assertTrue(any("관심종목 NVDA" in item for item in implications))
        self.assertTrue(any("관심섹터 반도체" in item for item in implications))

    def test_news_market_journal_module_saves_standard_review_payload(self):
        from research_os import news_market_journal

        saves = []

        class FakeResponse(SimpleNamespace):
            def model_dump(self, mode="json"):
                return {"entry": self.entry.model_dump(mode=mode)}

        class DumpEntry(SimpleNamespace):
            def model_dump(self, mode="json"):
                return dict(self.__dict__)

        runtime = SimpleNamespace(
            market_research_key=lambda market: f"MARKET-{market}",
            render_market_close_markdown=lambda response, report_date: f"# {response.entry.market} {report_date}",
            save_research_markdown=lambda **kwargs: saves.append(kwargs) or SimpleNamespace(relative_path="research_vault/MARKET-KR/a.md"),
        )
        entry = DumpEntry(
            market="KR",
            session_date="2026-06-13",
            sentiment="중립",
            risk_level="보통",
            regime="혼조",
            tags=["semiconductor"],
            auto_utilization_focus={"focus": "risk"},
            interest_implications=["관심종목 점검"],
        )
        response = FakeResponse(entry=entry, storage=None)
        vault_dir = PROJECT_ROOT / ".test-tmp" / "market-close-storage"

        saved = news_market_journal.save_market_close_review_response(
            runtime,
            response=response,
            entry=entry,
            vault_dir=vault_dir,
            report_date=date(2026, 6, 13),
        )

        self.assertIs(saved, response)
        self.assertEqual(saves[0]["ticker"], "MARKET-KR")
        self.assertEqual(saves[0]["report_type"], "market-close-review")
        self.assertIn("KR 2026-06-13 폐장 리뷰", saves[0]["manifest_entry"]["summary"])
        self.assertEqual(saves[0]["manifest_entry"]["sentiment"], "중립")
        self.assertEqual(saves[0]["manifest_entry"]["risk_level"], "보통")
        self.assertEqual(saves[0]["manifest_entry"]["auto_utilization_focus"], {"focus": "risk"})
        self.assertEqual(saves[0]["manifest_entry"]["interest_implications"], ["관심종목 점검"])
        self.assertTrue(saves[0]["overwrite_existing"])

    def test_news_market_journal_module_saves_entry_and_markdown(self):
        from research_os import news_market_journal

        writes = []
        saves = []

        class FakeEntry:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

            @classmethod
            def model_validate(cls, raw_entry):
                return cls(**raw_entry)

            def model_dump(self, mode="json"):
                return dict(self.__dict__)

        class FakeResponse:
            status = "success"
            module = "market_close_review"

            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)
                self.status = "success"
                self.module = "market_close_review"
                self.storage = None

        runtime = SimpleNamespace(
            MarketCloseEntry=FakeEntry,
            MarketCloseReviewResponse=FakeResponse,
            build_auto_market_utilization_focus=lambda **_kwargs: {"focus": "risk"},
            build_market_interest_implications=lambda **_kwargs: ["implication"],
            build_market_next_watch=lambda _tags, _market: ["watch"],
            build_market_portfolio_actions=lambda _sentiment, _risk, _regime: ["action"],
            build_sector_implications=lambda _summary, _tags: ["sector"],
            capture_quality_status=lambda raw_content: {"status": "정상", "text_length": len(raw_content)},
            clean_market_summary_text=lambda text: text,
            compact_interest_text=lambda text, limit: str(text)[:limit],
            cumulative_market_patterns=lambda entries, market: ([f"{market} pattern"], "regime summary"),
            current_storage_date=lambda: date(2026, 6, 13),
            current_storage_timestamp=lambda: "2026-06-13T09:00:00+09:00",
            infer_market_close_sentiment=lambda _summary: ("positive", "low", "risk-on"),
            infer_market_from_news_item=lambda _item: "US",
            infer_market_tags=lambda _summary: ["macro"],
            market_close_journal_path=lambda _settings: Path("market_journal.json"),
            market_research_key=lambda market: f"MARKET-{market}",
            news_item_safe_view=lambda item: dict(item),
            read_market_close_journal=lambda _settings: {"entries": []},
            render_market_close_markdown=lambda response, report_date: f"# {response.entry.market} {report_date}",
            resolve_vault_dir=lambda value: Path(value),
            save_research_markdown=lambda **kwargs: saves.append(kwargs) or SimpleNamespace(relative_path="research_vault/MARKET-US/a.md"),
            summarize_market_lines=lambda _summary: ["driver"],
            write_json_store=lambda path, payload: writes.append((path, payload)),
        )
        settings = SimpleNamespace(research_vault_dir="research_vault")
        item = {
            "title": "FOMC update",
            "source_url": "https://example.com/fomc",
            "raw_content": "FOMC and NASDAQ risk-on update",
        }

        response = news_market_journal.save_news_item_to_market_journal(runtime, item, settings)

        self.assertEqual(response.entry.market, "US")
        self.assertEqual(response.entry.session_date, "2026-06-13")
        self.assertEqual(response.history_count, 1)
        self.assertEqual(len(writes), 1)
        self.assertEqual(len(saves), 1)
        self.assertEqual(saves[0]["ticker"], "MARKET-US")
        self.assertEqual(saves[0]["report_type"], "market-close-review")
        self.assertIn("news_inbox", saves[0]["structured_payload"]["source"])


class NewsActionModuleTests(unittest.TestCase):
    def test_news_action_module_marks_market_journal_candidate(self):
        from research_os import news_actions

        runtime = SimpleNamespace(
            current_storage_timestamp=lambda: "2026-06-13T09:00:00+09:00",
            news_scope_label=lambda scope: {"MARKET": "시장 흐름"}.get(scope, scope),
            http_exception=RuntimeError,
        )
        item = {"id": "n1", "tags": ["macro"]}

        result = news_actions.update_news_inbox_item_action(runtime, item, "시장일지")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["item"]["scope"], "MARKET")
        self.assertEqual(result["item"]["scope_label"], "시장 흐름")
        self.assertEqual(result["item"]["review_status"], "시장일지 후보")
        self.assertIn("market_journal_candidate", result["item"]["tags"])

    def test_news_action_module_infers_market_from_text_and_scope(self):
        from research_os import news_actions

        self.assertEqual(
            news_actions.infer_market_from_news_item({"title": "코스피와 원화 흐름", "tags": []}),
            "KR",
        )
        self.assertEqual(
            news_actions.infer_market_from_news_item({"summary": "FOMC and NASDAQ rallied", "tags": []}),
            "US",
        )
        self.assertEqual(
            news_actions.infer_market_from_news_item({"scope": "MARKET-US", "tags": []}),
            "US",
        )
        self.assertEqual(news_actions.infer_market_from_news_item({"tags": []}), "GLOBAL")


class NewsInboxModuleTests(unittest.TestCase):
    def test_news_inbox_module_fingerprint_uses_runtime_callback(self):
        from research_os import news_inbox

        calls = []
        runtime = SimpleNamespace(
            content_fingerprint=lambda text: calls.append(text) or "hash-value",
        )

        result = news_inbox.news_item_fingerprint(runtime, "Title", "Body", "HTTPS://Example.com/Article ")

        self.assertEqual(result, "hash-value")
        self.assertEqual(calls, ["url::https://example.com/article"])

    def test_news_inbox_module_filters_and_sanitizes_safe_view(self):
        from research_os import news_inbox

        runtime = SimpleNamespace(storage_quality_entry_is_policy_url_only=lambda _item: False)
        item = {
            "id": "n1",
            "title": "시장 뉴스",
            "source_url": "https://example.com/news",
            "raw_content": "본문" * 500,
            "tags": ["needs_body_copy"],
            "capture_quality": {"status": "보강 필요"},
            "source_url_processing": {
                "status": "empty_text",
                "text": "원문 본문" * 300,
                "raw_text": "저장되면 안 되는 원문",
            },
        }

        keys = news_inbox.news_filter_key(runtime, item)
        safe_item = news_inbox.news_item_safe_view(item)

        self.assertIn("needs_body", keys)
        self.assertIn("url_only", keys)
        self.assertIn("quality_issue", keys)
        self.assertLessEqual(len(safe_item["raw_content"]), news_inbox.NEWS_SAFE_TEXT_LIMIT + 3)
        self.assertNotIn("raw_text", safe_item["source_url_processing"])
        self.assertFalse(safe_item["source_url_processing"]["full_text_stored"])
        self.assertIn("copyright_safe_metadata", safe_item["tags"])

    def test_news_inbox_module_build_payload_applies_filter_counts(self):
        from research_os import news_inbox

        payload = {
            "updated_at": "2026-06-13T09:00:00+09:00",
            "items": [
                {
                    "id": "n1",
                    "created_at": "2026-06-13T08:00:00+09:00",
                    "title": "URL only",
                    "source_url": "https://example.com/a",
                    "tags": ["url_only"],
                    "capture_quality": {"status": "보강 필요"},
                    "target_matches": [{"label": "AI"}],
                },
                {
                    "id": "n2",
                    "created_at": "2026-06-12T08:00:00+09:00",
                    "title": "Promoted",
                    "promoted": True,
                    "promoted_storage": {"relative_path": "research_vault/MARKET/a.md"},
                    "capture_quality": {"status": "보강 필요"},
                },
                {
                    "id": "n3",
                    "created_at": "2026-06-14T08:00:00+09:00",
                    "title": "URL only duplicate",
                    "source_url": "https://example.com/a?page=2",
                    "target_matches": [{"label": "AI"}],
                    "relevance_score": 40,
                },
            ],
        }
        runtime = SimpleNamespace(
            news_inbox_path=lambda _settings: "news_inbox",
            read_json_store=lambda _path, _default=None: payload,
            storage_quality_entry_is_policy_url_only=lambda _item: False,
        )

        result = news_inbox.build_news_inbox_payload(runtime, SimpleNamespace(), limit=10, filter_key="needs_body")
        actionable = news_inbox.build_news_inbox_payload(runtime, SimpleNamespace(), limit=10, filter_key="actionable")

        self.assertEqual(result["count"], 3)
        self.assertEqual(result["actionable_unpromoted_count"], 2)
        self.assertEqual(result["filter_counts"]["needs_body"], 1)
        self.assertEqual(result["quality_issue_count"], 1)
        self.assertEqual([item["id"] for item in result["items"]], ["n1"])
        self.assertEqual([item["id"] for item in actionable["items"]], ["n3", "n1"])
        self.assertEqual([item["id"] for item in actionable["priority_news_preview"]], ["n3", "n1"])
        self.assertEqual(actionable["duplicate_priority_group_count"], 1)
        self.assertEqual(actionable["duplicate_priority_groups"][0]["canonical_url"], "https://example.com/a")


class NewsInboxPriorityQueueCheckToolTests(unittest.TestCase):
    def test_news_inbox_priority_queue_summarizes_actionable_items(self):
        tool = load_news_inbox_priority_queue_tool()

        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "backend").mkdir()
            (root / "backend" / "research_os_main.py").write_text("", encoding="utf-8")
            store_dir = root / "research_vault" / "_system"
            store_dir.mkdir(parents=True)
            (store_dir / "news_inbox.json").write_text(
                json.dumps(
                    {
                        "updated_at": "2026-07-02T08:00:00+09:00",
                        "items": [
                            {
                                "id": "p1",
                                "title": "AI 규제 가이드라인 발표",
                                "source_url": "https://example.com/policy",
                                "scope": "POLICY",
                                "relevance_score": 37,
                                "target_matches": [{"label": "피지컬 AI"}],
                            },
                            {
                                "id": "n1",
                                "title": "일반 뉴스",
                                "source_url": "https://example.com/news",
                                "relevance_score": 3,
                            },
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            status = tool.build_priority_queue_status(root, limit=7)

        self.assertEqual(status["total_count"], 2)
        self.assertEqual(status["priority_count"], 1)
        self.assertEqual(status["policy_priority_count"], 1)
        self.assertEqual(status["target_matched_count"], 1)
        self.assertEqual(status["queue"][0]["id"], "p1")
        self.assertIn("타깃 매칭", status["queue"][0]["reason"])
        self.assertEqual(tool.strict_errors(status), [])

    def test_news_inbox_priority_queue_cli_supports_json_output(self):
        tool_source = (PROJECT_ROOT / "tools" / "check_news_inbox_priority_queue.py").read_text(encoding="utf-8")

        self.assertIn('parser.add_argument("--json"', tool_source)
        self.assertIn('"errors": errors', tool_source)
        self.assertIn("json.dumps(result", tool_source)

    def test_news_inbox_priority_queue_groups_duplicate_priority_urls(self):
        from research_os import news_inbox

        items = [
            {
                "id": "n1",
                "title": "AI 관계장관 간담회",
                "source_url": "https://www.korea.kr/briefing/pressReleaseView.do?newsId=156769176&pageIndex=1&startDate=2025-07-02",
            },
            {
                "id": "n2",
                "title": "AI 관계장관 간담회",
                "source_url": "https://www.korea.kr/briefing/pressReleaseView.do?newsId=156769176&pageIndex=1&startDate=2025-07-01",
            },
            {
                "id": "n3",
                "title": "다른 정책 뉴스",
                "source_url": "https://example.com/policy?id=42&utm_source=test",
            },
        ]

        groups = news_inbox.duplicate_priority_news_groups(items)

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["count"], 2)
        self.assertEqual(
            groups[0]["canonical_url"],
            "https://www.korea.kr/briefing/pressReleaseView.do?newsId=156769176",
        )
        self.assertEqual([entry["id"] for entry in groups[0]["entries"]], ["n1", "n2"])
        self.assertEqual(groups[0]["entries"][0]["relevance_score"], 0.0)

    def test_news_inbox_priority_queue_cli_prints_duplicate_ids(self):
        tool_source = (PROJECT_ROOT / "tools" / "check_news_inbox_priority_queue.py").read_text(encoding="utf-8")

        self.assertIn('id_note = f" | ids {ids}"', tool_source)
        self.assertIn("group.get(\"ids\", [])", tool_source)

    def test_news_inbox_priority_queue_strict_errors_validate_shapes(self):
        tool = load_news_inbox_priority_queue_tool()
        status = {
            "total_count": 1,
            "filter_counts": {"actionable": 1},
            "priority_count": 1,
            "queue": [
                {
                    "rank": 1,
                    "title": "",
                    "source_url": "not-a-url",
                    "scope": "INBOX",
                    "is_policy_law": True,
                }
            ],
        }

        errors = tool.strict_errors(status)

        self.assertTrue(any("제목" in error for error in errors))
        self.assertTrue(any("URL" in error for error in errors))
        self.assertTrue(any("POLICY" in error for error in errors))


class StorageDuplicateReviewCheckToolTests(unittest.TestCase):
    def test_storage_duplicate_review_summarizes_policy_and_files(self):
        tool = load_storage_duplicate_review_tool()

        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "backend").mkdir()
            (root / "backend" / "research_os_main.py").write_text("", encoding="utf-8")
            system_dir = root / "research_vault" / "_system"
            research_dir = root / "research_vault" / "SECTOR"
            system_dir.mkdir(parents=True)
            research_dir.mkdir(parents=True)
            (research_dir / "rep.md").write_text("# 대표", encoding="utf-8")
            (research_dir / "dup.md").write_text("# 중복", encoding="utf-8")
            (system_dir / "storage_duplicate_review.json").write_text(
                json.dumps(
                    {
                        "status": "success",
                        "as_of": "2026-07-02T08:00:00+09:00",
                        "checked_count": 2,
                        "unique_representative_count": 1,
                        "duplicate_group_count": 1,
                        "duplicate_entry_count": 1,
                        "representative_policy": {
                            "dossier_usage": "representative_only",
                            "duplicate_usage": "excluded_from_dossier",
                            "hard_delete_allowed": False,
                        },
                        "dossier_usage_summary": {"duplicate_excluded_count": 1},
                        "groups": [
                            {
                                "group_id": "g1",
                                "ticker": "SECTOR",
                                "duplicate_count": 1,
                                "representative": {"title": "대표", "relative_path": "research_vault/SECTOR/rep.md"},
                                "duplicates": [{"title": "중복", "relative_path": "research_vault/SECTOR/dup.md"}],
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            status = tool.summarize_duplicate_review(root)

        self.assertEqual(status["duplicate_group_count"], 1)
        self.assertEqual(status["duplicate_entry_count"], 1)
        self.assertEqual(status["calculated_duplicate_entry_count"], 1)
        self.assertEqual(status["representative_missing"], [])
        self.assertEqual(status["duplicate_missing"], [])
        self.assertEqual(tool.strict_errors(status, max_age_hours=10**9), [])

    def test_storage_duplicate_review_cli_supports_json_output(self):
        tool_source = (PROJECT_ROOT / "tools" / "check_storage_duplicate_review.py").read_text(encoding="utf-8")

        self.assertIn('parser.add_argument("--json"', tool_source)
        self.assertIn('"errors": errors', tool_source)
        self.assertIn("json.dumps(result", tool_source)

    def test_storage_duplicate_review_formats_duplicate_preview_lines(self):
        tool = load_storage_duplicate_review_tool()

        lines = tool.duplicate_preview_lines(
            {
                "duplicates": [
                    {
                        "title": "중복 리포트",
                        "duplicate_reason": "title_body_similarity",
                        "similarity": 0.875,
                        "source_url": "https://example.com/report",
                    }
                ]
            }
        )

        self.assertEqual(len(lines), 1)
        self.assertIn("중복 리포트", lines[0])
        self.assertIn("title_body_similarity", lines[0])
        self.assertIn("유사도 0.88", lines[0])
        self.assertIn("https://example.com/report", lines[0])

    def test_storage_duplicate_review_strict_errors_validate_policy(self):
        tool = load_storage_duplicate_review_tool()
        status = {
            "status": "success",
            "age_hours": 1,
            "duplicate_group_count": 1,
            "duplicate_entry_count": 2,
            "calculated_duplicate_entry_count": 1,
            "groups": [{}],
            "representative_policy": {
                "dossier_usage": "all",
                "duplicate_usage": "included",
                "hard_delete_allowed": True,
            },
            "dossier_usage_summary": {"duplicate_excluded_count": 0},
            "representative_missing": ["missing-rep.md"],
            "duplicate_missing": ["missing-dup.md"],
        }

        errors = tool.strict_errors(status)

        self.assertTrue(any("대표" in error for error in errors))
        self.assertTrue(any("excluded_from_dossier" in error for error in errors))
        self.assertTrue(any("hard delete" in error for error in errors))
        self.assertTrue(any("중복 항목 수" in error for error in errors))


class MacroSourceSignalLinkageCheckToolTests(unittest.TestCase):
    def test_macro_source_signal_linkage_summarizes_kcif_and_regional_sources(self):
        tool = load_macro_source_signal_linkage_tool()

        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "backend").mkdir()
            (root / "backend" / "research_os_main.py").write_text("", encoding="utf-8")
            system_dir = root / "research_vault" / "_system"
            system_dir.mkdir(parents=True)
            (system_dir / "kcif_reports_watch.json").write_text(
                json.dumps(
                    {
                        "reports": [
                            {
                                "title": "미국 고용지표",
                                "matched_themes": ["금리/채권"],
                                "recommended_action": "시장일지에 반영하세요.",
                                "detail_analysis": {
                                    "raw_text_stored": False,
                                    "source_summary_available": True,
                                    "derived_points": ["금리 신호"],
                                },
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (system_dir / "regional_business_sources_watch.json").write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "title": "중국 반도체",
                                "source_provider": "KIEP",
                                "matched_themes": ["AI/반도체"],
                                "target_matches": [{"ticker": "005930"}],
                                "recommended_action": "보유종목 리스크 메모에 반영하세요.",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            status = tool.source_linkage_status(root)

        self.assertEqual(status["kcif_count"], 1)
        self.assertEqual(status["regional_count"], 1)
        self.assertEqual(status["linked_count"], 2)
        self.assertEqual(status["target_linked_count"], 1)
        self.assertEqual(status["theme_only_count"], 1)
        self.assertEqual(status["unlinked_count"], 0)
        self.assertEqual(status["action_count"], 2)
        self.assertEqual(status["kcif_detail_ready_count"], 1)
        self.assertEqual(status["sample_target_links"][0]["target_labels"], ["005930"])
        self.assertEqual(tool.strict_errors(status), [])

    def test_macro_source_signal_linkage_strict_errors_validate_empty_links(self):
        tool = load_macro_source_signal_linkage_tool()
        status = {
            "kcif_count": 1,
            "regional_count": 1,
            "total_count": 2,
            "linked_count": 1,
            "action_count": 0,
            "kcif_detail_ready_count": 0,
        }

        errors = tool.strict_errors(status)

        self.assertTrue(any("연결률" in error for error in errors))
        self.assertTrue(any("recommended_action" in error for error in errors))
        self.assertTrue(any("KCIF" in error for error in errors))


class AutomationStatusModuleTests(unittest.TestCase):
    def test_automation_status_module_catches_rag_status_errors(self):
        from research_os import automation_status

        def failing_rag_status(_vault_dir):
            raise RuntimeError("index unavailable")

        runtime = SimpleNamespace(rag_memory_status=failing_rag_status)

        result = automation_status.safe_rag_memory_status(runtime, Path("vault"))

        self.assertEqual(result["document_count"], 0)
        self.assertIn("index unavailable", result["warning"])

    def test_automation_digest_uses_total_news_inbox_count(self):
        from research_os import automation_status

        settings = SimpleNamespace(
            research_vault_dir="vault",
            daily_recommendations_enabled=True,
            daily_recommendations_time="08:00",
        )
        stores = {
            "interest_targets": {
                "payload": {
                    "target_count": 1,
                    "ticker_target_count": 1,
                    "sector_target_count": 0,
                    "portfolio_linked_count": 1,
                    "rag_connected_count": 1,
                    "ticker_targets": [],
                    "sector_targets": [],
                }
            },
            "automation": {"dossier_count": 0, "failed_count": 0, "daily_brief_date": "2026-06-18"},
            "duplicate": {},
            "refresh_queue": {},
            "daily_state": {},
        }
        runtime = SimpleNamespace(
            resolve_vault_dir=lambda _path: Path("vault"),
            interest_collection_targets_path=lambda _settings: "interest_targets",
            research_automation_status_path=lambda _settings: "automation",
            storage_duplicate_review_path=lambda _settings: "duplicate",
            dossier_refresh_queue_status_path=lambda _settings: "refresh_queue",
            daily_recommendation_state_path=lambda _settings: "daily_state",
            read_json_store=lambda path, default=None: stores.get(path, default or {}),
            read_latest_daily_brief=lambda _settings: {"payload": {"date": "2026-06-18"}},
            rag_memory_status=lambda _vault_dir: {"document_count": 9, "snapshot_count": 2},
            build_news_inbox_payload=lambda _settings, limit=10: {
                "items": [{"id": "n1"}],
                "count": 122,
                "unpromoted_count": 115,
                "actionable_unpromoted_count": 7,
                "quality_issue_count": 0,
                "priority_news_preview": [{"id": "n1", "title": "AI 정책"}],
                "duplicate_priority_groups": [{"canonical_url": "https://example.com/a", "count": 2}],
            },
            build_external_source_schedule_status=lambda _settings: [],
            summarize_daily_recommendation_store=lambda _settings, limit=10: {"latest_recommendation_date": "2026-06-18"},
            should_run_daily_recommendations=lambda _settings: False,
            build_nps_domestic_equity_allocation_status=lambda _settings: {"status": "within_target"},
            read_kcif_reports_watch=lambda _settings: {},
            should_refresh_kcif_cache=lambda _watch: False,
            read_regional_business_sources_watch=lambda _settings: {},
            should_refresh_regional_business_cache=lambda _watch: False,
            read_dart_filing_cache=lambda _settings: {},
            dart_daily_check_status=lambda _cache, _settings: {"due": False, "failure_count": 0},
            current_storage_timestamp=lambda: "2026-06-18T09:00:00+09:00",
        )

        digest = automation_status.build_research_automation_dashboard_digest(runtime, settings)

        self.assertEqual(digest["news_inbox_count"], 122)
        self.assertEqual(digest["news_unpromoted_count"], 115)
        self.assertEqual(digest["news_actionable_unpromoted_count"], 7)
        self.assertEqual(digest["news_priority_count"], 7)
        self.assertEqual(digest["news_priority_preview_count"], 1)
        self.assertEqual(digest["news_priority_preview"][0]["title"], "AI 정책")
        self.assertEqual(digest["news_duplicate_priority_group_count"], 1)
        self.assertEqual(digest["news_duplicate_priority_entry_count"], 2)

    def test_automation_digest_next_action_uses_dossier_duplicate_review_count(self):
        from research_os import automation_status

        settings = SimpleNamespace(
            research_vault_dir="vault",
            daily_recommendations_enabled=True,
            daily_recommendations_time="08:00",
        )
        stores = {
            "interest_targets": {
                "payload": {
                    "target_count": 1,
                    "duplicate_suspected_count": 1338,
                    "ticker_targets": [],
                    "sector_targets": [],
                }
            },
            "automation": {"dossier_count": 0, "failed_count": 0, "daily_brief_date": "2026-06-18"},
            "duplicate": {"duplicate_entry_count": 19, "duplicate_group_count": 1},
            "refresh_queue": {},
            "daily_state": {},
        }
        runtime = SimpleNamespace(
            resolve_vault_dir=lambda _path: Path("vault"),
            interest_collection_targets_path=lambda _settings: "interest_targets",
            research_automation_status_path=lambda _settings: "automation",
            storage_duplicate_review_path=lambda _settings: "duplicate",
            dossier_refresh_queue_status_path=lambda _settings: "refresh_queue",
            daily_recommendation_state_path=lambda _settings: "daily_state",
            read_json_store=lambda path, default=None: stores.get(path, default or {}),
            read_latest_daily_brief=lambda _settings: {"payload": {"date": "2026-06-18"}},
            rag_memory_status=lambda _vault_dir: {"document_count": 9, "snapshot_count": 2},
            build_news_inbox_payload=lambda _settings, limit=10: {"items": [], "count": 0, "unpromoted_count": 0},
            build_external_source_schedule_status=lambda _settings: [],
            summarize_daily_recommendation_store=lambda _settings, limit=10: {"latest_recommendation_date": "2026-06-18"},
            should_run_daily_recommendations=lambda _settings: False,
            build_nps_domestic_equity_allocation_status=lambda _settings: {"status": "within_target"},
            read_kcif_reports_watch=lambda _settings: {},
            should_refresh_kcif_cache=lambda _watch: False,
            read_regional_business_sources_watch=lambda _settings: {},
            should_refresh_regional_business_cache=lambda _watch: False,
            read_dart_filing_cache=lambda _settings: {},
            dart_daily_check_status=lambda _cache, _settings: {"due": False, "failure_count": 0},
            current_storage_timestamp=lambda: "2026-06-18T09:00:00+09:00",
        )

        digest = automation_status.build_research_automation_dashboard_digest(runtime, settings)

        self.assertEqual(digest["duplicate_suspected_count"], 1338)
        self.assertTrue(any("중복 의심 자료 19개" in item for item in digest["next_actions"]))
        self.assertFalse(any("중복 의심 자료 1338개" in item for item in digest["next_actions"]))

    def test_automation_digest_includes_nps_rebalance_plan(self):
        from research_os import automation_status

        settings = SimpleNamespace(
            research_vault_dir="vault",
            daily_recommendations_enabled=True,
            daily_recommendations_time="08:00",
        )
        stores = {
            "interest_targets": {"payload": {"target_count": 1, "ticker_targets": [], "sector_targets": []}},
            "automation": {"dossier_count": 0, "failed_count": 0, "daily_brief_date": "2026-06-18"},
            "duplicate": {},
            "refresh_queue": {},
            "daily_state": {},
        }
        nps_monitor = {
            "status": "above_target",
            "recommended_action": "국내주식 노출이 목표보다 높습니다.",
        }
        nps_plan = {
            "status": "needs_reduction",
            "summary": "국내주식 14% 목표까지 축소 검토가 필요합니다.",
            "candidates": {"reduce": [{"ticker": "395160"}], "review": [], "keep": []},
        }
        runtime = SimpleNamespace(
            resolve_vault_dir=lambda _path: Path("vault"),
            interest_collection_targets_path=lambda _settings: "interest_targets",
            research_automation_status_path=lambda _settings: "automation",
            storage_duplicate_review_path=lambda _settings: "duplicate",
            dossier_refresh_queue_status_path=lambda _settings: "refresh_queue",
            daily_recommendation_state_path=lambda _settings: "daily_state",
            read_json_store=lambda path, default=None: stores.get(path, default or {}),
            read_latest_daily_brief=lambda _settings: {"payload": {"date": "2026-06-18"}},
            rag_memory_status=lambda _vault_dir: {"document_count": 9, "snapshot_count": 2},
            build_news_inbox_payload=lambda _settings, limit=10: {"items": [], "count": 0, "unpromoted_count": 0},
            build_external_source_schedule_status=lambda _settings: [],
            summarize_daily_recommendation_store=lambda _settings, limit=10: {"latest_recommendation_date": "2026-06-18"},
            should_run_daily_recommendations=lambda _settings: False,
            build_nps_domestic_equity_allocation_status=lambda _settings: nps_monitor,
            build_nps_domestic_equity_rebalance_plan=lambda monitor: nps_plan if monitor is nps_monitor else {},
            read_kcif_reports_watch=lambda _settings: {},
            should_refresh_kcif_cache=lambda _watch: False,
            read_regional_business_sources_watch=lambda _settings: {},
            should_refresh_regional_business_cache=lambda _watch: False,
            read_dart_filing_cache=lambda _settings: {},
            dart_daily_check_status=lambda _cache, _settings: {"due": False, "failure_count": 0},
            current_storage_timestamp=lambda: "2026-06-18T09:00:00+09:00",
        )

        digest = automation_status.build_research_automation_dashboard_digest(runtime, settings)

        self.assertEqual(digest["nps_domestic_equity_allocation"], nps_monitor)
        self.assertEqual(digest["nps_domestic_equity_rebalance_plan"], nps_plan)
        self.assertTrue(any("국내주식 노출" in item for item in digest["next_actions"]))

    def test_automation_digest_helpers_rank_targets_and_next_actions(self):
        from research_os.automation_digest_helpers import build_dashboard_next_actions
        from research_os.automation_digest_helpers import select_priority_targets

        targets = [
            {"ticker": "LOW", "priority": "low", "recent_document_count": 10, "rag_document_count": 10},
            {"ticker": "HIGH", "priority": "high", "recent_document_count": 1, "rag_document_count": 1},
        ]

        ranked = select_priority_targets(targets)
        actions = build_dashboard_next_actions(
            target_count=1,
            daily_brief_date="2026-06-18",
            duplicate_count=2,
            failed_count=0,
            news_unpromoted_count=0,
            news_actionable_unpromoted_count=0,
            news_quality_issue_count=0,
            kcif_due=False,
            kcif_related_count=3,
            regional_sources_due=False,
            regional_sources_related_count=0,
            dart_daily={"due": False, "failure_count": 0},
            daily_recommendations_due=False,
            daily_recommendations={"latest_recommendation_date": "2026-06-18"},
        )

        self.assertEqual(ranked[0]["ticker"], "HIGH")
        self.assertIn("중복 의심 자료 2개", actions[0])
        self.assertTrue(any("KCIF 관련 매크로 보고서 3개" in item for item in actions))
        self.assertTrue(any("2026-06-18 한국/미국 추천 후보" in item for item in actions))

    def test_automation_digest_next_actions_prioritize_actionable_news(self):
        from research_os.automation_digest_helpers import build_dashboard_next_actions

        actions = build_dashboard_next_actions(
            target_count=1,
            daily_brief_date="2026-06-18",
            duplicate_count=0,
            failed_count=0,
            news_unpromoted_count=115,
            news_actionable_unpromoted_count=7,
            news_quality_issue_count=0,
            kcif_due=False,
            kcif_related_count=0,
            regional_sources_due=False,
            regional_sources_related_count=0,
            dart_daily={"due": False, "failure_count": 0},
            daily_recommendations_due=False,
            daily_recommendations={"latest_recommendation_date": "2026-06-18"},
        )

        self.assertTrue(any("우선 분류 7개" in item and "전체 미승격 115개" in item for item in actions))

    def test_automation_schedule_status_builds_source_rows(self):
        from research_os import automation_schedule_status

        settings = SimpleNamespace(
            regional_business_sources_auto_refresh=True,
            regional_business_sources_refresh_hours=24,
            regional_business_sources_enabled=True,
            company_ir_sources_enabled=True,
            company_ir_sources_auto_refresh=True,
            company_ir_sources_refresh_hours=12,
            naver_research_enabled=True,
            naver_research_auto_refresh=True,
            naver_research_refresh_hours=24,
            shinhan_research_enabled=True,
            shinhan_research_auto_refresh=True,
            shinhan_research_refresh_hours=24,
            policy_sources_enabled=True,
            policy_sources_auto_refresh=True,
            policy_sources_refresh_hours=24,
            dart_api_key="dummy",
            dart_filing_auto_refresh=True,
            dart_filing_refresh_hours=24,
        )
        runtime = SimpleNamespace(
            dart_daily_check_status=lambda _cache, _settings: {"due": True, "target_count": 3},
            read_company_ir_sources_watch=lambda _settings: {"updated_at": "2026-06-18T06:00:00+09:00", "related_items": [{}]},
            read_dart_filing_cache=lambda _settings: {"updated_at": "2026-06-18T06:00:00+09:00", "status": "success"},
            read_kcif_reports_watch=lambda _settings: {"updated_at": "2026-06-18T06:00:00+09:00", "related_reports": [{}, {}], "source_status": "cached"},
            read_naver_research_cache=lambda _settings: {"updated_at": "2026-06-18T06:00:00+09:00", "entries": {"a": {}}, "status": "success"},
            read_policy_sources_watch=lambda _settings: {"updated_at": "2026-06-18T06:00:00+09:00", "related_items": [{}], "source_status": "cached"},
            read_regional_business_sources_watch=lambda _settings: {"updated_at": "2026-06-18T06:00:00+09:00", "related_items": [{}], "source_status": "cached"},
            read_shinhan_research_cache=lambda _settings: {"entries": {"a": {}, "b": {}}, "status": "success"},
            should_refresh_company_ir_cache=lambda _watch, refresh_hours=24: False,
            should_refresh_kcif_cache=lambda _watch: False,
            should_refresh_policy_sources_cache=lambda _watch, refresh_hours=24: False,
            should_refresh_regional_business_cache=lambda _watch: False,
        )

        rows = automation_schedule_status.build_external_source_schedule_status(runtime, settings)
        by_key = {row["key"]: row for row in rows}

        self.assertEqual(len(rows), 7)
        self.assertEqual(by_key["kcif_reports_watch"]["related_count"], 2)
        self.assertEqual(by_key["policy_sources_watch"]["related_count"], 1)
        self.assertFalse(by_key["policy_sources_watch"]["due"])
        self.assertTrue(by_key["shinhan_research"]["due"])
        self.assertEqual(by_key["dart_filing_watch"]["related_count"], 3)
        self.assertTrue(by_key["dart_filing_watch"]["due"])

    def test_automation_pipeline_uses_runtime_refresh_callbacks(self):
        from research_os import automation_status

        calls = []
        settings = SimpleNamespace(
            research_vault_dir="vault",
            daily_recommendations_enabled=True,
            daily_recommendations_time="09:00",
        )

        def refresh_source(name):
            def _refresh(_settings, *, limit, force, save_result):
                calls.append(name)
                return {"status": "success", "limit": limit, "save_result": save_result}

            return _refresh

        runtime = SimpleNamespace(
            backfill_research_memory_documents_from_manifest=lambda _vault_dir: {"updated_count": 0, "tickers": []},
            build_daily_brief_payload=lambda _settings: {"date": "2026-06-13"},
            build_external_source_schedule_status=lambda _settings: [],
            build_interest_automation_board=lambda _settings, save_result=False: {
                "target_count": 1,
                "ticker_target_count": 1,
                "sector_target_count": 0,
                "portfolio_linked_count": 1,
                "rag_connected_count": 1,
                "thesis_connected_count": 1,
                "duplicate_suspected_count": 0,
                "automation_steps": [],
                "next_actions": [],
                "ticker_targets": [],
                "sector_targets": [],
            },
            build_kcif_reports_watch_payload=lambda _settings, *, limit, force, save_result: {"status": "success"},
            build_news_inbox_payload=lambda _settings, limit=10: {"items": [], "count": 0, "unpromoted_count": 0, "quality_issue_count": 0},
            build_regional_business_sources_watch_payload=lambda _settings, *, limit, force, save_result: {"status": "success"},
            current_storage_timestamp=lambda: "2026-06-13T09:00:00+09:00",
            daily_recommendation_state_path=lambda _settings: "daily_recommendation_state",
            dart_daily_check_status=lambda _cache, _settings: {"due": False, "failure_count": 0},
            dossier_candidate_tickers=lambda _settings, limit=30: [],
            interest_collection_targets_path=lambda _settings: "interest_targets",
            provider_error_message=lambda exc, _settings: str(exc),
            rag_memory_status=lambda _vault_dir: {"document_count": 1, "snapshot_count": 1},
            read_dart_filing_cache=lambda _settings: {},
            read_json_store=lambda _path, default=None: {},
            read_kcif_reports_watch=lambda _settings: {"related_reports": [], "updated_at": "2026-06-13T08:00:00+09:00"},
            read_latest_daily_brief=lambda _settings: {"payload": {"date": "2026-06-13"}},
            read_manifest=lambda _vault_dir: [],
            read_news_inbox=lambda _settings: {"items": []},
            read_regional_business_sources_watch=lambda _settings: {"related_items": [], "updated_at": "2026-06-13T08:00:00+09:00"},
            refresh_naver_research_cache=refresh_source("naver"),
            refresh_shinhan_research_cache=refresh_source("shinhan"),
            research_automation_status_path=lambda _settings: "automation_status",
            resolve_vault_dir=lambda value: Path(value),
            save_daily_brief=lambda payload, _settings: payload,
            should_refresh_kcif_cache=lambda _payload: False,
            should_refresh_regional_business_cache=lambda _payload: False,
            should_run_daily_recommendations=lambda _settings: False,
            storage_duplicate_review_path=lambda _settings: "duplicate_review",
            summarize_daily_recommendation_store=lambda _settings, limit=10: {},
            synthesize_and_save_dossier=lambda ticker, _settings, save_result=False: {"ticker": ticker},
            dossier_refresh_queue_status_path=lambda _settings: "refresh_queue",
            write_json_store=lambda _path, _payload: calls.append("write_status"),
        )

        result = automation_status.run_research_automation_pipeline(runtime, settings, limit=2, save_result=False)

        self.assertEqual(calls[:2], ["shinhan", "naver"])
        self.assertIn("write_status", calls)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["automation_digest"]["daily_brief_date"], "2026-06-13")


class DailyBriefModuleTests(unittest.TestCase):
    def test_daily_brief_module_uses_runtime_date_for_thesis_age(self):
        from research_os import daily_brief

        runtime = SimpleNamespace(current_storage_date=lambda: date(2026, 6, 13))

        self.assertEqual(daily_brief.portfolio_thesis_date_age_days(runtime, "2026-06-01"), 12)
        self.assertIsNone(daily_brief.portfolio_thesis_date_age_days(runtime, "날짜 없음"))

    def test_daily_brief_module_renders_core_sections(self):
        from research_os import daily_brief

        payload = {
            "date": "2026-06-13",
            "generated_at": "2026-06-13T09:00:00+09:00",
            "portfolio_tickers": ["018260"],
            "snapshot_count": 1,
            "recent_entry_count": 1,
            "market_entries": [],
            "customs_trade_reference": {},
            "snapshots": [
                {
                    "ticker": "018260",
                    "updated_at": "2026-06-12T10:00:00+09:00",
                    "summary": "클라우드 매출 성장과 마진 개선",
                    "confidence": 0.82,
                }
            ],
            "portfolio_overview": {
                "snapshot_connected_count": 1,
                "holding_count": 1,
                "priority_reviews": [
                    {
                        "ticker": "018260",
                        "company_name": "삼성에스디에스",
                        "status": "정상",
                        "confidence": 0.82,
                        "recommended_action": "기존 논거와 비교",
                        "watch_kpis": ["클라우드 매출"],
                    }
                ],
            },
            "interest_automation": {"ticker_targets": [], "sector_targets": []},
            "recent_entries": [
                {
                    "ticker": "018260",
                    "type": "research-capture",
                    "date": "2026-06-12",
                    "summary": "신규 저장 자료",
                    "confidence": 0.8,
                }
            ],
            "next_actions": ["Dossier 논거 변화를 확인하세요."],
        }

        rendered = daily_brief.render_daily_brief_markdown(payload)

        self.assertIn("# 일일 리서치 브리핑", rendered)
        self.assertIn("## 포트폴리오 우선 점검", rendered)
        self.assertIn("삼성에스디에스(018260)", rendered)
        self.assertIn("Dossier 논거 변화를 확인하세요.", rendered)


class DossierSynthesisModuleTests(unittest.TestCase):
    def test_dossier_synthesis_renderer_formats_payload_sections(self):
        from research_os import dossier_synthesis

        markdown = dossier_synthesis.render_dossier_markdown(
            {
                "ticker": "PL",
                "company_name": "Planet Labs PBC",
                "date": "2026-06-18",
                "thesis_summary": "위성 데이터 수요를 핵심 논거로 추적합니다.",
                "source_count": 3,
                "duplicate_count": 1,
                "confidence": 0.82,
                "tags": ["dossier", "satellite"],
                "consensus_facts": ["매출 성장률 확인"],
                "bull_thesis": ["강세: 신규 계약 확대"],
                "bear_thesis": ["약세: 현금흐름 부담"],
                "cruxes": ["계약 성장 지속 여부"],
                "observables": ["매출 성장률: 다음 실적에서 확인"],
                "invalidation_conditions": ["성장률 둔화"],
                "latest_changes": [
                    {"date": "2026-06-18", "type": "broker-report", "summary": "계약 확대 업데이트"}
                ],
            }
        )

        self.assertIn("# Planet Labs PBC Dossier 합성 보고서", markdown)
        self.assertIn("- 고유 자료: 3개", markdown)
        self.assertIn("- 중복 제외: 1개", markdown)
        self.assertIn("- 합성 신뢰도: 82%", markdown)
        self.assertIn("2026-06-18 · broker-report · 계약 확대 업데이트", markdown)


class ResearchMemoryPolicyTests(unittest.TestCase):
    def test_dossier_text_module_dedupes_exact_manifest_entries(self):
        from research_os import dossier_text

        test_tmp_dir = PROJECT_ROOT / ".test-tmp"
        test_tmp_dir.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=test_tmp_dir, ignore_cleanup_errors=True) as temp_dir:
            vault_dir = Path(temp_dir) / "research_vault"
            stock_dir = vault_dir / "003230"
            stock_dir.mkdir(parents=True)
            first = stock_dir / "first.md"
            second = stock_dir / "second.md"
            body = "\n".join(
                [
                    "삼양식품 미국 채널 매출 성장률이 개선되고 있습니다.",
                    "불닭볶음면 글로벌 수요와 마진 개선이 핵심 투자 논거입니다.",
                    "환율과 원가 리스크는 감시하되 장기 성장 가시성은 유지됩니다.",
                ]
            )
            first.write_text(body, encoding="utf-8")
            second.write_text(body, encoding="utf-8")
            entries = [
                {
                    "ticker": "003230",
                    "type": "research-capture",
                    "date": "2026-05-24",
                    "file_name": first.name,
                    "relative_path": first.relative_to(vault_dir.parent).as_posix(),
                    "summary": "삼양식품 글로벌 수요와 마진 개선",
                    "content_hash": "same-content",
                },
                {
                    "ticker": "003230",
                    "type": "research-capture",
                    "date": "2026-05-24",
                    "file_name": second.name,
                    "relative_path": second.relative_to(vault_dir.parent).as_posix(),
                    "summary": "삼양식품 글로벌 수요와 마진 개선",
                    "content_hash": "same-content",
                },
            ]

            unique_entries, duplicates = dossier_text.dedupe_manifest_entries_by_similarity(entries, vault_dir)

        self.assertEqual([entry["file_name"] for entry in unique_entries], [first.name])
        self.assertEqual([entry["file_name"] for entry in duplicates], [second.name])
        self.assertEqual(duplicates[0]["duplicate_reason"], "exact_match")

    def test_dossier_text_module_detects_capture_duplicate_without_main_runtime(self):
        from research_os import dossier_text

        test_tmp_dir = PROJECT_ROOT / ".test-tmp"
        test_tmp_dir.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=test_tmp_dir, ignore_cleanup_errors=True) as temp_dir:
            vault_dir = Path(temp_dir) / "research_vault"
            stock_dir = vault_dir / "018260"
            stock_dir.mkdir(parents=True)
            existing = stock_dir / "existing.md"
            raw_content = "삼성에스디에스 클라우드 매출 성장과 영업이익 마진 개선이 확인된 리서치 본문입니다."
            existing.write_text(raw_content, encoding="utf-8")
            manifest = [
                {
                    "ticker": "018260",
                    "type": "research-capture",
                    "date": "2026-05-25",
                    "file_name": existing.name,
                    "relative_path": existing.relative_to(vault_dir.parent).as_posix(),
                    "summary": "클라우드 매출 성장과 마진 개선",
                    "source_url": "https://example.com/report",
                    "content_hash": dossier_text.content_fingerprint(raw_content),
                }
            ]

            result = dossier_text.detect_capture_duplicate(
                vault_dir=vault_dir,
                ticker="018260",
                title="삼성에스디에스 리서치",
                raw_content=raw_content,
                source_url="https://example.com/report",
                read_manifest_fn=lambda _vault_dir: manifest,
                summarize_capture_fn=lambda text: text[:60],
                special_research_keys=set(),
            )

        self.assertTrue(result["is_duplicate_suspected"])
        self.assertEqual(result["reason"], "source_url_exact_match")
        self.assertEqual(result["matched_file_name"], existing.name)

    def test_dossier_text_module_capture_quality_classifies_ready_and_failed(self):
        from research_os import dossier_text

        ready = dossier_text.capture_quality_status(raw_content="매출 성장과 마진 개선이 확인됩니다. " * 60)
        failed = dossier_text.capture_quality_status(
            raw_content="",
            attachment_info={
                "extraction_profile": {"ocr_status": "unavailable"},
            },
            source_url_processing={"status": "empty_text"},
        )

        self.assertEqual(ready["status"], "정상")
        self.assertEqual(failed["status"], "실패")
        self.assertIn("웹사이트 본문 추출 실패", failed["warnings"])
        self.assertIn("이미지 OCR 미연결", failed["warnings"])

    def test_dossier_capture_quality_module_flags_failed_entries(self):
        from research_os import dossier_capture_quality

        self.assertTrue(
            dossier_capture_quality.is_failed_capture_manifest_entry(
                {"relative_path": "research_vault/winerror-10061.md"}
            )
        )
        quality = dossier_capture_quality.capture_quality_status(
            raw_content="",
            source_url_processing={"status": "fetch_failed"},
        )

        self.assertEqual(quality["status"], "실패")
        self.assertEqual(quality["url_status"], "fetch_failed")
        self.assertIn("분석 반영 제외", quality["readiness"])

    def test_manifest_similarity_text_drops_naver_url_noise_summary(self):
        from research_os import dossier_text

        text = dossier_text.manifest_similarity_text(
            {
                "title": "Daily Morning Brief",
                "summary": "com/research/market_info_read.",
            },
            "",
        )
        tokens = dossier_text.similarity_tokens(text)

        self.assertNotIn("com", tokens)
        self.assertNotIn("research", tokens)
        self.assertNotIn("market_info_read", tokens)

    def test_dossier_similarity_module_hashes_and_scores_tokens(self):
        from research_os import dossier_similarity

        left = dossier_similarity.similarity_tokens("Revenue growth margin expansion")
        right = dossier_similarity.similarity_tokens("growth margin risk")

        self.assertEqual(
            dossier_similarity.content_fingerprint("  SAME   Text "),
            dossier_similarity.content_fingerprint("same text"),
        )
        self.assertIn("growth", left)
        self.assertGreater(dossier_similarity.token_jaccard_similarity(left, right), 0)
        self.assertEqual(dossier_similarity.token_jaccard_similarity(set(), right), 0.0)

    def test_duplicate_review_excludes_soft_archived_files(self):
        import json
        import research_os_main as main
        from research_os.settings import Settings

        test_tmp_dir = PROJECT_ROOT / ".test-tmp"
        test_tmp_dir.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=test_tmp_dir, ignore_cleanup_errors=True) as temp_dir:
            vault_dir = Path(temp_dir) / "research_vault"
            stock_dir = vault_dir / "003230"
            stock_dir.mkdir(parents=True)
            active_a = stock_dir / "003230-research-capture-2026-05-24-a.md"
            active_b = stock_dir / "003230-research-capture-2026-05-24-b.md"
            archived = stock_dir / "003230-research-capture-2026-05-24-old.md"
            duplicate_text = "\n".join(
                [
                    "삼양식품 수출 성장과 불닭볶음면 글로벌 수요가 핵심입니다.",
                    "미국과 유럽 채널 확장으로 매출 성장 가시성이 높습니다.",
                    "원가와 환율 리스크는 감시해야 하지만 장기 논거는 유지됩니다.",
                    "동일한 리서치 본문을 중복 저장한 테스트 문서입니다.",
                ]
            )
            for path in (active_a, active_b, archived):
                path.write_text(duplicate_text, encoding="utf-8")
            manifest = [
                {
                    "ticker": "003230",
                    "type": "research-capture",
                    "date": "2026-05-24",
                    "file_name": active_a.name,
                    "relative_path": active_a.relative_to(vault_dir.parent).as_posix(),
                    "summary": "삼양식품 수출 성장",
                    "content_hash": "same-active",
                },
                {
                    "ticker": "003230",
                    "type": "research-capture",
                    "date": "2026-05-24",
                    "file_name": active_b.name,
                    "relative_path": active_b.relative_to(vault_dir.parent).as_posix(),
                    "summary": "삼양식품 수출 성장",
                    "content_hash": "same-active",
                },
                {
                    "ticker": "003230",
                    "type": "research-capture",
                    "date": "2026-05-23",
                    "file_name": archived.name,
                    "relative_path": archived.relative_to(vault_dir.parent).as_posix(),
                    "summary": "삼양식품 수출 성장",
                    "content_hash": "same-active",
                    "status": "archived",
                    "is_deleted": True,
                },
            ]
            (vault_dir / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            result = main.build_storage_duplicate_review(
                Settings(research_vault_dir=str(vault_dir)),
                limit=10,
                save_result=False,
            )

        self.assertEqual(result["skipped_archived_count"], 1)
        self.assertEqual(result["duplicate_entry_count"], 1)
        self.assertEqual(result["representative_policy"]["dossier_usage"], "representative_only")
        self.assertEqual(result["representative_policy"]["duplicate_usage"], "excluded_from_dossier")
        self.assertFalse(result["representative_policy"]["hard_delete_allowed"])
        self.assertEqual(result["dossier_usage_summary"]["duplicate_excluded_count"], 1)
        self.assertEqual(result["dossier_usage_summary"]["archived_excluded_count"], 1)
        self.assertEqual(result["groups"][0]["excluded_duplicate_count"], 1)
        self.assertEqual(result["groups"][0]["dossier_usage"], "representative_only")
        self.assertEqual(result["groups"][0]["duplicate_usage"], "excluded_from_dossier")
        duplicate_names = [
            item["file_name"]
            for group in result["groups"]
            for item in group["duplicates"]
        ]
        self.assertIn(active_b.name, duplicate_names)
        self.assertNotIn(archived.name, duplicate_names)

    def test_storage_quality_counts_only_ocr_problem_not_ocr_success(self):
        import json
        import research_os_main as main
        from research_os.settings import Settings

        test_tmp_dir = PROJECT_ROOT / ".test-tmp"
        test_tmp_dir.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=test_tmp_dir, ignore_cleanup_errors=True) as temp_dir:
            vault_dir = Path(temp_dir) / "research_vault"
            vault_dir.mkdir(parents=True)
            (vault_dir / "manifest.json").write_text(
                json.dumps(
                    [
                        {
                            "ticker": "POLICY",
                            "type": "research-capture",
                            "date": "2026-05-24",
                            "file_name": "success.md",
                            "summary": "OCR/추출 완료 본문 29,150자",
                            "tags": ["ocr_completed"],
                            "attachment": {
                                "extraction_char_count": 29150,
                                "extraction_profile": {"ocr_status": "success"},
                            },
                        },
                        {
                            "ticker": "POLICY",
                            "type": "research-capture",
                            "date": "2026-05-24",
                            "file_name": "needs.md",
                            "summary": "스캔 PDF",
                            "tags": ["ocr_needed"],
                            "attachment": {
                                "ocr_required": True,
                                "extraction_profile": {"ocr_status": "unavailable"},
                            },
                        },
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            result = main.build_storage_quality_dashboard(Settings(research_vault_dir=str(vault_dir)))

        self.assertEqual(result["ocr_needed_count"], 1)
        self.assertEqual(result["ocr_needed_items"][0]["file_name"], "needs.md")

    def test_storage_quality_lists_body_missing_items(self):
        import json
        import research_os_main as main
        from research_os.settings import Settings

        test_tmp_dir = PROJECT_ROOT / ".test-tmp"
        test_tmp_dir.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=test_tmp_dir, ignore_cleanup_errors=True) as temp_dir:
            vault_dir = Path(temp_dir) / "research_vault"
            vault_dir.mkdir(parents=True)
            (vault_dir / "manifest.json").write_text(
                json.dumps(
                    [
                        {
                            "ticker": "POLICY",
                            "type": "research-capture",
                            "date": "2026-05-26",
                            "file_name": "url-only.md",
                            "summary": "제한된 URL-only 자료",
                            "tags": ["url_only"],
                            "capture_quality": {"status": "보강 필요"},
                        }
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            result = main.build_storage_quality_dashboard(Settings(research_vault_dir=str(vault_dir)))

        self.assertEqual(result["body_missing_count"], 1)
        self.assertEqual(result["body_missing_items"][0]["file_name"], "url-only.md")
        self.assertEqual(result["body_missing_items"][0]["quality_status"], "보강 필요")

    def test_storage_quality_tracks_public_ir_sec_body_copy_separately(self):
        import json
        import research_os_main as main
        from research_os.settings import Settings

        test_tmp_dir = PROJECT_ROOT / ".test-tmp"
        test_tmp_dir.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=test_tmp_dir, ignore_cleanup_errors=True) as temp_dir:
            vault_dir = Path(temp_dir) / "research_vault"
            vault_dir.mkdir(parents=True)
            (vault_dir / "manifest.json").write_text(
                json.dumps(
                    [
                        {
                            "ticker": "PUBLIC_IR_SEC",
                            "scope": "public_ir_sec",
                            "type": "public-ir-sec",
                            "date": "2026-06-04",
                            "file_name": "joby-url-only.md",
                            "summary": "Joby public IR URL-only",
                            "tags": ["public_ir_sec", "url_text_unavailable", "needs_body_copy"],
                            "capture_quality": {"status": "보강 필요", "needs_body_copy": True},
                        }
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            result = main.build_storage_quality_dashboard(Settings(research_vault_dir=str(vault_dir)))

        self.assertEqual(result["body_missing_count"], 0)
        self.assertEqual(result["public_ir_sec_count"], 1)
        self.assertEqual(result["public_ir_sec_needs_body_count"], 1)
        self.assertEqual(result["public_ir_sec_items"][0]["file_name"], "joby-url-only.md")

    def test_storage_quality_does_not_count_rag_synthesis_source_body_tags(self):
        import json
        import research_os_main as main
        from research_os.settings import Settings

        test_tmp_dir = PROJECT_ROOT / ".test-tmp"
        test_tmp_dir.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=test_tmp_dir, ignore_cleanup_errors=True) as temp_dir:
            vault_dir = Path(temp_dir) / "research_vault"
            vault_dir.mkdir(parents=True)
            (vault_dir / "manifest.json").write_text(
                json.dumps(
                    [
                        {
                            "ticker": "SEARCH",
                            "type": "rag-query-synthesis",
                            "date": "2026-06-14",
                            "file_name": "search-rag-query-synthesis.md",
                            "summary": "URL-only 원천을 포함한 합성 보고서",
                            "tags": ["rag_query_synthesis", "public_ir_sec", "url_text_unavailable", "needs_body_copy"],
                        }
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            result = main.build_storage_quality_dashboard(Settings(research_vault_dir=str(vault_dir)))

        self.assertEqual(result["body_missing_count"], 0)
        self.assertEqual(result["public_ir_sec_count"], 0)
        self.assertEqual(result["normal_count"], 1)

    def test_deduped_dossier_candidates_skip_system_keys(self):
        import json
        import research_os_main as main
        from research_os.settings import Settings

        test_tmp_dir = PROJECT_ROOT / ".test-tmp"
        test_tmp_dir.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=test_tmp_dir, ignore_cleanup_errors=True) as temp_dir:
            vault_dir = Path(temp_dir) / "research_vault"
            system_dir = vault_dir / "_system"
            system_dir.mkdir(parents=True)
            (system_dir / "storage_duplicate_review.json").write_text(
                json.dumps(
                    {
                        "ticker_breakdown": [
                            {"ticker": "SECTOR-KR-BALANCED", "duplicate_group_count": 5, "duplicate_entry_count": 20},
                            {"ticker": "MARKET-KR", "duplicate_group_count": 4, "duplicate_entry_count": 12},
                            {"ticker": "018260", "duplicate_group_count": 1, "duplicate_entry_count": 2},
                        ]
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (vault_dir / "manifest.json").write_text(
                json.dumps(
                    [
                        {
                            "ticker": "018260",
                            "type": "research-capture",
                            "date": "2026-06-16",
                            "file_name": "018260-research-capture.md",
                            "summary": "검증된 Dossier 입력 자료입니다. 클라우드 매출 성장과 마진 개선을 확인했습니다.",
                            "ticker_verification": {"verified": True, "official_symbol": "018260"},
                        }
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            candidates = main.dossier_refresh_candidates_from_duplicate_review(
                Settings(research_vault_dir=str(vault_dir)),
                limit=5,
            )

        self.assertEqual([item["ticker"] for item in candidates], ["018260"])

    def test_deduped_dossier_candidates_require_verified_sources(self):
        import json
        import research_os_main as main
        from research_os.settings import Settings

        test_tmp_dir = PROJECT_ROOT / ".test-tmp"
        test_tmp_dir.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=test_tmp_dir, ignore_cleanup_errors=True) as temp_dir:
            vault_dir = Path(temp_dir) / "research_vault"
            system_dir = vault_dir / "_system"
            system_dir.mkdir(parents=True)
            (system_dir / "storage_duplicate_review.json").write_text(
                json.dumps(
                    {
                        "ticker_breakdown": [
                            {"ticker": "035420", "company_name": "NAVER", "duplicate_group_count": 2, "duplicate_entry_count": 5},
                            {"ticker": "NBIS", "company_name": "Nebius", "duplicate_group_count": 1, "duplicate_entry_count": 1},
                        ]
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (vault_dir / "manifest.json").write_text(
                json.dumps(
                    [
                        {
                            "ticker": "NBIS",
                            "type": "research-capture",
                            "date": "2026-06-16",
                            "file_name": "NBIS-research-capture.md",
                            "summary": "검증된 Dossier 입력 자료입니다. AI 인프라 수요와 매출 성장 근거를 확인했습니다.",
                            "ticker_verification": {"verified": True, "official_symbol": "NBIS"},
                        }
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            candidates = main.dossier_refresh_candidates_from_duplicate_review(
                Settings(research_vault_dir=str(vault_dir)),
                limit=5,
            )

        self.assertEqual([item["ticker"] for item in candidates], ["NBIS"])

    def test_deduped_dossier_refresh_updates_parent_status_timestamp(self):
        import json
        import research_os_main as main
        from research_os.settings import Settings

        test_tmp_dir = PROJECT_ROOT / ".test-tmp"
        test_tmp_dir.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=test_tmp_dir, ignore_cleanup_errors=True) as temp_dir:
            vault_dir = Path(temp_dir) / "research_vault"
            system_dir = vault_dir / "_system"
            system_dir.mkdir(parents=True)
            (system_dir / "storage_duplicate_review.json").write_text(
                json.dumps(
                    {
                        "duplicate_group_count": 1,
                        "duplicate_entry_count": 2,
                        "ticker_breakdown": [
                            {"ticker": "018260", "company_name": "삼성에스디에스", "duplicate_group_count": 1, "duplicate_entry_count": 2}
                        ]
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (system_dir / "research_automation_status.json").write_text(
                json.dumps({"updated_at": "2026-05-17T22:54:52+09:00", "dossier_count": 30}, ensure_ascii=False),
                encoding="utf-8",
            )
            (vault_dir / "manifest.json").write_text(
                json.dumps(
                    [
                        {
                            "ticker": "018260",
                            "type": "research-capture",
                            "date": "2026-06-16",
                            "file_name": "018260-research-capture.md",
                            "summary": "검증된 Dossier 입력 자료입니다. 클라우드 매출 성장과 마진 개선을 확인했습니다.",
                            "ticker_verification": {"verified": True, "official_symbol": "018260"},
                        }
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            settings = Settings(research_vault_dir=str(vault_dir))
            dossier_payload = {
                "company_name": "삼성에스디에스",
                "source_count": 2,
                "duplicate_count": 1,
                "confidence": 0.9,
                "storage": {"relative_path": "research_vault/018260/dossier.md"},
            }

            with patch.object(main, "current_storage_timestamp", return_value="2026-05-30T18:00:00+09:00"), patch.object(
                main, "synthesize_and_save_dossier", return_value=dossier_payload
            ):
                result = main.run_deduped_dossier_refresh_queue(settings, limit=1, save_result=True)

            status = json.loads((system_dir / "research_automation_status.json").read_text(encoding="utf-8"))

        self.assertEqual(result["as_of"], "2026-05-30T18:00:00+09:00")
        self.assertEqual(status["updated_at"], result["as_of"])
        self.assertEqual(status["last_deduped_dossier_refresh"]["updated_at"], result["as_of"])
        self.assertEqual(status["last_deduped_dossier_refresh"]["refreshed_count"], 1)
        self.assertEqual(status["duplicate_suspected_count"], 2)
        self.assertEqual(status["duplicate_group_count"], 1)

    def test_legacy_policy_defaults_to_soft_archive(self):
        import research_os_main as main

        policy = main.research_memory_legacy_policy(
            ticker="003230",
            legacy_file_count=2,
            archived_file_count=1,
        )

        self.assertEqual(policy["policy"], "soft_archive")
        self.assertFalse(policy["hard_delete_allowed"])
        self.assertIn("status=archived", policy["archive_behavior"])
        self.assertIn("레거시 일괄 보관", policy["recommended_action"])

    def test_legacy_policy_handles_empty_legacy_set(self):
        import research_os_main as main

        policy = main.research_memory_legacy_policy(ticker="003230")

        self.assertEqual(policy["legacy_file_count"], 0)
        self.assertIn("보관할 레거시 파일이 없습니다", policy["recommended_action"])


class CredentialPolicyTests(unittest.TestCase):
    def test_safety_config_masks_secrets_and_reports_policy_only(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(
            brokerage_api_key="FAKEKEY123456789",
            brokerage_api_secret="FAKESECRET123456789",
            secret_salt="local-secret-salt",
            kis_app_key="FAKEKISKEY123456789",
            kis_app_secret="FAKEKISSECRET123456789",
            kis_access_token="Bearer fake-token-for-test",
            dart_api_key="FAKEDARTKEY123456789",
            research_vault_dir="../research_vault",
        )

        response = main.read_safety_config(settings)
        policy = response["credential_policy"]

        self.assertTrue(response["secrets_are_masked"])
        self.assertEqual(response["brokerage_api_key"], "FAKE****6789")
        self.assertEqual(response["kis_access_token"] if "kis_access_token" in response else "********", "********")
        self.assertTrue(policy["gitignore_required"])
        self.assertTrue(policy["configured_secrets"]["kis_access_token"])
        self.assertTrue(policy["configured_secrets"]["dart_api_key"])
        self.assertIn("EXPO_PUBLIC_*", policy["frontend_rule"])
        self.assertNotIn("fake-token-for-test", str(response))
        self.assertNotIn("FAKEKISSECRET123456789", str(response))

    def test_mask_secret_never_returns_short_secret_values(self):
        from research_os.settings import mask_secret

        self.assertEqual(mask_secret("short"), "********")
        self.assertEqual(mask_secret(""), "********")
        self.assertEqual(mask_secret("1234567890abcdef"), "1234****cdef")


class ConsoleAssetHashTests(unittest.TestCase):
    def test_html_and_js_refs_use_file_hash_versions(self):
        tool = load_console_hash_tool()
        versions = {
            "styles.css": "stylehash123",
            "console.js": "consolehash1",
            "api.js": "apihash12345",
        }

        html = (
            '<link rel="stylesheet" href="./styles.css" />\n'
            '<script type="module" src="./console.js?v=manual-version"></script>\n'
        )
        js = 'import { request } from "./api.js?v=manual-version";\n'

        updated_html = tool.update_html_content(html, versions)
        updated_js = tool.update_console_js_content(js, versions)

        self.assertIn('href="./styles.css?v=stylehash123"', updated_html)
        self.assertIn('src="./console.js?v=consolehash1"', updated_html)
        self.assertNotIn("manual-version", updated_html)
        self.assertEqual(
            updated_js,
            'import { request } from "./api.js?v=apihash12345";\n',
        )

    def test_console_result_templates_keep_company_name_first_display(self):
        console_js = (PROJECT_ROOT / "mobile_app" / "research_console" / "console.js").read_text(
            encoding="utf-8"
        )

        blocked_templates = [
            "${item.company_name || item.ticker} (${item.ticker})",
            "${item.company_name || item.ticker} · ${item.ticker}",
            "${item.ticker}: ${item.action}",
            "${value.company_name || value.ticker} (${value.ticker})",
            "`티커: ${value.ticker}`",
            "공식 코드 ${item.ticker",
            "종목코드 ${item.ticker",
        ]
        for template in blocked_templates:
            self.assertNotIn(template, console_js)

    def test_asset_hash_rewrite_reaches_fixed_point(self):
        tool = load_console_hash_tool()
        project_root = PROJECT_ROOT

        pending = tool.changed_update_paths(project_root)

        self.assertEqual(pending, [])


class RagQuerySynthesisStorageTests(unittest.TestCase):
    def test_rag_query_synthesis_query_file_suffix_is_filesystem_safe(self):
        from research_os import rag_query_synthesis_storage

        self.assertEqual(
            rag_query_synthesis_storage._query_file_suffix("  AI 메모리 / HBM?  "),
            "ai-hbm",
        )
        self.assertEqual(rag_query_synthesis_storage._query_file_suffix("   "), "search")
        self.assertEqual(rag_query_synthesis_storage._query_file_suffix("A" * 120), "a" * 96)

    def test_rag_query_synthesis_storage_persists_manifest_rag_and_thesis(self):
        from research_os import rag_query_synthesis_storage
        from research_os.research_memory import ResearchStorageInfo

        class DumpItem(SimpleNamespace):
            def model_dump(self, mode=None):
                return dict(self.__dict__)

        save_calls = []
        rag_calls = []
        thesis_calls = []

        def fake_save_research_markdown(**kwargs):
            save_calls.append(kwargs)
            return ResearchStorageInfo(
                file_name=f"{kwargs['ticker']}-{kwargs['report_type']}.md",
                relative_path=f"research_vault/{kwargs['ticker']}/{kwargs['ticker']}-{kwargs['report_type']}.md",
                absolute_path=str(kwargs['vault_dir'] / kwargs['ticker'] / f"{kwargs['ticker']}-{kwargs['report_type']}.md"),
            )

        thesis = DumpItem(title="AI 메모리 투자 논거", confidence=0.88)
        watch_item = DumpItem(metric="HBM 매출", direction="상승")
        runtime = SimpleNamespace(
            build_rag_query_synthesis_thesis=lambda storage_key, payload, watch_kpis: (thesis, [watch_item]),
            current_storage_date=lambda: date(2026, 6, 13),
            rag_synthesis_storage_key=lambda documents: "005930",
            read_manifest=lambda vault_dir: [
                {
                    "file_name": "005930-rag-query-synthesis.md",
                    "ticker": "005930",
                    "summary": "저장된 RAG 합성",
                }
            ],
            render_rag_query_synthesis_markdown=lambda payload: "# RAG 합성\n005930",
            save_research_markdown=fake_save_research_markdown,
            ticker_company_name=lambda ticker: "삼성전자",
            ticker_watch_kpis=lambda ticker: ["HBM 매출", "DRAM 가격"],
            upsert_research_memory_document=lambda **kwargs: rag_calls.append(kwargs) or {"status": "upserted"},
            upsert_ticker_thesis_snapshot=lambda **kwargs: thesis_calls.append(kwargs) or {"status": "snapshot_saved"},
        )
        payload = {
            "date": "2026-06-13",
            "summary": "AI 메모리 관련 근거 합성",
            "source_documents": [{"ticker": "005930"}],
            "source_count": 2,
            "candidate_count": 3,
            "grouped_count": 1,
            "confidence": 0.86,
            "tags": ["ai", "memory", "semiconductor"],
            "tickers": ["005930"],
            "consensus_facts": ["HBM 수요 증가"],
            "bull_thesis": ["메모리 업황 회복"],
            "bear_thesis": ["밸류에이션 부담"],
            "cruxes": ["AI 서버 수요 지속 여부"],
            "observables": ["HBM 계약 공시"],
        }
        vault_dir = PROJECT_ROOT / ".test-tmp" / "rag_query_synthesis_storage_vault"

        result = rag_query_synthesis_storage.save_rag_query_synthesis_result(
            runtime,
            vault_dir=vault_dir,
            query="AI 메모리",
            payload=payload,
        )

        self.assertEqual(result["storage_key"], "005930")
        self.assertEqual(result["rag_document"], {"status": "upserted"})
        self.assertEqual(result["thesis_snapshot"], {"status": "snapshot_saved"})
        self.assertEqual(len(save_calls), 1)
        saved = save_calls[0]
        self.assertEqual(saved["vault_dir"], vault_dir)
        self.assertEqual(saved["ticker"], "005930")
        self.assertEqual(saved["report_type"], "rag-query-synthesis")
        self.assertEqual(saved["report_date"], date(2026, 6, 13))
        self.assertEqual(saved["file_suffix"], "ai")
        self.assertEqual(saved["structured_payload"], payload)
        self.assertEqual(saved["manifest_entry"]["query"], "AI 메모리")
        self.assertEqual(saved["manifest_entry"]["source_confidence"], 0.86)
        self.assertEqual(saved["manifest_entry"]["investment_thesis"], {"title": "AI 메모리 투자 논거", "confidence": 0.88})
        self.assertEqual(saved["manifest_entry"]["watch_items"], [{"metric": "HBM 매출", "direction": "상승"}])
        self.assertEqual(rag_calls[0]["vault_dir"], vault_dir)
        self.assertEqual(rag_calls[0]["entry"]["file_name"], "005930-rag-query-synthesis.md")
        self.assertEqual(thesis_calls[0]["ticker"], "005930")
        self.assertEqual(thesis_calls[0]["company_name"], "삼성전자")
        self.assertEqual(thesis_calls[0]["investment_thesis"], thesis)
        self.assertEqual(thesis_calls[0]["watch_items"], [watch_item])
        self.assertEqual(thesis_calls[0]["source_entry"]["type"], "rag-query-synthesis")
        self.assertEqual(thesis_calls[0]["source_entry"]["date"], "2026-06-13")
        self.assertEqual(thesis_calls[0]["confidence"], 0.86)

    def test_rag_query_synthesis_storage_skips_noop_payload(self):
        from research_os import rag_query_synthesis_storage

        def fail_if_called(**kwargs):
            raise AssertionError(f"no-op RAG synthesis should not save: {kwargs}")

        runtime = SimpleNamespace(
            build_rag_query_synthesis_thesis=fail_if_called,
            current_storage_date=lambda: date(2026, 6, 13),
            rag_synthesis_storage_key=lambda documents: "SEARCH",
            read_manifest=fail_if_called,
            render_rag_query_synthesis_markdown=fail_if_called,
            save_research_markdown=fail_if_called,
            ticker_company_name=lambda ticker: "검색",
            ticker_watch_kpis=lambda ticker: [],
            upsert_research_memory_document=fail_if_called,
            upsert_ticker_thesis_snapshot=fail_if_called,
        )
        payload = {
            "date": "2026-06-13",
            "summary": "검색 후보가 없습니다.",
            "source_documents": [],
            "source_count": 0,
            "candidate_count": 0,
            "grouped_count": 0,
            "confidence": 0.0,
            "tags": [],
            "tickers": [],
            "consensus_facts": [],
            "bull_thesis": [],
            "bear_thesis": [],
            "cruxes": [],
            "observables": [],
        }

        result = rag_query_synthesis_storage.save_rag_query_synthesis_result(
            runtime,
            vault_dir=PROJECT_ROOT / ".test-tmp" / "rag_query_synthesis_storage_noop",
            query="없는 검색어",
            payload=payload,
        )

        self.assertEqual(result["storage_key"], "SEARCH")
        self.assertIsNone(result["storage"])
        self.assertIsNone(result["rag_document"])
        self.assertIsNone(result["thesis_snapshot"])
        self.assertTrue(result["skipped"])
        self.assertEqual(result["skip_reason"], "no_candidate_documents")


class DartFilingStorageTests(unittest.TestCase):
    def test_dart_filing_storage_persists_manifest_and_rag(self):
        from research_os import dart_filing_storage
        from research_os.research_memory import ResearchStorageInfo

        save_calls = []
        rag_calls = []

        def fake_save_research_markdown(**kwargs):
            save_calls.append(kwargs)
            return ResearchStorageInfo(
                file_name=f"{kwargs['ticker']}-{kwargs['report_type']}.md",
                relative_path=f"research_vault/{kwargs['ticker']}/{kwargs['ticker']}-{kwargs['report_type']}.md",
                absolute_path=str(kwargs['vault_dir'] / kwargs['ticker'] / f"{kwargs['ticker']}-{kwargs['report_type']}.md"),
            )

        runtime = SimpleNamespace(
            dart_filing_importance=lambda report_name: ("높음", "리스크 재점검", ["dart", "risk"]),
            manifest_with_ticker_verification=lambda ticker, entry: {**entry, "ticker": ticker, "verified": True},
            render_dart_filing_markdown=lambda ticker, filing, importance, action: f"{ticker} {importance} {action}",
            resolve_vault_dir=lambda value: Path(value),
            save_research_markdown=fake_save_research_markdown,
            upsert_research_memory_document=lambda **kwargs: rag_calls.append(kwargs) or {"status": "upserted"},
        )
        filing = {
            "corp_name": "삼성전자",
            "receipt_date": "20260613",
            "report_name": "주요사항보고서",
            "rcept_no": "202606130001",
            "source_url": "https://dart.example.test/filing",
        }
        vault_dir = PROJECT_ROOT / ".test-tmp" / "dart_filing_storage_vault"

        storage = dart_filing_storage.save_dart_filing_watch_item(
            runtime,
            ticker="005930",
            filing=filing,
            settings=SimpleNamespace(research_vault_dir=str(vault_dir)),
        )

        self.assertEqual(storage.file_name, "005930-dart-filing-watch.md")
        self.assertEqual(len(save_calls), 1)
        saved = save_calls[0]
        self.assertEqual(saved["vault_dir"], vault_dir)
        self.assertEqual(saved["ticker"], "005930")
        self.assertEqual(saved["report_type"], "dart-filing-watch")
        self.assertEqual(saved["report_date"], date(2026, 6, 13))
        self.assertEqual(saved["file_suffix"], "202606130001")
        self.assertEqual(saved["structured_payload"]["importance"], "높음")
        self.assertEqual(saved["structured_payload"]["filing"], filing)
        self.assertEqual(saved["manifest_entry"]["module"], "dart_filing_watch")
        self.assertEqual(saved["manifest_entry"]["ticker"], "005930")
        self.assertEqual(saved["manifest_entry"]["source_type"], "official_filing")
        self.assertEqual(saved["manifest_entry"]["source_url"], "https://dart.example.test/filing")
        self.assertEqual(saved["manifest_entry"]["rcept_no"], "202606130001")
        self.assertTrue(saved["manifest_entry"]["verified"])
        self.assertEqual(len(rag_calls), 1)
        self.assertEqual(rag_calls[0]["vault_dir"], vault_dir)
        self.assertEqual(rag_calls[0]["entry"]["type"], "dart-filing-watch")
        self.assertEqual(rag_calls[0]["entry"]["source_type"], "official_filing")
        self.assertEqual(rag_calls[0]["entry"]["date"], "2026-06-13")
        self.assertIn("005930", rag_calls[0]["full_text"])



class DartFilingMetadataModuleTests(unittest.TestCase):
    def test_dart_metadata_helpers_classify_render_and_cache_filing(self):
        from research_os import dart_filing_metadata

        filing = {
            "corp_name": "삼성전자",
            "report_name": "주요사항보고서",
            "receipt_date": "20260613",
            "rcept_no": "202606130001",
            "source_url": "https://dart.example.test/filing",
        }

        importance, action, tags = dart_filing_metadata.dart_filing_importance(filing["report_name"])
        markdown = dart_filing_metadata.render_dart_filing_markdown("005930", filing, importance, action)

        self.assertEqual(importance, "높음")
        self.assertIn("risk", tags)
        self.assertEqual(dart_filing_metadata.dart_filing_cache_key("005930", filing), "005930:202606130001")
        self.assertIn("삼성전자", markdown)
        self.assertIn("주요사항보고서", markdown)

    def test_dart_metadata_helpers_classify_retryable_and_mapping_errors(self):
        from research_os import dart_filing_metadata

        retryable = dart_filing_metadata.classify_dart_filing_refresh_error(TimeoutError("OpenDART timeout"))
        mapping = dart_filing_metadata.classify_dart_filing_refresh_error(Exception("corp_code를 찾지 못했습니다: 123456"))

        self.assertEqual(retryable["category"], "transient_provider_error")
        self.assertTrue(retryable["retryable"])
        self.assertEqual(mapping["category"], "needs_mapping_review")
        self.assertFalse(mapping["retryable"])

    def test_dart_metadata_helpers_derive_periodic_quarter_neighbors(self):
        from research_os import dart_filing_metadata

        self.assertEqual(
            dart_filing_metadata.dart_periodic_quarter_label("분기보고서 (2026.03)", "20260515"),
            "FY2026 Q1",
        )
        self.assertEqual(
            dart_filing_metadata.dart_periodic_quarter_label("사업보고서", "20260331"),
            "FY2025 Annual",
        )
        self.assertEqual(
            dart_filing_metadata.korean_earnings_neighbor_dates("FY2026 Q2"),
            ("2026-05-15", "2026-11-14"),
        )

class RecentActivityPublicIrModuleTests(unittest.TestCase):
    def test_recent_activity_public_ir_compacts_sec_entry_with_quality_guard(self):
        from research_os import recent_activity_public_ir

        item = recent_activity_public_ir.compact_recent_public_ir_sec_entry(
            {
                "date": "2026-06-17",
                "ticker": "PL",
                "title": "Planet Labs 8-K",
                "summary": "Planet Labs filed a contract update",
                "source_url": "https://www.sec.gov/Archives/edgar/data/pl/8-k.htm",
                "filing_form": "8-K",
                "capture_quality": {"status": "정상", "needs_body_copy": False},
                "tags": ["SEC", "contract"],
            },
            {
                "tickers": ["PL"],
                "ticker_set": {"PL"},
                "ticker_names": {"PL": "Planet Labs PBC"},
                "names": ["Planet Labs"],
                "sectors": [],
            },
        )

        self.assertEqual(item["ticker"], "PL")
        self.assertEqual(item["source_provider"], "SEC EDGAR")
        self.assertEqual(item["source_reliability"], "공식 SEC 8-K")
        self.assertTrue(item["usable_for_recommendation"])
        self.assertFalse(item["needs_body_copy"])
class DartFilingWatchTests(unittest.TestCase):
    def test_dart_watch_exclusion_helpers_keep_reason_and_dedupe(self):
        from research_os import dart_watch_exclusions

        runtime = SimpleNamespace(normalize_ticker=lambda value: str(value).strip().upper())
        excluded = [{"ticker": "360750", "source": "portfolio", "reason": "etf_not_dart_corp"}]
        reason = dart_watch_exclusions.dart_watch_exclusion_reason(
            {"ticker": "360750", "name": "TIGER 미국S&P500 ETF"}
        )
        entry = dart_watch_exclusions.dart_excluded_ticker_entry(
            "360750",
            "portfolio",
            reason,
            {"name": "TIGER 미국S&P500 ETF"},
        )

        dart_watch_exclusions.append_unique_dart_exclusion(runtime, excluded, entry)

        self.assertEqual(reason, "etf_not_dart_corp")
        self.assertEqual(len(excluded), 1)
        self.assertEqual(excluded[0]["name"], "TIGER 미국S&P500 ETF")
        self.assertIn("OpenDART", entry["message"])

    def test_dart_watch_universe_helpers_filter_active_failures(self):
        from research_os import dart_watch_universe

        runtime = SimpleNamespace(normalize_ticker=lambda value: str(value or "").strip().upper())
        cache = {
            "last_failures": [
                {"ticker": "003230", "error": "rate limit"},
                {"ticker": "360750", "error": "ETF"},
                {"ticker": "999999", "error": "stale"},
            ]
        }
        target_universe = {
            "target_tickers": ["003230"],
            "excluded_tickers": [{"ticker": "360750", "reason": "etf_not_dart_corp"}],
        }

        failures = dart_watch_universe.active_dart_last_failures(
            runtime,
            cache,
            target_universe,
        )

        self.assertEqual(failures, [{"ticker": "003230", "error": "rate limit"}])

    def test_recent_dart_entries_sort_by_receipt_date_before_detection_time(self):
        import research_os_main as main

        cache = {
            "entries": {
                "old-discovered-today": {
                    "ticker": "361610",
                    "detected_at": "2026-05-18T15:38:43+09:00",
                    "filing": {
                        "report_name": "유상증자결정",
                        "receipt_date": "20260429",
                        "rcept_no": "20260429800839",
                    },
                },
                "latest-discovered-earlier": {
                    "ticker": "361610",
                    "detected_at": "2026-05-17T10:00:00+09:00",
                    "filing": {
                        "report_name": "분기보고서 (2026.03)",
                        "receipt_date": "20260515",
                        "rcept_no": "20260515002149",
                    },
                },
            }
        }

        recent = main.recent_dart_cache_entries(cache, "361610", limit=2)

        self.assertEqual(recent[0]["filing"]["rcept_no"], "20260515002149")

    def test_recent_dart_entries_without_ticker_returns_all_recent_entries(self):
        import research_os_main as main

        cache = {
            "entries": {
                "a": {
                    "ticker": "003230",
                    "detected_at": "2026-05-18T09:00:00+09:00",
                    "filing": {"receipt_date": "20260514", "rcept_no": "A"},
                },
                "b": {
                    "ticker": "361610",
                    "detected_at": "2026-05-18T09:00:00+09:00",
                    "filing": {"receipt_date": "20260515", "rcept_no": "B"},
                },
            }
        }

        recent = main.recent_dart_cache_entries(cache, limit=5)

        self.assertEqual([item["filing"]["rcept_no"] for item in recent], ["B", "A"])

    def test_dart_periodic_filing_overrides_schedule_fallback_for_same_quarter(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        profile = {
            "ticker": "033500",
            "company_name": "동성화인텍",
            "country": "KR",
            "latest_reported_quarter": "FY2026 Q1",
            "latest_reported_earnings_date": "2026-05-15",
            "earnings_calendar_source": "DART 정기보고서 제출 기한 기준 자동 산출",
            "latest_earnings_profile": {
                "quarter": "FY2026 Q1",
                "earnings_report_date": "2026-05-15",
            },
        }
        signal = {
            "recent_entries": [
                {
                    "filing": {
                        "corp_name": "동성화인텍",
                        "stock_code": "033500",
                        "rcept_no": "20260514001136",
                        "report_name": "분기보고서 (2026.03)",
                        "receipt_date": "20260514",
                        "source_url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260514001136",
                    }
                }
            ]
        }

        with (
            patch.object(main, "refresh_dart_filing_for_ticker_if_stale") as refresh_mock,
            patch.object(main, "build_dart_filing_signal", return_value=signal),
        ):
            enriched = main.merge_dart_latest_earnings_calendar("033500", profile, settings)

        refresh_mock.assert_called_once()
        self.assertEqual(enriched["latest_reported_quarter"], "FY2026 Q1")
        self.assertEqual(enriched["latest_reported_earnings_date"], "2026-05-14")
        self.assertIn("OpenDART 신규 공시 목록", enriched["earnings_calendar_source"])
        self.assertEqual(enriched["latest_earnings_profile"]["earnings_report_date"], "2026-05-14")


    def test_cached_dart_periodic_filing_is_used_without_external_refresh(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")

        def fake_profile(_ticker, _settings):
            return {
                "ticker": "361610",
                "company_name": "SK아이이테크놀로지",
                "country": "KR",
            }

        signal = {
            "recent_entries": [
                {
                    "filing": {
                        "corp_name": "SK아이이테크놀로지",
                        "stock_code": "361610",
                        "rcept_no": "20260515002149",
                        "report_name": "분기보고서 (2026.03)",
                        "receipt_date": "20260515",
                        "source_url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260515002149",
                    }
                }
            ]
        }

        with (
            patch.object(main, "current_storage_date", return_value=date(2026, 5, 18)),
            patch.object(main, "verified_profile_for_ticker", side_effect=fake_profile),
            patch.object(main, "refresh_dart_filing_for_ticker_if_stale") as refresh_mock,
            patch.object(main, "build_dart_filing_signal", return_value=signal),
            patch.object(main, "merge_cached_earnings_calendar", side_effect=lambda _ticker, profile, *_args, **_kwargs: profile),
        ):
            profile = main.official_ticker_profile("361610", settings, refresh_external=False)

        refresh_mock.assert_not_called()
        self.assertEqual(profile["latest_reported_quarter"], "FY2026 Q1")
        self.assertEqual(profile["latest_reported_earnings_date"], "2026-05-15")
        self.assertIn("OpenDART 신규 공시 목록", profile["earnings_calendar_source"])

    def test_dart_watch_universe_includes_portfolio_and_interest_korean_tickers(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        portfolio_store = {
            "portfolios": {
                "DEFAULT": {
                    "holdings": [
                        {"ticker": "003230", "name": "삼양식품"},
                        {"ticker": "PL", "name": "Planet Labs"},
                        {"ticker": "CASH", "name": "현금"},
                    ]
                }
            }
        }
        interest_store = {
            "tickers": [
                {"ticker": "071050", "name": "한국금융지주"},
                {"ticker": "AAPL", "name": "Apple"},
            ],
            "sectors": [],
        }

        with (
            patch.object(main, "read_portfolio_store", return_value=portfolio_store),
            patch.object(main, "read_interest_list", return_value=interest_store),
        ):
            universe = main.dart_watch_universe(settings)

        self.assertEqual(universe["target_tickers"], ["003230", "071050"])
        self.assertEqual(universe["portfolio_tickers"], ["003230"])
        self.assertEqual(universe["interest_tickers"], ["071050"])
        self.assertEqual(universe["target_count"], 2)
        excluded_pairs = {
            (item["ticker"], item["source"], item["reason"])
            for item in universe["excluded_tickers"]
        }
        self.assertIn(("PL", "portfolio", "non_kr_ticker"), excluded_pairs)
        self.assertIn(("AAPL", "interest", "non_kr_ticker"), excluded_pairs)

    def test_dart_watch_universe_excludes_etfs_before_opendart_lookup(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        portfolio_store = {
            "portfolios": {
                "DEFAULT": {
                    "holdings": [
                        {"ticker": "360750", "name": "TIGER 미국S&P500 ETF", "sector": "ETF / US Equity"},
                        {"ticker": "395160", "name": "KODEX AI반도체 ETF", "theme_tags": ["ETF", "AI"]},
                        {"ticker": "033500", "name": "동성화인텍"},
                    ]
                }
            }
        }

        with (
            patch.object(main, "read_portfolio_store", return_value=portfolio_store),
            patch.object(main, "read_interest_list", return_value={"tickers": [], "sectors": []}),
        ):
            universe = main.dart_watch_universe(settings)

        self.assertEqual(universe["target_tickers"], ["033500"])
        excluded_pairs = {
            (item["ticker"], item["reason"])
            for item in universe["excluded_tickers"]
        }
        self.assertIn(("360750", "etf_not_dart_corp"), excluded_pairs)
        self.assertIn(("395160", "etf_not_dart_corp"), excluded_pairs)

    def test_dart_watch_universe_marks_pending_interest_verification(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        interest_store = {
            "tickers": [
                {
                    "ticker": "10",
                    "tags": ["verification_pending"],
                    "verification": {
                        "verified": False,
                        "company_name": "10",
                        "verification_source": "save_first_pending_verification",
                    },
                },
                {
                    "ticker": "071050",
                    "verification": {"verified": True, "company_name": "한국금융지주"},
                },
            ],
            "sectors": [],
        }

        with (
            patch.object(main, "read_portfolio_store", return_value={"portfolios": {}}),
            patch.object(main, "read_interest_list", return_value=interest_store),
        ):
            universe = main.dart_watch_universe(settings)

        self.assertEqual(universe["target_tickers"], ["071050"])
        excluded_pairs = {
            (item["ticker"], item["source"], item["reason"])
            for item in universe["excluded_tickers"]
        }
        self.assertIn(("10", "interest", "verification_pending"), excluded_pairs)

    def test_daily_dart_refresh_records_full_portfolio_interest_coverage(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(
            research_vault_dir="../research_vault",
            dart_api_key="FAKE_DART_KEY",
            dart_filing_lookback_days=45,
        )
        portfolio_store = {
            "portfolios": {
                "DEFAULT": {
                    "holdings": [
                        {"ticker": "003230", "name": "삼양식품"},
                    ]
                }
            }
        }
        interest_store = {
            "tickers": [
                {"ticker": "071050", "name": "한국금융지주"},
            ],
            "sectors": [],
        }
        cache_store = {"updated_at": None, "entries": {}, "last_run": None}
        requested_tickers = []

        class FakeOpenDartClient:
            is_configured = True

            def __init__(self, _settings):
                pass

            def fetch_recent_filings(self, ticker, *, lookback_days, page_count):
                requested_tickers.append((ticker, lookback_days, page_count))
                return (
                    {"corp_name": f"{ticker} 회사"},
                    [
                        {
                            "corp_name": f"{ticker} 회사",
                            "stock_code": ticker,
                            "rcept_no": f"{ticker}202605150001",
                            "report_name": "분기보고서 (2026.03)",
                            "receipt_date": "20260515",
                            "source_url": f"https://dart.fss.or.kr/{ticker}",
                        }
                    ],
                )

        def fake_read_cache(_settings):
            return copy.deepcopy(cache_store)

        def fake_write_cache(_settings, payload):
            cache_store.clear()
            cache_store.update(copy.deepcopy(payload))

        with (
            patch.object(main, "read_portfolio_store", return_value=portfolio_store),
            patch.object(main, "read_interest_list", return_value=interest_store),
            patch.object(main, "OpenDartClient", FakeOpenDartClient),
            patch.object(main, "read_dart_filing_cache", side_effect=fake_read_cache),
            patch.object(main, "write_dart_filing_cache", side_effect=fake_write_cache),
            patch.object(main, "current_storage_date", return_value=date(2026, 5, 18)),
            patch.object(main, "current_storage_timestamp", return_value="2026-05-18T09:00:00+09:00"),
        ):
            result = main.refresh_dart_filing_watch(settings, save_result=False)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["target_count"], 2)
        self.assertEqual(result["target_universe"]["portfolio_tickers"], ["003230"])
        self.assertEqual(result["target_universe"]["interest_tickers"], ["071050"])
        self.assertEqual(sorted(ticker for ticker, _lookback, _page_count in requested_tickers), ["003230", "071050"])
        self.assertTrue(all(lookback == 45 for _ticker, lookback, _page_count in requested_tickers))
        self.assertEqual(cache_store["daily_check"]["date"], "2026-05-18")
        self.assertEqual(cache_store["daily_check"]["checked_tickers"], ["003230", "071050"])
        self.assertEqual(result["daily_check"]["status"], "complete")
        self.assertEqual(result["daily_check"]["failure_count"], 0)
        self.assertFalse(result["daily_check"]["due"])
        self.assertEqual(result["daily_check"]["reliability_status"], "신뢰 가능")
        self.assertEqual(result["daily_check"]["checked_count"], 2)
        self.assertEqual(result["daily_check"]["coverage_rate"], 1.0)
        self.assertEqual(result["daily_check"]["next_check_after"], "2026-05-18T15:00:00+09:00")
        self.assertEqual(result["saved_count"], 2)

    def test_daily_dart_refresh_retries_transient_provider_errors(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(
            research_vault_dir="../research_vault",
            dart_api_key="FAKE_DART_KEY",
            dart_filing_lookback_days=45,
        )
        cache_store = {"updated_at": None, "entries": {}, "last_run": None}
        attempts = {"003230": 0}

        class FakeOpenDartClient:
            is_configured = True

            def __init__(self, _settings):
                pass

            def fetch_recent_filings(self, ticker, *, lookback_days, page_count):
                attempts[ticker] += 1
                if attempts[ticker] == 1:
                    raise TimeoutError("OpenDART timeout")
                return (
                    {"corp_name": "삼양식품"},
                    [
                        {
                            "corp_name": "삼양식품",
                            "stock_code": ticker,
                            "rcept_no": "202605150001",
                            "report_name": "분기보고서 (2026.03)",
                            "receipt_date": "20260515",
                            "source_url": "https://dart.fss.or.kr/003230",
                        }
                    ],
                )

        def fake_read_cache(_settings):
            return copy.deepcopy(cache_store)

        def fake_write_cache(_settings, payload):
            cache_store.clear()
            cache_store.update(copy.deepcopy(payload))

        with (
            patch.object(main, "dart_watch_universe", return_value={
                "target_tickers": ["003230"],
                "portfolio_tickers": ["003230"],
                "interest_tickers": [],
                "excluded_tickers": [],
                "target_count": 1,
            }),
            patch.object(main, "OpenDartClient", FakeOpenDartClient),
            patch.object(main, "read_dart_filing_cache", side_effect=fake_read_cache),
            patch.object(main, "write_dart_filing_cache", side_effect=fake_write_cache),
            patch.object(main, "current_storage_date", return_value=date(2026, 5, 18)),
            patch.object(main, "current_storage_timestamp", return_value="2026-05-18T09:00:00+09:00"),
        ):
            result = main.refresh_dart_filing_watch(settings, save_result=False)

        self.assertEqual(result["status"], "success")
        self.assertEqual(attempts["003230"], 2)
        self.assertEqual(result["failed_count"], 0)

    def test_daily_dart_status_surfaces_partial_success_failures(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        cache = {
            "daily_check": {
                "date": "2026-05-18",
                "checked_at": "2026-05-18T09:00:00+09:00",
                "target_count": 2,
                "checked_tickers": ["003230", "071050"],
                "failed_tickers": ["071050"],
            }
        }
        target_universe = {
            "target_tickers": ["003230", "071050"],
            "portfolio_tickers": ["003230"],
            "interest_tickers": ["071050"],
            "excluded_tickers": [],
            "target_count": 2,
        }

        with (
            patch.object(main, "current_storage_date", return_value=date(2026, 5, 18)),
            patch.object(main, "dart_watch_universe", return_value=target_universe),
        ):
            status = main.dart_daily_check_status(cache, settings)

        self.assertFalse(status["due"])
        self.assertEqual(status["status"], "partial_success")
        self.assertEqual(status["reliability_status"], "부분 신뢰")
        self.assertEqual(status["checked_count"], 1)
        self.assertEqual(status["coverage_rate"], 0.5)
        self.assertEqual(status["failed_tickers"], ["071050"])
        self.assertEqual(status["failure_count"], 1)

    def test_daily_dart_status_ignores_failures_removed_from_current_targets(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        cache = {
            "daily_check": {
                "date": "2026-05-18",
                "checked_at": "2026-05-18T09:00:00+09:00",
                "target_count": 2,
                "checked_tickers": ["003230", "117700"],
                "failed_tickers": ["117700"],
            }
        }
        target_universe = {
            "target_tickers": ["003230"],
            "portfolio_tickers": ["003230"],
            "interest_tickers": [],
            "excluded_tickers": [
                {"ticker": "117700", "reason": "etf_not_dart_corp"},
            ],
            "target_count": 1,
        }

        with (
            patch.object(main, "current_storage_date", return_value=date(2026, 5, 18)),
            patch.object(main, "dart_watch_universe", return_value=target_universe),
        ):
            status = main.dart_daily_check_status(cache, settings)

        self.assertEqual(status["status"], "complete")
        self.assertEqual(status["failed_tickers"], [])
        self.assertEqual(status["failure_count"], 0)
        self.assertEqual(status["checked_count"], 1)

    def test_active_dart_last_failures_ignores_excluded_etfs(self):
        import research_os_main as main

        cache = {
            "last_failures": [
                {"ticker": "117700", "category": "needs_mapping_review"},
                {"ticker": "071050", "category": "provider_error"},
            ]
        }
        target_universe = {
            "target_tickers": ["003230", "071050"],
            "excluded_tickers": [
                {"ticker": "117700", "reason": "etf_not_dart_corp"},
            ],
        }

        failures = main.active_dart_last_failures(cache, target_universe)

        self.assertEqual(failures, [{"ticker": "071050", "category": "provider_error"}])
    def test_daily_dart_status_marks_missing_daily_run_as_due(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        cache = {
            "daily_check": {
                "date": "2026-05-17",
                "checked_at": "2026-05-17T09:00:00+09:00",
                "target_count": 1,
                "checked_tickers": ["003230"],
            }
        }
        target_universe = {
            "target_tickers": ["003230", "071050"],
            "portfolio_tickers": ["003230"],
            "interest_tickers": ["071050"],
            "excluded_tickers": [],
            "target_count": 2,
        }

        with (
            patch.object(main, "current_storage_date", return_value=date(2026, 5, 18)),
            patch.object(main, "dart_watch_universe", return_value=target_universe),
        ):
            status = main.dart_daily_check_status(cache, settings)

        self.assertTrue(status["due"])
        self.assertEqual(status["status"], "due")
        self.assertEqual(status["reliability_status"], "점검 필요")
        self.assertEqual(status["checked_count"], 0)
        self.assertEqual(status["coverage_rate"], 0)
        self.assertEqual(status["missing_tickers"], ["003230", "071050"])

    def test_recent_weekly_source_family_collapses_subdomains(self):
        import research_os_main as main

        self.assertEqual(main.recent_weekly_source_family("ir.jobyaviation.com"), "jobyaviation.com")
        self.assertEqual(main.recent_weekly_source_family("https://www.example.co.kr/path"), "example.co.kr")
        self.assertEqual(main.recent_weekly_source_family("SEC EDGAR"), "SEC EDGAR")

    def test_public_ir_sec_body_supplemented_url_only_is_usable(self):
        from research_os.recent_activity import compact_recent_public_ir_sec_entry

        item = compact_recent_public_ir_sec_entry(
            {
                "date": "2026-06-05",
                "ticker": "PL",
                "scope": "public_ir_sec",
                "type": "public-ir-sec",
                "title": "Planet Labs SEC Exhibit 99.1",
                "summary": "보강된 SEC 실적 발표",
                "source_url": "https://www.sec.gov/Archives/planet.htm",
                "source_provider": "SEC EDGAR",
                "source_category": "실적 발표",
                "filing_form": "8-K EX-99.1",
                "capture_quality": {
                    "status": "정상",
                    "source_status": "fetch_failed",
                    "needs_body_copy": True,
                    "body_supplemented": True,
                },
            },
            {"tickers": ["PL"], "ticker_set": {"PL"}, "ticker_names": {"PL": "Planet Labs PBC"}},
        )

        self.assertIsNotNone(item)
        assert item is not None
        self.assertTrue(item["usable_for_recommendation"])
        self.assertFalse(item["needs_body_copy"])
        self.assertEqual(item["recommendation_guard"], "추천 가산 가능")
        self.assertEqual(item["source_reliability"], "공식 SEC 8-K EX-99.1")

    def test_recent_weekly_group_quality_summary_uses_all_items_not_visible_sample(self):
        import research_os_main as main

        items = [
            {
                "ticker": f"{i:06d}",
                "company_name": f"테스트{i:02d}",
                "usable_for_recommendation": i < 4,
                "needs_body_copy": i >= 4,
                "quality_status": "정상" if i < 4 else "보강 필요",
            }
            for i in range(10)
        ]

        group = main.recent_weekly_category_group("공개 IR/SEC", "public_ir_sec", items, limit=2)

        self.assertEqual(group["count"], 10)
        self.assertEqual(group["visible_count"], 2)
        self.assertEqual(group["target_count"], 10)
        self.assertIn("테스트07", group["target_names"])
        self.assertEqual(group["ticker_count"], 10)
        self.assertIn("000009", group["tickers"])
        self.assertEqual(group["quality_summary"]["total_count"], 10)
        self.assertEqual(group["quality_summary"]["usable_for_recommendation"], 4)
        self.assertEqual(group["quality_summary"]["needs_body_copy"], 6)
        self.assertEqual(group["quality_summary"]["blocked_or_needs_review"], 6)
        self.assertEqual(group["quality_summary"]["statuses"]["보강 필요"], 6)
        self.assertEqual(group["quality_summary"]["providers"], {"출처 미확인": 10})
        self.assertEqual(group["quality_summary"]["source_families"], {"출처 미확인": 10})

    def test_recent_weekly_brief_filters_targets_and_dedupes_reports(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        portfolio_store = {
            "portfolios": {
                "DEFAULT": {
                    "holdings": [
                        {"ticker": "003230", "name": "삼양식품"},
                    ]
                }
            }
        }
        interest_store = {
            "tickers": [{"ticker": "327260", "name": "RF머트리얼즈"}],
            "sectors": [{"name": "반도체"}],
        }
        manifest_entries = [
            {
                "date": "2026-05-31",
                "ticker": "003230",
                "type": "broker-report",
                "summary": "삼양식품 실적 발표 리포트",
                "relative_path": "REPORT/003230-a.md",
            },
            {
                "date": "2026-05-31",
                "ticker": "003230",
                "type": "broker-report",
                "summary": "삼양식품 실적 발표 리포트",
                "relative_path": "REPORT/003230-b.md",
            },
            {
                "date": "2026-05-30",
                "type": "sector-note",
                "summary": "반도체 수출 장비 사이클 점검",
                "relative_path": "SECTOR/semiconductor.md",
            },
            {
                "date": "2026-05-30",
                "type": "market-note",
                "summary": "유럽 금리와 환율 점검",
                "tags": ["macro"],
                "relative_path": "MARKET/europe-rate.md",
            },
            {
                "date": "2026-05-30",
                "ticker": "003230",
                "type": "research-capture",
                "summary": "삼양식품 자동 운영 메모",
                "tags": ["auto_operational_note", "coverage_backfill_note"],
                "relative_path": "REPORT/003230-auto.md",
            },
            {
                "date": "2026-05-29",
                "type": "customs-trade-brief",
                "summary": "5월 수출입 실적 업데이트",
                "tags": ["customs", "export"],
                "relative_path": "CUSTOMS/export.md",
            },
            {
                "date": "2026-05-31",
                "ticker": "PUBLIC_IR_SEC",
                "scope": "public_ir_sec",
                "type": "public-ir-sec",
                "source_type": "public_ir_sec",
                "summary": "삼양식품 공개 IR 본문 추출 완료",
                "source_url": "https://www.sec.gov/Archives/samyang-8k.htm",
                "source_provider": "SEC EDGAR",
                "source_category": "SEC 실적 공시",
                "filing_form": "8-K",
                "filing_group": "financial_release",
                "capture_quality": {"status": "정상", "needs_body_copy": False},
                "relative_path": "PUBLIC_IR_SEC/samyang.md",
            },
            {
                "date": "2026-05-31",
                "ticker": "PUBLIC_IR_SEC",
                "scope": "public_ir_sec",
                "type": "public-ir-sec",
                "source_type": "public_ir_sec",
                "summary": "RF머트리얼즈 공개 IR URL-only 보관",
                "source_url": "https://example.com/rf-ir",
                "capture_quality": {"status": "보강 필요", "needs_body_copy": True},
                "relative_path": "PUBLIC_IR_SEC/rf.md",
            },
        ]
        dart_cache = {
            "entries": {
                "003230-20260531": {
                    "ticker": "003230",
                    "filing": {
                        "corp_name": "삼양식품",
                        "stock_code": "003230",
                        "report_name": "주식등의대량보유상황보고서",
                        "receipt_date": "20260531",
                        "rcept_no": "20260531000123",
                    },
                }
            }
        }

        with (
            patch.object(main, "current_storage_date", return_value=date(2026, 6, 1)),
            patch.object(main, "current_storage_timestamp", return_value="2026-06-01T09:00:00+09:00"),
            patch.object(main, "read_portfolio_store", return_value=portfolio_store),
            patch.object(main, "read_interest_list", return_value=interest_store),
            patch.object(main, "read_manifest", return_value=manifest_entries),
            patch.object(main, "read_dart_filing_cache", return_value=dart_cache),
            patch.object(main, "resolve_vault_dir", return_value=PROJECT_ROOT / "research_vault"),
            patch.object(main, "dart_daily_check_status", return_value={"status": "complete", "due": False}),
            patch.object(main, "build_external_source_schedule_status", return_value=[]),
        ):
            brief = main.build_recent_weekly_research_brief(settings, days=7, refresh_if_due=False)

        self.assertEqual(brief["counts"]["filings"], 1)
        self.assertEqual(brief["counts"]["important_filings"], 1)
        self.assertEqual(brief["counts"]["ownership_filings"], 1)
        self.assertEqual(brief["counts"]["reports"], 3)
        self.assertEqual(brief["counts"]["display_reports"], 2)
        self.assertEqual(brief["counts"]["hidden_low_signal_reports"], 1)
        self.assertEqual(brief["counts"]["customs_exports"], 1)
        self.assertEqual(brief["counts"]["public_ir_sec"], 2)
        self.assertEqual(brief["counts"]["public_ir_sec_usable"], 1)
        self.assertEqual(brief["counts"]["public_ir_sec_blocked"], 1)
        self.assertEqual(brief["counts"]["public_ir_sec_needs_body"], 1)
        groups = {group["key"]: group for group in brief["category_groups"]}
        self.assertEqual(groups["ownership_filings"]["count"], 1)
        self.assertEqual(groups["display_reports"]["count"], 2)
        self.assertEqual(groups["public_ir_sec"]["count"], 2)
        self.assertEqual(groups["public_ir_sec"]["quality_summary"]["usable_for_recommendation"], 1)
        self.assertEqual(groups["public_ir_sec"]["quality_summary"]["needs_body_copy"], 1)
        self.assertEqual(groups["public_ir_sec"]["quality_summary"]["blocked_or_needs_review"], 1)
        self.assertEqual(groups["public_ir_sec"]["quality_summary"]["providers"]["SEC EDGAR"], 1)
        self.assertEqual(groups["public_ir_sec"]["quality_summary"]["source_families"]["SEC EDGAR"], 1)
        self.assertEqual(groups["public_ir_sec"]["quality_summary"]["filing_forms"]["8-K"], 1)
        self.assertEqual(groups["public_ir_sec"]["quality_summary"]["reliability_labels"]["공식 SEC 8-K"], 1)
        self.assertEqual(groups["customs_exports"]["count"], 1)
        self.assertIn("삼양식품", groups["ownership_filings"]["target_names"])
        self.assertEqual(brief["watch_summary"]["status"], "점검 완료")
        self.assertEqual(brief["important_filings"][0]["summary"], "주식등의대량보유상황보고서")
        self.assertEqual(brief["ownership_filings"][0]["company_name"], "삼양식품")
        summaries = [item["summary"] for item in brief["items"]]
        self.assertEqual(summaries.count("삼양식품 실적 발표 리포트"), 1)
        self.assertIn("반도체 수출 장비 사이클 점검", summaries)
        self.assertIn("5월 수출입 실적 업데이트", summaries)
        self.assertNotIn("유럽 금리와 환율 점검", summaries)
        display_summaries = [item["summary"] for item in brief["display_reports"]]
        self.assertNotIn("삼양식품 자동 운영 메모", display_summaries)
        public_items = {item["summary"]: item for item in brief["public_ir_sec_items"]}
        public_guards = {summary: item["recommendation_guard"] for summary, item in public_items.items()}
        self.assertEqual(public_guards["삼양식품 공개 IR 본문 추출 완료"], "추천 가산 가능")
        self.assertEqual(public_guards["RF머트리얼즈 공개 IR URL-only 보관"], "본문 보강 전 추천 점수 가산 제외")
        samyang_public = public_items["삼양식품 공개 IR 본문 추출 완료"]
        self.assertEqual(samyang_public["source_provider"], "SEC EDGAR")
        self.assertEqual(samyang_public["filing_form"], "8-K")
        self.assertEqual(samyang_public["source_reliability"], "공식 SEC 8-K")
        rf_public = public_items["RF머트리얼즈 공개 IR URL-only 보관"]
        self.assertEqual(rf_public["source_provider"], "example.com")
        self.assertEqual(groups["public_ir_sec"]["quality_summary"]["providers"]["example.com"], 1)
        self.assertEqual(groups["public_ir_sec"]["quality_summary"]["source_families"]["example.com"], 1)
        target_digest = {item["target"]: item for item in brief["target_digest"]}
        self.assertEqual(target_digest["삼양식품"]["filing"], 1)
        self.assertEqual(target_digest["삼양식품"]["report"], 1)
        self.assertEqual(target_digest["삼양식품"]["public_ir_sec"], 1)
        self.assertEqual(target_digest["RF머트리얼즈"]["public_ir_sec"], 1)


class CustomsTradeDataQualityTests(unittest.TestCase):
    def test_service_status_only_customs_rows_are_not_counted_as_trade_data(self):
        from research_os.customs_data_provider import fetch_customs_trade_rows
        from research_os.settings import Settings

        settings = Settings(
            customs_trade_enabled=True,
            customs_trade_api_key="test-key",
            customs_trade_api_url="https://example.test/customs",
            customs_trade_max_rows=20,
        )

        with patch("research_os.customs_data_provider.KoreaCustomsTradeClient.fetch_item_trade_rows") as fetch_mock:
            fetch_mock.return_value = ([{"resultCode": "00", "resultMsg": "정상서비스."}], [], "https://example.test/customs")
            result = fetch_customs_trade_rows(
                settings,
                start_yymm="202605",
                end_yymm="202605",
                item_code="190230",
                country_code="US",
            )

        self.assertEqual(result["row_count"], 0)
        self.assertEqual(result["rows"], [])
        self.assertTrue(any("실제 수출입 행 데이터가 비어" in warning for warning in result["warnings"]))

    def test_empty_customs_snapshot_is_warning_and_not_saved(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        empty_fetch = {
            "configured": True,
            "status_message": "ok",
            "source_url": "https://example.test/customs",
            "start_yymm": "202605",
            "end_yymm": "202605",
            "item_code": "190230",
            "country_code": "US",
            "row_count": 0,
            "warnings": ["관세청 API가 정상 응답했지만 실제 수출입 행 데이터가 비어 있습니다."],
            "rows": [],
        }

        with patch.object(main, "fetch_customs_trade_rows", return_value=empty_fetch):
            snapshot = main.build_customs_trade_snapshot(
                settings=settings,
                start_yymm="202605",
                end_yymm="202605",
                item_code="190230",
                country_code="US",
            )
            saved = main.save_customs_trade_snapshot(snapshot, settings)

        self.assertEqual(snapshot["status"], "warning")
        self.assertFalse(snapshot["has_valid_data"])
        self.assertEqual(snapshot["data_quality"], "no_valid_trade_rows")
        self.assertEqual(snapshot["data_quality_label"], "실제 수출입 수치 없음")
        self.assertTrue(snapshot["storage_skip_expected"])
        self.assertIn("저장/RAG 반영하지 않습니다", snapshot["storage_policy"])
        self.assertIn("수출입총괄", snapshot["next_action"])
        self.assertTrue(saved["storage_skipped"])
        self.assertIn("저장/RAG 반영하지 않습니다", saved["storage_skip_reason"])

    def test_customs_trade_storage_helper_persists_valid_snapshot_and_rag(self):
        from research_os import customs_trade
        from research_os.research_memory import ResearchStorageInfo

        save_calls = []
        rag_calls = []

        def fake_save_research_markdown(**kwargs):
            save_calls.append(kwargs)
            return ResearchStorageInfo(
                file_name=f"{kwargs['ticker']}-{kwargs['report_type']}.md",
                relative_path=f"research_vault/{kwargs['ticker']}/{kwargs['ticker']}-{kwargs['report_type']}.md",
                absolute_path=str(kwargs['vault_dir'] / kwargs['ticker'] / f"{kwargs['ticker']}-{kwargs['report_type']}.md"),
            )

        runtime = SimpleNamespace(
            current_storage_date=lambda: date(2026, 6, 13),
            render_customs_trade_markdown=lambda snapshot, storage_date: f"customs {storage_date.isoformat()}",
            resolve_vault_dir=lambda value: Path(value),
            save_research_markdown=fake_save_research_markdown,
            upsert_saved_workflow_rag_document=lambda **kwargs: rag_calls.append(kwargs) or {"status": "upserted"},
        )
        snapshot = {
            "has_valid_data": True,
            "start_yymm": "202605",
            "end_yymm": "202605",
            "key_takeaways": ["반도체 수출 증가", "자동차 둔화"],
            "source": "관세청",
            "source_urls": ["https://example.test/customs"],
            "sector_implications": ["반도체 점검"],
            "release_schedule": "1,11,21",
            "warnings": [],
        }
        vault_dir = PROJECT_ROOT / ".test-tmp" / "customs-storage-vault"

        saved = customs_trade.save_customs_trade_snapshot(
            runtime,
            snapshot,
            SimpleNamespace(research_vault_dir=str(vault_dir)),
        )

        self.assertEqual(saved["storage"].file_name, "CUSTOMS-customs-trade-brief.md")
        self.assertEqual(saved["rag_document"], {"status": "upserted"})
        self.assertEqual(save_calls[0]["ticker"], "CUSTOMS")
        self.assertEqual(save_calls[0]["report_type"], "customs-trade-brief")
        self.assertEqual(save_calls[0]["file_suffix"], "202605-202605")
        self.assertIn("반도체 수출 증가", save_calls[0]["manifest_entry"]["summary"])
        self.assertEqual(save_calls[0]["manifest_entry"]["source_confidence"], 0.88)
        self.assertEqual(save_calls[0]["manifest_entry"]["sector_implications"], ["반도체 점검"])
        self.assertEqual(rag_calls[0]["storage_key"], "CUSTOMS")
        self.assertEqual(rag_calls[0]["source_confidence"], 0.88)
        self.assertEqual(rag_calls[0]["metadata"]["source_urls"], ["https://example.test/customs"])

    def test_customs_total_trend_provider_status_is_separated_from_item_trade_api(self):
        from research_os.analysis_data_provider import get_analysis_data_provider
        from research_os.settings import Settings

        settings = Settings(
            data_provider_mode="kis",
            customs_trade_enabled=True,
            customs_trade_api_key="test-key",
            customs_trade_api_url="https://example.test/item-trade",
            customs_trade_total_api_url="https://example.test/total-trend",
        )

        statuses = {provider["name"]: provider for provider in get_analysis_data_provider(settings).status()}

        self.assertIn("korea_customs_trade", statuses)
        self.assertIn("korea_customs_trade_total_trend", statuses)
        self.assertTrue(statuses["korea_customs_trade_total_trend"]["ready"])
        self.assertIn("수출입총괄", statuses["korea_customs_trade_total_trend"]["message"])

    def test_customs_total_trend_403_returns_actionable_warning_without_secret(self):
        from research_os.customs_data_provider import fetch_customs_total_trend_status
        from research_os.settings import Settings

        class FakeResponse:
            status_code = 403
            text = "Forbidden"
            headers = {}

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def get(self, *args, **kwargs):
                return FakeResponse()

        settings = Settings(
            customs_trade_enabled=True,
            customs_trade_api_key="secret-test-key",
            customs_trade_total_api_url="https://example.test/total-trend",
        )

        with patch("research_os.customs_data_provider.httpx.Client", new=FakeClient):
            status = fetch_customs_total_trend_status(
                settings,
                start_yymm="202605",
                end_yymm="202605",
            )

        self.assertEqual(status["status"], "warning")
        self.assertFalse(status["authorized"])
        self.assertEqual(status["http_status_code"], 403)
        self.assertIn("활용 신청/승인", " ".join(status["warnings"]))
        self.assertIn("활용 신청/승인", status["next_action"])
        self.assertNotIn("secret-test-key", str(status))

    def test_daily_customs_reference_includes_total_trend_diagnostic_when_rows_are_empty(self):
        import research_os_main as main
        from research_os.settings import Settings

        settings = Settings(customs_trade_release_days="1,11,21")
        empty_fetch = {
            "configured": True,
            "status_message": "ok",
            "source_url": "https://example.test/customs",
            "start_yymm": "202605",
            "end_yymm": "202605",
            "item_code": "",
            "country_code": "US",
            "row_count": 0,
            "warnings": ["품목별 수출입 행 데이터가 비어 있습니다."],
            "rows": [],
        }
        total_status = {
            "status": "warning",
            "authorized": False,
            "http_status_code": 403,
            "warnings": ["관세청 수출입총괄(GW) API가 403 Forbidden을 반환했습니다."],
            "row_count": 0,
            "next_action": "data.go.kr에서 활용 신청/승인 상태를 확인하세요.",
        }

        with (
            patch.object(main, "should_check_customs_trade_today", return_value=True),
            patch.object(main, "fetch_customs_trade_rows", return_value=empty_fetch),
            patch.object(main, "fetch_customs_total_trend_status", return_value=total_status),
        ):
            reference = main.build_daily_customs_trade_reference(settings)

        self.assertEqual(reference["status"], "warning")
        self.assertFalse(reference["has_valid_data"])
        self.assertTrue(reference["storage_skip_expected"])
        self.assertIn("저장/RAG 반영하지 않습니다", reference["storage_policy"])
        self.assertEqual(reference["total_trend_status"]["http_status_code"], 403)
        self.assertIn("활용 신청/승인", reference["total_trend_status"]["next_action"])
        self.assertTrue(any("403 Forbidden" in warning for warning in reference["warnings"]))

    def test_customs_total_trend_status_route_is_diagnostic_only(self):
        import research_os_main as main
        from fastapi.testclient import TestClient

        diagnostic = {
            "status": "warning",
            "configured": True,
            "authorized": False,
            "http_status_code": 403,
            "source_url": "https://example.test/total-trend",
            "docs_url": "https://www.data.go.kr/data/15102108/openapi.do",
            "start_yymm": "202605",
            "end_yymm": "202605",
            "row_count": 0,
            "rows": [],
            "warnings": ["관세청 수출입총괄(GW) API가 403 Forbidden을 반환했습니다."],
            "message": "관세청 수출입총괄(GW) API 권한 또는 연결 확인 필요",
            "next_action": "data.go.kr에서 활용 신청/승인 상태를 확인하세요.",
        }

        with patch.object(main, "fetch_customs_total_trend_status", return_value=diagnostic):
            response = TestClient(main.app).get(
                "/api/v1/macro/customs-trade/total-trend/status?start_yymm=202605&end_yymm=202605",
                headers={"Authorization": "Bearer dev-local-token"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["module"], "korea_customs_trade_total_trend_status")
        self.assertEqual(payload["http_status_code"], 403)
        self.assertFalse(payload["authorized"])
        self.assertIn("진단 전용", payload["storage_policy"])
        self.assertIn("활용 신청/승인", payload["next_action"])
        self.assertNotIn("storage", payload)

    def test_latest_customs_route_attaches_total_trend_diagnostic_before_skipping_storage(self):
        import research_os_main as main
        from fastapi.testclient import TestClient

        empty_fetch = {
            "configured": True,
            "status_message": "ok",
            "source_url": "https://example.test/customs",
            "start_yymm": "202605",
            "end_yymm": "202605",
            "item_code": "190230",
            "country_code": "US",
            "row_count": 0,
            "warnings": ["품목별 수출입 행 데이터가 비어 있습니다."],
            "rows": [],
        }
        total_status = {
            "status": "warning",
            "authorized": False,
            "http_status_code": 403,
            "warnings": ["관세청 수출입총괄(GW) API가 403 Forbidden을 반환했습니다."],
            "row_count": 0,
            "next_action": "data.go.kr에서 활용 신청/승인 상태를 확인하세요.",
        }

        with (
            patch.object(main, "fetch_customs_trade_rows", return_value=empty_fetch),
            patch.object(main, "fetch_customs_total_trend_status", return_value=total_status),
        ):
            response = TestClient(main.app).get(
                "/api/v1/macro/customs-trade/latest?start_yymm=202605&end_yymm=202605&save_result=true",
                headers={"Authorization": "Bearer dev-local-token"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "warning")
        self.assertTrue(payload["storage_skipped"])
        self.assertEqual(payload["total_trend_status"]["http_status_code"], 403)
        self.assertIn("활용 신청/승인", payload["total_trend_status"]["next_action"])
        self.assertTrue(any("403 Forbidden" in warning for warning in payload["warnings"]))


class PortfolioPerformanceTests(unittest.TestCase):
    def test_portfolio_performance_quality_marks_price_difference(self):
        from research_os.portfolio_performance import build_performance_quality_summary

        summary = build_performance_quality_summary(
            [
                {"coverage_rate": 0.9, "included_count": 3},
                {"coverage_rate": 0.85, "included_count": 2},
            ],
            [{"ticker": "003230", "difference_rate": 0.02}],
            excluded_holding_count=1,
            latest_stored_price_checked_at="2026-06-13T09:00:00+09:00",
            price_basis="저장 현재가 + 국내 가격 히스토리 최신 종가",
        )

        self.assertEqual(summary["confidence_label"], "보통")
        self.assertEqual(summary["min_coverage_rate"], 0.85)
        self.assertEqual(summary["average_coverage_rate"], 0.875)
        self.assertEqual(summary["covered_holding_count"], 3)
        self.assertEqual(summary["excluded_holding_count"], 1)
        self.assertEqual(summary["domestic_price_difference_count"], 1)
        self.assertEqual(summary["latest_stored_price_checked_at"], "2026-06-13T09:00:00+09:00")

    def test_portfolio_period_accumulators_finalize_coverage_and_leaders(self):
        from research_os.portfolio_performance import (
            build_period_accumulators,
            finalize_period_accumulators,
        )

        definitions = [("1w", "최근 1주일", 7)]
        accumulators = build_period_accumulators(definitions)
        period = accumulators["1w"]
        period["target_dates"].extend(["2026-06-05", "2026-06-06"])
        period["price_as_of_dates"].extend(["2026-06-12", "2026-06-13"])
        period["current_value"] = 1200.123
        period["base_value"] = 1000.0
        period["net_profit"] = 200.123
        period["included_count"] = 2
        period["covered_market_value"] = 1200.123
        period["top_gainers"].extend([
            {"ticker": "A", "net_profit": 10},
            {"ticker": "B", "net_profit": 50},
            {"ticker": "C", "net_profit": 20},
            {"ticker": "D", "net_profit": 40},
        ])
        period["top_losers"].extend([
            {"ticker": "A", "net_profit": -10},
            {"ticker": "B", "net_profit": -50},
            {"ticker": "C", "net_profit": -20},
            {"ticker": "D", "net_profit": -40},
        ])

        finalized = finalize_period_accumulators(definitions, accumulators, current_portfolio_value=2400)

        self.assertEqual(len(finalized), 1)
        self.assertEqual(finalized[0]["current_value"], 1200.12)
        self.assertEqual(finalized[0]["base_value"], 1000.0)
        self.assertEqual(finalized[0]["net_profit"], 200.12)
        self.assertEqual(finalized[0]["return_rate"], 0.2001)
        self.assertEqual(finalized[0]["target_date"], "2026-06-06")
        self.assertEqual(finalized[0]["price_as_of"], "2026-06-13")
        self.assertEqual(finalized[0]["coverage_rate"], 0.5001)
        self.assertEqual([item["ticker"] for item in finalized[0]["top_gainers"]], ["B", "D", "C"])
        self.assertEqual([item["ticker"] for item in finalized[0]["top_losers"]], ["B", "D", "C"])

    def test_portfolio_performance_helpers_select_history_and_current_value(self):
        from research_os.models import PortfolioHolding
        from research_os.portfolio_performance import (
            historical_close_on_or_before,
            portfolio_holding_current_value,
        )

        rows = [
            {"date": "2026-06-10", "close": "95"},
            {"date": "2026-06-12", "close": "100"},
            {"date": "2026-06-13", "close": "105"},
        ]
        parse_float = lambda value: float(value) if value not in {None, ""} else None
        holding = PortfolioHolding(
            ticker="PL",
            quantity=10,
            current_price=5,
            market_value=0,
            currency="USD",
        )

        close, close_date = historical_close_on_or_before(rows, date(2026, 6, 11), parse_float)
        current_value = portfolio_holding_current_value(
            holding,
            6.5,
            lambda _holding: 1300.0,
            prefer_market_value=False,
        )

        self.assertEqual((close, close_date), (95.0, "2026-06-10"))
        self.assertEqual(current_value, 84500.0)

    def test_price_refresh_summary_tracks_status_counts_and_latest_check(self):
        from research_os.models import PortfolioHolding
        from research_os.portfolio_performance import build_price_refresh_summary

        summary = build_price_refresh_summary([
            PortfolioHolding(
                ticker="003230",
                name="삼양식품",
                price_refresh_status="updated",
                price_checked_at="2026-05-19T09:00:00+09:00",
            ),
            PortfolioHolding(
                ticker="033500",
                name="동성화인텍",
                price_refresh_status="confirmed",
                price_checked_at="2026-05-19T09:05:00+09:00",
            ),
            PortfolioHolding(ticker="PL", name="Planet Labs", price_refresh_status="unavailable"),
        ])

        self.assertTrue(summary["enabled"])
        self.assertTrue(summary["force_price_refresh"])
        self.assertEqual(summary["updated"], 1)
        self.assertEqual(summary["confirmed"], 1)
        self.assertEqual(summary["unavailable"], 1)
        self.assertEqual(summary["latest_checked_at"], "2026-05-19T09:05:00+09:00")

    def test_portfolio_load_refreshes_prices_and_persists_result(self):
        import research_os_main as main
        from research_os.models import PortfolioHolding, SavedPortfolio
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        portfolio = SavedPortfolio(
            portfolio_name="테스트",
            holdings=[
                PortfolioHolding(
                    ticker="003230",
                    name="삼양식품",
                    quantity=10,
                    average_cost=80,
                    current_price=100,
                    market_value=1000,
                    cost_basis=800,
                    currency="KRW",
                )
            ],
            portfolio_value=1000,
            updated_at="2026-05-18T09:00:00+09:00",
        )
        store = {
            "portfolios": {
                main.portfolio_store_key("테스트"): portfolio.model_dump(mode="json")
            }
        }

        with (
            patch.object(main, "read_portfolio_store", return_value=copy.deepcopy(store)),
            patch.object(main, "latest_provider_price", return_value=(120, "live-test")) as latest_price,
            patch.object(main, "portfolio_store_path", return_value=PROJECT_ROOT / "tmp_portfolios.json"),
            patch.object(main, "write_json_store") as write_json_store,
            patch.object(main, "current_storage_timestamp", return_value="2026-05-19T09:00:00+09:00"),
        ):
            result = main.get_portfolio("테스트", settings=settings)

        latest_price.assert_called_once_with("003230", settings, force_refresh=True)
        self.assertEqual(result.active_portfolio.holdings[0].current_price, 120)
        self.assertEqual(result.active_portfolio.holdings[0].market_value, 1200)
        self.assertEqual(result.active_portfolio.holdings[0].unrealized_gain, 400)
        self.assertEqual(result.active_portfolio.holdings[0].unrealized_return, 0.5)
        self.assertEqual(result.active_portfolio.holdings[0].price_refresh_status, "updated")
        self.assertEqual(result.active_portfolio.holdings[0].price_checked_at, "2026-05-19T09:00:00+09:00")
        self.assertEqual(result.active_portfolio.updated_at, "2026-05-19T09:00:00+09:00")
        self.assertTrue(write_json_store.called)
        persisted_store = write_json_store.call_args.args[1]
        persisted = persisted_store["portfolios"][main.portfolio_store_key("테스트")]
        self.assertEqual(persisted["holdings"][0]["current_price"], 120)
        self.assertEqual(persisted["holdings"][0]["price_refresh_status"], "updated")
        self.assertEqual(persisted["portfolio_value"], 1200)

    def test_portfolio_load_marks_overseas_quantity_as_protected_during_price_refresh(self):
        import research_os_main as main
        from research_os.models import PortfolioHolding, SavedPortfolio
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        portfolio = SavedPortfolio(
            portfolio_name="테스트",
            holdings=[
                PortfolioHolding(
                    ticker="JOBY",
                    name="Joby Aviation",
                    quantity=208,
                    average_cost=7.55,
                    current_price=10.0,
                    market_value=2080,
                    cost_basis=1570.4,
                    currency="USD",
                ),
                PortfolioHolding(
                    ticker="003230",
                    name="삼양식품",
                    quantity=18,
                    average_cost=85000,
                    current_price=1357000,
                    market_value=24426000,
                    cost_basis=1530000,
                    currency="KRW",
                ),
            ],
            portfolio_value=24428080,
        )

        with (
            patch.object(main, "latest_provider_price", return_value=(11.0, "live-test")),
            patch.object(main, "current_storage_timestamp", return_value="2026-05-26T10:00:00+09:00"),
        ):
            refreshed = main.sort_and_weight_portfolio(portfolio, settings, refresh_prices=True)

        by_ticker = {holding.ticker: holding for holding in refreshed.holdings}
        self.assertEqual(by_ticker["JOBY"].quantity, 208)
        self.assertEqual(by_ticker["JOBY"].sync_status, "manual_or_overseas_protected")
        self.assertEqual(by_ticker["JOBY"].sync_source, "portfolio_state_guard")
        self.assertIsNone(by_ticker["003230"].sync_status)

    def test_kiwoom_domestic_sync_updates_domestic_and_preserves_overseas(self):
        import research_os_main as main
        from research_os.models import PortfolioHolding, SavedPortfolio
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        portfolio = SavedPortfolio(
            portfolio_name="테스트",
            holdings=[
                PortfolioHolding(
                    ticker="003230",
                    name="삼양식품",
                    quantity=10,
                    average_cost=80,
                    current_price=100,
                    market_value=1000,
                    cost_basis=800,
                    currency="KRW",
                ),
                PortfolioHolding(
                    ticker="PL",
                    name="Planet Labs PBC",
                    quantity=100,
                    average_cost=1.84,
                    current_price=42,
                    market_value=6000000,
                    cost_basis=260000,
                    currency="USD",
                ),
            ],
            portfolio_value=6001000,
        )
        balance = {
            "api_id": "kt00018",
            "holdings": [
                {
                    "ticker": "003230",
                    "name": "삼양식품",
                    "quantity": 12,
                    "average_cost": 85,
                    "current_price": 120,
                    "market_value": 1440,
                    "cost_basis": 1020,
                    "unrealized_gain": 420,
                    "unrealized_return": 0.4118,
                    "currency": "KRW",
                }
            ],
        }

        with patch.object(main, "current_storage_timestamp", return_value="2026-05-21T09:00:00+09:00"):
            synced, summary = main.sync_saved_portfolio_with_kiwoom_domestic(
                portfolio,
                balance,
                settings,
            )

        by_ticker = {holding.ticker: holding for holding in synced.holdings}
        self.assertEqual(by_ticker["003230"].quantity, 12)
        self.assertEqual(by_ticker["003230"].average_cost, 85)
        self.assertEqual(by_ticker["003230"].price_source, "kiwoom_domestic_balance")
        self.assertEqual(by_ticker["PL"].quantity, 100)
        self.assertEqual(by_ticker["PL"].average_cost, 1.84)
        self.assertEqual(summary["updated_count"], 1)
        self.assertEqual(summary["skipped_count"], 1)
        self.assertEqual(summary["skipped"][0]["reason"], "manual_or_overseas_protected")
        self.assertEqual(by_ticker["PL"].sync_status, "manual_or_overseas_protected")

    def test_kiwoom_domestic_sync_does_not_overwrite_explicit_foreign_holding(self):
        import research_os_main as main
        from research_os.models import PortfolioHolding, SavedPortfolio
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        portfolio = SavedPortfolio(
            portfolio_name="테스트",
            holdings=[
                PortfolioHolding(
                    ticker="AB123C",
                    name="Foreign Manual",
                    quantity=100,
                    average_cost=5,
                    current_price=7,
                    market_value=700,
                    currency="USD",
                )
            ],
        )
        balance = {
            "api_id": "kt00018",
            "holdings": [
                {
                    "ticker": "AB123C",
                    "name": "Unexpected Domestic Match",
                    "quantity": 1,
                    "average_cost": 999,
                    "current_price": 999,
                    "market_value": 999,
                    "currency": "KRW",
                }
            ],
        }

        synced, summary = main.sync_saved_portfolio_with_kiwoom_domestic(
            portfolio,
            balance,
            settings,
        )

        holding = synced.holdings[0]
        self.assertEqual(holding.quantity, 100)
        self.assertEqual(holding.average_cost, 5)
        self.assertEqual(holding.currency, "USD")
        self.assertEqual(holding.sync_status, "manual_or_overseas_protected")
        self.assertEqual(summary["updated_count"], 0)
        self.assertEqual(summary["skipped"][0]["reason"], "manual_or_overseas_protected")

    def test_portfolio_import_infers_krw_for_domestic_ticker(self):
        import research_os_main as main

        holding = main.portfolio_holding_from_row(
            {
                "종목코드": "003230",
                "종목명": "삼양식품",
                "수량": "18",
                "현재가": "1,357,000",
            }
        )

        self.assertIsNotNone(holding)
        self.assertEqual(holding.currency, "KRW")

    def test_kiwoom_domestic_sync_preview_does_not_write_and_apply_records_history(self):
        import research_os_main as main
        from research_os.models import PortfolioHolding, SavedPortfolio
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        portfolio = SavedPortfolio(
            portfolio_name="테스트",
            holdings=[
                PortfolioHolding(
                    ticker="033500",
                    name="동성화인텍",
                    quantity=167,
                    average_cost=29800,
                    market_value=3700000,
                    currency="KRW",
                ),
                PortfolioHolding(
                    ticker="PL",
                    name="Planet Labs PBC",
                    quantity=100,
                    average_cost=1.84,
                    market_value=6000000,
                    currency="USD",
                ),
            ],
        )
        store = {
            "portfolios": {
                main.portfolio_store_key("테스트"): portfolio.model_dump(mode="json")
            }
        }
        balance = {
            "api_id": "kt00018",
            "holdings": [
                {
                    "ticker": "033500",
                    "name": "동성화인텍",
                    "quantity": 170,
                    "average_cost": 29700,
                    "current_price": 22500,
                    "market_value": 3825000,
                    "cost_basis": 5049000,
                    "unrealized_gain": -1224000,
                    "unrealized_return": -0.2424,
                }
            ],
        }

        with (
            patch.object(main, "read_portfolio_store", return_value=copy.deepcopy(store)),
            patch.object(main, "fetch_kiwoom_domestic_balance", return_value=balance),
            patch.object(main, "write_json_store") as write_json_store,
            patch.object(main, "append_portfolio_sync_history") as append_history,
            patch.object(main, "current_storage_timestamp", return_value="2026-05-21T10:00:00+09:00"),
        ):
            preview = main.build_portfolio_kiwoom_domestic_sync_response(
                "테스트",
                settings,
                apply_changes=False,
            )

        self.assertEqual(preview["sync_summary"]["mode"], "preview")
        preview_by_ticker = {
            holding["ticker"]: holding
            for holding in preview["active_portfolio"]["holdings"]
        }
        self.assertEqual(preview_by_ticker["033500"]["quantity"], 170)
        self.assertEqual(preview_by_ticker["PL"]["quantity"], 100)
        write_json_store.assert_not_called()
        append_history.assert_not_called()

        with (
            patch.object(main, "read_portfolio_store", return_value=copy.deepcopy(store)),
            patch.object(main, "fetch_kiwoom_domestic_balance", return_value=balance),
            patch.object(main, "write_json_store") as write_json_store,
            patch.object(main, "append_portfolio_sync_history") as append_history,
            patch.object(main, "current_storage_timestamp", return_value="2026-05-21T10:00:00+09:00"),
        ):
            applied = main.build_portfolio_kiwoom_domestic_sync_response(
                "테스트",
                settings,
                apply_changes=True,
            )

        self.assertEqual(applied["sync_summary"]["mode"], "apply")
        self.assertTrue(write_json_store.called)
        append_history.assert_called_once()

    def test_kiwoom_domestic_sync_connection_error_returns_safe_status(self):
        import httpx
        import research_os_main as main
        from research_os.models import PortfolioHolding, SavedPortfolio
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        portfolio = SavedPortfolio(
            portfolio_name="테스트",
            holdings=[
                PortfolioHolding(ticker="033500", name="동성화인텍", quantity=167),
                PortfolioHolding(ticker="PL", name="Planet Labs PBC", quantity=100),
            ],
        )
        store = {
            "portfolios": {
                main.portfolio_store_key("테스트"): portfolio.model_dump(mode="json")
            }
        }

        with (
            patch.object(main, "read_portfolio_store", return_value=store),
            patch.object(main, "fetch_kiwoom_domestic_balance", side_effect=httpx.ConnectError("connection refused")),
            patch.object(main, "write_json_store") as write_json_store,
            patch.object(main, "append_portfolio_sync_history") as append_history,
        ):
            result = main.build_portfolio_kiwoom_domestic_sync_response(
                "테스트",
                settings,
                apply_changes=False,
            )

        self.assertEqual(result["sync_summary"]["status"], "kiwoom_unavailable")
        self.assertIn("연결하지 못했습니다", result["sync_summary"]["message"])
        self.assertEqual(result["sync_summary"]["mode"], "preview")
        self.assertEqual(result["sync_summary"]["skipped_count"], 2)
        self.assertTrue(
            all(item["reason"] == "kiwoom_unavailable" for item in result["sync_summary"]["skipped"])
        )
        write_json_store.assert_not_called()
        append_history.assert_not_called()

    def test_portfolio_sync_history_reads_newest_valid_records_and_summarizes_status(self):
        import research_os_main as main
        from research_os.models import PortfolioHolding, SavedPortfolio
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        history_path = PROJECT_ROOT / "tmp_portfolio_sync_history.jsonl"
        self.addCleanup(lambda: history_path.unlink(missing_ok=True))
        history_path.write_text(
            "\n".join(
                [
                    '{"created_at":"2026-05-21T09:00:00+09:00","portfolio_name":"테스트","mode":"apply","updated_count":1}',
                    "not-json",
                    '{"created_at":"2026-05-21T10:00:00+09:00","portfolio_name":"다른","mode":"apply","updated_count":9}',
                    '{"created_at":"2026-05-21T11:00:00+09:00","portfolio_name":"테스트","mode":"apply","updated_count":2}',
                ]
            ),
            encoding="utf-8",
        )

        with patch("research_os.portfolio_sync.portfolio_sync_history_path", return_value=history_path):
            records = main.read_portfolio_sync_history(settings, limit=3)

        self.assertEqual([record["created_at"] for record in records], [
            "2026-05-21T11:00:00+09:00",
            "2026-05-21T10:00:00+09:00",
            "2026-05-21T09:00:00+09:00",
        ])

        portfolio = SavedPortfolio(
            portfolio_name="테스트",
            holdings=[
                PortfolioHolding(ticker="033500", name="동성화인텍", sync_status="account_synced", sync_checked_at="2026-05-21T11:00:00+09:00"),
                PortfolioHolding(ticker="PL", name="Planet Labs PBC", sync_status="manual_or_overseas_protected", sync_checked_at="2026-05-21T11:00:00+09:00"),
                PortfolioHolding(ticker="123456", name="국내 미확인", sync_status="kiwoom_domestic_missing", sync_checked_at="2026-05-21T11:00:00+09:00"),
            ],
        )
        store = {
            "portfolios": {
                main.portfolio_store_key("테스트"): portfolio.model_dump(mode="json")
            }
        }

        with (
            patch.object(main, "read_portfolio_store", return_value=store),
            patch.object(main, "read_portfolio_sync_history", return_value=records),
        ):
            result = main.get_portfolio_sync_history("테스트", limit=10, settings=settings)

        self.assertEqual(result["portfolio_name"], "테스트")
        self.assertEqual([item["portfolio_name"] for item in result["history"]], ["테스트", "테스트"])
        self.assertEqual(result["summary"]["counts"]["account_synced"], 1)
        self.assertEqual(result["summary"]["counts"]["manual_or_overseas_protected"], 1)
        self.assertEqual(result["summary"]["counts"]["kiwoom_domestic_missing"], 1)

    def test_intelligent_table_can_force_live_price_refresh(self):
        import research_os_main as main
        from research_os.models import (
            PortfolioHolding,
            SavedPortfolio,
            TickerVerificationResponse,
        )
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        portfolio = SavedPortfolio(
            portfolio_name="테스트",
            holdings=[
                PortfolioHolding(
                    ticker="003230",
                    name="삼양식품",
                    quantity=10,
                    average_cost=80,
                    current_price=100,
                    market_value=1000,
                    cost_basis=800,
                    currency="KRW",
                )
            ],
            portfolio_value=1000,
        )
        store = {
            "portfolios": {
                main.portfolio_store_key("테스트"): portfolio.model_dump(mode="json")
            }
        }
        verification = TickerVerificationResponse(
            requested_symbol="003230",
            official_symbol="003230",
            company_name="삼양식품",
            exchange="KRX",
            country="KR",
            verified=True,
            verification_source="test",
            message="ok",
        )

        with (
            patch.object(main, "read_portfolio_store", return_value=copy.deepcopy(store)),
            patch.object(main, "latest_provider_price", return_value=(120, "live-test")) as latest_price,
            patch.object(main, "portfolio_store_path", return_value=PROJECT_ROOT / "tmp_portfolios.json"),
            patch.object(main, "write_json_store") as write_json_store,
            patch.object(main, "current_storage_timestamp", return_value="2026-05-19T09:10:00+09:00"),
            patch.object(main, "resolve_vault_dir", return_value=PROJECT_ROOT / "research_vault"),
            patch.object(main, "count_research_memory_documents_by_ticker", return_value={}),
            patch.object(main, "read_manifest", return_value=[]),
            patch.object(main, "read_dart_filing_cache", return_value={"entries": {}}),
            patch.object(main, "official_ticker_profile", return_value={"company_name": "삼양식품", "sector": "식품"}),
            patch.object(main, "verify_ticker_symbol", return_value=verification),
            patch.object(main, "fetch_52_week_high_for_holding", return_value={"week52_status": "테스트"}),
            patch.object(main, "parse_latest_target_price_from_memory", return_value=None),
            patch.object(main, "read_ticker_thesis_snapshot", return_value=None),
        ):
            result = main.build_portfolio_intelligent_table(
                "테스트",
                settings,
                force_price_refresh=True,
                persist_refresh=True,
            )

        latest_price.assert_called_once_with("003230", settings, force_refresh=True)
        self.assertEqual(result["price_refresh"]["updated"], 1)
        self.assertEqual(result["holdings"][0]["current_price"], 120)
        self.assertEqual(result["holdings"][0]["price_refresh_status"], "updated")
        self.assertEqual(result["holdings"][0]["price_checked_at"], "2026-05-19T09:10:00+09:00")
        self.assertTrue(write_json_store.called)

    def test_performance_marks_overseas_history_limits_and_cache_mode(self):
        import research_os_main as main
        from research_os.models import PortfolioHolding, SavedPortfolio
        from research_os.settings import Settings

        settings = Settings(research_vault_dir="../research_vault")
        portfolio = SavedPortfolio(
            portfolio_name="테스트",
            holdings=[
                PortfolioHolding(
                    ticker="003230",
                    name="삼양식품",
                    quantity=10,
                    average_cost=80,
                    current_price=110,
                    market_value=1200,
                    cost_basis=800,
                    unrealized_gain=400,
                    currency="KRW",
                ),
                PortfolioHolding(
                    ticker="PL",
                    name="Planet Labs",
                    quantity=1,
                    average_cost=8,
                    current_price=10,
                    market_value=14000,
                    cost_basis=11200,
                    unrealized_gain=2800,
                    unrealized_return=0.25,
                    currency="USD",
                ),
            ],
            portfolio_value=15200,
        )
        store = {
            "portfolios": {
                main.portfolio_store_key("테스트"): portfolio.model_dump(mode="json")
            }
        }
        history_rows = [
            {"date": "2025-05-18", "close": 60},
            {"date": "2025-11-17", "close": 80},
            {"date": "2026-04-18", "close": 90},
            {"date": "2026-05-11", "close": 100},
            {"date": "2026-05-18", "close": 120},
        ]

        def fake_history_rows(ticker, _settings, **_kwargs):
            if ticker == "003230":
                return "003230", history_rows, {"cache_hit": True}
            raise ValueError("국내 가격 히스토리 지원 대상이 아닙니다.")

        original_history_cache = dict(main.PORTFOLIO_HISTORY_CACHE)
        main.PORTFOLIO_HISTORY_CACHE.clear()
        main.PORTFOLIO_HISTORY_CACHE["003230:280"] = history_rows

        with (
            patch.object(main, "read_portfolio_store", return_value=store),
            patch.object(main, "sort_and_weight_portfolio", side_effect=lambda p, *_args, **_kwargs: p),
            patch.object(main, "portfolio_history_rows_for_ticker", side_effect=fake_history_rows),
            patch.object(main, "current_storage_date", return_value=date(2026, 5, 18)),
            patch.object(main, "current_storage_timestamp", return_value="2026-05-18T09:00:00+09:00"),
        ):
            result = main.build_portfolio_performance("테스트", settings)

        main.PORTFOLIO_HISTORY_CACHE.clear()
        main.PORTFOLIO_HISTORY_CACHE.update(original_history_cache)

        self.assertEqual(result["calculation_mode"], "recomputed_on_request")
        self.assertFalse(result["current_price_refresh"]["enabled"])
        self.assertFalse(result["current_price_refresh"]["force_price_refresh"])
        self.assertIn("저장 현재가", result["current_price_refresh"]["description"])
        self.assertFalse(result["result_cache"]["enabled"])
        self.assertTrue(result["price_history_cache"]["enabled"])
        self.assertEqual(result["price_history_cache"]["hit_count"], 1)
        self.assertEqual(result["performance_quality"]["confidence_label"], "제한적")
        self.assertEqual(result["performance_quality"]["domestic_price_difference_count"], 1)
        self.assertEqual(result["current_price_comparison"]["difference_count"], 1)
        self.assertEqual(result["current_price_comparison"]["items"][0]["name"], "삼양식품")
        self.assertEqual(result["price_basis"], "저장 현재가 + 국내 가격 히스토리 최신 종가")
        self.assertIn("가격 갱신/차트 조회", result["price_refresh_guidance"])
        self.assertEqual(result["unsupported_history_count"], 1)
        self.assertEqual(result["unsupported_history_market_value"], 14000)
        self.assertEqual(result["skipped_holdings"][0]["category"], "overseas_or_unsupported_history")
        self.assertEqual(result["skipped_holdings"][0]["manual_unrealized_gain"], 2800)
        self.assertEqual(result["skipped_holdings"][0]["manual_unrealized_return"], 0.25)
        self.assertIn("네이버 국내 종목 코드", " ".join(result["data_limitations"]))
        self.assertEqual(result["periods"][0]["net_profit"], 200)
        self.assertEqual(result["periods"][0]["return_rate"], 0.2)

class InvestmentJournalManualImportTests(unittest.TestCase):
    def temp_database_dir(self) -> TemporaryDirectory:
        temp_root = PROJECT_ROOT / ".test-tmp"
        temp_root.mkdir(exist_ok=True)
        return TemporaryDirectory(dir=temp_root)

    def make_settings(self, temp_dir: str):
        from app.settings import Settings

        return Settings(
            local_db_path=str(Path(temp_dir) / "investment_journal_test.sqlite3"),
            secret_salt="test-secret-salt",
            dev_user_token="test-token",
            db_backup_on_startup=False,
            sqlite_restrict_file_permissions=False,
        )

    def test_manual_csv_import_feeds_mobile_analytics_charts(self):
        import main as backend_main
        from app.database import init_db
        from app.settings import get_settings
        from fastapi.testclient import TestClient

        with self.temp_database_dir() as temp_dir:
            settings = self.make_settings(temp_dir)
            init_db(settings)
            backend_main.app.dependency_overrides[get_settings] = lambda: settings
            client = TestClient(backend_main.app)
            try:
                csv_text = "\n".join(
                    [
                        "trade_date,broker,account_name,transaction_type,ticker,name,quantity,price,buy_amount,sell_amount,profit_loss_amount,dividend_amount,tax_amount,commission_amount,currency,fx_rate_krw,memo",
                        "2026-01-15,CSV,테스트계좌,trade,005930,삼성전자,10,70000,700000,710000,10000,500,100,50,KRW,,국내 수동 입력",
                        "2026-02-03,CSV,해외계좌,trade,PL,Planet Labs,2,8,16,18,10,0,1,1,USD,1300,해외 수동 입력",
                    ]
                )

                import_response = client.post(
                    "/api/v1/manual-transactions/import.csv",
                    content=csv_text.encode("utf-8-sig"),
                    headers={
                        "Authorization": "Bearer test-token",
                        "Content-Type": "text/csv; charset=utf-8",
                    },
                )
                self.assertEqual(import_response.status_code, 200)
                imported = import_response.json()
                self.assertEqual(imported["imported_count"], 2)
                self.assertEqual(imported["failed_count"], 0)

                analytics_response = client.get(
                    "/api/v1/journal/analytics",
                    headers={"Authorization": "Bearer test-token"},
                )
                self.assertEqual(analytics_response.status_code, 200)
                analytics = analytics_response.json()

                self.assertEqual(analytics["manual_transactions_count"], 2)
                self.assertEqual(analytics["total_entries"], 2)
                self.assertEqual(analytics["realized_profit_loss_total"], 20750)
                self.assertEqual(analytics["dividend_total"], 500)
                self.assertEqual(analytics["tax_total"], 1400)
                self.assertEqual(analytics["commission_total"], 1350)
                self.assertEqual(analytics["win_count"], 2)
                self.assertEqual(analytics["win_rate"], 100.0)
                self.assertEqual(analytics["annual_profit"][0]["period"], "2026")
                self.assertEqual(analytics["annual_profit"][0]["profit_loss_total"], 20750)
                self.assertEqual(analytics["quarterly_profit"][0]["period"], "2026-Q1")
                self.assertEqual(analytics["quarterly_profit"][0]["profit_loss_total"], 20750)
                self.assertEqual(
                    [row["period"] for row in analytics["monthly_profit"]],
                    ["2026-02", "2026-01"],
                )
                self.assertEqual(analytics["monthly_profit"][0]["tax_total"], 1300)
                self.assertEqual(analytics["monthly_profit"][0]["commission_total"], 1300)
                self.assertEqual(len(analytics["profit_trend"]), 2)
                self.assertEqual(
                    analytics["profit_trend"][-1]["cumulative_profit_loss"],
                    20750,
                )
                self.assertTrue(
                    any(row["ticker"] == "005930" for row in analytics["ticker_allocation"])
                )
                self.assertTrue(
                    any(row["account_name"] == "해외계좌" for row in analytics["account_allocation"])
                )
                usd_breakdown = next(
                    row
                    for row in analytics["currency_breakdown"]
                    if row["currency"] == "USD"
                )
                self.assertEqual(usd_breakdown["converted_count"], 1)
                self.assertEqual(usd_breakdown["profit_loss_total_krw"], 10400)
                self.assertEqual(analytics["dividend_by_year"][0]["amount"], 500)
                self.assertEqual(analytics["tax_by_year"][0]["amount"], 1400)
                self.assertEqual(analytics["commission_by_year"][0]["amount"], 1350)
            finally:
                backend_main.app.dependency_overrides.pop(get_settings, None)

    def test_manual_csv_import_accepts_korean_headers_and_cp949(self):
        import main as backend_main
        from app.database import init_db
        from app.settings import get_settings
        from fastapi.testclient import TestClient

        with self.temp_database_dir() as temp_dir:
            settings = self.make_settings(temp_dir)
            init_db(settings)
            backend_main.app.dependency_overrides[get_settings] = lambda: settings
            client = TestClient(backend_main.app)
            try:
                csv_text = "\n".join(
                    [
                        "거래일,증권사,계좌,유형,종목코드,종목명,수량,가격,매매손익,배당,세금,수수료,통화,메모",
                        "2026-04-10,타증권,테스트계좌,매매,000660,SK하이닉스,3,\"170,000\",\"12,000\",0,500,100,KRW,CP949 테스트",
                    ]
                )

                response = client.post(
                    "/api/v1/manual-transactions/import.csv",
                    files={
                        "file": (
                            "manual-transactions-cp949.csv",
                            csv_text.encode("cp949"),
                            "text/csv",
                        ),
                    },
                    headers={"Authorization": "Bearer test-token"},
                )

                self.assertEqual(response.status_code, 200)
                imported = response.json()
                self.assertEqual(imported["imported_count"], 1)
                self.assertEqual(imported["failed_count"], 0)
                transaction = imported["transactions"][0]
                self.assertEqual(transaction["ticker"], "000660")
                self.assertEqual(transaction["transaction_type"], "trade")
                self.assertEqual(transaction["profit_loss_amount"], 12000)
                self.assertEqual(transaction["commission_amount"], 100)
            finally:
                backend_main.app.dependency_overrides.pop(get_settings, None)

    def test_manual_csv_import_partially_saves_valid_rows_and_reports_failures(self):
        import main as backend_main
        from app.database import init_db, list_manual_transactions
        from app.settings import get_settings
        from fastapi.testclient import TestClient

        with self.temp_database_dir() as temp_dir:
            settings = self.make_settings(temp_dir)
            init_db(settings)
            backend_main.app.dependency_overrides[get_settings] = lambda: settings
            client = TestClient(backend_main.app)
            try:
                csv_text = "\n".join(
                    [
                        "거래일,증권사,계좌,유형,종목코드,종목명,매매손익,통화",
                        "2026-05-01,CSV,테스트계좌,trade,005930,삼성전자,1000,KRW",
                        ",CSV,테스트계좌,trade,000660,SK하이닉스,2000,KRW",
                        ",,,,,,,",
                    ]
                )

                response = client.post(
                    "/api/v1/manual-transactions/import.csv",
                    content=csv_text.encode("utf-8"),
                    headers={
                        "Authorization": "Bearer test-token",
                        "Content-Type": "text/csv; charset=utf-8",
                    },
                )

                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(payload["imported_count"], 1)
                self.assertEqual(payload["failed_count"], 1)
                self.assertEqual(payload["skipped_count"], 1)
                self.assertEqual(payload["errors"][0]["row"], 3)
                self.assertIn("거래일은 필수입니다", payload["errors"][0]["message"])

                transactions = list_manual_transactions(settings)
                self.assertEqual(len(transactions), 1)
                self.assertEqual(transactions[0]["ticker"], "005930")
                self.assertEqual(transactions[0]["profit_loss_amount"], 1000)
            finally:
                backend_main.app.dependency_overrides.pop(get_settings, None)

    def test_manual_csv_template_download_has_korean_headers_and_sample_row(self):
        import main as backend_main
        from app.settings import get_settings
        from fastapi.testclient import TestClient

        with self.temp_database_dir() as temp_dir:
            settings = self.make_settings(temp_dir)
            backend_main.app.dependency_overrides[get_settings] = lambda: settings
            client = TestClient(backend_main.app)
            try:
                response = client.get(
                    "/api/v1/manual-transactions/import.csv/template",
                    headers={"Authorization": "Bearer test-token"},
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content[:3], b"\xef\xbb\xbf")
                self.assertIn("manual-transactions-template.csv", response.headers["content-disposition"])
                text = response.content.decode("utf-8-sig")
                self.assertIn("거래일,증권사,계좌,유형,종목코드,종목명", text)
                self.assertIn("분할보정비율,보정메모,메모", text)
                self.assertIn("2026-05-22,타증권,기타,trade,005930,삼성전자", text)
            finally:
                backend_main.app.dependency_overrides.pop(get_settings, None)

    def test_manual_csv_template_allows_localhost_dev_origins(self):
        import main as backend_main
        from app.settings import get_settings
        from fastapi.testclient import TestClient

        with self.temp_database_dir() as temp_dir:
            settings = self.make_settings(temp_dir)
            backend_main.app.dependency_overrides[get_settings] = lambda: settings
            client = TestClient(backend_main.app)
            try:
                response = client.get(
                    "/api/v1/manual-transactions/import.csv/template",
                    headers={
                        "Authorization": "Bearer test-token",
                        "Origin": "http://localhost:8083",
                    },
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:8083")
            finally:
                backend_main.app.dependency_overrides.pop(get_settings, None)

    def test_foreign_manual_transaction_without_fx_is_excluded_from_krw_profit(self):
        from app.database import create_manual_transaction, get_journal_analytics, init_db

        with self.temp_database_dir() as temp_dir:
            settings = self.make_settings(temp_dir)
            init_db(settings)
            create_manual_transaction(
                settings=settings,
                trade_date="2026-03-01",
                broker="CSV",
                account_name="해외계좌",
                transaction_type="trade",
                ticker="TSLA",
                name="Tesla",
                quantity=1,
                price=200,
                profit_loss_amount=10,
                tax_amount=1,
                commission_amount=1,
                currency="USD",
            )

            analytics = get_journal_analytics(settings)

            self.assertEqual(analytics["manual_transactions_count"], 1)
            self.assertEqual(analytics["fx_unconverted_count"], 1)
            self.assertEqual(analytics["realized_profit_loss_total"], 0)
            self.assertEqual(analytics["currency_breakdown"][0]["currency"], "USD")
            self.assertEqual(analytics["currency_breakdown"][0]["unconverted_count"], 1)

    def test_history_background_job_persists_progress_and_counts(self):
        import main as backend_main
        from app.database import get_history_sync_job, init_db, start_history_sync_job
        from app.application_models import JournalSourceTradesResponse, PortfolioResponse
        from app.kiwoom_balance import KiwoomBalanceSummary
        from app.kiwoom_trade_journal import KiwoomTradeJournalSummary

        with self.temp_database_dir() as temp_dir:
            settings = self.make_settings(temp_dir)
            init_db(settings)
            portfolio = PortfolioResponse(
                broker="KIWOOM",
                synced_from="mock",
                summary=KiwoomBalanceSummary(),
                holdings_count=0,
                holdings=[],
            )
            journal = JournalSourceTradesResponse(
                broker="KIWOOM",
                synced_from=["ka10170", "kt00007"],
                base_date="20260101",
                trade_summary=KiwoomTradeJournalSummary(),
                trade_journal_items_count=2,
                trade_journal_items=[],
                order_executions_count=3,
                order_executions=[],
                needs_review_count=3,
            )
            job = start_history_sync_job(
                settings=settings,
                broker="KIWOOM",
                start_date="20260101",
                end_date="20260102",
                total_days=2,
            )

            with (
                patch.object(backend_main, "read_portfolio", return_value=portfolio),
                patch.object(
                    backend_main,
                    "_fetch_journal_source_trades_for_date_with_retry",
                    return_value=journal,
                ),
                patch.object(
                    backend_main,
                    "_sleep_with_history_cancel_check",
                    return_value=True,
                ),
            ):
                backend_main._run_kiwoom_history_sync_job(
                    settings=settings,
                    job_id=int(job["id"]),
                    dates=[date(2026, 1, 1), date(2026, 1, 2)],
                )

            saved = get_history_sync_job(settings, int(job["id"]))
            self.assertEqual(saved["status"], "success")
            self.assertEqual(saved["processed_days"], 2)
            self.assertEqual(saved["total_journal_items_count"], 4)
            self.assertEqual(saved["total_order_executions_count"], 6)
            self.assertEqual(saved["total_needs_review_count"], 6)
            self.assertEqual(saved["last_success_date"], "20260102")
            self.assertIsNone(saved["next_date"])

    def test_history_start_resumes_from_last_successful_date(self):
        import main as backend_main
        from app.database import (
            fail_history_sync_job,
            init_db,
            start_history_sync_job,
            update_history_sync_job_progress,
        )

        class FakeBackgroundTasks:
            def __init__(self):
                self.tasks = []

            def add_task(self, func, *args, **kwargs):
                self.tasks.append((func, args, kwargs))

        with self.temp_database_dir() as temp_dir:
            settings = self.make_settings(temp_dir)
            init_db(settings)
            previous = start_history_sync_job(
                settings=settings,
                broker="KIWOOM",
                start_date="20260101",
                end_date="20260103",
                total_days=3,
            )
            update_history_sync_job_progress(
                settings=settings,
                job_id=int(previous["id"]),
                journal_items_count=1,
                order_executions_count=1,
                needs_review_count=1,
                completed_date="20260101",
                next_date="20260102",
            )
            fail_history_sync_job(settings, int(previous["id"]), "network interrupted")
            background_tasks = FakeBackgroundTasks()

            response = backend_main.start_kiwoom_history_sync(
                background_tasks=background_tasks,
                start_date="2026-01-01",
                end_date="2026-01-03",
                settings=settings,
            )

            self.assertEqual(response.status, "accepted")
            self.assertEqual(response.job["resume_from_job_id"], previous["id"])
            self.assertEqual(response.job["total_days"], 2)
            self.assertEqual(len(background_tasks.tasks), 1)
            _, args, _ = background_tasks.tasks[0]
            self.assertEqual(
                [item.strftime("%Y%m%d") for item in args[2]],
                ["20260102", "20260103"],
            )

    def test_history_start_accepts_one_year_but_rejects_longer_range(self):
        import main as backend_main
        from app.database import init_db
        from fastapi import HTTPException

        class FakeBackgroundTasks:
            def __init__(self):
                self.tasks = []

            def add_task(self, func, *args, **kwargs):
                self.tasks.append((func, args, kwargs))

        with self.temp_database_dir() as temp_dir:
            settings = self.make_settings(temp_dir)
            init_db(settings)
            background_tasks = FakeBackgroundTasks()

            response = backend_main.start_kiwoom_history_sync(
                background_tasks=background_tasks,
                start_date="2024-01-01",
                end_date="2024-12-31",
                settings=settings,
            )

            self.assertEqual(response.status, "accepted")
            self.assertEqual(response.job["total_days"], 366)
            self.assertEqual(len(background_tasks.tasks), 1)
            _, args, _ = background_tasks.tasks[0]
            self.assertEqual(len(args[2]), 366)

            with self.assertRaises(HTTPException) as context:
                backend_main.start_kiwoom_history_sync(
                    background_tasks=FakeBackgroundTasks(),
                    start_date="2024-01-01",
                    end_date="2025-01-01",
                    settings=settings,
                )
            self.assertEqual(context.exception.status_code, 400)
            self.assertIn("최대 1년", context.exception.detail)

    def test_history_cancelled_job_keeps_next_date_for_manual_resume(self):
        from app.database import (
            cancel_history_sync_job,
            finish_cancelled_history_sync_job,
            get_history_sync_job,
            get_resumable_history_sync_job,
            init_db,
            mark_history_sync_job_day_started,
            start_history_sync_job,
        )

        with self.temp_database_dir() as temp_dir:
            settings = self.make_settings(temp_dir)
            init_db(settings)
            job = start_history_sync_job(
                settings=settings,
                broker="KIWOOM",
                start_date="20260101",
                end_date="20260131",
                total_days=31,
            )
            mark_history_sync_job_day_started(settings, int(job["id"]), "20260115")
            cancel_history_sync_job(settings, int(job["id"]))
            finish_cancelled_history_sync_job(settings, int(job["id"]))

            saved = get_history_sync_job(settings, int(job["id"]))
            resumable = get_resumable_history_sync_job(
                settings=settings,
                broker="KIWOOM",
                start_date="20260101",
                end_date="20260131",
            )
            self.assertEqual(saved["status"], "cancelled")
            self.assertIsNone(saved["current_date"])
            self.assertEqual(saved["next_date"], "20260115")
            self.assertEqual(resumable["id"], saved["id"])

    def test_history_retry_records_backoff_checkpoint_without_waiting(self):
        import main as backend_main
        from app.database import get_history_sync_job, init_db, start_history_sync_job
        from app.application_models import JournalSourceTradesResponse
        from app.kiwoom_trade_journal import KiwoomTradeJournalSummary

        with self.temp_database_dir() as temp_dir:
            settings = self.make_settings(temp_dir)
            settings.history_sync_backoff_initial_seconds = 2
            settings.history_sync_backoff_multiplier = 2
            init_db(settings)
            job = start_history_sync_job(
                settings=settings,
                broker="KIWOOM",
                start_date="20260101",
                end_date="20260101",
                total_days=1,
            )
            journal = JournalSourceTradesResponse(
                broker="KIWOOM",
                synced_from=["ka10170", "kt00007"],
                base_date="20260101",
                trade_summary=KiwoomTradeJournalSummary(),
                trade_journal_items_count=1,
                trade_journal_items=[],
                order_executions_count=0,
                order_executions=[],
                needs_review_count=1,
            )

            with (
                patch.object(
                    backend_main,
                    "_fetch_journal_source_trades_for_date",
                    side_effect=[RuntimeError("rate limited"), journal],
                ),
                patch.object(
                    backend_main,
                    "_sleep_with_history_cancel_check",
                    return_value=True,
                ),
            ):
                result = backend_main._fetch_journal_source_trades_for_date_with_retry(
                    settings=settings,
                    job_id=int(job["id"]),
                    target_date="20260101",
                )

            saved = get_history_sync_job(settings, int(job["id"]))
            self.assertIs(result, journal)
            self.assertEqual(saved["retry_count"], 1)
            self.assertEqual(saved["last_backoff_seconds"], 2)
            self.assertIn("재시도 1/", saved["error_message"])
            self.assertEqual(saved["next_date"], "20260101")

    def test_sqlite_pragmas_and_account_storage_do_not_keep_raw_account_label(self):
        from app.database import connect_db, create_manual_transaction, init_db

        with self.temp_database_dir() as temp_dir:
            settings = self.make_settings(temp_dir)
            init_db(settings)
            row = create_manual_transaction(
                settings=settings,
                trade_date="2026-05-22",
                broker="MANUAL",
                account_name="123456789012",
                transaction_type="trade",
                ticker="005930",
                name="삼성전자",
                quantity=1,
                price=70000,
                profit_loss_amount=1000,
            )

            self.assertEqual(row["account_name"], "1234****12")
            self.assertRegex(row["account_hash"], r"^[0-9a-f]{16}$")
            self.assertNotIn("123456789012", str(row))

            with connect_db(settings) as connection:
                journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
                foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]
                busy_timeout = connection.execute("PRAGMA busy_timeout").fetchone()[0]

            self.assertEqual(journal_mode.lower(), "wal")
            self.assertEqual(foreign_keys, 1)
            self.assertGreaterEqual(busy_timeout, settings.sqlite_busy_timeout_ms)

    def test_kiwoom_token_cache_reuses_valid_token_without_network(self):
        from app.database import init_db, upsert_brokerage_token
        from app.kiwoom_auth import KiwoomAuthClient

        with self.temp_database_dir() as temp_dir:
            settings = self.make_settings(temp_dir)
            init_db(settings)
            upsert_brokerage_token(
                settings=settings,
                broker="KIWOOM",
                environment="mock",
                token_type="Bearer",
                access_token="cached-token-value",
                refresh_token="refresh-token-value",
                expires_dt="20991231235959",
                expires_at="2099-12-31T23:59:59",
            )

            with patch("app.kiwoom_auth.httpx.post") as post:
                result = KiwoomAuthClient(settings).issue_access_token()

            post.assert_not_called()
            self.assertEqual(result.token, "cached-token-value")
            self.assertEqual(result.refresh_token, "refresh-token-value")

    def test_manual_trade_entered_before_kiwoom_sync_is_marked_duplicate_and_excluded(self):
        from app.application_models import JournalSourceTradesResponse, PortfolioResponse
        from app.database import (
            count_journal_drafts,
            create_manual_transaction,
            create_or_update_journal_entry,
            finish_sync_run,
            get_journal_analytics,
            init_db,
            list_journal_drafts,
            list_manual_transactions,
            start_sync_run,
        )
        from app.kiwoom_balance import KiwoomBalanceSummary
        from app.kiwoom_trade_journal import KiwoomTradeJournalItem, KiwoomTradeJournalSummary

        with self.temp_database_dir() as temp_dir:
            settings = self.make_settings(temp_dir)
            init_db(settings)
            create_manual_transaction(
                settings=settings,
                trade_date="2026-01-15",
                broker="MANUAL",
                account_name="테스트계좌",
                transaction_type="trade",
                ticker="005930",
                name="삼성전자",
                quantity=10,
                price=70000,
                profit_loss_amount=5000,
                currency="KRW",
            )
            sync_run_id = start_sync_run(settings, broker="KIWOOM")
            portfolio = PortfolioResponse(
                broker="KIWOOM",
                synced_from="mock",
                summary=KiwoomBalanceSummary(),
                holdings_count=0,
                holdings=[],
            )
            journal = JournalSourceTradesResponse(
                broker="KIWOOM",
                synced_from=["ka10170"],
                base_date="20260115",
                trade_summary=KiwoomTradeJournalSummary(),
                trade_journal_items_count=1,
                trade_journal_items=[
                    KiwoomTradeJournalItem(
                        ticker="005930",
                        name="삼성전자",
                        buy_average_price=70000,
                        buy_quantity=10,
                        profit_loss_amount=5000,
                    )
                ],
                order_executions_count=0,
                order_executions=[],
                needs_review_count=1,
            )
            finish_sync_run(settings, sync_run_id, portfolio, journal)

            manual = list_manual_transactions(settings)[0]
            self.assertEqual(manual["dedup_status"], "duplicate_kiwoom")
            self.assertIn("키움 원천 거래", manual["dedup_reason"])

            draft = list_journal_drafts(settings)[0]
            create_or_update_journal_entry(
                settings=settings,
                draft_id=int(draft["id"]),
                strategy_name="ORB",
                setup_tags=["breakout"],
                entry_reason="키움 원천 거래 복기",
                exit_reason="",
                rule_followed=True,
                good_points="",
                improvement_points="",
                memo="",
                manual_profit_loss_amount=5000,
            )
            analytics = get_journal_analytics(settings)

            self.assertEqual(analytics["completed_drafts"], 1)
            self.assertEqual(analytics["duplicate_manual_transactions_count"], 1)
            self.assertEqual(analytics["manual_transactions_count"], 1)
            self.assertEqual(analytics["total_entries"], 1)
            self.assertEqual(analytics["realized_profit_loss_total"], 5000)

            self.assertEqual(count_journal_drafts(settings), 0)
            self.assertEqual(list_journal_drafts(settings), [])
            self.assertEqual(count_journal_drafts(settings, include_completed=True), 1)
            self.assertEqual(
                list_journal_drafts(settings, include_completed=True)[0]["draft_status"],
                "completed",
            )


    def test_completed_trade_journal_links_matching_order_execution_draft(self):
        from app.application_models import JournalSourceTradesResponse, PortfolioResponse
        from app.database import (
            create_or_update_journal_entry,
            finish_sync_run,
            get_journal_analytics,
            init_db,
            list_journal_drafts,
            list_journal_entries,
            start_sync_run,
        )
        from app.kiwoom_balance import KiwoomBalanceSummary
        from app.kiwoom_order_execution import KiwoomOrderExecution
        from app.kiwoom_trade_journal import KiwoomTradeJournalItem, KiwoomTradeJournalSummary

        with self.temp_database_dir() as temp_dir:
            settings = self.make_settings(temp_dir)
            init_db(settings)
            sync_run_id = start_sync_run(settings, broker="KIWOOM")
            portfolio = PortfolioResponse(
                broker="KIWOOM",
                synced_from="mock",
                summary=KiwoomBalanceSummary(),
                holdings_count=0,
                holdings=[],
            )
            journal = JournalSourceTradesResponse(
                broker="KIWOOM",
                synced_from=["ka10170", "kt00007"],
                base_date="20260115",
                trade_summary=KiwoomTradeJournalSummary(),
                trade_journal_items_count=1,
                trade_journal_items=[
                    KiwoomTradeJournalItem(
                        ticker="005930",
                        name="삼성전자",
                        buy_average_price=70000,
                        buy_quantity=10,
                        sell_average_price=71000,
                        sell_quantity=10,
                        buy_amount=700000,
                        sell_amount=710000,
                        profit_loss_amount=5000,
                        profit_rate=0.7,
                    )
                ],
                order_executions_count=1,
                order_executions=[
                    KiwoomOrderExecution(
                        order_no="100001",
                        ticker="005930",
                        name="삼성전자",
                        trade_side_name="매도",
                        order_status="체결",
                        order_time="090000",
                        confirm_time="090100",
                        order_price=71000,
                        order_quantity=10,
                        filled_price=71000,
                        filled_quantity=10,
                        remaining_quantity=0,
                    )
                ],
                needs_review_count=2,
            )
            finish_sync_run(settings, sync_run_id, portfolio, journal)

            pending = list_journal_drafts(settings)
            self.assertEqual(len(pending), 2)
            trade_draft = next(
                item for item in pending if item["source_type"] == "trade_journal"
            )

            entry = create_or_update_journal_entry(
                settings=settings,
                draft_id=int(trade_draft["id"]),
                strategy_name="ORB",
                setup_tags=["breakout"],
                entry_reason="키움 원천 거래 복기",
                exit_reason="",
                rule_followed=True,
                good_points="",
                improvement_points="",
                memo="",
                manual_profit_loss_amount=5000,
            )

            self.assertEqual(list_journal_drafts(settings), [])
            all_drafts = list_journal_drafts(settings, include_completed=True)
            statuses = {item["source_type"]: item["draft_status"] for item in all_drafts}
            self.assertEqual(statuses["trade_journal"], "completed")
            self.assertEqual(statuses["order_execution"], "linked")
            self.assertEqual(entry["source_payload"]["related_order_executions_count"], 1)
            self.assertEqual(
                entry["source_payload"]["related_order_executions"][0]["order_no"],
                "100001",
            )

            entries = list_journal_entries(settings)
            self.assertEqual(len(entries), 1)
            self.assertEqual(
                entries[0]["source_payload"]["related_order_executions_count"],
                1,
            )
            analytics = get_journal_analytics(settings)
            self.assertEqual(analytics["total_entries"], 1)
            self.assertEqual(analytics["pending_drafts"], 0)
            self.assertEqual(analytics["completed_drafts"], 1)



class KiwoomResearchOsIntegrationTests(unittest.TestCase):
    def test_kiwoom_interest_group_status_normalizes_groups_and_details(self):
        from research_os.kiwoom_interest import (
            build_kiwoom_interest_groups_status,
            build_kiwoom_interest_sync_preview,
        )
        from research_os.settings import Settings

        settings = Settings(
            brokerage_api_key="fake-key",
            brokerage_api_secret="fake-secret",
            kiwoom_interest_endpoint_path="/api/dostk/watchlist",
        )

        with (
            patch(
                "research_os.kiwoom_interest.KiwoomAuthClient.issue_access_token",
                return_value=SimpleNamespace(token="token"),
            ),
            patch(
                "research_os.kiwoom_interest.httpx.post",
                side_effect=[
                    SimpleNamespace(
                        raise_for_status=lambda: None,
                        json=lambda: {
                            "nofi": [
                                {"gcod": "001", "name": "AI 반도체"},
                                {"gcod": "002", "name": "방산"},
                            ]
                        },
                    ),
                    SimpleNamespace(
                        raise_for_status=lambda: None,
                        json=lambda: {
                            "nofj": [
                                {"cod2": "0117V0"},
                                {"cod2": "000660"},
                                {"cod2": "042660"},
                            ]
                        },
                    ),
                ],
            ) as post,
        ):
            result = build_kiwoom_interest_groups_status(settings, include_details=True, max_groups=1)

        self.assertEqual(result["api_ids"], ["ka01300", "ka01301"])
        self.assertEqual(result["endpoint_path"], "/api/dostk/watchlist")
        self.assertEqual(result["group_count"], 2)
        self.assertEqual(result["groups"][0]["group_id"], "001")
        self.assertEqual(result["details"][0]["item_count"], 3)
        self.assertEqual(result["details"][0]["items"][0]["ticker"], "0117V0")
        self.assertEqual(post.call_args_list[0].kwargs["headers"]["api-id"], "ka01300")
        self.assertEqual(post.call_args_list[1].kwargs["headers"]["api-id"], "ka01301")
        self.assertEqual(post.call_args_list[1].kwargs["json"], {"arn_grp_id": "001"})

        def fake_resolver(ticker):
            return SimpleNamespace(
                company_name={
                    "000660": "SK하이닉스",
                    "042660": "한화오션",
                }.get(ticker, "")
            )

        preview = build_kiwoom_interest_sync_preview(
            result,
            {"tickers": [{"ticker": "000660", "company_name": "SK하이닉스"}]},
            ticker_resolver=fake_resolver,
        )

        self.assertEqual(preview["write_mode"], "preview_only")
        self.assertEqual(preview["already_tracked_count"], 1)
        self.assertEqual(preview["add_candidate_count"], 1)
        self.assertEqual(preview["needs_review_count"], 1)
        self.assertEqual(preview["candidates"][0]["action"], "needs_review")
        self.assertFalse(preview["candidates"][0]["sync_eligible"])
        self.assertEqual(preview["candidates"][1]["action"], "already_tracked")
        self.assertEqual(preview["candidates"][1]["company_name"], "SK하이닉스")
        self.assertEqual(preview["candidates"][2]["action"], "add_candidate")
        self.assertEqual(preview["candidates"][2]["company_name"], "한화오션")

    def test_kiwoom_interest_sync_candidates_dry_run_and_save(self):
        import research_os_main as main
        from research_os.models import KiwoomInterestSyncCandidate, KiwoomInterestSyncRequest, TickerVerificationResponse
        from research_os.settings import Settings

        settings = Settings()
        request = KiwoomInterestSyncRequest(
            candidates=[
                KiwoomInterestSyncCandidate(ticker="A000660", company_name="SK하이닉스", group_name="AI 반도체"),
                KiwoomInterestSyncCandidate(ticker="0117V0", company_name="비표준", group_name="매수종목"),
                KiwoomInterestSyncCandidate(ticker="A042660", company_name="한화오션", group_name="방산"),
                KiwoomInterestSyncCandidate(ticker="042660", company_name="한화오션", group_name="방산"),
                KiwoomInterestSyncCandidate(ticker="", company_name="티커 없음", group_name="기타"),
            ],
            dry_run=True,
        )
        interest_payload = {
            "tickers": [{"ticker": "000660", "priority": "high", "tags": ["existing"]}],
            "sectors": [],
        }

        def fake_verify(symbol, _settings):
            return (
                main.normalize_ticker(symbol),
                TickerVerificationResponse(
                    requested_symbol=symbol,
                    official_symbol=main.normalize_ticker(symbol),
                    company_name="한화오션" if main.normalize_ticker(symbol) == "042660" else "SK하이닉스",
                    exchange="KRX",
                    country="KR",
                    verified=True,
                    verification_source="test",
                    message="verified",
                ),
            )

        with (
            patch.object(main, "read_interest_list", return_value=interest_payload),
            patch.object(main, "local_interest_verification_response", side_effect=fake_verify),
            patch.object(main, "write_json_store") as write_json,
            patch.object(main, "append_kiwoom_interest_sync_history") as append_history,
        ):
            dry_run = main.sync_kiwoom_interest_candidates(request, settings)

        write_json.assert_not_called()
        append_history.assert_called_once()
        self.assertTrue(append_history.call_args.kwargs["summary"]["dry_run"])
        self.assertEqual(dry_run["write_mode"], "preview_only")
        self.assertEqual(dry_run["prepared_count"], 1)
        self.assertEqual(dry_run["skipped_count"], 4)
        self.assertEqual(dry_run["prepared_tickers"][0]["ticker"], "042660")

        request.dry_run = False
        with (
            patch.object(main, "read_interest_list", return_value=interest_payload),
            patch.object(main, "local_interest_verification_response", side_effect=fake_verify),
            patch.object(main, "write_json_store") as write_json,
            patch.object(main, "append_kiwoom_interest_sync_history") as append_history,
        ):
            saved = main.sync_kiwoom_interest_candidates(request, settings)

        self.assertEqual(saved["write_mode"], "saved")
        self.assertEqual(saved["prepared_count"], 1)
        write_json.assert_called_once()
        saved_payload = write_json.call_args.args[1]
        self.assertEqual([item["ticker"] for item in saved_payload["tickers"]], ["000660", "042660"])
        self.assertIn("kiwoom_interest_sync", saved_payload["tickers"][1]["tags"])
        append_history.assert_called_once()
        self.assertFalse(append_history.call_args.kwargs["summary"]["dry_run"])

    def test_kiwoom_interest_sync_history_records_newest_valid_rows(self):
        from research_os.kiwoom_interest import (
            append_kiwoom_interest_sync_history,
            read_kiwoom_interest_sync_history,
        )
        from research_os.settings import Settings

        with TemporaryDirectory() as temp_dir:
            settings = Settings(research_vault_dir=temp_dir)
            append_kiwoom_interest_sync_history(
                settings,
                summary={
                    "module": "kiwoom_interest_sync",
                    "dry_run": True,
                    "write_mode": "preview_only",
                    "requested_count": 2,
                    "prepared_count": 1,
                    "skipped_count": 1,
                    "interest_ticker_count": 3,
                    "prepared_tickers": [{"ticker": "042660"}],
                    "skipped": [{"ticker": "000660", "reason": "duplicate"}],
                    "next_action": "검토 필요",
                },
            )
            append_kiwoom_interest_sync_history(
                settings,
                summary={
                    "module": "kiwoom_interest_sync",
                    "dry_run": False,
                    "write_mode": "saved",
                    "requested_count": 1,
                    "prepared_count": 1,
                    "skipped_count": 0,
                    "interest_ticker_count": 4,
                    "prepared_tickers": [{"ticker": "042660"}],
                    "next_action": "저장 완료",
                },
            )

            history = read_kiwoom_interest_sync_history(settings, limit=5)

        self.assertEqual([item["mode"] for item in history], ["apply", "dry_run"])
        self.assertEqual(history[0]["write_mode"], "saved")
        self.assertEqual(history[0]["prepared_tickers"][0]["ticker"], "042660")
        self.assertEqual(history[1]["skipped"][0]["reason"], "duplicate")

    def test_research_os_kiwoom_token_cache_reuses_valid_token_without_network(self):
        from research_os.kiwoom_auth import KiwoomAuthClient
        from research_os.settings import Settings

        with TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "kiwoom_access_token.json"
            cache_path.write_text(
                json.dumps(
                    {
                        "broker": "KIWOOM",
                        "environment": "mock",
                        "token_type": "Bearer",
                        "token": "cached-research-os-token",
                        "expires_dt": "20991231235959",
                    }
                ),
                encoding="utf-8",
            )
            settings = Settings(
                brokerage_api_key="fake-key",
                brokerage_api_secret="fake-secret",
                kiwoom_use_mock=True,
                kiwoom_token_cache_file=str(cache_path),
            )

            with patch("research_os.kiwoom_auth.httpx.post") as post:
                result = KiwoomAuthClient(settings).issue_access_token()

            post.assert_not_called()
            self.assertEqual(result.token, "cached-research-os-token")

    def test_research_os_kiwoom_domestic_balance_reads_continuation_pages(self):
        import research_os_main as main
        from research_os.settings import Settings

        class FakeResponse:
            def __init__(self, payload: dict, headers: dict):
                self._payload = payload
                self.headers = headers

            def raise_for_status(self):
                return None

            def json(self):
                return self._payload

        responses = [
            FakeResponse(
                {
                    "tot_pur_amt": "1,000",
                    "tot_evlt_amt": "1,200",
                    "acnt_evlt_remn_indv_tot": [
                        {"stk_cd": "A003230", "stk_nm": "삼양식품", "rmnd_qty": "1"}
                    ],
                },
                {"cont-yn": "Y", "next-key": "NEXT1", "api-id": "kt00018"},
            ),
            FakeResponse(
                {
                    "tot_pur_amt": "1,000",
                    "tot_evlt_amt": "1,200",
                    "acnt_evlt_remn_indv_tot": [
                        {"stk_cd": "A033500", "stk_nm": "동성화인텍", "rmnd_qty": "2"}
                    ],
                },
                {"cont-yn": "N", "next-key": "", "api-id": "kt00018"},
            ),
        ]
        settings = Settings(
            brokerage_api_key="fake-key",
            brokerage_api_secret="fake-secret",
            kiwoom_balance_max_pages=5,
            kiwoom_page_delay_seconds=0,
        )

        with (
            patch.object(main.KiwoomAuthClient, "issue_access_token", return_value=SimpleNamespace(token="token")),
            patch.object(main.httpx, "post", side_effect=responses) as post,
        ):
            result = main.fetch_kiwoom_domestic_balance(settings)

        self.assertEqual(post.call_count, 2)
        first_headers = post.call_args_list[0].kwargs["headers"]
        second_headers = post.call_args_list[1].kwargs["headers"]
        self.assertEqual(first_headers["cont-yn"], "N")
        self.assertEqual(second_headers["cont-yn"], "Y")
        self.assertEqual(second_headers["next-key"], "NEXT1")
        self.assertEqual(result["pages_read"], 2)
        self.assertFalse(result["has_next"])
        self.assertEqual([item["ticker"] for item in result["holdings"]], ["003230", "033500"])


class NpsDomesticEquityAllocationMonitorTests(unittest.TestCase):
    def test_classifies_domestic_equity_and_excludes_overseas_exposure(self):
        from research_os.models import PortfolioHolding
        from research_os.nps_allocation_monitor import classify_domestic_equity_holding

        samsung = PortfolioHolding(ticker="005930", name="삼성전자", market_value=140, currency="KRW")
        korea_etf = PortfolioHolding(ticker="0117V0", name="TIGER 코리아AI전력기기TOP3플러스 ETF", market_value=50, currency="KRW")
        us_etf = PortfolioHolding(ticker="360750", name="TIGER 미국S&P500", market_value=200, currency="KRW")
        us_stock = PortfolioHolding(ticker="PL", name="Planet Labs PBC", market_value=300, currency="USD")
        industrial_stock = PortfolioHolding(
            ticker="033500",
            name="동성화인텍",
            market_value=100,
            currency="KRW",
            sector="Industrials",
        )

        self.assertTrue(classify_domestic_equity_holding(samsung).is_domestic_equity)
        self.assertTrue(classify_domestic_equity_holding(korea_etf).is_domestic_equity)
        self.assertTrue(classify_domestic_equity_holding(industrial_stock).is_domestic_equity)
        self.assertFalse(classify_domestic_equity_holding(us_etf).is_domestic_equity)
        self.assertEqual(classify_domestic_equity_holding(us_etf).bucket, "domestic_listed_overseas_exposure")
        self.assertFalse(classify_domestic_equity_holding(us_stock).is_domestic_equity)

    def test_build_monitor_calculates_nps_14_percent_gap(self):
        from research_os.models import PortfolioHolding
        from research_os.nps_allocation_monitor import build_nps_domestic_equity_allocation_monitor

        monitor = build_nps_domestic_equity_allocation_monitor(
            portfolio_name="테스트",
            holdings=[
                PortfolioHolding(ticker="005930", name="삼성전자", market_value=120, currency="KRW"),
                PortfolioHolding(ticker="360750", name="TIGER 미국S&P500", market_value=280, currency="KRW"),
                PortfolioHolding(ticker="PL", name="Planet Labs PBC", market_value=600, currency="USD"),
            ],
            portfolio_value=1000,
            target_weight=0.14,
            warn_tolerance=0.01,
            checked_at="2026-06-23T12:00:00+09:00",
        )

        self.assertEqual(monitor["status"], "below_target")
        self.assertEqual(monitor["current_domestic_equity_weight"], 0.12)
        self.assertEqual(monitor["gap_pct_points"], 2.0)
        self.assertEqual(monitor["gap_value"], 20.0)
        self.assertEqual(monitor["included_domestic_equity_count"], 1)
        self.assertEqual(monitor["excluded_count"], 2)
        self.assertEqual(monitor["top_excluded_holdings"][0]["ticker"], "PL")

    def test_rebalance_plan_builds_reduction_scenarios(self):
        from research_os.models import PortfolioHolding
        from research_os.nps_allocation_monitor import (
            build_nps_domestic_equity_allocation_monitor,
            build_nps_domestic_equity_rebalance_plan,
        )

        monitor = build_nps_domestic_equity_allocation_monitor(
            portfolio_name="테스트",
            holdings=[
                PortfolioHolding(ticker="003230", name="삼양식품", market_value=500, currency="KRW"),
                PortfolioHolding(ticker="395160", name="KODEX AI반도체 ETF", market_value=300, currency="KRW"),
                PortfolioHolding(ticker="360750", name="TIGER 미국S&P500", market_value=200, currency="KRW"),
            ],
            portfolio_value=1000,
            target_weight=0.14,
            checked_at="2026-06-24T12:00:00+09:00",
        )

        plan = build_nps_domestic_equity_rebalance_plan(
            monitor,
            evidence_by_ticker={
                "395160": {
                    "latest_recommendation": {
                        "rank": 2,
                        "score": 111,
                        "market": "KR",
                        "recommendation_date": "2026-06-24",
                    },
                    "research_document_count": 6,
                    "nps_signal": {"domestic_match_found": False, "large_holding_event_count": 0},
                }
            },
        )

        self.assertEqual(plan["module"], "nps_domestic_equity_rebalance_plan")
        self.assertEqual(plan["status"], "needs_reduction")
        self.assertEqual(plan["target_domestic_equity_value"], 140.0)
        self.assertEqual(plan["reduction_needed_value"], 660.0)
        self.assertEqual(len(plan["scenarios"]), 3)
        self.assertEqual(plan["candidates"]["review"][0]["ticker"], "395160")
        self.assertEqual(plan["candidates"]["review"][0]["evidence"]["research_document_count"], 6)
        self.assertTrue(plan["candidates"]["review"][0]["evidence"]["latest_recommendation"])
        self.assertEqual(plan["scenarios"][0]["title"], "ETF/테마 우선 축소")
        self.assertGreater(plan["scenarios"][0]["suggested_reduction_value"], 0)


class InvestmentInsightHubTests(unittest.TestCase):
    def test_build_investment_insight_hub_integrates_policy_filings_news_and_sentiment(self):
        from datetime import date

        from research_os.investment_insight_hub import build_investment_insight_hub
        from research_os.models import PortfolioHolding

        payload = build_investment_insight_hub(
            portfolio_name="가족 합산",
            holdings=[
                PortfolioHolding(
                    ticker="003230",
                    name="삼양식품",
                    market_value=1200000,
                    unrealized_return=18.5,
                    price_source="stored",
                    price_checked_at="2026-06-24T09:00:00+09:00",
                    sector="음식료",
                )
            ],
            market_journal={
                "entries": [
                    {
                        "market": "KR",
                        "session_date": "2026-06-24",
                        "sentiment": "긍정",
                        "risk_level": "보통",
                        "regime": "risk-on",
                        "tags": ["수출", "음식료"],
                        "summary": "수출주 심리 개선",
                    }
                ]
            },
            news_inbox={
                "items": [
                    {
                        "created_at": "2026-06-24T10:00:00+09:00",
                        "title": "라면 수출 규제 완화 정책 논의",
                        "scope": "POLICY",
                        "summary": "삼양식품 수출 정책 수혜 가능성",
                        "tags": ["policy", "regulation"],
                    }
                ]
            },
            dart_cache={
                "entries": {
                    "a": {
                        "ticker": "003230",
                        "importance": "높음",
                        "tags": ["earnings"],
                        "filing": {
                            "stock_code": "003230",
                            "corp_name": "삼양식품",
                            "receipt_date": "2026-06-24",
                            "report_name": "분기보고서",
                        },
                        "action": "실적 모델 업데이트",
                    }
                }
            },
            recent_weekly={"counts": {"filing": 1, "report": 2}},
            generated_at="2026-06-24T12:00:00+09:00",
            today=date(2026, 6, 24),
        )

        self.assertEqual(payload["module"], "investment_insight_hub")
        self.assertEqual(payload["coverage"]["market_journal_items"], 1)
        self.assertEqual(payload["coverage"]["policy_law_items"], 1)
        self.assertEqual(payload["coverage"]["official_filing_items"], 1)
        self.assertGreaterEqual(len(payload["insights"]), 4)
        self.assertTrue(any(item["source_family"] == "policy_law_news" for item in payload["insights"]))
        self.assertTrue(any(item["source_family"] == "official_filings" for item in payload["insights"]))


if __name__ == "__main__":
    unittest.main()
