# Assets module — integration snippets (team-a)

The Assets module was built under an exclusive-files constraint: no shared
file (`api.py`, `models/__init__.py`, `main.py`, `App.tsx`, router, payroll,
offboarding, audit core) was touched. Everything below is the **complete**
set of edits the integrator needs to wire it in. All snippets are additive.

Branch: `team-a-assets` (base `c64edc5233ce366f021e462676e5aaae2b0000ab`).

## Files delivered

Backend (`backend/`):
- `app/models/assets.py` — `Asset`, `AssetAssignment` (+ shared CHECK texts)
- `app/schemas/assets.py`
- `app/services/assets_service.py` — FSM + custody rules; stages chained
  audit on the session, endpoint commits once (same transaction)
- `app/api/v1/endpoints/assets.py` — router (not yet registered)
- `app/api/v1/endpoints/test_assets.py` — 97-check suite (standalone + pytest)
- `migrations/versions/0046_assets.py` — chains from `0045_payroll_pipeline_run_type`
  (the head at build time; re-chain if another module lands a head first)

Frontend (`frontend/`):
- `src/pages/Assets.tsx` — register + custody management (HR/Admin)
- `src/pages/MyAssets.tsx` — own custody + self-only acknowledgement
- `src/pages/Assets.test.tsx` — 18 vitest checks

## 1. `backend/app/api/v1/api.py`

Add `assets` to the endpoint import block (after `expenses`):

```python
from app.api.v1.endpoints import (
    ...,
    expenses,
    assets,
    ...
)
```

Register the router (next to the expenses registration):

```python
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
```

## 2. `backend/app/models/__init__.py`

Add (near the expenses import):

```python
from .assets import Asset, AssetAssignment
```

## 3. `frontend/src/App.tsx`

Lazy imports (near line 52, beside `Offboarding`):

```tsx
const Assets = lazy(() => import("@/pages/Assets"))
const MyAssets = lazy(() => import("@/pages/MyAssets"))
```

Flat protected route (beside `/offboarding`, ~line 217):

```tsx
<Route path="/assets" element={<ProtectedRoute><Assets /></ProtectedRoute>} />
<Route path="/my-assets" element={<ProtectedRoute><MyAssets /></ProtectedRoute>} />
```

Tenant-scoped routes (inside `<Route path="/t/:slug/*">`, beside
`<Route path="offboarding" ...>`, ~line 412):

```tsx
<Route path="assets" element={<Assets />} />
<Route path="my-assets" element={<MyAssets />} />
```

## 4. Navigation (optional, integrator's choice)

`frontend/src/components/shell/WorkspaceRail.tsx` (~line 264, beside
Offboarding):

```tsx
{ label: "Assets", to: "/assets", icon: Briefcase },
{ label: "My Assets", to: "/my-assets", icon: Briefcase },
```

`frontend/src/components/Layout.tsx` breadcrumb (~line 374): add
`pathname.startsWith("/assets")` / `"/my-assets"` branches if breadcrumbs
are wanted.

## 5. Offboarding consumption (read-only, no offboarding edit required)

`GET /api/v1/assets/clearance/{employee_id}` (HR/Admin/Manager, visibility
scoped) returns:

```json
{
  "employee_id": 7,
  "clear": false,
  "outstanding_count": 1,
  "outstanding": [
    {"assignment_id": 12, "asset_id": 3, "tag": "AST-0002",
     "name": "Laptop Two", "assigned_at": "...", "acknowledged_at": null}
  ]
}
```

It writes nothing on either side. The offboarding team may call it from
their checklist/progress UI or gate completion on `clear == true`; that
edit belongs to them.

## 6. Contract summary (as implemented)

- Tag unique **per tenant** (case-insensitive in-app; DB
  `uq_assets_tenant_tag` on `(tenant_id, tag)`).
- Statuses `in_stock / assigned / maintenance / retired / lost`; every
  illegal move is `409 invalid_state_transition` (shared error envelope).
- Assign: only `in_stock`, same-tenant **Active** employee, single open
  assignment per asset (`409 asset_already_assigned` /
  `employee_not_active`); new spells start unacknowledged.
- Ack: `POST /assets/assignments/{id}/ack` — self-only (403 for everyone
  else, including admins), single-shot (409), closed spells 409.
- Transfer: closes the open spell (`close_reason=transferred`) and opens a
  new unacknowledged spell in one transaction; re-ack required.
- Return: condition `good→in_stock`, `damaged→maintenance`, `lost→lost`;
  records condition on the closed spell.
- Maintenance: start only from `in_stock` (blocked 409 while assigned);
  complete → `in_stock`. Retire from `in_stock|maintenance`; final.
- Tenant: lists filtered, foreign rows 404, conflicting client tenant id
  409 `tenant_mismatch` (shared tenancy dependency).
- Roles: HR/SuperAdmin manage; Associate own-only reads; Manager reporting
  line; PayrollViewer 403.
- Audit: every write stages a chained entry (`record_audit`) and commits
  once with the mutation; refused moves leave no audit row.

## 7. Test commands

```bash
# backend (from backend/)
python3 app/api/v1/endpoints/test_assets.py     # 97 checks
# or: pytest app/api/v1/endpoints/test_assets.py

# frontend (from frontend/)
npx vitest run src/pages/Assets.test.tsx        # 18 tests
npm run typecheck
```

The backend suite mounts the router itself (integration not wired), builds
its own schema, and exercises migration 0046 up/down/re-up on a scratch
SQLite database via `scripts.migrate`.