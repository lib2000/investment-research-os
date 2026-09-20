import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def test_public_listing_parser_only_keeps_allowed_metadata() -> None:
    from research_os.kis_global_research import parse_kis_global_research_listing_html

    html = """
    <ul class="view_area line">
      <li>
        <div class="head blue">글로벌 전략</div>
        <a class="body_tit">미국 금리와 반도체 시장 점검</a>
        <p class="body_sub">이 문장은 원문 요약이라 저장하면 안 됩니다.</p>
        <span class="tit_info">한국투자증권 리서치본부 2026.09.18</span>
      </li>
      <li>
        <div class="head blue">글로벌 ETF</div>
        <a class="body_tit">달러 유동성 점검</a>
        <span class="tit_info">2026.09.17</span>
      </li>
    </ul>
    """

    items = parse_kis_global_research_listing_html(html, limit=10)

    assert len(items) == 2
    assert items[0]["title"] == "미국 금리와 반도체 시장 점검"
    assert items[0]["category"] == "글로벌 전략"
    assert items[0]["published_at"] == "2026-09-18"
    assert items[0]["author"] == "한국투자증권 리서치본부"
    assert items[0]["access_scope"] == "listing_metadata_only"
    serialized = json.dumps(items, ensure_ascii=False)
    assert "원문 요약" not in serialized
    assert "body_sub" not in serialized


def test_listing_policy_and_refresh_due_are_explicit() -> None:
    from research_os.kis_global_research import (
        kis_global_research_copyright_policy,
        should_refresh_kis_global_research_cache,
    )

    policy = kis_global_research_copyright_policy()
    assert policy["full_text_stored"] is False
    assert policy["pdf_auto_downloaded"] is False
    assert policy["login_bypass"] is False

    now = datetime(2026, 9, 20, 12, tzinfo=timezone.utc)
    fresh = {"updated_at": (now - timedelta(hours=23)).isoformat()}
    stale = {"updated_at": (now - timedelta(hours=24)).isoformat()}
    assert not should_refresh_kis_global_research_cache(fresh, refresh_hours=24, now=now)
    assert should_refresh_kis_global_research_cache(stale, refresh_hours=24, now=now)


def test_refresh_cache_saves_metadata_once_and_deduplicates() -> None:
    import research_os_main as main
    from research_os.settings import Settings

    item = {
        "item_id": "kis-item-1",
        "title": "글로벌 시장 메타데이터",
        "category": "글로벌 전략",
        "author": "리서치본부",
        "published_at": "2026-09-20",
        "source": "korea_investment_securities",
        "source_url": "https://securities.koreainvestment.com/main/research/research/Strategy.jsp?jkGubun=7",
        "access_scope": "listing_metadata_only",
    }
    response = SimpleNamespace(
        captured_item=SimpleNamespace(ticker="MARKET-GLOBAL", source_type="market_research"),
        storage=None,
    )
    with TemporaryDirectory() as tmpdir:
        settings = Settings(research_vault_dir=tmpdir)
        with (
            patch.object(main, "fetch_kis_global_research_items", return_value=([item], [])),
            patch.object(main, "save_kis_global_research_item", return_value=response) as save_item,
        ):
            first = main.refresh_kis_global_research_cache(settings, limit=1)
            second = main.refresh_kis_global_research_cache(settings, limit=1)

        assert first["saved_count"] == 1
        assert second["saved_count"] == 0
        assert second["skipped_count"] == 1
        assert save_item.call_count == 1
        cache = main.read_kis_global_research_cache(settings)
        entry = cache["entries"]["kis-item-1"]
        assert entry["access_scope"] == "listing_metadata_only"
        assert "summary" not in entry


def test_parenthesized_us_listing_symbol_uses_verified_ticker() -> None:
    import research_os_main as main
    from research_os.settings import Settings

    with patch.object(main, "ensure_verified_ticker", return_value="CRM"):
        target, source_hint, source_type = main.infer_kis_global_research_storage_target(
            {"title": "세일스포스(CRM USA): Dreamforce Day 2", "category": "기업분석"},
            Settings(research_vault_dir="unused"),
        )

    assert target == "CRM"
    assert source_hint == "kis_global_us_symbol"
    assert source_type == "analyst_report"


class KisGlobalResearchTests(unittest.TestCase):
    """Keep the daily verification runner independent of an optional pytest install."""

    def test_public_listing_parser_only_keeps_allowed_metadata(self) -> None:
        test_public_listing_parser_only_keeps_allowed_metadata()

    def test_listing_policy_and_refresh_due_are_explicit(self) -> None:
        test_listing_policy_and_refresh_due_are_explicit()

    def test_refresh_cache_saves_metadata_once_and_deduplicates(self) -> None:
        test_refresh_cache_saves_metadata_once_and_deduplicates()

    def test_parenthesized_us_listing_symbol_uses_verified_ticker(self) -> None:
        test_parenthesized_us_listing_symbol_uses_verified_ticker()
