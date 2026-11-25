# The journey suite — the pilot gate's evidence

**Request:** `QA-01` · **Lane:** qa-validation · **Date:** 2026-10-22 · **Updated:** 2026-10-27
**Branch:** merged to `main` (`5e87961`; batch 18 code in `main` after this record)
**Staging:** `KARMA_STAGE`, an empty Oracle schema in the same Autonomous Database
instance as production, with no customer data.

---

## 1. The result

| | |
|---|---|
| **Journeys locally, against the SQLite file** | **70 browser tests passed, 0 failed** — `cd frontend && npx playwright test` (54 desktop tests, including 22 accessibility and contrast checks, 4 audit-chain journeys, the directory's server-filter journey and the employment journey, plus 16 responsive checks) |
| **Journeys on staging, against real Oracle** | **69 passed, 1 skipped, 0 failed — twice in a row** — `bash scripts/staging/gate.sh` at `5e87961`. One test is skipped by design |
| **Backend suites** (counted separately, per DEC-012) | **33 suites, 4 172 checks, 0 failed** — `bash ci/run_backend_tests.sh` |
| **Secret scan** | clean — `ci/secret_scan.py` |
| **Merged OpenAPI** | up to date — `scripts/merge_openapi.py --check` |
| **Frontend verify** | green — `npm run verify` (typecheck, route check, API-path check, build, class check) |

**The gate is not met.** Eleven of the twelve journeys the pilot gate names exist and
pass. The twelfth — the payroll refusal — is still missing: the product now refuses
correctly (`PR-01` is merged), but **no Playwright journey exercises it yet**; §5 says
exactly what is left.

The counts are two different things and are not summed (DEC-012): **4 172** is the
backend checks, **11** is the journeys.

### The twelve the gate names, and the eleven that exist

| # | Journey | File | Status |
|---|---|---|---|
| 1 | The signed-in pages keep their text legible in dark mode | `frontend/e2e/contrast.spec.ts` | passes |
| 2 | The public pages keep their text legible in dark mode | `frontend/e2e/contrast.spec.ts` | passes |
| 3 | A first sign-in must replace the administrator-set password | `frontend/e2e/first-login.spec.ts` | passes |
| 4 | A protected route cannot be reached before the password is replaced | `frontend/e2e/first-login.spec.ts` | passes |
| 5 | Every workspace rail entry opens the screen it names | `frontend/e2e/navigation.spec.ts` | passes |
| 6 | People opens the employee directory and lists employees | `frontend/e2e/navigation.spec.ts` | passes |
| 7 | People sub-pages open their own tab | `frontend/e2e/navigation.spec.ts` | passes |
| 8 | The admin section links to import, jobs and MFA | `frontend/e2e/navigation.spec.ts` | passes |
| 9 | The command palette navigates to People, not the platform page | `frontend/e2e/navigation.spec.ts` | passes |
| 10 | No navigation entry lands on the marketing homepage | `frontend/e2e/navigation.spec.ts` | passes |
| 11 | **A previewed import commits exactly what it previewed, and re-importing it changes nothing** | `frontend/e2e/import.spec.ts` | **passes — new in this request** |
| 12 | **A pay run for a jurisdiction with no verified rule pack is refused, and nothing is written** | — | **does not exist — the refusal is merged (`PR-01`); the journey is not written** |
| 13 | **A large import is queued, the screen follows its progress, and the operator can cancel it** | `frontend/e2e/import-queued.spec.ts` | **passes** — the panel reads `0 of N rows applied` while the worker is off (it never invents progress), and Cancel is offered, works, and disappears |

---

## 2. The import journey, in full

**File:** `frontend/e2e/import.spec.ts` · **Feature IDs:** `IM-06`, `IM-07`, `UX-08`

**Setup.** A synthetic CSV with one department row, a code unique to the run
(`QA1-XXXXXXXX`), a fixed name and a fixed description. No real person, no real
company, no real figure. The journey signs in as the seeded SuperAdmin through the
login screen, exactly as a person would.

**Assertions, in order.** Each one is against the database or against the screen —
never against the import's own response:

| # | Assertion | Evidence it is read from |
|---|---|---|
| 1 | The API base URL is not a production host | the guard, `frontend/e2e/support/environment.ts` |
| 2 | Every API call the browser made went to a non-production host | the browser's own request log |
| 3 | The fixture is not in the table before the import | `GET /departments/` |
| 4 | The preview says: 1 created, 0 rejected, 0 unchanged | the dry-run panel the operator looked at |
| 5 | The dry run wrote **nothing** — the row count is unchanged and the row is absent | `GET /departments/` |
| 6 | After the commit, the department is in the table **exactly once**, with the name and description the file carried | `GET /departments/` |
| 7 | The number of rows the table gained **equals the number the preview promised** | `GET /departments/`, before and after |
| 8 | The audit trail carries **one** `import_commit` row for `departments`, and its `created=` figure **equals the change in the table** | `GET /reports/audit` |
| 9 | The People → Departments screen shows the row | the screen |
| 10 | The second preview says: 0 created, 1 unchanged | the dry-run panel |
| 11 | The second commit leaves the row count unchanged and does not duplicate the row | `GET /departments/` |
| 12 | The second commit's audit row says `created=0` | `GET /reports/audit` |

**Expected state changes.** One new row in `departments`; one `import_dry_run` and one
`import_commit` row in `audit_logs` per import; one row in `import_dry_runs` per
dry run. Nothing else moves. The second import changes no data row at all.

**Why it is written this way.** The defect it guards against is `DI-01`: the commit
path used to report `created=N`, write an audit row saying `created=N`, and write
**nothing**. A test that believed the response would have passed the whole time. So
the numbers in the import's response are only ever used as the *preview* — the claim —
and the *table* is the evidence. The audit row is held against the change in the
table, which is what makes an audit trail that records a fiction detectable.

**It runs in both places from one set of specs.** The Playwright configuration is the
only thing that differs: the local one starts a throwaway SQLite backend and a
preview build, the staging one reuses what `scripts/staging/run.sh` has running.

---

## 3. The guard: a staging run cannot point at production

**Where:** `frontend/e2e/support/environment.ts` (the rule) and
`frontend/e2e/support/global-setup.ts` (where it is run).

- The **global setup** runs before the first journey. It refuses the run when the API
  base URL, the top-level base URL, or any project's base URL is a production host.
  A run pointed at production stops before anything signs in.
- The **import journey** calls the same rule again, and asserts that every API call
  the browser actually made went to a non-production host. So the property holds for
  the traffic, not only for the configuration.
- `scripts/staging/run.sh` refuses to start when the schema it is about to migrate is
  a production schema name, and when the address it will serve on is a production
  host.

**Why `*.onrender.com` is production.** The deployment is a Render service:
`karmathy-backend.onrender.com` is the API and `karmathy-frontend.onrender.com` is
the static site (`docs/DEPLOYMENT.md`). Staging is local, on `127.0.0.1`, against a
scratch schema. A hosted staging service — a paid decision nobody has approved
(ESC-004) — would have to be listed in `PRODUCTION_HOSTS` as an explicit exception
before the guard would allow it.

**The guard is asserted, not assumed.** It is a check with a demonstrated failure, not
a claim: see §6.

---

## 4. The J1–J14 coverage

### 4.1 A note on the matrix itself, and an open question

**The mandate is not in this repository.** `docs/validation/FEATURE_MATRIX.md` names
`KARMATHY_MULTI_AGENT_BUILD_BRIEF.md` as its source of truth; that file is not
committed here, and neither is §11. So the **J-numbers below are this repository's
reconstruction**, built from the pilot scope the repository does state
(`docs/audit/AUDIT_REPORT.md` §9 "In scope", the pilot criteria in
`docs/coordination/GATE_0_DECISIONS.md` §6, and the journeys the gate counts in
`agents/ESCALATIONS.md` ESC-009).

**Open question for the Release Manager (owner: the human, with the Super Agent):**
confirm the fourteen rows and their labels against the mandate's §11. If a row is
mis-titled, the *coverage* below is still correct — it is a property of the product,
not of the label — but the mapping's labels need correcting. **This is a request, not
a blocker for the journeys themselves.**

### 4.2 The fourteen

| J | Journey | In-scope capability | Coverage | Evidence |
|---|---|---|---|---|
| **J1** | A first sign-in must replace the administrator-set password, and no protected route is reachable until it is | `P-02`, `UX-01` | **journey** | `frontend/e2e/first-login.spec.ts` — 2 journeys |
| **J2** | Every workspace rail and sidebar entry opens the screen it names, and none lands on the catch-all homepage | `UX-01`, `UX-03` | **journey** | `frontend/e2e/navigation.spec.ts` — 6 journeys |
| **J3** | The screens are legible in both themes (WCAG 2.2 AA, 1.4.3) | `UX-08`, `UX-09` | **journey** | `frontend/e2e/contrast.spec.ts` — 2 journeys |
| **J4** | A CSV import previews, commits exactly what it previewed, and re-importing it changes nothing | `IM-06`, `IM-07` | **journey** | `frontend/e2e/import.spec.ts` — 1 journey (**new**) |
| **J5** | A pay run for a jurisdiction with no verified rule pack is refused with `rule_pack_not_verified`, nothing is written, and the message names what is missing and who must verify it | `PY-08`, `PY-10` | **NOT COVERED** | The refusal is merged (`PR-01`: 422, nothing written) and the contract is settled (§5.1). No Playwright journey exercises it yet — **Gap G1**. |
| **J6** | A role that is not permitted is refused everywhere, with the shared error envelope | `AD-04`, `A-04` | **another kind of test** | `backend/security_test_suite.py` — a role matrix over **every served operation**, with a negative test per role per operation, and the permitted role proved to succeed, not merely to get past the gate |
| **J7** | Every mutation writes an audit row in the same transaction, and the trail is not public | `AD-07` | **another kind of test** | `security_test_suite.py` (the audit log is not public), `visibility_test_suite.py` (Associate and Manager refused, HR allowed) |
| **J8** | A hire is atomic: the employee, the onboarding checklist and the audit row are written together, or nothing is | `HR-01` | **another kind of test** | `backend/hire_test_suite.py` — 26 checks, including "the failed hire created no employee", "the failed hire wrote no audit row", and the idempotent retry |
| **J9** | The employee directory shows only the employees the caller may see | `HR-03`, `A-02` | **another kind of test** | `backend/visibility_test_suite.py` — 29 checks (Associate sees only themselves, a Manager their reporting line, HR everyone). The journey asserts the directory *renders*; it does not prove the scoping, and does not claim to |
| **J10** | A leave request is raised, approved, and the balance moves | `LV-01`, `LV-02`, `LV-03` | **another kind of test** | `backend/smoke_test_phases_3_7.py` — leave types, entitlements, request, approval, and the balance moving |
| **J11** | Time capture becomes a timesheet and then a payroll input | `TM-01`, `TM-03` | **another kind of test** | `backend/smoke_test_phases_3_7.py` — clock-in, duplicate refusal, clock-out, hours, timesheet generate/submit/approve |
| **J12** | A background job is queued, leased, retried, and dead-lettered | `J-04`…`J-07` | **another kind of test** | `backend/jobs_test_suite.py` — 24 checks: claim, lease, heartbeat, retry with backoff, dead-letter, idempotent re-enqueue. `backend/job_worker_test_suite.py` — 44 checks: a queued import is **applied once and not twice**, a permanent refusal and a **cancellation** (`JobCancelled`) are dead on attempt 1, a transient failure is retried and succeeds on the second attempt, the heartbeat holds the lease through a slow handler, `stop()` waits for the job in flight, and an expired lease is released and re-run. The screen follows the job and stops it: `frontend/e2e/import-queued.spec.ts` |
| **J13** | The onboarding setup is resumable and the readiness check names the gaps | `CF-01`, `CF-09`, `CF-11` | **another kind of test** (the portal and the preset engine); **no journey, and no screen to drive** | `backend/smoke_test_client_onboarding.py` — 20 checks; `backend/onboarding_test_suite.py` — 163 checks (six presets, the dependency graph, provenance, the readiness check changing nothing). **Gap G5**: the presets and readiness API has no frontend route, and `write_state()` is called only from the test suite — the journey needs a screen first |
| **J14** | The critical journeys work at 360, 768, 1024 and 1440 px, keyboard-operable, and axe clean | `UX-08`, `UX-09` | **journey** | `frontend/e2e/responsive.spec.ts` — 16 tests, four per width: the sign-in screen fits, the shell shows the navigation that belongs to the width, no page scrolls sideways, and the skip link moves focus. `frontend/e2e/accessibility.spec.ts` — 22 accessibility checks over the pages, including its negative test (`QA-04`). **G2 and G3 closed**; a manual keyboard and screen-reader pass is still a human task and is not claimed |

**Summary.** Five rows are covered by a journey (J1–J4 and J14 — the desktop journeys,
the accessibility and contrast checks, the audit-chain journeys and the responsive suite), and all
of them now run **against real Oracle on staging as well as against the local SQLite file**
(`SUP-05`, re-run twice at batch 18: 69 passed / 1 skipped each time). Eight rows are covered by a
different kind of test (J6–J13), and one journey (13) exercises the queue from
the screen — queued, followed, cancelled. **One row is not covered at all: J5** — the
payroll refusal, gap `G1`.

### 4.3 The mapping is not the gate

The pilot gate says *"all 12 E2E journeys pass on staging"*. Eleven do. A mapping
that claims the other eight rows are covered by backend suites does **not** make the
gate green, and this report does not claim it does. Two further facts make the gap
bigger than the table shows:

1. **The backend suites have never run against Oracle.** Each suite now builds its
   SQLite database under its own `tempfile.mkdtemp()` directory (QA-05), so concurrent
   runs no longer collide — but the 4 172 checks still run against a file, not against
   the Oracle engine production uses. The staging environment runs the *application*
   against Oracle; the checks do not. So J6–J13 are covered — but not "on staging",
   which is what the gate asks for. **Gap G4.**
2. **The payroll refusal is a gate criterion in its own right.** The audit's pilot
   gate lists it separately: *"The payroll refusal demonstrated on staging: a pay run
   for a jurisdiction with no verified pack returns `rule_pack_not_verified` and
   writes nothing."* The refusal itself is now merged (`PR-01`: 422,
   `rule_pack_not_verified`, nothing written). What is missing is the **journey** that
   demonstrates it; until that journey exists the criterion is not evidenced and
   `D-014` stays open.

