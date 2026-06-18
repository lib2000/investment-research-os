from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.firecrawl_ir_collector import (  # noqa: E402
    DESIGN_NAME,
    SOURCE_PLATFORM,
    build_firecrawl_ir_collection_result,
    build_firecrawl_ir_signal_payload,
)
from research_os.settings import get_settings  # noqa: E402


APPLE_IR_SAMPLE = {
    "company": "Apple",
    "ticker": "AAPL",
    "raw_url": "https://investor.apple.com/",
    "resolved_url": "https://investor.apple.com/",
    "page_title": "Apple Investor Relations",
    "markdown": "Apple Investor Relations provides earnings releases, SEC filings, governance materials, and shareholder information.",
    "language": "en",
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate Firecrawl IR Collector v1 payload/RPC readiness.")
    parser.add_argument("--company", default=APPLE_IR_SAMPLE["company"])
    parser.add_argument("--ticker", default=APPLE_IR_SAMPLE["ticker"])
    parser.add_argument("--url", default=APPLE_IR_SAMPLE["raw_url"])
    parser.add_argument("--resolved-url", default=APPLE_IR_SAMPLE["resolved_url"])
    parser.add_argument("--title", default=APPLE_IR_SAMPLE["page_title"])
    parser.add_argument("--text", default=APPLE_IR_SAMPLE["markdown"])
    parser.add_argument("--submit", action="store_true", help="Call MARKET_SIGNAL_GRAPH_RPC_URL when enabled.")
    parser.add_argument("--json", action="store_true", help="Print full non-secret validation JSON.")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    item = {
        "company": args.company,
        "ticker": args.ticker,
        "raw_url": args.url,
        "resolved_url": args.resolved_url,
        "page_title": args.title,
        "markdown": args.text,
        "language": "en",
    }
    payload = build_firecrawl_ir_signal_payload(item)
    errors: list[str] = []
    if payload.get("source_platform") != SOURCE_PLATFORM:
        errors.append("source_platform must be firecrawl_ir")
    if payload.get("source_kind") != "ir":
        errors.append("source_kind must be ir")
    if payload.get("channel") != "web":
        errors.append("channel must be web")
    if len(str(payload.get("external_id") or "")) != 64:
        errors.append("external_id must be sha256(url)")
    if len(str(payload.get("canonical_hash") or "")) != 64:
        errors.append("canonical_hash must be sha256(source_platform + url + normalized_title)")
    if not payload.get("needs_enrichment"):
        errors.append("needs_enrichment must be true")
    if payload.get("analysis_status") != "pending":
        errors.append("analysis_status must be pending")
    metadata = payload.get("metadata") or {}
    if metadata.get("collector") != "firecrawl" or metadata.get("target_type") != "company_ir":
        errors.append("metadata collector/target_type contract mismatch")

    settings = get_settings()
    rpc_enabled = bool(settings.market_signal_graph_enabled and settings.firecrawl_ir_enabled)
    result = {
        "status": "failed" if errors else "success",
        "design": DESIGN_NAME,
        "rpc_enabled": rpc_enabled,
        "dry_run": not args.submit,
        "payload": payload,
        "errors": errors,
    }
    if args.submit:
        if not rpc_enabled:
            result["rpc"] = {
                "status": "skipped",
                "reason": "FIRECRAWL_IR_ENABLED and MARKET_SIGNAL_GRAPH_ENABLED must both be true",
            }
        else:
            result["rpc"] = build_firecrawl_ir_collection_result(item, settings, dry_run=False).get("rpc")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"[{result['status']}] {DESIGN_NAME}")
        print(f"- source_platform: {payload['source_platform']}")
        print(f"- external_id: {payload['external_id']}")
        print(f"- canonical_hash: {payload['canonical_hash']}")
        print(f"- rpc_enabled: {rpc_enabled}")
        print(f"- dry_run: {not args.submit}")
        if result.get("rpc"):
            print(f"- rpc_status: {result['rpc'].get('status')}")
            if result["rpc"].get("reason"):
                print(f"- rpc_reason: {result['rpc'].get('reason')}")
        for error in errors:
            print(f"ERROR: {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
