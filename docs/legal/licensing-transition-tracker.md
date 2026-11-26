# Licensing Transition Tracker (consolidation, Tier 2 docs-only)

> Status: **PREPARED-ONLY / report-only**. This tracker consolidates evidence
> from slices 1–3 and records what is still missing. It makes no licence
> effective, publishes no root licence file, and authorises no push, merge,
> release, or enforcement switch. Nothing here is legal advice.
> Prospective holder label: **LibrePeople project** (label only, not a rights
> claim). Karmathy marks are preserved verbatim, not scrubbed — transfer is
> UNRESOLVED (see U1).

## 1. Slices 1–3 — done + evidence

| Slice | Spec | Deliverables | Evidence (this branch / worktree) |
|---|---|---|---|
| 1 — provenance baseline | `spec/features/licensing-provenance-baseline/` | `docs/legal/ownership-and-provenance-register.md` (20 rows, five labels, Karmathy rows UNRESOLVED); `docs/legal/licensing-policy.md` (AGPL-3.0-or-later PROPOSED, CC BY 4.0 PROPOSED docs-only); `docs/legal/third-party-licences.md`; `docs/legal/LICENSE.AGPL-3.0.prepared` (text NOT yet fetched); `docs/legal/decision-register.md` (D1–D10); `docs/legal/legal-clearance-register.md` (L1–L7); `docs/legal/unresolved-blocker-register.md` (U1–U5); `docs/legal/governance-note.md` (visibility unchanged, report-only) | Committed as `a9efb34 docs(legal): prepared-only licensing provenance baseline (Tier 1)` on `chore/licensing-transition`; `git diff --name-only main...HEAD` lists exactly these 8 files (see §7 verbatim outputs); no root `LICENSE`/`COPYING`/`NOTICE` (see §7 `ROOTLIC`: all absent) |
| 2 — inventory + SBOM | `spec/features/licensing-inventory-sbom/` | `docs/legal/dependency-licence-inventory.json` (713 rows: 62 direct / 651 transitive) + `docs/legal/dependency-licence-inventory.md` (rendered view); `docs/legal/sbom-20261126T012556Z.json`; append-only U6 + L8–L11 (fpdf2 LGPL, Oracle UPL, MPL-2.0 test-only, ISC lucide-react, all UNVERIFIED) | Present as **uncommitted** (stacked) files: `git status --porcelain -- docs/legal spec/features` shows `?? docs/legal/dependency-licence-inventory.json`, `?? docs/legal/dependency-licence-inventory.md`, `?? docs/legal/sbom-20261126T012556Z.json`, `?? spec/features/licensing-inventory-sbom/`, plus `M docs/legal/legal-clearance-register.md` and `M docs/legal/unresolved-blocker-register.md` (the append-only U/L edits, uncommitted). Backend licences all UNVERIFIED — zero rows marked compliant |
| 3 — compliance CI | `spec/features/licensing-compliance-ci/` | `ci/check_licences.py` (report-only, always exits 0); `.github/workflows/licence-compliance.yml` (report-only, `continue-on-error`); `docs/legal/compliance-ci.md` (Confirmed / Review required / Blocked / Unknown + triage + human push gate) | Present as **uncommitted** (stacked) files: `git status --porcelain` shows `?? .github/workflows/licence-compliance.yml`, `?? ci/check_licences.py`, `?? docs/legal/compliance-ci.md`, `?? spec/features/licensing-compliance-ci/`. No existing CI job removed/renamed. Report-only: findings never block merges |
| This slice (tracker consolidation, Tier 2 docs-only) | `spec/features/licensing-tracker-consolidation/contract.md` | This file only: `docs/legal/licensing-transition-tracker.md` | Created uncommitted; no commits made by this slice (see §7 `LOG-3`); no production code touched (see §7 `DIFFSTAT-PROD`: empty) |

## 2. Slice 4+ — missing

