import unittest
import sys
from datetime import date, datetime
from tempfile import TemporaryDirectory
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def import_research_os_main_or_skip():
    try:
        import importlib

        return importlib.import_module("research_os_main")
    except ModuleNotFoundError as exc:
        if exc.name == "fastapi":
            raise unittest.SkipTest("FastAPI is not installed in this Python environment") from exc
        raise


from research_os.daily_recommendations import (
    add_daily_recommendation_penalty,
    add_daily_recommendation_score,
    apply_daily_recommendation_consensus_row,
    apply_daily_recommendation_evidence_documents,
    apply_daily_recommendation_freshness_profile,
    apply_daily_recommendation_overseas_tracking,
    apply_daily_recommendation_price_check,
    apply_daily_recommendation_priority_target,
    apply_daily_recommendation_recent_weekly_evidence,
    apply_daily_recommendation_tracking_feedback,
    daily_recommendation_tracking_feedback_profile,
    daily_recommendation_state_path,
    daily_recommendation_consensus_label,
    daily_recommendation_target_label,
    daily_recommendation_tracking_feedback,
    ensure_daily_recommendation_candidate,
    finalize_daily_recommendation_candidate,
    finalize_daily_recommendation_ranking,
    parse_daily_recommendations_time,
    saved_portfolio_price_lookup,
    summarize_daily_recommendation_store,
    should_run_daily_recommendations,
    update_recommendation_tracking,
    upsert_daily_recommendations,
    write_json_payload,
)
from research_os.investment_direction_profile import (
    apply_investment_direction_profile,
    matched_investment_direction_themes,
)
from research_os.settings import Settings
from research_os.storage_quality import storage_quality_entry_needs_body


