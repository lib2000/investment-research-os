"""Export the privacy-safe Daily Research feed used by the static homepage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.public_daily_research import (  # noqa: E402
    get_public_daily_research_feed,
    public_daily_research_default_output_path,
    write_public_daily_research_feed,
)
from research_os.settings import Settings  # noqa: E402


def _project_relative_path(value: str) -> Path:
    candidate = Path(value)
    resolved = (PROJECT_ROOT / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as error:
        raise argparse.ArgumentTypeError("출력 경로는 프로젝트 루트 내부여야 합니다.") from error
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export a privacy-safe feed for the public Daily Research homepage."
    )
    parser.add_argument(
        "--output",
        type=_project_relative_path,
        default=public_daily_research_default_output_path(PROJECT_ROOT),
        help="JSON output path under the project root.",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print the feed without writing a file.",
    )
    args = parser.parse_args()
    settings = Settings.from_env()

    if args.stdout:
        payload = get_public_daily_research_feed(settings)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    payload = write_public_daily_research_feed(settings, args.output)
    print(
        json.dumps(
            {
                "status": "exported",
                "output": str(args.output.relative_to(PROJECT_ROOT)),
                "publication_state": payload["publication"]["state"],
                "report_date": payload["publication"]["report_date"],
                "archive_count": len(payload["archive"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
