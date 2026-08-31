from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from research_os.settings import Settings  # noqa: E402
from research_os_main import (  # noqa: E402
    OFFICIAL_TICKER_REGISTRY,
    earnings_calendar_policy,
)


def test_mirae_global_income_ce_is_classified_as_a_non_equity_fund() -> None:
    profile = OFFICIAL_TICKER_REGISTRY["B0634"]

    assert profile["company_name"] == "미래에셋글로벌인컴증권자투자신탁1호(채권혼합)종류C-e"
    assert profile["asset_type"] == "mutual_fund"
    assert profile["country"] == "KR"


def test_mirae_global_income_ce_skips_company_earnings_lookup() -> None:
    policy = earnings_calendar_policy("B0634", Settings())

    assert policy["kind"] == "not_applicable"
    assert policy["asset_type"] == "mutual_fund"
