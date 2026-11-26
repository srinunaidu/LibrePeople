# L1–L17 licensing review (evidence-bound)

Scope: dependency/licence inventory for a future licensing decision. This file
makes **no licence effective** and gives **no legal advice**. Items needing a
lawyer are marked **requires counsel**. Branch: `agent/ops/licensing-l1-l17`.

Base: `main` HEAD `5b1cb526ff5fec4bb2e95aa197e20900a7016494` (verified before branching).

## 1. Backend direct (L1–L3)

Source: `backend/requirements.txt` — **21 pins** (non-comment lines; prior
`docs/licensing/backend-direct.md` says 19 — drift: `psycopg2-binary==2.9.13`
and `boto3>=1.34.0` were added after that doc was written, **requires
re-freeze of the doc**). Pins: fastapi 0.111.0, uvicorn[standard] 0.29.0,
sqlalchemy 2.0.29, oracledb 26.0.1, psycopg2-binary 2.9.13, pydantic-settings
2.3.0, pydantic 2.7.4, python-jose[cryptography] 3.3.0, bcrypt 4.2.0,
python-multipart 0.0.9, fpdf2>=2.7.0,<3.0.0, oci>=2.120.0, boto3>=1.34.0,
alembic 1.13.1, jsonschema 4.26.0, python-dotenv 1.0.1, pyotp 2.9.0,
qrcode[pil] 7.4.2, numpy>=1.26.0, statsmodels>=0.14.0, ortools==9.15.*.
No backend lock file (`backend/*.lock` absent) — **nothing backend-side is
lock-confirmed**.

Licence fields: **UNVERIFIED for all 21** — no licence metadata collected
from installed distributions or PyPI. Evidence: `backend-direct.md` table
(all rows UNVERIFIED); no `pip show`/METADATA capture on file.

## 2. Backend transitive (L4)

Source: `.venv311` `pip freeze`, **114 rows** (`backend-transitive.md`).
Licence: **UNVERIFIED for all 114**. Reconciliation vs
`docs/licensing/sbom/backend-transitive.json`: file holds a **114-element
list — counts match** (docs manifest `generated_utc 2026-11-23`, head
`969d4038`; manifest head predates current `main` — **re-freeze required
before release**). Range pins (fpdf2→2.9.0, oci→2.192.0, numpy→2.4.6,
statsmodels→0.15.0, ortools→9.15.6755) float — re-freeze each release.

## 3. Frontend direct + lock fields (L5–L6)

Source: `frontend/package.json` — **24 deps + 19 devDeps = 43 direct**;
licence fields from `frontend/package-lock.json` (lockfileVersion 3) are
**citable to the lock file**. All 43 carry a lock `license` field (24× MIT
except class-variance-authority Apache-2.0, lucide-react ISC; devDeps 16× MIT,
@axe-core/playwright MPL-2.0, @playwright/test + typescript Apache-2.0).
Evidence: `frontend-direct.md` table; verified `packages["node_modules/<name>"].license`.

## 4. Frontend transitive (L7)

Source: `frontend/package-lock.json` — **538 `packages` entries (537
non-root), 335 top-level `node_modules/<name>`**. Reconciliation vs
`docs/licensing/sbom/frontend-transitive.json` (537-element list):
**matches non-root count**. Licence split (all 538 entries, citable to lock):
MIT 477, Apache-2.0 25, ISC 20, BSD-2-Clause 7, MPL-2.0 2, BSD-3-Clause 2,
Python-2.0 1, CC-BY-4.0 1, BlueOak-1.0.0 1, 0BSD 1, **UNVERIFIED 0** at
top-level sample (335/335 carry a field; nested-denormalised counts differ —
see §6). Non-MIT/Apache/ISC top-level set: argparse 2.0.1 (Python-2.0),
axe-core 4.14.0 (MPL-2.0), caniuse-lite 1.0.30001816 (CC-BY-4.0), entities /
eslint-scope / espree / esrecurse / estraverse / esutils / uri-js
(BSD-2-Clause), esquery / source-map-js (BSD-3-Clause), minimatch 10.2.6
(BlueOak-1.0.0), tslib 2.8.1 (0BSD).

## 5. Vendored / generated / test-only / docs notices / headers / SBOMs

- **Vendored (L8):** none found. Evidence: `grep -ri
  "third_party|thirdparty|vendor/"` (excluding node_modules/.git) → no hits;
  `find -iname *vendor*|*third_party*|*thirdparty*|*bundled*` → no dirs;
  `copyleft-and-proprietary.md` records no font vendoring (Helvetica
  built-in only), no fpdf2/oracledb/oci source copies; `backend/wallet/*`
  git-ignored except README.
- **Generated (L9):** `frontend/dist/assets/*.js` build outputs present in
  working tree (git-ignored build artefacts, not inventoried as source);
  no `auto-generated / do not edit` source headers found outside dist.
- **Test-only (L10):** @axe-core/playwright 4.14.0 (MPL-2.0), axe-core
  4.14.0 (MPL-2.0), @playwright/test 1.64.1 + playwright-core (Apache-2.0),
  vitest 2.1.9 / happy-dom / testing-library / eslint stack (MIT). MPL-2.0
  items are dev-only, not shipped in the production bundle — build config
  confirms `vite build` ships `dependencies` only.
