from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.firecrawl_monitor_collector import (  # noqa: E402
    DESIGN_NAME as COLLECTOR_DESIGN,
    build_firecrawl_monitor_dry_run_result,
    build_firecrawl_monitor_readiness_status,
)
from research_os.firecrawl_monitor_events import (  # noqa: E402
    DESIGN_NAME as EVENT_DESIGN,
    summarize_firecrawl_monitor_event_store,
)
from research_os.settings import get_settings  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Firecrawl Monitor operational preflight: registry, secret, and webhook ingest flow."
    )
    parser.add_argument("--env-file", type=Path, help="Load local secret env file before checks.")
    parser.add_argument("--env-override", action="store_true", help="Allow env-file values to override process env.")
    parser.add_argument("--require-env-registry", action="store_true", help="Require FIRECRAWL_MONITOR_SOURCES_JSON.")
    parser.add_argument("--require-webhook-secret", action="store_true", help="Require FIRECRAWL_MONITOR_WEBHOOK_SECRET.")
    parser.add_argument("--require-create-ready", action="store_true", help="Require live monitor create readiness.")
    parser.add_argument("--use-live-vault", action="store_true", help="Write webhook test event to configured research vault.")
    parser.add_argument("--output-json", type=Path, help="Write sanitized result JSON.")
    parser.add_argument("--json", action="store_true", help="Print sanitized result JSON.")
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


def _load_env_file(path: Path, *, override: bool) -> dict[str, Any]:
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


def _masked_settings(settings: Any) -> dict[str, Any]:
    return {
        "firecrawl_monitor_enabled": bool(getattr(settings, "firecrawl_monitor_enabled", False)),
        "firecrawl_monitor_dry_run": bool(getattr(settings, "firecrawl_monitor_dry_run", True)),
        "firecrawl_api_key_configured": bool(getattr(settings, "firecrawl_api_key", "")),
        "firecrawl_monitor_sources_json_configured": bool(getattr(settings, "firecrawl_monitor_sources_json", "")),
        "firecrawl_monitor_webhook_secret_configured": bool(
            getattr(settings, "firecrawl_monitor_webhook_secret", "")
        ),
        "firecrawl_base_url": str(getattr(settings, "firecrawl_base_url", "") or ""),
    }


def _settings_with_isolated_vault(settings: Any, temp_dir: str | None) -> Any:
    if not temp_dir:
        return settings
    vault_dir = str(Path(temp_dir) / "research_vault")
    if hasattr(settings, "model_copy"):
        return settings.model_copy(update={"research_vault_dir": vault_dir})
    if hasattr(settings, "copy"):
        return settings.copy(update={"research_vault_dir": vault_dir})
    setattr(settings, "research_vault_dir", vault_dir)
    return settings


def _sample_monitor_payload() -> dict[str, Any]:
    return {
        "type": "monitor.page",
        "data": [
            {
                "monitorId": "preflight-monitor",
                "checkId": "preflight-check",
                "url": "https://www.sec.gov/newsroom/press-releases",
                "status": "changed",
                "metadata": {"title": "SEC Press Releases preflight"},
                "judgment": {"meaningful": True, "reason": "Webhook preflight event"},
                "diff": {"text": "- old\n+ new preflight event"},
            }
        ],
    }


def _run_webhook_flow(settings: Any) -> dict[str, Any]:
    import research_os_main as main
    from fastapi.testclient import TestClient

    main.app.dependency_overrides[main.get_settings] = lambda: settings
    client = TestClient(main.app)
    payload = _sample_monitor_payload()
    try:
        reject_response = client.post(
            "/api/v1/public-ir-sec/firecrawl-monitor/webhook",
            json=payload,
            headers={"X-Firecrawl-Webhook-Secret": "wrong-preflight-secret"},
        )
        accept_response = client.post(
            "/api/v1/public-ir-sec/firecrawl-monitor/webhook",
            json=payload,
            headers={"X-Firecrawl-Webhook-Secret": str(getattr(settings, "firecrawl_monitor_webhook_secret", ""))},
        )
    finally:
        main.app.dependency_overrides.pop(main.get_settings, None)
    store_summary = summarize_firecrawl_monitor_event_store(settings)
    return {
        "rejected_status_code": reject_response.status_code,
        "accepted_status_code": accept_response.status_code,
        "accepted_saved_count": int((accept_response.json() if accept_response.content else {}).get("saved_count") or 0)
        if accept_response.status_code == 200
        else 0,
        "event_store_count": int(store_summary.get("event_count") or 0),
        "event_store_meaningful_count": int(store_summary.get("meaningful_count") or 0),
    }


