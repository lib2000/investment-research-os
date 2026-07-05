"""Check safe Telegram delivery and cleanup planning without sending by default."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
TOOLS_DIR = PROJECT_ROOT / "tools"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from check_telegram_brief_sender import (  # noqa: E402
    DEFAULT_RECOMMENDATIONS_STORE,
    default_telegram_chat_id,
    load_latest_recommendations,
    sample_current,
    sample_previous,
)
from research_os.portfolio_change_detection import detect_portfolio_changes  # noqa: E402
from research_os.telegram_brief_delivery import DESIGN_NAME, execute_telegram_delivery  # noqa: E402
from research_os.telegram_brief_sender import build_telegram_brief_payload  # noqa: E402


DEFAULT_STATE_FILE = PROJECT_ROOT / "research_vault" / "_system" / "telegram_brief_delivery_state.json"


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y"}


def default_bot_token() -> tuple[str, str]:
    for name in ("MARKET_SIGNAL_GRAPH_TELEGRAM_BOT_TOKEN", "TELEGRAM_BOT_TOKEN"):
        value = os.getenv(name, "").strip()
        if value:
            return value, name
    return "", "none"


def read_json(path: Path, default):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    if not isinstance(data, dict):
        raise SystemExit(f"JSON object expected: {path}")
    return data


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def sample_state() -> dict:
    return {
        "sent_messages": [
            {
                "chat_id": "12345",
                "message_id": 101,
                "text": "Investment Priority Brief\nToday Recommendations\n- #1 ABSI",
                "sent_at": "2026-07-05T00:00:00+00:00",
            },
            {
                "chat_id": "12345",
                "message_id": 102,
                "text": "routine status ok: all checks passed",
                "category": "routine_status_ok",
                "sent_at": "2026-07-05T00:01:00+00:00",
            },
        ]
    }


def build_payload(chat_id: str, recommendations_path: Path) -> dict:
    change_result = detect_portfolio_changes(sample_previous(), sample_current())
    return build_telegram_brief_payload(
        change_result,
        chat_id=chat_id,
        today_recommendations=load_latest_recommendations(recommendations_path),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Telegram 중요 브리프 발송/삭제 계획을 안전 기본값으로 점검합니다.")
    parser.add_argument("--json", action="store_true", help="점검 결과를 JSON으로 출력합니다.")
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE, help="발송 ledger 상태 파일")
    parser.add_argument("--recommendations-json", type=Path, default=DEFAULT_RECOMMENDATIONS_STORE)
    parser.add_argument("--sample-state", action="store_true", help="삭제 후보/보호 메시지 샘플 상태로 점검합니다.")
    parser.add_argument("--enabled", action="store_true", help="전달 기능 enabled 플래그를 켭니다.")
    parser.add_argument("--submit", action="store_true", help="dry-run을 해제하고 실제 sendMessage/deleteMessage를 허용합니다.")
    parser.add_argument("--cleanup-enabled", action="store_true", help="저우선순위 메시지 삭제를 허용합니다.")
    parser.add_argument("--write-state", action="store_true", help="실행 후 상태 파일을 갱신합니다.")
    parser.add_argument("--chat-id", default=None, help="실제 전송 없이 payload에 넣을 chat id")
    parser.add_argument("--api-base-url", default=os.getenv("TELEGRAM_API_BASE_URL", "https://api.telegram.org"))
    parser.add_argument("--timeout-seconds", type=float, default=float(os.getenv("TELEGRAM_TIMEOUT_SECONDS", "10")))
    args = parser.parse_args()

    env_chat_id, chat_id_source = default_telegram_chat_id()
    bot_token, bot_token_source = default_bot_token()
    effective_chat_id = args.chat_id if args.chat_id is not None else env_chat_id
    enabled = bool(args.enabled or env_bool("TELEGRAM_BRIEF_DELIVERY_ENABLED", False))
    dry_run = not bool(args.submit) or env_bool("TELEGRAM_BRIEF_DELIVERY_DRY_RUN", True)
    if args.submit:
        dry_run = False
    cleanup_enabled = bool(args.cleanup_enabled or env_bool("TELEGRAM_BRIEF_CLEANUP_ENABLED", False))

    payload = build_payload(effective_chat_id, args.recommendations_json)
    state = sample_state() if args.sample_state else read_json(args.state_file, {"sent_messages": []})
    result = execute_telegram_delivery(
        payload,
        state=state,
        enabled=enabled,
        dry_run=dry_run,
        cleanup_enabled=cleanup_enabled,
        bot_token=bot_token,
        api_base_url=args.api_base_url,
        timeout_seconds=args.timeout_seconds,
    )
    result["chat_id_source"] = "cli" if args.chat_id is not None and args.chat_id else chat_id_source
    result["bot_token_source"] = bot_token_source if bot_token else "none"
    result["state_file"] = str(args.state_file)

    if args.write_state and result.get("updated_state"):
        write_json(args.state_file, result["updated_state"])
        result["state_written"] = True
    else:
        result["state_written"] = False

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"[{result.get('status')}] {DESIGN_NAME}")
        print(f"- enabled: {result.get('enabled')}")
        print(f"- dry_run: {result.get('dry_run')}")
        print(f"- cleanup_enabled: {result.get('cleanup_enabled')}")
        print(f"- bot_token_configured: {result.get('bot_token_configured')}")
        print(f"- chat_id_source: {result.get('chat_id_source')}")
        print(f"- planned_send_count: {result.get('planned_send_count')}")
        print(f"- delete_candidate_count: {result.get('delete_candidate_count')}")
        print(f"- protected_message_count: {result.get('protected_message_count')}")
        print(f"- applied_send_count: {result.get('applied_send_count')}")
        print(f"- applied_delete_count: {result.get('applied_delete_count')}")
        for error in result.get("errors") or []:
            print(f"- error: {error}")
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
