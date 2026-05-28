import hashlib
import json
import os
import sqlite3
import stat
import subprocess
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from app.application_models import JournalSourceTradesResponse, PortfolioResponse
from app.privacy import account_label_for_storage, redact_account_numbers
from app.settings import Settings


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect_db(settings: Settings) -> Iterator[sqlite3.Connection]:
    db_path = Path(settings.local_db_path)
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path
    connection = sqlite3.connect(
        db_path,
        timeout=max(settings.sqlite_busy_timeout_ms / 1000, 1),
    )
    try:
        connection.row_factory = sqlite3.Row
        _apply_sqlite_encryption_key(connection, settings)
        _configure_sqlite_connection(connection, settings)
        _restrict_db_file_permissions(db_path, settings)
        yield connection
        connection.commit()
    finally:
        connection.close()
        _restrict_db_file_permissions(db_path, settings)


def init_db(settings: Settings) -> None:
    with connect_db(settings) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS sync_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                broker TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                portfolio_holdings_count INTEGER NOT NULL DEFAULT 0,
                journal_items_count INTEGER NOT NULL DEFAULT 0,
                order_executions_count INTEGER NOT NULL DEFAULT 0,
                needs_review_count INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                deleted_at TEXT
            );

            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_run_id INTEGER NOT NULL,
                broker TEXT NOT NULL,
                synced_from TEXT NOT NULL,
                summary_json TEXT NOT NULL,
                holdings_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                deleted_at TEXT,
                FOREIGN KEY(sync_run_id) REFERENCES sync_runs(id)
            );

            CREATE TABLE IF NOT EXISTS journal_drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_run_id INTEGER NOT NULL,
                broker TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_key TEXT NOT NULL,
                ticker TEXT,
                name TEXT,
                draft_status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                dedup_keys_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                deleted_at TEXT,
                UNIQUE(source_type, source_key),
                FOREIGN KEY(sync_run_id) REFERENCES sync_runs(id)
            );

            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                draft_id INTEGER NOT NULL,
                broker TEXT NOT NULL,
                ticker TEXT,
                name TEXT,
                strategy_name TEXT NOT NULL DEFAULT '',
                setup_tags_json TEXT NOT NULL DEFAULT '[]',
                entry_reason TEXT NOT NULL DEFAULT '',
                exit_reason TEXT NOT NULL DEFAULT '',
                emotion_tags_json TEXT NOT NULL DEFAULT '[]',
                rule_followed INTEGER,
                good_points TEXT NOT NULL DEFAULT '',
                improvement_points TEXT NOT NULL DEFAULT '',
                memo TEXT NOT NULL DEFAULT '',
                manual_profit_loss_amount INTEGER,
                manual_profit_rate REAL,
                manual_buy_amount INTEGER,
                manual_sell_amount INTEGER,
                planned_entry_price REAL,
                actual_entry_price REAL,
                stop_loss_price REAL,
                target_price REAL,
                exit_price REAL,
                planned_risk_amount INTEGER,
                realized_r_multiple REAL,
                source_payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(draft_id),
                FOREIGN KEY(draft_id) REFERENCES journal_drafts(id)
            );

            CREATE TABLE IF NOT EXISTS history_sync_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                broker TEXT NOT NULL,
                status TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                total_days INTEGER NOT NULL,
                processed_days INTEGER NOT NULL DEFAULT 0,
                total_journal_items_count INTEGER NOT NULL DEFAULT 0,
                total_order_executions_count INTEGER NOT NULL DEFAULT 0,
                total_needs_review_count INTEGER NOT NULL DEFAULT 0,
                current_date TEXT,
                last_success_date TEXT,
                next_date TEXT,
                last_page_api_id TEXT,
                last_page_no INTEGER,
                last_cursor TEXT,
                retry_count INTEGER NOT NULL DEFAULT 0,
                last_backoff_seconds REAL,
                resume_from_job_id INTEGER,
                started_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                finished_at TEXT,
                error_message TEXT,
                deleted_at TEXT
            );

            CREATE TABLE IF NOT EXISTS manual_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date TEXT NOT NULL,
                broker TEXT NOT NULL DEFAULT 'MANUAL',
                account_name TEXT NOT NULL DEFAULT '기타',
                account_hash TEXT,
                dedup_key TEXT,
                dedup_status TEXT NOT NULL DEFAULT 'active',
                dedup_reason TEXT NOT NULL DEFAULT '',
                transaction_type TEXT NOT NULL DEFAULT 'trade',
                ticker TEXT,
                name TEXT,
                quantity REAL,
                price REAL,
                buy_amount INTEGER,
                sell_amount INTEGER,
                profit_loss_amount INTEGER,
                dividend_amount INTEGER,
                tax_amount INTEGER,
                commission_amount INTEGER,
                currency TEXT NOT NULL DEFAULT 'KRW',
                fx_rate_krw REAL,
                buy_amount_krw INTEGER,
                sell_amount_krw INTEGER,
                profit_loss_amount_krw INTEGER,
                dividend_amount_krw INTEGER,
                tax_amount_krw INTEGER,
                commission_amount_krw INTEGER,
                split_adjustment_ratio REAL NOT NULL DEFAULT 1,
                adjusted_quantity REAL,
                adjusted_price REAL,
                adjustment_note TEXT NOT NULL DEFAULT '',
                memo TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS fx_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                currency TEXT NOT NULL,
                rate_date TEXT NOT NULL,
                fx_rate_krw REAL NOT NULL,
                source TEXT NOT NULL DEFAULT 'manual',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(currency, rate_date)
            );

            CREATE TABLE IF NOT EXISTS corporate_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                action_type TEXT NOT NULL,
                effective_date TEXT NOT NULL,
                adjustment_ratio REAL NOT NULL,
                source TEXT NOT NULL DEFAULT 'manual',
                memo TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(ticker, action_type, effective_date)
            );

            CREATE TABLE IF NOT EXISTS brokerage_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                broker TEXT NOT NULL,
                environment TEXT NOT NULL,
                token_type TEXT NOT NULL DEFAULT 'Bearer',
                access_token TEXT NOT NULL,
                refresh_token TEXT,
                expires_dt TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                issued_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(broker, environment)
            );

            CREATE TABLE IF NOT EXISTS trade_dedup_keys (
                dedup_key TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_key TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        _ensure_column(connection, "journal_drafts", "dedup_keys_json", "TEXT NOT NULL DEFAULT '[]'")
        _ensure_column(connection, "journal_entries", "manual_profit_loss_amount", "INTEGER")
        _ensure_column(connection, "journal_entries", "manual_profit_rate", "REAL")
        _ensure_column(connection, "journal_entries", "manual_buy_amount", "INTEGER")
        _ensure_column(connection, "journal_entries", "manual_sell_amount", "INTEGER")
        _ensure_column(connection, "journal_entries", "strategy_name", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(connection, "journal_entries", "setup_tags_json", "TEXT NOT NULL DEFAULT '[]'")
        _ensure_column(connection, "journal_entries", "planned_entry_price", "REAL")
        _ensure_column(connection, "journal_entries", "actual_entry_price", "REAL")
        _ensure_column(connection, "journal_entries", "stop_loss_price", "REAL")
        _ensure_column(connection, "journal_entries", "target_price", "REAL")
        _ensure_column(connection, "journal_entries", "exit_price", "REAL")
        _ensure_column(connection, "journal_entries", "planned_risk_amount", "INTEGER")
        _ensure_column(connection, "journal_entries", "realized_r_multiple", "REAL")
        _ensure_column(connection, "sync_runs", "deleted_at", "TEXT")
        _ensure_column(connection, "portfolio_snapshots", "deleted_at", "TEXT")
        _ensure_column(connection, "history_sync_jobs", "current_date", "TEXT")
        _ensure_column(connection, "history_sync_jobs", "last_success_date", "TEXT")
        _ensure_column(connection, "history_sync_jobs", "next_date", "TEXT")
        _ensure_column(connection, "history_sync_jobs", "last_page_api_id", "TEXT")
        _ensure_column(connection, "history_sync_jobs", "last_page_no", "INTEGER")
        _ensure_column(connection, "history_sync_jobs", "last_cursor", "TEXT")
        _ensure_column(
            connection, "history_sync_jobs", "retry_count", "INTEGER NOT NULL DEFAULT 0"
        )
        _ensure_column(connection, "history_sync_jobs", "last_backoff_seconds", "REAL")
        _ensure_column(connection, "history_sync_jobs", "resume_from_job_id", "INTEGER")
        _ensure_column(connection, "history_sync_jobs", "deleted_at", "TEXT")
        _ensure_column(connection, "brokerage_tokens", "refresh_token", "TEXT")
        _ensure_column(connection, "journal_drafts", "deleted_at", "TEXT")
        _ensure_column(connection, "manual_transactions", "account_hash", "TEXT")
        _ensure_column(connection, "manual_transactions", "dedup_key", "TEXT")
        _ensure_column(
            connection,
            "manual_transactions",
            "dedup_status",
            "TEXT NOT NULL DEFAULT 'active'",
        )
        _ensure_column(
            connection,
            "manual_transactions",
            "dedup_reason",
            "TEXT NOT NULL DEFAULT ''",
        )
        _ensure_column(connection, "manual_transactions", "currency", "TEXT NOT NULL DEFAULT 'KRW'")
        _ensure_column(connection, "manual_transactions", "fx_rate_krw", "REAL")
        _ensure_column(connection, "manual_transactions", "buy_amount_krw", "INTEGER")
        _ensure_column(connection, "manual_transactions", "sell_amount_krw", "INTEGER")
        _ensure_column(connection, "manual_transactions", "profit_loss_amount_krw", "INTEGER")
        _ensure_column(connection, "manual_transactions", "dividend_amount_krw", "INTEGER")
        _ensure_column(connection, "manual_transactions", "tax_amount_krw", "INTEGER")
        _ensure_column(connection, "manual_transactions", "commission_amount", "INTEGER")
        _ensure_column(connection, "manual_transactions", "commission_amount_krw", "INTEGER")
        _ensure_column(
            connection,
            "manual_transactions",
            "split_adjustment_ratio",
            "REAL NOT NULL DEFAULT 1",
        )
        _ensure_column(connection, "manual_transactions", "adjusted_quantity", "REAL")
        _ensure_column(connection, "manual_transactions", "adjusted_price", "REAL")
        _ensure_column(
            connection,
            "manual_transactions",
            "adjustment_note",
            "TEXT NOT NULL DEFAULT ''",
        )


def _configure_sqlite_connection(
    connection: sqlite3.Connection,
    settings: Settings,
) -> None:
    connection.execute(f"PRAGMA busy_timeout = {int(settings.sqlite_busy_timeout_ms)}")
    connection.execute("PRAGMA foreign_keys = ON")
    if settings.sqlite_enable_wal:
        connection.execute("PRAGMA journal_mode = WAL")
        synchronous = settings.sqlite_synchronous.strip().upper() or "NORMAL"
        if synchronous not in {"OFF", "NORMAL", "FULL", "EXTRA"}:
            synchronous = "NORMAL"
        connection.execute(f"PRAGMA synchronous = {synchronous}")


def _apply_sqlite_encryption_key(
    connection: sqlite3.Connection,
    settings: Settings,
) -> None:
    encryption_key = settings.sqlite_encryption_key.strip()
    if not encryption_key:
        return
    escaped_key = encryption_key.replace("'", "''")
    connection.execute(f"PRAGMA key = '{escaped_key}'")
    cipher_row = connection.execute("PRAGMA cipher_version").fetchone()
    if not cipher_row:
        raise RuntimeError(
            "SQLITE_ENCRYPTION_KEY was provided, but this sqlite driver does not "
            "support SQLCipher. Install a SQLCipher-enabled sqlite driver or remove "
            "the key for local development."
        )


def _restrict_db_file_permissions(db_path: Path, settings: Settings) -> None:
    if not settings.sqlite_restrict_file_permissions:
        return
    for path in [db_path, Path(f"{db_path}-wal"), Path(f"{db_path}-shm")]:
        if not path.exists():
            continue
        try:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass
        if os.name == "nt":
            _restrict_windows_file_acl(path)


def _restrict_windows_file_acl(path: Path) -> None:
    user_name = os.environ.get("USERNAME")
    if not user_name:
        return
    try:
        subprocess.run(
            [
                "icacls",
                str(path),
                "/inheritance:r",
                "/grant:r",
                f"{user_name}:F",
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def create_manual_transaction(
    settings: Settings,
    trade_date: str,
    broker: str,
    account_name: str,
    transaction_type: str,
    ticker: str,
    name: str,
    quantity: float | None = None,
    price: float | None = None,
    buy_amount: int | None = None,
    sell_amount: int | None = None,
    profit_loss_amount: int | None = None,
    dividend_amount: int | None = None,
    tax_amount: int | None = None,
    commission_amount: int | None = None,
    currency: str = "KRW",
    fx_rate_krw: float | None = None,
    split_adjustment_ratio: float = 1.0,
    adjustment_note: str = "",
    memo: str = "",
) -> dict:
    now = utc_now_iso()
    normalized_currency = _normalize_currency(currency)
    effective_fx_rate = _resolve_fx_rate_krw(
        settings=settings,
        currency=normalized_currency,
        trade_date=trade_date,
        explicit_fx_rate=fx_rate_krw,
    )
    storage_account_name, account_hash = account_label_for_storage(
        account_name,
        settings.secret_salt,
    )
    safe_split_ratio = _normalize_adjustment_ratio(split_adjustment_ratio)
    adjusted_quantity = (
        round(float(quantity) * safe_split_ratio, 8) if quantity is not None else None
    )
    adjusted_price = round(float(price) / safe_split_ratio, 8) if price is not None else None
    with connect_db(settings) as connection:
        dedup_key = _trade_dedup_key(
            trade_date=trade_date,
            ticker=ticker,
            quantity=quantity,
            price=price,
        )
        duplicate_source = _get_dedup_source(connection, dedup_key)
        dedup_status = "duplicate_kiwoom" if duplicate_source == "kiwoom" else "active"
        dedup_reason = (
            "키움 원천 거래와 날짜/종목/수량/가격이 같아 분석 합산에서 제외됩니다."
            if dedup_status == "duplicate_kiwoom"
            else ""
        )
        cursor = connection.execute(
            """
            INSERT INTO manual_transactions
              (trade_date, broker, account_name, account_hash, dedup_key, dedup_status,
               dedup_reason, transaction_type, ticker, name,
               quantity, price, buy_amount, sell_amount, profit_loss_amount,
               dividend_amount, tax_amount, commission_amount, currency, fx_rate_krw,
               buy_amount_krw, sell_amount_krw, profit_loss_amount_krw,
               dividend_amount_krw, tax_amount_krw, commission_amount_krw,
               split_adjustment_ratio,
               adjusted_quantity, adjusted_price, adjustment_note,
               memo, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade_date,
                broker.strip() or "MANUAL",
                storage_account_name,
                account_hash,
                dedup_key,
                dedup_status,
                dedup_reason,
                transaction_type.strip().lower() or "trade",
                ticker.strip().upper() or None,
                name.strip(),
                quantity,
                price,
                buy_amount,
                sell_amount,
                profit_loss_amount,
                dividend_amount,
                tax_amount,
                commission_amount,
                normalized_currency,
                effective_fx_rate,
                _convert_to_krw(buy_amount, effective_fx_rate),
                _convert_to_krw(sell_amount, effective_fx_rate),
                _convert_to_krw(profit_loss_amount, effective_fx_rate),
                _convert_to_krw(dividend_amount, effective_fx_rate),
                _convert_to_krw(tax_amount, effective_fx_rate),
                _convert_to_krw(commission_amount, effective_fx_rate),
                safe_split_ratio,
                adjusted_quantity,
                adjusted_price,
                adjustment_note,
                memo,
                now,
                now,
            ),
        )
        row = connection.execute(
            "SELECT * FROM manual_transactions WHERE id = ?",
            (int(cursor.lastrowid),),
        ).fetchone()
    return dict(row)


def upsert_fx_rate(
    settings: Settings,
    currency: str,
    rate_date: str,
    fx_rate_krw: float,
    source: str = "manual",
) -> dict:
    now = utc_now_iso()
    normalized_currency = _normalize_currency(currency)
    with connect_db(settings) as connection:
        connection.execute(
            """
            INSERT INTO fx_rates
              (currency, rate_date, fx_rate_krw, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(currency, rate_date) DO UPDATE SET
                fx_rate_krw = excluded.fx_rate_krw,
                source = excluded.source,
                updated_at = excluded.updated_at
            """,
            (normalized_currency, rate_date, fx_rate_krw, source, now, now),
        )
        row = connection.execute(
            """
            SELECT *
            FROM fx_rates
            WHERE currency = ? AND rate_date = ?
            """,
            (normalized_currency, rate_date),
        ).fetchone()
    return dict(row)


def get_fx_rate_krw(
    settings: Settings,
    currency: str,
    rate_date: str,
) -> float | None:
    normalized_currency = _normalize_currency(currency)
    if normalized_currency == "KRW":
        return 1.0
    with connect_db(settings) as connection:
        row = connection.execute(
            """
            SELECT fx_rate_krw
            FROM fx_rates
            WHERE currency = ? AND rate_date <= ?
            ORDER BY rate_date DESC
            LIMIT 1
            """,
            (normalized_currency, rate_date),
        ).fetchone()
    return float(row["fx_rate_krw"]) if row else None


def upsert_corporate_action(
    settings: Settings,
    ticker: str,
    action_type: str,
    effective_date: str,
    adjustment_ratio: float,
    source: str = "manual",
    memo: str = "",
) -> dict:
    now = utc_now_iso()
    normalized_ticker = (ticker or "").strip().upper()
    normalized_action = (action_type or "split").strip().lower()
    with connect_db(settings) as connection:
        connection.execute(
            """
            INSERT INTO corporate_actions
              (ticker, action_type, effective_date, adjustment_ratio,
               source, memo, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker, action_type, effective_date) DO UPDATE SET
                adjustment_ratio = excluded.adjustment_ratio,
                source = excluded.source,
                memo = excluded.memo,
                updated_at = excluded.updated_at
            """,
            (
                normalized_ticker,
                normalized_action,
                effective_date,
                _normalize_adjustment_ratio(adjustment_ratio),
                source,
                memo,
                now,
                now,
            ),
        )
        row = connection.execute(
            """
            SELECT *
            FROM corporate_actions
            WHERE ticker = ? AND action_type = ? AND effective_date = ?
            """,
            (normalized_ticker, normalized_action, effective_date),
        ).fetchone()
    return dict(row)


def _normalize_currency(currency: str | None) -> str:
    return (currency or "KRW").strip().upper()[:3] or "KRW"


def _normalize_adjustment_ratio(value: float | int | None) -> float:
    ratio = float(value or 1)
    return ratio if ratio > 0 else 1.0


def _resolve_fx_rate_krw(
    settings: Settings,
    currency: str,
    trade_date: str,
    explicit_fx_rate: float | None = None,
) -> float | None:
    if currency == "KRW":
        return 1.0
    if explicit_fx_rate and explicit_fx_rate > 0:
        return float(explicit_fx_rate)
    return get_fx_rate_krw(settings, currency, trade_date)


def _convert_to_krw(value: int | float | None, fx_rate_krw: float | None) -> int | None:
    if value is None or fx_rate_krw is None:
        return None
    return int(round(float(value) * float(fx_rate_krw)))


def _trade_dedup_key(
    trade_date: str | None,
    ticker: str | None,
    quantity: float | int | None,
    price: float | int | None,
) -> str | None:
    if not trade_date or not ticker or quantity in (None, "") or price in (None, ""):
        return None
    try:
        normalized_quantity = f"{float(quantity):.8f}".rstrip("0").rstrip(".")
        normalized_price = f"{float(price):.4f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return None
    if not normalized_quantity or not normalized_price:
        return None
    return ":".join(
        [
            _analytics_date(str(trade_date)).replace("-", ""),
            str(ticker).strip().upper().lstrip("A"),
            normalized_quantity,
            normalized_price,
        ]
    )


def _stable_source_key(prefix: str, values: dict) -> str:
    payload = json.dumps(values, ensure_ascii=False, sort_keys=True)
    return f"{prefix}:{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]}"


def _get_dedup_source(
    connection: sqlite3.Connection,
    dedup_key: str | None,
) -> str | None:
    if not dedup_key:
        return None
    row = connection.execute(
        "SELECT source FROM trade_dedup_keys WHERE dedup_key = ?",
        (dedup_key,),
    ).fetchone()
    return row["source"] if row else None


def _register_trade_dedup_keys(
    connection: sqlite3.Connection,
    dedup_keys: list[str],
    source: str,
    source_type: str,
    source_key: str,
    now: str,
) -> None:
    for dedup_key in sorted(set(key for key in dedup_keys if key)):
        connection.execute(
            """
            INSERT INTO trade_dedup_keys
              (dedup_key, source, source_type, source_key, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(dedup_key) DO UPDATE SET
              source = CASE
                WHEN excluded.source = 'kiwoom' THEN excluded.source
                ELSE trade_dedup_keys.source
              END,
              source_type = CASE
                WHEN excluded.source = 'kiwoom' THEN excluded.source_type
                ELSE trade_dedup_keys.source_type
              END,
              source_key = CASE
                WHEN excluded.source = 'kiwoom' THEN excluded.source_key
                ELSE trade_dedup_keys.source_key
              END,
              updated_at = excluded.updated_at
            """,
            (dedup_key, source, source_type, source_key, now),
        )
    if source == "kiwoom":
        _mark_manual_duplicates_for_kiwoom_keys(connection, dedup_keys, now)


def _mark_manual_duplicates_for_kiwoom_keys(
    connection: sqlite3.Connection,
    dedup_keys: list[str],
    now: str,
) -> None:
    active_keys = sorted(set(key for key in dedup_keys if key))
    if not active_keys:
        return
    placeholders = ",".join("?" for _ in active_keys)
    connection.execute(
        f"""
        UPDATE manual_transactions
        SET dedup_status = ?,
            dedup_reason = ?,
            updated_at = ?
        WHERE dedup_key IN ({placeholders})
          AND dedup_status != ?
        """,
        (
            "duplicate_kiwoom",
            "키움 원천 거래와 날짜/종목/수량/가격이 같아 분석 합산에서 제외됩니다.",
            now,
            *active_keys,
            "duplicate_kiwoom",
        ),
    )


def count_manual_transactions(settings: Settings) -> int:
    with connect_db(settings) as connection:
        row = connection.execute("SELECT COUNT(*) AS total FROM manual_transactions").fetchone()
    return int(row["total"] if row else 0)


def list_manual_transactions(
    settings: Settings,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    with connect_db(settings) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM manual_transactions
            ORDER BY trade_date DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
    return [dict(row) for row in rows]


def delete_manual_transaction(settings: Settings, transaction_id: int) -> dict:
    with connect_db(settings) as connection:
        row = connection.execute(
            "SELECT id FROM manual_transactions WHERE id = ?",
            (transaction_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"Manual transaction not found: {transaction_id}")
        connection.execute(
            "DELETE FROM manual_transactions WHERE id = ?",
            (transaction_id,),
        )
    return {"deleted_transaction_id": transaction_id}


def get_brokerage_token(
    settings: Settings,
    broker: str,
    environment: str,
) -> dict | None:
    with connect_db(settings) as connection:
        row = connection.execute(
            """
            SELECT *
            FROM brokerage_tokens
            WHERE broker = ? AND environment = ?
            """,
            (broker, environment),
        ).fetchone()
    return dict(row) if row else None


def upsert_brokerage_token(
    settings: Settings,
    broker: str,
    environment: str,
    token_type: str,
    access_token: str,
    expires_dt: str,
    expires_at: str,
    refresh_token: str | None = None,
) -> dict:
    now = utc_now_iso()
    with connect_db(settings) as connection:
        connection.execute(
            """
            INSERT INTO brokerage_tokens
              (broker, environment, token_type, access_token, refresh_token,
               expires_dt, expires_at, issued_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(broker, environment) DO UPDATE SET
                token_type = excluded.token_type,
                access_token = excluded.access_token,
                refresh_token = COALESCE(excluded.refresh_token, brokerage_tokens.refresh_token),
                expires_dt = excluded.expires_dt,
                expires_at = excluded.expires_at,
                issued_at = excluded.issued_at,
                updated_at = excluded.updated_at
            """,
            (
                broker,
                environment,
                token_type or "Bearer",
                access_token,
                refresh_token,
                expires_dt,
                expires_at,
                now,
                now,
            ),
        )
    return get_brokerage_token(settings, broker, environment) or {}


def delete_brokerage_token(settings: Settings, broker: str, environment: str) -> dict:
    with connect_db(settings) as connection:
        connection.execute(
            """
            DELETE FROM brokerage_tokens
            WHERE broker = ? AND environment = ?
            """,
            (broker, environment),
        )
    return {"deleted": True, "broker": broker, "environment": environment}


def start_history_sync_job(
    settings: Settings,
    broker: str,
    start_date: str,
    end_date: str,
    total_days: int,
    resume_from_job_id: int | None = None,
) -> dict:
    now = utc_now_iso()
    with connect_db(settings) as connection:
        cursor = connection.execute(
            """
            INSERT INTO history_sync_jobs
              (broker, status, start_date, end_date, total_days, resume_from_job_id,
               started_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                broker,
                "running",
                start_date,
                end_date,
                total_days,
                resume_from_job_id,
                now,
                now,
            ),
        )
        job_id = int(cursor.lastrowid)
    return get_history_sync_job(settings, job_id) or {}


def get_resumable_history_sync_job(
    settings: Settings,
    broker: str,
    start_date: str,
    end_date: str,
) -> dict | None:
    with connect_db(settings) as connection:
        row = connection.execute(
            """
            SELECT *
            FROM history_sync_jobs
            WHERE broker = ?
              AND start_date = ?
              AND end_date = ?
              AND status IN ('failed', 'cancelled', 'paused')
              AND next_date IS NOT NULL
              AND deleted_at IS NULL
            ORDER BY id DESC
            LIMIT 1
            """,
            (broker, start_date, end_date),
        ).fetchone()
    return _format_history_sync_job(dict(row)) if row else None


def pause_stale_history_sync_jobs(settings: Settings) -> int:
    now = utc_now_iso()
    with connect_db(settings) as connection:
        cursor = connection.execute(
            """
            UPDATE history_sync_jobs
            SET status = ?,
                current_date = NULL,
                next_date = COALESCE("current_date", next_date),
                updated_at = ?,
                error_message = ?
            WHERE status IN ('running', 'cancel_requested')
              AND deleted_at IS NULL
            """,
            (
                "paused",
                now,
                "서버가 재시작되어 작업이 일시정지되었습니다. 같은 기간으로 다시 불러오면 이어받습니다.",
            ),
        )
    return int(cursor.rowcount or 0)


def mark_history_sync_job_day_started(
    settings: Settings,
    job_id: int,
    target_date: str,
) -> None:
    with connect_db(settings) as connection:
        connection.execute(
            """
            UPDATE history_sync_jobs
            SET current_date = ?,
                next_date = ?,
                last_page_api_id = NULL,
                last_page_no = NULL,
                last_cursor = NULL,
                retry_count = 0,
                last_backoff_seconds = NULL,
                updated_at = ?
            WHERE id = ?
              AND deleted_at IS NULL
            """,
            (target_date, target_date, utc_now_iso(), job_id),
        )


def mark_history_sync_job_page_checkpoint(
    settings: Settings,
    job_id: int,
    target_date: str,
    api_id: str,
    page_no: int,
    cursor: str | None,
) -> None:
    with connect_db(settings) as connection:
        connection.execute(
            """
            UPDATE history_sync_jobs
            SET current_date = ?,
                next_date = ?,
                last_page_api_id = ?,
                last_page_no = ?,
                last_cursor = ?,
                updated_at = ?
            WHERE id = ?
              AND deleted_at IS NULL
            """,
            (
                target_date,
                target_date,
                api_id,
                page_no,
                cursor or "",
                utc_now_iso(),
                job_id,
            ),
        )


def mark_history_sync_job_retry(
    settings: Settings,
    job_id: int,
    target_date: str,
    retry_count: int,
    backoff_seconds: float,
    error_message: str,
) -> None:
    with connect_db(settings) as connection:
        connection.execute(
            """
            UPDATE history_sync_jobs
            SET current_date = ?,
                next_date = ?,
                retry_count = ?,
                last_backoff_seconds = ?,
                error_message = ?,
                updated_at = ?
            WHERE id = ?
              AND deleted_at IS NULL
            """,
            (
                target_date,
                target_date,
                retry_count,
                backoff_seconds,
                error_message[:1000],
                utc_now_iso(),
                job_id,
            ),
        )


def update_history_sync_job_progress(
    settings: Settings,
    job_id: int,
    journal_items_count: int,
    order_executions_count: int,
    needs_review_count: int,
    completed_date: str | None = None,
    next_date: str | None = None,
) -> None:
    with connect_db(settings) as connection:
        connection.execute(
            """
            UPDATE history_sync_jobs
            SET processed_days = processed_days + 1,
                total_journal_items_count = total_journal_items_count + ?,
                total_order_executions_count = total_order_executions_count + ?,
                total_needs_review_count = total_needs_review_count + ?,
                current_date = NULL,
                last_success_date = COALESCE(?, last_success_date),
                next_date = ?,
                last_page_api_id = NULL,
                last_page_no = NULL,
                last_cursor = NULL,
                retry_count = 0,
                last_backoff_seconds = NULL,
                error_message = NULL,
                updated_at = ?
            WHERE id = ?
              AND deleted_at IS NULL
            """,
            (
                journal_items_count,
                order_executions_count,
                needs_review_count,
                completed_date,
                next_date,
                utc_now_iso(),
                job_id,
            ),
        )


def finish_history_sync_job(settings: Settings, job_id: int) -> None:
    now = utc_now_iso()
    with connect_db(settings) as connection:
        connection.execute(
            """
            UPDATE history_sync_jobs
            SET status = ?,
                current_date = NULL,
                next_date = NULL,
                updated_at = ?,
                finished_at = ?
            WHERE id = ?
            """,
            ("success", now, now, job_id),
        )


def cancel_history_sync_job(settings: Settings, job_id: int) -> dict | None:
    now = utc_now_iso()
    with connect_db(settings) as connection:
        connection.execute(
            """
            UPDATE history_sync_jobs
            SET status = ?, updated_at = ?
            WHERE id = ? AND status IN ('running', 'cancel_requested')
              AND deleted_at IS NULL
            """,
            ("cancel_requested", now, job_id),
        )
    return get_history_sync_job(settings, job_id)


def finish_cancelled_history_sync_job(settings: Settings, job_id: int) -> None:
    now = utc_now_iso()
    with connect_db(settings) as connection:
        connection.execute(
            """
            UPDATE history_sync_jobs
            SET status = ?, current_date = NULL, updated_at = ?, finished_at = ?
            WHERE id = ?
              AND deleted_at IS NULL
            """,
            ("cancelled", now, now, job_id),
        )


def fail_history_sync_job(
    settings: Settings,
    job_id: int,
    error_message: str,
) -> None:
    now = utc_now_iso()
    with connect_db(settings) as connection:
        connection.execute(
            """
            UPDATE history_sync_jobs
            SET status = ?, updated_at = ?, finished_at = ?, error_message = ?
            WHERE id = ?
              AND deleted_at IS NULL
            """,
            ("failed", now, now, error_message[:1000], job_id),
        )


def get_history_sync_job(settings: Settings, job_id: int) -> dict | None:
    with connect_db(settings) as connection:
        row = connection.execute(
            """
            SELECT *
            FROM history_sync_jobs
            WHERE id = ?
              AND deleted_at IS NULL
            """,
            (job_id,),
        ).fetchone()
    return _format_history_sync_job(dict(row)) if row else None


def clear_imported_sync_records(settings: Settings, confirm: bool = False) -> dict:
    with connect_db(settings) as connection:
        active_count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM history_sync_jobs
            WHERE status IN ('running', 'cancel_requested')
              AND deleted_at IS NULL
            """
        ).fetchone()["count"]
        if active_count:
            raise ValueError("진행 중인 과거 거래 불러오기를 먼저 멈춰 주세요.")

        tables = [
            "journal_drafts",
            "portfolio_snapshots",
            "sync_runs",
            "history_sync_jobs",
        ]
        record_counts = {}
        for table in tables:
            record_counts[table] = connection.execute(
                f"SELECT COUNT(*) AS count FROM {table} WHERE deleted_at IS NULL"
            ).fetchone()["count"]

        total_count = sum(int(value or 0) for value in record_counts.values())
        if not confirm:
            return {
                "requires_confirm": True,
                "record_count": total_count,
                "record_counts": record_counts,
                "preserved_journal_entries": True,
            }

        now = utc_now_iso()
        for table in tables:
            connection.execute(
                f"UPDATE {table} SET deleted_at = ? WHERE deleted_at IS NULL",
                (now,),
            )

    return {
        "deleted": True,
        "soft_deleted": record_counts,
        "record_count": total_count,
        "preserved_journal_entries": True,
    }


def get_latest_history_sync_job(settings: Settings) -> dict | None:
    with connect_db(settings) as connection:
        row = connection.execute(
            """
            SELECT *
            FROM history_sync_jobs
            WHERE deleted_at IS NULL
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    return _format_history_sync_job(dict(row)) if row else None


def start_sync_run(settings: Settings, broker: str) -> int:
    now = utc_now_iso()
    with connect_db(settings) as connection:
        cursor = connection.execute(
            """
            INSERT INTO sync_runs (broker, status, started_at)
            VALUES (?, ?, ?)
            """,
            (broker, "running", now),
        )
        return int(cursor.lastrowid)


def finish_sync_run(
    settings: Settings,
    sync_run_id: int,
    portfolio: PortfolioResponse,
    journal: JournalSourceTradesResponse,
) -> None:
    now = utc_now_iso()
    with connect_db(settings) as connection:
        connection.execute(
            """
            UPDATE sync_runs
            SET status = ?,
                finished_at = ?,
                portfolio_holdings_count = ?,
                journal_items_count = ?,
                order_executions_count = ?,
                needs_review_count = ?
            WHERE id = ?
            """,
            (
                "success",
                now,
                portfolio.holdings_count,
                journal.trade_journal_items_count,
                journal.order_executions_count,
                journal.needs_review_count,
                sync_run_id,
            ),
        )
        connection.execute(
            """
            INSERT INTO portfolio_snapshots
              (sync_run_id, broker, synced_from, summary_json, holdings_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                sync_run_id,
                portfolio.broker,
                portfolio.synced_from,
                portfolio.summary.model_dump_json(),
                json.dumps(
                    [item.model_dump(mode="json") for item in portfolio.holdings],
                    ensure_ascii=False,
                ),
                now,
            ),
        )
        _upsert_trade_journal_drafts(
            connection,
            sync_run_id,
            journal,
            now,
            settings.secret_salt,
        )
        _upsert_order_execution_drafts(
            connection,
            sync_run_id,
            journal,
            now,
            settings.secret_salt,
        )


def fail_sync_run(settings: Settings, sync_run_id: int, error_message: str) -> None:
    with connect_db(settings) as connection:
        connection.execute(
            """
            UPDATE sync_runs
            SET status = ?, finished_at = ?, error_message = ?
            WHERE id = ?
            """,
            ("failed", utc_now_iso(), error_message[:1000], sync_run_id),
        )


def get_latest_sync_run(settings: Settings) -> dict | None:
    with connect_db(settings) as connection:
        row = connection.execute(
            """
            SELECT *
            FROM sync_runs
            WHERE deleted_at IS NULL
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    return dict(row) if row else None


def count_journal_drafts(
    settings: Settings,
    include_completed: bool = False,
) -> int:
    status_filter = "" if include_completed else "AND draft_status = 'needs_review'"
    with connect_db(settings) as connection:
        row = connection.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM journal_drafts
            WHERE deleted_at IS NULL
              {status_filter}
            """
        ).fetchone()
    return int(row["total"] if row else 0)


def list_journal_drafts(
    settings: Settings,
    limit: int = 50,
    offset: int = 0,
    include_completed: bool = False,
) -> list[dict]:
    status_filter = "" if include_completed else "AND draft_status = 'needs_review'"
    with connect_db(settings) as connection:
        rows = connection.execute(
            f"""
            SELECT id, sync_run_id, broker, source_type, source_key,
                   ticker, name, draft_status, payload_json, created_at, updated_at
            FROM journal_drafts
            WHERE deleted_at IS NULL
              {status_filter}
            ORDER BY updated_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
    drafts = []
    for row in rows:
        item = dict(row)
        item["payload"] = json.loads(item.pop("payload_json"))
        drafts.append(item)
    return drafts


def get_journal_draft(settings: Settings, draft_id: int) -> dict | None:
    with connect_db(settings) as connection:
        row = connection.execute(
            """
            SELECT id, sync_run_id, broker, source_type, source_key,
                   ticker, name, draft_status, payload_json, created_at, updated_at
            FROM journal_drafts
            WHERE id = ?
            """,
            (draft_id,),
        ).fetchone()
    if not row:
        return None
    item = dict(row)
    item["payload"] = json.loads(item.pop("payload_json"))
    return item


def create_or_update_journal_entry(
    settings: Settings,
    draft_id: int,
    strategy_name: str,
    setup_tags: list[str],
    entry_reason: str,
    exit_reason: str,
    rule_followed: bool | None,
    good_points: str,
    improvement_points: str,
    memo: str,
    manual_profit_loss_amount: int | None = None,
    manual_profit_rate: float | None = None,
    manual_buy_amount: int | None = None,
    manual_sell_amount: int | None = None,
    planned_entry_price: float | None = None,
    actual_entry_price: float | None = None,
    stop_loss_price: float | None = None,
    target_price: float | None = None,
    exit_price: float | None = None,
    planned_risk_amount: int | None = None,
    realized_r_multiple: float | None = None,
) -> dict:
    draft = get_journal_draft(settings, draft_id)
    if not draft:
        raise ValueError(f"Journal draft not found: {draft_id}")

    now = utc_now_iso()
    rule_value = None if rule_followed is None else int(rule_followed)

    with connect_db(settings) as connection:
        connection.execute(
            """
            INSERT INTO journal_entries
              (draft_id, broker, ticker, name, strategy_name, setup_tags_json,
               entry_reason, exit_reason, rule_followed,
               good_points, improvement_points,
               memo, manual_profit_loss_amount, manual_profit_rate,
               manual_buy_amount, manual_sell_amount, planned_entry_price,
               actual_entry_price, stop_loss_price, target_price, exit_price,
               planned_risk_amount, realized_r_multiple,
               source_payload_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(draft_id)
            DO UPDATE SET
              strategy_name = excluded.strategy_name,
              setup_tags_json = excluded.setup_tags_json,
              entry_reason = excluded.entry_reason,
              exit_reason = excluded.exit_reason,
              rule_followed = excluded.rule_followed,
              good_points = excluded.good_points,
              improvement_points = excluded.improvement_points,
              memo = excluded.memo,
              manual_profit_loss_amount = excluded.manual_profit_loss_amount,
              manual_profit_rate = excluded.manual_profit_rate,
              manual_buy_amount = excluded.manual_buy_amount,
              manual_sell_amount = excluded.manual_sell_amount,
              planned_entry_price = excluded.planned_entry_price,
              actual_entry_price = excluded.actual_entry_price,
              stop_loss_price = excluded.stop_loss_price,
              target_price = excluded.target_price,
              exit_price = excluded.exit_price,
              planned_risk_amount = excluded.planned_risk_amount,
              realized_r_multiple = excluded.realized_r_multiple,
              source_payload_json = excluded.source_payload_json,
              updated_at = excluded.updated_at
            """,
            (
                draft_id,
                draft["broker"],
                draft.get("ticker"),
                draft.get("name"),
                strategy_name.strip(),
                json.dumps(setup_tags, ensure_ascii=False),
                entry_reason,
                exit_reason,
                rule_value,
                good_points,
                improvement_points,
                memo,
                manual_profit_loss_amount,
                manual_profit_rate,
                manual_buy_amount,
                manual_sell_amount,
                planned_entry_price,
                actual_entry_price,
                stop_loss_price,
                target_price,
                exit_price,
                planned_risk_amount,
                realized_r_multiple,
                json.dumps(draft["payload"], ensure_ascii=False),
                now,
                now,
            ),
        )
        connection.execute(
            """
            UPDATE journal_drafts
            SET draft_status = ?, updated_at = ?
            WHERE id = ?
            """,
            ("completed", now, draft_id),
        )
        row = connection.execute(
            """
            SELECT *
            FROM journal_entries
            WHERE draft_id = ?
            """,
            (draft_id,),
        ).fetchone()

    return _format_journal_entry(dict(row))


def list_journal_entries(
    settings: Settings,
    limit: int = 50,
    offset: int = 0,
    ticker: str | None = None,
    strategy_name: str | None = None,
    setup_tag: str | None = None,
    result: str | None = None,
    rule_status: str | None = None,
    search: str | None = None,
) -> list[dict]:
    has_filters = any([ticker, strategy_name, setup_tag, result, rule_status, search])
    query_limit = 10000 if has_filters else limit + offset
    with connect_db(settings) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM journal_entries
            ORDER BY updated_at DESC, id DESC
            LIMIT ?
            """,
            (query_limit,),
        ).fetchall()
    entries = [_format_journal_entry(dict(row)) for row in rows]
    entries = _filter_journal_entries(
        entries=entries,
        ticker=ticker,
        strategy_name=strategy_name,
        setup_tag=setup_tag,
        result=result,
        rule_status=rule_status,
        search=search,
    )
    return entries[offset : offset + limit]


def count_journal_entries(
    settings: Settings,
    ticker: str | None = None,
    strategy_name: str | None = None,
    setup_tag: str | None = None,
    result: str | None = None,
    rule_status: str | None = None,
    search: str | None = None,
) -> int:
    has_filters = any([ticker, strategy_name, setup_tag, result, rule_status, search])
    if not has_filters:
        with connect_db(settings) as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM journal_entries").fetchone()
        return int(row["total"] if row else 0)

    return len(
        list_journal_entries(
            settings=settings,
            limit=10000,
            offset=0,
            ticker=ticker,
            strategy_name=strategy_name,
            setup_tag=setup_tag,
            result=result,
            rule_status=rule_status,
            search=search,
        )
    )


def delete_journal_entry(settings: Settings, entry_id: int) -> dict:
    with connect_db(settings) as connection:
        row = connection.execute(
            """
            SELECT id, draft_id
            FROM journal_entries
            WHERE id = ?
            """,
            (entry_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"Journal entry not found: {entry_id}")

        draft_id = int(row["draft_id"])
        connection.execute(
            """
            DELETE FROM journal_entries
            WHERE id = ?
            """,
            (entry_id,),
        )
        connection.execute(
            """
            UPDATE journal_drafts
            SET draft_status = ?, updated_at = ?
            WHERE id = ?
            """,
            ("needs_review", utc_now_iso(), draft_id),
        )

    return {"deleted_entry_id": entry_id, "draft_id": draft_id}


def get_journal_analytics(
    settings: Settings,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    entries = list_journal_entries(settings, limit=1000)
    manual_transactions = list_manual_transactions(settings, limit=10000)
    entries = _filter_entries_by_analytics_date(entries, start_date, end_date)
    manual_transactions = _filter_manual_transactions_by_analytics_date(
        manual_transactions,
        start_date,
        end_date,
    )
    with connect_db(settings) as connection:
        draft_rows = connection.execute(
            """
            SELECT draft_status, COUNT(*) AS count
            FROM journal_drafts
            WHERE deleted_at IS NULL
            GROUP BY draft_status
            """
        ).fetchall()

    draft_counts = {row["draft_status"]: row["count"] for row in draft_rows}
    rule_followed_count = sum(1 for item in entries if item.get("rule_followed") is True)
    rule_broken_count = sum(1 for item in entries if item.get("rule_followed") is False)
    rule_unknown_count = sum(1 for item in entries if item.get("rule_followed") is None)
    known_rule_count = rule_followed_count + rule_broken_count
    ticker_counts: dict[str, int] = {}
    profit_loss_values: list[int] = []
    profit_rate_values: list[float] = []
    r_multiple_values: list[float] = []
    entry_slippage_amount_values: list[float] = []
    entry_slippage_rate_values: list[float] = []
    planned_reward_risk_ratios: list[float] = []
    entry_profit_pairs: list[tuple[dict, int]] = []
    rule_profit_loss_totals = {
        "followed": 0,
        "broken": 0,
        "unknown": 0,
    }
    strategy_performance: dict[str, dict[str, int]] = {}
    setup_tag_performance: dict[str, dict[str, int]] = {}
    total_buy_amount = 0
    total_sell_amount = 0
    planned_risk_amount_total = 0
    planned_price_entry_count = 0
    stop_loss_defined_count = 0
    target_defined_count = 0
    analytics_events: list[dict] = []
    brokerage_dedup_keys: set[str] = set()

    for entry in entries:
        profit_loss_value = _entry_profit_loss_value(entry)
        r_multiple_value = _entry_r_multiple_value(entry, profit_loss_value)
        planned_entry_price = entry.get("planned_entry_price")
        actual_entry_price = entry.get("actual_entry_price")
        stop_loss_price = entry.get("stop_loss_price")
        target_price = entry.get("target_price")
        ticker = entry.get("ticker") or "UNKNOWN"
        ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1
        payload = entry.get("source_payload", {})
        profit_rate_value = entry.get("manual_profit_rate")
        buy_amount_value = entry.get("manual_buy_amount")
        sell_amount_value = entry.get("manual_sell_amount")
        planned_risk_amount_value = entry.get("planned_risk_amount")

        if profit_rate_value is None:
            profit_rate_value = payload.get("profit_rate")
        if buy_amount_value is None:
            buy_amount_value = payload.get("buy_amount")
        if sell_amount_value is None:
            sell_amount_value = payload.get("sell_amount")

        if profit_loss_value is not None:
            profit_loss_values.append(profit_loss_value)
            entry_profit_pairs.append((entry, profit_loss_value))
            event = _journal_entry_analytics_event(entry, profit_loss_value)
            brokerage_dedup_keys.update(event.get("dedup_keys", []))
            analytics_events.append(event)
            strategy_name = (entry.get("strategy_name") or "UNSPECIFIED").strip()
            _add_performance_bucket(
                strategy_performance,
                strategy_name or "UNSPECIFIED",
                profit_loss_value,
            )
            for setup_tag in entry.get("setup_tags", []):
                _add_performance_bucket(
                    setup_tag_performance,
                    setup_tag,
                    profit_loss_value,
                )
            if entry.get("rule_followed") is True:
                rule_profit_loss_totals["followed"] += profit_loss_value
            elif entry.get("rule_followed") is False:
                rule_profit_loss_totals["broken"] += profit_loss_value
            else:
                rule_profit_loss_totals["unknown"] += profit_loss_value
        if profit_rate_value is not None:
            profit_rate_values.append(float(profit_rate_value))
        if r_multiple_value is not None:
            r_multiple_values.append(r_multiple_value)
        if planned_entry_price is not None:
            planned_price_entry_count += 1
        if stop_loss_price is not None:
            stop_loss_defined_count += 1
        if target_price is not None:
            target_defined_count += 1
        slippage = _entry_slippage_values(entry)
        if slippage:
            entry_slippage_amount_values.append(slippage["amount"])
            entry_slippage_rate_values.append(slippage["rate"])
        reward_risk_ratio = _entry_planned_reward_risk_ratio(entry)
        if reward_risk_ratio is not None:
            planned_reward_risk_ratios.append(reward_risk_ratio)
        if buy_amount_value is not None:
            total_buy_amount += int(buy_amount_value)
        if sell_amount_value is not None:
            total_sell_amount += int(sell_amount_value)
        if planned_risk_amount_value is not None:
            planned_risk_amount_total += int(planned_risk_amount_value)

    fx_unconverted_count = 0
    corporate_action_adjusted_count = 0
    duplicate_manual_transactions_count = 0

    for transaction in manual_transactions:
        manual_profit_loss = _manual_transaction_net_profit_krw(transaction)
        manual_dedup_key = transaction.get("dedup_key")
        is_duplicate_manual = (
            transaction.get("dedup_status") == "duplicate_kiwoom"
            or bool(manual_dedup_key and manual_dedup_key in brokerage_dedup_keys)
        )
        if is_duplicate_manual:
            duplicate_manual_transactions_count += 1
            continue
        analytics_events.append(_manual_transaction_analytics_event(transaction))
        if _manual_transaction_requires_fx(transaction) and manual_profit_loss is None:
            fx_unconverted_count += 1
            continue
        if manual_profit_loss != 0:
            profit_loss_values.append(manual_profit_loss)
            entry_profit_pairs.append((_manual_transaction_entry_summary(transaction), manual_profit_loss))
        if float(transaction.get("split_adjustment_ratio") or 1) != 1:
            corporate_action_adjusted_count += 1
        ticker = transaction.get("ticker") or "UNKNOWN"
        ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1
        buy_amount_value = transaction.get("buy_amount_krw")
        sell_amount_value = transaction.get("sell_amount_krw")
        if buy_amount_value is not None:
            total_buy_amount += int(buy_amount_value)
        if sell_amount_value is not None:
            total_sell_amount += int(sell_amount_value)

    active_manual_transactions_count = len(manual_transactions) - duplicate_manual_transactions_count
    top_tickers = [
        {"ticker": ticker, "count": count}
        for ticker, count in sorted(
            ticker_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )[:5]
    ]
    realized_profit_loss_total = sum(profit_loss_values)
    gross_profit_total = sum(value for value in profit_loss_values if value > 0)
    gross_loss_total = sum(value for value in profit_loss_values if value < 0)
    win_count = sum(1 for value in profit_loss_values if value > 0)
    loss_count = sum(1 for value in profit_loss_values if value < 0)
    breakeven_count = sum(1 for value in profit_loss_values if value == 0)
    closed_count = win_count + loss_count + breakeven_count
    positive_r_count = sum(1 for value in r_multiple_values if value > 0)
    negative_r_count = sum(1 for value in r_multiple_values if value < 0)
    breakeven_r_count = sum(1 for value in r_multiple_values if value == 0)
    r_closed_count = positive_r_count + negative_r_count + breakeven_r_count
    best_entry = None
    worst_entry = None
    if entry_profit_pairs:
        best_entry = _analytics_entry_summary(max(entry_profit_pairs, key=lambda item: item[1]))
        worst_entry = _analytics_entry_summary(min(entry_profit_pairs, key=lambda item: item[1]))
    chronological_profit_pairs = sorted(
        entry_profit_pairs,
        key=lambda item: (
            item[0].get("updated_at") or "",
            item[0].get("id") or 0,
        ),
    )
    curve_stats = _build_cumulative_profit_stats(chronological_profit_pairs)
    streak_stats = _build_streak_stats(chronological_profit_pairs)
    dividend_total = sum(int(event["dividend_amount"]) for event in analytics_events)
    tax_total = sum(int(event["tax_amount"]) for event in analytics_events)
    commission_total = sum(int(event.get("commission_amount") or 0) for event in analytics_events)

    return {
        "filter_start_date": start_date,
        "filter_end_date": end_date,
        "total_entries": len(entries) + active_manual_transactions_count,
        "completed_drafts": draft_counts.get("completed", 0),
        "pending_drafts": draft_counts.get("needs_review", 0),
        "rule_followed_count": rule_followed_count,
        "rule_broken_count": rule_broken_count,
        "rule_unknown_count": rule_unknown_count,
        "rule_follow_rate": (
            round(rule_followed_count / known_rule_count * 100, 2)
            if known_rule_count
            else None
        ),
        "top_tickers": top_tickers,
        "realized_profit_loss_total": realized_profit_loss_total,
        "gross_profit_total": gross_profit_total,
        "gross_loss_total": gross_loss_total,
        "profit_factor": (
            round(gross_profit_total / abs(gross_loss_total), 2)
            if gross_loss_total
            else None
        ),
        "expectancy_per_trade": (
            round(realized_profit_loss_total / len(profit_loss_values), 2)
            if profit_loss_values
            else None
        ),
        "planned_risk_amount_total": planned_risk_amount_total,
        "total_r_multiple": round(sum(r_multiple_values), 2),
        "average_r_multiple": (
            round(sum(r_multiple_values) / len(r_multiple_values), 2)
            if r_multiple_values
            else None
        ),
        "best_r_multiple": round(max(r_multiple_values), 2)
        if r_multiple_values
        else None,
        "worst_r_multiple": round(min(r_multiple_values), 2)
        if r_multiple_values
        else None,
        "positive_r_count": positive_r_count,
        "negative_r_count": negative_r_count,
        "r_win_rate": (
            round(positive_r_count / r_closed_count * 100, 2)
            if r_closed_count
            else None
        ),
        "planned_price_entry_count": planned_price_entry_count,
        "stop_loss_defined_count": stop_loss_defined_count,
        "target_defined_count": target_defined_count,
        "average_entry_slippage_amount": (
            round(sum(entry_slippage_amount_values) / len(entry_slippage_amount_values), 2)
            if entry_slippage_amount_values
            else None
        ),
        "average_entry_slippage_rate": (
            round(sum(entry_slippage_rate_values) / len(entry_slippage_rate_values), 4)
            if entry_slippage_rate_values
            else None
        ),
        "average_planned_reward_risk_ratio": (
            round(sum(planned_reward_risk_ratios) / len(planned_reward_risk_ratios), 2)
            if planned_reward_risk_ratios
            else None
        ),
        "average_profit_loss": (
            round(realized_profit_loss_total / len(profit_loss_values), 2)
            if profit_loss_values
            else None
        ),
        "average_profit_rate": (
            round(sum(profit_rate_values) / len(profit_rate_values), 2)
            if profit_rate_values
            else None
        ),
        "win_count": win_count,
        "loss_count": loss_count,
        "breakeven_count": breakeven_count,
        "win_rate": round(win_count / closed_count * 100, 2) if closed_count else None,
        "rule_followed_profit_loss_total": rule_profit_loss_totals["followed"],
        "rule_broken_profit_loss_total": rule_profit_loss_totals["broken"],
        "rule_unknown_profit_loss_total": rule_profit_loss_totals["unknown"],
        "best_entry": best_entry,
        "worst_entry": worst_entry,
        "strategy_performance": _format_performance_rows(
            strategy_performance,
            label_key="strategy_name",
        ),
        "setup_tag_performance": _format_performance_rows(
            setup_tag_performance,
            label_key="tag",
        ),
        "cumulative_profit_curve": curve_stats["curve"],
        "max_drawdown_amount": curve_stats["max_drawdown_amount"],
        "max_drawdown_rate": curve_stats["max_drawdown_rate"],
        "monthly_performance": _build_monthly_performance(chronological_profit_pairs),
        "annual_profit": _build_period_profit(analytics_events, "year"),
        "quarterly_profit": _build_period_profit(analytics_events, "quarter"),
        "monthly_profit": _build_period_profit(analytics_events, "month"),
        "profit_trend": _build_profit_trend(analytics_events),
        "ticker_allocation": _build_allocation_rows(analytics_events, "ticker"),
        "type_allocation": _build_allocation_rows(analytics_events, "transaction_type"),
        "account_allocation": _build_allocation_rows(analytics_events, "account_name"),
        "dividend_total": dividend_total,
        "dividend_by_year": _build_period_sum(analytics_events, "year", "dividend_amount"),
        "tax_total": tax_total,
        "tax_by_year": _build_period_sum(analytics_events, "year", "tax_amount"),
        "commission_total": commission_total,
        "commission_by_year": _build_period_sum(analytics_events, "year", "commission_amount"),
        "currency_breakdown": _build_currency_breakdown(analytics_events),
        "fx_unconverted_count": fx_unconverted_count,
        "corporate_action_adjusted_count": corporate_action_adjusted_count,
        "duplicate_manual_transactions_count": duplicate_manual_transactions_count,
        "manual_transactions_count": len(manual_transactions),
        "current_win_streak": streak_stats["current_win_streak"],
        "current_loss_streak": streak_stats["current_loss_streak"],
        "longest_win_streak": streak_stats["longest_win_streak"],
        "longest_loss_streak": streak_stats["longest_loss_streak"],
        "total_buy_amount": total_buy_amount,
        "total_sell_amount": total_sell_amount,
        "latest_entry_at": entries[0]["updated_at"] if entries else None,
    }


def _format_journal_entry(row: dict) -> dict:
    row["setup_tags"] = json.loads(row.pop("setup_tags_json", "[]") or "[]")
    row.pop("emotion_tags_json", None)
    row["source_payload"] = json.loads(row.pop("source_payload_json"))
    if row.get("rule_followed") is not None:
        row["rule_followed"] = bool(row["rule_followed"])
    return row


def _journal_entry_analytics_event(entry: dict, profit_loss_value: int) -> dict:
    payload = entry.get("source_payload", {})
    buy_amount = entry.get("manual_buy_amount")
    sell_amount = entry.get("manual_sell_amount")
    if buy_amount is None:
        buy_amount = payload.get("buy_amount")
    if sell_amount is None:
        sell_amount = payload.get("sell_amount")
    event_date = _journal_entry_analytics_date(entry)
    return {
        "date": event_date,
        "ticker": entry.get("ticker") or "UNKNOWN",
        "name": entry.get("name") or "",
        "broker": entry.get("broker") or "KIWOOM",
        "account_name": entry.get("broker") or "KIWOOM",
        "transaction_type": "trade",
        "profit_loss_amount": int(profit_loss_value),
        "dividend_amount": 0,
        "tax_amount": 0,
        "commission_amount": 0,
        "activity_amount": _activity_amount(
            buy_amount=buy_amount,
            sell_amount=sell_amount,
            profit_loss_amount=profit_loss_value,
        ),
        "currency": "KRW",
        "fx_rate_krw": 1.0,
        "is_converted_to_krw": True,
        "dedup_keys": _source_payload_dedup_keys(payload, event_date),
    }


def _manual_transaction_analytics_event(transaction: dict) -> dict:
    profit_loss = _manual_transaction_net_profit_krw(transaction)
    is_converted = profit_loss is not None
    dividend_amount = int(transaction.get("dividend_amount_krw") or 0)
    tax_amount = int(transaction.get("tax_amount_krw") or 0)
    commission_amount = int(transaction.get("commission_amount_krw") or 0)
    return {
        "date": _analytics_date(transaction.get("trade_date")),
        "ticker": transaction.get("ticker") or "UNKNOWN",
        "name": transaction.get("name") or "",
        "broker": transaction.get("broker") or "MANUAL",
        "account_name": transaction.get("account_name") or "기타",
        "transaction_type": transaction.get("transaction_type") or "trade",
        "profit_loss_amount": int(profit_loss or 0),
        "dividend_amount": dividend_amount if is_converted else 0,
        "tax_amount": tax_amount if is_converted else 0,
        "commission_amount": commission_amount if is_converted else 0,
        "activity_amount": _activity_amount(
            buy_amount=transaction.get("buy_amount_krw"),
            sell_amount=transaction.get("sell_amount_krw"),
            profit_loss_amount=profit_loss if is_converted else None,
            dividend_amount=dividend_amount if is_converted else None,
            tax_amount=tax_amount if is_converted else None,
            commission_amount=commission_amount if is_converted else None,
        ),
        "currency": transaction.get("currency") or "KRW",
        "fx_rate_krw": transaction.get("fx_rate_krw"),
        "is_converted_to_krw": is_converted,
        "dedup_key": transaction.get("dedup_key"),
        "dedup_status": transaction.get("dedup_status") or "active",
    }


def _manual_transaction_net_profit(transaction: dict) -> int:
    return (
        int(transaction.get("profit_loss_amount") or 0)
        + int(transaction.get("dividend_amount") or 0)
        - int(transaction.get("tax_amount") or 0)
        - int(transaction.get("commission_amount") or 0)
    )


def _manual_transaction_net_profit_krw(transaction: dict) -> int | None:
    has_source_amount = any(
        transaction.get(field) not in (None, "", 0)
        for field in [
            "profit_loss_amount",
            "dividend_amount",
            "tax_amount",
            "commission_amount",
            "buy_amount",
            "sell_amount",
        ]
    )
    if _manual_transaction_requires_fx(transaction) and has_source_amount:
        return None
    return (
        int(transaction.get("profit_loss_amount_krw") or 0)
        + int(transaction.get("dividend_amount_krw") or 0)
        - int(transaction.get("tax_amount_krw") or 0)
        - int(transaction.get("commission_amount_krw") or 0)
    )


def _manual_transaction_requires_fx(transaction: dict) -> bool:
    currency = _normalize_currency(transaction.get("currency"))
    return currency != "KRW" and not transaction.get("fx_rate_krw")


def _source_payload_dedup_keys(payload: dict, trade_date: str | None) -> list[str]:
    keys = [
        _trade_dedup_key(
            trade_date=trade_date,
            ticker=payload.get("ticker") or payload.get("stk_cd"),
            quantity=payload.get("buy_quantity"),
            price=payload.get("buy_average_price"),
        ),
        _trade_dedup_key(
            trade_date=trade_date,
            ticker=payload.get("ticker") or payload.get("stk_cd"),
            quantity=payload.get("sell_quantity"),
            price=payload.get("sell_average_price"),
        ),
        _trade_dedup_key(
            trade_date=trade_date,
            ticker=payload.get("ticker") or payload.get("stk_cd"),
            quantity=payload.get("filled_quantity") or payload.get("cntr_qty"),
            price=payload.get("filled_price") or payload.get("cntr_uv"),
        ),
        _trade_dedup_key(
            trade_date=trade_date,
            ticker=payload.get("ticker") or payload.get("stk_cd"),
            quantity=payload.get("quantity"),
            price=payload.get("price"),
        ),
    ]
    return [key for key in keys if key]


def _manual_transaction_entry_summary(transaction: dict) -> dict:
    return {
        "id": f"manual-{transaction.get('id')}",
        "ticker": transaction.get("ticker") or "UNKNOWN",
        "name": transaction.get("name") or transaction.get("broker") or "수동입력",
        "manual_profit_rate": None,
        "rule_followed": None,
        "entry_reason": transaction.get("memo") or transaction.get("adjustment_note") or transaction.get("transaction_type"),
        "updated_at": transaction.get("trade_date") or transaction.get("updated_at"),
        "source_payload": {
            "currency": transaction.get("currency") or "KRW",
            "fx_rate_krw": transaction.get("fx_rate_krw"),
            "split_adjustment_ratio": transaction.get("split_adjustment_ratio"),
            "adjusted_quantity": transaction.get("adjusted_quantity"),
            "adjusted_price": transaction.get("adjusted_price"),
        },
    }


def _analytics_date(value: str | None) -> str:
    if not value:
        return "UNKNOWN"
    text = str(value).strip()
    if len(text) >= 8 and text[:8].isdigit() and "-" not in text[:10]:
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    return text[:10]


def _journal_entry_analytics_date(entry: dict) -> str:
    payload = entry.get("source_payload", {}) or {}
    return _analytics_date(payload.get("trade_date") or entry.get("updated_at"))


def _is_date_in_analytics_range(
    value: str,
    start_date: str | None,
    end_date: str | None,
) -> bool:
    if value == "UNKNOWN":
        return start_date is None and end_date is None
    if start_date and value < start_date:
        return False
    if end_date and value > end_date:
        return False
    return True


def _filter_entries_by_analytics_date(
    entries: list[dict],
    start_date: str | None,
    end_date: str | None,
) -> list[dict]:
    if start_date is None and end_date is None:
        return entries
    return [
        entry
        for entry in entries
        if _is_date_in_analytics_range(
            _journal_entry_analytics_date(entry),
            start_date,
            end_date,
        )
    ]


def _filter_manual_transactions_by_analytics_date(
    transactions: list[dict],
    start_date: str | None,
    end_date: str | None,
) -> list[dict]:
    if start_date is None and end_date is None:
        return transactions
    return [
        transaction
        for transaction in transactions
        if _is_date_in_analytics_range(
            _analytics_date(transaction.get("trade_date")),
            start_date,
            end_date,
        )
    ]


def _activity_amount(
    buy_amount: int | float | None = None,
    sell_amount: int | float | None = None,
    profit_loss_amount: int | float | None = None,
    dividend_amount: int | float | None = None,
    tax_amount: int | float | None = None,
    commission_amount: int | float | None = None,
) -> int:
    values = [
        abs(int(value))
        for value in [
            buy_amount,
            sell_amount,
            profit_loss_amount,
            dividend_amount,
            tax_amount,
            commission_amount,
        ]
        if value not in (None, "")
    ]
    return max(values) if values else 0


def _filter_journal_entries(
    entries: list[dict],
    ticker: str | None,
    strategy_name: str | None,
    setup_tag: str | None,
    result: str | None,
    rule_status: str | None,
    search: str | None,
) -> list[dict]:
    ticker_filter = (ticker or "").strip().upper()
    strategy_filter = (strategy_name or "").strip().lower()
    setup_filter = (setup_tag or "").strip().lower()
    result_filter = (result or "").strip().lower()
    rule_filter = (rule_status or "").strip().lower()
    search_filter = (search or "").strip().lower()

    filtered = []
    for entry in entries:
        if ticker_filter and ticker_filter not in (entry.get("ticker") or "").upper():
            continue
        if strategy_filter and strategy_filter not in (
            entry.get("strategy_name") or ""
        ).lower():
            continue
        if setup_filter and not any(
            setup_filter in tag.lower() for tag in entry.get("setup_tags", [])
        ):
            continue

        if rule_filter == "followed" and entry.get("rule_followed") is not True:
            continue
        if rule_filter == "broken" and entry.get("rule_followed") is not False:
            continue
        if rule_filter == "unknown" and entry.get("rule_followed") is not None:
            continue

        profit_loss_value = _entry_profit_loss_value(entry)
        if result_filter == "profit" and not (
            profit_loss_value is not None and profit_loss_value > 0
        ):
            continue
        if result_filter == "loss" and not (
            profit_loss_value is not None and profit_loss_value < 0
        ):
            continue
        if result_filter == "breakeven" and not (
            profit_loss_value is not None and profit_loss_value == 0
        ):
            continue
        if result_filter == "unknown" and profit_loss_value is not None:
            continue

        if search_filter and search_filter not in _entry_search_text(entry):
            continue

        filtered.append(entry)

    return filtered


def _entry_profit_loss_value(entry: dict) -> int | None:
    value = entry.get("manual_profit_loss_amount")
    if value is None:
        value = entry.get("source_payload", {}).get("profit_loss_amount")
    return None if value is None else int(value)


def _entry_r_multiple_value(
    entry: dict,
    profit_loss_value: int | None = None,
) -> float | None:
    value = entry.get("realized_r_multiple")
    if value is not None:
        return float(value)

    planned_risk_amount = entry.get("planned_risk_amount")
    if planned_risk_amount in (None, 0):
        return None
    if profit_loss_value is None:
        profit_loss_value = _entry_profit_loss_value(entry)
    if profit_loss_value is None:
        return None
    return round(profit_loss_value / int(planned_risk_amount), 4)


def _entry_slippage_values(entry: dict) -> dict | None:
    planned_entry_price = entry.get("planned_entry_price")
    actual_entry_price = entry.get("actual_entry_price")
    if planned_entry_price in (None, 0) or actual_entry_price is None:
        return None

    amount = float(actual_entry_price) - float(planned_entry_price)
    rate = amount / float(planned_entry_price) * 100
    return {"amount": amount, "rate": rate}


def _entry_planned_reward_risk_ratio(entry: dict) -> float | None:
    planned_entry_price = entry.get("planned_entry_price")
    stop_loss_price = entry.get("stop_loss_price")
    target_price = entry.get("target_price")
    if (
        planned_entry_price is None
        or stop_loss_price is None
        or target_price is None
    ):
        return None

    risk = abs(float(planned_entry_price) - float(stop_loss_price))
    if risk == 0:
        return None
    reward = abs(float(target_price) - float(planned_entry_price))
    return round(reward / risk, 4)


def _entry_search_text(entry: dict) -> str:
    values = [
        entry.get("ticker"),
        entry.get("name"),
        entry.get("strategy_name"),
        " ".join(entry.get("setup_tags", [])),
        entry.get("entry_reason"),
        entry.get("exit_reason"),
        entry.get("good_points"),
        entry.get("improvement_points"),
        entry.get("memo"),
    ]
    return " ".join(str(value) for value in values if value).lower()


def _analytics_entry_summary(entry_pair: tuple[dict, int]) -> dict:
    entry, profit_loss_value = entry_pair
    return {
        "id": entry.get("id"),
        "ticker": entry.get("ticker"),
        "name": entry.get("name"),
        "profit_loss_amount": profit_loss_value,
        "profit_rate": entry.get("manual_profit_rate")
        if entry.get("manual_profit_rate") is not None
        else entry.get("source_payload", {}).get("profit_rate"),
        "rule_followed": entry.get("rule_followed"),
        "entry_reason": entry.get("entry_reason"),
        "updated_at": entry.get("updated_at"),
    }


def _add_performance_bucket(
    bucket: dict[str, dict[str, int]],
    key: str,
    profit_loss_value: int,
) -> None:
    current = bucket.setdefault(
        key,
        {
            "count": 0,
            "profit_loss_total": 0,
            "win_count": 0,
            "loss_count": 0,
            "breakeven_count": 0,
        },
    )
    current["count"] += 1
    current["profit_loss_total"] += profit_loss_value
    if profit_loss_value > 0:
        current["win_count"] += 1
    elif profit_loss_value < 0:
        current["loss_count"] += 1
    else:
        current["breakeven_count"] += 1


def _format_performance_rows(
    data: dict[str, dict[str, int]],
    label_key: str,
) -> list[dict]:
    rows = []
    for label, values in data.items():
        count = values["count"]
        profit_loss_total = values["profit_loss_total"]
        closed_count = (
            values.get("win_count", 0)
            + values.get("loss_count", 0)
            + values.get("breakeven_count", 0)
        )
        rows.append(
            {
                label_key: label,
                "count": count,
                "profit_loss_total": profit_loss_total,
                "average_profit_loss": round(profit_loss_total / count, 2)
                if count
                else None,
                "win_count": values.get("win_count", 0),
                "loss_count": values.get("loss_count", 0),
                "breakeven_count": values.get("breakeven_count", 0),
                "win_rate": (
                    round(values.get("win_count", 0) / closed_count * 100, 2)
                    if closed_count
                    else None
                ),
            }
        )
    return sorted(rows, key=lambda item: (-item["profit_loss_total"], item[label_key]))


def _build_period_profit(events: list[dict], period: str) -> list[dict]:
    rows: dict[str, dict] = {}
    for event in events:
        key = _period_key(event["date"], period)
        if key == "UNKNOWN":
            continue
        row = rows.setdefault(
            key,
            {
                "period": key,
                "profit_loss_total": 0,
                "dividend_total": 0,
                "tax_total": 0,
                "commission_total": 0,
                "count": 0,
            },
        )
        row["profit_loss_total"] += int(event["profit_loss_amount"])
        row["dividend_total"] += int(event["dividend_amount"])
        row["tax_total"] += int(event["tax_amount"])
        row["commission_total"] += int(event.get("commission_amount") or 0)
        row["count"] += 1
    return [rows[key] for key in sorted(rows.keys(), reverse=True)]


def _build_period_sum(events: list[dict], period: str, field: str) -> list[dict]:
    rows: dict[str, dict] = {}
    for event in events:
        value = int(event.get(field) or 0)
        if value == 0:
            continue
        key = _period_key(event["date"], period)
        if key == "UNKNOWN":
            continue
        row = rows.setdefault(key, {"period": key, "amount": 0, "count": 0})
        row["amount"] += value
        row["count"] += 1
    return [rows[key] for key in sorted(rows.keys(), reverse=True)]


def _build_profit_trend(events: list[dict]) -> list[dict]:
    sorted_events = sorted(
        [event for event in events if event["date"] != "UNKNOWN"],
        key=lambda event: event["date"],
    )
    cumulative = 0
    trend = []
    for index, event in enumerate(sorted_events, start=1):
        profit_loss = int(event["profit_loss_amount"])
        cumulative += profit_loss
        trend.append(
            {
                "sequence": index,
                "date": event["date"],
                "ticker": event["ticker"],
                "transaction_type": event["transaction_type"],
                "profit_loss_amount": profit_loss,
                "cumulative_profit_loss": cumulative,
            }
        )
    return trend


def _build_allocation_rows(events: list[dict], field: str) -> list[dict]:
    buckets: dict[str, dict] = {}
    total_amount = sum(int(event.get("activity_amount") or 0) for event in events)
    for event in events:
        key = event.get(field) or "UNKNOWN"
        row = buckets.setdefault(
            key,
            {
                field: key,
                "amount": 0,
                "profit_loss_total": 0,
                "count": 0,
                "weight": None,
            },
        )
        row["amount"] += int(event.get("activity_amount") or 0)
        row["profit_loss_total"] += int(event.get("profit_loss_amount") or 0)
        row["count"] += 1
    rows = []
    for row in buckets.values():
        row["weight"] = (
            round(row["amount"] / total_amount * 100, 2)
            if total_amount
            else None
        )
        rows.append(row)
    return sorted(rows, key=lambda item: (-item["amount"], str(item[field])))[:10]


def _build_currency_breakdown(events: list[dict]) -> list[dict]:
    buckets: dict[str, dict] = {}
    for event in events:
        currency = _normalize_currency(event.get("currency"))
        row = buckets.setdefault(
            currency,
            {
                "currency": currency,
                "count": 0,
                "converted_count": 0,
                "unconverted_count": 0,
                "profit_loss_total_krw": 0,
                "activity_amount_krw": 0,
                "latest_fx_rate_krw": None,
            },
        )
        row["count"] += 1
        if event.get("is_converted_to_krw", True):
            row["converted_count"] += 1
            row["profit_loss_total_krw"] += int(event.get("profit_loss_amount") or 0)
            row["activity_amount_krw"] += int(event.get("activity_amount") or 0)
        else:
            row["unconverted_count"] += 1
        if event.get("fx_rate_krw"):
            row["latest_fx_rate_krw"] = event.get("fx_rate_krw")
    return sorted(
        buckets.values(),
        key=lambda item: (-item["activity_amount_krw"], item["currency"]),
    )


def _period_key(date_value: str, period: str) -> str:
    if not date_value or date_value == "UNKNOWN":
        return "UNKNOWN"
    year = date_value[:4]
    month = date_value[5:7]
    if period == "year":
        return year
    if period == "quarter":
        quarter = (int(month) - 1) // 3 + 1
        return f"{year}-Q{quarter}"
    return date_value[:7]


def _build_cumulative_profit_stats(entry_pairs: list[tuple[dict, int]]) -> dict:
    cumulative_profit = 0
    peak_profit = 0
    max_drawdown_amount = 0
    max_drawdown_rate = None
    curve = []

    for index, (entry, profit_loss_value) in enumerate(entry_pairs, start=1):
        cumulative_profit += profit_loss_value
        peak_profit = max(peak_profit, cumulative_profit)
        drawdown_amount = cumulative_profit - peak_profit
        if drawdown_amount < max_drawdown_amount:
            max_drawdown_amount = drawdown_amount
            max_drawdown_rate = (
                round(drawdown_amount / peak_profit * 100, 2)
                if peak_profit
                else None
            )
        curve.append(
            {
                "sequence": index,
                "entry_id": entry.get("id"),
                "ticker": entry.get("ticker"),
                "name": entry.get("name"),
                "profit_loss_amount": profit_loss_value,
                "cumulative_profit_loss": cumulative_profit,
                "drawdown_amount": drawdown_amount,
                "updated_at": entry.get("updated_at"),
            }
        )

    return {
        "curve": curve,
        "max_drawdown_amount": max_drawdown_amount,
        "max_drawdown_rate": max_drawdown_rate,
    }


def _build_monthly_performance(entry_pairs: list[tuple[dict, int]]) -> list[dict]:
    monthly: dict[str, dict[str, int]] = {}
    for entry, profit_loss_value in entry_pairs:
        month_key = (entry.get("updated_at") or "")[:7] or "UNKNOWN"
        current = monthly.setdefault(
            month_key,
            {
                "entries_count": 0,
                "profit_loss_total": 0,
                "win_count": 0,
                "loss_count": 0,
                "breakeven_count": 0,
            },
        )
        current["entries_count"] += 1
        current["profit_loss_total"] += profit_loss_value
        if profit_loss_value > 0:
            current["win_count"] += 1
        elif profit_loss_value < 0:
            current["loss_count"] += 1
        else:
            current["breakeven_count"] += 1

    rows = []
    for month, values in sorted(monthly.items()):
        closed_count = (
            values["win_count"] + values["loss_count"] + values["breakeven_count"]
        )
        rows.append(
            {
                "month": month,
                "entries_count": values["entries_count"],
                "profit_loss_total": values["profit_loss_total"],
                "win_count": values["win_count"],
                "loss_count": values["loss_count"],
                "breakeven_count": values["breakeven_count"],
                "win_rate": round(values["win_count"] / closed_count * 100, 2)
                if closed_count
                else None,
            }
        )
    return rows


def _build_streak_stats(entry_pairs: list[tuple[dict, int]]) -> dict:
    current_kind = None
    current_count = 0
    longest_win_streak = 0
    longest_loss_streak = 0

    for _, profit_loss_value in entry_pairs:
        if profit_loss_value > 0:
            kind = "win"
        elif profit_loss_value < 0:
            kind = "loss"
        else:
            kind = "breakeven"

        if kind == current_kind:
            current_count += 1
        else:
            current_kind = kind
            current_count = 1

        if kind == "win":
            longest_win_streak = max(longest_win_streak, current_count)
        elif kind == "loss":
            longest_loss_streak = max(longest_loss_streak, current_count)

    return {
        "current_win_streak": current_count if current_kind == "win" else 0,
        "current_loss_streak": current_count if current_kind == "loss" else 0,
        "longest_win_streak": longest_win_streak,
        "longest_loss_streak": longest_loss_streak,
    }


def _ensure_column(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_type: str,
) -> None:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    existing_columns = {row["name"] for row in rows}
    if column_name not in existing_columns:
        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        )


def _format_history_sync_job(row: dict) -> dict:
    total_days = int(row.get("total_days") or 0)
    processed_days = int(row.get("processed_days") or 0)
    row["progress_rate"] = (
        round(processed_days / total_days * 100, 2) if total_days else None
    )
    return row


def _upsert_trade_journal_drafts(
    connection: sqlite3.Connection,
    sync_run_id: int,
    journal: JournalSourceTradesResponse,
    now: str,
    secret_salt: str,
) -> None:
    for item in journal.trade_journal_items:
        payload = item.model_dump(mode="json")
        payload["trade_date"] = journal.base_date
        dedup_keys = _source_payload_dedup_keys(payload, journal.base_date)
        source_key = _stable_source_key(
            "ka10170",
            {
                "trade_date": journal.base_date,
                "ticker": item.ticker,
                "buy_quantity": item.buy_quantity,
                "buy_average_price": item.buy_average_price,
                "sell_quantity": item.sell_quantity,
                "sell_average_price": item.sell_average_price,
                "buy_amount": item.buy_amount,
                "sell_amount": item.sell_amount,
            },
        )
        _upsert_journal_draft(
            connection=connection,
            sync_run_id=sync_run_id,
            broker=journal.broker,
            source_type="trade_journal",
            source_key=source_key,
            ticker=item.ticker,
            name=item.name,
            payload=payload,
            now=now,
            secret_salt=secret_salt,
            dedup_keys=dedup_keys,
        )


def _upsert_order_execution_drafts(
    connection: sqlite3.Connection,
    sync_run_id: int,
    journal: JournalSourceTradesResponse,
    now: str,
    secret_salt: str,
) -> None:
    for item in journal.order_executions:
        payload = item.model_dump(mode="json")
        payload["trade_date"] = journal.base_date
        dedup_keys = _source_payload_dedup_keys(payload, journal.base_date)
        source_key = _stable_source_key(
            "kt00007",
            {
                "trade_date": journal.base_date,
                "order_no": item.order_no,
                "ticker": item.ticker,
                "filled_quantity": item.filled_quantity,
                "filled_price": item.filled_price,
                "order_time": item.order_time,
                "confirm_time": item.confirm_time,
            },
        )
        _upsert_journal_draft(
            connection=connection,
            sync_run_id=sync_run_id,
            broker=journal.broker,
            source_type="order_execution",
            source_key=source_key,
            ticker=item.ticker,
            name=item.name,
            payload=payload,
            now=now,
            secret_salt=secret_salt,
            dedup_keys=dedup_keys,
        )


def _upsert_journal_draft(
    connection: sqlite3.Connection,
    sync_run_id: int,
    broker: str,
    source_type: str,
    source_key: str,
    ticker: str | None,
    name: str | None,
    payload: dict,
    now: str,
    secret_salt: str,
    dedup_keys: list[str],
) -> None:
    storage_payload = redact_account_numbers(payload, secret_salt)
    connection.execute(
        """
        INSERT INTO journal_drafts
          (sync_run_id, broker, source_type, source_key, ticker, name,
           draft_status, payload_json, dedup_keys_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_type, source_key)
        DO UPDATE SET
          sync_run_id = excluded.sync_run_id,
          ticker = excluded.ticker,
          name = excluded.name,
          payload_json = excluded.payload_json,
          dedup_keys_json = excluded.dedup_keys_json,
          updated_at = excluded.updated_at
        """,
        (
            sync_run_id,
            broker,
            source_type,
            source_key,
            ticker,
            name,
            "needs_review",
            json.dumps(storage_payload, ensure_ascii=False),
            json.dumps(dedup_keys, ensure_ascii=False),
            now,
            now,
        ),
    )
    _register_trade_dedup_keys(
        connection=connection,
        dedup_keys=dedup_keys,
        source="kiwoom",
        source_type=source_type,
        source_key=source_key,
        now=now,
    )
