"""Analyze code-change impact using the local code knowledge graph."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_code_knowledge_graph import DEFAULT_OUTPUT, build_graph, project_root  # noqa: E402

FLOW_IMPACT_HINTS = {
    "daily_recommendations": "오늘 추천 1~3위 생성, 저장, 성과 추적 화면을 재검증하세요.",
    "research_storage_rag": "저장 데이터/RAG 색인, LLM 응답 저장, 저장/RAG 상태 확인을 재검증하세요.",
    "portfolio_realtime": "포트폴리오 수량 보호, 실시간 현재가, 수익률 계산을 재검증하세요.",
    "source_automation": "외부 리포트 자동 수집, 시장일지 반영, 출처별 실패 처리를 재검증하세요.",
    "classification_quality": "자동 분류 태그, 범위/출처 판정, 관심종목 영향 반영을 재검증하세요.",
    "console_click_regression": "콘솔 버튼 클릭 피드백과 쓰기 액션 스모크를 재검증하세요.",
    "backend_module_health": "백엔드 모듈 경계, 오프라인 준비 점검, 구조 지도 문서를 재검증하세요.",
}


def changed_files(root: Path, base: str | None) -> list[str]:
    cmd = ["git", "diff", "--name-only"]
    if base:
        cmd.append(base)
    result = subprocess.run(cmd, cwd=root, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "git diff 실행에 실패했습니다.")
    files = [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]
    untracked = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=root, text=True, capture_output=True, check=False)
    if untracked.returncode == 0:
        files.extend(line.strip().replace("\\", "/") for line in untracked.stdout.splitlines() if line.strip())
    return sorted(dict.fromkeys(files))


def load_graph(root: Path, graph_path: Path, refresh: bool) -> dict:
    target = graph_path if graph_path.is_absolute() else root / graph_path
    if refresh or not target.exists():
        graph = build_graph(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
        return graph
    return json.loads(target.read_text(encoding="utf-8"))


def file_nodes(graph: dict) -> set[str]:
    return {str(node.get("path")) for node in graph.get("nodes", []) if node.get("type") == "file" and node.get("path")}


def fallback_flow_ids(path: str) -> set[str]:
    if path == "backend/research_os_main.py":
        return {"daily_recommendations", "research_storage_rag", "portfolio_realtime", "source_automation", "classification_quality", "backend_module_health"}
    if path == "backend/main.py":
        return {"portfolio_realtime", "backend_module_health"}
    if path.startswith("backend/research_os/"):
        lower = path.lower()
        ids: set[str] = {"backend_module_health"}
        if "daily_recommend" in lower:
            ids.add("daily_recommendations")
        if "rag" in lower or "research_memory" in lower or "llm" in lower:
            ids.add("research_storage_rag")
        if "portfolio" in lower:
            ids.add("portfolio_realtime")
        if any(token in lower for token in ["kcif", "regional", "source", "naver", "market_journal"]):
            ids.add("source_automation")
        if "classification" in lower or "ticker_registry" in lower:
            ids.add("classification_quality")
        return ids
    if path.startswith("mobile_app/research_console/"):
        ids = {"console_click_regression"}
        if path.endswith("api.js") or path.endswith("console.js") or path.endswith("index.html"):
            ids.update({"daily_recommendations", "research_storage_rag", "portfolio_realtime", "source_automation", "classification_quality"})
        return ids
    if path == "README.md" or path.startswith("scripts/"):
        return {"backend_module_health"}
    if path.startswith("tools/"):
        ids = {"backend_module_health"}
        lower = path.lower()
        if "daily_recommend" in lower:
            ids.add("daily_recommendations")
        if "rag" in lower or "llm" in lower or "storage_quality" in lower:
            ids.add("research_storage_rag")
        if "portfolio" in lower:
            ids.add("portfolio_realtime")
        if "source" in lower or "naver" in lower:
            ids.add("source_automation")
        if "classification" in lower:
            ids.add("classification_quality")
        if "console" in lower or "smoke_research_console" in lower:
            ids.add("console_click_regression")
        return ids
    if path.startswith("docs/"):
        return {"backend_module_health"}
    return set()


def impacted_flows(graph: dict, path: str) -> list[dict]:
    flow_by_id = {str(flow.get("id")): flow for flow in graph.get("flows", [])}
    hit_ids: set[str] = set()
    for flow in graph.get("flows", []):
        flow_id = str(flow.get("id"))
        candidates = set(flow.get("expected_files") or []) | set(flow.get("sample_files") or [])
        if path in candidates or any(path.startswith(candidate.rstrip("/") + "/") for candidate in candidates):
            hit_ids.add(flow_id)
            continue
        lower = path.lower()
        keywords = [str(item).lower() for item in flow.get("keyword_hits") or []]
        if any(keyword and keyword in lower for keyword in keywords):
            hit_ids.add(flow_id)
    hit_ids.update(fallback_flow_ids(path))
    return [flow_by_id[flow_id] for flow_id in sorted(hit_ids) if flow_id in flow_by_id]


def main() -> int:
    parser = argparse.ArgumentParser(description="코드 변경이 어떤 운영 흐름에 영향을 주는지 점검합니다.")
    parser.add_argument("--base", help="비교 기준 ref. 생략하면 워킹트리 diff를 사용합니다.")
    parser.add_argument("--graph", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--refresh", action="store_true", help="분석 전에 코드 지식 그래프를 다시 생성합니다.")
    parser.add_argument("--strict", action="store_true", help="그래프에 매핑되지 않은 코드 변경이 있으면 실패합니다.")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    graph = load_graph(root, args.graph, refresh=args.refresh)
    files = changed_files(root, args.base)
    known_files = file_nodes(graph)
    relevant = [path for path in files if path == "README.md" or path.startswith(("backend/", "mobile_app/", "tools/", "scripts/", "docs/"))]
    unmapped = [path for path in relevant if path not in known_files and not fallback_flow_ids(path)]
    flow_hits: dict[str, dict] = {}
    file_impacts: list[tuple[str, list[dict]]] = []
    for path in relevant:
        hits = impacted_flows(graph, path)
        file_impacts.append((path, hits))
        for flow in hits:
            flow_hits[str(flow.get("id"))] = flow

    print(f"프로젝트 루트: {root}")
    print(f"변경 파일: {len(files)}개 / 분석 대상: {len(relevant)}개")
    if not relevant:
        print("분석 대상 코드/문서 변경이 없습니다.")
        return 0
    print("\n파일별 영향")
    for path, hits in file_impacts:
        if hits:
            labels = ", ".join(str(flow.get("label") or flow.get("id")) for flow in hits)
            print(f"- {path}: {labels}")
        else:
            marker = "그래프 매핑 없음" if path in unmapped else "직접 연결 흐름 없음"
            print(f"- {path}: {marker}")
    print("\n운영 흐름별 재검증 권장")
    if flow_hits:
        for flow_id in sorted(flow_hits):
            flow = flow_hits[flow_id]
            print(f"- {flow.get('label') or flow_id}: {FLOW_IMPACT_HINTS.get(flow_id, '관련 기능을 수동/스모크로 재검증하세요.')}")
    else:
        print("- 직접 매핑된 운영 흐름이 없습니다. 변경 파일의 개별 테스트를 우선 실행하세요.")
    if unmapped:
        print("\n주의: 코드 지식 그래프에 아직 매핑되지 않은 파일")
        for path in unmapped:
            print(f"- {path}")
        if args.strict:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
