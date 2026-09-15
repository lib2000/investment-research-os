"""Check public Git candidates and source-release archives for private data.

The checker intentionally reports only file paths. It never prints a matched
credential value, so it can be used in CI, release logs, and support captures.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import zipfile
from pathlib import Path, PurePosixPath


ENV_FILE_PATH_PATTERN = re.compile(r"(^|/)\.env($|[./])")

FORBIDDEN_PATH_PATTERNS = [
    ENV_FILE_PATH_PATTERN,
    re.compile(r"(^|/)research_vault($|/)"),
    re.compile(r"(^|/)(secrets|credentials)($|/)"),
    re.compile(r"(^|/)(attachments?|backups?)($|/)", re.IGNORECASE),
    re.compile(r"(^|/)\.git($|/)"),
    re.compile(r"(^|/)(node_modules|\.venv|venv|dist|build)($|/)", re.IGNORECASE),
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
    re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{30,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{24,}", re.IGNORECASE),
]

SENSITIVE_CONFIG_NAMES = (
    "TOSS_CLIENT_SECRET",
    "TOSS_CLIENT_ID",
    "TOSS_ACCOUNT_SEQ",
    "KIS_APP_KEY",
    "KIS_APP_SECRET",
    "KIWOOM_API_KEY",
    "KIWOOM_API_SECRET",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_REPORT_ALERT_BOT_TOKEN",
    "DART_API_KEY",
    "FMP_API_KEY",
    "FINNHUB_API_KEY",
    "TAVILY_API_KEY",
    "BRAVE_API_KEY",
    "FIRECRAWL_API_KEY",
    "FIRECRAWL_MONITOR_WEBHOOK_SECRET",
    "DEV_USER_TOKEN",
    "SECRET_SALT",
)
_SENSITIVE_CONFIG_NAME_PATTERN = "|".join(SENSITIVE_CONFIG_NAMES)
SENSITIVE_ASSIGNMENT_PATTERNS = [
    re.compile(
        rf"(?m)^[ \t]*(?:[-*][ \t]*)?(?:export[ \t]+)?(?P<name>{_SENSITIVE_CONFIG_NAME_PATTERN})[ \t]*=[ \t]*(?P<value>[^#\r\n]+)"
    ),
    re.compile(
        rf"(?m)[\"'](?P<name>{_SENSITIVE_CONFIG_NAME_PATTERN})[\"'][ \t]*:[ \t]*[\"'](?P<value>[^\"'\r\n]+)"
    ),
]

TEXT_SUFFIXES = {
    ".py",
    ".ps1",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
    ".css",
    ".md",
    ".txt",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".example",
}

MAX_ARCHIVE_MEMBER_COUNT = 10_000
MAX_ARCHIVE_TEXT_ENTRY_BYTES = 4 * 1024 * 1024


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


def normalize_relative_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def is_allowed_path(path: str) -> bool:
    normalized = normalize_relative_path(path)
    return (
        Path(normalized).name == ".env.example"
        or normalized in ALLOWED_PATHS
        or any(normalized.endswith(f"/{allowed}") for allowed in ALLOWED_PATHS)
    )


def is_forbidden_path(path: str) -> bool:
    normalized = normalize_relative_path(path)
    for pattern in FORBIDDEN_PATH_PATTERNS:
        if not pattern.search(normalized):
            continue
        if pattern is ENV_FILE_PATH_PATTERN and is_allowed_path(normalized):
            continue
        return True
    return False


def should_scan_content(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES or path.name.endswith(".env.example")


def _looks_like_placeholder(value: str) -> bool:
    normalized = value.strip().strip("\"'").strip()
    lowered = normalized.lower()
    if not normalized or normalized in {"*", "***", "********"}:
        return True
    if normalized.startswith(("${", "$", "<")):
        return True
    return any(
        marker in lowered
        for marker in (
            "replace-with",
            "dev-local-token",
            "your-",
            "example",
            "change-me",
            "placeholder",
            "os.getenv",
            "getenv(",
        )
    )


def _looks_like_sensitive_value(value: str) -> bool:
    normalized = value.strip().strip("\"'").strip()
    if _looks_like_placeholder(normalized) or len(normalized) < 8:
        return False
    if any(character.isspace() for character in normalized):
        return False
    return not any(character in normalized for character in "<>{}[]()")


def contains_secret_like_content(text: str) -> bool:
    if any(pattern.search(text) for pattern in SECRET_VALUE_PATTERNS):
        return True
    for pattern in SENSITIVE_ASSIGNMENT_PATTERNS:
        for match in pattern.finditer(text):
            if _looks_like_sensitive_value(match.group("value")):
                return True
    return False


def scan_file_candidates(root: Path, files: list[str]) -> tuple[list[str], list[str]]:
    path_issues = [path for path in files if is_forbidden_path(path)]
    content_issues: list[str] = []

    for relative in files:
        path = root / relative
        if not path.exists() or not path.is_file() or not should_scan_content(path):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if contains_secret_like_content(text):
            content_issues.append(relative)

    return path_issues, content_issues


def scan_repository(root: Path) -> dict:
    files = public_candidate_files(root)
    path_issues, content_issues = scan_file_candidates(root, files)
    ok = not path_issues and not content_issues
    return {
        "status": "ok" if ok else "error",
        "scan_target": "repository",
        "project_root": str(root),
        "candidate_file_count": len(files),
        "path_issue_count": len(path_issues),
        "content_issue_count": len(content_issues),
        "path_issues": path_issues,
        "content_issues": content_issues,
    }


def _archive_member_path_issue(member_name: str) -> bool:
    normalized = member_name.replace("\\", "/")
    pure_path = PurePosixPath(normalized)
    if pure_path.is_absolute() or re.match(r"^[A-Za-z]:/", normalized):
        return True
    if ".." in pure_path.parts:
        return True
    return is_forbidden_path(normalized)


def scan_archive(archive_path: Path) -> dict:
    resolved = archive_path.expanduser().resolve()
    path_issues: list[str] = []
    content_issues: list[str] = []
    member_count = 0
    crc_failure: str | None = None

    try:
        with zipfile.ZipFile(resolved) as archive:
            members = [member for member in archive.infolist() if not member.is_dir()]
            member_count = len(members)
            if member_count > MAX_ARCHIVE_MEMBER_COUNT:
                path_issues.append("archive_member_count_exceeds_limit")

            for member in members:
                relative = member.filename.replace("\\", "/")
                if _archive_member_path_issue(relative):
                    path_issues.append(relative)
                    continue
                if not should_scan_content(Path(relative)):
                    continue
                if member.file_size > MAX_ARCHIVE_TEXT_ENTRY_BYTES:
                    content_issues.append(f"{relative} (text_entry_too_large_to_scan)")
                    continue
                text = archive.read(member).decode("utf-8", errors="ignore")
                if contains_secret_like_content(text):
                    content_issues.append(relative)

            crc_failure = archive.testzip()
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile):
        path_issues.append("archive_unreadable")

    if crc_failure:
        path_issues.append(f"{crc_failure} (crc_error)")

    ok = not path_issues and not content_issues
    return {
        "status": "ok" if ok else "error",
        "scan_target": "archive",
        "project_root": None,
        "archive_path": str(resolved),
        "archive_member_count": member_count,
        "candidate_file_count": member_count,
        "path_issue_count": len(path_issues),
        "content_issue_count": len(content_issues),
        "path_issues": path_issues,
        "content_issues": content_issues,
    }


def print_human_result(result: dict) -> None:
    target = "공개 ZIP" if result["scan_target"] == "archive" else "공개 Git 후보"
    print(f"점검 대상: {target}")
    print(f"후보 파일: {result['candidate_file_count']}개")
    print(f"민감 경로 의심: {result['path_issue_count']}개")
    print(f"토큰/개인키/계정식별값 의심: {result['content_issue_count']}개")
    if result["path_issues"]:
        print("민감 경로 의심 파일:")
        for path in result["path_issues"]:
            print(f"- {path}")
    if result["content_issues"]:
        print("민감정보 내용 의심 파일 (값은 출력하지 않음):")
        for path in result["content_issues"]:
            print(f"- {path}")
    message = "공개 저장소/ZIP 안전 점검 통과" if result["status"] == "ok" else "공개 저장소/ZIP 안전 점검 실패"
    print(message)


def main() -> int:
    parser = argparse.ArgumentParser(description="공개 Git 후보 또는 공개 ZIP의 민감정보 포함 여부를 점검합니다.")
    parser.add_argument("--json", action="store_true", help="점검 결과를 JSON으로 출력합니다.")
    parser.add_argument("--archive", type=Path, help="공개 배포 전 점검할 ZIP 경로입니다.")
    args = parser.parse_args()

    result = scan_archive(args.archive) if args.archive else scan_repository(project_root(Path.cwd()))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_human_result(result)
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
