# Shared Error Contract

**Status:** approved (Gate 0B)
**Owner:** coordinator
**Applies to:** every HTTP endpoint in `backend/app/api/v1/endpoints/`, every background
job, every generated API client, and every UI error surface.

This is the **one** error envelope and the **one** code list for the whole system.
If a lane needs a new error, it adds a row to the code list in this file *first*
and then raises it. No lane may invent a private error shape, return a bare
string `detail`, or return a stack trace.

---

## 1. The envelope

Every non-2xx response body is exactly this object. No top-level keys other
than `error`. No extra keys inside `error` other than the six below.

```json
{
  "error": {
    "code": "employee_not_found",
    "category": "not_found",
    "message": "Employee not found",
    "retryable": false,
    "details": {},
    "request_id": "01J8Z9K2QF3M7N4P0R5S6T7V8W"
  }
}
```

| Field | Type | Required | Meaning |
|---|---|---|---|
| `code` | string | yes | Stable machine-readable identifier. Snake_case. Clients branch on this. **Never prose. Never changes meaning once published.** |
| `category` | enum | yes | One of the eight categories in §2. Drives generic client behaviour (retry, re-auth, permission screen). |
| `message` | string | yes | Safe to display to a user. No stack traces, no SQL, no hostnames, no DSNs, no record ids that would confirm an object exists. |
| `retryable` | boolean | yes | Whether the *identical* request may succeed later. `true` only for `dependency`, `rate_limit`, `internal`. |
| `details` | object | yes | Structured, machine-readable context. Empty object `{}` when there is nothing to add. Contents MUST NOT contain personal data (see §5). |
| `request_id` | string | yes | Correlates the response with the server log line. Echoed in the `X-Request-ID` response header. The user can quote it. |

### Rules

1. **`code` is a contract.** Renaming a published code is a breaking change and
   requires a coordinator change request.
2. **`message` is not a contract.** It may be reworded. Clients MUST NOT parse
   `message`.
3. **`details` is a contract for the codes that populate it.** A code that
   documents a `details` shape keeps that shape. See §4.
4. **404 vs 403.** If revealing existence would leak information, respond
   `404 not_found` rather than `403 forbidden`. The `visibility.py` module
   already does this for employee-scoped reads.
5. **No `detail` key.** FastAPI's default `{"detail": ...}` shape is banned.
   The `http_exception_handler` in `backend/app/core/errors.py` already renders
   ordinary `HTTPException` into this envelope, so an endpoint that raises a
   plain `HTTPException` still conforms — but it should raise `ApiError` so the
   `code` is meaningful.

---

## 2. Categories

| Category | HTTP status | `retryable` default | Client behaviour |
|---|---|---|---|
| `validation` | 422 | `false` | Show field errors. Do not retry. |
| `auth` | 401 | `false` | Trigger the single refresh attempt, then sign out. |
| `permission` | 403 | `false` | Render a permission state. Never a blank screen. Never a 404-as-blank. |
| `not_found` | 404 | `false` | Show "not found". Do not reveal whether the object exists. |
| `conflict` | 409 | `false` | Show the conflict message; offer reload. |
| `concurrency` | 409 | `false` | Show "someone else changed this"; offer reload. |
| `dependency` | 503 | `true` | Show "temporarily unavailable"; offer retry. Send `Retry-After`. |
| `rate_limit` | 429 | `true` | Show "try again shortly"; honour `Retry-After`. Send `Retry-After`. |
| `internal` | 500 | `true` | Show a generic message plus the `request_id`. Never show internals. |

`401` responses MUST carry the `WWW-Authenticate: Bearer` header.
`429` and `503` responses MUST carry a `Retry-After` header.

---

## 3. Code list

Every code the API can return. `app/core/errors.py` is the implementation;
this table is the contract and the two must agree. CI checks that every
`ApiError(...)` / `validation(...)` / `not_found(...)` / `forbidden(...)` /
`conflict(...)` / `unavailable(...)` / `internal(...)` call site in the backend
uses a code from this list.

### 3.1 validation — 422

