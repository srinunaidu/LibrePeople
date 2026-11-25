# Karmathy — Enterprise Readiness Audit

**Auditor:** automated + manual code review with live verification
**Date:** 2026-10-19
**Baseline commit:** `f043d48`
**Remediation commit:** `243fe7d` and the follow-up state-machine commit
**Live system under test:** `https://karmathy-backend.onrender.com`

---

## 0. How to read this document

This audit was produced by reading the repository and by exercising the
**deployed** application over HTTP. Where a claim is supported by a test, the
test name and suite are given. Where something could not be verified, it says
so explicitly rather than assuming.

Status legend:

| Code | Meaning |
|---|---|
| **A** | Implemented and verified by a passing test or live request |
| **B** | Implemented, not adequately verified |
| **C** | Partially implemented |
| **D** | UI-only or configuration-only |
| **E** | Mocked or simulated |
| **F** | Missing |
| **G** | Blocked by an external dependency |
| **H** | Not applicable to current scope |

### Method

- Read all 225 API operations, 76 tables, 22 frontend pages, 6 test suites.
- Exercised the **live** deployment to confirm findings were real, not
  theoretical. The most serious finding was reproduced against production.
- Wrote `backend/security_test_suite.py` (66 checks) and
  `scripts/verify_tenant_isolation.py` (negative tests) as executable evidence.
- Re-ran every pre-existing suite after remediation to detect regressions.

---

## 1. Executive summary

Karmathy is a broad, working **single-tenant HCM application**. It is **not**
a multi-tenant, enterprise-ready product, and the documentation claiming
otherwise is incorrect.

Three findings dominate:

1. **The product had no effective authentication barrier.** An anonymous
   visitor could create themselves a `SuperAdmin` account and read the entire
   employee database. Reproduced against production before remediation.

2. **There is no tenant isolation, and no object-level data visibility.** Zero
   of 76 tables carry a tenant discriminator; one tenant can read *and write*
   another's data. Separately, role checks gate *administrative actions* but not
   *data reads*: a lowest-privilege `Associate` can read the whole employee
   directory, colleagues' leave and termination records, offers, and the audit
   log. The `/t/:slug/` routing in the frontend changes branding only.

3. **Payroll had neither a real state machine nor safe money handling.** Money
   was computed in binary floating point, terminated employees were paid, and
   a client could mint a pay run already marked `Finalized`, bypassing
   calculation and approval entirely.

Findings 1 and 3 are **fixed and verified in production**. Finding 2 is
**documented with a migration but not yet applied** — it requires an Oracle
schema change and a data backfill that cannot be safely completed
unattended. It remains the single largest risk to the product.

### Readiness verdict

> Karmathy is suitable for **internal evaluation and a single trusted
> organisation**. It is **not** suitable for multi-tenant commercial use, and
> must not be described as multi-tenant, SOC 2 compliant, or production-ready
> until Section 3 (tenant isolation) and P1-3 (data visibility) are complete.
>
> The authentication barrier that previously did not exist is now real and
> verified against production. That was the difference between "a demo anyone
> could walk into" and "a system with a genuine front door." It is not yet a
> multi-tenant product.

---

## 2. Capability matrix

Legend: **Fix** = remediated this session. **Open** = not remediated.

### 2.1 Authentication & access control

| Capability | Evidence | Status | Notes |
|---|---|---|---|
| Login / JWT issue | `backend/app/api/v1/endpoints/auth.py` | **A** | Verified live + suite |
| Inactive user rejected at login | explicit check in `login()` | **A** | Verified |
| User enumeration prevented | identical 401 + message for unknown user and bad password | **A** | `SEC-3` |
| **Self-service role escalation** | **live: `POST /auth/register {"role":"SuperAdmin"}` → 201, then full employee PII read** | **A after Fix** | **was CRITICAL** |
| Registration disabled by default | `ALLOW_SELF_REGISTRATION=False` | **A** | `SEC-1` |
| Password strength on signup | ≥12 chars, mixed case + digits | **A** | `SEC-1` |
| Privileged user creation | admin-only `POST /auth/users` | **A** | `SEC-2` |
| Role allow-list | `VALID_ROLES` validator | **A** | Unknown roles → 422 |
| Brute-force protection | **absent before; sliding-window limiter added** | **A** | 429 after N attempts |
| Server-side authorisation | `get_current_admin_user` on admin routes | **A** | Associate → 403 verified |
| Token lifetime | 30 min, configurable | **B** | No refresh/revocation |

