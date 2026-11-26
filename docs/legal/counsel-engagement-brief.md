# Counsel Engagement Brief — PREPARED-ONLY (NO LEGAL EFFECT)

> Status: **PREPARED-ONLY briefing pack for external counsel. No legal
> effect.** This file requests advice; it states no conclusions. All blockers
> U1–U12 remain open and all clearance items L1–L17 remain undetermined.
> Publication of any licensing package remains withheld (U12 / L17). No
> push, merge, release, or visibility change is performed or authorised by
> this file.

## 1. Background

- The LibrePeople tree was extracted from Karmathy branch
  `feature/librepeople-production` at commit
  `5a6461ea0709911693cae7a4b7ff897bca8c2c13` via `git archive HEAD`
  (tracked files only; no history mirror) — see `README.md` line 7.
- No transfer instrument, employment/contractor record, or corporate
  authorisation for the Karmathy-originated material is on file in the
  repository (U1 finding; repo-wide instrument search negative).
- The proposed (PROPOSED ONLY) posture is AGPL-3.0-or-later for the
  application and CC BY 4.0 for original documentation (decisions D3–D4;
  owner decisions O1–O5 remain OPEN).
- Prior evidence packs: `docs/legal/legal-review-package.md` (§§1–§10
  reviewer questions), `docs/legal/final-ownership-decision-register.md`
  (U1–U12 evidence record),
  `docs/legal/final-licensing-decision-register.md` (Track-2 technical
  summary), `docs/legal/legal-clearance-register.md` (L1–L17).

## 2. Declaration summary (as received — NOT independently verified)

- Founder-provided declaration (received 2026-11-26, NOT independently
  verified), recorded verbatim in
  `docs/legal/founder-ownership-declaration.md`:
  1. The founder personally developed Karmathy from scratch.
  2. The founder is the founder of Karmathy.
  3. The founder is also the founder of LibrePeople.
  4. The founder asserts original ownership of Karmathy's independently created intellectual property.
  5. The founder intends to authorize the use of the rights they own in LibrePeople.
  6. The proposed LibrePeople application licence is AGPL-3.0-or-later.
  7. The proposed documentation licence is CC BY 4.0.
- No identity, company, employment, date, or signature details were supplied;
  all such fields are [BRACKETED]. The declaration changes nothing about
  third-party obligations (stated explicitly per item in §§5–6 below).

## 3. Provenance and extraction evidence

- README `Source provenance` (`README.md` line 7): extraction method and
  source commit as in §1 above — a provenance statement, not a grant.
- Transfer manifest figure: **1831 files per programme transfer manifest
  (mandate brief §7)**.
- Current tree: `git ls-files | wc -l` = **1996** at branch HEAD
  `chore/founder-ownership-licensing` (from main `60dc8c9`) — labelled
  "current tree (includes post-transfer work)". The difference is expected
  growth, NOT an error; no reconciliation is attempted here.
- In-repo history covers 2026-11-25–2026-11-26 only; pre-extraction authorship
  is not evidenced here. Zero `Signed-off-by` trailers in history (U4).
- Evidence index: `docs/legal/provenance-evidence.md` (22-row path index),
  `docs/legal/chain-of-title-appendix.md`,
  `docs/legal/ownership-and-provenance-register.md`.

## 4. U1–U12 matrix snapshot (all OPEN; declaration input noted, never conclusive)

| ID | Status before | Declaration input (DECLARED unverified — no conclusive status claimed) | Counsel/owner action still required |
|----|---------------|---------------------------------------------------------------------|--------------------------------------|
| U1 | NOT DOCUMENTED | Points 1–5 recorded as DECLARED (unverified) provenance pointer | Signed transfer instrument + counsel confirmation (closure criteria unchanged) |
| U2 | PARTIALLY DOCUMENTED | None — declaration changes nothing about third-party obligations | Counsel compatibility determination per licence group |
| U3 | NOT DOCUMENTED | Points 6–7 recorded as DECLARED (unverified) intent only | Filed scope list + counsel confirmation |
| U4 | PARTIALLY DOCUMENTED | Points 1–2 recorded as DECLARED (unverified) authorship pointer | Authorship records + declarations + counsel on sufficiency |
| U5 | NOT DOCUMENTED | Point 6 recorded as DECLARED (unverified) intent; text still NOT fetched | Fetch/verify official text + counsel pre-publication review |
| U6 | PARTIALLY DOCUMENTED | None — declaration changes nothing about third-party obligations | Counsel clearance per group |
| U7 | NOT DOCUMENTED | Points 1–5 recorded as DECLARED (unverified) pointer | Signed brand instrument + counsel note |
| U8 | NOT DOCUMENTED | Points 1–5 recorded as DECLARED (unverified) pointer | Filed authorisation + counsel note |
| U9 | NOT DOCUMENTED | Points 4–5 recorded as DECLARED (unverified) pointer | Signed instrument + counsel confirmation |
| U10 | NOT DOCUMENTED | Points 4–5 recorded as DECLARED (unverified) pointer | Signed instrument + counsel note |
| U11 | PARTIALLY DOCUMENTED | None — declaration changes nothing about third-party obligations | Counsel-signed clearance records |
| U12 | PARTIALLY DOCUMENTED | Package still WITHHELD; declaration grants no clearance | All U1–U11 closed + written counsel publication approval |

