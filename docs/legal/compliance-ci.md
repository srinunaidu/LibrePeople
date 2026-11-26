# Licensing compliance CI (report-only, PREPARED-ONLY)

Report-only licensing compliance for `chore/licensing-transition`.
Runner: `ci/check_licences.py`, caller: `.github/workflows/licence-compliance.yml`.
No enforcement: the check exits 0 by default and the workflow uses
`continue-on-error`, so findings never block merges.

## Exit codes

| Invocation | Exit code | Meaning |
| --- | --- | --- |
| `python ci/check_licences.py` | `0` | Report-only default; reports written, findings never fail the build. |
| `python ci/check_licences.py --check-only` | `0` | Stdout only, no report files written, always exits 0. |
| `python ci/check_licences.py --strict` (or `--strict --check-only`) | `0` | Only when zero `Blocked`/`Unknown` verdict rows **and** zero `Blocked`/`Unknown` repo-level findings. |
| `python ci/check_licences.py --strict` (or `--strict --check-only`) | `1` | Any `Blocked`/`Unknown` verdict row or any `Blocked`/`Unknown` finding is present (current inventory: 3 Blocked / 133 Unknown, so strict exits 1). |
| Usage errors / unreadable inventory | `2` | `argparse` usage errors exit 2; an unreadable/non-list inventory exits non-zero. |

`--help` documents both `--check-only` and `--strict`. Determinism: verdict
rows, findings, and non-confirmed listings are sorted; JSON reports use stable
(sorted) keys; SBOM freshness compares the inventory package@version set
against the `docs/legal/sbom-*.json` component set. Set `SOURCE_DATE_EPOCH`
to a fixed epoch for byte-identical JSON reports across runs
(`meta.generated_utc` honours it). The script prints only package
names/versions/licences and findings text — never secret values.

## Enforcement policy

Report-only is the current and only active mode: the workflow stays
`continue-on-error: true` with no required-check gate, and `--strict` MUST
NOT be enabled in CI without explicit human approval. Enabling enforcement
requires a human decision recorded in
`docs/legal/legal-clearance-register.md` (legal sign-off that `Blocked` and
`Unknown` are at zero or formally cleared), plus a workflow change to
uncomment the disabled strict-gate snippet in
`.github/workflows/licence-compliance.yml`. Until then, `--strict` is a
local dry-run aid only (`python ci/check_licences.py --strict --check-only`).

## Statuses

| Status | Meaning | Per-dependency rule |
| --- | --- | --- |
| `Confirmed` | Verified permissive licence, compatible with the proposed AGPL-3.0-or-later posture. | Licence is a verified member of the allowlist: MIT, Apache-2.0, ISC, BSD-2-Clause, BSD-3-Clause, 0BSD, BlueOak-1.0.0. |
| `Review required` | Needs human legal review before any reliance. | Recognised licence needing posture review (CC-BY-4.0, Python-2.0), unrecognised identifiers, stale SBOM, missing NOTICE, direct-coverage gaps, or tracked files matching the `.gitignore` allowlist. |
| `Blocked` | Must not ship until cleared by legal. Report-only: does not block merges. | Restricted licence markers (GPL/AGPL/LGPL/MPL/commercial/unknown, including MPL-2.0 weak copyleft), or tracked secret-blob files (`*.key`, `*.pem`, `*.p12`, `*.pfx`, `*.wallet`). |
| `Unknown` | Cannot be evaluated from current metadata. | Licence is `UNVERIFIED`, missing, or empty; or a repo-level check (e.g. file enumeration) could not run. `UNVERIFIED` is never `Confirmed`. |

## Checks

1. **Direct inventory** - every `backend/requirements.txt` pin and every
   `frontend/package.json` dependency/devDependency must have a
   `scope == direct` row in `docs/legal/dependency-licence-inventory.json`.
   Gaps are `Review required` findings.
2. **Transitive listing** - all `scope == transitive` rows are listed with
   verdicts; nothing is silently dropped.
3. **Restricted metadata** - GPL/AGPL/LGPL/MPL/commercial/unknown licence
   markers are `Blocked`; `UNVERIFIED`/missing is `Unknown`, never `Confirmed`.
4. **NOTICE presence** - a root `NOTICE`/`NOTICE.md`/`NOTICE.txt` is required;
   absence is `Review required` (attributions currently live in
   `docs/legal/third-party-licences.md`).
5. **SBOM freshness** - the `docs/legal/sbom-*.json` component set must equal
   the inventory package@version set. Stale or missing SBOM is
   `Review required`, never a silent pass.
