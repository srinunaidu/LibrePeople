# PostgreSQL backup & restore (LibrePeople)

Tooling-gated runbook: every step states its prerequisite. Nothing below was
executed on the authoring machine (no Docker daemon, no PostgreSQL there), so
commands are quoted from the repo's scripts, not from a run. Companion to
`docs/runbooks/db-backup-restore.md` (script reference) and
`docs/runbooks/local-deploy.md` §§7–9 (rollback/recovery context).

## 0. Tooling prerequisites (all steps)

| Step | Needs |
|---|---|
| 1–2 backup | `pg_dump` (PostgreSQL client tools) on the machine running the script; connection via `DATABASE_URL=postgresql://…` **or** libpq env (`PGHOST/PGPORT/PGUSER/PGDATABASE/PGPASSWORD`); a `BACKUP_DIR` with free disk |
| 3 encryption | `gpg` (age alternative noted); a recipient key or passphrase — never committed, never pasted here |
| 4 verify | `pg_restore` on the verifying machine |
| 5 restore | `pg_restore` + `docker compose` access (compose stack) or `psql` target; a pre-existing snapshot of the target; owner approval for anything shared |
| 6 targets | owner sign-off — RPO/RTO below are PROPOSED, not commitments |

## 1. Full backup (pg_dump, custom format)

Tooling prerequisite: `pg_dump` + connection env (see §0).

```sh
scripts/db_backup.sh
BACKUP_DIR=/var/backups/karmathy scripts/db_backup.sh
```

This writes `BACKUP_DIR/karmathy-<timestamp>.dump` via
`pg_dump --format=custom` (see `scripts/db_backup.sh`). Record the migration
head alongside the archive (read-only):

```sh
docker compose exec backend python -m scripts.migrate status
```

Write the head (e.g. `0047_expense_category_tenant_code`) into a sidecar
file next to the archive, e.g. `<archive>.head.txt`.

## 2. Retention

- Keep the last 7 daily archives + the 4 most recent pre-deploy snapshots.
- Name pre-deploy snapshots explicitly so rollback can find them:
  `BACKUP_DIR` + `karmathy-predeploy-<date>.dump`
  (copy/rename the timestamped file after step 1).
- Prune only archives whose head file matches a superseded deploy AND that
  are older than 7 days. Never prune the most recent known-good archive.

## 3. Encryption at rest (no secrets in repo)

Tooling prerequisite: `gpg` (or `age`); recipient key available locally.

```sh
gpg --encrypt --recipient <ops-key-id> --output <archive>.dump.gpg <archive>.dump
```

- Guidance only: the `<ops-key-id>` / passphrase lives with the operator
  (Vault/KMS/local keyring). No key, passphrase, or ciphertext is ever
  committed — `.env.example` holds placeholders only.
- `age` alternative: `age --recipient <age-recipient> --output <archive>.dump.age <archive>.dump`.
- Decrypt only on the restoring host, immediately before step 5:
  `gpg --decrypt --output <archive>.dump <archive>.dump.gpg`.

## 4. Integrity verify (before you trust the archive)

Tooling prerequisite: `pg_restore` on the verifying machine.

```sh
test -s <archive>.dump && echo "non-empty OK"
pg_restore --list <archive>.dump | head
```

Both must succeed: non-empty file AND a readable table of contents. For a
restore rehearsal, restore into an empty scratch database (never the live
one) and run `python -m scripts.migrate status` afterwards — the head must
be ≤ current chain head (`backend/migrations/CHAIN_STRATEGY.md`).

## 5. Restore into a clean environment

Tooling prerequisite: snapshot of the target + `pg_restore` + owner approval.
`scripts/db_restore.sh` is destructive (`pg_restore --clean --if-exists`).

```sh
scripts/db_backup.sh                       # snapshot the target FIRST
scripts/db_restore.sh ./backups/karmathy-20261121-120000.dump
# non-interactive (automation only, snapshot must already exist):
scripts/db_restore.sh --yes ./backups/karmathy-20261121-120000.dump
```

After restore, bring the schema to head (the archive may predate it):

```sh
docker compose exec backend python -m scripts.migrate upgrade
docker compose exec backend python -m scripts.migrate status
```

Clean-environment variant (fresh volume, no live data at risk):

```sh
docker compose down -v                     # DELETES the db volume; clean env only
docker compose up -d db
scripts/db_restore.sh ./backups/karmathy-20261121-120000.dump
docker compose up -d backend
docker compose exec backend python -m scripts.migrate upgrade
curl http://localhost:8000/health
```

Chain rules (`backend/migrations/CHAIN_STRATEGY.md`): restore never renames
revisions; `alembic_version` rows in the archive reference real revision IDs,
so `upgrade` continues the linear chain to head. Full `downgrade base`
destroys schema + data — proven only on sqlite scratch, NOT on PG.

## 6. RPO / RTO — PROPOSED targets for owner approval (NOT commitments)

These numbers are proposals only. They have not been measured, exercised, or
agreed; do not quote them as SLAs.

| Target | Proposed value | Status |
|---|---|---|
| RPO (max data loss) | ≤ 24 h (daily backup) | PROPOSED — needs owner approval |
| RTO (restore to serving) | ≤ 4 h on a Docker host with images cached | PROPOSED — needs owner approval |

What approval covers: backup cadence, off-host archive copy, who holds the
encryption recipient, and who may authorise a production restore.

## 7. Oracle note — tooling-gated, out of scope

Existing Oracle/Autonomous Database installs are unaffected: nothing here
changes the Oracle chain. Oracle needs the wallet trio (`ORACLE_DSN`,
`ORACLE_USER`, `ORACLE_PASSWORD`, `ORACLE_WALLET_DIR`) plus live Oracle
credentials; connectivity probing is `scripts/test_adb_connection.py`. No
Oracle step was attempted and no Oracle connection details are recorded here.
