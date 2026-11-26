# Documents UI — build contract (frontend only, backend untouched)

Base: main @ 25664a2. Branch: agent/ux/documents-contract. Risk tier: 2 (read/write UI on live endpoints, no schema/storage change).

## 0. Verified backend evidence (all read 2026-11-26, do not re-derive)

- `backend/app/api/v1/endpoints/core_hr.py:454` GET `/employee-documents` — list, optional `?employee_id` only filter; `WORKFORCE_ROLES`; visibility-scoped.
- `:464` POST `/employee-documents` — create; `ADMIN_ROLES`; seeds `DocumentVersion(v1)` + `record_audit("create_employee_document")`.
- `:488` GET `/employee-documents/{id}/versions` — history oldest-first; `WORKFORCE_ROLES` + `ensure_can_view_employee`.
- `:509` POST `/employee-documents/{id}/versions` — new version, bumps `current_version`; `ADMIN_ROLES`; 409 on concurrent version.
- `:557` POST `/employee-documents/{id}/ack` — once per account, 409 `already_acknowledged`; `WORKFORCE_ROLES` + mirror record.
- `backend/app/main.py:338` GET `/api/v1/files/{path}` — authenticated download; appends `DocumentAccessLog` when `storage_key` matches.
- `backend/app/models/core_hr.py:120-152` `EmployeeDocument`: `document_type` (NOT `category` — no category column), `file_name`, `storage_url`, `storage_key`, `current_version`, `retention_until`, `status` ∈ {Active, Archived, Expired} (read-only, no PATCH), `expiry_date`, `uploaded_at`. `:164` `DocumentVersion` append-only; `:191` `DocumentAck` unique (doc,user); `:217` `DocumentAccessLog` write-only from download route, no viewer endpoint.
- `backend/app/models/job_queue.py:36-46` `JobType` = 10 values; NO expiry-reminder job exists. Expiry today = `services/data_quality.py:619` `documents.expiring` DQ check + `retention/documents.py` sweep only.
- `backend/app/storage/backends.py:260` `get_storage()`: default `LocalStorage(LOCAL_STORAGE_DIR)`; OCI opt-in; `s3` raises without R2 config. LP-DOC-003 stays BLOCKED — no storage work here.
- Frontend today: no standalone library (matrix: People.tsx + ess/ESSHub.tsx only; `DocumentsExpiry.tsx` is a settings page, not a library). Route convention `App.tsx` `/admin/<slug>` + `ProtectedRoute roles=["SuperAdmin","HR"]`. Page-kit exemplar (`CustomFields.tsx`, `DocumentsExpiry.tsx`): `Layout` + `PageHeader` + `SectionCard` + `@/components/ui` (`LoadingRegion`, `TableSkeleton`, `RetryableAlert`, `EmptyState`) + `@/lib/api` + `useAuth`/`useTenant`.

## 1. Goal + scope

Ship a standalone, read-mostly document library UI for HR operators: browse employee documents, associate to employee, capture type/metadata/expiry, upload (create), download, view version history, renew by uploading a new version, acknowledge, and display status/expiry/audit — using ONLY the six endpoints above.

Requirement↔endpoint mapping (exhaustive — nothing else may be called):
| # | Requirement | Endpoint |
|---|-------------|----------|
| R1 | Library list | GET `/employee-documents` |
| R2 | Filter by employee | GET `/employee-documents?employee_id=` (only server filter) |
| R3 | Upload / associate + metadata (`document_type`, `file_name`, `storage_url`, `expiry_date`, `retention_until`) | POST `/employee-documents` |
| R4 | Version history | GET `/employee-documents/{id}/versions` |
| R5 | Renewal = new version | POST `/employee-documents/{id}/versions` |
| R6 | Acknowledge | POST `/employee-documents/{id}/ack` |
| R7 | Download | GET `/api/v1/files/{path}` (anchor to `storage_url`) |
| R8 | Status/expiry display | Read `status`, `expiry_date` off R1 payload; expiry badge computed client-side (30-day rule) |
| R9 | Audit display | Surface `record_audit` outcome strings only (no endpoint; hash-chain read is out of scope) |
| R10 | Client-side search/filter (type/status/expiry bucket) | In-memory over R1 payload (no server search exists) |

`document_type` is the category surrogate (values: Contract, ID, Tax, Certificate, Policy, Other per model). No `category` field exists — UI must not invent one.

## 2. Acceptance criteria (12, each independently testable)

1. Route `/admin/documents` renders for SuperAdmin/HR and is hidden/denied for other roles (ProtectedRoute).
2. Library table lists all documents from R1 with columns: employee, type, file, version (`current_version`), status, expiry, uploaded_at.
3. Employee filter calls R2 with `?employee_id=` and shows only that employee's rows.
4. Text/type/status/expiry-bucket filters work fully client-side with no additional network call.
5. Upload form (employee_id, document_type, file_name, storage_url, expiry_date, retention_until; status defaults Active) POSTs R3, shows 201 row, and writes nothing else.
6. Non-admin upload attempt is blocked in UI and the API's 403 surfaces as an error alert (no silent fail).
7. Version history panel per document lists R4 rows oldest-first with version_no, file_name, uploaded_by, uploaded_at.
8. Renewal uploads via R5 only; after success `current_version` increments and the history panel refreshes.
9. Acknowledge button calls R6; success shows ack; repeat ack shows the 409 `already_acknowledged` message.
10. Download link points at the document's `storage_url` (R7); no public/guessable URL is constructed in UI.
11. Expiry badge rule (client-side, 30-day threshold): Expired (past date or status=Expired) / Expiring ≤30d / Valid; no job, push, or email is scheduled.
12. All states covered: loading skeleton, empty (no documents), per-panel error with retry, role-denied EmptyState.

## 3. Explicit NO-GO list (STOP and report instead of building)

- Access-log viewer (no GET endpoint for `DocumentAccessLog` exists).
- Push/email expiry reminders (no `JobType` for it; DQ check + sweep are backend-owned).
- Server-side search beyond `employee_id` (list endpoint has no other filter).
- Status PATCH/DELETE/archive endpoint (none exists; status is read-only display).
- Any storage change (backend, bucket, `get_storage`, migration) — LP-DOC-003 BLOCKED stays out.
- Any backend file edit whatsoever (frontend-only slice).

## 4. File ownership

- NEW: `frontend/src/pages/documents/DocumentsLibrary.tsx` (page; may split into `components/` under same dir, no other dirs).
- NEW: `frontend/src/lib/documents-library.test.ts` (vitest: badge rule, client filters, api-path constants).
- EDIT: `frontend/src/App.tsx` — add lazy import + single `/admin/documents` route ONLY.
- Forbidden: everything else. No backend, no store, no CSS system, no nav-rail changes.

## 5. Test plan (backend untouched)

`npm run test -- documents-library` (vitest) + `npm run typecheck` + `npm run build` + grep `employee-documents|/api/v1/files` asserts the six paths only; routes test asserts `/admin/documents` resolves. No pytest required (no backend change).

## 6. Rollback

Revert the one route line in `App.tsx` + delete `frontend/src/pages/documents/`; no data migration involved.

## 7. Open decisions — recorded as RESOLVED per lead

New `/admin/documents` route (not extending DocumentsExpiry) · renewal = new version via R5 (no renewal endpoint) · expiring-soon = 30 days client-side · DOC-003 storage out of scope.
