# Publication Package — WITHHELD (PREPARED-ONLY, NOT EFFECTIVE)

> Tier 1 PREPARED-ONLY publish preparation on isolated branch
> `chore/licensing-publish-prep` (cut from `chore/licensing-transition @ d13a3a7`;
> `main @ f3ee5cf` untouched, read-only reference, never a merge target).
> This file publishes NO effective licence, makes NO grant, and changes NO
> production, dependency, or CI file. Nothing here is legal advice.
> Ownership blockers U1–U12 are UNRESOLVED; clearance items L1–L17 are
> UNVERIFIED / BLOCKED. **Publication is NOT cleared.**
> Rights holder: TBD — DO NOT INVENT. Year: TBD — DO NOT INVENT.
> Contacts: TBD — DO NOT INVENT (no inbox designated, no timeline claimed).

## 1. Per-file prepared-vs-withheld table

| Artefact | State | Rationale / blocker |
|----------|-------|---------------------|
| Root `LICENSE` | WITHHELD (absent) | Publishing would make terms effective before clearance (U5, U12; L17). Verified absent on this branch and on `main` root. |
| Root `COPYING` | WITHHELD (absent) | Same as `LICENSE` (U5, U12; L17). Verified absent. |
| Root `NOTICE` | WITHHELD (absent) | No notice text cleared for publication; attribution questions unresolved (U7–U10, U12; L12, L14, L17). Verified absent. |
| Official AGPL-3.0 text (fetched/verified vendor) | WITHHELD — NOT fetched | No fetch from `gnu.org` performed by this slice; no official text vendored or modified. Placeholder only (U5; L17). |
| `docs/legal/LICENSE.AGPL-3.0.prepared` (placeholder) | PREPARED (placeholder only) | Stages the intended location of the future text; states text NOT fetched; creates no grant (U5). Must not be treated as an effective grant. |
| All source headers (`SPDX-License-Identifier` or equivalent) | WITHHELD — none inserted | Verified: `grep -ri "SPDX-License-Identifier" backend/app frontend/src` returns empty on this branch (U1, U7–U10, U12; L12–L14, L17). |
| `NOTICE` / third-party notice files (draft) | WITHHELD (draft only) | Third-party terms unchanged by this slice; no notice added, removed, or modified (U2, U6, U11, U12; L1–L5, L8–L11, L15–L17). |
| Docs CC BY 4.0 grant | WITHHELD — PROPOSED only | Scope of "original docs" unconfirmed; authorship/dates unextracted (U3, U4, U12; L6, L17). No grant text published. |
| Policy / strategy refs (`docs/legal/licensing-policy.md`, `governance-note.md`, `commercial-open-source-strategy.md`, `decision-register.md`, `licensing-transition-tracker.md`) | PREPARED (draft refs only) | Draft posture/wording only; clearance L1–L5, L8–L11 still UNVERIFIED; wording confirmation pending (L7). Create no grant. |
| `SECURITY.md` contacts | WITHHELD — TBD only | No security contact designated; addresses are TBD placeholders, no disclosure-timeline owner claimed. Holder/contacts: TBD — DO NOT INVENT. |
| `CODE_OF_CONDUCT.md` contacts / enforcement details | WITHHELD — TBD only | Enforcement contacts TBD; full Covenant text referenced by URL only, not vendored as a grant. Contacts: TBD — DO NOT INVENT. |
| `docs/legal/dependency-licence-inventory.json` + `.md` (713 rows) | PREPARED (evidence) | 138 rows triaged (575/2/3/133); 133 backend rows still UNVERIFIED Unknown (U6, U11; L15–L16). Grants no clearance. |
| `docs/legal/sbom-20261126T043959Z.json` | PREPARED (evidence, fresh) | Fresh SBOM; matches inventory; grants no clearance (L16). |
| `docs/legal/ownership-and-provenance-register.md` | PREPARED (evidence) | All ownership rows UNRESOLVED; no transfer instrument on file (U1–U10; L12–L14). |
| `docs/legal/unresolved-blocker-register.md` (U1–U12) | PREPARED (evidence) | All UNRESOLVED, including U12 (this slice). |
| `docs/legal/legal-clearance-register.md` (L1–L17) | PREPARED (evidence) | All UNVERIFIED / PROPOSED / DRAFT, including L17 (this slice). |
| `docs/legal/licensing-package-status.md` | PREPARED (evidence) | Prior-slice prepared-vs-withheld baseline; this file extends it for publication review. |

