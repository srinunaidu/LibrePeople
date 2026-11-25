# Gate 0 — Coordinator Decisions and Delivery Plan

**Status:** approved
**Date:** 2026-10-19
**Coordinator:** Karmathy build coordinator
**Build brief:** *Karmathy HCM: Multi-Agent Build Brief* (section 0)

This is the coordinator's record of Gate 0. It contains the decisions that
unblock feature work, the plan those decisions imply, and the reason each
decision was taken. Nothing here changes the build brief; it records how the
brief is being applied to the capacity and the codebase that actually exist.

---

## 1. Gate 0A — Decisions

### 1.1 Database model per customer

**Decision: one Oracle Autonomous Database, one Oracle schema per customer.**

Each customer is a separate deployment (unchanged from the owner's earlier
decision) and, within a shared ADB instance, a separate Oracle *schema*. A
schema is an Oracle user with its own tables, so a customer's data is
physically separated from another customer's without needing a second
database.

Why this and not a database per customer:

| | Separate schema | Separate database |
|---|---|---|
| Customers on the free tier | unlimited | **2** |
| Isolation | table-level, enforced by the schema owner | instance-level |
| Migrations | schema-qualified | instance-qualified |
| Extra capacity available | the second free database, as headroom for staging or a noisy tenant | none |

The free tier allows two databases. A database-per-customer model would cap
the product at two customers with no room for a staging copy. A schema
per customer leaves the second database free and keeps the isolation
property that matters.

**Consequence:** the application must be able to point at a different schema
per deployment. That is a configuration concern (`DB_SCHEMA`), not a code
concern, because a deployment serves exactly one customer. Cross-tenant
queries remain impossible by construction: there is no tenant dimension in
any query, because there is only ever one tenant in the database.

**Change request raised:** the connection handling currently assumes the
default schema. Schema qualification in the migration runner is **Block 3**
work. Nothing in Block 1 or 2 depends on it.

### 1.2 Weekly engineering hours per agent lane

**Decision: one engineer, 20–40 h/week, executed as a single lane.**

This is the owner's recorded capacity. The brief's three-lane structure is
retained in the *plan* (the same concerns are addressed in the same order)
but not in the *execution*: parallel agents writing to one repository with
one reviewer produce merge conflicts and duplicated review effort, and the
brief's own review checklist requires a second reviewer per merge.

**Consequence:** the brief's 7-week schedule is not achievable and is not
the plan. The sequencing in section 3 below is the plan.

### 1.3 Launch business presets

**Decision: `retail`, `construction`, `hospitality`, `healthcare_clinic`,
`light_manufacturing`, `generic_office`.** As specified in the brief.

Presets are jurisdiction-agnostic. Any field that could only be filled from
a jurisdiction rule pack carries the sentinel `REQUIRES_RULE_PACK` and
blocks payroll enablement until a verified pack is attached. The schema that
enforces this is `contracts/rules/preset.schema.json`.

### 1.4 First launch jurisdiction for payroll rule packs

**Decision: India. Payroll ships disabled until a rule pack is verified by a
named human.**

No statutory value is written into the codebase or into any pack from
memory. The rule-pack *format* is implemented and validated
(`contracts/rules/rule-pack.schema.json`), and the loader, the verification
workflow and the blocked-jurisdiction behaviour are implemented. What is
**not** done is the population of an India pack with tax rates, social
security contributions, statutory leave entitlements or minimum wage.

The brief permits exactly this at section 8: *"The payroll rule packs for
the pilot jurisdiction are verified and signed off by a named professional,
or payroll is disabled for the pilot."*

**What is needed to enable payroll for the pilot:** a named verifier, the
source document for each rule (the Act, Rule, or notification it comes
from), and the effective dates. A pack cannot leave `draft` without a
`source` block, a `verification` block naming the verifier, and at least one
golden case. Those constraints are enforced by the schema, not by policy.

**Consequence:** the payroll module ships with a "requires configuration"
state and the admin compliance view shows every payroll row as *requires
verification*. It never shows as passing.

### 1.5 External LLM in the configuration assistant

**Decision: no. The default build has no LLM call at all.**

The configuration assistant is a rule engine over tenant configuration. Each
rule has an ID, a condition, a plain-language message, a severity and a fix
target, and every rule has a positive and a negative test. A curated help
index provides fixed answers.

If LLM mode is ever approved it receives configuration metadata only — never
employee rows — and is behind a feature flag that is off by default.

### 1.6 ML libraries for forecasting

**Decision: statistical methods only.** `statsmodels` for Holt-Winters
exponential smoothing, `ortools` (CP-SAT) for the roster solver, and
`numpy`/`pandas` for the data handling. No gradient-boosted or neural
models.

