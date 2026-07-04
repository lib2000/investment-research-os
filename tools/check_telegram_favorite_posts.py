"""Check Telegram favorite-channel popular-post ingestion without account secrets."""

from __future__ import annotations

import argparse
import json
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


def build_runtime(settings: Settings, *, live_fetch: bool) -> TelegramFavoritePostsRuntime:
    if live_fetch:
        from research_os.telegram_market_journal import fetch_telegram_public_channel_posts

        fetch_posts = fetch_telegram_public_channel_posts
    else:
        fetch_posts = sample_posts

    state_path = PROJECT_ROOT / "tmp" / "telegram_favorite_posts_check_state.json"
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
        telegram_favorite_posts_state_path=lambda _settings: state_path,
        fetch_telegram_public_channel_posts=fetch_posts,
    )


def build_settings(args: argparse.Namespace) -> Settings:
    channels_json = args.channels_json
    if args.channels_json_file:
        channels_json = args.channels_json_file.read_text(encoding="utf-8").strip()
    if not channels_json and args.sample:
        channels_json = SAMPLE_CHANNELS_JSON
    return Settings(
        research_vault_dir=str(PROJECT_ROOT / ".test-tmp" / "telegram-favorite-posts-check-vault"),
        telegram_favorite_posts_enabled=args.enabled,
        telegram_favorite_posts_time=args.time,
        telegram_favorite_channels_json=channels_json or "",
        telegram_favorite_posts_top_n=args.top_n,
        telegram_favorite_posts_min_views=args.min_views,
        telegram_favorite_posts_timeout_seconds=args.timeout_seconds,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Telegram 즐겨찾기 인기글 수집 설정을 dry-run으로 점검합니다.")
    parser.add_argument("--enabled", action="store_true", help="enabled 상태로 스케줄/status를 점검합니다.")
    parser.add_argument("--sample", action="store_true", help="샘플 공개 채널 설정과 샘플 게시글로 점검합니다.")
    parser.add_argument("--channels-json", default="", help="TELEGRAM_FAVORITE_CHANNELS_JSON 값")
    parser.add_argument("--channels-json-file", type=Path, help="채널 JSON 파일")
    parser.add_argument("--live-fetch", action="store_true", help="실제 t.me/s 공개 preview를 조회합니다.")
    parser.add_argument("--sync-news-inbox", action="store_true", help="임시 vault 뉴스 인박스에 dry-run 저장까지 확인합니다.")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--min-views", type=int, default=0)
    parser.add_argument("--time", default="22:00")
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--output-json", type=Path, help="점검 결과 JSON 저장")
    parser.add_argument("--json", action="store_true", help="점검 결과를 JSON으로 출력합니다.")
    args = parser.parse_args()

    settings = build_settings(args)
    runtime = build_runtime(settings, live_fetch=args.live_fetch)
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
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "success" else 1

    print(f"[{result['status']}] telegram_favorite_posts_check")
    print(f"- enabled: {result['enabled']}")
    print(f"- daily_time: {result['daily_time']}")
    print(f"- channel_count: {result['channel_count']}")
    print(f"- candidate_count: {result['candidate_count']}")
    print(f"- task_status: {status.get('status')}")
    for post in result["top_posts"][:5]:
        print(f"- top: {post['channel_label']} | {post['view_count']} views | {post['title']}")
    for warning in result["warnings"][:5]:
        print(f"- warning: {warning}")
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
