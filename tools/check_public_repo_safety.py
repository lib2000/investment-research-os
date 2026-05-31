"""Check that public Git tracking does not include private local data."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


FORBIDDEN_PATH_PATTERNS = [
    re.compile(r"(^|/)\.env($|[./])"),
    re.compile(r"(^|/)research_vault($|/)"),
    re.compile(r"(^|/)(secrets|credentials)($|/)"),
    re.compile(r"(^|/).*(access[-_]?token|token[-_]?cache).*\.json$", re.IGNORECASE),
    re.compile(r".*\.(sqlite|sqlite3|db|pem|key|p12|pfx)$", re.IGNORECASE),
]

ALLOWED_PATHS = {
    "backend/.env.example",
    "mobile_app/.env.example",
    "apps/mobile/.env.example",
}

SECRET_VALUE_PATTERNS = [
    re.compile(r"-----BEGIN (RSA |EC |OPENSSH |PRIVATE )?PRIVATE KEY-----"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
]

TEXT_SUFFIXES = {
    ".py", ".ps1", ".js", ".jsx", ".ts", ".tsx", ".html", ".css",
    ".md", ".txt", ".json", ".yml", ".yaml", ".toml", ".example",
}


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / ".git").exists() and (candidate / "backend" / "research_os_main.py").exists():
            return candidate
    raise SystemExit("InvestmentJournalApp Git 루트를 찾지 못했습니다.")


def public_candidate_files(root: Path) -> list[str]:
    completed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise SystemExit((completed.stderr or completed.stdout).decode("utf-8", errors="replace"))
    raw = completed.stdout.decode("utf-8", errors="replace")
    return [item for item in raw.split("\0") if item]


def is_forbidden_path(path: str) -> bool:
    if path in ALLOWED_PATHS:
        return False
    normalized = path.replace("\\", "/")
    return any(pattern.search(normalized) for pattern in FORBIDDEN_PATH_PATTERNS)


def should_scan_content(path: Path) -> bool:
    if path.suffix.lower() in TEXT_SUFFIXES:
        return True
    return path.name.endswith(".env.example")


def main() -> int:
    root = project_root(Path.cwd())
    files = public_candidate_files(root)
    path_issues = [path for path in files if is_forbidden_path(path)]
    content_issues: list[str] = []

    for relative in files:
        path = root / relative
        if not path.exists() or not should_scan_content(path):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in SECRET_VALUE_PATTERNS:
            if pattern.search(text):
                content_issues.append(relative)
                break

    print(f"프로젝트 루트: {root}")
    print(f"공개 후보 파일: {len(files)}개")
    print(f"민감 경로 추적 의심: {len(path_issues)}개")
    print(f"토큰/개인키 패턴 의심: {len(content_issues)}개")

    if path_issues:
        print("민감 경로 추적 의심 파일:")
        for path in path_issues:
            print(f"- {path}")
    if content_issues:
        print("토큰/개인키 패턴 의심 파일:")
        for path in content_issues:
            print(f"- {path}")

    if path_issues or content_issues:
        print("공개 저장소 안전 점검 실패")
        return 1
    print("공개 저장소 안전 점검 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
