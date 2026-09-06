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
    portfolio_human_review_queue,
    portfolio_review_priority_queue,
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
            self.assertTrue(review_packet["quantity_confirmation_required"])

            queue = portfolio_human_review_queue(
                [
                    {
                        "ticker": "OTHER",
                        "company_name": "다른 종목",
                        "portfolios": ["이형주"],
                        "market_value": 900_000,
                        "human_review_packet": {
                            "date": "2026-08-21",
                            "summary": "저장 증빙 검토 필요",
                            "quantity_confirmation_required": False,
                        },
                    },
                    {
                        "ticker": "300080",
                        "company_name": "플리토",
                        "portfolios": ["이형주"],
                        "market_value": 100_000,
                        "human_review_packet": review_packet,
                    },
                ]
            )
            self.assertEqual([item["ticker"] for item in queue], ["300080", "OTHER"])
            self.assertEqual(queue[0]["reason"], "계좌 동기화 미검출로 보유 수량 확인 필요")
            self.assertEqual(queue[0]["review_gate_effect"], "none")

    def test_review_priority_queue_is_read_only_and_uses_quantity_then_market_value(self):
        queue = portfolio_review_priority_queue(
            [
                {
                    "ticker": "COMPLETE",
                    "company_name": "수량 확인 종목",
                    "portfolios": ["이형주"],
                    "market_value": 100,
                    "completion_rate": 1,
                    "review_completion_rate": 1,
                    "review_state": {"checklist": True, "team_report": True},
                    "human_review_packet": {"quantity_confirmation_required": True},
                },
                {
                    "ticker": "HIGH",
                    "company_name": "체크리스트 보강 종목",
                    "portfolios": ["가족 합산"],
                    "market_value": 10_000_000,
                    "completion_rate": 1,
                    "review_completion_rate": 5 / 6,
                    "review_state": {"checklist": False, "team_report": True},
                    "missing_modules": [],
                    "review_missing_modules": ["체크리스트"],
                    "checklist_status": {"reason": "체크리스트 8/16; 검토 게이트 75% 미만입니다."},
                    "next_action": "16개 리서치 체크리스트로 투자 준비도를 수치화하세요.",
                },
                {
                    "ticker": "LOW",
                    "company_name": "기준 근거 보강 종목",
                    "portfolios": ["가족 합산"],
                    "market_value": 1_000_000,
                    "completion_rate": 0,
                    "review_completion_rate": 0,
                    "review_state": {"checklist": False, "team_report": False},
                    "missing_modules": ["기준 리포트", "체크리스트"],
                    "review_missing_modules": ["기준 리포트", "체크리스트"],
                },
            ]
        )

        self.assertEqual([item["ticker"] for item in queue], ["COMPLETE", "HIGH", "LOW"])
        self.assertEqual(queue[0]["queue_kind"], "quantity_confirmation")
        self.assertEqual(queue[1]["queue_kind"], "checklist_review")
        self.assertEqual(queue[2]["queue_kind"], "document_gap")
        self.assertTrue(all(item["action_mode"] == "read_only" for item in queue))
        self.assertTrue(all(item["automatic_completion"] is False for item in queue))
        self.assertEqual(queue[0]["review_gate_effect"], "none")
        self.assertEqual(queue[1]["review_gate_effect"], "read_only")

    def test_react_research_console_local_origin_is_allowlisted(self):
        source = (PROJECT_ROOT / "backend" / "research_os_main.py").read_text(encoding="utf-8")

        self.assertIn('"http://127.0.0.1:5173"', source)
        self.assertIn('"http://localhost:5173"', source)