| Code | `details` shape | Raised when |
|---|---|---|
| `validation_error` | free-form (field errors) | Request body or query failed schema validation. |
| `invalid_state_transition` | `{from, to}` | An entity was moved to a state its rules forbid (e.g. finalised pay run edited). |
| `reference_not_found` | `{entity, id}` | A payload named a master-data reference (a department, job, location or position id) that does not exist. `entity` names what should have resolved and `id` is the value that was sent; the field that carried it is in the message. The import module has a row-level code of the same name (§3.10) — that one appears in a row-error report, this one in the HTTP envelope. |
| `password_policy_violation` | `{violations: [string]}` | Password fails the policy in `backend/app/core/password_policy.py`. |
| `password_reuse` | `{}` | Password matches one of the last N. |
| `password_breached` | `{}` | Password appears in the local breached-password list. |
| `mfa_required` | `{}` | The operation needs a second factor that is not yet satisfied. |
| `mfa_invalid_code` | `{}` | TOTP code rejected. |
| `mfa_recovery_code_invalid` | `{}` | Recovery code rejected. |
| `import_header_unknown` | `{unknown: [string], expected: [string]}` | CSV contained headers that are not in the alias table. |
| `import_row_invalid` | `{row: int, field: string, reason: string}` | A CSV row failed validation. |
| `import_confirm_token_invalid` | `{}` | The dry-run confirmation token does not match the dry-run result hash. |
| `invalid_idempotency_key` | `{}` | The `Idempotency-Key` header is empty or longer than 200 characters. |
| `rule_pack_not_verified` | `{jurisdiction, pay_date, pack_status, required: [string]}` | An operation needs a rule pack that is not `verified`, or one that cannot be read. `pay_date` is the date the pack has to cover; `pack_status` is what was found — `absent`, `draft`, `pending_verification`, `superseded`, or `verified` when the pack is verified but the engine cannot read it; `required` is the list of the checks that have to be satisfied before the operation can proceed. The refusal is the product's honesty guarantee: a pay figure is never computed from a rule that has not been verified, so the message says which pack has to be verified and by whom. |
| `rule_pack_missing` | `{jurisdiction}` | No rule pack exists for the jurisdiction. |
| `forecast_insufficient_history` | `{series, weeks_available, weeks_required}` | Forecast window is below the configured minimum. |
| `solver_infeasible` | `{unfilled: [object]}` | The roster solver could not satisfy a hard constraint. |
| `module_dependency_unmet` | `{module, requires: [string]}` | A module was enabled without its dependencies. |
| `tenant_mismatch` | `{}` | A client-supplied tenant id conflicts with the tenant resolved from the JWT claim (`tenant`, fallback `tid`) or the verified hostname mapping. Refused 422/403 so a caller cannot probe whether another tenant exists. |

### 3.2 auth — 401

| Code | `details` shape | Raised when |
|---|---|---|
| `unauthenticated` | `{}` | Missing, malformed, expired or invalid access token. |
| `invalid_credentials` | `{}` | Wrong username or password. **Identical response for unknown user and wrong password** — no user enumeration. |
| `refresh_token_invalid` | `{}` | Refresh token unknown, expired, already rotated, or revoked. |
| `refresh_token_reused` | `{}` | A rotated refresh token was presented again. **Revokes the whole token family.** |
| `tenant_unresolvable` | `{}` | No tenant could be resolved from the JWT `tenant`/`tid` claim or the verified hostname mapping. Fail closed: 401/403, never a default tenant. |

### 3.3 permission — 403

| Code | `details` shape | Raised when |
|---|---|---|
| `forbidden` | `{}` | The role is not permitted to perform the action. |
| `insufficient_scope` | `{required: [string]}` | The action requires a scope the caller lacks. |
| `outside_visibility_scope` | `{}` | The record is outside the caller's visibility scope. |
| `separation_of_duties` | `{conflicting_role}` | The caller holds a role that conflicts with the action (e.g. approving their own pay run). |
| `mfa_required_for_role` | `{role}` | The caller's role mandates a second factor. |
| `password_change_required` | `{}` | Identity established, but the account must replace an administrator-set or bootstrapped password before using the API. Only `GET /auth/me`, `POST /auth/password` and `POST /auth/logout` remain reachable. |
| `account_locked` | `{retry_after_seconds}` | Repeated failed sign-ins locked the account. Only returned **after** the correct password was supplied, so it does not reveal whether an account exists. Sends a `Retry-After` header. |
| `account_disabled` | `{}` | The account is deactivated. |
| `break_glass_expired` | `{grant_id, ttl_minutes}` | A break-glass grant has passed its TTL (max 480 min, default 240 min) and can no longer be used. 403. |
| `break_glass_not_granted` | `{actor, target}` | No active break-glass grant exists for this actor on the target tenant. Break-glass is not usable for SuperAdmin's own tenant or for FSM/registry modification. 403. |

