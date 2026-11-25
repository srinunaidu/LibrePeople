# Feature: ui-global-error-ux

## Goal
Make error/loading/empty/success handling global and identical across ALL frontend pages — no generic "Something went wrong" without retry/hint/requestId remains.

## Acceptance criteria
- AC-40 — lib/api.ts: `fieldErrors(err): Map<string,string>` parses 422 `detail[]` → field map (loc slice(1) → msg); `errorMessage/isRetryable/requestId/details` are used everywhere, not 10% of pages.
- AC-41 — `RetryableAlert` (in `components/ui/feedback.tsx`): `Alert tone=error` wrapper with required `title`, `message`, `onRetry?`, shows Retry CTA iff `isRetryable(err)`, renders `requestId` span `data-testid=request-id` when present, branches network (!response) → "Check your connection".
- AC-42 — `PendingVerificationAlert` (new `components/ui/PendingVerificationAlert.tsx`): single warning tone, human copy "configurable calculation, cannot calculate", links to `docs/PAYROLL.md §3.3`, used on every 409 `rule_pack_not_verified`. Zero duplicated amber strings remain (grep `pending_verification` only in component + PayRuns badge).
- AC-43 — Field-level 422: every form maps `fieldErrors` to `Input/Select/Textarea error` prop (red border) + inline `<p role=alert>` under field; global `<p>` fallback only if no field matches. `lib/useFieldErrors.ts` hook (or util) provides `getFieldError(name)`.
- AC-44 — 409 gate: any 409 renders `PendingVerificationAlert` with link; PayRuns IN badge + JurisdictionRules keep badge but error path uses shared component.
- AC-45 — Success: all payroll/admin writes use `toast.success` (sonner) not `<Alert tone=success>`; Alert success removed from payroll/admin. Compliance toast pattern is global standard.
- AC-46 — Loading/empty discipline: every list read → `LoadingRegion`+`TableSkeleton` while loading, `EmptyState` with `action` (Create/Retry) when empty, `RetryableAlert` when failed. No page uses bare "Loading…" text.
- AC-47 — Forecasting `readableLoadError(err,fallback)` is global helper (moved to `lib/api.ts` or re-exported from `pages/forecasting/shared.tsx`): 403/404/422 branching adopted by all pages, not only forecasting.
- AC-48 — Gate: grep proves no page left generic — `grep -R 'Alert.*tone="error"' frontend/src/pages | xargs grep -L 'isRetryable\|RetryableAlert\|requestId' == 0` and `grep -R 'Something went wrong' frontend/src | grep -v ErrorBoundary fallback == 0`; `grep -R 'could not be read' frontend/src/pages` all route through `RetryableAlert`.

## Non-goals
- No backend, rule packs, engine, migrations, rates, or API contracts changed.
- No visual redesign beyond Alert/Input existing props.
- No new i18n or error-code taxonomy.

## Files to touch
- CREATE `frontend/src/lib/useFieldErrors.ts` — hook/util wrapping `fieldErrors` map + `clearField`
- MODIFY `frontend/src/lib/api.ts:98-121` — add `fieldErrors(err): Map<string,string>` + `isPendingVerification(err)` helper; keep `errorMessage/isRetryable/requestId`
- MODIFY `frontend/src/components/ui/feedback.tsx:23-82` — add `RetryableAlert` export (Alert+action Retry+requestId+title)
- CREATE `frontend/src/components/ui/PendingVerificationAlert.tsx` — warning tone, copy + link to docs/PAYROLL.md#33
- MODIFY `frontend/src/components/ui/inputs.tsx:4-60` — document `error` prop usage; add `aria-invalid`+`aria-describedby` when error
- MODIFY `frontend/src/components/ui/ErrorBoundary.tsx:46-97` — add `requestId` display from `apiError` if present
- MODIFY `frontend/src/pages/forecasting/shared.tsx:74-89` — export `readableLoadError` for global reuse (or re-export via lib/api)
- MODIFY `frontend/src/pages/payroll/PayRuns.tsx:64-170` — use RetryableAlert+fieldErrors+PendingVerificationAlert+toast
- MODIFY `frontend/src/pages/payroll/PayRunDetail.tsx`, `PayrollOverview.tsx:40-98`, `PayrollSetup.tsx`, `frontend/src/pages/admin/JurisdictionRules.tsx`, `ComplianceCenter.tsx`, `BankExport.tsx`, `SalaryRevisions.tsx` — same pattern
- BULK MODIFY `frontend/src/pages/admin/*.tsx` (~30 stubs incl. Certifications, LeaveTypes, ScheduledReporting, etc.) — replace bare Alert error/Loading… with RetryableAlert/TableSkeleton/EmptyState
- MODIFY `frontend/src/pages/Login.tsx:15-38` — keep `loginErrorMessage` network vs 500 branching as reference impl; wrap with RetryableAlert props
- MODIFY `frontend/src/pages/admin/*` toast calls — `import { toast } from "sonner"` + `toast.success` on writes

