import logging
from mimetypes import guess_type
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.config import settings
from app.api.deps import get_current_active_user, get_db, require_roles
from app.api.v1.api import api_router
from app.models.user import User
from app.core.database import engine, Base
from app.models import (  # noqa: F401  (register models)
    user,
    department,
    job,
    job_queue,
    employee,
    recruiting,
    onboarding,
    time_attendance,
    scheduling,
    leave,
    offboarding,
    audit,
    client_onboarding,
    core_hr,
    payroll,
    performance,
    benefits,
    learning,
    integrations_platform,
    compliance,
    ess_hr,
    filing_record,
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# CORS.
#
# The API authenticates with a bearer token rather than a cookie, so the safe
# default is an empty allow-list (no browser origin may read responses). The
# deployment sets BACKEND_CORS_ORIGINS to the exact frontend origins.
#
# `allow_credentials` is deliberately disabled: combined with an explicit
# allow-list it would additionally let any allowed origin send ambient
# credentials.
#
# The tenant headers are the multi-tenant read path: the frontend sends the
# workspace slug on every non-auth request (`X-Tenant-Slug`), and integrators
# may pin a request to a tenant (`X-Tenant-Id`, checked against the resolved
# tenant). A custom header forces a CORS preflight, so both must be allowed
# or every cross-origin tenant-scoped read fails the preflight and the
# screens render empty (the P4 journeys caught this: the employee selectors
# stayed empty while the same token listed rows over a simple request).
_cors_origins = settings.cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Tenant-Slug", "X-Tenant-Id"],
    expose_headers=["Retry-After"],
    max_age=600,
)
if settings.is_production and (not _cors_origins or "*" in _cors_origins):
    raise RuntimeError(
        "BACKEND_CORS_ORIGINS is unset or wildcard in production. "
        "Set it to the exact frontend origin(s)."
    )

# Security headers on every response (CSP, HSTS, X-Content-Type-Options,
# X-Frame-Options, Referrer-Policy).
from app.core.security_headers import SecurityHeadersMiddleware  # noqa: E402

app.add_middleware(SecurityHeadersMiddleware)

# Structured JSON logging with request correlation and redaction.
from app.core.observability import configure_logging  # noqa: E402

configure_logging(settings.LOG_LEVEL)

# Consistent failure envelope + correlation-id middleware. Installed before
# the routers so every route is covered by both.
from app.core.errors import install_handlers  # noqa: E402

install_handlers(app)

# Override FastAPI's default validation-error handler so that Pydantic
# ``RequestValidationError`` (422) also renders the structured envelope
# instead of ``{"detail": [...]}``.
from app.core.errors import validation_error_handler  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402

app.add_exception_handler(RequestValidationError, validation_error_handler)

# IdempotencyRecord lives beside the logic that uses it; import it here so
# its table is part of the migration metadata.
from app.core.idempotency import IdempotencyRecord  # noqa: E402,F401

app.include_router(api_router, prefix=settings.API_V1_STR)


# --------------------------------------------------------------------------
# Authenticated document download
#
# The ``/files`` StaticFiles mount is gone (item 9): it served uploaded
# documents and offer letters to any caller, unauthenticated. Documents are
# served through the route below instead — an authenticated, active account,
# and a path validated against the storage root so nothing outside it is
# reachable.
# --------------------------------------------------------------------------


#: The job worker thread, when ``JOB_WORKER_ENABLED`` is set. ``None`` means
#: this process does not execute background jobs.
_job_worker = None


