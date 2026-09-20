"""DART annual-report lab observability and bounded A001 collection.

The ledger deliberately stores neither request parameters nor authentication
keys.  OpenDART may report an application error in a HTTP 200 response, so the
body status is recorded independently from the HTTP status.
"""

from __future__ import annotations

from datetime import timedelta
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from uuid import uuid4

from research_os.settings import Settings
from research_os.state_store import (
    current_storage_date,
    current_storage_datetime,
    current_storage_timestamp,
    user_state_dir,
)


SCHEMA_VERSION = 2
ANNUAL_REPORT_DETAIL_TYPE = "A001"
ANNUAL_REPORT_CODE = "11011"
DART_SUCCESS_STATUSES = frozenset({"000"})
DART_EMPTY_STATUSES = frozenset({"013"})
DEFAULT_PROVIDER_LIMIT_REFERENCE = 20_000
DEFAULT_DAILY_SELF_CAP = 15_000
MAX_RECENT_FAILURES = 30
MAX_BATCH_TICKERS = 50
MAX_GOVERNANCE_BATCH_TICKERS = 12
DEFAULT_GOVERNANCE_BATCH_TICKERS = 2
LEDGER_FILE_NAME = "dart_annual_report_lab.sqlite3"

# Keep this registry in lockstep with OpenDartClient's request bundle.  It is
# intentionally a compact public-research subset, not an archive of raw DART
# response bodies or annual-report text.
GOVERNANCE_ENDPOINT_KEYS = (
    "largest_holders",
    "largest_holder_changes",
    "executives",
    "employees",
    "share_structure",
    "dividends",
    "board_remuneration",
    "individual_remuneration",
)

DISCLAIMER = (
    "출처: 금융감독원 전자공시시스템(DART) 오픈API. 금융감독원은 공시정보의 "
    "정확성·완전성을 보장하지 않으며 이용 결과에 대해 책임지지 않습니다"
    "(오픈API 이용약관 제23조). 본 화면은 정보 제공 목적의 관측·분석 도구이며 "
    "투자 권유나 매매 신호가 아닙니다."
)

_ALLOWED_OUTCOMES = {
    "in_flight",
    "ok",
    "empty",
    "dart_err",
    "http_err",
    "invalid_payload",
    "exception",
    "quota_stopped",
}
_FAILURE_OUTCOMES = {"dart_err", "http_err", "invalid_payload", "exception"}
_SECRET_QUERY_RE = re.compile(r"(?i)(crtfc_key(?:=|%3D))[^&\s]+")
_LONG_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{32,}(?![A-Za-z0-9_-])")


class DartQuotaExceeded(RuntimeError):
    """Raised before a request when the local daily self-cap is exhausted."""

    def __init__(self, used: int, limit: int) -> None:
        self.used = used
        self.limit = limit
        super().__init__(f"DART 플랫폼 자체 일일 한도에 도달했습니다: {used}/{limit}")


def dart_lab_db_path(settings: Settings) -> Path:
    return user_state_dir(settings) / LEDGER_FILE_NAME


