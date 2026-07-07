"""Check optional Telegram account-session collector readiness."""

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

from research_os.settings import Settings  # noqa: E402
from research_os.telegram_authenticated_collector import (  # noqa: E402
    build_env_template,
    collect_authenticated_posts,
    masked_collection_status,
    sample_limited_channel_status,
)


def read_env_file(path: Path | None) -> dict[str, str]:
    if not path:
        return {}
    if not path.exists():
        raise SystemExit(f"env file not found: {path}")
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def env_value(values: dict[str, str], name: str, default: str = "") -> str:
    value = values.get(name, default)
    return str(value if value is not None else default).strip()


def env_bool(values: dict[str, str], name: str, default: bool) -> bool:
    value = values.get(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def env_int(values: dict[str, str], name: str, default: int) -> int:
    value = values.get(name)
    if value is None:
        return default
    try:
        return int(str(value).strip())
    except ValueError:
        return default


def settings_from_args(args: argparse.Namespace, env_values: dict[str, str]) -> Settings:
    channels_json = args.channels_json
    if args.channels_json_file:
        channels_json = args.channels_json_file.read_text(encoding="utf-8").strip()
    return Settings(
        research_vault_dir=str(PROJECT_ROOT / "research_vault"),
        telegram_authenticated_collection_enabled=args.enabled
        or env_bool(env_values, "TELEGRAM_AUTHENTICATED_COLLECTION_ENABLED", False),
        telegram_authenticated_collection_dry_run=not args.no_dry_run
        if args.no_dry_run
        else env_bool(env_values, "TELEGRAM_AUTHENTICATED_COLLECTION_DRY_RUN", True),
        telegram_authenticated_channels_json=channels_json
        or env_value(env_values, "TELEGRAM_AUTHENTICATED_CHANNELS_JSON", env_value(env_values, "TELEGRAM_FAVORITE_CHANNELS_JSON", "")),
        telegram_api_id=env_value(env_values, "TELEGRAM_API_ID", ""),
        telegram_api_hash=env_value(env_values, "TELEGRAM_API_HASH", ""),
        telegram_session_file=env_value(env_values, "TELEGRAM_SESSION_FILE", "../research_vault/_private/telegram_user"),
        telegram_authenticated_max_posts=args.max_posts
        if args.max_posts is not None
        else env_int(env_values, "TELEGRAM_AUTHENTICATED_MAX_POSTS", 30),
        telegram_authenticated_top_n=args.top_n
        if args.top_n is not None
        else env_int(env_values, "TELEGRAM_AUTHENTICATED_TOP_N", 10),
    )


def console_print(value: object) -> None:
    text = str(value)
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    print(text.encode(encoding, errors="replace").decode(encoding, errors="replace"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Telegram 계정 인증 기반 수집기 readiness를 점검합니다.")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--use-env", action="store_true", help="현재 환경변수를 함께 사용합니다.")
    parser.add_argument("--enabled", action="store_true", help="enabled=true 상태로 점검합니다.")
    parser.add_argument("--no-dry-run", action="store_true", help="dry_run=false 상태로 점검합니다.")
    parser.add_argument("--channels-json", default="")
    parser.add_argument("--channels-json-file", type=Path)
    parser.add_argument("--max-posts", type=int)
    parser.add_argument("--top-n", type=int)
    parser.add_argument("--write-env-template", type=Path)
    parser.add_argument("--collect", action="store_true", help="준비 완료 시 실제 계정 세션으로 수집합니다.")
    parser.add_argument("--allow-live", action="store_true", help="collect 실행을 명시적으로 허용합니다.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.write_env_template:
        output_path = args.write_env_template if args.write_env_template.is_absolute() else PROJECT_ROOT / args.write_env_template
        if output_path.exists():
            raise SystemExit(f"refusing to overwrite existing file: {output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(build_env_template(), encoding="utf-8")
        console_print(f"created env template: {output_path}")
        return 0

    env_values = dict(os.environ) if args.use_env else {}
    env_values.update(read_env_file(args.env_file))
    settings = settings_from_args(args, env_values)
    status = masked_collection_status(settings)
    limited_status = sample_limited_channel_status(settings)
    result = {
        "status": "ready" if status["ready"] else "not_ready",
        "module": "telegram_authenticated_collector_check",
        "collector": status,
        "limited_channels": limited_status,
        "collect_result": {"status": "skipped", "reason": "collect not requested"},
        "errors": [],
    }
    if args.collect:
        if not args.allow_live:
            result["collect_result"] = {"status": "blocked", "reason": "--allow-live is required for authenticated collection"}
            result["errors"].append("live collection requires --allow-live")
        elif not status["ready"]:
            result["collect_result"] = {"status": "blocked", "reason": "collector is not ready"}
            result["errors"].extend(status["blockers"])
        else:
            posts, warnings = collect_authenticated_posts(settings)
            result["collect_result"] = {
                "status": "success",
                "candidate_count": len(posts),
                "warnings": warnings,
                "top_posts": [
                    {
                        "channel_label": post.channel_label,
                        "title": post.title,
                        "url": post.url,
                        "view_count": post.view_count,
                        "published_at": post.published_at,
                    }
                    for post in posts
                ],
            }
    exit_ok = not result["errors"]
    if args.json:
        console_print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        console_print(f"[{result['status']}] telegram_authenticated_collector")
        console_print(f"- ready: {status['ready']}")
        console_print(f"- telethon_installed: {status['dependency']['telethon_installed']}")
        console_print(f"- channel_count: {status['channel_count']}")
        console_print(f"- limited_channel_count: {limited_status['limited_channel_count']}")
        for blocker in status["blockers"][:8]:
            console_print(f"- blocker: {blocker}")
    return 0 if exit_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
