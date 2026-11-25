# Frontend coverage of released backend features

**Date:** 2026-10-27 · **Audited commit:** `2853e29`, gaps closed at `FD-12` (`024b1fc`), `FD-13` (`9b52bf8`), `FD-14` (`d39e72a`), `SUP-06` (`32ead73`) and `FD-15` (`5e87961`) · **Owner:** Super Agent

## The question

The backend's surface grows with every batch. **Does the product actually expose it?** A backend
operation with no screen is a capability the customer is paying for and cannot use — and a screen
that *says* the product cannot do something the server does is worse, because it is a false
statement made in the product's own voice.

This file records the audit, the findings, and where each gap is tracked. It is not a coverage
percentage: see "Why there is no single number" below.

## Method

1. **The route inventory** is the application's own: every operation served under `/api/v1`, taken
   from `app.routes` (the same list `security_test_suite` holds to the role matrix). 311 operations
   at the audited commit.
2. **The frontend surface** is `frontend/src/**` — the screens do not use the generated client in
   `packages/api-client` at all (no import of `@karmathy/api-client` exists, and
   `frontend/package.json` does not depend on it). Every screen calls the shared axios instance in
   `frontend/src/lib/api.ts`.
3. **File-level verification** of the features released in the last three batches: for each, the
   screen that calls the operation, whether it exposes the *action* or only lists data, and the gap.

## Verified findings

| Feature | Backend operation(s) | Frontend caller | Action or list | State |
|---|---|---|---|---|
| Background-jobs monitor (`PS-10`) | `GET /admin/jobs` | `pages/Jobs.tsx:141` | List, filters, paging; the counts come from the contract's `meta` | wired — the flat page fields were corrected in `SUP-06` (`D-044`) |
| | `POST /admin/jobs/{id}/retry`, `…/discard` | `pages/Jobs.tsx:171-179` | Retry and Discard buttons, with a reason dialog for discard | wired |
| | `GET /admin/jobs/{id}` | `pages/Jobs.tsx` (`openDetail`) | The "View" modal reads the job itself, with loading/error states and the stored `result` | **fixed in `FD-12`** — the operation has a caller, and serving the result needed a backend fix (`D-039`) |
| Queued-import progress (`DI-04`) | `GET /import-export/import/{entity}/progress/{job_id}` | `lib/imports.ts` (`fetchProgress`) → `pages/Import.tsx` | Polls every 2 s, shows applied/rejected/percent/batch, stops at the end | **fixed in `FD-11`** — the screen used to say no feed was served |
| Cancel a queued import (`DI-06`) | `POST /import-export/import/{entity}/cancel` | `lib/imports.ts` (`cancelImport`) → `pages/Import.tsx` | A Cancel button that disappears once it is cancelled | **added in `FD-11`** |
| Audit trail (`PS-03`/`PS-04`) | `GET /reports/audit` | `pages/Reports.tsx:77`, `HRHome.tsx:54`, `SuperAdminHome.tsx:51` | List of the last 25 entries | wired |
| Audit-chain verification (`PS-12`) | `GET /admin/audit/verify` | `pages/Reports.tsx` (`verifyChain`) | A "Verify the chain" action in the Audit trail card; the verdict, the entry count, the time and the head to anchor; one sentence per break; an error state that claims nothing | **added in `FD-13`** — the operation had no route before `PS-12`, and no screen before this batch |
| A list that failed to load | every `/platform` list | `pages/Platform.tsx` (`safe`, `DataList`) | The card says "This list could not be read" instead of "nothing recorded yet" | **fixed in `FD-12`** — 21 lists name their source |
| Payroll inputs (`PY-03`) | `GET /payroll/payslips?pay_run_id=`, `inputs_json` on `PaySlipOut` | `pages/Platform.tsx` (`PayslipPanel`) | Run selector, the inputs the slip consumed, the rows it excluded, and every line's rule id, version and calculation | **fixed in `FD-12`** — nothing is recalculated in the browser |
| Core HR lifecycle | `PATCH`/`DELETE` on positions, locations, cost centres | `pages/People.tsx` (`ENDPOINT` map, `RowActions`) | Create, edit, archive/restore, delete | wired |
| | `GET`/`POST /core-hr/employee-documents` | `pages/People.tsx` (`openEmployee`, `addDocument`) | The detail panel lists an employee's documents and, for SuperAdmin/HR, records one | **fixed in `FD-12`** — a register that points at the customer's storage; no file upload |
| Employment history (`HR-12`) | `GET /employees/{id}/history` | `pages/People.tsx` (`openEmployee`) | The detail panel lists the effective-dated changes, oldest first, with the actor and reason | **added in `FD-15`** |
| Change employment (`HR-12`) | `PATCH /employees/{id}` | `pages/People.tsx` (`changeEmployment`) | A form for status, type, job, department, manager, salary, effective date and reason; sends only the fields that differ; the server's refusal is shown | **added in `FD-15`** |

## What `FD-12` fixed

- **The job monitor read a row, not the job.** `GET /admin/jobs/{job_id}` had no caller, and the
  modal said the payload was not stored. The operation now has a caller — and serving it exposed
  `D-039`: `serialise` had never returned the stored result, so the screen could only ever say "no
  result stored". The stored **input** is still not requested, because it can carry a confirmation
  token.
- **The payslip inputs were invisible.** The Payroll tab now shows the approved time and leave a
  payslip consumed, the draft rows it **excluded**, and the rule id, version and calculation behind
  every line. Nothing is recalculated in the browser.
