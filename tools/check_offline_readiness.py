"""Run backend-free readiness checks for the Investment Research OS."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


CHECKS = [
    ("Git 동기화 상태", ["tools/check_git_sync_status.py"]),
    ("백엔드 런타임 준비도", ["tools/check_backend_runtime_env.py"]),
    ("백엔드 모듈 상태", ["tools/check_backend_module_health.py", "--strict"]),
    ("클래식 콘솔 정적 계약", ["tools/check_console_static_contract.py", "--strict"]),
    ("클래식 콘솔 자산/JS", ["tools/check_console_asset_and_js.py"]),
    (
        "포트폴리오 저장 수량",
        [
            "tools/check_portfolio_store.py",
            "--portfolio",
            "이형주",
            "--min-holdings",
            "17",
            "--forbid-zero",
        ],
    ),
    ("리서치 소스 저장 상태", ["tools/check_research_source_store.py", "--strict"]),
    ("저장 자료 품질", ["tools/check_storage_quality_store.py", "--strict"]),
    ("매일 추천 저장/추적", ["tools/check_daily_recommendations_store.py", "--require-milestones", "--require-quality"]),
]


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (
            candidate / "research_vault"
        ).exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def main() -> int:
    root = project_root(Path.cwd())
    print(f"프로젝트 루트: {root}", flush=True)
    for label, args in CHECKS:
        print(f"\n==> {label}", flush=True)
        completed = subprocess.run([sys.executable, *args], cwd=root, check=False)
        if completed.returncode != 0:
            print(f"오프라인 운영 점검 실패: {label}", flush=True)
            return completed.returncode
    print("\n오프라인 운영 점검 통과", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
