# Ownership and Provenance Register (PREPARED-ONLY, Tier 1)

> Status: **DRAFT / PREPARED-ONLY**. No licence is made effective by this file.
> Prospective holder label: **LibrePeople project**. SPDX expression
> **AGPL-3.0-or-later** is **PROPOSED** only. No root `LICENSE` / `COPYING` /
> `NOTICE` is published as effective by this slice. No source headers added.
> No owners or dates are invented: transfer rows are marked **UNRESOLVED** and
> dates are either sourced or marked **unknown**.

## Classification labels

- `LibrePeople-created` — created in this repo under the LibrePeople project.
- `Karmathy-transferred` — bears Karmathy marks; transfer to LibrePeople is
  **UNRESOLVED** pending legal reviewer sign-off. Not asserted as owned.
- `third-party` — external dependency / base image / platform config schema.
- `copied-adapted` — third-party or prior-work content copied and adapted here.
- `unclear` — evidence missing; needs reviewer determination.

## Register

| # | Item (path) | Evidence observed | Classification | Owner | Date | Notes |
|---|-------------|-------------------|----------------|-------|------|-------|
| 1 | `README.md` | Repo readme describing this project; authorship history not verified | `unclear` | unknown | unknown | Do not assert authorship; verify before Slice 2. |
| 2 | `docs/licensing/backend-direct.md` | Licence inventory doc produced in this repo (WS1 inventory) | `LibrePeople-created` | LibrePeople project (prospective label, not a rights claim) | unknown | Inventory method cited inside doc; creation date not sourced. |
| 3 | `docs/licensing/backend-transitive.md` | Licence inventory doc produced in this repo (WS1 inventory) | `LibrePeople-created` | LibrePeople project (prospective label, not a rights claim) | unknown | Same caveat as #2. |
| 4 | `docs/licensing/frontend-direct.md` | Licence inventory doc produced in this repo (WS1 inventory) | `LibrePeople-created` | LibrePeople project (prospective label, not a rights claim) | unknown | Same caveat as #2. |
| 5 | `docs/licensing/frontend-transitive.md` | Licence inventory doc produced in this repo (WS1 inventory) | `LibrePeople-created` | LibrePeople project (prospective label, not a rights claim) | unknown | Same caveat as #2. |
| 6 | `docs/licensing/provenance-and-exclusions.md` | Provenance/method doc produced in this repo | `LibrePeople-created` | LibrePeople project (prospective label, not a rights claim) | unknown | States inventory date/method as WS1 on branch `feature/librepeople-production`; exact calendar date unknown. |
| 7 | `docs/licensing/copyleft-and-proprietary.md` | Copyleft analysis doc produced in this repo | `LibrePeople-created` | LibrePeople project (prospective label, not a rights claim) | unknown | Informational only, not legal advice (per doc). |
| 8 | `docs/licensing/sbom/backend-transitive.json` | Generated SBOM artefact from WS1 inventory | `LibrePeople-created` | LibrePeople project (prospective label, not a rights claim) | unknown | Generation timestamp, if any, is inside the file; not asserted here. |
| 9 | `backend/requirements.txt` | Dependency pin list (19 pins per provenance doc); upstream rights belong to each package owner | `third-party` | unknown (each package: respective upstream owner) | unknown | Pins reference third-party packages; no ownership claim over the packages. |
| 10 | `backend/pyproject.toml` (package name `karmathy-backend`) | Package name field still reads `karmathy-backend`; rename authority unverified | `Karmathy-transferred` — **UNRESOLVED** | UNRESOLVED (Karmathy → LibrePeople transfer not evidenced) | unknown | Name is preserved verbatim, not scrubbed. Needs legal reviewer sign-off before rename or rights assertion. |
| 11 | `frontend/package.json` + `frontend/package-lock.json` (package name `karmathy-frontend`) | Package name field still reads `karmathy-frontend`; 24 deps + 19 devDeps; 538 lock entries | `Karmathy-transferred` — **UNRESOLVED** | UNRESOLVED (Karmathy → LibrePeople transfer not evidenced) | unknown | Names preserved verbatim, not scrubbed. Needs legal reviewer sign-off. |
| 12 | `backend/app/services/offer_letter.py` (fpdf2 lazy import) | `from fpdf import FPDF` is function-local/lazy (line ~77); app runs without fpdf2 installed; fpdf2 upstream LGPL-3.0-only per copyleft doc, UNVERIFIED locally | `copied-adapted` (app code of unclear prior authorship) + `third-party` dependency (fpdf2) | unknown (app code); fpdf2: respective upstream owner | unknown | fpdf2 used dynamically, not vendored/modified; Helvetica built-in only. Licence obligations UNVERIFIED — see legal-clearance register. |
| 13 | `backend/app/storage/backends.py` + `backend/app/core/database.py` (oci lazy) | `import oci` is lazy in `backends.py` (~line 176); `database.py` contains no direct `oci` import (verified by grep); Oracle UPL/Apache-2.0 mix per copyleft doc, UNVERIFIED locally | `unclear` (app code authorship) + `third-party` dependency (oci SDK) | unknown (app code); oci: respective upstream owner (Oracle) | unknown | `database.py` oci association is contextual (Oracle DB driver path), not an import. Needs reviewer confirmation of which Oracle packages ship in each deploy path. |
| 14 | `backend/Dockerfile` (`python:3.11-slim`) | Base image `python:3.11-slim`; Dockerfile authorship not verified | `third-party` (base image) + `unclear` (Dockerfile text) | unknown (Dockerfile); base image: respective upstream owner | unknown | Base-image terms governed by upstream, unchanged. |
| 15 | `frontend/Dockerfile` (`node:20-alpine` / `nginx:alpine`) | Build stage `node:20-alpine`, serve stage `nginx:alpine`; authorship not verified | `third-party` (base images) + `unclear` (Dockerfile text) | unknown (Dockerfile); base images: respective upstream owners | unknown | Base-image terms governed by upstream, unchanged. |
| 16 | `docker-compose.yml` | Local orchestration config; authorship not verified | `unclear` | unknown | unknown | Verify before asserting ownership. |
| 17 | `render.yaml` | Deploy config; authorship not verified | `unclear` | unknown | unknown | Verify before asserting ownership. |
| 18 | `.github/workflows/deploy.yml` | CI deploy workflow; authorship not verified | `unclear` | unknown | unknown | Verify before asserting ownership. |
| 19 | `frontend/src/components/PublicLayout.tsx` (`© 2026 Karmathy`) | Footer reads `© 2026 Karmathy. All rights reserved.` (line ~202); `Karmathy` brand mentions at lines ~105, ~172, ~198 | `Karmathy-transferred` — **UNRESOLVED** | UNRESOLVED (Karmathy → LibrePeople transfer not evidenced) | 2026 (as asserted in-file; not independently verified) | Mark and footer preserved verbatim, not scrubbed or removed. No trademark assignment is claimed. Needs legal reviewer sign-off. |
| 20 | `Makefile` + `ci/run_backend_tests.sh` | Build/test helper scripts; authorship not verified | `unclear` | unknown | unknown | Read-only in this slice (`make -n test` inspection only). |

## Karmathy references — preservation statement

Every `Karmathy` string listed above is preserved verbatim in the source tree.
This register does not rename, scrub, or remove any Karmathy mark, and makes
no trademark claim. Transfer of any Karmathy-marked asset to the LibrePeople
project is **UNRESOLVED** until a legal reviewer provides written evidence and
authority (see `unresolved-blocker-register.md`).
