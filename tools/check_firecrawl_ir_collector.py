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
    build_firecrawl_ir_batch_result,
    build_firecrawl_ir_collection_result,
    build_firecrawl_ir_signal_payload,
    normalize_firecrawl_ir_inputs,
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
    parser.add_argument("--input-json", type=Path, help="Optional Firecrawl IR item/list JSON file.")
    parser.add_argument(
        "--use-env-registry",
        action="store_true",
        help="Read FIRECRAWL_IR_SOURCES_JSON instead of the built-in Apple sample.",
    )
    parser.add_argument("--submit", action="store_true", help="Call MARKET_SIGNAL_GRAPH_RPC_URL when enabled.")
    parser.add_argument("--json", action="store_true", help="Print full non-secret validation JSON.")
    return parser


def _load_items(args: argparse.Namespace, settings) -> tuple[list[dict], str]:
    if args.input_json:
        data = json.loads(args.input_json.read_text(encoding="utf-8"))
        return normalize_firecrawl_ir_inputs(data), "input_json"
    if args.use_env_registry:
        data = json.loads(settings.firecrawl_ir_sources_json or "[]")
        return normalize_firecrawl_ir_inputs(data), "env_registry"
    return ([{
        "company": args.company,
        "ticker": args.ticker,
        "raw_url": args.url,
        "resolved_url": args.resolved_url,
        "page_title": args.title,
        "markdown": args.text,
        "language": "en",
    }], "sample")


def _validate_payload(payload: dict) -> list[str]:
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
    return errors


def _rpc_submit_readiness_errors(settings) -> list[str]:
    errors: list[str] = []
    if not getattr(settings, "firecrawl_ir_enabled", False):
        errors.append("FIRECRAWL_IR_ENABLED must be true for --submit")
    if not getattr(settings, "market_signal_graph_enabled", False):
        errors.append("MARKET_SIGNAL_GRAPH_ENABLED must be true for --submit")
    if not getattr(settings, "market_signal_graph_rpc_url", ""):
        errors.append("MARKET_SIGNAL_GRAPH_RPC_URL or SUPABASE_URL must be configured for --submit")
    if not getattr(settings, "market_signal_graph_service_role_key", ""):
        errors.append("MARKET_SIGNAL_GRAPH_SERVICE_ROLE_KEY or SUPABASE_SERVICE_ROLE_KEY must be configured for --submit")
    return errors


def main() -> int:
    args = _build_parser().parse_args()
    settings = get_settings()
    items, input_source = _load_items(args, settings)
    payload_results: list[dict] = []
    errors: list[str] = [] if items else ["no firecrawl IR items found"]
    for index, item in enumerate(items, start=1):
        try:
            payload = build_firecrawl_ir_signal_payload(item)
            item_errors = _validate_payload(payload)
            payload_results.append({"index": index, "payload": payload, "errors": item_errors})
            errors.extend(f"item {index}: {error}" for error in item_errors)
        except Exception as exc:
            payload_results.append({"index": index, "payload": None, "errors": [str(exc)]})
            errors.append(f"item {index}: {exc}")

    rpc_enabled = bool(settings.market_signal_graph_enabled and settings.firecrawl_ir_enabled)
    submit_readiness_errors = _rpc_submit_readiness_errors(settings) if args.submit else []
    errors.extend(submit_readiness_errors)
    result = {
        "status": "failed" if errors else "success",
        "design": DESIGN_NAME,
        "input_source": input_source,
        "item_count": len(items),
        "rpc_enabled": rpc_enabled,
        "rpc_url_configured": bool(settings.market_signal_graph_rpc_url),
        "service_role_key_configured": bool(settings.market_signal_graph_service_role_key),
        "dry_run": not args.submit,
        "payload": payload_results[0]["payload"] if len(payload_results) == 1 else None,
        "payloads": payload_results,
        "errors": errors,
    }
    if args.submit:
        if submit_readiness_errors:
            result["rpc"] = {
                "status": "skipped",
                "reason": "rpc_not_ready",
                "readiness_errors": submit_readiness_errors,
            }
        elif errors:
            result["rpc"] = {"status": "skipped", "reason": "payload_validation_failed"}
        else:
            if len(items) == 1:
                result["rpc"] = build_firecrawl_ir_collection_result(items[0], settings, dry_run=False).get("rpc")
            else:
                result["batch"] = build_firecrawl_ir_batch_result(items, settings, dry_run=False)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"[{result['status']}] {DESIGN_NAME}")
        print(f"- input_source: {input_source}")
        print(f"- item_count: {len(items)}")
        if len(payload_results) == 1 and payload_results[0]["payload"]:
            payload = payload_results[0]["payload"]
            print(f"- source_platform: {payload['source_platform']}")
            print(f"- external_id: {payload['external_id']}")
            print(f"- canonical_hash: {payload['canonical_hash']}")
        print(f"- rpc_enabled: {rpc_enabled}")
        print(f"- rpc_url_configured: {bool(settings.market_signal_graph_rpc_url)}")
        print(f"- service_role_key_configured: {bool(settings.market_signal_graph_service_role_key)}")
        print(f"- dry_run: {not args.submit}")
        if result.get("batch"):
            print(f"- batch_status: {result['batch'].get('status')}")
            print(f"- batch_counts: {result['batch'].get('status_counts')}")
        if result.get("rpc"):
            print(f"- rpc_status: {result['rpc'].get('status')}")
            if result["rpc"].get("reason"):
                print(f"- rpc_reason: {result['rpc'].get('reason')}")
        for error in errors:
            print(f"ERROR: {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