| Item | Status | Evidence |
|---|---|---|
| `CONTRIBUTING.md` | MISSING — belongs to slice 4+, not this slice | `test -e`: ABSENT (see §7 slice-4 absence check) |
| `CODE_OF_CONDUCT.md` | MISSING — belongs to slice 4+, not this slice | `test -e`: ABSENT |
| `SECURITY.md` | MISSING — belongs to slice 4+, not this slice | `test -e`: ABSENT |
| `.github/ISSUE_TEMPLATE/` ×3 (bug_report, feature_request, legal-review) | MISSING — belongs to slice 4+, not this slice | `test -e`: all three ABSENT |
| `.github/pull_request_template.md` | MISSING — belongs to slice 4+, not this slice | `test -e`: ABSENT |
| README licence section (effective grant notice) | MISSING — intentionally withheld; README §License currently states "No LICENSE published: ownership and dependency clearance pending. Do not distribute releases until cleared." | `grep -in licen README.md` (see §7): no effective grant |
| Commercial strategy input | MISSING — pending legal-reviewer response; needs human/lead sign-off before slice 4 (per contract open decisions) | No commercial-strategy file on file |
| Root `LICENSE` / `COPYING` / `NOTICE` | WITHHELD — publishing would make terms effective before clearance (decision D6); AGPL text not yet fetched from `https://www.gnu.org/licenses/agpl-3.0.txt` (U5) | `test ! -e`: all three absent (see §7 `ROOTLIC`) |

## 3. Publication blockers — U1–U6 / L1–L11 (all UNRESOLVED)

> No effective licensing step (grant, notice, header, release, visibility
> change, enforcement) until every row below is cleared with written evidence
> and sign-off. Statuses sourced from `docs/legal/unresolved-blocker-register.md`
> and `docs/legal/legal-clearance-register.md`; appended slice-2 rows included.

| # | Question | Status |
|---|---|---|
| U1 | By what written instrument and signatory authority were Karmathy assets (package names `karmathy-backend`, `karmathy-frontend`, `© 2026 Karmathy` footer/brand in `frontend/src/components/PublicLayout.tsx`) transferred to the LibrePeople project, and who may sign the grant? | **UNRESOLVED** — transfer instrument: none on file. Karmathy strings preserved verbatim (Karmathy, Karmathy, Karmathy — not scrubbed) |
| U2 | Are the 19 direct / 114 transitive backend licences (UNVERIFIED), fpdf2 LGPL-3.0-only, Oracle UPL mix, MPL-2.0 test-only, ISC lucide-react compatible with the proposed posture? (see L1–L5) | **UNRESOLVED** |
| U3 | Exact scope of "original docs" for the CC BY 4.0 PROPOSED grant (`README.md`, `docs/licensing/`, `docs/legal/` package, or narrower)? | **UNRESOLVED** — scope statement: none on file |
| U4 | Authorship dates and contributors for each `unclear` ownership-register row (`README.md`, Dockerfiles text, compose/render/workflow configs, `Makefile`, `ci/run_backend_tests.sh`, app-code authorship)? | **UNRESOLVED** — per-file authorship not yet extracted |
| U5 | Has the official AGPL-3.0 text been fetched from `https://www.gnu.org/licenses/agpl-3.0.txt` and verified? | **UNRESOLVED** (expected; slice-2 step) — `LICENSE.AGPL-3.0.prepared` notes text NOT yet fetched; no root `LICENSE`/`COPYING` |
| U6 | Slice-2 inventory (713 rows; `sbom-20261126T012556Z.json`) confirms U2 still open: fpdf2 LGPL-3.0-only (upstream-declared, UNVERIFIED locally), Oracle UPL/Apache-2.0 mix (UNVERIFIED locally), MPL-2.0 test-only `@axe-core/playwright` (confinement unconfirmed), ISC `lucide-react` (compatibility unconfirmed) | **UNRESOLVED** |
| L1 | 19-direct / 114-transitive backend licence set compatible with future AGPL-3.0-or-later grant? 114 rows UNVERIFIED (no PyPI metadata fetch) | UNVERIFIED — clearance required |
| L2 | fpdf2 2.9.0 (LGPL-3.0-only per upstream, UNVERIFIED locally): lazy, unmodified, unvendored use via `backend/app/services/offer_letter.py` keeps LGPL boundary at the library? | UNVERIFIED — clearance required |
| L3 | Oracle oracledb 26.0.1 + oci 2.192.0 (UPL / Apache-2.0 mix, UNVERIFIED locally): which deploy paths ship them; compatible with proposed AGPL posture? | UNVERIFIED — clearance required |
| L4 | MPL-2.0 test-only components confined to test paths, never shipped in production? | UNVERIFIED — clearance required |
| L5 | ISC `lucide-react`: compatible with proposed posture for frontend bundle? | UNVERIFIED — clearance required |
| L6 | CC BY 4.0 PROPOSED for original docs only: confirm scope before slice 2 | PROPOSED — scope confirmation required |
| L7 | No-endorsement claim wording (no GNU/FSF endorsement, no trademark assignment) sufficient? | DRAFT — reviewer to confirm |
| L8 | Slice-2 finding: fpdf2 UNVERIFIED rows — LGPL boundary + upstream licence text carried on redistribution? | UNVERIFIED — clearance required |
| L9 | Slice-2 finding: oracledb + oci UNVERIFIED rows — deploy-path scope + term compatibility? | UNVERIFIED — clearance required |
| L10 | Slice-2 finding: MPL-2.0 `@axe-core/playwright` 4.14.0 — test-path confinement? | UNVERIFIED — clearance required |
| L11 | Slice-2 finding: ISC `lucide-react` 1.59.0 — frontend-bundle compatibility? | UNVERIFIED — clearance required |

