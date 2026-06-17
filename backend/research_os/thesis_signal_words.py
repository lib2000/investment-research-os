"""Shared signal word helpers for thesis impact classification."""

from __future__ import annotations


POSITIVE_SIGNAL_WORDS = {
    "beat",
    "beats",
    "raise",
    "raised",
    "strong",
    "accelerate",
    "growth",
    "margin expansion",
    "positive",
    "상회",
    "강세",
    "상향",
    "개선",
    "성장",
}


NEGATIVE_SIGNAL_WORDS = {
    "below",
    "miss",
    "misses",
    "cut",
    "lowered",
    "weak",
    "decelerate",
    "decline",
    "pressure",
    "negative",
    "risk",
    "하회",
    "약세",
    "하향",
    "둔화",
    "악화",
    "압박",
}


def text_has_any(text: str, words: set[str]) -> bool:
    lowered = text.lower()
    return any(word.lower() in lowered for word in words)
