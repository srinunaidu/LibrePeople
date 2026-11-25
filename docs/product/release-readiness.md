# LibrePeople — Release Readiness Dashboard

> **Status: NOT READY FOR PRODUCTION RELEASE — NOT READY**

- Branch: `feature/librepeople-production`
- Worktree: `/Users/srinivas/LLM/Workforce/librepeople-prod`
- Base commit: `af0e2289e5f83b05b5953457cdc884ae5356cdb6`
- Generated: 2026-11-22 (UTC)
- Scope: docs-only dashboard. No app code was changed to produce this file.
- Machine-readable mirror: `docs/product/release-readiness.json` (numbers identical).
- **No production claims.** Nothing in this file claims production readiness, a production deployment,
  customer data handling, or a verified production payroll run. All verdicts below are read-only
  observations with a refresh command per row.

## 1. Release status — NOT READY

The release is NOT READY because every blocking fact below is observed, not assumed.
NOT READY is held by row 6 (FY26-27 pack `pending_verification`, engine refuses IN pay
on/after 2026-04-01) and 17 BLOCKED traceability rows — even though the secret scan is
now clean (row 5: 0 findings, exit 0, observed 2026-11-22 UTC).

| # | Blocking fact | Observed value | Source file | Refresh command |
|---|---|---|---|---|
| 1 | Traceability rows still NOT STARTED | 0 / 136 (TESTED 78, IMPLEMENTED 38, BLOCKED 17, IN PROGRESS 3, VERIFIED 0) | `docs/product/requirements-traceability.csv` | `awk -F, 'NR>1 && $4=="NOT STARTED" {n++} END{print n+0}' docs/product/requirements-traceability.csv` → `0` |
| 2 | Traceability rows IMPLEMENTED | 38 (TESTED 78, BLOCKED 17, IN PROGRESS 3, VERIFIED 0, NOT STARTED 0) | `docs/product/requirements-traceability.csv` | `awk -F, 'NR>1 && $4=="IMPLEMENTED" {n++} END{print n+0}' docs/product/requirements-traceability.csv` → `38` |
| 3 | Level-B battery executed areas | 0 of 20 (all PLANNED, NOT-RUN) | `docs/product/acceptance-suite.md` | `grep -c '^Status: PLANNED' docs/product/acceptance-suite.md` → `20` |
| 4 | Backend suites executed in this slice | 0 of 52 defined (NOT-RUN) | `ci/run_backend_tests.sh` | `sed -n '/^SUITES=(/,/^)/p' ci/run_backend_tests.sh \| grep -cE '^\s+[a-z]'` → `52` (defined; execution NOT-RUN) |
| 5 | Secret-scan findings open | 0 findings (clean — `secret_scan: no secrets found.`), exit 0, observed 2026-11-22 (UTC) | `ci/secret_scan.py` | `python3 ci/secret_scan.py; echo exit=$?` → `secret_scan: no secrets found.`, `exit=0` |
| 6 | Payroll pack for FY26-27 onward | `pending_verification` (engine refuses IN pay on/after 2026-04-01) | `backend/rule_packs/in-standard-fy2627-skeleton.json` | `grep -H '"status"' backend/rule_packs/in-standard-fy2627-skeleton.json` → `"pending_verification"` |
| 7 | Surplus IDs with no phase / no owner decision | 14, decision-gated | `docs/product/phase-gates.md` (surplus table) | `grep -oE 'LP-[A-Z]+-[0-9]+' docs/product/phase-gates.md \| sort -u \| wc -l` → `136` (= 122 assigned + 14 surplus) |

## 2. Traceability — 136 IDs: TESTED 78, IMPLEMENTED 38, BLOCKED 17, IN PROGRESS 3, VERIFIED 0

