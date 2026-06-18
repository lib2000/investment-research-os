"""Check the offline Market Signal Graph portfolio pipeline contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.market_signal_graph_pipeline_contract import (  # noqa: E402
    DESIGN_NAME,
    build_market_signal_graph_pipeline_contract,
)


def _read_list(path: Path, *, keys: tuple[str, ...]) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        for key in keys:
            value = data.get(key)
            if isinstance(value, list):
                data = value
                break
    if not isinstance(data, list):
        raise SystemExit(f"JSON list or wrapper expected: {path}")
    return [item for item in data if isinstance(item, dict)]


def _read_object(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"JSON object expected: {path}")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Market Signal Graph 포트폴리오 파이프라인 offline contract를 점검합니다.")
    parser.add_argument("--ir-input-json", type=Path, help="Firecrawl IR source/scrape item JSON")
    parser.add_argument("--firecrawl-earnings-input-json", type=Path, help="Firecrawl earnings item JSON")
    parser.add_argument("--earnings-input-json", type=Path, help="Earnings transcript item JSON")
    parser.add_argument("--sec-dart-signal-json", type=Path, help="SEC/DART 추가 signal item JSON")
    parser.add_argument("--previous-health-json", type=Path, help="이전 portfolio_health brief JSON")
    parser.add_argument("--current-as-of", default="2026-06-19T08:00:00+09:00")
    parser.add_argument("--telegram-chat-id", default="")
    parser.add_argument("--output-json", type=Path, help="contract 결과 저장")
    parser.add_argument("--json", action="store_true", help="전체 결과 JSON 출력")
    args = parser.parse_args()

    result = build_market_signal_graph_pipeline_contract(
        ir_inputs=_read_list(args.ir_input_json, keys=("items", "sources", "results", "payloads")) if args.ir_input_json else None,
        firecrawl_earnings_inputs=(
            _read_list(args.firecrawl_earnings_input_json, keys=("items", "sources", "results", "payloads", "earnings"))
            if args.firecrawl_earnings_input_json
            else None
        ),
        earnings_inputs=(
            _read_list(args.earnings_input_json, keys=("items", "sources", "results", "payloads", "transcripts"))
            if args.earnings_input_json
            else None
        ),
        sec_dart_signals=_read_list(args.sec_dart_signal_json, keys=("items", "signals")) if args.sec_dart_signal_json else None,
        previous_health_brief=_read_object(args.previous_health_json) if args.previous_health_json else None,
        current_as_of=args.current_as_of,
        telegram_chat_id=args.telegram_chat_id or None,
    )
    if args.output_json:
        output_path = args.output_json if args.output_json.is_absolute() else PROJECT_ROOT / args.output_json
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        summary = result.get("summary") if isinstance(result.get("summary"), dict) else {}
        counts = result.get("source_payload_counts") if isinstance(result.get("source_payload_counts"), dict) else {}
        print(f"[{result.get('status')}] {DESIGN_NAME}")
        print(f"- contracts: {', '.join(result.get('contracts') or [])}")
        print(
            "- source_payloads: "
            f"firecrawl_ir={counts.get('firecrawl_ir', 0)} "
            f"firecrawl_earnings={counts.get('firecrawl_earnings', 0)} "
            f"earnings_transcript={counts.get('earnings_transcript', 0)} "
            f"deepseek_ir_analysis={counts.get('deepseek_ir_analysis', 0)} "
            f"portfolio_briefs={counts.get('portfolio_briefs', 0)}"
        )
        print(f"- scored_signals: {summary.get('signal_count')} / tickers={summary.get('ticker_count')}")
        print(f"- portfolio_score: {summary.get('portfolio_score')}")
        print(f"- movers/watch: {summary.get('top_mover_count')} / {summary.get('watch_item_count')}")
        print(f"- telegram_messages: {summary.get('telegram_message_count')}")
        for error in result.get("errors") or []:
            print(f"- error: {error}")
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
