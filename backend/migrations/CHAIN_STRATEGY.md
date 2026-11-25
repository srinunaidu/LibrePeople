# Migration chain strategy (Agent D)

Base: `62d741a`. 49 version files, 49 revisions, **single linear chain,
single head**: `0047_expense_category_tenant_code`.

## 1. Graph map (from `revision`/`down_revision` in every file)

Live order is NOT filename order. Two filenames lie:

- `0006_schema_alignment` (down `0005_forecasting`) is the true 0006 on
  the main path: `…0005 → 0006_schema_alignment → 0007 → … → 0014…`.
- `0006_forecast_run_location_role` (down **`0014_payslip_contributions`**)
  is a misnamed later node: `0014 → 0006_forecast_run_location_role →
  0015_forecast_scenarios → 0016 → … → 0033`.
- `lp_files_url_rewrite` (down `0033_login_failure_window`) is **merged
  inline, not dangling**: `0033 → lp_files_url_rewrite →
  0034_pg_foundations → … → 0047`.
- `0018`/`0019` use indirection constants (`DOWN_REVISION`,
  `PREVIOUS_REVISION`) resolving to `0017_forecast_costs` and
  `0018_scenario_versions` respectively — same linear result.

`alembic history` + `ScriptDirectory.get_heads()` confirm: one head,
`walk_revisions()` yields all 49. Do NOT renumber/rename: `alembic_version`
rows in deployed DBs reference these IDs; renaming breaks `upgrade`.

## 2. Multiple-head handling

There is **none** in the runner: `app/core/migrations.py::head_revision()`
returns `heads[0]` (silently picks one); `scripts/migrate.py` just runs
`upgrade head` (Alembic errors on multiple heads at runtime). Test suites
repeat the `heads[0]` pattern (`migration_test_suite`,
`schema_alignment_test_suite`, `india_payroll_test_suite`).
Exception: `hr_helpdesk_test_suite` compares
`set(scripts.get_heads())` against stamped versions — dynamic and
multi-head-tolerant. Convention (single head + `heads[0]`) holds today;
a future branch must add an explicit merge revision — Alembic will refuse
`upgrade head` otherwise, which is the backstop.

## 3. Fresh-install proof (executed here, sqlite scratch COPY)

 scratch DB `/tmp/agentD_proof.db` (repo dev DB untouched; `.db` removed):

1. `alembic upgrade head` → exit 0, stamped
   `0047_expense_category_tenant_code`, 110 tables.
2. `alembic downgrade base` → exit 0, version rows empty.
3. `alembic upgrade head` → exit 0, back at head.
   Full log: `backend/migrations/proof/reupgrade-head.log`;
   `proof/history.txt` records the chain. No failures.

## 4. Oracle-compatibility notes (static review only — no PG/Oracle here)

- `env.py` renders `render_as_batch` on sqlite only; Oracle/PG get plain DDL.
- `0034_pg_foundations` is PG-guarded (`bind.dialect.name !=
  "postgresql"` → no-op): safe everywhere, no-op downgrade by design.
- `lp_files_url_rewrite` is pure DML via portable helpers — dialect-neutral.
- Several revisions branch on `bind.dialect.name == "sqlite"`
  (`0006_forecast_run_location_role`, `0043`, `0047`) or exclude sqlite
  (`0006_schema_alignment`); Oracle paths rely on `app/core/migrations.py`
  catalog helpers (ORA-01408/00942/01442 guards). **Not executed:**
  no Oracle (or PG) instance exists in this environment, so Oracle/PG
  behaviour is reviewed, not proven. Do not fabricate results.

## 5. Recommendation: keep the chain, do not consolidate

- **Keep 49-revision chain.** A squashed baseline would invalidate
  `alembic_version` stamps in legacy-adopted production DBs (stamped at
  `0001_baseline` + incremental history) and destroy the tested
  downgrade path proven above.
- **Rollback implication:** every revert is `downgrade -N` on real
  revisions; a baseline squash would make partial rollback impossible.
- If readability ever forces it: squash only with a bridge plan (stamp-map
  old→new IDs + dual-path `migrate.py`), never bare.

## 6. Honest limits

- sqlite proof only. PG extension line (`CREATE EXTENSION pgcrypto`)
  never executed (guard skips non-PG). Oracle never executed.
- `0047` downgrade drops/recreates a uniqueness constraint — data
  violating the old global uniqueness will fail re-upgrade; snapshot
  before downgrading production.
