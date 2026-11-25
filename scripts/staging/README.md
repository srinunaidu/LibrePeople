# The staging environment

**What it is:** the application, the built frontend, and a **real Oracle schema** that holds no
customer data. It is what the pilot gate means by *"on staging"*.

**Why it is local and not hosted.** The free tier has room for one web service and one static
site, and both are used by production. A second hosted service would need a paid plan, which the
owner has not approved. What the environment needs to be is not a hostname — it is *the same
code, the same migrations and the same database engine as production*, separated by data. That is
what this is.

**The schema.** `KARMA_STAGE`, an empty Oracle user in the same Autonomous Database instance as
production. The live schema is `ADMIN`; this one has its own tables and its own password, in
`~/.karmathy/karma_stage_password`, mode `0600`, outside the repository. **The live schema is
never touched by anything in this directory.**

## Running it

```bash
cd /Users/srinivas/LLM/Workforce/Karmathy
bash scripts/staging/run.sh
```

It applies the migrations to the schema, seeds the synthetic accounts the journeys use, starts
the API on 8010 and the built frontend on 4173, and prints where everything is.

Then, in another shell:

```bash
cd frontend
npx playwright test --config ../scripts/staging/playwright.staging.config.ts
```

Or the whole gate in one command — it brings the environment up, runs the journeys against it,
and reports the result with the commit:

```bash
bash scripts/staging/gate.sh
```

To stop it:

```bash
pkill -f 'e2e_server.py' ; pkill -f 'vite preview'
```

## What it is for

| | |
|---|---|
| **The journey suite** | The local suite runs against a SQLite file. This runs against Oracle, so it exercises the engine that production uses: the identifier folding, the reserved words, the implicit DDL commits, the DDL that refuses a second index over one column list. |
| **The migration round trip** | `migrate upgrade` → `migrate downgrade base` → `migrate upgrade`, against a schema with no data. This is the check a SQLite suite cannot do, and it is the gate the release procedure needs. |
| **The release candidate** | Point the stack at a branch and the environment runs that branch. The code under test is the code that will be deployed. |
| **A rehearsal** | A backup and a restore can be rehearsed here, in a schema that holds nothing, instead of in production. |

## What it is not

- **It is not production.** It has no customer data, no real credentials and no public address.
- **It is not a substitute for a hosted staging service.** If the business later wants staging to
  be reachable from a browser outside the company network, that is a paid service and a separate
  decision (ESC-004).
- **It does not replace the local suite.** The local suite is fast and stays in CI. This one is
  slower and needs the wallet, so it is a release-time check, not a per-commit check.

## The one thing to be careful about

`run.sh` applies migrations to `KARMA_STAGE`. **Point it at the live schema and it will try to
migrate production.** The schema name comes from `STAGING_SCHEMA` and defaults to `KARMA_STAGE`;
the script refuses to start if the password file for that schema is not in `~/.karmathy/`, which is
the practical guard — the live schema's password is under a different name.

## The guards, and what they refuse

Two guards, on the two ways this environment can reach production. Both are checks, not
claims: each has been seen to fail.

| Guard | Where | Refuses |
|---|---|---|
| The schema | `scripts/staging/run.sh` | a schema whose name is a production one (`ADMIN`, `PROD`, `LIVE`, …), and an API URL on a production host. `STAGING_SCHEMA=ADMIN bash scripts/staging/run.sh` → *"refusing to run: 'ADMIN' is a production schema"*, exit 2 |
| The API base URL | `frontend/e2e/support/environment.ts`, run by `frontend/e2e/support/global-setup.ts` | a journey run pointed at a production host. `KARMA_API_URL=https://karmathy-backend.onrender.com/api/v1 npx playwright test` → the run stops in the global setup, before the first journey, exit 1 |

The journey guard treats every `*.onrender.com` host as production, because the deployed API
(`karmathy-backend.onrender.com`) and the deployed static site (`karmathy-frontend.onrender.com`)
are the only public services in this project and staging is local. A hosted staging service — a
paid decision nobody has approved (ESC-004) — would have to be listed in `PRODUCTION_HOSTS` as an
explicit exception before the guard would allow it.

## Before a release

```bash
bash scripts/staging/gate.sh
```

and record the result in `agents/PROGRESS.md` with the commit. The result and the J1–J14
coverage are written up in `docs/validation/JOURNEYS.md`. A release candidate that has not
been through this has not been tested against the database it will run on.
