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

---

## Addendum 2026-11-25 — 0016 boolean-default fix applied, chain BLOCKED at third (non-boolean) defect

Branch `agent/ops/pg-proof`, base `d4b9efe`. Exclusive paths only:
`backend/migrations/versions/0016_attendance_roster_link.py`,
`0017_forecast_costs.py`, `0029_schema_drift_fix.py` (same-pattern
recurrences only), `backend/pg_enum_checkfirst_test_suite.py` (extended),
this report. No app logic, rule packs, frontend, or other migration
semantics touched. No push.

### Fix (gate B — Boolean `server_default` PG-strictness)

`0016` declared `sa.Column("resolved", sa.Boolean(), server_default=
sa.text("0"))` — `DEFAULT 0`, rejected by PG for boolean columns. Model
`WorkingTimeViolation.resolved` (`backend/app/models/time_attendance.py:95`)
is `default=False`, so the fix is `server_default=sa.false()` (renders
`DEFAULT false` on PG, `0` on SQLite — behavior-neutral on SQLite).

Repo-wide grep of all `server_default` in `migrations/versions` found the
same pattern recurring twice, fixed identically: `0017_forecast_costs`
`excludes_statutory` (`sa.text("1")` → `sa.true()`, model
`default=True`); `0029_schema_drift_fix` `balance_applied`
(`sa.text("0")` → `sa.false()`, model `default=False`). All other
`server_default="0"`/`text("1")` hits are Integer/Numeric/String columns
(valid on PG) — untouched. Already-correct `sa.true()`/`sa.false()`
spellings (`0035`, `0036`, `0037`, `0039`, `0003`) untouched.

Regression: new static AST scan `test_no_boolean_int_server_default` in
`pg_enum_checkfirst_test_suite.py` fails on any Boolean column with an
int-like default (`0`/`1`/`"0"`/`"1"`/`text("0")`/`text("1")`); runs
everywhere. Post-fix suite (no PG in env): 2 passed, 0 failed, 1 skipped.

### Re-run (scratch PG 16.16, port 55433, fresh `initdb`, `upgrade head`)

`0016` and `0017` are FIXED on PG — log shows `created table
working_time_violations`, `created table forecast_costs`, chain proceeds
`0016 -> 0017 -> ... -> 0022`. Then a THIRD, DIFFERENT defect stops the
chain at `0022_audit_hash_chain` (`install_append_only`); per scope rules
it was NOT fixed (different class + lives in app logic
`backend/app/core/audit_chain.py`, outside exclusive paths).

Verbatim error:

```text
psycopg2.errors.SyntaxError: syntax error at or near "NOT"
LINE 1: CREATE TRIGGER IF NOT EXISTS audit_logs_no_update BEFORE UPD...
[SQL: CREATE TRIGGER IF NOT EXISTS audit_logs_no_update BEFORE UPDATE ON audit_logs BEGIN SELECT RAISE(ABORT, 'audit_logs is append-only'); END]
...
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.SyntaxError) syntax error at or near "NOT"
```

Cause (diagnosis only, no fix applied): `install_append_only`
(`backend/app/core/audit_chain.py:498`, called from
`0022_audit_hash_chain.py:121`) emits SQLite trigger syntax
(`CREATE TRIGGER IF NOT EXISTS ... BEGIN SELECT RAISE(ABORT, ...)`),
invalid on PostgreSQL (no `IF NOT EXISTS` on `CREATE TRIGGER`, no
`RAISE(ABORT)` body — needs a `RETURNS trigger` function +
`EXECUTE FUNCTION`). Valid on SQLite; broken on PG. Not the
Boolean-default pattern, requires app-logic change — out of scope.
`0029`'s `balance_applied` fix is therefore scan-gated but NOT yet
PG-proven (chain dies at `0022` before reaching it). Steps after the
blocker (seed+login smoke, backup/restore, downgrade/upgrade,
spot-checks) not executed.

### Regression (SQLite, behavior-neutrality)

`leave_test_suite.py`: 100 passed, 0 failed. `security_test_suite.py`:
2162 passed, 0 failed. `time_corrections_test_suite.py`: 63 passed,
0 failed. `pg_enum_checkfirst_test_suite.py` (no PG in env): 2 passed,
0 failed, 1 skipped.

### Verdict

