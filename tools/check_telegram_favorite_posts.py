"""Check Telegram favorite-channel popular-post ingestion without account secrets."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.dossier_text import content_fingerprint  # noqa: E402
from research_os.settings import Settings  # noqa: E402
from research_os.state_store import news_inbox_path, read_json_store, write_json_store  # noqa: E402
from research_os.telegram_favorite_posts import (  # noqa: E402
    TelegramFavoritePostsRuntime,
    build_telegram_favorite_posts_task_status,
    collect_telegram_favorite_popular_posts,
    parse_telegram_favorite_channels_json,
    refresh_telegram_favorite_posts,
)
from research_os.telegram_market_journal import TelegramMarketPost  # noqa: E402


SAMPLE_CHANNELS_JSON = '[{"username":"sample_channel","label":"Sample","max_posts":10}]'
ENV_TEMPLATE = """# Telegram favorite-channel popular posts -> News Inbox.
# Copy this to an ignored env file or backend\\.env and replace channel names.
TELEGRAM_FAVORITE_POSTS_ENABLED=false
TELEGRAM_FAVORITE_POSTS_TIME=22:00
TELEGRAM_FAVORITE_CHANNELS_JSON=[{"username":"example_channel","label":"Example","max_posts":30}]
TELEGRAM_FAVORITE_POSTS_TIMEOUT_SECONDS=10
TELEGRAM_FAVORITE_POSTS_TOP_N=10
TELEGRAM_FAVORITE_POSTS_MIN_VIEWS=0
"""


def sample_posts(**_kwargs):
    return (
        [
            TelegramMarketPost(
                message_id="sample_channel/101",
                post_id="101",
                url="https://t.me/sample_channel/101",
                title="AI 전력망 인기글",
                text="AI 데이터센터 전력망 병목과 변압기 공급 이슈",
                published_at="2026-07-05T11:00:00+00:00",
                view_count=1800,
            ),
            TelegramMarketPost(
                message_id="sample_channel/102",
                post_id="102",
                url="https://t.me/sample_channel/102",
                title="반도체 장비 인기글",
                text="HBM 테스트 장비 수요와 후공정 병목",
                published_at="2026-07-05T12:00:00+00:00",
                view_count=1200,
            ),
            TelegramMarketPost(
                message_id="sample_channel/103",
                post_id="103",
                url="https://t.me/sample_channel/103",
                title="낮은 조회수",
                text="최소 조회수 기준 미달",
                published_at="2026-07-05T13:00:00+00:00",
                view_count=10,
            ),
        ],
        [],
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
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def env_bool(values: dict[str, str], name: str, default: bool = False) -> bool:
    value = values.get(name, os.getenv(name))
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def env_int(values: dict[str, str], name: str, default: int) -> int:
    value = values.get(name, os.getenv(name))
    if value is None:
        return default
    try:
        return int(str(value).strip())
    except ValueError:
        return default


def env_float(values: dict[str, str], name: str, default: float) -> float:
    value = values.get(name, os.getenv(name))
    if value is None:
        return default
    try:
        return float(str(value).strip())
    except ValueError:
        return default


def env_str(values: dict[str, str], name: str, default: str = "") -> str:
    value = values.get(name, os.getenv(name))
    return str(value if value is not None else default).strip()


def console_print(value: object) -> None:
    text = str(value)
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    print(text.encode(encoding, errors="replace").decode(encoding, errors="replace"))


def build_runtime(settings: Settings, *, live_fetch: bool, state_path: Path | None = None) -> TelegramFavoritePostsRuntime:
    if live_fetch:
        from research_os.telegram_market_journal import fetch_telegram_public_channel_posts

        fetch_posts = fetch_telegram_public_channel_posts
    else:
        fetch_posts = sample_posts

    resolved_state_path = state_path or PROJECT_ROOT / "tmp" / "telegram_favorite_posts_check_state.json"
    return TelegramFavoritePostsRuntime(
        current_storage_date=lambda: date(2026, 7, 5),
        current_storage_timestamp=lambda: "2026-07-05T22:01:00+09:00",
        current_storage_datetime=lambda: datetime(2026, 7, 5, 22, 1),
        read_json_store=read_json_store,
        write_json_store=write_json_store,
        read_news_inbox=lambda local_settings: read_json_store(news_inbox_path(local_settings), {"items": []}),
        write_news_inbox=lambda local_settings, payload: write_json_store(news_inbox_path(local_settings), payload),
        content_fingerprint=content_fingerprint,
        provider_error_message=lambda exc, _settings: str(exc),
        telegram_favorite_posts_state_path=lambda _settings: resolved_state_path,
        fetch_telegram_public_channel_posts=fetch_posts,
    )


def build_settings(args: argparse.Namespace, env_values: dict[str, str]) -> Settings:
    channels_json = args.channels_json
    if args.channels_json_file:
        channels_json = args.channels_json_file.read_text(encoding="utf-8").strip()
    if not channels_json and (args.use_env or args.env_file):
        channels_json = env_str(env_values, "TELEGRAM_FAVORITE_CHANNELS_JSON", "")
    if not channels_json and args.sample:
        channels_json = SAMPLE_CHANNELS_JSON
    return Settings(
        research_vault_dir=str(PROJECT_ROOT / ".test-tmp" / "telegram-favorite-posts-check-vault"),
        telegram_favorite_posts_enabled=args.enabled or env_bool(env_values, "TELEGRAM_FAVORITE_POSTS_ENABLED", False),
        telegram_favorite_posts_time=args.time or env_str(env_values, "TELEGRAM_FAVORITE_POSTS_TIME", "22:00"),
        telegram_favorite_channels_json=channels_json or "",
        telegram_favorite_posts_top_n=args.top_n if args.top_n is not None else env_int(env_values, "TELEGRAM_FAVORITE_POSTS_TOP_N", 10),
        telegram_favorite_posts_min_views=args.min_views if args.min_views is not None else env_int(env_values, "TELEGRAM_FAVORITE_POSTS_MIN_VIEWS", 0),
        telegram_favorite_posts_timeout_seconds=args.timeout_seconds if args.timeout_seconds is not None else env_float(env_values, "TELEGRAM_FAVORITE_POSTS_TIMEOUT_SECONDS", 10.0),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Telegram 즐겨찾기 인기글 수집 설정을 dry-run으로 점검합니다.")
    parser.add_argument("--enabled", action="store_true", help="enabled 상태로 스케줄/status를 점검합니다.")
    parser.add_argument("--sample", action="store_true", help="샘플 공개 채널 설정과 샘플 게시글로 점검합니다.")
    parser.add_argument("--channels-json", default="", help="TELEGRAM_FAVORITE_CHANNELS_JSON 값")
    parser.add_argument("--channels-json-file", type=Path, help="채널 JSON 파일")
    parser.add_argument("--env-file", type=Path, help="backend\\.env 또는 별도 ignored env 파일")
    parser.add_argument("--use-env", action="store_true", help="현재 프로세스 환경변수에서 Telegram 설정을 읽습니다.")
    parser.add_argument("--write-env-template", type=Path, help="텔레그램 즐겨찾기 env 템플릿을 생성합니다.")
    parser.add_argument("--state-file", type=Path, help="점검 상태 파일 경로. 생략하면 tmp 아래 기본 파일을 사용합니다.")
    parser.add_argument("--live-fetch", action="store_true", help="실제 t.me/s 공개 preview를 조회합니다.")
    parser.add_argument("--sync-news-inbox", action="store_true", help="임시 vault 뉴스 인박스에 dry-run 저장까지 확인합니다.")
    parser.add_argument("--top-n", type=int, default=None)
    parser.add_argument("--min-views", type=int, default=None)
    parser.add_argument("--time", default=None)
    parser.add_argument("--timeout-seconds", type=float, default=None)
    parser.add_argument("--output-json", type=Path, help="점검 결과 JSON 저장")
    parser.add_argument("--json", action="store_true", help="점검 결과를 JSON으로 출력합니다.")
    args = parser.parse_args()

    if args.write_env_template:
        output_path = args.write_env_template if args.write_env_template.is_absolute() else PROJECT_ROOT / args.write_env_template
        if output_path.exists():
            raise SystemExit(f"refusing to overwrite existing file: {output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(ENV_TEMPLATE, encoding="utf-8")
        print(f"created env template: {output_path}")
        return 0

    env_values = read_env_file(args.env_file)
    settings = build_settings(args, env_values)
    state_file = args.state_file if not args.state_file or args.state_file.is_absolute() else PROJECT_ROOT / args.state_file
    runtime = build_runtime(settings, live_fetch=args.live_fetch, state_path=state_file)
    channels, parse_warnings = parse_telegram_favorite_channels_json(settings.telegram_favorite_channels_json)
    posts, collect_warnings = collect_telegram_favorite_popular_posts(runtime, settings) if channels else ([], [])
    status = build_telegram_favorite_posts_task_status(runtime, settings)
    refresh_result = (
        refresh_telegram_favorite_posts(runtime, settings, force=True)
        if args.sync_news_inbox
        else {"status": "skipped", "reason": "sync-news-inbox not requested"}
    )
    result = {
        "status": "success" if channels and (posts or not args.live_fetch) else "needs_configuration",
        "module": "telegram_favorite_posts_check",
        "enabled": settings.telegram_favorite_posts_enabled,
        "env_file_loaded": bool(args.env_file),
        "daily_time": settings.telegram_favorite_posts_time,
        "channel_count": len(channels),
        "top_n": settings.telegram_favorite_posts_top_n,
        "min_views": settings.telegram_favorite_posts_min_views,
        "candidate_count": len(posts),
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
        "task_status": status,
        "refresh_result": refresh_result,
        "warnings": [*parse_warnings, *collect_warnings],
    }
    if args.output_json:
        output_path = args.output_json if args.output_json.is_absolute() else PROJECT_ROOT / args.output_json
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.json:
        console_print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "success" else 1

    console_print(f"[{result['status']}] telegram_favorite_posts_check")
    console_print(f"- enabled: {result['enabled']}")
    console_print(f"- daily_time: {result['daily_time']}")
    console_print(f"- channel_count: {result['channel_count']}")
    console_print(f"- candidate_count: {result['candidate_count']}")
    console_print(f"- task_status: {status.get('status')}")
    for post in result["top_posts"][:5]:
        console_print(f"- top: {post['channel_label']} | {post['view_count']} views | {post['title']}")
    for warning in result["warnings"][:5]:
        console_print(f"- warning: {warning}")
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
