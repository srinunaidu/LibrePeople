# Dependency Licence Inventory (PREPARED-ONLY - report only)

> Prospective holder: **LibrePeople project only** (no rights claimed or transferred by this file).
> Posture: **AGPL-3.0-or-later PROPOSED**; docs **CC BY 4.0 PROPOSED (docs-only)**. No effective licensing.
> Backend licences are **UNVERIFIED** (no metadata collected, no backend lock file, no registry fetch).
> Frontend licences are the **package-lock entry verbatim** where present, **UNVERIFIED** where absent.
> No row is marked compliant. Nothing here is legal advice. Normative machine-readable file:
> `docs/legal/dependency-licence-inventory.json` (generated 2026-11-26T04:39:42+00:00; triage pass 2026-11-26, see below).

## Triage pass 2026-11-26 (Tier 1, report-only — no reclassification)

> Triage-only pass over every non-Confirmed row from the scanner
> (`python ci/check_licences.py --check-only`: 575 Confirmed / 2 Review
> required / 3 Blocked / 133 Unknown, 713 rows). Each of the 138 triaged rows
> carries 9 fields (package, version, scope, licence, source,
> redistribution_obligations, attribution, compatibility, remediation) plus
> final classification (`triage_verdict`), triage date (`triage_date`), and
> evidence pointer (`triage_evidence`) in the normative JSON. No licence string
> was changed; **zero Unknown rows were reclassified to Confirmed** (no
> registry/lockfile metadata was fetched in this slice, so no new evidence
> exists). Full record:
> `spec/features/licensing-triage-remediation/triage-report.md`.
> Compatibility notes for the four flagged families (MPL-2.0 axe-core test-only,
> LGPL fpdf2, Oracle UPL, ISC lucide-react) are in `docs/legal/compliance-ci.md`
> ("Triage compatibility notes"). Fresh SBOM: `docs/legal/sbom-20261126T043959Z.json`.

## Summary (713 rows: 62 direct, 651 transitive)

| Ecosystem | Direct | Transitive | Licence basis |
|---|---|---|---|
| Backend (`backend/requirements.txt`, 19 pins -> 114 freeze rows) | 19 | 114 | All UNVERIFIED |
| Frontend deps (`frontend/package.json`, 24) | 24 | - | Lock entry verbatim |
| Frontend devDeps (`frontend/package.json`, 19) | 19 | - | Lock entry verbatim |
| Frontend transitive (`frontend/package-lock.json`, 537 non-root entries) | - | 537 | Lock entry verbatim |

## Flagged findings (all UNVERIFIED - clearance required, see legal-clearance register)

| Package | Note |
|---|---|
| fpdf2 (direct + transitive rows) | Upstream declares LGPL-3.0-only, not independently verified; lazy import in `backend/app/services/offer_letter.py`; boundary review required (L2/L8) |
| oracledb 26.0.1, oci 2.192.0 (direct + transitive rows) | Upstream UPL-1.0 / Apache-2.0 mix, not independently verified; deploy-path scope review required (L3/L9) |
| @axe-core/playwright 4.14.0 (MPL-2.0, dev direct + transitive rows) | Test-only confinement to be confirmed (L4/L10) |
| lucide-react 1.59.0 (ISC, direct + transitive rows) | Compatibility to be confirmed (L5/L11) |

## Backend direct (19)

| Package | Version | Scope | Licence | Required action |
|---|---|---|---|---|
| fastapi | 0.111.0 | direct | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| uvicorn | 0.29.0 | direct | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| sqlalchemy | 2.0.29 | direct | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| oracledb | 26.0.1 | direct | UNVERIFIED | Counsel to confirm deploy-path scope and term compatibility before any effective grant. See docs/licensing/copyleft-and-proprietary.md (Oracle section). |
| pydantic-settings | 2.3.0 | direct | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| pydantic | 2.7.4 | direct | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| python-jose | 3.3.0 | direct | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| bcrypt | 4.2.0 | direct | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| python-multipart | 0.0.9 | direct | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| fpdf2 | 2.9.0 | direct | UNVERIFIED | Counsel to clear fpdf2 LGPL boundary before any effective grant; carry upstream licence text on redistribution. See docs/licensing/copyleft-and-proprietary.md. |
| oci | 2.192.0 | direct | UNVERIFIED | Counsel to confirm deploy-path scope and term compatibility before any effective grant. See docs/licensing/copyleft-and-proprietary.md (Oracle section). |
| alembic | 1.13.1 | direct | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| jsonschema | 4.26.0 | direct | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| python-dotenv | 1.0.1 | direct | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| pyotp | 2.9.0 | direct | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| qrcode | 7.4.2 | direct | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| numpy | 2.4.6 | direct | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| statsmodels | 0.15.0 | direct | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| ortools | 9.15.6755 | direct | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |

