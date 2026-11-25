"""Database engine and session factory.

Pool policy (LP-DATA-001 / LP-INT-003..005):

* SQLite (tests, local development) uses :class:`NullPool`: every checkout
  opens its own connection, so a test that forgets to close a session
  cannot starve a fixed-size pool. This is what failed
  ``import_test_suite`` with
  ``QueuePool limit of size 5 overflow 10 reached, connection timed out``:
  the same 5+10 pool was applied to a file-backed SQLite database while
  leaked test sessions held every slot.
* Server databases (Oracle / Postgres) use :class:`QueuePool` with
  env-overridable sizing and pre-ping:

  ``DB_POOL_SIZE`` (default 5), ``DB_POOL_MAX_OVERFLOW`` (default 10),
  ``DB_POOL_TIMEOUT`` seconds (default 30), ``DB_POOL_RECYCLE`` seconds
  (unset by default = no recycle), ``DB_POOL_PRE_PING``
  (default true; ``1/true/yes/on`` = true).
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import settings


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_optional_int(name: str) -> int | None:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None

# Connect arguments passed through to python-oracledb.
connect_args: dict = {}

if settings.ORACLE_WALLET_DIR:
    # Thin mode mTLS. The PEM private key is encrypted, so wallet_password is
    # required when a wallet password was set at download time.
    connect_args["config_dir"] = settings.ORACLE_WALLET_DIR
    connect_args["wallet_location"] = settings.ORACLE_WALLET_DIR
    if settings.ORACLE_WALLET_PASSWORD:
        connect_args["wallet_password"] = settings.ORACLE_WALLET_PASSWORD

if settings.ORACLE_DSN:
    # Canonical Oracle Autonomous Database + wallet pattern:
    # credentials and the TNS alias are passed explicitly to the driver.
    missing = [
        name
        for name, value in (
            ("ORACLE_USER", settings.ORACLE_USER),
            ("ORACLE_PASSWORD", settings.ORACLE_PASSWORD),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            "ORACLE_DSN is set but missing: " + ", ".join(missing)
        )
    connect_args.update(
        user=settings.ORACLE_USER,
        password=settings.ORACLE_PASSWORD,
        dsn=settings.ORACLE_DSN,
    )
    database_url = "oracle+oracledb://:@"
elif settings.DATABASE_URL:
    database_url = settings.DATABASE_URL
else:
    raise RuntimeError(
        "No database configured. Set DATABASE_URL, or "
        "ORACLE_DSN + ORACLE_USER + ORACLE_PASSWORD (+ ORACLE_WALLET_DIR)."
    )

def _pool_kwargs(url: str, base_connect_args: dict) -> dict:
    """Pool arguments for ``create_engine`` based on the URL dialect.

    SQLite gets ``NullPool`` (no fixed slot count to exhaust) plus
    ``check_same_thread=False`` so the test client may use the file
    database from more than one thread. Anything else gets ``QueuePool``
    with env-overridable sizing and pre-ping.
    """
    if url.startswith("sqlite"):
        args = dict(base_connect_args)
        args.setdefault("check_same_thread", False)
        return {"poolclass": NullPool, "connect_args": args}
    kwargs: dict = {
        "poolclass": QueuePool,
        "pool_size": _env_int("DB_POOL_SIZE", 5),
        "max_overflow": _env_int("DB_POOL_MAX_OVERFLOW", 10),
        "pool_timeout": _env_int("DB_POOL_TIMEOUT", 30),
        "pool_pre_ping": _env_bool("DB_POOL_PRE_PING", True),
        "connect_args": dict(base_connect_args),
    }
    recycle = _env_optional_int("DB_POOL_RECYCLE")
    if recycle is not None:
        kwargs["pool_recycle"] = recycle
    return kwargs


engine = create_engine(
    database_url,
    **_pool_kwargs(database_url, connect_args),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
