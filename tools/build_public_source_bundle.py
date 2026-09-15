"""Build a reviewable public source ZIP from Git-tracked files only.

It does not package local data, untracked files, environment files, dependency
folders, or generated reports. The output is scanned again before it replaces
the requested ZIP path.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import zipfile
from pathlib import Path

from check_public_repo_safety import (
    is_forbidden_path,
    project_root,
    scan_archive,
    scan_file_candidates,
)


def tracked_files(root: Path) -> list[str]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise SystemExit((completed.stderr or completed.stdout).decode("utf-8", errors="replace"))
    return [item for item in completed.stdout.decode("utf-8", errors="replace").split("\0") if item]


def current_commit(root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def validate_bundle_files(root: Path, files: list[str]) -> tuple[list[str], list[str]]:
    missing_or_linked = [
        relative
        for relative in files
        if not (root / relative).is_file() or (root / relative).is_symlink()
    ]
    forbidden = [relative for relative in files if is_forbidden_path(relative)]
    scanned_paths, content_issues = scan_file_candidates(root, files)
    path_issues = sorted(set(missing_or_linked + forbidden + scanned_paths))
    return path_issues, content_issues


def safe_prefix(value: str) -> str:
    candidate = value.strip().replace("\\", "/").strip("/")
    if not candidate or "/" in candidate or candidate in {".", ".."}:
        raise SystemExit("--prefix는 공백, 경로 구분자, '..' 없이 한 폴더명이어야 합니다.")
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser(description="Git 추적 소스만 포함한 공개 검토용 ZIP을 생성합니다.")
    parser.add_argument("--output", type=Path, help="생성할 ZIP 경로입니다. 기본값은 output 아래입니다.")
    parser.add_argument("--prefix", help="ZIP 안의 최상위 폴더명입니다.")
    parser.add_argument("--json", action="store_true", help="결과를 JSON으로 출력합니다.")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    files = tracked_files(root)
    path_issues, content_issues = validate_bundle_files(root, files)
    if path_issues or content_issues:
        result = {
            "status": "error",
            "project_root": str(root),
            "candidate_file_count": len(files),
            "path_issues": path_issues,
            "content_issues": content_issues,
            "message": "안전 점검에 실패해 공개 ZIP을 만들지 않았습니다.",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result["message"])
        return 1

    prefix = safe_prefix(args.prefix or root.name)
    output = (args.output or root / "output" / f"{root.name}-public-source.zip").expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f"{output.name}.tmp")
    temporary.unlink(missing_ok=True)

    manifest = {
        "schema_version": 1,
        "kind": "public-source-review-bundle",
        "source_commit": current_commit(root),
        "file_count": len(files),
        "files": files,
    }
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for relative in files:
                archive_name = f"{prefix}/{relative.replace(chr(92), '/')}"
                archive.write(root / relative, arcname=archive_name)
            archive.writestr(
                f"{prefix}/PUBLIC-BUNDLE-MANIFEST.json",
                json.dumps(manifest, ensure_ascii=False, indent=2),
            )

        archive_result = scan_archive(temporary)
        if archive_result["status"] != "ok":
            temporary.unlink(missing_ok=True)
            result = {
                "status": "error",
                "project_root": str(root),
                "archive_check": archive_result,
                "message": "생성 ZIP의 안전 재점검에 실패해 결과 파일을 삭제했습니다.",
            }
            print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result["message"])
            return 1
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)

    result = {
        "status": "ok",
        "project_root": str(root),
        "output": str(output),
        "source_commit": manifest["source_commit"],
        "file_count": len(files),
        "message": "Git 추적 소스만 포함한 공개 검토용 ZIP 생성 완료",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result["message"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
