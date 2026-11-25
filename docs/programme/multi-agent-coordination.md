# LibrePeople Multi-Agent Coordination Matrix

> Git-only + docs. No code changes in this commit.
> Base: `feature/librepeople-production` @ `80ed1aa`.
> Worktrees are detached at base HEAD. Feature branches are NOT created yet — agents create
> `agent/<workstream>/<task-id>` from their assigned worktree only when starting work.
> Do not push. Do not touch `main`.
>
> ## Status update (2026-11-24, HEAD `5cf0568`)
>
> - Production HEAD now `5cf0568` (merge of ESS IDOR fix + traceability reconciliation + Slice 3 integration + fix).
> - ESS IDOR fix: DONE (critical security, validated PASS, 51/51 + 2162/0 + 29/0).
> - Traceability reconciliation: DONE (122 VERIFIED -> 2 VERIFIED, 105 IMPLEMENTED, 18 BLOCKED, 8 DEFERRED, 3 IN PROGRESS).
> - `npm run verify` EXIT 0.
> - 22-domain gap register: DONE (critical/high/medium/low findings).
> - Remaining genuine gaps: helpdesk employee self-create, backup/restore honesty, workflow engine (out of v1 scope), expenses UI (deferred), payroll FY26-27 (blocked on statutory sign-off).
>
> ## Status update (2026-11-24, HEAD `9efae62`)
>
> - E-UX-03 checklist C3-C8 + H1-H5: DONE (leave/payroll/onboarding slices). Results:
>   112 slice-3 + 552 slice-2 + 20 slice-1 = 684 tests; full suite 811/811;
>   `npm run verify` EXIT 0. Commits `c369289` → `c160e58` → `9efae62`. 7 pages + test
>   + 2 docs. Validated PASS. Docs commit follows this update.
>
> ## Status update (2026-11-23, HEAD `0bf8efb`)
>
> - E-UX-02 admin slice 2: DONE (commits `2be58c7`, `7ded1c1`, `0bf8efb`, 106 files, validated 572/572 + 699/699).
> - E-UX-03 checklist C3-C8 + H1-H5: IN PROGRESS (leave/payroll/onboarding subdirs; assignee Team E qwen4-max next).
>
> ## Status update (2026-11-23, HEAD `80ed1aa`)
>
> - A-PRODUCT-01 Assets: DONE (integrated `805af50`, 97/0 18/18 validated).
> - B-PAYROLL-01 PT research: DONE (`b0f563c` primary citations, placeholders skip-only).
> - C-PLATFORM-01 proof-stop: DONE (tools absent recorded, no repeat).
> - D-SECURITY-01 tenant re-review: DONE + follow-up hardening DONE (`80ed1aa`, 85/57/169/108 green, security 2090/2 pre-existing assets gap separate).
> - E-UX-01 honest-feedback slice 1: DONE (`07321bc` + `6901f98`, 147/147 validated).
>
> ## Status update (2026-11-23, HEAD `6901f98`)
>
> - Team E UX slice 1 complete: Alert success/error on 14 pages + Leave bulk
>   allSettled with per-id failures. Validated 147/147. Commits `07321bc`, `6901f98`.
> - Slice 1 exclusive files (16, frozen — later slices must NOT touch):
>   `frontend/src/lib/bulk.ts`, `frontend/src/lib/feedback-slice1.test.ts`,
>   `frontend/src/pages/ClientOnboarding.tsx`, `Leave.tsx`, `Offboarding.tsx`,
>   `Onboarding.tsx`, `Platform.tsx`, `Recruiting.tsx`, `RosterBuilder.tsx`,
>   `Scheduling.tsx`, `TimeAttendance.tsx`, `frontend/src/pages/admin/UserAdmin.tsx`,
>   `frontend/src/pages/benefits/BenefitsHub.tsx`, `ess/ESSHub.tsx`,
>   `learning/LearningHub.tsx`, `performance/PerformanceHub.tsx`.
>
> ## Next assignments
>
> - Assets security 2 pre-existing (assets ops matrix) → Team A backlog.
> - PT values → Team B blocked-pending-reviewer.
> - Platform → Class C monitor.
> - Team E UX slice 2 (~80 admin pages) → DONE as E-UX-02 (`2be58c7`, `7ded1c1`, `0bf8efb`, 106 files, 572/572 + 699/699 validated).
> - Checklist C3-C8 + H1-H5 → DONE as E-UX-03 (`c369289`, `c160e58`, `9efae62`; 684 slice tests, 811/811 full, verify EXIT 0, validated PASS).

## Environment probe (2026-11-23, librepeople-prod worktree)

- `command -v docker` → absent (exit 1)
- `command -v psql` → absent (exit 1)
- `command -v pg_isready` → absent (exit 1)
- Conclusion: C-PLATFORM-01 PG disposable proof MUST NOT run; record absent + stop.