| Implementation status (col 4) | Observed count | Source file | Refresh command |
|---|---|---|---|
| TESTED | 78 | `docs/product/requirements-traceability.csv` | `awk -F, 'NR>1 && $4=="TESTED" {n++} END{print n+0}' docs/product/requirements-traceability.csv` → `78` |
| IMPLEMENTED | 38 | `docs/product/requirements-traceability.csv` | `awk -F, 'NR>1 && $4=="IMPLEMENTED" {n++} END{print n+0}' docs/product/requirements-traceability.csv` → `38` |
| BLOCKED | 17 | `docs/product/requirements-traceability.csv` | `awk -F, 'NR>1 && $4=="BLOCKED" {n++} END{print n+0}' docs/product/requirements-traceability.csv` → `17` |
| IN PROGRESS | 3 | `docs/product/requirements-traceability.csv` | `awk -F, 'NR>1 && $4=="IN PROGRESS" {n++} END{print n+0}' docs/product/requirements-traceability.csv` → `3` |
| VERIFIED | 0 | `docs/product/requirements-traceability.csv` | `awk -F, 'NR>1 && $4=="VERIFIED" {n++} END{print n+0}' docs/product/requirements-traceability.csv` → `0` |
| NOT STARTED | 0 | `docs/product/requirements-traceability.csv` | `awk -F, 'NR>1 && $4=="NOT STARTED" {n++} END{print n+0}' docs/product/requirements-traceability.csv` → `0` |
| Total data rows | 136 | `docs/product/requirements-traceability.csv` | `tail -n +2 docs/product/requirements-traceability.csv \| wc -l` → `136` |
| Distinct status values present | 4 (`TESTED`, `IMPLEMENTED`, `BLOCKED`, `IN PROGRESS`) | `docs/product/requirements-traceability.csv` | `awk -F, 'NR>1{c[$4]++} END{for(s in c) print s, c[s]}' docs/product/requirements-traceability.csv` → `TESTED 78, IMPLEMENTED 38, BLOCKED 17, IN PROGRESS 3` |

Histogram arithmetic: **78 + 38 + 17 + 3 + 0 + 0 = 136 total.**

## 3. Coverage — 122 assigned + 14 surplus = 136

Per-phase extraction command shape (replace `A<n>`):

`awk -v h='## Phase A<n> ' 'index($0,h){f=1;next} f&&/^## Phase /{exit} f{print}' docs/product/phase-gates.md | grep '^PRD IDs covered:' | grep -oE 'LP-[A-Z]+-[0-9]+' | sort -u | wc -l`