## 5. L1–L17 matrix snapshot (all UNDETERMINED; declaration changes nothing on third-party items)

| ID | Standing | Declaration effect |
|----|----------|--------------------|
| L1 | UNVERIFIED — clearance required | None — declaration changes nothing about third-party obligations |
| L2 | UNVERIFIED — clearance required | None — declaration changes nothing about third-party obligations |
| L3 | UNVERIFIED — clearance required | None — declaration changes nothing about third-party obligations |
| L4 | UNVERIFIED — clearance required | None — declaration changes nothing about third-party obligations |
| L5 | UNVERIFIED — clearance required | None — declaration changes nothing about third-party obligations |
| L6 | PROPOSED — scope confirmation required | Point 7 recorded as DECLARED (unverified) intent only; scope still undefined |
| L7 | DRAFT — reviewer to confirm | None |
| L8 | UNVERIFIED — clearance required | None — declaration changes nothing about third-party obligations |
| L9 | UNVERIFIED — clearance required | None — declaration changes nothing about third-party obligations |
| L10 | UNVERIFIED — clearance required | None — declaration changes nothing about third-party obligations |
| L11 | UNVERIFIED — clearance required | None — declaration changes nothing about third-party obligations |
| L12 | UNVERIFIED — clearance required | Points 4–5 recorded as DECLARED (unverified); grant text still absent |
| L13 | UNVERIFIED — clearance required | Points 4–5 recorded as DECLARED (unverified); posture still PROPOSED |
| L14 | UNVERIFIED — clearance required | None — no assignment claimed; declaration supplies no trademark authority |
| L15 | UNVERIFIED — clearance required (triage grants none) | None — declaration changes nothing about third-party obligations |
| L16 | UNVERIFIED — clearance required | None — declaration changes nothing about third-party obligations |
| L17 | UNVERIFIED — clearance required | None — publication still WITHHELD |

## 6. SBOM and inventory counts

- `docs/legal/dependency-licence-inventory.json`: 715 rows (64 direct / 651
  transitive per Track-2 update; invset == SBOM-union).
- `docs/legal/sbom-20261126T043959Z.json`: 715 components (current).
- `docs/legal/sbom-20261126T012556Z.json`: retained as historical snapshot.
- Checker (`ci/check_licences.py --check-only`): Confirmed 672 / Review 34 /
  Blocked 9 / Unknown 0 — mechanical mapping only; counsel must confirm.

## 7. Proposed structure (for counsel to approve or correct)

- Application code → AGPL-3.0-or-later (PROPOSED, subject to clearance).
- Original documentation → CC BY 4.0 (PROPOSED, subject to clearance; scope
  "original docs only" still to be enumerated).
- Third-party material → retains original licences and notices; compatibility
  to be determined by counsel.
- Commercial/dual licensing → separate analysis required; no terms offered.

## 8. Draft instruments enclosed (both DRAFT — NOT EXECUTED)

- `docs/legal/karmathy-librepeople-ip-authorization.md` — IP authorization
  draft with Alternatives A (individual ownership, authorization only) and B
  (company ownership, assignment + corporate authorization required).
- `docs/legal/librepeople-licensing-authorization.md` — licensing
  authorization draft (AGPL-3.0-or-later + CC BY 4.0, both PROPOSED; effective
  date BLANK).
- `docs/legal/founder-ownership-declaration.md` — verbatim declaration record.

## 9. Questions for counsel (source: programme mandate brief §7 — "Ask counsel to determine")

1. Whether founder ownership is sufficiently established.
2. Whether additional assignments are needed.
3. Whether any corporate ownership or authorization issues exist.
4. Whether AGPL-3.0-or-later can lawfully cover the application.
5. Whether CC BY 4.0 is appropriate for the documentation.
6. Whether third-party obligations are satisfied.
7. Whether commercial licensing or dual licensing is possible.
8. What must be completed before public publication.

## 10. Written opinions requested

- (a) Ownership sufficiency opinion covering questions 1–3 above, with the
  evidence counsel relied on and any further records required.
- (b) Licence-posture opinion covering questions 4–6 above, per licence
  group, with compatibility determinations suitable for filing in
  `docs/legal/`.
- (c) Commercial/dual-licensing viability opinion covering question 7.
- (d) Publication-gate opinion covering question 8, listing the exact
  completion criteria for U1–U12 / L1–L17.

## 11. Execution documents needed from the owner side

- Completed declarant identity / entity / capacity particulars (currently all
  [BRACKETED]).
- Employment / contractor history statement (or confirmation none exists).
- Alternative A or B selection with supporting records (entity identification
  and corporate authorisation under Alternative B).
- Executed IP authorization + executed licensing authorization (both currently
  DRAFT — NOT EXECUTED, signatures BLANK).
- Enumerated "original docs" scope list (U3 / L6).
- Fetched and verified official AGPL-3.0 text (U5).

## 12. Publication conditions (explicit — nothing published until ALL hold)

- Nothing is published until: (1) every U1–U11 item closed with filed
  artefacts; (2) every L1–L16 item determined by counsel in writing;
  (3) executed IP authorization on file; (4) official AGPL-3.0 text fetched
  and verified; (5) docs scope enumerated and approved; (6) written counsel
  publication approval recorded (U12; L17). Until then: no root
  `LICENSE`/`COPYING`/`NOTICE`, no headers, no notice changes, no visibility
  change.
