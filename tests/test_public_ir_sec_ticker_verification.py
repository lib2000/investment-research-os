from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from research_os.public_ir_sec import (  # noqa: E402
    PublicIrSecCollectRequest,
    backfill_public_ir_sec_ticker_verifications,
    collect_public_ir_sec_url,
)
from research_os.research_memory import read_manifest  # noqa: E402


def verified_pl() -> dict:
    return {
        "requested_symbol": "PL",
        "official_symbol": "PL",
        "company_name": "Planet Labs PBC",
        "exchange": "NYSE",
        "country": "US",
        "verified": True,
        "verification_source": "local_cached_registry",
        "message": "verified locally",
    }


def test_public_ir_sec_save_attaches_only_server_verified_ticker_metadata(tmp_path, monkeypatch) -> None:
    vault = tmp_path / "research_vault"
    settings = SimpleNamespace(research_vault_dir=str(vault))
    request = PublicIrSecCollectRequest(
        url="https://www.sec.gov/Archives/edgar/data/1836833/example.htm",
        target_key="PL",
        source_title="Planet Labs 8-K",
        source_provider="SEC EDGAR",
        source_type="sec_company_submissions",
    )
    monkeypatch.setattr(
        "research_os.public_ir_sec.fetch_capture_source_url",
        lambda _url: {"status": "success", "title": "Planet Labs 8-K", "final_url": str(request.url)},
    )
    monkeypatch.setattr(
        "research_os.public_ir_sec.render_source_url_body",
        lambda _info: "Planet Labs official filing " * 40,
    )

    result = collect_public_ir_sec_url(request, settings, ticker_verification=verified_pl())

    assert result["status"] == "success"
    entries = read_manifest(vault)
    assert entries[0]["ticker_verification"]["verified"] is True
    assert entries[0]["ticker_verification"]["official_symbol"] == "PL"


def test_backfill_only_updates_official_sources_with_matching_verified_ticker(tmp_path) -> None:
    vault = tmp_path / "research_vault"
    vault.mkdir()
    entries = [
        {
            "ticker": "PL",
            "type": "public-ir-sec",
            "scope": "public_ir_sec",
            "date": "2026-08-26",
            "file_name": "pl-sec.md",
            "source_url": "https://www.sec.gov/Archives/edgar/data/1836833/example.htm",
            "source_type": "sec_company_submissions",
        },
        {
            "ticker": "PL",
            "type": "public-ir-sec",
            "scope": "public_ir_sec",
            "date": "2026-08-26",
            "file_name": "pl-untrusted.md",
            "source_url": "https://example.invalid/source",
            "source_type": "other",
        },
    ]
    (vault / "manifest.json").write_text(json.dumps(entries), encoding="utf-8")

    result = backfill_public_ir_sec_ticker_verifications(
        vault,
        ticker_verification_for=lambda ticker: verified_pl() if ticker == "PL" else {},
        target_tickers={"PL"},
        apply=True,
    )

    assert result["updated_count"] == 1
    updated = {entry["file_name"]: entry for entry in read_manifest(vault)}
    assert updated["pl-sec.md"]["ticker_verification"]["official_symbol"] == "PL"
    assert "ticker_verification" not in updated["pl-untrusted.md"]