class DailyRecommendationsTests(unittest.TestCase):
    def test_accuracy_eval_counts_string_penalties(self):
        from tools import evaluate_daily_recommendation_accuracy as accuracy_eval

        positive, penalty = accuracy_eval.component_points(
            {
                "score_components": [{"points": 10}, {"score": 4}],
                "score_penalties": ["최근 자료 신선도 보강 필요 (-2)", {"points": -3}],
            }
        )

        self.assertEqual(positive, 14)
        self.assertEqual(penalty, 5)

    def test_accuracy_eval_reports_outcome_breakdowns(self):
        from tools import evaluate_daily_recommendation_accuracy as accuracy_eval

        score, failures, details = accuracy_eval.score_tracked_outcomes(
            [
                {
                    "ticker": "AAA",
                    "company_name": "Alpha",
                    "tracking_milestones": [
                        {"key": "7d", "label": "추천 후 1주일", "status": "complete", "price_change_pct": -0.1},
                        {"key": "15d", "label": "추천 후 15일", "status": "complete", "price_change_pct": -0.04},
                    ],
                },
                {
                    "ticker": "BBB",
                    "company_name": "Beta",
                    "tracking_milestones": [
                        {"key": "7d", "label": "추천 후 1주일", "status": "complete", "price_change_pct": 0.08}
                    ],
                },
            ]
        )

        self.assertGreater(score, 0)
        self.assertTrue(any("hit_rate" in failure for failure in failures))
        self.assertEqual(details["underperforming_tickers"][0]["key"], "AAA")
        self.assertEqual(details["underperforming_tickers"][0]["completed_count"], 2)
        self.assertEqual(details["milestone_breakdown"][0]["key"], "15d")

    def test_accuracy_eval_reports_review_hold_feedback(self):
        from tools import evaluate_daily_recommendation_accuracy as accuracy_eval

        _score, _failures, details = accuracy_eval.score_tracked_outcomes(
            [
                {
                    "ticker": "AAA",
                    "company_name": "Alpha",
                    "tracking_milestones": [
                        {"key": "7d", "label": "추천 후 1주일", "status": "complete", "price_change_pct": -0.1},
                    ],
                },
                {
                    "ticker": "BBB",
                    "company_name": "Beta",
                    "tracking_milestones": [
                        {"key": "7d", "label": "추천 후 1주일", "status": "complete", "price_change_pct": -0.03},
                    ],
                },
            ],
            tracking_feedback_profiles={
                "AAA": {
                    "completed_count": 4,
                    "hit_rate": 0.0,
                    "average_change_pct": -0.08,
                    "penalty_points": 16,
                    "review_hold": True,
                },
                "BBB": {
                    "completed_count": 2,
                    "hit_rate": 0.0,
                    "average_change_pct": -0.03,
                    "penalty_points": 6,
                    "review_hold": False,
                },
            },
        )

        self.assertEqual(details["review_hold_tickers"][0]["ticker"], "AAA")
        self.assertEqual(details["penalized_tickers_without_hold"][0]["ticker"], "BBB")

    def test_accuracy_eval_reports_latest_policy_drift(self):
        from tools import evaluate_daily_recommendation_accuracy as accuracy_eval

        failures, details = accuracy_eval.latest_policy_alignment(
            [
                {"rank": 1, "ticker": "WEAK", "company_name": "Weak Co"},
                {"rank": 2, "ticker": "OK", "company_name": "Okay Co"},
            ],
            {
                "WEAK": {
                    "hit_rate": 0.0,
                    "average_change_pct": -0.08,
                    "penalty_points": 16,
                    "review_hold": True,
                },
                "OK": {
                    "hit_rate": 0.5,
                    "average_change_pct": 0.03,
                    "penalty_points": 0,
                    "review_hold": False,
                },
            },
        )

        self.assertEqual(failures, ["latest_policy_drift: 최신 추천에 반복 부진 보류 후보 포함: WEAK"])
        self.assertEqual(details["latest_review_hold_records"][0]["ticker"], "WEAK")
        self.assertEqual(details["latest_review_hold_records"][0]["penalty_points"], 16)

    def test_accuracy_eval_defers_latest_policy_drift_before_schedule(self):
        from tools import evaluate_daily_recommendation_accuracy as accuracy_eval

        self.assertTrue(
            accuracy_eval.latest_policy_drift_deferred_until_schedule(
                "2026-06-18",
                now=datetime(2026, 6, 19, 7, 30),
                daily_time="08:00",
            )
        )
        self.assertFalse(
            accuracy_eval.latest_policy_drift_deferred_until_schedule(
                "2026-06-18",
                now=datetime(2026, 6, 19, 8, 1),
                daily_time="08:00",
            )
        )

    def test_candidate_policy_eval_rejects_review_hold_in_top_slots(self):
        from tools import check_daily_recommendation_candidate_policy as policy_check

        failures, details = policy_check.validate_candidate_policy(
            {
                "candidates": [
                    {
                        "rank": 1,
                        "ticker": "WEAK",
                        "tracking_feedback_profile": {
                            "review_hold": True,
                            "hit_rate": 0.0,
                            "average_change_pct": -0.12,
                            "penalty_points": 16,
                        },
                    },
                    {"rank": 2, "ticker": "OK"},
                ],
                "warnings": ["반복 부진 top3 보류: OTLY"],
            },
            top_limit=3,
            expected_held_tickers=["OTLY"],
            require_hold_warning=True,
        )

        self.assertIn("top3_review_hold: WEAK", failures)
        self.assertEqual(details["top_candidates"][0]["ticker"], "WEAK")
        self.assertEqual(details["top_candidates"][0]["tracking_hit_rate"], 0.0)
        self.assertEqual(details["top_candidates"][0]["tracking_penalty_points"], 16)

    def test_tracking_feedback_profile_matches_review_hold_policy(self):
        profile = daily_recommendation_tracking_feedback_profile(
            {
                "completed_count": 3,
                "hit_rate": 0.0,
                "average_change_pct": -0.08,
                "penalty_points": 16,
                "horizon_penalty_points": 4,
                "weakest_milestone": {"key": "15d", "label": "추천 후 15일"},
            }
        )

        self.assertTrue(profile["review_hold"])
        self.assertEqual(profile["penalty_points"], 16)
        self.assertEqual(profile["weakest_milestone"]["key"], "15d")

    def test_candidate_policy_eval_requires_expected_hold_warning(self):
        from tools import check_daily_recommendation_candidate_policy as policy_check

        failures, _details = policy_check.validate_candidate_policy(
            {
                "candidates": [{"rank": 1, "ticker": "OK"}],
                "warnings": ["반복 부진 top3 보류: OTLY, 112610"],
            },
            top_limit=3,
            expected_held_tickers=["OTLY", "112610"],
            require_hold_warning=True,
        )

        self.assertEqual(failures, [])

    def test_saved_portfolio_price_lookup_uses_latest_checked_price(self):
        lookup = saved_portfolio_price_lookup(
            {
                "portfolios": {
                    "OLD": {
                        "holdings": [
                            {
                                "ticker": "ABSI",
                                "current_price": "6.10",
                                "price_source": "old_provider",
                                "price_checked_at": "2026-06-17T08:00:00+09:00",
                            },
                            {"ticker": "PL", "current_price": None},
                        ]
                    },
                    "NEW": {
                        "holdings": [
                            {
                                "ticker": "ABSI",
                                "current_price": 6.4,
                                "price_source": "finnhub",
                                "price_checked_at": "2026-06-18T06:55:31+09:00",
                            }
                        ]
                    },
                }
            }
        )

        self.assertEqual(lookup["ABSI"], (6.4, "saved_portfolio:finnhub"))
        self.assertNotIn("PL", lookup)

    def test_tracking_feedback_penalizes_recent_underperformers(self):
        feedback = daily_recommendation_tracking_feedback(
            [
                {
                    "ticker": "OTLY",
                    "tracking_milestones": [
                        {"status": "complete", "price_change_pct": -0.18},
                        {"status": "complete", "price_change_pct": -0.08},
                        {"status": "complete", "price_change_pct": -0.06},
                    ],
                },
                {
                    "ticker": "ABSI",
                    "tracking_milestones": [
                        {"status": "complete", "price_change_pct": 0.12},
                        {"status": "complete", "price_change_pct": -0.01},
                    ],
                },
            ]
        )

        self.assertEqual(feedback["OTLY"]["penalty_points"], 12)
        self.assertNotIn("ABSI", feedback)

        candidate = {"score": 40, "score_penalties": [], "risk_notes": [], "quality_flags": [], "evidence_sources": []}
        apply_daily_recommendation_tracking_feedback(candidate, feedback["OTLY"])

        self.assertEqual(candidate["score"], 28)
        self.assertTrue(candidate["tracking_feedback_profile"]["review_hold"])
        self.assertIn("최근 추천 성과 부진 피드백 (-12)", candidate["score_penalties"])
        self.assertTrue(any("hit rate" in item for item in candidate["risk_notes"]))
        self.assertIn("최근 추천 성과 피드백 감점", candidate["quality_flags"])

    def test_tracking_feedback_adds_horizon_penalty_for_weak_15d(self):
        feedback = daily_recommendation_tracking_feedback(
            [
                {
                    "ticker": "WIND",
                    "tracking_milestones": [
                        {"key": "7d", "label": "추천 후 1주일", "status": "complete", "price_change_pct": -0.02},
                        {"key": "7d", "label": "추천 후 1주일", "status": "complete", "price_change_pct": -0.01},
                        {"key": "15d", "label": "추천 후 15일", "status": "complete", "price_change_pct": -0.08},
                        {"key": "15d", "label": "추천 후 15일", "status": "complete", "price_change_pct": -0.12},
                    ],
                }
            ]
        )

        self.assertEqual(feedback["WIND"]["base_penalty_points"], 6)
        self.assertEqual(feedback["WIND"]["horizon_penalty_points"], 4)
        self.assertEqual(feedback["WIND"]["penalty_points"], 10)
        self.assertEqual(feedback["WIND"]["weakest_milestone"]["key"], "15d")

        candidate = {"score": 40, "score_penalties": [], "risk_notes": [], "quality_flags": [], "evidence_sources": []}
        apply_daily_recommendation_tracking_feedback(candidate, feedback["WIND"])

        self.assertEqual(candidate["score"], 30)
        self.assertTrue(any("추천 후 15일" in item for item in candidate["risk_notes"]))

    def test_daily_recommendation_consensus_label_uses_company_or_ticker(self):
        self.assertEqual(
            daily_recommendation_consensus_label({"company_name": "삼양식품"}, "003230"),
            "삼양식품",
        )
        self.assertEqual(daily_recommendation_consensus_label({}, "PL"), "PL")
        self.assertEqual(daily_recommendation_consensus_label({"company_name": "  "}, "JOBY"), "")

    def test_daily_recommendation_target_label_prefers_display_names(self):
        self.assertEqual(
            daily_recommendation_target_label({"label": "삼양식품", "company_name": "대체"}, "003230"),
            "삼양식품",
        )
        self.assertEqual(
            daily_recommendation_target_label({"company_name": "동성화인텍"}, "033500"),
            "동성화인텍",
        )
        self.assertEqual(
            daily_recommendation_target_label({"name": "Planet Labs"}, "PL"),
            "Planet Labs",
        )
        self.assertEqual(daily_recommendation_target_label({}, "JOBY"), "JOBY")

    def test_ensure_daily_recommendation_candidate_initializes_defaults(self):
        candidates = {}

        first = ensure_daily_recommendation_candidate(candidates, "003230", "삼양식품")
        second = ensure_daily_recommendation_candidate(candidates, "003230", "삼양식품")
        overseas = ensure_daily_recommendation_candidate(candidates, "JOBY", "Joby Aviation")

        self.assertIs(first, second)
        self.assertEqual(first["ticker"], "003230")
        self.assertEqual(first["company_name"], "삼양식품")
        self.assertEqual(first["currency"], "KRW")
        self.assertEqual(first["score"], 0)
        self.assertEqual(first["portfolio_risk_connection"], {})
        self.assertEqual(overseas["currency"], "USD")

    def test_investment_direction_profile_scores_matching_ai_power_candidate(self):
        candidate = ensure_daily_recommendation_candidate({}, "ORCL", "Oracle")
        candidate["evidence_sources"].append("AIDC 전력망 SOFC 현장발전 검토")

        updated = apply_investment_direction_profile(candidate)

        self.assertIs(updated, candidate)
        profile = candidate["investment_direction_profile"]
        self.assertEqual(profile["source_id"], "user-pasted-research-2026-06-14")
        self.assertEqual(profile["score_bonus"], 8)
        self.assertEqual(profile["themes"][0]["key"], "ai_power_bottleneck")
        self.assertIn("첨부 투자 방향: AI 전력 병목", [item["label"] for item in candidate["score_components"]])
        self.assertTrue(any("AI 데이터센터" in item for item in candidate["reasons"]))
        self.assertTrue(any("가스터빈 납기" in item for item in candidate["risk_notes"]))

    def test_investment_direction_profile_scores_repo_liquidity_candidate(self):
        candidate = ensure_daily_recommendation_candidate({}, "TLT", "Long Treasury ETF")
        candidate["evidence_sources"].append("SOFR-ON RRP와 SOFR-IORB, TGA, T-bill 순발행을 함께 확인")

        apply_investment_direction_profile(candidate)

        profile = candidate["investment_direction_profile"]
        self.assertEqual(profile["themes"][0]["key"], "repo_liquidity_stress")
        self.assertEqual(profile["score_bonus"], 6)
        self.assertTrue(any("SOFR 단기자금 유동성" in item["label"] for item in candidate["score_components"]))
        self.assertTrue(any("deleveraging" in item for item in candidate["risk_notes"]))
        self.assertTrue(any("SOFR-ON RRP" in item for item in profile["watch_triggers"]))

    def test_investment_direction_profile_scores_enterprise_ai_data_cloud_candidate(self):
        candidate = ensure_daily_recommendation_candidate({}, "SNOW", "Snowflake")
        candidate["evidence_sources"].append("AWS Graviton, Natoma MCP governance, RPO와 NRR 점검")

        apply_investment_direction_profile(candidate)

        profile = candidate["investment_direction_profile"]
        self.assertEqual(profile["themes"][0]["key"], "enterprise_ai_data_cloud")
        self.assertEqual(profile["score_bonus"], 6)
        self.assertTrue(any("엔터프라이즈 AI 데이터 클라우드" in item["label"] for item in candidate["score_components"]))
        self.assertTrue(any("AWS lock-in" in item for item in candidate["risk_notes"]))
        self.assertTrue(any("RPO" in item for item in profile["watch_triggers"]))

    def test_investment_direction_profile_score_bonus_matches_component_sum(self):
        candidate = ensure_daily_recommendation_candidate({}, "SNOW", "Snowflake")
        candidate["evidence_sources"].append("AIDC 전력망 SOFC, HBM CoWoS, AWS Graviton 데이터 클라우드 점검")

        apply_investment_direction_profile(candidate)

        profile = candidate["investment_direction_profile"]
        profile_component_points = sum(
            int(component.get("points") or 0)
            for component in candidate["score_components"]
            if str(component.get("label") or "").startswith("첨부 투자 방향:")
        )
        self.assertGreater(len(profile["themes"]), 1)
        self.assertEqual(profile["score_bonus"], profile_component_points)
        self.assertEqual(candidate["score"], profile_component_points)

    def test_investment_direction_profile_ignores_unmatched_candidate(self):
        candidate = ensure_daily_recommendation_candidate({}, "003230", "삼양식품")
        candidate["evidence_sources"].append("라면 수출과 원가 안정성 점검")

        self.assertEqual(matched_investment_direction_themes(candidate), [])
        updated = apply_investment_direction_profile(candidate)

        self.assertIs(updated, candidate)
        self.assertNotIn("investment_direction_profile", candidate)
        self.assertEqual(candidate["score"], 0)

    def test_apply_daily_recommendation_consensus_row_scores_target_and_portfolio_context(self):
        candidate = ensure_daily_recommendation_candidate({}, "003230", "삼양식품")

        updated = apply_daily_recommendation_consensus_row(
            candidate,
            {
                "currency": "KRW",
                "current_price": 100000,
                "target_upside": 0.24,
                "valuation_signal": "저평가",
                "source_count": 3,
                "market_value": 12000000,
                "interest": True,
                "latest_source_file": "report.md",
                "source_scope": "portfolio",
            },
            price_refresh_mode="consensus",
            as_of="2026-06-14T08:00:00+09:00",
        )

        self.assertIs(updated, candidate)
        self.assertEqual(candidate["baseline_price"], 100000)
        self.assertEqual(candidate["baseline_price_source"], "consensus")
        self.assertEqual(candidate["baseline_price_checked_at"], "2026-06-14T08:00:00+09:00")
        labels = [item["label"] for item in candidate["score_components"]]
        self.assertIn("증권사 목표가 상승여력", labels)
        self.assertIn("밸류에이션 신호", labels)
        self.assertIn("리포트 근거 수", labels)
        self.assertIn("실제 보유 포트폴리오 비중", labels)
        self.assertIn("관심종목 등록", labels)
        self.assertTrue(candidate["portfolio_risk_connection"]["linked"])
        self.assertEqual(candidate["portfolio_risk_connection"]["priority"], "high")
        self.assertIn("보유 포트폴리오 평가금액 12,000,000원", candidate["portfolio_context"])
        self.assertIn("저장된 증권사 목표주가 대비 상승여력 24.0%", candidate["reasons"])
        self.assertIn("밸류에이션 신호: 저평가", candidate["reasons"])
        self.assertIn("목표가/리포트 근거 3건", candidate["evidence_sources"])
        self.assertIn("최근 근거 파일: report.md", candidate["evidence_sources"])
        self.assertIn("대상 범위: portfolio", candidate["evidence_sources"])

    def test_apply_daily_recommendation_priority_target_scores_research_links(self):
        candidate = ensure_daily_recommendation_candidate({}, "003230", "삼양식품")

        updated = apply_daily_recommendation_priority_target(
            candidate,
            {
                "priority": "high",
                "recent_document_count": 4,
                "rag_document_count": 8,
                "thesis_snapshot_connected": True,
                "market_journal_matches": [
                    {"summary": "수출 성장과 원가 안정성이 동시에 확인되었습니다."},
                    {"summary": "후속 메모"},
                ],
                "next_action": "실적 발표 전 가격 조건 확인",
            },
        )

        self.assertIs(updated, candidate)
        labels = [item["label"] for item in candidate["score_components"]]
        self.assertEqual(candidate["score"], 50)
        self.assertIn("보유/관심 우선순위", labels)
        self.assertIn("최근 저장자료", labels)
        self.assertIn("RAG 연결 문서", labels)
        self.assertIn("최신 투자 논거 스냅샷", labels)
        self.assertIn("시장일지 연결", labels)
        self.assertIn("최근 저장자료 4건", candidate["reasons"])
        self.assertIn("시장일지 연결: 수출 성장과 원가 안정성이 동시에 확인되었습니다.", candidate["reasons"])
        self.assertIn("RAG 연결 문서 8건", candidate["evidence_sources"])
        self.assertIn("최신 투자 논거 스냅샷 연결", candidate["evidence_sources"])
        self.assertEqual(candidate["risk_notes"], ["실적 발표 전 가격 조건 확인"])

    def test_apply_daily_recommendation_recent_weekly_evidence_scores_and_dedupes_groups(self):
        candidate = ensure_daily_recommendation_candidate({}, "003230", "삼양식품")
        recent_items = [
            {"category": "filing", "relative_path": "filing.md", "summary": "공시 요약", "date": "2026-06-14"},
            {"category": "report", "relative_path": "report.md", "summary": "리포트 요약", "date": "2026-06-14"},
            {
                "category": "public_ir_sec",
                "relative_path": "ir.md",
                "summary": "IR 요약",
                "usable_for_recommendation": True,
            },
            {
                "category": "public_ir_sec",
                "relative_path": "blocked.md",
                "summary": "본문 보강 필요",
                "usable_for_recommendation": False,
            },
        ]
        weekly_groups = [
            {"key": "reports", "label": "리포트", "count": 2, "visible_count": 2, "ticker_count": 1},
            {"key": "reports", "label": "리포트 중복", "count": 9},
            {"key": "public_ir_sec", "label": "공개 IR/SEC", "count": 2, "visible_count": 1, "ticker_count": 1},
        ]

        updated = apply_daily_recommendation_recent_weekly_evidence(candidate, recent_items, weekly_groups)

        self.assertIs(updated, candidate)
        labels = [item["label"] for item in candidate["score_components"]]
        self.assertIn("최근 중요 공시 반영", labels)
        self.assertIn("최근 핵심 리포트 반영", labels)
        self.assertIn("최근 공개 IR/SEC 반영", labels)
        self.assertIn("최근 1주 중요 공시 1건 확인", candidate["reasons"])
        self.assertIn("본문 추출이 확인된 공개 IR/SEC 자료가 최근 1주 브리프와 RAG 근거에 연결됨", candidate["reasons"])
        self.assertIn("최근 1주 공시 브리프 반영", candidate["evidence_sources"])
        self.assertIn("최근 1주 핵심 리포트 1건", candidate["evidence_sources"])
        self.assertIn("최근 1주 공개 IR/SEC 자료 1건", candidate["evidence_sources"])
        self.assertIn("공개 IR/SEC 본문 보강 필요", candidate["quality_flags"])
        self.assertTrue(candidate["risk_notes"][0].startswith("공개 IR/SEC URL-only 자료 1건"))
        self.assertEqual(len(candidate["evidence_documents"]), 4)
        self.assertEqual([group["key"] for group in candidate["weekly_evidence_groups"]], ["reports", "public_ir_sec"])
        weekly_text = next(item for item in candidate["evidence_sources"] if item.startswith("최근 1주 자료 묶음"))
        self.assertIn("리포트 2건", weekly_text)
        self.assertIn("공개 IR/SEC 2건", weekly_text)

    def test_apply_daily_recommendation_evidence_documents_preserves_recent_then_rag(self):
        candidate = {
            "evidence_documents": [
                {"title": "최근 문서", "source_relative_path": "recent.md"},
            ]
        }

        updated = apply_daily_recommendation_evidence_documents(
            candidate,
            [
                {"title": "RAG 문서", "source_relative_path": "rag.md"},
            ],
        )

        self.assertIs(updated, candidate)
        self.assertEqual(
            [item["source_relative_path"] for item in candidate["evidence_documents"]],
            ["recent.md", "rag.md"],
        )

        empty = apply_daily_recommendation_evidence_documents({}, None)
        self.assertEqual(empty["evidence_documents"], [])

    def test_apply_daily_recommendation_freshness_profile_records_tone_and_focus(self):
        verification = SimpleNamespace(company_name="삼양식품")
        candidate = {
            "ticker": "003230",
            "company_name": "003230",
            "score": 10,
            "score_components": [],
            "score_penalties": [],
            "quality_flags": [],
            "evidence_sources": [],
            "reasons": [],
        }

        updated = apply_daily_recommendation_freshness_profile(
            candidate,
            ticker="003230",
            verification=verification,
            profile={"analysis_focus": "수출 성장"},
            freshness={"tone": "warning", "summary": "최근 자료 보강 필요"},
        )

        self.assertIs(updated, candidate)
        self.assertEqual(candidate["company_name"], "삼양식품")
        self.assertEqual(candidate["score"], 13)
        self.assertEqual(candidate["score_components"][-1], {"label": "저장자료 신선도 확인 필요", "points": 5})
        self.assertEqual(candidate["score_penalties"], ["최근 자료 신선도 보강 필요 (-2)"])
        self.assertIn("저장자료 신선도 확인 필요", candidate["quality_flags"])
        self.assertIn("최근 자료 보강 필요", candidate["evidence_sources"])
        self.assertIn("분석 초점: 수출 성장", candidate["reasons"])

        ok_candidate = {"score": 0, "score_components": [], "evidence_sources": []}
        apply_daily_recommendation_freshness_profile(
            ok_candidate,
            ticker="A",
            verification=SimpleNamespace(company_name=""),
            profile={},
            freshness={"tone": "ok"},
        )
        self.assertEqual(ok_candidate["score"], 10)
        self.assertEqual(ok_candidate["evidence_sources"], ["저장자료 신선도 확인"])

    def test_apply_daily_recommendation_overseas_tracking_marks_fx_review(self):
        candidate = {
            "ticker": "PL",
            "currency": "usd",
            "baseline_price": 42.5,
            "baseline_price_source": "test",
            "baseline_price_checked_at": "2026-06-14T08:00:00+09:00",
            "quality_flags": [],
        }

        updated = apply_daily_recommendation_overseas_tracking(candidate)

        self.assertIs(updated, candidate)
        self.assertTrue(candidate["overseas_tracking"]["needs_fx_conversion"])
        self.assertEqual(candidate["overseas_tracking"]["currency"], "USD")
        self.assertEqual(candidate["overseas_tracking"]["baseline_price"], 42.5)
        self.assertEqual(candidate["overseas_tracking"]["price_source"], "test")
        self.assertIn("해외 종목: 환율·원화 평가 병행 확인", candidate["quality_flags"])

        domestic = apply_daily_recommendation_overseas_tracking({"currency": "KRW"})
        self.assertFalse(domestic["overseas_tracking"]["needs_fx_conversion"])
        self.assertEqual(domestic["overseas_tracking"]["currency"], "KRW")

    def test_apply_daily_recommendation_price_check_records_success_and_missing_price(self):
        candidate = {"score": 10, "score_components": [], "score_penalties": []}

        updated = apply_daily_recommendation_price_check(
            candidate,
            price=123.4,
            source="test",
            checked_at="2026-06-14T08:00:00+09:00",
        )

        self.assertIs(updated, candidate)
        self.assertEqual(candidate["baseline_price"], 123.4)
        self.assertEqual(candidate["baseline_price_source"], "test")
        self.assertEqual(candidate["baseline_price_checked_at"], "2026-06-14T08:00:00+09:00")
        self.assertEqual(candidate["score"], 15)
        self.assertEqual(candidate["score_components"][-1], {"label": "현재가 확인", "points": 5})

        missing = {"score": 10, "score_components": [], "score_penalties": []}
        apply_daily_recommendation_price_check(missing, price=None)

        self.assertEqual(missing["score"], 5)
        self.assertIn("기준 현재가 미확인", missing["quality_flags"])
        self.assertEqual(missing["score_penalties"], ["현재가 미확인 (-5)"])
        self.assertTrue(missing["risk_notes"][0].startswith("기준 현재가를 확인하지 못해"))

    def test_finalize_daily_recommendation_ranking_limits_and_ranks_candidates(self):
        from research_os import daily_recommendation_ranking

        result = finalize_daily_recommendation_ranking(
            {
                "A": {"ticker": "A", "company_name": "알파", "score": 70, "baseline_price": None},
                "B": {"ticker": "B", "company_name": "베타", "score": 90, "baseline_price": 10},
                "C": {"ticker": "C", "company_name": "감마", "score": 90, "baseline_price": None},
            },
            limit=2,
            as_of="2026-06-14T08:00:00+09:00",
            consensus_summary="테스트 요약",
            warnings=["w1", "w2"],
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["selected_count"], 2)
        self.assertEqual(result["universe_count"], 3)
        self.assertEqual(result["consensus_summary"], "테스트 요약")
        self.assertEqual(result["warnings"], ["w1", "w2"])
        self.assertEqual([item["ticker"] for item in result["candidates"]], ["B", "C"])
        self.assertEqual([item["rank"] for item in result["candidates"]], [1, 2])
        direct_result = daily_recommendation_ranking.finalize_daily_recommendation_ranking(
            {
                "A": {"ticker": "A", "company_name": "알파", "score": 70, "baseline_price": None},
                "B": {"ticker": "B", "company_name": "베타", "score": 90, "baseline_price": 10},
                "C": {"ticker": "C", "company_name": "감마", "score": 90, "baseline_price": None},
            },
            limit=2,
            as_of="2026-06-14T08:00:00+09:00",
            consensus_summary="테스트 요약",
            warnings=["w1", "w2"],
        )
        self.assertEqual(direct_result, result)

    def test_finalize_daily_recommendation_ranking_holds_severe_repeat_underperformers(self):
        result = finalize_daily_recommendation_ranking(
            {
                "WEAK": {
                    "ticker": "WEAK",
                    "company_name": "약세",
                    "score": 200,
                    "baseline_price": 10,
                    "tracking_feedback_profile": {
                        "completed_count": 4,
                        "hit_rate": 0.0,
                        "average_change_pct": -0.12,
                        "penalty_points": 12,
                        "review_hold": True,
                    },
                },
                "A": {"ticker": "A", "company_name": "알파", "score": 130, "baseline_price": 10},
                "B": {"ticker": "B", "company_name": "베타", "score": 120, "baseline_price": 10},
                "C": {"ticker": "C", "company_name": "감마", "score": 110, "baseline_price": 10},
            },
            limit=3,
            as_of="2026-06-18T08:00:00+09:00",
            warnings=[f"w{i}" for i in range(12)],
        )

        self.assertEqual([item["ticker"] for item in result["candidates"]], ["A", "B", "C"])
        self.assertIn("WEAK", result["warnings"][0])
        self.assertEqual(len(result["warnings"]), 10)

    def test_daily_recommendation_score_helpers_ignore_invalid_values(self):
        candidate = {"score": 10}

        add_daily_recommendation_score(candidate, "5", "리포트")
        add_daily_recommendation_score(candidate, 0, "무시")
        add_daily_recommendation_score(candidate, "bad", "무시")
        add_daily_recommendation_penalty(candidate, "현재가 미확인", "3")
        add_daily_recommendation_penalty(candidate, "메모만")
        add_daily_recommendation_penalty(candidate, "")

        self.assertEqual(candidate["score"], 12)
        self.assertEqual(candidate["score_components"], [{"label": "리포트", "points": 5}])
        self.assertEqual(candidate["score_penalties"], ["현재가 미확인 (-3)", "메모만"])

    def test_finalize_daily_recommendation_candidate_builds_score_explanation(self):
        candidate = {
            "score": 22,
            "reasons": [],
            "evidence_sources": ["근거 A", "근거 A", "근거 B"],
            "risk_notes": ["위험 A", "위험 A"],
            "score_penalties": ["현재가 미확인 (-5)", "현재가 미확인 (-5)"],
            "quality_flags": ["확인 필요", "확인 필요"],
            "score_components": [
                {"label": "보유", "points": 20},
                {"label": "리포트", "points": 10},
            ],
        }

        finalized = finalize_daily_recommendation_candidate(candidate)

        self.assertEqual(finalized["reasons"], ["보유/관심목록과 저장 리서치에 포함된 일일 점검 후보입니다."])
        self.assertEqual(finalized["evidence_sources"], ["근거 A", "근거 B"])
        self.assertEqual(finalized["risk_notes"], ["위험 A"])
        self.assertEqual(finalized["score_penalties"], ["현재가 미확인 (-5)"])
        self.assertEqual(finalized["quality_flags"], ["확인 필요"])
        self.assertEqual(finalized["score_explanation"]["positive_points"], 30)
        self.assertEqual(finalized["score_explanation"]["penalty_points"], 5)
        self.assertEqual(finalized["score_explanation"]["top_component"]["label"], "보유")
        self.assertEqual(finalized["score_explanation"]["component_weights"][0]["weight_pct"], 66.7)

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
        self.assertEqual(parse_daily_recommendations_time(settings), (8, 0))

    def test_daily_recommendation_status_exposes_today_records(self):
        main = import_research_os_main_or_skip()

        settings = Settings(daily_recommendations_time="08:00")
        with (
            patch.object(
                main,
                "summarize_daily_recommendation_store",
                return_value={
                    "records": [
                        {"recommendation_date": "2026-06-12", "rank": 1, "ticker": "OLD"},
                        {"recommendation_date": "2026-06-13", "rank": 2, "ticker": "B"},
                        {"recommendation_date": "2026-06-13", "rank": 1, "ticker": "A"},
                    ],
                    "latest_recommendation_date": "2026-06-13",
                },
            ),
            patch.object(main, "current_storage_date", return_value=date(2026, 6, 13)),
            patch.object(main, "read_json_store", return_value={"last_run_date": "2026-06-13"}),
            patch.object(main, "should_run_daily_recommendations", return_value=False),
        ):
            payload = main.get_daily_recommendations_status(settings)

        self.assertEqual(payload["daily_time"], "08:00")
        self.assertTrue(payload["has_today_recommendations"])
        self.assertEqual([item["ticker"] for item in payload["today_records"]], ["A", "B"])
        self.assertEqual(payload["today_recommendation_date"], "2026-06-13")

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
        main = import_research_os_main_or_skip()

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
        main = import_research_os_main_or_skip()

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
        main = import_research_os_main_or_skip()

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
        main = import_research_os_main_or_skip()

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
                            "count": 3,
                            "visible_count": 1,
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
        self.assertIn("공개 IR/SEC 3건(표시 1/3건/종목 1개)", weekly_evidence)
        self.assertIn("추천 가능 0건/본문 보강 1건/출처 SEC EDGAR 1건", weekly_evidence)
        self.assertIn("품질 URL-only 보강 필요 1건", weekly_evidence)
        self.assertTrue(candidate["portfolio_risk_connection"]["linked"])

    def test_promoted_news_inbox_item_is_not_counted_as_open_quality_warning(self):
        main = import_research_os_main_or_skip()

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
