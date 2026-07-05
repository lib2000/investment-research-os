from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_OPENCLAW_DIR = Path.home() / ".openclaw" / "workspace" / "data" / "investment_research"
MODULE_NAME = "show_openclaw_bridge_status"
EXPECTED_READ_ORDER = [
    "bridge_status.json",
    "openclaw_first_read.md",
    "openclaw_first_read.json",
    "openclaw_bridge_manifest.json",
    "investment_research_context.md",
    "investment_research_context.json",
    "openclaw_knowledge_graph_blueprint.md",
    "openclaw_knowledge_graph_blueprint.json",
    "openclaw_knowledge_graph_nodes.json",
    "openclaw_knowledge_graph_edges.json",
    "openclaw_knowledge_graph_master_index.md",
    "openclaw_knowledge_graph_glossary.md",
    "openclaw_knowledge_graph_marginalia_queue.md",
    "openclaw_bridge_completion_report.md",
    "openclaw_bridge_completion_report.json",
]


def summarize_latest_recommendations(rows: list[dict]) -> list[dict]:
    summarized: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        summarized.append(
            {
                "market": row.get("market"),
                "rank": row.get("rank"),
                "ticker": row.get("ticker"),
                "company_name": row.get("company_name"),
                "score": row.get("score"),
                "baseline_price": row.get("baseline_price"),
                "currency": row.get("currency"),
            }
        )
    return sorted(
        summarized,
        key=lambda item: (str(item.get("market") or ""), int(item.get("rank") or 999)),
    )


