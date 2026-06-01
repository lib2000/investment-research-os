"""Build a lightweight code/operation knowledge graph for Investment Research OS.

The graph is intentionally backend-free and secret-safe. It scans tracked source
areas only, extracts deterministic structure (files, functions, classes,
FastAPI routes, JS DOM/API references), and writes a JSON artifact under the
local research vault so the console and readiness checks can reason about
operational impact without sending source code to an external service.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

GRAPH_VERSION = 1
DEFAULT_OUTPUT = Path("research_vault/_system/code_knowledge_graph.json")
SCAN_GLOBS = [
    "backend/research_os_main.py",
    "backend/research_os/*.py",
    "backend/requirements.txt",
    "backend/research_os/README.md",
    "mobile_app/research_console/*.js",
    "mobile_app/research_console/*.html",
    "tools/*.py",
    "tools/*.ps1",
    "scripts/*.ps1",
    "README.md",
    "docs/structure-map.md",
    "docs/operations-readiness.md",
    "docs/testing.md",
]
EXCLUDED_PARTS = {"__pycache__", "node_modules", ".git", "research_vault"}
HTTP_METHODS = {"get", "post", "put", "delete", "patch"}
API_PATH_RE = re.compile(r"[\"'`](/api/v1/[^\"'`?)]*)")
IMPORT_RE = re.compile(r"(?:import\s+(?:[^'\"]+?\s+from\s+)?|from\s+)[\"']([^\"']+)[\"']")
JS_FUNCTION_RE = re.compile(r"(?:function\s+([A-Za-z_$][\w$]*)|(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)")
DOM_ID_RE = re.compile(r"querySelector\(\s*[\"']#([A-Za-z0-9_-]+)[\"']\s*\)")
HTML_ID_RE = re.compile(r"\bid=[\"']([^\"']+)[\"']")
BUTTON_RE = re.compile(r"<button\b([^>]*)>(.*?)</button>", re.IGNORECASE | re.DOTALL)
ATTR_RE = re.compile(r"([A-Za-z_:][-A-Za-z0-9_:.]*)=[\"']([^\"']*)[\"']")

FLOW_DEFINITIONS = {
    "daily_recommendations": {
        "label": "매일 추천 1~3위",
        "keywords": ["daily_recommendations", "dailyRecommendations", "daily-recommendations", "오늘 추천"],
        "expected_files": ["backend/research_os/daily_recommendations.py", "tools/check_daily_recommendations_store.py"],
    },
    "research_storage_rag": {
        "label": "저장 데이터/RAG",
        "keywords": ["rag_memory", "research_memory", "RAG", "research-memory", "저장 데이터"],
        "expected_files": ["backend/research_os/rag_memory.py", "backend/research_os/research_memory.py"],
    },
    "portfolio_realtime": {
        "label": "포트폴리오 실시간/수량 보호",
        "keywords": ["portfolio", "Portfolio", "portfolio_store", "portfolio_sync", "포트폴리오"],
        "expected_files": ["backend/research_os/portfolio_store.py", "tools/check_portfolio_store.py"],
    },
    "source_automation": {
        "label": "외부 리포트/소스 자동화",
        "keywords": ["kcif", "regional_sources", "naver", "source", "리서치 소스"],
        "expected_files": ["backend/research_os/kcif_reports.py", "backend/research_os/regional_sources.py"],
    },
    "classification_quality": {
        "label": "자동 분류 태그/RAG 품질",
        "keywords": ["classification", "classification_system_tags", "source_type", "자동 분류"],
        "expected_files": ["backend/research_os/classification.py", "tools/check_classification_quality.py"],
    },
    "investment_calendar": {
        "label": "투자 캘린더/실적 일정",
        "keywords": ["investment_calendar", "investment-calendar", "투자 캘린더", "실적발표"],
        "expected_files": ["backend/research_os/investment_calendar.py", "mobile_app/research_console/console.js"],
    },
    "console_click_regression": {
        "label": "콘솔 클릭/쓰기 회귀",
        "keywords": ["smoke_research_console", "data-workflow-action", "actionFeedback", "클래식 콘솔"],
        "expected_files": ["tools/smoke_research_console_menus.py", "tools/smoke_research_console_write_actions.py"],
    },
    "backend_module_health": {
        "label": "백엔드 모듈 헬스/구조 안정화",
        "keywords": ["check_backend_module_health", "research_os_main", "requirements", "fastapi", "start-research-backend", "백엔드 실행", "코드 지식 그래프", "구조 지도"],
        "expected_files": ["backend/research_os/code_knowledge.py", "backend/requirements.txt", "scripts/start-research-backend.ps1", "tools/check_backend_module_health.py", "tools/check_offline_readiness.py", "docs/structure-map.md"],
    },
}


@dataclass
class GraphBuilder:
    root: Path
    nodes: dict[str, dict] = field(default_factory=dict)
    edges: list[dict] = field(default_factory=list)
    seen_edges: set[tuple[str, str, str]] = field(default_factory=set)

    def rel(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def add_node(self, node_id: str, node_type: str, label: str, **attrs: object) -> None:
        if node_id not in self.nodes:
            self.nodes[node_id] = {"id": node_id, "type": node_type, "label": label, **attrs}
        else:
            self.nodes[node_id].update({k: v for k, v in attrs.items() if v not in (None, "", [])})

    def add_edge(self, source: str, target: str, kind: str, **attrs: object) -> None:
        key = (source, target, kind)
        if key in self.seen_edges:
            return
        self.seen_edges.add(key)
        self.edges.append({"source": source, "target": target, "kind": kind, **attrs})

    def add_file(self, path: Path, text: str) -> str:
        rel = self.rel(path)
        suffix = path.suffix.lower().lstrip(".") or "text"
        layer = infer_layer(rel)
        node_id = f"file:{rel}"
        self.add_node(
            node_id,
            "file",
            rel,
            path=rel,
            language=suffix,
            layer=layer,
            line_count=len(text.splitlines()),
            sha1=hashlib.sha1(text.encode("utf-8", errors="replace")).hexdigest()[:12],
        )
        return node_id

    def scan_python(self, path: Path, text: str) -> None:
        file_id = self.add_file(path, text)
        rel = self.rel(path)
        try:
            tree = ast.parse(text, filename=rel)
        except SyntaxError as exc:
            self.add_node(f"error:{rel}:{exc.lineno}", "parse_error", f"{rel}:{exc.lineno}", message=exc.msg)
            self.add_edge(file_id, f"error:{rel}:{exc.lineno}", "has_error")
            return
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_id = f"python:function:{rel}:{node.name}"
                self.add_node(func_id, "function", node.name, path=rel, line=node.lineno, async_fn=isinstance(node, ast.AsyncFunctionDef))
                self.add_edge(file_id, func_id, "defines")
                self._scan_fastapi_route(file_id, func_id, node)
            elif isinstance(node, ast.ClassDef):
                class_id = f"python:class:{rel}:{node.name}"
                self.add_node(class_id, "class", node.name, path=rel, line=node.lineno)
                self.add_edge(file_id, class_id, "defines")
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._add_import(file_id, alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                self._add_import(file_id, node.module)

    def _scan_fastapi_route(self, file_id: str, func_id: str, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            func = decorator.func
            if not isinstance(func, ast.Attribute) or func.attr not in HTTP_METHODS:
                continue
            if not decorator.args or not isinstance(decorator.args[0], ast.Constant):
                continue
            route = str(decorator.args[0].value)
            if not route.startswith("/"):
                continue
            route_id = f"route:{func.attr.upper()}:{route}"
            self.add_node(route_id, "api_route", f"{func.attr.upper()} {route}", method=func.attr.upper(), path=route)
            self.add_edge(func_id, route_id, "exposes_route")
            self.add_edge(file_id, route_id, "contains_route")

    def _add_import(self, file_id: str, module_name: str) -> None:
        if not module_name:
            return
        target_id = f"module:{module_name}"
        self.add_node(target_id, "module", module_name)
        self.add_edge(file_id, target_id, "imports")

    def scan_js_like(self, path: Path, text: str) -> None:
        file_id = self.add_file(path, text)
        rel = self.rel(path)
        for match in IMPORT_RE.finditer(text):
            target = match.group(1)
            node_id = f"js_import:{target}"
            self.add_node(node_id, "js_module", target)
            self.add_edge(file_id, node_id, "imports")
        for match in JS_FUNCTION_RE.finditer(text):
            name = match.group(1) or match.group(2)
            func_id = f"js:function:{rel}:{name}"
            self.add_node(func_id, "function", name, path=rel)
            self.add_edge(file_id, func_id, "defines")
        for match in DOM_ID_RE.finditer(text):
            dom_id = match.group(1)
            node_id = f"dom_id:{dom_id}"
            self.add_node(node_id, "dom_id", f"#{dom_id}")
            self.add_edge(file_id, node_id, "references_dom")
        for match in API_PATH_RE.finditer(text):
            api_path = match.group(1)
            node_id = f"api_call:{api_path}"
            self.add_node(node_id, "api_call", api_path, path=api_path)
            self.add_edge(file_id, node_id, "calls_api")

    def scan_html(self, path: Path, text: str) -> None:
        file_id = self.add_file(path, text)
        for match in HTML_ID_RE.finditer(text):
            dom_id = match.group(1)
            node_id = f"dom_id:{dom_id}"
            self.add_node(node_id, "dom_id", f"#{dom_id}")
            self.add_edge(file_id, node_id, "declares_dom")
        for match in BUTTON_RE.finditer(text):
            attrs = dict(ATTR_RE.findall(match.group(1)))
            label = re.sub(r"<[^>]+>", "", match.group(2)).strip()
            key = attrs.get("id") or attrs.get("data-workflow-action") or label
            if not key:
                continue
            node_id = f"button:{key}"
            self.add_node(
                node_id,
                "button",
                label or key,
                html_id=attrs.get("id"),
                workflow_action=attrs.get("data-workflow-action"),
            )
            self.add_edge(file_id, node_id, "declares_button")

    def scan_markdown(self, path: Path, text: str) -> None:
        file_id = self.add_file(path, text)
        for line_no, line in enumerate(text.splitlines(), start=1):
            if line.startswith("## "):
                section = line.lstrip("# ").strip()
                node_id = f"doc_section:{self.rel(path)}:{section}"
                self.add_node(node_id, "doc_section", section, path=self.rel(path), line=line_no)
                self.add_edge(file_id, node_id, "documents")

    def finalize(self) -> dict:
        flows = []
        all_text_by_file = {node["path"]: json.dumps(node, ensure_ascii=False).lower() for node in self.nodes.values() if node.get("type") == "file"}
        node_blob = json.dumps(list(self.nodes.values()), ensure_ascii=False).lower()
        for flow_id, definition in FLOW_DEFINITIONS.items():
            matched_files = sorted(
                path for path, blob in all_text_by_file.items()
                if any(keyword.lower() in path.lower() or keyword.lower() in blob for keyword in definition["keywords"])
            )
            expected = definition["expected_files"]
            missing = [path for path in expected if f"file:{path}" not in self.nodes]
            keyword_hits = [keyword for keyword in definition["keywords"] if keyword.lower() in node_blob]
            flows.append(
                {
                    "id": flow_id,
                    "label": definition["label"],
                    "expected_files": expected,
                    "missing_files": missing,
                    "matched_file_count": len(matched_files),
                    "sample_files": matched_files[:12],
                    "keyword_hits": keyword_hits[:12],
                    "status": "ok" if not missing and matched_files and keyword_hits else "needs_review",
                }
            )
        nodes = sorted(self.nodes.values(), key=lambda item: (item["type"], item["id"]))
        edges = sorted(self.edges, key=lambda item: (item["source"], item["kind"], item["target"]))
        return {
            "schema_version": GRAPH_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "project": "Investment Research OS",
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges,
            "flows": flows,
            "summary": summarize(nodes, edges, flows),
        }


def infer_layer(rel: str) -> str:
    if rel.startswith("backend/research_os_main.py"):
        return "api_entrypoint"
    if rel.startswith("backend/research_os/"):
        return "backend_domain"
    if rel.startswith("mobile_app/research_console/"):
        return "classic_console"
    if rel.startswith("tools/"):
        return "operations_tooling"
    if rel.startswith("docs/"):
        return "operations_docs"
    return "other"


def summarize(nodes: list[dict], edges: list[dict], flows: list[dict]) -> dict:
    by_type: dict[str, int] = {}
    by_layer: dict[str, int] = {}
    for node in nodes:
        by_type[node["type"]] = by_type.get(node["type"], 0) + 1
        if node.get("layer"):
            by_layer[str(node["layer"])] = by_layer.get(str(node["layer"]), 0) + 1
    return {
        "nodes_by_type": dict(sorted(by_type.items())),
        "files_by_layer": dict(sorted(by_layer.items())),
        "edge_kinds": dict(sorted({edge["kind"]: sum(1 for item in edges if item["kind"] == edge["kind"]) for edge in edges}.items())),
        "flows_ok": sum(1 for flow in flows if flow["status"] == "ok"),
        "flows_needing_review": [flow["id"] for flow in flows if flow["status"] != "ok"],
    }


def iter_scan_files(root: Path) -> Iterable[Path]:
    seen: set[Path] = set()
    for pattern in SCAN_GLOBS:
        for path in root.glob(pattern):
            if not path.is_file() or any(part in EXCLUDED_PARTS for part in path.parts):
                continue
            if path not in seen:
                seen.add(path)
                yield path


def build_graph(root: Path) -> dict:
    builder = GraphBuilder(root=root)
    for path in sorted(iter_scan_files(root)):
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        suffix = path.suffix.lower()
        if suffix == ".py":
            builder.scan_python(path, text)
        elif suffix in {".js", ".mjs", ".ts", ".tsx"}:
            builder.scan_js_like(path, text)
        elif suffix == ".html":
            builder.scan_html(path, text)
        elif suffix == ".md":
            builder.scan_markdown(path, text)
        else:
            builder.add_file(path, text)
    return builder.finalize()


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (candidate / "mobile_app" / "research_console").exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def main() -> int:
    parser = argparse.ArgumentParser(description="코드/운영 지식 그래프를 생성합니다.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--print-summary", action="store_true")
    args = parser.parse_args()
    root = project_root(Path.cwd())
    graph = build_graph(root)
    output = args.output if args.output.is_absolute() else root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"프로젝트 루트: {root}")
    print(f"코드 지식 그래프 저장: {output.relative_to(root)}")
    print(f"노드 {graph['node_count']}개 / 엣지 {graph['edge_count']}개 / 정상 흐름 {graph['summary']['flows_ok']}/{len(graph['flows'])}개")
    if args.print_summary:
        print(json.dumps(graph["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