---

## 5. The gaps, named, owned and dated

| Gap | What is missing | Owner | Request | Date |
|---|---|---|---|---|
| **G1** | The payroll-refusal **journey**. The refusal itself is merged (`PR-01`) and returns 422 `rule_pack_not_verified`, writing nothing | **qa-validation** | `QA-01` follow-up — needs a request file | **proposed 2026-11-05** — to be confirmed by the Super Agent; the date is a proposal, not a commitment made on another lane's behalf |
| ~~**G2**~~ | ~~The responsive journey: the `mobile` project matches a spec file that does not exist, so it runs nothing while the summary reads "passed"~~ | **qa-validation** | `QA-02` | **closed 2026-10-26** — 16 tests at 360/768/1024/1440 px; five defects found and fixed (`docs/validation/RESPONSIVE.md`) |
| ~~**G3**~~ | ~~axe-core in CI, and the two frontend checks that are not in the gate~~ | **qa-validation** | `QA-04` | **closed 2026-10-26** — 21 axe tests over 20 pages; both checks in the frontend job |
| **G4** | The backend suites run against SQLite only; they have never run against the Oracle engine production uses | **qa-validation**, with the Release Manager for the environment | *no request yet — needs opening* | **proposed 2026-11-12** |
| **G5** | No journey for the onboarding setup — the customer's first hour. **Blocked on a screen**: no frontend route consumes `/onboarding/presets` or `/onboarding/readiness`, and `write_state()` is called only from the test suite | **onboarding-config** (the screen), then qa-validation (the journey) | *no request yet — needs opening; `QA-02` recorded the blocker* | **proposed 2026-11-12** |

