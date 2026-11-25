# Target Architecture — Karmathy HCM

**Status:** Phase 0 decision record (discovery only — no code, schema, or migration changes)
**Date:** 2026-11-06
**Branch:** `feature/target-architecture-doc` off `main` (base commit `3850614`)
**Related:** `docs/coordination/GATE_0_DECISIONS.md`, `HCM_SaaS_Agent_Requirements.md`, `docs/DEPLOYMENT.md`

This document records the target architecture for Karmathy HCM (Human Capital Management — an HR system for small-to-mid businesses covering hire, org structure, time and leave, payroll, employee self-service, documents, compliance and reports). It consolidates the Gate 0 decisions into one view: logical layers, data flow, tenant isolation model, forecasting approach, and deployment topology. It is a Phase 0 document: it records decisions and rationale only. Nothing here mutates production data or schema.

## 1. Decisions summary

| Decision | Value | Source / rationale |
|---|---|---|
| Data tenancy | **Schema-per-tenant**: one Oracle schema per customer, within one shared Oracle Autonomous Database (ADB) instance | `GATE_0_DECISIONS.md` §1.1 — approved. Rejects shared schema with tenant discriminator, database-per-tenant, and hybrid (see §6) |
| Backend framework | FastAPI 0.111.0, Python 3.11, SQLAlchemy 2.0.29, Alembic 1.13.1, Pydantic 2.7.4 | Retained; existing codebase is FastAPI; no repository evidence for Spring Boot (`GATE_0_DECISIONS.md`, `info.md` §5) |
| Frontend | React 18 + TypeScript + Vite 5 + Tailwind v3 + Radix + TanStack Query/Table/Virtual | Existing stack; built and deployed on Render |
| Oracle driver | `oracledb` thin mode, mTLS required, wallet files (`tnsnames.ora`, `sqlnet.ora`, `ewallet.pem`) | `backend/requirements.txt`, `docs/DEPLOYMENT.md` |
| External LLM | **None.** Default build has no LLM call at all | `GATE_0_DECISIONS.md` §1.5 |
| Forecasting / optimisation | Statistical methods only: `statsmodels` (Holt-Winters), `ortools` CP-SAT (roster solver), `numpy`/`pandas` (data handling); no gradient-boosted or neural models | `GATE_0_DECISIONS.md` §1.6 |
| Billing | **Deferred — out of scope for the pilot.** No billing subsystem, no payment integration, no plan-based entitlement enforcement at launch. Tenant provisioning is a manual operator step; subscription/plan selection is deferred until a customer contract exists | §4 (decision recorded here) |
| Authentication | JWT access/refresh tokens, bearer auth, MFA, forced password change on seed/admin-set accounts, no default password | `GATE_0_DECISIONS.md` §1.7, `backend/app/core/security.py` |
| Background jobs | Database-backed durable queue with leases, retry, dead-letter; one worker per deployment; `JOB_WORKER_ENABLED` | `docs/DEPLOYMENT.md` |
| Object storage | Local disk in dev/free tier (`STORAGE_BACKEND=local`); Oracle Object Storage (`oci`) for durability | `docs/DEPLOYMENT.md` known limitations |

## 2. Logical layers

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1 — Presentation                                      │
│ React SPA (Vite build, served as static files by nginx)     │
│ Five role-based homes (SuperAdmin, HR, Manager, Employee,   │
│ PayrollViewer); TanStack Query/Table/Virtual for data       │
└─────────────────┬───────────────────────────────────────────┘
                  │ HTTPS, same-origin /api/v1 (no VITE_API_URL)
┌─────────────────▼───────────────────────────────────────────┐
│ Layer 2 — API                                               │
│ FastAPI 0.111.0 + uvicorn; 80 paths / 92 operations across  │
│ 10 domains (contracts/openapi); JWT bearer auth; CORS       │
│ allow-list, allow_credentials=false; error envelope per     │
│ contracts/errors.md                                         │
└─────────────────┬───────────────────────────────────────────┘
                  │ bearer token + DB session on schema per deployment
┌─────────────────▼───────────────────────────────────────────┐
│ Layer 3 — Application services                              │
│ visibility.py / ownership checks (read filters, write gates)│
│ job queue (claim/lease/heartbeat/dead-letter), import engine│
│ rule-pack loader + verification, field encryption (versioned│
│ keys, rotatable), onboarding state machine, forecasting     │
│ service (statsmodels / ortools)                             │
└─────────────────┬───────────────────────────────────────────┘
                  │ SQLAlchemy 2.0 + Alembic migrations       │
