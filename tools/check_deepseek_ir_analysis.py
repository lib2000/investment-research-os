"""Check DeepSeek IR analysis payload generation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.deepseek_ir_analysis import (  # noqa: E402
    ANALYSIS_TYPE,
    DESIGN_NAME,
    SOURCE_PLATFORM,
    build_deepseek_ir_analysis_batch_result,
)
from research_os.firecrawl_ir_collector import build_firecrawl_ir_signal_payload  # noqa: E402


def sample_items() -> list[dict]:
    signal = build_firecrawl_ir_signal_payload(
        {
            "company": "Planet Labs",
            "ticker": "PL",
            "raw_url": "https://investors.planet.com/",
            "page_title": "Planet Labs Investor Relations",
            "markdown": "Investor relations page with SEC filings and shareholder materials.",
        }
    )
    return [
        {
            "signal": signal,
            "analysis": {
                "stance": "positive",
                "score": 7.4,
                "confidence": 0.82,
                "summary": "Recent IR material supports a constructive but execution-sensitive view.",
                "key_points": ["IR source captured", "Earnings and filings available"],
                "risks": ["Execution risk"],
                "catalysts": ["Upcoming earnings update"],
            },
        }
    ]


def read_items(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("items") or data.get("analyses") or []
    if not isinstance(data, list):
        raise SystemExit(f"JSON list or wrapper expected: {path}")
    return [item for item in data if isinstance(item, dict)]


def main() -> int:
    parser = argparse.ArgumentParser(description="DeepSeek IR signal_analyses payload 계약을 점검합니다.")
    parser.add_argument("--input-json", type=Path, help="signal/analysis item JSON")
    parser.add_argument("--output-json", type=Path, help="batch 결과 저장")
    parser.add_argument("--json", action="store_true", help="점검 결과를 JSON으로 출력합니다.")
    args = parser.parse_args()

    result = build_deepseek_ir_analysis_batch_result(read_items(args.input_json) if args.input_json else sample_items())
    if args.output_json:
        output_path = args.output_json if args.output_json.is_absolute() else PROJECT_ROOT / args.output_json
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("status") == "success" else 1

    print(f"[{result.get('status')}] {DESIGN_NAME}")
    print(f"- source_platform: {SOURCE_PLATFORM}")
    print(f"- analysis_type: {ANALYSIS_TYPE}")
    print(f"- item_count: {result.get('item_count')}")
    print(f"- valid_count: {result.get('valid_count')}")
    print(f"- failed_count: {result.get('failed_count')}")
    for item in result.get("results") or []:
        payload = item.get("payload") if isinstance(item, dict) else None
        if payload:
            print(
                f"- {item.get('index')}. valid | {payload.get('ticker')} "
                f"{payload.get('stance')} score={payload.get('score')} confidence={payload.get('confidence')}"
            )
        else:
            print(f"- {item.get('index')}. failed | {', '.join(item.get('errors') or [])}")
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