## Frontend direct - dependencies (24)

| Package | Version | Scope | Licence | Required action |
|---|---|---|---|---|
| @radix-ui/react-checkbox | 1.4.1 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-dialog | 1.3.1 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-dropdown-menu | 2.2.1 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-label | 2.1.17 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-popover | 1.3.1 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-progress | 1.2.1 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-slot | 1.5.0 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-switch | 1.4.1 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-tabs | 1.2.1 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-tooltip | 1.4.1 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @tanstack/react-query | 5.104.4 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @tanstack/react-table | 8.21.3 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @tanstack/react-virtual | 3.14.21 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| axios | 1.20.0 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| class-variance-authority | 0.7.1 | direct | Apache-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| clsx | 2.1.1 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| cmdk | 1.1.1 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| date-fns | 4.4.0 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| lucide-react | 1.59.0 | direct | ISC | Counsel to confirm ISC compatibility for the frontend bundle before any effective grant. |
| react | 18.3.1 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| react-dom | 18.3.1 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| react-router-dom | 6.30.6 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| sonner | 2.0.8 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| tailwind-merge | 2.6.1 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |

## Frontend direct - devDependencies (19)

| Package | Version | Scope | Licence | Required action |
|---|---|---|---|---|
| @axe-core/playwright | 4.14.0 | direct | MPL-2.0 | Confirm test-only confinement (excluded from production bundle) with evidence before any effective grant. |
| @playwright/test | 1.64.1 | direct | Apache-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @testing-library/jest-dom | 7.0.1 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @testing-library/react | 16.3.3 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @types/react | 18.3.31 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @types/react-dom | 18.3.7 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @typescript-eslint/eslint-plugin | 8.72.2 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @typescript-eslint/parser | 8.72.2 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @vitejs/plugin-react | 4.7.0 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| autoprefixer | 10.6.1 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| eslint | 9.39.5 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| eslint-plugin-react | 7.37.5 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| eslint-plugin-react-hooks | 5.2.0 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| happy-dom | 21.0.4 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| postcss | 8.5.30 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| tailwindcss | 3.4.19 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| typescript | 5.9.3 | direct | Apache-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| vite | 5.4.21 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| vitest | 2.1.9 | direct | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |

## Backend transitive - freeze rows (114, all UNVERIFIED)