6. **Proprietary allowlist** - tracked files matching `.gitignore` allowlist
   patterns are reported: secret blobs are `Blocked`, other overrides
   (e.g. `backend/wallet/*`, over-broad `*credential*` matches) are
   `Review required` to confirm they are intentional and secret-free.

## Triage

1. Run `python ci/check_licences.py --check-only` and read the stdout table.
2. Open the `licensing-compliance-report` workflow artifact (`{md,json}`)
   for the full per-dependency table.
3. For each `Blocked` row: do not rely on that dependency; record legal
   clearance (or removal/replacement) in
   `docs/legal/legal-clearance-register.md`.
4. For each `Unknown` row: verify the licence from the upstream source and
   record it in `docs/legal/legal-clearance-register.md`; never treat
   `UNVERIFIED` as cleared.
5. For each `Review required` finding: resolve (add NOTICE row, refresh SBOM,
   narrow `.gitignore`, confirm allowlist overrides) or escalate to legal.
6. Re-run the check; confirm counts move from `Blocked`/`Unknown` to
   `Confirmed` only via recorded clearance, not script edits.

## Triage compatibility notes (2026-11-26, report-only — not legal advice)

> Written during the Tier 1 triage pass (575 Confirmed / 2 Review required /
> 3 Blocked / 133 Unknown). Each note records the evidence on file and the
> remediation; none clears the item — the linked L-row stays UNVERIFIED.

- **MPL-2.0 (`@axe-core/playwright` 4.14.0 dev-direct + transitive row, plus
  transitive `axe-core` 4.14.0 — 3 Blocked rows).** Licence is citable to the
  lock file (`packages["node_modules/@axe-core/playwright"].license` and
  `packages["node_modules/axe-core"].license`, both `MPL-2.0`); the direct row
  is declared in `frontend/package.json` **devDependencies** (`^4.14.0`), i.e.
  test tooling (`playwright test`). MPL-2.0 is file-level (weak) copyleft:
  conveying the covered files requires making their Source Code available under
  MPL-2.0, but it does not attach AGPL-style conditions to the larger work —
  still, confinement must be evidenced. Remediation: confirm with build evidence
  that neither package ships in production bundles (dev-only install / bundle
  audit) and record clearance at L10 before any effective grant. Until then the
  rows stay **Blocked**.
- **LGPL (`fpdf2` 2.9.0 — backend direct + transitive rows, currently
  UNVERIFIED).** Upstream declares LGPL-3.0-only (not independently verified in
  this repo — no backend lock file, no registry fetch). Use is lazy
  (`from fpdf import FPDF` inside `backend/app/services/offer_letter.py`),
  unmodified and unvendored, Helvetica built-in only (see
  `docs/licensing/copyleft-and-proprietary.md`, fpdf2 section). LGPL keeps the
  copyleft boundary at the library for dynamic linking, but that assessment plus
  the obligation to carry the upstream licence text on redistribution both need
  counsel sign-off. Remediation: verify the licence from the upstream source,
  confirm the boundary for our distribution paths, carry the upstream text on
  redistribution — L2/L8. Rows stay **Unknown** until verified.
- **Oracle UPL (oracledb 26.0.1 + oci 2.192.0 — backend direct + transitive
  rows, currently UNVERIFIED).** Upstream mix is UPL-1.0 / Apache-2.0 (not
  independently verified locally). `import oci` is lazy inside
  `backend/app/storage/backends.py` (`OCIObjectStorage`); `database.py` has no
  direct `oci` import — so the SDK only loads on Oracle-backed deploy paths.
  UPL-1.0 is permissive but carries Oracle-specific patent/attribution terms
  whose compatibility with a future AGPL-3.0-or-later grant is for counsel, not
  this report. Remediation: enumerate which deploy paths ship these packages and
  confirm term compatibility — L3/L9. Rows stay **Unknown** until verified.
- **ISC (`lucide-react` 1.59.0 — frontend direct row + transitive rows,
  21 ISC rows scanner-Confirmed).** Licence is citable to the lock file
  (`packages["node_modules/lucide-react"].license: ISC`, range `^1.59.0` in
  `frontend/package.json` dependencies). ISC is a short permissive licence
  (functionally MIT/BSD-equivalent), hence scanner-Confirmed as a verified
  permissive identifier — but "Confirmed" here means licence-identified, not
  legally cleared: frontend-bundle compatibility with the proposed posture still
  needs counsel confirmation at L11 before any effective grant. Remediation:
  record L11 clearance. Rows remain flagged in the clearance register until then.

## Human push gate

NO push to `main`, NO merge to `main`, NO release, and NO switch to
enforcement (blocking) mode without explicit human approval. This slice is
PREPARED-ONLY and report-only; the gate is lifted only by a human decision,
never by a green check.
