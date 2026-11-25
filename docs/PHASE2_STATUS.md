# Karmathy — Phase 2 Status Register

**Date:** 2026-10-19
**Session commits:** `b8183e6` … `2b75113`
**Deployed at:** `2b75113` (backend + frontend both `live`)
**Baseline verified against:** previous-phase audit `docs/ENTERPRISE_AUDIT.md`

---

## 1. Previous-phase verification

I re-inspected the source rather than trusting the previous phase's own
conclusions. Results:

| Previous claim | Verified? | Evidence |
|---|---|---|
| Unauthenticated privilege escalation closed | **Yes** | live re-probe: `POST /auth/register` → **403** |
| Payroll money is Decimal | **Yes** | `payroll_engine.py`, 21 `Decimal` references |
| Terminated employees excluded from payroll | **Yes** | `FIN-2` suite |
| Pay-run state machine enforced | **Yes** | `FIN-3`/`FIN-4` suites |
| Diagnostics require auth | **Yes** | live: all three → **401** |
| Rate limiting present | **Yes, with a caveat** | in-process only; breaks across replicas |
| 192 local checks passing | **Yes** | reproduced |
| **Tenant isolation** | **NO — still 0/76 tables** | `verify_tenant_isolation.py`: 0 passed, 5 failed |
| **Object-level data visibility** | **NO — was absent** | Associate read everything (below) |
| **Employee/hiring mutations audited** | **NO — 18 unaudited** | now closed |
| Payroll connected to time/leave/benefits | **NO — still absent** | gross = base salary only |

Also newly discovered this session (not in the previous audit):

- An **expired or invalid token returned 403**, so clients treated a lapsed
  session as "forbidden" rather than "sign in again". Now **401 + WWW-Authenticate**.
- `Query.with_columns` (used in the new metrics code) was **removed in
  SQLAlchemy 2.0** and 500s. Caught by the suite before it shipped.
- The metrics permission check originally matched the *substring*
  `"PayrollViewer"` instead of the caller's role, which would have granted an
  Associate access to compensation data.

---

## 2. Status register

### Completed and verified

| Item | Verification |
|---|---|
| Object-level data visibility (P1-3) | 29 checks, 3-level reporting chain, fail-closed orphan; **confirmed live** (Associate 0 rows vs Admin 12/12/13) |
| Audit coverage (P1-1) | 0 endpoint files with mutations lack `record_audit` |
| Correlation IDs | live: inbound `X-Request-ID` echoed |
| Structured logs + redaction | JSON format, recursive scrub of 25 sensitive key names |
| Error classification | 9 categories → envelope `{code, category, message, retryable, details, request_id}` |
| Dependency-failure handling | 503 + `Retry-After`; raw exception text never returned |
| Idempotency | DB-backed; employee create + payroll process |
| Concurrency control | stale write → 409 with a "reload" instruction |
| Import validation | 43 checks: dry run, duplicates, types, references, per-batch savepoint |
| Data-quality engine | 44 checks, 13 registered rules, read-only |
| Metric catalogue | 41 checks, 12 metrics, 3 reconciliation defects fixed |
| Live E2E | **40/40** against production |

### Implemented but not verified

| Item | Why |
|---|---|
| Tenant-scoping migration SQL | Written and reviewed; **never executed against Oracle** |
| Per-metric `withheld` list | Tested locally; low traffic so far in production |
| Idempotency replay on import | Tested locally; not exercised in production traffic |

### Incomplete

| Item | Status |
|---|---|
| **P0-2 tenant isolation** | Migration prepared, rollout documented, **not applied** |
| **P1-2 payroll ↔ time/leave/benefits** | Engine accepts the inputs; **nothing populates them** |
| Phase 3 workflow orchestration | Not started — approval chains, delegation, escalation |
| Phase 4 onboarding journey | Existing portal unchanged; no readiness gates |
| Phase 8 integrations | Unchanged; SSO/SCIM/e-sign/background-check still configuration-only |
| Phase 11 performance | No latency or query measurement taken |
| Phase 12 design/UX | Unchanged |

### Blocked

