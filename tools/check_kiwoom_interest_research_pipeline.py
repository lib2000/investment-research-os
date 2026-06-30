"""Check research-pipeline coverage after Kiwoom interest sync."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


SYSTEM_DIR = Path("research_vault/_system")
INTEREST_STORE = SYSTEM_DIR / "interest_list.json"
INTEREST_TARGETS_STORE = SYSTEM_DIR / "interest_collection_targets.json"
DAILY_RECOMMENDATIONS_STORE = SYSTEM_DIR / "daily_recommendations.json"
KIWOOM_SYNC_HISTORY = SYSTEM_DIR / "kiwoom_interest_sync_history.jsonl"


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (candidate / "research_vault").exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def load_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise SystemExit(f"필수 저장 파일을 찾지 못했습니다: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"JSON 파싱 실패: {path} | {exc}") from exc


def normalized_ticker(value: Any) -> str:
    return str(value or "").strip().upper()


def company_name(item: dict[str, Any]) -> str:
    verification = item.get("verification") if isinstance(item.get("verification"), dict) else {}
    return str(verification.get("company_name") or item.get("company_name") or item.get("name") or "").strip()


def tags(item: dict[str, Any]) -> list[str]:
    return [str(tag).strip() for tag in item.get("tags", []) if str(tag or "").strip()]


def latest_kiwoom_apply(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    latest: dict[str, Any] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("mode") == "apply" and row.get("write_mode") == "saved":
            latest = row
    return latest


def latest_recommendations(payload: dict[str, Any]) -> list[dict[str, Any]]:
    records = [item for item in payload.get("records", []) if isinstance(item, dict)]
    dates = sorted({str(item.get("recommendation_date") or "") for item in records if item.get("recommendation_date")})
    if not dates:
        return []
    latest_date = dates[-1]
    return [item for item in records if item.get("recommendation_date") == latest_date]


def target_tier(target: dict[str, Any], recommended: bool) -> str:
    rag_count = int(target.get("rag_document_count") or 0)
    recent_count = int(target.get("recent_document_count") or 0)
    thesis_connected = bool(target.get("thesis_snapshot_connected"))
    if recommended or (rag_count > 0 and recent_count > 0 and thesis_connected):
        return "core_tracking"
    if rag_count > 0 or recent_count > 0 or thesis_connected:
        return "candidate"
    return "needs_collection"


def compact_target(target: dict[str, Any], tier: str) -> dict[str, Any]:
    return {
        "ticker": target.get("ticker"),
        "company_name": target.get("company_name"),
        "tier": tier,
        "source": target.get("source"),
        "priority": target.get("priority"),
        "recent_document_count": target.get("recent_document_count", 0),
        "unique_document_count": target.get("unique_document_count", 0),
        "rag_document_count": target.get("rag_document_count", 0),
        "thesis_snapshot_connected": bool(target.get("thesis_snapshot_connected")),
        "market_journal_match_count": len(target.get("market_journal_matches") or []),
        "next_action": target.get("next_action"),
    }


def build_report(root: Path) -> dict[str, Any]:
    interest_payload = load_json(root / INTEREST_STORE)
    board_payload = load_json(root / INTEREST_TARGETS_STORE)
    recommendations_payload = load_json(root / DAILY_RECOMMENDATIONS_STORE)
    sync_history = latest_kiwoom_apply(root / KIWOOM_SYNC_HISTORY)

    tickers = [item for item in interest_payload.get("tickers", []) if isinstance(item, dict)]
    kiwoom_tickers = [
        item
        for item in tickers
        if "kiwoom_interest_sync" in tags(item)
    ]
    kiwoom_codes = {normalized_ticker(item.get("ticker")) for item in kiwoom_tickers if item.get("ticker")}
    nonstandard = sorted(code for code in kiwoom_codes if not (code.isdigit() and len(code) == 6))

    board = board_payload.get("payload") if isinstance(board_payload.get("payload"), dict) else board_payload
    ticker_targets = [
        item
        for item in board.get("ticker_targets", [])
        if isinstance(item, dict) and normalized_ticker(item.get("ticker")) in kiwoom_codes
    ]
    targets_by_ticker = {normalized_ticker(item.get("ticker")): item for item in ticker_targets}

    latest_records = latest_recommendations(recommendations_payload)
    recommended_codes = {normalized_ticker(item.get("ticker")) for item in latest_records}
    kiwoom_recommendations = [
        {
            "market": item.get("market"),
            "rank": item.get("rank"),
            "ticker": item.get("ticker"),
            "company_name": item.get("company_name"),
            "score": item.get("score"),
        }
        for item in latest_records
        if normalized_ticker(item.get("ticker")) in kiwoom_codes
    ]

    tiers: dict[str, list[dict[str, Any]]] = {"core_tracking": [], "candidate": [], "needs_collection": []}
    for code in sorted(kiwoom_codes):
        target = targets_by_ticker.get(code)
        if not target:
            item = next((entry for entry in kiwoom_tickers if normalized_ticker(entry.get("ticker")) == code), {})
            tiers["needs_collection"].append(
                {
                    "ticker": code,
                    "company_name": company_name(item),
                    "tier": "needs_collection",
                    "source": "missing_interest_automation_target",
                    "priority": item.get("priority"),
                    "recent_document_count": 0,
                    "unique_document_count": 0,
                    "rag_document_count": 0,
                    "thesis_snapshot_connected": False,
                    "market_journal_match_count": 0,
                    "next_action": "관심종목 자동화 보드를 재생성해 수집 대상으로 반영하세요.",
                }
            )
            continue
        tier = target_tier(target, code in recommended_codes)
        tiers[tier].append(compact_target(target, tier))

    group_counts = Counter()
    for item in kiwoom_tickers:
        item_tags = tags(item)
        group = next((tag for tag in item_tags if tag not in {"kiwoom_interest", "kiwoom_interest_sync"}), "미분류")
        group_counts[group] += 1

    missing_board_count = len(kiwoom_codes - set(targets_by_ticker))
    stale_board = not str(board.get("as_of") or "").strip()
    if sync_history.get("created_at") and board.get("as_of"):
        try:
            board_time = datetime.fromisoformat(str(board["as_of"]).replace("Z", "+00:00"))
            sync_time = datetime.fromisoformat(str(sync_history["created_at"]).replace("Z", "+00:00"))
            stale_board = board_time < sync_time
        except ValueError:
            stale_board = True

    return {
        "status": "success" if not nonstandard and not missing_board_count and not stale_board else "needs_attention",
        "module": "kiwoom_interest_research_pipeline",
        "checked_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds"),
        "latest_kiwoom_sync": {
            "created_at": sync_history.get("created_at"),
            "requested_count": sync_history.get("requested_count", 0),
            "prepared_count": sync_history.get("prepared_count", 0),
            "interest_ticker_count": sync_history.get("interest_ticker_count", 0),
        },
        "interest_store": {
            "total_ticker_count": len(tickers),
            "kiwoom_synced_ticker_count": len(kiwoom_codes),
            "kiwoom_nonstandard_count": len(nonstandard),
            "kiwoom_nonstandard_samples": nonstandard[:10],
            "kiwoom_group_counts": dict(sorted(group_counts.items())),
        },
        "collection_board": {
            "as_of": board.get("as_of"),
            "target_count": board.get("target_count", 0),
            "ticker_target_count": board.get("ticker_target_count", 0),
            "kiwoom_target_count": len(ticker_targets),
            "missing_kiwoom_target_count": missing_board_count,
            "kiwoom_rag_connected_count": sum(1 for item in ticker_targets if int(item.get("rag_document_count") or 0) > 0),
            "kiwoom_recent_document_connected_count": sum(1 for item in ticker_targets if int(item.get("recent_document_count") or 0) > 0),
            "kiwoom_thesis_connected_count": sum(1 for item in ticker_targets if item.get("thesis_snapshot_connected")),
        },
        "recommendations": {
            "latest_recommendation_date": max(
                [str(item.get("recommendation_date") or "") for item in latest_records],
                default="",
            ),
            "latest_record_count": len(latest_records),
            "kiwoom_latest_recommendation_count": len(kiwoom_recommendations),
            "kiwoom_latest_recommendations": kiwoom_recommendations,
        },
        "tiers": {
            "core_tracking_count": len(tiers["core_tracking"]),
            "candidate_count": len(tiers["candidate"]),
            "needs_collection_count": len(tiers["needs_collection"]),
            "core_tracking_samples": tiers["core_tracking"][:10],
            "candidate_samples": tiers["candidate"][:10],
            "needs_collection_samples": tiers["needs_collection"][:10],
        },
        "next_actions": [
            "핵심 추적 종목은 오늘 추천 후보와 비교해 점수 급등/급락 원인을 확인하세요.",
            "일반 후보는 RAG 검색 합성 또는 Dossier 갱신으로 최신 투자 논거를 보강하세요.",
            "수집 보강 필요 종목은 공시·리포트·시장일지 키워드가 부족하므로 자동 수집 보드의 검색어를 우선 실행하세요.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="키움 관심종목 리서치 파이프라인 반영 상태를 점검합니다.")
    parser.add_argument("--json", action="store_true", help="JSON으로 출력합니다.")
    args = parser.parse_args()
    root = project_root(Path.cwd())
    report = build_report(root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"상태: {report['status']} | 모듈: {report['module']}")
        print(
            "관심종목: 전체 {total_ticker_count}개 | 키움 동기화 {kiwoom_synced_ticker_count}개 | 비표준 {kiwoom_nonstandard_count}개".format(
                **report["interest_store"]
            )
        )
        print(
            "자동화 보드: 전체 대상 {target_count}개 | 키움 대상 {kiwoom_target_count}개 | 누락 {missing_kiwoom_target_count}개 | RAG 연결 {kiwoom_rag_connected_count}개".format(
                **report["collection_board"]
            )
        )
        print(
            "오늘 추천: 최신 {latest_recommendation_date} | 전체 {latest_record_count}개 | 키움 포함 {kiwoom_latest_recommendation_count}개".format(
                **report["recommendations"]
            )
        )
        print(
            "등급: 핵심 추적 {core_tracking_count}개 | 일반 후보 {candidate_count}개 | 수집 보강 필요 {needs_collection_count}개".format(
                **report["tiers"]
            )
        )
        print("키움 그룹:", ", ".join(f"{key}={value}" for key, value in report["interest_store"]["kiwoom_group_counts"].items()))
        for item in report["tiers"]["needs_collection_samples"][:5]:
            print(f"보강 필요: {item.get('company_name') or item.get('ticker')} | {item.get('ticker')} | {item.get('next_action')}")
    return 0 if report["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
