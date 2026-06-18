"""Check earnings_transcript_collector_v1 payload generation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.earnings_transcript_collector import (  # noqa: E402
    DESIGN_NAME,
    build_earnings_transcript_batch_result,
    normalize_earnings_transcript_inputs,
)


def sample_inputs() -> list[dict]:
    return [
        {
            "company": "Planet Labs",
            "ticker": "PL",
            "raw_url": "https://investors.planet.com/events-and-presentations/",
            "title": "Planet Labs Q1 FY2027 earnings call transcript",
            "fiscal_period": "Q1 FY2027",
            "event_date": "2026-06-04",
            "transcript_text": "Management discussed revenue growth, customer expansion, margin discipline, and guidance for the next quarter.",
            "speaker_count": 4,
        }
    ]


def read_inputs(path: Path) -> list:
    return normalize_earnings_transcript_inputs(json.loads(path.read_text(encoding="utf-8")))


def main() -> int:
    parser = argparse.ArgumentParser(description="Earnings transcript payload 계약을 점검합니다.")
    parser.add_argument("--input-json", type=Path, help="transcript source JSON")
    parser.add_argument("--output-json", type=Path, help="payload 결과 저장")
    args = parser.parse_args()

    items = read_inputs(args.input_json) if args.input_json else sample_inputs()
    result = build_earnings_transcript_batch_result(items)
    if args.output_json:
        output_path = args.output_json if args.output_json.is_absolute() else PROJECT_ROOT / args.output_json
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[{result.get('status')}] {DESIGN_NAME}")
    print(f"- item_count: {result.get('item_count')}")
    print(f"- valid_count: {result.get('valid_count')}")
    print(f"- failed_count: {result.get('failed_count')}")
    for item in result.get("results") or []:
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        print(
            f"- {item.get('index')}. {item.get('status')} | "
            f"{metadata.get('ticker') or 'UNKNOWN'} {metadata.get('fiscal_period') or ''} | "
            f"external_id={str(payload.get('external_id') or '')[:12]}"
        )
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
