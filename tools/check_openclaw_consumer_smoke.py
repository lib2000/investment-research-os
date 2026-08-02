from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workspace_paths import openclaw_investment_dir

DEFAULT_OPENCLAW_DIR = openclaw_investment_dir()
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
JSON_FILES = {
    "bridge_status.json",
    "openclaw_first_read.json",
    "openclaw_bridge_manifest.json",
    "investment_research_context.json",
    "openclaw_knowledge_graph_blueprint.json",
    "openclaw_knowledge_graph_nodes.json",
    "openclaw_knowledge_graph_edges.json",
    "openclaw_bridge_completion_report.json",
}
JSON_LIST_FILES = {
    "openclaw_knowledge_graph_nodes.json",
    "openclaw_knowledge_graph_edges.json",
}
SENSITIVE_MARKERS = [
    f'"access_{"token"}":',
    f'"refresh_{"token"}":',
    f'"id_{"token"}":',
    f'"client_{"secret"}":',
    f'"service_role_{"key"}":',
    f'"private_{"key"}":',
    "-----BEGIN " + "PRIVATE KEY-----",
]


def load_text(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"required OpenClaw consumer file missing: {path}")
    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        raise AssertionError(f"required OpenClaw consumer file is empty: {path}")
    return text


def load_json_file(path: Path) -> dict[str, Any]:
    text = load_text(path)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"OpenClaw consumer JSON parse failed: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise AssertionError(f"OpenClaw consumer JSON root must be object: {path}")
    return payload


def load_json_list_file(path: Path) -> list[Any]:
    text = load_text(path)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"OpenClaw consumer JSON parse failed: {path}: {exc}") from exc
    if not isinstance(payload, list):
        raise AssertionError(f"OpenClaw consumer JSON root must be list: {path}")
    return payload


def sha256_hex(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_timestamp(value: Any) -> datetime:
    if not value:
        raise AssertionError("OpenClaw consumer timestamp missing")
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise AssertionError(f"OpenClaw consumer timestamp invalid: {value}") from exc
    if parsed.tzinfo is None:
        raise AssertionError(f"OpenClaw consumer timestamp must include timezone: {value}")
    return parsed


def recommendation_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "market": row.get("market"),
        "rank": row.get("rank"),
        "ticker": row.get("ticker"),
        "company_name": row.get("company_name"),
        "score": row.get("score"),
        "baseline_price": row.get("baseline_price"),
        "currency": row.get("currency"),
    }


def sorted_recommendations(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [recommendation_summary(row) for row in rows if isinstance(row, dict)],
        key=lambda item: (str(item.get("market") or ""), int(item.get("rank") or 999)),
    )


def validate_hashes(openclaw_dir: Path, status: dict[str, Any], errors: list[str]) -> None:
    expected_file_hashes = {
        "first_read_json": "openclaw_first_read.json",
        "first_read_markdown": "openclaw_first_read.md",
        "context_json": "investment_research_context.json",
        "context_markdown": "investment_research_context.md",
        "knowledge_graph_blueprint_json": "openclaw_knowledge_graph_blueprint.json",
        "knowledge_graph_blueprint_markdown": "openclaw_knowledge_graph_blueprint.md",
        "knowledge_graph_nodes": "openclaw_knowledge_graph_nodes.json",
        "knowledge_graph_edges": "openclaw_knowledge_graph_edges.json",
        "knowledge_graph_master_index": "openclaw_knowledge_graph_master_index.md",
        "knowledge_graph_glossary": "openclaw_knowledge_graph_glossary.md",
        "knowledge_graph_marginalia": "openclaw_knowledge_graph_marginalia_queue.md",
        "bridge_manifest": "openclaw_bridge_manifest.json",
    }
    file_hashes = status.get("file_sha256") if isinstance(status.get("file_sha256"), dict) else {}
    for key, filename in expected_file_hashes.items():
        expected = str(file_hashes.get(key) or "").lower()
        actual_path = openclaw_dir / filename
        if not expected:
            errors.append(f"bridge_status missing file_sha256.{key}")
        elif not actual_path.exists() or expected != sha256_hex(actual_path):
            errors.append(f"bridge_status file_sha256 mismatch for {key}")

    expected_report_hashes = {
        "completion_report_json": "openclaw_bridge_completion_report.json",
        "completion_report_markdown": "openclaw_bridge_completion_report.md",
    }
    report_hashes = status.get("completion_report_sha256") if isinstance(status.get("completion_report_sha256"), dict) else {}
    for key, filename in expected_report_hashes.items():
        expected = str(report_hashes.get(key) or "").lower()
        actual_path = openclaw_dir / filename
        if not expected:
            errors.append(f"bridge_status missing completion_report_sha256.{key}")
        elif not actual_path.exists() or expected != sha256_hex(actual_path):
            errors.append(f"bridge_status completion_report_sha256 mismatch for {key}")


