"""Check whether the local backend runtime can actually start.

This is intentionally light-weight: it does not import the backend app, so it
can explain missing dependencies without failing at the first import error.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import socket
import sys
from pathlib import Path
from urllib import error, request


REQUIRED_DISTRIBUTIONS = {
    "fastapi": "0.115.12",
    "uvicorn": "0.34.2",
    "pydantic": "2.13.2",
    "httpx": "0.28.1",
    "python-dotenv": "1.1.0",
}


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "research_os_main.py").exists() and (
            candidate / "backend" / "requirements.txt"
        ).exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def installed_version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def check_http_health(url: str, timeout: float) -> tuple[bool, str]:
    try:
        with request.urlopen(url, timeout=timeout) as response:
            status = response.status
            return (200 <= status < 300, f"HTTP {status}")
    except error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        return False, f"연결 실패: {reason}"
    except socket.timeout:
        return False, "연결 시간 초과"
    except OSError as exc:
        return False, f"연결 실패: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description="백엔드 런타임 준비 상태를 확인합니다.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("--strict", action="store_true", help="의존성 또는 백엔드 미가동을 실패로 처리합니다.")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    print(f"프로젝트 루트: {root}")
    print(f"Python: {sys.executable}")

    missing: list[str] = []
    mismatched: list[str] = []
    for distribution, expected in REQUIRED_DISTRIBUTIONS.items():
        actual = installed_version(distribution)
        if actual is None:
            missing.append(distribution)
            print(f"{distribution}: 없음 | 기대 {expected}")
        elif actual != expected:
            mismatched.append(f"{distribution}={actual} (기대 {expected})")
            print(f"{distribution}: {actual} | 기대 {expected} | 확인 필요")
        else:
            print(f"{distribution}: {actual} | 정상")

    health_url = args.base_url.rstrip("/") + "/api/v1/system/health"
    health_ok, health_message = check_http_health(health_url, args.timeout)
    print(f"백엔드 health: {health_url} | {health_message}")

    if missing or mismatched or not health_ok:
        print("권장 조치:")
        if missing or mismatched:
            print(r"1. Windows PowerShell에서 `pip install -r backend\requirements.txt`로 백엔드 의존성을 맞추세요.")
        if not health_ok:
            print(r"2. Windows PowerShell에서 `cd C:\Users\lib20\InvestmentJournalApp` 후 `.\scripts\start-research-backend.ps1 -Port 8001`를 실행하세요.")
        print("3. 실행 후 `http://127.0.0.1:8001/console/index.html`에서 콘솔을 확인하세요.")
        if args.strict:
            return 1

    print("백엔드 런타임 준비 상태 확인 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
