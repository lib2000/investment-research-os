"""Optional Telegram account-session collector.

The default public collector only reads t.me/s previews. Some channels expose
only an app preview or file-only messages. This module keeps the account-based
path explicit, disabled by default, and secret-free in status output.
"""

from __future__ import annotations

import asyncio
import importlib.util
from dataclasses import dataclass
from datetime import timezone
from pathlib import Path
from typing import Any

from research_os.settings import Settings
from research_os.telegram_favorite_posts import (
    TelegramFavoritePopularPost,
    favorite_channel_username_from_item,
    parse_telegram_favorite_channels_json,
    telegram_favorite_post_sort_key,
)
from research_os.telegram_market_journal import telegram_public_channel_url


@dataclass(frozen=True)
class TelegramAuthenticatedChannel:
    username: str
    label: str
    max_posts: int


def telethon_available() -> bool:
    return importlib.util.find_spec("telethon") is not None


def configured_session_file(settings: Settings) -> Path:
    path = Path(str(settings.telegram_session_file or "").strip())
    if path.is_absolute():
        return path
    return path.resolve()


def session_file_exists(path: Path) -> bool:
    return path.exists() or path.with_suffix(".session").exists()


def parse_authenticated_channels(settings: Settings) -> tuple[list[TelegramAuthenticatedChannel], list[str]]:
    raw = settings.telegram_authenticated_channels_json or settings.telegram_favorite_channels_json
    favorite_channels, warnings = parse_telegram_favorite_channels_json(raw)
    channels = [
        TelegramAuthenticatedChannel(
            username=channel.username,
            label=channel.label,
            max_posts=min(max(int(channel.max_posts or settings.telegram_authenticated_max_posts or 30), 1), 100),
        )
        for channel in favorite_channels
    ]
    return channels, warnings


def masked_collection_status(settings: Settings) -> dict:
    session_path = configured_session_file(settings)
    channels, parse_warnings = parse_authenticated_channels(settings)
    api_id = str(settings.telegram_api_id or "").strip()
    api_hash = str(settings.telegram_api_hash or "").strip()
    dependency_ready = telethon_available()
    api_id_ready = api_id.isdigit()
    api_hash_ready = len(api_hash) >= 16
    session_ready = session_file_exists(session_path)
    enabled = bool(settings.telegram_authenticated_collection_enabled)
    dry_run = bool(settings.telegram_authenticated_collection_dry_run)
    ready = bool(enabled and not dry_run and dependency_ready and api_id_ready and api_hash_ready and session_ready and channels)
    blockers: list[str] = []
    if not enabled:
        blockers.append("TELEGRAM_AUTHENTICATED_COLLECTION_ENABLED=false")
    if dry_run:
        blockers.append("TELEGRAM_AUTHENTICATED_COLLECTION_DRY_RUN=true")
    if not dependency_ready:
        blockers.append("optional dependency telethon is not installed")
    if not api_id_ready:
        blockers.append("TELEGRAM_API_ID must be configured as digits")
    if not api_hash_ready:
        blockers.append("TELEGRAM_API_HASH must be configured")
    if not session_ready:
        blockers.append("TELEGRAM_SESSION_FILE session is missing")
    if not channels:
        blockers.append("authenticated channel list is empty")
    return {
        "module": "telegram_authenticated_collector",
        "enabled": enabled,
        "dry_run": dry_run,
        "ready": ready,
        "dependency": {"telethon_installed": dependency_ready},
        "secrets": {
            "api_id_configured": api_id_ready,
            "api_hash_configured": api_hash_ready,
            "session_file_configured": bool(str(settings.telegram_session_file or "").strip()),
            "session_file_exists": session_ready,
            "session_file_name": session_path.name or "configured",
        },
        "channel_count": len(channels),
        "max_posts": settings.telegram_authenticated_max_posts,
        "top_n": settings.telegram_authenticated_top_n,
        "warnings": parse_warnings,
        "blockers": blockers,
        "next_action": (
            "인증 수집 준비가 완료됐습니다. 실제 수집은 명시적으로 dry-run을 끈 상태에서만 실행됩니다."
            if ready
            else "Telethon 설치, TELEGRAM_API_ID/API_HASH, 세션 파일, enabled=true, dry_run=false를 순서대로 준비하세요."
        ),
    }