| Package | Version | Scope | Licence | Required action |
|---|---|---|---|---|
| absl-py | 2.5.1 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| aiohappyeyeballs | 2.7.1 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| aiohttp | 3.14.5 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| aiosignal | 1.4.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| alembic | 1.13.1 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| annotated-doc | 0.0.7 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| annotated-types | 0.8.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| anyio | 4.16.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| asn1crypto | 1.5.1 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| attrs | 26.1.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| bcrypt | 4.2.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| boolean.py | 5.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| CacheControl | 0.15.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| certifi | 2026.11.20 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| cffi | 2.1.1 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| charset-normalizer | 3.5.2 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| circuitbreaker | 2.1.3 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| click | 8.5.1 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| crc32c | 2.8 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| cryptography | 50.0.2 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| cyclonedx-python-lib | 11.12.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| defusedxml | 0.7.1 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| dnspython | 2.9.2 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| ecdsa | 0.19.2 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| email-validator | 2.4.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| fastapi | 0.111.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| fastapi-cli | 0.0.34 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| filelock | 4.3.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| fonttools | 4.68.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| formulaic | 1.2.2 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| fpdf2 | 2.9.0 | transitive | UNVERIFIED | Counsel to clear fpdf2 LGPL boundary before any effective grant; carry upstream licence text on redistribution. See docs/licensing/copyleft-and-proprietary.md. |
| frozenlist | 1.8.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| h11 | 0.16.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| httpcore | 1.0.9 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| httptools | 0.9.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| httpx | 0.28.1 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| idna | 3.20 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| immutabledict | 4.3.1 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| iniconfig | 2.3.1 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| interface_meta | 2.0.1 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| Jinja2 | 3.1.6 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| jsonschema | 4.26.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| jsonschema-specifications | 2025.9.1 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| license-expression | 30.4.4 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| Mako | 1.4.3 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| markdown-it-py | 4.3.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| MarkupSafe | 3.0.4 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| mdurl | 0.1.2 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| msgpack | 1.2.4 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| multidict | 7.2.1 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| narwhals | 2.29.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| numpy | 2.4.6 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| oci | 2.192.0 | transitive | UNVERIFIED | Counsel to confirm deploy-path scope and term compatibility before any effective grant. See docs/licensing/copyleft-and-proprietary.md (Oracle section). |
| oracledb | 26.0.1 | transitive | UNVERIFIED | Counsel to confirm deploy-path scope and term compatibility before any effective grant. See docs/licensing/copyleft-and-proprietary.md (Oracle section). |
| orjson | 3.13.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| ortools | 9.15.6755 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| packageurl-python | 0.17.6 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| packaging | 26.3 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| pandas | 3.1.1 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| patsy | 1.0.3 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| pillow | 13.0.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| pip-requirements-parser | 32.0.1 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| pip_api | 0.0.35 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| pip_audit | 2.10.1 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| platformdirs | 4.14.8 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| pluggy | 1.7.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| propcache | 0.5.4 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| protobuf | 6.33.6 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| py-serializable | 2.2.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| pyasn1 | 0.6.5 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| pycparser | 3.12 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| pydantic | 2.7.4 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| pydantic-settings | 2.3.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| pydantic_core | 2.18.4 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| Pygments | 2.21.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| PyJWT | 2.15.1 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| pyOpenSSL | 26.4.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| pyotp | 2.9.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| pyparsing | 3.3.3 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| pypng | 0.20220715.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| pytest | 9.2.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| python-dateutil | 2.9.0.post0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| python-dotenv | 1.0.1 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| python-jose | 3.3.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| python-multipart | 0.0.9 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| python-pkcs11 | 0.9.4 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| pytz | 2026.6 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| PyYAML | 6.0.4 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| qrcode | 7.4.2 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| referencing | 0.37.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| requests | 2.34.2 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| rich | 15.0.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| rich-toolkit | 0.20.6 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| rpds-py | 2026.9.1 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| rsa | 4.9.1 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| scipy | 1.17.1 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| shellingham | 1.5.4 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| six | 1.17.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| sortedcontainers | 2.4.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| SQLAlchemy | 2.0.29 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| starlette | 0.37.2 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| statsmodels | 0.15.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| tomli | 2.5.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| tomli_w | 1.2.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| typer | 0.29.2 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| typing_extensions | 4.16.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| ujson | 6.1.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| urllib3 | 2.8.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| uvicorn | 0.29.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| uvloop | 0.23.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| watchfiles | 1.3.0 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| websockets | 17.4 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| wrapt | 2.5.2 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| yarl | 1.25.1 | transitive | UNVERIFIED | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |

## Frontend transitive - lock entries (537, verbatim/UNVERIFIED)

