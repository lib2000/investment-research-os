"""Summarize market-journal linkage coverage for interest and portfolio targets."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGETS = PROJECT_ROOT / "research_vault" / "_system" / "interest_collection_targets.json"


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"targets file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"targets JSON parse failed: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"targets JSON object expected: {path}")
    return payload


def rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key)
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def target_label(row: dict[str, Any]) -> str:
    return " ".join(
        str(row.get(key) or "").strip()
        for key in ("ticker", "company_name", "name")
        if str(row.get(key) or "").strip()
    ).strip()


def parse_session_date(value: Any) -> date | None:
    text = str(value or "").strip()[:10]
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def summarize_group(group_rows: list[dict[str, Any]], *, sample_limit: int) -> dict[str, Any]:
    linked = []
    unlinked = []
    market_counts: Counter[str] = Counter()
    latest_session = ""
    match_count = 0
    for row in group_rows:
        matches = [item for item in row.get("market_journal_matches") or [] if isinstance(item, dict)]
        label = target_label(row)
        if matches:
            linked.append(row)
        else:
            unlinked.append(row)
        match_count += len(matches)
        for match in matches:
            market = str(match.get("market") or "UNKNOWN").strip().upper() or "UNKNOWN"
            market_counts[market] += 1
            session_date = str(match.get("session_date") or "").strip()
            if session_date > latest_session:
                latest_session = session_date
        row["_linkage_label"] = label
    total = len(group_rows)
    latest_date = parse_session_date(latest_session)
    latest_age_days = (date.today() - latest_date).days if latest_date else None
    return {
        "target_count": total,
        "linked_count": len(linked),
        "unlinked_count": len(unlinked),
        "linked_ratio": len(linked) / total if total else 0.0,
        "match_count": match_count,
        "market_counts": dict(sorted(market_counts.items())),
        "latest_session_date": latest_session,
        "latest_session_age_days": latest_age_days,
        "linked_samples": [str(row.get("_linkage_label") or "") for row in linked[:sample_limit]],
        "unlinked_samples": [str(row.get("_linkage_label") or "") for row in unlinked[:sample_limit]],
    }


def build_status(path: Path, *, sample_limit: int) -> dict[str, Any]:
    root = read_json(path)
    payload = root.get("payload") if isinstance(root.get("payload"), dict) else root
    ticker_rows = rows(payload, "ticker_targets")
    sector_rows = rows(payload, "sector_targets")
    all_rows = [*ticker_rows, *sector_rows]
    return {
        "status": "ok",
        "targets_file": str(path),
        "updated_at": root.get("updated_at") or payload.get("as_of"),
        "total": summarize_group(all_rows, sample_limit=sample_limit),
        "tickers": summarize_group(ticker_rows, sample_limit=sample_limit),
        "sectors": summarize_group(sector_rows, sample_limit=sample_limit),
    }


def strict_errors(status: dict[str, Any], *, min_linked_ratio: float, max_latest_age_days: int) -> list[str]:
    errors: list[str] = []
    total = status.get("total") if isinstance(status.get("total"), dict) else {}
    ratio = float(total.get("linked_ratio") or 0.0)
    if ratio < min_linked_ratio:
        errors.append(f"market journal linkage ratio is low: {ratio:.1%} < {min_linked_ratio:.1%}")
    age = total.get("latest_session_age_days")
    if age is None:
        errors.append("market journal latest session date is missing")
    elif int(age) > max_latest_age_days:
        errors.append(f"market journal latest session is stale: {age}d > {max_latest_age_days}d")
    if int(total.get("target_count") or 0) <= 0:
        errors.append("market journal linkage has no targets")
    return errors


def render_text(status: dict[str, Any]) -> str:
    total = status.get("total") if isinstance(status.get("total"), dict) else {}
    tickers = status.get("tickers") if isinstance(status.get("tickers"), dict) else {}
    sectors = status.get("sectors") if isinstance(status.get("sectors"), dict) else {}
    return "\n".join(
        [
            f"[{status.get('status')}] market_journal_linkage",
            f"- updated_at: {status.get('updated_at')}",
            (
                "- total: "
                f"{total.get('linked_count')}/{total.get('target_count')} "
                f"({float(total.get('linked_ratio') or 0):.1%}) "
                f"matches={total.get('match_count')} latest={total.get('latest_session_date')}"
            ),
            (
                "- tickers: "
                f"{tickers.get('linked_count')}/{tickers.get('target_count')} "
                f"unlinked={tickers.get('unlinked_count')}"
            ),
            (
                "- sectors: "
                f"{sectors.get('linked_count')}/{sectors.get('target_count')} "
                f"unlinked={sectors.get('unlinked_count')}"
            ),
            "- unlinked samples: " + ", ".join(str(item) for item in (total.get("unlinked_samples") or [])[:8]),
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Check market-journal linkage coverage for collection targets.")
    parser.add_argument("--targets-file", type=Path, default=DEFAULT_TARGETS)
    parser.add_argument("--sample-limit", type=int, default=10)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--min-linked-ratio", type=float, default=0.45)
    parser.add_argument("--max-latest-age-days", type=int, default=7)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    path = args.targets_file if args.targets_file.is_absolute() else PROJECT_ROOT / args.targets_file
    status = build_status(path, sample_limit=max(1, args.sample_limit))
    errors = strict_errors(
        status,
        min_linked_ratio=args.min_linked_ratio,
        max_latest_age_days=args.max_latest_age_days,
    )
    if args.strict and errors:
        status["status"] = "error"
    status["errors"] = errors if args.strict else []
    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
    else:
        print(render_text(status))
        for error in status["errors"]:
            print(f"- error: {error}")
    return 0 if status.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