The brief's default is followed. This is also the right call for the
deployment: a trained model is a trained model that has to be versioned,
retrained and explained, and none of that is affordable here.

### 1.7 Default admin credential — rotated

**Decision: rotated, and the rotation is enforced by the code, not by a
convention.**

The credential that shipped in `backend/scripts/seed_admin.py` and was
repeated in `README.md` and `docs/DEPLOYMENT.md` was still authenticating
against the live production backend as SuperAdmin when Gate 0 opened. It
has been rotated. See `REVAMP_NOTES.md` for the outcome of the review of the
sessions that used it.

Four changes make it impossible to repeat:

1. **No default password exists anywhere.** The seed script reads
   `ADMIN_INITIAL_PASSWORD` from the environment and refuses to run without
   it. It never prints a password.
2. **Forced password change.** A seeded or administrator-set account carries
   `must_change_password` and can do exactly three things: read its own
   profile, change its password, and sign out. The gate is in
   `get_current_active_user`, which every protected endpoint depends on, so a
   new endpoint cannot forget it.
3. **A secret scan in CI.** `ci/secret_scan.py` fails the build on the
   published credential, on private keys, on known token formats, and on
   high-entropy values assigned to secret-looking names. The published
   credential is in the denylist specifically so that reintroducing it fails.
4. **The credential is not in the documentation.** The seed instructions now
   show how to generate one.

---

## 2. Gate 0B — Contracts

Approved and in the repository:

| Contract | Path | What it is |
|---|---|---|
| Error envelope and code list | `contracts/errors.md` | One envelope shape, nine categories, a named code for every failure the API can return. |
| Rule schemas | `contracts/rules/preset.schema.json`, `contracts/rules/rule-pack.schema.json` | JSON Schema 2020-12 for presets and jurisdiction rule packs. Enforces the `REQUIRES_RULE_PACK` sentinel and the verification preconditions. |
| Domain events | `contracts/events/{shifts,payroll_runs,imports,jobs}.yaml` | 19 events with a shared envelope. |
| OpenAPI fragments | `contracts/openapi/*.yaml` | 80 paths, 92 operations across 10 domains, merged to `contracts/openapi/openapi.yaml`. |
| Contract guide | `contracts/README.md` | How to add a fragment, a domain or an error code, and who may change what. |

**The drift rule.** The application's generated OpenAPI is the authority for
what the code does *today*; the merged contract is the authority for what the
code *promises*. A promised endpoint the application does not serve is a
**hard CI failure**. An endpoint the application serves that the contract
does not declare is reported for coordinator triage, not a failure — because
failing on it would block every incremental change.

An operation is marked `x-lifecycle: released` when the contract promises
it, and `x-lifecycle: planned` when it is declared but not yet built.
Promotion from `planned` to `released` is the act of making the promise.

**Change-request rule.** No lane changes another lane's contract without a
written change request to the coordinator and the owning lane. In practice
there is one lane, so this means: a change to `contracts/errors.md` that
would alter a published code's meaning is a breaking change and needs a
coordinator note in the commit.

---

## 3. The plan

### 3.1 What the brief costs

The brief's three lanes cost, against this codebase and this team:

| Lane | Scope | Estimate (engineer-weeks) |
|---|---|---|
| Agent 1 | Platform, security, data, onboarding, imports, jobs, audit, retention | 30–45 |
| Agent 2 | Employees, time, leave, scheduling, forecasting, payroll, rule packs, reports | 35–55 |
| Agent 3 | Design system, monorepo, app shell, role homes, all module UI, 12 E2E journeys, a11y, load, marketing site | 30–50 |
| **Total** | | **95–150** |

At 20–40 h/week (2.9–5.8 engineer-weeks per month) that is **16–52 months
solo**, or **54–86 engineers** for the brief's 7 weeks. Neither is available.
The brief's schedule is therefore replaced by the sequence below, which
delivers the same intent in the same order, at a rate the team can sustain,
with every step leaving the system in a shippable state.

### 3.2 The sequence

Effort in engineer-weeks at 30 productive hours each. **Cumulative** is the
point at which the pilot gate can be assessed.

