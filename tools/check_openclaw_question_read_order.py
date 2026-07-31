from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, NamedTuple

from workspace_paths import openclaw_investment_dir

DEFAULT_OPENCLAW_DIR = openclaw_investment_dir()
BRIDGE_STATUS_FILE = "bridge_status.json"
FIRST_READ_JSON_FILE = "openclaw_first_read.json"
MANIFEST_FILE = "openclaw_bridge_manifest.json"


class QuestionRoute(NamedTuple):
    route_id: str
    question: str
    required_files: tuple[str, ...]
    required_payload_keys: tuple[str, ...]
    required_commands: tuple[str, ...]


QUESTION_ROUTES = (
    QuestionRoute(
        route_id="today_work_report",
        question="오늘 시스템에서 구현한 작업 보고하고 다음 스케줄을 말해줘",
        required_files=(BRIDGE_STATUS_FILE, "openclaw_first_read.md", FIRST_READ_JSON_FILE),
        required_payload_keys=("today_work_report", "next_schedule", "answer_correction"),
        required_commands=("today_answer_readiness", "today_answer_quality"),
    ),
    QuestionRoute(
        route_id="recommendations_priority",
        question="오늘 추천 종목과 중요 메시지 알려줘",
        required_files=(
            BRIDGE_STATUS_FILE,
            "openclaw_first_read.md",
            FIRST_READ_JSON_FILE,
            "investment_research_context.md",
            "investment_research_context.json",
        ),
        required_payload_keys=("latest_recommendations", "latest_market_counts", "telegram"),
        required_commands=("priority_answer_quality",),
    ),
    QuestionRoute(
        route_id="bridge_status_completion",
        question="현재 연동 상태와 완료 감사 결과 알려줘",
        required_files=(
            BRIDGE_STATUS_FILE,
            "openclaw_bridge_completion_report.md",
            "openclaw_bridge_completion_report.json",
        ),
        required_payload_keys=("primary_files", "operational_commands"),
        required_commands=("status_summary", "quick_health", "final_completion_audit"),
    ),
    QuestionRoute(
        route_id="knowledge_graph_context",
        question="투자 방향과 지식 그래프 컨텍스트 알려줘",
        required_files=(
            BRIDGE_STATUS_FILE,
            "openclaw_knowledge_graph_blueprint.md",
            "openclaw_knowledge_graph_blueprint.json",
            "openclaw_knowledge_graph_nodes.json",
            "openclaw_knowledge_graph_edges.json",
            "openclaw_knowledge_graph_master_index.md",
        ),
        required_payload_keys=("primary_files", "operational_commands"),
        required_commands=("knowledge_graph_validation",),
    ),
)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise AssertionError(f"required file not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise AssertionError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise AssertionError(f"JSON root must be an object: {path}")
    return payload


def is_subsequence(haystack: list[str], needle: tuple[str, ...]) -> bool:
    index = 0
    for item in haystack:
        if index < len(needle) and item == needle[index]:
            index += 1
    return index == len(needle)


def command_keys(*payloads: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for payload in payloads:
        commands = payload.get("operational_commands")
        if isinstance(commands, dict):
            keys.update(str(key) for key, value in commands.items() if value)
        for key, value in payload.items():
            if key.endswith("_command") and value:
                keys.add(key.removesuffix("_command"))
    return keys


def route_ids_from_first_read(first_read: dict[str, Any]) -> set[str]:
    routes = first_read.get("question_routes")
    if not isinstance(routes, list):
        return set()
    return {
        str(route.get("id") or route.get("route_id") or "")
        for route in routes
        if isinstance(route, dict) and (route.get("id") or route.get("route_id"))
    }


def validate_recommendation_coverage(first_read: dict[str, Any]) -> list[str]:
    rows = first_read.get("latest_recommendations")
    if not isinstance(rows, list):
        return ["latest_recommendations must be a list"]
    counts = Counter(str(row.get("market") or "") for row in rows if isinstance(row, dict))
    errors: list[str] = []
    for market in ("KR", "US"):
        if counts.get(market, 0) < 3:
            errors.append(f"latest_recommendations missing {market} top 3: {dict(counts)}")
    return errors


def build_route_result(
    route: QuestionRoute,
    *,
    openclaw_dir: Path,
    bridge_status: dict[str, Any],
    first_read: dict[str, Any],
    manifest: dict[str, Any],
    available_commands: set[str],
    first_read_route_ids: set[str],
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    missing_files = [filename for filename in route.required_files if not (openclaw_dir / filename).exists()]
    completion_deferred = (
        route.route_id == "bridge_status_completion"
        and bridge_status.get("source_git_dirty") is True
        and set(missing_files) == {"openclaw_bridge_completion_report.md", "openclaw_bridge_completion_report.json"}
    )
    if completion_deferred:
        warnings.append("완료 감사는 미커밋 변경이 있어 보류되었습니다.")
    elif missing_files:
        errors.append(f"missing route files: {', '.join(missing_files)}")

    status_read_order = bridge_status.get("read_order") if isinstance(bridge_status.get("read_order"), list) else []
    manifest_read_order = manifest.get("read_order") if isinstance(manifest.get("read_order"), list) else []
    status_read_order = [str(item) for item in status_read_order]
    manifest_read_order = [str(item) for item in manifest_read_order]
    if not is_subsequence(status_read_order, route.required_files):
        errors.append(f"bridge_status read_order missing ordered route: {route.route_id}")
    if not is_subsequence(manifest_read_order, route.required_files):
        errors.append(f"manifest read_order missing ordered route: {route.route_id}")

    missing_payload_keys = [key for key in route.required_payload_keys if key not in first_read]
    if missing_payload_keys:
        errors.append(f"first-read missing payload keys: {', '.join(missing_payload_keys)}")

    missing_commands = [key for key in route.required_commands if key not in available_commands]
    if missing_commands:
        errors.append(f"missing operational commands: {', '.join(missing_commands)}")

    if first_read_route_ids and route.route_id not in first_read_route_ids:
        errors.append(f"first-read question_routes missing route id: {route.route_id}")

    if route.route_id == "recommendations_priority":
        errors.extend(validate_recommendation_coverage(first_read))

    return {
        "id": route.route_id,
        "question": route.question,
        "status": "failure" if errors else "degraded" if warnings else "ok",
        "errors": errors,
        "warnings": warnings,
        "required_files": list(route.required_files),
        "missing_files": missing_files,
        "required_payload_keys": list(route.required_payload_keys),
        "required_commands": list(route.required_commands),
        "missing_commands": missing_commands,
    }


def build_result(openclaw_dir: Path = DEFAULT_OPENCLAW_DIR) -> dict[str, Any]:
    openclaw_dir = openclaw_dir.resolve()
    bridge_status = load_json(openclaw_dir / BRIDGE_STATUS_FILE)
    first_read = load_json(openclaw_dir / FIRST_READ_JSON_FILE)
    manifest = load_json(openclaw_dir / MANIFEST_FILE)
    available_commands = command_keys(bridge_status, first_read, manifest)
    first_read_route_ids = route_ids_from_first_read(first_read)
    routes = [
        build_route_result(
            route,
            openclaw_dir=openclaw_dir,
            bridge_status=bridge_status,
            first_read=first_read,
            manifest=manifest,
            available_commands=available_commands,
            first_read_route_ids=first_read_route_ids,
        )
        for route in QUESTION_ROUTES
    ]
    errors = [
        f"{route['id']}: {error}"
        for route in routes
        for error in route.get("errors") or []
    ]
    has_degraded_route = any(route.get("status") == "degraded" for route in routes)
    return {
        "status": "failure" if errors else "degraded" if has_degraded_route else "ok",
        "errors": errors,
        "openclaw_dir": str(openclaw_dir),
        "route_count": len(routes),
        "first_read_declared_route_count": len(first_read_route_ids),
        "available_commands": sorted(available_commands),
        "routes": routes,
    }


def render_text(result: dict[str, Any]) -> str:
    lines = [
        f"OpenClaw question read-order: {result.get('status')}",
        f"- openclaw_dir: {result.get('openclaw_dir')}",
        f"- routes: {result.get('route_count')}",
        "- route checks:",
    ]
    for route in result.get("routes") or []:
        lines.append(f"  - {route.get('id')}: {route.get('status')} | {route.get('question')}")
    if result.get("errors"):
        lines.append("- errors:")
        for error in result["errors"]:
            lines.append(f"  - {error}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test OpenClaw question-specific file read order.")
    parser.add_argument("--openclaw-dir", type=Path, default=DEFAULT_OPENCLAW_DIR)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        result = build_result(args.openclaw_dir)
    except AssertionError as exc:
        result = {"status": "failure", "errors": [str(exc)], "openclaw_dir": str(args.openclaw_dir.resolve())}
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"OpenClaw question read-order: failure\n- error: {exc}")
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))
    return 0 if result.get("status") in {"ok", "degraded"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
