# Feature: design-system-finish (Phase B)

## Behavior

Finish the design-system unification left over from R1/compact work: collapse
the remaining Card / StatusPill / Skeleton dualities to one canonical kit
pattern each, migrate every call site to the barrel, and clear the remaining
raw-`<table>` pages onto kit `Table`. Pure className/swap migration — no visual
or behavior change. Synthetic data only. No backend, no migrations, no CI
changes.

Per-duplicate decisions (canonical + why):

1. Card: `Card` / `SectionCard` from `ui/card.tsx` via the `@/components/ui`
   barrel. The local definitions in `ui.tsx` are duplicates of the canonical
   pair; DELETE the local definitions, keep barrel re-exports
   (NOT compatibility shims).
2. StatusPill: `StatusPill` (+ `StatusTone`) from `ui/status-pill.tsx`
   (mk-chip, dot tones) via the barrel. The local `ui.tsx` definition
   (badge-based `STATUS_TONE` map) is the duplicate; DELETE it, keep the barrel
   re-export. All `badge-*` usage outside StatusPill internals migrates to
   `StatusPill`.
3. Skeleton: `Skeleton` / `CardSkeleton` / `TableSkeleton` / `LoadingRegion`
   from `ui/skeleton.tsx` via the barrel. The local `ui.tsx` definitions are
   duplicates; DELETE them, keep barrel re-exports.
4. StatCard → KPICard: `KPICard` (`ui/kpi-card.tsx`) is the canonical metric
   card (props 1:1 with `StatCard`: label/value/hint/icon/tone, plus loading /
   error / sparkline / trend / onClick). Migrate ~25 `StatCard` call sites to
   `KPICard`; `StatCard` is superseded.
5. `ui-modal` canonical: `Modal/*` from `ui/modal.tsx` via the barrel is the
   only dialog primitive. `ErrorBox` migrates to barrel `Modal`
   (trap + close + focus). Zero `@radix-ui/react-dialog` imports outside
   `ui/modal`.
6. Imports: barrel `@/components/ui` canonical. Deep `@/components/ui/*`
   imports only inside `ui/*` itself — migrate 29 deep `ui/status-pill`, 6
   deep `ui/skeleton`, 6 deep `ui/card` imports to the barrel.
7. Tables: kit `Table` from `ui/table.tsx` via the barrel (sortable off by
   default per column; pass `sortable={false}`). Migrate ~45 raw `<table>`
   sites. Marketing `ProductMockup.tsx:122` is EXCLUDED (out of scope).
8. Tokens: `.dark` safe-text fix (no unreadable muted text on dark), dedupe
   `.dark` blocks, tenant token cleanup. No token renames; values unchanged.
9. A11y additions: `table.tsx` th keyboard sort (tabIndex + Enter/Space +
   focus ring), clickable `KPICard` aria-label, `ErrorBox` → barrel `Modal`.

## Acceptance criteria

1. AC-01 — Zero non-barrel Card/StatusPill/Skeleton definitions: no local
   `Card`, `SectionCard`, `StatCard`, `StatusPill`, `STATUS_TONE`,
   `Skeleton`, `CardSkeleton`, `TableSkeleton`, `LoadingRegion` definitions in
   `ui.tsx`; barrel re-exports from `ui/card`, `ui/status-pill`,
   `ui/skeleton` only.
2. AC-02 — All `StatCard` call sites migrated to `KPICard` with identical
   props (label/value/hint/icon/tone); zero `<StatCard` remaining.
3. AC-03 — Zero deep `ui/status-pill` imports in pages/components (29 files);
   all use the barrel.
4. AC-04 — Zero deep `ui/skeleton` (6) + `ui/card` (6) imports; all use the
   barrel.
5. AC-05 — Zero raw `<table` outside `ui/table.tsx` internals and marketing;
   all migrated pages render kit `Table` (`sortable={false}`, captions
   preserved). Marketing `ProductMockup.tsx:122` exempt.
6. AC-06 — Zero `badge-*` class usage outside StatusPill internals (tests
   excluded); status chips render via `StatusPill`.
7. AC-07 — Tokens: `.dark` safe-text fixed, `.dark` blocks deduped, tenant
   tokens cleaned; `npm run check:tokens` green; no visual change in
   light mode.
