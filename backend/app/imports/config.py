"""The configuration this lane owns.

Why it is not in ``app.core.config``
------------------------------------
``backend/app/core/config.py`` belongs to the Platform & Security lane. One
agent owns one file, so the settings that only the import engine and the
upload retention care about live here, in the lane that uses them. They
are read from the same environment, so a deployment configures them the
same way it configures everything else.

The settings
------------
``IMPORT_MAX_UPLOAD_BYTES``
    The largest upload the importer accepts. The brief's five megabytes is
    the default; a deployment with more headroom can raise it.
``IMPORT_MAX_ROWS``
    The largest number of data rows in one file. The brief's ten thousand
    is the default.
``IMPORT_BATCH_SIZE``
    How many rows are held in memory at once while an import runs. This is
    the knob that keeps the importer inside the free tier's 512 MB budget.
``IMPORT_TOKEN_TTL_MINUTES``
    How long a confirmation token stays usable. Fifteen minutes: long
    enough for an operator to read a preview, short enough that a
    forgotten preview is not a stale preview.
``IMPORT_MAX_OUTSTANDING_TOKENS``
    How many uncommitted dry runs may be outstanding at once. The oldest
    is evicted past this, so a process cannot accumulate an unbounded
    number of them.
``UPLOAD_RETENTION_DAYS``
    How long an uploaded file is kept when its import is never committed.
    Seven days by default.
``TENANT_ID``
    Which customer this deployment serves. Under the one-customer-per-
    deployment model there is exactly one, and it is recorded on every
    import so that a misconfigured deployment is visible in the data.
``IMPORT_SALARY_MIN`` / ``IMPORT_SALARY_MAX``
    The bounds the tenant's configuration places on an imported salary,
    per pay period. Unset means no bound beyond the column's own.
``IMPORT_JOB_ROW_THRESHOLD``
    How many rows a file may hold before its import runs as a background
    job instead of inside the request. A small file is quicker to apply
    straight away; a large one is quicker to apply in the background,
    where the operator can see how far it has got.
``IMPORT_JOB_TTL_MINUTES``
    How long the confirmation token of a queued import stays usable. A
    job waits in a queue, so the token of an import that has been queued
    has to outlive the queue.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class ImportSettings(BaseSettings):
    """The import engine's configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    IMPORT_MAX_UPLOAD_BYTES: int = 5 * 1024 * 1024
    IMPORT_MAX_ROWS: int = 10_000
    IMPORT_BATCH_SIZE: int = 500

    IMPORT_TOKEN_TTL_MINUTES: int = 15
    IMPORT_MAX_OUTSTANDING_TOKENS: int = 100

    UPLOAD_RETENTION_DAYS: int = 7

    # Deprecated in favour of per-request tenant resolution: keep the field so
    # existing deployments and imports that read ``settings.TENANT_ID`` keep
    # working, but it now resolves from the request tenant context and falls
    # back to DEFAULT_TENANT_SLUG ("default") for legacy JWTs / backfill.
    _TENANT_ID_LEGACY: str = "default"

    IMPORT_SALARY_MIN: float | None = None
    IMPORT_SALARY_MAX: float | None = None

    IMPORT_JOB_ROW_THRESHOLD: int = 2000
    IMPORT_JOB_TTL_MINUTES: int = 60

    @property
    def TENANT_ID(self) -> str:
        """Resolve the tenant id from the current request context.

        Falls back to ``DEFAULT_TENANT_SLUG`` ("default") when there is no
        active request context (background jobs, seeds) or the tenant could
        not be resolved — never leaks one tenant's rows into another's import.
        """
        from app.core.tenancy import current_tenant_id, DEFAULT_TENANT_SLUG

        return current_tenant_id() or DEFAULT_TENANT_SLUG


settings = ImportSettings()