def _connect(settings: Settings) -> sqlite3.Connection:
    path = dart_lab_db_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 10000")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS dart_request_event (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            requested_at_kst TEXT NOT NULL,
            completed_at_kst TEXT,
            activity_date TEXT NOT NULL,
            job_name TEXT NOT NULL,
            api_name TEXT NOT NULL,
            target TEXT,
            outcome TEXT NOT NULL,
            counted INTEGER NOT NULL DEFAULT 1 CHECK (counted IN (0, 1)),
            http_status INTEGER,
            dart_status TEXT,
            message TEXT,
            duration_ms INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_dart_event_activity
            ON dart_request_event(activity_date, event_id);
        CREATE INDEX IF NOT EXISTS idx_dart_event_outcome
            ON dart_request_event(outcome, event_id);

        CREATE TABLE IF NOT EXISTS dart_lab_run (
            run_id TEXT PRIMARY KEY,
            activity_date TEXT NOT NULL,
            started_at_kst TEXT NOT NULL,
            completed_at_kst TEXT NOT NULL,
            job_name TEXT NOT NULL,
            status TEXT NOT NULL,
            selected_count INTEGER NOT NULL DEFAULT 0,
            saved_count INTEGER NOT NULL DEFAULT 0,
            skipped_count INTEGER NOT NULL DEFAULT 0,
            failed_count INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_dart_lab_run_activity
            ON dart_lab_run(activity_date, started_at_kst);

        CREATE TABLE IF NOT EXISTS dart_lab_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at_kst TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS dart_governance_snapshot (
            snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            corp_code TEXT,
            corp_name TEXT,
            business_year TEXT NOT NULL,
            report_code TEXT NOT NULL,
            source_receipt_no TEXT,
            source_url TEXT,
            content_hash TEXT NOT NULL,
            captured_at_kst TEXT NOT NULL,
            status TEXT NOT NULL,
            summary_json TEXT NOT NULL,
            UNIQUE(ticker, business_year, report_code, content_hash)
        );
        CREATE INDEX IF NOT EXISTS idx_dart_governance_latest
            ON dart_governance_snapshot(ticker, business_year, report_code, captured_at_kst DESC);
        """
    )
    return connection


def _compact_text(value: object, *, limit: int = 500) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]


def sanitize_dart_event_text(value: object, *, secret: str = "") -> str:
    """Return a compact message that cannot retain a DART authentication key."""

    text = _compact_text(value)
    if secret:
        text = text.replace(secret, "[REDACTED]")
    text = _SECRET_QUERY_RE.sub(r"\1[REDACTED]", text)
    # Error objects can stringify a full request URL.  DART keys are long
    # opaque tokens, so scrub token-shaped values as a final defence.
    text = _LONG_TOKEN_RE.sub("[REDACTED]", text)
    return text[:500]


def classify_dart_response(*, http_status: int | None, dart_status: str | None) -> str:
    if http_status is not None and not 200 <= int(http_status) < 300:
        return "http_err"
    normalized = str(dart_status or "").strip()
    if not normalized or normalized in DART_SUCCESS_STATUSES:
        return "ok"
    if normalized in DART_EMPTY_STATUSES:
        return "empty"
    return "dart_err"


def _provider_limit_reference(settings: Settings) -> int:
    value = int(
        getattr(settings, "dart_provider_limit_reference", DEFAULT_PROVIDER_LIMIT_REFERENCE) or 0
    )
    return max(4, value)


def _configured_daily_self_cap(settings: Settings) -> int:
    value = int(getattr(settings, "dart_daily_self_cap", DEFAULT_DAILY_SELF_CAP) or 0)
    return max(1, value)


def _daily_self_cap(settings: Settings) -> int:
    """Return an effective cap that can never exceed 75% of the reference limit."""

    configured = _configured_daily_self_cap(settings)
    reference = _provider_limit_reference(settings)
    safe_ceiling = max(1, (reference * 3) // 4)
    return min(configured, safe_ceiling)


def begin_dart_request(
    settings: Settings,
    *,
    job_name: str,
    api_name: str,
    target: str | None = None,
) -> int:
    """Atomically reserve one locally permitted DART request."""

    now = current_storage_datetime()
    activity_date = now.date().isoformat()
    requested_at = now.isoformat(timespec="milliseconds")
    cap = _daily_self_cap(settings)
    safe_job = _compact_text(job_name, limit=80) or "opendart_client"
    safe_api = _compact_text(api_name, limit=80) or "unknown"
    safe_target = _compact_text(target, limit=120) or None
    connection = _connect(settings)
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT COALESCE(SUM(counted), 0) AS used "
            "FROM dart_request_event WHERE activity_date = ?",
            (activity_date,),
        ).fetchone()
        used = int(row["used"] if row else 0)
        if used >= cap:
            connection.execute(
                """
                INSERT INTO dart_request_event (
                    requested_at_kst, completed_at_kst, activity_date,
                    job_name, api_name, target, outcome, counted, message
                ) VALUES (?, ?, ?, ?, ?, ?, 'quota_stopped', 0, ?)
                """,
                (
                    requested_at,
                    requested_at,
                    activity_date,
                    safe_job,
                    safe_api,
                    safe_target,
                    f"플랫폼 자체 일일 한도 {cap}건에 도달해 네트워크 요청 전에 중단",
                ),
            )
            connection.commit()
            raise DartQuotaExceeded(used, cap)
        cursor = connection.execute(
            """
            INSERT INTO dart_request_event (
                requested_at_kst, activity_date, job_name, api_name,
                target, outcome, counted
            ) VALUES (?, ?, ?, ?, ?, 'in_flight', 1)
            """,
            (requested_at, activity_date, safe_job, safe_api, safe_target),
        )
        connection.commit()
        return int(cursor.lastrowid)
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()


def complete_dart_request(
    settings: Settings,
    event_id: int,
    *,
    outcome: str,
    http_status: int | None = None,
    dart_status: str | None = None,
    message: object = "",
    duration_ms: int | None = None,
    secret: str = "",
) -> None:
    normalized_outcome = outcome if outcome in _ALLOWED_OUTCOMES else "exception"
    completed_at = current_storage_timestamp()
    safe_message = sanitize_dart_event_text(message, secret=secret)
    connection = _connect(settings)
    try:
        connection.execute(
            """
            UPDATE dart_request_event
               SET completed_at_kst = ?, outcome = ?, http_status = ?,
                   dart_status = ?, message = ?, duration_ms = ?
             WHERE event_id = ?
            """,
            (
                completed_at,
                normalized_outcome,
                int(http_status) if http_status is not None else None,
                _compact_text(dart_status, limit=12) or None,
                safe_message or None,
                max(0, int(duration_ms)) if duration_ms is not None else None,
                int(event_id),
            ),
        )
        connection.commit()
    finally:
        connection.close()


def _meta_int(settings: Settings, key: str, default: int = 0) -> int:
    connection = _connect(settings)
    try:
        row = connection.execute("SELECT value FROM dart_lab_meta WHERE key = ?", (key,)).fetchone()
    finally:
        connection.close()
    if not row:
        return default
    try:
        return int(row["value"])
    except (TypeError, ValueError):
        return default


def _write_meta(settings: Settings, key: str, value: object) -> None:
    connection = _connect(settings)
    try:
        connection.execute(
            """
            INSERT INTO dart_lab_meta(key, value, updated_at_kst)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at_kst = excluded.updated_at_kst
            """,
            (_compact_text(key, limit=80), _compact_text(value, limit=500), current_storage_timestamp()),
        )
        connection.commit()
    finally:
        connection.close()


def _snapshot_value(row: dict, *keys: str, limit: int = 120) -> str | None:
    """Return the first compact public field from an official row."""

    for key in keys:
        value = _compact_text(row.get(key), limit=limit)
        if value:
            return value
    return None


def _snapshot_rows(
    endpoint_rows: dict[str, list[dict]],
    key: str,
    fields: tuple[tuple[str, tuple[str, ...]], ...],
    *,
    limit: int,
) -> list[dict[str, str]]:
    """Project raw endpoint rows into the documented, minimized data contract."""

    projected: list[dict[str, str]] = []
    for row in endpoint_rows.get(key, [])[:limit]:
        if not isinstance(row, dict):
            continue
        item = {
            label: value
            for label, source_keys in fields
            if (value := _snapshot_value(row, *source_keys)) is not None
        }
        if item:
            projected.append(item)
    return projected


def _governance_snapshot_from_payload(
    ticker: str,
    corp: dict,
    payload: dict,
) -> dict[str, Any]:
    """Build a compact, public research snapshot without retaining raw bodies."""

    endpoints = [item for item in payload.get("endpoints", []) if isinstance(item, dict)]
    endpoint_rows = {
        str(item.get("key") or ""): [row for row in item.get("rows", []) if isinstance(row, dict)]
        for item in endpoints
    }
    endpoint_statuses: list[dict[str, str | None]] = []
    receipt_numbers: list[str] = []
    states: list[str] = []
    for item in endpoints:
        key = _compact_text(item.get("key"), limit=60)
        if not key:
            continue
        rows = endpoint_rows.get(key, [])
        receipt_no = next(
            (
                _snapshot_value(row, "rcept_no", limit=20)
                for row in rows
                if _snapshot_value(row, "rcept_no", limit=20)
            ),
            None,
        )
        if receipt_no:
            receipt_numbers.append(receipt_no)
        state = _compact_text(item.get("state"), limit=20) or "error"
        states.append(state)
        endpoint_statuses.append(
            {
                "key": key,
                "label": _compact_text(item.get("label"), limit=80) or key,
                "api_name": _compact_text(item.get("api_name"), limit=100) or None,
                "state": state,
                "dart_status": _compact_text(item.get("dart_status"), limit=12) or None,
                "receipt_no": receipt_no,
            }
        )

    error_count = sum(1 for state in states if state == "error")
    usable_count = sum(1 for state in states if state in {"ok", "empty"})
    if error_count and usable_count:
        status = "partial_success"
    elif error_count:
        status = "failed"
    elif any(state == "ok" for state in states):
        status = "success"
    else:
        status = "empty"

    summary = {
        "largest_holders": _snapshot_rows(
            endpoint_rows,
            "largest_holders",
            (
                ("name", ("nm", "mxmm_shrholdr_nm")),
                ("relationship", ("relate", "mxmm_shrholdr_relate")),
                ("stock_kind", ("stock_knd",)),
                ("shares", ("trmend_posesn_stock_co", "posesn_stock_co", "stock_co")),
                ("ownership_pct", ("trmend_posesn_stock_qota_rt", "qota_rt", "posesn_stock_qota_rt")),
            ),
            limit=6,
        ),
        "largest_holder_changes": _snapshot_rows(
            endpoint_rows,
            "largest_holder_changes",
            (
                ("date", ("change_on",)),
                ("name", ("mxmm_shrholdr_nm", "nm")),
                ("shares", ("posesn_stock_co", "trmend_posesn_stock_co")),
                ("ownership_pct", ("qota_rt", "trmend_posesn_stock_qota_rt")),
                ("cause", ("change_cause",)),
            ),
            limit=6,
        ),
        "executives": _snapshot_rows(
            endpoint_rows,
            "executives",
            (
                ("name", ("nm",)),
                ("position", ("ofcps",)),
                ("registered", ("rgist_exctv_at",)),
                ("full_time", ("fte_at",)),
                ("role", ("chrg_job",)),
                ("largest_holder_relation", ("mxmm_shrholdr_relate",)),
                ("tenure_end", ("tenure_end_on",)),
            ),
            limit=12,
        ),
        "employees": _snapshot_rows(
            endpoint_rows,
            "employees",
            (
                ("business_unit", ("fo_bbm",)),
                ("gender", ("sexdstn",)),
                ("regular", ("rgllbr_co",)),
                ("contract", ("cnttk_co",)),
                ("total", ("sm",)),
                ("average_tenure", ("avrg_cnwk_sdytrn",)),
                ("average_salary", ("jan_salary_am",)),
            ),
            limit=12,
        ),
        "share_structure": _snapshot_rows(
            endpoint_rows,
            "share_structure",
            (
                ("class", ("se",)),
                ("issued", ("istc_totqy",)),
                ("treasury", ("tesstk_co",)),
                ("float", ("distb_stock_co",)),
            ),
            limit=6,
        ),
        "dividends": _snapshot_rows(
            endpoint_rows,
            "dividends",
            (
                ("category", ("se",)),
                ("stock_kind", ("stock_knd",)),
                ("current", ("thstrm",)),
                ("prior", ("frmtrm",)),
                ("two_years_prior", ("lwfr",)),
            ),
            limit=8,
        ),
        "board_remuneration": _snapshot_rows(
            endpoint_rows,
            "board_remuneration",
            (
                ("category", ("se",)),
                ("people", ("nmpr",)),
                ("approved_amount", ("gmtsck_confm_amount",)),
            ),
            limit=8,
        ),
        "individual_remuneration": _snapshot_rows(
            endpoint_rows,
            "individual_remuneration",
            (
                ("name", ("nm",)),
                ("position", ("ofcps",)),
                ("total_amount", ("mendng_totamt",)),
                ("stock_compensation_amount", ("stk_bsd_pd_mendng_totamt_amt",)),
                ("stock_option_price", ("stk_opt_exrc_pr",)),
            ),
            limit=5,
        ),
    }
    source_receipt_no = next(iter(dict.fromkeys(receipt_numbers)), None)
    source_url = (
        f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={source_receipt_no}"
        if source_receipt_no
        else None
    )
    payload_for_hash = {
        "ticker": _compact_text(ticker, limit=12),
        "corp_code": _compact_text(corp.get("corp_code"), limit=12),
        "business_year": _compact_text(payload.get("business_year"), limit=8),
        "report_code": _compact_text(payload.get("report_code"), limit=12),
        "endpoint_statuses": endpoint_statuses,
        "summary": summary,
    }
    content_hash = hashlib.sha256(
        json.dumps(payload_for_hash, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "ticker": _compact_text(ticker, limit=12),
        "corp_code": _compact_text(corp.get("corp_code"), limit=12) or None,
        "corp_name": _compact_text(corp.get("corp_name"), limit=120) or None,
        "business_year": _compact_text(payload.get("business_year"), limit=8),
        "report_code": _compact_text(payload.get("report_code"), limit=12),
        "source_receipt_no": source_receipt_no,
        "source_url": source_url,
        "content_hash": content_hash,
        "captured_at_kst": current_storage_timestamp(),
        "status": status,
        "summary": summary,
        "endpoint_statuses": endpoint_statuses,
    }


def _store_governance_snapshot(settings: Settings, snapshot: dict[str, Any]) -> bool:
    """Persist only normalized facts; unchanged content remains immutable once."""

    summary_json = json.dumps(
        {
            "summary": snapshot.get("summary") or {},
            "endpoint_statuses": snapshot.get("endpoint_statuses") or [],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    connection = _connect(settings)
    try:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO dart_governance_snapshot(
                ticker, corp_code, corp_name, business_year, report_code,
                source_receipt_no, source_url, content_hash, captured_at_kst,
                status, summary_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot.get("ticker"),
                snapshot.get("corp_code"),
                snapshot.get("corp_name"),
                snapshot.get("business_year"),
                snapshot.get("report_code"),
                snapshot.get("source_receipt_no"),
                snapshot.get("source_url"),
                snapshot.get("content_hash"),
                snapshot.get("captured_at_kst"),
                snapshot.get("status"),
                summary_json,
            ),
        )
        connection.commit()
        return bool(cursor.rowcount)
    finally:
        connection.close()


def _latest_governance_snapshots(
    settings: Settings,
    *,
    business_year: str | None = None,
    limit: int = 24,
) -> list[dict[str, Any]]:
    connection = _connect(settings)
    try:
        if business_year:
            rows = connection.execute(
                """
                SELECT ticker, corp_code, corp_name, business_year, report_code,
                       source_receipt_no, source_url, captured_at_kst, status, summary_json
                  FROM dart_governance_snapshot
                 WHERE business_year = ? AND report_code = ?
                 ORDER BY captured_at_kst DESC, snapshot_id DESC
                 LIMIT ?
                """,
                (business_year, ANNUAL_REPORT_CODE, max(1, limit)),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT ticker, corp_code, corp_name, business_year, report_code,
                       source_receipt_no, source_url, captured_at_kst, status, summary_json
                  FROM dart_governance_snapshot
                 ORDER BY captured_at_kst DESC, snapshot_id DESC
                 LIMIT ?
                """,
                (max(1, limit),),
            ).fetchall()
    finally:
        connection.close()
    snapshots: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        item = dict(row)
        ticker = str(item.get("ticker") or "").strip()
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        try:
            stored = json.loads(str(item.pop("summary_json") or "{}"))
        except (TypeError, ValueError, json.JSONDecodeError):
            stored = {}
        item["summary"] = stored.get("summary") if isinstance(stored, dict) else {}
        item["endpoint_statuses"] = (
            stored.get("endpoint_statuses") if isinstance(stored, dict) else []
        )
        snapshots.append(item)
    return snapshots


