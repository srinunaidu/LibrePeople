# Karmathy HCM — Iteration Log

| Iteration | Branch | Commit | Date | Summary |
|---|---|---|---|---|
| 0 | main | 5f7db13 | 2026-10-20 | Baseline: FEATURE_MATRIX.md, SEED_DATA.md, seed/dev/ generator, Makefile |
| 1 | main | c3680dc | 2026-10-20 | Security headers (P-07): SecurityHeadersMiddleware + test suite |
| 2 | iter/2-mfa | f551cbc | 2026-10-20 | MFA (P-05): TOTP enrollment/confirm/disable, recovery codes, require_mfa dependency, migration 0003 |
| 3 | iter/3-visibility | dbc27cc | 2026-10-20 | Visibility + ownership checks (A-01/A-02/A-04): 10 endpoint files scoped with apply_visibility/ensure_can_view_employee |
| 4 | iter/4-job-queue | 56bb4a2 | 2026-10-20 | Job queue (J-04/J-05/J-06/J-07): JobQueue model, queue service with leases/retry/dead-letter, rule registry with 8 handlers, migration 0004 |
| 5 | iter/5-csv-import | 25eea34 | 2026-10-20 | CSV import engine (I-01 through I-07): header aliasing, formula-injection neutralisation, dry-run/commit with confirmation token, row-error CSV, idempotent upsert |
| 6 | iter/6-frontend | 7fb2331 | 2026-10-20 | Frontend UI for Import, MFA, and Jobs pages (P-05, J-04/J-05/J-06/J-07, I-01 through I-07): role-gated routes at /import, /mfa, /jobs; typecheck and build pass |
| 7 | agent/qa-validation/QA-01-twelve-journeys | (this branch) | 2026-10-22 | The import journey (`IM-06`, `IM-07`): a CSV is previewed, committed, and the **table** — not the response — is asked what happened; the audit row is held against the change in the table; a re-import changes nothing. The production guard (`frontend/e2e/support/environment.ts`, run by the global setup) refuses a run pointed at production. `scripts/staging/gate.sh`: the whole gate in one command. **11 journeys pass on staging against real Oracle**; the payroll-refusal journey waits for `PR-01`. The J1–J14 coverage, with the gaps named and owned, is in `docs/validation/JOURNEYS.md` |

Matrix counts after iteration 6: 20 VERIFIED, 48 PARTIAL, 73 MISSING, 4 BLOCKED (rule pack), 145 total.

Deployment note: Backend deploy to Render is failing repeatedly (update_failed status) after multiple attempts. Backend code is verified working locally with all 14 test suites passing (469 checks). Frontend typechecks and builds successfully. The backend Docker image builds but the container fails during startup on Render — likely a runtime configuration issue with the production environment.