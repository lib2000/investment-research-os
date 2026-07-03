from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.firecrawl_monitor_collector import (  # noqa: E402
    DESIGN_NAME,
    build_firecrawl_monitor_dry_run_result,
    build_firecrawl_monitor_readiness_status,
    normalize_firecrawl_monitor_sources,
)
from research_os.settings import get_settings  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate Firecrawl Monitor v1 readiness without creating monitors.")
    parser.add_argument("--input-json", type=Path, help="Optional Firecrawl monitor source JSON.")
    parser.add_argument("--use-env-registry", action="store_true", help="Read FIRECRAWL_MONITOR_SOURCES_JSON.")
    parser.add_argument("--require-env-registry", action="store_true", help="Require FIRECRAWL_MONITOR_SOURCES_JSON.")
    parser.add_argument("--require-create-ready", action="store_true", help="Require settings that permit real monitor creation.")
    parser.add_argument("--env-file", type=Path, help="Load a local secret env file before checks. Values are not printed.")
    parser.add_argument("--env-override", action="store_true", help="Allow --env-file values to replace current env values.")
    parser.add_argument("--output-json", type=Path, help="Write non-secret validation JSON.")
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
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return (key, value) if key else None


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


def _source_registry_from_args(args: argparse.Namespace, settings) -> tuple[list[dict], str, list[str]]:
    errors: list[str] = []
    if args.input_json:
        try:
            return normalize_firecrawl_monitor_sources(json.loads(args.input_json.read_text(encoding="utf-8"))), "input_json", errors
        except Exception as exc:
            return [], "input_json", [f"input json parse failed: {exc}"]
    if args.use_env_registry or args.require_env_registry:
        raw = getattr(settings, "firecrawl_monitor_sources_json", "") or "[]"
        try:
            return normalize_firecrawl_monitor_sources(json.loads(raw)), "env_registry", errors
        except Exception as exc:
            return [], "env_registry", [f"FIRECRAWL_MONITOR_SOURCES_JSON parse failed: {exc}"]
    return [], "sample", errors


def _write_output_json(result: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _payload_hash_prefix(item: dict) -> str:
    return sha256(json.dumps(item, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:12]


def _looks_like_placeholder(value: str) -> bool:
    lowered = str(value or "").strip().lower()
    return not lowered or lowered.startswith("replace-with-") or lowered in {"changeme", "todo", "placeholder"}


def _dry_run_from_items(items: list[dict], input_source: str, settings) -> dict:
    readiness = build_firecrawl_monitor_readiness_status(settings)
    return {
        "status": "dry_run",
        "module": "firecrawl_monitor_dry_run",
        "design": DESIGN_NAME,
        "source_registry": {"item_count": len(items), "input_source": input_source, "parse_error": None},
        "create_ready": bool(readiness.get("create_ready")),
        "create_readiness_errors": readiness.get("create_readiness_errors") or [],
        "monitors": [
            {
                "name": item.get("name"),
                "target_count": len(item.get("targets") or []),
                "target_types": [target.get("type") for target in item.get("targets") or []],
                "schedule": item.get("schedule"),
                "goal": item.get("goal"),
                "webhook_configured": bool(item.get("webhook")),
                "payload_hash_prefix": _payload_hash_prefix(item),
                "payload": item,
            }
            for item in items
        ],
    }


def main() -> int:
    args = _build_parser().parse_args()
    env_file_result = None
    if args.env_file:
        env_file_result = _load_env_file(args.env_file, override=args.env_override)
        if hasattr(get_settings, "cache_clear"):
            get_settings.cache_clear()
    settings = get_settings()
    registry_items, input_source, registry_errors = _source_registry_from_args(args, settings)
    readiness = build_firecrawl_monitor_readiness_status(settings)
    dry_run = (
        _dry_run_from_items(registry_items, input_source, settings)
        if input_source != "sample" and not registry_errors
        else build_firecrawl_monitor_dry_run_result(settings)
    )
    errors = list(registry_errors)
    if args.require_env_registry and input_source != "env_registry":
        errors.append("FIRECRAWL_MONITOR_SOURCES_JSON must be used for --require-env-registry")
    if args.require_env_registry and not registry_items:
        errors.append("FIRECRAWL_MONITOR_SOURCES_JSON did not produce monitor sources")
    if args.require_create_ready and not readiness.get("create_ready"):
        errors.extend(readiness.get("create_readiness_errors") or ["Firecrawl monitor create is not ready"])
    result = {
        "status": "failed" if errors else "success",
        "design": DESIGN_NAME,
        "input_source": input_source,
        "item_count": len(registry_items) if input_source != "sample" else int((dry_run.get("source_registry") or {}).get("item_count") or 0),
        "firecrawl_monitor_enabled": bool(getattr(settings, "firecrawl_monitor_enabled", False)),
        "firecrawl_monitor_dry_run": bool(getattr(settings, "firecrawl_monitor_dry_run", True)),
        "firecrawl_api_key_configured": bool(str(getattr(settings, "firecrawl_api_key", "") or "").strip())
        and not _looks_like_placeholder(str(getattr(settings, "firecrawl_api_key", "") or "")),
        "firecrawl_base_url": str(getattr(settings, "firecrawl_base_url", "") or ""),
        "create_ready": bool(readiness.get("create_ready")),
        "create_readiness_errors": readiness.get("create_readiness_errors") or [],
        "readiness": readiness,
        "dry_run": dry_run,
        "require_env_registry": args.require_env_registry,
        "require_create_ready": args.require_create_ready,
        "env_file_loaded": bool(env_file_result),
        "env_file_loaded_count": int((env_file_result or {}).get("loaded_count") or 0),
        "env_file_skipped_existing_count": int((env_file_result or {}).get("skipped_existing_count") or 0),
        "errors": errors,
    }
    if args.output_json:
        result["output_json"] = str(args.output_json)
        _write_output_json(result, args.output_json)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        preflight = readiness.get("operational_preflight") if isinstance(readiness, dict) else {}
        print(f"[{result['status']}] {DESIGN_NAME}")
        print(f"- input_source: {input_source}")
        print(f"- item_count: {result['item_count']}")
        print(f"- firecrawl_monitor_enabled: {result['firecrawl_monitor_enabled']}")
        print(f"- firecrawl_monitor_dry_run: {result['firecrawl_monitor_dry_run']}")
        print(f"- firecrawl_api_key_configured: {result['firecrawl_api_key_configured']}")
        print(f"- firecrawl_base_url: {result['firecrawl_base_url']}")
        print(f"- create_ready: {result['create_ready']}")
        if isinstance(preflight, dict):
            print(
                "- operational_preflight: "
                f"ready={bool(preflight.get('ready'))} "
                f"registry={bool(preflight.get('registry_configured'))} "
                f"webhook_secret={bool(preflight.get('webhook_secret_configured'))}"
            )
            for error in preflight.get("errors") or []:
                print(f"  - {error}")
        for error in result["create_readiness_errors"]:
            print(f"  - {error}")
        print(
            f"- env_file_loaded: {result['env_file_loaded']} "
            f"(loaded={result['env_file_loaded_count']}, skipped_existing={result['env_file_skipped_existing_count']})"
        )
        for monitor in dry_run.get("monitors", []):
            print(
                f"- monitor: {monitor.get('name')} | targets={monitor.get('target_count')} "
                f"| types={','.join(monitor.get('target_types') or [])} | webhook={monitor.get('webhook_configured')}"
            )
        for error in errors:
            print(f"ERROR: {error}")
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
