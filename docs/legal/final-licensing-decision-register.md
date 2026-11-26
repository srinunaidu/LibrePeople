# Final Licensing Decision Register — Track 2 TECHNICAL review (NOT legal advice)

> Branch: `agent/legal/licensing-evidence` from main `d80c0cd7f350be4be08b768d9a05573ef41a628f` (verified before branching). Date: 2026-11-26.
> Exclusive paths touched: this file (new) + `docs/legal/dependency-licence-inventory.json` + `docs/legal/sbom-20261126T043959Z.json` (in-place SBOM corrections only). No LICENSE/NOTICE/COPYING/CONTRIBUTING/CODE_OF_CONDUCT/SECURITY.md created. No push. No secrets.
> Method: backend = installed METADATA where present, else PyPI JSON API (read-only, `https://pypi.org/pypi/<name>/<ver>/json`, accessed 2026-11-26) recorded per package as METADATA / CLASSIFIER / PYPI-JSON; frontend = `package-lock.json` lock entries + npm registry spot-checks. This register records technical evidence only. **STOP: nothing here is legal clearance. All verdicts below are mechanical mappings — COUNSEL MUST CONFIRM; not a legal opinion.**

## Q1 — Backend: declared licence for EVERY pin in `backend/requirements.txt` (21 pins)

| # | Pin | Frozen | Licence (recorded) | Source | Authority (accessed 2026-11-26) |
|---|---|---|---|---|---|
| 1 | fastapi==0.111.0 | 0.111.0 | MIT | CLASSIFIER | PyPI JSON `fastapi/0.111.0` (license=null; classifiers MIT). Installed METADATA License empty (fastapi 0.162.0 env). |
| 2 | uvicorn[standard]==0.29.0 | 0.29.0 | BSD-3-Clause | METADATA | `docs/licensing/sbom/backend-transitive.json` (installed dist-info). |
| 3 | sqlalchemy==2.0.29 | 2.0.29 | MIT | PYPI-JSON | PyPI JSON `sqlalchemy/2.0.29` license="MIT" + MIT classifier. |
| 4 | **oracledb==26.0.1** | 26.0.1 | **UPL-1.0 OR Apache-2.0** | PYPI-JSON (expression) | PyPI JSON `oracledb/26.0.1` license_expression="UPL-1.0 OR Apache-2.0". Used via `oracle+oracledb://` dialect (`backend/app/core/database.py`). |
| 5 | psycopg2-binary==2.9.13 | — (not in freeze) | LGPL with exceptions | PYPI-JSON **[ROW ADDED — was absent]** | PyPI JSON `psycopg2-binary/2.9.13` license="LGPL with exceptions" + LGPL classifier. Pin enforced by `backend/tests/test_postgres_driver_pinned.py`. |
| 6 | pydantic-settings==2.3.0 | 2.3.0 | MIT | CLASSIFIER | PyPI JSON `pydantic-settings/2.3.0` (license=null; classifiers MIT). |
| 7 | **pydantic==2.7.4** | 2.7.4 | **MIT** | CLASSIFIER (corroborated METADATA) | PyPI JSON `pydantic/2.7.4` (license=null; classifiers MIT); bt METADATA=MIT. |
| 8 | python-jose[cryptography]==3.3.0 | 3.3.0 | MIT | PYPI-JSON | license="MIT" + MIT classifier. |
| 9 | bcrypt==4.2.0 | 4.2.0 | Apache-2.0 | PYPI-JSON | license="Apache-2.0" + Apache classifier. |
| 10 | python-multipart==0.0.9 | 0.0.9 | Apache-2.0 | METADATA | bt installed METADATA. (PyPI license field empty; classifier Apache.) |
| 11 | **fpdf2>=2.7.0,<3.0.0** | 2.9.0 | **LGPL-3.0-only** | PYPI-JSON (expression, corroborated METADATA) | PyPI JSON `fpdf2/2.9.0` license_expression="LGPL-3.0-only"; bt=LGPL-3.0-only. Lazy function-local import `backend/app/services/offer_letter.py:77` (`from fpdf import FPDF # lazy import`), Helvetica built-in, not vendored/modified. |
| 12 | **oci>=2.120.0** | 2.192.0 | **UPL-1.0 OR Apache-2.0** | PYPI-JSON | `oci/2.192.0` license="The Universal Permissive License (UPL), Version 1.0…" + Apache/UPL classifiers; floor `oci/2.120.0` license="Universal Permissive License 1.0 or Apache License 2.0". Lazy import `backend/app/storage/backends.py:176`. |
| 13 | boto3>=1.34.0 | — (not in freeze) | Apache-2.0 | PYPI-JSON **[ROW ADDED — was absent]** | PyPI JSON `boto3/1.34.0` license="Apache License 2.0" + Apache classifier. Recorded at floor; **pin unbounded — freeze/lock still needed**. Lazy import `backend/app/storage/s3.py:55`. |
| 14 | alembic==1.13.1 | 1.13.1 | MIT | PYPI-JSON | license="MIT". |
| 15 | jsonschema==4.26.0 | 4.26.0 | MIT | PYPI-JSON (expression) | license_expression="MIT". |
| 16 | python-dotenv==1.0.1 | 1.0.1 | BSD-3-Clause | PYPI-JSON | license="BSD-3-Clause". |
| 17 | pyotp==2.9.0 | 2.9.0 | MIT License (verbatim) | PYPI-JSON | license="MIT License" + MIT classifier; bt verbatim "MIT License". |
| 18 | qrcode[pil]==7.4.2 | 7.4.2 | BSD (verbatim) | METADATA | bt verbatim "BSD". |
| 19 | numpy>=1.26.0 | 2.4.6 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | PYPI-JSON (expression, corroborated METADATA) | PyPI JSON `numpy/2.4.6` license_expression (frozen version; floor 1.26.0 carries BSD text + GCC-Runtime-Exception bundle note). |
| 20 | statsmodels>=0.14.0 | 0.15.0 | BSD-3-Clause | PYPI-JSON (expression) | PyPI JSON `statsmodels/0.15.0` license_expression="BSD-3-Clause". |
| 21 | ortools==9.15.* | 9.15.6755 | Apache 2.0 (verbatim) | PYPI-JSON | license="Apache 2.0" + Apache classifier; bt verbatim "Apache 2.0". |