## 4. Commits / branches

| Fact | Value |
|---|---|
| Current branch (`git branch --show-current`) | `chore/licensing-transition` — verified via shell; no merge/rebase/push performed by this slice |
| HEAD | `a9efb34` (slice-1 provenance-baseline commit); `git log --oneline -3` after this slice shows no new commits by this slice |
| `main` ref | `4969512 Merge branch 'agent/qa/cloud-expenses-proof' into main` — untouched (no push/merge; `origin/main` == `main` at `4969512`) |
| Merge base (`git merge-base HEAD main`) | `b14261a` — HEAD (`a9efb34`) is 1 commit ahead of base on a diverged line; `git diff --stat main...HEAD` covers only the 8 committed slice-1 files (190 insertions, 0 deletions of history) |
| Main drift | `main` has moved far ahead on unrelated work (cloud/expenses merges: `4969512`, `5746017`, `abcbf62`, `9dacf9d`, …) while this branch's committed history is the standalone LibrePeople extraction line (`f8877a1`, `62d741a`, `b468324`, `b14261a`, `a9efb34`). No rebase/merge attempted here — drift is recorded, not resolved |
| Uncommitted / stacked changes | Modified: `docs/legal/legal-clearance-register.md`, `docs/legal/unresolved-blocker-register.md` (slice-2 append-only U/L edits). Untracked: `ci/check_licences.py`, `.github/workflows/licence-compliance.yml`, `docs/legal/compliance-ci.md`, `docs/legal/dependency-licence-inventory.json`, `docs/legal/dependency-licence-inventory.md`, `docs/legal/sbom-20261126T012556Z.json`, `spec/features/licensing-compliance-ci/`, `spec/features/licensing-inventory-sbom/`, `spec/features/licensing-provenance-baseline/`, `spec/features/licensing-tracker-consolidation/`, plus this tracker file. Left uncommitted per contract (do not commit/push) |
| Worktrees | 7 entries (`wt-backend-rebrand` on `a9efb34 [chore/licensing-transition]` is this worktree; 6 sibling worktrees on agent branches — see verbatim list) |
| Production-code guard | `git diff --stat main...HEAD -- backend/ frontend/ ci/ Makefile` is EMPTY — no production code changed. Only untracked `ci/check_licences.py` exists in the worktree and it belongs to stacked sibling slice 3, not this slice; this slice adds no `*.py`/`*.tsx`/`*.ts` |

## 5. No-push-to-main-until-review gate

**GATE: NO push to `main`, NO merge to `main`, NO release, and NO switch to
enforcement (blocking) mode without explicit human approval and legal-reviewer
sign-off on all unresolved blockers (U1–U6 / L1–L11).** All work stays on
`chore/licensing-transition`, uncommitted/unpushed unless approved. A green
compliance check never lifts this gate — only a human decision does. The
validator decides acceptance of this slice; this tracker does not claim it.

## 6. Karmathy preservation statement

Every `Karmathy` string in the source tree is preserved verbatim by this
licensing line of work: package names `karmathy-backend`
(`backend/pyproject.toml:2`) and `karmathy-frontend`
(`frontend/package.json:2`), and the `© 2026 Karmathy` footer plus brand
mentions in `frontend/src/components/PublicLayout.tsx` (~lines 105, 172, 198,
202). This tracker performs no rename, scrub, or removal of any Karmathy mark
(Karmathy references intentionally retained for reviewer adjudication) and
claims no trademark assignment. Transfer to the LibrePeople project is
UNRESOLVED (U1) pending written evidence and signatory authority.

## 7. Verbatim command outputs (recorded 2026-11-26, branch `chore/licensing-transition`)

### `git branch --show-current`

```
chore/licensing-transition
```

### `git branch -a`

