"""Check classic console cache-busting references and JavaScript syntax."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from update_console_asset_hashes import update_console_asset_hashes


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "mobile_app" / "research_console" / "console.js").exists() and (
            candidate / "tools" / "update_console_asset_hashes.py"
        ).exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def main() -> int:
    parser = argparse.ArgumentParser(description="콘솔 자산 해시와 JavaScript 문법을 점검합니다.")
    parser.add_argument("--skip-node", action="store_true", help="node --check를 건너뜁니다.")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    asset_status = update_console_asset_hashes(root, check=True)
    if asset_status != 0:
        return asset_status

    if not args.skip_node:
        completed = subprocess.run(
            ["node", "--check", "mobile_app/research_console/console.js"],
            cwd=root,
            check=False,
        )
        if completed.returncode != 0:
            print("클래식 콘솔 JavaScript 문법 확인 실패")
            return completed.returncode

    print("클래식 콘솔 자산/JS 상태 정상")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