## 2. Blockers — publication NOT cleared

### U1–U12: all UNRESOLVED (see `docs/legal/unresolved-blocker-register.md`)

| # | Summary | Status |
|---|---------|--------|
| U1 | Transfer instrument / signatory authority for brand-named assets; grant signatory | **UNRESOLVED** |
| U2 | Backend licence compatibility (19 direct / 114 transitive UNVERIFIED; LGPL/UPL/MPL/ISC questions) | **UNRESOLVED** |
| U3 | Scope of "original docs" for PROPOSED docs grant | **UNRESOLVED** |
| U4 | Authorship dates / contributors per file unextracted | **UNRESOLVED** |
| U5 | Official AGPL-3.0 text NOT fetched/verified | **UNRESOLVED** (expected; later-slice step) |
| U6 | Slice-2 inventory confirms U2 still open (LGPL/UPL/MPL/ISC UNVERIFIED) | **UNRESOLVED** |
| U7 | Brand UI surface relicensing / rebrand / retain instrument | **UNRESOLVED** |
| U8 | Event-namespace and package/service/hosted-URL rename-or-retain authority | **UNRESOLVED** |
| U9 | Backend core/main + contracts/rules relicensing instrument | **UNRESOLVED** |
| U10 | Render/docker/makefile/scripts relicensing instrument; historical notice | **UNRESOLVED** |
| U11 | Triage pass report-only (138 rows with verdicts; zero Unknown reclassified to Confirmed) — clearance unchanged | **UNRESOLVED** — evidence-gathering only |
| U12 | Packaging pass PREPARED-ONLY — why root files, official text, headers, notice changes stay WITHHELD | **UNRESOLVED** |

### L1–L17: all UNVERIFIED / BLOCKED (see `docs/legal/legal-clearance-register.md`)

| # | Summary | Status |
|---|---------|--------|
| L1 | Backend licence set vs future posture (114 rows UNVERIFIED) | UNVERIFIED — clearance required |
| L2 | fpdf2 LGPL-3.0-only boundary question | UNVERIFIED — clearance required |
| L3 | Oracle UPL/Apache-2.0 mix deploy-path question | UNVERIFIED — clearance required |
| L4 | MPL-2.0 test-only confinement question | UNVERIFIED — clearance required |
| L5 | ISC `lucide-react` frontend-bundle question | UNVERIFIED — clearance required |
| L6 | Docs-grant scope confirmation | PROPOSED — scope confirmation required |
| L7 | No-endorsement / no-trademark-assignment wording | DRAFT — reviewer to confirm |
| L8 | fpdf2 inventory finding | UNVERIFIED — clearance required |
| L9 | oracledb/oci inventory finding | UNVERIFIED — clearance required |
| L10 | `@axe-core/playwright` MPL-2.0 confinement finding | UNVERIFIED — clearance required |
| L11 | `lucide-react` ISC compatibility finding | UNVERIFIED — clearance required |
| L12 | Express grant vs reserved-rights footer question | UNVERIFIED — clearance required |
| L13 | Derived-code vs PROPOSED posture absent transfer instrument | UNVERIFIED — clearance required |
| L14 | Trademark retain-vs-rename question; no assignment claimed | UNVERIFIED — clearance required |
| L15 | Triage Review/Blocked/Unknown record confirmation | UNVERIFIED — clearance required (triage grants none) |
| L16 | Scanner allowlist rationale + fresh-SBOM match confirmation | UNVERIFIED — clearance required |
| L17 | This packaging pass publishes nothing effective; publication waits for U1–U12 clearance with written evidence | UNVERIFIED — clearance required |

## 3. Scanner state, SBOM, no-LICENSE — publication NOT cleared