```
  agent/backend/r2-storage
  agent/backend/rebrand-extract
+ agent/database/migration-chain
+ agent/deploy/standalone-ops
  agent/feat/expenses-ui
  agent/feat/expenses-ui-navfix
+ agent/frontend/rebrand-ux
  agent/frontend/tenantswitcher-gate
  agent/ops/admin-recovery
  agent/ops/api-inventory
  agent/ops/compliance-package
  agent/ops/decision-register
  agent/ops/deploy-config
  agent/ops/enum-flag-fix
  agent/ops/expenses-contract
  agent/ops/feature-matrix
  agent/ops/known-failures-docs
  agent/ops/legal-review
  agent/ops/link-e2e-employee
+ agent/ops/neon-provision
  agent/ops/oracle-scope
  agent/ops/password-rotation
  agent/ops/perf-baseline
  agent/ops/perf-repeat
  agent/ops/pg-proof
  agent/ops/reliability-runbooks
  agent/ops/render-bootstrap
  agent/ops/render-deploy
  agent/ops/render-smoke
  agent/ops/render-watch
  agent/ops/render-watch-2
  agent/ops/requirement-closure
  agent/ops/reviewer-handover
  agent/ops/secret-rotation
  agent/ops/visibility-governance
  agent/qa/acceptance-harness
  agent/qa/api-workflows
  agent/qa/browser-e2e
  agent/qa/cloud-e2e-pack
  agent/qa/cloud-e2e-round3
  agent/qa/cloud-e2e-run
  agent/qa/cloud-expenses
  agent/qa/cloud-expenses-proof
  agent/qa/cloud-expenses-verify
+ agent/qa/final-regression
  agent/qa/firefox-e2e
  agent/qa/harness-flip-assert
  agent/qa/integrity-head-fix
  agent/quality/suite-failures
  agent/sec/cors-hardening
  agent/sec/mfa-column-pg
  agent/sec/mfa-fixture-scan
* chore/licensing-transition
  main
  remotes/origin/HEAD -> origin/main
  remotes/origin/agent/ops/feature-matrix
  remotes/origin/agent/ops/render-deploy
  remotes/origin/main
```

### `git status --porcelain` (full)

```
M docs/legal/legal-clearance-register.md
 M docs/legal/unresolved-blocker-register.md
?? .github/workflows/licence-compliance.yml
?? ci/check_licences.py
?? docs/legal/compliance-ci.md
?? docs/legal/dependency-licence-inventory.json
?? docs/legal/dependency-licence-inventory.md
?? docs/legal/licensing-transition-tracker.md
?? docs/legal/sbom-20261126T012556Z.json
?? spec/features/licensing-compliance-ci/
?? spec/features/licensing-inventory-sbom/
?? spec/features/licensing-provenance-baseline/
?? spec/features/licensing-tracker-consolidation/
```

(This slice's only change is the added
`?? docs/legal/licensing-transition-tracker.md` line; every other entry is
pre-existing stacked sibling-slice work. See contract deviation in §8:
the worktree status necessarily shows more than just the tracker file.)

### `git status --porcelain -- docs/legal spec/features` (scoped)

```
M docs/legal/legal-clearance-register.md
 M docs/legal/unresolved-blocker-register.md
?? docs/legal/compliance-ci.md
?? docs/legal/dependency-licence-inventory.json
?? docs/legal/dependency-licence-inventory.md
?? docs/legal/licensing-transition-tracker.md
?? docs/legal/sbom-20261126T012556Z.json
?? spec/features/licensing-compliance-ci/
?? spec/features/licensing-inventory-sbom/
?? spec/features/licensing-provenance-baseline/
?? spec/features/licensing-tracker-consolidation/
```

(Captured after this slice; the only line attributable to this slice is
`?? docs/legal/licensing-transition-tracker.md`.)

### `git log --oneline -10` (current branch)

```
a9efb34 docs(legal): prepared-only licensing provenance baseline (Tier 1)
b14261a Remove out-of-scope US rule pack (India-first); shipped verified allowlist is in-standard.json only
b468324 Rebrand backend Karmathy->LibrePeople; DEFAULT_CURRENCY USD->INR
62d741a feat: migrate verified HCM backend and frontend
f8877a1 chore: establish standalone LibrePeople repository
```

### `git log --oneline -10 main`

