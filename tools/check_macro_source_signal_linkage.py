"""Validate macro/regional source linkage signals without a backend."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SYSTEM_DIR = Path("research_vault/_system")


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (
            candidate / "research_vault"
        ).exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"소스 신호 파일을 찾지 못했습니다: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path.name} JSON 파싱 실패: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{path.name} 최상위 구조가 객체가 아닙니다.")
    return payload


def _items(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    return [item for item in (payload.get(key) or []) if isinstance(item, dict)]


def _has_list(item: dict[str, Any], key: str) -> bool:
    return bool([value for value in (item.get(key) or []) if value])


def source_linkage_status(root: Path) -> dict[str, Any]:
    kcif = load_json(root / SYSTEM_DIR / "kcif_reports_watch.json")
    regional = load_json(root / SYSTEM_DIR / "regional_business_sources_watch.json")
    kcif_reports = _items(kcif, "reports")
    regional_items = _items(regional, "items")
    all_items = [
        *({"source_family": "KCIF", **item} for item in kcif_reports),
        *({"source_family": str(item.get("source_provider") or "REGIONAL"), **item} for item in regional_items),
    ]
    linked_items = [
        item
        for item in all_items
        if _has_list(item, "matched_themes") or _has_list(item, "target_matches") or item.get("portfolio_related")
    ]
    action_items = [item for item in all_items if str(item.get("recommended_action") or "").strip()]
    detail_ready = [
        item
        for item in kcif_reports
        if isinstance(item.get("detail_analysis"), dict)
        and item["detail_analysis"].get("raw_text_stored") is False
        and (
            item["detail_analysis"].get("source_summary_available")
            or _has_list(item["detail_analysis"], "derived_points")
        )
    ]
    family_counts: dict[str, int] = {}
    for item in all_items:
        family = str(item.get("source_family") or "UNKNOWN")
        family_counts[family] = family_counts.get(family, 0) + 1
    return {
        "kcif_count": len(kcif_reports),
        "regional_count": len(regional_items),
        "total_count": len(all_items),
        "linked_count": len(linked_items),
        "action_count": len(action_items),
        "kcif_detail_ready_count": len(detail_ready),
        "family_counts": dict(sorted(family_counts.items())),
        "sample_actions": [
            {
                "source": item.get("source_family"),
                "title": item.get("title"),
                "themes": item.get("matched_themes") or [],
                "target_count": len(item.get("target_matches") or []) if isinstance(item.get("target_matches"), list) else 0,
                "recommended_action": item.get("recommended_action"),
            }
            for item in sorted(
                action_items,
                key=lambda row: (
                    len(row.get("target_matches") or []) if isinstance(row.get("target_matches"), list) else 0,
                    float(row.get("relevance_score") or 0),
                ),
                reverse=True,
            )[:5]
        ],
    }


def strict_errors(
    status: dict[str, Any],
    *,
    min_kcif: int = 1,
    min_regional: int = 1,
    min_linked_ratio: float = 0.9,
    min_kcif_detail_ratio: float = 0.6,
) -> list[str]:
    errors: list[str] = []
    total_count = int(status.get("total_count") or 0)
    linked_count = int(status.get("linked_count") or 0)
    kcif_count = int(status.get("kcif_count") or 0)
    kcif_detail_ready_count = int(status.get("kcif_detail_ready_count") or 0)
    if int(status.get("kcif_count") or 0) < min_kcif:
        errors.append(f"KCIF 연결 자료가 {min_kcif}개 미만입니다.")
    if int(status.get("regional_count") or 0) < min_regional:
        errors.append(f"지역/매크로 연결 자료가 {min_regional}개 미만입니다.")
    if total_count and linked_count / total_count < min_linked_ratio:
        errors.append("테마/타깃 연결률이 기준보다 낮습니다.")
    if int(status.get("action_count") or 0) < max(1, min(kcif_count, min_kcif)):
        errors.append("recommended_action이 있는 매크로 소스가 부족합니다.")
    if kcif_count and kcif_detail_ready_count / kcif_count < min_kcif_detail_ratio:
        errors.append("KCIF 상세 신호 분석 또는 저작권 안전 플래그 커버리지가 기준보다 낮습니다.")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="KCIF/지역 매크로 소스의 시장일지·리스크 연결 신호를 점검합니다.")
    parser.add_argument("--strict", action="store_true", help="운영 품질 문제가 있으면 실패 코드로 종료")
    parser.add_argument("--min-kcif", type=int, default=1, help="최소 KCIF 연결 자료 수")
    parser.add_argument("--min-regional", type=int, default=1, help="최소 지역/매크로 연결 자료 수")
    parser.add_argument("--min-linked-ratio", type=float, default=0.9, help="테마/타깃 연결률 최소 기준")
    parser.add_argument("--min-kcif-detail-ratio", type=float, default=0.6, help="KCIF 상세 신호 분석 최소 커버리지")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    status = source_linkage_status(root)
    print(
        "매크로/지역 소스 연결 신호: "
        f"KCIF {status['kcif_count']}개 | "
        f"지역/매크로 {status['regional_count']}개 | "
        f"연결 {status['linked_count']}/{status['total_count']}개 | "
        f"권장 조치 {status['action_count']}개 | "
        f"KCIF 상세 {status['kcif_detail_ready_count']}개",
        flush=True,
    )
    family_label = ", ".join(f"{name}={count}" for name, count in status["family_counts"].items())
    print(f"출처 분포: {family_label or '없음'}", flush=True)
    for item in status["sample_actions"]:
        themes = ", ".join(str(theme) for theme in item["themes"][:4]) or "테마 없음"
        print(
            f"- [{item['source']}] {item['title']} | 테마 {themes} | "
            f"타깃 {item['target_count']}개 | {item['recommended_action']}",
            flush=True,
        )
    errors = strict_errors(
        status,
        min_kcif=args.min_kcif,
        min_regional=args.min_regional,
        min_linked_ratio=args.min_linked_ratio,
        min_kcif_detail_ratio=args.min_kcif_detail_ratio,
    )
    if errors:
        print("점검 오류:", flush=True)
        for error in errors:
            print(f"- {error}", flush=True)
    if args.strict and errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