| Block | Scope | Effort | Cumulative | Gate |
|---|---|---|---|---|
| **0** | Gate 0 decisions, contracts, credential rotation, Alembic baseline, CI gate | **done** | 0 | Credential rotated; CI green |
| **1** | Security foundation: password policy, MFA, refresh rotation, lockout, field encryption with key versions; central policy module; visibility applied to every read; ownership checks on every write; real `Manager` and `PayrollViewer` roles | 4–6 | 4–6 | Negative tests for every module |
| **2** | Data layer: index every foreign key and filter column; paginate every list; transaction boundaries; idempotency keys | 1.5–2 | 5.5–8 | Schema matches models |
| **3** | Audit: hash chain, append-only, verification CLI | 1 | 6.5–9 | Chain verifies |
| **4** | Background jobs (database queue, leases, retry, dead-letter); storage on OCI; CSV import engine | 3–4 | 9.5–13 | Import round-trips |
| **5** | Onboarding state machine, presets, configuration-assistant rules, retention and erasure | 2.5–3.5 | 12–16.5 | Setup is resumable |
| **6** | Workforce core: effective-dated history, leave ledger, overtime rules, working-time checks | 3–4 | 15–20.5 | Every calculation traceable |
| **7** | Scheduling solver, forecasting, payroll engine, rule-pack loader | 4–6 | 19–26.5 | Payroll refuses without a verified pack |
| **8** | Reports, compliance outputs, role-based homes, module UI, generated API client | 3–4 | 22–30.5 | Role homes read real data |
| **9** | E2E journeys, accessibility, load and failure tests, validation reports | 2–3 | 24–33.5 | 12 journeys pass on staging |

**Pilot gate** is assessed at the end of Block 8, because the pilot needs
working payroll *inputs*, a usable interface, and the compliance view — not a
complete marketing site or a monorepo migration.

### 3.3 Deliberately deferred, with reasons

These are in the brief and are **not** in the plan above. Each is deferred
with a reason, not silently dropped.

| Deferred | Why | Revisit when |
|---|---|---|
| Monorepo migration (`packages/ui`, `packages/tokens`, `packages/api-client`, `packages/tenant-theme`), pnpm/Turborepo | 3–5 ew of tooling churn with no user-visible value. The existing `frontend/src/components/ui/` already holds the primitives. | After the pilot, when a second front-end surface exists |
| Astro marketing site | 2–4 ew for a static site. The current SPA already serves the pages and is indexed. | After the pilot |
| Storybook for every component | 0.5–1 ew. The components are documented in `docs/DESIGN_SYSTEM.md`; Storybook is a better home but not a better outcome. | With the monorepo migration |
| Tailwind v4 + Style Dictionary | 1–1.5 ew, and it is a *migration* of a working design system, not an addition. The current Tailwind v3 setup is not broken. | With the monorepo migration |
| Full role-aware routing beyond the five role homes | The role homes deliver the "needs your action" benefit; per-route role gating is a refinement. | Block 8, if time remains |
| Multi-jurisdiction rule packs beyond India | Each jurisdiction is a project, and none of them can be written without a verifier. | When a second customer contracts for one |
| Cross-tenant `tenant_id` scoping | The deployment model is one customer per deployment. Schema-wide tenancy is a large project that the chosen model makes unnecessary. | Only if the shared-demo model returns |
| SSO / SCIM / e-signature / background-check integrations | Each needs a real external provider and a paid account. Status tracking already exists. | With a customer contract |
| SOC 2 / ISO 27001 | These are audits of an *organisation*, not features. They need a policy set, an auditor and a budget. | Never "in a build" |

### 3.4 What "production ready" means here

The brief's definition is adopted unchanged. Two points are made concrete:

- **No statutory value outside a rule pack.** A rule pack may only be
  `verified` by a named human against a cited source, with a golden case.
  Until then the affected module is disabled and says why.
- **A feature that is not ready is removed from navigation and behind a
  disabled flag.** It never appears as a visible dead option.

---

## 4. The compliance coverage matrix — true status

The brief's section 5 matrix is the product's honesty contract. Its true
status at the end of Gate 0:

