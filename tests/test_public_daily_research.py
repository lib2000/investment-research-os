from __future__ import annotations

from datetime import date
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _top_pick(*, status: str = "ready", recommendation_date: str = "2026-09-01") -> dict:
    return {
        "status": status,
        "generated_at": "2026-09-01T08:05:00+09:00",
        "recommendation_date": recommendation_date,
        "scope": {
            "label": "가족 전체 보유 종목 + 관심 종목",
            "member_portfolio_count": 3,
            "scope_fingerprint": "private-fingerprint",
        },
        "selection": {
            "selected_score": 170,
            "method": "private_selection_method",
        },
        "card": {
            "company_name": "Example Medical AI",
            "ticker": "EXAI",
            "market": "미국",
            "scope_status": "가족 보유 종목",
            "thesis": "최근 공개 실적과 목표주가 기록을 다시 대조했습니다.",
            "metrics": [
                {"label": "기준 가격", "value": "$12.34", "detail": "2026-09-01"},
            ],
            "reasons": [
                "공시 원문과 최근 실적 자료를 함께 확인했습니다.",
                "가족 보유 종목이라는 내부 선별 정보입니다.",
            ],
            "risks": [
                "Dossier/팀 리포트 원문을 추가 확인해야 합니다.",
                "실적 발표 후 변동성이 커질 수 있습니다.",
            ],
            "evidence": [
                "최근 공개 IR/SEC 자료 3건",
                "저장 품질: 활용 가능 5건",
            ],
            "evidence_strength": {
                "grade": "B",
                "document_count": 5,
                "recent_30d_count": 3,
            },
            "next_review": {
                "target_date": "2026-09-07",
                "label": "다음 실적 확인",
            },
        },
    }


def _recommendations() -> dict:
    return {
        "records": [
            {
                "recommendation_date": "2026-09-01",
                "ticker": "EXAI",
                "company_name": "Example Medical AI",
                "market_label": "미국",
                "score": 170,
                "evidence_quality_summary": {
                    "grade": "B",
                    "score": 82,
                    "document_count": 5,
                    "blocks_buy_decision": False,
                },
            },
            {
                "recommendation_date": "2026-08-31",
                "ticker": "ARCH",
                "company_name": "Archive Company",
                "market_label": "한국",
                "score": 155,
                "evidence_quality_summary": {
                    "grade": "A",
                    "score": 91,
                    "document_count": 7,
                    "blocks_buy_decision": False,
                },
            },
        ]
    }


def test_public_feed_removes_private_scope_and_internal_selection_fields() -> None:
    from research_os.public_daily_research import build_public_daily_research_feed

    feed = build_public_daily_research_feed(
        _top_pick(),
        _recommendations(),
        {"as_of": "2026-09-01T07:55:00+09:00", "checks": {"dart": {"status": "success"}}},
        today=date(2026, 9, 1),
    )

    assert feed["publication"]["state"] == "published"
    assert feed["publication"]["archive_start_date"] == "2026-09-01"
    assert feed["publication"]["next_scheduled_issue"] == "매일 07:10 KST 이후"
    assert feed["schema_version"] == "1.1"
    assert feed["latest"]["ticker"] == "EXAI"
    assert feed["latest"]["reference_price"] == {
        "value": "$12.34",
        "detail": "리서치 생성 당시 기준 · 실시간 시세 아님",
    }
    assert [item["label"] for item in feed["latest"]["metrics"]] == [
        "근거 문서",
        "최근 업데이트",
        "출처 범주",
        "다음 확인",
    ]
    assert [item["value"] for item in feed["latest"]["research_signals"]] == ["B", "3개", "3개", "1행"]
    assert feed["latest"]["evidence"]["source_types"] == ["공시 원문"]
    assert feed["latest"]["evidence"]["source_ledger"] == [
        {
            "sequence": "01",
            "source_type": "공시 원문",
            "purpose": "사실·일정 확인",
            "publication_basis": "공개 자료 기준",
            "role": "핵심 사실",
        }
    ]
    assert [item["report_date"] for item in feed["archive"]] == ["2026-09-01"]
    serialized = str(feed)
    assert "가족" not in serialized
    assert "private-fingerprint" not in serialized
    assert "private_selection_method" not in serialized
    assert "selected_score" not in serialized
    assert "Dossier" not in serialized
    assert "팀 리포트" not in serialized
    assert "170" not in serialized
    assert "https://" not in serialized


def test_stale_public_card_is_labelled_as_recent_not_today() -> None:
    from research_os.public_daily_research import build_public_daily_research_feed

    feed = build_public_daily_research_feed(
        _top_pick(recommendation_date="2026-09-01"),
        _recommendations(),
        today=date(2026, 9, 2),
    )

    assert feed["publication"]["state"] == "awaiting_daily_refresh"
    assert feed["latest"]["edition_label"] == "최근 발행 리서치"
    assert feed["latest"]["report_date"] == "2026-09-01"


def test_public_history_starts_on_september_first() -> None:
    from research_os.public_daily_research import build_public_daily_research_feed

    feed = build_public_daily_research_feed(
        _top_pick(recommendation_date="2026-08-31"),
        _recommendations(),
        today=date(2026, 9, 1),
    )

    assert feed["publication"]["state"] == "awaiting_first_issue"
    assert feed["latest"] is None
    assert [item["report_date"] for item in feed["archive"]] == ["2026-09-01"]


def test_review_hold_does_not_publish_a_ticker() -> None:
    from research_os.public_daily_research import build_public_daily_research_feed

    feed = build_public_daily_research_feed(
        _top_pick(status="review_hold"),
        _recommendations(),
        today=date(2026, 9, 1),
    )

    assert feed["publication"]["state"] == "review_hold"
    assert feed["latest"] is None


def test_public_site_contract_uses_generated_feed_not_private_api() -> None:
    app_source = (PROJECT_ROOT / "apps" / "daily-research-site" / "app.js").read_text(encoding="utf-8")
    exporter_source = (PROJECT_ROOT / "tools" / "export_public_daily_research.py").read_text(encoding="utf-8")

    assert "public-daily-research.json" in app_source
    assert "/api/v1/" not in app_source
    assert "research_signals" in app_source
    assert "source_ledger" in app_source
    assert "PUBLIC EVIDENCE DOSSIER" in app_source
    assert "write_public_daily_research_feed" in exporter_source


def test_daily_operations_exports_public_feed_after_recommendation_preview() -> None:
    runner_source = (PROJECT_ROOT / "tools" / "run_daily_research_operations.ps1").read_text(
        encoding="utf-8-sig"
    )

    assert "[switch]$SkipPublicDailyResearchExport" in runner_source
    assert "python tools\\export_public_daily_research.py" in runner_source
    assert "공개 일일 리서치 피드 내보내기" in runner_source
    assert runner_source.index("추천 저장/재계산 프리뷰 저장") < runner_source.index(
        "공개 일일 리서치 피드 내보내기"
    )
    assert runner_source.index("공개 일일 리서치 피드 내보내기") < runner_source.index(
        "텔레그램 중요 브리프 delivery ledger 갱신"
    )