| Item | Blocker | Needs |
|---|---|---|
| P0-2 tenant isolation | Oracle DDL on production not authorised. Adding columns untested against the live ADB could take the service down (`ORA-00904` if code lands before columns). Backfill also needs a **business decision** on which client owns existing rows. | Explicit authorisation + owner mapping |
| `base_salary` unit | Genuinely ambiguous. Original code treats it as per-period. Reading it as annual÷12 would **cut every paycheck 12×**. | Product-owner ruling |
| Statutory payroll | No jurisdiction defined, no validated rules, no provider. | Business decision |
| Rate limiter durability | In-process only; a second replica doubles the effective limit. | Redis or equivalent — only worth it when scaling out |
| Backup/restore | Oracle ADB backups exist platform-side; **restore has not been tested**. | A restore rehearsal |

### Regressed

None. All 11 suites were re-run after each change; no previously passing check
began failing. Two suites were **deliberately updated** because they asserted
old defective behaviour (payroll segregation of duties; public registration),
and that is recorded in `docs/ENTERPRISE_AUDIT.md`.

One genuine incident: the first production deploy of the operating-model
changes **failed (`update_failed`)**. Render auto-rolled back to the previous
commit — no outage, no data loss. Root cause was `autoincrement=True` on an
`Integer` primary key, which raises `ORA-01408` on Oracle; every other model in
this codebase already uses `Identity()`. Fixed, redeployed, live.

---

## 3. Test results — actual, this session

Local, Python 3.11, SQLite:

| Suite | Result |
|---|---|
| `security_test_suite.py` | 66 passed, 0 failed |
| `visibility_test_suite.py` | 29 passed, 0 failed |
| `ops_model_test_suite.py` | 38 passed, 0 failed |
| `import_test_suite.py` | 43 passed, 0 failed |
| `data_quality_test_suite.py` | 44 passed, 0 failed |
| `metrics_test_suite.py` | 41 passed, 0 failed |
| `smoke_test_phases_3_7.py` | 39 passed, 0 failed |
| `smoke_test_client_onboarding.py` | 20 passed, 0 failed |
| `smoke_test_all_phases.py` | 67 passed, 0 failed |
| `smoke_test.py`, `smoke_test_phase2.py` | COMPLETE |
| **Total** | **387** |
| `scripts/verify_tenant_isolation.py` | **0 passed, 5 failed** — expected; this is the P0-2 evidence |

Production, commit `2b75113`:

| Probe | Result |
|---|---|
| `POST /auth/register` anonymous | **403** |
| Invalid bearer token | **401 + `WWW-Authenticate: Bearer`** |
| `/health/db`, `/health/storage`, `/health/wallet` anonymous | **401** each |
| Inbound `X-Request-ID` | echoed unchanged |
| Error envelope shape | `{error:{code,category,message,retryable,request_id}}` |
| Data-quality rules registered | 13 |
| Metrics returned in summary | 8, `withheld: []` for admin |
| Associate: employees / leave / terminations | **0 / 0 / 0 rows** |
| Admin: employees / leave / terminations | **13 / 12 / 12 rows** |
| Associate: audit, labour cost, candidates | **403** each |
| `scripts/live_e2e.py` | **40 passed, 0 failed** |
| Frontend dashboard | 6 cards, real data, no CORS/network errors |
| `npm run build` + `tsc --noEmit` | clean |

---

## 4. Recommendations for the next phase

Ordered by risk, not by effort.

1. **Decide `base_salary` semantics.** Everything downstream of payroll
   depends on it and the current answer may be wrong.
2. **Authorise and stage the tenant migration.** It is the only P0 left. Run
   the DDL in a maintenance window, backfill, then deploy scoping code.
3. **Connect payroll to time, leave and benefits** (P1-2). Payroll currently
   ignores approved leave, overtime and benefit deductions. This is the largest
   functional gap and affects real money.
4. **Build the onboarding readiness gate.** Activation should refuse to
   complete while security or configuration prerequisites are unmet.
5. **Measure performance before optimising** (Phase 11). No latency baseline
   exists, so any optimisation is currently guesswork.
6. **Add CI that runs all 11 suites on every push.** Two real defects this
   session reached the deploy stage; a gate would have caught both earlier.
7. **Decide the deployment model** (single-tenant per customer vs shared).
   This determines whether tenant isolation is urgent or the marketing claim
   should change.