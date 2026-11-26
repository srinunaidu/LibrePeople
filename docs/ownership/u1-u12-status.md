# U1–U12 Ownership Status (Agent O — facts only, no clearance, not legal advice)

Branch `agent/ops/ownership-u1-u12` from main `5b1cb52`. Read-only sweep; `API.md` not read.
No LICENSE/NOTICE/COPYING created. No signatures, consent, or ownership invented — every
gap names UNKNOWN where the party is unidentified. Legal conclusions need counsel.

## Shared evidence (applies to all items)

- Headers: zero `Copyright`/`Licensed under`/`SPDX-License-Identifier` hits across
  212 `backend/app/*.py` + 288 `frontend/src/*.ts*` (re-grep 2026-11-26; matches
  `docs/licensing/provenance-and-exclusions.md` §Source headers).
- Identity residue: `frontend/package.json` name still `"karmathy-frontend"`;
  `backend/pyproject.toml` name `karmathy-backend`, description "Karmathy backend (FastAPI)".
  Footer now renders `© 2026 LibrePeople` (`PublicLayout.tsx:202`) — provenance doc's
  `© 2026 Karmathy` string is stale. Footer is a UI string, not a title claim.
- Contributors (`git log --format="%an %ae" | sort -u`, names only): Agent E (Deployment+Ops),
  LibrePeople Extraction, srinivas, tier-coder. No external authors recorded; roles/employment
  status of none established.
- Chain commits verified: `f8877a1` standalone repo, `62d741a` HCM backend+frontend migrate,
  rebrand `b468324` + `66b751d`. (Note: `216e869` is a register roll-up, not a rebrand commit
  as `legal-review-package.md` §4 states — counsel to use the rebrand SHAs above.)
- No `vendor/`/`third_party/` dirs at any depth. No author/contributor/license fields beyond
  the package names above. Repo visibility UNVERIFIED (per legal-review-package §5).

## Per-item status

### U1 — Transfer Karmathy → LibrePeople — PARTIAL
Affected: whole tree (migration `62d741a`, rebrands above). Evidence: git history shows code
movement, not title. Owner: UNKNOWN. Missing: bill of sale / IP transfer deed, schedule of
assets, effective date, consideration. Needed doc TITLE: "Intellectual Property Assignment
(Karmathy → LibrePeople)" — fields: assignor, assignee, asset schedule, effective date,
consideration, warranties, signatories, governing law. Signatory: UNKNOWN (authorised
officer of Karmathy-side transferor + LibrePeople-side transferee — identities unrecorded).
Next: owner names both parties; counsel drafts.

### U2 — Original authorship of HCM code — MISSING
Affected: `backend/app/**`, `frontend/src/**`. Evidence: none beyond the 4 git identities
above, which post-date the code. Owner: UNKNOWN. Missing: author list, work-for-hire /
authorship declarations. Needed TITLE: "Schedule of Original Authors" — fields: work ID,
author name, date, employment/contractor status, rights basis. Signatory: UNKNOWN (each
listed author or their employer). Next: owner commissions authorship audit; counsel advises.

### U3 — Employee contributions — MISSING
Affected: unknown subset of tree. Evidence: no employment contracts or IP-assignment clauses
on record. Owner: UNKNOWN. Missing: employment agreements with present-assignment language,
employer schedule. Needed TITLE: "Employee IP Assignment Confirmation" — fields: employee,
employer, scope (past + future works), effective date, signature. Signatory: UNKNOWN (each
employee contributor + employing entity). Next: owner identifies employing entities; counsel drafts.

### U4 — Contractor / third-party contributions — MISSING
Affected: unknown subset. Evidence: none. Owner: UNKNOWN. Missing: contractor agreements,
assignment or licence-back terms. Needed TITLE: "Contractor IP Assignment / Work-for-Hire
Agreement" — fields: contractor, engaging entity, deliverables, assignment vs licence,
consideration, signature. Signatory: UNKNOWN (each contractor + engaging entity). Next: owner
lists all contractors; counsel drafts.

### U5 — Current copyright ownership — MISSING
Affected: whole tree. Evidence: no ownership claim anywhere (licensing docs + legal-review
package expressly disclaim). Footer UI string is not title. Owner: UNKNOWN. Missing: chain-of-title
opinion, title register. Needed TITLE: "Chain-of-Title Memorandum" — fields: asset, each link
(transferor→transferee, instrument, date), gaps flagged. Signatory: counsel (opinion), owner
(instructs). Next: owner engages counsel; do not assert ownership meanwhile.

