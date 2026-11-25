"""The Oracle migration round trip.

Why this exists
---------------
The SQLite suite cannot see the failures that stop the migration chain on
Oracle. SQLite allows two indexes over one column list, folds every
identifier the same way in every case, and has no reserved words — so a
migration can pass every local test and still fail on the database the
product runs on. It did: the chain could not be applied to a fresh Oracle
schema at all, and the one defect that reached production took the deploy
down with it.

This script applies the chain to a **scratch** Oracle schema, downgrades it
to the base, and applies it again — three times — and reports the revision
after every step. It is the proof that the chain works on Oracle, and the
thing the release procedure runs before a release.

It needs the Autonomous Database wallet, so it cannot be an ordinary
pull-request job: the wallet and the schema password are release-time
secrets and the schema is a database that has to be created first. The
Release Manager decides where it runs; this script is what runs.

What it does
------------
1. **Refuses to touch the live schema.** ``ADMIN`` is the schema the
   product runs on and it holds rows the migrations would backfill and
   constrain. The script refuses it by name and refuses to run at all
   without an explicit ``--i-know-this-is-a-scratch-schema``.
2. **Empties the scratch schema.** Every table in it is dropped. Oracle
   commits DDL implicitly, so a failed migration leaves its tables behind
   and the next run has to start from nothing.
3. **Runs the round trip three times.** ``upgrade`` → ``downgrade base`` →
   ``upgrade``, three times in a row, and the revision is read from the
   database after every step.
4. **Checks the final catalog.** The revision is the head, and no two
   indexes in the schema cover the same column list — the property Oracle
   refuses with ORA-01408.

Usage
-----
    ORACLE_DSN=karmkathyadb_high \\
    ORACLE_USER=KARMA_VERIFY \\
    ORACLE_PASSWORD="$(cat ~/.karmathy/karma_verify_password)" \\
    ORACLE_WALLET_DIR=backend/wallet \\
    ORACLE_WALLET_PASSWORD="$(cat ~/.karmathy/wallet_password)" \\
    SECRET_KEY="$(openssl rand -base64 48)" \\
    python ci/oracle_migration_roundtrip.py --i-know-this-is-a-scratch-schema

The password is read from the environment and is never printed, never
written to a file and never committed.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"

#: The live schema. The product runs on it and it holds rows.
LIVE_SCHEMA = "ADMIN"

#: The revision the chain must reach. Read from the repository rather than
#: repeated here, so adding a revision does not mean editing this script.
sys.path.insert(0, str(BACKEND_DIR))


def _head_revision() -> str:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    heads = ScriptDirectory.from_config(cfg).get_heads()
    return heads[0] if heads else ""


def _engine():
    """The application's engine, built from the environment."""
    from app.core.database import engine

    return engine


def _revision(engine) -> str | None:
    from sqlalchemy import text

    with engine.connect() as conn:
        rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
    return rows[0][0] if rows else None


def _drop_everything(engine, schema: str) -> int:
    """Drop every table in the scratch schema, and the alembic history."""
    from sqlalchemy import text

    dropped = 0
    with engine.connect() as conn:
        tables = [
            row[0]
            for row in conn.execute(
                text(
                    "SELECT table_name FROM all_tables WHERE owner = :owner "
                    "AND table_name <> 'ALEMBIC_VERSION'"
                ),
                {"owner": schema},
            )
        ]
        for table in tables:
            conn.execute(
                text(f'DROP TABLE "{table}" CASCADE CONSTRAINTS PURGE')
            )
            dropped += 1
        conn.commit()
        try:
            conn.execute(text("DROP TABLE ALEMBIC_VERSION PURGE"))
            conn.commit()
        except Exception:  # noqa: BLE001
            conn.rollback()
    return dropped


def _duplicate_column_lists(engine, schema: str) -> list[str]:
    """The column lists that more than one index in the schema covers.

    Oracle allows two indexes over one column list only when the lists
    differ, and refuses the second with ORA-01408. A schema that has one is
    a schema that a later migration cannot extend.
    """
    from sqlalchemy import text

    query = text(
        "SELECT i.table_name, i.index_name, "
        "LISTAGG(ic.column_name, ',') WITHIN GROUP (ORDER BY ic.column_position) "
        "FROM all_indexes i "
        "JOIN all_ind_columns ic "
        "  ON ic.index_owner = i.owner AND ic.index_name = i.index_name "
        "WHERE i.owner = :owner "
        "GROUP BY i.table_name, i.index_name"
    )
    with engine.connect() as conn:
        rows = conn.execute(query, {"owner": schema}).fetchall()

    seen: dict[tuple[str, str], str] = {}
    problems: list[str] = []
    for table, index, columns in rows:
        key = (table.upper(), columns.upper())
        if key in seen:
            problems.append(
                f"{index} and {seen[key]} both index {table} ({columns})"
            )
        else:
            seen[key] = index
    return problems