def load_json(path: Path) -> dict:
    if not path.exists():
        raise AssertionError(f"required file missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise AssertionError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise AssertionError(f"JSON root must be an object: {path}")
    return payload


def build_status_summary(openclaw_dir: Path = DEFAULT_OPENCLAW_DIR) -> dict:
    status = load_json(openclaw_dir / "bridge_status.json")
    first_read = load_json(openclaw_dir / "openclaw_first_read.json")
    manifest = load_json(openclaw_dir / "openclaw_bridge_manifest.json")
    context = load_json(openclaw_dir / "investment_research_context.json")
    completion = load_json(openclaw_dir / "openclaw_bridge_completion_report.json")

    rec = ((context.get("current_state") or {}).get("daily_recommendations") or {})
    telegram = (((context.get("current_state") or {}).get("news_and_telegram") or {}).get("telegram_favorite_posts") or {})
    read_order = status.get("read_order") or manifest.get("read_order") or []
    market_counts = rec.get("latest_market_counts") or {}
    latest_recommendations = summarize_latest_recommendations(rec.get("latest_rows") or [])
    context_generated_at = context.get("generated_at")
    context_age_hours = None
    if context_generated_at:
        try:
            parsed_generated_at = datetime.fromisoformat(str(context_generated_at))
            if parsed_generated_at.tzinfo is not None:
                context_age_hours = round(
                    (datetime.now(timezone.utc) - parsed_generated_at.astimezone(timezone.utc)).total_seconds() / 3600,
                    3,
                )
        except ValueError:
            context_age_hours = None
    files_present = {str(name): (openclaw_dir / str(name)).exists() for name in read_order}
    errors: list[str] = []
    if status.get("status") != "ok":
        errors.append(f"bridge_status is not ok: {status.get('status')}")
    if completion.get("status") != "ok":
        errors.append(f"completion report is not ok: {completion.get('status')}")
    missing = [name for name, present in files_present.items() if not present]
    if missing:
        errors.append(f"read_order files missing: {', '.join(missing)}")
    if read_order != EXPECTED_READ_ORDER or manifest.get("read_order") != EXPECTED_READ_ORDER:
        errors.append("read_order does not match optimized OpenClaw consumer order")
    if manifest.get("first_read_file") != "openclaw_first_read.md":
        errors.append("manifest first_read_file mismatch")
    if manifest.get("first_read_json_file") != "openclaw_first_read.json":
        errors.append("manifest first_read_json_file mismatch")
    if first_read.get("schema") != "openclaw_investment_research_first_read_v1":
        errors.append("first_read schema mismatch")
    if first_read.get("generated_at") != context_generated_at:
        errors.append("first_read generated_at does not match context generated_at")
    if first_read.get("read_order") != EXPECTED_READ_ORDER:
        errors.append("first_read read_order mismatch")
    if first_read.get("latest_market_counts") != market_counts:
        errors.append("first_read market counts mismatch")
    if manifest.get("context_generated_at") != context_generated_at:
        errors.append("manifest context_generated_at does not match context generated_at")
    if status.get("context_generated_at") != context_generated_at:
        errors.append("bridge_status context_generated_at does not match context generated_at")
    expected_recommendation_count = sum(int(count or 0) for count in market_counts.values())
    if expected_recommendation_count and len(latest_recommendations) != expected_recommendation_count:
        errors.append(
            f"latest_recommendations count mismatch: {len(latest_recommendations)} != {expected_recommendation_count}"
        )
    first_read_rows = first_read.get("latest_recommendations") if isinstance(first_read.get("latest_recommendations"), list) else []
    if len(first_read_rows) != len(latest_recommendations):
        errors.append(f"first_read recommendations count mismatch: {len(first_read_rows)} != {len(latest_recommendations)}")
    return {
        "status": "ok" if not errors else "failure",
        "errors": errors,
        "openclaw_dir": str(openclaw_dir),
        "source_git": {
            "branch": status.get("source_git_branch"),
            "commit": status.get("source_git_commit"),
            "dirty": status.get("source_git_dirty"),
        },
        "copied_at": status.get("copied_at"),
        "context_generated_at": context_generated_at,
        "context_age_hours": context_age_hours,
        "first_read": {
            "schema": first_read.get("schema"),
            "generated_at": first_read.get("generated_at"),
            "read_this_first": first_read.get("read_this_first") is True,
            "latest_recommendation_date": first_read.get("latest_recommendation_date"),
            "latest_market_counts": first_read.get("latest_market_counts") or {},
            "latest_recommendation_count": len(first_read_rows),
        },
        "latest_recommendation_date": rec.get("latest_recommendation_date"),
        "latest_market_counts": market_counts,
        "latest_recommendations": latest_recommendations,
        "telegram_saved_count": telegram.get("saved_count"),
        "read_order": read_order,
        "read_order_files_present": files_present,
        "completion_report_sha256": status.get("completion_report_sha256") or {},
        "operational_commands": status.get("operational_commands") or {},
    }


def render_text(summary: dict) -> str:
    git = summary.get("source_git") or {}
    commands = summary.get("operational_commands") or {}
    market_counts = json.dumps(summary.get("latest_market_counts") or {}, ensure_ascii=False, separators=(",", ":"))
    lines = [
        f"OpenClaw bridge status: {summary.get('status')}",
        f"- dir: {summary.get('openclaw_dir')}",
        f"- source git: {git.get('branch')} {git.get('commit')} dirty={git.get('dirty')}",
        f"- copied_at: {summary.get('copied_at')}",
        f"- context_generated_at: {summary.get('context_generated_at')}",
        f"- context_age_hours: {summary.get('context_age_hours')}",
        f"- first_read: rows={(summary.get('first_read') or {}).get('latest_recommendation_count')} generated_at={(summary.get('first_read') or {}).get('generated_at')}",
        f"- latest_recommendation_date: {summary.get('latest_recommendation_date')}",
        f"- latest_market_counts: {market_counts}",
        f"- telegram_saved_count: {summary.get('telegram_saved_count')}",
        "- latest_recommendations:",
    ]
    for item in summary.get("latest_recommendations") or []:
        lines.append(
            "  {market}#{rank} {ticker} {name} score={score} baseline={baseline} {currency}".format(
                market=item.get("market"),
                rank=item.get("rank"),
                ticker=item.get("ticker"),
                name=item.get("company_name"),
                score=item.get("score"),
                baseline=item.get("baseline_price"),
                currency=item.get("currency"),
            )
        )
    lines.extend([
        "- read_order:",
    ])
    for index, item in enumerate(summary.get("read_order") or [], start=1):
        present = (summary.get("read_order_files_present") or {}).get(str(item))
        lines.append(f"  {index}. {item} present={present}")
    if commands:
        lines.append(f"- final_audit: {commands.get('final_completion_audit')}")
        lines.append(f"- offline_readiness: {commands.get('offline_readiness')}")
    if summary.get("errors"):
        lines.append("- errors:")
        for error in summary["errors"]:
            lines.append(f"  - {error}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Show concise OpenClaw Investment Research bridge status.")
    parser.add_argument("--openclaw-dir", type=Path, default=DEFAULT_OPENCLAW_DIR)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()
    try:
        summary = build_status_summary(args.openclaw_dir.resolve())
    except AssertionError as exc:
        summary = {"status": "failure", "errors": [str(exc)], "openclaw_dir": str(args.openclaw_dir.resolve())}
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(render_text(summary))
    return 0 if summary.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
