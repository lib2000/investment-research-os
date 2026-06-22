from __future__ import annotations

import argparse
import json
import os
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
    scrape_firecrawl_ir_item,
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
EXPECTED_FIRECRAWL_MCP_VERSION = "3.17.0"


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
    parser.add_argument(
        "--require-env-registry",
        action="store_true",
        help="Require FIRECRAWL_IR_SOURCES_JSON and fail instead of using sample input.",
    )
    parser.add_argument(
        "--require-rpc-ready",
        action="store_true",
        help="Require RPC settings without submitting data.",
    )
    parser.add_argument("--output-json", type=Path, help="Write the non-secret validation result JSON to this path.")
    parser.add_argument("--submit", action="store_true", help="Call MARKET_SIGNAL_GRAPH_RPC_URL when enabled.")
    parser.add_argument(
        "--hosted-scrape-dry-run",
        action="store_true",
        help="Call Firecrawl hosted POST /v2/scrape for the first IR URL and validate the normalized payload without RPC submit.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Load KEY=VALUE settings from a local secret env file before readiness checks. Values are not printed.",
    )
    parser.add_argument(
        "--env-override",
        action="store_true",
        help="Allow --env-file values to replace variables already set in the current process.",
    )
    parser.add_argument("--json", action="store_true", help="Print full non-secret validation JSON.")
    return parser


def _parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    if key.startswith("export "):
        key = key[len("export "):].strip()
    if not key:
        return None
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return key, value


def _load_env_file(path: Path, *, override: bool = False) -> dict[str, int | str]:
    if not path.exists():
        raise FileNotFoundError(f"env file not found: {path}")
    loaded = 0
    skipped = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_env_line(line)
        if parsed is None:
            continue
        key, value = parsed
        if not override and key in os.environ:
            skipped += 1
            continue
        os.environ[key] = value
        loaded += 1
    return {"path": str(path), "loaded_count": loaded, "skipped_existing_count": skipped}


def _load_items(args: argparse.Namespace, settings) -> tuple[list[dict], str]:
    if args.input_json:
        data = json.loads(args.input_json.read_text(encoding="utf-8"))
        return normalize_firecrawl_ir_inputs(data), "input_json"
    if args.use_env_registry or args.require_env_registry:
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


def _rpc_submit_readiness_errors(settings, *, purpose: str = "--submit") -> list[str]:
    errors: list[str] = []
    if not getattr(settings, "firecrawl_ir_enabled", False):
        errors.append(f"FIRECRAWL_IR_ENABLED must be true for {purpose}")
    if getattr(settings, "firecrawl_ir_dry_run", True):
        errors.append(f"FIRECRAWL_IR_DRY_RUN must be false for {purpose}")
    if not getattr(settings, "market_signal_graph_enabled", False):
        errors.append(f"MARKET_SIGNAL_GRAPH_ENABLED must be true for {purpose}")
    if not getattr(settings, "market_signal_graph_rpc_url", ""):
        errors.append(f"MARKET_SIGNAL_GRAPH_RPC_URL or SUPABASE_URL must be configured for {purpose}")
    if not getattr(settings, "market_signal_graph_service_role_key", ""):
        errors.append(f"MARKET_SIGNAL_GRAPH_SERVICE_ROLE_KEY or SUPABASE_SERVICE_ROLE_KEY must be configured for {purpose}")
    return errors


def _mcp_version_errors(settings) -> list[str]:
    configured = str(getattr(settings, "firecrawl_ir_mcp_version", "") or "").strip()
    if configured == EXPECTED_FIRECRAWL_MCP_VERSION:
        return []
    return [
        f"FIRECRAWL_IR_MCP_VERSION must be {EXPECTED_FIRECRAWL_MCP_VERSION} "
        f"(configured: {configured or 'missing'})"
    ]


