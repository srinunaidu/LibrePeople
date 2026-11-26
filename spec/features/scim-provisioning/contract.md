# Feature: scim-provisioning
## Behavior
SCIM 2.0 Users subset under /scim/v2/Users: list/query (filter=userName), create, update (PUT/PATCH), deactivate (active=false; no hard delete). Auth via SCIM bearer token separate from JWT. Tenant isolated per-request via resolve_tenant; idempotency on externalId; audit every mutation; rate-limited.
## Acceptance criteria
1. GET /scim/v2/Users?filter=userName eq "x" returns SCIM ListResponse scoped to request tenant only.
2. POST /scim/v2/Users with existing externalId returns 200 existing user (no duplicate); new user returns 201.
3. Missing/invalid SCIM bearer returns 401; JWT of valid user without SCIM token returns 401/403.
4. PATCH active=false deactivates (is_active=false); DELETE returns 404 (hard delete disabled).
5. Abuse test: >N req/min returns 429; every mutation writes an audit row.
## Non-goals
No Groups write, no bulk, no enterprise extensions (Groups read-only only if trivial, else excluded).
## Interfaces / data
Reuse existing scim_tokens (SCIMToken: token_hash/client_id/label/expires_at — exists, zero routes use it); NO new token table. New scim.py router + verify_scim_token dependency (sha256 compare, expiry check). User mapping: userName→username/email, externalId→new nullable users.external_id column. Uses record_audit, app.core.rate_limit.
## Test plan
pytest backend/tests/test_scim_provisioning.py -q (new: auth-bypass matrix must 401/403, tenant-isolation, idempotency, deactivate, 429). Regression: JWT auth tests.
## Risk tier
2 (normal)
## Rollback
Remove SCIM router + external_id migration; JWT paths untouched.
## Open decisions — RESOLVED by lead 2026-11-26
(1) Request-tenant scoping is sufficient (consistent with existing visibility model; no per-user tenant FK). (2) Created users: role=Associate + must_change_password=true ONLY. (3) Minimal SuperAdmin-only mint endpoint POST /scim/v2/Tokens included (else tokens can never exist).
## NO-GO (STOP and report)
Touching payroll/identity invariants; Groups write; bulk; inventing auth primitives; weakening tenant isolation.