Gate B Boolean defaults (`0016`, `0017`): FIXED on PG and regression-gated
(`0029` same-fix applied, PG proof pending). Full PG proof: still
BLOCKED — now at `0022_audit_hash_chain` SQLite-trigger-syntax
`SyntaxError` (verbatim above). Cleanup: `pg_ctl stop` exit 0,
`rm -rf /tmp/lp-pgdata /tmp/lp-venv` + logs; `pg_isready` no response,
no postgres/uvicorn residue.

---

## Addendum 2026-11-25 — 0022 trigger-syntax fix applied, chain BLOCKED at fourth (non-trigger) defect

Branch `agent/ops/pg-proof`, base `7e1d9c2`. Exclusive paths only:
`backend/app/core/audit_chain.py` (`install_append_only` + same-file
downgrade recurrence `remove_append_only`), `backend/
pg_enum_checkfirst_test_suite.py` (extended), this report. Migration
`0022` itself untouched. No other app logic, migrations, rule packs,
frontend. No push. Synthetic data only.

### Fix (gate A — append-only trigger PG syntax)

`install_append_only` (`audit_chain.py:482`, called from
`0022_audit_hash_chain.py:121`) emitted SQLite-only DDL on every
non-Oracle dialect: `CREATE TRIGGER IF NOT EXISTS ... BEGIN SELECT
RAISE(ABORT, ...)` — invalid on PG (no `IF NOT EXISTS` on
`CREATE TRIGGER`, no `RAISE(ABORT)` body). Now dialect-aware:
SQLite/Oracle branches byte-identical; `postgresql` branch emits
`CREATE OR REPLACE FUNCTION <trigger>_fn() RETURNS trigger ...
RAISE EXCEPTION ... LANGUAGE plpgsql` + `DROP TRIGGER IF EXISTS` +
`CREATE TRIGGER ... BEFORE <op> ... FOR EACH ROW EXECUTE FUNCTION`.
Downgrade `remove_append_only` kept consistent (same-file recurrence):
PG drops the trigger then `DROP FUNCTION IF EXISTS <trigger>_fn()`.

Repo-wide grep for other migration-reachable SQLite-only DDL emitters
(`RAISE(ABORT`, `sqlite_master`, `CREATE TRIGGER`, backtick quoting)
across `app/core` + `migrations`: the ONLY emitter is
`install_append_only`; the one other `sqlite_master` hit is a test
helper (`app/api/v1/endpoints/test_assets.py:529`), not migration DDL —
untouched. No same-pattern recurrences remain.

Regression: new static check
`test_append_only_trigger_branches_on_dialect` in
`pg_enum_checkfirst_test_suite.py` requires the PG markers
(`CREATE OR REPLACE FUNCTION`, `RAISE EXCEPTION`, `EXECUTE FUNCTION`,
`DROP TRIGGER IF EXISTS`, `DROP FUNCTION IF EXISTS`) while the SQLite
spellings stay present. SQLite suites: `audit_test_suite.py` 29
passed / 0 failed; `audit_chain_test_suite.py` 58 passed / 0 failed;
`pg_enum_checkfirst_test_suite.py` (no PG in env) 3 passed / 0 failed /
1 skipped.

### Re-run (scratch PG 16.16, port 55433, fresh `initdb`, `upgrade head`)

`0022` is FIXED on PG — log shows `[0022_audit_hash_chain] created
audit_chain_head`, `chained 0 existing entries`, `seeded the head`,
`append-only triggers installed on audit_logs`, chain proceeds
`0022 -> 0023 -> ... -> 0033`. Then a FOURTH, DIFFERENT defect stops
the chain at `lp_files_url_rewrite`; per scope rules it was NOT fixed.

Verbatim error:

```text
psycopg2.errors.UndefinedFunction: operator does not exist: leaveledgerentrytype ~~ unknown
LINE 3: WHERE leave_ledger.entry_type LIKE '/files/%'
HINT:  No operator matches the given name and argument types. You might need to add explicit type casts.
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedFunction) operator does not exist: leaveledgerentrytype ~~ unknown
```

Cause (diagnosis only, no fix applied): `lp_files_url_rewrite`
calls `count_legacy_files_urls` (`app/storage/url_rewrite.py`), which
issues `LIKE` against the native PG enum column
`leave_ledger.entry_type`. PG defines no `~~` operator for a custom
enum vs `unknown`; SQLite/Oracle compare it as text. Requires an
app-logic/migration change (cast or text comparison) — out of scope.
Single-transaction PG DDL rolled the scratch DB back to empty
(`pg_tables` = 0, no `alembic_version`); steps after the blocker
(seed+login smoke, backup/restore, downgrade/upgrade, spot-checks)
not executed.