def _write_output_json(result: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _payload_summary(payload_result: dict) -> dict:
    payload = payload_result.get("payload") or {}
    metadata = payload.get("metadata") or {}
    errors = payload_result.get("errors") or []
    return {
        "index": payload_result.get("index"),
        "ticker": metadata.get("ticker") or "",
        "company": metadata.get("company") or "",
        "url": payload.get("url") or "",
        "external_id_prefix": str(payload.get("external_id") or "")[:12],
        "status": "failed" if errors else "valid",
        "errors": errors,
    }


def _mark_duplicate_payload_errors(payload_results: list[dict]) -> list[str]:
    errors: list[str] = []
    seen_external_ids: dict[tuple[str, str], int] = {}
    seen_canonical_hashes: dict[tuple[str, str], int] = {}
    for result in payload_results:
        payload = result.get("payload") or {}
        item_errors = result.setdefault("errors", [])
        index = int(result.get("index") or 0)
        platform = str(payload.get("source_platform") or SOURCE_PLATFORM)
        external_id = str(payload.get("external_id") or "")
        canonical_hash = str(payload.get("canonical_hash") or "")
        external_key = (platform, external_id)
        canonical_key = (platform, canonical_hash)
        if external_id and external_key in seen_external_ids:
            message = f"item {index}: duplicate source_platform/external_id with item {seen_external_ids[external_key]}"
            item_errors.append(message)
            errors.append(message)
            continue
        if external_id:
            seen_external_ids[external_key] = index
        if canonical_hash and canonical_key in seen_canonical_hashes:
            message = f"item {index}: duplicate source_platform/canonical_hash with item {seen_canonical_hashes[canonical_key]}"
            item_errors.append(message)
            errors.append(message)
            continue
        if canonical_hash:
            seen_canonical_hashes[canonical_key] = index
    return errors


def _rpc_preflight_result(readiness_errors: list[str]) -> dict:
    if readiness_errors:
        return {
            "status": "skipped",
            "reason": "rpc_not_ready",
            "readiness_errors": readiness_errors,
        }
    return {"status": "ready"}


def _batch_counts_summary(batch_result: dict) -> str:
    status_counts = batch_result.get("status_counts") or {}
    return (
        f"success={int(batch_result.get('success_count') or status_counts.get('success') or 0)} "
        f"failed={int(batch_result.get('failed_count') or status_counts.get('failed') or 0)} "
        f"skipped={int(batch_result.get('skipped_count') or status_counts.get('skipped') or 0)} "
        f"dry_run={int(status_counts.get('dry_run') or 0)}"
    )


def _refresh_result_status(result: dict) -> str:
    if result.get("errors"):
        result["status"] = "failed"
        return result["status"]
    if result.get("batch"):
        result["status"] = str(result["batch"].get("status") or result.get("status") or "success")
        return result["status"]
    if result.get("rpc"):
        rpc_status = str(result["rpc"].get("status") or "")
        if rpc_status in {"success", "skipped", "failed"}:
            result["status"] = rpc_status
    return str(result.get("status") or "success")


def main() -> int:
    args = _build_parser().parse_args()
    env_file_result = None
    if args.env_file:
        env_file_result = _load_env_file(args.env_file, override=args.env_override)
        if hasattr(get_settings, "cache_clear"):
            get_settings.cache_clear()
    settings = get_settings()
    items, input_source = _load_items(args, settings)
    payload_results: list[dict] = []
    errors: list[str] = [] if items else ["no firecrawl IR items found"]
    if args.require_env_registry and input_source != "env_registry":
        errors.append("FIRECRAWL_IR_SOURCES_JSON must be used for --require-env-registry")
    for index, item in enumerate(items, start=1):
        try:
            payload = build_firecrawl_ir_signal_payload(item)
            item_errors = _validate_payload(payload)
            payload_results.append({"index": index, "payload": payload, "errors": item_errors})
            errors.extend(f"item {index}: {error}" for error in item_errors)
        except Exception as exc:
            payload_results.append({"index": index, "payload": None, "errors": [str(exc)]})
            errors.append(f"item {index}: {exc}")
    errors.extend(_mark_duplicate_payload_errors(payload_results))

    rpc_enabled = bool(settings.market_signal_graph_enabled and settings.firecrawl_ir_enabled)
    mcp_version_errors = _mcp_version_errors(settings)
    rpc_readiness_errors = _rpc_submit_readiness_errors(settings, purpose="RPC readiness")
    hosted_scrape_errors: list[str] = []
    if args.hosted_scrape_dry_run and not getattr(settings, "firecrawl_api_key", ""):
        hosted_scrape_errors.append("FIRECRAWL_API_KEY must be configured for --hosted-scrape-dry-run")
    submit_readiness_errors = _rpc_submit_readiness_errors(settings) if args.submit else []
    rpc_ready_errors = (
        _rpc_submit_readiness_errors(settings, purpose="--require-rpc-ready")
        if args.require_rpc_ready and not args.submit
        else []
    )
    errors.extend(mcp_version_errors)
    errors.extend(hosted_scrape_errors)
    errors.extend(submit_readiness_errors)
    errors.extend(rpc_ready_errors)
    result = {
        "status": "failed" if errors else "success",
        "design": DESIGN_NAME,
        "input_source": input_source,
        "item_count": len(items),
        "rpc_enabled": rpc_enabled,
        "firecrawl_ir_enabled": bool(settings.firecrawl_ir_enabled),
        "firecrawl_ir_dry_run": bool(settings.firecrawl_ir_dry_run),
        "firecrawl_ir_mcp_version": str(settings.firecrawl_ir_mcp_version or ""),
        "expected_firecrawl_ir_mcp_version": EXPECTED_FIRECRAWL_MCP_VERSION,
        "rpc_url_configured": bool(settings.market_signal_graph_rpc_url),
        "service_role_key_configured": bool(settings.market_signal_graph_service_role_key),
        "firecrawl_api_key_configured": bool(getattr(settings, "firecrawl_api_key", "")),
        "firecrawl_base_url": str(getattr(settings, "firecrawl_base_url", "") or ""),
        "rpc_submit_ready": not (mcp_version_errors or rpc_readiness_errors),
        "rpc_readiness_errors": rpc_readiness_errors,
        "require_env_registry": args.require_env_registry,
        "require_rpc_ready": args.require_rpc_ready,
        "env_file_loaded": bool(env_file_result),
        "env_file_loaded_count": int((env_file_result or {}).get("loaded_count") or 0),
        "env_file_skipped_existing_count": int((env_file_result or {}).get("skipped_existing_count") or 0),
        "dry_run": not args.submit,
        "payload": payload_results[0]["payload"] if len(payload_results) == 1 else None,
        "payloads": payload_results,
        "payload_summaries": [_payload_summary(payload_result) for payload_result in payload_results],
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

    if args.hosted_scrape_dry_run and not hosted_scrape_errors and not errors:
        result["hosted_scrape"] = scrape_firecrawl_ir_item(items[0], settings)
        if result["hosted_scrape"].get("status") != "success":
            errors.append(
                "hosted Firecrawl scrape failed: "
                f"{result['hosted_scrape'].get('reason') or result['hosted_scrape'].get('status')}"
            )
            result["errors"] = errors

    if args.require_rpc_ready and not args.submit:
        result["rpc"] = _rpc_preflight_result(rpc_ready_errors)

    _refresh_result_status(result)

    if args.output_json:
        result["output_json"] = str(args.output_json)
        _write_output_json(result, args.output_json)

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
        if result["payload_summaries"]:
            print("- payload_summaries:")
            for summary in result["payload_summaries"]:
                label = f"{summary['ticker']} {summary['company']}".strip()
                print(
                    f"  {summary['index']}. {summary['status']} | {label} | "
                    f"{summary['url']} | external_id={summary['external_id_prefix']}"
                )
        print(f"- firecrawl_ir_enabled: {bool(settings.firecrawl_ir_enabled)}")
        print(f"- firecrawl_ir_dry_run: {bool(settings.firecrawl_ir_dry_run)}")
        print(f"- firecrawl_ir_mcp_version: {settings.firecrawl_ir_mcp_version}")
        print(f"- expected_firecrawl_ir_mcp_version: {EXPECTED_FIRECRAWL_MCP_VERSION}")
        print(f"- firecrawl_api_key_configured: {result['firecrawl_api_key_configured']}")
        print(f"- firecrawl_base_url: {result['firecrawl_base_url']}")
        print(f"- rpc_enabled: {rpc_enabled}")
        print(f"- rpc_url_configured: {bool(settings.market_signal_graph_rpc_url)}")
        print(f"- service_role_key_configured: {bool(settings.market_signal_graph_service_role_key)}")
        print(f"- rpc_submit_ready: {not rpc_readiness_errors}")
        if rpc_readiness_errors:
            print(f"- rpc_readiness_errors: {len(rpc_readiness_errors)}")
            for error in rpc_readiness_errors:
                print(f"  - {error}")
        print(f"- require_env_registry: {args.require_env_registry}")
        print(f"- require_rpc_ready: {args.require_rpc_ready}")
        print(
            f"- env_file_loaded: {result['env_file_loaded']} "
            f"(loaded={result['env_file_loaded_count']}, skipped_existing={result['env_file_skipped_existing_count']})"
        )
        print(f"- dry_run: {not args.submit}")
        if result.get("batch"):
            print(f"- batch_status: {result['batch'].get('status')}")
            print(f"- batch_counts: {_batch_counts_summary(result['batch'])}")
        if result.get("rpc"):
            print(f"- rpc_status: {result['rpc'].get('status')}")
            if result["rpc"].get("reason"):
                print(f"- rpc_reason: {result['rpc'].get('reason')}")
        if result.get("hosted_scrape"):
            print(f"- hosted_scrape_status: {result['hosted_scrape'].get('status')}")
            if result["hosted_scrape"].get("reason"):
                print(f"- hosted_scrape_reason: {result['hosted_scrape'].get('reason')}")
            if result["hosted_scrape"].get("status") == "success":
                print(
                    "- hosted_scrape_payload: "
                    f"{result['hosted_scrape'].get('ticker')} "
                    f"{result['hosted_scrape'].get('company')} | "
                    f"{result['hosted_scrape'].get('url')} | "
                    f"external_id={result['hosted_scrape'].get('external_id_prefix')}"
                )
        for error in errors:
            print(f"ERROR: {error}")
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
