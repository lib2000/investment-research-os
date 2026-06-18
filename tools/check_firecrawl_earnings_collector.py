"""Check firecrawl_earnings_collector_v1 payload generation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.firecrawl_earnings_collector import (  # noqa: E402
    DESIGN_NAME,
    build_firecrawl_earnings_batch_result,
    normalize_firecrawl_earnings_inputs,
)


SAMPLE = [
    {
        "company": "Planet Labs",
        "ticker": "PL",
        "raw_url": "https://investors.planet.com/events-and-presentations/",
        "title": "Planet Labs Q1 FY2027 earnings release",
        "fiscal_period": "Q1 FY2027",
        "event_date": "2026-06-04",
        "markdown": "Revenue growth, customer retention, and margin discipline were reported.",
    }
]


def read_items(path: Path) -> list[dict]:
    return normalize_firecrawl_earnings_inputs(json.loads(path.read_text(encoding="utf-8")))


def main() -> int:
    parser = argparse.ArgumentParser(description="Firecrawl earnings Market Signal Graph payload 계약을 점검합니다.")
    parser.add_argument("--input-json", type=Path, help="Firecrawl earnings item/list JSON")
    parser.add_argument("--output-json", type=Path, help="batch 결과 저장")
    args = parser.parse_args()

    items = read_items(args.input_json) if args.input_json else SAMPLE
    result = build_firecrawl_earnings_batch_result(items)
    if args.output_json:
        output_path = args.output_json if args.output_json.is_absolute() else PROJECT_ROOT / args.output_json
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[{result.get('status')}] {DESIGN_NAME}")
    print(f"- item_count: {result.get('item_count')}")
    print(f"- valid_count: {result.get('valid_count')}")
    print(f"- failed_count: {result.get('failed_count')}")
    for item in result.get("results") or []:
        payload = item.get("payload") if isinstance(item, dict) else None
        if payload:
            metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
            print(
                f"- {item.get('index')}. valid | {metadata.get('ticker')} "
                f"{metadata.get('fiscal_period') or metadata.get('event_date')} | "
                f"external_id={str(payload.get('external_id'))[:12]}"
            )
        else:
            print(f"- {item.get('index')}. failed | {', '.join(item.get('errors') or [])}")
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