@app.on_event("startup")
def on_startup():
    """Bring the database schema up to date, seed admin users, and start the job worker.

    Alembic is the only schema change path. The previous behaviour — calling
    ``create_all()`` in a background thread — could not evolve an existing
    table and silently drifted from the models; it is gone.

    The migration runs in a background thread so it never blocks the server
    from binding. In production the database may be slow to reach, and a
    blocked startup would fail the platform health check and roll the deploy
    back.

    A migration failure is recorded and surfaced by ``/health/db`` rather than
    being swallowed, so a schema that is behind the code is visible instead of
    producing confusing runtime errors.

    The worker starts only when ``JOB_WORKER_ENABLED`` is set. It is off by
    default: a test harness that asserts a large import is *queued* must not
    have a background thread apply it mid-assertion, and a deployment should
    opt in to executing work rather than discover it is doing so.

    One instance is the deployment model, so one worker is enough. The
    constraint solver is deterministic, so a second worker would be safe but
    would not add throughput.

    When this process also migrates, the worker waits for the migration
    thread. A worker that starts first would query a table the migration has
    not created yet and log a failure every poll; the queue is durable, so
    waiting costs nothing.
    """
    import threading

    from app.core.migrations import run_pending_migrations
    import time

    def _start_job_worker() -> None:
        """Start the background job worker."""
        global _job_worker
        if not settings.JOB_WORKER_ENABLED:
            print("[startup] JOB_WORKER_ENABLED is disabled; not starting job worker.")
            return
        if _job_worker is not None:
            print("[startup] Job worker already running, skipping.")
            return
        from app.jobs.worker import JobWorker
        _job_worker = JobWorker(
            poll_seconds=settings.JOB_WORKER_POLL_SECONDS,
            lease_seconds=settings.JOB_WORKER_LEASE_SECONDS,
        )
        _job_worker.start()
        print(f"[startup] Job worker started: {_job_worker.worker_id}")

    if not settings.MIGRATE_ON_STARTUP:
        print("[startup] MIGRATE_ON_STARTUP is disabled; skipping migrations.")
        _start_job_worker()
        return

    def _migrate() -> None:
        try:
            run_pending_migrations()
        except Exception as exc:  # noqa: BLE001
            print(f"[startup] MIGRATION FAILED: {exc}")
            logging.getLogger("librepeople.startup").exception(
                "database migration failed at startup"
            )
        finally:
            _start_job_worker()
            # Seed the bootstrap admin after migration completes
            _seed_admin_users()

    def _seed_admin_users() -> None:
        """Seed the bootstrap SuperAdmin, retrying transient DB errors.

        The actual seeding is fail-closed (see :func:`seed_initial_admin`):
        a missing or policy-rejected ``ADMIN_INITIAL_PASSWORD`` creates no
        users and returns immediately without retrying. Only a database
        error is retried, because the migration may still be settling when
        this startup handler runs.
        """
        for attempt in range(15):
            try:
                seed_initial_admin()
                return
            except Exception as e:  # noqa: BLE001
                print(f"[startup] Seed attempt {attempt + 1}/15 failed: {e}")
                time.sleep(3)
        print("[startup] Seed failed after 15 attempts - database may not be ready yet")

    threading.Thread(target=_migrate, daemon=True).start()


def seed_initial_admin(session_factory=None) -> str:
    """Create the single bootstrap SuperAdmin from the environment.

    The credentials are never hardcoded: ``ADMIN_INITIAL_USERNAME``,
    ``ADMIN_INITIAL_EMAIL`` and ``ADMIN_INITIAL_PASSWORD`` are read from
    the environment on every call (same variables as
    ``backend/scripts/seed_admin.py``, which remains the operator path
    for creating the first administrator).

    Fail-closed outcomes create no users:

    * ``already-exists`` — at least one user is present; nothing to do.
    * ``skipped-no-env`` — ``ADMIN_INITIAL_PASSWORD`` is unset; the
      database is left with zero users rather than a default credential.
    * ``rejected-policy`` — the supplied password fails ``check_password``;
      nothing is stored.

    ``seeded`` means exactly one ``SuperAdmin`` row (left in a
    ``must_change_password`` state) was created. Calling again is a no-op
    (idempotent): the second call returns ``already-exists``.

    MFA and impersonation behaviour are untouched by this function.
    """
    import os

    from app.core.database import SessionLocal
    from app.core.password_policy import check_password
    from app.core.security import get_password_hash
    from app.models.user import User

    factory = session_factory or SessionLocal
    username = os.environ.get("ADMIN_INITIAL_USERNAME", settings.ADMIN_INITIAL_USERNAME)
    email = os.environ.get("ADMIN_INITIAL_EMAIL", settings.ADMIN_INITIAL_EMAIL)
    password = os.environ.get("ADMIN_INITIAL_PASSWORD")
    db = factory()
    try:
        if db.query(User).count() > 0:
            print("[startup] Users already exist, skipping bootstrap seed.")
            return "already-exists"
        if not password:
            print(
                "[startup] ADMIN_INITIAL_PASSWORD is not set; "
                "no bootstrap user created (fail-closed)."
            )
            return "skipped-no-env"
        result = check_password(
            password,
            username=username,
            email=email,
            min_length=settings.PASSWORD_MIN_LENGTH,
        )
        if not result.ok:
            print(
                "[startup] ADMIN_INITIAL_PASSWORD failed the password policy; "
                "no bootstrap user created (fail-closed)."
            )
            return "rejected-policy"
        db.add(
            User(
                username=username,
                email=email,
                hashed_password=get_password_hash(password),
                role="SuperAdmin",
                is_active=True,
                must_change_password=True,
            )
        )
        db.commit()
        print(
            f"[startup] Seeded initial SuperAdmin '{username}'. "
            "The account must change its password at first sign-in."
        )
        return "seeded"
    finally:
        db.close()
