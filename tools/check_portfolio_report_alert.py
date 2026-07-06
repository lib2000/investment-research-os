"""Build and optionally deliver a 07:00 Telegram alert for new holding reports."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.portfolio_report_alert import (  # noqa: E402
    DESIGN_NAME,
    build_report_alert_payload,
    normalize_target_bot_username,
    select_new_holding_reports,
    state_after_plan,
)
from research_os.telegram_brief_delivery import execute_telegram_delivery  # noqa: E402


DEFAULT_PORTFOLIOS = PROJECT_ROOT / "research_vault" / "_system" / "user_portfolios.json"
DEFAULT_MANIFEST = PROJECT_ROOT / "research_vault" / "manifest.json"
DEFAULT_COMPANY_IR_SOURCES = PROJECT_ROOT / "research_vault" / "_system" / "company_ir_sources_watch.json"
DEFAULT_STATE_FILE = PROJECT_ROOT / "research_vault" / "_system" / "portfolio_report_alert_state.json"


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y"}


def default_bot_token() -> tuple[str, str]:
    for name in (
        "TELEGRAM_REPORT_ALERT_BOT_TOKEN",
        "MARKET_SIGNAL_GRAPH_TELEGRAM_BOT_TOKEN",
        "TELEGRAM_BOT_TOKEN",
    ):
        value = os.getenv(name, "").strip()
        if value:
            return value, name
    return "", "none"


def default_chat_id() -> tuple[str, str]:
    for name in (
        "TELEGRAM_REPORT_ALERT_CHAT_ID",
        "MARKET_SIGNAL_GRAPH_TELEGRAM_CHAT_ID",
        "TELEGRAM_CHAT_ID",
    ):
        value = os.getenv(name, "").strip()
        if value:
            return value, name
    return "", "none"


def persisted_windows_env(name: str) -> str:
    try:
        command = (
            "[Environment]::GetEnvironmentVariable('{0}', 'User');"
            "[Environment]::GetEnvironmentVariable('{0}', 'Machine')"
        ).format(name)
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", command],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return ""
    if completed.returncode != 0:
        return ""
    for line in (completed.stdout or "").splitlines():
        value = line.strip()
        if value:
            return value
    return ""


def default_target_bot() -> tuple[str, str]:
    for name in ("TELEGRAM_REPORT_ALERT_TARGET_BOT_USERNAME", "TELEGRAM_BOT_USERNAME"):
        value = os.getenv(name, "").strip()
        if value:
            return normalize_target_bot_username(value), name
        persisted = persisted_windows_env(name)
        if persisted:
            return normalize_target_bot_username(persisted), f"{name}:windows"
    return normalize_target_bot_username("@lib20_bot"), "default"


def read_json(path: Path, default: Any) -> Any:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    if not isinstance(data, (dict, list)):
        raise SystemExit(f"JSON object/list expected: {path}")
    return data


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def redacted_for_output(value: Any) -> Any:
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for key, item in value.items():
            if key == "chat_id" and item:
                output[key] = "configured"
            else:
                output[key] = redacted_for_output(item)
        return output
    if isinstance(value, list):
        return [redacted_for_output(item) for item in value]
    return value


def build_result(args: argparse.Namespace) -> dict[str, Any]:
    env_chat_id, chat_id_source = default_chat_id()
    bot_token, bot_token_source = default_bot_token()
    target_bot, target_bot_source = default_target_bot()
    effective_chat_id = args.chat_id if args.chat_id is not None else env_chat_id
    enabled = bool(args.enabled or env_bool("TELEGRAM_REPORT_ALERT_ENABLED", False))
    dry_run = True
    if args.submit:
        dry_run = False
    elif not env_bool("TELEGRAM_REPORT_ALERT_DRY_RUN", True):
        dry_run = False

    state = read_json(args.state_file, {"sent_report_keys": []})
    if not isinstance(state, dict):
        raise SystemExit(f"state JSON object expected: {args.state_file}")
    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    selection = select_new_holding_reports(
        portfolios=read_json(args.portfolios_json, {"portfolios": {}}),
        manifest=read_json(args.manifest_json, []),
        company_ir_sources=read_json(args.company_ir_sources_json, {"items": []}),
        state=state,
        today=as_of,
        lookback_days=args.lookback_days,
        max_items=args.max_items,
        include_previously_sent=args.include_previously_sent,
    )
    selection["as_of"] = as_of.isoformat()
    payload = build_report_alert_payload(
        selection,
        chat_id=effective_chat_id,
        target_bot=target_bot,
        max_message_chars=args.max_message_chars,
        max_items=args.max_items,
        send_empty=args.send_empty,
    )
    delivery = execute_telegram_delivery(
        payload,
        state={"sent_messages": state.get("sent_messages") or []},
        enabled=enabled,
        dry_run=dry_run,
        cleanup_enabled=False,
        bot_token=bot_token,
        api_base_url=args.api_base_url,
        timeout_seconds=args.timeout_seconds,
    )
    delivered = bool(delivery.get("applied_send_count"))
    next_state = state_after_plan(state, payload, delivered=delivered)
    if delivery.get("updated_state"):
        next_state["sent_messages"] = delivery["updated_state"].get("sent_messages") or []
    result = {
        "design": DESIGN_NAME,
        "status": "success" if delivery.get("status") == "success" else "failure",
        "errors": delivery.get("errors") or [],
        "target_bot": target_bot,
        "target_bot_source": target_bot_source,
        "send_time": "07:00",
        "enabled": enabled,
        "dry_run": dry_run,
        "bot_token_configured": bool(bot_token),
        "bot_token_source": bot_token_source if bot_token else "none",
        "chat_id_configured": bool(effective_chat_id),
        "chat_id_source": "cli" if args.chat_id is not None and args.chat_id else chat_id_source,
        "state_file": str(args.state_file),
        "selection": selection,
        "payload": redacted_for_output(payload),
        "delivery": redacted_for_output({key: value for key, value in delivery.items() if key != "updated_state"}),
        "updated_state": redacted_for_output(next_state),
    }
    if args.output_json:
        output_path = args.output_json if args.output_json.is_absolute() else PROJECT_ROOT / args.output_json
        write_json(output_path, result)
        result["output_json"] = str(output_path)
    if args.write_state:
        write_json(args.state_file, next_state)
        result["state_written"] = True
    else:
        result["state_written"] = False
    return result


def render_text(result: dict[str, Any]) -> str:
    selection = result.get("selection") if isinstance(result.get("selection"), dict) else {}
    payload = result.get("payload") if isinstance(result.get("payload"), dict) else {}
    delivery = result.get("delivery") if isinstance(result.get("delivery"), dict) else {}
    lines = [
        f"[{result.get('status')}] {DESIGN_NAME}",
        f"- target_bot: {result.get('target_bot')}",
        f"- send_time: {result.get('send_time')}",
        f"- enabled: {result.get('enabled')}",
        f"- dry_run: {result.get('dry_run')}",
        f"- bot_token_configured: {result.get('bot_token_configured')}",
        f"- chat_id_configured: {result.get('chat_id_configured')} ({result.get('chat_id_source')})",
        f"- holding_count: {selection.get('holding_count')}",
        f"- candidate_count: {selection.get('candidate_count')}",
        f"- message_count: {payload.get('message_count')}",
        f"- applied_send_count: {delivery.get('applied_send_count')}",
        f"- state_written: {result.get('state_written')}",
    ]
    for error in result.get("errors") or []:
        lines.append(f"- error: {error}")
    text = str(payload.get("text") or "")
    if text:
        lines.extend(["", text])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenClaw 보유 종목 신규 리포트 텔레그램 07:00 알림을 점검/전송합니다.")
    parser.add_argument("--portfolios-json", type=Path, default=DEFAULT_PORTFOLIOS)
    parser.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--company-ir-sources-json", type=Path, default=DEFAULT_COMPANY_IR_SOURCES)
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--as-of", help="YYYY-MM-DD 기준일. 기본값은 오늘")
    parser.add_argument("--lookback-days", type=int, default=int(os.getenv("TELEGRAM_REPORT_ALERT_LOOKBACK_DAYS", "3")))
    parser.add_argument("--max-items", type=int, default=int(os.getenv("TELEGRAM_REPORT_ALERT_MAX_ITEMS", "8")))
    parser.add_argument("--max-message-chars", type=int, default=int(os.getenv("TELEGRAM_REPORT_ALERT_MAX_MESSAGE_CHARS", "3600")))
    parser.add_argument("--chat-id", default=None)
    parser.add_argument("--enabled", action="store_true")
    parser.add_argument("--submit", action="store_true")
    parser.add_argument("--send-empty", action="store_true")
    parser.add_argument("--include-previously-sent", action="store_true")
    parser.add_argument("--write-state", action="store_true")
    parser.add_argument("--api-base-url", default=os.getenv("TELEGRAM_API_BASE_URL", "https://api.telegram.org"))
    parser.add_argument("--timeout-seconds", type=float, default=float(os.getenv("TELEGRAM_TIMEOUT_SECONDS", "10")))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = build_result(args)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
