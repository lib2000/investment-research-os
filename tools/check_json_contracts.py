"""Check that repository check tools expose a machine-readable JSON contract."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = PROJECT_ROOT / "tools"


def check_tool_source(path: Path) -> dict:
    source = path.read_text(encoding="utf-8")
    has_json_flag = 'add_argument("--json"' in source
    has_json_dump = "json.dumps(" in source
    has_main = re.search(r"def\s+main\s*\(", source) is not None
    status_contract = any(
        token in source
        for token in (
            '"status"',
            "'status'",
            "status ==",
            "errors =",
            "problems =",
            "strict_errors(",
            '"ok"',
        )
    )
    errors = []
    if not has_main:
        errors.append("missing main()")
    if not has_json_flag:
        errors.append("missing --json argument")
    if not has_json_dump:
        errors.append("missing json.dumps output")
    if not status_contract:
        errors.append("missing status contract hint")
    return {
        "path": str(path.relative_to(PROJECT_ROOT)),
        "has_main": has_main,
        "has_json_flag": has_json_flag,
        "has_json_dump": has_json_dump,
        "status_contract": status_contract,
        "status": "success" if not errors else "failure",
        "errors": errors,
    }


def build_result() -> dict:
    results = [check_tool_source(path) for path in sorted(TOOLS_DIR.glob("check_*.py"))]
    failed = [item for item in results if item["status"] != "success"]
    return {
        "status": "success" if not failed else "failure",
        "tool_count": len(results),
        "failed_count": len(failed),
        "failed_tools": [item["path"] for item in failed],
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="check_*.py JSON 출력 계약을 점검합니다.")
    parser.add_argument("--json", action="store_true", help="점검 결과를 JSON으로 출력합니다.")
    args = parser.parse_args()

    result = build_result()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"[{result['status']}] check_json_contracts")
        print(f"- tool_count: {result['tool_count']}")
        print(f"- failed_count: {result['failed_count']}")
        for path in result["failed_tools"]:
            print(f"- failed: {path}")
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