Finding Q1: 21/21 pins now carry licence evidence (was 0/21). Confidence: HIGH for expression/license-field rows; MEDIUM for CLASSIFIER-only rows (fastapi, pydantic, pydantic-settings) — required approval: counsel confirms classifier→licence inference against upstream text. Per-item required approval for flagged six (oracledb, oci, fpdf2, pydantic, fastapi, sqlalchemy): counsel clears deploy-path scope + term compatibility before any effective grant; record in `legal-clearance-register.md`.

## Q2 — Frontend: direct licences + transitive counts; the 9 UNVERIFIED transitives

- Direct (lock verbatim, 43): 24 deps = 22×MIT, 1×Apache-2.0 (`class-variance-authority` 0.7.1), 1×ISC (`lucide-react` 1.59.0); 19 devDeps = 16×MIT, 2×Apache-2.0 (`@playwright/test`, `typescript`), 1×MPL-2.0 (`@axe-core/playwright` 4.14.0 — test-only confinement to be evidenced).
- Transitive (537 non-root entries, `package-lock.json` at HEAD): MIT 477, Apache-2.0 25, ISC 20, BSD-2-Clause 7, MPL-2.0 2, BSD-3-Clause 2, Python-2.0 1 (`argparse` 2.0.1), CC-BY-4.0 1 (`caniuse-lite`), BlueOak-1.0.0 1 (`minimatch` 10.2.6), 0BSD 1 (`tslib` 2.8.1). Sums to 537. `docs/licensing/sbom/frontend-transitive.json` matches exactly — no correction needed.
- The "9 UNVERIFIED transitives from prior review": **do not reproduce** — all 537 non-root entries at HEAD carry a `license` field. Resolved as NOT-REPRODUCIBLE (prior lock since refreshed). Registry spot-checks 2026-11-26 (`registry.npmjs.org/<pkg>/<ver>`, license field): argparse→Python-2.0 ✓, caniuse-lite→CC-BY-4.0 ✓, minimatch@10.2.6→BlueOak-1.0.0 ✓, tslib→0BSD ✓, lucide-react→ISC ✓. Confidence HIGH. Required approval: counsel confirms posture for CC-BY-4.0 (data), Python-2.0 (legacy), MPL-2.0 test-confinement, ISC bundle.

