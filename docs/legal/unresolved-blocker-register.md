# Unresolved-Blocker Register (exact questions + evidence)

> These blockers must be resolved with written evidence before any effective
> licensing step. No owner or date is asserted here beyond what is sourced.

| # | Exact question | Evidence | Status |
|---|---------------|----------|--------|
| U1 | By what written instrument and signatory authority were Karmathy assets (including package names `karmathy-backend`, `karmathy-frontend` and the `© 2026 Karmathy` footer/brand in `frontend/src/components/PublicLayout.tsx`) transferred to the LibrePeople project, and who may sign the grant? | `backend/pyproject.toml:2` (`name = "karmathy-backend"`); `frontend/package.json:2` (`"karmathy-frontend"`); `frontend/src/components/PublicLayout.tsx` lines ~105, ~172, ~198 (brand) and ~202 (`© 2026 Karmathy. All rights reserved.`); transfer instrument: none on file | **UNRESOLVED** |
| U2 | Are the 19 direct / 114 transitive backend licences (UNVERIFIED), fpdf2 LGPL-3.0-only, Oracle UPL mix, MPL-2.0 test-only, and ISC lucide-react compatible with the proposed posture? (see legal-clearance register L1–L5) | `docs/licensing/backend-direct.md`, `docs/licensing/backend-transitive.md`, `docs/licensing/sbom/backend-transitive.json`, `docs/licensing/copyleft-and-proprietary.md`, `docs/licensing/provenance-and-exclusions.md` | **UNRESOLVED** |
| U3 | What is the exact scope of "original docs" for the CC BY 4.0 PROPOSED grant (does it include `README.md`, `docs/licensing/`, this `docs/legal/` package, or a narrower set)? | Scope statement: none on file beyond the human constraint "original docs only" | **UNRESOLVED** |
| U4 | What are the authorship dates and contributors for each `unclear` row in the ownership register (`README.md`, Dockerfiles text, compose/render/workflow configs, `Makefile`, `ci/run_backend_tests.sh`, app-code authorship)? | Git history exists (`git log` intact) but per-file authorship not yet extracted; no dates asserted | **UNRESOLVED** |
| U5 | Has the official AGPL-3.0 text been fetched from `https://www.gnu.org/licenses/agpl-3.0.txt` and verified? | `docs/legal/LICENSE.AGPL-3.0.prepared` notes text NOT yet fetched; no root `LICENSE`/`COPYING` exists | **UNRESOLVED** (expected; Slice 2 step) |
