from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "research_vault" / "_system" / "openclaw_integration"
DEFAULT_OPENCLAW_DIR = Path.home() / ".openclaw" / "workspace" / "data" / "investment_research"
KNOWLEDGE_GRAPH_FILES = {
    "nodes": "openclaw_knowledge_graph_nodes.json",
    "edges": "openclaw_knowledge_graph_edges.json",
    "master_index": "openclaw_knowledge_graph_master_index.md",
    "glossary": "openclaw_knowledge_graph_glossary.md",
    "marginalia": "openclaw_knowledge_graph_marginalia_queue.md",
}
FIRST_READ_JSON_FILE = "openclaw_first_read.json"
FIRST_READ_MARKDOWN_FILE = "openclaw_first_read.md"


SECRET_PATTERNS = [
    re.compile(r'"access_token"\s*:', re.IGNORECASE),
    re.compile(r'"refresh_token"\s*:', re.IGNORECASE),
    re.compile(r'"app(?:_|-)?secret"\s*:', re.IGNORECASE),
    re.compile(r'"secret(?:_|-)?key"\s*:', re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE),
    re.compile(r"kis_access_token\.json\s*:\s*\{", re.IGNORECASE),
    re.compile(r"kiwoom_access_token\.json\s*:\s*\{", re.IGNORECASE),
]


