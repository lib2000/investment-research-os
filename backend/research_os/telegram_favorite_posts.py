"""Telegram favorite-channel popular post collection.

This module intentionally starts from public channel previews. Telegram app
"Favorites" are account state, so private/user-folder access must be supplied
through an explicit authenticated collector later instead of guessed locally.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from re import search, sub
from typing import Any, Callable

from research_os.settings import Settings
from research_os.telegram_market_journal import (
    TelegramMarketPost,
    fetch_telegram_public_channel_posts,
    telegram_public_channel_url,
)


@dataclass(frozen=True)
class TelegramFavoriteChannel:
    username: str
    url: str
    label: str
    max_posts: int = 30


@dataclass(frozen=True)
class TelegramFavoritePopularPost:
    channel_username: str
    channel_label: str
    message_id: str
    post_id: str
    url: str
    title: str
    text: str
    published_at: str | None
    view_count: int
    popularity_score: int
    forward_count: int | None = None


@dataclass(frozen=True)
class TelegramFavoritePostsRuntime:
    current_storage_date: Callable[[], Any]
    current_storage_timestamp: Callable[[], str]
    current_storage_datetime: Callable[[], datetime]
    read_json_store: Callable[[Path, Any], Any]
    write_json_store: Callable[[Path, Any], None]
    read_news_inbox: Callable[[Settings], dict]
    write_news_inbox: Callable[[Settings, dict], None]
    content_fingerprint: Callable[[str | None], str]
    provider_error_message: Callable[[Exception, Settings], str]
    telegram_favorite_posts_state_path: Callable[[Settings], Path]
    fetch_telegram_public_channel_posts: Callable[..., tuple[list[TelegramMarketPost], list[str]]]


def _compact_text(value: str, limit: int = 700) -> str:
    text = sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def favorite_channel_username_from_item(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.startswith("https://t.me/"):
        text = text.removeprefix("https://t.me/").strip("/")
    if text.startswith("@"):
        text = text[1:]
    if text.startswith("s/"):
        text = text[2:]
    if "/" in text:
        text = text.split("/", 1)[0]
    return text.strip("/")


def parse_telegram_favorite_channels_json(raw_value: str | None) -> tuple[list[TelegramFavoriteChannel], list[str]]:
    warnings: list[str] = []
    text = str(raw_value or "").strip()
    if not text:
        return [], ["TELEGRAM_FAVORITE_CHANNELS_JSON 설정이 비어 있습니다."]
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return [], [f"TELEGRAM_FAVORITE_CHANNELS_JSON 파싱 실패: {exc.msg}"]
    raw_channels = payload.get("channels") if isinstance(payload, dict) else payload
    if not isinstance(raw_channels, list):
        return [], ["TELEGRAM_FAVORITE_CHANNELS_JSON는 배열 또는 channels 배열을 포함해야 합니다."]
    channels: list[TelegramFavoriteChannel] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_channels):
        if isinstance(item, str):
            username = favorite_channel_username_from_item(item)
            url = telegram_public_channel_url(username, None)
            label = f"@{username}"
            max_posts = 30
        elif isinstance(item, dict):
            username = favorite_channel_username_from_item(item.get("username") or item.get("url"))
            if not username:
                warnings.append(f"channels[{index}] username/url이 비어 있어 건너뜁니다.")
                continue
            url = telegram_public_channel_url(username, str(item.get("url") or ""))
            label = str(item.get("label") or item.get("name") or f"@{username}").strip()
            try:
                max_posts = int(item.get("max_posts") or 30)
            except (TypeError, ValueError):
                max_posts = 30
        else:
            warnings.append(f"channels[{index}] 항목 형식이 올바르지 않아 건너뜁니다.")
            continue
        key = username.lower()
        if not username or key in seen:
            continue
        seen.add(key)
        channels.append(
            TelegramFavoriteChannel(
                username=username,
                url=url,
                label=label or f"@{username}",
                max_posts=min(max(max_posts, 1), 100),
            )
        )
    if not channels:
        warnings.append("수집할 텔레그램 즐겨찾기 채널이 없습니다.")
    return channels, warnings


def telegram_favorite_post_sort_key(post: TelegramFavoritePopularPost) -> tuple[int, int]:
    try:
        post_id = int(post.post_id)
    except ValueError:
        post_id = 0
    return post.popularity_score, post_id


def collect_telegram_favorite_popular_posts(
    runtime: TelegramFavoritePostsRuntime,
    settings: Settings,
    *,
    limit: int | None = None,
) -> tuple[list[TelegramFavoritePopularPost], list[str]]:
    """Collect configured posts, optionally retaining the full analysis set.

    The historical default remains ``TELEGRAM_FAVORITE_POSTS_TOP_N``.  The
    deep-analysis report deliberately passes a larger limit so its channel and
    post counts describe the collected universe rather than only the popular
    post preview.
    """
    channels, warnings = parse_telegram_favorite_channels_json(settings.telegram_favorite_channels_json)
    selected: list[TelegramFavoritePopularPost] = []
    for channel in channels:
        try:
            posts, channel_warnings = runtime.fetch_telegram_public_channel_posts(
                channel_username=channel.username,
                channel_url=channel.url,
                timeout_seconds=settings.telegram_favorite_posts_timeout_seconds,
                user_agent=settings.telegram_favorite_posts_user_agent,
                max_posts=channel.max_posts,
            )
            warnings.extend(f"{channel.label}: {warning}" for warning in channel_warnings)
        except Exception as exc:
            warnings.append(f"{channel.label}: {runtime.provider_error_message(exc, settings)}")
            continue
        for post in posts:
            view_count = int(post.view_count or 0)
            if view_count < max(int(settings.telegram_favorite_posts_min_views or 0), 0):
                continue
            selected.append(
                TelegramFavoritePopularPost(
                    channel_username=channel.username,
                    channel_label=channel.label,
                    message_id=post.message_id,
                    post_id=post.post_id,
                    url=post.url,
                    title=post.title,
                    text=post.text,
                    published_at=post.published_at,
                    view_count=view_count,
                    popularity_score=view_count,
                )
            )
    selected.sort(key=telegram_favorite_post_sort_key, reverse=True)
    effective_limit = settings.telegram_favorite_posts_top_n if limit is None else limit
    if effective_limit is None or int(effective_limit) <= 0:
        return selected, warnings
    return selected[: max(int(effective_limit), 1)], warnings


def _news_item_from_popular_post(
    runtime: TelegramFavoritePostsRuntime,
    post: TelegramFavoritePopularPost,
) -> dict:
    fingerprint = runtime.content_fingerprint(f"telegram-favorite::{post.url.lower()}")
    now = runtime.current_storage_timestamp()
    raw_content = "\n".join(
        value
        for value in [
            f"텔레그램 즐겨찾기 채널: {post.channel_label} (@{post.channel_username})",
            f"인기도: 조회수 {post.view_count:,}",
            f"게시 시각: {post.published_at}" if post.published_at else "",
            f"원문 링크: {post.url}",
            f"짧은 메모: {_compact_text(post.text)}",
            "저장 정책: 텔레그램 원문 전체를 장기 보관하지 않고 링크, 제목, 조회수, 짧은 자체 메모만 시스템에 반영합니다.",
        ]
        if value
    )
    return {
        "id": fingerprint[:16],
        "fingerprint": fingerprint,
        "title": f"Telegram 인기글: {post.title}",
        "scope": "MARKET",
        "scope_label": "시장 흐름",
        "scope_reason": "telegram_favorite_popular_post",
        "source_type": "news",
        "source_url": post.url,
        "raw_content": raw_content,
        "summary": _compact_text(f"{post.channel_label} 인기글. 조회수 {post.view_count:,}. {post.title}", 420),
        "safe_user_note": _compact_text(raw_content, 900),
        "document_preview": _compact_text(post.text, 420),
        "confidence": 0.72,
        "tags": [
            "telegram_favorite",
            "popular_post",
            "market_sentiment",
            "copyright_safe_metadata",
            "url_only",
        ],
        "telegram_popularity": {
            "channel_username": post.channel_username,
            "channel_label": post.channel_label,
            "message_id": post.message_id,
            "view_count": post.view_count,
            "popularity_score": post.popularity_score,
            "published_at": post.published_at,
        },
        "copyright_policy": {
            "mode": "metadata_plus_short_note",
            "full_article_body_stored": False,
            "allowed_fields": ["title", "source_url", "channel", "view_count", "short_note"],
        },
        "created_at": now,
        "updated_at": now,
        "promoted": False,
        "promoted_storage": None,
    }


def sync_popular_posts_to_news_inbox(
    runtime: TelegramFavoritePostsRuntime,
    settings: Settings,
    posts: list[TelegramFavoritePopularPost],
) -> dict:
    inbox = runtime.read_news_inbox(settings)
    items = [item for item in inbox.get("items", []) if isinstance(item, dict)]
    saved: list[dict] = []
    duplicates: list[dict] = []
    for post in posts:
        item = _news_item_from_popular_post(runtime, post)
        existing = next(
            (
                entry
                for entry in items
                if entry.get("fingerprint") == item["fingerprint"]
                or (
                    entry.get("source_url")
                    and item.get("source_url")
                    and str(entry.get("source_url")).lower() == str(item.get("source_url")).lower()
                )
            ),
            None,
        )
        if existing:
            existing["updated_at"] = runtime.current_storage_timestamp()
            existing["duplicate_seen_count"] = int(existing.get("duplicate_seen_count") or 1) + 1
            existing["telegram_popularity"] = item["telegram_popularity"]
            duplicates.append(existing)
            continue
        items.insert(0, item)
        saved.append(item)
    inbox["items"] = items[:500]
    runtime.write_news_inbox(settings, inbox)
    return {
        "saved_count": len(saved),
        "duplicate_count": len(duplicates),
        "saved": saved,
        "duplicates": duplicates,
        "news_inbox_count": len(inbox["items"]),
    }


def parse_telegram_favorite_posts_time(settings: Settings) -> tuple[int, int]:
    match = search(r"^(\d{1,2}):(\d{2})$", str(settings.telegram_favorite_posts_time or "22:00").strip())
    if not match:
        return 22, 0
    return min(max(int(match.group(1)), 0), 23), min(max(int(match.group(2)), 0), 59)


def should_run_telegram_favorite_posts(
    runtime: TelegramFavoritePostsRuntime,
    settings: Settings,
    now: datetime | None = None,
) -> bool:
    if not settings.telegram_favorite_posts_enabled:
        return False
    now = now or runtime.current_storage_datetime()
    hour, minute = parse_telegram_favorite_posts_time(settings)
    if now.time() < now.replace(hour=hour, minute=minute, second=0, microsecond=0).time():
        return False
    state = runtime.read_json_store(runtime.telegram_favorite_posts_state_path(settings), {})
    today = now.date().isoformat()
    return state.get("last_run_date") != today and state.get("last_attempt_date") != today


def refresh_telegram_favorite_posts(
    runtime: TelegramFavoritePostsRuntime,
    settings: Settings,
    force: bool = False,
) -> dict:
    state_path = runtime.telegram_favorite_posts_state_path(settings)
    previous_state = runtime.read_json_store(state_path, {})
    today = runtime.current_storage_date().isoformat()
    if not settings.telegram_favorite_posts_enabled and not force:
        state = {
            **previous_state,
            "status": "disabled",
            "last_attempt_at": runtime.current_storage_timestamp(),
            "last_attempt_date": today,
            "last_attempt_message": "텔레그램 즐겨찾기 인기글 자동 수집이 비활성화되어 있습니다.",
        }
        runtime.write_json_store(state_path, state)
        return {"status": "disabled", "module": "telegram_favorite_posts", "state_path": str(state_path)}
    try:
        posts, warnings = collect_telegram_favorite_popular_posts(runtime, settings)
        sync = sync_popular_posts_to_news_inbox(runtime, settings, posts)
    except Exception as exc:
        state = {
            **previous_state,
            "status": "error",
            "last_attempt_at": runtime.current_storage_timestamp(),
            "last_attempt_date": today,
            "last_attempt_message": runtime.provider_error_message(exc, settings),
        }
        runtime.write_json_store(state_path, state)
        return {
            "status": "error",
            "module": "telegram_favorite_posts",
            "message": state["last_attempt_message"],
            "state_path": str(state_path),
        }
    run_at = runtime.current_storage_timestamp()
    status = "success" if posts else "not_found"
    state = {
        "status": status,
        "last_run_at": run_at if posts else previous_state.get("last_run_at"),
        "last_run_date": today if posts else previous_state.get("last_run_date"),
        "last_attempt_at": run_at,
        "last_attempt_date": today,
        "last_attempt_message": (
            f"텔레그램 즐겨찾기 인기글 {len(posts)}건 점검, 신규 {sync['saved_count']}건 뉴스 인박스 반영"
            if posts
            else "텔레그램 즐겨찾기 채널에서 기준을 충족한 인기글을 찾지 못했습니다."
        ),
        "candidate_count": len(posts),
        "saved_count": sync["saved_count"],
        "duplicate_count": sync["duplicate_count"],
        "top_posts": [
            {
                "channel_label": post.channel_label,
                "channel_username": post.channel_username,
                "title": post.title,
                "url": post.url,
                "view_count": post.view_count,
                "published_at": post.published_at,
            }
            for post in posts
        ],
        "warnings": warnings,
    }
    runtime.write_json_store(state_path, state)
    return {
        "status": status,
        "module": "telegram_favorite_posts",
        "candidate_count": len(posts),
        "saved_count": sync["saved_count"],
        "duplicate_count": sync["duplicate_count"],
        "news_inbox_count": sync["news_inbox_count"],
        "top_posts": state["top_posts"],
        "warnings": warnings,
        "state_path": str(state_path),
    }


def build_telegram_favorite_posts_task_status(
    runtime: TelegramFavoritePostsRuntime,
    settings: Settings,
) -> dict:
    state = runtime.read_json_store(runtime.telegram_favorite_posts_state_path(settings), {})
    channels, warnings = parse_telegram_favorite_channels_json(settings.telegram_favorite_channels_json)
    enabled = bool(settings.telegram_favorite_posts_enabled)
    due_now = should_run_telegram_favorite_posts(runtime, settings) if enabled else False
    if not enabled:
        status = "disabled"
        next_action = "TELEGRAM_FAVORITE_POSTS_ENABLED=true와 TELEGRAM_FAVORITE_CHANNELS_JSON 설정 후 22:00 자동 수집을 켜세요."
    elif not channels:
        status = "needs_configuration"
        next_action = "즐겨찾기 채널 목록 JSON이 비어 있어 수집할 수 없습니다."
    elif due_now:
        status = "due"
        next_action = "오늘 22:00 이후 자동 수집이 아직 실행되지 않았습니다."
    elif state.get("status") == "error":
        status = "needs_attention"
        next_action = "최근 텔레그램 즐겨찾기 인기글 수집 오류를 확인하세요."
    else:
        status = "ok"
        next_action = "최근 상태가 정상입니다. 같은 텔레그램 원본은 뉴스 인박스에서 중복 저장하지 않습니다."
    return {
        "status": status,
        "module": "telegram_favorite_posts_task_status",
        "enabled": enabled,
        "daily_time": settings.telegram_favorite_posts_time,
        "configured_channel_count": len(channels),
        "top_n": settings.telegram_favorite_posts_top_n,
        "min_views": settings.telegram_favorite_posts_min_views,
        "due_now": due_now,
        "state": state,
        "warnings": warnings,
        "next_action": next_action,
    }
