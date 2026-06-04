import unittest
import sys
from datetime import date, datetime
from tempfile import TemporaryDirectory
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.daily_recommendations import (
    daily_recommendation_state_path,
    parse_daily_recommendations_time,
    summarize_daily_recommendation_store,
    should_run_daily_recommendations,
    update_recommendation_tracking,
    upsert_daily_recommendations,
    write_json_payload,
)
from research_os.settings import Settings
from research_os.storage_quality import storage_quality_entry_needs_body


class DailyRecommendationsTests(unittest.TestCase):
    def test_daily_recommendation_schedule_uses_state_file(self):
        with TemporaryDirectory() as temp_dir:
            settings = Settings(
                research_vault_dir=str(Path(temp_dir) / "research_vault"),
                daily_recommendations_time="09:30",
            )

            self.assertEqual(parse_daily_recommendations_time(settings), (9, 30))
            self.assertFalse(
                should_run_daily_recommendations(
                    settings,
                    now=datetime(2026, 5, 31, 9, 29),
                )
            )
            self.assertTrue(
                should_run_daily_recommendations(
                    settings,
                    now=datetime(2026, 5, 31, 9, 30),
                )
            )
            write_json_payload(
                daily_recommendation_state_path(settings),
                {"last_run_date": "2026-05-31"},
            )
            self.assertFalse(
                should_run_daily_recommendations(
                    settings,
                    now=datetime(2026, 5, 31, 10, 0),
                )
            )

    def test_daily_recommendation_schedule_defaults_invalid_time(self):
        settings = Settings(daily_recommendations_time="bad-value")
        self.assertEqual(parse_daily_recommendations_time(settings), (9, 0))

    def test_daily_recommendations_save_top_three_and_track_milestones(self):
        with TemporaryDirectory() as temp_dir:
            settings = Settings(research_vault_dir=str(Path(temp_dir) / "research_vault"))
            candidates = [
                {
                    "ticker": "003230",
                    "company_name": "삼양식품",
                    "score": 88,
                    "baseline_price": 100000,
                    "baseline_price_source": "test",
                    "currency": "KRW",
                    "score_components": [{"label": "목표가", "points": 35}],
                    "score_explanation": {
                        "positive_points": 35,
                        "penalty_points": 0,
                        "final_score": 88,
                        "component_weights": [{"label": "목표가", "points": 35, "weight_pct": 100.0}],
                    },
                    "score_penalties": [],
                    "quality_flags": [],
                    "portfolio_risk_connection": {
                        "linked": True,
                        "priority": "high",
                        "message": "보유 비중과 함께 확인",
                    },
                    "reasons": ["목표가 상승여력"],
                    "evidence_sources": ["저장 리포트 3건"],
                },
                {
                    "ticker": "033500",
                    "company_name": "동성화인텍",
                    "score": 77,
                    "baseline_price": 20000,
                    "baseline_price_source": "test",
                    "currency": "KRW",
                    "reasons": ["공시 최신"],
                    "evidence_sources": ["DART"],
                },
                {
                    "ticker": "PL",
                    "company_name": "Planet Labs PBC",
                    "score": 71,
                    "baseline_price": 40,
                    "baseline_price_source": "test",
                    "currency": "USD",
                    "overseas_tracking": {
                        "currency": "USD",
                        "needs_fx_conversion": True,
                        "fx_note": "환율 확인",
                    },
                    "reasons": ["RAG 문서 연결"],
                    "evidence_sources": ["Dossier"],
                },
                {
                    "ticker": "JOBY",
                    "company_name": "Joby Aviation",
                    "score": 60,
                    "baseline_price": 10,
                    "baseline_price_source": "test",
                },
            ]

            saved = upsert_daily_recommendations(
                settings,
                candidates=candidates,
                recommendation_date=date(2026, 5, 1),
                generated_at="2026-05-01T09:00:00+09:00",
            )
            tracking = update_recommendation_tracking(
                settings,
                as_of=date(2026, 5, 8),
                checked_at="2026-05-08T09:00:00+09:00",
                price_lookup=lambda ticker: (110000, "test") if ticker == "003230" else (None, "test"),
            )
            status = summarize_daily_recommendation_store(settings)

        self.assertEqual(saved["saved_count"], 3)
        self.assertEqual(tracking["due_count"], 3)
        self.assertEqual(status["record_count"], 3)
        first = status["latest_records"][0]
        self.assertEqual(first["company_name"], "삼양식품")
        self.assertEqual(first["score_components"][0]["label"], "목표가")
        self.assertEqual(first["score_explanation"]["component_weights"][0]["weight_pct"], 100.0)
        self.assertTrue(first["portfolio_risk_connection"]["linked"])
        overseas = [item for item in status["latest_records"] if item["ticker"] == "PL"][0]
        self.assertTrue(overseas["overseas_tracking"]["needs_fx_conversion"])
        week = first["tracking_milestones"][0]
        self.assertEqual(week["status"], "complete")
        self.assertEqual(week["price_change_pct"], 0.1)
        self.assertEqual(status["performance_summary"]["complete_count"], 1)
        self.assertEqual(status["performance_summary"]["pending_count"], 12)
        self.assertEqual(status["performance_summary"]["price_unavailable_count"], 2)
        self.assertEqual(status["performance_summary"]["positive_count"], 1)

    def test_copyright_safe_url_only_is_not_body_missing_warning(self):
        import research_os_main as main

        policy_item = {
            "source_url": "https://example.com/news",
            "tags": ["copyright_safe_metadata", "url_only", "url_text_unavailable"],
            "capture_quality": {"status": "보강 필요"},
            "promoted": True,
        }
        self.assertFalse(
            storage_quality_entry_needs_body(
                policy_item
            )
        )
        self.assertNotIn("needs_body", main.news_filter_key(policy_item))
        self.assertNotIn("quality_issue", main.news_filter_key(policy_item))
        self.assertTrue(
            storage_quality_entry_needs_body(
                {
                    "tags": ["url_only", "url_text_unavailable"],
                    "capture_quality": {"status": "보강 필요"},
                }
            )
        )


    def test_daily_recommendation_storage_quality_records_missing_dashboard_evidence(self):
        import research_os_main as main

        candidate = {
            "ticker": "033500",
            "company_name": "동성화인텍",
            "score": 10,
            "score_components": [],
            "score_penalties": [],
            "quality_flags": [],
            "evidence_sources": [],
        }

        main._apply_daily_recommendation_storage_quality(candidate, None)

        self.assertIn("저장 품질 대시보드 연결 없음", candidate["quality_flags"])
        self.assertTrue(candidate["evidence_sources"][0].startswith("저장 품질:"))
        self.assertIn("활용 가능 0건", candidate["evidence_sources"][0])
        self.assertIn("검증된 활성 저장자료 부족", candidate["quality_flags"])


    def test_daily_recommendation_storage_quality_penalizes_weak_evidence(self):
        import research_os_main as main

        quality = main._daily_recommendation_manifest_quality_by_ticker(
            [
                {"ticker": "003230", "summary": "정상 리포트", "date": "2026-05-29"},
                {
                    "ticker": "003230",
                    "duplicate_check": {"is_duplicate_suspected": True},
                    "date": "2026-05-29",
                },
                {
                    "ticker": "003230",
                    "tags": ["url_text_unavailable", "needs_body_copy"],
                    "capture_quality": {"status": "보강 필요"},
                },
                {
                    "ticker": "003230",
                    "attachment": {"ocr_required": True},
                },
                {
                    "ticker": "003230",
                    "status": "archived",
                },
            ]
        )["003230"]
        candidate = {
            "ticker": "003230",
            "company_name": "삼양식품",
            "score": 10,
            "score_components": [],
            "score_penalties": [],
            "quality_flags": [],
            "evidence_sources": [],
        }

        main._apply_daily_recommendation_storage_quality(candidate, quality)

        self.assertEqual(candidate["score"], 5)
        self.assertEqual(candidate["score_components"][0]["label"], "검증 저장자료 품질")
        self.assertTrue(candidate["score_penalties"])
        self.assertIn("중복 의심 자료는 대표 자료만 근거로 사용", candidate["quality_flags"])
        self.assertIn("본문/OCR 보강 전 투자 근거 가중치 제한", candidate["quality_flags"])
        self.assertTrue(candidate["evidence_sources"][0].startswith("저장 품질:"))

    def test_daily_recommendation_candidate_ranking_uses_split_quality_helpers(self):
        import research_os_main as main

        settings = Settings(research_vault_dir="../research_vault")
        consensus_scan = {
            "summary": "테스트 후보 1개",
            "warnings": [],
            "as_of": "2026-05-31T09:00:00+09:00",
            "price_refresh_mode": "test",
            "rows": [
                {
                    "ticker": "003230",
                    "company_name": "삼양식품",
                    "current_price": 100000,
                    "price_source": "test",
                    "target_upside": 0.2,
                    "valuation_signal": "저평가",
                    "source_count": 2,
                    "market_value": 12000000,
                }
            ],
        }

        with (
            patch.object(main, "read_manifest", return_value=[{"ticker": "003230", "date": "2026-05-31"}]),
            patch.object(main, "read_dart_filing_cache", return_value={}),
            patch.object(main, "build_interest_automation_board", return_value={"ticker_targets": []}),
            patch.object(main, "build_target_consensus_scan", return_value=consensus_scan),
            patch.object(
                main,
                "build_recent_weekly_research_brief",
                return_value={
                    "public_ir_sec_items": [
                        {
                            "category": "public_ir_sec",
                            "ticker": "003230",
                            "summary": "삼양식품 공개 IR URL-only",
                            "needs_body_copy": True,
                            "usable_for_recommendation": False,
                        }
                    ],
                    "category_groups": [
                        {
                            "key": "public_ir_sec",
                            "label": "공개 IR/SEC",
                            "count": 1,
                            "ticker_count": 1,
                            "tickers": ["003230"],
                            "quality_summary": {
                                "usable_for_recommendation": 0,
                                "needs_body_copy": 1,
                                "blocked_or_needs_review": 1,
                                "providers": {"SEC EDGAR": 1},
                                "reliability_labels": {"URL-only 보강 필요": 1},
                            },
                            "items": [],
                        }
                    ],
                },
            ),
            patch.object(
                main,
                "verify_ticker_symbol_local_cached",
                return_value=SimpleNamespace(official_symbol="003230", company_name="삼양식품"),
            ),
            patch.object(main, "official_ticker_profile", return_value={"analysis_focus": "실적과 해외 성장"}),
            patch.object(main, "build_ticker_freshness_status", return_value={"tone": "ok", "summary": "저장자료 신선도 양호"}),
        ):
            result = main.build_daily_recommendation_candidates(settings, limit=3)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["selected_count"], 1)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["rank"], 1)
        self.assertEqual(candidate["company_name"], "삼양식품")
        component_labels = [item["label"] for item in candidate["score_components"]]
        self.assertIn("검증 저장자료 품질", component_labels)
        self.assertNotIn("최근 공개 IR/SEC 반영", component_labels)
        self.assertTrue(any("공개 IR/SEC URL-only" in item for item in candidate["risk_notes"]))
        self.assertEqual(candidate["weekly_evidence_groups"][0]["label"], "공개 IR/SEC")
        self.assertEqual(candidate["weekly_evidence_groups"][0]["ticker_count"], 1)
        self.assertEqual(candidate["weekly_evidence_groups"][0]["quality_summary"]["needs_body_copy"], 1)
        weekly_evidence = next(item for item in candidate["evidence_sources"] if "최근 1주 자료 묶음" in item)
        self.assertIn("추천 가능 0건/본문 보강 1건/출처 SEC EDGAR 1건", weekly_evidence)
        self.assertIn("품질 URL-only 보강 필요 1건", weekly_evidence)
        self.assertTrue(candidate["portfolio_risk_connection"]["linked"])

    def test_promoted_news_inbox_item_is_not_counted_as_open_quality_warning(self):
        import research_os_main as main

        item = {
            "promoted": True,
            "promoted_storage": {"relative_path": "research_vault/003230/a.md"},
            "tags": ["news_inbox"],
            "capture_quality": {"status": "보강 필요"},
        }

        self.assertNotIn("needs_body", main.news_filter_key(item))
        self.assertNotIn("quality_issue", main.news_filter_key(item))


if __name__ == "__main__":
    unittest.main()
