# Karmathy HCM — Feasibility Assessment

**Companion to:** `AUDIT_REPORT.md` and `UPGRADE_PLAN.md`
**Assessment date:** 2026-10-19

---

## 1. Inputs you provided

| # | Question | Your answer |
|---|---|---|
| 1 | Team size / experience | **1 engineer** (no separate frontend/backend/Oracle specialists) |
| 2 | Weekly capacity | **20–40 h/week** |
| 3 | First paying or pilot customer | **1–3 months** |
| 4 | Monthly budget | **$0 — free tiers only** |
| 5 | Compliance / security required by the pilot | **India statutory payroll, CCPA, GDPR, ISO 27001, SOC 2** (all five) |
| 6 | Design resource | **Engineers only** |
| 7 | Target regions | **India, US, UK/EU, Middle East, Southeast Asia** |
| 8 | Deployment model | **Single tenant per customer** |
| 9 | `base_salary` unit | **Per pay period** |
| 10 | Live testing | **Use the documented default admin login** (verified; the default credential is still active) |
| 11 | Data retention | **Per-region rules** |

**Not provided:** years of experience with React/FastAPI/Oracle; which role(s) the single engineer is strongest in.
The codebase suggests a competent full-stack generalist, but that is an inference, not a confirmed input.

---

## 2. Technical feasibility

### 2.1 What the current code proves

- A **working 236-operation API** and **22-page SPA** that build and run. [Fact]
- **435 numbered local checks pass**, including security, import, metrics and data-quality suites. [Fact]
- Real engineering hygiene in places: Decimal payroll, state machine, idempotency, request IDs, structured errors,
  a visibility policy module, audit logging, mTLS wallet support. [Fact]
- The revamped shell already has a skip link, mobile drawer, focus-visible styles and labelled forms on the top
  5 pages. [Fact]

This is **not** a prototype that needs rewriting. The proposed stack changes are incremental and can be done
without a rewrite.

### 2.2 Skill gaps and how to cover them

| Area | Assessment | Consequence | Cover |
|---|---|---|---|
| React/TypeScript/Vite | Code compiles, patterns are conventional. Likely sufficient | Low | Existing engineer |
| FastAPI/SQLAlchemy | Layered, tested, coherent. Likely sufficient | Low | Existing engineer |
| Oracle DDL/ops | Correct use of `Identity()` and mTLS, but no migrations and no restore rehearsal | **Medium** | Learn Alembic + Oracle online DDL; rehearse a restore |
| Security engineering | Good recent fixes, but 73 unscoped reads and 7 IDORs remain | **High** | Prioritise; consider a one-off external review |
| **India statutory payroll** | Not implemented at all (flat percentage) | **Critical** | A payroll/tax specialist is mandatory; cannot be learned from docs safely |
| **US/UK/Middle East/SEA payroll** | Not implemented; each jurisdiction is a project | **Critical** | Do not promise; per-country partner |
| **SOC 2 / ISO 27001** | Nothing evidenced; no policies, no audit | **Critical** | Auditor + compliance platform + 3–12 months |
| **GDPR/CCPA** | No retention/erasure/consent/DPA | **High** | Privacy lawyer |
| Product design | No designer | **Medium** | Use a constrained design system; budget 20–30% extra |
| DevOps at scale | Single free instance, no metrics/alerting | **Medium** | Sentry + uptime + paid tier when scaling |

**Verdict on technical feasibility:** the *engineering* is feasible for one person. The **compliance and
multi-jurisdiction payroll** are not engineering tasks and cannot be delivered by the same person in the same
timeframe.

---

## 3. Timeline feasibility (the calculation)

### 3.1 Capacity

Using **1 engineer-week = 30 productive hours**:

```
capacity per month (ew) = (hours/week × 52 / 12) / 30
  at 20 h/week = 2.89 ew/month
  at 30 h/week = 4.33 ew/month   (midpoint)
  at 40 h/week = 5.78 ew/month

available by a 3-month deadline:
  20 h/week  → 8.7 ew
  30 h/week  → 13.0 ew
  40 h/week  → 17.3 ew
```

### 3.2 Effort required (from `UPGRADE_PLAN.md`)