- **Docs notices (L11):** no licence grant found in `docs/` or root README;
  only notice is the UI string `© 2026 Karmathy. All rights reserved.` in
  `frontend/src/components/PublicLayout.tsx` (~line 202) — **not a source
  licence header; transfer/grant UNRESOLVED** (see `docs/legal`
  registers U1/L12).
- **Source headers sample (L12):** `grep -r SPDX-License-Identifier|Copyright`
  over `backend/app` + `frontend/src` → **zero source headers**. No
  `Licensed under` headers anywhere sampled.
- **Existing SBOMs (L13):** `docs/licensing/sbom/` holds
  `backend-transitive.json` (114), `frontend-transitive.json` (537),
  `manifest.json` (head 969d4038, 2026-11-23). Counts reconcile (§2, §4);
  manifest predates current HEAD — stale for release. (Note: `docs/legal/`
  holds separate `sbom-*.json` + `dependency-licence-inventory.json` from a
  parallel slice — not reconciled here; owners should dedupe.)

## 6. Flagged-item verdicts (L14–L17; evidence or UNVERIFIED, never guessed)

| # | Item | Verdict | Evidence |
|---|---|---|---|
| F1 | MPL-2.0 (@axe-core/playwright 4.14.0, axe-core 4.14.0) | **Cleared-with-evidence (scope-limited)** | Lock `license: MPL-2.0` citable to `package-lock.json`; both are devDependencies / test-only, not in production bundle. File-level copyleft boundary + non-shipment keeps it out of the distributed app — **requires counsel** to confirm test-segregation practice. |
| F2 | LGPL (fpdf2, freeze 2.9.0) | **UNVERIFIED — needs-counsel** | Pin + freeze confirmed; licence field UNVERIFIED locally (upstream declares LGPL-3.0-only — not independently verified here). Use is lazy import in `backend/app/services/offer_letter.py`, no modification/vendoring (evidence: `copyleft-and-proprietary.md`). Dynamic-linking/LGPL boundary question — **requires counsel**. |
| F3a | Oracle UPL (oci, freeze 2.192.0) | **UNVERIFIED — needs-counsel** | Pin + freeze confirmed; licence UNVERIFIED locally (upstream states UPL-1.0 — not verified here). Lazy import in `backend/app/storage/backends.py`. Commercial-vs-UPL terms — **requires counsel**. |
| F3b | oracledb 26.0.1 (dual UPL/Apache-2.0 upstream) | **UNVERIFIED — needs-counsel** | Pin confirmed; dual-licence character **UNVERIFIED** locally. Used by `backend/app/core/database.py` + Alembic env. Which of the two grants applies to our distribution — **requires counsel**. |
| F4 | ISC (lucide-react 1.59.0 direct + 12 transitive: anymatch, electron-to-chromium, fastq, flatted, glob-parent, isexe, lru-cache, picocolors, semver, siginfo, which, yallist) | **Cleared-with-evidence** | Lock `license: ISC` citable for each. ISC is permissive with an attribution clause — attribution handled via proposed NOTICE contents (decision-package §4). |
| F5 | CC-BY-4.0 (caniuse-lite 1.0.30001816, transitive via browserslist; docs-scope question) | **Cleared-with-evidence (scope-limited)** | Lock `license: CC-BY-4.0` citable; it is embedded data (browser-compat dataset), not code linked into the app. Attribution retained via NOTICE draft. Whether CC-BY-4.0 data inside a shipped bundle needs distinct notice wording — **requires counsel**. No docs in this repo are under CC-BY-4.0 yet (proposed only). |
| F6 | AGPL-3.0 presence | **Cleared-with-evidence (absent)** | `grep -ri agpl|affero` over repo (excl. node_modules/.git) hits only `ci/check_licences.py` comments (proposed posture), `spec/.../contract.md`, and `docs/legal/LICENSE.AGPL-3.0.prepared` stub. **No AGPL-licensed dependency or AGPL licence text ships.** |
| F7 | Dual-licensing instances | **UNVERIFIED — needs-counsel** | oracledb (F3b) is the only known dual-licence candidate; election unrecorded. No other dual-licensed dep identified — but backend metadata is UNVERIFIED so completeness is **UNVERIFIED**. |
| F8 | Commercial-license needs | **Needs-counsel (blocked)** | No commercial licence is on file for anything. Whether Oracle artefacts (F3) or any UNVERIFIED backend dep needs one — **requires counsel**. Default posture recorded: all-rights-reserved until cleared. |
| F9 | Attribution/notice obligations | **Needs-counsel (draft prepared, not published)** | Permissive set (MIT/ISC/Apache-2.0/BSD/0BSD/BlueOak-1.0.0/Python-2.0) + CC-BY-4.0 data + MPL-2.0 test-only + LGPL/UPL pending — consolidated NOTICE *contents* drafted inside `decision-package.md` §4 only (no NOTICE file committed). Sufficiency of a single NOTICE file — **requires counsel**. |

**Verdict counts:** cleared-with-evidence 3 (F1 scope-limited, F4, F6 absent) ·
scope-limited clears needing counsel sign-off 2 (F1, F5) · unverified 3 (F2,
F3a, F3b) · needs-counsel/blocked 3 (F7 election, F8, F9 sufficiency).
Backend licence metadata as a whole: **UNVERIFIED** (114/114 transitive +
21/21 direct) — the single largest release blocker.
