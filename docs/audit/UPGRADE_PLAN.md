# Karmathy HCM — Upgrade Plan (Phase 0 proposal)

**Date:** 2026-10-21 · **Author:** Super Agent · **Status:** **proposed — awaiting the owner's approval**
**Basis:** `docs/audit/AUDIT_REPORT.md` (verified baseline) and `docs/product/FEATURE_MATRIX.md` (142 capabilities).

This plan changes the order of work from the mandate's default phases for one reason, stated
plainly: **the audit found seven capabilities that exist and fail open, and a role model that is
documented and not enforced.** Building forecasting, scheduling or AI on top of that foundation
compounds it. The mandate allows re-ordering "when the audited dependencies justify it"; this is
that case, and §6 records the change explicitly.

---

## 1. Effort units and how to read them

| Unit | Meaning | Calendar time at the confirmed capacity |
|---|---|---|
| **S** | ≤ 1 engineer-day | 1–2 days |
| **M** | 2–5 engineer-days | 1 week |
| **L** | 1–3 engineer-weeks | 2–4 weeks |
| **XL** | > 3 engineer-weeks | 4–8 weeks |

**The confirmed capacity is one engineer at 20–40 h/week** (Gate 0 decision 1.2, confirmed by the
owner on 2026-10-19). Every range below is calibrated to it. The uncertainty is real: an estimate
carries ±50 % unless it is marked firm. Calendar figures assume one lane at a time, because that is
the capacity, not because the dependencies are optional.

---

## 2. The phase plan

| Phase | Scope | Effort | Cumulative | Exit gate |
|---|---|---|---|---|
| **0 — Audit and decisions** | Inventory, baseline, feature registry, risks, plan, pilot definition | done | 0 | **Owner approves this plan and resolves the decisions in `agents/DECISIONS.md`** |
| **1 — Security and data integrity** | Role enforcement, the payroll gate, the audit trail, the import commit, DEC-000 closure, staging | 4–7 ew | 4–7 | Security negative tests pass per role; no open Critical/High; DEC-000 closed and recorded |
| **2 — Contracts, jobs and data integrity** | Contract reconciliation by domain, job lifecycle, idempotency, observability, the harness fix | 2–3 ew | 6–10 | Contract drift check green; job lifecycle tests pass |
| **3 — Import, presets and onboarding** | Import completion, presets, module dependencies, readiness check, resumable setup | 3–4 ew | 9–14 | Import journeys pass valid/invalid/idempotent/oversized; setup is resumable |
| **4 — Core HCM workflows** | Effective-dated history, leave ledger, working time, lifecycle, approvals, recruitment and offboarding workflows | 4–6 ew | 13–20 | The J5–J7, J10 journeys pass across frontend, API, database and authorisation |
| **5 — Forecasting and scheduling** | Solver, constraints, publication, scenarios, the connected loop | 4–6 ew | 17–26 | Forecast accuracy reported; constraints tested; J8–J9 pass |
| **6 — Payroll integrity** | Calculation pipeline, inputs, reconciliation, payslips, rule-pack machinery | 3–5 ew | 20–31 | Independent calculation fixtures and end-to-end reconciliation pass |
| **7 — Experience and design system** | The approved shell, role homes, module screens, accessibility, responsive | 3–5 ew | 23–36 | J13 passes at every viewport; the previous experience stays available behind the flag |
| **8 — AI capabilities** | Only approved capabilities, with the controls landing first | 4–8 ew | 27–44 | Capability evaluations, leakage tests, authorisation-bypass tests and graceful-degradation tests pass |
| **9 — Integration, validation, release** | Full regression, E2E, security, accessibility, performance, recovery | 2–3 ew | 29–47 | No open Critical/High; all evidence published; the human's go/no-go is recorded |

**Total: 29–47 engineer-weeks at one engineer.** At 20–40 h/week that is **7–12 months** to the
full target, and **4–7 weeks** to a pilot. The numbers in `FEASIBILITY.md` are the decision, not
this table.

**Phases 1 and 2 are not optional and not parallelisable.** Everything after them is.

---

## 3. The dependency graph

