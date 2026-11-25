---
# Feature: tenant-workplace-routes

**Feature ID:** tenant-workplace-routes
**Contract path:** spec/features/tenant-workplace-routes/contract.md
**Tier:** Tier 2 (new routes across App.tsx; affects tenant navigation; tests required via E2E)

## Goal
Add tenant-scoped route wrapper in App.tsx so /t/:slug/* renders the app shell inside tenant context. "Open workplace" must successfully open the tenant dashboard.

## Acceptance criteria

**AC-01** Add a `<Route path="/t/:slug/*">` wrapper in `frontend/src/App.tsx` that renders `<ProtectedRoute><TenantLayout /></ProtectedRoute>` with nested routes for all workspace pages.

**AC-02** Create `frontend/src/components/TenantLayout.tsx` — a layout wrapper that wraps children in `<Layout>` and ensures tenant context is active.

**AC-03** The "Open workspace" link in `ClientOnboarding.tsx` (`/t/{slug}/dashboard`) successfully renders the dashboard inside tenant context — no blank page.

**AC-04** All existing global routes (`/dashboard`, `/people`, etc.) continue to work unchanged — no regression.

**AC-05** `npm run typecheck && npm run build` pass in frontend/

**AC-06** All changes committed to main

## Files to touch
- `frontend/src/App.tsx` — add `/t/:slug/*` route wrapper with nested workspace routes
- `frontend/src/components/TenantLayout.tsx` — new file: tenant-scoped layout wrapper

## Test command
Frontend: `npm run typecheck && npm run build`