| Scope | Effort (ew) | Source |
|---|---|---|
| Tier 1 security/data foundation (ownership, visibility, storage, credential, Alembic, offer transaction, CI, deps, RBAC) — **excluding** payroll inputs | **7.6** | B1 items 1–6, 8–12 |
| + 30% contingency | **9.9** | — |
| Tier 1 foundation **including** payroll inputs | **9.6** | B1 items 1–12 |
| + 30% contingency | **12.5** | — |
| Pilot UI slice (tokens, shell, Associate/Manager homes, Leave/Time/Recruiting, a11y) | **8.5** | B2.2 |
| Full UX revamp (phases 1–8 + tooling) | **24–38.5** | B2.1 |
| Stack migration element (tooling + Astro) | **5–9** | B2.0 + B2 phase 5 |
| Backend upgrade programme (single-tenant model) | **18.5–32.5** | B3 |

### 3.3 Realistic dates

Months = effort ÷ capacity.

| Deliverable | Effort | @20 h/wk | @30 h/wk | @40 h/wk |
|---|---|---|---|---|
| **(a) Foundation (Tier 1, excl. payroll inputs)** | 7.6 ew | **2.6 mo** | **1.8 mo** | **1.3 mo** |
| (a) + 30% contingency | 9.9 ew | **3.4 mo** | **2.3 mo** | **1.7 mo** |
| (a) + payroll inputs | 9.6 ew | **3.3 mo** | **2.2 mo** | **1.7 mo** |
| (a) + payroll inputs + 30% contingency | 12.5 ew | **4.3 mo** | **2.9 mo** | **2.2 mo** |
| (a) + pilot UI slice (no overlap) | 16.1 ew | **5.6 mo** | **3.7 mo** | **2.8 mo** |
| **(b) Full UX revamp** | 24–38.5 ew | **8.3–13.3 mo** | **5.5–8.9 mo** | **4.2–6.7 mo** |
| **(c) Stack migration** (tooling + Astro) | 5–9 ew | **1.7–3.1 mo** | **1.2–2.1 mo** | **0.9–1.6 mo** |

### 3.4 Verdict on the 1–3 month target

- **A full secure pilot + revamp is not achievable in 1–3 months solo.** The foundation alone is **1.3–3.4 months**
  depending on hours (7.6–9.9 ew), before any UI work.
- **A security-only pilot on the existing UI is achievable in ~1.7–2.3 months at 30–40 h/week** (9.9 ew with
  contingency), or **~3.4 months at 20 h/week**. This is the only reading of the 1–3 month target that holds.
- **Adding the 8.5-ew pilot UI slice raises the total to 16.1 ew → 2.8–5.6 months** (2.8–3.7 months at 30–40 h/week).
  A customer-facing revamp therefore **does not** fit the 1–3 month target.
- A reduced-scope, security-first pilot is achievable only if:
  1. the customer is a **single design partner** on a dedicated deployment;
  2. **payroll is run in parallel/dry-run** and is not the customer's system of record;
  3. the Tier 1 security/storage fixes land first (7.6 ew excluding payroll, 9.6 ew including it);
  4. the **existing UI is shipped as-is**; the 8.5-ew revamp slice is deferred until after the pilot;
  5. no SOC 2/ISO/GDPR certification is promised.
- **If the pilot customer requires any of the five compliance regimes at signing, the 1–3 month target is
  infeasible at any hours level.**

---

## 4. Infrastructure feasibility

### 4.1 Current platform limits (free tier)

> Figures are the commonly published free-tier limits; verify current provider terms before relying on them.

| Component | Limit | Implication |
|---|---|---|
| Render free web service | ~512 MB RAM, shared CPU, **spins down after ~15 min idle**, 750 h/month | 42 s cold start measured; low concurrency headroom |
| Render static site | Free, global CDN | Fine for the SPA and Astro |
| Oracle ADB Always Free | 2 databases, ~20 GB each, shared OCPU | Fine for a pilot; shared CPU is the latency risk |
| Oracle Object Storage Always Free | ~20 GB total, limited API requests | Documents dominate growth |
| In-process rate limiter | Per replica | Fine at one replica; wrong at two |
| DB pool | `pool_size=5`, `max_overflow=10` (15 connections/instance) | Caps concurrent DB work |
| Backups | ADB platform backups, **restore untested** | RPO/RTO unknown |

