# Single-Tenant Install — Feature Contract

Branch: `agent/feat/single-tenant` from main HEAD (`e2a2652`).
Synthetic data only. No push.

## 1. Behavior

LibrePeople runs as **one org per install**. The workspace/tenant
switcher is removed from the shell. Attribution (who did what, audit
trail, created-by/actor columns) stays exactly as-is — only the
multi-tenant switching surface is removed.

## 2. Verdicts

### REMOVE — TenantSwitcher.tsx + WorkspaceRail slot + import

- Delete `frontend/src/components/shell/TenantSwitcher.tsx`.
- Remove the `TenantSwitcher` import (`WorkspaceRail.tsx:7`) and the
  bottom-pinned `<TenantSwitcher />` slot (`WorkspaceRail.tsx:345`).

### REMOVE — `/t/:slug` mirror route + TenantLayout import + tenantPath prefixing + tenantSlugStore/tenant-slug state

- Remove the `/t/:slug/*` mirror route (`App.tsx:393`) and the
  `TenantLayout` import (`App.tsx:7`).
- Remove `tenantPath` prefixing (`frontend/src/lib/tenantPath.ts`) and
  the `tenantSlugStore` / tenant-slug state (`TenantContext.tsx`,
  `useClientId.ts`, `lib/api.ts` tenant-slug plumbing).
- `TenantLayout.tsx` is deleted once unreferenced.

### REMOVE — client registry CRUD + `/tenants` aliases + by-slug lookup

- Remove the client registry CRUD (`client_onboarding.py:98-153`:
  list/create/get/update/delete `/clients`).
- Remove the `/tenants` aliases (`client_onboarding.py:193-228`).
- Remove the public by-slug lookup (`client_onboarding.py:77-79`
  `/clients/by-slug/{slug}`).
- The per-install company settings endpoints (branding/locale) stay.

### REMOVE — break-glass cross-tenant grant scope, KEEP step-up auth

- Remove the cross-tenant grant scope (`break_glass` endpoint ~`api.py:97`
  grant lookup by `target_tenant_id`; `models/break_glass.py:37`
  `target_tenant_id` column usage in grant scope checks).
- KEEP step-up (step-up authentication / elevated-approval flow) as-is.
- No schema change: the column is untouched; only the cross-tenant
  grant-scope logic is removed.

### RENAME — TenantBranding to "Company branding", same endpoints

- `frontend/src/pages/admin/TenantBranding.tsx` becomes the
  "Company branding" screen. Same REST endpoints, same store shape.
  Only user-facing labels/copy change (`Tenant` → `Company`).

### RENAME — ModuleEntitlements / FeatureFlags to install-level flags, same store

- `ModuleEntitlements.tsx` / `FeatureFlags.tsx` become install-level
  flag screens. Same endpoints and store shape; per-tenant scoping
  copy removed.

### REMOVE — per-tenant preset usage, KEEP tenant_state.py mechanism

- Remove per-tenant preset usage (`onboarding.py:194`
  `tenant_only`/`modules_to_enable` per-tenant application).
- KEEP the `tenant_state.py` mechanism (preset diff/provenance
  machinery) unchanged.

### REMOVE — multi-source resolution / hostname mapping, single-org default

- Remove multi-source tenant resolution and hostname→tenant mapping
  (`tenancy.py:19` resolution-order block; `main.py:57-58` tenant-header
  CORS wiring).
- The install resolves to its single org by default. `X-Tenant-*`
  headers are tolerated-and-ignored (accepted, never authoritative).

### REMOVE — DEFAULT_TENANT_SLUG display rule

- Remove the `DEFAULT_TENANT_SLUG` fallback display rule (UI copy and
  any user-facing "default tenant" labeling). Backend constant may
  remain as an internal data default; it must never surface in UI.

### REMOVE — `[data-tenant]` scoping, index.css:392 + 1034-1054

- Remove the `[data-tenant]` attribute scoping: the tenant-aware dark
  surface rule (`index.css:392`) and the tenant-branding gated block
  (`index.css:1034-1054`). Company-branding variables apply
  install-wide without the attribute gate.

### KEEP (do not touch)

- `tenant_id` columns, indexes, and query criterion.
- `require_tenant`, audit writes, `ContextVar` tenant context.
- JWT reads (claims parsing stays; claims just no longer switch org).
- Org hierarchy display and per-install config.

## 3. Acceptance criteria

1. **AC-1 — `/t/:slug/*` redirects.** Any request to `/t/:slug/*`
   issues a `302` redirect to the bare path (same suffix, slug
   dropped). Covered by a redirect test.
2. **AC-2 — switcher absent.** The workspace switcher renders nowhere;
   a DOM-absent test asserts no switcher element in the shell.
3. **AC-3 — removed endpoints 404.** The removed registry/lookup
   endpoints (`/clients`, `/tenants` aliases, `/clients/by-slug/*`)
   return `404`. Covered by 404 tests.
4. **AC-4 — cross-principal access denied.** Cross-principal
   (cross-tenant-id) access returns `403`/`404`, never data. Covered
   by existing isolation tests (must stay green).
5. **AC-5 — single-org settings round-trip.** Company branding/locale
   settings round-trip (read → update → read-back) for the single org.
   Covered by a settings round-trip test.
6. **AC-6 — zero grep hits.** `grep` for the removed surface
   (`TenantSwitcher`, `/t/:slug`, `tenantSlugStore`, `by-slug`,
   `/tenants`, `target_tenant_id` grant-scope usage, `[data-tenant]`,
   `DEFAULT_TENANT_SLUG` display) returns zero hits in the shipped
   code (tests excluded where they assert absence).

## 4. Routing plan

`/t/:slug/*` → `302` to the bare path (slug segment dropped, remainder
and query preserved). `302` (not `301`) is justified: the redirect is
a compatibility shim for bookmarked/cached multi-tenant URLs during the
transition, not a permanent canonical move; a permanent `301` would
let browsers and caches pin the rewrite before the single-tenant
canonical URLs are finalized.

## 5. NO-GO list (STOP and report instead)

- A schema change or migration is needed to satisfy any verdict.
- Audit behavior (audit writes, chain, actor attribution) would change.
- An existing test breaks in a way that implies backend reliance on
  the removed surface.
- Any referenced line number proves wrong on read (do not improvise).
- Real (non-synthetic) data would be touched.

## 6. No schema / migration

No migrations. No schema changes. No data operations. `tenant_id`
columns, indexes, and constraints are untouched. Synthetic fixtures
only in tests.

## 7. Test plan

- `cd frontend && npm run typecheck` — clean.
- `cd frontend && npm run build` — clean.
- `cd frontend && npm run test:unit` (full frontend unit suite) —
  green, including the new redirect test and DOM-absent test.
- `bash ci/run_backend_tests.sh auth` + `visibility` +
  `client_onboarding` (smoke) + `break-glass`/`cross_tenant` suites
  where present — green, including the new 404 tests and the
  settings round-trip test.

## 8. Risk tier

Tier 2 (moderate): touches routing, shell chrome, and endpoint
surface across frontend and backend, but changes no schema, no audit
semantics, and no auth primitives. Rollback by revert.

## 9. Rollback

Revert the implementation commit(s). The contract commit stays as
record. No data migration to unwind (none was run).