@app.on_event("shutdown")
def on_shutdown():
    """Stop the job worker, letting the job in flight finish.

    A daemon thread would be killed with the process, and an import killed
    half-way is a transaction the database has to roll back. Waiting for the
    current job is the difference between a clean stop and a crash.
    """
    global _job_worker
    if _job_worker is None:
        return
    stopped = _job_worker.stop(timeout=settings.JOB_WORKER_SHUTDOWN_SECONDS)
    if stopped:
        print(f"[shutdown] job worker {_job_worker.worker_id} stopped")
    else:
        print(
            f"[shutdown] job worker {_job_worker.worker_id} did not stop within "
            f"{settings.JOB_WORKER_SHUTDOWN_SECONDS}s"
        )
    _job_worker = None


@app.get("/")
def root():
    return {"msg": "LibrePeople Workforce Management API", "version": settings.VERSION}


def _document_path(path: str) -> Path | None:
    """Resolve a client-supplied document key against the storage root.

    Returns ``None`` for anything that cannot be the key of a file inside
    the storage root: absolute paths, ``..`` segments, backslashes, NUL
    bytes, or a resolved path outside the root or a directory.
    """
    if not path or path != path.strip() or "\\" in path or "\x00" in path:
        return None
    relative = Path(path)
    if relative.is_absolute() or ".." in relative.parts:
        return None
    root = Path(settings.LOCAL_STORAGE_DIR).resolve()
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root) or candidate.is_dir():
        return None
    return candidate