```
                        ┌──────────────────────────┐
                        │  OWNER DECISIONS          │  DEC-000, DEC-002, DEC-003, DEC-004
                        │  (agents/DECISIONS.md)    │  DEC-005…DEC-014
                        └────────────┬─────────────┘
                                     │ gates
      ┌──────────────────────────────┴──────────────────────────────┐
      │                                                             │
┌─────▼──────────────────────┐                      ┌───────────────▼────────────────┐
│ PHASE 1  security & data  │                      │ SUP-03 one worktree per agent  │
│ integrity                 │                      │ SUP-04 staging environment     │
├───────────────────────────┤                      │ PS-02 secret scan (CI green)   │
│ PS-01 reset guard  [M]    │◄──── merges ────────┤                                │
│ PS-05 role enforcement [L] │                      │ (independent of product code)  │
│ PR-01 payroll gate    [M]  │                      └────────────────────────────────┘
│ DI-01 import commit   [M]  │
│ PS-03 audit txn      [L]   │
│ PS-04 hash chain     [L]   │
│ PS-07 hashed denylist[S]   │
│ HR-12 / AD-09 DSAR   [XL]  │
└────────────┬──────────────┘
             │ every phase below depends on the role model and the audit trail
   ┌─────────┼──────────┬───────────────┬─────────────────┐
   │         │          │               │                 │
┌──▼───┐ ┌───▼────┐ ┌───▼──────┐ ┌─────▼──────┐  ┌───────▼───────┐
│PHASE │ │PHASE 3 │ │PHASE 4   │ │PHASE 5     │  │PHASE 6        │
│2 con-│ │import  │ │core HCM  │ │forecast &  │  │payroll        │
│tracts│ │presets │ │workflows │ │scheduling  │  │integrity      │
│& jobs│ │setup   │ │          │ │            │  │               │
└──┬───┘ └───┬────┘ └────┬─────┘ └─────┬──────┘  └───────┬───────┘
   │         │           │             │                 │
   └─────────┴───────────┴─────────────┴─────────────────┘
                             │
                    ┌────────▼─────────┐        ┌──────────────────┐
                    │ PHASE 7 UX       │        │ PHASE 8 AI       │
                    │ (tracks each     │        │ (controls land   │
                    │  contract)       │        │  with the first  │
                    └────────┬─────────┘        │  capability)     │
                             │                  └────────┬─────────┘
                    ┌────────▼───────────────────────────▼─────────┐
                    │ PHASE 9 integration, validation, release     │
                    └──────────────────────────────────────────────┘
```

**The rules this graph encodes** (mandate §9):

1. Security and shared domain contracts precede dependent business logic.
2. Migrations and API contracts precede frontend integration.
3. CSV schemas and import contracts precede the full import interface.
4. Preset schemas precede preset-dependent onboarding.
5. Forecast inputs precede roster optimisation.
6. Scheduling constraints precede publication and swaps.
7. Approved time and leave precede payroll reconciliation.
8. Backend authorisation precedes treating frontend hiding as a control.
9. E2E tests use the integrated contract, never a mock.
10. Release work depends on the validation reports and the approved gate.

---

## 4. What is already in flight

| Work | State | Merge gate |
|---|---|---|
| `PS-02` secret-scan allowlist | branch, 1 commit | Merge first. Nothing else merges until CI is green. |
| `PS-01` production reset guard | branch, 1 commit, stacked on PS-02 | Merge second. |
| `DI-01` import commit rework | uncommitted, shared checkout | Needs a branch, a handoff and a gate. |
| `PR-01` payroll rule machinery (money, loader, engine, reconciliation, 22 tests) | uncommitted, shared checkout | Needs a branch. **Its endpoint does not exist yet — the machinery is not a capability until it is wired and gated.** |
| `OC-01` preset schema and dependency graph | branch, **no commits** | Nothing to merge. |
| `QA` matrix status pass, test-count reconciliation, seed verification | uncommitted, shared checkout | Needs a branch. This work is the evidence base for everything else. |
| `FD` monorepo, tokens, component library, API client, tenant theme | uncommitted, shared checkout | Needs a branch **and a decision** — it reverses Gate 0 §3.3, which deferred the monorepo. See `DEC-013`. |
| `WC` leave ledger, retention tooling | uncommitted, shared checkout | Needs a branch. |
| `PL` forecast backtest harness | uncommitted, shared checkout | Needs a branch. |

