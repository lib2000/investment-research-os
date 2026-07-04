"""뉴스 인박스 우선 분류 큐를 백엔드 없이 검증합니다."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any


SYSTEM_DIR = Path("research_vault/_system")


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (
            candidate / "research_vault"
        ).exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def load_news_inbox_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"뉴스 인박스 파일을 찾지 못했습니다: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"뉴스 인박스 JSON 파싱 실패: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("뉴스 인박스 최상위 구조가 객체가 아닙니다.")
    items = payload.get("items")
    if not isinstance(items, list):
        raise SystemExit("뉴스 인박스 items 구조가 배열이 아닙니다.")
    return payload


def _news_inbox_module(root: Path):
    backend_dir = root / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    from research_os import news_inbox

    return news_inbox


def _runtime():
    return SimpleNamespace(storage_quality_entry_is_policy_url_only=is_policy_url_only_item)


def is_policy_url_only_item(item: dict[str, Any]) -> bool:
    tags = {str(tag).lower() for tag in (item.get("tags") or [])}
    return (
        (item.get("is_policy_law") or item.get("scope") == "POLICY" or "policy_law" in tags)
        and bool(item.get("source_url"))
        and not str(item.get("safe_user_note") or item.get("raw_content") or "").strip()
    )


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def console_print(value: str = "") -> None:
    try:
        print(value, flush=True)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        print(value.encode(encoding, errors="replace").decode(encoding, errors="replace"), flush=True)


def priority_reason(item: dict[str, Any]) -> str:
    reasons: list[str] = []
    target_matches = item.get("target_matches")
    if isinstance(target_matches, list) and target_matches:
        labels = [
            str(match.get("label") or match.get("name") or match.get("ticker") or "").strip()
            for match in target_matches
            if isinstance(match, dict)
        ]
        reasons.append("타깃 매칭" + (f"({', '.join(label for label in labels if label)})" if labels else ""))
    relevance_score = _number(item.get("relevance_score"))
    if relevance_score >= 30:
        reasons.append(f"관련도 {relevance_score:g}")
    if item.get("market_journal_candidate"):
        reasons.append("시장일지 후보")
    if item.get("is_policy_law") or item.get("scope") == "POLICY":
        reasons.append("정책/법령/규제")
    tags = {str(tag).lower() for tag in (item.get("tags") or [])}
    telegram_popularity = item.get("telegram_popularity") if isinstance(item.get("telegram_popularity"), dict) else {}
    telegram_views = _number(telegram_popularity.get("view_count") or telegram_popularity.get("popularity_score"))
    if "telegram_favorite" in tags or str(item.get("scope_reason") or "") == "telegram_favorite_popular_post":
        reasons.append(f"텔레그램 인기글 조회 {telegram_views:g}")
    return ", ".join(reasons) or "우선 분류 기준 충족"


def build_priority_queue_status(root: Path, limit: int = 7) -> dict[str, Any]:
    payload = load_news_inbox_payload(root / SYSTEM_DIR / "news_inbox.json")
    news_inbox = _news_inbox_module(root)
    items = [
        news_inbox.apply_news_policy_law_classification(dict(item))
        for item in payload.get("items", [])
        if isinstance(item, dict)
    ]
    counts = news_inbox.news_filter_counts(_runtime(), items)
    priority_items = news_inbox.filter_news_inbox_items(_runtime(), items, "actionable")
    priority_items = sorted(priority_items, key=news_inbox.news_priority_sort_key, reverse=True)
    policy_priority_count = sum(
        1 for item in priority_items if item.get("is_policy_law") or item.get("scope") == "POLICY"
    )
    target_matched_count = sum(
        1 for item in priority_items if isinstance(item.get("target_matches"), list) and item.get("target_matches")
    )
    telegram_total_count = sum(
        1
        for item in items
        if "telegram_favorite" in {str(tag).lower() for tag in (item.get("tags") or [])}
        or str(item.get("scope_reason") or "") == "telegram_favorite_popular_post"
    )
    telegram_priority_count = sum(
        1
        for item in priority_items
        if "telegram_favorite" in {str(tag).lower() for tag in (item.get("tags") or [])}
        or str(item.get("scope_reason") or "") == "telegram_favorite_popular_post"
    )
    quality_issue_count = counts.get("quality_issue", 0)
    duplicate_groups = news_inbox.duplicate_priority_news_groups(priority_items)
    queue = [
        {
            "rank": index,
            "id": item.get("id"),
            "title": str(item.get("title") or "").strip(),
            "source_url": str(item.get("source_url") or "").strip(),
            "scope": str(item.get("scope") or "INBOX").strip(),
            "scope_label": item.get("scope_label") or news_inbox.news_scope_label(str(item.get("scope") or "INBOX")),
            "relevance_score": _number(item.get("relevance_score")),
            "target_match_count": len(item.get("target_matches") or []) if isinstance(item.get("target_matches"), list) else 0,
            "is_policy_law": bool(item.get("is_policy_law") or item.get("scope") == "POLICY"),
            "market_journal_candidate": bool(item.get("market_journal_candidate")),
            "is_telegram_favorite": "telegram_favorite" in {str(tag).lower() for tag in (item.get("tags") or [])}
            or str(item.get("scope_reason") or "") == "telegram_favorite_popular_post",
            "reason": priority_reason(item),
        }
        for index, item in enumerate(priority_items[: max(1, min(int(limit or 7), 30))], start=1)
    ]
    return {
        "updated_at": payload.get("updated_at"),
        "total_count": len(items),
        "filter_counts": counts,
        "priority_count": len(priority_items),
        "display_count": len(queue),
        "policy_priority_count": policy_priority_count,
        "target_matched_count": target_matched_count,
        "telegram_total_count": telegram_total_count,
        "telegram_priority_count": telegram_priority_count,
        "quality_issue_count": quality_issue_count,
        "duplicate_priority_group_count": len(duplicate_groups),
        "duplicate_priority_entry_count": sum(int(group["count"]) for group in duplicate_groups),
        "duplicate_priority_groups": duplicate_groups,
        "queue": queue,
    }


def strict_errors(status: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if status.get("total_count", 0) <= 0:
        errors.append("뉴스 인박스 항목이 없습니다.")
    counts = status.get("filter_counts") if isinstance(status.get("filter_counts"), dict) else {}
    if status.get("priority_count", 0) != counts.get("actionable", 0):
        errors.append("우선 분류 개수와 필터 카운트가 일치하지 않습니다.")
    if status.get("telegram_total_count", 0) > 0 and status.get("telegram_priority_count", 0) <= 0:
        errors.append("텔레그램 인기글이 뉴스 우선 분류에 반영되지 않았습니다.")
    for item in status.get("queue") or []:
        title = str(item.get("title") or "").strip()
        source_url = str(item.get("source_url") or "").strip()
        if not title:
            errors.append(f"{item.get('rank')}위 우선 뉴스 제목이 비어 있습니다.")
        if not source_url.startswith(("http://", "https://")):
            errors.append(f"{item.get('rank')}위 우선 뉴스 URL이 유효하지 않습니다.")
        if item.get("is_policy_law") and str(item.get("scope") or "") != "POLICY":
            errors.append(f"{item.get('rank')}위 정책/법령 뉴스 scope가 POLICY가 아닙니다.")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="뉴스 인박스 우선 분류 큐를 백엔드 없이 점검합니다.")
    parser.add_argument("--limit", type=int, default=8, help="표시할 우선 뉴스 수")
    parser.add_argument("--strict", action="store_true", help="운영 품질 문제가 있으면 실패 코드로 종료")
    parser.add_argument("--json", action="store_true", help="점검 결과를 JSON으로 출력")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    status = build_priority_queue_status(root, limit=args.limit)
    errors = strict_errors(status)
    result = {"status": "failure" if errors else "success", "errors": errors, **status}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    else:
        console_print(
            "뉴스 인박스 우선 분류: "
            f"전체 {status['total_count']}개, "
            f"미승격 {status['filter_counts'].get('unpromoted', 0)}개, "
            f"우선 {status['priority_count']}개, "
            f"정책/법령 우선 {status['policy_priority_count']}개, "
            f"타깃 매칭 {status['target_matched_count']}개, "
            f"텔레그램 우선 {status['telegram_priority_count']}/{status['telegram_total_count']}개, "
            f"품질 확인 {status['quality_issue_count']}개, "
            f"우선 중복 후보 {status['duplicate_priority_group_count']}묶음",
        )
        if status.get("updated_at"):
            console_print(f"업데이트: {status['updated_at']}")
        for item in status["queue"]:
            console_print(
                f"- {item['rank']}위 [{item['scope_label']}] {item['title']} "
                f"| 점수 {item['relevance_score']:g} | {item['reason']} | {item['source_url']}",
            )
        for group in status["duplicate_priority_groups"]:
            ids = ", ".join(str(item).strip() for item in group.get("ids", []) if str(item or "").strip())
            id_note = f" | ids {ids}" if ids else ""
            console_print(
                f"중복 후보: {group['count']}개 | {group['canonical_url']} | "
                f"{' / '.join(group['titles'])}{id_note}",
            )
    if errors and not args.json:
        console_print("점검 오류:")
        for error in errors:
            console_print(f"- {error}")
    if args.strict and errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