┌─────────────────▼───────────────────────────────────────────┐
│ Layer 4 — Data tier                                           │
│ Oracle Autonomous Database (ADB), one schema per customer   │
│ Schema = tenant. Tables, indexes, sequences live in that    │
│ schema; connection targeted via DB_SCHEMA config, not code  │
└─────────────────────────────────────────────────────────────┘
```

### Layer responsibilities

**Layer 1 — Presentation.** Single-page application built with Vite; production image is a multi-stage Docker build (`npm ci && npm run build`, then `nginx:alpine` serving `dist/`). The frontend container is the edge: the browser calls `/api/v1/...` on the same origin, so no `VITE_API_URL` is needed. Role-based home screens show only what the caller's role may see; navigation never exposes a disabled feature as a visible dead option.

**Layer 2 — API.** FastAPI application (`backend/app/main.py`) registers domain routers under `api/v1`. Every one of the ~300 operations declares who may call it; the merged OpenAPI contract in `contracts/openapi/openapi.yaml` is the authority for what the code promises, and the generated OpenAPI is the authority for what the code does today (drift rule: promised-but-unserved endpoints fail CI hard). JWT access/refresh tokens; password policy, refresh rotation, lockout, forced password change.

**Layer 3 — Application services.** Stateless business logic behind the API:
- Central policy module (`visibility.py`): every read filtered by visibility, every write gated by ownership; roles enforced per operation (1,779 role-vs-operation checks in tests).
- Job queue: durable database queue; worker claims jobs with a conditional-update lease, heartbeats at a third of the lease TTL, dead-letters jobs it cannot run. One worker per deployment is the model; a second worker would be safe but adds no throughput.
- Import engine: spreadsheet import with dry run, queued background application for large files, all-or-nothing visibility, stop recorded in audit trail.
- Rule-pack loader: JSON Schema 2020-12 validation (`contracts/rules/rule-pack.schema.json`); a pack may only be `verified` by a named human against a cited source with a golden case; payroll stays disabled until a verified pack is attached.
- Field encryption: versioned, rotatable keys; sensitive values (salary, bank details, national identifiers, dates of birth) redacted before audit trail.

**Layer 4 — Data tier.** Oracle Autonomous Database. One schema per customer: a schema is an Oracle user with its own tables, so a customer's data is physically separated from another customer's without needing a second database. There is no tenant dimension in any query — a deployment serves exactly one customer, so cross-tenant queries are impossible by construction. Schema targeting is configuration (`DB_SCHEMA`), not code; schema-qualified migration running is Block 3 work per GATE_0 §1.1.

## 3. Data flow

### 3.1 Synchronous request (typical UI action)

1. User action in the React SPA (e.g. approve a timesheet, view employee directory).
2. TanStack Query issues `GET/POST /api/v1/...` to the same origin; nginx routes `/api/` to the FastAPI backend container (docker-compose VM path) or directly to the Render backend service.
3. FastAPI validates the bearer JWT, resolves the caller's role, and applies the central policy: read visibility filters and write ownership checks. Unauthorised calls return the standard error envelope (`contracts/errors.md`) with the named code.
4. SQLAlchemy 2.0 session targets the deployment's Oracle schema (`DB_SCHEMA`); statement executed against ADB over mTLS.
5. Result shaped via Pydantic schemas, returned to the browser; audit entry written for every mutation (who, what changed, hashed source address, sensitive values redacted).

### 3.2 Background job (import, forecast, roster solve)

1. Client enqueues a job (`202 Accepted`); job row inserted into the durable job queue with input payload hash.
2. The deployment's single worker polls the queue (`JOB_WORKER_POLL_SECONDS`), claims the next due job with a conditional update (lease), runs it (import engine applies all-or-nothing; forecasting service runs Holt-Winters/CP-SAT; roster solver runs CP-SAT), heartbeats during execution.
3. On completion, the result payload is stored beside the job hash (`job_result_payload`); progress served at `GET /import-export/import/{entity}/progress/{job_id}`; unrecoverable failures go to the dead-letter list with the reason, never silently retried into the same refusal.

### 3.3 Forecasting data flow (no LLM, no ML models)

Historical time/leave/roster rows → `numpy`/`pandas` frame → `statsmodels` Holt-Winters exponential smoothing produces demand forecast → `ortools` CP-SAT solves roster against hard constraints → forecast/roster rows written to the deployment schema. No model artefacts to version or retrain; no employee rows ever leave the deployment (and no external LLM is involved).

## 4. Tenant isolation model

**Chosen model: schema-per-tenant.** One Oracle schema per customer inside a single shared ADB instance (`karmkathyadb_high`, AP-Hyderabad).

| Property | How it is guaranteed |
|---|---|
| Physical separation | Each customer is an Oracle user with its own tables; another customer's rows are not in the same schema |
| No cross-tenant queries possible | No `tenant_id` column exists anywhere; every deployment connects to exactly one schema via `DB_SCHEMA` |
| Configuration, not code | Schema targeting is `DB_SCHEMA` env var; application code never branches on tenant |
| Blast radius | A bad migration or corrupt data affects one schema/customer, not all customers |
| Free-tier fit | Oracle Always Free allows two databases; one runs production, the second is headroom for staging or a noisy tenant (`GATE_0_DECISIONS.md` §1.1) |
| Network | mTLS to ADB is required; Render free tier has dynamic egress IPs so IP allow-lists are unusable — access is via mTLS only (`docs/DEPLOYMENT.md`) |

**Rejected alternatives** (compared in §6): shared schema with tenant discriminator, database-per-tenant, hybrid. The task's mandated decision stands: schema-per-tenant, not shared schema with discriminator.

### Consequence for testing
Cross-tenant leakage tests are N/A by construction — there is only ever one tenant in a database. Within-tenant role boundaries are still tested exhaustively (every role against every operation; rank-and-file employee hitting an admin URL is refused).

## 5. Billing — decision

**Billing is deferred: out of scope for the pilot. No billing subsystem is built.**

Rationale:
- The deployment model is one customer per deployment (schema-per-tenant), so there is no multi-tenant metering problem to solve at launch: no plan-based entitlement enforcement, no usage aggregation across tenants, no invoicing.
- `HCM_SaaS_Agent_Requirements.md` treats subscription/plan selection as conditional ("Select subscription/plan (if billing is in scope)").
- Payment integrations require a real external provider and a paid account; `GATE_0_DECISIONS.md` §3.3 defers SSO/SCIM/background-check integrations "with a customer contract" — the same standard applies to billing.
- Phase 0 explicitly prohibits paid cloud cost (`contract` Non-goals); the live deployment runs on Render free tier + Oracle Always Free.
- Tenant onboarding is a manual operator step (create workspace, attach preset, seed admin from `ADMIN_INITIAL_PASSWORD` env secret).

**Revisit trigger:** when the first customer contracts. At that point add subscription/plan selection and a payment integration behind the same "named provider, paid account" bar as SSO/SCIM.

## 6. Alternatives considered

| Module | Options | Selected | Why |
|---|---|---|---|
| Tenancy | Shared schema + `tenant_id` discriminator; database-per-tenant; hybrid; **schema-per-tenant** | Schema-per-tenant | Shared schema was rejected for this product: one customer per deployment means a discriminator buys nothing and adds leakage surface; database-per-tenant caps the free tier at two customers with no staging headroom; hybrid adds complexity for no current need (`GATE_0_DECISIONS.md` §1.1) |
| Architecture style | Monolith vs microservices | Monolith (one repo, one lane) | One engineer, 20–40 h/week; parallel agents writing to one repo produce merge conflicts and duplicated review (`GATE_0_DECISIONS.md` §1.2, §3.3) |
| Backend framework | FastAPI (retained) vs Spring Boot | FastAPI | Existing codebase, team skills, `oracledb` Python support; no repository evidence that Spring Boot is better (`GATE_0_DECISIONS.md`, AC-02 requires rejection to cite evidence, not preference) |
| Hosting | Render (current) vs OCI / AWS / Azure | Render free tier (deployment of record); Oracle VM path as fallback | Zero paid cost in Phase 0; ADB already on OCI; VM path exists as fallback (`docs/DEPLOYMENT.md`) |
| Forecasting | statsmodels/ortools vs gradient-boosted / neural | Statistical methods only | A trained model must be versioned, retrained and explained; none of that is affordable (`GATE_0_DECISIONS.md` §1.6) |
| AI / config assistant | External LLM vs rule engine + help index | Rule engine, no LLM | No external LLM (`GATE_0_DECISIONS.md` §1.5); LLM mode, if ever approved, gets configuration metadata only, never employee rows, behind an off-by-default flag |
| Workflow engine | Built workflow engine vs BPMN product | Built (deferred to Block 7 area) | BPMN product is a third-party integration with its own licensing/ops; deferred per `GATE_0_DECISIONS.md` §3.3 |
| Monorepo / design system | packages/ui, tokens, api-client, tenant-theme (pnpm/Turborepo) vs current `frontend/src/components/ui/` | Current layout retained | 3–5 engineer-weeks of tooling churn with no user-visible value (`GATE_0_DECISIONS.md` §3.3) |

## 7. Deployment topology

```
┌─────────────┐      HTTPS/same-origin      ┌──────────────────┐
│   Browser   │◄───────────────────────────►│  Render / Frontend│
│  (SPA UI)   │      /api/v1 on origin      │  (static site,   │
└─────────────┘      or nginx edge          │  nginx serves    │
                                            │  dist/, proxies  │
                                            └────────┬─────────┘
                                                     │ HTTPS / mTLS
                                                     ▼
                                            ┌──────────────────┐
                                            │  Render / Backend│
                                            │  FastAPI + uvicorn│
                                            │  (Docker, free)  │
                                            └────────┬─────────┘
                                                     │ oracledb thin, mTLS
                                                     ▼
                                            ┌──────────────────┐
                                            │ Oracle ADB       │
                                            │ karmkathyadb_high│
                                            │ One schema per   │
                                            │ customer (tenant)│
                                            └──────────────────┘
```

- **Primary deployment (of record):** Render free tier — `karmathy-backend` (Docker web service, free) and `karmathy-frontend` (static site, free), Singapore region; deploys triggered automatically on push to `main` (`autoDeployTrigger: commit`). Live URLs: frontend `https://karmathy-frontend.onrender.com`, backend `https://karmathy-backend.onrender.com`.
- **Fallback path:** `.github/workflows/deploy.yml` runs on every push to `main`; when VM secrets are set it pulls the commit on an Oracle VM and runs `docker compose up -d --build`. `docker-compose.yml` builds two images: backend (`backend/Dockerfile`, API on `:8000`, migrations as release step) and frontend (`frontend/Dockerfile`, multi-stage Vite build + `nginx:alpine`, proxies `/api/` to `backend:8000`). Render remains the deployment of record; the VM path is not the URL the pilot uses.
- **Database:** Oracle Autonomous Database, display name `karmkathy_adb`, DB name `KARMKATHYADB`, TNS alias `karmkathyadb_high`, mTLS required. Schema `ADMIN` today; a dedicated app user per schema is a future improvement. One schema per customer once multi-tenant onboarding is wired; schema targeting via `DB_SCHEMA`.
- **Secrets (never committed):** ADB admin password and wallet password in `~/.karmathy/` locally, Render env vars `ORACLE_PASSWORD` / `ORACLE_WALLET_PASSWORD`; `SECRET_KEY` generated by Render; Render API key in `~/.render/api_key`. Wallet files live in `backend/wallet/` (git-ignored).
- **Background jobs:** `JOB_WORKER_ENABLED` default `false`; set `true` on the backend service so queued jobs execute. One worker per deployment; result payloads stored beside job hashes; dead-letter for unrecoverable jobs.
- **Object storage:** `STORAGE_BACKEND=local` (ephemeral disk — documents lost on redeploy) for the free tier; switch to `oci` (Oracle Object Storage) for durability.
- **Known free-tier limits:** ephemeral disk, spin-down (cold start on first request), single schema today, dynamic egress IPs (mTLS only to ADB), no separate hosted staging site — release previews run locally against real Oracle.

## 8. Out of scope for Phase 0 (decision record only)

- Application code, database schema, or migrations (`contract` Non-goals).
- Production deployment changes, DNS, credential rotation, paid cloud cost.
- Phase 1–6 delivery work: tenant context, configuration studio, workflow engine, payroll rule packs, etc.
- Billing subsystem (deferred — §5).
- External LLM (rejected — §1).
- Cross-tenant `tenant_id` scoping (deferred; only if the shared-demo model returns — `GATE_0_DECISIONS.md` §3.3).
- SSO / SCIM / e-signature / background-check integrations (deferred until a customer contract).
- SOC 2 / ISO 27001 (organisational audits, not build features).

## 9. Risks and mitigations (Phase 0 decision record)

| Failure mode | Mitigation | Owner |
|---|---|---|
| Tenancy decision contradicted later (shared-schema pressure) | Record schema-per-tenant as the winning option in `DECISION_LOG.md` with rationale; any reversal needs a migration and a new Gate decision | Build coordinator |
| Schema-qualified migrations not ready (Block 3) | Block 1–2 do not depend on it; keep `DB_SCHEMA` as config now, add qualification in Block 3 | Build coordinator |
| Credential leakage reintroduced | `ci/secret_scan.py` denylist; no default password; seed reads `ADMIN_INITIAL_PASSWORD` only; forced password change on every new admin account | Build coordinator |
| Payroll runs without a verified rule pack | Payroll disabled until named-human verification with source + golden case; schema enforces, not policy | Build coordinator / named verifier |
| No staging environment (free tier) | Release previews run on laptop against real Oracle; recommend modest paid tier when real customers approach (`info.md` §7) | Owner |
| Forecasting accuracy claims without a model | Statistical methods only; no model artefacts to version; accuracy is a property of inputs, not a black box | Build coordinator |
| Billing expectation from customers | Documented as deferred; manual operator onboarding until first customer contract | Owner |
