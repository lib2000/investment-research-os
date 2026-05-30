"""Report local git sync state without requiring network access."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / ".git").exists() or (candidate / ".git").is_file():
            if (candidate / "backend" / "research_os_main.py").exists():
                return candidate
    raise SystemExit("InvestmentJournalApp Git 루트를 찾지 못했습니다.")


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise SystemExit((completed.stderr or completed.stdout).strip() or f"git {' '.join(args)} 실패")
    return completed.stdout.strip()


def count(root: Path, rev_range: str) -> int:
    output = git(root, "rev-list", "--count", rev_range)
    return int(output or "0")


def main() -> int:
    parser = argparse.ArgumentParser(description="로컬 Git 동기화 상태를 확인합니다.")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch", default=None)
    args = parser.parse_args()

    root = project_root(Path.cwd())
    branch = args.branch or git(root, "branch", "--show-current")
    upstream = f"{args.remote}/{branch}"
    status = git(root, "status", "--short", "--branch")
    ahead = count(root, f"{upstream}..HEAD")
    behind = count(root, f"HEAD..{upstream}")
    latest = git(root, "log", "-1", "--oneline")

    print(f"프로젝트 루트: {root}")
    print(f"브랜치: {branch}")
    print(f"업스트림: {upstream}")
    print(f"최신 커밋: {latest}")
    print(f"동기화: ahead={ahead}, behind={behind}")
    print("상태:")
    print(status)
    if ahead > 0:
        print(f"푸시 대기 커밋 {ahead}개가 있습니다. Windows Git 인증이 가능한 터미널에서 `git push {args.remote} {branch}`를 실행하세요.")
    if behind > 0:
        print(f"주의: 원격이 {behind}커밋 앞서 있습니다. pull/rebase 전에는 충돌 가능성을 확인하세요.")
    print("Git 동기화 상태 확인 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