| Package | Version | Scope | Licence | Required action |
|---|---|---|---|---|
| @adobe/css-tools | 4.5.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @alloc/quick-lru | 5.3.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @axe-core/playwright | 4.14.0 | transitive | MPL-2.0 | Confirm test-only confinement (excluded from production bundle) with evidence before any effective grant. |
| @babel/code-frame | 7.29.7 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @babel/compat-data | 7.29.7 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @babel/core | 7.29.7 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @babel/generator | 7.29.8 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @babel/helper-compilation-targets | 7.29.7 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @babel/helper-globals | 7.29.7 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @babel/helper-module-imports | 7.29.7 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @babel/helper-module-transforms | 7.29.7 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @babel/helper-plugin-utils | 7.29.7 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @babel/helper-string-parser | 7.29.7 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @babel/helper-validator-identifier | 7.29.7 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @babel/helper-validator-option | 7.29.7 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @babel/helpers | 7.29.10 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @babel/parser | 7.29.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @babel/plugin-transform-react-jsx-self | 7.29.7 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @babel/plugin-transform-react-jsx-source | 7.29.7 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @babel/runtime | 7.29.13 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @babel/template | 7.29.7 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @babel/traverse | 7.29.10 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @babel/types | 7.29.8 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @esbuild/aix-ppc64 | 0.21.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @esbuild/android-arm | 0.21.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @esbuild/android-arm64 | 0.21.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @esbuild/android-x64 | 0.21.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @esbuild/darwin-arm64 | 0.21.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @esbuild/darwin-x64 | 0.21.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @esbuild/freebsd-arm64 | 0.21.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @esbuild/freebsd-x64 | 0.21.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @esbuild/linux-arm | 0.21.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @esbuild/linux-arm64 | 0.21.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @esbuild/linux-ia32 | 0.21.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @esbuild/linux-loong64 | 0.21.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @esbuild/linux-mips64el | 0.21.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @esbuild/linux-ppc64 | 0.21.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @esbuild/linux-riscv64 | 0.21.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @esbuild/linux-s390x | 0.21.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @esbuild/linux-x64 | 0.21.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @esbuild/netbsd-x64 | 0.21.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @esbuild/openbsd-x64 | 0.21.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @esbuild/sunos-x64 | 0.21.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @esbuild/win32-arm64 | 0.21.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @esbuild/win32-ia32 | 0.21.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @esbuild/win32-x64 | 0.21.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @eslint-community/eslint-utils | 4.10.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @eslint-community/regexpp | 4.12.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @eslint/config-array | 0.21.2 | transitive | Apache-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| balanced-match | 1.0.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| brace-expansion | 1.1.21 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| minimatch | 3.1.5 | transitive | ISC | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @eslint/config-helpers | 0.4.2 | transitive | Apache-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @eslint/core | 0.17.0 | transitive | Apache-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @eslint/eslintrc | 3.3.7 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| balanced-match | 1.0.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| brace-expansion | 1.1.21 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| ignore | 5.3.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| minimatch | 3.1.5 | transitive | ISC | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @eslint/js | 9.39.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @eslint/object-schema | 2.1.7 | transitive | Apache-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @eslint/plugin-kit | 0.4.1 | transitive | Apache-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @floating-ui/core | 1.8.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @floating-ui/dom | 1.8.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @floating-ui/react-dom | 2.1.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @floating-ui/utils | 0.2.12 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @humanfs/core | 0.19.2 | transitive | Apache-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @humanfs/node | 0.16.8 | transitive | Apache-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @humanfs/types | 0.15.0 | transitive | Apache-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @humanwhocodes/module-importer | 1.0.1 | transitive | Apache-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @humanwhocodes/retry | 0.4.3 | transitive | Apache-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @jridgewell/gen-mapping | 0.3.13 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @jridgewell/remapping | 2.3.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @jridgewell/resolve-uri | 3.1.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @jridgewell/sourcemap-codec | 1.6.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @jridgewell/trace-mapping | 0.3.31 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @napi-rs/lzma-linux-x64-gnu | 1.5.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @nodelib/fs.scandir | 2.1.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @nodelib/fs.stat | 2.0.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @nodelib/fs.walk | 1.2.8 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @playwright/test | 1.64.1 | transitive | Apache-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/primitive | 1.2.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-arrow | 1.1.17 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-checkbox | 1.4.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-collection | 1.2.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-compose-refs | 1.1.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-context | 1.3.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-dialog | 1.3.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-direction | 1.2.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-dismissable-layer | 1.2.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-dropdown-menu | 2.2.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-focus-guards | 1.2.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-focus-scope | 1.3.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-id | 1.1.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-label | 2.1.17 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-menu | 2.2.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-popover | 1.3.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-popper | 1.4.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-portal | 1.2.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-presence | 1.1.11 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-primitive | 2.2.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-progress | 1.2.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-roving-focus | 1.2.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-slot | 1.5.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-switch | 1.4.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-tabs | 1.2.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-tooltip | 1.4.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-use-callback-ref | 1.1.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-use-controllable-state | 1.3.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-use-effect-event | 0.0.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-use-is-hydrated | 0.1.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-use-layout-effect | 1.1.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-use-rect | 1.1.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-use-size | 1.1.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/react-visually-hidden | 1.2.13 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @radix-ui/rect | 1.1.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @remix-run/router | 1.23.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @rolldown/pluginutils | 1.0.0-beta.27 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @rollup/rollup-android-arm-eabi | 4.64.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @rollup/rollup-android-arm64 | 4.64.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @rollup/rollup-darwin-arm64 | 4.64.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @rollup/rollup-darwin-x64 | 4.64.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @rollup/rollup-freebsd-arm64 | 4.64.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @rollup/rollup-freebsd-x64 | 4.64.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @rollup/rollup-linux-arm-gnueabihf | 4.64.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @rollup/rollup-linux-arm-musleabihf | 4.64.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @rollup/rollup-linux-arm64-gnu | 4.64.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @rollup/rollup-linux-arm64-musl | 4.64.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @rollup/rollup-linux-loong64-gnu | 4.64.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @rollup/rollup-linux-loong64-musl | 4.64.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @rollup/rollup-linux-ppc64-gnu | 4.64.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @rollup/rollup-linux-ppc64-musl | 4.64.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @rollup/rollup-linux-riscv64-gnu | 4.64.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @rollup/rollup-linux-riscv64-musl | 4.64.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @rollup/rollup-linux-s390x-gnu | 4.64.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @rollup/rollup-linux-x64-gnu | 4.64.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @rollup/rollup-linux-x64-musl | 4.64.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @rollup/rollup-openbsd-x64 | 4.64.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @rollup/rollup-openharmony-arm64 | 4.64.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @rollup/rollup-win32-arm64-msvc | 4.64.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @rollup/rollup-win32-ia32-msvc | 4.64.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @rollup/rollup-win32-x64-gnu | 4.64.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @rollup/rollup-win32-x64-msvc | 4.64.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @tanstack/query-core | 5.104.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @tanstack/react-query | 5.104.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @tanstack/react-table | 8.21.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @tanstack/react-virtual | 3.14.21 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @tanstack/table-core | 8.21.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @tanstack/virtual-core | 3.19.6 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @testing-library/dom | 10.4.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @testing-library/jest-dom | 7.0.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| dom-accessibility-api | 0.6.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @testing-library/react | 16.3.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @types/aria-query | 5.0.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @types/babel__core | 7.20.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @types/babel__generator | 7.27.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @types/babel__template | 7.4.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @types/babel__traverse | 7.28.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @types/estree | 1.0.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @types/json-schema | 7.0.15 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @types/node | 26.6.6 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @types/prop-types | 15.7.15 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @types/react | 18.3.31 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @types/react-dom | 18.3.7 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @types/whatwg-mimetype | 3.0.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @types/ws | 8.18.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @typescript-eslint/eslint-plugin | 8.72.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @typescript-eslint/parser | 8.72.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @typescript-eslint/project-service | 8.72.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @typescript-eslint/scope-manager | 8.72.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @typescript-eslint/tsconfig-utils | 8.72.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @typescript-eslint/type-utils | 8.72.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @typescript-eslint/types | 8.72.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @typescript-eslint/typescript-estree | 8.72.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| semver | 7.8.6 | transitive | ISC | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @typescript-eslint/utils | 8.72.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @typescript-eslint/visitor-keys | 8.72.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| eslint-visitor-keys | 5.0.1 | transitive | Apache-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @vitejs/plugin-react | 4.7.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @vitest/expect | 2.1.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @vitest/mocker | 2.1.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @vitest/pretty-format | 2.1.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @vitest/runner | 2.1.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @vitest/snapshot | 2.1.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @vitest/spy | 2.1.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| @vitest/utils | 2.1.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| acorn | 8.19.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| acorn-jsx | 5.3.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| agent-base | 6.0.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| ajv | 6.15.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| ansi-regex | 5.0.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| ansi-styles | 4.3.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| any-promise | 1.3.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| anymatch | 3.1.3 | transitive | ISC | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| arg | 5.0.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| argparse | 2.0.1 | transitive | Python-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| aria-hidden | 1.2.6 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| aria-query | 5.3.0 | transitive | Apache-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| array-buffer-byte-length | 1.0.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| array-includes | 3.2.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| array.prototype.findlast | 1.2.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| array.prototype.flat | 1.3.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| array.prototype.flatmap | 1.3.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| array.prototype.tosorted | 1.1.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| arraybuffer.prototype.slice | 1.0.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| assertion-error | 2.0.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| async-function | 1.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| asynckit | 0.4.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| autoprefixer | 10.6.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| available-typed-arrays | 1.0.7 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| axe-core | 4.14.0 | transitive | MPL-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| axios | 1.20.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| balanced-match | 4.0.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| baseline-browser-mapping | 2.11.29 | transitive | Apache-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| binary-extensions | 2.3.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| brace-expansion | 5.0.12 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| braces | 3.0.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| browserslist | 4.29.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| buffer-image-size | 0.6.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| cac | 6.7.14 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| call-bind | 1.0.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| call-bind-apply-helpers | 1.0.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| call-bound | 1.0.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| callsites | 3.1.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| camelcase-css | 2.0.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| caniuse-lite | 1.0.30001816 | transitive | CC-BY-4.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| chai | 5.3.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| chalk | 4.1.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| check-error | 2.1.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| chokidar | 3.6.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| glob-parent | 5.1.2 | transitive | ISC | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| class-variance-authority | 0.7.1 | transitive | Apache-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| clsx | 2.1.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| cmdk | 1.1.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| color-convert | 2.0.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| color-name | 1.1.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| combined-stream | 1.0.8 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| commander | 4.1.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| concat-map | 0.0.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| convert-source-map | 2.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| cross-spawn | 7.0.6 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| css.escape | 1.5.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| cssesc | 3.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| csstype | 3.2.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| data-view-buffer | 1.0.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| data-view-byte-length | 1.0.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| data-view-byte-offset | 1.0.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| date-fns | 4.4.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| debug | 4.4.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| deep-eql | 5.0.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| deep-is | 0.1.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| define-data-property | 1.1.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| define-properties | 1.2.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| delayed-stream | 1.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| dequal | 2.0.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| detect-node-es | 1.1.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| didyoumean | 1.2.2 | transitive | Apache-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| dlv | 1.1.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| doctrine | 2.1.0 | transitive | Apache-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| dom-accessibility-api | 0.5.16 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| dunder-proto | 1.0.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| electron-to-chromium | 1.5.459 | transitive | ISC | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| entities | 7.0.1 | transitive | BSD-2-Clause | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| es-abstract | 1.24.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| es-abstract-get | 1.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| es-define-property | 1.0.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| es-errors | 1.3.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| es-iterator-helpers | 1.4.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| es-module-lexer | 1.7.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| es-object-atoms | 1.1.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| es-set-tostringtag | 2.1.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| es-shim-unscopables | 1.1.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| es-to-primitive | 1.3.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| esbuild | 0.21.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| escalade | 3.2.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| escape-string-regexp | 4.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| eslint | 9.39.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| eslint-plugin-react | 7.37.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| eslint-plugin-react-hooks | 5.2.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| balanced-match | 1.0.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| brace-expansion | 1.1.21 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| minimatch | 3.1.5 | transitive | ISC | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| resolve | 2.0.0-next.7 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| eslint-scope | 8.4.0 | transitive | BSD-2-Clause | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| eslint-visitor-keys | 3.4.3 | transitive | Apache-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| balanced-match | 1.0.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| brace-expansion | 1.1.21 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| eslint-visitor-keys | 4.2.1 | transitive | Apache-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| ignore | 5.3.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| minimatch | 3.1.5 | transitive | ISC | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| espree | 10.4.0 | transitive | BSD-2-Clause | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| eslint-visitor-keys | 4.2.1 | transitive | Apache-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| esquery | 1.7.0 | transitive | BSD-3-Clause | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| esrecurse | 4.3.0 | transitive | BSD-2-Clause | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| estraverse | 5.3.0 | transitive | BSD-2-Clause | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| estree-walker | 3.0.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| esutils | 2.0.3 | transitive | BSD-2-Clause | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| expect-type | 1.4.0 | transitive | Apache-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| fast-deep-equal | 3.1.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| fast-glob | 3.3.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| glob-parent | 5.1.2 | transitive | ISC | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| fast-json-stable-stringify | 2.1.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| fast-levenshtein | 2.0.6 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| fastq | 1.20.3 | transitive | ISC | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| file-entry-cache | 8.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| fill-range | 7.1.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| find-up | 5.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| flat-cache | 4.0.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| flatted | 3.4.4 | transitive | ISC | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| follow-redirects | 1.16.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| for-each | 0.3.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| form-data | 4.0.6 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| fraction.js | 5.3.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| fsevents | 2.3.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| function-bind | 1.1.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| function.prototype.name | 1.2.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| functions-have-names | 1.2.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| generator-function | 2.0.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| gensync | 1.0.0-beta.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| get-intrinsic | 1.3.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| get-nonce | 1.0.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| get-proto | 1.0.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| get-symbol-description | 1.1.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| glob-parent | 6.0.2 | transitive | ISC | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| globals | 14.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| globalthis | 1.0.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| gopd | 1.2.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| happy-dom | 21.0.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| has-bigints | 1.1.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| has-flag | 4.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| has-property-descriptors | 1.0.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| has-proto | 1.2.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| has-symbols | 1.1.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| has-tostringtag | 1.0.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| hasown | 2.0.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| https-proxy-agent | 5.0.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| ignore | 7.0.14 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| import-fresh | 3.3.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| imurmurhash | 0.1.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| indent-string | 4.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| internal-slot | 1.1.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| is-array-buffer | 3.0.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| is-async-function | 2.1.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| is-bigint | 1.1.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| is-binary-path | 2.1.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| is-boolean-object | 1.2.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| is-callable | 1.2.7 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| is-core-module | 2.17.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| is-data-view | 1.0.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| is-date-object | 1.1.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| is-document.all | 1.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| is-extglob | 2.1.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| is-finalizationregistry | 1.1.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| is-generator-function | 1.1.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| is-glob | 4.0.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| is-map | 2.0.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| is-negative-zero | 2.0.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| is-number | 7.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| is-number-object | 1.1.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| is-regex | 1.2.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| is-set | 2.0.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| is-shared-array-buffer | 1.0.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| is-string | 1.1.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| is-symbol | 1.1.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| is-typed-array | 1.1.15 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| is-weakmap | 2.0.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| is-weakref | 1.1.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| is-weakset | 2.0.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| isarray | 2.0.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| isexe | 2.0.0 | transitive | ISC | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| iterator.prototype | 1.1.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| jiti | 1.21.7 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| js-tokens | 4.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| js-yaml | 4.3.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| jsesc | 3.1.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| json-buffer | 3.0.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| json-schema-traverse | 0.4.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| json-stable-stringify-without-jsonify | 1.0.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| json5 | 2.2.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| jsx-ast-utils | 3.3.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| keyv | 4.5.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| levn | 0.4.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| lilconfig | 3.1.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| lines-and-columns | 1.2.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| locate-path | 6.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| lodash.merge | 4.6.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| loose-envify | 1.4.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| loupe | 3.2.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| lru-cache | 5.1.1 | transitive | ISC | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| lucide-react | 1.59.0 | transitive | ISC | Counsel to confirm ISC compatibility for the frontend bundle before any effective grant. |
| lz-string | 1.5.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| magic-string | 0.30.21 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| math-intrinsics | 1.1.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| merge2 | 1.4.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| micromatch | 4.0.8 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| mime-db | 1.52.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| mime-types | 2.1.35 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| min-indent | 1.0.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| minimatch | 10.2.6 | transitive | BlueOak-1.0.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| ms | 2.1.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| mz | 2.7.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| nanoid | 3.3.20 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| natural-compare | 1.4.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| node-exports-info | 1.6.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| node-releases | 2.0.59 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| normalize-path | 3.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| object-assign | 4.1.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| object-hash | 3.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| object-inspect | 1.13.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| object-keys | 1.1.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| object.assign | 4.1.7 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| object.entries | 1.1.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| object.fromentries | 2.0.8 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| object.values | 1.2.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| optionator | 0.9.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| own-keys | 1.0.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| p-limit | 3.1.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| p-locate | 5.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| parent-module | 1.0.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| path-exists | 4.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| path-key | 3.1.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| path-parse | 1.0.7 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| pathe | 1.1.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| pathval | 2.0.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| picocolors | 1.1.1 | transitive | ISC | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| picomatch | 2.3.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| pirates | 4.0.7 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| playwright | 1.64.1 | transitive | Apache-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| playwright-core | 1.64.1 | transitive | Apache-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| possible-typed-array-names | 1.1.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| postcss | 8.5.30 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| postcss-import | 15.1.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| postcss-js | 4.1.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| postcss-load-config | 6.0.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| postcss-nested | 6.2.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| postcss-selector-parser | 6.1.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| postcss-value-parser | 4.2.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| prelude-ls | 1.2.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| pretty-format | 27.5.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| ansi-styles | 5.2.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| react-is | 17.0.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| prop-types | 15.8.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| proxy-from-env | 2.1.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| punycode | 2.3.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| queue-microtask | 1.2.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| react | 18.3.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| react-dom | 18.3.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| react-is | 16.13.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| react-refresh | 0.17.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| react-remove-scroll | 2.7.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| react-remove-scroll-bar | 2.3.8 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| react-router | 6.30.6 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| react-router-dom | 6.30.6 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| react-style-singleton | 2.2.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| read-cache | 1.0.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| readdirp | 3.6.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| redent | 3.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| reflect.getprototypeof | 1.0.10 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| regexp.prototype.flags | 1.5.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| resolve | 1.22.13 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| resolve-from | 4.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| reusify | 1.1.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| rollup | 4.64.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| run-parallel | 1.2.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| safe-array-concat | 1.1.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| safe-push-apply | 1.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| safe-regex-test | 1.1.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| scheduler | 0.23.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| semver | 6.3.1 | transitive | ISC | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| set-function-length | 1.2.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| set-function-name | 2.0.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| set-proto | 1.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| shebang-command | 2.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| shebang-regex | 3.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| side-channel | 1.1.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| side-channel-list | 1.0.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| side-channel-map | 1.0.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| side-channel-weakmap | 1.0.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| siginfo | 2.0.0 | transitive | ISC | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| sonner | 2.0.8 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| source-map-js | 1.2.2 | transitive | BSD-3-Clause | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| stackback | 0.0.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| std-env | 3.10.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| stop-iteration-iterator | 1.1.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| string.prototype.matchall | 4.1.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| string.prototype.repeat | 1.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| string.prototype.trim | 1.2.11 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| string.prototype.trimend | 1.0.10 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| string.prototype.trimstart | 1.0.8 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| strip-indent | 3.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| strip-json-comments | 3.1.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| sucrase | 3.35.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| supports-color | 7.2.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| supports-preserve-symlinks-flag | 1.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| tailwind-merge | 2.6.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| tailwindcss | 3.4.19 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| thenify | 3.3.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| thenify-all | 1.6.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| tinybench | 2.9.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| tinyexec | 0.3.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| tinyglobby | 0.2.17 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| fdir | 6.5.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| picomatch | 4.0.7 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| tinypool | 1.1.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| tinyrainbow | 1.2.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| tinyspy | 3.0.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| to-regex-range | 5.0.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| ts-api-utils | 2.5.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| ts-interface-checker | 0.1.13 | transitive | Apache-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| tslib | 2.8.1 | transitive | 0BSD | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| type-check | 0.4.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| typed-array-buffer | 1.0.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| typed-array-byte-length | 1.0.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| typed-array-byte-offset | 1.0.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| typed-array-length | 1.0.8 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| typescript | 5.9.3 | transitive | Apache-2.0 | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| unbox-primitive | 1.1.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| undici-types | 8.9.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| update-browserslist-db | 1.3.4 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| uri-js | 4.4.1 | transitive | BSD-2-Clause | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| use-callback-ref | 1.3.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| use-sidecar | 1.1.3 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| util-deprecate | 1.0.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| vite | 5.4.21 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| vite-node | 2.1.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| vitest | 2.1.9 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| whatwg-mimetype | 3.0.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| which | 2.0.2 | transitive | ISC | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| which-boxed-primitive | 1.1.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| which-builtin-type | 1.2.1 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| which-collection | 1.0.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| which-typed-array | 1.1.24 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| why-is-node-running | 2.3.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| word-wrap | 1.2.5 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| ws | 8.22.2 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| yallist | 3.1.1 | transitive | ISC | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |
| yocto-queue | 0.1.0 | transitive | MIT | Legal reviewer to verify the licence from the upstream source and record clearance in docs/legal/legal-clearance-register.md; no effective licensing step until  |

## Registers

- New findings appended to `docs/legal/unresolved-blocker-register.md` (U6) and `docs/legal/legal-clearance-register.md` (L8-L11).
- Timestamped SBOM: `docs/legal/sbom-20261126T012556Z.json`.