| Phase | Observed unique PRD IDs | Source file | Refresh command |
|---|---|---|---|
| A0 | 4 | `docs/product/phase-gates.md` | `awk -v h='## Phase A0 ' 'index($0,h){f=1;next} f&&/^## Phase /{exit} f{print}' docs/product/phase-gates.md \| grep '^PRD IDs covered:' \| grep -oE 'LP-[A-Z]+-[0-9]+' \| sort -u \| wc -l` → `4` |
| A1 | 5 | `docs/product/phase-gates.md` | `awk -v h='## Phase A1 ' 'index($0,h){f=1;next} f&&/^## Phase /{exit} f{print}' docs/product/phase-gates.md \| grep '^PRD IDs covered:' \| grep -oE 'LP-[A-Z]+-[0-9]+' \| sort -u \| wc -l` → `5` |
| A2 | 5 | `docs/product/phase-gates.md` | `awk -v h='## Phase A2 ' 'index($0,h){f=1;next} f&&/^## Phase /{exit} f{print}' docs/product/phase-gates.md \| grep '^PRD IDs covered:' \| grep -oE 'LP-[A-Z]+-[0-9]+' \| sort -u \| wc -l` → `5` |
| A3 | 18 | `docs/product/phase-gates.md` | `awk -v h='## Phase A3 ' 'index($0,h){f=1;next} f&&/^## Phase /{exit} f{print}' docs/product/phase-gates.md \| grep '^PRD IDs covered:' \| grep -oE 'LP-[A-Z]+-[0-9]+' \| sort -u \| wc -l` → `18` |
| A4 | 18 | `docs/product/phase-gates.md` | `awk -v h='## Phase A4 ' 'index($0,h){f=1;next} f&&/^## Phase /{exit} f{print}' docs/product/phase-gates.md \| grep '^PRD IDs covered:' \| grep -oE 'LP-[A-Z]+-[0-9]+' \| sort -u \| wc -l` → `18` |
| A5 | 27 | `docs/product/phase-gates.md` | `awk -v h='## Phase A5 ' 'index($0,h){f=1;next} f&&/^## Phase /{exit} f{print}' docs/product/phase-gates.md \| grep '^PRD IDs covered:' \| grep -oE 'LP-[A-Z]+-[0-9]+' \| sort -u \| wc -l` → `27` |
| A6 | 9 | `docs/product/phase-gates.md` | `awk -v h='## Phase A6 ' 'index($0,h){f=1;next} f&&/^## Phase /{exit} f{print}' docs/product/phase-gates.md \| grep '^PRD IDs covered:' \| grep -oE 'LP-[A-Z]+-[0-9]+' \| sort -u \| wc -l` → `9` |
| A7 | 13 | `docs/product/phase-gates.md` | `awk -v h='## Phase A7 ' 'index($0,h){f=1;next} f&&/^## Phase /{exit} f{print}' docs/product/phase-gates.md \| grep '^PRD IDs covered:' \| grep -oE 'LP-[A-Z]+-[0-9]+' \| sort -u \| wc -l` → `13` |
| A8 | 9 | `docs/product/phase-gates.md` | `awk -v h='## Phase A8 ' 'index($0,h){f=1;next} f&&/^## Phase /{exit} f{print}' docs/product/phase-gates.md \| grep '^PRD IDs covered:' \| grep -oE 'LP-[A-Z]+-[0-9]+' \| sort -u \| wc -l` → `9` |
| A9 | 2 | `docs/product/phase-gates.md` | `awk -v h='## Phase A9 ' 'index($0,h){f=1;next} f&&/^## Phase /{exit} f{print}' docs/product/phase-gates.md \| grep '^PRD IDs covered:' \| grep -oE 'LP-[A-Z]+-[0-9]+' \| sort -u \| wc -l` → `2` |
| A10 | 10 | `docs/product/phase-gates.md` | `awk -v h='## Phase A10 ' 'index($0,h){f=1;next} f&&/^## Phase /{exit} f{print}' docs/product/phase-gates.md \| grep '^PRD IDs covered:' \| grep -oE 'LP-[A-Z]+-[0-9]+' \| sort -u \| wc -l` → `10` |
| A11 | 2 | `docs/product/phase-gates.md` | `awk -v h='## Phase A11 ' 'index($0,h){f=1;next} f&&/^## Phase /{exit} f{print}' docs/product/phase-gates.md \| grep '^PRD IDs covered:' \| grep -oE 'LP-[A-Z]+-[0-9]+' \| sort -u \| wc -l` → `2` |
| Assigned subtotal | 122 | `docs/product/phase-gates.md` | sum of the 12 rows above: 4+5+5+18+18+27+9+13+9+2+10+2 = `122` |
| Surplus (no phase) | 14 | `docs/product/phase-gates.md` (surplus table) | `136` global − `122` assigned = `14` |
| Global total | 136 | `docs/product/phase-gates.md` | `grep -oE 'LP-[A-Z]+-[0-9]+' docs/product/phase-gates.md \| sort -u \| wc -l` → `136` |
| CSV IDs missing from phase-gates | 0 | `docs/product/requirements-traceability.csv` + `docs/product/phase-gates.md` | `comm -13 <(tail -n +2 docs/product/requirements-traceability.csv \| cut -d, -f1 \| sort -u) <(grep -oE 'LP-[A-Z]+-[0-9]+' docs/product/phase-gates.md \| sort -u) \| wc -l` → `0` |
| Phase-gate IDs outside the CSV | 0 | `docs/product/requirements-traceability.csv` + `docs/product/phase-gates.md` | `comm -23 <(tail -n +2 docs/product/requirements-traceability.csv \| cut -d, -f1 \| sort -u) <(grep -oE 'LP-[A-Z]+-[0-9]+' docs/product/phase-gates.md \| sort -u) \| wc -l` → `0` |

