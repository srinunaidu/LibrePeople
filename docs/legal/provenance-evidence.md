# Provenance Evidence (PREPARED-ONLY)

> Status: **DRAFT / PREPARED-ONLY**. Companion to
> `docs/legal/ownership-and-provenance-register.md`. Lists the evidence path
> for every register row. No licence is made effective by this file. No owners
> or dates are invented; Karmathy transfer rows are **UNRESOLVED**.

| Register row | Evidence path(s) |
|--------------|------------------|
| Row 1 (`LibrePeople-created` inventory docs) | `docs/licensing/backend-direct.md`; `docs/licensing/backend-transitive.md`; `docs/licensing/frontend-direct.md`; `docs/licensing/frontend-transitive.md`; `docs/licensing/provenance-and-exclusions.md`; `docs/licensing/copyleft-and-proprietary.md` |
| Row 2 (`LibrePeople-created` legal package) | `docs/legal/ownership-and-provenance-register.md`; `docs/legal/licensing-policy.md`; `docs/legal/governance-note.md`; `docs/legal/decision-register.md`; `docs/legal/third-party-licences.md`; `docs/legal/LICENSE.AGPL-3.0.prepared` |
| Row 3 (PublicLayout `© 2026 Karmathy`) | `frontend/src/components/PublicLayout.tsx` (brand ~105, ~172, ~198; footer ~202) |
| Row 4 (DashboardFallback) | `frontend/src/components/home/DashboardFallback.tsx` (~69) |
| Row 5 (ProductMockup) | `frontend/src/components/marketing/ProductMockup.tsx` (~46) |
| Row 6 (Thread + design system) | `frontend/src/components/marketing/Thread.tsx` (~4); `frontend/src/lib/designSystem.ts` (~2) |
| Row 7 (`karmathy:*` events) | `frontend/e2e/redesign-e2e.spec.ts` (~96–109); grep `karmathy:` in `frontend/src` |
| Row 8 (`karmathy-backend/frontend` names) | `backend/pyproject.toml:2`; `frontend/package.json:2`; `frontend/package-lock.json:2,8` |
| Row 9 (backend core/main) | `backend/app/main.py`; `backend/app/core/config.py:148`; `backend/app/core/security.py:194-195`; `backend/app/core/audit_chain.py:11-70`; `backend/app/core/url_guard.py:222`; `backend/app/jobs/worker.py:119,224`; `backend/app/imports/analyse.py:199` |
| Row 10 (contracts/rules) | `contracts/rules/`; `backend/contracts/rules/`; `backend/rule_packs/in-standard.json:609`; `backend/app/core/presets/preset.schema.json:4`; `backend/contracts/rules/rule-pack.schema.json:4-5`; `backend/test_fixtures/rule_packs/` |
| Row 11 (render/docker/makefile/scripts) | `render.yaml`; `docker-compose.yml`; `backend/Dockerfile`; `frontend/Dockerfile`; `Makefile`; `ci/run_backend_tests.sh`; `backend/scripts/__init__.py:1`; `backend/scripts/generate_db_schema.py:152`; `backend/scripts/migrate.py:194` |
| Row 12 (other Karmathy brand surface) | `frontend/src/lib/seo.ts:5,19`; `frontend/src/context/TenantContext.tsx:309,353,358,361`; `frontend/src/components/shell/WorkspaceRail.tsx:348`; `frontend/index.html:25-26,33`; `frontend/public/sitemap.xml`; `frontend/public/robots.txt:34`; `frontend/.env.example:3`; `frontend/src/components/ui/ErrorBoundary.test.tsx:165-166` |
| Row 13 (requirements pins) | `backend/requirements.txt`; `docs/licensing/backend-direct.md`; `docs/legal/dependency-licence-inventory.json` |
| Row 14 (base images) | `backend/Dockerfile`; `frontend/Dockerfile`; `docs/licensing/provenance-and-exclusions.md` |
| Row 15 (offer_letter fpdf2) | `backend/app/services/offer_letter.py` (~77); `docs/licensing/copyleft-and-proprietary.md` (fpdf2 section) |
| Row 16 (`unclear` texts) | `README.md`; `contracts/README.md`; `contracts/events`; `contracts/openapi`; `frontend/playwright.config.ts` |
| Row 17 (`generated` artefacts) | `docs/licensing/sbom/backend-transitive.json`; `docs/legal/sbom-20261126T012556Z.json`; `docs/legal/dependency-licence-inventory.json`; method in `docs/licensing/provenance-and-exclusions.md` |
| Row 18 (`vendored` statement) | Grep/glob audit of repo root (no `vendor/`, `third_party/`, or vendored archives observed); `backend/requirements.txt`; `frontend/package-lock.json` |
| Row 19 (fonts/icons/assets) | `frontend/index.html:5,13-15`; `frontend/public/favicon.svg`; `frontend/public/og-image.png`; `frontend/public/sitemap.xml`; `frontend/public/robots.txt`; `frontend/public/_redirects`; `frontend/package.json` (`lucide-react`) |
| Row 20 (`historical notices`) | `frontend/src/components/PublicLayout.tsx` (~202); `docs/legal/LICENSE.AGPL-3.0.prepared`; repo root (absence of `LICENSE`/`COPYING`/`NOTICE`) |
| Row 21 (`contributor authorship`) | `git log` (intact, per-file authorship NOT extracted in this slice); `docs/legal/unresolved-blocker-register.md` U4 |
| Row 22 (authorship dates) | Per-row evidence paths above; `docs/legal/unresolved-blocker-register.md` U4 |

## Audit method

Read-only `grep`/`glob` over the working tree on branch
`chore/licensing-transition`. No file content was modified outside
`docs/legal/` by this slice; no history rewritten; every `Karmathy` string
preserved verbatim.
