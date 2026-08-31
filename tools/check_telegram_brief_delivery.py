"""Check safe Telegram delivery and cleanup planning without sending by default."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
TOOLS_DIR = PROJECT_ROOT / "tools"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from check_telegram_brief_sender import (  # noqa: E402
    DEFAULT_COMPANY_IR_SOURCES,
    DEFAULT_MANIFEST,
    DEFAULT_PORTFOLIOS,
    DEFAULT_RECOMMENDATIONS_STORE,
    DEFAULT_REPORT_ALERT_STATE,
    default_telegram_chat_id,
    load_portfolio_report_alert_selection,
    load_latest_recommendations,
    sample_current,
    sample_previous,
)
from research_os.portfolio_change_detection import detect_portfolio_changes  # noqa: E402
from research_os.portfolio_report_alert import build_report_alert_payload, normalize_target_bot_username, state_after_plan  # noqa: E402
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


def default_report_target_bot() -> str:
    for name in ("TELEGRAM_REPORT_ALERT_TARGET_BOT_USERNAME", "TELEGRAM_BOT_USERNAME"):
        value = os.getenv(name, "").strip()
        if value:
            return normalize_target_bot_username(value)
    return normalize_target_bot_username("@lib20_bot")


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


def redacted_for_output(value):
    if isinstance(value, dict):
        output = {}
        for key, item in value.items():
            if key == "chat_id" and item:
                output[key] = "configured"
            else:
                output[key] = redacted_for_output(item)
        return output
    if isinstance(value, list):
        return [redacted_for_output(item) for item in value]
    return value


def state_with_last_plan(state: dict, result: dict) -> dict:
    clean_result = {key: value for key, value in result.items() if key not in {"updated_state"}}
    return {
        **state,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "last_delivery_plan": clean_result,
    }


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


def build_payload(
    chat_id: str,
    recommendations_path: Path,
    *,
    portfolio_report_alert: dict | None = None,
) -> dict:
    change_result = detect_portfolio_changes(sample_previous(), sample_current())
    return build_telegram_brief_payload(
        change_result,
        chat_id=chat_id,
        today_recommendations=load_latest_recommendations(recommendations_path),
        portfolio_report_alert=portfolio_report_alert,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Telegram 중요 브리프 발송/삭제 계획을 안전 기본값으로 점검합니다.")
    parser.add_argument("--json", action="store_true", help="점검 결과를 JSON으로 출력합니다.")
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE, help="발송 ledger 상태 파일")
    parser.add_argument("--recommendations-json", type=Path, default=DEFAULT_RECOMMENDATIONS_STORE)
    parser.add_argument("--portfolios-json", type=Path, default=DEFAULT_PORTFOLIOS)
    parser.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--company-ir-sources-json", type=Path, default=DEFAULT_COMPANY_IR_SOURCES)
    parser.add_argument("--report-alert-state-file", type=Path, default=DEFAULT_REPORT_ALERT_STATE)
    parser.add_argument("--report-alert-lookback-days", type=int, default=3)
    parser.add_argument("--report-alert-max-items", type=int, default=8)
    parser.add_argument("--skip-report-alerts", action="store_true", help="통합 브리프에서 보유 리포트 섹션을 제외합니다.")
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
    if args.sample_state:
        # Sample mode is an offline safety check.  It must stay non-operative
        # even when the caller's environment enables a real delivery schedule.
        enabled = False
        dry_run = True
        cleanup_enabled = False

    report_alert = None
    if not args.skip_report_alerts:
        report_alert = load_portfolio_report_alert_selection(
            portfolios_path=args.portfolios_json,
            manifest_path=args.manifest_json,
            company_ir_sources_path=args.company_ir_sources_json,
            state_path=args.report_alert_state_file,
            lookback_days=args.report_alert_lookback_days,
            max_items=args.report_alert_max_items,
        )
    payload = build_payload(effective_chat_id, args.recommendations_json, portfolio_report_alert=report_alert)
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
    result["portfolio_report_alert_count"] = payload.get("portfolio_report_alert_count", 0)
    result["report_alert_state_file"] = str(args.report_alert_state_file)

    if args.write_state and result.get("updated_state"):
        state_to_write = state_with_last_plan(result["updated_state"], result)
        write_json(args.state_file, state_to_write)
        result["updated_state"] = state_to_write
        result["state_written"] = True
    else:
        result["state_written"] = False

    if report_alert is not None:
        report_state = read_json(args.report_alert_state_file, {"sent_report_keys": []})
        report_payload = build_report_alert_payload(
            report_alert,
            chat_id=effective_chat_id,
            target_bot=default_report_target_bot(),
            max_items=args.report_alert_max_items,
        )
        report_delivered = bool(result.get("applied_send_count"))
        next_report_state = state_after_plan(report_state, report_payload, delivered=report_delivered)
        next_report_state["integrated_delivery"] = {
            "design": DESIGN_NAME,
            "source_message_type": "integrated_investment_brief",
            "delivered": report_delivered,
            "applied_send_count": result.get("applied_send_count"),
            "portfolio_report_alert_count": payload.get("portfolio_report_alert_count", 0),
            "telegram_brief_state_file": str(args.state_file),
        }
        if result.get("updated_state"):
            next_report_state["sent_messages"] = result["updated_state"].get("sent_messages") or []
        report_state_is_default = args.report_alert_state_file.resolve() == DEFAULT_REPORT_ALERT_STATE.resolve()
        delivery_state_is_default = args.state_file.resolve() == DEFAULT_STATE_FILE.resolve()
        should_write_report_state = args.write_state and (not report_state_is_default or delivery_state_is_default)
        if should_write_report_state:
            write_json(args.report_alert_state_file, next_report_state)
            result["report_alert_state_written"] = True
        else:
            result["report_alert_state_written"] = False
        result["report_alert_updated_state"] = redacted_for_output(next_report_state)
    else:
        result["report_alert_state_written"] = False

    if args.json:
        print(json.dumps(redacted_for_output(result), ensure_ascii=False, indent=2))
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
        print(f"- portfolio_report_alert_count: {result.get('portfolio_report_alert_count')}")
        print(f"- report_alert_state_written: {result.get('report_alert_state_written')}")
        for error in result.get("errors") or []:
            print(f"- error: {error}")
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