- Scanner (`ci/check_licences.py --check-only`, exit 0, 2026-11-26):
  **575 Confirmed / 2 Review required / 3 Blocked / 133 Unknown (575/2/3/133)** —
  per `spec/features/licensing-triage-remediation/triage-report.md`.
  The 2 Review rows (`argparse` Python-2.0, `caniuse-lite` CC-BY-4.0) and 3 Blocked
  rows (MPL-2.0 `@axe-core/playwright` dev-direct + transitive, `axe-core`
  transitive) need reviewer confirmation; the 133 Unknown rows (19 backend direct
  + 114 backend transitive) are all UNVERIFIED. Triage reclassified zero Unknown
  rows to Confirmed.
- SBOM: `docs/legal/sbom-20261126T043959Z.json` is fresh (generated
  2026-11-26) and matches the 713-row inventory (62 direct / 651 transitive);
  it grants no clearance (L16).
- No `LICENSE`: root `LICENSE` / `COPYING` / `NOTICE` are absent on this branch
  (`test ! -e LICENSE && test ! -e COPYING && test ! -e NOTICE` passes) and
  absent on `main` root. No full AGPL grant text is vendored under `docs/legal/`.
- Conclusion: **publication NOT cleared** — U1–U12 UNRESOLVED, L1–L17
  UNVERIFIED/BLOCKED, scanner non-Confirmed rows open, SBOM evidence-only.

## 4. Isolation of uncleared components — UNRESOLVED, non-publishable

Uncleared brand-derived material is ISOLATED here as non-publishable: no
removal, scrub, rename, or relicensing performed by this slice, and no holder
or date asserted beyond what is sourced in the registers (holder/year: TBD —
DO NOT INVENT).

- Reserved-rights brand footer in `frontend/src/components/PublicLayout.tsx`
  (brand/footer lines; see U1, U7; L12–L14) — transfer instrument: none on file.
- `DashboardFallback` brand UI surface — U7; L12, L13.
- `ProductMockup` brand UI surface — U7; L12, L13.
- `Thread` design element — U7; L12, L13.
- Brand-prefixed event namespace (e2e spec + app event names) — U8; L14.
- Brand-named packages/services/hosted URLs (`backend/pyproject.toml`,
  `frontend/package.json`, `frontend/index.html`, sitemap, robots,
  `.env.example`) — U1, U8; L14.
- Backend core/main (`backend/app/main.py`, `backend/app/core/*`) — U9; L12, L13.
- Contracts/rules (brand-titled schemas, brand-signed packs, rule packs,
  test fixtures) — U9; L12, L13.
- Render/docker/makefile/scripts (`render.yaml`, `docker-compose.yml`,
  Dockerfiles, `Makefile`, `ci/run_backend_tests.sh`, `backend/scripts/`) plus
  the historical reserved-rights notice — U4, U10; L12, L13.

Third-party terms are unchanged by this slice: no third-party notice added,
removed, or modified; no dependency added, removed, or upgraded (L12–L17).

## 5. Holder / year / contacts — TBD only (DO NOT INVENT)

- Rights holder: **TBD — DO NOT INVENT** (no holder asserted in this file).
- Year / dates: **TBD — DO NOT INVENT** (no year asserted in this file;
  per-file authorship/dates per U4 unextracted).
- Security contact: **TBD — DO NOT INVENT** (no inbox designated; `SECURITY.md`
  placeholders only, no SLA claimed).
- Conduct enforcement contact: **TBD — DO NOT INVENT**.
- No contact address, inbox, or response timeline is asserted anywhere in
  this file.

## 6. What this slice did and did not do

- Did: created this withheld-publication review file on the isolated prep
  branch; verified the `LICENSE.AGPL-3.0.prepared` placeholder still states the
  official text was NOT fetched; verified root `LICENSE`/`COPYING`/`NOTICE`
  absent, no source headers inserted, `main` root clean.
- Did not: publish any effective licence; fetch `gnu.org` text; insert any
  header; finalize any `NOTICE`/third-party file; modify any brand-derived or
  third-party notice; change any production, dependency, or CI file; push,
  merge, release, or alter visibility. Push / merge / publication each require
  separate explicit human approval.