- **An employee's documents had no surface.** The People panel lists them and records one.
- **A failed list no longer reads as an empty one.** This is the shape that hid `D-035`.
- **Two navigation lies.** `/platform` showed the integrations tab, so Core HR was unreachable and
  the "Platform" tab navigated to an unregistered URL and out of the product (`D-038`).
- **The directory said a page was everyone** (`D-041`). It pages now and says how much it has read.

## What `FD-13` fixed

- **The chain could not be checked from the product.** `PS-04` made the trail tamper-evident and the
  only way to run the verification was `python -m scripts.verify_audit_chain`. `PS-12` served
  `GET /admin/audit/verify`; this batch is the screen. The audit card now has a **Verify the chain**
  action that reports the verdict, the number of entries walked and the head hash to record outside
  the database.
- **Each break has its own sentence.** The server's stable reason code (`hash_mismatch`,
  `missing_predecessor`, `head_mismatch`) is turned into one plain sentence; an unknown code is
  shown, never hidden.
- **A failed check claims nothing.** A request that fails reads as "the chain could not be
  verified", not as an intact chain and not as "no entries" — the same shape as the failed-list fix
  in `FD-12`.
- **It is an action, not a page load.** The journey counts the requests the page makes before the
  button is pressed and asserts zero: a full walk on every visit is a cost the customer did not ask
  for, and a cached verdict would be a claim the screen cannot support.

## What batch 11 fixed

- **A false statement in the product.** `lib/imports.ts` exported `JOB_PROGRESS = { available:
  false }` with a comment asserting, as a checked fact, that no progress feed existed. After
  `fcdb658` that was untrue, and the import screen printed *"The backend does not serve a queued
  import's progress yet"* to the operator. The flag is gone; the screen polls the real operation.
- **The journey that asserted it.** `frontend/e2e/import-queued.spec.ts` checked for that sentence.
  It now asserts the live panel and a cancellation instead.

## Gaps left, and where they are tracked

| Gap | Why it matters | Tracked as |
|---|---|---|
| The generated client is unused | `packages/api-client` is maintained and never imported, so two generations of the API contract exist in the tree and only one is exercised | `FD-01` (partial, DEC-013 deferred the wiring) |
| A reloaded import cannot be cancelled | The confirmation token is deliberately not persisted, so cancel needs the token in memory | recorded in `FD-11`; a "my imports" list would fix it, and that is a product decision |

**Closed by `FD-12`:** the unused `GET /admin/jobs/{job_id}` (which needed a backend fix — it had
never served the stored result); `inputs_json` never shown; the employee-document register with no
caller; a failed list rendered as an empty one. Closing them found three more: the `/platform`
tab shadowing (`D-038`), the directory reading one page and calling it everyone (`D-041`), and a
contrast failure the unreachable tab had kept out of the axe run (`D-042`).

**Closed by `FD-14`:** the directory read a bare list and filtered its loaded page, so a search
could report "no match" for a person who exists and the screen could not say how many employees
there were. `GET /employees/` now answers `{items, meta}` and applies `search`, `department_id`,
`status`, `manager_id`, `sort`/`order` and `page`/`page_size`; `/people` sends the filters, prints
the server's total and pages with `page`. The seven employee pickers read every page instead of
treating one page as everyone. Closing it exposed `D-044`: `GET /admin/jobs` still answers flat
page fields where `PaginatedJobs` declares `meta`.

**Added by `FD-15`:** the employee panel now reads and writes the employment record. The
effective-dated history is shown with its dates, actor and reason; a status, type, job, department,
manager or salary change goes through `PATCH`, and the form sends only the fields that differ, so
an untouched option cannot rewrite the record. A move the lifecycle does not define is shown with
the allowed moves and changes nothing.

**Closed by `SUP-06`:** `GET /admin/jobs` answered its four page counts flat while the contract's
`PaginatedJobs` declares `items` + `meta`; `/jobs` read the flat fields, so a contract-generated
client would have seen nothing. The listing now uses the shared `PageMeta`, the suite asserts the
flat fields are absent, and the journey fails if the rendered count is `undefined`.

**Closed by `FD-13`:** the audit chain could be described but not checked — the contract and the
generated client both declared `GET /admin/audit/verify`, the server had no route, and the trail's
own documentation told an operator to anchor a head hash that no operation returned. The operation
is served (`PS-12`) and the screen reads it. Closing it exposed `D-043`: the declared
`AuditVerification` schema had no field for the head.

## Why there is no single number

A "N of 311 operations have a screen" figure would be wrong in both directions, and the first
attempt at one was. Screens build paths by concatenation (`${ENDPOINT}/${id}`), so a scan for path
literals reports an operation as unused when a screen calls it — `/departments/{department_id}` and
`/employees/{employee_id}` are both called and both appear "missing" under a literal scan. In the
other direction, an operation that appears in a comment or a link would count as covered.

So this file claims only what was verified by reading the caller. The route inventory is
reproducible:

```bash
cd backend && python - <<'PY'
import os, tempfile
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/x.db"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
from app.main import app
for route in app.routes:
    path = getattr(route, "path", "")
    if path.startswith("/api/v1"):
        for method in sorted(getattr(route, "methods", []) - {"HEAD", "OPTIONS"}):
            print(method, path)
PY
```

## The rule this audit leaves behind

**A backend operation that ships without a screen is not a user-facing feature, and a screen that
claims the server cannot do something is a defect.** `DI-04`'s operation shipped in batch 10 with the
second problem and was corrected in batch 11. The check that would catch it earlier is a
per-batch question in the release note: *which screen calls this, and does that screen still describe
the old behaviour?* — asked in `agents/super/PROMPT.md`'s release checklist from this batch on.
