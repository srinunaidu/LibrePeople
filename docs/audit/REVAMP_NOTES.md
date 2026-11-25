# Karmathy HCM — Revamp Notes

**Date:** 2026-10-21 · **Author:** Super Agent · **Companion to** `docs/audit/AUDIT_REPORT.md`

Discrepancies that are **not** in the audit's top ten, and findings that are explicitly out of
scope. Each is recorded so that nobody re-derives it later, and so that a stale document is
corrected rather than silently contradicted.

---

## A. Documentation drift — the documents disagree with the code

| # | Discrepancy | Evidence | Action |
|---|---|---|---|
| A1 | **The feature matrix claimed `PY-08` VERIFIED.** The payroll refusal does not exist. | `grep -rn rule_pack_not_verified backend/` → no match; `payroll.py` has 0 rule-pack references | Corrected: `PY-10` is `broken` in `docs/product/FEATURE_MATRIX.md`. QA's re-verification pass had already moved the legacy row to `MISSING` (D-014). |
| A2 | **The matrix's import rows `I-01`…`I-07` read `MISSING` while the engine existed** — and iteration 5's log claims "I-01 through I-07" delivered. | `docs/validation/ITERATION_LOG.md` vs `docs/validation/FEATURE_MATRIX.md` | Corrected in the QA pass: `I-01` and `I-04` are `implemented`, the rest are partial or broken. The iteration log now agrees with the matrix. |
| A3 | **The matrix's summary table was the iteration-0 baseline** (13/35/45/5 across 98 rows) while the table held 150 rows. | `docs/validation/FEATURE_MATRIX.md` | The summary is now generated from the rows. |
| A4 | **Four feature IDs were used twice** — `RP-01`…`RP-04` for both rule packs and reports. | QA's status pass | The reports rows are renumbered `RC-`…; the catalogue uses capability IDs instead. |
| A5 | **Six documents quote four different test counts** (435, 425, 469, 530) and three different suite counts (11, 14, 17). | `docs/validation/TEST_COUNT.md` | The method is fixed by DEC-012: the sum of per-suite `N passed` at a named commit. The measured value is **520**. The `530` in `agents/PROGRESS.md` and the Release Manager handoff was wrong and is corrected. |
| A6 | **The matrix cited `GET /imports/templates`; the application serves `/import-export/import/{entity}/template/{entity}`.** | the served OpenAPI | Corrected. |
| A7 | **`agents/DECISIONS.md` no longer holds the coordinator's record.** It was replaced by another lane's design-decisions file before a `git add agents/` staged it. The coordinator's DEC-000…DEC-011 record was never committed. | `git show 0ed1376:agents/DECISIONS.md` is a design-decisions file | **Restored** in this audit, with the lane's design decisions preserved as an annex and each labelled as a lane proposal pending ratification. See `DEC-014`. |
| A8 | **The contract promises 92 operations; the application serves 259.** 210 endpoints are undeclared and 125 operations are marked `planned`. | `check_openapi_drift.py`, `grep -c "x-lifecycle: planned"` | `SUP-02` triage, by domain, in dependency order. The contract is not edited automatically. |
| A9 | **The import contract and the implementation disagree on the flow's shape.** The contract declares `/imports/uploads/{upload_id}/dry-run`; the code serves `/import-export/import/{entity}/dry-run`. | `contracts/openapi/imports.yaml` vs the served routes | `DEC-003`. |

---

## B. Findings that are out of scope for the pilot, recorded so they are not lost