8. AC-08 — A11y: sortable `th` keyboard-operable (tabIndex + Enter/Space +
   focus ring), clickable `KPICard` carries an aria-label, `ErrorBox` renders
   through barrel `Modal` (focus trap + close + focus return). Documented
   exemptions (do not fix): pagination ghost `sm` buttons, `ErrorBox` button
   44px rule (dense/admin pattern).
9. AC-09 — Page fixes: ESSHub theme select wired (applies via `ThemeContext`),
   ModuleEntitlements tile-button pattern recorded as kit-exempt (aria-pressed
   toggles, no kit equivalent). Gates green per batch; Playwright
   before/after screenshots for Leave, Scheduling, PayRuns (light + dark)
   stored OUTSIDE the repo; no push.

## Non-goals (NO-GO list)

- No backend changes, no API/path changes, no migrations.
- No CI workflow changes; no new dependencies; no new routes.
- No behavior or copy changes — mechanical swaps only. Where the kit cannot
  express a pattern, leave it untouched and list it as excluded with reason.
- No marketing-kit files touched (`marketing/*` out of scope, incl.
  `ProductMockup.tsx:122`).
- No screenshots committed to the repo (`/tmp/phase-b-finish/` only).
- No push to remote; work stays on `agent/ux/phase-b-finish`.

## Interfaces / data

None. Config: none. Back-compat: barrel API unchanged; deleted locals were
internal duplicates only.

## Test plan

After EACH batch (payroll, admin, rest):

- `npm run typecheck` — must be clean.
- `npm run build` — must succeed.
- `npm run test:unit` — full suite must be 100% green; record exact count.
- Grep gates: zero non-barrel Card/StatusPill defs; zero raw `<table>`
  outside `ui/table` + marketing; zero `badge-*` outside StatusPill
  internals; zero deep `ui/(card|status-pill|skeleton)` imports; zero
  `@radix-ui/react-dialog` outside `ui/modal`.

On ANY failure: STOP all further batches, fix within the batch only if the
fix is a mechanical swap error, otherwise report the failure verbatim with
file:line and wait.

STOP conditions (do not work around, report instead): any page needing a
backend/API change; any missing endpoint; any behavior the kit cannot
express (leave untouched + list as excluded with reason); any new
dependency needed; any marketing-kit file touched (out of scope).

## Risk tier

2 (normal; broad touch, mechanical swaps).

## Rollback

Revert per-batch commit; no migrations/flags. Batches: (1) payroll pages,
(2) admin pages, (3) rest.

## Open decisions — RESOLVED

- D-a verified at build.
- D-b DELETE definitions, keep barrel re-exports (NOT compatibility shims).
- D-c 3 batches payroll→admin→rest.
- D-d screenshots Leave/Scheduling/PayRuns light+dark.

## Evidence annex (file:line refs, main HEAD `50fa2c6`)

- Duplicates: `frontend/src/components/ui.tsx:27` (`Card`),
  `ui.tsx:55` (`SectionCard`), `ui.tsx:95` (`StatCard`),
  `ui.tsx:250` (`STATUS_TONE`), `ui.tsx:268` (`StatusPill`),
  `ui.tsx:307` (`Skeleton`), `ui.tsx:311` (`CardSkeleton`),
  `ui.tsx:323` (`TableSkeleton`), `ui.tsx:337` (`LoadingRegion`).
- Canonical: `frontend/src/components/ui/card.tsx:10` (`Card`),
  `ui/card.tsx:25` (`SectionCard`), `ui/status-pill.tsx:50`
  (`StatusPill`), `ui/status-pill.tsx:29` (`StatusTone`),
  `ui/skeleton.tsx:3,8,19,33`, `ui/kpi-card.tsx:29` (`KPICard`),
  `ui/table.tsx`, `ui/modal.tsx:1` (radix), `ui/error-box.tsx:1` (radix).
