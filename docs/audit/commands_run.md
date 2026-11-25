# commands_run.md — Phase 0 audit, 2026-10-21

**Mode:** read-only, except for the creation of this repository's documentation.
**Isolation:** every backend and frontend command was run in a dedicated git worktree
(`/Users/srinivas/LLM/Workforce/karmathy-baseline`) checked out at `origin/main` = `70a8745`.
**Why:** the shared checkout has four lanes writing to it concurrently, and `ci/run_backend_tests.sh`
deletes `backend/*.db` before each suite, so two concurrent runs in one directory delete each
other's databases. This is defect **D-015**. The measurements below are the isolated ones.

**Command counting rule.** A check count is the sum of the per-suite `N passed` figures printed by
`ci/run_backend_tests.sh`, over the suites in its `SUITES` array, at a named commit, with every
suite green (adopted from `agents/qa-validation/DECISIONS.md` DEC-012). Backend checks and
Playwright journeys are **never summed**.

---

## 1. Repository and branch inventory

| Command | Outcome |
|---|---|
| `git -C <repo> rev-parse origin/main` | `70a874517ff6098a94b8c99cf9727c4cbe423536` |
| `git log --oneline origin/main -1` | `70a8745 docs: record the credential recovery and the schema diagnostics` |
| `git for-each-ref refs/heads refs/remotes` | 12 refs. Branches: `main` `70a8745`, `agents/super/board-2026-10-21` `58e4cd1`, `agents/super/phase0-2026-10-21` (this audit), `agent/platform-security/ps-01-production-reset-guard` `da927a8`, `agent/platform-security/ps-02-secret-scan-allowlist` `d35f183`, `agent/onboarding-config/OC-01-preset-schema-and-graph` `58e4cd1` (no commits), plus the historical `iter/*` and `feature/hcm-slack-revamp`. |
| `git worktree list` | 4 worktrees: the primary checkout, `karmathy-onboarding-config`, `karmathy-platform-security`, `karmathy-baseline` (this audit, now removed) |
| `git status --short` (primary checkout) | 40+ paths: uncommitted work in at least six lanes (§7 of the audit report) |
| `gh --version` | **not installed** |
| `curl -s https://api.github.com/repos/srinunaidu/Karmathy` | **HTTP 404** — the repository is private and no credential is available |
| `curl -s https://github.com/srinunaidu/Karmathy` | **HTTP 404** |
| `curl -s -o /dev/null -w "%{http_code}" https://github.com/.../actions/workflows/ci.yml/badge.svg` | **HTTP 404** — CI status is not readable from here |

**Consequence:** the CI status of `main` and the list of open pull requests could **not** be
read. Every CI claim in this audit is a local reproduction of the CI steps, not a run.

## 2. Backend test suites — the baseline

```bash
git worktree add --detach ../karmathy-baseline origin/main
cd ../karmathy-baseline && bash ci/run_backend_tests.sh
```

| Suite | Checks | Result |
|---|---|---|
| `startup_test_suite` | 10 | pass |
| `migration_test_suite` | 26 | pass |
| `security_test_suite` | 74 | pass |
| `security_headers_test_suite` | 8 | pass |
| `visibility_test_suite` | 29 | pass |
| `ops_model_test_suite` | 40 | pass |
| `mfa_test_suite` | 17 | pass |
| `jobs_test_suite` | 21 | pass |
| `metrics_test_suite` | 41 | pass |
| `data_quality_test_suite` | 44 | pass |
| `import_test_suite` | 43 | pass |
| `reset_admin_password_test_suite` | 15 | pass |
| `schema_drift_test_suite` | 12 | pass |
| `schema_alignment_test_suite` | 14 | pass |
| `smoke_test_phases_3_7` | 39 | pass |
| `smoke_test_client_onboarding` | 20 | pass |
| `smoke_test_all_phases` | 67 | pass |
| **Total** | **520** | **17 suites, 0 failed** |

> The **530** quoted in `agents/PROGRESS.md` and the Release Manager handoff is **not
> reproducible**. It is 520 plus either the harness's own summary line or the 10 Playwright
> journeys. Corrected by `agents/DECISIONS.md` DEC-012 and `agents/PROGRESS.md`.

The suites are deterministic: the isolated run above was repeated with the same result.

## 3. Security gates

| Command | Outcome |
|---|---|
| `.venv/bin/python ci/secret_scan.py` | **exit 1** — `secret_scan: 11 finding(s)`, all local test fixtures in `backend/reset_admin_password_test_suite.py`, `backend/scripts/reset_admin_password.py`, `frontend/e2e/{contrast,first-login,navigation}.spec.ts`, `frontend/playwright.config.ts`. The published credential is **not** among them. |
| `grep -rn "rule_pack_not_verified" backend/ --include="*.py"` | **no match anywhere in the backend** — the payroll rule-pack gate does not exist (defect D-014) |
| `grep -c "rule_pack\|RulePack\|verified" backend/app/api/v1/endpoints/payroll.py` | **0** |
| `grep -rn "require_roles\|require_any_role" backend/app --include="*.py" \| grep -v deps.py` | **no match** — the role half of the central policy module is never used by any endpoint |
| `grep -rln "apply_visibility\|ensure_can_view_employee" backend/app/api/v1/endpoints/*.py` | **13 files** — the visibility half of the policy module *is* applied |
| `grep -rn "\.role" backend/app/api/v1/endpoints/*.py` | 3 ad-hoc role comparisons: `reports.py:124`, `reports.py:159`, `scheduling.py:182` |
| `grep -n "role" backend/app/models/user.py` | `role: Mapped[str] = mapped_column(String(50), default="Associate")` — a free string, not an enum |
| `grep -n "ALL_ROLES" backend/app/api/deps.py` | `("SuperAdmin", "HR", "Manager", "Associate", "PayrollViewer")` — `Manager` and `PayrollViewer` are named and enforced nowhere |

