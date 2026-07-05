from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "research_vault" / "_system" / "openclaw_integration"
DEFAULT_OPENCLAW_DIR = Path.home() / ".openclaw" / "workspace" / "data" / "investment_research"
GRAPH_FILES = {
    "blueprint_json": "openclaw_knowledge_graph_blueprint.json",
    "blueprint_markdown": "openclaw_knowledge_graph_blueprint.md",
    "nodes": "openclaw_knowledge_graph_nodes.json",
    "edges": "openclaw_knowledge_graph_edges.json",
    "master_index": "openclaw_knowledge_graph_master_index.md",
    "glossary": "openclaw_knowledge_graph_glossary.md",
    "marginalia": "openclaw_knowledge_graph_marginalia_queue.md",
}
SECRET_PATTERNS = [
    re.compile(r'"access_token"\s*:', re.IGNORECASE),
    re.compile(r'"refresh_token"\s*:', re.IGNORECASE),
    re.compile(r'"client_secret"\s*:', re.IGNORECASE),
    re.compile(r'"service_role_key"\s*:', re.IGNORECASE),
    re.compile(r'"private_key"\s*:', re.IGNORECASE),
    re.compile(r"-----BEGIN\s+PRIVATE KEY-----", re.IGNORECASE),
]


def load_json(path: Path) -> Any:
    if not path.exists():
        raise AssertionError(f"JSON file not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise AssertionError(f"JSON file is invalid: {path}: {exc}") from exc


def load_text(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"text file not found: {path}")
    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        raise AssertionError(f"text file is empty: {path}")
    return text


def parse_generated_at(value: Any) -> datetime:
    if not value:
        raise AssertionError("context generated_at is missing")
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise AssertionError(f"context generated_at is invalid: {value}") from exc
    if parsed.tzinfo is None:
        raise AssertionError("context generated_at must include timezone")
    return parsed


def validate_no_secret_like_content(path: Path) -> None:
    text = path.read_text(encoding="utf-8-sig")
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            raise AssertionError(f"secret-like content found in {path}: {pattern.pattern}")


def validate_graph_bundle(directory: Path, *, max_age_hours: float | None = None) -> list[str]:
    context = load_json(directory / "investment_research_context.json")
    if not isinstance(context, dict):
        raise AssertionError("investment_research_context.json root must be object")
    generated_at = parse_generated_at(context.get("generated_at"))
    age_hours = (datetime.now(timezone.utc) - generated_at.astimezone(timezone.utc)).total_seconds() / 3600
    if max_age_hours is not None and age_hours > max_age_hours:
        raise AssertionError(f"knowledge graph context is stale: {age_hours:.2f}h > {max_age_hours:.2f}h")

    manifest = load_json(directory / "openclaw_bridge_manifest.json")
    if not isinstance(manifest, dict):
        raise AssertionError("openclaw_bridge_manifest.json root must be object")
    graph_files = manifest.get("knowledge_graph_files")
    if graph_files != {
        "nodes": GRAPH_FILES["nodes"],
        "edges": GRAPH_FILES["edges"],
        "master_index": GRAPH_FILES["master_index"],
        "glossary": GRAPH_FILES["glossary"],
        "marginalia": GRAPH_FILES["marginalia"],
    }:
        raise AssertionError("manifest knowledge_graph_files mismatch")

    for filename in GRAPH_FILES.values():
        validate_no_secret_like_content(directory / filename)

    blueprint = load_json(directory / GRAPH_FILES["blueprint_json"])
    nodes = load_json(directory / GRAPH_FILES["nodes"])
    edges = load_json(directory / GRAPH_FILES["edges"])
    if blueprint != context.get("openclaw_knowledge_graph_blueprint"):
        raise AssertionError("blueprint JSON does not match context payload")
    if not isinstance(nodes, list) or not nodes:
        raise AssertionError("knowledge graph nodes must be a non-empty list")
    if not isinstance(edges, list) or not edges:
        raise AssertionError("knowledge graph edges must be a non-empty list")

    allowed_node_types = set(blueprint.get("node_types") or [])
    allowed_edge_types = set(blueprint.get("edge_types") or [])
    node_ids: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            raise AssertionError("knowledge graph node must be object")
        node_id = str(node.get("id") or "")
        node_type = str(node.get("type") or "")
        if not node_id:
            raise AssertionError("knowledge graph node id is missing")
        if node_id in node_ids:
            raise AssertionError(f"duplicate knowledge graph node id: {node_id}")
        if node_type not in allowed_node_types:
            raise AssertionError(f"knowledge graph node type is undeclared: {node_id} {node_type}")
        if node_type == "concept" and not (node.get("term") or node.get("title")):
            raise AssertionError(f"concept node missing term/title: {node_id}")
        if node_type == "concept" and not node.get("definition"):
            raise AssertionError(f"concept node missing definition: {node_id}")
        if node_type == "note" and not node.get("parent"):
            raise AssertionError(f"note node missing parent: {node_id}")
        node_ids.add(node_id)

    external_placeholder_prefixes = ("concept.", "source.", "artifact.", "project.", "decision.", "topic.", "note.")
    for edge in edges:
        if not isinstance(edge, dict):
            raise AssertionError("knowledge graph edge must be object")
        source = str(edge.get("from") or "")
        target = str(edge.get("to") or "")
        edge_type = str(edge.get("type") or "")
        if not source or not target or not edge_type:
            raise AssertionError("knowledge graph edge requires from/to/type")
        if edge_type not in allowed_edge_types:
            raise AssertionError(f"knowledge graph edge type is undeclared: {edge_type}")
        if source not in node_ids and not source.startswith(external_placeholder_prefixes):
            raise AssertionError(f"knowledge graph edge source is unresolved: {source}")
        if target not in node_ids and not target.startswith(external_placeholder_prefixes):
            raise AssertionError(f"knowledge graph edge target is unresolved: {target}")

    master_index = load_text(directory / GRAPH_FILES["master_index"])
    glossary = load_text(directory / GRAPH_FILES["glossary"])
    marginalia = load_text(directory / GRAPH_FILES["marginalia"])
    for required in ("concept.relu", "topic.graph_rendering_8000_nodes", "note.graph_rendering_lod_experiment"):
        combined = "\n".join([master_index, glossary, marginalia])
        if required not in combined:
            raise AssertionError(f"knowledge graph markdown missing node id: {required}")
    if "ReLU" not in glossary or "definition:" not in glossary:
        raise AssertionError("knowledge graph glossary missing ReLU definition")
    if "unverified" not in marginalia:
        raise AssertionError("knowledge graph marginalia queue missing unverified status")
    return [
        f"generated_at={context.get('generated_at')} nodes={len(nodes)} edges={len(edges)} "
        f"age_hours={age_hours:.3f}"
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate OpenClaw personal knowledge graph bundle.")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--openclaw-dir", type=Path, default=DEFAULT_OPENCLAW_DIR)
    parser.add_argument("--skip-openclaw", action="store_true")
    parser.add_argument("--max-age-hours", type=float, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = {
        "status": "ok",
        "errors": [],
        "source_dir": str(args.source_dir.resolve()),
        "openclaw_dir": str(args.openclaw_dir.resolve()),
        "source_messages": [],
        "openclaw_messages": [],
    }
    try:
        source_messages = validate_graph_bundle(args.source_dir.resolve(), max_age_hours=args.max_age_hours)
        result["source_messages"] = source_messages
        if not args.skip_openclaw:
            openclaw_messages = validate_graph_bundle(args.openclaw_dir.resolve(), max_age_hours=args.max_age_hours)
            result["openclaw_messages"] = openclaw_messages
    except AssertionError as exc:
        result["status"] = "failure"
        result["errors"] = [str(exc)]
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"[failure] {exc}")
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"[source] ok: {args.source_dir.resolve()}")
        for message in result["source_messages"]:
            print(f"  - {message}")
        if not args.skip_openclaw:
            print(f"[openclaw] ok: {args.openclaw_dir.resolve()}")
            for message in result["openclaw_messages"]:
                print(f"  - {message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
