# Cloud E2E pack (deployed env) — AUTHORED, NOT RUN

End-to-end coverage against the **deployed** environment:

- API: `https://librepeople-backend.onrender.com` (override: `CLOUD_API_URL`)
- App: `https://librepeople-frontend.onrender.com` (override: `CLOUD_APP_URL`)

Status: specs are written and committed. They have **not been executed** —
provisioned cloud users were not available to this author. Run them when the
six synthetic users below exist on the deployed tenant.

## Files

| Spec | What it proves |
|---|---|
| `cloud-auth.spec.ts` | Each of the 6 roles: API login mints a token, `/login` → `/dashboard` in the UI, sign-out returns a protected route to `/login` |
| `cloud-employee-lifecycle.spec.ts` | Admin creates an employee (API 201 + `/people` serves them); leave apply → approve stays Approved (API + list persistence + `/leave` loads); employee creating employees is refused (403/404) |
| `cloud-ess-access.spec.ts` | Employee reaches own self-service (`/ess` + `GET /ess/notifications|directory` 200); employee never lands on `/admin/*`; employee admin writes refused (403/404); unauthenticated reads refused; admin surface loads for HR admin |
| `cloud-helpdesk.spec.ts` | Case opens (201) → comment (201) → history + queue persist; `/admin/hrhelp-cases` shows the case; a stranger's case reads as **404, never 403** (LP-SVC-003); unauthenticated reads 401 |
| `cloud-assets-documents.spec.ts` | Asset registered (`in_stock`) → assigned → custody persists; `/assets` names the tag; document recorded (v1) → second version (v2) → history oldest-first; People panel lists the newest version; employee create refused; stranger asset reads 404 |
| `cloud-reports-exit.spec.ts` | `GET /reports/dashboard|headcount|leave` 200 + `/reports` loads; termination created → listed → exit-interview notes attached via `PUT` and read back; `/offboarding` table lists the employee; employee minting terminations refused |

Cross-cutting, per spec: every UI journey captures console errors and failed
cloud requests and asserts both are empty; every write is namespaced
(`CLOUD*`/`QA-*` + run token) so fixtures never collide; credentials come
from `process.env` at runtime only — never hard-coded, never logged.

## How to run (once users are provisioned)

```sh
# Six synthetic users on the deployed tenant; passwords have no defaults.
export E2E_HRADMIN_USERNAME=e2e_hradmin    E2E_HRADMIN_PASSWORD=...
export E2E_HREXEC_USERNAME=e2e_hrexec      E2E_HREXEC_PASSWORD=...
export E2E_PAYROLL_USERNAME=e2e_payroll    E2E_PAYROLL_PASSWORD=...
export E2E_MANAGER_USERNAME=e2e_manager    E2E_MANAGER_PASSWORD=...
export E2E_EMPLOYEE_USERNAME=e2e_employee  E2E_EMPLOYEE_PASSWORD=...
export E2E_READONLY_USERNAME=e2e_readonly  E2E_READONLY_PASSWORD=...
# Optional overrides (defaults are the Render URLs above):
export CLOUD_API_URL=https://librepeople-backend.onrender.com/api/v1
export CLOUD_APP_URL=https://librepeople-frontend.onrender.com
npx playwright test e2e/cloud --config=<cloud-config>
```

Any role whose variables are unset is **SKIPPED with the reason**, never
failed — a partial run still proves the roles that are present.

## Pre-run blocker (owned by another agent, not this pack)

`frontend/e2e/support/global-setup.ts` refuses **any** run whose API or app
URL is `*.onrender.com`, and the default `playwright.config.ts` points at
local servers. This pack must therefore run under a **dedicated cloud
config** (new file, outside this pack's exclusive paths) that sets
`baseURL`/`KARMA_API_URL` to the deployed URLs and replaces the production
guard with an explicit opt-in (e.g. require `CLOUD_E2E_ACK=1`). Until that
config exists, `npx playwright test e2e/cloud` under the default config
stops at global setup by design. Conventions mirrored here (role login,
`CLOUD*` isolation, console-error capture, 403/404 boundaries) follow
`e2e/p4-lifecycle.spec.ts`, `e2e/navigation.spec.ts`,
`e2e/frontend-truth.spec.ts`; E2E variable-name conventions were read from
`docs/render-deployment.md` (no `E2E_*` names existed in-repo, so the
`E2E_<ROLE>_USERNAME/PASSWORD` scheme is defined by this pack).

## NOT COVERED (with reasons)

- **Exit-interview detail UI** (`/admin/exit-interviews`): no backend
  endpoint serves exit interviews — notes live on the termination
  (`PUT /offboarding/terminations/{id}`), which this pack asserts instead.
- **Document/comment hard delete**: no DELETE route exists for either
  (comments are append-only by design; documents expire via the retention
  sweep). Fixtures are namespaced synthetics; nothing real is uploaded.
- **Binary file upload/download bytes**: document versions are metadata rows
  (`storage_url` + version history), so the pack asserts the version chain,
  not byte transfer. R2 env vars are absent on the service while
  `STORAGE_BACKEND` is set — verify before any file-bytes smoke.
- **Payroll calculation figures**: covered by local `frontend-truth` stubs;
  the cloud pack asserts reports load, not recomputed payslip maths.
- **MFA-gated privileged flows**: local specs enroll MFA via TOTP; the cloud
  pack does not rotate or assert MFA on the shared deployed tenant.
