from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }
    PROJECT_NAME: str = "LibrePeople"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database
    # Provide either DATABASE_URL, or the Oracle ADB wallet trio below.
    DATABASE_URL: str = ""
    ORACLE_WALLET_DIR: str | None = None
    RULE_PACK_DIR: str | None = None
    #: Tenant default currency (ISO 4217). Used to backfill pay runs and
    #: payslips written before the currency column existed, and as the
    #: default when a client omits currency on a create request.
    DEFAULT_CURRENCY: str = "INR"
    ORACLE_WALLET_PASSWORD: str | None = None
    ORACLE_DSN: str | None = None
    ORACLE_USER: str | None = None
    ORACLE_PASSWORD: str | None = None

    # Security
    SECRET_KEY: str
    # The JWT algorithm is pinned to HS256 (see app.core.security). This
    # setting is retained only so an existing deployment that sets it keeps
    # working; a value other than HS256 is rejected at startup rather than
    # silently widening the accepted algorithm set.
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    # Password policy
    PASSWORD_MIN_LENGTH: int = 12
    PASSWORD_HISTORY_DEPTH: int = 5

    # Login lockout (per account, in addition to the per-IP rate limit).
    #
    # Five failed sign-ins within a 15-minute window lock the account for the
    # lockout duration. The failure count is kept per account on the server;
    # no client-supplied header can reset or bypass it.
    #
    # OPEN (product owner): the 15-minute lock duration is the default and is
    # configurable here until the owner confirms it.
    LOGIN_MAX_FAILED_ATTEMPTS: int = 5
    LOGIN_FAILURE_WINDOW_SECONDS: int = 900
    LOGIN_LOCKOUT_SECONDS: int = 900

    # Reverse proxies whose forwarded headers (X-Forwarded-For, -Host, -Proto)
    # are believed. Comma-separated CIDRs. The default is EMPTY: nothing is
    # trusted and the direct TCP peer is always the client. No cloud or
    # platform address is added here; the deployment names its own proxy.
    TRUSTED_PROXY_CIDRS: str = ""

    # Field encryption. FIELD_ENCRYPTION_KEYS is a comma-separated list of
    # `key_id:secret` pairs. FIELD_ENCRYPTION_ACTIVE_KEY_ID selects the key
    # used for new writes; every key in the registry can still decrypt, which
    # is what makes rotation possible without a data migration.
    #
    # There is no fallback to SECRET_KEY in any environment: encryption is
    # only possible with a registered key, and production refuses to start
    # without FIELD_ENCRYPTION_KEYS and FIELD_ENCRYPTION_ACTIVE_KEY_ID.
    FIELD_ENCRYPTION_KEYS: str = ""
    FIELD_ENCRYPTION_ACTIVE_KEY_ID: str = ""

    # Bootstrap administrator seeding.
    #
    # The application never ships credentials: the first SuperAdmin is
    # created only when ADMIN_INITIAL_PASSWORD is supplied by the
    # environment (see backend/scripts/seed_admin.py, which remains the
    # operator path, and the startup seed in app.main). The password must
    # pass the password policy. Without it the application starts with zero
    # users (fail-closed) — no default credential exists in any environment.
    ADMIN_INITIAL_USERNAME: str = "admin"
    ADMIN_INITIAL_EMAIL: str = "admin@librepeople.example"
    ADMIN_INITIAL_PASSWORD: str | None = None

    # Synthetic development seed data (seed/dev/). Off by default: sample
    # departments, jobs and employees are never loaded unless explicitly
    # enabled, and never in production.
    ALLOW_DEV_SEED: bool = False

    # Public self-service registration. Off by default: in production an
    # administrator provisions accounts instead of letting anyone sign up.
    ALLOW_SELF_REGISTRATION: bool = False

    # Brute-force protection on the login endpoint (per remote IP).
    LOGIN_RATE_LIMIT_ATTEMPTS: int = 10
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 300

    # Public operational probes. /health stays on (platform health check);
    # the detailed diagnostics must be authenticated.
    PUBLIC_DIAGNOSTIC_ENDPOINTS: bool = False

    # CORS — comma-separated list. Empty means "same-origin only" (no browser
    # origins are allowed), which is the safe default for a token API.
    BACKEND_CORS_ORIGINS: str = ""

    # Environment
    ENVIRONMENT: str = "development"

    # Run Alembic migrations at application start.
    #
    # Safe for the single-instance deployment this product uses. For a
    # multi-instance deployment, set this to False and run
    # `python -m scripts.migrate upgrade` as a separate release step so two
    # instances cannot attempt the same migration concurrently.
    MIGRATE_ON_STARTUP: bool = True

    # Log verbosity: DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_LEVEL: str = "INFO"

    # Background job worker.
    #
    # The queue is durable but nothing executed it until the worker existed:
    # a large import was answered with 202 ("queued") and never applied. The
    # worker runs in the web process and is off by default, so a deployment
    # opts in explicitly and a test harness is not silently changed by a
    # background thread applying the rows it asserts on.
    #
    # One instance is the deployment model, so one worker is enough. The
    # claim is a conditional update, so a second worker would be safe but
    # would not add throughput.
    JOB_WORKER_ENABLED: bool = False
    #: How long an idle worker waits between passes.
    JOB_WORKER_POLL_SECONDS: float = 2.0
    #: The lease a claimed job holds. A worker heartbeats at a third of this.
    JOB_WORKER_LEASE_SECONDS: int = 300
    #: How long shutdown waits for the job in flight to finish.
    JOB_WORKER_SHUTDOWN_SECONDS: float = 15.0

    #: The upload-retention schedule — the IM-10 defect was that
    #: nothing scheduled it. Off by default; opting in enqueues one
    #: retention job on boot and another every interval. The enqueue is
    #: deduped while a retention job is pending or running.
    RETENTION_SCHEDULE_ENABLED: bool = False
    #: Hours between retention enqueue attempts. 0 disables the periodic loop.
    RETENTION_RUN_INTERVAL_HOURS: float = 24.0

    # Object Storage (Oracle Cloud) — for documents & offer letters
    STORAGE_BACKEND: str = "local"  # "local" or "oci"
    LOCAL_STORAGE_DIR: str = "/tmp/karmathy-storage"
    OCI_NAMESPACE: str | None = None
    OCI_BUCKET_NAME: str | None = None
    OCI_CONFIG_FILE: str = "~/.oci/config"
    OCI_PROFILE: str = "DEFAULT"

    # Email delivery (LP-NOT-002) — provider selection for notifications.
    # "log" records the send in the logs (default, no SMTP needed);
    # "smtp" sends through any SMTP relay with the stdlib only (no vendor SDK).
    EMAIL_PROVIDER: str = "log"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_USE_TLS: bool = True
    SMTP_FROM: str | None = None

    # LP-ADM-005 operational status collectors (read-only env defaults).
    #
    # No auto-upgrade and no backup runner live behind these settings: they
    # only describe what the operator arranged outside the app so that
    # GET /admin/status can report it honestly. Unset means "not arranged":
    # the endpoint then reports backup as not configured plus an actionable
    # warning instead of inventing a healthy timestamp.
    BACKUP_ENABLED: bool = False
    BACKUP_SCHEDULE: str = "manual"
    BACKUP_LAST_SUCCESS_AT: str | None = None
    BACKUP_MAX_AGE_HOURS: int = 24

    # Content-Security-Policy. When unset, a conservative default is applied
    # (scripts, styles, images, fonts, and connections all restricted to
    # 'self' plus inline styles). Set via CONTENT_SECURITY_POLICY env var to
    # trust additional sources (self-hosted fonts, document previews from OCI,
    # etc.).
    CONTENT_SECURITY_POLICY: str = ""

    @property
    def cors_origins(self) -> List[str]:
        raw = self.BACKEND_CORS_ORIGINS.strip()
        if not raw:
            return []
        if raw == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]

    @property
    def trusted_proxy_networks(self) -> List:
        """The configured trusted proxy networks, parsed.

        Raises ``ValueError`` for a malformed entry, so a typo fails at startup
        rather than silently trusting nothing (or everything).
        """
        import ipaddress

        raw = (self.TRUSTED_PROXY_CIDRS or "").strip()
        if not raw:
            return []
        return [
            ipaddress.ip_network(item.strip(), strict=False)
            for item in raw.split(",")
            if item.strip()
        ]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in ("production", "prod", "live")

    def validate(self) -> None:
        """Fail fast on a configuration that would weaken the platform.

        Called at import and again at application startup. A misconfiguration
        must stop the process, not produce a service that is weaker than the
        operator believes.

        The checks are split by environment. A pinned algorithm and a sane
        token lifetime are correctness requirements and are enforced
        everywhere. A minimum secret length is enforced in production, where
        the key protects real data, and only warned about elsewhere — refusing
        to start a development environment over a short key helps nobody.
        """
        if self.ALGORITHM != "HS256":
            raise RuntimeError(
                "ALGORITHM is pinned to HS256 for this application. "
                f"Refusing to start with ALGORITHM={self.ALGORITHM!r}."
            )
        if len(self.SECRET_KEY) < 32:
            message = (
                "SECRET_KEY must be at least 32 characters. Generate one with "
                "`python -c \"import secrets; print(secrets.token_urlsafe(48))\"`."
            )
            if self.is_production:
                raise RuntimeError(message)
            import logging

            logging.getLogger("librepeople.config").warning(
                "%s This is not enforced outside production.", message
            )
        if self.PASSWORD_MIN_LENGTH < 12:
            raise RuntimeError(
                "PASSWORD_MIN_LENGTH must be at least 12 (NIST SP 800-63B)."
            )
        if self.ACCESS_TOKEN_EXPIRE_MINUTES > 60:
            raise RuntimeError(
                "ACCESS_TOKEN_EXPIRE_MINUTES must be 60 or less; access tokens "
                "are short-lived and refreshed through a rotating refresh token."
            )
        try:
            self.trusted_proxy_networks
        except ValueError as exc:
            raise RuntimeError(
                f"TRUSTED_PROXY_CIDRS is not a valid list of networks: {exc}"
            ) from None
        if self.is_production:
            missing = [
                name
                for name, value in (
                    ("FIELD_ENCRYPTION_KEYS", self.FIELD_ENCRYPTION_KEYS),
                    (
                        "FIELD_ENCRYPTION_ACTIVE_KEY_ID",
                        self.FIELD_ENCRYPTION_ACTIVE_KEY_ID,
                    ),
                )
                if not (value or "").strip()
            ]
            if missing:
                raise RuntimeError(
                    "Production refuses to start without field encryption "
                    "configuration: "
                    + ", ".join(missing)
                    + ". Set FIELD_ENCRYPTION_KEYS and "
                    "FIELD_ENCRYPTION_ACTIVE_KEY_ID; there is no fallback "
                    "to SECRET_KEY."
                )
            # CORS fail-closed: a token API must never answer cross-origin
            # reads from an unspecified set of origins in production. An
            # empty allow-list (same-origin default) or any wildcard entry
            # would either be a misconfigured deploy or, with Starlette's
            # CORSMiddleware, an allow-all (`"*"` anywhere in allow_origins
            # enables allow-all-origins). Refuse to start instead of
            # warning and serving.
            origins = self.cors_origins
            if not origins or "*" in origins:
                raise RuntimeError(
                    "Production refuses to start with BACKEND_CORS_ORIGINS "
                    f"unset or wildcard (got {origins!r}). Set it to the "
                    "exact frontend origin(s), e.g. "
                    "BACKEND_CORS_ORIGINS=https://app.example.com."
                )
settings = Settings()
settings.validate()