## Dirty-state guard (do not touch)

`git status --porcelain` in `librepeople-prod` at matrix creation showed pre-existing dirt —
agents must NOT touch, restamp, or "fix" these:

- `M backend/app/api/v1/endpoints/forecasting.py`
- `M backend/app/services/forecasting.py`
- `M backend/forecasting_tenant_isolation_test_suite.py`
- `M docs/product/acceptance-evidence/LP-DOC-003.json`
- `M docs/product/acceptance-evidence/LP-NFR-009.json`
- `M docs/product/acceptance-evidence/LP-NFR-010.json`
- `M docs/product/acceptance-evidence/LP-NFR-011.json`
- `M docs/product/acceptance-evidence/LP-NFR-012.json`
- `M docs/product/acceptance-evidence/LP-NFR-013.json`
- `M docs/product/acceptance-evidence/summary.md`
- Untracked: `.venv311/`, `.vite/`, `docs/product/acceptance-status.md`,
  `docs/product/acceptance-suite.md`, `docs/product/phase-gates.md`,
  `docs/product/ui-gap-analysis.md`, `docs/product/ui-payment-mappings.csv`,
  `docs/product/workflow.md`, `spec/features/acceptance-harness-p1/`,
  `spec/features/p3-db-validation/`

## Task matrix

