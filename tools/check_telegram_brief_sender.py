"""Check telegram_brief_sender_v1 payload rendering without sending."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.portfolio_change_detection import detect_portfolio_changes  # noqa: E402
from research_os.telegram_brief_sender import DESIGN_NAME, build_telegram_brief_payload  # noqa: E402


def sample_previous() -> dict:
    return {
        "brief_type": "portfolio_health",
        "channel": "portfolio",
        "created_at": "2026-06-17T08:00:00+09:00",
        "content": {
            "total_score": 6.4,
            "holdings": [
                {"ticker": "PL", "company": "Planet Labs", "stance": "neutral", "confidence": 0.54, "score": 6.0},
                {"ticker": "JOBY", "company": "Joby Aviation", "stance": "positive", "confidence": 0.72, "score": 7.2},
                {"ticker": "INTC", "company": "Intel", "stance": "neutral", "confidence": 0.44, "score": 5.7},
            ],
        },
    }


def sample_current() -> dict:
    return {
        "brief_type": "portfolio_health",
        "channel": "portfolio",
        "created_at": "2026-06-18T08:00:00+09:00",
        "content": {
            "health": {"total_score": 6.9},
            "holdings": [
                {"ticker": "PL", "company": "Planet Labs", "stance": "positive", "confidence": 0.78, "score": 7.1},
                {"ticker": "JOBY", "company": "Joby Aviation", "stance": "risk", "confidence": 0.58, "score": 6.4},
                {"ticker": "ABSI", "company": "Absci", "stance": "positive", "confidence": 0.62, "score": 6.8},
            ],
        },
    }


def read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"JSON object expected: {path}")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Telegram portfolio brief payload를 dry-run으로 점검합니다.")
    parser.add_argument("--change-json", type=Path, help="portfolio_change_detection_v1 결과 JSON")
    parser.add_argument("--output-json", type=Path, help="Telegram payload 결과 저장")
    parser.add_argument("--chat-id", default="", help="실제 전송 없이 payload에 넣을 chat id")
    parser.add_argument("--max-message-chars", type=int, default=3600)
    args = parser.parse_args()

    change_result = read_json(args.change_json) if args.change_json else detect_portfolio_changes(sample_previous(), sample_current())
    payload = build_telegram_brief_payload(
        change_result,
        chat_id=args.chat_id,
        max_message_chars=args.max_message_chars,
    )
    if args.output_json:
        output_path = args.output_json if args.output_json.is_absolute() else PROJECT_ROOT / args.output_json
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[{payload.get('status')}] {DESIGN_NAME}")
    print(f"- chat_id_configured: {payload.get('chat_id_configured')}")
    print(f"- message_count: {payload.get('message_count')}")
    text = str(payload.get("text") or "")
    print(f"- text_chars: {len(text)}")
    for marker in ["Portfolio Health", "Top Movers", "Watch Items"]:
        print(f"- contains_{marker.replace(' ', '_').lower()}: {marker in text}")
    return 0 if payload.get("status") == "success" and text else 1


if __name__ == "__main__":
    raise SystemExit(main())
