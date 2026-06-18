"""Check portfolio brief payload generation for Market Signal Graph."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.deepseek_ir_analysis import build_deepseek_ir_analysis_batch_result  # noqa: E402
from research_os.firecrawl_ir_collector import build_firecrawl_ir_signal_payload  # noqa: E402
from research_os.portfolio_brief_contract import DESIGN_NAME, build_portfolio_brief_batch_result  # noqa: E402
from research_os.portfolio_signal_score import build_portfolio_signal_scores  # noqa: E402


def sample_analysis_payloads() -> list[dict]:
    signal = build_firecrawl_ir_signal_payload(
        {
            "company": "Planet Labs",
            "ticker": "PL",
            "raw_url": "https://investors.planet.com/",
            "page_title": "Planet Labs Investor Relations",
            "markdown": "IR material",
        }
    )
    batch = build_deepseek_ir_analysis_batch_result(
        [
            {
                "signal": signal,
                "analysis": {
                    "stance": "positive",
                    "score": 7.4,
                    "confidence": 0.82,
                    "summary": "Constructive IR read-through.",
                },
            }
        ]
    )
    return [item["payload"] for item in batch["results"] if item.get("payload")]


def read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"JSON object expected: {path}")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Portfolio IR/Health brief payload 계약을 점검합니다.")
    parser.add_argument("--score-json", type=Path, help="portfolio_signal_score_v1 결과 JSON")
    parser.add_argument("--analysis-json", type=Path, help="DeepSeek analysis payload list/wrapper JSON")
    parser.add_argument("--as-of", default="2026-06-19T08:00:00+09:00")
    parser.add_argument("--output-json", type=Path, help="brief batch 결과 저장")
    args = parser.parse_args()

    if args.analysis_json:
        data = json.loads(args.analysis_json.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("items") or data.get("analyses") or data.get("results") or []
        analysis_payloads = [item.get("payload", item) for item in data if isinstance(item, dict)]
    else:
        analysis_payloads = sample_analysis_payloads()
    if args.score_json:
        score_result = read_json(args.score_json)
    else:
        score_result = build_portfolio_signal_scores(analysis_payloads)
    result = build_portfolio_brief_batch_result(
        analysis_payloads=analysis_payloads,
        score_result=score_result,
        as_of=args.as_of,
    )
    if args.output_json:
        output_path = args.output_json if args.output_json.is_absolute() else PROJECT_ROOT / args.output_json
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[{result.get('status')}] {DESIGN_NAME}")
    print(f"- brief_count: {result.get('brief_count')}")
    print(f"- brief_types: {', '.join(result.get('brief_types') or [])}")
    for brief in result.get("briefs") or []:
        content = brief.get("content") if isinstance(brief.get("content"), dict) else {}
        print(f"- {brief.get('brief_type')} | channel={brief.get('channel')} | items={len(content.get('items') or content.get('holdings') or [])}")
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
