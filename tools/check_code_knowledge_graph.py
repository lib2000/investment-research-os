"""Validate the local code/operation knowledge graph."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from build_code_knowledge_graph import DEFAULT_OUTPUT, build_graph, project_root

MIN_NODES = 180
MIN_EDGES = 180
REQUIRED_FLOW_IDS = {
    "daily_recommendations",
    "research_storage_rag",
    "portfolio_realtime",
    "source_automation",
    "classification_quality",
    "investment_calendar",
    "console_click_regression",
    "backend_module_health",
}
REQUIRED_NODE_IDS = {
    "file:backend/research_os_main.py",
    "file:backend/research_os/daily_recommendations.py",
    "file:backend/research_os/investment_calendar.py",
    "file:backend/research_os/rag_memory.py",
    "file:backend/research_os/portfolio_store.py",
    "file:backend/research_os/code_knowledge.py",
    "file:mobile_app/research_console/console.js",
    "file:mobile_app/research_console/index.html",
    "file:tools/check_offline_readiness.py",
    "file:tools/check_backend_module_health.py",
}


def load_or_refresh(root: Path, output: Path, refresh: bool) -> dict:
    if refresh or not output.exists():
        graph = build_graph(root)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
        return graph
    return json.loads(output.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="코드 지식 그래프 품질을 점검합니다.")
    parser.add_argument("--graph", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--refresh", action="store_true", help="점검 전에 그래프를 다시 생성합니다.")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--max-graph-age-hours", type=float, default=24.0, help="그래프 생성 시각 최신성 기준")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    graph_path = args.graph if args.graph.is_absolute() else root / args.graph
    graph = load_or_refresh(root, graph_path, refresh=args.refresh or args.strict)
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    flows = graph.get("flows") or []
    node_ids = {str(node.get("id")) for node in nodes}
    flow_by_id = {str(flow.get("id")): flow for flow in flows}
    errors: list[str] = []
    warnings: list[str] = []

    if graph.get("schema_version") != 1:
        errors.append(f"지원하지 않는 그래프 schema_version: {graph.get('schema_version')}")
    generated_at = str(graph.get("generated_at") or "").strip()
    graph_age_hours: float | None = None
    if not generated_at:
        errors.append("그래프 생성 시각 누락")
    else:
        try:
            parsed_generated_at = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
            if parsed_generated_at.tzinfo is None:
                parsed_generated_at = parsed_generated_at.replace(tzinfo=timezone.utc)
            graph_age_hours = (datetime.now(timezone.utc) - parsed_generated_at.astimezone(timezone.utc)).total_seconds() / 3600
            if graph_age_hours < -0.1:
                errors.append(f"그래프 생성 시각이 미래입니다: {generated_at}")
            if graph_age_hours > args.max_graph_age_hours:
                errors.append(f"그래프 생성 시각 오래됨: {generated_at} / 허용 {args.max_graph_age_hours:g}시간")
        except ValueError:
            errors.append(f"그래프 생성 시각 파싱 실패: {generated_at}")
    if graph.get("node_count") != len(nodes):
        errors.append(f"그래프 node_count 불일치: {graph.get('node_count')} / 실제 {len(nodes)}")
    if graph.get("edge_count") != len(edges):
        errors.append(f"그래프 edge_count 불일치: {graph.get('edge_count')} / 실제 {len(edges)}")
    summary = graph.get("summary") if isinstance(graph.get("summary"), dict) else {}
    if summary.get("flows_ok") != sum(1 for flow in flows if flow.get("status") == "ok"):
        errors.append("그래프 summary.flows_ok 불일치")
    summary_needing = summary.get("flows_needing_review")
    actual_needing = sorted(flow.get("id") for flow in flows if flow.get("status") != "ok")
    if isinstance(summary_needing, list) and sorted(str(item) for item in summary_needing) != actual_needing:
        errors.append("그래프 summary.flows_needing_review 불일치")
    if len(nodes) < MIN_NODES:
        errors.append(f"노드 수 부족: {len(nodes)}개 / 최소 {MIN_NODES}개")
    if len(edges) < MIN_EDGES:
        errors.append(f"엣지 수 부족: {len(edges)}개 / 최소 {MIN_EDGES}개")

    missing_nodes = sorted(REQUIRED_NODE_IDS - node_ids)
    if missing_nodes:
        errors.append("필수 코드 노드 누락: " + ", ".join(missing_nodes))

    missing_flows = sorted(REQUIRED_FLOW_IDS - set(flow_by_id))
    if missing_flows:
        errors.append("필수 운영 흐름 누락: " + ", ".join(missing_flows))
    for flow_id in sorted(REQUIRED_FLOW_IDS & set(flow_by_id)):
        flow = flow_by_id[flow_id]
        if flow.get("status") != "ok":
            errors.append(f"운영 흐름 점검 필요: {flow_id} ({flow.get('label')})")
        if int(flow.get("matched_file_count") or 0) <= 0:
            errors.append(f"운영 흐름 연결 파일 없음: {flow_id}")

    api_routes = [node for node in nodes if node.get("type") == "api_route"]
    api_calls = [node for node in nodes if node.get("type") == "api_call"]
    buttons = [node for node in nodes if node.get("type") == "button"]
    if len(api_routes) < 50:
        warnings.append(f"API route 노드가 예상보다 적음: {len(api_routes)}개")
    if len(api_calls) < 40:
        warnings.append(f"콘솔 API call 노드가 예상보다 적음: {len(api_calls)}개")
    if len(buttons) < 80:
        warnings.append(f"버튼 노드가 예상보다 적음: {len(buttons)}개")

    print(f"프로젝트 루트: {root}")
    print(f"그래프 파일: {graph_path.relative_to(root)}")
    age_label = "미확인" if graph_age_hours is None else f"{graph_age_hours:.1f}시간"
    print(f"생성 시각: {graph.get('generated_at') or '미확인'} | 경과 {age_label}")
    print(f"노드: {len(nodes)}개 / 엣지: {len(edges)}개")
    print(f"API route: {len(api_routes)}개 / 콘솔 API call: {len(api_calls)}개 / 버튼: {len(buttons)}개")
    print("운영 흐름: " + ", ".join(f"{flow['id']}={flow.get('status')}" for flow in flows))
    if warnings:
        for warning in warnings:
            print(f"주의: {warning}")
    if errors:
        for error in errors:
            print(f"오류: {error}")
        return 1 if args.strict else 0
    print("코드 지식 그래프 상태 정상")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
