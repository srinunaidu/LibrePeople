# LibrePeople — Master Feature-Parity Checklist

Branch: `agent/ops/parity-checklist` from main HEAD `e67f618` (verified `git rev-parse HEAD`).
Date: 2026-11-26. Read-only synthesis — no suites re-run, no code changed, CSV untouched.
Rule: no invented completions; anything unsourced is marked NOT VERIFIED.

## Recomputed CSV counts (source: `docs/product/requirements-traceability.csv`, header + python csv parse)

136 data rows. VERIFIED 104; IMPLEMENTED 3 (LP-TIME-008/009/010); IN PROGRESS 3 (LP-NFR-009/010/011);
BLOCKED 18 (LP-DOC-003, LP-NFR-012/013, 15× LP-PAY-001…015); DEFERRED 8
(LP-EXP-001/002/003, LP-NOT-001/003, LP-SVC-001/002/003). Matches the CSV header comment.
19 distinct Domain codes in CSV (ADM AUD COMP CORE DATA DOC ESS EXP INT LEAVE LIFE NFR NOT PAY REC REP SVC TAL TIME).
Task brief cites 22 HCM domains; 3 additional domains have no CSV rows and no sourced evidence —
marked NOT VERIFIED below (§20), not filled.

## E2E evidence actually quoted (not re-run)

- Local: desktop **100 passed** + responsive **16 passed** = **116** (`docs/release/e2e-report.md`, 2026-11-25,
  branch `agent/qa/browser-e2e`). Firefox report confirms same Chromium baseline 116
  (`docs/release/e2e-report-firefox.md`). No "829/829" claim found anywhere — NOT VERIFIED, not repeated.
- Cloud (`docs/cloud-e2e-report.md`): round 1: 9 passed / 16 failed; round 2 canonical 15 passed / 10 failed;
  round 3: **25/25** (D-1 fix verified, zero 403s); expenses rounds 4–5 + full pack **35 passed / 0 failed / 0 skipped**
  (final line 343). Firefox desktop run host-blocked; Gecko 159 result 112/116 per ADR-006 (env caveat, not product).
- Frontend scripts (`frontend/package.json`): `test:unit` vitest, `e2e`/`e2e:desktop` playwright, `verify`
  (typecheck + check:routes + check:api-paths + check:design + build + check:classes). Counts cited are per-report runs.
- API inventory (`docs/api-inventory.md` @216e869): 387 routes / 33 modules; contract ~90 endpoints, 0 missing.
  Discrepancies D-01…D-06 (`docs/api-discrepancy-report.md`): D-02/D-03 closed by a0a1fc5, D-04/D-05 by 502b672/2f05c5f,
  D-06 no action; D-01 OPEN (test_assets.py still in endpoints/, 0 routes).
- Known failures (`docs/known-test-failures.md`): all 8 rows read RESOLVED — security_headers, import,
  india_payroll (114/0), payroll_framework_restart, reset_admin_password, scheduling (ENV-RESOLVED via .venv311),
  cost_forecast, accuracy (both via 1b945fb route registration). Green gates: migration 67/0, security 2162/0, leave 100/0.
- Known limitations (`docs/validation/known-limitations.md` + release-notes §§3/5): Oracle/prod-DB unproven locally;
  statutory sign-off outstanding (payroll dry-run FY25-26 only, gratuity OFF); no load/perf measurement (NFR PROPOSED);
  expenses UI deferred-per-CSV (UI slice exists, see EXP row); no prod deploy/customer-data/payroll activation w/o approval.
