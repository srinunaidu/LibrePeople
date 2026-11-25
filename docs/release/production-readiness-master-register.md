# Production Readiness Master Register (§14 gates)

- HEAD: `cdd93f8` (merge agent/ops/pg-proof), branch `main` (base `5289fb6`).
- Status roll-up: **NOT READY** — payroll/compliance verifier sign-off outstanding; docker/PG/browsers absent so several gates are NOT TESTED.
- Rule: a gate marked BLOCKED or NOT TESTED is never upgraded. Only the validator may change status.
- Standing evidence (this programme, carried, not re-run here): suites **2162 / 37 / 30 / 29 / 251 / 80**, verify **EXIT 0**, secret scan **clean**, sqlite round-trip **exit 0**; **docker / PostgreSQL / browsers absent** in this environment.

| §14 gate | Owner | Evidence (commit / SHA / counts) | Acceptance criteria | Status | Next action |
|---|---|---|---|---|---|
| Security | Team B (Security) | Secret scan clean; hardening commits b4cf23f, 2e3c001, 4742091, fdc5419, 19706bd; security suite 2162-subset per programme; CORS fail-closed + D1 detector (0b92fd5, already on main) | Scan clean + security suite green, no hardcoded creds | PASS (sqlite/local scope) | Re-run on PG-backed deploy env |
| PostgreSQL | Team D (Database) | Scratch PG 16.16 clean-install + full chain to 0047 + seed/login + rollback exit 0; evidence `docs/release/pg-proof-report.md` (merge cdd93f8) | Migrations apply clean on PG 15+, round-trip exit 0 | PASS (scratch scope) | Prod-volume/TLS/multi-instance hardening |
| Deployment | Team E (Deploy/Ops) | Standalone-ops merged (daddd21); **docker absent — image build not run here** | Docker build + standalone boot green | NOT TESTED | Build image, boot standalone, record SHA |
| Browser E2E | Team C (Frontend/QA) | Rebrand-ux merged (fef05f4); **browsers absent** | E2E pass on Chrome/Firefox matrices | NOT TESTED | Run deployment-browser-matrix.md suites |
| Backup / restore | Team E (Deploy/Ops) | Scratch scope: pg_dump 0.49s + restore 0.62s + count match (110 tables, 5 rows, version 0047); RPO/RTO remain PROPOSED, not commitments; evidence `docs/release/pg-proof-report.md` | Documented backup + tested restore | PASS (scratch scope) | PG backup/restore drill, record evidence |
| Performance | Team E (Perf) | b46d24b synthetic 10-employee SQLite smoke (`docs/performance/synthetic-10emp.md`, PROPOSED targets only) | Agreed targets met on prod-like data | NOT TESTED | Set targets, run on PG, record numbers |
| Payroll | Team F (Payroll/compliance) | FY25-26 pack v1.0.0 `verified`; FY26-27 skeleton v0.1.0 `pending_verification`, engine refuses ≥2026-04-01 (`rule_pack_not_verified`); §29 verifier sign-off outstanding | Named-human verification + gate suites green | BLOCKED | Verifier transcribes FY26-27 instruments, fills 5 fields, flips status |
| Licensing | Team F (Payroll/licensing prep) | SBOM WS1 (969d403) + transitive JSON + manifest (`docs/licensing/sbom/`, head 969d403); `docs/release/legal-clearance-checklist.md` (this package, no clearance claimed) | Owner/counsel clearance recorded | BLOCKED | Owner review of legal-clearance-checklist |
| Documentation | Team A (Docs) | Decision papers DOC-003/NFR-012/NFR-013 (ab9b392, recommendations only); closure index `docs/release/closure-evidence-index.json` | All §14 gates evidenced, no invented values | IN PROGRESS | Complete this register + reviewer package review |
| Product functionality | QA / Validator | Tracker `docs/release/production-readiness-tracker.md`: 122 VERIFIED / 3 BLOCKED / 8 DEFERRED / 3 IN PROGRESS (136 rows, DictReader count); blockers LP-DOC-003, LP-NFR-012, LP-NFR-013 | 0 BLOCKED, IN PROGRESS closed or ticketed, payroll gate cleared | FAIL (BLOCKED > 0) | Clear blockers, re-verify CSV count |

No statutory activation, no licence publication, no ownership claims made by this package.
