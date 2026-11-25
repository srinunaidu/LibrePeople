# PostgreSQL Proof Report (scratch DB, reversible)

**Verdict: BLOCKED** — migration chain fails on PostgreSQL at revision 0012. No product code changed. Branch `agent/ops/pg-proof`, base `5289fb6`.

## Environment

postgres (PostgreSQL) 16.16 (Homebrew); Python 3.15.0; SQLAlchemy 2.1.5; alembic 1.20.1; psycopg2-binary (scratch venv `/tmp/lp-venv`, `--system-site-packages`; pinned `requirements.txt` uninstallable on 3.15 — ortools has no wheel, pydantic-core fails to build — so venv = system site-packages + psycopg2 only, repo untouched).

## Steps (command + UTC timestamp + exit code)

| # | Command | Time | Exit |
|---|---------|------|------|
| 0 | `brew install postgresql@16` (no sudo) | 2026-11-25T08:03Z | 0 |
| 1 | `postgres --version` → 16.16 | 08:03:14Z | 0 |
| 1 | `initdb -D /tmp/lp-pgdata` | 08:03:14Z | 0 |
| 1 | `pg_ctl -D /tmp/lp-pgdata -o "-p 55433 -k /tmp" start`; `pg_isready` ok; `createdb librepeople_proof` | 08:03:17Z | 0/0/0 |
| 2 | `alembic upgrade head` (no SECRET_KEY) | 08:05:11Z | 1 (config error, operator-side: `SECRET_KEY Field required`; retried with dummy ≥32-char value) |
| 2 | `ALEMBIC_DATABASE_URL=postgresql+psycopg2://…:55433/librepeople_proof alembic upgrade head` | 08:05:18Z | **1 — STOP per contract; steps 3–6 not executed** |

Revisions 0001_baseline → 0011 ran; 0012_leave_ledger failed. Tail of output:

```text
[0008_fk_indexes] 84 indexes created
[0009_credential_role_constraint] users.role holds only known roles
[0010_payroll_jurisdiction] pay_runs.jurisdiction is already present; skipping
psycopg2.errors.DuplicateObject: type "leaveledgerentrytype" already exists
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.DuplicateObject) type "leaveledgerentrytype" already exists
```

## Diagnosis (no fix applied — product code frozen)

`0001_baseline` calls `metadata.create_all(tables=<frozen subset>)`, which on PG creates the native enum `leaveledgerentrytype` (from model `LeaveLedger.entry_type`), although the owning `leave_ledger` table is NOT in the frozen set (0012 creates it). `0012_leave_ledger` then runs `op.create_table(... sa.Enum(..., name="leaveledgerentrytype") ...)`, which emits an unconditional `CREATE TYPE` → collision. Works on SQLite/Oracle (enums → VARCHAR, no CREATE TYPE); broken on PG. Because PG uses transactional DDL, the whole chain rolled back: DB left empty (no tables, no `alembic_version`). Fix belongs to the Architect (e.g. `checkfirst`/shared-Enum handling in 0001/0012) — out of scope for this agent.

## Rollback / cleanup

Rollback rehearsal (step 6) not reached — nothing to roll back (empty DB). Cleanup 08:07:06Z: `pg_ctl stop` exit 0; `rm -rf /tmp/lp-pgdata /tmp/lp-venv` + logs exit 0; `pg_isready` → no response (exit 2), `ps` shows no postgres/uvicorn residue. No running processes left.

## Explicitly NOT PROVEN

Oracle parity; production data volumes; any RPO/RTO commitment (no backup rehearsal ran — scratch DB only); TLS; multi-instance; seed/login/health on PG; the 110-table / constraint / tenant-discriminator checks.

---

## Addendum 2026-11-25 — enum fix applied, chain BLOCKED at second (non-enum) defect

Branch `agent/ops/pg-proof`, base `f669924`. Exclusive paths only:
`backend/migrations/versions/0012_leave_ledger.py`,
`backend/pg_enum_checkfirst_test_suite.py` (new), this report. No other app
code touched. No push.

### Fix (gate A)

`0012_leave_ledger`: the `entry_type` column's `sa.Enum(..., name=
"leaveledgerentrytype")` now declares `create_type=False`, and `upgrade()`
calls a new `_ensure_entry_type(bind)` first, which issues a standalone
`sa.Enum(...).create(bind, checkfirst=True)` with values read from `COLUMNS`.
A repo-wide grep confirms `0012` is the only migration version using
`sa.Enum`/`postgresql.ENUM`/`create_type`/`CREATE TYPE` — no same-pattern
recurrences exist. Behavior-neutral on SQLite/Oracle (enum compiles to
VARCHAR, no `CREATE TYPE`); required on PG. Table/column semantics unchanged.

New suite `backend/pg_enum_checkfirst_test_suite.py`: (a) static AST scan of
all `migrations/versions/*.py` — fails on any named enum without
`create_type=False` unless used only as the receiver of
`.create(checkfirst=True)`; (b) PG-gated `upgrade head` on a scratch DB when
`ALEMBIC_DATABASE_URL`/`PG_PROOF_URL` is a reachable postgresql URL, else
SKIP (never fails for missing PG). Red-to-green proven: pre-fix file fails
the scan at `0012_leave_ledger.py:102`; post-fix passes.

### Re-run (scratch PG 16.16, port 55433, fresh `initdb`, `upgrade head`)

`0012` is FIXED on PG — log shows `created leave_ledger` + all five indexes,
no `DuplicateObject`, chain proceeds `0012 -> 0013 -> ... -> 0016`. Then a
SECOND, DIFFERENT defect stops the chain at `0016_attendance_roster_link`
(`CREATE TABLE working_time_violations`); per scope rules it was NOT fixed.

Verbatim error:

```text
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.DatatypeMismatch) column "resolved" is of type boolean but default expression is of type integer
HINT:  You will need to rewrite or cast the expression.
[SQL:
CREATE TABLE working_time_violations (
	...
	resolved BOOLEAN DEFAULT 0,
	...
)
]
```

Cause (diagnosis only, no fix applied): `0016` declares
`sa.Column("resolved", sa.Boolean(), nullable=True, server_default=sa.text("0"))`
— an integer-literal default on a boolean column. SQLite accepts it; PG
rejects it. Not the enum pattern, so out of scope for this agent; the chain
cannot reach head/0047 until the Architect fixes it. Steps after the blocker
(seed+login smoke, backup/restore rehearsal, downgrade/upgrade, spot-checks)
not executed.

### Regression (SQLite, behavior-neutrality)

`leave_test_suite.py`: 100 passed, 0 failed. `security_test_suite.py`: 2162
passed, 0 failed. `migration_test_suite.py`: 67 passed, 0 failed.
`pg_enum_checkfirst_test_suite.py` (no PG in env): 1 passed, 0 failed,
1 skipped.

### Verdict

Gate A enum collision: FIXED and regression-gated. Full PG proof: still
BLOCKED — now at `0016_attendance_roster_link` boolean-default
`DatatypeMismatch` (verbatim above). Cleanup: `pg_ctl stop` exit 0,
`rm -rf /tmp/lp-pgdata /tmp/lp-venv` + logs; `pg_isready` no response,
no postgres/uvicorn residue.
