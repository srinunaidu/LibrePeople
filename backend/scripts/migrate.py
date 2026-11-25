"""Run database migrations, including adoption of the pre-Alembic schema.

This platform was deployed before Alembic existed. The production database
was built by ``create_all()`` and has no migration history. This script is
what brings it under Alembic control without rebuilding it.

What it does
------------
1. Connects to the database.
2. Looks for the ``alembic_version`` table.
   * **Present** — the database is already under Alembic. Run ``upgrade head``.
   * **Absent, and the inherited schema is present** (the ``users`` table
     exists) — this is a legacy database. The baseline is *stamped* (recorded
     as already applied) rather than replayed, because the tables are already
     there and replaying the baseline would fail. Then ``upgrade head`` runs
     the newer migrations, which are additive.
   * **Absent, and no schema** — a fresh database. ``upgrade head`` runs from
     the beginning; the baseline creates the inherited schema.
3. Reports what it did.

The legacy-detection step is logged loudly. Adopting a legacy database is a
one-way, deliberate operation and an operator should be able to see that it
happened.

Usage
-----
    python -m scripts.migrate status      # report only, change nothing
    python -m scripts.migrate upgrade     # bring the database to head
    python -m scripts.migrate downgrade -1
    python -m scripts.migrate history
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# The database URL must be resolvable before the application modules import,
# because `app.core.database` builds its engine at import time.
if os.environ.get("ALEMBIC_DATABASE_URL") and not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["ALEMBIC_DATABASE_URL"]

from sqlalchemy import inspect, text  # noqa: E402

from app.core.database import engine  # noqa: E402
from app.core.migrations import (  # noqa: E402
    BASELINE_REVISION,
    MIGRATION_STATE,
    current_revision,
    head_revision,
    run_pending_migrations,
)
from app.core.observability import get_logger  # noqa: E402

log = get_logger("karmathy.migrate")

#: A table that exists in the inherited schema. Its presence means the
#: database was built by `create_all()` and predates Alembic.
LEGACY_MARKER_TABLE = "users"


def _alembic_config():
    from alembic.config import Config

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    return cfg


def _is_legacy_schema(inspector) -> bool:
    """True when the database holds the inherited schema but no history."""
    tables = set(inspector.get_table_names())
    if "alembic_version" in tables:
        return False
    return LEGACY_MARKER_TABLE in tables


def _has_history(inspector) -> bool:
    return "alembic_version" in set(inspector.get_table_names())


def status() -> int:
    """Report the database's migration state without changing anything."""
    with engine.connect() as conn:
        inspector = inspect(conn)
        legacy = _is_legacy_schema(inspector)
        has_history = _has_history(inspector)
        tables = len(inspector.get_table_names())

        print("Database state")
        print("-" * 60)
        print(f"  dialect              : {engine.dialect.name}")
        print(f"  tables present       : {tables}")
        print(f"  alembic history      : {'present' if has_history else 'absent'}")
        print(f"  inherited schema     : {'detected (legacy)' if legacy else 'not detected'}")
        print(f"  current revision     : {current_revision() or '(none)'}")

    head = head_revision()
    print(f"  head revision(s)     : {head or '(none)'}")
    if legacy:
        print()
        print(
            "  ACTION: this database predates Alembic. Running `upgrade` will "
            "stamp the baseline and then apply the newer migrations."
        )
    return 0


def upgrade(revision: str = "head") -> int:
    """Bring the database to ``revision`` (default: head)."""
    try:
        state = run_pending_migrations(revision)
    except Exception as exc:  # noqa: BLE001
        # The release step runs before the server binds, so a failure here
        # ends the container and the reason is only in the container's
        # output. Recording it in the audit trail leaves it somewhere the
        # operator can read it from — the database is still there.
        _record_failure(exc)
        raise
    print(
        f"[migrate] Database is now at {state.get('current_revision') or revision}.",
        file=sys.stderr,
    )
    if state.get("legacy_schema_adopted"):
        print(
            "[migrate] The legacy schema was adopted by stamping the baseline.",
            file=sys.stderr,
        )
    return 0


def _record_failure(exc: BaseException) -> None:
    """Write a migration failure to the audit trail.

    Best effort: if the audit table cannot be written the failure is
    still reported on the console, and the original exception is what
    propagates.
    """
    try:
        from types import SimpleNamespace

        from app.core.audit import record_audit
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            # The row is written through the same writer as every other
            # audited action, so it is chained and carries the same shape.
            # A release runner has no user row, so the actor is a synthetic
            # object with a name and no id.
            record_audit(
                db,
                SimpleNamespace(id=None, username="release-migration"),
                "migration_failed",
                "Migration",
                details=f"{type(exc).__name__}: {exc}"[:2000],
            )
            db.commit()
            print(
                "[migrate] The failure was recorded in the audit trail.",
                file=sys.stderr,
            )
        finally:
            db.close()
    except Exception as inner:  # noqa: BLE001
        print(
            f"[migrate] The failure could not be recorded in the audit "
            f"trail: {type(inner).__name__}: {inner}",
            file=sys.stderr,
        )


def downgrade(revision: str) -> int:
    from alembic import command

    command.downgrade(_alembic_config(), revision)
    print(f"[migrate] Database downgraded to {revision}.", file=sys.stderr)
    return 0


def history() -> int:
    from alembic import command

    command.history(_alembic_config(), verbose=False)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Karmathy database migrations")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="report the migration state")
    up = sub.add_parser("upgrade", help="apply migrations up to a revision")
    up.add_argument("revision", nargs="?", default="head")
    down = sub.add_parser("downgrade", help="revert migrations")
    down.add_argument("revision", nargs="?", default="-1")
    sub.add_parser("history", help="show the migration history")

    args = parser.parse_args(argv)

    if args.command == "status":
        return status()
    if args.command == "upgrade":
        return upgrade(args.revision)
    if args.command == "downgrade":
        return downgrade(args.revision)
    if args.command == "history":
        return history()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