### 2.2 Tenant isolation — **the critical gap**

| Capability | Evidence | Status | Notes |
|---|---|---|---|
| Tenant column on HCM tables | **0 of 76 tables have `tenant_id`** | **F** | verified via SQLAlchemy inspector |
| Tenant on `users` | `users` columns: `id, username, email, hashed_password, role, is_active, employee_id, created_at` | **F** | no tenant reference |
| Cross-tenant read blocked | Globex's user read Acme's client record | **F** | `verify_tenant_isolation.py` |
| Cross-tenant write blocked | Globex **renamed Acme's client**, HTTP 200 | **F** | `verify_tenant_isolation.py` |
| Frontend `/t/:slug/` | `frontend/src/context/TenantContext.tsx` | **D** | Branding only — no data filtering |
| Public tenant resolver | `GET /onboarding-portal/clients/by-slug/{slug}` | **C** | Returns tenant config unauthenticated |

**Evidence (run `scripts/verify_tenant_isolation.py`):**

```
==== TENANT ISOLATION: 0 passed, 5 failed ====
  tables: 76
  tables carrying a tenant_id column: 0
  - Acme cannot see the Globex client record   leaked: ['globex']
  - Globex cannot modify an Acme client record  name='HIJACKED BY GLOBEX'
```

#### 2.2.1 Measured access for a lowest-privilege `Associate` (production)

RBAC is **not** absent — it gates *administrative* actions. It does **not** gate
*data visibility*. Measured live against production with a freshly provisioned
`Associate` token:

