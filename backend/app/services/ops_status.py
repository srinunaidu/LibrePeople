"""Read-only operational status collectors (LP-ADM-005).

Each collector answers one question about the deployment without changing
anything: no queries write, nothing commits, nothing triggers an upgrade or
a backup. The endpoint in ``app/api/v1/endpoints/admin_status.py`` only
calls these and returns the result.

Sources, deliberately boring:

* upgrade — the Alembic stamp on the database vs the head the codebase
  knows about (the same pair ``GET /health/db`` reports);
* backup — the ``BACKUP_*`` env defaults in ``app/core/config.py``. There
  is no in-app backup runner, so an unset ``BACKUP_LAST_SUCCESS_AT`` means
  "not arranged", reported as not configured plus a warning — never a
  healthy timestamp;
* warnings — actionable conditions derived from the two above plus a dead
  job count from the queue. Every warning names what the operator should
  do next.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _parse_dt(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(str(raw).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def collect_upgrade() -> dict[str, Any]:
    """Report the schema revision vs the codebase head (read only)."""
    from app.core import migrations as _migrations

    current = _migrations.database_revision()
    if current is None:
        current = (_migrations.MIGRATION_STATE or {}).get("current_revision")
    head = _migrations.head_revision()
    if head is None:
        head = (_migrations.MIGRATION_STATE or {}).get("head_revision")
    status = (_migrations.MIGRATION_STATE or {}).get("status") or "unknown"
    up_to_date: bool | None = None
    if current and head:
        up_to_date = current == head
    return {
        "current_revision": current,
        "head_revision": head,
        "up_to_date": up_to_date,
        "status": status,
    }


def collect_backup(now: datetime | None = None) -> dict[str, Any]:
    """Report the operator-arranged backup state from env defaults."""
    from app.core.config import settings

    checked = now or datetime.now(timezone.utc)
    last_success = _parse_dt(settings.BACKUP_LAST_SUCCESS_AT)
    configured = bool(settings.BACKUP_ENABLED and last_success is not None)
    stale: bool | None = None
    if last_success is not None:
        try:
            max_age = float(settings.BACKUP_MAX_AGE_HOURS)
        except (TypeError, ValueError):
            max_age = 24.0
        stale = (checked - last_success).total_seconds() > max_age * 3600
    return {
        "configured": configured,
        "schedule": settings.BACKUP_SCHEDULE or "manual",
        "last_success_at": last_success,
        "stale": stale,
    }


def collect_dead_jobs(db) -> int:
    """Count dead jobs without touching them (read only)."""
    try:
        from app.models.job_queue import JobQueue

        try:
            rows = (
                db.query(JobQueue).filter(JobQueue.state.in_(["dead", "DEAD"])).all()
            )
        except Exception:  # noqa: BLE001 — fall back to a full scan
            rows = db.query(JobQueue).all()
            rows = [j for j in rows if str(getattr(j, "state", "")).lower() == "dead"]
        return len(rows)
    except Exception:  # noqa: BLE001 — no queue table yet means no dead jobs
        return 0


def collect_warnings(
    db,
    upgrade: dict[str, Any],
    backup: dict[str, Any],
) -> list[dict[str, str]]:
    """Derive the actionable operational warnings (read only)."""
    warnings: list[dict[str, str]] = []
    if upgrade.get("up_to_date") is False:
        warnings.append(
            {
                "code": "migration_behind",
                "severity": "warning",
                "message": (
                    "Database schema "
                    f"{upgrade.get('current_revision')!r} is behind the "
                    f"codebase head {upgrade.get('head_revision')!r}. "
                    "Run the pending migrations from a release step; "
                    "this endpoint never upgrades automatically."
                ),
            }
        )
    if not backup.get("configured"):
        warnings.append(
            {
                "code": "backup_not_configured",
                "severity": "warning",
                "message": (
                    "No successful backup is recorded (BACKUP_ENABLED / "
                    "BACKUP_LAST_SUCCESS_AT are unset). Arrange scheduled "
                    "backups and verify a restore before relying on them."
                ),
            }
        )
    elif backup.get("stale"):
        warnings.append(
            {
                "code": "backup_stale",
                "severity": "warning",
                "message": (
                    "The last recorded backup is older than "
                    "BACKUP_MAX_AGE_HOURS. Run a backup and confirm "
                    "BACKUP_LAST_SUCCESS_AT advances."
                ),
            }
        )
    dead = collect_dead_jobs(db)
    if dead > 0:
        warnings.append(
            {
                "code": "dead_jobs_present",
                "severity": "warning",
                "message": (
                    f"{dead} background job(s) exhausted their attempts and "
                    "are in the dead state. Review GET /admin/jobs?state=dead "
                    "and retry or discard them."
                ),
            }
        )
    return warnings


def collect_status(db) -> dict[str, Any]:
    """Assemble the full admin status payload (read only, no commit)."""
    from app.core.config import settings

    upgrade = collect_upgrade()
    backup = collect_backup()
    warnings = collect_warnings(db, upgrade, backup)
    return {
        "app_version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "upgrade": upgrade,
        "backup": {
            "configured": backup["configured"],
            "schedule": backup["schedule"],
            "last_success_at": backup["last_success_at"],
            "stale": backup["stale"],
        },
        "warnings": warnings,
        "checked_at": datetime.now(timezone.utc),
    }
