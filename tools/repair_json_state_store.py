"""Safely recover a known trailing-delimiter corruption in a local JSON state file."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


ROOT_CANDIDATE = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_CANDIDATE / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from research_os.state_store import write_json_store  # noqa: E402


DEFAULT_RELATIVE_PATH = Path("research_vault") / "_system" / "interest_collection_targets.json"


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (candidate / "research_vault").exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def inspect_recovery(path: Path) -> tuple[dict, str]:
    raw = path.read_text(encoding="utf-8-sig")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        decoder = json.JSONDecoder()
        try:
            payload, end = decoder.raw_decode(raw.lstrip())
        except json.JSONDecodeError as decode_exc:
            raise ValueError(f"첫 JSON 객체를 복구할 수 없습니다: {decode_exc.msg}") from exc
        trailing = raw.lstrip()[end:].strip()
        if not isinstance(payload, dict) or trailing != "}":
            raise ValueError(
                "안전하게 복구할 수 없는 JSON 손상입니다. 단일 여분 닫는 중괄호만 자동 복구할 수 있습니다."
            ) from exc
        return payload, "trailing_closing_brace"
    if not isinstance(payload, dict):
        raise ValueError("상태 JSON 최상위 구조가 객체가 아닙니다.")
    return payload, "already_valid"


def main() -> int:
    parser = argparse.ArgumentParser(description="복구 가능한 로컬 상태 JSON 손상만 원자적으로 복구합니다.")
    parser.add_argument("--path", type=Path, default=DEFAULT_RELATIVE_PATH)
    parser.add_argument("--apply", action="store_true", help="dry-run 대신 원본 백업과 원자적 복구를 실행합니다.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    state_dir = (root / "research_vault" / "_system").resolve()
    path = (args.path if args.path.is_absolute() else root / args.path).resolve()
    try:
        path.relative_to(state_dir)
    except ValueError:
        raise SystemExit(f"research_vault/_system 밖의 파일은 복구할 수 없습니다: {path}")
    if not path.exists():
        raise SystemExit(f"상태 JSON 파일을 찾지 못했습니다: {path}")
    try:
        payload, recovery_kind = inspect_recovery(path)
    except ValueError as exc:
        result = {"status": "error", "path": str(path.relative_to(root)), "error": str(exc), "applied": False}
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result["error"])
        return 1

    result = {
        "status": "success",
        "path": str(path.relative_to(root)),
        "recovery_kind": recovery_kind,
        "applied": False,
        "backup_path": None,
        "updated_at": payload.get("updated_at"),
    }
    if args.apply and recovery_kind != "already_valid":
        timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
        backup = path.with_name(f"{path.name}.corrupt-{timestamp}.bak")
        backup.write_bytes(path.read_bytes())
        write_json_store(path, payload)
        result.update({"applied": True, "backup_path": str(backup.relative_to(root))})
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        message = "복구 적용" if result["applied"] else "dry-run"
        print(f"상태 JSON {message}: {result['path']} | {recovery_kind}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