Coverage arithmetic: **122 assigned + 14 surplus = 136 total.**

## 4. Tests — observed counts only, NOT-RUN where not executed

No passes are invented. Anything not executed in this docs-only slice is labelled NOT-RUN.

| Suite / check | Observed result | Verdict | Source file | Refresh command |
|---|---|---|---|---|
| Traceability NOT STARTED count | 0 | OBSERVED | `docs/product/requirements-traceability.csv` | `awk -F, 'NR>1 && $4=="NOT STARTED" {n++} END{print n+0}' docs/product/requirements-traceability.csv` → `0` |
| Traceability TESTED count | 78 | OBSERVED | `docs/product/requirements-traceability.csv` | `awk -F, 'NR>1 && $4=="TESTED" {n++} END{print n+0}' docs/product/requirements-traceability.csv` → `78` |
| Traceability IMPLEMENTED count | 38 | OBSERVED | `docs/product/requirements-traceability.csv` | `awk -F, 'NR>1 && $4=="IMPLEMENTED" {n++} END{print n+0}' docs/product/requirements-traceability.csv` → `38` |
| Traceability BLOCKED count | 17 | OBSERVED (release still NOT READY while BLOCKED > 0) | `docs/product/requirements-traceability.csv` | `awk -F, 'NR>1 && $4=="BLOCKED" {n++} END{print n+0}' docs/product/requirements-traceability.csv` → `17` |
| Traceability IN PROGRESS count | 3 | OBSERVED | `docs/product/requirements-traceability.csv` | `awk -F, 'NR>1 && $4=="IN PROGRESS" {n++} END{print n+0}' docs/product/requirements-traceability.csv` → `3` |
| Traceability VERIFIED count | 0 | OBSERVED | `docs/product/requirements-traceability.csv` | `awk -F, 'NR>1 && $4=="VERIFIED" {n++} END{print n+0}' docs/product/requirements-traceability.csv` → `0` |
| Phase-gate global ID count | 136 | OBSERVED | `docs/product/phase-gates.md` | `grep -oE 'LP-[A-Z]+-[0-9]+' docs/product/phase-gates.md \| sort -u \| wc -l` → `136` |
| Level-B battery areas | 20 defined, 20 PLANNED, 0 executed | NOT-RUN | `docs/product/acceptance-suite.md` | `grep -c '^## Area' docs/product/acceptance-suite.md` → `20`; `grep -c '^Status: PLANNED' docs/product/acceptance-suite.md` → `20` |
| Backend suites (`ci/run_backend_tests.sh`) | 52 defined, 0 executed here | NOT-RUN | `ci/run_backend_tests.sh` | `sed -n '/^SUITES=(/,/^)/p' ci/run_backend_tests.sh \| grep -cE '^\s+[a-z]'` → `52`; run with `bash ci/run_backend_tests.sh` (not run in this slice) |
| Rules/pack suites (`backend/app/rules`) | not executed here | NOT-RUN | `backend/app/rules/` | `cd backend && python3 -m pytest app/rules -q` (not run in this slice) |
| Migration files present | 44 files (count only, not a test) | OBSERVED-COUNT | `backend/migrations/versions/` | `ls backend/migrations/versions/*.py \| wc -l` → `44` |
| Secret scan | 0 findings (clean — `secret_scan: no secrets found.`), exit 0, observed 2026-11-22 (UTC) | OBSERVED-PASS (see §5) | `ci/secret_scan.py` | `python3 ci/secret_scan.py; echo exit=$?` → `secret_scan: no secrets found.`, `exit=0` |

## 5. Security findings

