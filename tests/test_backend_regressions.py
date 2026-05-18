import sys
import unittest
import copy
from datetime import date
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
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


class WebCaptureRenderingTests(unittest.TestCase):
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


class FileExtractionTests(unittest.TestCase):
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


class ResearchMemoryPolicyTests(unittest.TestCase):
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

    def test_asset_hash_rewrite_reaches_fixed_point(self):
        tool = load_console_hash_tool()
        project_root = PROJECT_ROOT

        pending = tool.changed_update_paths(project_root)

        self.assertEqual(pending, [])


class DartFilingWatchTests(unittest.TestCase):
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
        self.assertIn(
            {"ticker": "PL", "source": "portfolio", "reason": "non_kr_ticker"},
            universe["excluded_tickers"],
        )
        self.assertIn(
            {"ticker": "AAPL", "source": "interest", "reason": "non_kr_ticker"},
            universe["excluded_tickers"],
        )

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
        self.assertFalse(result["daily_check"]["due"])
        self.assertEqual(result["saved_count"], 2)


class PortfolioPerformanceTests(unittest.TestCase):
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
                    current_price=120,
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

        def fake_history_rows(ticker, _settings):
            if ticker == "003230":
                return "003230", history_rows, {"cache_hit": True}
            raise ValueError("국내 가격 히스토리 지원 대상이 아닙니다.")

        with (
            patch.object(main, "read_portfolio_store", return_value=store),
            patch.object(main, "sort_and_weight_portfolio", side_effect=lambda p, *_args, **_kwargs: p),
            patch.object(main, "portfolio_history_rows_for_ticker", side_effect=fake_history_rows),
            patch.object(main, "current_storage_date", return_value=date(2026, 5, 18)),
            patch.object(main, "current_storage_timestamp", return_value="2026-05-18T09:00:00+09:00"),
        ):
            result = main.build_portfolio_performance("테스트", settings)

        self.assertEqual(result["calculation_mode"], "recomputed_on_request")
        self.assertFalse(result["result_cache"]["enabled"])
        self.assertTrue(result["price_history_cache"]["enabled"])
        self.assertEqual(result["price_history_cache"]["hit_count"], 1)
        self.assertEqual(result["unsupported_history_count"], 1)
        self.assertEqual(result["unsupported_history_market_value"], 14000)
        self.assertEqual(result["skipped_holdings"][0]["category"], "overseas_or_unsupported_history")
        self.assertIn("네이버 국내 종목 코드", " ".join(result["data_limitations"]))
        self.assertEqual(result["periods"][0]["net_profit"], 200)
        self.assertEqual(result["periods"][0]["return_rate"], 0.2)


if __name__ == "__main__":
    unittest.main()
