import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


def _read_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y"}


def _read_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value.strip())
    except ValueError:
        return default


def _read_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value.strip())
    except ValueError:
        return default


class Settings(BaseModel):
    app_name: str = "Investment Journal API Gateway"
    default_broker: str = "KIWOOM"
    brokerage_api_key: str = Field(default="********")
    brokerage_api_secret: str = Field(default="********")
    kiwoom_base_url: str = "https://api.kiwoom.com"
    kiwoom_mock_base_url: str = "https://mockapi.kiwoom.com"
    kiwoom_use_mock: bool = True
    kiwoom_registered_ip: str = Field(default="********")
    secret_salt: str = Field(default="********")
    dev_user_token: str = Field(default="dev-local-token")
    local_db_path: str = "investment_journal.sqlite3"
    history_sync_min_delay_seconds: float = 0.0
    history_sync_request_delay_seconds: float = 2.0
    history_sync_rate_limit_seconds: float = 2.0
    history_sync_max_retries: int = 5
    history_sync_backoff_initial_seconds: float = 2.0
    history_sync_backoff_max_seconds: float = 60.0
    history_sync_backoff_multiplier: float = 2.0
    kiwoom_page_delay_seconds: float = 0.4
    sqlite_enable_wal: bool = True
    sqlite_busy_timeout_ms: int = 30000
    sqlite_synchronous: str = "NORMAL"
    sqlite_encryption_key: str = Field(default="")
    sqlite_restrict_file_permissions: bool = True
    db_backup_on_startup: bool = True
    db_backup_dir: str = "backups"
    db_backup_retention_days: int = 30
    db_backup_interval_hours: int = 168
    token_expiry_buffer_seconds: int = 300
    kiwoom_allow_refresh_token: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            default_broker=os.getenv("DEFAULT_BROKER", "KIWOOM"),
            brokerage_api_key=os.getenv("KIWOOM_API_KEY", "********"),
            brokerage_api_secret=os.getenv("KIWOOM_API_SECRET", "********"),
            kiwoom_base_url=os.getenv("KIWOOM_BASE_URL", "https://api.kiwoom.com"),
            kiwoom_mock_base_url=os.getenv(
                "KIWOOM_MOCK_BASE_URL", "https://mockapi.kiwoom.com"
            ),
            kiwoom_use_mock=_read_bool("KIWOOM_USE_MOCK", True),
            kiwoom_registered_ip=os.getenv("KIWOOM_REGISTERED_IP", "********"),
            secret_salt=os.getenv("SECRET_SALT", "********"),
            dev_user_token=os.getenv("DEV_USER_TOKEN", "dev-local-token"),
            local_db_path=os.getenv("LOCAL_DB_PATH", "investment_journal.sqlite3"),
            history_sync_min_delay_seconds=_read_float(
                "HISTORY_SYNC_MIN_DELAY_SECONDS", 0.0
            ),
            history_sync_request_delay_seconds=_read_float(
                "HISTORY_SYNC_REQUEST_DELAY_SECONDS", 2.0
            ),
            history_sync_rate_limit_seconds=_read_float(
                "HISTORY_SYNC_RATE_LIMIT_SECONDS", 2.0
            ),
            history_sync_max_retries=_read_int("HISTORY_SYNC_MAX_RETRIES", 5),
            history_sync_backoff_initial_seconds=_read_float(
                "HISTORY_SYNC_BACKOFF_INITIAL_SECONDS", 2.0
            ),
            history_sync_backoff_max_seconds=_read_float(
                "HISTORY_SYNC_BACKOFF_MAX_SECONDS", 60.0
            ),
            history_sync_backoff_multiplier=_read_float(
                "HISTORY_SYNC_BACKOFF_MULTIPLIER", 2.0
            ),
            kiwoom_page_delay_seconds=_read_float("KIWOOM_PAGE_DELAY_SECONDS", 0.4),
            sqlite_enable_wal=_read_bool("SQLITE_ENABLE_WAL", True),
            sqlite_busy_timeout_ms=_read_int("SQLITE_BUSY_TIMEOUT_MS", 30000),
            sqlite_synchronous=os.getenv("SQLITE_SYNCHRONOUS", "NORMAL"),
            sqlite_encryption_key=os.getenv("SQLITE_ENCRYPTION_KEY", ""),
            sqlite_restrict_file_permissions=_read_bool(
                "SQLITE_RESTRICT_FILE_PERMISSIONS",
                True,
            ),
            db_backup_on_startup=_read_bool("DB_BACKUP_ON_STARTUP", True),
            db_backup_dir=os.getenv("DB_BACKUP_DIR", "backups"),
            db_backup_retention_days=_read_int("DB_BACKUP_RETENTION_DAYS", 30),
            db_backup_interval_hours=_read_int("DB_BACKUP_INTERVAL_HOURS", 168),
            token_expiry_buffer_seconds=_read_int("TOKEN_EXPIRY_BUFFER_SECONDS", 300),
            kiwoom_allow_refresh_token=_read_bool("KIWOOM_ALLOW_REFRESH_TOKEN", False),
        )

    @property
    def kiwoom_api_base_url(self) -> str:
        if self.kiwoom_use_mock:
            return self.kiwoom_mock_base_url
        return self.kiwoom_base_url


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()


def mask_secret(value: str) -> str:
    if not value or value == "********":
        return "********"
    if len(value) <= 8:
        return "********"
    return f"{value[:4]}****{value[-4:]}"
