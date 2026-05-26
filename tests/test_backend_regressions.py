import sys
import unittest
import copy
import json
from datetime import date
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from tempfile import TemporaryDirectory
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


class BackendModuleBoundaryTests(unittest.TestCase):
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
            patch.object(main, "write_json_store"), \
            patch.object(main, "save_market_close_review", return_value=response) as save_review:
            result = main.refresh_naver_market_close_journal(settings, force=False)

        request = save_review.call_args.args[0]
        self.assertEqual(request.source_origin, "naver_research_auto")
        self.assertEqual(request.source_provider, "naver_finance_research")
        self.assertEqual(request.source_title, "국내 주식 마감 시황")
        self.assertEqual(result["entry"]["source_origin"], "naver_research_auto")

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

        broken = "title=êµ­ë´ ì£¼ì ë§ê° ìí©"
        repaired = main.repair_mojibake_log_line(broken)

        self.assertIn("국내 주식 마감 시황", repaired)

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


class FileExtractionTests(unittest.TestCase):
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


class ResearchMemoryPolicyTests(unittest.TestCase):
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

            candidates = main.dossier_refresh_candidates_from_duplicate_review(
                Settings(research_vault_dir=str(vault_dir)),
                limit=5,
            )

        self.assertEqual([item["ticker"] for item in candidates], ["018260"])

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


class DartFilingWatchTests(unittest.TestCase):
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


class CustomsTradeDataQualityTests(unittest.TestCase):
    def test_service_status_only_customs_rows_are_not_counted_as_trade_data(self):
        from research_os.data_providers import fetch_customs_trade_rows
        from research_os.settings import Settings

        settings = Settings(
            customs_trade_enabled=True,
            customs_trade_api_key="test-key",
            customs_trade_api_url="https://example.test/customs",
            customs_trade_max_rows=20,
        )

        with patch("research_os.data_providers.KoreaCustomsTradeClient.fetch_item_trade_rows") as fetch_mock:
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

    def test_customs_total_trend_provider_status_is_separated_from_item_trade_api(self):
        from research_os.data_providers import get_analysis_data_provider
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
        from research_os.data_providers import fetch_customs_total_trend_status
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

        with patch("research_os.data_providers.httpx.Client", new=FakeClient):
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

        with patch.object(main, "portfolio_sync_history_path", return_value=history_path):
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
        self.assertIn("가격 갱신 불러오기", result["price_refresh_guidance"])
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


if __name__ == "__main__":
    unittest.main()