def build_result(
    openclaw_dir: Path = DEFAULT_OPENCLAW_DIR,
    *,
    max_age_hours: float = 1.0,
    expected_latest_count: int = 6,
    allow_working_tree: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []
    loaded_files: dict[str, dict[str, Any] | list[Any] | str] = {}
    loaded_file_names: list[str] = []

    try:
        status = load_json_file(openclaw_dir / "bridge_status.json")
    except AssertionError as exc:
        return {
            "status": "failure",
            "errors": [str(exc)],
            "openclaw_dir": str(openclaw_dir),
            "loaded_files": [],
        }

    read_order = status.get("read_order") if isinstance(status.get("read_order"), list) else []
    if read_order != EXPECTED_READ_ORDER:
        errors.append("OpenClaw consumer read_order mismatch")

    for filename in read_order or EXPECTED_READ_ORDER:
        path = openclaw_dir / str(filename)
        try:
            if str(filename) in JSON_FILES:
                if str(filename) in JSON_LIST_FILES:
                    loaded_files[str(filename)] = load_json_list_file(path)
                else:
                    loaded_files[str(filename)] = load_json_file(path)
            else:
                loaded_files[str(filename)] = load_text(path)
            loaded_file_names.append(str(filename))
        except AssertionError as exc:
            errors.append(str(exc))

    manifest = loaded_files.get("openclaw_bridge_manifest.json")
    first_read = loaded_files.get("openclaw_first_read.json")
    context = loaded_files.get("investment_research_context.json")
    knowledge_graph_blueprint = loaded_files.get("openclaw_knowledge_graph_blueprint.json")
    knowledge_graph_nodes = loaded_files.get("openclaw_knowledge_graph_nodes.json")
    knowledge_graph_edges = loaded_files.get("openclaw_knowledge_graph_edges.json")
    completion = loaded_files.get("openclaw_bridge_completion_report.json")
    context_markdown = str(loaded_files.get("investment_research_context.md") or "")
    first_read_markdown = str(loaded_files.get("openclaw_first_read.md") or "")
    knowledge_graph_markdown = str(loaded_files.get("openclaw_knowledge_graph_blueprint.md") or "")
    knowledge_graph_master_index = str(loaded_files.get("openclaw_knowledge_graph_master_index.md") or "")
    knowledge_graph_glossary = str(loaded_files.get("openclaw_knowledge_graph_glossary.md") or "")
    knowledge_graph_marginalia = str(loaded_files.get("openclaw_knowledge_graph_marginalia_queue.md") or "")
    completion_markdown = str(loaded_files.get("openclaw_bridge_completion_report.md") or "")

    if status.get("status") != "ok":
        errors.append(f"bridge_status is not ok: {status.get('status')}")
    copied_at = parse_timestamp(status.get("copied_at"))
    age_hours = (datetime.now(timezone.utc) - copied_at.astimezone(timezone.utc)).total_seconds() / 3600
    if age_hours > max_age_hours:
        errors.append(f"OpenClaw consumer bridge copy is stale: {age_hours:.2f}h > {max_age_hours:.2f}h")
    if status.get("source_git_dirty") is not False and not allow_working_tree:
        errors.append("OpenClaw consumer source_git_dirty must be false")
    if status.get("secrets_excluded") is not True:
        errors.append("OpenClaw consumer bridge_status must confirm secrets_excluded=true")

    if isinstance(manifest, dict):
        if manifest.get("read_order") != EXPECTED_READ_ORDER:
            errors.append("OpenClaw consumer manifest read_order mismatch")
        if manifest.get("first_read_file") != "openclaw_first_read.md":
            errors.append("OpenClaw consumer manifest missing first-read markdown")
        if manifest.get("first_read_json_file") != "openclaw_first_read.json":
            errors.append("OpenClaw consumer manifest missing first-read JSON")
        if manifest.get("knowledge_graph_blueprint_file") != "openclaw_knowledge_graph_blueprint.md":
            errors.append("OpenClaw consumer manifest missing knowledge graph blueprint markdown")
        if manifest.get("knowledge_graph_blueprint_json_file") != "openclaw_knowledge_graph_blueprint.json":
            errors.append("OpenClaw consumer manifest missing knowledge graph blueprint JSON")
        graph_files = manifest.get("knowledge_graph_files") if isinstance(manifest.get("knowledge_graph_files"), dict) else {}
        for key, expected in {
            "nodes": "openclaw_knowledge_graph_nodes.json",
            "edges": "openclaw_knowledge_graph_edges.json",
            "master_index": "openclaw_knowledge_graph_master_index.md",
            "glossary": "openclaw_knowledge_graph_glossary.md",
            "marginalia": "openclaw_knowledge_graph_marginalia_queue.md",
        }.items():
            if graph_files.get(key) != expected:
                errors.append(f"OpenClaw consumer manifest missing knowledge graph file: {key}")
    else:
        errors.append("OpenClaw consumer manifest did not load")

    if isinstance(first_read, dict):
        if first_read.get("schema") != "openclaw_investment_research_first_read_v1":
            errors.append("OpenClaw consumer first-read schema mismatch")
        if first_read.get("read_order") != EXPECTED_READ_ORDER:
            errors.append("OpenClaw consumer first-read read_order mismatch")
    else:
        errors.append("OpenClaw consumer first-read JSON did not load")

    latest_recommendations: list[dict[str, Any]] = []
    market_counts: dict[str, Any] = {}
    latest_recommendation_date = ""
    telegram_saved_count = None
    if isinstance(context, dict):
        rec = ((context.get("current_state") or {}).get("daily_recommendations") or {})
        telegram = (((context.get("current_state") or {}).get("news_and_telegram") or {}).get("telegram_favorite_posts") or {})
        market_counts = rec.get("latest_market_counts") if isinstance(rec.get("latest_market_counts"), dict) else {}
        latest_recommendations = sorted_recommendations(rec.get("latest_rows") if isinstance(rec.get("latest_rows"), list) else [])
        latest_recommendation_date = str(rec.get("latest_recommendation_date") or "")
        telegram_saved_count = telegram.get("saved_count")
        if status.get("context_generated_at") != context.get("generated_at"):
            errors.append("OpenClaw consumer context_generated_at mismatch")
        if isinstance(manifest, dict) and manifest.get("context_generated_at") != context.get("generated_at"):
            errors.append("OpenClaw consumer manifest context_generated_at mismatch")
    else:
        errors.append("OpenClaw consumer context did not load")

    if isinstance(knowledge_graph_blueprint, dict):
        if knowledge_graph_blueprint.get("schema") != "openclaw_personal_knowledge_graph_blueprint_v1":
            errors.append("OpenClaw consumer knowledge graph blueprint schema mismatch")
        seed_ids = {
            str(item.get("id") or "")
            for item in knowledge_graph_blueprint.get("seed_nodes", [])
            if isinstance(item, dict)
        }
        for required_seed in (
            "concept.relu",
            "topic.graph_rendering_8000_nodes",
            "note.graph_rendering_lod_experiment",
        ):
            if required_seed not in seed_ids:
                errors.append(f"OpenClaw consumer knowledge graph blueprint missing seed: {required_seed}")
    else:
        errors.append("OpenClaw consumer knowledge graph blueprint did not load")

    if isinstance(knowledge_graph_nodes, list):
        graph_node_ids = {
            str(item.get("id") or "")
            for item in knowledge_graph_nodes
            if isinstance(item, dict)
        }
        for required_seed in (
            "concept.relu",
            "topic.graph_rendering_8000_nodes",
            "note.graph_rendering_lod_experiment",
        ):
            if required_seed not in graph_node_ids:
                errors.append(f"OpenClaw consumer knowledge graph nodes missing seed: {required_seed}")
    else:
        errors.append("OpenClaw consumer knowledge graph nodes did not load")
    if not isinstance(knowledge_graph_edges, list) or not knowledge_graph_edges:
        errors.append("OpenClaw consumer knowledge graph edges did not load")

    if isinstance(completion, dict):
        if completion.get("status") != "ok":
            errors.append(f"OpenClaw consumer completion report is not ok: {completion.get('status')}")
    else:
        errors.append("OpenClaw consumer completion report did not load")

    expected_from_counts = sum(int(value or 0) for value in market_counts.values()) if market_counts else expected_latest_count
    expected_count = expected_latest_count or expected_from_counts
    if len(latest_recommendations) != expected_count:
        errors.append(f"OpenClaw consumer latest recommendation count mismatch: {len(latest_recommendations)} != {expected_count}")
    if expected_from_counts and len(latest_recommendations) != expected_from_counts:
        errors.append(
            f"OpenClaw consumer market count mismatch: {len(latest_recommendations)} != {expected_from_counts}"
        )
    status_latest = status.get("latest_recommendations") if isinstance(status.get("latest_recommendations"), list) else []
    if status_latest and sorted_recommendations(status_latest) != latest_recommendations:
        errors.append("OpenClaw consumer bridge_status latest_recommendations mismatch")

    if "latest recommendations" not in context_markdown.lower() and "최신 추천" not in context_markdown:
        errors.append("OpenClaw consumer markdown missing latest recommendations")
    if "OpenClaw Investment Research First Read" not in first_read_markdown:
        errors.append("OpenClaw consumer first-read markdown missing title")
    if "Latest Recommendations" not in first_read_markdown or "Safety" not in first_read_markdown:
        errors.append("OpenClaw consumer first-read markdown missing compact sections")
    if "secrets, broker tokens, raw DB files" not in context_markdown and "민감정보" not in context_markdown:
        errors.append("OpenClaw consumer markdown missing sensitive-data exclusion note")
    if "Master Index" not in knowledge_graph_markdown or "concept.relu" not in knowledge_graph_markdown:
        errors.append("OpenClaw consumer knowledge graph markdown missing expected blueprint content")
    if "topic.graph_rendering_8000_nodes" not in knowledge_graph_master_index:
        errors.append("OpenClaw consumer knowledge graph master index missing topic node")
    if "concept.relu" not in knowledge_graph_glossary or "definition:" not in knowledge_graph_glossary:
        errors.append("OpenClaw consumer knowledge graph glossary missing concept definition")
    if "note.graph_rendering_lod_experiment" not in knowledge_graph_marginalia:
        errors.append("OpenClaw consumer knowledge graph marginalia missing note")
    if "completion_report_sha256" not in completion_markdown and "File Hashes" not in completion_markdown:
        errors.append("OpenClaw consumer completion markdown missing completion hashes")

    combined_text = "\n".join(
        value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        for value in loaded_files.values()
    )
    for marker in SENSITIVE_MARKERS:
        if marker.lower() in combined_text.lower():
            errors.append(f"OpenClaw consumer sensitive marker found: {marker}")

    validate_hashes(openclaw_dir, status, errors)

    hashes_checked = [
        "file_sha256.context_json",
        "file_sha256.first_read_json",
        "file_sha256.first_read_markdown",
        "file_sha256.context_markdown",
        "file_sha256.knowledge_graph_blueprint_json",
        "file_sha256.knowledge_graph_blueprint_markdown",
        "file_sha256.knowledge_graph_nodes",
        "file_sha256.knowledge_graph_edges",
        "file_sha256.knowledge_graph_master_index",
        "file_sha256.knowledge_graph_glossary",
        "file_sha256.knowledge_graph_marginalia",
        "file_sha256.bridge_manifest",
        "completion_report_sha256.completion_report_json",
        "completion_report_sha256.completion_report_markdown",
    ]

    return {
        "status": "ok" if not errors else "failure",
        "errors": errors,
        "openclaw_dir": str(openclaw_dir),
        "loaded_files": loaded_file_names,
        "read_order": read_order,
        "source_git": {
            "branch": status.get("source_git_branch"),
            "commit": status.get("source_git_commit"),
            "dirty": status.get("source_git_dirty"),
        },
        "copied_at": status.get("copied_at"),
        "bridge_age_hours": round(age_hours, 3),
        "latest_recommendation_date": latest_recommendation_date,
        "latest_market_counts": market_counts,
        "latest_recommendation_count": len(latest_recommendations),
        "latest_recommendations": latest_recommendations,
        "telegram_saved_count": telegram_saved_count,
        "hash_checked_count": len(hashes_checked),
        "hashes_checked": hashes_checked,
        "sensitive_markers_checked": SENSITIVE_MARKERS,
    }


def render_text(result: dict[str, Any]) -> str:
    git = result.get("source_git") or {}
    lines = [
        f"OpenClaw consumer smoke: {result.get('status')}",
        f"- dir: {result.get('openclaw_dir')}",
        f"- source git: {git.get('branch')} {git.get('commit')} dirty={git.get('dirty')}",
        f"- copied_at: {result.get('copied_at')} age={result.get('bridge_age_hours')}h",
        f"- latest: {result.get('latest_recommendation_date')} rows={result.get('latest_recommendation_count')}",
        f"- market_counts: {json.dumps(result.get('latest_market_counts') or {}, ensure_ascii=False, separators=(',', ':'))}",
        f"- telegram_saved_count: {result.get('telegram_saved_count')}",
        f"- hash_checked_count: {result.get('hash_checked_count')}",
        "- loaded_files:",
    ]
    for filename in result.get("loaded_files") or []:
        lines.append(f"  - {filename}")
    lines.append("- latest_recommendations:")
    for item in result.get("latest_recommendations") or []:
        lines.append(
            "  - {market}#{rank} {ticker} {company_name} score={score} baseline={baseline_price} {currency}".format(
                **item
            )
        )
    if result.get("errors"):
        lines.append("- errors:")
        for error in result.get("errors") or []:
            lines.append(f"  - {error}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test OpenClaw's consumer-facing Investment Research bridge files.")
    parser.add_argument("--openclaw-dir", type=Path, default=DEFAULT_OPENCLAW_DIR)
    parser.add_argument("--max-age-hours", type=float, default=1.0)
    parser.add_argument("--expected-latest-count", type=int, default=6)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        result = build_result(
            args.openclaw_dir.resolve(),
            max_age_hours=args.max_age_hours,
            expected_latest_count=args.expected_latest_count,
        )
    except AssertionError as exc:
        result = {"status": "failure", "errors": [str(exc)], "openclaw_dir": str(args.openclaw_dir.resolve())}

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
