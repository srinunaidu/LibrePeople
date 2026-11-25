"""The audit hash chain: linkage, verification, tamper detection, append-only.

What this suite proves
----------------------
The audit trail is evidence only if a reader can tell an edited row from an
honest one. This suite pins the chain:

* every entry stores the hash of the one before it, starting from the genesis
  hash, and the stored hash recomputes from the row;
* ``verify_chain`` and ``python -m scripts.verify_audit_chain`` report the
  number of entries verified and exit 0 on an honest chain;
* an edited row is caught, the first failing entry is named, and the command
  exits non-zero;
* a row removed from the tail is caught by the head comparison;
* the database refuses UPDATE and DELETE on the audit table, and the
  downgrade removes those guards;
* two writers that read the same head cannot fork the chain, and concurrent
  writers produce one linear chain;
* an entry staged in a transaction that rolls back is not in the chain and
  does not move the head;
* the migration chain applies, refuses a tamper, and reverts cleanly.

Run:  python audit_chain_test_suite.py
"""
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
TMP_DIR = tempfile.mkdtemp(prefix="audit_chain_suite_")
DB_PATH = os.path.join(TMP_DIR, "chain.db")

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["ALEMBIC_DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"

from sqlalchemy import create_engine, select, text  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.audit import record_audit  # noqa: E402
from app.core.audit_chain import (  # noqa: E402
    GENESIS_HASH,
    _compare_and_set_head,
    _read_head,
    append_entry,
    backfill_chain,
    compute_entry_hash,
    install_append_only,
    remove_append_only,
    set_head,
    verify_chain,
)
from app.core.database import Base, engine  # noqa: E402
from app.models.audit import AuditChainHead, AuditLog  # noqa: E402

# Every model module is imported so that ``create_all`` can resolve the
# foreign keys the rest of the schema declares.
import importlib  # noqa: E402
import pkgutil  # noqa: E402

import app.models  # noqa: E402

for _finder, _name, _is_pkg in pkgutil.iter_modules(app.models.__path__):
    if not _is_pkg:
        importlib.import_module(f"app.models.{_name}")

RESULTS = {"pass": 0, "fail": 0}
FAILURES: list[tuple[str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        RESULTS["pass"] += 1
        print(f"  PASS  {name}")
    else:
        RESULTS["fail"] += 1
        FAILURES.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


Base.metadata.create_all(bind=engine)


def new_engine(name: str):
    path = os.path.join(TMP_DIR, f"{name}.db")
    eng = create_engine(
        f"sqlite:///{path}",
        connect_args={"timeout": 30, "check_same_thread": False},
    )
    Base.metadata.create_all(bind=eng)
    return eng


def run_verify_cli(db_path: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    env["SECRET_KEY"] = os.environ["SECRET_KEY"]
    return subprocess.run(
        [sys.executable, "-m", "scripts.verify_audit_chain"],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )


def run_migrations(db_path: str, direction: str, target: str) -> None:
    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    env["ALEMBIC_DATABASE_URL"] = f"sqlite:///{db_path}"
    env["SECRET_KEY"] = os.environ["SECRET_KEY"]
    result = subprocess.run(
        [sys.executable, "-m", "scripts.migrate", direction, target],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"migration {direction} {target} failed:\n{result.stdout}\n{result.stderr}"
        )


# ---------------------------------------------------------------------------
# The chain is built, and it links
# ---------------------------------------------------------------------------
print()
print("-" * 68)
print("Every entry links to the one before it")
print("-" * 68)

with Session(engine) as db:
    record_audit(db, None, "chain_probe", "Probe", 1, details="first")
    record_audit(db, None, "chain_probe", "Probe", 2, details="second")
    record_audit(db, None, "chain_probe", "Probe", 3, details="third")
    db.commit()

with Session(engine) as db:
    entries = db.execute(select(AuditLog).order_by(AuditLog.id)).scalars().all()
    head = db.get(AuditChainHead, 1)

check("three entries were written", len(entries) == 3, f"rows={len(entries)}")
check("the first entry starts at the genesis hash",
      bool(entries) and entries[0].prev_hash == GENESIS_HASH,
      f"prev_hash={entries[0].prev_hash if entries else None!r}")
check("each entry names the previous entry's hash",
      all(entries[i].prev_hash == entries[i - 1].entry_hash
          for i in range(1, len(entries))),
      f"prev_hashes={[e.prev_hash for e in entries]}")
check("every entry carries a hash",
      all(e.entry_hash and len(e.entry_hash) == 64 for e in entries),
      f"hashes={[e.entry_hash for e in entries]}")
check("the head row names the newest entry",
      head is not None and head.head_hash == entries[-1].entry_hash
      and head.head_id == entries[-1].id,
      f"head={head.head_hash if head else None!r} "
      f"last={entries[-1].entry_hash if entries else None!r}")
check("a stored hash recomputes from its row",
      bool(entries)
      and entries[0].entry_hash
      == compute_entry_hash(
          prev_hash=entries[0].prev_hash,
          actor_id=entries[0].actor_id,
          actor_name=entries[0].actor_name,
          action=entries[0].action,
          entity_type=entries[0].entity_type,
          entity_id=entries[0].entity_id,
          details=entries[0].details,
          source_ip_hash=entries[0].source_ip_hash,
          created_at=entries[0].created_at,
      ),
      f"stored={entries[0].entry_hash if entries else None}")

with Session(engine) as db:
    result = verify_chain(db)
check("an honest chain verifies", result.ok, result.message)
check("the verification counts the entries", result.entries == 3,
      f"entries={result.entries}")
check("the verification reports the head", result.head == entries[-1].entry_hash,
      f"head={result.head!r}")

cli = run_verify_cli(DB_PATH)
check("the command exits 0 on an honest chain", cli.returncode == 0,
      f"exit={cli.returncode} stderr={cli.stderr[:160]}")
check("the command reports the number of entries verified",
      "3 entries verified" in cli.stdout,
      f"stdout={cli.stdout[:160]!r}")
check("the command prints the head hash", entries[-1].entry_hash in cli.stdout,
      f"stdout={cli.stdout[:160]!r}")

# ---------------------------------------------------------------------------
# Append-only: the database refuses an update and a delete
# ---------------------------------------------------------------------------
print()
print("-" * 68)
print("The database refuses an update and a delete")
print("-" * 68)

with engine.begin() as conn:
    install_append_only(conn)
with engine.begin() as conn:
    triggers = {
        row[0]
        for row in conn.execute(
            text("SELECT name FROM sqlite_master WHERE type = 'trigger'")
        )
    }
check("the append-only triggers exist",
      {"audit_logs_no_update", "audit_logs_no_delete"} <= triggers,
      f"triggers={sorted(triggers)}")

update_refused = False
try:
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE audit_logs SET details = 'rewritten' WHERE id = :id"),
            {"id": entries[0].id},
        )
except Exception as exc:  # noqa: BLE001 - the refusal is the assertion
    update_refused = "append-only" in str(exc)
check("an update of an audit row is refused", update_refused,
      "the update was not refused")

delete_refused = False
try:
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM audit_logs WHERE id = :id"), {"id": entries[0].id}
        )
except Exception as exc:  # noqa: BLE001
    delete_refused = "append-only" in str(exc)
check("a delete of an audit row is refused", delete_refused,
      "the delete was not refused")

with Session(engine) as db:
    still_there = db.get(AuditLog, entries[0].id)
check("the refused statements changed nothing",
      still_there is not None and still_there.details == "first",
      f"row={still_there.details if still_there else None!r}")

with engine.begin() as conn:
    remove_append_only(conn)
with engine.begin() as conn:
    remaining = conn.execute(
        text("SELECT count(*) FROM sqlite_master WHERE type = 'trigger'")
    ).scalar()
check("the guards can be removed (the downgrade path)", remaining == 0,
      f"triggers={remaining}")

# ---------------------------------------------------------------------------
# A tampered row is caught, and named
# ---------------------------------------------------------------------------
print()
print("-" * 68)
print("An edited row is caught and the entry is named")
print("-" * 68)

with engine.begin() as conn:
    conn.execute(
        text("UPDATE audit_logs SET details = 'edited' WHERE id = :id"),
        {"id": entries[1].id},
    )
with Session(engine) as db:
    result = verify_chain(db)
check("an edited row fails verification", not result.ok, result.message)
check("the first failing entry is named", result.failure_id == entries[1].id,
      f"failure_id={result.failure_id} expected={entries[1].id}")
check("the failure says the row was edited",
      "edited" in (result.failure_reason or ""),
      f"reason={result.failure_reason!r}")
check("the entries before the failure are still counted", result.entries == 1,
      f"entries={result.entries}")

cli = run_verify_cli(DB_PATH)
check("the command exits non-zero on a tampered chain", cli.returncode == 1,
      f"exit={cli.returncode}")
check("the command names the failing entry", f"entry {entries[1].id}" in cli.stderr,
      f"stderr={cli.stderr[:200]!r}")

# Restoring the row makes the chain verify again: the failure was the edit,
# not the procedure.
with engine.begin() as conn:
    conn.execute(
        text("UPDATE audit_logs SET details = 'second' WHERE id = :id"),
        {"id": entries[1].id},
    )
with Session(engine) as db:
    result = verify_chain(db)
check("restoring the row restores the chain", result.ok, result.message)

# ---------------------------------------------------------------------------
# A row removed from the tail is caught
# ---------------------------------------------------------------------------
print()
print("-" * 68)
print("A truncated tail is caught by the head")
print("-" * 68)

truncation_engine = new_engine("truncation")
with Session(truncation_engine) as db:
    for index in range(3):
        append_entry(
            db, actor_id=None, actor_name="probe", action="truncate_probe",
            entity_type="Probe", details=f"entry-{index}",
        )
    db.commit()

with Session(truncation_engine) as db:
    result = verify_chain(db)
check("the truncation fixture verifies before the removal", result.ok, result.message)

with truncation_engine.begin() as conn:
    conn.execute(text("DELETE FROM audit_logs WHERE id = (SELECT MAX(id) FROM audit_logs)"))
with Session(truncation_engine) as db:
    result = verify_chain(db)
check("a removed tail entry fails verification", not result.ok, result.message)
check("the failure says the head and the last entry disagree",
      "head" in (result.failure_reason or ""),
      f"reason={result.failure_reason!r}")
check("the remaining entries still verify on their own",
      result.entries == 2, f"entries={result.entries}")
truncation_engine.dispose()

# ---------------------------------------------------------------------------
# Two writers cannot fork the chain
# ---------------------------------------------------------------------------
print()
print("-" * 68)
print("Two writers cannot fork the chain")
print("-" * 68)

race_engine = new_engine("race")

# Deterministic: both writers read the same head, one wins, the other's
# compare-and-set matches nothing.
with Session(race_engine) as first, Session(race_engine) as second:
    prev_first, _ = _read_head(first)
    prev_second, _ = _read_head(second)
    check("two writers read the same head", prev_first == prev_second,
          f"{prev_first!r} vs {prev_second!r}")
    append_entry(
        first, actor_id=None, actor_name="first", action="race_probe",
        entity_type="Probe", details="first wins",
    )
    first.commit()
    stale = _compare_and_set_head(second, prev_second, "f" * 64)
    second.rollback()
check("a stale writer cannot move the head", not stale,
      "the stale compare-and-set won")

with Session(race_engine) as db:
    append_entry(
        db, actor_id=None, actor_name="second", action="race_probe",
        entity_type="Probe", details="second retries on the new head",
    )
    db.commit()
with Session(race_engine) as db:
    result = verify_chain(db)
check("the retried writer extends the chain", result.ok and result.entries == 2,
      result.message)

# Concurrent: several threads append at once and the chain stays linear.
errors: list[str] = []


def worker(index: int) -> None:
    for attempt in range(5):
        for _try in range(40):
            with Session(race_engine) as db:
                try:
                    append_entry(
                        db, actor_id=None, actor_name=f"thread-{index}",
                        action="concurrent_probe", entity_type="Probe",
                        details=f"thread-{index}-{attempt}",
                    )
                    db.commit()
                    break
                except (OperationalError, RuntimeError) as exc:
                    db.rollback()
                    last = f"{type(exc).__name__}: {exc}"
                    time.sleep(0.02)
        else:
            errors.append(f"thread {index} attempt {attempt}: {last}")


threads = [threading.Thread(target=worker, args=(index,)) for index in range(3)]
for thread in threads:
    thread.start()
for thread in threads:
    thread.join(timeout=120)

check("the concurrent writers all committed", not errors, "; ".join(errors[:2]))
with Session(race_engine) as db:
    result = verify_chain(db)
    predecessors = {
        row.prev_hash for row in db.execute(select(AuditLog)).scalars().all()
    }
check("the concurrent chain is linear and complete",
      result.ok and result.entries == 2 + 15,
      f"{result.message} errors={errors[:1]}")
check("no entry shares a predecessor",
      len(predecessors) == result.entries,
      f"entries={result.entries} predecessors={len(predecessors)}")
race_engine.dispose()

# ---------------------------------------------------------------------------
# A rollback leaves no entry and does not move the head
# ---------------------------------------------------------------------------
print()
print("-" * 68)
print("A rolled-back transaction leaves no chain entry")
print("-" * 68)

rollback_engine = new_engine("rollback")
with Session(rollback_engine) as db:
    append_entry(
        db, actor_id=None, actor_name="probe", action="rollback_probe",
        entity_type="Probe", details="kept",
    )
    db.commit()
with Session(rollback_engine) as db:
    before_head, before_id = _read_head(db)
    before_count = db.execute(select(AuditLog)).scalars().all().__len__()
    append_entry(
        db, actor_id=None, actor_name="probe", action="rollback_probe",
        entity_type="Probe", details="discarded",
    )
    db.rollback()
with Session(rollback_engine) as db:
    after_head, after_id = _read_head(db)
    after_count = db.execute(select(AuditLog)).scalars().all().__len__()
    result = verify_chain(db)
check("the rolled-back entry is not in the table", after_count == before_count,
      f"before={before_count} after={after_count}")
check("the rolled-back entry did not move the head",
      (after_head, after_id) == (before_head, before_id),
      f"before={before_head!r} after={after_head!r}")
check("the chain still verifies after the rollback", result.ok, result.message)
rollback_engine.dispose()

# ---------------------------------------------------------------------------
# The migration applies, guards, and reverts
# ---------------------------------------------------------------------------
print()
print("-" * 68)
print("The migration applies, guards and reverts")
print("-" * 68)

migrated_path = os.path.join(TMP_DIR, "migrated.db")
run_migrations(migrated_path, "upgrade", "head")

with sqlite3.connect(migrated_path) as conn:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(audit_logs)")}
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'")}
    triggers = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'trigger'")}
check("the migration adds both chain columns",
      {"prev_hash", "entry_hash"} <= columns, f"columns={sorted(columns)}")
check("the migration creates the head table",
      "audit_chain_head" in tables, f"tables={sorted(tables)}")
check("the migration installs the append-only triggers",
      {"audit_logs_no_update", "audit_logs_no_delete"} <= triggers,
      f"triggers={sorted(triggers)}")

migrated_engine = create_engine(f"sqlite:///{migrated_path}")
with Session(migrated_engine) as db:
    record_audit(db, None, "migration_probe", "Probe", 1, details="on the migrated schema")
    db.commit()
    result = verify_chain(db)
check("an entry written on the migrated schema verifies", result.ok, result.message)

refused = False
try:
    with migrated_engine.begin() as conn:
        conn.execute(text("DELETE FROM audit_logs"))
except Exception as exc:  # noqa: BLE001
    refused = "append-only" in str(exc)
check("the migrated schema refuses a delete", refused, "the delete was not refused")
migrated_engine.dispose()

run_migrations(migrated_path, "downgrade", "0021_audit_source_address")
with sqlite3.connect(migrated_path) as conn:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(audit_logs)")}
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'")}
    triggers = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'trigger'")}
check("the downgrade removes the chain columns",
      not ({"prev_hash", "entry_hash"} & columns), f"columns={sorted(columns)}")
check("the downgrade removes the head table",
      "audit_chain_head" not in tables, f"tables={sorted(tables)}")
check("the downgrade removes the guards", not triggers, f"triggers={sorted(triggers)}")
check("the downgrade keeps the audit rows",
      sqlite3.connect(migrated_path).execute(
          "SELECT count(*) FROM audit_logs").fetchone()[0] == 1,
      "the rows were lost")

run_migrations(migrated_path, "upgrade", "head")
with sqlite3.connect(migrated_path) as conn:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(audit_logs)")}
check("the chain can be applied again", {"prev_hash", "entry_hash"} <= columns,
      f"columns={sorted(columns)}")

# A row written by the previous release between the expand and the contract
# revision is chained by the contract, not refused by it. The shape is the
# one revision 0022 leaves behind: the chain columns exist and are nullable.
late_engine = create_engine(f"sqlite:///{os.path.join(TMP_DIR, 'late.db')}")
with late_engine.begin() as conn:
    conn.execute(text(
        "CREATE TABLE audit_logs ("
        "id INTEGER PRIMARY KEY, actor_id INTEGER, actor_name VARCHAR(100), "
        "action VARCHAR(80) NOT NULL, entity_type VARCHAR(60) NOT NULL, "
        "entity_id INTEGER, details TEXT, tenant_id VARCHAR(60), "
        "break_glass_grant_id INTEGER, source_ip_hash VARCHAR(64), "
        "prev_hash VARCHAR(64), entry_hash VARCHAR(64), created_at TIMESTAMP)"
    ))
    conn.execute(text(
        "CREATE TABLE audit_chain_head ("
        "id INTEGER PRIMARY KEY, head_hash VARCHAR(64) NOT NULL, "
        "head_id INTEGER, updated_at TIMESTAMP)"
    ))
    conn.execute(
        text("INSERT INTO audit_chain_head (id, head_hash) VALUES (1, :genesis)"),
        {"genesis": GENESIS_HASH},
    )
    conn.execute(text(
        "INSERT INTO audit_logs (actor_name, action, entity_type, details, "
        "created_at) VALUES ('old-release', 'late_write', 'Probe', "
        "'written between revisions', CURRENT_TIMESTAMP)"
    ))
    chained, late_id, late_hash = backfill_chain(conn)
    set_head(conn, late_hash, late_id)
check("the backfill chains a late write", chained == 1, f"chained={chained}")
with Session(late_engine) as db:
    result = verify_chain(db)
check("the chain with the late write verifies",
      result.ok and result.entries == 1, result.message)
late_engine.dispose()

# ---------------------------------------------------------------------------
# A legacy table without the chain columns takes the expand-then-contract path
# ---------------------------------------------------------------------------
# The production database was built by ``create_all`` long before this
# revision, so it has rows and no chain columns. This fixture reproduces that
# shape: migrate to 0021, swap in a legacy ``audit_logs`` with two rows, then
# upgrade. It is the only place the nullable-expand path actually runs.
print()
print("-" * 68)
print("A legacy table is expanded, backfilled and contracted")
print("-" * 68)

legacy_path = os.path.join(TMP_DIR, "legacy.db")
run_migrations(legacy_path, "upgrade", "0021_audit_source_address")
with sqlite3.connect(legacy_path) as conn:
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute(
        "CREATE TABLE audit_logs_legacy ("
        "id INTEGER PRIMARY KEY, actor_id INTEGER, actor_name VARCHAR(100), "
        "action VARCHAR(80) NOT NULL, entity_type VARCHAR(60) NOT NULL, "
        "entity_id INTEGER, details TEXT, source_ip_hash VARCHAR(64), "
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    conn.executemany(
        "INSERT INTO audit_logs_legacy (actor_name, action, entity_type, "
        "entity_id, details) VALUES (?, ?, ?, ?, ?)",
        [
            ("legacy", "legacy_probe", "Probe", 1, "before the chain"),
            ("legacy", "legacy_probe", "Probe", 2, "still before the chain"),
        ],
    )
    conn.execute("DROP TABLE audit_logs")
    conn.execute("ALTER TABLE audit_logs_legacy RENAME TO audit_logs")
    conn.commit()

run_migrations(legacy_path, "upgrade", "head")
with sqlite3.connect(legacy_path) as conn:
    # 0028 deliberately skipped audit_logs (decision 1) and 0029 adds the
    # tenant_id / break_glass_grant_id columns the model carries; verify_chain
    # reads them via the ORM, so the legacy fixture must have gained them from
    # the migration rather than from this test.
    info = {row[1]: row[3] for row in conn.execute("PRAGMA table_info(audit_logs)")}
    legacy_rows = conn.execute(
        "SELECT prev_hash, entry_hash FROM audit_logs ORDER BY id"
    ).fetchall()
    legacy_head = conn.execute(
        "SELECT head_hash FROM audit_chain_head WHERE id = 1"
    ).fetchone()
check(
    "the drift-fix revision adds the audit tenant columns",
    {"tenant_id", "break_glass_grant_id"} <= set(info),
    f"columns={sorted(info)}",
)
check("the expand revision adds both columns to a legacy table",
      {"prev_hash", "entry_hash"} <= set(info), f"columns={sorted(info)}")
check("the contract revision makes them NOT NULL",
      info.get("prev_hash") == 1 and info.get("entry_hash") == 1,
      f"prev_hash={info.get('prev_hash')} entry_hash={info.get('entry_hash')}")
check("both legacy rows were backfilled",
      len(legacy_rows) == 2 and all(row[1] for row in legacy_rows),
      f"rows={legacy_rows}")
check("the backfill starts at the genesis hash",
      bool(legacy_rows) and legacy_rows[0][0] == GENESIS_HASH,
      f"prev_hash={legacy_rows[0][0] if legacy_rows else None!r}")
check("the backfill links the rows in id order",
      len(legacy_rows) == 2 and legacy_rows[1][0] == legacy_rows[0][1],
      f"rows={legacy_rows}")
check("the head names the last backfilled entry",
      legacy_head is not None and legacy_head[0] == legacy_rows[-1][1],
      f"head={legacy_head!r} last={legacy_rows[-1][1] if legacy_rows else None!r}")

legacy_engine = create_engine(f"sqlite:///{legacy_path}")
with Session(legacy_engine) as db:
    result = verify_chain(db)
check("the backfilled chain verifies", result.ok and result.entries == 2,
      result.message)

refused_unhashed = False
try:
    with legacy_engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO audit_logs (action, entity_type, details) "
            "VALUES ('unhashed', 'Probe', 'no chain columns')"
        ))
except Exception as exc:  # noqa: BLE001 - the refusal is the assertion
    refused_unhashed = "NOT NULL" in str(exc).upper()
check("a write without the chain columns is refused", refused_unhashed,
      "the unhashed insert was not refused")
legacy_engine.dispose()

# ---------------------------------------------------------------------------
print()
print("=" * 68)
print(f"==== AUDIT CHAIN SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed ====")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 68)
raise SystemExit(1 if RESULTS["fail"] else 0)
