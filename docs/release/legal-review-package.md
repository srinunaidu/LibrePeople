# Legal Review Package (owner/counsel — NO clearance claimed)

Prepared by Agent F on branch `agent/ops/legal-review` from `216e869`.
This package claims **no clearance, no approval, no ownership** and is **not legal advice**.
No `LICENSE`/`NOTICE`/`COPYING` file is created or published by this package (forbidden).
No code or dependency was modified. Sources: `docs/licensing/**`,
`backend/requirements.txt`, `frontend/package.json` + `package-lock.json` (spot-check),
`docs/release/legal-clearance-checklist.md`.

## 1. SBOM vs manifest reconciliation (method + result)

- Backend: `backend/requirements.txt` has **19 pins** — all 19 present in
  `docs/licensing/backend-direct.md` and freeze-confirmed. Freeze resolves:
  fpdf2→2.9.0, oci→2.192.0, oracledb→26.0.1. **No backend lock file** exists;
  freeze-confirmed, not lock-confirmed. Range pins float (fpdf2, oci, numpy,
  statsmodels, ortools) — re-freeze at release cut.
- Backend SBOM JSON (`sbom/backend-transitive.json`, 114 rows): **105 carry a
  licence string, 9 are UNVERIFIED**: fastapi 0.111.0, Jinja2 3.1.6,
  markdown-it-py 4.3.0, mdurl 0.1.2, oci 2.192.0, pip_api 0.0.35,
  pip_audit 2.10.1, scipy 1.17.1, tomli_w 1.2.0. Spot-check method: exact-name
  lookup of 10 entries (the 8 checklist-named + oracledb + fpdf2 + oci) against
  the SBOM JSON; all 10 lookups reproduced the documented values.
- Doc staleness note: `backend-direct.md` / `backend-transitive.md` mark
  **every** row UNVERIFIED, but the SBOM JSON records `oracledb: "UPL-1.0 OR
  Apache-2.0"` and `fpdf2: "LGPL-3.0-only"`. Counsel should treat the JSON as
  the newer record and verify both from package metadata — see §2.
- Frontend: `package.json` has 24 deps + 19 devDeps; all 43 reconciled to
  `frontend-direct.md` with lock-resolved versions and lock licence fields
  (verify by re-running the lock lookup). Transitive SBOM
  (`frontend-transitive.json`, 537 entries): **0 UNVERIFIED** — every entry
  carries a lock-file licence field. Spot-checked 10 via `package-lock.json`
  `packages["node_modules/<name>"].license`: argparse 2.0.1 Python-2.0,
  caniuse-lite CC-BY-4.0, minimatch 10.2.6 BlueOak-1.0.0, tslib 2.8.1 0BSD,
  axe-core/@axe-core/playwright 4.14.0 MPL-2.0 (test-only, not shipped),
  lucide-react 1.59.0 ISC, electron-to-chromium ISC, lru-cache ISC,
  playwright-core Apache-2.0 — all matched the transitive doc.

## 2. Flagged packages deep-dive

| Package | Pin / resolved | Licence status (existing docs only) | Usage points | Clearance question |
|---|---|---|---|---|
| oracledb | `==26.0.1` / 26.0.1 | SBOM JSON: `UPL-1.0 OR Apache-2.0`; md docs: UNVERIFIED (unconfirmed) | `backend/app/core/database.py` (`oracle+oracledb://`), Alembic `env.py` | Confirm licence from installed package metadata; record acceptance for the shipped distribution model |
| oci | `>=2.120.0` / 2.192.0 | UNVERIFIED everywhere (upstream UPL-1.0 claimed, unconfirmed) | lazy `import oci` in `backend/app/storage/backends.py` (`OCIObjectStorage`); not needed for local dev | Confirm licence; record acceptance; note no wallet/SDK vendored (`backend/wallet/*` git-ignored except README) |
| fpdf2 | `>=2.7.0,<3.0.0` / 2.9.0 | SBOM JSON: `LGPL-3.0-only`; md docs: UNVERIFIED (unconfirmed) | lazy function-local `from fpdf import FPDF` in `backend/app/services/offer_letter.py`; Helvetica built-in only, no `.ttf` vendored, no modification | Counsel: confirm LGPL boundary (dynamic/lazy, unmodified, unvendored) holds for our redistribution; redistribution of fpdf2 itself must carry its licence text |

No `vendor/` / `third_party/` dirs, no bundled fonts, no modified copies found
(per existing docs; re-confirm at release cut). No GPL/AGPL in the direct set;
backend transitive UNVERIFIED rows keep a full licence scan mandatory.

## 3. Attribution / redistribution (as documented — no new claims)

- Frontend licences are citable to `frontend/package-lock.json`; backend
  licences are not lock-confirmed — do not publish LICENSE/NOTICE from these files.
- Documented obligation notes only: fpdf2 redistribution must carry its licence
  text; Oracle SDK/client terms to be confirmed against distribution model.
- Non-standard frontend transitive licences on record: Python-2.0 (argparse),
  CC-BY-4.0 (caniuse-lite, data only), BlueOak-1.0.0 (minimatch), 0BSD (tslib),
  MPL-2.0 (axe-core, test-only). Counsel to advise on attribution wording.

## 4. Ownership / provenance

- Extraction record: standalone repo established at `f8877a1`
  ("establish standalone LibrePeople repository"); HCM backend+frontend migrated
  at `62d741a`; rebrand Karmathy→LibrePeople through `216e869`. Residual
  provenance marker: `frontend/package.json` name field is still
  `"karmathy-frontend"` and the marketing footer renders `© 2026 Karmathy`.
- **No ownership claims are made** in this package or the licensing docs.

## 5. Repository visibility — UNVERIFIED

GitHub settings cannot be checked from this environment: **VISIBILITY
UNVERIFIED**. Owner action: confirm the repository is **private** in GitHub
Settings; if public, restrict immediately while clearance is pending.

## 6. Engagement requirement + sign-off

- Approver identity is **TBD by the owner**: owner + qualified counsel must be
  named before release. Nothing here substitutes for counsel review.
- Sign-off checklist (all pending — initials + date each):
  - [ ] Full licence scan completed for all 9 backend UNVERIFIED rows: ______
  - [ ] oracledb / oci / fpdf2 accepted for redistribution model: ______
  - [ ] SBOM JSON vs md-doc staleness (§1) resolved: ______
  - [ ] LICENSE/NOTICE decision recorded (publish vs withhold + why): ______
  - [ ] Range pins re-frozen at release cut: ______
  - [ ] Repo visibility confirmed private: ______
