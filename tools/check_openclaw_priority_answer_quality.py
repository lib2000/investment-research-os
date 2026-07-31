from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from workspace_paths import openclaw_investment_dir

DEFAULT_OPENCLAW_DIR = openclaw_investment_dir()
FIRST_READ_JSON_FILE = "openclaw_first_read.json"
EXPECTED_MARKET_COUNTS = {"KR": 3, "US": 3}
BANNED_ANSWER_FRAGMENTS = [
    "추천 없음",
    "중요 메시지 없음",
    "자료가 없습니다",
    "확인할 수 없습니다",
]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise AssertionError(f"required file not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise AssertionError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise AssertionError(f"JSON root must be an object: {path}")
    return payload


def recommendation_label(row: dict[str, Any]) -> str:
    market = row.get("market") or "?"
    rank = row.get("rank") or "?"
    ticker = row.get("ticker") or ""
    company = row.get("company_name") or ticker
    score = row.get("score")
    baseline = row.get("baseline_price")
    currency = row.get("currency") or ""
    return f"{market}#{rank} {ticker} {company} score={score} baseline={baseline} {currency}".strip()


def recommendation_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("latest_recommendations")
    if not isinstance(rows, list):
        raise AssertionError("latest_recommendations must be a list")
    clean_rows = [row for row in rows if isinstance(row, dict)]
    if len(clean_rows) < sum(EXPECTED_MARKET_COUNTS.values()):
        raise AssertionError("latest_recommendations must include KR/US top 3")
    counts = Counter(str(row.get("market") or "") for row in clean_rows)
    for market, expected in EXPECTED_MARKET_COUNTS.items():
        if counts.get(market, 0) < expected:
            raise AssertionError(f"latest_recommendations missing {market} top {expected}: {dict(counts)}")
    return sorted(clean_rows, key=lambda row: (str(row.get("market") or ""), int(row.get("rank") or 999)))


def build_expected_answer(payload: dict[str, Any]) -> str:
    rows = recommendation_rows(payload)
    telegram = payload.get("telegram") if isinstance(payload.get("telegram"), dict) else {}
    favorite_message_count = int(
        telegram.get("favorite_saved_count")
        or telegram.get("favorite_candidate_count")
        or telegram.get("favorite_top_post_count")
        or 0
    )
    lines = [
        "오늘 추천 종목",
        f"- 기준 파일: openclaw_first_read.json / bridge_status.json",
    ]
    for row in rows:
        lines.append(f"- {recommendation_label(row)}")
    lines.extend(
        [
            "",
            "중요 메시지",
            f"- 텔레그램 즐겨찾기 수집: {favorite_message_count}건",
            f"- 우선 브리프: {telegram.get('priority_brief_design') or 'n/a'}",
            f"- 전달 정책: {telegram.get('priority_delivery_design') or 'n/a'}",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def validate_answer_quality(payload: dict[str, Any], answer: str) -> list[str]:
    errors: list[str] = []
    rows = recommendation_rows(payload)
    telegram = payload.get("telegram") if isinstance(payload.get("telegram"), dict) else {}
    favorite_saved_count = int(telegram.get("favorite_saved_count") or 0)
    favorite_candidate_count = int(telegram.get("favorite_candidate_count") or 0)
    favorite_top_post_count = int(telegram.get("favorite_top_post_count") or 0)
    favorite_message_count = favorite_saved_count or favorite_candidate_count or favorite_top_post_count
    if favorite_message_count <= 0:
        errors.append("telegram favorite message count must be positive")

    for banned in BANNED_ANSWER_FRAGMENTS:
        if banned in answer:
            errors.append(f"answer contains banned fragment: {banned}")

    required_fragments = ["오늘 추천 종목", "중요 메시지", "openclaw_first_read.json"]
    if favorite_message_count:
        required_fragments.append(str(favorite_message_count))
    for row in rows:
        for key in ("market", "rank", "ticker", "company_name"):
            value = row.get(key)
            if value is not None:
                required_fragments.append(str(value))
    for fragment in required_fragments:
        if fragment and fragment not in answer:
            errors.append(f"answer missing required fragment: {fragment}")

    if errors:
        raise AssertionError("; ".join(errors))
    counts = Counter(str(row.get("market") or "") for row in rows)
    return [
        f"recommendation_count={len(rows)}",
        f"kr_count={counts.get('KR', 0)}",
        f"us_count={counts.get('US', 0)}",
        f"telegram_saved_count={favorite_saved_count}",
        f"telegram_candidate_count={favorite_candidate_count}",
        "banned_priority_answer_fragments_absent=true",
    ]


def build_result(openclaw_dir: Path = DEFAULT_OPENCLAW_DIR, answer_file: Path | None = None) -> dict[str, Any]:
    payload = load_json(openclaw_dir / FIRST_READ_JSON_FILE)
    answer = answer_file.read_text(encoding="utf-8-sig") if answer_file else build_expected_answer(payload)
    messages = validate_answer_quality(payload, answer)
    rows = recommendation_rows(payload)
    telegram = payload.get("telegram") if isinstance(payload.get("telegram"), dict) else {}
    return {
        "status": "ok",
        "openclaw_dir": str(openclaw_dir),
        "answer_source": str(answer_file) if answer_file else "generated_expected_answer",
        "generated_at": payload.get("generated_at"),
        "latest_recommendation_date": payload.get("latest_recommendation_date"),
        "recommendation_count": len(rows),
        "latest_market_counts": dict(Counter(str(row.get("market") or "") for row in rows)),
        "telegram_saved_count": telegram.get("favorite_saved_count"),
        "telegram_candidate_count": telegram.get("favorite_candidate_count"),
        "messages": messages,
        "answer_preview": answer[:1600],
    }


def render_text(result: dict[str, Any]) -> str:
    lines = [
        f"OpenClaw priority-answer quality: {result.get('status')}",
        f"- openclaw_dir: {result.get('openclaw_dir')}",
        f"- answer_source: {result.get('answer_source')}",
        f"- latest_recommendation_date: {result.get('latest_recommendation_date')}",
        f"- recommendation_count: {result.get('recommendation_count')}",
        f"- latest_market_counts: {json.dumps(result.get('latest_market_counts') or {}, ensure_ascii=False, separators=(',', ':'))}",
        f"- telegram_saved_count: {result.get('telegram_saved_count')}",
        f"- telegram_candidate_count: {result.get('telegram_candidate_count')}",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test OpenClaw's recommendation and important-message answer quality.")
    parser.add_argument("--openclaw-dir", type=Path, default=DEFAULT_OPENCLAW_DIR)
    parser.add_argument("--answer-file", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        result = build_result(args.openclaw_dir.resolve(), args.answer_file.resolve() if args.answer_file else None)
    except AssertionError as exc:
        result = {"status": "failure", "errors": [str(exc)], "openclaw_dir": str(args.openclaw_dir.resolve())}
        if args.answer_file:
            result["answer_source"] = str(args.answer_file.resolve())
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"OpenClaw priority-answer quality: failure\n- error: {exc}")
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
