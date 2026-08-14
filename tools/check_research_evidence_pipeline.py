from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = PROJECT_ROOT / "backend" / ".env"
DEFAULT_STATE_FILE = PROJECT_ROOT / "research_vault" / "_system" / "research_evidence_pipeline_status.json"
KST = timezone(timedelta(hours=9))

CANONICAL_ENDPOINTS = {
    "earnings_status": "/api/v1/earnings-calendar/status",
    "earnings_refresh": "/api/v1/earnings-calendar/refresh",
    "dart_status": "/api/v1/dart/filings/status",
    "dart_refresh": "/api/v1/dart/filings/refresh",
    "company_ir_status": "/api/v1/company-ir-sources/watch?refresh=false",
    "company_ir_refresh": "/api/v1/company-ir-sources/refresh?limit=20&save_result=true",
    "public_ir_sec_status": "/api/v1/public-ir-sec/status",
    "automation_status": "/api/v1/research-automation/status",
    "dossier_review_status": "/api/v1/research-automation/dedupes/review",
    "dossier_review_refresh": "/api/v1/research-automation/dedupes/review?limit=80&save_result=true",
    "dossier_queue_refresh": "/api/v1/research-automation/dedupes/refresh-dossiers?limit=8&save_result=true",
}

LEGACY_ENDPOINT_ALIASES = {
    "/api/v1/dart-filings/status": CANONICAL_ENDPOINTS["dart_status"],
    "/api/v1/dart-filings/refresh": CANONICAL_ENDPOINTS["dart_refresh"],
    "/api/v1/company-ir-sources/status": CANONICAL_ENDPOINTS["company_ir_status"],
}


class PipelineRequestError(RuntimeError):
    def __init__(self, message: str, *, http_status: int | None = None) -> None:
        super().__init__(message)
        self.http_status = http_status


def _strip_env_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def read_env_value(path: Path, name: str) -> str:
    if not path.exists():
        return ""
    value = ""
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, candidate = line.split("=", 1)
        if key.strip() == name:
            value = _strip_env_value(candidate)
    return value


def resolve_dev_user_token(env_file: Path) -> tuple[str, str]:
    for name in ("INVESTMENT_RESEARCH_DEV_USER_TOKEN", "DEV_USER_TOKEN"):
        value = os.getenv(name, "").strip()
        if value:
            return value, f"environment:{name}"
    value = read_env_value(env_file, "DEV_USER_TOKEN")
    if value:
        return value, str(env_file)
    raise ValueError(
        "DEV_USER_TOKEN is not configured. Set it in backend/.env or the "
        "INVESTMENT_RESEARCH_DEV_USER_TOKEN environment variable."
    )


