# Local deploy (docker-compose) — LibrePeople

Standalone local install from this repo. Every command below is exact and in
order. Nothing here was executed on the authoring machine (no Docker daemon
there — see "Tooling gate" at the bottom), so first-run output is described
from the repo's scripts and compose file, not from a run.

## Prerequisites

- Docker Engine with the Compose v2 plugin (`docker compose version` works).
- A shell at the repo root (`LibrePeople/`).
- No secrets committed: copy the example file and fill it in locally.

## 1. Configure environment

```sh
cp .env.example .env
```

Edit `.env` and set, at minimum:

| Variable | Value for local compose |
|---|---|
| `SECRET_KEY` | 32+ random chars — `python3 -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `DATABASE_URL` | `postgresql://librepeople:change-me@db:5432/librepeople` |
| `FIELD_ENCRYPTION_KEYS` | `key1:` + `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `FIELD_ENCRYPTION_ACTIVE_KEY_ID` | `key1` |
| `POSTGRES_USER` / `POSTGRES_DB` | `librepeople` (defaults already do this) |
| `POSTGRES_PASSWORD` | anything local-only |

The `db` host in `DATABASE_URL` is the compose service name, not a real
hostname. Keep `ENVIRONMENT=development` locally.

## 2. Build and start

```sh
docker compose up -d --build
```

What this does: builds `librepeople-backend` (runs migrations on start, then
uvicorn on 8000) and `librepeople-frontend` (nginx on 80), and starts
`librepeople-db` (`postgres:16-alpine`). The backend waits for the db
`pg_isready` healthcheck (`service_healthy`) before starting. The images are
the artefacts — there are no source bind-mounts, so a rollback restores the
previous build.

Follow progress:

```sh
docker compose ps
docker compose logs -f backend
```

## 3. Confirm the schema is at head

The backend container already ran `python -m scripts.migrate upgrade` as its
release step. Confirm (read-only):

```sh
docker compose exec backend python -m scripts.migrate status
```

If the database predates the migration chain, `upgrade` stamps the baseline
and moves forward — see `backend/scripts/migrate.py`. To migrate explicitly:

```sh
docker compose exec backend python -m scripts.migrate upgrade
```

## 4. Seed the first SuperAdmin

The app ships with zero users (fail-closed). Supply the password only through
the environment of the command — never in a file:

```sh
docker compose exec -e ADMIN_INITIAL_PASSWORD='<a strong password>' \
  backend python -m scripts.seed_admin
```

Optional overrides: `ADMIN_INITIAL_USERNAME`, `ADMIN_INITIAL_EMAIL` (same
`-e` mechanism). The password must pass the policy (12+ chars, 3 of 4
character classes). The account is created in a `must_change_password` state:
sign in once and set a new password. Container restarts never change the
password — recovery is `python -m scripts.reset_admin_password` by hand.

## 5. Health checks

```sh
curl http://localhost:8000/health        # backend liveness -> {"status":"healthy"}
curl -o /dev/null -s -w '%{http_code}\n' http://localhost/   # frontend -> 200
```

## 6. Stop / reset

```sh
docker compose down        # keeps data: pgdata is a named volume
docker compose down -v     # DELETES the database volume; data is gone
```

## 7. PostgreSQL backup & restore — tooling-gated

Tooling exists in-repo and is the only supported path:

- `scripts/db_backup.sh` — `pg_dump --format=custom` into `BACKUP_DIR`
  (default `./backups`). Needs `pg_dump` on the machine running it plus
  `DATABASE_URL=postgresql://…` or libpq env (`PGHOST/PGPORT/PGUSER/…`).
- `scripts/db_restore.sh [--yes] <archive.dump>` — destructive (`--clean`);
  snapshot first, never point at production without owner approval.

Full procedure: `docs/runbooks/db-backup-restore.md`. Neither script was run
here (no daemon, no database); the commands above are quoted from that
runbook, not from a local execution.

## 8. Oracle installs — tooling-gated, out of scope

Existing Oracle/Autonomous Database installs are unaffected by this compose
stack: nothing here changes the Oracle chain. Oracle needs the wallet trio
(`ORACLE_DSN`, `ORACLE_USER`, `ORACLE_PASSWORD`, `ORACLE_WALLET_DIR`) and
live Oracle credentials; connectivity probing is `scripts/test_adb_connection.py`.
No Oracle step was attempted here and no Oracle connection details are
recorded anywhere in this repo.

## Tooling gate (authoring machine)

`docker --version` on the authoring machine returns
`zsh: command not found: docker` — no daemon, so no image was built, no
container was started, and no `docker compose` command above was executed
there. Verify steps 2–5 on a machine with Docker before treating this
runbook as exercised.