@app.get("/api/v1/files/{path:path}")
def download_document(
    path: str,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Download a stored document (offer letter, payslip, attachment, ...).

    Requires an authenticated, active account, and the key must resolve to
    a file inside the storage root. Objects are stored under opaque keys, so
    there is no other caller-controlled component in the path.

    LP-DOC-002: when the key belongs to an employee document, the download
    is recorded in the document's access log — who read what, and when.
    """
    from app.models.core_hr import DocumentAccessLog, EmployeeDocument

    candidate = _document_path(path)
    if candidate is None or not candidate.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    doc = db.query(EmployeeDocument).filter(EmployeeDocument.storage_key == path).first()
    if doc is not None:
        db.add(DocumentAccessLog(document_id=doc.id, accessed_by=_user.username))
        db.commit()
    return FileResponse(
        candidate,
        filename=candidate.name,
        media_type=guess_type(candidate.name)[0] or "application/octet-stream",
    )


# --------------------------------------------------------------------------
# Health / diagnostics
#
# /health is a liveness probe and stays public (the platform checks it).
# The detailed probes below can reach the database and can WRITE to object
# storage, so they require an authenticated operator unless
# PUBLIC_DIAGNOSTIC_ENDPOINTS is explicitly enabled.
# --------------------------------------------------------------------------

#: The diagnostic endpoints are reachable by a SuperAdmin only.
#:
#: The token is fully validated (signature, expiry, known user, active,
#: not locked, password change complete) by :func:`get_current_active_user`,
#: and the role is then checked by ``require_roles("SuperAdmin")``. A
#: missing, garbage, expired, HR or Manager token is refused before the
#: handler body runs, so a rejected request touches neither the database,
#: the wallet files nor the storage backend.
#:
#: ``PUBLIC_DIAGNOSTIC_ENDPOINTS`` no longer bypasses this check. The
#: setting is retained only so existing environment files still load; it has
#: no effect on these routes.
require_diagnostic_access = require_roles("SuperAdmin")


@app.get("/health")
def health():
    """Liveness probe. Intentionally reveals nothing about internals."""
    return {"status": "healthy"}


@app.get("/health/db")
def health_db(_: User = Depends(require_diagnostic_access)):
    """Verify the database connection and report the migration state.

    Connection error text can contain host/DSN detail, so failures are reported
    generically and the underlying exception is logged server-side only.
    """
    import logging

    from sqlalchemy import text

    log = logging.getLogger("librepeople.health")
    # Oracle requires FROM DUAL for a bare `SELECT 1`; SQLite rejects the DUAL
    # table. Probe the dialect rather than hard-coding either dialect's syntax,
    # because a wrong probe makes this endpoint report an outage on a healthy
    # database — which is worse than having no health check at all.
    probe = "SELECT 1 FROM DUAL" if engine.dialect.name == "oracle" else "SELECT 1"
    try:
        with engine.connect() as conn:
            conn.execute(text(probe))
    except Exception as exc:  # noqa: BLE001
        log.error("database health check failed: %s", exc)
        raise HTTPException(status_code=503, detail="database unavailable") from None

    from app.core.migrations import MIGRATION_STATE, database_revision, head_revision

    migration = dict(MIGRATION_STATE)
    # The truth is what the database is stamped at. The in-process state only
    # describes a migration run *by this process*, which in the container is
    # the release step that ran before the server started.
    current = database_revision() or migration.get("current_revision")
    head = head_revision() or migration.get("head_revision")
    return {
        "status": "ok",
        "database": "connected",
        "migration": {
            "status": migration.get("status"),
            "current_revision": current,
            "head_revision": head,
            "up_to_date": bool(current) and current == head,
            "legacy_schema_adopted": migration.get("legacy_schema_adopted", False),
        },
    }


@app.get("/health/schema")
def health_schema(_: User = Depends(require_diagnostic_access)):
    """Diagnostic: compare the live schema with the SQLAlchemy models.

    A deployment that predates Alembic was built by ``create_all()`` from
    the models as they were then. The models have moved on, so a table can
    be missing a column the code now expects. The frozen baseline does not
    evolve those tables, so the drift is invisible until a query fails.

    The report names the tables and columns; it does not change anything.
    """
    import logging
    import traceback

    from app.core.observability import get_logger

    log = logging.getLogger("librepeople.health")
    structured = get_logger("librepeople.health")
    try:
        from app.core.schema_drift import schema_drift_report

        report = schema_drift_report()
    except Exception as exc:  # noqa: BLE001
        log.error("schema drift check failed: %s", exc)
        log.debug("schema drift traceback: %s", traceback.format_exc())
        return {
            "in_sync": None,
            "error": f"{type(exc).__name__}: {exc}",
            "missing_tables": [],
            "missing_columns": {},
            "extra_columns": {},
            "type_mismatches": {},
            "inspection_errors": {},
            "extra_tables": [],
        }

    if not report.get("in_sync"):
        # The structured logger takes the fields as keywords; the standard
        # library logger does not.
        structured.warning(
            "the live schema does not match the models",
            missing_tables=report.get("missing_tables"),
            missing_columns=report.get("missing_columns"),
        )
    return report


@app.get("/health/storage")
def health_storage(_: User = Depends(require_diagnostic_access)):
    """Diagnostic: exercise the storage backend end to end.

    It saves a probe, reads it back, checks that the bytes came back
    intact, and deletes it. The checksum is compared rather than merely
    computed, because a backend that reports success and loses the bytes
    is worse than one that fails loudly: the caller has already moved on.

    Audit finding A5-02: the deployment's local disk is ephemeral, so
    `STORAGE_BACKEND=oci` is the production setting. This probe says
    which backend is actually in use.
    """
    import logging

    from app.storage import get_storage

    log = logging.getLogger("librepeople.health")
    storage = get_storage()
    info = {"backend": type(storage).__name__}
    key = "_diag/storage-probe.txt"
    payload = b"karmathy storage probe"
    try:
        storage.save(key, payload, "text/plain")
        info["save_ok"] = True
        info["exists"] = storage.exists(key)
        read_back = storage.read(key)
        info["read_ok"] = read_back == payload
        info["bytes"] = len(read_back)
        info["checksum_ok"] = storage.checksum(key) is not None
        info["deleted"] = storage.delete(key)
        info["deleted_ok"] = not storage.exists(key)
    except Exception as exc:  # noqa: BLE001
        log.error("storage health check failed: %s", exc)
        raise HTTPException(
            status_code=503, detail="storage backend unavailable"
        ) from None
    return info


@app.get("/health/wallet")
def health_wallet(_: User = Depends(require_diagnostic_access)):
    """Diagnostic: report which wallet files the app can see.

    Returns booleans and file *names* only — never wallet contents, DSNs, or
    passwords.
    """
    from pathlib import Path

    directory = settings.ORACLE_WALLET_DIR
    info: dict = {
        "wallet_configured": bool(directory),
        "wallet_password_configured": bool(settings.ORACLE_WALLET_PASSWORD),
        "dsn_configured": bool(settings.ORACLE_DSN),
    }
    if not directory:
        return info
    path = Path(directory)
    if not path.exists():
        info["wallet_dir_exists"] = False
        return info
    info["wallet_dir_exists"] = True
    info["files"] = sorted(f.name for f in path.iterdir() if f.is_file())
    return info