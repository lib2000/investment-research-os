"""Check whether market-journal linkage is reflected sanely in daily recommendations."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORE = PROJECT_ROOT / "research_vault" / "_system" / "daily_recommendations.json"
DEFAULT_TARGETS = PROJECT_ROOT / "research_vault" / "_system" / "interest_collection_targets.json"
MARKET_ORDER = {"KR": 0, "US": 1}
MARKET_REFERENCE_TOKENS = ("시장일지", "마감", "장세", "정책 신호 시장", "시장 참고")


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"JSON file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"JSON parse failed for {path}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"JSON object expected: {path}")
    return payload


def record_market(record: dict[str, Any]) -> str:
    market = str(record.get("market") or "").strip().upper()
    if market in MARKET_ORDER:
        return market
    currency = str(record.get("currency") or "").strip().upper()
    ticker = str(record.get("ticker") or "").strip()
    if currency == "KRW" or (ticker.isdigit() and len(ticker) == 6):
        return "KR"
    return "US"


def record_rank(record: dict[str, Any]) -> int:
    value = record.get("rank")
    return value if isinstance(value, int) else 999


def record_sort_key(record: dict[str, Any]) -> tuple[int, int, str]:
    return (MARKET_ORDER.get(record_market(record), 99), record_rank(record), str(record.get("ticker") or ""))


def latest_records(store_payload: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    records = [item for item in store_payload.get("records") or [] if isinstance(item, dict)]
    latest_date = str(store_payload.get("latest_recommendation_date") or "").strip()
    if not latest_date and records:
        latest_date = max(str(item.get("recommendation_date") or "") for item in records)
    latest = [
        item
        for item in records
        if str(item.get("recommendation_date") or "").strip() == latest_date
    ]
    return latest_date, sorted(latest, key=record_sort_key)


def target_rows(target_payload: dict[str, Any]) -> list[dict[str, Any]]:
    payload = target_payload.get("payload") if isinstance(target_payload.get("payload"), dict) else target_payload
    rows: list[dict[str, Any]] = []
    for key in ("ticker_targets", "sector_targets"):
        rows.extend(item for item in payload.get(key) or [] if isinstance(item, dict))
    return rows


def target_index(target_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in target_rows(target_payload):
        ticker = str(row.get("ticker") or "").strip().upper()
        name = str(row.get("name") or row.get("company_name") or "").strip().upper()
        if ticker:
            index[ticker] = row
        if name:
            index.setdefault(name, row)
    return index


def score_component_labels(record: dict[str, Any]) -> list[str]:
    return [
        str(component.get("label") or component.get("name") or "").strip()
        for component in (record.get("score_components") or [])
        if isinstance(component, dict) and str(component.get("label") or component.get("name") or "").strip()
    ]


def text_blob(record: dict[str, Any]) -> str:
    return "\n".join(
        str(item)
        for item in [
            *(record.get("reasons") or []),
            *(record.get("evidence_sources") or []),
            *score_component_labels(record),
        ]
        if str(item or "").strip()
    )


def has_market_reference(record: dict[str, Any]) -> bool:
    blob = text_blob(record)
    return any(token in blob for token in MARKET_REFERENCE_TOKENS)


def has_market_score_component(record: dict[str, Any]) -> bool:
    return any("시장일지" in label for label in score_component_labels(record))


def row_summary(record: dict[str, Any], row: dict[str, Any] | None) -> dict[str, Any]:
    matches = [item for item in (row or {}).get("market_journal_matches") or [] if isinstance(item, dict)]
    return {
        "market": record_market(record),
        "rank": record_rank(record),
        "ticker": record.get("ticker"),
        "company_name": record.get("company_name"),
        "score": record.get("score"),
        "target_linked": bool(matches),
        "target_match_count": len(matches),
        "has_market_score_component": has_market_score_component(record),
        "has_market_reference": has_market_reference(record),
        "score_component_count": len(score_component_labels(record)),
        "market_match_latest_session": max(
            (str(match.get("session_date") or "") for match in matches),
            default="",
        ),
    }


def build_status(
    store_path: Path,
    targets_path: Path,
    *,
    min_latest: int = 6,
    min_market_score_components: int = 3,
    min_market_references: int = 6,
) -> dict[str, Any]:
    store = read_json(store_path)
    targets = read_json(targets_path)
    latest_date, latest = latest_records(store)
    index = target_index(targets)
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[str] = []

    for record in latest:
        ticker = str(record.get("ticker") or "").strip().upper()
        row = index.get(ticker)
        if row is None:
            row = index.get(str(record.get("company_name") or "").strip().upper())
        rows.append(row_summary(record, row))

    linked_count = sum(1 for row in rows if row["target_linked"])
    market_component_count = sum(1 for row in rows if row["has_market_score_component"])
    market_reference_count = sum(1 for row in rows if row["has_market_reference"])
    market_counts = Counter(str(row.get("market") or "UNKNOWN") for row in rows)
    max_match_count = max((int(row.get("target_match_count") or 0) for row in rows), default=0)

    if len(latest) < min_latest:
        errors.append(f"latest recommendation count is low: {len(latest)} < {min_latest}")
    if linked_count < min(len(latest), min_latest):
        errors.append(f"market-journal target linkage missing: {linked_count}/{len(latest)}")
    if market_component_count < min_market_score_components:
        errors.append(
            "market-journal score component coverage is low: "
            f"{market_component_count} < {min_market_score_components}"
        )
    if market_reference_count < min_market_references:
        errors.append(
            "market-journal reference coverage is low: "
            f"{market_reference_count} < {min_market_references}"
        )
    if max_match_count > 5:
        warnings.append(f"some recommendation targets have many market-journal matches: max={max_match_count}")
    for row in rows:
        if row["has_market_score_component"] and not row["target_linked"]:
            errors.append(f"{row.get('ticker') or row.get('company_name')} has market-journal score without target linkage")

    return {
        "module": "daily_recommendation_market_journal_quality",
        "status": "error" if errors else "ok",
        "store_path": str(store_path),
        "targets_path": str(targets_path),
        "latest_recommendation_date": latest_date,
        "latest_count": len(latest),
        "latest_market_counts": dict(sorted(market_counts.items())),
        "linked_recommendation_count": linked_count,
        "market_score_component_count": market_component_count,
        "market_reference_count": market_reference_count,
        "max_target_match_count": max_match_count,
        "rows": rows,
        "errors": errors,
        "warnings": warnings,
    }


def render_text(status: dict[str, Any]) -> str:
    lines = [
        f"[{status.get('status')}] daily_recommendation_market_journal_quality",
        f"- latest: {status.get('latest_recommendation_date')} rows={status.get('latest_count')}",
        (
            "- coverage: "
            f"linked={status.get('linked_recommendation_count')}/{status.get('latest_count')} "
            f"score_components={status.get('market_score_component_count')} "
            f"references={status.get('market_reference_count')}"
        ),
        f"- market_counts: {status.get('latest_market_counts')}",
    ]
    for row in status.get("rows") or []:
        lines.append(
            "- "
            f"{row.get('market')}#{row.get('rank')} {row.get('ticker')} {row.get('company_name')} "
            f"linked={row.get('target_linked')} matches={row.get('target_match_count')} "
            f"score_component={row.get('has_market_score_component')} reference={row.get('has_market_reference')}"
        )
    for warning in status.get("warnings") or []:
        lines.append(f"- warning: {warning}")
    for error in status.get("errors") or []:
        lines.append(f"- error: {error}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check market-journal quality in latest daily recommendations.")
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    parser.add_argument("--targets-file", type=Path, default=DEFAULT_TARGETS)
    parser.add_argument("--min-latest", type=int, default=6)
    parser.add_argument("--min-market-score-components", type=int, default=3)
    parser.add_argument("--min-market-references", type=int, default=6)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    store = args.store if args.store.is_absolute() else PROJECT_ROOT / args.store
    targets = args.targets_file if args.targets_file.is_absolute() else PROJECT_ROOT / args.targets_file
    status = build_status(
        store,
        targets,
        min_latest=max(1, args.min_latest),
        min_market_score_components=max(0, args.min_market_score_components),
        min_market_references=max(0, args.min_market_references),
    )
    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
    else:
        print(render_text(status))
    return 0 if status.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
