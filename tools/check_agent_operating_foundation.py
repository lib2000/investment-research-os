"""Check the local operating foundation for high-performance agents."""

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
    parser = argparse.ArgumentParser(description="에이전트 운영 기반 readiness를 점검합니다.")
    parser.add_argument("--json", action="store_true", help="점검 결과를 JSON으로 출력합니다.")
    parser.add_argument("--strict", action="store_true", help="기반 점수가 95점 미만이거나 핵심 항목이 빠지면 실패합니다.")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    backend_dir = root / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    from research_os.agent_operating_foundation import build_agent_operating_foundation_status
    from research_os.settings import Settings

    payload = build_agent_operating_foundation_status(Settings(research_vault_dir=str(root / "research_vault")))
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"[{payload['status']}] agent_operating_foundation_status")
        print(f"- score: {payload['score']} / {payload['min_score']}")
        print(f"- critical: {payload['critical_ready_count']}/{payload['critical_check_count']} ready")
        print(f"- optional: {payload['optional_ready_count']}/{payload['optional_check_count']} ready")
        for item in payload["checks"]:
            status = "정상" if item["ready"] else "확인 필요"
            print(f"- {item['label']}: {status} {item['score']}점 | {item['evidence']}")
        if payload["next_actions"]:
            print("다음 조치:")
            for action in payload["next_actions"]:
                print(f"- {action}")

    if args.strict and payload["status"] != "ok":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