```
4969512 Merge branch 'agent/qa/cloud-expenses-proof' into main
5746017 docs(cloud): round-5 expenses nav-fix verified live on abcbf62
abcbf62 Merge branch 'agent/feat/expenses-ui-navfix' into main
9dacf9d Merge branch 'agent/qa/cloud-expenses-verify' into main
ca168d1 Merge branch 'agent/qa/cloud-expenses' into main
a49095d docs(cloud): verification — expenses nav fix not deployed, re-run blocked
7d4ab08 fix(expenses): absolute post-create navigate to /expenses/:id
b21eeec test(cloud): round-4 expenses — 2 pass/1 skip (provisioning), full pack 27/1/0
530a49f Merge branch 'agent/feat/expenses-ui': expenses UI slice (list/detail/create + L1/L2 approve + mark-paid + receipts, 18 tests)
acb7a24 feat: expenses UI slice (list/detail/create + L1/L2 approve + mark-paid + receipts, 18 tests)
```

### `git rev-parse HEAD main origin/main`

```
a9efb345d7d6e4f701e551263a93f3e835ba3df6
496951222bc212eb4630319db26f108898def57d
496951222bc212eb4630319db26f108898def57d
```

### `git merge-base HEAD main`

```
b14261aba3e6ece6e9bd0f9677a556d696d1b56d
```

### `git diff --stat main...HEAD`

```
 docs/legal/LICENSE.AGPL-3.0.prepared            | 12 ++++++
 docs/legal/decision-register.md                 | 17 +++++++++
 docs/legal/governance-note.md                   | 12 ++++++
 docs/legal/legal-clearance-register.md          | 14 +++++++
 docs/legal/licensing-policy.md                  | 35 +++++++++++++++++
 docs/legal/ownership-and-provenance-register.md | 50 +++++++++++++++++++++++++
 docs/legal/third-party-licences.md              | 38 +++++++++++++++++++
 docs/legal/unresolved-blocker-register.md       | 12 ++++++
 8 files changed, 190 insertions(+)
```

### `git worktree list`

```
/Users/srinivas/LLM/Workforce/LibrePeople               f3b2cd4 [agent/feat/small-api-gaps]
/Users/srinivas/LLM/Workforce/agent-frontend-rebrand-ux 66b751d [agent/frontend/rebrand-ux]
/Users/srinivas/LLM/Workforce/qa-final-regression       4cc8be1 [agent/qa/final-regression]
/Users/srinivas/LLM/Workforce/wt-backend-rebrand        a9efb34 [chore/licensing-transition]
/Users/srinivas/LLM/Workforce/wt-database               c6d2f10 [agent/database/migration-chain]
/Users/srinivas/LLM/Workforce/wt-deploy-ops             daddd21 [agent/deploy/standalone-ops]
/Users/srinivas/LLM/Workforce/wt-neon-provision         fd9d4c5 [agent/ops/neon-provision]
```

### Root licence absence (`test ! -e LICENSE / COPYING / NOTICE`)

```
no LICENSE
no COPYING
no NOTICE
```

(each line printed because the corresponding `test ! -e <file>` passed —
no root licence file exists.)

### Production-code guard (`git diff --stat main...HEAD -- backend/ frontend/ ci/ Makefile`)

```
(empty — no output; no production code changed)
```

### Slice-4 absence check

```
ABSENT: CONTRIBUTING.md
ABSENT: CODE_OF_CONDUCT.md
ABSENT: SECURITY.md
ABSENT: .github/ISSUE_TEMPLATE/bug_report.md
ABSENT: .github/ISSUE_TEMPLATE/feature_request.md
ABSENT: .github/ISSUE_TEMPLATE/legal-review.md
ABSENT: .github/pull_request_template.md
EXISTS: README.md (licence section: "No LICENSE published: ownership and dependency clearance pending. Do not distribute releases until cleared." — no effective grant)
```

## 8. Contract deviations

- **Criterion 3 (status shows ONLY the tracker file):** cannot be met
  literally in this worktree because stacked uncommitted sibling-slice work
  (slices 2–3: inventory/SBOM files, `ci/check_licences.py`,
  `licence-compliance.yml`, `compliance-ci.md`, modified U/L registers, and
  the `spec/features/licensing-*/` harness inputs) predates this slice and
  must be left uncommitted per instructions. This slice itself adds ONLY
  `docs/legal/licensing-transition-tracker.md` (untracked) and makes zero
  commits — verified by `git log --oneline -3` (unchanged: `a9efb34`,
  `b14261a`, `b468324`) and by the scoped status diff. The sibling-slice
  compliance-ci contract itself anticipates this stacking (its criterion 7
  excludes "uncommitted sibling-slice paths on the same branch").
- No other deviations: single new docs-only file, no `*.py`/`*.tsx`/`*.ts`
  touched by this slice, no root licence added, no Karmathy scrub, no
  scanner/CI changes, no merge/rebase/push.