### U6 — Contributor rights / licences back — MISSING
Affected: any contributor-retained rights. Evidence: none (no CLAs, no licence-backs).
Owner: UNKNOWN. Missing: CLA register, inbound licence terms. Needed TITLE: "Contributor
Licence Agreement (inbound)" — fields: contributor, grant scope, patent grant, moral-rights
position, signature. Signatory: UNKNOWN (each contributor). Next: owner decides CLA vs
assignment policy; counsel drafts.

### U7 — Third-party / dependency materials — PARTIAL
Affected: `backend/requirements.txt` (19 pins → 114 freeze rows), `frontend/package.json`
(24+19) + lock (538 entries). Evidence: `docs/licensing/*`, SBOM JSONs; 9 backend rows
UNVERIFIED (fastapi, Jinja2, markdown-it-py, mdurl, oci, pip_api, pip_audit, scipy, tomli_w);
flagged oracledb / oci / fpdf2 unconfirmed for redistribution. Owner: respective upstreams
(licence confirmation pending — not concluded here). Missing: full licence scan, acceptance
record. Needed TITLE: "Third-Party Licence Acceptance Record" — fields: package, version,
licence (from metadata), use (link/static/dynamic), acceptance, approver + date. Signatory:
owner + counsel (acceptance decision). Next: run full scan; counsel clears redistribution.

### U8 — Vendored / bundled materials — ESTABLISHED (as observed fact, not clearance)
Affected: n/a — no `vendor/`/`third_party/` dirs exist; no bundled `.ttf`; fpdf2 used via
lazy unmodified import (`offer_letter.py:77`); no wallet/SDK vendored (git-ignored).
Owner: n/a (nothing vendored). Missing: re-confirmation at release cut (per checklist item 6).
Needed TITLE: none unless vendoring appears — then "Vendored-Code Schedule". Signatory: release
manager (re-confirmation). Next: re-run vendor sweep at release cut.

### U9 — Generated assets (e.g. PDFs) — PARTIAL
Affected: `backend/app/services/offer_letter.py` (fpdf2-generated offer letters), other
generators unverified. Evidence: generator code present; output ownership/licence boundary
(LGPL dynamic-use question) unresolved — needs counsel, no conclusion here. Owner: UNKNOWN.
Missing: output-ownership policy, LGPL-boundary opinion. Needed TITLE: "Generated-Output
Ownership Policy" — fields: generator, output type, rights holder rule, licence boundary
note. Signatory: owner + counsel. Next: counsel opines on fpdf2 boundary; owner adopts policy.

### U10 — Test assets / fixtures — PARTIAL
Affected: `frontend/src/**/*.test.*`, e2e dirs, `admin_*_test.db` (git-ignored, uninventoried).
Evidence: test files exist in-repo; provenance/rights unrecorded; third-party fixtures
(e.g. axe-core MPL-2.0, test-only) noted in legal-review-package §3. Owner: UNKNOWN for
in-house fixtures; respective upstreams for tooling. Missing: fixture-provenance list.
Needed TITLE: "Test-Asset Provenance Schedule" — fields: asset, source (in-house/upstream),
licence, shipped-vs-test-only. Signatory: QA/engineering lead (inventory) + counsel (review).
Next: inventory fixtures incl. `.gitignore`d local DBs at release cut.

### U11 — Proposed LibrePeople rights holder — MISSING
Affected: future LICENSE/NOTICE, footer, package identity fields. Evidence: no designated
rights-holder entity on record; visibility UNVERIFIED. Owner: UNKNOWN (TBD by owner).
Missing: entity designation, holder-name decision, rename of `karmathy-*` package names.
Needed TITLE: "Rights-Holder Designation" — fields: legal entity name, jurisdiction,
effective date, authorising resolution, signatory. Signatory: UNKNOWN (owner-side authorised
officer — identity unrecorded). Next: owner names entity + approver; counsel records.

### U12 — Unresolved register entries touching ownership — PARTIAL
Affected: `docs/release/blocker-register.md`, `decision-register.md` (DOC-003 PENDING,
NFR-012/013 PENDING), `external-dependency-register.md:34` ("ownership/authority
confirmation, third-party licence review + notices"). Evidence: registers list the gaps but
contain no ownership entries. Owner: UNKNOWN. Missing: ownership section in each register,
authority confirmations. Needed TITLE: "Register Ownership Addendum" — fields: register,
entry ID, ownership question, resolution, sign-off. Signatory: product owner (register) +
counsel (confirmation). Next: owner routes register gaps to counsel before release.

## Counts

ESTABLISHED 1 (U8) · PARTIAL 5 (U1, U7, U9, U10, U12) · MISSING 6 (U2, U3, U4, U5, U6, U11).
No item is cleared. Nothing here is legal advice.
