# Karmathy HCM — Feasibility (Phase 0)

**Date:** 2026-10-21 · **Author:** Super Agent · **Basis:** `docs/audit/AUDIT_REPORT.md`
**Status:** proposed — the decision is the owner's.

---

## 1. The confirmed constraints

These are not estimates. Each is a recorded answer or a measured fact.

| Constraint | Value | Source |
|---|---|---|
| Team | **One engineer** | Gate 0 decision 1.2, confirmed by the owner 2026-10-19 |
| Weekly hours | **20–40 h/week** | Gate 0 decision 1.2 |
| Infrastructure budget | **$0** — Render free tier, one Oracle Autonomous Database free tier | `render.yaml`, `docs/DEPLOYMENT.md` |
| Databases available | **2** (one in use, one reserved as headroom) | Gate 0 decision 1.1 |
| Deployment model | **One customer per deployment, one Oracle schema per customer** | Gate 0 decision 1.1 |
| First jurisdiction | **India**, payroll disabled until a pack is verified by a named human | Gate 0 decision 1.4 |
| Statutory values | **Never written into the codebase** | Gate 0 decision 1.4, DEC-006 |
| Storage | **Ephemeral** (`STORAGE_BACKEND=local`) — documents are lost on redeploy | `docs/DEPLOYMENT.md` |
| Deploy trigger | **A push to `main` deploys to production** | `render.yaml` `autoDeployTrigger: commit` |
| Agents | 8 specialist roles, **one lane executing at a time** | Gate 0 decision 1.2; DEC-009 |

**The single most consequential fact:** the brief's nine-agent structure with a 7-week schedule
would need **54–86 engineers** (Gate 0 §3.1). The confirmed capacity is one. Every estimate below
is calibrated to one engineer, and the plan is therefore a sequence, not a parallel programme.

---

## 2. The numbers

At **30 productive hours per week** (the midpoint of the confirmed range):

| Target | Effort | Calendar at 30 h/wk | Calendar at 20 h/wk |
|---|---|---|---|
| **Pilot** (Phase 0 + Phase 1 + the pilot subset of Phases 2–4) | **9–14 ew** | **3–5 months** | **4.5–7 months** |
| The four capabilities the value proposition rests on (role model, payroll gate, import commit, setup wizard) | 5–8 ew | 2–3 months | 3–4 months |
| Full target (all ten phases) | **29–47 ew** | **10–16 months** | **15–24 months** |
| The 12 journeys, the load harness and the release evidence | 3–4 ew | 1–1.5 months | 1.5–2 months |

**Uncertainty is ±50 %** on every figure above. The exception is the effort already spent: the
audit, the contracts, the CI gate, the credential rotation, the migrations and 520 backend checks
are done, and they are the platform the estimates are built on.

**What the estimates do not include:** the time to appoint and brief a statutory verifier, the
time for a customer to complete a security review, the time to migrate real customer data, and any
work that a customer contract makes necessary and the mandate did not foresee.

---

## 3. Feasibility by capability group

| Group | Feasible? | Notes |
|---|---|---|
| **Role model, audit trail, the payroll gate, the import commit** | **Yes, and first** | 1.5–2.5 ew. All four are defects in code that already exists; there is no new architecture. |
| **Industry presets and the configuration assistant** | **Yes** | 1.5–2 ew for the six presets, the dependency graph and the readiness check, once the schema is validated. The schema exists; the content does not. |
| **Effective-dated history, the leave ledger, working time** | **Yes** | 2–3 ew. It is the largest data-model change in the plan and it touches every read of employee data. |
| **Core HCM workflows (recruitment, onboarding, offboarding, approvals)** | **Yes, partially** | The endpoints exist and are shallow. The workflows are 2–3 ew for the ones the pilot needs and 2 ew more for the rest. |
| **Forecasting and scheduling** | **Yes, but late** | The forecast engine exists and is the strongest piece of domain logic in the repository. The roster solver is 2–3 ew of OR-Tools work and needs `ortools` in the image — **which means a dependency addition and a container rebuild.** |
| **Payroll integrity** | **Yes for generic calculation; no for statutory** | The generic pipeline is 2–3 ew. Statutory calculation is **not feasible without a named verifier and cited sources**, and it is not on the critical path to a pilot. |
| **AI, any tier** | **Not feasible now, feasible later** | The controls alone are 2–3 ew and they must land with the first capability. No capability may ship without them. |
| **Multi-jurisdiction rule packs** | **Not feasible** | Each jurisdiction is a project with a human verifier attached. |
| **Data subject export, erasure, retention** | **Feasible and required** | 1.5–2 ew. It is a legal exposure, so it is Phase 1 work, not a deferral. |
| **Marketing site, SSO/SCIM/e-signature, multi-entity** | **Not feasible** | Already deferred with reasons at Gate 0 §3.3; each needs a real provider and a paid account. |
| **Load and performance engineering** | **Feasible once the harness exists** | 1 ew for a harness that measures the free tier's actual limits. There is no measurement today, so no budget can be set. |

