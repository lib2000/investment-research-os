"""Offline readiness check for the unified insider-trading pipeline."""

from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.insider_trading import (  # noqa: E402
    PriceBar,
    build_insider_report,
    classify_source_url,
    parse_dart_elestock_payload,
    parse_insider_summary_text,
    parse_sec_form4_xml,
)


SEC_SAMPLE = """<ownershipDocument>
<issuer><issuerName>Readiness Corp</issuerName><issuerTradingSymbol>READY</issuerTradingSymbol></issuer>
<reportingOwner><reportingOwnerId><rptOwnerName>Test Owner</rptOwnerName></reportingOwnerId>
<reportingOwnerRelationship><isOfficer>1</isOfficer><officerTitle>CFO</officerTitle></reportingOwnerRelationship></reportingOwner>
<nonDerivativeTable><nonDerivativeTransaction>
<securityTitle><value>Common Stock</value></securityTitle><transactionDate><value>2026-09-01</value></transactionDate>
<transactionCoding><transactionCode>P</transactionCode></transactionCoding><transactionAmounts>
<transactionShares><value>1000</value></transactionShares><transactionPricePerShare><value>10</value></transactionPricePerShare>
<transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode></transactionAmounts>
<postTransactionAmounts><sharesOwnedFollowingTransaction><value>11000</value></sharesOwnedFollowingTransaction></postTransactionAmounts>
</nonDerivativeTransaction></nonDerivativeTable></ownershipDocument>"""


def run_check() -> dict:
    checks: dict[str, bool] = {}
    errors: list[str] = []
    try:
        sec_event = parse_sec_form4_xml(
            SEC_SAMPLE,
            source_url="https://www.sec.gov/Archives/edgar/data/1/form4.xml",
            filing_date=date(2026, 9, 2),
        )[0]
        checks["sec_form4_parser"] = sec_event.tx_code == "P" and sec_event.transaction_value == 10000
    except Exception as exc:
        checks["sec_form4_parser"] = False
        errors.append(f"SEC parser: {exc}")
        sec_event = None

    try:
        dart_event = parse_dart_elestock_payload(
            {
                "status": "000",
                "list": [{
                    "rcept_no": "20260901000001", "rcept_dt": "20260901",
                    "corp_name": "준비도", "repror": "테스트", "isu_exctv_ofcps": "대표이사",
                    "sp_stock_lmp_cnt": "11000", "sp_stock_lmp_irds_cnt": "1000",
                }],
            },
            ticker="005930",
            corp={"corp_code": "00126380", "corp_name": "준비도"},
        )[0]
        checks["opendart_parser"] = dart_event.tx_code == "ACQUIRE" and dart_event.avg_price is None
    except Exception as exc:
        checks["opendart_parser"] = False
        errors.append(f"OpenDART parser: {exc}")

    summary_event = parse_insider_summary_text(
        "$TSLA 내부자 매수 공시: CFO, 2026-09-11, 5,000주, $210, 거래 후 보유 120,000주"
    )
    checks["summary_parser"] = bool(summary_event and summary_event.ticker == "TSLA" and summary_event.post_shares == 120000)

    checks["source_allowlist"] = (
        classify_source_url("https://www.sec.gov/test.xml")["source_tier"] == "primary"
        and classify_source_url("https://www.secform4.com/insider-trading/X.htm")["source_tier"] == "secondary"
    )
    unsafe_rejected = False
    try:
        classify_source_url("https://127.0.0.1/private")
    except ValueError:
        unsafe_rejected = True
    checks["private_url_rejected"] = unsafe_rejected

    if sec_event:
        bars = [
            PriceBar(date=date(2026, 5, 1) + timedelta(days=index), close=10 + index * 0.05)
            for index in range(140)
        ]
        report = build_insider_report(
            event=sec_event,
            events=[sec_event],
            price_rows=bars,
            source_status={"provider": "SEC EDGAR", "coverage_complete": True},
            checkpoints={
                "valuation_band": "확인 필요",
                "fundamental_catalysts": ["확인 필요"],
                "linked_research": [],
                "risk_management": ["사람 검토"],
            },
        )
        checks["six_axis_report"] = len(report.get("axes") or {}) == 6
        checks["no_order_contract"] = "주문" in report.get("disclaimer", "")
    else:
        checks["six_axis_report"] = False
        checks["no_order_contract"] = False

    source_contracts = {
        "api_routes": (
            PROJECT_ROOT / "backend" / "research_os_main.py",
            ["/api/v1/insider-trading/status", "/api/v1/insider-trading/analyze", "/api/v1/insider-trading/refresh"],
        ),
        "console": (
            PROJECT_ROOT / "mobile_app" / "research_console" / "index.html",
            ['data-tab="insider"', 'id="insiderForm"', 'id="insiderResult"'],
        ),
        "daily_automation": (
            PROJECT_ROOT / "tools" / "run_daily_research_operations.ps1",
            ["SkipInsiderTradingResearch", "run_insider_trading_research.py", "never sends a message"],
        ),
    }
    for name, (path, terms) in source_contracts.items():
        content = path.read_text(encoding="utf-8")
        checks[name] = all(term in content for term in terms)

    failed = [name for name, passed in checks.items() if not passed]
    errors.extend(f"failed check: {name}" for name in failed)
    return {
        "status": "ok" if not failed else "error",
        "module": "insider_trading_readiness",
        "checks": checks,
        "passed_count": sum(checks.values()),
        "check_count": len(checks),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="내부자거래 6축 파이프라인 오프라인 준비도를 점검합니다.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    result = run_check()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"내부자거래 파이프라인: {result['status']} ({result['passed_count']}/{result['check_count']})")
        for error in result["errors"]:
            print(f"- {error}")
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