| # | Finding | Observed value | Source file | Refresh command |
|---|---|---|---|---|
| S-01 | Secret-scan total findings | 0, exit 0 (clean — build gate passes), observed 2026-11-22 (UTC) | `ci/secret_scan.py` | `python3 ci/secret_scan.py; echo exit=$?` → `secret_scan: no secrets found.`, `exit=0` |
| S-02 | `secret-assignment` on `PASSWORD` in backend test suites | 0 (none observed 2026-11-22) | `ci/secret_scan.py` | `python3 ci/secret_scan.py \| grep -c "value assigned to 'PASSWORD'"` → `0` |
| S-03 | `secret-assignment` on `SECRET_KEY` in payroll execution suite | 0 (none observed 2026-11-22) | `ci/secret_scan.py` | `python3 ci/secret_scan.py \| grep -c "payroll_execution_test_suite"` → `0` |
| S-04 | `secret-assignment` on `token` in frontend design-alignment script | 0 (none observed 2026-11-22) | `ci/secret_scan.py` | `python3 ci/secret_scan.py \| grep -c "check-design-alignment"` → `0` |

Security note: secret scan observed clean on 2026-11-22 (UTC) — 0 findings, exit 0, so no
open secret-scan defects are carried by this dashboard. No production-security posture is
claimed.

## 6. Payroll — pack status + 409 gate

| # | Check | Observed value | Source file | Refresh command |
|---|---|---|---|---|
| P-01 | FY25-26 pack status (`in-standard` v1.0.0) | `verified` | `backend/rule_packs/in-standard.json` (mirror: `rule_packs/in-standard.json`) | `grep -H '"status"' backend/rule_packs/in-standard.json rule_packs/in-standard.json` → `"verified"` (both) |
| P-02 | FY26-27 skeleton pack status | `pending_verification` — engine refuses IN calculations on/after 2026-04-01 | `backend/rule_packs/in-standard-fy2627-skeleton.json` (mirror: `rule_packs/in-standard-fy2627-skeleton.json`) | `grep -H '"status"' backend/rule_packs/in-standard-fy2627-skeleton.json` → `"pending_verification"` |
| P-03 | Refusal code for unverified pack | `rule_pack_not_verified` (409 CONFLICT category) | `backend/app/rules/resolver.py:10` (code contract), `backend/app/api/v1/endpoints/filings.py:55` (`status_code=409`) | `grep -rn "rule_pack_not_verified" backend/app/rules/resolver.py backend/app/api/v1/endpoints/filings.py` |
| P-04 | Pay-run path raises the refusal instead of calculating | raise sites present, nothing calculated on refusal | `backend/app/api/v1/endpoints/payroll.py:536,544` | `grep -n "rule_pack_not_verified" backend/app/api/v1/endpoints/payroll.py` |
| P-05 | Reports/filings paths refuse identically | 409 `rule_pack_not_verified` with same details shape | `backend/app/api/v1/endpoints/reports.py:476,487,638` | `grep -n "rule_pack_not_verified" backend/app/api/v1/endpoints/reports.py` |

Payroll note: no end-to-end payroll run to a `Paid` state is claimed here, and no production payroll
calculation is claimed. The FY26-27 skeleton is structure only per
`backend/rule_packs/in-standard-FY2627-SIGNOFF.md`.

## 7. Defects and surplus (decision-gated)

14 surplus PRD IDs have no phase assigned and start only when product-owner decisions are recorded
(surplus table in `docs/product/phase-gates.md`). Each row below is individually refreshable.