## Q3 — Vendored / generated code: NONE in shipped source

- `find` for `third_party|vendor|bundled` in-repo (excl. `.git`, `node_modules`): only `frontend/dist/assets/vendor-*.js` (Vite code-split chunks, **untracked build output** — `git ls-files frontend/dist` empty) and `node_modules/**` (gitignored package-manager cache, incl. `playwright*/ThirdPartyNotices.txt`, `@babel/core/lib/vendor/` — not vendored source). No committed vendored dirs.
- "Generated" hits are prose only (`backend/app/core/ids.py` "Auto-generated natural keys" = runtime IDs; `filing_record.py` "generated bytes" = hashes of outputs). No codegen markers. Confidence HIGH. Required approval: none (re-verify if build outputs become committed).

## Q4 — Compatibility MATRIX (mechanical mapping — COUNSEL MUST CONFIRM, not a legal opinion)

Obligations (one line each, cited to licence-text sections):
- MIT: retain copyright + permission notice (license text condition ¶2). | ISC: retain copyright + permission notice (ISC text ¶1–2). | BSD-2-Clause: retain notice + disclaimer (clauses 1–2); BSD-3-Clause adds no-endorsement (clause 3). | 0BSD/BlueOak-1.0.0: retain-notice-only public-domain-equivalent. | Apache-2.0: §4 retain notices + state changes + NOTICE file; §2–3 copyright + patent grants; §6 no-trademark. | PSF-2.0/PSFL/Unlicense/MIT-0/MIT-CMU: permissive notice-retention family (exact text governs). | Python-2.0: CNRI legacy terms, GPL-incompatible (checker REVIEW). | CC-BY-4.0: §3 attribution + indicate changes (data licence; posture review). | MPL-2.0: §3 file-level copyleft, Exhibit A notices; §3.2/3.3 Larger Work combination. | LGPL-3.0-only / LGPL-2.1-or-later / "LGPL with exceptions": §§4–6 combined-work duties (shared-library/dynamic-link mechanism, reverse-engineering allowance §6, carry licence text). | UPL-1.0 OR Apache-2.0: dual; UPL §2 grant + patent/termination terms need counsel read. | Compound `X AND/OR Y` expressions: each element's duties apply per operator.

| Licence family | vs PROPOSED AGPL-3.0-or-later | vs PROPOSED CC-BY-4.0 (docs) | Mechanical note |
|---|---|---|---|
| MIT / ISC / BSD / Apache-2.0 / 0BSD / BlueOak / PSF | combinable (permissive) | combinable | counsel confirms NOTICE/build-attribution |
| MPL-2.0 (axe-core, certifi, orjson) | file-level copyleft; test-only/bundle-scope question | same | counsel confirms confinement |
| LGPL (fpdf2, crc32c, psycopg2-binary) | boundary question (linking mechanism, §6 duties) | same | counsel clears before grant |
| UPL-1.0 OR Apache-2.0 (oracledb, oci) | term-compatibility question (L3/L9) | same | counsel + deploy-path scope |
| CC-BY-4.0 / Python-2.0 (transitive data/legacy) | posture question | — | counsel confirms |
| "Dual License" (python-dateutil), "BSD-3-Clause AND TCL" (ujson) etc. | identify exact texts | same | human identification required |

