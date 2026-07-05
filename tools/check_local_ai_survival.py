"""Check local-first resilience if premium external AI access disappears."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (
            candidate / "research_vault"
        ).exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def main() -> int:
    parser = argparse.ArgumentParser(description="고급 외부 AI 제한 시 로컬 운영 생존 모드를 점검합니다.")
    parser.add_argument("--json", action="store_true", help="점검 결과를 JSON으로 출력합니다.")
    parser.add_argument("--strict", action="store_true", help="핵심 로컬 운영 조건이 빠지면 실패 코드로 종료합니다.")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    backend_dir = root / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    from research_os.local_ai_survival import build_local_ai_survival_status
    from research_os.settings import Settings

    payload = build_local_ai_survival_status(Settings(research_vault_dir=str(root / "research_vault")))
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"[{payload['status']}] local_ai_survival_status")
        print(f"- local_operation_ready: {payload['local_operation_ready']}")
        print(
            "- critical: "
            f"{payload['critical_ready_count']}/{payload['critical_check_count']} ready"
        )
        print(
            "- optional: "
            f"{payload['optional_ready_count']}/{payload['optional_check_count']} ready"
        )
        print("- fallback_layers:")
        for layer in payload["fallback_layers"]:
            print(f"  - {layer}")
        if payload["next_actions"]:
            print("- next_actions:")
            for action in payload["next_actions"]:
                print(f"  - {action}")

    if args.strict and not payload["local_operation_ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