| PRD ID | Subject | Source file | Refresh command |
|---|---|---|---|
| LP-ADM-005 | Administrator-visible upgrade/backup status and operational warnings | `docs/product/phase-gates.md` | `grep -q 'LP-ADM-005' docs/product/phase-gates.md && echo present` → `present` |
| LP-DATA-002 | Import validation (type, size, encoding, columns, duplicates, references) | `docs/product/phase-gates.md` | `grep -q 'LP-DATA-002' docs/product/phase-gates.md && echo present` → `present` |
| LP-EXP-001 | Expense categories, limits, policies, currencies, receipts, submission | `docs/product/phase-gates.md` | `grep -q 'LP-EXP-001' docs/product/phase-gates.md && echo present` → `present` |
| LP-EXP-002 | Travel requests, claims, multi-level approvals, reimbursement status | `docs/product/phase-gates.md` | `grep -q 'LP-EXP-002' docs/product/phase-gates.md && echo present` → `present` |
| LP-EXP-003 | Approved reimbursements into payroll/payment exports | `docs/product/phase-gates.md` | `grep -q 'LP-EXP-003' docs/product/phase-gates.md && echo present` → `present` |
| LP-NOT-001 | In-app notification centre and event-driven notifications | `docs/product/phase-gates.md` | `grep -q 'LP-NOT-001' docs/product/phase-gates.md && echo present` → `present` |
| LP-NOT-002 | Configurable email delivery through replaceable providers | `docs/product/phase-gates.md` | `grep -q 'LP-NOT-002' docs/product/phase-gates.md && echo present` → `present` |
| LP-NOT-003 | (Notifications surplus — see surplus table) | `docs/product/phase-gates.md` | `grep -q 'LP-NOT-003' docs/product/phase-gates.md && echo present` → `present` |
| LP-DOC-001 | (Documents surplus — see surplus table) | `docs/product/phase-gates.md` | `grep -q 'LP-DOC-001' docs/product/phase-gates.md && echo present` → `present` |
| LP-DOC-002 | (Documents surplus — see surplus table) | `docs/product/phase-gates.md` | `grep -q 'LP-DOC-002' docs/product/phase-gates.md && echo present` → `present` |
| LP-DOC-003 | (Documents surplus — see surplus table) | `docs/product/phase-gates.md` | `grep -q 'LP-DOC-003' docs/product/phase-gates.md && echo present` → `present` |
| LP-SVC-001 | (Helpdesk surplus — see surplus table) | `docs/product/phase-gates.md` | `grep -q 'LP-SVC-001' docs/product/phase-gates.md && echo present` → `present` |
| LP-SVC-002 | (Helpdesk surplus — see surplus table) | `docs/product/phase-gates.md` | `grep -q 'LP-SVC-002' docs/product/phase-gates.md && echo present` → `present` |
| LP-SVC-003 | (Helpdesk surplus — see surplus table) | `docs/product/phase-gates.md` | `grep -q 'LP-SVC-003' docs/product/phase-gates.md && echo present` → `present` |

Surplus count check: `grep -oE 'LP-(ADM-005|DATA-002|EXP-00[123]|NOT-00[123]|DOC-00[123]|SVC-00[123])' docs/product/phase-gates.md | sort -u | wc -l` → `14`.

Open defects carried by this dashboard: the 14 decision-gated surplus items above plus the 17
BLOCKED traceability rows (§2). The secret scan is clean (0 findings, exit 0, observed
2026-11-22 UTC) and carries no open defect. No defect is claimed fixed here beyond what the
refresh commands above observe.

## 8. How to refresh this dashboard

Re-run every `Refresh command` in §§1–7 on branch `feature/librepeople-production`; any changed
observed value means this file (and its JSON mirror) must be regenerated, not hand-edited.
Validation gate for this slice:

```
test -s docs/product/release-readiness.md && test -s docs/product/release-readiness.json \
&& awk -F, 'NR>1 && $4=="NOT STARTED" {n++} END{exit !(n==0)}' docs/product/requirements-traceability.csv \
&& awk -F, 'NR>1 && $4=="TESTED" {n++} END{exit !(n==78)}' docs/product/requirements-traceability.csv \
&& awk -F, 'NR>1 && $4=="IMPLEMENTED" {n++} END{exit !(n==38)}' docs/product/requirements-traceability.csv \
&& awk -F, 'NR>1 && $4=="BLOCKED" {n++} END{exit !(n==17)}' docs/product/requirements-traceability.csv \
&& awk -F, 'NR>1 && $4=="IN PROGRESS" {n++} END{exit !(n==3)}' docs/product/requirements-traceability.csv \
&& awk -F, 'NR>1 && $4=="VERIFIED" {n++} END{exit !(n==0)}' docs/product/requirements-traceability.csv \
&& python3 ci/secret_scan.py | grep -q 'no secrets found' \
&& grep -q 'NOT READY' docs/product/release-readiness.md \
&& git status --short | grep -v '^??' | grep -v 'release-readiness' | wc -l | grep -q '^ *0$'
```