### 4.2 What breaks first, and at what scale

| Order | Bottleneck | Trigger (estimate) | Symptom |
|---|---|---|---|
| 1 | **Cold start** | Any idle period > 15 min | 40 s first request; users think it is down |
| 2 | **Ephemeral storage** | Every redeploy | Offer letters / documents disappear |
| 3 | **Backend RAM/CPU** | ~10–20 concurrent users; payroll for >200 employees | Slow responses, 502s, request timeouts |
| 4 | **DB connection pool** | >15 simultaneous DB-bound requests | Queueing; sync endpoints block threadpool |
| 5 | **ADB shared OCPU** | Payroll runs + reports at month-end | Multi-second queries |
| 6 | **Object storage 20 GB** | ~2,000 employees × 10 docs × 1 MB | Upload failures |
| 7 | **Single replica** | Any load balancing need | Rate limits multiply; no HA |

**Estimated pilot scale that fits free tier:** **1 customer, 50–200 employees, 5–15 concurrent users**, light
document volume, payroll run off-hours. [Assumption, based on the limits above — not load-tested]

**At 10× (5–10 customers / 500–2,000 employees):** the free tier will not hold. Expect to need a paid backend
instance (no spin-down, more RAM), a shared rate-limit/queue store, and either multiple ADBs or a paid ADB.

### 4.3 Data volume estimate (pilot)

| Data | Assumption | Volume |
|---|---|---|
| Employees | 200 | ~200 rows |
| Payroll slips | 200 × 12 months | ~2,400 rows/year |
| Time entries | 200 × 250 days | ~50,000 rows/year |
| Audit | ~20 mutations/employee/month | ~48,000 rows/year |
| Documents | 200 × 10 × 1 MB | **~2 GB** |
| Total DB | — | well under 20 GB for years |
| Object storage | — | ~2 GB at pilot; ~20 GB at 10× |

**Conclusion:** the database is not the constraint; **documents, backend memory and cold starts** are.

---

## 5. Cost feasibility

### 5.1 Pilot at $0

| Item | Plan | Monthly |
|---|---|---|
| Render backend | Free (spins down) | $0 |
| Render frontend | Free static | $0 |
| Oracle ADB | Always Free | $0 |
| Oracle Object Storage | Always Free (<20 GB) | $0 |
| Sentry | Free tier | $0 |
| Uptime monitor | Free tier | $0 |
| GitHub Actions | Free minutes | $0 |
| Domain | Optional, annual | ~$1/mo amortised |
| **Total** | | **~$0–1/mo** |

**But $0 buys:** cold starts, one replica, no paid support, no guaranteed backup SLA beyond the platform,
and no compliance tooling. That is acceptable only for a design partner who accepts it in writing.

### 5.2 Minimum paid profile (recommended for a real pilot)

| Item | Plan | Monthly (approx.) |
|---|---|---|
| Render backend (no spin-down) | Starter | $7 |
| Render frontend | Free static | $0 |
| Oracle ADB | Always Free | $0 |
| Sentry | Team/free | $0–26 |
| Uptime + status page | Free | $0 |
| **Total** | | **~$7–35/mo** |

### 5.3 At 10× scale (estimate)

| Item | Monthly (approx.) |
|---|---|
| Backend (Standard, 2 GB) | $25 |
| Managed Redis (queue + rate limit) | $10–30 |
| Oracle ADB (if free limits exceeded) | $50–300+ (highly variable) |
| Object storage overage | $1–10 |
| Monitoring/error tracking | $26–80 |
| **Total** | **~$110–450/mo** |

**Compliance is the real cost, not hosting:** SOC 2 Type I audits commonly run **$10k–$30k** and ISO 27001
**$15k–$50k+** including auditor and tooling, before staff time. [Assumption — vendor quotes vary; not obtained]
With a $0 budget, **neither certification is achievable in the timeframe**.

---

