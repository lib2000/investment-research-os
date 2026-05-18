import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from app.database import _apply_sqlite_encryption_key, _restrict_db_file_permissions
from app.settings import Settings


def resolve_db_path(settings: Settings) -> Path:
    db_path = Path(settings.local_db_path)
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path
    return db_path


def resolve_backup_dir(settings: Settings) -> Path:
    backup_dir = Path(settings.db_backup_dir)
    if not backup_dir.is_absolute():
        backup_dir = Path.cwd() / backup_dir
    return backup_dir


def list_database_backups(settings: Settings) -> dict:
    backup_dir = resolve_backup_dir(settings)
    backups = []
    if backup_dir.exists():
        for path in sorted(backup_dir.glob("*.sqlite3"), reverse=True):
            stat = path.stat()
            backups.append(
                {
                    "file_name": path.name,
                    "path": str(path),
                    "size_bytes": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            )
    return {
        "backup_dir": str(backup_dir),
        "retention_days": settings.db_backup_retention_days,
        "interval_hours": settings.db_backup_interval_hours,
        "backups": backups,
    }


def backup_database_if_due(settings: Settings, reason: str = "startup") -> dict:
    if not settings.db_backup_on_startup and reason == "startup":
        return {
            "backup_created": False,
            "reason": reason,
            "message": "DB_BACKUP_ON_STARTUP is disabled.",
        }

    latest = _latest_backup_path(settings)
    if latest and not _is_backup_due(latest, settings):
        cleanup_result = cleanup_old_backups(settings)
        return {
            "backup_created": False,
            "reason": reason,
            "latest_backup": str(latest),
            "deleted_old_count": cleanup_result["deleted_old_count"],
            "message": "Latest backup is still within the configured interval.",
        }

    return backup_database(settings, reason=reason)


def backup_database(settings: Settings, reason: str = "manual") -> dict:
    db_path = resolve_db_path(settings)
    if not db_path.exists():
        return {
            "backup_created": False,
            "reason": reason,
            "message": f"Database file does not exist: {db_path}",
        }

    backup_dir = resolve_backup_dir(settings)
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{db_path.stem}_{stamp}.sqlite3"

    source = sqlite3.connect(
        db_path,
        timeout=max(settings.sqlite_busy_timeout_ms / 1000, 1),
    )
    destination = sqlite3.connect(backup_path)
    try:
        _apply_sqlite_encryption_key(source, settings)
        _apply_sqlite_encryption_key(destination, settings)
        source.backup(destination)
        destination.commit()
    finally:
        destination.close()
        source.close()

    _restrict_db_file_permissions(backup_path, settings)
    cleanup_result = cleanup_old_backups(settings)
    return {
        "backup_created": True,
        "reason": reason,
        "source_db": str(db_path),
        "backup_path": str(backup_path),
        "backup_file_name": backup_path.name,
        "size_bytes": backup_path.stat().st_size,
        "deleted_old_count": cleanup_result["deleted_old_count"],
    }


def cleanup_old_backups(settings: Settings) -> dict:
    backup_dir = resolve_backup_dir(settings)
    if not backup_dir.exists():
        return {"deleted_old_count": 0, "deleted_files": []}

    retention_days = max(int(settings.db_backup_retention_days), 1)
    cutoff = datetime.now() - timedelta(days=retention_days)
    deleted_files = []
    for path in backup_dir.glob("*.sqlite3"):
        modified_at = datetime.fromtimestamp(path.stat().st_mtime)
        if modified_at < cutoff:
            path.unlink()
            deleted_files.append(path.name)

    return {
        "deleted_old_count": len(deleted_files),
        "deleted_files": deleted_files,
    }


def _latest_backup_path(settings: Settings) -> Path | None:
    backup_dir = resolve_backup_dir(settings)
    if not backup_dir.exists():
        return None
    backups = sorted(
        backup_dir.glob("*.sqlite3"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not backups:
        return None
    return backups[0]


def _is_backup_due(latest_backup: Path, settings: Settings) -> bool:
    interval_hours = max(float(settings.db_backup_interval_hours), 0.0)
    if interval_hours <= 0:
        return True
    latest_at = datetime.fromtimestamp(latest_backup.stat().st_mtime)
    return datetime.now() - latest_at >= timedelta(hours=interval_hours)
