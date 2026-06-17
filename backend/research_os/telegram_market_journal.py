"""Telegram public-channel ingestion helpers for the US market-close journal."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from html import unescape
from re import IGNORECASE, search, sub
from typing import Iterable
from urllib.parse import urlencode, urljoin

import httpx
from bs4 import BeautifulSoup


TELEGRAM_MARKET_CLOSE_SOURCE_ORIGIN = "telegram_auto"
TELEGRAM_MARKET_CLOSE_SOURCE_PROVIDER = "telegram_ehdwl"
DEFAULT_TELEGRAM_MARKET_CHANNEL_USERNAME = "ehdwl"
DEFAULT_TELEGRAM_MARKET_CHANNEL_URL = "https://t.me/s/ehdwl"


@dataclass(frozen=True)
class TelegramMarketPost:
    message_id: str
    post_id: str
    url: str
    title: str
    text: str
    published_at: str | None = None


@dataclass(frozen=True)
class TelegramMarketCloseCandidate:
    source_item_id: str
    source_url: str
    source_title: str
    source_published_at: str | None
    session_date: str
    raw_summary: str
    included_post_count: int


def telegram_market_close_source_metadata(title: str | None = None) -> dict[str, str]:
    return {
        "source_origin": TELEGRAM_MARKET_CLOSE_SOURCE_ORIGIN,
        "source_provider": TELEGRAM_MARKET_CLOSE_SOURCE_PROVIDER,
        "source_title": str(title or ""),
    }


def normalize_telegram_channel_username(value: str | None) -> str:
    text = str(value or DEFAULT_TELEGRAM_MARKET_CHANNEL_USERNAME).strip()
    if text.startswith("https://t.me/"):
        text = text.removeprefix("https://t.me/").strip("/")
    if text.startswith("@"):
        text = text[1:]
    if text.startswith("s/"):
        text = text[2:]
    return text.strip("/") or DEFAULT_TELEGRAM_MARKET_CHANNEL_USERNAME


def telegram_public_channel_url(username: str | None = None, url: str | None = None) -> str:
    if url:
        text = str(url).strip()
        if "/s/" in text:
            return text
        if text.startswith("https://t.me/"):
            return "https://t.me/s/" + normalize_telegram_channel_username(text)
    return "https://t.me/s/" + normalize_telegram_channel_username(username)


def first_non_empty_line(text: str) -> str:
    for line in str(text or "").splitlines():
        stripped = line.strip(" \t\r\n*")
        if stripped:
            return stripped
    return ""


def compact_telegram_text(text: str) -> str:
    normalized = unescape(str(text or ""))
    normalized = normalized.replace("\xa0", " ")
    normalized = sub(r"[ \t]+\n", "\n", normalized)
    normalized = sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def parse_telegram_public_channel_html(
    html: str,
    *,
    channel_username: str = DEFAULT_TELEGRAM_MARKET_CHANNEL_USERNAME,
    base_url: str = DEFAULT_TELEGRAM_MARKET_CHANNEL_URL,
) -> list[TelegramMarketPost]:
    soup = BeautifulSoup(html, "html.parser")
    posts: list[TelegramMarketPost] = []
    for node in soup.select(".tgme_widget_message"):
        data_post = str(node.get("data-post") or "").strip()
        if not data_post:
            continue
        text_node = node.select_one(".tgme_widget_message_text")
        text = compact_telegram_text(text_node.get_text("\n") if text_node else "")
        if not text:
            continue
        post_id = data_post.rsplit("/", 1)[-1]
        if not post_id:
            continue
        link_node = node.select_one("a.tgme_widget_message_date")
        href = str(link_node.get("href") or "").strip() if link_node else ""
        time_node = node.select_one("time")
        published_at = str(time_node.get("datetime") or "").strip() or None if time_node else None
        posts.append(
            TelegramMarketPost(
                message_id=data_post,
                post_id=post_id,
                url=href or urljoin(base_url.rstrip("/") + "/", post_id),
                title=first_non_empty_line(text),
                text=text,
                published_at=published_at,
            )
        )
    return posts


def telegram_public_page_url(channel_url: str, before_post_id: int | None = None) -> str:
    if before_post_id is None:
        return channel_url
    separator = "&" if "?" in channel_url else "?"
    return f"{channel_url}{separator}{urlencode({'before': before_post_id})}"


def telegram_post_sort_key(post: TelegramMarketPost) -> int:
    try:
        return int(post.post_id)
    except ValueError:
        return 0


def fetch_telegram_public_channel_posts_page(
    *,
    channel_username: str,
    channel_url: str,
    timeout_seconds: float,
    user_agent: str,
    before_post_id: int | None = None,
) -> tuple[list[TelegramMarketPost], list[str]]:
    warnings: list[str] = []
    base_url = telegram_public_channel_url(channel_username, channel_url)
    url = telegram_public_page_url(base_url, before_post_id=before_post_id)
    headers = {"User-Agent": user_agent}
    with httpx.Client(timeout=timeout_seconds, follow_redirects=True, trust_env=False) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
    posts = parse_telegram_public_channel_html(
        response.text,
        channel_username=normalize_telegram_channel_username(channel_username),
        base_url=base_url,
    )
    if not posts:
        warnings.append("텔레그램 공개 미리보기에서 게시글 본문을 찾지 못했습니다.")
    return posts, warnings


def fetch_telegram_public_channel_posts(
    *,
    channel_username: str,
    channel_url: str,
    timeout_seconds: float,
    user_agent: str,
    max_posts: int,
) -> tuple[list[TelegramMarketPost], list[str]]:
    posts, warnings = fetch_telegram_public_channel_posts_page(
        channel_username=channel_username,
        channel_url=channel_url,
        timeout_seconds=timeout_seconds,
        user_agent=user_agent,
    )
    posts.sort(key=telegram_post_sort_key)
    return posts[-max(int(max_posts or 20), 1):], warnings


def fetch_telegram_public_channel_posts_backfill(
    *,
    channel_username: str,
    channel_url: str,
    timeout_seconds: float,
    user_agent: str,
    max_pages: int = 4,
) -> tuple[list[TelegramMarketPost], list[str]]:
    warnings: list[str] = []
    by_message_id: dict[str, TelegramMarketPost] = {}
    before_post_id: int | None = None
    for _ in range(max(int(max_pages or 1), 1)):
        posts, page_warnings = fetch_telegram_public_channel_posts_page(
            channel_username=channel_username,
            channel_url=channel_url,
            timeout_seconds=timeout_seconds,
            user_agent=user_agent,
            before_post_id=before_post_id,
        )
        warnings.extend(page_warnings)
        if not posts:
            break
        for post in posts:
            by_message_id[post.message_id] = post
        numeric_ids = [telegram_post_sort_key(post) for post in posts if telegram_post_sort_key(post) > 0]
        if not numeric_ids:
            break
        next_before = min(numeric_ids)
        if before_post_id is not None and next_before >= before_post_id:
            break
        before_post_id = next_before
    return sorted(by_message_id.values(), key=telegram_post_sort_key), warnings


def parse_us_market_session_date(title: str, *, today: date | None = None, published_at: str | None = None) -> str | None:
    match = search(r"\b(\d{1,2})/(\d{1,2})\b", str(title or ""))
    if not match:
        return None
    current = today or date.today()
    year = current.year
    if published_at:
        try:
            parsed = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            year = parsed.year
        except ValueError:
            pass
    month = int(match.group(1))
    day = int(match.group(2))
    if current.month == 1 and month == 12 and not published_at:
        year -= 1
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def is_us_market_close_anchor(post: TelegramMarketPost) -> bool:
    title = post.title
    text = post.text
    if not search(r"\b\d{1,2}/\d{1,2}\b", title):
        return False
    if "한국 증시" in title:
        return False
    if "미 증시" in title or "미증시" in title:
        return True
    lower = text.lower()
    return (
        ("나스닥" in text or "nasdaq" in lower)
        and ("s&p" in lower or "s＆p" in lower or "s&p500" in lower)
        and ("다우" in text or "dow" in lower)
    )


def is_related_us_market_section(post: TelegramMarketPost) -> bool:
    title = post.title
    text = post.text
    markers = (
        "특징 종목",
        "FICC",
        "한국 증시 관련 수치",
        "필라델피아 반도체",
        "국제유가",
        "달러화",
        "국채 금리",
        "시간 외",
        "나스닥",
        "S&P",
        "미 증시",
    )
    return any(marker.lower() in title.lower() or marker.lower() in text.lower() for marker in markers)


def _candidate_posts_for_anchor(posts: list[TelegramMarketPost], anchor_index: int, max_related_posts: int) -> list[TelegramMarketPost]:
    selected = [posts[anchor_index]]
    for prior in reversed(posts[:anchor_index]):
        if len(selected) >= max_related_posts:
            break
        if is_us_market_close_anchor(prior):
            break
        if is_related_us_market_section(prior):
            selected.append(prior)
    return selected


def render_telegram_market_summary(posts: Iterable[TelegramMarketPost], *, max_chars: int) -> str:
    sections: list[str] = []
    for post in posts:
        header_parts = [f"Telegram @{DEFAULT_TELEGRAM_MARKET_CHANNEL_USERNAME}", f"message={post.message_id}"]
        if post.published_at:
            header_parts.append(f"published_at={post.published_at}")
        header_parts.append(f"url={post.url}")
        sections.append("--- " + " | ".join(header_parts) + " ---\n" + post.text)
    rendered = "\n\n".join(sections).strip()
    limit = max(int(max_chars or 12000), 1000)
    if len(rendered) <= limit:
        return rendered
    return rendered[:limit].rstrip() + "\n\n[원문 길이 제한으로 이후 텔레그램 본문은 생략됨]"


def telegram_us_market_close_candidates(
    posts: list[TelegramMarketPost],
    *,
    today: date | None = None,
    max_related_posts: int = 4,
    max_summary_chars: int = 12000,
) -> list[TelegramMarketCloseCandidate]:
    sorted_posts = sorted(posts, key=telegram_post_sort_key)
    by_session_date: dict[str, TelegramMarketCloseCandidate] = {}
    for index, post in enumerate(sorted_posts):
        if not is_us_market_close_anchor(post):
            continue
        session_date = parse_us_market_session_date(post.title, today=today, published_at=post.published_at)
        if not session_date:
            continue
        selected = _candidate_posts_for_anchor(sorted_posts, index, max(max_related_posts, 1))
        selected.sort(key=telegram_post_sort_key)
        source_title = f"Telegram @{DEFAULT_TELEGRAM_MARKET_CHANNEL_USERNAME}: {post.title}"
        candidate = TelegramMarketCloseCandidate(
            source_item_id=post.message_id,
            source_url=post.url,
            source_title=source_title,
            source_published_at=post.published_at,
            session_date=session_date,
            raw_summary=render_telegram_market_summary(selected, max_chars=max_summary_chars),
            included_post_count=len(selected),
        )
        previous = by_session_date.get(session_date)
        previous_sort_key = 0
        if previous:
            try:
                previous_sort_key = int(previous.source_item_id.rsplit("/", 1)[-1])
            except ValueError:
                previous_sort_key = 0
        if previous is None or telegram_post_sort_key(post) > previous_sort_key:
            by_session_date[session_date] = candidate
    return sorted(by_session_date.values(), key=lambda item: item.session_date, reverse=True)


def latest_telegram_us_market_close_candidate(
    posts: list[TelegramMarketPost],
    *,
    today: date | None = None,
    max_related_posts: int = 4,
    max_summary_chars: int = 12000,
) -> TelegramMarketCloseCandidate | None:
    candidates = telegram_us_market_close_candidates(
        posts,
        today=today,
        max_related_posts=max_related_posts,
        max_summary_chars=max_summary_chars,
    )
    return candidates[0] if candidates else None
