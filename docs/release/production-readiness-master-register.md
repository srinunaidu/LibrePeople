# Production Readiness Master Register (§14 gates)

- HEAD: `4cc8be1` (merge agent/backend/rebrand-extract), branch `agent/ops/compliance-package` (base `4cc8be1`).
- Status roll-up: **NOT READY** — payroll/compliance verifier sign-off outstanding; docker/PG/browsers absent so several gates are NOT TESTED.
- Rule: a gate marked BLOCKED or NOT TESTED is never upgraded. Only the validator may change status.
- Standing evidence (this programme, carried, not re-run here): suites **2162 / 37 / 30 / 29 / 251 / 80**, verify **EXIT 0**, secret scan **clean**, sqlite round-trip **exit 0**; **docker / PostgreSQL / browsers absent** in this environment.

| §14 gate | Owner | Evidence (commit / SHA / counts) | Acceptance criteria | Status | Next action |
|---|---|---|---|---|---|
| Security | Team B (Security) | Secret scan clean; hardening commits b4cf23f, 2e3c001, 4742091, fdc5419, 19706bd; security suite 2162-subset per programme | Scan clean + security suite green, no hardcoded creds | PASS (sqlite/local scope) | Re-run on PG-backed deploy env |
| PostgreSQL | Team D (Database) | Migration chain merged (7b6c5c4); sqlite round-trip exit 0; **PG absent — never run on PG** | Migrations apply clean on PG 15+, round-trip exit 0 | NOT TESTED | Run migration + round-trip against PG |
| Deployment | Team E (Deploy/Ops) | Standalone-ops merged (daddd21); **docker absent — image build not run here** | Docker build + standalone boot green | NOT TESTED | Build image, boot standalone, record SHA |
| Browser E2E | Team C (Frontend/QA) | Rebrand-ux merged (fef05f4); **browsers absent** | E2E pass on Chrome/Firefox matrices | NOT TESTED | Run deployment-browser-matrix.md suites |
| Backup / restore | Team E (Deploy/Ops) | sqlite round-trip exit 0 (local only) | Documented backup + tested restore | NOT TESTED | PG backup/restore drill, record evidence |
| Performance | Team E (Perf) | b46d24b synthetic 10-employee SQLite smoke (`docs/performance/synthetic-10emp.md`, PROPOSED targets only) | Agreed targets met on prod-like data | NOT TESTED | Set targets, run on PG, record numbers |
| Payroll | Team F (Payroll/compliance) | FY25-26 pack v1.0.0 `verified`; FY26-27 skeleton v0.1.0 `pending_verification`, engine refuses ≥2026-04-01 (`rule_pack_not_verified`); §29 verifier sign-off outstanding | Named-human verification + gate suites green | BLOCKED | Verifier transcribes FY26-27 instruments, fills 5 fields, flips status |
| Licensing | Team F (Payroll/licensing prep) | SBOM WS1 (969d403) + transitive JSON + manifest (`docs/licensing/sbom/`, head 969d403); `docs/release/legal-clearance-checklist.md` (this package, no clearance claimed) | Owner/counsel clearance recorded | BLOCKED | Owner review of legal-clearance-checklist |
| Documentation | Team A (Docs) | Decision papers DOC-003/NFR-012/NFR-013 (ab9b392, recommendations only); closure index `docs/release/closure-evidence-index.json` | All §14 gates evidenced, no invented values | IN PROGRESS | Complete this register + reviewer package review |
| Product functionality | QA / Validator | Tracker `docs/release/production-readiness-tracker.md`: 122 VERIFIED / 3 BLOCKED / 8 DEFERRED / 3 IN PROGRESS (136 rows, DictReader count); blockers LP-DOC-003, LP-NFR-012, LP-NFR-013 | 0 BLOCKED, IN PROGRESS closed or ticketed, payroll gate cleared | FAIL (BLOCKED > 0) | Clear blockers, re-verify CSV count |

No statutory activation, no licence publication, no ownership claims made by this package.
