"""Evidence-preserving Telegram market deep-analysis report renderer.

The report is deliberately deterministic: it only summarizes the configured
channel posts and never turns a social signal into a buy/sell instruction.
Authenticated collection may provide forwards; public ``t.me/s`` previews do
not, so the renderer labels that field as unavailable instead of inventing it.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from re import findall, sub
from typing import Any, Iterable

from research_os.telegram_brief_sender import chunk_telegram_message


DESIGN_NAME = "telegram_deep_analysis_v1"
DEFAULT_TOP_N = 10
DEFAULT_ENTITY_ALIASES = {
    "삼성전자": {"label": "삼성전자", "ticker": "005930.KS"},
    "SK하이닉스": {"label": "SK하이닉스", "ticker": "000660.KS"},
    "엔비디아": {"label": "엔비디아", "ticker": "NVDA"},
    "NVIDIA": {"label": "엔비디아", "ticker": "NVDA"},
    "일라이 릴리": {"label": "일라이릴리", "ticker": "LLY"},
    "페이팔": {"label": "페이팔", "ticker": "PYPL"},
    "마벨": {"label": "마벨", "ticker": "MRVL"},
    "테이크투": {"label": "테이크투 인터랙티브", "ticker": "TTWO"},
    "CHEVRON": {"label": "CHEVRON", "ticker": "CVX"},
    "레인보우로보틱스": {"label": "레인보우로보틱스", "ticker": "277810.KQ"},
}
POSITIVE_TERMS = (
    "상승", "급등", "호조", "호실적", "개선", "상향", "매수", "수주", "계약", "승인", "확대", "흑자", "성장",
    "beat", "upgrade", "outperform", "approval", "record", "growth", "bullish",
)
NEGATIVE_TERMS = (
    "하락", "급락", "부진", "악화", "하향", "매도", "리스크", "우려", "실망", "손실", "포기", "감소",
    "miss", "downgrade", "underperform", "risk", "bearish", "decline", "drop",
)
STOP_WORDS = {
    "그리고", "그러나", "대한", "관련", "통해", "이번", "오늘", "내일", "시장", "주가", "투자", "분석", "발표", "기준",
    "있다", "한다", "했다", "것으로", "에서", "에게", "하는", "지난", "최근", "현재", "뉴스", "리서치", "보고서",
    "this", "that", "with", "from", "will", "have", "about", "after", "into", "your", "stock", "market", "http", "https", "www",
}
UPPERCASE_TICKER_EXCLUSIONS = {"AI", "ETF", "EPS", "FDA", "FOMC", "GDP", "IPO", "USD", "KRW", "GTA", "ROA", "ROE", "OPM", "ARR", "CAGR", "DXY", "YCC", "KST"}


def _compact(value: Any, limit: int = 180) -> str:
    text = sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= limit else text[:limit].rstrip() + "..."


def _as_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def parse_entity_aliases_json(raw_value: str | None) -> tuple[dict[str, dict[str, str]], list[str]]:
    """Merge optional aliases without requiring ticker claims in source posts."""
    aliases = {key.casefold(): dict(value) for key, value in DEFAULT_ENTITY_ALIASES.items()}
    warnings: list[str] = []
    text = str(raw_value or "").strip()
    if not text:
        return aliases, warnings
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return aliases, [f"TELEGRAM_DEEP_ANALYSIS_ENTITY_ALIASES_JSON 파싱 실패: {exc.msg}"]
    entries = payload.get("entities") if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        return aliases, ["TELEGRAM_DEEP_ANALYSIS_ENTITY_ALIASES_JSON는 entities 배열 또는 배열이어야 합니다."]
    for index, item in enumerate(entries):
        if not isinstance(item, dict):
            warnings.append(f"entities[{index}] 형식이 올바르지 않아 건너뜁니다.")
            continue
        alias = _compact(item.get("alias") or item.get("name"), 80)
        label = _compact(item.get("label") or alias, 80)
        ticker = _compact(item.get("ticker"), 24)
        if not alias:
            warnings.append(f"entities[{index}] alias/name이 비어 있어 건너뜁니다.")
            continue
        aliases[alias.casefold()] = {"label": label or alias, "ticker": ticker}
    return aliases, warnings


def _post_mapping(post: Any) -> dict[str, Any]:
    if isinstance(post, dict):
        return post
    return {
        "channel_username": getattr(post, "channel_username", ""),
        "channel_label": getattr(post, "channel_label", ""),
        "post_id": getattr(post, "post_id", ""),
        "url": getattr(post, "url", ""),
        "title": getattr(post, "title", ""),
        "text": getattr(post, "text", ""),
        "published_at": getattr(post, "published_at", None),
        "view_count": getattr(post, "view_count", 0),
        "forward_count": getattr(post, "forward_count", None),
    }


def sentiment_score(text: str) -> int:
    lowered = str(text or "").casefold()
    positive = sum(lowered.count(term.casefold()) for term in POSITIVE_TERMS)
    negative = sum(lowered.count(term.casefold()) for term in NEGATIVE_TERMS)
    return max(-100, min(100, (positive - negative) * 10))


def _keyword_counts(posts: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    display: dict[str, str] = {}
    for post in posts:
        text = f"{post.get('title') or ''} {post.get('text') or ''}"
        for token in findall(r"[A-Za-z][A-Za-z0-9&.+-]{1,}|[가-힣]{2,}", text):
            normalized = token.casefold()
            if normalized in STOP_WORDS or token.isdigit():
                continue
            counts[normalized] += 1
            display.setdefault(normalized, token)
    return [{"keyword": display[key], "count": count} for key, count in counts.most_common(5)]


def _entity_rows(posts: Iterable[dict[str, Any]], aliases: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for post in posts:
        text = f"{post.get('title') or ''}\n{post.get('text') or ''}"
        lowered = text.casefold()
        candidates: dict[str, dict[str, str]] = {}
        for alias, entity in aliases.items():
            if alias in lowered:
                key = entity.get("ticker") or entity.get("label") or alias
                candidates[key] = entity
        # A bare capitalized word is too ambiguous in Korean market posts
        # (ROA, OPM, CME, and many abbreviations are not listed equities).
        # Unknown securities therefore need an explicit ticker convention;
        # broader company-name coverage belongs in the configured alias list.
        ticker_matches = findall(
            r"\$([A-Z]{2,5})\b|\b(?:NASDAQ|NYSE|KOSPI|KOSDAQ)\s*[:：]\s*([A-Z]{2,5})\b",
            text,
        )
        for match in ticker_matches:
            ticker = next((value for value in match if value), "")
            if ticker not in UPPERCASE_TICKER_EXCLUSIONS:
                candidates.setdefault(ticker, {"label": ticker, "ticker": ticker})
        post_score = sentiment_score(text)
        for key, entity in candidates.items():
            row = rows.setdefault(key, {"label": entity.get("label") or key, "ticker": entity.get("ticker") or "", "mentions": 0, "sentiment_score": 0, "examples": []})
            row["mentions"] += 1
            row["sentiment_score"] += post_score
            if len(row["examples"]) < 2:
                row["examples"].append(_compact(post.get("title") or post.get("text"), 100))
    for row in rows.values():
        row["sentiment_score"] = max(-100, min(100, int(row["sentiment_score"] / max(row["mentions"], 1))))
    return sorted(rows.values(), key=lambda row: (abs(row["sentiment_score"]), row["mentions"], row["label"]), reverse=True)[:10]


def _engagement_score(post: dict[str, Any]) -> float:
    # Sentiment and forwards are the defined primary score. Views are only a
    # stable tie-breaker for public previews where forwarding is unavailable.
    return sentiment_score(f"{post.get('title') or ''}\n{post.get('text') or ''}") + min(_as_int(post.get("forward_count")), 1000) * 0.25 + math.log1p(_as_int(post.get("view_count"))) * 0.01


def build_telegram_deep_analysis(
    posts: Iterable[Any],
    *,
    analyzed_at: datetime | None = None,
    configured_channel_count: int | None = None,
    entity_aliases_json: str | None = None,
    top_n: int = DEFAULT_TOP_N,
) -> dict[str, Any]:
    normalized = [_post_mapping(post) for post in posts]
    aliases, warnings = parse_entity_aliases_json(entity_aliases_json)
    channel_keys = {str(post.get("channel_username") or post.get("channel_label") or "").casefold() for post in normalized}
    channel_count = configured_channel_count if configured_channel_count is not None else len(channel_keys - {""})
    scores = [sentiment_score(f"{post.get('title') or ''}\n{post.get('text') or ''}") for post in normalized]
    aggregate = round(sum(scores) / len(scores)) if scores else 0
    top_posts = sorted(normalized, key=lambda post: (_engagement_score(post), _as_int(post.get("view_count"))), reverse=True)[: max(1, int(top_n or DEFAULT_TOP_N))]
    entities = _entity_rows(normalized, aliases)
    keywords = _keyword_counts(normalized)
    positive = sum(1 for score in scores if score > 0)
    negative = sum(1 for score in scores if score < 0)
    summary = (
        f"{len(normalized)}개 게시글에서 긍정 신호 {positive}건, 부정 신호 {negative}건이 감지됐습니다. "
        + ("긍정 언급이 우세하지만 거시·개별 리스크 원문을 함께 확인하세요." if aggregate > 0 else "부정 또는 혼합 신호가 있어 원문 확인이 필요합니다." if aggregate < 0 else "방향성은 혼합으로, 원문 근거를 우선 확인하세요.")
    )
    return {
        "design": DESIGN_NAME,
        "analyzed_at": (analyzed_at or datetime.now().astimezone()).isoformat(timespec="minutes"),
        "channel_count": int(channel_count or 0),
        "post_count": len(normalized),
        "sentiment_score": aggregate,
        "sentiment_label": "긍정" if aggregate > 0 else "부정" if aggregate < 0 else "중립",
        "summary": summary,
        "keywords": keywords,
        "entities": entities,
        "top_posts": [{**post, "sentiment_score": sentiment_score(f"{post.get('title') or ''}\n{post.get('text') or ''}"), "engagement_score": round(_engagement_score(post), 2)} for post in top_posts],
        "warnings": warnings,
        "scoring": {"sentiment_range": "-100~100", "primary_inputs": ["post sentiment", "forward count when available"], "view_count": "displayed and used only as a public-preview tie-breaker"},
    }


def _delta(value: int) -> str:
    return f"+{value}" if value > 0 else str(value)


def render_telegram_deep_analysis_report(analysis: dict[str, Any]) -> str:
    timestamp = str(analysis.get("analyzed_at") or "")
    try:
        display_time = datetime.fromisoformat(timestamp).strftime("%H시 %M분")
    except ValueError:
        display_time = "시간 미확인"
    lines = [
        f"📝 텔레그램 심층 분석 Report ({display_time}) 기준",
        f"🌡️ 센티먼트 {analysis.get('sentiment_label') or '중립'} ({_delta(_as_int(analysis.get('sentiment_score')))})",
        f"💡 요약 {analysis.get('summary') or '수집된 게시글이 없습니다.'}",
    ]
    keywords = analysis.get("keywords") or []
    lines.append("🗣️ Top 키워드: " + (", ".join(f"{item.get('keyword')}({item.get('count')})" for item in keywords) if keywords else "수집된 키워드 없음"))
    lines.append("🔥 주목받는 종목")
    entities = analysis.get("entities") or []
    if entities:
        for entity in entities:
            icon = "📈" if _as_int(entity.get("sentiment_score")) > 0 else "📉" if _as_int(entity.get("sentiment_score")) < 0 else "➖"
            label = _compact(entity.get("label"), 70)
            ticker = _compact(entity.get("ticker"), 20)
            example = _compact((entity.get("examples") or [""])[0], 120)
            lines.extend([f"{icon} {label}{f' ({ticker})' if ticker else ''} ({_delta(_as_int(entity.get('sentiment_score')))})", f"언급 {entity.get('mentions', 0)}건 · {example}"])
    else:
        lines.append("➖ 설정된 별칭 또는 티커 기반으로 감지된 종목이 없습니다.")
    lines.append(f"🎉 수집 완료! {analysis.get('channel_count', 0)}개 채널에서 게시글 {analysis.get('post_count', 0)}개 분석")
    lines.append("🔥 현시점 인기 게시글 TOP 10")
    for index, post in enumerate(analysis.get("top_posts") or [], start=1):
        views = f"{_as_int(post.get('view_count')):,} 👁️"
        forwards = f"{_as_int(post.get('forward_count')):,} 📤" if post.get("forward_count") is not None else "공유 미제공"
        lines.extend([f"[{index}위] {views} | {forwards}", f"📺 {_compact(post.get('channel_label') or post.get('channel_username'), 80)}", f"📝 {_compact(post.get('title') or post.get('text'), 190)}", f"🔗 {_compact(post.get('url'), 220)}"])
    lines.extend([
        "ℹ️ 스코어링: 최근 게시글 감정(-100~100)과 공유 횟수(제공 시)를 합산하며, 조회수는 공개 preview의 동률 정렬에만 사용합니다.",
        "⚠️ 이 리포트는 채널 게시글 기반 참고 정보이며, 투자 판단 전 원문과 공시·실적을 직접 확인하세요.",
    ])
    return "\n".join(lines)


def build_telegram_deep_analysis_payload(
    analysis: dict[str, Any],
    *,
    chat_id: str = "",
    max_message_chars: int = 3600,
) -> dict[str, Any]:
    text = render_telegram_deep_analysis_report(analysis)
    messages = [
        {"chat_id": chat_id, "text": chunk, "disable_web_page_preview": True, "priority": "must_keep", "category": "telegram_deep_analysis"}
        for chunk in chunk_telegram_message(text, max_chars=max_message_chars)
    ]
    return {"design": DESIGN_NAME, "status": "success", "chat_id_configured": bool(str(chat_id).strip()), "message_count": len(messages), "messages": messages, "text": text, "analysis": analysis}