### Verdict

Gate A trigger syntax (`0022`): FIXED on PG and regression-gated.
Full PG proof: still BLOCKED — now at `lp_files_url_rewrite`
enum-`LIKE` `UndefinedFunction` (verbatim above). Cleanup:
`pg_ctl stop` exit 0, `rm -rf /tmp/lp-pgdata /tmp/lp-venv` + logs;
`pg_isready` no response, no postgres/uvicorn residue.

---

## Addendum 2026-11-25 — lp_files_url_rewrite enum-LIKE fix applied, chain BLOCKED at fifth (non-LIKE) defect

Branch `agent/ops/pg-proof`, base `4020b2e`. Exclusive paths only:
`backend/migrations/versions/lp_files_url_rewrite.py`,
`backend/pg_enum_checkfirst_test_suite.py` (extended), this report.
`app/storage/url_rewrite.py` read-only-checked, NOT edited (see follow-up
below). No other app code, migrations, rule packs, frontend. No push.
Synthetic data only.

### Fix (gate A — native-enum `LIKE` in `lp_files_url_rewrite`)

On PG a reflected native-enum column (e.g. `leave_ledger.entry_type`) is a
`String` subclass, so the shared helper's bare `column.like(...)` rendered
`<enumtype> ~~ unknown` → `UndefinedFunction`. The migration no longer
calls the app helpers' SQL emitters: it imports ONLY `OLD_PREFIX` /
`NEW_PREFIX` and emits its own SQL with portable `CAST(<col> AS TEXT)` in
every `LIKE` predicate (never the PG-only `::` operator — SQLite behavior
identical). A per-column count runs first, so an enum column (count always
0) never reaches the `func.replace(<enum-col>, ...)` UPDATE PG could not
resolve. Same rows rewritten; idempotent; downgrade mirrors.

Follow-up required (out of scope, NOT fixed): `app/storage/url_rewrite.py:45`
and `:79` still issue bare `column.like(...)` — any PG caller of
`rewrite_prefix`/`count_legacy_files_urls` (e.g. `scripts/verify_files_urls.py`)
hits the same `UndefinedFunction`. Needs a separate app-logic follow-up.