| Row | True status at Gate 0 |
|---|---|
| Access control and least privilege | **Partial.** A central `visibility.py` policy exists but is applied in 3 of 25 endpoint files. 73 reads and 7 writes are unscoped. **Block 1.** |
| Authentication strength | **Partial.** MFA not implemented. Password policy, forced change, refresh rotation and lockout implemented at Gate 0. **Block 1 completes it.** |
| Audit trail and tamper evidence | **Partial.** Every mutation is audited, but the log is ordinary rows with no hash chain. **Block 3.** |
| Data encryption at rest for sensitive fields | **Partial.** Field encryption is now versioned and rotatable. Banking and national identifiers are not yet encrypted. **Blocks 1 and 6.** |
| Data subject access (export) | **Not built.** Block 5. |
| Erasure and anonymisation | **Not built.** Block 5. |
| Retention schedules | **Not built.** Block 5. |
| Consent records | **Not built.** Block 6. |
| Equal-opportunity data separation | **Not built.** Block 6. |
| Working time limits | **Partial.** A flat `hours − 8` calculation exists. No rule pack, no thresholds, no violation records. **Block 6.** |
| Rest breaks and rest periods | **Not built.** Block 6. |
| Overtime calculation | **Partial.** Daily only, no multipliers, no cap, no traceable rule. **Block 6.** |
| Minimum wage and pay floors | **Not built.** Block 6. |
| Leave entitlements | **Partial.** Accrual exists and is tenure-based; it is not ledger-based, has no carry-over, and carries no statutory source. **Block 6.** |
| Public holidays | **Not built.** Block 6. |
| Payroll tax withholding | **Not built, and deliberately disabled.** A flat percentage exists and is *not* statutory. It is replaced in Block 7 by rule-pack-driven calculation, which stays blocked until a pack is verified. |
| Social security and employer contributions | **Not built.** Block 7. |
| Mandatory payslip content | **Not built.** Block 7. |
| Pay frequency and pay-date rules | **Not built.** Block 7. |
| Statutory filings and returns | **Not built.** Block 8. |
| Work eligibility and right-to-work documents | **Partial.** Documents exist; expiry tracking, reminders and masked storage do not. **Block 6.** |
| Health and safety incident records | **Not built.** Block 6. |
| Training and certification currency | **Partial.** Certifications exist; currency tracking does not. **Block 6.** |
| Employment contract records | **Not built.** Block 6. |
| Reporting and records retention | **Partial.** Operational reports exist; retention is not applied to them. **Blocks 5 and 8.** |
| Pay transparency and equal-pay reporting | **Not built.** Block 8. |
| Accessibility of the product itself | **Partial.** Manual checks pass on the top five authenticated pages; no automated axe run in CI, no keyboard pass, no responsive verification. **Block 9.** |
| Secure transport and headers | **Partial.** CORS is an allow-list and `allow_credentials` is off. HSTS and CSP are not set. **Block 1.** |

**No row is marked passing.** Rows that are not built show as *not built*;
rows whose rule source or verifier is missing show as *requires verification*.
The admin compliance view is built in Block 5 and reads from this same
status model, so the product cannot claim more than the coordinator has
verified.

---

## 5. Stop conditions

Reaffirmed from the brief, with the coordinator's reading:

- A lane that discovers a requirement that would break a contract, a security
  rule, or the 512 MB free-tier memory budget **stops and raises a change
  request**. It does not work around the issue.
- With one lane, "raises a change request" means: write it down in
  `REVAMP_NOTES.md` and in the commit message, and take the decision to the
  owner before implementing the alternative.

**Known change requests already raised:**

| ID | Subject | Raised in |
|---|---|---|
| CR-001 | The rule-pack status vocabulary in `contracts/events/payroll_runs.yaml` did not match the lifecycle in the brief. Corrected to `draft` / `pending_verification` / `verified` / `superseded`. | Gate 0 |
| CR-002 | `contracts/errors.md` listed `password_change_required` and `account_locked` under `auth` (401). They are `permission` (403) responses: identity *is* established, and a 401 would make the client treat them as an expired session. The contract and the implementation were changed together. | Gate 0 |
| CR-003 | Oracle schema qualification is needed for the one-schema-per-customer model. Deferred to Block 3. | Gate 0 |
| CR-004 | `app/core/security.py` previously returned the ciphertext unchanged when decryption failed. It now raises. Two call sites swallowed that into a generic "connection failed" status and were corrected to report a key-configuration problem. | Gate 0 |
| CR-005 | Oracle refuses a second modification of the same table inside one transaction in this configuration, with `ORA-12838: cannot read/modify an object after modifying it in parallel`. A row-at-a-time loop that updates the same table once per record fails on the second iteration. Bulk operations must use one statement per table, or commit per record. This is a property of the Oracle Autonomous Database target, not of the code, and it will matter for the bulk import, bulk leave posting and job-queue drains that Blocks 4 and 6 will build. | Gate 0 |

---

## 6. Gate final — the pilot criteria

Unchanged from the brief's section 8, and the coordinator will issue a
written go or no-go against them:

- Every row in the coverage matrix shows its true status, with no row marked
  passing without verification.
- All 12 E2E journeys pass on staging.
- Security negative tests pass for every endpoint.
- No open Critical or High defects.
- Load smoke meets the targets in the feasibility assessment.
- Backup and restore rehearsal completed and recorded.
- The payroll rule packs for the pilot jurisdiction are verified and signed
  off by a named professional, **or payroll is disabled for the pilot**.
- A written go or no-go.