def _governance_covered_tickers(settings: Settings, *, business_year: str) -> set[str]:
    connection = _connect(settings)
    try:
        rows = connection.execute(
            """
            SELECT DISTINCT ticker
              FROM dart_governance_snapshot
             WHERE business_year = ?
               AND report_code = ?
               AND status IN ('success', 'partial_success', 'empty')
            """,
            (business_year, ANNUAL_REPORT_CODE),
        ).fetchall()
    finally:
        connection.close()
    return {str(row["ticker"]).strip() for row in rows if str(row["ticker"]).strip()}


def build_dart_governance_status(
    settings: Settings,
    *,
    target_universe: dict | None,
) -> dict[str, Any]:
    """Return the secret-free M2 readiness and latest normalized snapshots."""

    universe = target_universe if isinstance(target_universe, dict) else {}
    business_year = str(current_storage_date().year - 1)
    targets = [
        str(ticker).strip()
        for ticker in universe.get("target_tickers") or []
        if re.fullmatch(r"\d{6}", str(ticker).strip())
    ]
    covered = _governance_covered_tickers(settings, business_year=business_year)
    snapshots = _latest_governance_snapshots(settings, business_year=business_year, limit=48)
    return {
        "state": "active",
        "business_year": business_year,
        "report_code": ANNUAL_REPORT_CODE,
        "scope": "가족 보유·관심 한국 종목의 최신 사업보고서 정형 API",
        "storage_policy": "원문·원본 응답·요청 URL 없이 정규화된 공개 사실과 content hash만 저장",
        "target_count": len(targets),
        "covered_tickers": sorted(covered),
        "missing_tickers": [ticker for ticker in targets if ticker not in covered],
        "coverage_rate": round(len(covered) / len(targets), 4) if targets else 1.0,
        "recent_snapshots": snapshots[:12],
        "endpoint_keys": list(GOVERNANCE_ENDPOINT_KEYS),
        "default_batch_tickers": DEFAULT_GOVERNANCE_BATCH_TICKERS,
        "max_batch_tickers": MAX_GOVERNANCE_BATCH_TICKERS,
    }


