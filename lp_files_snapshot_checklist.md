# lp_files_url_rewrite — Real-Database Snapshot Checklist

> **Status: NOT RUN on a real database.** The migration and URL rewrite were
> exercised only against temporary SQLite (see "Confirmed pass" below). A real
> run is blocked until the product owner approves this checklist and provides
> the target database.

## What the migration does

`backend/migrations/versions/lp_files_url_rewrite.py` (revision
`lp_files_url_rewrite`) rewrites stored URLs from the old unauthenticated
prefix `/files/` to the authenticated prefix `/api/v1/files/`. It is driven by
`backend/app/storage/url_rewrite.py`:

* `rewrite_prefix` / `rewrite_stored_files_urls` — the UPDATE (idempotent:
  `LIKE '/files/%'` filter, so a re-run is a no-op).
* `count_legacy_files_urls` — reports every **text column** (`String`/`Text`)
  of **every table** in the database that still holds values under
  `/files/` (the script prints `LEGACY <table>.<column>: <n> row(s)`).

## Table and column to verify

On this tree the migration is exercised on **`documents.doc_url`**
(`backend/lp_phase2_files_test_suite.py` — "migration rewrites stored
`/files/` URLs on temporary SQLite"; the suite's Alembic run rewrote 2 rows
in `documents.doc_url`). A real database may have legacy values in other
tables/columns — **discover them with step 3**, not by hard-coding.

## Steps, in order

1. **Owner approval gate** — confirm from the product owner that the
   real-database migration is approved for this database and this time window.
2. **Snapshot** — create a restorable copy of the database, offline:
   * PostgreSQL: `pg_dump -Fc -f lp_files_snapshot_<ts>.dump <db>`
     (or use the RDS automated snapshot if that is the store of record);
     note the database name and the `pg_dump` options used.
   * SQLite: `sqlite3 <db> ".backup 'lp_files_snapshot_<ts>.db'"` and then
     `sqlite3 <db> "PRAGMA integrity_check;"` (must print `ok`).
   Store the snapshot outside the target database.
3. **Record expected row counts** — from the real database, run:
   ```
   python backend/scripts/verify_files_urls.py --database-url <URL>
   ```
   It prints one `LEGACY` line per affected `<table>.<column>: <n> row(s)`
   and exits 0 only when there are none. Record every line as the pre-migration
   baseline. Expected post-migration state: **0 legacy rows in every
   table.column** (the script prints `VERIFIED no stored values still use the
   unauthenticated /files/ prefix` and exits 0).
4. **Run the migration** — bring the database to the head revision that
   includes it:
   ```
   cd backend && python -m scripts.migrate upgrade
   ```
   (or `alembic upgrade head` using `backend/alembic.ini`). Do not run
   `lp_files_url_rewrite` against any other database.
5. **Verify after the run** — re-run step 3's command; expect `VERIFIED ...`
   and exit 0. Every previously recorded `<table>.<column>` must now report 0
   rows.

## Rollback steps

* **Undo the migration, keep the data** (the migration itself is reversible):
  ```
  cd backend && alembic downgrade lp_files_url_rewrite
  ```
  Its `downgrade()` rewrites `/api/v1/files/` back to `/files/`. Then confirm
  with:
  ```
  python backend/scripts/verify_files_urls.py --database-url <URL> --expect-legacy
  ```
  (exit 0 while legacy values are present — the deliberate-downgrade case).
* **Restore the database** from the snapshot taken in step 2:
  * PostgreSQL: `pg_restore -d <db> lp_files_snapshot_<ts>.dump` (or a point in
    time recovery from the automated snapshot).
  * SQLite: stop the application, copy `lp_files_snapshot_<ts>.db` over the
    live file, restart, and re-check `PRAGMA integrity_check` (expect `ok`).
  Then re-run `verify_files_urls.py --expect-legacy` and expect the same
  baseline counts recorded in step 3.

## Confirmed pass on the current tree (no real database touched)

* `python lp_phase2_files_test_suite.py` → **8 passed, 0 failed**
  (temp-SQLite migration tests, Alembic migration test on temp SQLite, and the
  verification script exit-0 check).
* `python scripts/verify_files_urls.py --database-url sqlite:///<temp suite DB>`
  → `VERIFIED no stored values still use the unauthenticated /files/ prefix`,
  **exit 0**.

## Notes

* The migration module docstring in
  `backend/migrations/versions/lp_files_url_rewrite.py` states it "has NOT been
  run against any real database. A snapshot of the database and explicit owner
  approval are required before running it anywhere else." — this checklist is
  that approval path.
* Never run this on any database other than the one approved in step 1.