---

## 4. Infrastructure feasibility

| Question | Answer |
|---|---|
| Can the free tier serve one pilot customer? | **Yes** — the live deployment serves 600 seeded employees and 22,321 time entries. The limit is memory (512 MB), not CPU. |
| Can the free tier serve a staging environment as well? | **Yes, if the second Oracle database is used** — Gate 0 reserved it for exactly this. It requires the owner to create the service and the schema. |
| Does the release step work on Render? | **Yes**, and it has failed usefully: the ORA-01430 behind a failed deploy was found *because* the migration failure was written to the audit trail (`X-22`). |
| Is the storage model a blocker? | **For the pilot, yes**: offer letters and onboarding documents are lost on redeploy. Switch `STORAGE_BACKEND=oci` (Oracle Object Storage) or accept the limitation explicitly in the pilot's terms. **Not feasible on a $0 budget if OCI requires a paid shape** — to be confirmed by the owner. |
| Does the 512 MB limit bound the design? | **Yes** — background work runs in the database queue rather than in memory, and the forecast engine is vectorised over the caller's series. Both were designed for this. |
| Does the monorepo change (in flight) add infrastructure? | **Yes** — pnpm, Turborepo, Style Dictionary, Storybook and `openapi-typescript-codegen` are new toolchain dependencies. They are free, but they add a build surface and a CI cost, and they reverse a deferred decision. See `DEC-013`. |

---

## 5. The recommendation

**Ship a security-and-workflow pilot for one customer, not a product.**

| | |
|---|---|
| **Scope** | The role model, the audit trail, the payroll gate, the import commit, the presets, the setup wizard, effective-dated employee history, the leave ledger, time capture, and the role-aware experience. |
| **Excluded** | Scheduling, forecasting, AI, recruitment beyond requisitions and offers, benefits administration, learning, performance, multi-jurisdiction, marketing, integrations, multi-entity. |
| **Payroll** | Ships in a "requires configuration" state, with the refusal demonstrated on staging. No statutory claim. |
| **Time to pilot** | **3–5 months** at the confirmed capacity, assuming the owner answers the three questions within a week and the staging environment is created in the first two weeks. |
| **Time to the full target** | **10–16 months**. If the business needs the full target sooner, the capacity has to change, and the options are a second engineer (halves the calendar, roughly) or a narrower scope. |

**Why this and not a broader build.** The audit found seven capabilities that exist and fail open.
Every one of them is in the pilot's scope, deliberately: a customer who imports their employees
and cannot get the data in (D-001), or who runs a pay run in an unverified jurisdiction (D-014), or
whose managers can see records they should not (AD-04), is a customer who churns and a liability
that persists. Fixing them first is both the fastest route to a working product and the only
defensible one.

**Why not more parallelism.** Eight lanes exist and can all produce code. One engineer reviews,
gates and merges them. Pretending otherwise produced the current situation: six lanes of uncommitted
work in a shared directory with no gate on any of it.

---

## 6. What would change the recommendation

| If this changes | Then |
|---|---|
| A second engineer joins | The calendar compresses toward the parallel plan; the dependency graph in `UPGRADE_PLAN.md` §3 becomes real. Phases 2 and 3 run concurrently. |
| The owner wants the full target in under six months | The scope must be cut, not the time. The exclusions in §5 are already the cut; going below them means a product that is a worse version of everything. |
| A customer contracts for a specific jurisdiction | The statutory work becomes a funded project with a named verifier, and it enters as a separate Phase 6a. |
| The free tier proves insufficient | The database-per-customer model (Gate 0 §3.1) reopens, and the second database stops being staging headroom. |
| A security review by a customer fails on the audit trail | `PS-03` and `PS-04` move to the front of Phase 1 and the pilot slips by their duration. |

---

## 7. The decision the owner has to make

One sentence: **do you accept a 3–5 month pilot of the security-and-workflow scope above, on the
free tier, with payroll disabled and no statutory claim — and do you create the staging
environment in the first two weeks?** Everything else in this plan follows from that answer.

*Figures in this document are estimates with stated uncertainty (mandate §2.3: **Inferred**). The
underlying counts — 259 served operations, 520 backend checks, 150 matrix rows, 142 capabilities,
7 broken, 5 implemented — are **Verified** at `70a8745`.*
