"""Backend-free policy and integration check for the DART annual-report lab."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.dart_annual_report_lab import build_dart_annual_report_lab_status
from research_os.settings import Settings


def build_check_payload(*, require_configured: bool = False) -> dict:
    settings = Settings.from_env()
    lab = build_dart_annual_report_lab_status(
        settings,
        dart_cache={"entries": {}},
        target_universe={"target_tickers": [], "target_count": 0},
    )
    main_source = (PROJECT_ROOT / "backend" / "research_os_main.py").read_text(encoding="utf-8")
    html = (PROJECT_ROOT / "mobile_app" / "research_console" / "index.html").read_text(
        encoding="utf-8"
    )
    api = (PROJECT_ROOT / "mobile_app" / "research_console" / "api.js").read_text(
        encoding="utf-8"
    )
    console = (PROJECT_ROOT / "mobile_app" / "research_console" / "console.js").read_text(
        encoding="utf-8"
    )
    checks = [
        {
            "key": "backend_status_route",
            "passed": '"/api/v1/dart/annual-report-lab/status"' in main_source,
            "detail": "FastAPI 상태 엔드포인트",
        },
        {
            "key": "backend_refresh_route",
            "passed": '"/api/v1/dart/annual-report-lab/refresh"' in main_source,
            "detail": "FastAPI A001 순환 점검 엔드포인트",
        },
        {
            "key": "backend_governance_refresh_route",
            "passed": '"/api/v1/dart/annual-report-lab/governance/refresh"' in main_source,
            "detail": "FastAPI 지배구조 정형 스냅샷 엔드포인트",
        },
        {
            "key": "console_panel",
            "passed": all(
                marker in html
                for marker in (
                    'data-tab="dartAnnualLab"',
                    'id="dartAnnualLabContent"',
                    "DART 사업보고서 분석 랩",
                    "투자 권유나 매매 신호가 아닙니다",
                )
            ),
            "detail": "콘솔 진입점·본문 고지",
        },
        {
            "key": "console_api",
            "passed": all(
                marker in api
                for marker in (
                    "fetchDartAnnualReportLabStatus",
                    "refreshDartAnnualReportLab",
                    "refreshDartAnnualReportGovernance",
                )
            ),
            "detail": "콘솔 API 클라이언트",
        },
        {
            "key": "console_renderer",
            "passed": all(
                marker in console
                for marker in (
                    "renderDartAnnualReportLab",
                    "NO RUN",
                    "실패 10%↑",
                    "종합 점수와 랭킹은 산출하지 않습니다",
                    "dart-governance-snapshot",
                )
            ),
            "detail": "30일 원장·실패·지배구조 스냅샷·스크리닝 정책 렌더링",
        },
        *lab.get("policy_checks", []),
    ]
    if require_configured:
        checks.append(
            {
                "key": "api_key_configured",
                "passed": bool(lab.get("environment", {}).get("api_key_configured")),
                "detail": "DART_API_KEY 런타임 설정",
            }
        )
    failed = [item for item in checks if not item.get("passed")]
    return {
        "status": "error" if failed else "ok",
        "module": "dart_annual_report_lab_check",
        "configured": bool(lab.get("environment", {}).get("api_key_configured")),
        "external_requests": 0,
        "check_count": len(checks),
        "passed_count": len(checks) - len(failed),
        "failed_count": len(failed),
        "failed_keys": [item.get("key") for item in failed],
        "checks": checks,
        "quota": lab.get("quota"),
        "safety": lab.get("safety"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="DART 사업보고서 분석 랩 정책/연결을 점검합니다.")
    parser.add_argument("--json", action="store_true", help="JSON 결과를 출력합니다.")
    parser.add_argument(
        "--require-configured",
        action="store_true",
        help="DART_API_KEY 미설정도 실패로 처리합니다.",
    )
    args = parser.parse_args()
    payload = build_check_payload(require_configured=args.require_configured)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(
            f"DART 사업보고서 랩: {payload['passed_count']}/{payload['check_count']} PASS "
            f"· 외부 호출 {payload['external_requests']}건"
        )
        for item in payload["checks"]:
            print(f"{'PASS' if item.get('passed') else 'FAIL'} {item.get('key')}: {item.get('detail')}")
        if not payload["configured"]:
            print("INFO DART_API_KEY가 없으면 화면은 설정 필요 상태로 표시됩니다.")
    return 0 if payload["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