### 3.4 not_found — 404

| Code | `details` shape | Raised when |
|---|---|---|
| `not_found` | `{}` | The object does not exist, or is not visible to the caller. |
| `employee_not_found` | `{}` | Employee record missing or invisible. |
| `record_not_found` | `{entity}` | Generic entity missing. |
| `job_not_found` | `{}` | Background job unknown. |
| `preset_not_found` | `{preset}` | Preset id unknown. |
| `rule_pack_not_found` | `{pack_id}` | Rule pack unknown. |

### 3.5 conflict — 409

| Code | `details` shape | Raised when |
|---|---|---|
| `conflict` | `{}` | Generic uniqueness or state conflict. |
| `duplicate_natural_key` | `{entity, value}` | A master-data record with the same natural key (its unique code) already exists. |
| `reference_in_use` | `{entity, id, dependents: [{entity, count}], alternative}` | A master-data record is deleted while other rows still point at it. `dependents` names what points at it and how many rows, so the client can say what has to move first; `alternative` names the operation that is allowed instead — `archive` (set `is_active` to `false`). A deletion that is refused writes nothing. |
| `idempotency_key_reuse` | `{original_request_id}` | The idempotency key was reused with a different payload. |
| `request_in_flight` | `{}` | An identical request is still being processed. Wait for it to finish before retrying. |
| `pay_run_already_finalised` | `{pay_run_id}` | A finalised pay run cannot be modified. |
| `roster_already_published` | `{version}` | The roster version is published and immutable. |
| `leave_insufficient_balance` | `{leave_type, requested, available}` | Not enough leave balance. |
| `leave_overlaps_existing` | `{existing_request_id}` | The request overlaps an approved or pending request. |
| `ledger_reduction_refused` | `{entity, key, column, available}` | An import would lower a leave balance. The ledger records what a balance **gains** — an entitlement, a carry-over, a usage — so a file that takes days off is refused rather than written into the cached columns behind the ledger's back. A reduction is a reversal, and a reversal is a deliberate act with an author, not a side effect of a file. |
| `ledger_no_movement` | `{entity, key, column}` | An import would leave a leave balance with no ledger row behind it, which is a balance the reconciliation cannot see. A balance of zero days has no history, and historyless balances are refused. |
| `timesheet_locked` | `{period_end}` | The timesheet period is locked by a payroll cut-off. |
| `swap_violates_constraints` | `{constraints: [string]}` | A swap request breaks a hard constraint. |
| `invalid_tenant_transition` | `{from, to}` | A tenant lifecycle move is illegal for the current FSM state (e.g. `Active` → `Archived` without `Deprovisioning`). 409. |

### 3.6 concurrency — 409

| Code | `details` shape | Raised when |
|---|---|---|
| `concurrent_update` | `{entity, id}` | The row changed since it was read. Reload and retry. |
| `optimistic_lock_failed` | `{}` | Version column mismatch. |
| `lease_lost` | `{job_id}` | A background job lost its lease to another worker. |

### 3.7 dependency — 503

| Code | `details` shape | Raised when |
|---|---|---|
| `dependency_unavailable` | `{}` | The database or another required service is down. |
| `storage_unavailable` | `{}` | The object storage backend is unreachable. |
| `solver_timeout` | `{time_limit_seconds, unfilled: [object]}` | The roster solver hit its time limit. **Must carry the unmet-slot list.** |
| `malware_scanner_unavailable` | `{file_type}` | No malware scanner is configured, so uploads of that type are disabled. |
| `rule_pack_loader_failure` | `{pack_id, reason}` | A rule pack failed schema validation or signature check. |
| `secret_decryption_failed` | `{}` | An encrypted field could not be decrypted — usually a rotated or missing encryption key. **Never returns the ciphertext or plaintext unchanged.** |
| `secret_encryption_unconfigured` | `{}` | No field-encryption key registry is configured, so a secret cannot be stored safely. |

### 3.8 rate_limit — 429

