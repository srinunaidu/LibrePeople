# Founder Ownership Declaration — RECORD ONLY (NO LEGAL EFFECT)

> Status: **RECORD ONLY. No legal effect.** This file transcribes statements
> received from the founder. It makes no determination of rights, title, or
> registrability. Nothing in this file is independently verified. Every item
> remains subject to counsel review and owner action as routed in
> `docs/legal/final-ownership-decision-register.md` (U1–U12) and
> `docs/legal/legal-clearance-register.md` (L1–L17). Do not rely on this file
> to assert any rights position. Publication of any licensing package remains
> withheld (see U12 / L17).

## Source

- Founder-provided declaration (received 2026-11-26, NOT independently verified).
- Source: programme mandate brief §1, transcribed verbatim below.
- Record prepared on branch `chore/founder-ownership-licensing` from main
  `60dc8c9`. No personal, company, employment, date, or signature details were
  supplied; all such fields are left as [BRACKETED] placeholders. None have
  been filled in or inferred.

## Founder-provided points (verbatim, as received)

1. The founder personally developed Karmathy from scratch.
2. The founder is the founder of Karmathy.
3. The founder is also the founder of LibrePeople.
4. The founder asserts original ownership of Karmathy's independently created intellectual property.
5. The founder intends to authorize the use of the rights they own in LibrePeople.
6. The proposed LibrePeople application licence is AGPL-3.0-or-later.
7. The proposed documentation licence is CC BY 4.0.

## Identity and authority fields (all [BRACKETED] — not supplied, not inferred)

- Declarant full legal name: [FOUNDER FULL LEGAL NAME]
- Declarant contact / address: [CONTACT DETAILS]
- Karmathy entity (company name, registration number, jurisdiction): [KARMATHY ENTITY DETAILS]
- LibrePeople entity or project vehicle (name, form, jurisdiction): [LIBREPEOPLE ENTITY DETAILS]
- Role/capacity in which the declarant signs (e.g. individual, director, authorised officer): [CAPACITY]
- Employment / contractor history relevant to creation of the IP: [NOT SUPPLIED — requires owner to state or confirm none exists]
- Date of declaration: [DATE — BLANK, to be completed only at execution]
- Place of declaration: [PLACE — BLANK]
- Signature: [SIGNATURE — BLANK]
- Witness / notary (if counsel advises): [WITNESS — BLANK]

## Personal-creation claim (as asserted, not verified)

- The declaration asserts personal development of Karmathy from scratch
  (points 1–2 above, verbatim). No corroborating records (employment
  agreements, contractor agreements, commit-history exports, assignment deeds)
  are on file in this repository. Corroboration is routed to counsel (U4).

## Ownership claim (as asserted, not verified)

- The declaration asserts original ownership of Karmathy's independently
  created intellectual property (point 4 above, verbatim). No transfer
  instrument, title search, or corporate-ownership record is on file in this
  repository. Sufficiency of this assertion is routed to counsel (U1, U7–U10).

## Karmathy → LibrePeople history (as asserted, not verified)

- The declaration states an intention to authorize the use of the rights the
  founder owns in LibrePeople (point 5 above, verbatim). No executed
  authorisation instrument is on file. The repository's factual provenance
  record is separate: `README.md` records extraction from Karmathy branch
  `feature/librepeople-production` at commit
  `5a6461ea0709911693cae7a4b7ff897bca8c2c13` via `git archive HEAD`
  (tracked files only — a provenance statement, not a grant).

## IP scope covered by the declaration (as asserted, not verified)

- The declaration refers to "Karmathy's independently created intellectual
  property" without enumerating items. Pending counsel scope determination,
  the candidate in-repo scope (location pointers only, not a grant) is:
  - Package/brand names and marks (`backend/pyproject.toml:2`,
    `frontend/package.json:2`, `© 2026 Karmathy` footer in
    `frontend/src/components/PublicLayout.tsx`).
  - Brand UI surface (DashboardFallback, ProductMockup, Thread, `seo.ts`,
    tenant fallbacks, brand assets) — see U7.
  - `karmathy:*` event namespace and service/URL names — see U8.
  - Backend core/main, contracts/rules artefacts, `signed_by: Karmathy
    Compliance` packs — see U9.
  - Render/docker/makefile/scripts and historical notices — see U10.

## Third-party EXCLUSIONS (not covered by the declaration)

- The declaration covers only rights the founder owns (point 5: "the rights
  they own"). It does not extend to, and must not be read as covering, any
  third-party material. Excluded categories include:
  - Third-party open-source dependencies (backend pins and transitive sets,
    frontend direct/transitive sets) — each retains its original licence and
    notices; see L1–L5, L8–L11, L15–L16.
  - Oracle packages (`oracledb`, `oci`) under UPL-1.0 / Apache-2.0 mix.
  - LGPL-family components (`fpdf2`, `psycopg2-binary`, `crc32c`).
  - MPL-2.0 components (`@axe-core/playwright`, `axe-core`, `certifi`,
    `orjson`).
  - ISC `lucide-react` and other permissive-licensed frontend bundle content.
  - Data-licensed / legacy transitive entries (`caniuse-lite` CC-BY-4.0,
    `argparse` Python-2.0).
  - Base images, fonts, icons, and other upstream assets per
    `docs/licensing/provenance-and-exclusions.md`.
- Compatibility and obligation questions for all excluded material remain
  entirely with counsel (U2, U6, U11; L1–L5, L8–L11, L15–L16). The declaration
  changes nothing about third-party obligations.

## Evidence index (repo paths + commit refs — locations only, no conclusions)

- Provenance statement: `README.md` (line 7).
- Extraction source: Karmathy branch `feature/librepeople-production` at
  commit `5a6461ea0709911693cae7a4b7ff897bca8c2c13` (as recorded in README).
- Transfer-manifest figure: 1831 files per programme transfer manifest
  (mandate brief §7); current tree `git ls-files | wc -l` = 1996 at branch
  HEAD (includes post-transfer work; difference is expected growth, not an
  error — no reconciliation attempted).
- Ownership evidence base: `docs/legal/final-ownership-decision-register.md`
  (U1–U12), `docs/legal/ownership-and-provenance-register.md`,
  `docs/legal/provenance-evidence.md`,
  `docs/legal/chain-of-title-appendix.md`.
- Licensing evidence base:
  `docs/legal/final-licensing-decision-register.md` (Track-2 technical
  summary), `docs/legal/legal-clearance-register.md` (L1–L17),
  `docs/legal/dependency-licence-inventory.json` (715 rows),
  `docs/legal/sbom-20261126T043959Z.json` (715 components).
- No signed instrument, employment record, or corporate register entry is on
  file for any declaration point (verified: repo-wide instrument search per
  U1 finding; zero `Signed-off-by` trailers in history).

## Date and signature (BLANK — execution requires counsel + owner action)

- Declaration date: [DATE — BLANK]
- Declarant signature: [SIGNATURE — BLANK]
- This file must not be treated as an executed declaration. Execution requires
  the closure criteria recorded against U1–U12 (signed instrument filed
  in-repo or cited with reference number + counsel written confirmation).