## 4. Contracts

| Command | Outcome |
|---|---|
| `.venv/bin/python scripts/merge_openapi.py --check` | `openapi.yaml is up to date` — exit 0 |
| `.venv/bin/python scripts/check_openapi_drift.py --app https://karmathy-backend.onrender.com` | exit 0 — `matched: 43`, `RESULT: OK - the application serves everything the contract promises`; **210 endpoints** are served but undeclared (`contracts/openapi/_undeclared.md`) |
| `curl -s https://karmathy-backend.onrender.com/api/v1/openapi.json` | **259 served operations** across 25 tags — the authoritative served surface |
| `ls backend/migrations/versions/*.py` | 6 revisions (`0001_baseline` … `0006_schema_alignment`) |
| `grep -c "def upgrade\|def downgrade" backend/migrations/versions/*.py` | every revision has **both** `upgrade` and `downgrade` |
| `grep -c "x-lifecycle: released" contracts/openapi/*.yaml` | 2 (one in `auth.yaml`, one in the merged `openapi.yaml`) |
| `grep -c "x-lifecycle: planned" contracts/openapi/*.yaml` | 125 — the contract declares far more than it promises |

## 5. Frontend

```bash
cd ../karmathy-baseline/frontend && npm run verify   # typecheck, check:routes, check:api-paths, build, check:classes
```

| Step | Outcome |
|---|---|
| `npm run typecheck` | pass |
| `npm run check:routes` | `✓ Route integrity OK — all internal links resolve to 61 registered routes.` |
| `npm run check:api-paths` | `✓ API path integrity OK — no request repeats the /api/v1 prefix.` |
| `npm run build` | pass — `dist/assets/index-CWYhdA1B.js` **668.28 kB** (gzip 192.36 kB), `index-BeIyGW2g.css` 45.82 kB; Vite warns the chunk exceeds 500 kB |
| `npm run check:classes` | `✓ Class integrity OK — every colour utility in the source was emitted.` |
| `npx playwright test` | **10 passed, 0 failed** — 2 contrast, 2 first-sign-in, 6 navigation. The `mobile` project matches `responsive.spec.ts`, which does not exist, so it contributes nothing while the summary says "10 passed". |

## 6. Live systems (read-only)

| Command | Outcome |
|---|---|
| `curl https://karmathy-backend.onrender.com/health` | `200 {"status":"healthy"}` |
| `curl https://karmathy-backend.onrender.com/health/schema` | `401` — diagnostic endpoints require authentication (`PUBLIC_DIAGNOSTIC_ENDPOINTS=false`) |
| `curl https://karmathy-frontend.onrender.com/` | `200` |

## 7. The primary working tree

```bash
git status --short     # in the primary checkout
```

Observed during this audit, all uncommitted, all in the shared checkout:

| Path | Lane |
|---|---|
| `backend/app/imports/`, `backend/app/api/v1/endpoints/import_export.py`, `backend/import_test_suite.py`, `backend/migrations/versions/0007_import_dry_runs.py`, `backend/golden/` | data-import |
| `backend/app/rules/`, `backend/app/models/imports.py`, `rule_packs/demo-synthetic-draft.json`, `docs/PAYROLL.md`, `docs/REPORTS.md` | payroll-rules |
| `backend/app/forecasting/`, `docs/FORECASTING.md` | planning |
| `backend/app/retention/`, `backend/app/storage/`, `backend/app/models/leave.py` | workforce-core / data-import |
| `backend/tests/`, `docs/validation/*` | qa-validation |
| `packages/`, `package.json`, `pnpm-workspace.yaml`, `turbo.json`, `docs/DESIGN_SYSTEM.md` | frontend-design |
| `agents/*/STATE.md`, `agents/*/LEARNINGS.md`, `agents/frontend-design/DECISIONS.md` (as `agents/DECISIONS.md`) | several |

## 8. Commands that could **not** be run

| Command | Why |
|---|---|
| `gh run list` / any CI status query | `gh` is not installed and the API answers 404 without a token |
| Any load or performance test | **no load harness exists in the repository** |
| A journey run against staging | **there is no staging environment**; production is off-limits while DEC-000 is open |
| A migration downgrade rehearsal against Oracle | no Oracle connection is available to this audit, and the free tier is the deployment target |
| `axe` accessibility run | axe-core is not in the dependency set and not in CI |
| Backup and restore rehearsal | no backup or restore script exists |

## 9. Reproducing this audit

```bash
git worktree add --detach ../karmathy-baseline origin/main
cp -R .venv ../karmathy-baseline/.venv           # the venv is git-ignored
cd ../karmathy-baseline && bash ci/run_backend_tests.sh
cd ../karmathy-baseline && .venv/bin/python ci/secret_scan.py
cd ../karmathy-baseline && .venv/bin/python scripts/merge_openapi.py --check
cd ../karmathy-baseline && .venv/bin/python scripts/check_openapi_drift.py --app https://karmathy-backend.onrender.com
cd ../karmathy-baseline/frontend && npm ci && npm run verify && npx playwright test
```

The isolation matters. Do not run the backend suites in a checkout that another agent is using.