def refresh_dart_annual_report_governance(
    settings: Settings,
    *,
    target_universe: dict,
    client: Any,
    normalize_ticker: Callable[[str], str],
    tickers: list[str] | None = None,
    max_tickers: int = DEFAULT_GOVERNANCE_BATCH_TICKERS,
    business_year: int | str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Refresh a small, current-year governance bundle without raw retention."""

    started_at = current_storage_timestamp()
    year = str(business_year or current_storage_date().year - 1).strip()
    if not re.fullmatch(r"\d{4}", year):
        raise ValueError("business_year는 네 자리 사업연도여야 합니다.")
    limit = max(1, min(int(max_tickers or DEFAULT_GOVERNANCE_BATCH_TICKERS), MAX_GOVERNANCE_BATCH_TICKERS))
    explicit = bool(tickers)
    raw_candidates = tickers if explicit else list(target_universe.get("target_tickers") or [])
    candidates = list(
        dict.fromkeys(
            normalized
            for raw in raw_candidates
            if re.fullmatch(r"\d{6}", normalized := normalize_ticker(str(raw)))
        )
    )
    already_covered = _governance_covered_tickers(settings, business_year=year)
    eligible = candidates if force else [ticker for ticker in candidates if ticker not in already_covered]
    selected = eligible[:limit]
    skipped: list[dict[str, str]] = [
        {"ticker": ticker, "reason": "동일 사업연도 정규화 스냅샷이 이미 저장됨"}
        for ticker in candidates
        if ticker not in eligible
    ]
    saved: list[dict[str, str]] = []
    unchanged: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []

    if not getattr(client, "is_configured", False):
        status = "skipped"
        skipped.append({"reason": "DART_API_KEY가 설정되지 않아 외부 호출을 실행하지 않았습니다."})
    elif not selected:
        status = "skipped"
        skipped.append({"reason": "현재 사업연도 대상의 지배구조 스냅샷이 모두 저장되어 있습니다."})
    else:
        status = "success"
        for ticker in selected:
            try:
                corp, payload = client.fetch_annual_report_governance(
                    ticker,
                    business_year=year,
                    report_code=ANNUAL_REPORT_CODE,
                )
                snapshot = _governance_snapshot_from_payload(ticker, corp, payload)
                if snapshot["status"] == "failed":
                    failed.append({"ticker": ticker, "category": "provider_error", "error": "지배구조 API 묶음이 모두 실패했습니다."})
                    continue
                if _store_governance_snapshot(settings, snapshot):
                    saved.append({"ticker": ticker, "status": str(snapshot["status"])})
                else:
                    unchanged.append({"ticker": ticker, "reason": "공개 정형 사실이 이전 스냅샷과 동일함"})
            except DartQuotaExceeded as exc:
                failed.append(
                    {
                        "ticker": ticker,
                        "category": "quota_stopped",
                        "error": sanitize_dart_event_text(exc, secret=str(settings.dart_api_key or "")),
                    }
                )
                status = "quota_stopped"
                break
            except Exception as exc:
                failed.append(
                    {
                        "ticker": ticker,
                        "category": "provider_error",
                        "error": sanitize_dart_event_text(exc, secret=str(settings.dart_api_key or "")),
                    }
                )
        if failed and status == "success":
            status = "partial_success" if saved or unchanged else "failed"

    run_id = record_dart_lab_run(
        settings,
        started_at_kst=started_at,
        job_name="dart_annual_report_governance",
        status=status,
        selected_count=len(selected),
        saved_count=len(saved),
        skipped_count=len(skipped) + len(unchanged),
        failed_count=len(failed),
    )
    governance = build_dart_governance_status(settings, target_universe=target_universe)
    return {
        "status": status,
        "module": "dart_annual_report_governance_refresh",
        "run_id": run_id,
        "business_year": year,
        "report_code": ANNUAL_REPORT_CODE,
        "candidate_count": len(candidates),
        "selected_count": len(selected),
        "selected_tickers": selected,
        "saved_count": len(saved),
        "unchanged_count": len(unchanged),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "saved": saved[:30],
        "unchanged": unchanged[:30],
        "skipped": skipped[:30],
        "failed": failed[:30],
        "governance": governance,
        "quota": _quota_status(settings),
        "disclaimer": DISCLAIMER,
        "safety": {"orders": False, "messages": False, "account_changes": False},
    }


def record_dart_lab_run(
    settings: Settings,
    *,
    started_at_kst: str,
    job_name: str,
    status: str,
    selected_count: int,
    saved_count: int,
    skipped_count: int,
    failed_count: int,
) -> str:
    run_id = uuid4().hex
    connection = _connect(settings)
    try:
        connection.execute(
            """
            INSERT INTO dart_lab_run(
                run_id, activity_date, started_at_kst, completed_at_kst,
                job_name, status, selected_count, saved_count,
                skipped_count, failed_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                str(started_at_kst)[:10],
                started_at_kst,
                current_storage_timestamp(),
                _compact_text(job_name, limit=80),
                _compact_text(status, limit=40),
                max(0, int(selected_count)),
                max(0, int(saved_count)),
                max(0, int(skipped_count)),
                max(0, int(failed_count)),
            ),
        )
        connection.commit()
    finally:
        connection.close()
    return run_id