## Q5 — SBOM accuracy: corrections applied (before → after)

- `dependency-licence-inventory.json` + `sbom-20261126T043959Z.json`: **133 backend rows UNVERIFIED → evidenced licence** (105 METADATA via `docs/licensing/sbom/backend-transitive.json` 2026-11-23 rule; 8 CLASSIFIER incl. fastapi; oci PYPI-JSON dual; full row diff via `git diff`). **+2 rows ADDED to both files**: `psycopg2-binary@2.9.13` (LGPL with exceptions, PYPI-JSON), `boto3@1.34.0-floor` (Apache-2.0, PYPI-JSON; unbounded pin noted). Before: 713 rows, 19 direct backend, `direct-coverage` CI finding open on 2 pins. After: **715 rows (64 direct, 651 transitive), invset == SBOM-union (642 unique), `direct-coverage` Confirmed, `sbom-freshness` Confirmed.**
- Surfaced by correction (pre-existing `backend-transitive.json` data, now visible to checker): `certifi@2026.11.20`=MPL-2.0, `crc32c@2.8`=LGPL-2.1-or-later, `orjson@3.13.0`="MPL-2.0 AND (Apache-2.0 OR MIT)" → all need counsel scope review.
- Frontend: no changes (lock ↔ `frontend-transitive.json` already exact). Older `sbom-20261126T012556Z.json` left untouched as historical snapshot (still feeds SBOM union; sets remain consistent).
- Remaining UNVERIFIED: **0 rows**. The exact check that would re-verify any row: `curl -s https://pypi.org/pypi/<name>/<version>/json | jq '{license: .info.license, expr: .info.license_expression, lic: [.info.classifiers[] | select(startswith("License"))]}'` (backend) or `npm view <pkg>@<ver> license` + `node -p "require('./frontend/package-lock.json').packages['node_modules/<pkg>'].license"` (frontend); authoritative: upstream repo LICENSE file at the pinned tag.
- Checker result (`ci/check_licences.py --check-only`): **Confirmed 672 / Review 34 / Blocked 9 / Unknown 0** (was 575/2/3/133). Blocked 9 = fpdf2×2, axe-core×3, certifi, crc32c, orjson, psycopg2-binary (mechanical; counsel-gated). Unit tests: 9/10 pass; `test_strict_exits_nonzero_on_current_inventory` FAILS only on stale hardcoded counts (`"Blocked: 3"`, `"Unknown: 133"`) — strict still exits non-zero correctly. That test file is outside Track-2 paths; **owning track must update the expected counts** (no logic change needed).

## Q6 — AGPL-3.0-or-later consequences (factual triggers only, per licence text)

- AGPL-3.0 §13: offering interaction over a network triggers the duty to offer Corresponding Source to all users. §5/§6: conveying (distributing) modified or unmodified versions triggers source-offer + notice duties. §1/§6 define "Corresponding Source" (all source needed to generate, install, run, modify). §10: each conveyance auto-licenses downstream recipients. §7: only specified additional terms allowed. §11: patent grant + discriminatory-licence limits. §8: violation auto-terminates rights (cure via §§8¶2–3). These describe *when the text's duties attach*; they say nothing about pricing, hosting, or product packaging.
- **Business-model decision requires counsel + owner.**

## Clearance status

No row is cleared by this register. `triage_verdict` stays `Unknown` (Tier-1 record; clearance lives only in `docs/legal/legal-clearance-register.md`). Required approvals: counsel — (a) Oracle dual-licence scope/terms (oracledb, oci), (b) LGPL boundary (fpdf2, psycopg2-binary, crc32c), (c) MPL scope (axe-core incl. test-confinement evidence, certifi, orjson), (d) CC-BY-4.0/Python-2.0 posture; owner — AGPL business-model decision + boto3 pin/lock.