def _write_output_json(result: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    args = _build_parser().parse_args()
    env_result = None
    if args.env_file:
        env_result = _load_env_file(args.env_file, override=args.env_override)
        if hasattr(get_settings, "cache_clear"):
            get_settings.cache_clear()
    base_settings = get_settings()
    temp_ctx = None if args.use_live_vault else tempfile.TemporaryDirectory()
    try:
        settings = _settings_with_isolated_vault(base_settings, temp_ctx.name if temp_ctx else None)
        readiness = build_firecrawl_monitor_readiness_status(settings)
        dry_run = build_firecrawl_monitor_dry_run_result(settings)
        masked = _masked_settings(settings)
        errors: list[str] = []
        registry_count = int((dry_run.get("source_registry") or {}).get("item_count") or 0)
        if args.require_env_registry and not masked["firecrawl_monitor_sources_json_configured"]:
            errors.append("FIRECRAWL_MONITOR_SOURCES_JSON must be configured")
        if args.require_env_registry and registry_count <= 0:
            errors.append("FIRECRAWL_MONITOR_SOURCES_JSON did not produce monitor sources")
        if args.require_webhook_secret and not masked["firecrawl_monitor_webhook_secret_configured"]:
            errors.append("FIRECRAWL_MONITOR_WEBHOOK_SECRET must be configured")
        if args.require_create_ready and not readiness.get("create_ready"):
            errors.extend(readiness.get("create_readiness_errors") or ["Firecrawl monitor create is not ready"])
        webhook_flow = None
        if masked["firecrawl_monitor_webhook_secret_configured"]:
            webhook_flow = _run_webhook_flow(settings)
            if webhook_flow["rejected_status_code"] != 401:
                errors.append("Webhook mismatch check did not reject with 401")
            if webhook_flow["accepted_status_code"] != 200:
                errors.append("Webhook valid secret check did not return 200")
            if webhook_flow["accepted_saved_count"] < 1:
                errors.append("Webhook valid secret check did not save an event")
        result = {
            "status": "failed" if errors else "success",
            "module": "firecrawl_monitor_operational_preflight",
            "collector_design": COLLECTOR_DESIGN,
            "event_design": EVENT_DESIGN,
            "settings": masked,
            "source_registry": dry_run.get("source_registry") or {},
            "create_ready": bool(readiness.get("create_ready")),
            "create_readiness_errors": readiness.get("create_readiness_errors") or [],
            "webhook_flow": webhook_flow,
            "uses_live_vault": bool(args.use_live_vault),
            "env_file_loaded": bool(env_result),
            "env_file_loaded_count": int((env_result or {}).get("loaded_count") or 0),
            "env_file_skipped_existing_count": int((env_result or {}).get("skipped_existing_count") or 0),
            "errors": errors,
        }
        if args.output_json:
            result["output_json"] = str(args.output_json)
            _write_output_json(result, args.output_json)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"[{result['status']}] firecrawl_monitor_operational_preflight")
            print(f"- registry_count: {registry_count}")
            print(f"- webhook_secret_configured: {masked['firecrawl_monitor_webhook_secret_configured']}")
            print(f"- create_ready: {result['create_ready']}")
            print(f"- uses_live_vault: {result['uses_live_vault']}")
            if webhook_flow:
                print(
                    "- webhook_flow: "
                    f"reject={webhook_flow['rejected_status_code']} "
                    f"accept={webhook_flow['accepted_status_code']} "
                    f"saved={webhook_flow['accepted_saved_count']}"
                )
            for error in result["errors"]:
                print(f"ERROR: {error}")
        return 0 if result["status"] == "success" else 1
    finally:
        if temp_ctx:
            temp_ctx.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
