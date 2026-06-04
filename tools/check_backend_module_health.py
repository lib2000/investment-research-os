"""Backend module boundary and source-health checks without importing FastAPI deps."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

EXPECTED_MODULES = {
    "classification.py",
    "brokerage.py",
    "code_knowledge.py",
    "customs_trade.py",
    "daily_recommendations.py",
    "data_providers.py",
    "export_utils.py",
    "file_extraction.py",
    "kcif_reports.py",
    "kiwoom_auth.py",
    "investment_calendar.py",
    "llm_bridge_status.py",
    "market_journal.py",
    "models.py",
    "portfolio_analysis_coverage.py",
    "portfolio_import.py",
    "portfolio_performance.py",
    "portfolio_store.py",
    "portfolio_sync.py",
    "public_ir_sec.py",
    "rag_memory.py",
    "recent_activity.py",
    "regional_sources.py",
    "research_memory.py",
    "security.py",
    "settings.py",
    "source_url_preview.py",
    "storage_quality.py",
    "system_health.py",
    "ticker_registry.py",
    "web_capture.py",
}
EXPECTED_MAIN_IMPORTS = {
    "research_os.classification",
    "research_os.brokerage",
    "research_os.code_knowledge",
    "research_os.customs_trade",
    "research_os.daily_recommendations",
    "research_os.data_providers",
    "research_os.export_utils",
    "research_os.file_extraction",
    "research_os.kcif_reports",
    "research_os.kiwoom_auth",
    "research_os.investment_calendar",
    "research_os.llm_bridge_status",
    "research_os.market_journal",
    "research_os.models",
    "research_os.portfolio_analysis_coverage",
    "research_os.portfolio_import",
    "research_os.portfolio_performance",
    "research_os.portfolio_store",
    "research_os.portfolio_sync",
    "research_os.public_ir_sec",
    "research_os.rag_memory",
    "research_os.recent_activity",
    "research_os.regional_sources",
    "research_os.research_memory",
    "research_os.security",
    "research_os.settings",
    "research_os.source_url_preview",
    "research_os.storage_quality",
    "research_os.system_health",
    "research_os.ticker_registry",
    "research_os.web_capture",
}
BANNED_TERMS = ("bigkinds", "빅카인즈")
CURRENT_MAIN_LINE_BASELINE = 24016
DEFAULT_MAIN_MAX_LINES = 26000
DEFAULT_MIN_MODULE_COUNT = 24


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (candidate / "backend" / "research_os").exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def parse_python(path: Path) -> ast.Module:
    source = path.read_text(encoding="utf-8-sig")
    return ast.parse(source, filename=str(path))


def imported_modules(tree: ast.Module) -> set[str]:
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def main() -> int:
    parser = argparse.ArgumentParser(description="백엔드 모듈 분리/문법/금지 소스 잔존 여부를 점검합니다.")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--main-large-warning-lines", type=int, default=20000)
    parser.add_argument("--main-max-lines", type=int, default=DEFAULT_MAIN_MAX_LINES, help="research_os_main.py가 이 줄 수를 넘으면 실패")
    parser.add_argument("--min-module-count", type=int, default=DEFAULT_MIN_MODULE_COUNT, help="분리 도메인 모듈 최소 개수")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    backend = root / "backend"
    module_dir = backend / "research_os"
    errors: list[str] = []
    warnings: list[str] = []

    module_paths = sorted(module_dir.glob("*.py"))
    module_files = {path.name for path in module_paths}
    missing = sorted(EXPECTED_MODULES - module_files)
    if missing:
        errors.append("분리 기대 모듈 누락: " + ", ".join(missing))
    if len(module_files) < args.min_module_count:
        errors.append(f"백엔드 분리 모듈 수 부족: {len(module_files)}개 / 필요 {args.min_module_count}개")

    python_files = [backend / "research_os_main.py", *module_paths]
    for path in python_files:
        try:
            parse_python(path)
        except SyntaxError as exc:
            errors.append(f"문법 오류: {path.relative_to(root)}:{exc.lineno} {exc.msg}")
        text = path.read_text(encoding="utf-8-sig", errors="replace").lower()
        for term in BANNED_TERMS:
            if term.lower() in text:
                errors.append(f"삭제 요청 소스명 잔존: {path.relative_to(root)} contains {term}")

    main_path = backend / "research_os_main.py"
    main_tree = parse_python(main_path)
    main_imports = imported_modules(main_tree)
    missing_imports = sorted(EXPECTED_MAIN_IMPORTS - main_imports)
    if missing_imports:
        errors.append("research_os_main.py 분리 모듈 import 누락: " + ", ".join(missing_imports))

    main_lines = len(main_path.read_text(encoding="utf-8-sig").splitlines())
    if main_lines > args.main_max_lines:
        errors.append(f"research_os_main.py 줄 수 상한 초과: {main_lines}줄 / 상한 {args.main_max_lines}줄")
    if main_lines > args.main_large_warning_lines:
        delta = main_lines - CURRENT_MAIN_LINE_BASELINE
        if delta < 0:
            trend = f"기준 대비 {abs(delta)}줄 감소"
        elif delta > 0:
            trend = f"기준 대비 {delta}줄 증가"
        else:
            trend = "기준 대비 변화 없음"
        remaining = args.main_max_lines - main_lines
        warnings.append(
            f"research_os_main.py가 아직 큼: {main_lines}줄({trend}, 상한까지 {remaining}줄 여유). 라우터/도메인 분리 계속 권장"
        )

    largest_modules = sorted(
        ((path.name, len(path.read_text(encoding="utf-8-sig").splitlines())) for path in module_paths),
        key=lambda item: item[1],
        reverse=True,
    )[:5]

    print(f"프로젝트 루트: {root}")
    print(f"백엔드 모듈 수: {len(module_files)}개 / 최소 {args.min_module_count}개")
    print(f"Python 파싱 대상: {len(python_files)}개")
    print(f"research_os_main.py: {main_lines}줄 / 상한 {args.main_max_lines}줄")
    print("큰 도메인 모듈: " + ", ".join(f"{name}={lines}줄" for name, lines in largest_modules))
    if warnings:
        for warning in warnings:
            print(f"주의: {warning}")
    if errors:
        for error in errors:
            print(f"오류: {error}")
        return 1 if args.strict else 0
    print("백엔드 모듈 상태 정상")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