## 6. Risk register (top 10)

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | **Compliance promise cannot be met** (SOC 2/ISO/GDPR/CCPA/India payroll all required) | **High** | **Critical** | Do not sign a customer requiring them; scope the pilot as a design partnership; budget an auditor/lawyer/payroll specialist |
| 2 | **Object-level data leak** (73 unscoped reads, 7 IDOR writes) reaches a pilot | **High** | **Critical** | Fix Tier 1 items 1–2 before any customer data; add negative tests per module |
| 3 | **Wrong pay** because payroll ignores leave/overtime/benefits or misreads salary | **High** | **Critical** | Keep payroll in parallel/dry-run; explicit per-period unit; reconciliation sign-off |
| 4 | **Data loss** of documents on redeploy (local storage) | **High** | **High** | Switch to OCI Object Storage + copy existing files before pilot |
| 5 | **Default admin credential** is used/abused | **High** | **High** | Rotate now; named accounts; remove hardcoded seed password |
| 6 | **Solo-engineer bus factor / burnout** | **High** | **High** | Ruthless scope; no compliance promises; document decisions; consider a contractor for design/a11y |
| 7 | **Schema drift / failed deploy** (no migrations) | **Medium** | **High** | Alembic baseline; expand/contract; staging DB; restore rehearsal |
| 8 | **Free-tier cold start** loses the pilot's confidence | **High** | **Medium** | $7 Render Starter, or an uptime pinger (does not fix 502s) |
| 9 | **Dependency vulnerabilities** in auth/upload paths | **Medium** | **High** | Upgrade Starlette/FastAPI, python-multipart, python-jose; CI audit |
| 10 | **Multi-region payroll/tax scope creep** | **High** | **High** | Pick **one** jurisdiction (India) for the pilot; defer the others contractually |

---

## 7. Decision

### Recommendation: **Proceed with reduced scope — ship the security/storage foundation on the existing UI, as a single-tenant design partner with non-statutory payroll. Defer the revamp until after the pilot.**

Justification:

1. **The code is viable.** 236 operations, 435 passing checks, a coherent architecture and a real audit trail.
   This is not a rewrite situation; the proposed stack migration can be incremental.
2. **The security gaps are fixable.** Ownership checks + visibility wiring + storage + credential + Alembic + CI are
   **~7.6 ew without payroll inputs** (1.3–2.6 months at 20–40 h/week), or **~9.6 ew including them** (1.7–3.3
   months). That is the true "pilot-ready" bar.
3. **The 1–3 month date is only realistic if the UI revamp is deferred.** Full revamp (24–38.5 ew) and stack
   migration (5–9 ew) cannot fit. Even the 8.5-ew pilot UI slice pushes the total to 16.1 ew (2.8–5.6 months).
   Ship the existing screen set behind the fixed backend for the pilot.
4. **Single-tenant-per-customer is the right call for now.** It removes the XL schema-wide `tenant_id` project and
   matches your capacity. It does **not** remove the need for object-level authorisation, and the product must stop
   being described as multi-tenant.
5. **The compliance answers are the binding constraint.** With $0, one engineer, and a 1–3 month target, you cannot
   deliver SOC 2, ISO 27001, GDPR, CCPA and statutory India payroll. A customer who requires them at signing
   should be deferred; a design partner who accepts the limitations can start now.

### Conditions for "go"

- [ ] Tier 1 items **1–6 and 8–12** are complete (ownership, visibility, single-tenant split, storage, credential,
      base-salary wording, offer→hire transaction, Alembic, CI, dependencies, RBAC). Payroll inputs (item 7) may be
      deferred only if payroll is run in parallel/dry-run.
- [ ] The pilot runs on its **own** Render service + Oracle schema; the shared demo holds no customer data.
- [ ] Payroll is **parallel/dry-run** with a written reconciliation; no statutory claims.
- [ ] Marketing and contracts remove "multi-tenant", "SOC 2", "compliant payroll" until evidenced.
- [ ] A named incident contact and a tested restore path exist.
- [ ] Budget is raised to at least **$7–35/month** (or the cold-start/storage risk is accepted in writing).

### If those conditions cannot be met: **pause and fix foundations first.**

Do not take a paying customer who expects compliance or statutory payroll. The gap is not effort — it is
certification, legal review and jurisdiction-specific payroll expertise that a solo engineer cannot supply at $0.
