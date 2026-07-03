"""Check whether the local backend runtime can actually start.

This is intentionally light-weight: it does not import the backend app, so it
can explain missing dependencies without failing at the first import error.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import socket
import subprocess
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


def preferred_python(root: Path) -> Path:
    candidates = [
        root / ".venv" / "Scripts" / "python.exe",
        root / ".venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path(sys.executable)


def installed_version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def installed_versions_with_python(
    python_executable: Path,
    distributions: list[str],
) -> dict[str, str | None]:
    if Path(sys.executable).absolute() == python_executable.absolute():
        return {name: installed_version(name) for name in distributions}
    probe = "\n".join(
        [
            "import importlib.metadata as md",
            "import json",
            f"names = {distributions!r}",
            "out = {}",
            "for name in names:",
            "    try:",
            "        out[name] = md.version(name)",
            "    except md.PackageNotFoundError:",
            "        out[name] = None",
            "print(json.dumps(out))",
        ]
    )
    completed = subprocess.run(
        [str(python_executable), "-c", probe],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return {name: None for name in distributions}
    return json.loads(completed.stdout or "{}")


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


def run_daily_recommendation_tests(
    python_executable: Path,
    root: Path,
    timeout: float,
) -> tuple[bool, list[str]]:
    try:
        completed = subprocess.run(
            [str(python_executable), "-m", "unittest", "tests.test_daily_recommendations"],
            cwd=str(root),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return False, [f"시간 초과: {exc}"]
    except OSError as exc:
        return False, [f"실행 실패: {exc}"]
    output = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())
    lines = [line for line in output.splitlines() if line.strip()]
    return completed.returncode == 0, lines[-12:] or ["출력 없음"]


def is_wsl_like() -> bool:
    if os.name == "nt":
        return False
    try:
        version = Path("/proc/version").read_text(encoding="utf-8", errors="ignore").lower()
    except OSError:
        version = ""
    return "microsoft" in version or "wsl" in version


def health_blocked_by_local_sandbox(message: str) -> bool:
    lowered = message.lower()
    return is_wsl_like() and (
        "operation not permitted" in lowered
        or "errno 1" in lowered
        or "permission denied" in lowered
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="백엔드 런타임 준비 상태를 확인합니다.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("--strict", action="store_true", help="의존성 또는 백엔드 미가동을 실패로 처리합니다.")
    parser.add_argument("--check-daily-tests", action="store_true", help="일일 추천 단위 테스트까지 실행합니다.")
    parser.add_argument("--test-timeout", type=float, default=90.0, help="단위 테스트 실행 제한 시간(초)입니다.")
    parser.add_argument("--json", action="store_true", help="점검 결과를 JSON으로 출력합니다.")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    runtime_python = preferred_python(root)
    using_runtime_python = Path(sys.executable).absolute() == runtime_python.absolute()
    if not args.json:
        print(f"프로젝트 루트: {root}")
        print(f"Python: {runtime_python}")
    if not using_runtime_python and not args.json:
        print(f"검사 실행 Python: {sys.executable}")

    detected_versions = installed_versions_with_python(
        runtime_python,
        list(REQUIRED_DISTRIBUTIONS),
    )
    missing: list[str] = []
    mismatched: list[str] = []
    for distribution, expected in REQUIRED_DISTRIBUTIONS.items():
        actual = detected_versions.get(distribution)
        if actual is None:
            missing.append(distribution)
            if not args.json:
                print(f"{distribution}: 없음 | 기대 {expected}")
        elif actual != expected:
            mismatched.append(f"{distribution}={actual} (기대 {expected})")
            if not args.json:
                print(f"{distribution}: {actual} | 기대 {expected} | 확인 필요")
        else:
            if not args.json:
                print(f"{distribution}: {actual} | 정상")

    health_url = args.base_url.rstrip("/") + "/api/v1/system/health"
    health_ok, health_message = check_http_health(health_url, args.timeout)
    if not args.json:
        print(f"백엔드 health: {health_url} | {health_message}")
    health_sandbox_blocked = health_blocked_by_local_sandbox(health_message)
    if health_sandbox_blocked and not args.json:
        print("참고: WSL/Codex 격리 환경에서 localhost 접근이 차단된 상태일 수 있습니다. Windows PowerShell의 Python으로 재확인하세요.")

    daily_tests_ok = True
    daily_test_lines: list[str] = []
    if args.check_daily_tests:
        if not args.json:
            print("일일 추천 단위 테스트: 실행")
        daily_tests_ok, daily_test_lines = run_daily_recommendation_tests(
            runtime_python,
            root,
            timeout=args.test_timeout,
        )
        if not args.json:
            for line in daily_test_lines:
                print(f"  {line}")
            print(f"일일 추천 단위 테스트: {'통과' if daily_tests_ok else '실패'}")

    has_problem = bool(missing or mismatched or not health_ok or not daily_tests_ok)
    result = {
        "status": "warning" if has_problem else "ok",
        "project_root": str(root),
        "runtime_python": str(runtime_python),
        "probe_python": sys.executable,
        "using_runtime_python": using_runtime_python,
        "required_distributions": REQUIRED_DISTRIBUTIONS,
        "detected_versions": detected_versions,
        "missing_distributions": missing,
        "mismatched_distributions": mismatched,
        "health_url": health_url,
        "health_ok": health_ok,
        "health_message": health_message,
        "health_sandbox_blocked": health_sandbox_blocked,
        "daily_tests_checked": args.check_daily_tests,
        "daily_tests_ok": daily_tests_ok,
        "daily_test_tail": daily_test_lines,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if args.strict and has_problem else 0

    if has_problem:
        print("권장 조치:")
        action_number = 1
        if missing or mismatched:
            print(rf"{action_number}. Windows PowerShell에서 `pip install -r backend\requirements.txt`로 백엔드 의존성을 맞추세요.")
            action_number += 1
        if not health_ok:
            if health_sandbox_blocked:
                print(rf"{action_number}. 백엔드가 실제로 꺼졌다고 단정하지 말고 Windows PowerShell에서 `python tools\check_backend_runtime_env.py --strict`로 재확인하세요.")
            else:
                print(rf"{action_number}. Windows PowerShell에서 `cd C:\Users\lib20\InvestmentJournalApp` 후 `.\scripts\restart-research-backend.ps1 -Port 8001`로 백엔드를 재시작 검증하세요.")
            action_number += 1
            print(rf"{action_number}. 재시작 후 `.\tools\status_research_console.ps1 -Strict`로 콘솔/추천/시장일지 상태를 확인하세요.")
            action_number += 1
        if not daily_tests_ok:
            print(rf"{action_number}. Windows PowerShell에서 `python -m unittest tests.test_daily_recommendations`로 실패 상세를 확인하세요.")
            action_number += 1
        print(f"{action_number}. 실행 후 `http://127.0.0.1:8001/console/index.html`에서 콘솔을 확인하세요.")
        if args.strict:
            return 1

    print("백엔드 런타임 준비 상태 확인 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