`G4` needs a decision about what "the suites on staging" would even mean (a scratch
schema per suite, and the teardown); the rest are this lane's own work.

### 5.1 The contract disagreement — resolved

The refusal's status code was published twice, with two different codes and two
different `details` shapes. It is now settled: **one entry** in `contracts/errors.md`
§3.1 (validation, **422**), `details` `{jurisdiction, pay_date, pack_status, required:
[string]}`, which is what `contracts/openapi/payroll.yaml` publishes and what
`backend/app/api/v1/endpoints/payroll.py` raises. The 409 duplicate is gone. The
journey can therefore assert 422 and the merged `details` shape.

---

## 6. Every new check, seen to fail

A check that has never failed has never been tested. Each of these was broken on
purpose, in this worktree, and the failure was observed. **No product code was
changed in the tree that was committed** — the breaks were made, observed, and
reverted, and `git diff backend/` is empty.

| Check | How it was broken | What happened |
|---|---|---|
| The import journey catches a commit that reports success and writes nothing | In `backend/app/imports/runner.py`, the apply loop was replaced by the pre-`DI-01` behaviour: the rows are not written, but the counts are reported as if they were and the audit row records the fiction | **FAILED** — "the committed department is not in the table exactly once" (expected 1, received 0) |
| The audit assertion is live | The audit details were changed to report one more row than was created | **FAILED** — "the audit row does not carry the number of rows that were created" (expected `created=1`, received `created=2 updated=0 unchanged=0 rejected=0`) |
| The idempotency assertion is live | The upsert's existing-row lookup was made to return nothing, so the same file imported twice creates a second row | **FAILED** — "re-importing the same file changed the number of rows in the table" (expected 2, received 1) |
| The production guard refuses the run | `KARMA_API_URL=https://karmathy-backend.onrender.com/api/v1 npx playwright test` | **FAILED** — the run stopped in the global setup, before the first journey: *"refusing to run: the API base URL … is a production host"*. Exit code 1 |
| The staging script refuses a production schema | `STAGING_SCHEMA=ADMIN bash scripts/staging/run.sh` | **FAILED** — "refusing to run: 'ADMIN' is a production schema, not a scratch one". Exit code 2 |

---

## 7. The one command

```bash
bash scripts/staging/gate.sh
```

It brings the staging environment up, runs the journeys against it, and reports the
result with the commit. The release procedure is that one line.

---

## 8. What this report does not claim

- It does not claim the pilot gate is met. Eleven of the twelve journeys exist and
  pass; the twelfth does not exist.
- It does not claim the backend suites pass "on staging". They have never run
  against Oracle (§4.3, gap G4).
- It does not claim a row of the J1–J14 matrix is `VERIFIED` in the sense of DEC-012
  beyond what the named file proves at the named commit.
- It does not mark any compliance row satisfied. No statutory value is asserted
  anywhere in this work, and none was written into a test, a pack or a document.