| # | Finding | Why out of scope |
|---|---|---|
| B1 | **The seed's production guard runs after `app.models` is imported**, so a non-Oracle URL without a driver crashes with `ModuleNotFoundError` instead of refusing. It also refuses staging, though the brief allows it. | Local tooling. D-017, Low. Fix in the same pass as the harness work. |
| B2 | **`employee-validator` is used via `EmailStr` but is not declared** in `requirements.txt`; it works only by transitive resolution. | Dependency hygiene. A dependency bump could break user creation silently. |
| B3 | **`pydantic==2.7.4` has no Python 3.14 wheel** and builds from source. Deployment is on 3.11. | Not a blocker. Recorded so a local Python upgrade is not mistaken for a product failure. |
| B4 | **The smoke scripts hard-code `sqlite:///./smoke_test.db`** and fail on a second run with `UNIQUE constraint failed: departments.code`. | Local tooling; superseded by the suite runner. |
| B5 | **The frontend bundle is a single 668 kB chunk** with no code splitting and no virtualised lists. | `X-17`. A performance problem, not a correctness one. Phase 7. |
| B6 | **`check:api-paths` and `check:classes` are not in CI**, although both have caught real defects (183 dead classes). | CI completeness. `QA-04`. |
| B7 | **Ten generated E2E scripts in `backend/scripts/`** (`live_e2e.py`, `e2e_lifecycle.py`, `verify_tenant_isolation.py`, …) write to the live deployment. | `live_e2e.py` creates accounts against production. It should be renamed to make that obvious and be pointed at staging. |
| B8 | **A second deploy workflow (`deploy.yml`) targets an Oracle VM over SSH** and has never run. It pushes on every commit to `main`. | `DEC-002`. One deployment path, not two. |
| B9 | **`STORAGE_BACKEND=local` is ephemeral**: offer letters and onboarding documents are lost on redeploy. | Deployment architecture. The owner decides between OCI and an explicit pilot limitation. |
| B10 | **No backup or restore script exists**, so the pilot gate's "rehearsed restore" cannot be met. | `AD-08`. Phase 1. |

---

## C. Small defects worth their own line

| # | Defect | Severity | Owner |
|---|---|---|---|
| C1 | The lockout **transition** is not audited — twelve failed logins locked the account and no `login_blocked_locked` row exists. | High | platform-security (`PS-03`) |
| C2 | A failed sign-in against an **unknown username** leaves no audit row, so credential stuffing against guessed usernames is invisible to the trail. | Medium | platform-security (`PS-03`) |
| C3 | `audit_logs` has **no source address column**, while `refresh_tokens` has `ip_hash`. | Medium | platform-security (`PS-03`) |
| C4 | The administrator account's **failure counter reads 5 of 10**, three of which are the DEC-000 verification attempts. | Operational | owner |
| C5 | `ci/secret_scan.py` holds the **published credential in plain text** as a denylist entry. | High | platform-security (`PS-07`) |
| C6 | `ci/run_backend_tests.sh` **deletes `backend/*.db` before each suite**, so concurrent runs in one checkout destroy each other's databases. | High | qa-validation (`QA-05`) |
| C7 | `*.db-journal` was not in `.gitignore`; a SQLite journal file was written into `backend/` during a session and would have been committed by an `git add -A`. | Low | fixed on the board branch |
| C8 | The Playwright `mobile` project matches `responsive.spec.ts`, **which does not exist**, so it runs nothing while the summary reads "10 passed". | Medium | qa-validation (`QA-02`) |
| C9 | The import dry-run token is held in a **process-local, unbounded dict** — lost on restart, unbounded in memory, and not bound to the result hash despite the docstring saying it is. | High | data-import (`DI-02`) |
| C10 | The frontend agent's monorepo work **reverses Gate 0 §3.3**, which deferred the monorepo migration until after the pilot. | Decision | `DEC-013` |

---

## D. Things the previous audit found that are now stale

Kept so that nobody re-litigates them. The full text is in `archive/2026-10-19/`.

| Previous finding (2026-10-19) | State on 2026-10-21 |
|---|---|
| Object-level authorisation missing on 73 reads and 7 writes | **Done.** Visibility and ownership checks are applied in 13 endpoint files, with 29 visibility and 74 security checks. The *role* half is still missing (`AD-04`). |
| The documented default credential still authenticates in production | **Done.** It answers 401 on every environment; the account was rotated and the owner changed the password. |
| Production storage is ephemeral | **Still true** (B9). |
| No schema migrations | **Done.** 6 Alembic revisions, each with a downgrade. |
| No CI gate | **Done.** The gate exists and is currently red on the secret scan (`PS-02`). |
| The five requested compliance regimes are not achievable with one engineer and a $0 budget | **Still true.** Unchanged in `FEASIBILITY.md`. |

---

*Nothing in this file records a credential, a token, a key, a personal identifier or a customer
datum.*