| Task ID | Model | Workstream | Scope | Exclusive files | Dependencies | Acceptance | Tests | Status | Branch/worktree | Commit | Review |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A-PRODUCT-01 | opencode-go/qwen4-max | Product / Assets | New Assets domain only: new SQLAlchemy models + new `/assets*` endpoints + one new Alembic migration. No changes to payroll, forecasting, auth, or existing endpoints. | `backend/app/models/asset*.py`, `backend/app/api/v1/endpoints/assets*.py`, `backend/app/schemas/asset*.py`, `backend/alembic/versions/*_asset*.py`, `backend/tests/test_assets_*.py`, `docs/product/assets-*.md` (exclusive; no other task may write these paths) | Base `feature/librepeople-production @ c64edc5`; independent of B/C/D | 1) Migration applies cleanly forward + downgrades. 2) CRUD endpoints return tenant-scoped data with 401 without token, 403/404 cross-tenant. 3) OpenAPI lists `/assets*`. 4) No modified files outside exclusive list. | `pytest backend/tests/test_assets_tenant_isolation.py backend/tests/test_assets_crud.py -q`; `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`; `pytest backend/tests/test_no_cross_task_file_overlap.py -q` (asserts exclusive paths) | DONE (integrated 805af50, 97/0 18/18 validated) | Worktree: `/Users/srinivas/LLM/Workforce/lp-team-a-product` (detached @ c64edc5). Branch: TBD `agent/product/A-PRODUCT-01-assets` (create on start) | — | Pending validator |
| B-PAYROLL-01 | opencode-go/muse-spark-1.3-contributor | Payroll research | PT February-cap + TN half-yearly research ONLY. Docs + TEST-ONLY skipped placeholders. No payroll values, rates, caps, or formula changes. No model/migration/endpoint changes. | `docs/research/payroll/PT-feb-cap-TN-half-yearly-*.md`, `backend/tests/test_payroll_pt_tn_placeholders.py` (skipped stubs only), `docs/programme/payroll/B-PAYROLL-01-notes.md` (exclusive; no other task may write these paths) | Base `feature/librepeople-production @ c64edc5`; independent of A/C/D | 1) Research docs cite sources + open questions, zero numeric payroll constants added. 2) Placeholder test file contains only `@pytest.mark.skip` stubs, 0 production asserts changed. 3) `git diff --stat` shows no `backend/app/**` production files. 4) No overlap with A/C/D exclusive paths. | `pytest backend/tests/test_payroll_pt_tn_placeholders.py -q -rs` (expect all skipped); `grep -rE '[0-9]{3,}' docs/research/payroll/PT-feb-cap-TN-half-yearly-*.md` reviewed for accidental values (docs explain any numbers are source quotes, not code constants); `git status --porcelain backend/app/` must be clean | DONE (b0f563c primary citations, placeholders skip-only) | Worktree: `/Users/srinivas/LLM/Workforce/lp-team-b-payroll` (detached @ c64edc5). Branch: TBD `agent/payroll/B-PAYROLL-01-pt-tn-research` (create on start) | — | Pending validator |
| C-PLATFORM-01 | opencode-go/deepseek-v4.1-flash | Platform / PG disposable proof | Retry disposable-Postgres proof ONLY if `docker` + `psql`/`pg_isready` are now present. Current probe: all absent → record + STOP, no further action. If present later: ephemeral container only, no repo DB touched, proof log under exclusive docs path. | `docs/programme/platform/C-PLATFORM-01-pg-disposable-proof.md`, `docs/programme/platform/C-PLATFORM-01-probe.log`, `scripts/ops/pg-disposable-proof*.sh` (exclusive; no other task may write these paths) | Base `feature/librepeople-production @ c64edc5`; gate: `command -v docker && command -v psql` must both succeed or STOP. Independent of A/B/D. | 1) Probe log records `command -v` outputs. 2) If absent: doc states ABSENT + STOP with zero containers started. 3) If present: disposable PG boots, smoke migration + rollback succeed, container removed, repo DB untouched. 4) No files outside exclusive list. | If absent: `cat docs/programme/platform/C-PLATFORM-01-probe.log` shows absent + `docker ps` not executed. If present: `bash scripts/ops/pg-disposable-proof.sh` exits 0 + proof doc attached; `git status --porcelain` shows only exclusive paths | DONE (tools absent recorded, no repeat) | Worktree: `/Users/srinivas/LLM/Workforce/lp-team-c-platform` (detached @ c64edc5). Branch: TBD `agent/platform/C-PLATFORM-01-pg-proof` (create on start, only if gate passes) | — | Pending validator |
| D-SECURITY-01 | opencode-go/qwen4-max | Security / tenant-isolation re-review | READ-ONLY re-review of tenant isolation across forecasting + registry + legal + expenses + notifications. Produce findings doc. Zero code, migration, or evidence re-stamp changes. Must not touch forecasting dirt listed above. | `docs/programme/security/D-SECURITY-01-tenant-isolation-rereview.md` (exclusive; sole writable path for this task; no other task may write it) | Base `feature/librepeople-production @ c64edc5`; read-only on A/B/C outputs. Independent (no blocking dependency). | 1) Findings doc covers all 5 surfaces (forecasting, registry, legal, expenses, notifications) with file:line refs. 2) Verdict per surface: PASS / GAP + severity. 3) Zero production file modifications (`git diff --stat backend/ docs/product/acceptance-evidence/` empty). 4) Explicitly lists forecasting-dirt files as untouched. | `git status --porcelain backend/ docs/product/` shows no modifications after review; `pytest backend/forecasting_tenant_isolation_test_suite.py -q --collect-only` (read-only collection check, no writes); markdown link/file-ref check on findings doc | DONE + follow-up hardening DONE (80ed1aa, 85/57/169/108 green, security 2090/2 pre-existing assets gap separate) | Worktree: `/Users/srinivas/LLM/Workforce/lp-team-d-security` (detached @ c64edc5). Branch: TBD `agent/security/D-SECURITY-01-tenant-rereview` (create on start; docs-only commit) | — | Pending validator |
| E-UX-01 | Team E | UX / honest-feedback slice 1 | Alert success/error feedback on 14 pages + Leave bulk allSettled with per-id failures. | `frontend/src/lib/bulk.ts`, `frontend/src/lib/feedback-slice1.test.ts`, `frontend/src/pages/ClientOnboarding.tsx`, `Leave.tsx`, `Offboarding.tsx`, `Onboarding.tsx`, `Platform.tsx`, `Recruiting.tsx`, `RosterBuilder.tsx`, `Scheduling.tsx`, `TimeAttendance.tsx`, `frontend/src/pages/admin/UserAdmin.tsx`, `frontend/src/pages/benefits/BenefitsHub.tsx`, `ess/ESSHub.tsx`, `learning/LearningHub.tsx`, `performance/PerformanceHub.tsx` (frozen; no later task may write these paths) | Base `feature/librepeople-production @ 6901f98`; independent of A/B/C/D | 1) Success + error Alerts render on all 14 pages. 2) Leave bulk uses allSettled with per-id failure reporting. 3) 147/147 validated. | Slice-1 suite 147/147 green | DONE (07321bc + 6901f98, 147/147 validated) | Branch: `feature/librepeople-production` | `07321bc`, `6901f98` | Pending validator |
| E-UX-02 | Team E | UX / honest-feedback slice 2 (~80 admin pages) | Extend honest-feedback pattern to admin-console pages. Must NOT touch any of the 16 E-UX-01 frozen files. | `frontend/src/pages/admin/*.tsx` EXCEPT `UserAdmin.tsx`, `frontend/src/lib/bulk-admin.ts` (new), `frontend/src/lib/feedback-slice2.test.ts` (new), `docs/programme/ux/E-UX-02-*.md` (exclusive; no other task may write these paths) | Base `feature/librepeople-production @ 6901f98`; follows E-UX-01 pattern, no file overlap | 1) Success/error feedback on each covered admin page. 2) New slice-2 tests green. 3) `git diff --stat` shows zero of the 16 E-UX-01 frozen files. | Slice-2 test file green; `git diff --name-only` intersected with frozen list is empty | DONE (2be58c7 + 7ded1c1 + 0bf8efb, 106 files, 572/572 + 699/699 validated) | Branch: `feature/librepeople-production` | `2be58c7`, `7ded1c1`, `0bf8efb` | Pending validator |
| E-UX-03 | Team E | UX / checklist C3-C8 + H1-H5 | C3-C8 + H1-H5 checklist items on non-admin surfaces. Must NOT touch E-UX-01 frozen files or E-UX-02 admin exclusives. | `frontend/src/pages/leave/*.tsx`, `frontend/src/pages/payroll/*.tsx`, `frontend/src/pages/onboarding/*.tsx`, `frontend/src/lib/feedback-slice3.test.ts` (new), `docs/programme/ux/E-UX-03-*.md` (exclusive; no other task may write these paths) | Base `feature/librepeople-production @ 6901f98`; follows E-UX-01 pattern; disjoint from E-UX-01 + E-UX-02 | 1) Each C3-C8 + H1-H5 item addressed with file:line refs in E-UX-03 doc. 2) Slice-3 tests green. 3) No overlap with E-UX-01/E-UX-02 exclusive paths. | Slice-3 test file green; overlap check vs E-UX-01/E-UX-02 sets empty | DONE (c369289 → c160e58 → 9efae62; 112 slice3 + 552 slice2 + 20 slice1 = 684, full 811/811, `npm run verify` EXIT 0, 7 pages + test + 2 docs, validated PASS) | Branch: `integrate-slice3-ux` @ `9efae62` (product line `feature/librepeople-production` @ `d8f7a3d`) | `c369289`, `c160e58`, `9efae62` | Pending validator |

