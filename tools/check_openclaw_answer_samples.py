from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_OPENCLAW_DIR = Path.home() / ".openclaw" / "workspace" / "data" / "investment_research"
BANNED_STALE_FRAGMENTS = [
    "오늘 구현 작업 없음",
    "특별히 새로 구현된 작업 기록 없음",
    "오늘 시스템에 새로 구현되거나 변경된 작업은 없습니다",
    "추천 없음",
    "중요 메시지 없음",
    "자료가 없습니다",
]


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


def route_by_id(first_read: dict[str, Any]) -> dict[str, dict[str, Any]]:
    routes = first_read.get("question_routes")
    if not isinstance(routes, list):
        raise AssertionError("first_read.question_routes must be a list")
    mapped = {}
    for route in routes:
        if isinstance(route, dict) and route.get("id"):
            mapped[str(route["id"])] = route
    return mapped


def recommendation_line(row: dict[str, Any]) -> str:
    return (
        f"{row.get('market')}#{row.get('rank')} {row.get('ticker')} "
        f"{row.get('company_name')} score={row.get('score')} baseline={row.get('baseline_price')} {row.get('currency')}"
    ).strip()


def build_today_work_answer(first_read: dict[str, Any], bridge_status: dict[str, Any]) -> str:
    report = first_read.get("today_work_report") or {}
    schedule = first_read.get("next_schedule") or []
    lines = [
        "오늘 구현 작업 보고",
        "- 기준: bridge_status.json, openclaw_first_read.json, today_work_report",
        f"- source git: {bridge_status.get('source_git_branch')} {bridge_status.get('source_git_commit')}",
        f"- 오늘 반영 커밋: {report.get('commit_count')}건",
    ]
    for item in report.get("summary") or []:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("다음 스케줄")
    for item in schedule:
        if isinstance(item, dict):
            lines.append(f"- {item.get('time')}: {item.get('task')} ({item.get('status')})")
    return "\n".join(lines).strip() + "\n"


