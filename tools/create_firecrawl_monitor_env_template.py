from __future__ import annotations

import argparse
import json
from pathlib import Path
from textwrap import dedent


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY_PATH = PROJECT_ROOT / "docs" / "examples" / "firecrawl_monitor_registry.sample.json"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "tmp" / "firecrawl-monitor.local.env"


PLACEHOLDER_API_KEY = "replace-with-firecrawl-api-key"
PLACEHOLDER_WEBHOOK_SECRET = "replace-with-long-random-webhook-secret"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a safe Firecrawl Monitor local env template.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="Env file path to create.")
    parser.add_argument(
        "--registry-json",
        type=Path,
        default=DEFAULT_REGISTRY_PATH,
        help="Registry JSON to inline as FIRECRAWL_MONITOR_SOURCES_JSON.",
    )
    parser.add_argument("--force", action="store_true", help="Allow overwriting an existing output file.")
    parser.add_argument("--json", action="store_true", help="Print sanitized result JSON.")
    return parser


def _compact_registry_json(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def build_env_template(registry_json: str) -> str:
    return dedent(
        f"""\
        # Firecrawl Monitor local secret env.
        # Keep this file out of git. Fill placeholders manually before operational preflight.
        # Public webhook path:
        # https://<public-investment-app-host>/api/v1/public-ir-sec/firecrawl-monitor/webhook
        # Configure Firecrawl to send one of these secret headers:
        # X-Firecrawl-Webhook-Secret, X-Webhook-Secret, or Authorization: Bearer <secret>.
        # Add a webhook.url to each monitor entry before --require-monitor-webhook / --require-create-ready.
        FIRECRAWL_MONITOR_ENABLED=false
        FIRECRAWL_MONITOR_DRY_RUN=true
        FIRECRAWL_API_KEY={PLACEHOLDER_API_KEY}
        FIRECRAWL_MONITOR_WEBHOOK_SECRET={PLACEHOLDER_WEBHOOK_SECRET}
        FIRECRAWL_BASE_URL=https://api.firecrawl.dev/v2
        FIRECRAWL_TIMEOUT_SECONDS=30
        FIRECRAWL_MONITOR_SOURCES_JSON={registry_json}
        """
    )


def create_env_template(output_path: Path, registry_path: Path, *, force: bool = False) -> dict:
    if output_path.exists() and not force:
        return {
            "status": "skipped_existing",
            "path": str(output_path),
            "registry_path": str(registry_path),
            "message": "Existing env file was not overwritten. Use --force only after backing up secrets.",
        }
    registry_json = _compact_registry_json(registry_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_env_template(registry_json), encoding="utf-8")
    return {
        "status": "created" if not output_path.exists() else "created",
        "path": str(output_path),
        "registry_path": str(registry_path),
        "enabled_default": False,
        "dry_run_default": True,
        "api_key_placeholder": True,
        "webhook_secret_placeholder": True,
        "registry_bytes": len(registry_json.encode("utf-8")),
    }


def main() -> int:
    args = _build_parser().parse_args()
    result = create_env_template(args.output, args.registry_json, force=args.force)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"[{result['status']}] firecrawl_monitor_env_template")
        print(f"- path: {result['path']}")
        print(f"- registry_path: {result['registry_path']}")
        print("- enabled_default: false")
        print("- dry_run_default: true")
        print("- secrets: placeholders only")
        if result.get("message"):
            print(f"- message: {result['message']}")
    return 0 if result["status"] in {"created", "skipped_existing"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