def _quota_status(settings: Settings) -> dict[str, Any]:
    today = current_storage_date().isoformat()
    connection = _connect(settings)
    try:
        row = connection.execute(
            """
            SELECT COALESCE(SUM(counted), 0) AS used,
                   SUM(CASE WHEN outcome = 'quota_stopped' THEN 1 ELSE 0 END) AS stopped
              FROM dart_request_event
             WHERE activity_date = ?
            """,
            (today,),
        ).fetchone()
    finally:
        connection.close()
    used = int(row["used"] or 0) if row else 0
    stopped = int(row["stopped"] or 0) if row else 0
    configured_cap = _configured_daily_self_cap(settings)
    cap = _daily_self_cap(settings)
    reference = _provider_limit_reference(settings)
    return {
        "date_kst": today,
        "recorded_requests": used,
        "configured_self_cap": configured_cap,
        "self_cap": cap,
        "self_cap_clamped": configured_cap != cap,
        "remaining_before_self_cap": max(0, cap - used),
        "self_cap_usage_rate": round(used / cap, 4) if cap else 0.0,
        "provider_limit_reference": reference,
        "self_cap_of_reference_rate": round(cap / reference, 4) if reference else None,
        "quota_stopped": bool(stopped),
        "quota_stop_event_count": stopped,
        "reference_note": (
            "OpenDART 공식 가이드는 일반적으로 20,000건 이상 요청에서 status=020이 "
            "발생한다고 안내하며, 실제 요청 제한은 다르게 설정될 수 있습니다."
        ),
    }