## Non-overlap guarantee

Exclusive file sets above are disjoint by construction:

- `asset*` / `assets*` (A) ∩ payroll research paths (B) = ∅
- Platform `platform/C-PLATFORM-01*` + `scripts/ops/pg-disposable-*` (C) ∩ all others = ∅
- Security single-file `security/D-SECURITY-01-*` (D) ∩ all others = ∅
- D is read-only outside its one doc; B writes docs + skipped test stubs only.
- E-UX-01 frozen set (16 files: `lib/bulk.ts`, `lib/feedback-slice1.test.ts`, 10 top-level
  pages incl. `Leave.tsx`/`Platform.tsx`, `admin/UserAdmin.tsx`, benefits/ess/learning/
  performance hubs) ∩ E-UX-02 (`admin/*.tsx` except `UserAdmin.tsx` + `bulk-admin.ts` +
  `feedback-slice2.test.ts` + `programme/ux/E-UX-02-*`) = ∅
- E-UX-01 ∩ E-UX-03 (`pages/leave/*`, `pages/payroll/*`, `pages/onboarding/*` +
  `feedback-slice3.test.ts` + `programme/ux/E-UX-03-*`) = ∅; E-UX-02 ∩ E-UX-03 = ∅
  (admin/ vs leave+payroll+onboarding/ subdirs; distinct test + doc paths).

Any agent needing a path outside its exclusive list must STOP and escalate for matrix amendment.

## Status update (2026-11-25, HEAD `2890448`)

- Production HEAD now `2890448`.
- E-UX-01/02/03: DONE (811/811 frontend, `npm run verify` EXIT 0).
- ESS IDOR fix: DONE (validated PASS, 51/51 + 2162/0 + 29/0).
- Helpdesk self-create: DONE (validated PASS, 30/0 + 2162/0; access widened to WORKFORCE_ROLES with self-scoping).
- Traceability reconciliation: DONE (2 VERIFIED, 105 IMPLEMENTED, 18 BLOCKED, 8 DEFERRED, 3 IN PROGRESS).
- 22-domain gap register: DONE (`docs/programme/phase2-domain-gap-register.md`).
- Release notes + known limitations: DONE (`docs/release/release-notes-and-known-limitations.md`, 1795 words).
- Independent validation package: DONE (`docs/validation/*`, 18 files).
- `npm run verify`: EXIT 0 (typecheck, 247 routes, api-paths, design 0 violations, build 3.10s, classes, tokens).
- Remaining external blockers: payroll FY26-27 statutory sign-off, PostgreSQL/Oracle live proof (toolchain absent), performance measurement (PROPOSED), licensing clearance, NFR-012/013/DOC-003 owner decisions, gratuity OFF.
## Start-up protocol (each agent)

1. `git -C <worktree> rev-parse HEAD` must equal matrix base (`c64edc5`) before branching.
2. Create branch `agent/<workstream>/<TASK-ID>-*` from base with `git -C <worktree> checkout -b <branch>`.
3. Work only inside exclusive files. Never `git reset`, never `checkout .`, never re-stamp evidence.
4. Commit only exclusive paths. Do not push. Report branch + commit + `git status --porcelain`.