def _run(direction: str, target: str) -> subprocess.CompletedProcess:
    """Run the migration CLI against the configured database."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(BACKEND_DIR)
    return subprocess.run(
        [sys.executable, "-m", "scripts.migrate", direction, target],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=1800,
    )


def _tail(result: subprocess.CompletedProcess, lines: int = 12) -> str:
    text = (result.stderr or "") + (result.stdout or "")
    return "\n".join(text.strip().splitlines()[-lines:])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="The Oracle migration round trip")
    parser.add_argument(
        "--cycles",
        type=int,
        default=3,
        help="how many times the upgrade/downgrade/upgrade cycle is run",
    )
    parser.add_argument(
        "--i-know-this-is-a-scratch-schema",
        action="store_true",
        help="confirm the schema is a scratch one and may be emptied",
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="do not empty the schema first (the chain then adopts what is there)",
    )
    args = parser.parse_args(argv)

    schema = (os.environ.get("ORACLE_USER") or "").upper()
    if not schema:
        print("ORACLE_USER is not set; there is no schema to test.", file=sys.stderr)
        return 2
    if schema == LIVE_SCHEMA:
        print(
            f"refusing to run against {LIVE_SCHEMA}: that is the live schema, "
            "it holds rows, and the migrations would backfill and constrain "
            "them. Point this at a scratch schema.",
            file=sys.stderr,
        )
        return 2
    if not args.i_know_this_is_a_scratch_schema:
        print(
            "this script empties the schema it is given. Pass "
            "--i-know-this-is-a-scratch-schema to confirm it is one.",
            file=sys.stderr,
        )
        return 2

    engine = _engine()
    head = _head_revision()
    print("=" * 68)
    print("ORACLE MIGRATION ROUND TRIP")
    print("=" * 68)
    print(f"  schema               : {schema}")
    print(f"  dialect              : {engine.dialect.name}")
    print(f"  head revision        : {head}")
    print()

    failures: list[str] = []

    if not args.no_reset:
        dropped = _drop_everything(engine, schema)
        print(f"  emptied the schema   : {dropped} table(s) dropped")
    else:
        print("  emptied the schema   : no (--no-reset)")

    for cycle in range(1, args.cycles + 1):
        print()
        print(f"  --- cycle {cycle} of {args.cycles} ---")

        result = _run("upgrade", "head")
        if result.returncode != 0:
            failures.append(f"cycle {cycle}: upgrade failed")
            print("  upgrade              : FAILED")
            print(_tail(result))
            break
        revision = _revision(engine)
        print(f"  upgrade              : {revision}")
        if revision != head:
            failures.append(f"cycle {cycle}: upgrade reached {revision}, not {head}")

        result = _run("downgrade", "base")
        if result.returncode != 0:
            failures.append(f"cycle {cycle}: downgrade to base failed")
            print("  downgrade to base    : FAILED")
            print(_tail(result))
            break
        revision = _revision(engine)
        print(f"  downgrade to base    : {revision or '(none)'}")
        if revision is not None:
            failures.append(f"cycle {cycle}: the schema is still at {revision}")

        result = _run("upgrade", "head")
        if result.returncode != 0:
            failures.append(f"cycle {cycle}: the second upgrade failed")
            print("  upgrade again        : FAILED")
            print(_tail(result))
            break
        revision = _revision(engine)
        print(f"  upgrade again        : {revision}")
        if revision != head:
            failures.append(f"cycle {cycle}: the second upgrade reached {revision}")

    print()
    problems = _duplicate_column_lists(engine, schema)
    if problems:
        failures.append("the schema has two indexes over one column list")
        print("  duplicate column lists:")
        for problem in problems:
            print(f"    - {problem}")
    else:
        print("  duplicate column lists: none")

    from sqlalchemy import text

    with engine.connect() as conn:
        tables = conn.execute(
            text("SELECT COUNT(*) FROM all_tables WHERE owner = :owner"),
            {"owner": schema},
        ).scalar()
    print(f"  tables in the schema : {tables}")

    print()
    print("=" * 68)
    if failures:
        print("ORACLE MIGRATION ROUND TRIP: FAILED")
        for failure in failures:
            print(f"  - {failure}")
        print("=" * 68)
        return 1
    print(f"ORACLE MIGRATION ROUND TRIP: {args.cycles} cycles passed")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
