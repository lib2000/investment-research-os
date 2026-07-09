"""Check telegram_brief_sender_v1 payload rendering without sending."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.portfolio_change_detection import detect_portfolio_changes  # noqa: E402
from research_os.portfolio_report_alert import select_new_holding_reports  # noqa: E402
from research_os.telegram_brief_sender import DESIGN_NAME, build_telegram_brief_payload  # noqa: E402


DEFAULT_RECOMMENDATIONS_STORE = PROJECT_ROOT / "research_vault" / "_system" / "daily_recommendations.json"
DEFAULT_PORTFOLIOS = PROJECT_ROOT / "research_vault" / "_system" / "user_portfolios.json"
DEFAULT_MANIFEST = PROJECT_ROOT / "research_vault" / "manifest.json"
DEFAULT_COMPANY_IR_SOURCES = PROJECT_ROOT / "research_vault" / "_system" / "company_ir_sources_watch.json"
DEFAULT_REPORT_ALERT_STATE = PROJECT_ROOT / "research_vault" / "_system" / "portfolio_report_alert_state.json"


def default_telegram_chat_id() -> tuple[str, str]:
    for name in ("MARKET_SIGNAL_GRAPH_TELEGRAM_CHAT_ID", "TELEGRAM_CHAT_ID"):
        value = os.getenv(name, "").strip()
        if value:
            return value, name
    return "", "none"


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


def sample_today_recommendations() -> list[dict]:
    return [
        {
            "recommendation_date": "2026-07-05",
            "market": "KR",
            "market_label": "Korea",
            "rank": 1,
            "ticker": "361610",
            "company_name": "SKIET",
            "score": 139,
            "baseline_price": 17800,
            "currency": "KRW",
        },
        {
            "recommendation_date": "2026-07-05",
            "market": "US",
            "market_label": "US",
            "rank": 1,
            "ticker": "OTLY",
            "company_name": "Oatly Group AB",
            "score": 176,
            "baseline_price": 8.19,
            "currency": "USD",
        },
    ]


def sample_report_alert() -> dict:
    return {
        "design": "portfolio_report_alert_v1",
        "status": "success",
        "as_of": "2026-07-05",
        "holding_count": 2,
        "candidate_count": 1,
        "reports": [
            {
                "ticker": "ABSI",
                "holding_name": "Absci Corporation",
                "title": "Absci earnings report",
                "published_at": "2026-07-05",
                "source_provider": "Firecrawl IR",
                "report_key": "sample-absi-report",
            }
        ],
    }


def read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"JSON object expected: {path}")
    return data


def read_json_value(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def redact_payload_for_diagnostics(payload: dict) -> dict:
    redacted = json.loads(json.dumps(payload, ensure_ascii=False))
    for message in redacted.get("messages") or []:
        if isinstance(message, dict) and message.get("chat_id"):
            message["chat_id"] = "configured"
    return redacted


def latest_recommendations(store: dict) -> list[dict]:
    records = [item for item in store.get("records") or [] if isinstance(item, dict)]
    if not records:
        return []
    latest_date = str(store.get("latest_recommendation_date") or "").strip()
    if not latest_date:
        latest_date = max(str(item.get("recommendation_date") or "") for item in records)
    latest = [item for item in records if str(item.get("recommendation_date") or "") == latest_date]

    def sort_key(item: dict) -> tuple[str, int, str]:
        try:
            rank = int(item.get("rank") or 999)
        except (TypeError, ValueError):
            rank = 999
        return str(item.get("market") or ""), rank, str(item.get("ticker") or "")

    return sorted(latest, key=sort_key)


def load_latest_recommendations(path: Path | None) -> list[dict]:
    if path and path.exists():
        return latest_recommendations(read_json(path))
    return sample_today_recommendations()


def load_portfolio_report_alert_selection(
    *,
    portfolios_path: Path,
    manifest_path: Path,
    company_ir_sources_path: Path,
    state_path: Path,
    as_of: date | None = None,
    lookback_days: int = 3,
    max_items: int = 8,
    include_sample_if_missing: bool = False,
) -> dict:
    files_exist = portfolios_path.exists() or manifest_path.exists() or company_ir_sources_path.exists()
    if include_sample_if_missing and not files_exist:
        return sample_report_alert()
    state = read_json_value(state_path, {"sent_report_keys": []})
    if not isinstance(state, dict):
        state = {"sent_report_keys": []}
    selection = select_new_holding_reports(
        portfolios=read_json_value(portfolios_path, {"portfolios": {}}),
        manifest=read_json_value(manifest_path, []),
        company_ir_sources=read_json_value(company_ir_sources_path, {"items": []}),
        state=state,
        today=as_of or date.today(),
        lookback_days=lookback_days,
        max_items=max_items,
    )
    selection["as_of"] = (as_of or date.today()).isoformat()
    return selection


def main() -> int:
    parser = argparse.ArgumentParser(description="Telegram portfolio brief payload를 dry-run으로 점검합니다.")
    parser.add_argument("--change-json", type=Path, help="portfolio_change_detection_v1 결과 JSON")
    parser.add_argument("--output-json", type=Path, help="Telegram payload 결과 저장")
    parser.add_argument(
        "--recommendations-json",
        type=Path,
        default=DEFAULT_RECOMMENDATIONS_STORE,
        help="daily_recommendations.json 경로. 없으면 샘플 추천으로 dry-run합니다.",
    )
    parser.add_argument("--chat-id", default=None, help="실제 전송 없이 payload에 넣을 chat id")
    parser.add_argument("--max-message-chars", type=int, default=3600)
    parser.add_argument("--portfolios-json", type=Path, default=DEFAULT_PORTFOLIOS)
    parser.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--company-ir-sources-json", type=Path, default=DEFAULT_COMPANY_IR_SOURCES)
    parser.add_argument("--report-alert-state-file", type=Path, default=DEFAULT_REPORT_ALERT_STATE)
    parser.add_argument("--report-alert-lookback-days", type=int, default=3)
    parser.add_argument("--report-alert-max-items", type=int, default=8)
    parser.add_argument("--skip-report-alerts", action="store_true", help="통합 브리프에서 보유 리포트 섹션을 제외합니다.")
    parser.add_argument("--json", action="store_true", help="점검 결과를 JSON으로 출력합니다.")
    args = parser.parse_args()

    env_chat_id, env_chat_source = default_telegram_chat_id()
    effective_chat_id = args.chat_id if args.chat_id is not None else env_chat_id
    chat_id_source = "cli" if args.chat_id is not None and args.chat_id else env_chat_source
    change_result = read_json(args.change_json) if args.change_json else detect_portfolio_changes(sample_previous(), sample_current())
    today_recommendations = load_latest_recommendations(args.recommendations_json)
    report_alert = None
    if not args.skip_report_alerts:
        report_alert = load_portfolio_report_alert_selection(
            portfolios_path=args.portfolios_json,
            manifest_path=args.manifest_json,
            company_ir_sources_path=args.company_ir_sources_json,
            state_path=args.report_alert_state_file,
            lookback_days=args.report_alert_lookback_days,
            max_items=args.report_alert_max_items,
            include_sample_if_missing=True,
        )
    payload = build_telegram_brief_payload(
        change_result,
        chat_id=effective_chat_id,
        max_message_chars=args.max_message_chars,
        today_recommendations=today_recommendations,
        portfolio_report_alert=report_alert,
    )
    diagnostic_payload = redact_payload_for_diagnostics(payload)
    if args.output_json:
        output_path = args.output_json if args.output_json.is_absolute() else PROJECT_ROOT / args.output_json
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(diagnostic_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(diagnostic_payload, ensure_ascii=False, indent=2))
        return 0 if payload.get("status") == "success" and payload.get("text") else 1

    print(f"[{payload.get('status')}] {DESIGN_NAME}")
    print(f"- chat_id_configured: {payload.get('chat_id_configured')}")
    print(f"- chat_id_source: {chat_id_source}")
    print(f"- message_count: {payload.get('message_count')}")
    text = str(payload.get("text") or "")
    print(f"- text_chars: {len(text)}")
    print(f"- today_recommendation_count: {payload.get('today_recommendation_count')}")
    print(f"- portfolio_report_alert_count: {payload.get('portfolio_report_alert_count')}")
    priority_filter = payload.get("priority_filter") if isinstance(payload.get("priority_filter"), dict) else {}
    print(f"- priority_filter_mode: {priority_filter.get('mode')}")
    print(f"- suppressed_low_priority_count: {priority_filter.get('suppressed_low_priority_count')}")
    for marker in ["Investment Priority Brief", "Today Recommendations", "Holding Reports", "Portfolio Health", "Top Movers", "Watch Items"]:
        print(f"- contains_{marker.replace(' ', '_').lower()}: {marker in text}")
    return 0 if payload.get("status") == "success" and text else 1


if __name__ == "__main__":
    raise SystemExit(main())