**None of it is merged, and none of it is behind a gate. That is the first thing Phase 1 fixes.**

---

## 5. Task breakdown for Phase 1 and Phase 2

Every task has a request file under `agents/requests/`. The board is `agents/TASK_BOARD.md`.

### Phase 1 — security and data integrity (4–7 ew)

| ID | Task | Owner | Effort | Depends on | Parallel? |
|---|---|---|---|---|---|
| `PS-02` | Secret-scan allowlist (9 distinct values, reasons, no rule weakened) | platform-security | S | — | done, branch ready |
| `PS-01` | Production guard on the administrator reset | platform-security | M | `PS-02` | done, branch ready |
| `SUP-03` | One worktree and one branch per agent and per issue | Super Agent | S | — | **start immediately** — it gates every lane |
| `SUP-04` | Staging environment (Render service + second Oracle database) | Super Agent + owner | M | owner approval | needs the owner |
| `PS-05` | Apply `require_roles` to every endpoint; delete the ad-hoc comparisons; one negative test per role × endpoint | platform-security | L | `PS-02` | with `PR-01` |
| `PR-01` | The payroll rule-pack gate: refuse a pay run for a jurisdiction without a verified pack; wire the loader, the effective-date resolver and the golden cases | payroll-rules | M | `PS-05` (no endpoint edit overlap) | with `PS-05` |
| `DI-01` | The import commit path actually commits; counts match the database; the audit row matches | data-import | M | `PS-02` | with `PS-05` |
| `DI-02` | The confirmation token is bound to the result hash, has a TTL and a bound | data-import | S | `DI-01` | serialised |
| `PS-03` | The audit record is in the same transaction as the mutation; the two missing audit events; a source address | platform-security | L | `PS-05` | serialised against endpoint edits |
| `PS-04` | Hash-chained, append-only audit log with a verification command | platform-security | L | `PS-03` | serialised |
| `PS-07` | The denylist holds SHA-256 digests, not the credential | platform-security | S | `PS-02` | any time |
| `PY-01` | Salary unit semantics: `base_salary` is per pay period — the offer letter, the import schema and every label | payroll-rules | S | — | with `DI-01` |
| `HR-12`/`AD-09` | Data subject export, retention, erasure with legal hold | workforce-core | XL | `PS-05` | last in Phase 1 |

**Critical path: `PS-02` → `PS-05` → `PS-03` → `PS-04` ≈ 1 + 3 + 3 + 3 = 10 weeks.**
`PR-01`, `DI-01`, `DI-02`, `PS-01`, `PS-07` and `PY-01` fill the gaps around it. The critical path
is what the pilot waits for.

### Phase 2 — contracts, jobs and data integrity (2–3 ew)

| ID | Task | Owner | Effort | Depends on |
|---|---|---|---|---|
| `SUP-02` | Triage the 210 undeclared endpoints by domain; each owner declares and promotes | Super Agent + owners | M | Phase 1 |
| `SUP-05` | Promote `x-lifecycle` from `planned` to `released` as the code lands, in the same change request | owners | S each | `SUP-02` |
| `QA-05` | The test harness is concurrency-safe: per-suite database paths outside the shared directory | qa-validation | S | `SUP-03` |
| `DI-03` | The import feature set has a test per capability row | data-import | M | `DI-01`, `DI-02` |
| `JOB-01` | The `csv_import` job handler is real; progress and recovery | data-import | M | `DI-01` |
| `OBS-01` | Observability: request id, structured logging, job metrics | platform-security | M | `PS-03` |

---

## 6. The plan change, recorded

The mandate's default order places "Domain contracts and background processing" (Phase 2) before
"CSV import and tenant onboarding" (Phase 3), and puts the UX phase late. This plan moves three
things earlier, for these reasons:

1. **The payroll gate and the role model move into Phase 1**, before any new business capability.
   Reason: `PY-10` and `AD-04` are `broken`, and every capability built on them inherits the
   failure. Building onboarding first and fixing the gate later means the setup flow would open a
   door that payroll walks through.
