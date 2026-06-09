#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

DEFAULT_STORE = Path("research_vault/_system/user_portfolios.json")
DEFAULT_EXPECTED = "PL=100:USD,JOBY=208:USD,CHPT=22:USD,ABSI=29:USD,GOTU=50:USD,OTLY=8:USD,RXRX=9:USD,253450=36:KRW"


def project_root(cwd: Path) -> Path:
    for candidate in [cwd, *cwd.parents]:
        if (candidate / "backend" / "research_os_main.py").exists():
            return candidate
    return cwd


def load_portfolio_names(store_path: Path) -> list[str]:
    payload = json.loads(store_path.read_text(encoding="utf-8"))
    portfolios = payload.get("portfolios") if isinstance(payload, dict) else {}
    names: list[str] = []
    for key, item in (portfolios or {}).items():
        if not isinstance(item, dict):
            continue
        names.append(str(item.get("portfolio_name") or key).strip())
    return [name for name in names if name]


def refresh_portfolio(base_url: str, token: str, portfolio_name: str, timeout: float) -> dict:
    encoded = quote(portfolio_name, safe="")
    url = f"{base_url.rstrip('/')}/api/v1/portfolios/{encoded}?refresh_prices=true&persist_refresh=true"
    request = Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[-1000:]
        raise RuntimeError(f"{portfolio_name}: HTTP {exc.code} {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"{portfolio_name}: {exc.reason}") from exc
    active = data.get("active_portfolio") or {}
    return {
        "portfolio_name": active.get("portfolio_name") or portfolio_name,
        "holding_count": active.get("holding_count"),
        "updated_at": active.get("updated_at"),
        "storage_path": data.get("storage_path"),
    }


def run_check(root: Path, expected: str) -> None:
    commands = [
        [sys.executable, "tools/check_all_portfolio_store.py", "--min-holdings", "1", "--forbid-zero"],
        [
            sys.executable,
            "tools/check_portfolio_store.py",
            "--portfolio",
            "이형주",
            "--expected-holdings-count",
            "17",
            "--expected",
            expected,
            "--forbid-zero",
        ],
    ]
    for command in commands:
        subprocess.run(command, cwd=root, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh saved portfolio prices without modifying protected quantities.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--token", default="dev-local-token")
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    parser.add_argument("--portfolio", action="append", help="Portfolio name to refresh. Repeatable. Defaults to all saved portfolios.")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--skip-check", action="store_true")
    parser.add_argument("--expected-main", default=DEFAULT_EXPECTED)
    args = parser.parse_args()

    root = project_root(Path.cwd())
    store_path = args.store if args.store.is_absolute() else root / args.store
    portfolio_names = args.portfolio or load_portfolio_names(store_path)
    if not portfolio_names:
        raise SystemExit("갱신할 포트폴리오를 찾지 못했습니다.")

    refreshed = []
    failures = []
    for name in portfolio_names:
        try:
            refreshed.append(refresh_portfolio(args.base_url, args.token, name, args.timeout))
        except Exception as exc:  # noqa: BLE001 - print all refresh failures for operations.
            failures.append({"portfolio_name": name, "error": str(exc)})

    print(json.dumps({"status": "success" if not failures else "partial", "refreshed": refreshed, "failures": failures}, ensure_ascii=False, indent=2))
    if failures:
        return 1
    if not args.skip_check:
        run_check(root, args.expected_main)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