## Files not to touch
- `backend/**`, `rule_packs/**`, `contracts/**`, `backend/app/rules/engine.py|loader.py|reconciliation.py|money.py`
- `backend/migrations/**`, `docs/DB_SCHEMA.sql`
- `frontend/src/tokens.css` (unless token needed, then docs update)

## Step-by-step build plan
1. lib/api.ts: implement `export function fieldErrors(err): Map<string,string>` (parse `response.data.detail[]` loc/msg) + `isPendingVerification(err)` (409 + code `rule_pack_not_verified`); add tests.
2. lib/useFieldErrors.ts: `useFieldErrors(err)` returns `{fieldErrors, get, has, clear}` backed by `fieldErrors()`.
3. components/ui/feedback.tsx: add `RetryableAlert({err, title, fallback, onRetry})` — calls `errorMessage/isRetryable/requestId/readableLoadError`, renders `Alert tone=error title action={isRetryable&&onRetry?<Button onClick>Retry</Button>:null}` + requestId span.
4. components/ui/PendingVerificationAlert.tsx: `Alert tone=warning title="Calculation blocked — pending verification"> + <a href="/docs/PAYROLL.md#33"> docs/PAYROLL.md §3.3</a>`.
5. components/ui/inputs.tsx: ensure `error` adds `aria-invalid=true` and red border already does.
6. ErrorBoundary.tsx: read `requestId` from caught error if `apiError` present, render `Request ID: {id}`.
7. Payroll pages (PayRuns→PayRunDetail→Overview→Setup): replace `Alert error {errorMessage}` with `RetryableAlert err onRetry=load`, add `TableSkeleton/LoadingRegion/EmptyState action`, form: `const fe=useFieldErrors(formErr); <Input error={!!fe.get('jurisdiction')} />{fe.get('jurisdiction')&&<p role=alert>{fe.get(...)}</p>}`, success `toast.success`.
8. Admin bulk (JurisdictionRules, ComplianceCenter, BankExport, SalaryRevisions + remaining 26): same codemod — grep `Alert.*error`→`RetryableAlert`, `Loading…`→`TableSkeleton`, `toast.success` for writes, PendingVerificationAlert for 409.
9. Login: keep `loginErrorMessage` logic, render via `RetryableAlert` props (no regression on !response branch).
10. Forecasting: ensure `readableLoadError` imported from lib/api in all pages (or re-export).
11. Add Vitest suites: `RetryableAlert.test.tsx`, `PendingVerificationAlert.test.tsx`, `useFieldErrors.test.tsx` — 422 map, retry CTA, requestId, link.
12. Run grep gate + full frontend verify.

## Risks / edge cases
- 422 detail shape varies (string vs array): `fieldErrors` must handle both; fallback to global Alert if not array.
- No leakage: never render raw `details.missing` rates/thresholds beyond human copy + docs link.
- Retry storm: Retry button calls `load` not `window.reload`; 429 respects Retry-After via isRetryable.
- Empty vs error: failed read must NOT render EmptyState; guard `error ? null : empty`.
- Toast dupes: debounce toast on rapid resubmit; disable submit while saving.

## Test command
`cd frontend && npm run typecheck && npm run check:routes && npm run check:api-paths && npm run build && npm run test:unit`
Plus Vitest: `RetryableAlert` (retry shown/hidden + requestId), `field 422 inline` (Input error+aria), `PendingVerificationAlert` (warning+link), and grep gate: `! grep -R 'Alert.*tone="error"' frontend/src/pages | xargs grep -L 'RetryableAlert\|isRetryable'`
