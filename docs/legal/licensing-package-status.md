# Licensing Package Status — PREPARED-ONLY (NOT EFFECTIVE)

> Tier 1 PREPARED-ONLY packaging note on `chore/licensing-transition`.
> No effective licence is published by this file. No root `LICENSE` / `COPYING` /
> `NOTICE` exists, no source headers have been added, and the official AGPL-3.0
> text has NOT been fetched from `https://www.gnu.org/licenses/agpl-3.0.txt`
> (see U5; `docs/legal/LICENSE.AGPL-3.0.prepared` states the text has
> "NOT yet been fetched"). This file creates no rights or obligations.
> Nothing here is legal advice. Ownership blockers U1–U10 and clearance items
> L12–L14 remain UNRESOLVED / UNVERIFIED by mandate; publication blockers are
> recorded as U12 / L17 for the legal reviewer.

## 1. Prepared-vs-withheld table

| Artefact | State | Rationale / blocker |
|----------|-------|---------------------|
| `docs/legal/LICENSE.AGPL-3.0.prepared` (placeholder) | PREPARED | Staging placeholder only; states text NOT fetched (U5). Creates no grant. |
| `docs/legal/licensing-policy.md` (draft posture) | PREPARED (draft) | Draft only; clearance L1–L5, L8–L11 still UNVERIFIED. |
| `docs/legal/governance-note.md` | PREPARED (draft) | Wording confirmation pending (L7). |
| `docs/legal/commercial-open-source-strategy.md` (draft) | PREPARED (draft) | Already on file; not rewritten by this slice. |
| `docs/legal/dependency-licence-inventory.json` + `.md` (713 rows) | PREPARED (evidence) | 138 rows triaged (575/2/3/133 per triage report); 133 backend rows still UNVERIFIED Unknown (U6, U11; L15–L16). |
| `docs/legal/sbom-20261126T043959Z.json` | PREPARED (evidence) | Fresh SBOM; matches inventory; grants no clearance (L16). |
| `docs/legal/ownership-and-provenance-register.md` (U1–U10 rows) | PREPARED (evidence) | All ownership rows UNRESOLVED; no transfer instrument on file. |
| `docs/legal/unresolved-blocker-register.md` (U1–U12) | PREPARED (evidence) | All UNRESOLVED, including U12 (this slice). |
| `docs/legal/legal-clearance-register.md` (L1–L17) | PREPARED (evidence) | All UNVERIFIED / PROPOSED / DRAFT, including L17 (this slice). |
| `docs/legal/provenance-evidence.md` | PREPARED (evidence) | Already on file; not rewritten by this slice. |
| Root `LICENSE` | WITHHELD | Publishing would make terms effective before clearance (U12; L17). |
| Root `COPYING` | WITHHELD | Publishing would make terms effective before clearance (U12; L17). |
| Root `NOTICE` | WITHHELD | No notice text cleared for publication (U12; L17). |
| Official AGPL-3.0 text (fetched/verified vendor) | WITHHELD | Text NOT fetched (U5); no fetch claiming official performed by this slice. |
| All source headers (`SPDX-License-Identifier` or equivalent) | WITHHELD | No header inserted anywhere under `backend/app` or `frontend/src` (verified empty grep; U12). |
| Any third-party notice change | WITHHELD | Third-party terms are unchanged by this slice; no notice added, removed, or modified (L12–L17). |

## 2. Per-file publication blockers

Each row names the file (or file class) that is NOT publishable and the
blocker(s) that prevent publication. Blocker IDs refer to
`docs/legal/unresolved-blocker-register.md` (U1–U12) and
`docs/legal/legal-clearance-register.md` (L12–L17).