def _recent_activity(settings: Settings, *, days: int = 30) -> list[dict[str, Any]]:
    today = current_storage_date()
    start_date = today - timedelta(days=max(1, days) - 1)
    connection = _connect(settings)
    try:
        event_rows = connection.execute(
            """
            SELECT activity_date,
                   COALESCE(SUM(counted), 0) AS request_count,
                   SUM(CASE WHEN outcome IN ('dart_err','http_err','invalid_payload','exception') THEN 1 ELSE 0 END) AS failure_count,
                   SUM(CASE WHEN outcome = 'empty' THEN 1 ELSE 0 END) AS empty_count,
                   SUM(CASE WHEN outcome = 'quota_stopped' THEN 1 ELSE 0 END) AS quota_stop_count,
                   SUM(CASE WHEN outcome = 'in_flight' THEN 1 ELSE 0 END) AS in_flight_count
              FROM dart_request_event
             WHERE activity_date >= ?
             GROUP BY activity_date
            """,
            (start_date.isoformat(),),
        ).fetchall()
        run_rows = connection.execute(
            """
            SELECT activity_date, COUNT(*) AS run_count,
                   SUM(CASE WHEN status IN ('failed','partial_success','quota_stopped') THEN 1 ELSE 0 END) AS nonclean_run_count
              FROM dart_lab_run
             WHERE activity_date >= ?
             GROUP BY activity_date
            """,
            (start_date.isoformat(),),
        ).fetchall()
    finally:
        connection.close()
    events = {str(row["activity_date"]): dict(row) for row in event_rows}
    runs = {str(row["activity_date"]): dict(row) for row in run_rows}
    activity: list[dict[str, Any]] = []
    for offset in range(days):
        day = start_date + timedelta(days=offset)
        key = day.isoformat()
        event = events.get(key, {})
        run = runs.get(key, {})
        request_count = int(event.get("request_count") or 0)
        failure_count = int(event.get("failure_count") or 0)
        quota_stop_count = int(event.get("quota_stop_count") or 0)
        in_flight_count = int(event.get("in_flight_count") or 0)
        run_count = int(run.get("run_count") or 0)
        failure_rate = failure_count / request_count if request_count else 0.0
        if not request_count and not run_count and not quota_stop_count:
            status = "no_run"
        elif quota_stop_count:
            status = "quota_stopped"
        elif failure_count and failure_rate >= 0.1:
            status = "failed"
        elif failure_count or in_flight_count or int(run.get("nonclean_run_count") or 0):
            status = "partial_failure"
        else:
            status = "normal"
        activity.append(
            {
                "date_kst": key,
                "status": status,
                "request_count": request_count,
                "failure_count": failure_count,
                "failure_rate": round(failure_rate, 4),
                "empty_count": int(event.get("empty_count") or 0),
                "quota_stop_count": quota_stop_count,
                "run_count": run_count,
            }
        )
    return activity


def _recent_failures(settings: Settings, *, limit: int = MAX_RECENT_FAILURES) -> list[dict]:
    connection = _connect(settings)
    try:
        rows = connection.execute(
            """
            SELECT requested_at_kst, job_name, api_name, target, outcome,
                   http_status, dart_status, message
              FROM dart_request_event
             WHERE outcome IN ('dart_err','http_err','invalid_payload','exception','quota_stopped')
             ORDER BY event_id DESC
             LIMIT ?
            """,
            (max(1, min(int(limit), MAX_RECENT_FAILURES)),),
        ).fetchall()
    finally:
        connection.close()
    return [dict(row) for row in rows]


def _policy_checks(settings: Settings) -> list[dict[str, Any]]:
    path = dart_lab_db_path(settings)
    connection = _connect(settings)
    try:
        event_columns = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(dart_request_event)").fetchall()
        }
        governance_columns = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(dart_governance_snapshot)").fetchall()
        }
    finally:
        connection.close()
    forbidden_columns = {
        "crtfc_key",
        "api_key",
        "request_params",
        "request_url",
        "raw_response",
        "response_body",
        "raw_document",
    }
    required_governance_columns = {
        "ticker",
        "business_year",
        "report_code",
        "content_hash",
        "captured_at_kst",
        "status",
        "summary_json",
    }
    configured_key = str(settings.dart_api_key or "").strip()
    key_absent = True
    if configured_key:
        key_bytes = configured_key.encode("utf-8")
        for candidate in (path, Path(f"{path}-wal"), Path(f"{path}-shm")):
            if not candidate.exists():
                continue
            try:
                if key_bytes in candidate.read_bytes():
                    key_absent = False
                    break
            except OSError:
                key_absent = False
                break
    reference = _provider_limit_reference(settings)
    cap = _daily_self_cap(settings)
    checks = [
        (
            "a001_filter",
            ANNUAL_REPORT_DETAIL_TYPE == "A001" and ANNUAL_REPORT_CODE == "11011",
            "사업보고서 상세유형 A001·보고서 코드 11011 고정",
        ),
        (
            "body_status_whitelist",
            classify_dart_response(http_status=200, dart_status="010") == "dart_err"
            and classify_dart_response(http_status=200, dart_status="013") == "empty",
            "HTTP 200이어도 본문 status를 별도 판정",
        ),
        (
            "quota_preemption",
            0 < cap <= int(reference * 0.75),
            f"플랫폼 자체 한도 {cap:,}건 / 공식 안내 기준값 {reference:,}건",
        ),
        (
            "kst_timestamps",
            str(current_storage_datetime().tzinfo) in {"Asia/Seoul", "UTC+09:00"},
            "모든 원장 날짜와 시각을 Asia/Seoul 기준으로 기록",
        ),
        (
            "secret_free_schema",
            not (event_columns & forbidden_columns),
            "요청 원장에 인증키·전체 URL·요청 파라미터 컬럼 없음",
        ),
        (
            "governance_snapshot_schema",
            required_governance_columns <= governance_columns
            and not (governance_columns & forbidden_columns),
            "지배구조 스냅샷은 content hash·KST 시각·정규화 JSON만 저장하고 원문 응답은 저장하지 않음",
        ),
        (
            "secret_absent_from_ledger",
            key_absent,
            "현재 DART 인증키 바이트가 관측 원장에 없음",
        ),
    ]
    return [
        {"key": key, "status": "pass" if passed else "fail", "passed": passed, "detail": detail}
        for key, passed, detail in checks
    ]


