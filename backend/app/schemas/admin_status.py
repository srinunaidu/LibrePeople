"""Schemas for the administrator operational status (LP-ADM-005).

Mirrors ``contracts/openapi/admin.yaml`` (path ``/admin/status``) and the
``AdminStatus`` / ``UpgradeStatus`` / ``BackupStatus`` /
``OperationalWarning`` components in
``contracts/openapi/_components.yaml``.

Everything here is a read model: the endpoint reports what the deployment
looks like and never changes it. ``warnings`` carries the actionable part —
each entry names a condition and what the operator should do about it.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class UpgradeStatus(BaseModel):
    """Which release the database schema matches, if that is known."""

    current_revision: str | None = None
    head_revision: str | None = None
    up_to_date: bool | None = None
    status: str = "unknown"


class BackupStatus(BaseModel):
    """What the operator arranged for backups, read from env defaults."""

    configured: bool = False
    schedule: str = "manual"
    last_success_at: datetime | None = None
    stale: bool | None = None


class OperationalWarning(BaseModel):
    """One actionable condition the administrator should look at."""

    code: str
    severity: str = "warning"
    message: str


class AdminStatus(BaseModel):
    """The deployment's upgrade status, backup status and warnings."""

    app_version: str
    environment: str
    upgrade: UpgradeStatus
    backup: BackupStatus
    warnings: list[OperationalWarning] = []
    checked_at: datetime