| Code | `details` shape | Raised when |
|---|---|---|
| `rate_limited` | `{retry_after_seconds}` | The caller exceeded a rate limit. |
| `login_attempts_exceeded` | `{retry_after_seconds}` | Login attempt budget spent for this IP. |
| `export_quota_exceeded` | `{}` | Too many exports/imports in a period. |

### 3.9 internal — 500

| Code | `details` shape | Raised when |
|---|---|---|
| `internal_error` | `{}` | Unexpected exception. Technical detail is logged server-side only. |
| `audit_write_failed` | `{}` | The audit record could not be written. **The whole transaction is rolled back.** |
| `job_execution_failed` | `{job_id, attempt}` | A background job raised. Details are on the job record. |
| `migration_required` | `{current_revision, head_revision}` | The database schema is behind the code. |

---

### 3.10 import row-level — private to the import module (not HTTP envelope codes)

These codes describe a single row of an imported file, not an HTTP
response. They are raised by `backend/app/imports/errors.py` and returned
inside the `rows[].errors[].code` field of an import result; they never
appear as the top-level `error.code` of an HTTP response. They are listed
here so the import module's vocabulary is part of the shared contract and
so a client can branch on a row's `code` the same way it branches on an
HTTP `error.code`.

| Code | Category | Raised when |
|---|---|---|
| `unknown_headers` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |
| `missing_required` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |
| `invalid_integer` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |
| `invalid_number` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |
| `invalid_boolean` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |
| `invalid_date` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |
| `invalid_datetime` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |
| `invalid_time` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |
| `invalid_email` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |
| `invalid_enum` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |
| `too_long` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |
| `below_minimum` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |
| `above_maximum` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |
| `reference_not_found` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |
| `cross_file_reference_not_found` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |
| `duplicate_in_file` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |
| `duplicate_exists` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |
| `inconsistent_values` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |
| `too_many_rows` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |
| `file_too_large` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |
| `not_utf8` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |
| `malformed_csv` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |
| `empty_file` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |
| `no_header` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |
| `write_failed` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |
| `too_many_fields` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |
| `too_few_fields` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |
| `ledger_reduction_refused` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |
| `ledger_no_movement` | row-level | Row-level import validation or write failure. See `backend/app/imports/errors.py`. |

The two codes that also surface as HTTP `409 conflict` responses are
`ledger_reduction_refused` and `ledger_no_movement` (§3.5); every other code
in this table is row-level only.

## 4. `details` conventions

- `details` keys are snake_case.
- Array-valued keys hold arrays of objects or strings, never nested envelopes.
- `details` MUST NOT contain: names, email addresses, phone numbers, salary
  amounts, national identifiers, bank details, medical information, or any
  free-text value copied from a record. Use a reference id, never the value.
- Where a value must be shown but is sensitive (e.g. an email in a CSV error
  report), it is **masked** at the point of formatting — see
  `docs/IMPORT_TEMPLATES.md` — and never placed in `details`.

---

## 5. Personal data in errors

Error responses, error logs and error `details` are covered by the same
redaction rules as the rest of the platform:

- No names, salary figures, national IDs, bank data, health information.
- No raw SQL, no DSN, no hostnames, no file-system paths outside the app root.
- No stack traces, ever, to a client.
- Masked personal values (e.g. `a***@e***.com`) are permitted where a user
  needs to recognise their own record; the masking helper is the only way to
  produce them.

---

## 6. Background job errors

A background job does not return HTTP errors. It records the failure on the
job row using the same `code` vocabulary, plus:

| Job field | Meaning |
|---|---|
| `error_code` | A code from this list. |
| `error_message` | Safe for display. |
| `error_details` | Same rules as the HTTP `details`. |
| `attempts` | Number of attempts made. |
| `last_error_at` | Timestamp of the most recent failure. |

After `max_attempts` the job moves to `dead` and becomes visible in the
dead-letter view. A dead job is never silently discarded.

---

## 7. Client obligations

Generated clients (`packages/api-client`) MUST:

1. Type the error body as `ErrorEnvelope` from this file.
2. Branch on `code` (never on `message`).
3. On `401`, attempt **one** refresh, then sign out.
4. On `403`, render a permission state.
5. On `503`/`429`, offer retry and honour `Retry-After`.
6. Surface `request_id` in every error surface so a user can quote it.

The UI MUST render `message` verbatim for `validation` and `conflict` codes,
and a generic message plus `request_id` for `internal`.