Regression: new static scan `test_no_bare_like_without_cast` in
`pg_enum_checkfirst_test_suite.py` fails on any `.like()`/`.ilike()`
without a `cast()` receiver across `versions/*.py` (string-literal SQL such
as `0030`'s Oracle-only `REGEXP_LIKE` untouched); runs everywhere. Red to
green: bare `column.like(...)` flagged, `cast(column, Text).like(...)`
clean; post-fix suite (no PG in env): 4 passed, 0 failed, 1 skipped.

### Re-run (scratch PG 16.16, port 55433, fresh `initdb`, `upgrade head`, twice)

`lp_files_url_rewrite` is FIXED on PG — log shows
`0033 -> lp_files_url_rewrite -> 0034_pg_foundations` with
`[lp_files_url_rewrite] no stored /files/ URLs found; nothing to rewrite`,
no `UndefinedFunction`, chain proceeds `0034 -> ... -> 0043`. Then a FIFTH,
DIFFERENT defect stops the chain at `0044_forecasting_tenant_isolation`;
per scope rules it was NOT fixed.

Verbatim error:

```text
psycopg2.errors.StringDataRightTruncation: value too long for type character varying(32)
sqlalchemy.exc.DataError: (psycopg2.errors.StringDataRightTruncation) value too long for type character varying(32)
[SQL: UPDATE alembic_version SET version_num='0044_forecasting_tenant_isolation' WHERE alembic_version.version_num = '0043_integrity_expand']
```

Cause (diagnosis only, no fix applied): Alembic's `alembic_version.version_num`
is `VARCHAR(32)`; the revision id `0044_forecasting_tenant_isolation` is 33
characters. SQLite does not enforce `VARCHAR` length; PG rejects the stamp.
Different class (version stamping, not enum-`LIKE`) and different migration
(`0044`, outside exclusive paths) — out of scope. Single-transaction PG DDL
rolled the scratch DB back to empty (`pg_tables` = 0, no `alembic_version`,
verified via `psql`); steps after the blocker (seed+login smoke,
backup/restore, downgrade/upgrade, spot-checks) not executed.

### Regression (SQLite, behavior-neutrality)

`leave_test_suite.py`: 100 passed, 0 failed. `security_test_suite.py`: 2162
passed, 0 failed. `pg_enum_checkfirst_test_suite.py` (no PG in env):
4 passed, 0 failed, 1 skipped.

### Verdict

Gate A enum-`LIKE` (`lp_files_url_rewrite`): FIXED on PG and
regression-gated. Full PG proof: still BLOCKED — now at
`0044_forecasting_tenant_isolation` version-id `StringDataRightTruncation`
(verbatim above). Cleanup: `pg_ctl stop` exit 0,
`rm -rf /tmp/lp-pgdata /tmp/lp-venv` + logs; `pg_isready` no response,
no postgres/uvicorn residue.

## Addendum 2026-11-25 — 0044 version-stamp width fix applied, FULL PG PROOF PASSES

Branch `agent/ops/pg-proof`, base `0c4d7fa`. Exclusive paths only:
`backend/migrations/env.py` (version-table handling only),
`backend/pg_enum_checkfirst_test_suite.py` (extended), this report. No
revision id renamed, no app logic, migrations, rule packs, frontend touched.
No push. Synthetic data only.

### Fix (gate A — `alembic_version.version_num` truncation at 0044)

Alembic auto-creates `alembic_version(version_num VARCHAR(32))`
(`alembic/ddl/impl.py:169`, `Column("version_num", String(32))`) via
`create(checkfirst=True)`, so a pre-existing table is reused untouched. Repo
ids reach 33 chars (`0044_forecasting_tenant_isolation`, `0047_...`);
SQLite ignores `VARCHAR` length, PG rejects the stamp with
`StringDataRightTruncation`. `env.py` now calls `_ensure_wide_version_table`
before `context.configure`: create-if-missing with generic `String(255)`
(`WIDE_VERSION_NUM_LENGTH`; plain VARCHAR on every dialect, no PG-only
syntax), existing tables never altered, ids never renamed. A
`connection.commit()` follows the ensure — the inspection auto-begins a
transaction, and Alembic treats an in-transaction connection as externally
managed (`_in_external_transaction`) and never commits the run itself
(caught on SQLite: schema persisted via pysqlite DDL auto-commit but the
final stamp silently rolled back; on PG the whole run would roll back).

Regression: two static tests — every `revision`/`down_revision` id in
`versions/*.py` fits `WIDE_VERSION_NUM_LENGTH` (constants resolved, so
0018/0019 covered); `env.py` contains the ensure markers incl.
`connection.commit()`. Runs everywhere. Red to green: width 32 flags 0044
(own revision + 0045's down_revision) and 0047; width 255 clean. Post-fix
suite (no PG in env): 6 passed, 0 failed, 1 skipped.

### Re-run (scratch PG 16.16, port 55433, fresh `initdb`, full proof, no new defect)

`upgrade head` exit 0 (~3.4 s): `0043 -> 0044 -> ... -> 0047`, stamp
`0047_expense_category_tenant_code` (33 chars), `version_num varchar(255)`.
Schema: 110 tables, 136 FKs, 43 `tenant_id` columns. Seed smoke:
`seed_admin` created SuperAdmin `pgproof`; uvicorn login 200 (JWT) and
`/me` 200, server stopped. Backup/restore: `pg_dump -Fc` 0.49 s (364005
bytes), drop/recreate/`pg_restore` 0.62 s exit 0; post-restore 110 tables,
5 rows, version 0047, seed user present — counts match. Downgrade -1 →
`0046_assets`; `upgrade head` → 0047, 110 tables.

### Regression (SQLite, behavior-neutrality)

`migration_test_suite.py`: 67 passed, 0 failed. `leave_test_suite.py`:
100 passed, 0 failed. Fresh-SQLite smoke: wide table created + stamped
0047; pre-existing narrow table left byte-identical, chain still advances.

### Verdict

Gate A version-stamp (0044/0047 33-char ids): FIXED on PG and
regression-gated. Full PG proof: PASSES — upgrade head (0047), schema
checks, seed+login smoke, backup/restore rehearsal, downgrade/upcycle.
Cleanup: `pg_ctl stop` exit 0; `rm -rf /tmp/lp-pgdata /tmp/lp-venv` + dumps
+ logs + scratch DBs; `pg_isready` no response, no postgres/uvicorn
residue, no stray files.
