"""Validate the copyright-safe KIS global research listing cache locally."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SYSTEM_DIR = Path("research_vault/_system")
EXPECTED_SOURCE_PREFIX = "https://securities.koreainvestment.com/"
FORBIDDEN_KEYS = {
    "body_sub",
    "raw_html",
    "pdf_content",
    "pdf_text",
    "full_text",
    "original_content",
    "raw_text",
}


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (
            candidate / "research_vault"
        ).exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def load_cache(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"KIS 글로벌 리서치 상태 파일을 찾지 못했습니다: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"KIS 글로벌 리서치 상태 JSON 파싱 실패: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("KIS 글로벌 리서치 상태 최상위 구조가 객체가 아닙니다.")
    return payload


def find_forbidden_key(value: Any, path: str = "$") -> str | None:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in FORBIDDEN_KEYS:
                return f"{path}.{key}"
            nested = find_forbidden_key(item, f"{path}.{key}")
            if nested:
                return nested
    elif isinstance(value, list):
        for index, item in enumerate(value):
            nested = find_forbidden_key(item, f"{path}[{index}]")
            if nested:
                return nested
    return None


def age_hours(value: Any) -> float | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds() / 3600


def main() -> int:
    parser = argparse.ArgumentParser(description="KIS 글로벌 리서치 목록 메타데이터 저장 정책을 점검합니다.")
    parser.add_argument("--strict", action="store_true", help="경고가 있으면 종료 코드 1")
    parser.add_argument("--max-age-hours", type=float, default=30.0, help="최신성 기준")
    parser.add_argument("--json", action="store_true", help="JSON으로 출력")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    cache = load_cache(root / SYSTEM_DIR / "kis_global_research_cache.json")
    entries = cache.get("entries") if isinstance(cache.get("entries"), dict) else {}
    policy = cache.get("source_policy") if isinstance(cache.get("source_policy"), dict) else {}
    rows = [row for row in entries.values() if isinstance(row, dict)]
    issues: list[str] = []

    if cache.get("status") not in {"success", "partial_success"}:
        issues.append(f"최근 수집 상태 확인 필요: {cache.get('status') or '미확인'}")
    if not str(cache.get("source_url") or "").startswith(EXPECTED_SOURCE_PREFIX):
        issues.append("출처 URL이 한국투자증권 공개 리서치 목록이 아닙니다.")
    if policy.get("full_text_stored") is not False or policy.get("pdf_auto_downloaded") is not False or policy.get("login_bypass") is not False:
        issues.append("원문/PDF/로그인 우회 저장 정책이 불명확합니다.")
    forbidden_path = find_forbidden_key(cache)
    if forbidden_path:
        issues.append(f"금지된 원문 필드가 캐시에 있습니다: {forbidden_path}")
    missing_metadata = [
        str(row.get("item_id") or row.get("title") or "항목 미확인")
        for row in rows
        if not all(str(row.get(field) or "").strip() for field in ("item_id", "title", "category", "source", "source_url", "access_scope"))
    ]
    if missing_metadata:
        issues.append(f"필수 메타데이터 누락 {len(missing_metadata)}건")
    if any(row.get("access_scope") != "listing_metadata_only" for row in rows):
        issues.append("목록 메타데이터 범위를 벗어난 항목이 있습니다.")
    freshness = age_hours(cache.get("updated_at"))
    if freshness is None or freshness > max(float(args.max_age_hours), 1.0):
        issues.append("KIS 글로벌 리서치 캐시 최신성 확인 필요")

    result = {
        "status": "ok" if not issues else "needs_attention",
        "entry_count": len(rows),
        "updated_at": cache.get("updated_at"),
        "age_hours": freshness,
        "issues": issues,
        "cache_path": str(root / SYSTEM_DIR / "kis_global_research_cache.json"),
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            "KIS 글로벌 리서치 저장 상태: "
            f"{result['status']} | 항목 {result['entry_count']}개 | "
            f"갱신 {result['updated_at'] or '미확인'}"
        )
        for issue in issues:
            print(f"- {issue}")
    return 1 if args.strict and issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
