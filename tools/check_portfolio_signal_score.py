"""Check portfolio_signal_score_v1 with sample signal inputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.portfolio_signal_score import DESIGN_NAME, build_portfolio_signal_scores  # noqa: E402


def sample_signals() -> list[dict]:
    return [
        {"ticker": "PL", "company": "Planet Labs", "source_platform": "firecrawl_ir", "source_kind": "ir", "stance": "positive", "confidence": 0.82, "score": 7.4},
        {"ticker": "PL", "company": "Planet Labs", "source_platform": "earnings_transcript", "source_kind": "earnings_transcript", "stance": "positive", "confidence": 0.72, "score": 7.1},
        {"ticker": "PL", "company": "Planet Labs", "source_platform": "sec_edgar", "source_kind": "8-k", "stance": "neutral", "confidence": 0.56, "score": 5.6},
        {"ticker": "JOBY", "company": "Joby Aviation", "source_platform": "sec_edgar", "source_kind": "10-q", "stance": "risk", "confidence": 0.8, "score": 3.1},
        {"ticker": "005930", "company": "삼성전자", "source_platform": "opendart", "source_kind": "dart_quarterly", "stance": "positive", "confidence": 0.74, "score": 6.8},
    ]


def read_signals(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("items") or data.get("signals") or []
    if not isinstance(data, list):
        raise SystemExit(f"JSON list or wrapper expected: {path}")
    return [item for item in data if isinstance(item, dict)]


def main() -> int:
    parser = argparse.ArgumentParser(description="IR/Earnings/SEC/DART 통합 포트폴리오 점수 계약을 점검합니다.")
    parser.add_argument("--input-json", type=Path, help="signal item JSON")
    parser.add_argument("--output-json", type=Path, help="score 결과 저장")
    parser.add_argument("--json", action="store_true", help="점검 결과를 JSON으로 출력합니다.")
    args = parser.parse_args()

    signals = read_signals(args.input_json) if args.input_json else sample_signals()
    result = build_portfolio_signal_scores(signals)
    if args.output_json:
        output_path = args.output_json if args.output_json.is_absolute() else PROJECT_ROOT / args.output_json
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("status") == "success" else 1

    print(f"[{result.get('status')}] {DESIGN_NAME}")
    print(f"- signal_count: {result.get('signal_count')}")
    print(f"- ticker_count: {result.get('ticker_count')}")
    print(f"- portfolio_score: {result.get('portfolio_score')}")
    print(f"- source_family_counts: {result.get('source_family_counts')}")
    for item in result.get("tickers", [])[:5]:
        print(f"- {item.get('ticker')} {item.get('label')} score={item.get('score')} families={','.join(item.get('source_families') or [])}")
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