def request_json(
    base_url: str,
    path: str,
    token: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except HTTPError as exc:
        detail = ""
        try:
            error_payload = json.loads(exc.read().decode("utf-8", errors="replace"))
            detail = str(error_payload.get("detail") or "")
        except (json.JSONDecodeError, AttributeError):
            pass
        suffix = f": {detail}" if detail else ""
        raise PipelineRequestError(
            f"{method} {path} returned HTTP {exc.code}{suffix}",
            http_status=exc.code,
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise PipelineRequestError(f"{method} {path} failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise PipelineRequestError(f"{method} {path} returned a non-object JSON payload")
    return payload


def _status_counts(value: Any) -> dict[str, int]:
    counts: Counter[str] = Counter()

    def walk(item: Any) -> None:
        if isinstance(item, dict):
            for key, nested in item.items():
                if key in {"status", "capture_status", "reliability_status", "fallback_status"} and isinstance(nested, str):
                    counts[nested] += 1
                walk(nested)
        elif isinstance(item, list):
            for nested in item:
                walk(nested)

    walk(value)
    return dict(sorted(counts.items()))


def summarize_earnings(payload: dict[str, Any]) -> dict[str, Any]:
    entries = payload.get("entries") if isinstance(payload.get("entries"), dict) else {}
    counts = Counter(
        str(entry.get("status") or "unknown")
        for entry in entries.values()
        if isinstance(entry, dict)
    )
    fallback_tickers = sorted(
        str(ticker)
        for ticker, entry in entries.items()
        if isinstance(entry, dict) and entry.get("status") == "fallback_unavailable"
    )
    return {
        "status": payload.get("status"),
        "updated_at": payload.get("updated_at"),
        "entry_count": len(entries),
        "success_count": counts.get("success", 0),
        "not_applicable_count": counts.get("not_applicable", 0),
        "fallback_unavailable_count": counts.get("fallback_unavailable", 0),
        "fallback_unavailable_tickers": fallback_tickers,
        "other_status_count": sum(
            count
            for status, count in counts.items()
            if status not in {"success", "not_applicable", "fallback_unavailable"}
        ),
        "not_applicable_is_expected": True,
        "not_applicable_note": "ETF/ETN/펀드처럼 개별 기업 실적 일정 대상이 아닌 자산은 정상 분류입니다.",
        "status_counts": dict(sorted(counts.items())),
    }


def summarize_dart(payload: dict[str, Any]) -> dict[str, Any]:
    daily = payload.get("daily_check") if isinstance(payload.get("daily_check"), dict) else {}
    return {
        "status": payload.get("status"),
        "enabled": bool(payload.get("enabled")),
        "configured": bool(payload.get("configured")),
        "updated_at": payload.get("updated_at"),
        "entry_count": int(payload.get("entry_count") or 0),
        "daily_status": daily.get("status"),
        "daily_due": bool(daily.get("due")),
        "coverage_rate": daily.get("coverage_rate"),
        "checked_count": int(daily.get("checked_count") or 0),
        "target_count": int(daily.get("current_target_count") or 0),
        "failure_count": int(daily.get("failure_count") or 0),
        "failed_tickers": list(daily.get("failed_tickers") or []),
        "excluded_count": int(daily.get("excluded_count") or 0),
        "reliability_status": daily.get("reliability_status"),
        "reliability_message": daily.get("reliability_message"),
    }


def _safe_ir_failure(entry: dict[str, Any]) -> dict[str, Any]:
    error = str(entry.get("error") or entry.get("message") or "")
    if "403" in error:
        error_kind = "http_403"
    elif "404" in error:
        error_kind = "http_404"
    elif "timed out" in error.lower() or "timeout" in error.lower():
        error_kind = "timeout"
    else:
        error_kind = "request_failed"
    return {
        "source_key": entry.get("source_key"),
        "status": entry.get("status"),
        "error_kind": error_kind,
    }


def summarize_company_ir(payload: dict[str, Any]) -> dict[str, Any]:
    source_results = payload.get("source_results") if isinstance(payload.get("source_results"), list) else []
    failures = [
        _safe_ir_failure(entry)
        for entry in source_results
        if isinstance(entry, dict) and entry.get("status") not in {None, "success"}
    ]
    return {
        "status": payload.get("status"),
        "source_status": payload.get("source_status"),
        "updated_at": payload.get("updated_at"),
        "item_count": int(payload.get("item_count") or 0),
        "related_count": int(payload.get("related_count") or 0),
        "captured_count": int(payload.get("captured_count") or 0),
        "source_count": int(payload.get("source_count") or 0),
        "failed_source_count": len(failures),
        "failed_sources": failures,
        "warnings": list(payload.get("warnings") or []),
    }


def summarize_public_ir_sec(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": payload.get("status"),
        "entry_count": int(payload.get("entry_count") or 0),
        "recent_count": int(payload.get("recent_count") or 0),
        "needs_body_copy_count": int(payload.get("needs_body_copy_count") or 0),
        "sec_exhibit_followup_count": int(payload.get("sec_exhibit_followup_count") or 0),
        "status_counts": _status_counts(payload),
    }


def summarize_automation(payload: dict[str, Any]) -> dict[str, Any]:
    queue = payload.get("dossier_refresh_queue") if isinstance(payload.get("dossier_refresh_queue"), dict) else {}
    return {
        "status": payload.get("status"),
        "as_of": payload.get("as_of"),
        "source_schedule_due_count": int(payload.get("source_schedule_due_count") or 0),
        "dossier_refresh_queue": {
            "status": queue.get("status"),
            "as_of": queue.get("as_of"),
            "candidate_count": int(queue.get("candidate_count") or 0),
            "refreshed_count": int(queue.get("refreshed_count") or 0),
            "failed_count": int(queue.get("failed_count") or 0),
            "skipped_count": int(queue.get("skipped_count") or 0),
            "candidate_tickers": [
                str(entry.get("ticker"))
                for entry in (queue.get("candidates") or [])
                if isinstance(entry, dict) and entry.get("ticker")
            ],
        },
    }


def summarize_dossier_review(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": payload.get("status"),
        "as_of": payload.get("as_of"),
        "checked_count": int(payload.get("checked_count") or 0),
        "unique_representative_count": int(payload.get("unique_representative_count") or 0),
        "duplicate_group_count": int(payload.get("duplicate_group_count") or 0),
        "duplicate_entry_count": int(payload.get("duplicate_entry_count") or 0),
        "ticker_candidate_count": len(payload.get("ticker_breakdown") or []),
        "ticker_candidates": [
            str(entry.get("ticker"))
            for entry in (payload.get("ticker_breakdown") or [])
            if isinstance(entry, dict) and entry.get("ticker")
        ][:20],
    }


def _timed_call(call: Callable[[], dict[str, Any]]) -> tuple[dict[str, Any], float]:
    started = time.monotonic()
    payload = call()
    return payload, round(time.monotonic() - started, 3)


def collect_pipeline_status(
    base_url: str,
    token: str,
    *,
    timeout: int = 120,
    refresh: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    refresh_results: dict[str, Any] = {}
    errors: list[str] = []

    def call(name: str, path: str, *, method: str = "GET", body: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            payload, elapsed = _timed_call(
                lambda: request_json(base_url, path, token, method=method, body=body, timeout=timeout)
            )
            if method != "GET":
                refresh_results[name] = {
                    "status": payload.get("status"),
                    "elapsed_seconds": elapsed,
                    "updated_at": payload.get("updated_at") or payload.get("as_of"),
                }
            return payload
        except PipelineRequestError as exc:
            errors.append(str(exc))
            if method != "GET":
                refresh_results[name] = {
                    "status": "error",
                    "http_status": exc.http_status,
                    "message": str(exc),
                }
            return {}

    if refresh:
        call("earnings", CANONICAL_ENDPOINTS["earnings_refresh"], method="POST")
        call(
            "dart",
            CANONICAL_ENDPOINTS["dart_refresh"],
            method="POST",
            body={"force": force, "save_result": True},
        )
        call("company_ir", CANONICAL_ENDPOINTS["company_ir_refresh"], method="POST")
        call("dossier_review", CANONICAL_ENDPOINTS["dossier_review_refresh"], method="POST")
        call("dossier_queue", CANONICAL_ENDPOINTS["dossier_queue_refresh"], method="POST")

    payloads = {
        "earnings": call("earnings_status", CANONICAL_ENDPOINTS["earnings_status"]),
        "dart": call("dart_status", CANONICAL_ENDPOINTS["dart_status"]),
        "company_ir": call("company_ir_status", CANONICAL_ENDPOINTS["company_ir_status"]),
        "public_ir_sec": call("public_ir_sec_status", CANONICAL_ENDPOINTS["public_ir_sec_status"]),
        "automation": call("automation_status", CANONICAL_ENDPOINTS["automation_status"]),
        "dossier_review": call("dossier_review_status", CANONICAL_ENDPOINTS["dossier_review_status"]),
    }
    checks = {
        "earnings": summarize_earnings(payloads["earnings"]),
        "dart": summarize_dart(payloads["dart"]),
        "company_ir": summarize_company_ir(payloads["company_ir"]),
        "public_ir_sec": summarize_public_ir_sec(payloads["public_ir_sec"]),
        "automation": summarize_automation(payloads["automation"]),
        "dossier_review": summarize_dossier_review(payloads["dossier_review"]),
    }

    blocking_issues = list(errors)
    warnings: list[str] = []
    earnings = checks["earnings"]
    dart = checks["dart"]
    company_ir = checks["company_ir"]
    queue = checks["automation"]["dossier_refresh_queue"]

    if earnings["status"] != "success":
        blocking_issues.append("earnings status is unavailable")
    if earnings["fallback_unavailable_count"]:
        blocking_issues.append(
            f"earnings fallback_unavailable: {earnings['fallback_unavailable_count']} ticker(s)"
        )
    if not dart["configured"] or not dart["enabled"]:
        blocking_issues.append("DART is not configured or enabled")
    if dart["daily_status"] != "complete" or dart["failure_count"]:
        blocking_issues.append(
            f"DART daily check incomplete: status={dart['daily_status']} failures={dart['failure_count']}"
        )
    if company_ir["status"] != "success" or company_ir["item_count"] <= 0:
        blocking_issues.append("company IR status has no usable cached items")
    elif company_ir["failed_source_count"]:
        warnings.append(
            f"company IR is usable but {company_ir['failed_source_count']} source(s) returned 403/timeout/request errors"
        )
    if checks["public_ir_sec"]["status"] != "success":
        blocking_issues.append("public IR/SEC status is unavailable")
    if checks["automation"]["status"] != "success":
        blocking_issues.append("research automation status is unavailable")
    if queue["failed_count"]:
        blocking_issues.append(f"Dossier refresh queue failures: {queue['failed_count']}")
    if checks["dossier_review"]["status"] != "success":
        blocking_issues.append("Dossier duplicate review is unavailable")

    status = "error" if blocking_issues else "warning" if warnings else "success"
    return {
        "status": status,
        "module": "research_evidence_pipeline_check",
        "as_of": datetime.now(tz=KST).isoformat(timespec="seconds"),
        "base_url": base_url.rstrip("/"),
        "authentication": {
            "status": "attached" if token else "missing",
            "scheme": "Bearer",
            "token_exposed": False,
        },
        "endpoint_contract": {
            "canonical": CANONICAL_ENDPOINTS,
            "legacy_aliases": LEGACY_ENDPOINT_ALIASES,
        },
        "refresh_requested": refresh,
        "force_refresh_requested": force,
        "refresh_results": refresh_results,
        "checks": checks,
        "blocking_issues": blocking_issues,
        "warnings": warnings,
        "interpretation": {
            "not_applicable": "정상 분류: ETF/ETN/펀드 등 개별 기업 실적 일정 비대상",
            "fallback_unavailable": "조치 필요: 국내 기업 실적 일정의 DART fallback도 확보하지 못함",
            "dossier_candidate_count": queue["candidate_count"],
        },
    }


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check authenticated earnings, DART, IR, automation, and Dossier status without exposing tokens."
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--force", action="store_true", help="Force DART external refresh even when the cache is fresh.")
    parser.add_argument("--write-state", action="store_true")
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    try:
        token, token_source = resolve_dev_user_token(args.env_file.resolve())
        result = collect_pipeline_status(
            args.base_url,
            token,
            timeout=max(5, args.timeout),
            refresh=args.refresh,
            force=args.force,
        )
        result["authentication"]["source"] = token_source
    except (ValueError, PipelineRequestError) as exc:
        result = {
            "status": "error",
            "module": "research_evidence_pipeline_check",
            "as_of": datetime.now(tz=KST).isoformat(timespec="seconds"),
            "authentication": {
                "status": "missing_or_invalid",
                "scheme": "Bearer",
                "token_exposed": False,
            },
            "blocking_issues": [str(exc)],
            "warnings": [],
        }

    if args.write_state:
        write_json_atomic(args.state_file.resolve(), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if args.strict and result.get("status") == "error" else 0


if __name__ == "__main__":
    sys.exit(main())