| File / class | Blocker(s) | Why not publishable |
|--------------|-----------|---------------------|
| Root `LICENSE` (absent) | U5, U12; L17 | Official text not fetched/verified; package not cleared for publication. |
| Root `COPYING` (absent) | U5, U12; L17 | Same as `LICENSE`. |
| Root `NOTICE` (absent) | U7–U10, U12; L12, L14, L17 | Holder/attribution questions unresolved; no cleared notice text. |
| `docs/legal/LICENSE.AGPL-3.0.prepared` (as effective text) | U5; L17 | Placeholder only; must not be treated or published as an effective grant. |
| Source headers under `backend/app`, `frontend/src` | U1, U7–U10, U12; L12–L14, L17 | No authorship/grant basis for any header; reserved-rights footer present. |
| `frontend/src/components/PublicLayout.tsx` (`© 2026 Karmathy` footer/brand) | U1, U7, U12; L12–L14, L17 | Transfer instrument: none on file; express grant: none on file. |
| `frontend/src/components/home/DashboardFallback.tsx` | U7, U12; L12, L13, L17 | Karmathy-derived brand UI surface; no relicensing instrument. |
| `frontend/src/components/marketing/ProductMockup.tsx` | U7, U12; L12, L13, L17 | Karmathy-derived brand UI surface; no relicensing instrument. |
| `frontend/src/components/marketing/Thread.tsx` | U7, U12; L12, L13, L17 | Karmathy-derived design element; no relicensing instrument. |
| `karmathy:*` event namespace (`frontend/e2e/redesign-e2e.spec.ts`, app event names) | U8, U12; L14, L17 | Rename/retain authority unresolved; trademark assignment: none claimed. |
| `karmathy-backend` / `karmathy-frontend` names (`backend/pyproject.toml:2`, `frontend/package.json:2`, `frontend/index.html`, sitemap, robots, `.env.example`) | U1, U8, U12; L14, L17 | Transfer/rename authority unresolved. |
| Backend core/main (`backend/app/main.py`, `backend/app/core/*`) | U9, U12; L12, L13, L17 | Karmathy-derived; no relicensing instrument. |
| Contracts/rules (`contracts/rules/`, `backend/contracts/rules/`, `backend/rule_packs/`, `backend/test_fixtures/rule_packs/`, Karmathy-titled schemas, `signed_by: Karmathy Compliance` packs) | U9, U12; L12, L13, L17 | Karmathy-derived; no relicensing instrument. |
| Render/docker/makefile/scripts (`render.yaml`, `docker-compose.yml`, Dockerfiles, `Makefile`, `ci/run_backend_tests.sh`, `backend/scripts/`) | U4, U10, U12; L12, L13, L17 | Authorship/dates unextracted; no relicensing instrument; historical `© 2026 Karmathy` retained. |
| Third-party notices / dependency licence texts | U2, U6, U11, U12; L1–L5, L8–L11, L15–L17 | 133 backend rows UNVERIFIED; Review/Blocked rows need reviewer confirmation; terms unchanged. |
| `README.md`, docs scope for any CC BY 4.0 grant | U3, U4, U12; L6, L17 | "Original docs" scope unconfirmed; authorship/dates unextracted. |

## 3. Isolation of uncleared Karmathy-derived components — UNRESOLVED, non-publishable

The following components are uncleared Karmathy-derived material. They are
ISOLATED here as UNRESOLVED and non-publishable: no removal, scrub, rename, or
relicensing has been performed by this slice, and no holder or date is asserted
beyond what is sourced in the registers.

- PublicLayout `© 2026 Karmathy` footer/brand (`frontend/src/components/PublicLayout.tsx` ~105, ~172, ~198, ~202) — U1, U7; L12–L14.
- DashboardFallback (`frontend/src/components/home/DashboardFallback.tsx:69`) — U7; L12, L13.
- ProductMockup (`frontend/src/components/marketing/ProductMockup.tsx:46`) — U7; L12, L13.
- Thread (`frontend/src/components/marketing/Thread.tsx:4`) — U7; L12, L13.
- `karmathy:*` events (`frontend/e2e/redesign-e2e.spec.ts:96-109` and app event names) — U8; L14.
- `karmathy-backend` / `karmathy-frontend` names (`backend/pyproject.toml:2`, `frontend/package.json:2`, `frontend/index.html:25-26,33`, `frontend/public/sitemap.xml`, `frontend/public/robots.txt:34`, `frontend/.env.example:3`) — U1, U8; L14.
- Backend core/main (`backend/app/main.py`, `backend/app/core/*`) — U9; L12, L13.
- Contracts/rules (Karmathy-titled schemas, `signed_by: Karmathy Compliance` packs: `contracts/rules/`, `backend/contracts/rules/`, `backend/rule_packs/in-standard.json:609`, `backend/test_fixtures/rule_packs/`) — U9; L12, L13.
- Render/docker/makefile/scripts (`render.yaml`, `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `Makefile`, `ci/run_backend_tests.sh`, `backend/scripts/`) plus the historical `© 2026 Karmathy` notice — U4, U10; L12, L13.

Third-party terms are unchanged by this slice: no third-party notice has been
added, removed, or modified, and no dependency has been added, removed, or
upgraded. Clearance items L1–L5, L8–L11, L15–L16 remain UNVERIFIED.

## 4. What this slice did and did not do

- Did: verified the `LICENSE.AGPL-3.0.prepared` placeholder still states the
  official text was NOT fetched and that no full AGPL grant text is vendored
  under `docs/legal/`; created this status file; appended U12 and L17.
- Did not: publish any effective licence; fetch `gnu.org` text; insert any
  header; modify any Karmathy-derived or third-party notice; change any
  production, dependency, or CI file; push, merge, or release.
