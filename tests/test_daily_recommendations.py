import unittest
import sys
from datetime import date
from tempfile import TemporaryDirectory
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.daily_recommendations import (
    summarize_daily_recommendation_store,
    update_recommendation_tracking,
    upsert_daily_recommendations,
)
from research_os.settings import Settings
from research_os.storage_quality import storage_quality_entry_needs_body


class DailyRecommendationsTests(unittest.TestCase):
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
        week = first["tracking_milestones"][0]
        self.assertEqual(week["status"], "complete")
        self.assertEqual(week["price_change_pct"], 0.1)

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