- Gap register (`docs/programme/phase2-domain-gap-register.md`): gaps #1–2 FIXED; **gaps #3–#23 OPEN**
  (helpdesk self-create, backup/restore theatre, FY26-27 payroll, workflow engine, expenses UI, filing persistence,
  ER, docs UI, SCIM, reporting schedule/export, assets lifecycle, + medium/low #14–#23, + #23 platform residency/scheduler).

## Domain verdicts (implemented / tested / independently verified / partial / deferred / unsupported / defects)

| # | Domain | Req IDs | Implemented | Tested (passing suite cited) | Independently verified | Partial / Deferred / Unsupported | Known defects / evidence |
|---|---|---|---|---|---|---|---|
| 1 | ADM (Admin/auth) | LP-ADM-001…005 | Yes — auth.py:169/260/446, break_glass.py:130; App.tsx:181, Login/Mfa/UserAdmin | Yes — access 86, mfa 17, security 2073, admin_status 32 | Harness PASS fd568cd (access/mfa/security; admin_status) | — | Break-glass dep; D-03 contract snapshot (now closed a0a1fc5) |
| 2 | AUD (Audit) | LP-AUD-001…006 | Yes — admin_audit.py:84, reports.py:63; audit.py:18/:66 | Yes — audit 29 + chain 58; admin_audit PASS 7cba30f/fd568cd | Harness PASS fd568cd | — | AUD-005/006 route-mount FAIL on b3d72e2 (fixed per harness) |
| 3 | COMP (Compliance) | LP-COMP-001…012 | Yes — compliance.py:38–132; ComplianceCenter route | Partial — no dedicated endpoint suite; engine via india_payroll 114 | Harness PASS fd568cd (india_payroll) | PARTIAL endpoint coverage | Statutory sign-off outstanding (gap #5/#8) |
| 4 | CORE (Core HR) | LP-CORE-001…010 | Yes — employees.py:181–609, core_hr.py:89–452, People.tsx, ClientOnboarding | Yes — employees 64, history 85, legal_entity 49, master_data 35, custom_fields 29 | Harness PASS fd568cd | — | — |
| 5 | DATA (Import/DQ) | LP-DATA-001…007 | Yes — import_export.py:183–379, data_quality router, Import.tsx | Yes — DQ 44, migration 67, retention 11, schema 17+12; import PASS 7cba30f/fd568cd | Harness PASS fd568cd | — | import QueuePool timeout on b3d72e2 (fixed per harness) |
| 6 | DOC (Documents) | LP-DOC-001/002 + LP-DOC-003 BLOCKED | 001/002 yes (core_hr.py:452, 0040 migration); 003 storage BLOCKED | Yes — doc_002 11/0, files 8/0 | Harness PASS fd568cd (001/002); 003 NOT verified | BLOCKED: LP-DOC-003 storage backend (gap #10) | No standalone UI; expiry DQ-check only |
| 7 | ESS | LP-ESS (6) | Yes — ESSHub.tsx, ess_hr.py (IDOR fixed 5cf0568, 51/51) | Yes — ESS suites green | Harness evidence per CSV | — | IDOR fixed; SuperAdmin workspace list not cloud-covered (no account) |
| 8 | EXP (Expenses) | LP-EXP-001…003 CSV-DEFERRED | UI NOW EXISTS — /expenses, /expenses/new, /expenses/:id (acb7a24, navfix 7d4ab08, merged 530a49f); backend 16 routes | Yes — 18/18 UI tests; cloud R4 2/0/1skip + R5 associate PASS | Cloud-e2e R4/R5 live PASS on abcbf62 | CSV still DEFERRED (stale; matrix already flips to IMPLEMENTED) — **do NOT change CSV here** | CSV/matrix staleness acknowledged, not resolved |
| 9 | INT (Integrations) | LP-INT (5) | Yes per CSV file:line refs | Yes — suites green per CSV | Harness PASS per CSV | — | SCIM model w/o endpoints (gap #11) |
| 10 | LEAVE | LP-LEAVE (8) | Yes — leave.py incl. ledger/recon/payroll-input :173–270 | Yes — leave 100/0 | Harness PASS | PARTIAL: accrual automation manual-only (gap #18) | Leave-accrual job added 1b945fb (+55 tests) |
| 11 | LIFE (Lifecycle) | LP-LIFE (9) | Yes per CSV refs | Yes — suites green | Harness PASS per CSV | PARTIAL: probation/rehire/exit-interview shims (gap #15) | — |
| 12 | NOT (Notifications) | LP-NOT-002 VERIFIED; 001/003 DEFERRED | 002 yes; 001/003 no UI lane | 002 tested | 002 harness PASS | DEFERRED: 001 list, 003 create | — |
| 13 | NFR | 9 VERIFIED; 009/010/011 IN PROGRESS; 012/013 BLOCKED | Cross-cutting present | No perf/load/backup/E2E proof on HEAD | NOT verified | IN PROGRESS: perf targets PROPOSED; BLOCKED: residency/deploy matrix (gap #23, owner approval) | Backup/restore read-only theatre (gap #4) |
| 14 | PAY (Payroll) | LP-PAY-001…015 ALL BLOCKED | Code present; FY25-26 frozen, FY26-27 pending_verification | Engine math 114 passed (india_payroll) | NEVER VERIFIED — statutory sign-off outstanding; gratuity OFF | BLOCKED (statutory reviewer) | Gap #5; no activation w/o approval |
| 15 | REC (Recruitment) | LP-REC (7) | Yes; Interview entity + CRUD + 0049 added 1b945fb | Yes — 55 new tests green | Harness PASS per CSV | Prior Interview-shim gap closed | — |
| 16 | REP (Reports) | LP-REP (4) | Yes — reports.py:24–629 | Yes — suites green | Harness PASS per CSV | PARTIAL: scheduling/saved/export absent (gap #12); D-02 auth stricter-by-design (closed doc-side) | — |
| 17 | SVC (Helpdesk) | LP-SVC-001…003 CSV-DEFERRED | API create/comment added 24711ae; HR queue UI honestly denial-gated (HRHelpCases.tsx:26,65) | Cloud helpdesk 4/4 (R3, denial asserted) | Cloud R3 PASS | DEFERRED per CSV: SLA/queue/KB absent (gap #3) | sla_due stored, unenforced |
| 18 | TAL (Performance/Learning) | LP-TAL (6) | Flags/paths present | Suites green per CSV | Harness PASS per CSV | PARTIAL: cycles/360/calibration/PIP, SCORM/certs absent (gaps #19/#20) | — |
| 19 | TIME (Attendance) | 7 VERIFIED + TIME-008/009/010 IMPLEMENTED | Yes — time_attendance.py:272–413, scheduling drafts/versions | Yes — suites green | VERIFIED rows harness PASS; 008–010 IMPLEMENTED-only (no adequate verification) | PARTIAL: WorkingTimeViolation no read endpoint (gap #17); solver needs ortools | — |
| 20 | Unmapped (3 putative) | — | No CSV rows; no PRD § IDs sourced | None | NOT VERIFIED | UNSUPPORTED in this checklist — not filled, per STOP rule | Evidence gap recorded, not invented |

Cross-cutting: 18 BLOCKED + 8 CSV-DEFERRED preserved; nothing weakened; CSV statuses cross-referenced, not changed.
