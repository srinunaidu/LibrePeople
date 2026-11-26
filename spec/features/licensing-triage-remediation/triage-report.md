# Triage Report 2026-11-26 (Tier 1, PREPARED-ONLY report-only)

> No dependency removed, upgraded, substituted, or cleared. No licence string
> changed. No LICENSE published, no header inserted, no enforcement switch.
> This report records evidence-gathering only; every clearance row stays open.

## 1. Scope and method

- Input: `docs/legal/dependency-licence-inventory.json`, 713 rows
  (62 direct, 651 transitive), scanned with `python ci/check_licences.py --check-only`.
- Scanner verdicts before and after this pass (licence strings untouched):
  **575 Confirmed / 2 Review required / 3 Blocked / 133 Unknown**.
- Each of the 138 non-Confirmed rows now carries 9 fields (package, version,
  scope, licence, source, redistribution_obligations, attribution,
  compatibility, remediation) plus final classification (`triage_verdict`),
  triage date (`triage_date` = 2026-11-26), and evidence pointer
  (`triage_evidence`) in the normative JSON.
- No registry (PyPI) or lockfile metadata was fetched in this slice, so no new
  evidence exists: **zero Unknown rows reclassified to Confirmed**.

## 2. Triage findings by class

### Review required (2) — posture review, not licence identification

| Package | Version | Scope | Licence (lock-verbatim, unchanged) | Remediation |
|---|---|---|---|---|
| argparse | 2.0.1 | transitive | Python-2.0 | Human posture review of the legacy licence (clearance register; no reliance until cleared) |
| caniuse-lite | 1.0.30001816 | transitive | CC-BY-4.0 | Human posture review: content licence applied to code/data (clearance register; no reliance until cleared) |

### Blocked (3) — MPL-2.0, test-only confinement unconfirmed

| Package | Version | Scope | Licence (lock-verbatim, unchanged) | Remediation |
|---|---|---|---|---|
| @axe-core/playwright | 4.14.0 | direct | MPL-2.0 | Confirm with build evidence it never ships in production bundles; record L10 clearance |
| @axe-core/playwright | 4.14.0 | transitive | MPL-2.0 | Same as above (transitive of the dev/test path) |
| axe-core | 4.14.0 | transitive | MPL-2.0 | Same as above (transitive of the dev/test path) |

Evidence: `frontend/package.json` declares `@axe-core/playwright: ^4.14.0` under
**devDependencies** (test tooling, `playwright test`); both lock entries cite
`MPL-2.0`. Confinement is NOT yet evidenced — rows stay Blocked (L10/U6).

### Unknown (133) — UNVERIFIED backend, verification pending

- 19 backend direct + 114 backend transitive rows, all `UNVERIFIED` (no backend
  lock file, no registry fetch — inventory method unchanged).
- Includes fpdf2 2.9.0 (upstream LGPL-3.0-only, lazy import in
  `backend/app/services/offer_letter.py`) and oracledb 26.0.1 / oci 2.192.0
  (upstream UPL-1.0 / Apache-2.0 mix, lazy `import oci` in
  `backend/app/storage/backends.py`) — licence text still unverified locally,
  so they remain Unknown (L1–L3/L8–L9/U6), NOT reclassified on upstream claims.
- Per-row `triage_evidence` cites the requirements pin / freeze row and states
  the verification still required. Remediation per row: verify licence from the
  upstream source and record clearance; no effective grant until then.

## 3. Compatibility notes

Written in `docs/legal/compliance-ci.md` ("Triage compatibility notes",
2026-11-26) for all four flagged families: MPL-2.0 (axe-core test-only),
LGPL (fpdf2), Oracle UPL, ISC (lucide-react). Notes are informational, not
legal advice, and clear nothing.

## 4. Artefacts touched by this slice (docs/CI-only)

- `docs/legal/dependency-licence-inventory.json` — triage fields added to 138 rows.
- `docs/legal/dependency-licence-inventory.md` — header timestamp + triage section.
- `docs/legal/sbom-20261126T043959Z.json` — NEW timestamped SBOM, generated
  2026-11-26T04:39:59+00:00 (component set identical to inventory; prior SBOM kept).
- `docs/legal/compliance-ci.md` — triage compatibility notes.
- `docs/legal/unresolved-blocker-register.md` — appended U11 (counts + findings).
- `docs/legal/legal-clearance-register.md` — appended L15–L16.
- `ci/check_licences.py` — comment-only scanner allowlist rationale (CONFIRMED
  membership unchanged; nothing suppressed).
- This file + `scanner-check-only-output.txt` (verbatim scanner stdout).

## 5. Verification (validator re-runs)

```sh
python3 ci/check_licences.py --check-only   # exit 0; 575/2/3/133
python3 -m json.tool docs/legal/dependency-licence-inventory.json > /dev/null
python3 -m json.tool docs/legal/sbom-20261126T043959Z.json > /dev/null
git status --short && git diff --stat   # scoped to docs/legal, ci, spec/.../licensing-triage-remediation
```

Recorded scanner stdout (`--check-only`, exit 0, 2026-11-26):
`scanner-check-only-output.txt` in this directory.
