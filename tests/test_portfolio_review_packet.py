import json
import sys
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.portfolio_analysis_coverage import (  # noqa: E402
    portfolio_analysis_module_state,
    portfolio_human_review_packet,
    portfolio_vault_entries,
)
from research_os.portfolio_review_packet import (  # noqa: E402
    build_portfolio_human_review_packet,
    render_portfolio_human_review_packet_markdown,
    write_portfolio_human_review_packet,
)


class PortfolioReviewPacketTests(unittest.TestCase):
    def test_packet_deduplicates_official_filings_and_never_clears_modules(self):
        with TemporaryDirectory() as tmp:
            vault = Path(tmp) / "research_vault"
            ticker_dir = vault / "300080"
            ticker_dir.mkdir(parents=True)
            filing = {
                "filing": {
                    "stock_code": "300080",
                    "rcept_no": "20260811000013",
                    "receipt_date": "20260811",
                    "report_name": "반기보고서 (2026.06)",
                    "source_url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260811000013",
                }
            }
            for suffix in ("001", "002"):
                (ticker_dir / f"300080-dart-filing-watch-2026-08-11-{suffix}.json").write_text(
                    json.dumps(filing, ensure_ascii=False), encoding="utf-8"
                )
            store = {
                "portfolios": {
                    "이형주": {
                        "portfolio_name": "이형주",
                        "holdings": [
                            {
                                "ticker": "300080",
                                "name": "플리토",
                                "quantity": 156,
                                "current_price": 8430,
                                "price_source": "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-price",
                                "price_refresh_status": "updated",
                                "price_checked_at": "2026-08-21T18:33:15+09:00",
                                "sync_source": "toss_holdings",
                                "sync_status": "toss_missing",
                                "sync_checked_at": "2026-08-21T16:12:11+09:00",
                            }
                        ],
                    }
                }
            }
            cache = {
                "updated_at": "2026-08-21T20:20:17+09:00",
                "daily_check": {
                    "checked_at": "2026-08-21T18:46:18+09:00",
                    "checked_tickers": ["300080"],
                    "failed_tickers": [],
                },
            }

            packet = build_portfolio_human_review_packet(
                ticker="300080",
                portfolio_store=store,
                dart_cache=cache,
                vault_dir=vault,
                generated_at=datetime(2026, 8, 21, 21, 0, tzinfo=ZoneInfo("Asia/Seoul")),
            )

            self.assertEqual(packet["type"], "human-review-packet")
            self.assertEqual(len(packet["dart_filings"]), 1)
            self.assertEqual(packet["price_evidence"]["current_price"], 8430)
            self.assertTrue(packet["holding_snapshot"]["quantity_confirmation_required"])
            self.assertTrue(packet["dart_daily_watch"]["checked"])
            self.assertFalse(packet["review_gate"]["affects_document_coverage"])
            self.assertFalse(packet["review_gate"]["affects_review_gate"])

            paths = write_portfolio_human_review_packet(packet, ticker_dir)
            self.assertTrue(paths["json"].exists())
            self.assertIn("검토 게이트를 통과시키지 않습니다.", render_portfolio_human_review_packet_markdown(packet))

            entries = portfolio_vault_entries(vault, ["300080"])
            self.assertEqual(portfolio_analysis_module_state(entries), {
                "team_report": False,
                "trade_setup": False,
                "earnings_reaction": False,
                "model_update_note": False,
                "checklist": False,
                "recent_capture": True,
            })
            review_packet = portfolio_human_review_packet(entries)
            self.assertIsNotNone(review_packet)
            self.assertEqual(review_packet["review_gate_effect"], "none")
