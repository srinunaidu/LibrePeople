# PostgreSQL backup & restore (LibrePeople)

Stage 3 DB foundations. Oracle installs are unaffected: nothing here changes
the Oracle chain, and the scripts refuse to guess Oracle connection details.

## What exists

- `scripts/db_backup.sh` — `pg_dump --format=custom` to
  `BACKUP_DIR/karmathy-<timestamp>.dump` (default `BACKUP_DIR=./backups`).
- `scripts/db_restore.sh [--yes] <archive.dump>` — `pg_restore --clean
  --if-exists`. Destructive by design; asks for `YES` unless `--yes`.
- `docker-compose.yml` — `db` service (`postgres:16-alpine`), `pgdata`
  volume, `pg_isready` healthcheck; `backend` waits on `service_healthy`.
- `backend/migrations/versions/0034_pg_foundations.py` — PG-only `pgcrypto`
  marker, no-op elsewhere; chain head, chained on `lp_files_url_rewrite`.

## Prerequisites

- PostgreSQL client tools (`pg_dump`, `pg_restore`) where the scripts run.
- Connection via `DATABASE_URL=postgresql://…` **or** libpq env
  (`PGHOST`, `PGPORT`, `PGUSER`, `PGDATABASE`, `PGPASSWORD`). No credential
  is stored in the repo; `.env.example` holds placeholders only.
- A snapshot before any restore onto a database that matters.

## Backup

```sh
scripts/db_backup.sh
BACKUP_DIR=/var/backups/karmathy scripts/db_backup.sh
```

Verify: `pg_restore --list <archive.dump> | head` and confirm the file is
non-empty. Keep the archive with the migration head it was taken at
(`backend: python -m scripts.migrate status`).

## Restore

```sh
scripts/db_restore.sh ./backups/karmathy-20261121-120000.dump
# non-interactive (automation only, snapshot must already exist):
scripts/db_restore.sh --yes ./backups/karmathy-20261121-120000.dump
```

After restore, bring the schema to head (the archive may predate it):

```sh
cd backend && python -m scripts.migrate upgrade
```

## Operational notes

- Restore drops objects first (`--clean`). Never point it at production
  without a fresh backup and owner approval.
- `pgdata` is a named Docker volume; `docker compose down` keeps it,
  `docker compose down -v` deletes it. The second form destroys data.
- Oracle cutover is out of scope for Stage 3: existing Oracle installs keep
  the Oracle chain (`docs/product/postgresql-migration.md`).
