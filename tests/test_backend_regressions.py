import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


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
