"""Check portfolio_change_detection_v1 with sample or JSON brief files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.portfolio_change_detection import DESIGN_NAME, detect_portfolio_changes  # noqa: E402


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


def read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"JSON object expected: {path}")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Portfolio health brief change detection을 점검합니다.")
    parser.add_argument("--previous-json", type=Path, help="이전 portfolio_health brief JSON")
    parser.add_argument("--current-json", type=Path, help="현재 portfolio_health brief JSON")
    parser.add_argument("--output-json", type=Path, help="변화 감지 결과를 JSON으로 저장")
    parser.add_argument("--score-threshold", type=float, default=0.3)
    parser.add_argument("--confidence-threshold", type=float, default=0.1)
    args = parser.parse_args()

    if bool(args.previous_json) != bool(args.current_json):
        raise SystemExit("--previous-json and --current-json must be provided together.")
    previous = read_json(args.previous_json) if args.previous_json else sample_previous()
    current = read_json(args.current_json) if args.current_json else sample_current()
    result = detect_portfolio_changes(
        previous,
        current,
        score_threshold=args.score_threshold,
        confidence_threshold=args.confidence_threshold,
    )
    if args.output_json:
        output_path = args.output_json if args.output_json.is_absolute() else PROJECT_ROOT / args.output_json
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    status = result.get("status") or "unknown"
    print(f"[{status}] {DESIGN_NAME}")
    print(f"- previous_as_of: {result.get('previous_as_of') or 'sample'}")
    print(f"- current_as_of: {result.get('current_as_of') or 'sample'}")
    health = result.get("health_score") if isinstance(result.get("health_score"), dict) else {}
    print(f"- health_score: {health.get('previous')} -> {health.get('current')} ({health.get('direction')}, delta={health.get('delta')})")
    counts = result.get("change_counts") if isinstance(result.get("change_counts"), dict) else {}
    print(
        "- changes: "
        f"changed={counts.get('changed_count', 0)} "
        f"stance={counts.get('stance_changed_count', 0)} "
        f"confidence={counts.get('confidence_changed_count', 0)} "
        f"watch={counts.get('watch_item_count', 0)}"
    )
    for item in result.get("watch_items") or []:
        print(f"- watch: {item.get('ticker')} {item.get('previous_stance')} -> {item.get('current_stance')}")
    return 0 if status == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