def load_context(path: Path) -> dict:
    if not path.exists():
        raise AssertionError(f"context JSON not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise AssertionError(f"context JSON is invalid: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise AssertionError(f"context JSON root must be object: {path}")
    return payload


def parse_generated_at(value: object) -> datetime:
    if not value:
        raise AssertionError("generated_at is missing")
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise AssertionError(f"generated_at is invalid: {text}") from exc
    if parsed.tzinfo is None:
        raise AssertionError("generated_at must include timezone")
    return parsed


def validate_context(payload: dict, *, max_age_hours: float | None = None) -> list[str]:
    messages: list[str] = []
    if payload.get("module") != "openclaw_investment_research_context":
        raise AssertionError("module mismatch")
    generated_at = parse_generated_at(payload.get("generated_at"))
    age_hours = (datetime.now(timezone.utc) - generated_at.astimezone(timezone.utc)).total_seconds() / 3600
    if max_age_hours is not None and age_hours > max_age_hours:
        raise AssertionError(f"context is stale: {age_hours:.2f}h > {max_age_hours:.2f}h")
    state = payload.get("current_state")
    if not isinstance(state, dict):
        raise AssertionError("current_state missing")
    rec = state.get("daily_recommendations")
    if not isinstance(rec, dict):
        raise AssertionError("daily_recommendations missing")
    latest_rows = rec.get("latest_rows")
    if not isinstance(latest_rows, list) or len(latest_rows) < 6:
        raise AssertionError("daily recommendation latest rows must include KR/US top 3")
    market_counts = rec.get("latest_market_counts") or {}
    if int(market_counts.get("KR") or 0) < 3 or int(market_counts.get("US") or 0) < 3:
        raise AssertionError(f"KR/US recommendation counts are incomplete: {market_counts}")
    sanitization = payload.get("sanitization") or {}
    if sanitization.get("raw_tokens_excluded") is not True:
        raise AssertionError("raw token exclusion flag must be true")
    telegram = ((state.get("news_and_telegram") or {}).get("telegram_favorite_posts") or {})
    if int(telegram.get("saved_count") or 0) <= 0:
        raise AssertionError("telegram favorite posts are not reflected")
    nps = state.get("nps_rebalancing") or {}
    if nps.get("public_sources_only") is not True:
        raise AssertionError("NPS context must be marked as public-sources-only")
    firecrawl = state.get("firecrawl_monitoring") or {}
    defaults = firecrawl.get("safety_defaults") or {}
    if defaults.get("enabled_default") is not False or defaults.get("dry_run_default") is not True:
        raise AssertionError("Firecrawl safety defaults must remain enabled=false and dry_run=true")
    usage = payload.get("openclaw_usage") or {}
    if usage.get("status_file") != "bridge_status.json":
        raise AssertionError("OpenClaw usage must point to bridge_status.json")
    if usage.get("read_this_first") != FIRST_READ_MARKDOWN_FILE:
        raise AssertionError("OpenClaw usage must point read_this_first to first-read Markdown")
    if usage.get("read_this_first_json") != FIRST_READ_JSON_FILE:
        raise AssertionError("OpenClaw usage must point read_this_first_json to first-read JSON")
    if usage.get("completion_report") != "openclaw_bridge_completion_report.md":
        raise AssertionError("OpenClaw usage must point to completion report")
    if usage.get("completion_report_json") != "openclaw_bridge_completion_report.json":
        raise AssertionError("OpenClaw usage must point to completion report JSON")
    if usage.get("status_summary_command") != "python tools\\show_openclaw_bridge_status.py --json":
        raise AssertionError("OpenClaw usage must include status summary command")
    if usage.get("quick_health_command") != "python tools\\check_openclaw_quick_health.py --json":
        raise AssertionError("OpenClaw usage must include quick health command")
    if usage.get("today_answer_readiness_command") != "python tools\\check_openclaw_today_answer_readiness.py --json":
        raise AssertionError("OpenClaw usage must include today answer readiness command")
    if usage.get("today_answer_quality_command") != "python tools\\check_openclaw_today_answer_quality.py --json":
        raise AssertionError("OpenClaw usage must include today answer quality command")
    if usage.get("priority_answer_quality_command") != "python tools\\check_openclaw_priority_answer_quality.py --json":
        raise AssertionError("OpenClaw usage must include priority answer quality command")
    if usage.get("question_read_order_command") != "python tools\\check_openclaw_question_read_order.py --json":
        raise AssertionError("OpenClaw usage must include question read-order command")
    if usage.get("answer_samples_command") != "python tools\\check_openclaw_answer_samples.py --json":
        raise AssertionError("OpenClaw usage must include answer samples command")
    if usage.get("actual_answer_audit_command") != "python tools\\check_openclaw_actual_answer_audit.py --json":
        raise AssertionError("OpenClaw usage must include actual answer audit command")
    if usage.get("answer_capture_cycle_command") != "python tools\\check_openclaw_answer_capture_cycle.py --json":
        raise AssertionError("OpenClaw usage must include answer capture cycle command")
    if usage.get("answer_capture_cycle_run_command") != "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\run_openclaw_answer_capture_cycle.ps1 -Collect -WriteState":
        raise AssertionError("OpenClaw usage must include answer capture cycle run command")
    if usage.get("answer_capture_cycle_register_command") != "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\register_openclaw_answer_capture_cycle_task.ps1 -Collect":
        raise AssertionError("OpenClaw usage must include answer capture cycle register command")
    if usage.get("actual_answer_capture_command") != "python tools\\capture_openclaw_actual_answer.py --route-id today_work_report --answer-file <path> --audit --json":
        raise AssertionError("OpenClaw usage must include actual answer capture command")
    if usage.get("pending_answer_collect_command") != "python tools\\collect_openclaw_pending_answers.py --json":
        raise AssertionError("OpenClaw usage must include pending answer collect command")
    if usage.get("actual_answer_capture_status_command") != "python tools\\check_openclaw_actual_answer_capture_status.py --json":
        raise AssertionError("OpenClaw usage must include actual answer capture status command")
    if usage.get("safe_refresh_command") != "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\sync_openclaw_investment_context.ps1":
        raise AssertionError("OpenClaw usage must include safe refresh command")
    if usage.get("strict_refresh_command") != "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\sync_openclaw_investment_context.ps1 -RequireCompletionAudit":
        raise AssertionError("OpenClaw usage must include strict refresh command")
    final_audit = str(usage.get("final_completion_audit_command") or "")
    if "--require-report-hashes" not in final_audit:
        raise AssertionError("OpenClaw usage must include final completion hash audit command")
    if usage.get("wsl_refresh_command") != "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\sync_openclaw_wsl_investment_context.ps1":
        raise AssertionError("OpenClaw usage must include WSL refresh command")
    if usage.get("wsl_answer_context_command") != "python tools\\check_openclaw_wsl_answer_context.py --json":
        raise AssertionError("OpenClaw usage must include WSL answer context command")
    if usage.get("wsl_fresh_bootstrap_command") != "python tools\\check_openclaw_wsl_answer_context.py --require-fresh-bootstrap --json":
        raise AssertionError("OpenClaw usage must include WSL fresh bootstrap command")
    if usage.get("offline_readiness_command") != "python tools\\check_offline_readiness.py --json":
        raise AssertionError("OpenClaw usage must include offline readiness command")
    blueprint = payload.get("openclaw_knowledge_graph_blueprint")
    if not isinstance(blueprint, dict):
        raise AssertionError("OpenClaw knowledge graph blueprint missing")
    if blueprint.get("schema") != "openclaw_personal_knowledge_graph_blueprint_v1":
        raise AssertionError("OpenClaw knowledge graph blueprint schema mismatch")
    if (blueprint.get("source") or {}).get("raw_content_excluded") is not True:
        raise AssertionError("OpenClaw knowledge graph blueprint must exclude raw source content")
    seed_ids = {str(item.get("id") or "") for item in blueprint.get("seed_nodes") or [] if isinstance(item, dict)}
    for required_seed in (
        "concept.relu",
        "topic.graph_rendering_8000_nodes",
        "note.graph_rendering_lod_experiment",
    ):
        if required_seed not in seed_ids:
            raise AssertionError(f"OpenClaw knowledge graph blueprint missing seed node: {required_seed}")
    edge_types = set(blueprint.get("edge_types") or [])
    for edge in blueprint.get("seed_edges") or []:
        if isinstance(edge, dict) and edge.get("type") not in edge_types:
            raise AssertionError(f"OpenClaw knowledge graph blueprint edge type is undeclared: {edge.get('type')}")
    messages.append(
        f"generated_at={payload.get('generated_at')} latest={rec.get('latest_recommendation_date')} "
        f"rows={len(latest_rows)} telegram_saved={telegram.get('saved_count')}"
    )
    return messages


def validate_no_secret_like_content(path: Path) -> None:
    text = path.read_text(encoding="utf-8-sig")
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            raise AssertionError(f"secret-like content found in {path}: {pattern.pattern}")


def sha256_hex(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_read_order() -> list[str]:
    return [
        "bridge_status.json",
        FIRST_READ_MARKDOWN_FILE,
        FIRST_READ_JSON_FILE,
        "openclaw_bridge_manifest.json",
        "investment_research_context.md",
        "investment_research_context.json",
        "openclaw_knowledge_graph_blueprint.md",
        "openclaw_knowledge_graph_blueprint.json",
        KNOWLEDGE_GRAPH_FILES["nodes"],
        KNOWLEDGE_GRAPH_FILES["edges"],
        KNOWLEDGE_GRAPH_FILES["master_index"],
        KNOWLEDGE_GRAPH_FILES["glossary"],
        KNOWLEDGE_GRAPH_FILES["marginalia"],
        "openclaw_bridge_completion_report.md",
        "openclaw_bridge_completion_report.json",
    ]


def validate_bundle(directory: Path, *, max_age_hours: float | None = None) -> list[str]:
    json_path = directory / "investment_research_context.json"
    md_path = directory / "investment_research_context.md"
    first_read_json_path = directory / FIRST_READ_JSON_FILE
    first_read_md_path = directory / FIRST_READ_MARKDOWN_FILE
    kg_json_path = directory / "openclaw_knowledge_graph_blueprint.json"
    kg_md_path = directory / "openclaw_knowledge_graph_blueprint.md"
    kg_nodes_path = directory / KNOWLEDGE_GRAPH_FILES["nodes"]
    kg_edges_path = directory / KNOWLEDGE_GRAPH_FILES["edges"]
    kg_master_index_path = directory / KNOWLEDGE_GRAPH_FILES["master_index"]
    kg_glossary_path = directory / KNOWLEDGE_GRAPH_FILES["glossary"]
    kg_marginalia_path = directory / KNOWLEDGE_GRAPH_FILES["marginalia"]
    manifest_path = directory / "openclaw_bridge_manifest.json"
    if not md_path.exists():
        raise AssertionError(f"context Markdown not found: {md_path}")
    if not first_read_json_path.exists():
        raise AssertionError(f"OpenClaw first-read JSON not found: {first_read_json_path}")
    if not first_read_md_path.exists():
        raise AssertionError(f"OpenClaw first-read Markdown not found: {first_read_md_path}")
    if not kg_json_path.exists():
        raise AssertionError(f"OpenClaw knowledge graph blueprint JSON not found: {kg_json_path}")
    if not kg_md_path.exists():
        raise AssertionError(f"OpenClaw knowledge graph blueprint Markdown not found: {kg_md_path}")
    for label, path in {
        "nodes": kg_nodes_path,
        "edges": kg_edges_path,
        "master_index": kg_master_index_path,
        "glossary": kg_glossary_path,
        "marginalia": kg_marginalia_path,
    }.items():
        if not path.exists():
            raise AssertionError(f"OpenClaw knowledge graph {label} file not found: {path}")
    if not manifest_path.exists():
        raise AssertionError(f"OpenClaw bridge manifest not found: {manifest_path}")
    validate_no_secret_like_content(json_path)
    validate_no_secret_like_content(md_path)
    validate_no_secret_like_content(first_read_json_path)
    validate_no_secret_like_content(first_read_md_path)
    validate_no_secret_like_content(kg_json_path)
    validate_no_secret_like_content(kg_md_path)
    validate_no_secret_like_content(kg_nodes_path)
    validate_no_secret_like_content(kg_edges_path)
    validate_no_secret_like_content(kg_master_index_path)
    validate_no_secret_like_content(kg_glossary_path)
    validate_no_secret_like_content(kg_marginalia_path)
    validate_no_secret_like_content(manifest_path)
    payload = load_context(json_path)
    messages = validate_context(payload, max_age_hours=max_age_hours)
    first_read_payload = load_context(first_read_json_path)
    if first_read_payload.get("schema") != "openclaw_investment_research_first_read_v1":
        raise AssertionError("OpenClaw first-read JSON schema mismatch")
    if first_read_payload.get("generated_at") != payload.get("generated_at"):
        raise AssertionError("OpenClaw first-read generated_at does not match context")
    if first_read_payload.get("read_order") != expected_read_order():
        raise AssertionError("OpenClaw first-read read_order mismatch")
    first_read_markdown = first_read_md_path.read_text(encoding="utf-8-sig")
    for required in [
        "OpenClaw Investment Research First Read",
        "Latest Recommendations",
        "Safety",
        "Read Order",
        "bridge_status.json",
        "openclaw_bridge_manifest.json",
    ]:
        if required not in first_read_markdown:
            raise AssertionError(f"OpenClaw first-read Markdown is missing required text: {required}")
    blueprint_payload = load_context(kg_json_path)
    if blueprint_payload.get("schema") != "openclaw_personal_knowledge_graph_blueprint_v1":
        raise AssertionError("OpenClaw knowledge graph blueprint JSON schema mismatch")
    if blueprint_payload != payload.get("openclaw_knowledge_graph_blueprint"):
        raise AssertionError("OpenClaw knowledge graph blueprint JSON does not match context payload")
    manifest = load_context(manifest_path)
    if manifest.get("schema") != "investment_research_openclaw_bridge_v1":
        raise AssertionError("OpenClaw bridge manifest schema mismatch")
    if manifest.get("context_generated_at") != payload.get("generated_at"):
        raise AssertionError("OpenClaw bridge manifest generated_at does not match context")
    if manifest.get("first_read_file") != FIRST_READ_MARKDOWN_FILE:
        raise AssertionError("OpenClaw bridge manifest first_read_file mismatch")
    if manifest.get("first_read_json_file") != FIRST_READ_JSON_FILE:
        raise AssertionError("OpenClaw bridge manifest first_read_json_file mismatch")
    if manifest.get("context_file") != "investment_research_context.json":
        raise AssertionError("OpenClaw bridge manifest context_file mismatch")
    if manifest.get("markdown_file") != "investment_research_context.md":
        raise AssertionError("OpenClaw bridge manifest markdown_file mismatch")
    if manifest.get("knowledge_graph_blueprint_file") != "openclaw_knowledge_graph_blueprint.md":
        raise AssertionError("OpenClaw bridge manifest knowledge_graph_blueprint_file mismatch")
    if manifest.get("knowledge_graph_blueprint_json_file") != "openclaw_knowledge_graph_blueprint.json":
        raise AssertionError("OpenClaw bridge manifest knowledge_graph_blueprint_json_file mismatch")
    if manifest.get("knowledge_graph_files") != KNOWLEDGE_GRAPH_FILES:
        raise AssertionError("OpenClaw bridge manifest knowledge_graph_files mismatch")
    if manifest.get("read_order") != expected_read_order():
        raise AssertionError("OpenClaw bridge manifest read_order mismatch")
    command_fields = [
        "safe_refresh_command",
        "strict_refresh_command",
        "validation_command",
        "completion_audit_command",
        "knowledge_graph_validation_command",
        "final_completion_audit_command",
        "status_summary_command",
        "quick_health_command",
        "today_answer_readiness_command",
        "today_answer_quality_command",
        "priority_answer_quality_command",
        "question_read_order_command",
        "answer_samples_command",
        "actual_answer_audit_command",
        "actual_answer_capture_command",
        "actual_answer_capture_status_command",
        "wsl_refresh_command",
        "wsl_answer_context_command",
        "wsl_fresh_bootstrap_command",
        "offline_readiness_command",
    ]
    missing_commands = [field for field in command_fields if not manifest.get(field)]
    if missing_commands:
        raise AssertionError(f"OpenClaw bridge manifest must include commands: {', '.join(missing_commands)}")
    if manifest.get("completion_report_file") != "openclaw_bridge_completion_report.md":
        raise AssertionError("OpenClaw bridge manifest completion_report_file mismatch")
    if manifest.get("completion_report_json_file") != "openclaw_bridge_completion_report.json":
        raise AssertionError("OpenClaw bridge manifest completion_report_json_file mismatch")
    markdown = md_path.read_text(encoding="utf-8-sig")
    for required in [
        "오늘 추천 최신일",
        "민감정보",
        "오픈클로 사용 규칙",
        "show_openclaw_bridge_status.py --json",
        "KR 1위",
        "US 1위",
        "OpenClaw 개인 지식 그래프 Blueprint",
        "openclaw_knowledge_graph_blueprint.json",
    ]:
        if required not in markdown:
            raise AssertionError(f"Markdown context is missing required text: {required}")
    blueprint_markdown = kg_md_path.read_text(encoding="utf-8-sig")
    for required in [
        "Master Index",
        "Glossary",
        "Marginalia",
        "concept.relu",
        "topic.graph_rendering_8000_nodes",
        "note.graph_rendering_lod_experiment",
    ]:
        if required not in blueprint_markdown:
            raise AssertionError(f"OpenClaw knowledge graph blueprint markdown is missing required text: {required}")
    try:
        graph_nodes = json.loads(kg_nodes_path.read_text(encoding="utf-8-sig"))
        graph_edges = json.loads(kg_edges_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise AssertionError(f"OpenClaw knowledge graph JSON artifact is invalid: {exc}") from exc
    if not isinstance(graph_nodes, list) or not graph_nodes:
        raise AssertionError("OpenClaw knowledge graph nodes must be a non-empty list")
    if not isinstance(graph_edges, list) or not graph_edges:
        raise AssertionError("OpenClaw knowledge graph edges must be a non-empty list")
    graph_node_ids = {str(item.get("id") or "") for item in graph_nodes if isinstance(item, dict)}
    for required in ("concept.relu", "topic.graph_rendering_8000_nodes", "note.graph_rendering_lod_experiment"):
        if required not in graph_node_ids:
            raise AssertionError(f"OpenClaw knowledge graph nodes missing required id: {required}")
    for path, required in (
        (kg_master_index_path, "topic.graph_rendering_8000_nodes"),
        (kg_glossary_path, "concept.relu"),
        (kg_marginalia_path, "note.graph_rendering_lod_experiment"),
    ):
        if required not in path.read_text(encoding="utf-8-sig"):
            raise AssertionError(f"OpenClaw knowledge graph artifact missing {required}: {path}")
    status_path = directory / "bridge_status.json"
    if status_path.exists():
        validate_no_secret_like_content(status_path)
        status = load_context(status_path)
        if status.get("status") != "ok":
            raise AssertionError(f"bridge status is not ok: {status.get('status')}")
        if status.get("context_generated_at") != payload.get("generated_at"):
            raise AssertionError("bridge status generated_at does not match context")
        if status.get("secrets_excluded") is not True:
            raise AssertionError("bridge status must confirm secrets_excluded=true")
        if not status.get("source_git_commit") or not status.get("source_git_branch"):
            raise AssertionError("bridge status must include source git commit and branch")
        if status.get("source_git_dirty") not in (True, False):
            raise AssertionError("bridge status must include source_git_dirty boolean")
        if status.get("startup_notes_updated") is not True:
            raise AssertionError("bridge status must confirm startup_notes_updated=true")
        if not str(status.get("completion_report_markdown") or "").endswith("openclaw_bridge_completion_report.md"):
            raise AssertionError("bridge status completion_report_markdown mismatch")
        if status.get("read_order") != expected_read_order():
            raise AssertionError("bridge status read_order mismatch")
        commands = status.get("operational_commands") or {}
        command_manifest_map = {
            "safe_refresh": "safe_refresh_command",
            "strict_refresh": "strict_refresh_command",
            "validation": "validation_command",
            "completion_audit": "completion_audit_command",
            "knowledge_graph_validation": "knowledge_graph_validation_command",
            "final_completion_audit": "final_completion_audit_command",
            "status_summary": "status_summary_command",
            "quick_health": "quick_health_command",
            "today_answer_quality": "today_answer_quality_command",
            "priority_answer_quality": "priority_answer_quality_command",
            "question_read_order": "question_read_order_command",
            "answer_samples": "answer_samples_command",
            "actual_answer_audit": "actual_answer_audit_command",
            "actual_answer_capture": "actual_answer_capture_command",
            "actual_answer_capture_status": "actual_answer_capture_status_command",
            "wsl_refresh": "wsl_refresh_command",
            "wsl_answer_context": "wsl_answer_context_command",
            "wsl_fresh_bootstrap": "wsl_fresh_bootstrap_command",
            "offline_readiness": "offline_readiness_command",
        }
        for command_key, manifest_key in command_manifest_map.items():
            if not commands.get(command_key):
                raise AssertionError(f"bridge status missing operational command: {command_key}")
            if commands.get(command_key) != manifest.get(manifest_key):
                raise AssertionError(f"bridge status operational command mismatch: {command_key}")
        expected_hashes = {
            "first_read_json": first_read_json_path,
            "first_read_markdown": first_read_md_path,
            "context_json": json_path,
            "context_markdown": md_path,
            "knowledge_graph_blueprint_json": kg_json_path,
            "knowledge_graph_blueprint_markdown": kg_md_path,
            "knowledge_graph_nodes": kg_nodes_path,
            "knowledge_graph_edges": kg_edges_path,
            "knowledge_graph_master_index": kg_master_index_path,
            "knowledge_graph_glossary": kg_glossary_path,
            "knowledge_graph_marginalia": kg_marginalia_path,
            "bridge_manifest": manifest_path,
        }
        file_hashes = status.get("file_sha256") or {}
        for hash_key, hash_path in expected_hashes.items():
            recorded_hash = file_hashes.get(hash_key)
            if not recorded_hash:
                raise AssertionError(f"bridge status missing file_sha256: {hash_key}")
            if recorded_hash.lower() != sha256_hex(hash_path):
                raise AssertionError(f"bridge status file_sha256 mismatch: {hash_key}")
        report_hashes = status.get("completion_report_sha256") or {}
        expected_report_hashes = {
            "completion_report_json": directory / "openclaw_bridge_completion_report.json",
            "completion_report_markdown": directory / "openclaw_bridge_completion_report.md",
        }
        for hash_key, hash_path in expected_report_hashes.items():
            recorded_hash = report_hashes.get(hash_key)
            if not recorded_hash:
                continue
            if not hash_path.exists():
                raise AssertionError(f"OpenClaw completion report hash target missing: {hash_path}")
            validate_no_secret_like_content(hash_path)
            if recorded_hash.lower() != sha256_hex(hash_path):
                raise AssertionError(f"bridge status completion_report_sha256 mismatch: {hash_key}")
        readme_path = directory / "README.md"
        if not readme_path.exists():
            raise AssertionError(f"OpenClaw bridge README not found: {readme_path}")
        validate_no_secret_like_content(readme_path)
        readme = readme_path.read_text(encoding="utf-8-sig")
        for required in [
            "investment_research_context.md",
            "investment_research_context.json",
            "openclaw_first_read.md",
            "openclaw_first_read.json",
            "openclaw_knowledge_graph_blueprint.md",
            "openclaw_knowledge_graph_blueprint.json",
            "openclaw_knowledge_graph_nodes.json",
            "openclaw_knowledge_graph_edges.json",
            "openclaw_knowledge_graph_master_index.md",
            "openclaw_knowledge_graph_glossary.md",
            "openclaw_knowledge_graph_marginalia_queue.md",
            "openclaw_bridge_manifest.json",
            "read_order",
            "context generated at",
            "latest recommendation date",
            "latest market counts",
            "latest recommendations",
            "telegram favorite saved",
            "openclaw_bridge_completion_report.json",
            "openclaw_bridge_completion_report.md",
            "show_openclaw_bridge_status.py --json",
            "check_openclaw_today_answer_quality.py --json",
            "check_openclaw_priority_answer_quality.py --json",
            "check_openclaw_question_read_order.py --json",
            "check_openclaw_answer_samples.py --json",
            "capture_openclaw_actual_answer.py --route-id today_work_report --answer-file <path> --audit --json",
            "check_openclaw_actual_answer_capture_status.py --json",
            "check_openclaw_actual_answer_audit.py --json",
            "sync_openclaw_wsl_investment_context.ps1",
            "check_openclaw_wsl_answer_context.py --json",
            "check_openclaw_wsl_answer_context.py --require-fresh-bootstrap --json",
            "hash_status=ok",
            "hash_checked_count=14",
            "hash_mismatches=[]",
            "bridge_status.json",
            "secrets",
            "account-auth material are excluded",
        ]:
            if required not in readme:
                raise AssertionError(f"OpenClaw bridge README is missing required text: {required}")
        source_git = f"{status.get('source_git_branch')} {status.get('source_git_commit')}"
        if source_git not in readme:
            raise AssertionError(f"OpenClaw bridge README is missing source git: {source_git}")
        state = payload.get("current_state") or {}
        rec_state = state.get("daily_recommendations") or {}
        telegram_state = ((state.get("news_and_telegram") or {}).get("telegram_favorite_posts") or {})
        readme_status_values = {
            "context generated at": payload.get("generated_at"),
            "latest recommendation date": rec_state.get("latest_recommendation_date"),
            "latest market counts": json.dumps(rec_state.get("latest_market_counts") or {}, ensure_ascii=False, separators=(",", ":")),
            "telegram favorite saved": str(telegram_state.get("saved_count")),
        }
        for label, value in readme_status_values.items():
            expected = f"{label}: `{value}`"
            if expected not in readme:
                raise AssertionError(f"OpenClaw bridge README status summary mismatch: {label}")
        for row in rec_state.get("latest_rows") or []:
            expected = f"{row.get('market')}#{row.get('rank')} `{row.get('ticker')}` {row.get('company_name')}"
            if expected not in readme:
                raise AssertionError(f"OpenClaw bridge README is missing latest recommendation: {expected}")
        for manifest_key in command_manifest_map.values():
            command = str(manifest.get(manifest_key) or "")
            if command and command not in readme:
                raise AssertionError(f"OpenClaw bridge README is missing manifest command: {manifest_key}")
    return messages


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate sanitized OpenClaw Investment Research context bundles.")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--openclaw-dir", type=Path, default=DEFAULT_OPENCLAW_DIR)
    parser.add_argument("--skip-openclaw", action="store_true")
    parser.add_argument("--max-age-hours", type=float, default=24.0)
    parser.add_argument("--json", action="store_true", help="검증 결과를 JSON으로 출력합니다.")
    args = parser.parse_args()

    checks = [(args.source_dir.resolve(), "source")]
    if not args.skip_openclaw:
        checks.append((args.openclaw_dir.resolve(), "openclaw"))
    result = {
        "status": "ok",
        "source_dir": str(args.source_dir.resolve()),
        "openclaw_dir": None if args.skip_openclaw else str(args.openclaw_dir.resolve()),
        "checks": [],
    }
    try:
        for directory, label in checks:
            messages = validate_bundle(directory, max_age_hours=args.max_age_hours)
            result["checks"].append({"label": label, "directory": str(directory), "messages": messages})
    except AssertionError as exc:
        result["status"] = "failure"
        result["error"] = str(exc)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result["status"] == "ok":
            for check in result["checks"]:
                print(f"[{check['label']}] ok: {check['directory']}")
                for message in check["messages"]:
                    print(f"  - {message}")
        else:
            print(f"[failure] {result['error']}")
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