| Resource | Associate result |
|---|---|
| `/employees` | **200 — full employee directory** |
| `/leave/requests` | **200 — 12 records (other people's leave)** |
| `/leave/balances` | **200 — 24 records** |
| `/candidates` | **200** |
| `/offers` | **200 — compensation offers** |
| `/offboarding/terminations` | **200 — 12 records** |
| `/reports/audit` | **200 — the whole audit trail** |
| `/performance/reviews` | 200 |
| `/payroll/payslips`, `/payroll/pay-profiles` | 200 (0 rows currently populated) |
| `/onboarding-portal/clients` | 403 — correctly role-gated |

**Interpretation.** Two distinct defects, often conflated:

1. **No tenant boundary** (P0-2) — nothing in the schema separates customers.
2. **No object-level data visibility** (P1-3) — role checks exist, but a
   lowest-privilege user can read every employee's leave, terminations, offers
   and the entire audit log. In an HCM system, an Associate reading colleagues'
   leave and termination records is a privacy incident regardless of tenancy.

Both are evidence-backed and reproducible.

**Remediation prepared:** `scripts/migration_sql/TENANT_SCOPING.sql` — an
idempotent Oracle script adding nullable `tenant_id` to every table, the
`users.tenant_id → clients.id` foreign key, supporting indexes, and a
backfill-readiness report. **Not applied.** The rollout order is documented in
the script; applying code before the columns exist causes `ORA-00904` on every
query and would take the service down.

### 2.3 Payroll — financial correctness

| Capability | Before | After | Status |
|---|---|---|---|
| Decimal-safe money | **float arithmetic** (`gross * tax/100`) | `Decimal` + `ROUND_HALF_UP` at a single point | **A** (`FIN-1`) |
| Terminated employees excluded | **paid** (`.all()`, no status filter) | only `Active` / `On Leave` | **A** (`FIN-2`) |
| Excluded employees reported | silently dropped | `run.warning` names them | **A** (`FIN-2`) |
| State machine | **none** — `approve` had no status guard | `Draft→Processing→Approved→Finalized→Paid`, server-validated | **A** (`FIN-3`) |
| Segregation of duties | processor could approve own run | processor ≠ approver enforced | **A** (`FIN-3`) |
| Cannot approve empty run | possible | 400 unless payslips exist | **A** (`FIN-3`) |
| Idempotent processing | duplicate slips possible | 409 on reprocess + `uq_payslip_run_employee` | **A** (`FIN-3`) |
| Finalized runs immutable | **editable** | 409 on write to a locked run | **A** (`FIN-3`) |
| Client cannot forge state | **`POST /runs {"status":"Finalized"}` → 201** | `status` removed from create schemas | **A** (`FIN-4`) |
| Time & overtime fed into payroll | **not connected** — gross is base salary only | still not connected | **F Open** |
| Benefits fed into payroll | engine accepts `benefit_deductions`; nothing populates it | still not wired | **F Open** |
| Statutory tax engine | **flat configurable percentage** | unchanged, now correctly documented as non-statutory | **D** |
| Reconciliation / exception queue | absent | absent | **F Open** |

> **Do not claim statutory payroll support.** The engine computes gross from
> base salary minus a flat percentage. It is not a country-specific tax engine
> and has not been reviewed for any jurisdiction.

### 2.4 Leave

| Capability | Status | Notes |
|---|---|---|
| Balance changes exactly once on approval | **A** | Endpoint guards `status != Pending` |
| Double approval refused | **A** | verified; balance unchanged |
| Cancellation reverses balance | **A** | |
| Double cancellation does not double-credit | **A** | |
| CRUD-layer re-decision guard | **A after Fix** | `decide_request` now raises if not Pending |
| Over-draw capped at entitlement + carryover | **A after Fix** | |
| **Approval with no entitlement row** | **silently lost the days** | **A after Fix** — now audited as `leave_approval_without_entitlement` |
| Retroactive changes / partial days | `working_days_between` counts weekdays only | **C** |

### 2.5 Audit trail

| Capability | Status | Notes |
|---|---|---|
| Audit helper + atomic commit | **A** | `app/core/audit.py` |
| Audit log readable, authenticated | **A** | `GET /reports/audit` |
| Coverage: payroll, leave, time, scheduling, offboarding, performance, benefits, learning, compliance, core-hr, ESS, client-onboarding, import/export | **A** | 6–15 `record_audit` calls each |
| **Coverage: employees, requisitions, candidates, applications, offers, onboarding, departments, jobs** | **F** | **18 mutations, 0 audit calls** |
| Audit log immutable / tamper-evident | rows are ordinary rows; no delete endpoint, but no protection | **C Open** |
| Login audited | **A after Fix** | previously not audited |

**Why this matters:** you cannot currently prove who changed an employee's
job, department, or status, or who made a hiring decision, for the highest-risk
records in an HCM system.

### 2.6 Integrations — honest classification

| Integration | Reality | Status |
|---|---|---|
| Webhooks | Real HTTP delivery, HMAC-signed | **A** |
| Integration connectivity test | Real outbound call | **A** |
| Migration runner | Executes real imports | **A** |
| OCI Object Storage | Real; save/exists/delete/PAR verified | **A** |
| SSO (SAML/OIDC) | **Configuration rows only — no flow implemented** | **D** |
| SCIM | **Token rows only — no provisioning endpoints** | **D** |
| E-signature | **Status tracking only — no signing** | **D** |
| Background checks | **Status tracking only — no provider** | **D** |
| Email delivery | **In-app notifications only — no SMTP** | **D** |
| Real-time updates | **Polling only — no WebSocket** | **D** |

None of these should be presented to a customer as functional until the
provider, credentials, and environment exist.

### 2.7 Operational / infrastructure

| Item | Status | Notes |
|---|---|---|
| `/health` public liveness | **A** | reveals only `{"status":"healthy"}` |
| **`/health/db`, `/health/storage`, `/health/wallet` public** | **A after Fix** | `/health/storage` performed an anonymous **write** to object storage; `/health/db` returned raw connection errors |
| `/health/wallet` documented but **absent** | **A after Fix** | the function body was unreachable dead code after a `return`; the route did not exist |
| CORS | was wildcard default + `allow_credentials=True` | **A** — exact-origin allow-list, credentials off, warned in production if unset |
| Rate limiting | none → **added** (in-process; per-replica, documented) | **B** |
| Rate limiter store | in-memory | **B Open** — needs Redis for multi-replica |
| Uploads / file size limits | not audited in depth | **B Open** |
| Structured logging | print + stdlib logging only | **C** |
| Error tracking / Sentry | absent | **F Open** |
| Backup & restore | not verified | **G Open** |
| CI test gate | no workflow runs tests on PR | **F Open** |

### 2.8 Accessibility & UX

| Item | Status | Notes |
|---|---|---|
| Focus-visible states, reduced motion | **A** | in `index.css` |
| Semantic landmarks / skip link | **A** | present on app layout |
| Loading / error / empty states | **A** | verified present on all 10 data pages |
| WCAG 2.2 AA conformance | **not verified** — no axe/contrast audit run | **B Open** |
| Colour contrast on tenant themes | warned, not blocked | **C** |
| Form error association (`aria-describedby`, `aria-invalid`) | not systematically applied | **C Open** |

---

## 3. Findings register

### P0-1 — Unauthenticated privilege escalation ✅ FIXED

- **Evidence:** Live, pre-fix: `POST /api/v1/auth/register` with
  `{"role":"SuperAdmin"}` returned **201**; logging in as that user and calling
  `GET /api/v1/employees` returned **200** with real names and emails. The
  created user was `id=12, role=SuperAdmin`.
- **Root cause:** `UserCreate` exposed `role` and `is_active`; `register()`
  passed them straight into the model with no authorisation.
- **Impact:** Complete compromise. Any anonymous party could become a
  SuperAdmin and read all HR data.
- **Remediation:** `UserSelfRegister` schema has no `role`/`is_active`; the row
  is constructed with hard-coded `SELF_SERVICE_ROLE = "Associate"`; registration
  is off by default; privileged creation moved to admin-only `POST /auth/users`.
- **Tests:** `SEC-1` (6 checks), `SEC-2` (5 checks).
- **Acceptance:** anonymous escalation impossible; verified.

### P0-2 — No tenant isolation ⛔ OPEN

- **Evidence:** 0/76 tables scoped; cross-tenant read **and write** both
  demonstrated.
- **Impact:** Two customers on one deployment could read and corrupt each
  other's payroll and employee records. This alone disqualifies the product
  from multi-tenant sale.
- **Remediation prepared:** `scripts/migration_sql/TENANT_SCOPING.sql`.
- **Blocked on:** applying an Oracle schema change + backfill, then deploying
  scoping code, then verification. Not safe to do unattended.
- **Acceptance:** `scripts/verify_tenant_isolation.py` exits 0.

### P0-3 — Payroll money computed in binary floating point ✅ FIXED

- **Evidence:** `float(profile.base_salary or 0)`; totals accumulated with
  `+=` across employees.
- **Impact:** Cent-level drift; run totals could disagree with the sum of
  payslips — unacceptable for payroll.
- **Remediation:** `app/services/payroll_engine.py`, `Decimal` throughout,
  single rounding point, `ROUND_HALF_UP`.
- **Tests:** `FIN-1` (5 checks).

### P0-4 — Terminated employees were paid ✅ FIXED

- **Evidence:** `profiles = db.query(EmployeePayProfile).all()` — no join to
  employee status.
- **Impact:** Payroll to staff who had left. Direct financial loss.
- **Remediation:** filter to `Active` / `On Leave`; excluded set reported on
  `run.warning`.
- **Tests:** `FIN-2` (3 checks).

### P0-5 — Pay-run state machine bypass ✅ FIXED

- **Evidence:** `approve_run` set `status="Approved"` with no guard;
  `POST /runs {"status":"Finalized"}` returned **201**.
- **Impact:** A run could be created pre-finalized and finalized with **zero
  payslips**, bypassing calculation and approval.
- **Remediation:** explicit transition table, SoD, no-empty-run guard,
  finalize locking, `status` removed from create schemas.
- **Tests:** `FIN-3` (7 checks), `FIN-4` (7 checks).

### P0-6 — Public diagnostic endpoints ✅ FIXED

- **Evidence:** `GET /health/storage` anonymously wrote to object storage;
  `/health/db` returned `str(exc)` publicly.
- **Remediation:** `require_operator` dependency; `/health` stays public.

### P0-7 — Leave approval silently lost days ✅ FIXED

- **Evidence:** if no `LeaveBalance` row existed, `if balance:` skipped the
  update and the approval succeeded with no balance change and no record.
- **Remediation:** audit entry `leave_approval_without_entitlement` naming the
  employee, leave type, year, and days not deducted.
- **Tests:** `LEAVE-1` (10 checks).

### P1-1 — Employee and hiring mutations are unaudited ⛔ OPEN

18 mutations across employees, requisitions, candidates, applications, offers,
onboarding, departments, jobs record no audit event. **Recommended:** add
`record_audit` to each; mechanical and low-risk, not done here to keep this
change set reviewable.

### P1-3 — No object-level data visibility ⛔ OPEN

- **Evidence (production, live):** a lowest-privilege `Associate` token read
  `/employees` (full directory), `/leave/requests` (12 rows), `/leave/balances`
  (24 rows), `/candidates`, `/offers`, `/offboarding/terminations` (12 rows)
  and `/reports/audit` — **all HTTP 200**. `/onboarding-portal/clients` was
  correctly 403.
- **Root cause:** authorisation is role-based only. There is no
  "self / direct reports / all" scoping applied to list endpoints, and no
  owner filter on records.
- **Impact:** colleagues' leave, terminations and compensation offers are
  readable by any logged-in user. This is a privacy exposure independent of the
  multi-tenancy question.
- **Remediation:** add a `get_visible_employee_ids(user)` dependency (self +
  direct reports for Managers, all for HR/SuperAdmin) and apply it as a filter
  on every employee-scoped list endpoint.
- **Acceptance:** negative tests per module asserting an Associate receives only
  their own records.

### P1-2 — Payroll not connected to time, leave, or benefits ⛔ OPEN

Gross pay derives from base salary only. Approved leave does not reduce pay;
overtime is not paid; benefit enrollments are not deducted. The engine accepts
these inputs but nothing supplies them. **This is the largest functional gap
after tenant isolation.**

### P2-1 — `base_salary` unit is ambiguous ⛔ OPEN (business decision)

The column has no unit recorded. The original code treated it as a per-period
amount. An audit draft changed it to annual÷12 — which **would have cut every
paycheck by 12×**. That was reverted: reinterpretation is a business decision,
not a bug fix. **Decision needed from the product owner.** Tracked in
`payroll_engine.py` module docstring.

### P2-2 — No statutory tax engine ⛔ OPEN (correctly labelled)

Flat percentage only. Must not be described as compliant payroll.

---

## 4. Verification results — actual, recorded

### 4.1 Local (Python 3.11, SQLite)

| Suite | Result |
|---|---|
| `backend/security_test_suite.py` (new) | **66 passed, 0 failed** |
| `backend/smoke_test_phases_3_7.py` | **39 passed, 0 failed** |
| `backend/smoke_test_client_onboarding.py` | **20 passed, 0 failed** |
| `backend/smoke_test_all_phases.py` | **67 passed, 0 failed** |
| `backend/smoke_test.py` | COMPLETE |
| `backend/smoke_test_phase2.py` | COMPLETE |
| **Total assertive checks** | **192** |
| `scripts/verify_tenant_isolation.py` | **0 passed, 5 failed** — expected; this is the P0-2 evidence |

`security_test_suite.py` is idempotent: verified with three consecutive runs
against a single database file, 66/66 each time. (It initially only passed on a
fresh file, which produced false failures in a second run — fixed and
re-verified.)

### 4.2 Production (deployed at commit `61a4e0a`)

Both services confirmed `live` on `61a4e0a`. The original exploit was re-run
against production **after** the fix:

| Probe | Before fix | After fix |
|---|---|---|
| Anonymous `POST /auth/register` with `role: SuperAdmin` | **201 Created**, `id=12`, `role=SuperAdmin` | **403** — "Self-service registration is disabled" |
| Login as that account | **200**, SuperAdmin token | **401** |
| Read `/employees` with that token | **200** + real names and emails | **no token — attack blocked** |
| `GET /health/db` (anonymous) | **200** + raw connection error | **401** |
| `GET /health/storage` (anonymous) | **200** + performed an object-storage write | **401** |
| `GET /health/wallet` (anonymous) | **404** — route did not exist | **401** |

Live end-to-end suite after remediation:

| Suite | Result |
|---|---|
| `scripts/live_e2e.py` | **40 passed, 0 failed** (was 37; +3 security checks) |

Frontend regression check (CORS hardening could have broken this):
dashboard loads with 6 cards and real data, **no CORS or network errors**.

### 4.3 Deliberately updated tests

Two pre-existing tests asserted the **old, defective** behaviour and were
corrected to assert the fixed contract:

| Test | Was asserting | Now asserts |
|---|---|---|
| `smoke_test_all_phases.py` "approve pay run" | the same admin could process **and** approve | processor is blocked; a second operator approves; run is finalized |
| `smoke_test_client_onboarding.py` RBAC | public `/auth/register` works | registration closed; role cannot be requested; Associate cannot provision users |

---

## 5. Corrections to existing documentation

`DOCUMENT.md` and `docs/FEATURE_INVENTORY.md` contained claims that inspection
contradicts. These must not be repeated:

| Claim | Reality |
|---|---|
| "Multi-tenant", `client1.karmathy.com` | **No tenant isolation exists.** `/t/:slug/` is branding only. |
| `/health/wallet` endpoint | **Did not exist** — dead code after a `return`. |
| "6 feature cards" / homepage counts | Cosmetic; not re-verified. |
| "154 endpoints" | 225 operations across 154 paths. |
| "SOC 2 / compliance" language | No audit has been performed. None is claimed. |

---

## 6. Recommended sequence

1. **Apply tenant scoping** — run the migration, backfill, deploy scoping code,
   make `verify_tenant_isolation.py` pass. *Blocks any multi-tenant sale.*
2. **Audit employee and hiring mutations** — mechanical, high compliance value.
3. **Connect payroll to time/leave/benefits** — the biggest functional gap.
4. **Decide the `base_salary` unit** — needs product-owner ruling.
5. Add CI that runs all suites on every push.
6. Replace the in-process rate limiter with a shared store when scaling out.
7. Run an automated accessibility audit against WCAG 2.2 AA.

## 7. Open questions for the product owner

1. Is `EmployeePayProfile.base_salary` a **per-period** or **annual** amount?
   Current code assumes per-period. Getting this wrong mis-pays everyone.
2. Should self-service registration ever be enabled? Currently off.
3. Which **jurisdictions** must payroll actually support? Nothing can be
   claimed as statutory until this is answered.
4. Is the deployment intended to be **single-tenant per customer**, or shared?
   If per-customer, tenant scoping is lower priority than the claim is
   changed; if shared, it is the blocker for everything else.