def _is_annual_report_entry(entry: dict) -> bool:
    filing = entry.get("filing") if isinstance(entry, dict) else {}
    if not isinstance(filing, dict):
        return False
    if str(filing.get("detail_type") or "") == ANNUAL_REPORT_DETAIL_TYPE:
        return True
    report_name = str(filing.get("report_name") or "")
    return "사업보고서" in report_name and "반기보고서" not in report_name and "분기보고서" not in report_name


def build_dart_annual_report_lab_status(
    settings: Settings,
    *,
    dart_cache: dict | None,
    target_universe: dict | None,
) -> dict[str, Any]:
    cache = dart_cache if isinstance(dart_cache, dict) else {}
    universe = target_universe if isinstance(target_universe, dict) else {}
    entries = [
        item for item in (cache.get("entries") or {}).values()
        if isinstance(item, dict) and _is_annual_report_entry(item)
    ]
    entries.sort(
        key=lambda item: str(((item.get("filing") or {}).get("receipt_date")) or ""),
        reverse=True,
    )
    covered_tickers = sorted(
        {
            str(item.get("ticker") or "").strip()
            for item in entries
            if str(item.get("ticker") or "").strip()
        }
    )
    target_count = int(universe.get("target_count") or 0)
    policies = _policy_checks(settings)
    quota = _quota_status(settings)
    activity = _recent_activity(settings, days=30)
    failures = _recent_failures(settings)
    governance = build_dart_governance_status(settings, target_universe=universe)
    configured = bool(str(settings.dart_api_key or "").strip())
    if any(not item["passed"] for item in policies):
        overall = "degraded"
    elif quota["quota_stopped"]:
        overall = "quota_stopped"
    elif not configured:
        overall = "needs_configuration"
    else:
        overall = "ready"
    parsed_base = urlparse(str(settings.dart_base_url or ""))
    return {
        "status": "success",
        "module": "dart_annual_report_lab",
        "schema_version": SCHEMA_VERSION,
        "overall_state": overall,
        "generated_at_kst": current_storage_timestamp(),
        "scope": {
            "report_type": "사업보고서",
            "pblntf_detail_ty": ANNUAL_REPORT_DETAIL_TYPE,
            "reprt_code": ANNUAL_REPORT_CODE,
            "last_reprt_at": "Y",
            "universe": "가족 보유·관심 한국 종목",
        },
        "environment": {
            "api_key_configured": configured,
            "api_origin": f"{parsed_base.scheme}://{parsed_base.netloc}" if parsed_base.scheme else "확인 필요",
            "local_only": True,
            "timezone": "Asia/Seoul",
            "ledger_active": True,
        },
        "quota": quota,
        "policy_checks": policies,
        "activity_30d": activity,
        "recent_failures": failures,
        "coverage": {
            "target_count": target_count,
            "portfolio_target_count": int(universe.get("portfolio_count") or 0),
            "interest_target_count": int(universe.get("interest_count") or 0),
            "covered_ticker_count": len(covered_tickers),
            "coverage_rate": round(len(covered_tickers) / target_count, 4) if target_count else 1.0,
            "annual_report_entry_count": len(entries),
            "covered_tickers": covered_tickers,
            "missing_tickers": sorted(set(universe.get("target_tickers") or []) - set(covered_tickers)),
            "recent_reports": [
                {
                    "ticker": item.get("ticker"),
                    "company_name": item.get("corp_name") or (item.get("filing") or {}).get("corp_name"),
                    "report_name": (item.get("filing") or {}).get("report_name"),
                    "receipt_date": (item.get("filing") or {}).get("receipt_date"),
                    "source_url": (item.get("filing") or {}).get("source_url"),
                }
                for item in entries[:12]
            ],
            "cache_updated_at": cache.get("updated_at"),
        },
        "governance": governance,
        "milestones": [
            {
                "key": "collection",
                "label": "수집 상태",
                "state": "active",
                "detail": "A001 색인·오류 원장·쿼터 차단·커버리지",
            },
            {
                "key": "governance",
                "label": "지배구조·주주·보수",
                "state": governance.get("state") or "active",
                "detail": "최대주주·임원·직원·보수·배당·주식총수의 정규화 스냅샷(원문 응답 미저장)",
            },
            {
                "key": "business_text",
                "label": "사업의 내용 분석",
                "state": "planned",
                "detail": "원문 파싱, 연도 간 문구 diff, 위험 키워드 추이",
            },
            {
                "key": "screening",
                "label": "스크리닝",
                "state": "planned",
                "detail": "검증 가능한 불리언 필터만 제공·종합 점수와 랭킹 제외",
            },
        ],
        "screening_policy": {
            "boolean_filters_only": True,
            "composite_score_enabled": False,
            "ranking_enabled": False,
        },
        "source": {
            "name": "금융감독원 전자공시시스템 OpenDART",
            "guide_url": "https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001",
        },
        "disclaimer": DISCLAIMER,
        "safety": {"orders": False, "messages": False, "account_changes": False},
    }