2. **The import commit fix moves into Phase 1**, ahead of the preset work, because the presets
   deliver an employee-import template and the import path currently reports success without
   writing. A preset that hands a customer a broken door is worse than a missing preset.
3. **The staging environment is Phase 1, not Phase 9.** Reason: no phase can cite a staging
   result, a load result or a journey on staging until it exists, and the pilot gate needs all
   three. Building staging in Phase 9 means discovering the deployment problems when there is no
   time left to fix them.

**Not changed:** the order of the business domains, the dependency rules, the definition of done,
and the requirement for the owner's approval at every release gate.

---

## 7. Rollout and rollback

| Change | Rollout | Rollback |
|---|---|---|
| Role enforcement (`PS-05`) | Ship per endpoint family with the new test; behind a flag where a customer would lose access | Revert the dependency; the ad-hoc check returns with it — which is why the flag defaults to off for 7 days |
| Payroll gate (`PR-01`) | Ship the gate **before** the engine: the refusal first, then the calculation | The gate stays; the engine is disabled by jurisdiction. A gate is never rolled back. |
| Audit chain (`PS-04`) | Expand (nullable columns, backfill) → contract (not null) in a later release | The downgrade is tested in both revisions; the chain is additive |
| Import commit (`DI-01`) | Ship behind the same route; the dry run is unchanged | The commit route returns the previous 400 rather than a false success |
| Schema changes | Expand-then-contract, always. The contract step ships after the old code is gone | The downgrade is verified before the release candidate is prepared |
| Staging | A separate Render service; production is untouched until the owner promotes | Deleting the staging service changes nothing in production |
| The frontend shell | Feature-flagged; the old shell stays reachable for two clean pilot weeks | Flip the flag back |

**No release candidate is prepared while DEC-000 is open, any Critical or High defect is open, a
Tier 1 security item is open, a migration lacks a verified downgrade, a payroll feature is enabled
for a jurisdiction without a verified pack, or the journey suite is red on staging.**

---

## 8. Parallelisation, honestly

| Can run together | Cannot |
|---|---|
| `PS-02`, `SUP-03`, `SUP-04`, `PS-07` — no product code | Two issues touching the same file. Ever. |
| `PS-05` and `PR-01` — disjoint files (`app/api/deps.py` + endpoints vs. the payroll service) | `PS-03` and anything that edits an endpoint file |
| `DI-01` and `PS-05` — disjoint files (`import_export.py` vs. the other 13 endpoint files) | Anything and the shared checkout |
| Documentation, the design system, the test harness, the seed | Two lanes in one working directory — **R12** |

**The constraint that matters is not the dependency graph; it is one engineer.** The parallel
lanes above are parallel only in the sense that their *code* does not conflict. The capacity to
review and merge them is one person, and the gate on each is a human approval. Plan the work as
if it were serial, and the parallelisation is free upside when it appears.

---

## 9. The first two weeks, concretely

| Day | Action | Owner |
|---|---|---|
| 1 | The owner answers the three questions in `agents/ESCALATIONS.md` and ratifies the decisions in `agents/DECISIONS.md` | Owner |
| 1 | Merge `PS-02` then `PS-01` — CI goes green | Super Agent + owner |
| 1 | Every lane moves to its own worktree and branch (`SUP-03`) | Super Agent |
| 2 | The staging Render service is created against the second Oracle database (`SUP-04`) | Owner + Super Agent |
| 2–3 | The six uncommitted lanes land as branches with handoffs, one at a time | Each lane |
| 3–5 | `PS-05` starts: the role matrix, the endpoint sweep, the negative tests | platform-security |
| 5–7 | `PR-01` starts: the payroll gate and the wiring of the rule machinery | payroll-rules |
| 7–8 | `DI-01` and `DI-02`: the import commit path | data-import |
| 8–10 | `QA-05` (the harness), `QA-01`…`QA-04` (the journeys, the load harness, axe in CI) | qa-validation |
| 10 | Phase 1 exit review: every Phase 1 acceptance criterion, with evidence | Super Agent + owner |

**Nothing in Phase 2 starts until Phase 1's exit gate is met**, with the exception of
documentation, the test harness and the seed.
