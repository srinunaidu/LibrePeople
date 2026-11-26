# Third-Party Licences (DRAFT — reference only)

> Status: **DRAFT**. This file changes no third-party term. Upstream licences
> govern their own material. Anything not verified is marked **UNVERIFIED**,
> never inferred.

## Reference inventories (normative for this slice)

- `docs/licensing/backend-direct.md` — backend direct dependency licences.
- `docs/licensing/backend-transitive.md` — backend transitive licences.
- `docs/licensing/frontend-direct.md` — frontend direct dependency licences.
- `docs/licensing/frontend-transitive.md` — frontend transitive licences.
- `docs/licensing/provenance-and-exclusions.md` — inventory method, dates,
  and exclusions (WS1 inventory; backend 19 pins → 114 freeze rows, no backend
  lock file; frontend 24 deps + 19 devDeps → 538 lock entries).
- `docs/licensing/copyleft-and-proprietary.md` — copyleft and proprietary
  analysis (informational, not legal advice).
- `docs/licensing/sbom/backend-transitive.json` — backend transitive SBOM.

## Flagged components needing legal clearance (summary; detail in legal-clearance register)

- fpdf2 2.9.0 (LGPL-3.0-only per upstream, UNVERIFIED locally) — lazy import
  in `backend/app/services/offer_letter.py`; not vendored or modified;
  Helvetica built-in only.
- oracledb 26.0.1 + oci 2.192.0 (Oracle UPL / Apache-2.0 mix, UNVERIFIED
  locally) — lazy `import oci` in `backend/app/storage/backends.py`;
  `backend/app/core/database.py` has no direct `oci` import.
- MPL-2.0 test-only components — scope to be confirmed (must not ship in
  production bundles without clearance).
- ISC `lucide-react` — compatibility to be confirmed.
- Base images `python:3.11-slim`, `node:20-alpine`, `nginx:alpine` — governed
  by upstream image terms, unchanged.

## Rule

No third-party term is altered, replaced, or re-stated by any file in
`docs/legal/`. Where this draft and an upstream term appear to differ, the
upstream term governs.
