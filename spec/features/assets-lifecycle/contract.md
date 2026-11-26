# Feature: assets lifecycle gap (backlog item C) — UI completion slice
Verified HEAD: LibrePeople main = 257344ecc383b4eebef0d9fe6136bc266b5b1895. Backend FSM already complete — scope is UI completion only, no backend changes.
## Behavior
HR/Admin manage the full custody FSM from the register; employees ack own custody in My Assets; managers get clearance visibility. All moves reuse existing endpoints; illegal moves surface the server 409/403 verbatim.
## Acceptance criteria
1. Register filters work: GET /assets?status=&category= wired to dropdowns; selecting assigned shows only assigned rows (extends Assets.tsx:117-133).
2. Metadata edit works: PATCH /{asset_id} (tag/name/category/description/serial) from Manage panel; status never editable.
3. Manage panel shows per-asset custody history via GET /assets/assignments?asset_id= with ack/close-reason/condition columns.
4. Clearance view works: HR/Manager enters employee id, GET /assets/clearance/{id} renders outstanding list or "clear".
5. Damage/loss/disposal flow: return dialog requires condition (good→in_stock, damaged→maintenance, lost→lost); retire requires reason confirm; retired/lost offer no actions.
6. Tenant/role/audit preserved: non-admin sees only custody scope; ack button only on open+unacked own spell, 403 otherwise; every write stays atomic with audit row.
## Non-goals
No backend/FSM/schema/migration changes. No new pages or routes.
## Interfaces / data
Existing endpoints only (see contract evidence in builder notes). No new API, no migration, backwards compatible. File ownership: extend frontend/src/pages/Assets.tsx and frontend/src/pages/MyAssets.tsx (shared types only); extend frontend/src/pages/Assets.test.tsx. No new dirs.
## Test plan
typecheck + vitest Assets (extend pure-rule tests: filter params, edit payload excludes status, clearance rendering, retire-confirm); manual: assign→ack→transfer→re-ack→return(damaged)→complete→retire; cross-tenant read = 404; manager clearance read-only.
## Risk tier
2 (normal; UI-only, no migration, irreversible FSM moves stay server-guarded with 409).
## Rollback
Revert frontend commit; no data migration involved.
## NO-GO list (missing backend — STOP, do not invent)
Depreciation; maintenance records/schedule/cost; category master-data; incident reports; disposal method/sale value; export/aggregate reporting.
## Open decisions — RESOLVED by lead 2026-11-26
(1) gap register is binding source where CSV lacks LP-ASM rows; (2) UI-only confirmed, NO-GO items deferred to separate backend slices.
