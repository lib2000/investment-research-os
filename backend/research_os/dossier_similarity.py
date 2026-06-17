"""Dossier content fingerprint and token similarity helpers."""

from __future__ import annotations

import hashlib
from re import sub


def content_fingerprint(text: str | None) -> str:
    normalized = " ".join(str(text or "").lower().split())
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def similarity_tokens(text: str | None) -> set[str]:
    normalized = sub(r"[^0-9a-zA-Z가-힣]+", " ", str(text or "").lower())
    tokens = {
        token
        for token in normalized.split()
        if len(token) >= 2 and token not in {"the", "and", "for", "with", "from", "this", "that"}
    }
    return tokens


def token_jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / max(1, len(left | right))