def _message_text(message: Any) -> str:
    text = str(getattr(message, "message", "") or "").strip()
    if text:
        return text
    document = getattr(message, "document", None)
    attributes = getattr(document, "attributes", []) if document is not None else []
    for attribute in attributes:
        file_name = getattr(attribute, "file_name", "")
        if file_name:
            return str(file_name).strip()
    return ""


def _message_published_at(message: Any) -> str | None:
    value = getattr(message, "date", None)
    if not value:
        return None
    try:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    except AttributeError:
        return None


async def _collect_authenticated_posts_async(settings: Settings) -> tuple[list[TelegramFavoritePopularPost], list[str]]:
    try:
        from telethon import TelegramClient  # type: ignore
    except ImportError as exc:
        raise RuntimeError("optional dependency telethon is not installed") from exc

    status = masked_collection_status(settings)
    if not status["ready"]:
        raise RuntimeError("authenticated Telegram collector is not ready: " + "; ".join(status["blockers"]))

    channels, warnings = parse_authenticated_channels(settings)
    session_path = configured_session_file(settings)
    client = TelegramClient(str(session_path), int(str(settings.telegram_api_id).strip()), str(settings.telegram_api_hash).strip())
    posts: list[TelegramFavoritePopularPost] = []
    async with client:
        authorized = await client.is_user_authorized()
        if not authorized:
            raise RuntimeError("Telegram session is not authorized. Create the session interactively outside this collector first.")
        for channel in channels:
            entity = await client.get_entity(channel.username)
            async for message in client.iter_messages(entity, limit=channel.max_posts):
                text = _message_text(message)
                if not text:
                    continue
                view_count = int(getattr(message, "views", 0) or 0)
                message_id = str(getattr(message, "id", "") or "")
                if not message_id:
                    continue
                url = f"https://t.me/{channel.username}/{message_id}"
                posts.append(
                    TelegramFavoritePopularPost(
                        channel_username=channel.username,
                        channel_label=channel.label,
                        message_id=f"{channel.username}/{message_id}",
                        post_id=message_id,
                        url=url,
                        title=text.splitlines()[0].strip()[:180],
                        text=text,
                        published_at=_message_published_at(message),
                        view_count=view_count,
                        popularity_score=view_count,
                        forward_count=int(getattr(message, "forwards", 0) or 0),
                    )
                )
    posts.sort(key=telegram_favorite_post_sort_key, reverse=True)
    return posts[: max(int(settings.telegram_authenticated_top_n or 10), 1)], warnings


def collect_authenticated_posts(settings: Settings) -> tuple[list[TelegramFavoritePopularPost], list[str]]:
    return asyncio.run(_collect_authenticated_posts_async(settings))


def build_env_template() -> str:
    return "\n".join(
        [
            "# Optional Telegram account-session collector.",
            "# Keep this file ignored. Do not commit API hash or session files.",
            "TELEGRAM_AUTHENTICATED_COLLECTION_ENABLED=false",
            "TELEGRAM_AUTHENTICATED_COLLECTION_DRY_RUN=true",
            "TELEGRAM_API_ID=",
            "TELEGRAM_API_HASH=",
            "TELEGRAM_SESSION_FILE=../research_vault/_private/telegram_user",
            "TELEGRAM_AUTHENTICATED_CHANNELS_JSON=[{\"url\":\"https://t.me/example_channel\",\"label\":\"Example\",\"max_posts\":30}]",
            "TELEGRAM_AUTHENTICATED_MAX_POSTS=30",
            "TELEGRAM_AUTHENTICATED_TOP_N=10",
            "",
        ]
    )


def sample_limited_channel_status(settings: Settings) -> dict:
    channels, warnings = parse_authenticated_channels(settings)
    limited = [
        {
            "username": channel.username,
            "label": channel.label,
            "public_url": telegram_public_channel_url(channel.username, None),
            "requires_authenticated_fallback": True,
        }
        for channel in channels
        if favorite_channel_username_from_item(channel.username).lower() in {"tree_2023_07_17", "doc_pool"}
    ]
    return {
        "limited_channel_count": len(limited),
        "limited_channels": limited,
        "warnings": warnings,
    }