- Deep status-pill imports (29 files): `home/HRHome.tsx:22`,
  `home/AssociateHome.tsx:30`, `home/ManagerHome.tsx:23`,
  `home/PayrollHome.tsx:16`, `pages/Import.tsx:20`, `pages/Design.tsx:8`,
  `pages/ThemeStudio.tsx:12`, `pages/Platform.tsx:5`,
  `pages/admin/UserAdmin.tsx:21`, `pages/admin/BreakGlass.tsx:20`,
  `pages/admin/IntegrationCredentials.tsx:10`,
  `pages/admin/DataQuality.tsx:19`, `pages/admin/ComplianceCenter.tsx:34`,
  `pages/admin/IntegrationsHub.tsx:24`, `pages/Jobs.tsx:20` (+type),
  `pages/ess/ESSHub.tsx:32`, `pages/People.tsx:21`,
  `pages/ClientOnboarding.tsx:12`, `pages/payroll/PayRuns.tsx:36`,
  `pages/payroll/PayRunDetail.tsx:31`,
  `pages/payroll/PayrollOverview.tsx:20`,
  `pages/performance/PerformanceHub.tsx:36`,
  `pages/forecasting/ScenariosTab.tsx:22`,
  `pages/forecasting/AccuracyTab.tsx:22`, `pages/forecasting/RunsTab.tsx:19`,
  `pages/DesignGallery.tsx:9`, `pages/onboarding/OnboardingConfig.tsx:23`,
  `pages/leave/LeaveLedger.tsx:28`.
- Deep skeleton/card imports: `platform/PayslipPanel.tsx:4,7`,
  `platform/DataList.tsx:2,5`, `platform/ReconciliationPanel.tsx:6,9`,
  `pages/Design.tsx:3,11`, `pages/Platform.tsx:9`,
  `pages/ClientOnboarding.tsx:9,10`, `pages/DesignGallery.tsx:6`.
- StatCard call sites (~35): `pages/Recruiting.tsx:278-281`,
  `pages/Reports.tsx:177-179,347-350`, `pages/Onboarding.tsx:190-193`,
  `pages/ForecastRunDetail.tsx:283-290`, `pages/Offboarding.tsx:182-189`,
  `pages/Scheduling.tsx:186-189`, `pages/payroll/PayRunDetail.tsx:374-377`,
  `pages/Leave.tsx:209-212` (barrel imports; e.g. `Leave.tsx:11`).
- Raw `<table` (~45, excl. `ui/table.tsx` + marketing):
  `home/HRHome.tsx:152,196`, `home/AssociateHome.tsx:283`,
  `home/SuperAdminHome.tsx:170`, `home/PayrollHome.tsx:137,173`,
  `pages/Reports.tsx:394,440`, `pages/Platform.tsx:661`,
  `pages/expenses/Expenses.tsx:137`, `pages/admin/TenStepJourney.tsx:91`,
  `admin/ExportErasure.tsx:68`, `admin/UserAdmin.tsx:241`,
  `admin/InterviewScheduling.tsx:126`, `admin/BreakGlass.tsx:267`,
  `admin/IntegrationCredentials.tsx:103`, `admin/MobileInteraction.tsx:89`,
  `admin/WorkflowApproval.tsx:102`, `admin/JurisdictionRules.tsx:125`,
  `admin/RetentionExport.tsx:46`, `admin/DataQuality.tsx:166,229`,
  `admin/FeatureFlags.tsx:97`, `admin/RequisitionStages.tsx:93`,
  `admin/AnnouncementsDirectory.tsx:100`,
  `admin/SwapsReplacements.tsx:117`, `admin/ComplianceCenter.tsx:729`,
  `pages/Jobs.tsx:321`, `pages/Offboarding.tsx:258,325,418`,
  `pages/documents/DocumentsLibrary.tsx:268,322`, `pages/Assets.tsx:582,633`,
  `payroll/PayrollSetup.tsx:381,520,717`, `payroll/shared.tsx:226`,
  `payroll/PayRuns.tsx:306`, `payroll/PayRunDetail.tsx:615,661`,
  `payroll/PayrollOverview.tsx:141`, `pages/er/ERCases.tsx:231`,
  `pages/forecasting/AccuracyTab.tsx:336`,
  `pages/DesignGallery.tsx:368`, `pages/MyAssets.tsx:112,161`,
  `pages/onboarding/OnboardingConfig.tsx:277`. EXCLUDED:
  `marketing/ProductMockup.tsx:122`.
- Tokens: `frontend/src/index.css:254` (`.dark`), `frontend/src/tokens.css`,
  `frontend/src/lib/tokens.ts`.
- Theme wiring: `pages/ess/ESSHub.tsx:883` (select),
  `frontend/src/context/ThemeContext.tsx:27` (no setter exposed).
- ModuleEntitlements: `pages/admin/ModuleEntitlements.tsx` (tile-button
  pattern, bulk-settle copy).
- A11y targets: `ui/table.tsx` (th sort), `ui/kpi-card.tsx:84` (clickable),
  `ui/error-box.tsx`, `context/ErrorContext.tsx:58`.