def refresh_dart_annual_report_index(
    settings: Settings,
    *,
    dart_cache: dict,
    target_universe: dict,
    client: Any,
    normalize_ticker: Callable[[str], str],
    cache_key: Callable[[str, dict], str],
    filing_importance: Callable[[str], tuple[str, str, list[str]]],
    save_item: Callable[[str, dict, Settings], Any],
    write_cache: Callable[[Settings, dict], None],
    tickers: list[str] | None = None,
    max_tickers: int = 12,
    save_result: bool = True,
) -> dict[str, Any]:
    """Run one bounded, cursor-based A001 collection batch."""

    started_at = current_storage_timestamp()
    limit = max(1, min(int(max_tickers or 12), MAX_BATCH_TICKERS))
    explicit = bool(tickers)
    raw_candidates = tickers if explicit else list(target_universe.get("target_tickers") or [])
    candidates = list(
        dict.fromkeys(
            normalized
            for raw in raw_candidates
            if re.fullmatch(r"\d{6}", normalized := normalize_ticker(str(raw)))
        )
    )
    cursor = 0 if explicit or not candidates else _meta_int(settings, "a001_batch_cursor", 0) % len(candidates)
    if explicit:
        selected = candidates[:limit]
        next_cursor = 0
    else:
        rotated = candidates[cursor:] + candidates[:cursor]
        selected = rotated[:limit]
        next_cursor = (cursor + len(selected)) % len(candidates) if candidates else 0

    saved: list[dict] = []
    skipped: list[dict] = []
    failed: list[dict] = []
    entries = dart_cache.setdefault("entries", {})
    if not getattr(client, "is_configured", False):
        status = "skipped"
        skipped.append({"reason": "DART_API_KEY가 설정되지 않아 외부 호출을 실행하지 않았습니다."})
    else:
        status = "success"
        for ticker in selected:
            try:
                corp, filings = client.fetch_recent_filings(
                    ticker,
                    lookback_days=800,
                    page_count=10,
                    detail_type=ANNUAL_REPORT_DETAIL_TYPE,
                    final_reports_only=True,
                )
                if not filings:
                    skipped.append({"ticker": ticker, "reason": "최근 800일 A001 사업보고서 없음"})
                    continue
                for raw_filing in filings:
                    filing = {
                        **raw_filing,
                        "detail_type": ANNUAL_REPORT_DETAIL_TYPE,
                        "report_code": ANNUAL_REPORT_CODE,
                        "final_report_only": True,
                    }
                    key = cache_key(ticker, filing)
                    if key in entries:
                        skipped.append(
                            {"ticker": ticker, "rcept_no": filing.get("rcept_no"), "reason": "이미 저장됨"}
                        )
                        continue
                    importance, action, tags = filing_importance(str(filing.get("report_name") or ""))
                    storage = save_item(ticker, filing, settings) if save_result else None
                    entry = {
                        "ticker": ticker,
                        "corp_name": corp.get("corp_name"),
                        "filing": filing,
                        "importance": importance,
                        "action": action,
                        "tags": list(dict.fromkeys([*(tags or []), "annual_report", "A001"])),
                        "detected_at": current_storage_timestamp(),
                        "storage": storage.model_dump(mode="json") if storage else None,
                    }
                    entries[key] = entry
                    saved.append(entry)
            except DartQuotaExceeded as exc:
                failed.append(
                    {
                        "ticker": ticker,
                        "category": "quota_stopped",
                        "error": sanitize_dart_event_text(exc, secret=str(settings.dart_api_key or "")),
                    }
                )
                status = "quota_stopped"
                break
            except Exception as exc:  # provider errors are isolated per ticker
                failed.append(
                    {
                        "ticker": ticker,
                        "category": "provider_error",
                        "error": sanitize_dart_event_text(exc, secret=str(settings.dart_api_key or "")),
                    }
                )
        if failed and status == "success":
            status = "partial_success" if len(failed) < len(selected) else "failed"

    if not explicit:
        _write_meta(settings, "a001_batch_cursor", next_cursor)
    dart_cache["updated_at"] = current_storage_timestamp()
    dart_cache["entries"] = dict(list(entries.items())[-1200:])
    dart_cache["annual_report_lab"] = {
        "last_run_at": current_storage_timestamp(),
        "status": status,
        "selected_tickers": selected,
        "saved_count": len(saved),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "next_cursor": next_cursor,
    }
    write_cache(settings, dart_cache)
    run_id = record_dart_lab_run(
        settings,
        started_at_kst=started_at,
        job_name="dart_annual_report_a001",
        status=status,
        selected_count=len(selected),
        saved_count=len(saved),
        skipped_count=len(skipped),
        failed_count=len(failed),
    )
    return {
        "status": status,
        "module": "dart_annual_report_lab_refresh",
        "run_id": run_id,
        "scope": {
            "pblntf_detail_ty": ANNUAL_REPORT_DETAIL_TYPE,
            "reprt_code": ANNUAL_REPORT_CODE,
            "last_reprt_at": "Y",
        },
        "candidate_count": len(candidates),
        "selected_count": len(selected),
        "selected_tickers": selected,
        "saved_count": len(saved),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "skipped": skipped[:30],
        "failed": failed[:30],
        "next_cursor": next_cursor,
        "quota": _quota_status(settings),
        "disclaimer": DISCLAIMER,
        "safety": {"orders": False, "messages": False, "account_changes": False},
    }
