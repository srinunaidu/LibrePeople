# Production Readiness Tracker

- HEAD: ab9b392 (`feature/librepeople-production`)
- Branch: feature/librepeople-production
- Status: NOT READY (payroll pending + BLOCKED > 0)
- Live CSV: 122 VERIFIED / 0 IMPLEMENTED / 3 BLOCKED / 8 DEFERRED / 3 IN PROGRESS (136 data rows)
- Source: `docs/product/requirements-traceability.csv`, field `Implementation status`
- Verification: `python3 -c` with `csv.DictReader` counter on field 4
  (naive `awk -F,`/grep overcounts: status tokens also appear inside
  Blocker/evidence prose, e.g. "No VERIFIED per contract", and embedded
  commas break field splitting — authoritative count is the DictReader one above)
- Blockers (3): LP-DOC-003 + LP-NFR-012 + LP-NFR-013 (see blocker-register.md)
- In progress (3): LP-NFR-009 + LP-NFR-010 + LP-NFR-011
- Deferred (8): LP-EXP-001..003, LP-NOT-001, LP-NOT-003, LP-SVC-001..003
  (DEFERRED BY APPROVAL; remainder of the 14-ID surplus stays VERIFIED-but-gated)
- Payroll gate: PAY rows read VERIFIED in CSV but contract forbids VERIFIED —
  FY25-26 pack verified, FY26-27 skeleton `pending_verification`, §29
  payroll/compliance verifier sign-off outstanding → Status stays NOT READY.
- Evidence NFR-014: PASS — harness full pass at HEAD 65a1af2
  (integrity 62/0 + migration 67/0 + cross_tenant 31/0 + security 2078/0 +
  lp_phase2_access 86/0 + frontend route/api-path checks; promoted
  IMPLEMENTED → VERIFIED in 2ac4050; 0043 safe C2,C4-C9,C11-C13 + quarantine,
  C1/C3/C10 deferred application-checked).
- Hardenings since 2ac4050 (4): b4cf23f SuperAdmin write gate
  (every PATCH on SuperAdmin target gated + last-active-SuperAdmin guard);
  2e3c001 remove hardcoded bootstrap credentials (env-gated single seed);
  4742091 impersonate step-up (password-or-TOTP on POST /auth/impersonate);
  fdc5419 Admin MFA reset (SuperAdmin-only, password+TOTP step-up, no self-reset).
- Throttling: 19706bd step-up rate limiting on impersonate + admin MFA reset
  (login IP budget pre-step-up; 403 step_up_required feeds 5-in-900s lockout).
- SBOM: 969d403 WS1 inventory (backend/frontend direct+transitive, copyleft
  notes, provenance) + 59c3823 machine-readable transitive SBOM JSON + manifest
  (`docs/licensing/sbom/`).
- Runbook: 0b8a402 bootstrap rotation remediation
  (`docs/runbooks/bootstrap-rotation-remediation.md`).
- Closure: ab9b392 decision papers DOC-003/NFR-012/NFR-013
  (recommendations only, no approval claimed) + closure evidence index
  (`docs/release/closure-evidence-index.json`: 122 VERIFIED→evidence+head_sha,
  14 non-VERIFIED→register entries, workstreams A–F→status/evidence).
- Perf: b46d24b synthetic 10-employee SQLite smoke baseline
  (`docs/performance/synthetic-10emp.md`) — PROPOSED targets only, not acceptance.