def build_priority_answer(first_read: dict[str, Any]) -> str:
    rows = first_read.get("latest_recommendations") or []
    telegram = first_read.get("telegram") or {}
    lines = [
        "오늘 추천 종목",
        "- 기준: bridge_status.json, openclaw_first_read.json, investment_research_context.json",
    ]
    for row in rows:
        if isinstance(row, dict):
            lines.append(f"- {recommendation_line(row)}")
    lines.extend(
        [
            "",
            "중요 메시지",
            f"- 텔레그램 즐겨찾기 수집: {telegram.get('favorite_saved_count')}건",
            f"- 우선 브리프: {telegram.get('priority_brief_design')}",
            f"- 전달 정책: {telegram.get('priority_delivery_design')}",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def build_completion_answer(bridge_status: dict[str, Any], manifest: dict[str, Any]) -> str:
    commands = bridge_status.get("operational_commands") or {}
    return "\n".join(
        [
            "OpenClaw 연동 상태",
            "- 기준: bridge_status.json, openclaw_bridge_completion_report.json, openclaw_bridge_manifest.json",
            f"- source git: {bridge_status.get('source_git_branch')} {bridge_status.get('source_git_commit')}",
            f"- hash status: checked {len(bridge_status.get('file_sha256') or {})} files",
            f"- completion report: {bridge_status.get('completion_report_markdown')}",
            f"- final audit: {commands.get('final_completion_audit') or manifest.get('final_completion_audit_command')}",
        ]
    ).strip() + "\n"


def build_knowledge_graph_answer(first_read: dict[str, Any], context: dict[str, Any]) -> str:
    blueprint = context.get("openclaw_knowledge_graph_blueprint") or {}
    seed_nodes = [
        str(item.get("id"))
        for item in blueprint.get("seed_nodes") or []
        if isinstance(item, dict) and item.get("id")
    ]
    return "\n".join(
        [
            "투자 방향과 지식 그래프 컨텍스트",
            "- 기준: bridge_status.json, openclaw_knowledge_graph_blueprint.json, openclaw_knowledge_graph_nodes.json",
            f"- 최신 추천일: {first_read.get('latest_recommendation_date')}",
            f"- 시장별 추천: {json.dumps(first_read.get('latest_market_counts') or {}, ensure_ascii=False, separators=(',', ':'))}",
            f"- graph schema: {blueprint.get('schema')}",
            f"- seed nodes: {', '.join(seed_nodes[:8])}",
        ]
    ).strip() + "\n"


def validate_answer(route_id: str, answer: str, required_fragments: list[str]) -> list[str]:
    errors = []
    for banned in BANNED_STALE_FRAGMENTS:
        if banned in answer:
            errors.append(f"answer contains banned fragment: {banned}")
    for fragment in required_fragments:
        if fragment and fragment not in answer:
            errors.append(f"answer missing required fragment: {fragment}")
    return [f"{route_id}: {error}" for error in errors]


def build_result(openclaw_dir: Path = DEFAULT_OPENCLAW_DIR) -> dict[str, Any]:
    openclaw_dir = openclaw_dir.resolve()
    first_read = load_json(openclaw_dir / "openclaw_first_read.json")
    bridge_status = load_json(openclaw_dir / "bridge_status.json")
    manifest = load_json(openclaw_dir / "openclaw_bridge_manifest.json")
    context = load_json(openclaw_dir / "investment_research_context.json")
    routes = route_by_id(first_read)
    required_route_ids = [
        "today_work_report",
        "recommendations_priority",
        "bridge_status_completion",
        "knowledge_graph_context",
    ]
    missing_routes = [route_id for route_id in required_route_ids if route_id not in routes]
    if missing_routes:
        raise AssertionError(f"first_read.question_routes missing: {', '.join(missing_routes)}")

    samples = {
        "today_work_report": build_today_work_answer(first_read, bridge_status),
        "recommendations_priority": build_priority_answer(first_read),
        "bridge_status_completion": build_completion_answer(bridge_status, manifest),
        "knowledge_graph_context": build_knowledge_graph_answer(first_read, context),
    }
    required_fragments = {
        "today_work_report": ["오늘 구현 작업 보고", "다음 스케줄", "today_work_report", str((first_read.get("today_work_report") or {}).get("commit_count"))],
        "recommendations_priority": ["오늘 추천 종목", "중요 메시지", "KR#1", "US#1", str((first_read.get("telegram") or {}).get("favorite_saved_count"))],
        "bridge_status_completion": ["OpenClaw 연동 상태", "source git", "final audit", str(bridge_status.get("source_git_commit"))],
        "knowledge_graph_context": ["투자 방향과 지식 그래프 컨텍스트", "graph schema", "seed nodes", "시장별 추천"],
    }
    errors: list[str] = []
    sample_results = []
    for route_id, answer in samples.items():
        route_errors = validate_answer(route_id, answer, required_fragments[route_id])
        errors.extend(route_errors)
        sample_results.append(
            {
                "id": route_id,
                "question": routes[route_id].get("question"),
                "status": "ok" if not route_errors else "failure",
                "answer_preview": answer[:1200],
                "required_fragments": required_fragments[route_id],
            }
        )
    return {
        "status": "ok" if not errors else "failure",
        "errors": errors,
        "openclaw_dir": str(openclaw_dir),
        "sample_count": len(sample_results),
        "generated_at": first_read.get("generated_at"),
        "source_git": {
            "branch": bridge_status.get("source_git_branch"),
            "commit": bridge_status.get("source_git_commit"),
            "dirty": bridge_status.get("source_git_dirty"),
        },
        "samples": sample_results,
    }


def render_text(result: dict[str, Any]) -> str:
    lines = [
        f"OpenClaw answer samples: {result.get('status')}",
        f"- openclaw_dir: {result.get('openclaw_dir')}",
        f"- sample_count: {result.get('sample_count')}",
        "- samples:",
    ]
    for sample in result.get("samples") or []:
        lines.append(f"  - {sample.get('id')}: {sample.get('status')} | {sample.get('question')}")
    if result.get("errors"):
        lines.append("- errors:")
        for error in result["errors"]:
            lines.append(f"  - {error}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate and validate OpenClaw question-specific answer samples.")
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
            print(f"OpenClaw answer samples: failure\n- error: {exc}")
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
