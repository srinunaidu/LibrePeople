# Legal-Clearance Register (DRAFT — questions for legal reviewer)

> Nothing here is legal advice. Each row needs reviewer sign-off with cited
> evidence before any effective licensing step (Slice 2+).

| # | Question for reviewer | Evidence available in repo | Status |
|---|-----------------------|----------------------------|--------|
| L1 | Is the 19-direct / 114-transitive backend licence set compatible with a future AGPL-3.0-or-later grant? 114 rows UNVERIFIED (no licence metadata fetched from PyPI). | `docs/licensing/backend-direct.md`, `docs/licensing/backend-transitive.md`, `docs/licensing/sbom/backend-transitive.json`, `backend/requirements.txt` | UNVERIFIED — clearance required |
| L2 | fpdf2 2.9.0 (LGPL-3.0-only per upstream, UNVERIFIED locally): does lazy, unmodified, unvendored use via `backend/app/services/offer_letter.py` keep the LGPL boundary at the library for our distribution paths? | `backend/app/services/offer_letter.py` (~line 77 lazy import), `docs/licensing/copyleft-and-proprietary.md` (fpdf2 section) | UNVERIFIED — clearance required |
| L3 | Oracle packages (oracledb 26.0.1 + oci 2.192.0, UPL / Apache-2.0 mix, UNVERIFIED locally): which deploy paths ship them, and are those terms compatible with the proposed AGPL posture? Lazy `import oci` in `backend/app/storage/backends.py` (~line 176); no direct `oci` import in `backend/app/core/database.py`. | `backend/app/storage/backends.py`, `backend/app/core/database.py`, `docs/licensing/copyleft-and-proprietary.md` (Oracle section) | UNVERIFIED — clearance required |
| L4 | MPL-2.0 test-only components: confirm they are confined to test paths and never shipped in production bundles. | `docs/licensing/copyleft-and-proprietary.md`, `backend/requirements.txt`, `ci/run_backend_tests.sh` | UNVERIFIED — clearance required |
| L5 | ISC `lucide-react`: confirm compatibility with the proposed posture for the frontend bundle. | `frontend/package.json`, `frontend/package-lock.json`, `docs/licensing/frontend-direct.md`, `docs/licensing/frontend-transitive.md` | UNVERIFIED — clearance required |
| L6 | CC BY 4.0 PROPOSED for original docs only: confirm scope (which docs count as "original") before Slice 2. | `docs/licensing/`, `README.md`, this `docs/legal/` package | PROPOSED — scope confirmation required |
| L7 | Confirm no endorsement claim: this package claims no GNU/FSF endorsement and no trademark assignment. Confirm wording is sufficient. | `docs/legal/licensing-policy.md`, `docs/legal/governance-note.md` | DRAFT — reviewer to confirm |
