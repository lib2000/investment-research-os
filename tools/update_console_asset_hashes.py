from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path


CONSOLE_DIR = Path("mobile_app") / "research_console"
ASSET_FILES = ("styles.css", "console.js", "api.js")
MAX_UPDATE_PASSES = 5


def short_asset_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def versioned_ref(asset_name: str, version: str) -> str:
    return f"./{asset_name}?v={version}"


def update_html_content(content: str, versions: dict[str, str]) -> str:
    updated = content
    for asset_name in ("styles.css", "console.js"):
        versioned = versioned_ref(asset_name, versions[asset_name])
        updated = re.sub(
            rf'((?:href|src)=["\'])\./{re.escape(asset_name)}(?:\?v=[^"\']*)?(["\'])',
            rf"\1{versioned}\2",
            updated,
        )
    return updated


def update_console_js_content(content: str, versions: dict[str, str]) -> str:
    return re.sub(
        r'((?:from|import)\s+["\'])\./api\.js(?:\?v=[^"\']*)?(["\'])',
        rf"\1{versioned_ref('api.js', versions['api.js'])}\2",
        content,
    )


def compute_asset_versions(console_dir: Path) -> dict[str, str]:
    return {
        asset_name: short_asset_hash(console_dir / asset_name)
        for asset_name in ASSET_FILES
    }


def planned_updates(project_root: Path) -> dict[Path, str]:
    console_dir = project_root / CONSOLE_DIR
    versions = compute_asset_versions(console_dir)
    html_path = console_dir / "index.html"
    js_path = console_dir / "console.js"
    return {
        html_path: update_html_content(html_path.read_text(encoding="utf-8"), versions),
        js_path: update_console_js_content(js_path.read_text(encoding="utf-8"), versions),
    }


def changed_update_paths(project_root: Path) -> list[tuple[Path, str]]:
    return [
        (path, next_content)
        for path, next_content in planned_updates(project_root).items()
        if path.read_text(encoding="utf-8") != next_content
    ]


def update_console_asset_hashes(project_root: Path, *, check: bool = False) -> int:
    changed: list[Path] = []
    pending = changed_update_paths(project_root)

    if check and pending:
        print("콘솔 자산 해시가 최신이 아닙니다:")
        for path, _next_content in pending:
            print(f"- {path}")
        print("해결: python tools/update_console_asset_hashes.py")
        return 1

    for _pass_number in range(MAX_UPDATE_PASSES):
        if not pending:
            break
        changed.extend(path for path, _next_content in pending)
        for path, next_content in pending:
            path.write_text(next_content, encoding="utf-8", newline="\n")
        pending = changed_update_paths(project_root)
    else:
        print("콘솔 자산 해시가 안정화되지 않았습니다. 참조 구조를 확인하세요.")
        return 2

    changed = list(dict.fromkeys(changed))
    for path, next_content in planned_updates(project_root).items():
        current_content = path.read_text(encoding="utf-8")
        if current_content != next_content:
            print(f"콘솔 자산 해시 검증 실패: {path}")
            return 2

    if changed:
        print("콘솔 자산 해시 갱신 완료:")
        for path in changed:
            print(f"- {path}")
    else:
        print("콘솔 자산 해시가 이미 최신입니다.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classic Research Console JS/CSS 참조에 파일 내용 기반 cache-busting 해시를 붙입니다."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="파일을 수정하지 않고 해시가 최신인지 확인합니다.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="프로젝트 루트 경로입니다.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return update_console_asset_hashes(args.root.resolve(), check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
