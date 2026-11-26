# Final Ownership Decision Register — EVIDENCE ONLY (PREPARED-ONLY, Tier 1)

> Status: **EVIDENCE RECORD ONLY. No legal effect.** This file records what
> evidence was examined and what was factually found. It makes no
> determination of rights, title, or registrability. Every open item
> **requires counsel and/or owner action** as routed below. Do not rely on
> this file to assert any rights position. Prepared on branch
> `agent/legal/ownership-evidence` from main HEAD `d80c0cd`.

## Method (commands run, read-only)

- `git log --format='%an <%ae>' | sort | uniq -c` → contributor list (§A of appendix).
- `git log --follow --format='%an %ad %s'` per top-10 file → appendix §B.
- `git ls-files | grep -iE 'assign|transfer|deed|contribut|cla|copyright|license|notice|employment|contractor|waiver'` + root `LICENSE`/`NOTICE`/`COPYING` check → §D.
- Prior registers read as evidence inputs (not as conclusions):
  `docs/legal/ownership-and-provenance-register.md`,
  `docs/legal/provenance-evidence.md`, `docs/legal/decision-register.md`,
  `docs/legal/unresolved-blocker-register.md`, `docs/legal/legal-clearance-register.md`.

## Status vocabulary (used strictly)

- **ESTABLISHED-BY-EVIDENCE** — a signed instrument exists in-repo. (Expected: none.)
- **PARTIALLY DOCUMENTED** — version history exists but the signed instrument is missing.
- **NOT DOCUMENTED** — neither history attribution for the item nor any instrument is on file.

## Per-component table (factual authorship signals only — not rights claims)

| Component | Primary authors (from `git log`) | Evidence strength | Missing instruments | Required signatory TYPE (no names invented) |
|---|---|---|---|---|
| backend (`backend/app`, services, rules) | `LibrePeople Extraction` (first-commit migration); `srinivas <srinivas@example.com>` (subsequent edits, e.g. rebrand, workflow-engine) | Medium: first+last commits recorded per file; pre-extraction history absent (archive without history mirror) | Assignment/transfer instrument for Karmathy-derived code; employment/contractor agreements; contributor declarations; DCO sign-offs (zero `Signed-off-by` trailers found in 198 commits) | Counsel review + owner-side signatory: employer of contributor `srinivas` (UNKNOWN — requires owner to identify) and/or rights holder of Karmathy-marked code (UNKNOWN — requires owner to identify) |
| frontend (`frontend/src`) | Same pattern: Extraction first-commit; `srinivas` subsequent (rebrand, ds-unify b1–b3, module additions) | Medium: same caveat | Same as backend, plus brand-asset authority for `© 2026 Karmathy` footer and Karmathy brand surfaces | Same as backend; brand use additionally requires counsel determination |
| migrations (`backend/migrations/versions/`, 58 files; chain 0001→0047+ recorded in `backend/migrations/proof/history.txt`) | Extraction first-commit for migrated revisions; `srinivas` for strategy/proof docs | Medium: chain continuity recorded in-repo; pre-extraction authorship not evidenced in this repo | Same instruments as backend | Same as backend |
| rule_packs (`backend/rule_packs/`, `rule_packs/`, `contracts/rules/`) | Extraction first-commit; packs bear `signed_by: Karmathy Compliance` | Low–Medium: signature string is present but is a Karmathy signature, not a grant to LibrePeople | Transfer/relicensing instrument covering `signed_by: Karmathy Compliance` packs and Karmathy-titled schemas | Counsel + signatory: entity/person controlling `Karmathy Compliance` signatures (UNKNOWN — requires owner to identify) |
| docs (incl. `docs/legal/`, `docs/licensing/`) | `srinivas` (licensing slices); `LibrePeople Extraction` (migrated docs) | Medium: in-repo authorship visible; scope of "original docs" for any proposed grant undefined (U3) | Scope confirmation; no signed grant on file | Counsel (scope determination) + owner signatory |
| seed (`seed/dev/seed_dev.py`, `seed/prod/seed_prod.py`) | Extraction first-commit (migrated) | Low: synthetic-data claim rests on file header text (`Karmathy HCM — deterministic synthetic seed generator`); no independent verification run in this slice | Provenance attestation for seed content; confirmation no production/personal data present | Owner-side attestation (responsible party: UNKNOWN — requires owner to designate) + counsel if seed ships |
| config/deploy (`render.yaml`, `docker-compose.yml`, Dockerfiles, `Makefile`, `ci/*`, `backend/scripts/*`) | Extraction first-commit; `Agent E (Deployment+Ops)` standalone-ops commit 2026-11-25 | Medium | Same instruments as backend | Same as backend |
| tests (`backend/*_test_suite.py`, `frontend/e2e/*`, `backend/app/**/tests/*`) | Extraction first-commit; `srinivas`; `tier-coder` (2 commits, automation) | Medium | Contributor declarations for human and automation-authored test content | Counsel + owner signatory (same as backend); automation output requires owner policy on machine-assisted contributions |

## U1–U12 adjudication (EVIDENCE vocabulary only)

### U1 — Instrument transferring Karmathy assets (package names, `© 2026 Karmathy` footer/brand)
- Question: By what written instrument and signatory authority were Karmathy assets transferred to LibrePeople, and who may sign the grant?
- Evidence examined: `backend/pyproject.toml:2`, `frontend/package.json:2`, `frontend/src/components/PublicLayout.tsx` (~105/~172/~198/~202); repo-wide instrument search (§D appendix — no assignment/deed/transfer file found); root `LICENSE`/`COPYING`/`NOTICE` absent (verified `ls`).
- Finding (factual): No transfer instrument is present in the repository. Karmathy marks are preserved verbatim in-tree. README `Source provenance` records extraction from Karmathy branch `feature/librepeople-production` at commit `5a6461e` via `git archive` (tracked files only) — a provenance statement, not a grant.
- Confidence: **High** (absence verified by filename search + root listing; presence of marks verified by read).
- Missing evidence: Signed assignment/transfer; signatory authority record; Karmathy-side authorisation.
- Required approval + responsible party: **Requires counsel** (instrument validity/sufficiency) + **owner-side signatory** (UNKNOWN — requires owner to identify the Karmathy rights holder and the LibrePeople receiving party).
- Closure criteria: Signed instrument filed in-repo (or its location cited with reference number) + counsel written confirmation recorded.
- Status: **NOT DOCUMENTED**.

### U2 — Third-party licence compatibility (backend direct/transitive, fpdf2, Oracle UPL mix, MPL-2.0 test-only, ISC lucide-react)
- Question: Are the inventoried third-party terms compatible with the proposed posture?
- Evidence examined: `docs/licensing/backend-direct.md`, `backend-transitive.md`, `copyleft-and-proprietary.md`, `provenance-and-exclusions.md`; `docs/legal/dependency-licence-inventory.json`; `legal-clearance-register.md` L1–L5. No independent re-verification run in this slice.
- Finding: Inventory files exist and describe the licences as UNVERIFIED locally. No compatibility determination is recorded as counsel-signed.
- Confidence: **Medium** (inventory presence confirmed; compatibility evidence not examined here).
- Missing evidence: Counsel compatibility determination with written record.
- Required approval + responsible party: **Requires counsel**.
- Closure criteria: Counsel-signed compatibility note per licence group, filed in `docs/legal/`.
- Status: **PARTIALLY DOCUMENTED** (inventory exists, determination missing).

### U3 — Scope of "original docs" for any proposed docs grant
- Question: What exactly counts as "original docs"?
- Evidence examined: `CONTRIBUTING.md`, `docs/legal/contributor-dco-guidance.md`, decision-register D4. No scope definition file found.
- Finding: No scope statement beyond the constraint phrase "original docs only" exists in-repo.
- Confidence: **High** (searched; absent).
- Missing evidence: Enumerated scope list.
- Required approval + responsible party: **Requires counsel** (scope determination) + owner sign-off.
- Closure criteria: Filed scope list + counsel confirmation.
- Status: **NOT DOCUMENTED**.

### U4 — Authorship dates and contributors per `unclear` row
- Question: Who wrote what, when, for each `unclear` register row?
- Evidence examined: `git log` contributor counts + per-file first/last histories (appendix §§A–B). Pre-extraction history is absent by construction (`git archive`, no history mirror). Zero `Signed-off-by` trailers in 198 commits.
- Finding: In-repo history covers 2026-11-25–2026-11-26 only. Pre-extraction authorship/dates are not evidenced in this repository. DCO process is described in docs but no DCO sign-off is present in commit trailers.
- Confidence: **High** for the in-repo window; **Low** for anything pre-extraction (no evidence available here).
- Missing evidence: Pre-extraction authorship records; contributor declarations; DCO sign-offs.
- Required approval + responsible party: **Requires owner** to supply or attest authorship records (responsible party UNKNOWN — requires owner to designate) + **counsel** on sufficiency.
- Closure criteria: Per-file authorship table sourced to records + filed declarations.
- Status: **PARTIALLY DOCUMENTED** (in-repo window recorded; pre-extraction missing).

### U5 — Official AGPL-3.0 text fetched and verified
- Question: Has the official text been fetched from gnu.org and verified?
- Evidence examined: `docs/legal/LICENSE.AGPL-3.0.prepared` (states text NOT fetched); root `LICENSE`/`COPYING` absent.
- Finding: Not fetched; not published. Factually absent.
- Confidence: **High**.
- Missing evidence: Fetched text + verification record.
- Required approval + responsible party: Owner-side action (fetch/verify) + **counsel** before any publication step.
- Closure criteria: Verified text on file + verification note. (Publication itself stays withheld per U12.)
- Status: **NOT DOCUMENTED**.

### U6 — Slice-2 inventory confirmation (713 rows; fpdf2, Oracle mix, MPL-2.0, ISC)
- Question: Does the Slice-2 inventory change any clearance position?
- Evidence examined: `docs/legal/dependency-licence-inventory.json`, `docs/legal/sbom-20261126T012556Z.json`, `compliance-ci.md`, `legal-clearance-register.md` L8–L11 (read as inputs; triage verdicts recorded as evidence-gathering only, per U11).
- Finding: Inventory/triage records exist; the register itself records triage as evidence-gathering with no clearance granted.
- Confidence: **Medium** (files present; substance not re-audited here).
- Missing evidence: Counsel clearance per group.
- Required approval + responsible party: **Requires counsel**.
- Closure criteria: Same as U2, per group.
- Status: **PARTIALLY DOCUMENTED**.

### U7 — Instrument for Karmathy brand UI surface (footer, DashboardFallback, ProductMockup, Thread, seo.ts, tenant fallbacks, brand assets)
- Question: By what instrument may the brand surface be relicensed, rebranded, or retained?
- Evidence examined: Paths listed in `unresolved-blocker-register.md` U7 + register rows 3–6, 12, 19–20 (accepted as location pointers; spot-read `PublicLayout.tsx` footer line and `seo.ts` in prior slice records).
- Finding: No brand-transfer or rebrand-authorisation instrument is on file. Marks preserved verbatim.
- Confidence: **High** for absence of instrument (repo-wide search); **Medium** for per-file mark locations (pointer-based).
- Missing evidence: Brand assignment/authorisation; signatory authority.
- Required approval + responsible party: **Requires counsel** + owner-side brand holder signatory (UNKNOWN — requires owner to identify).
- Closure criteria: Signed brand instrument + counsel note; any rename executed only after that.
- Status: **NOT DOCUMENTED**.

### U8 — Instrument for `karmathy:*` event namespace and package/service/URL names
- Question: By what instrument may these names be renamed or retained, and who may authorise it?
- Evidence examined: `frontend/e2e/redesign-e2e.spec.ts:96–109` (pointer), `backend/pyproject.toml:2`, `frontend/package.json:2`, `index.html`, `sitemap.xml`, `robots.txt`, `.env.example` (pointers from register).
- Finding: No rename/retention authority is on file. Names preserved verbatim.
- Confidence: **High** (absence); **Medium** (locations pointer-based).
- Missing evidence: Written authorisation covering trademark/service-name use and rename authority.
- Required approval + responsible party: **Requires counsel** + owner-side signatory (UNKNOWN — requires owner to identify).
- Closure criteria: Filed authorisation + counsel note.
- Status: **NOT DOCUMENTED**.

### U9 — Instrument for Karmathy-derived backend core/main and contracts/rules artefacts
- Question: By what instrument may these be relicensed under the proposed posture?
- Evidence examined: Register rows 9–10 pointers (`backend/app/main.py`, `core/*`, `contracts/rules/`, `backend/rule_packs/in-standard.json:609` with `signed_by: Karmathy Compliance`, test fixtures).
- Finding: No relicensing instrument on file. The `signed_by: Karmathy Compliance` string is a Karmathy signature record, not a grant to LibrePeople.
- Confidence: **High** (absence); **Medium** (locations pointer-based; signature string verified by grep).
- Missing evidence: Relicensing/transfer instrument from the controlling party of Karmathy-signed artefacts.
- Required approval + responsible party: **Requires counsel** + signatory controlling Karmathy Compliance signatures (UNKNOWN — requires owner to identify).
- Closure criteria: Signed instrument + counsel confirmation.
- Status: **NOT DOCUMENTED**.

### U10 — Instrument for render/docker/makefile/scripts and the historical `©` notice
- Question: By what instrument may these be relicensed or modified?
- Evidence examined: Register rows 11, 20 pointers (`render.yaml`, `docker-compose.yml`, Dockerfiles, `Makefile`, `ci/run_backend_tests.sh`, `backend/scripts/`).
- Finding: No instrument on file.
- Confidence: **High** (absence); **Medium** (locations pointer-based).
- Missing evidence: Same class as U9.
- Required approval + responsible party: **Requires counsel** + owner-side signatory (UNKNOWN).
- Closure criteria: Signed instrument + counsel note.
- Status: **NOT DOCUMENTED**.

### U11 — Triage pass 2026-11-26: does it change any clearance status?
- Question: Do triage records plus L15–L16 change clearance?
- Evidence examined: `docs/legal/dependency-licence-inventory.json` (138 triaged rows, per U11 text), `docs/legal/sbom-20261126T043959Z.json`, `docs/legal/compliance-ci.md`, `spec/features/licensing-triage-remediation/triage-report.md` (as cited; substance not re-audited here).
- Finding: The register itself records triage as evidence-gathering only with zero Unknown→Confirmed reclassifications and no clearance granted.
- Confidence: **Medium** (reliance on register's own characterisation).
- Missing evidence: Counsel clearance per row/group.
- Required approval + responsible party: **Requires counsel**.
- Closure criteria: Counsel-signed clearance records.
- Status: **PARTIALLY DOCUMENTED** (triage evidence exists; clearance missing).

### U12 — What prevents publication of the prepared licensing package?
- Question: Why must root `LICENSE`/`COPYING`/`NOTICE`, official text, headers, and notice changes stay withheld while U1–U11 remain open?
- Evidence examined: `docs/legal/licensing-package-status.md` (prepared-vs-withheld table), `LICENSE.AGPL-3.0.prepared` (text NOT fetched), root absence verified by `ls`, no `SPDX-License-Identifier` under `backend/app`/`frontend/src` (per U12 text; not re-grepped here).
- Finding: Publication blockers recorded: no fetched licence text, no resolved transfer instruments (U1, U7–U10), no compatibility determinations (U2, U6, U11), no scope definition (U3), incomplete authorship (U4). Withholding is the factually observed state.
- Confidence: **High** for the observed withheld state; **Medium** for the header-absence claim (not re-verified in this slice — flagged for re-check at closure).
- Missing evidence: All U1–U11 closure artefacts.
- Required approval + responsible party: **Requires counsel** (publication gate) + owner sign-off.
- Closure criteria: Every U1–U11 item closed with filed artefacts + written counsel publication approval. Until then: no `LICENSE`/`NOTICE` files, no headers, no notice changes.
- Status: **PARTIALLY DOCUMENTED** (blocker list exists; gate approvals missing).

## Routing summary

- **Requires counsel:** U1, U2, U3, U5 (pre-publication), U6, U7, U8, U9, U10, U11, U12.
- **Requires owner signature/attestation:** U1, U3, U4, U5, U7, U8, U9, U10, U12 (all responsible parties UNKNOWN — requires owner to identify; no names invented).
- **ESTABLISHED-BY-EVIDENCE:** none (no signed instrument exists in-repo).
- Companion fact base: `docs/legal/chain-of-title-appendix.md`.

## Addenda 2026-11-26 — founder declaration record (append-only; history above unchanged)

> Each entry below records the bearing of the founder-provided declaration
> (`docs/legal/founder-ownership-declaration.md`, received 2026-11-26, NOT
> independently verified) on one item. No entry advances any item toward a
> conclusive status: the declaration is an unverified assertion, not a
> signed instrument, title record, or counsel determination. All counsel
> requirements and closure criteria stand as written above.

- **U1 addendum 2026-11-26:** previous NOT DOCUMENTED → recorded: NOT DOCUMENTED (unchanged; no instrument on file) + founder points 1–5 filed as DECLARED (unverified). Counsel requirement retained (instrument validity/sufficiency + owner-side signatory). Exact closure criteria: signed instrument filed in-repo (or cited with reference number) + counsel written confirmation recorded.
- **U2 addendum 2026-11-26:** previous PARTIALLY DOCUMENTED → recorded: PARTIALLY DOCUMENTED (unchanged). The declaration supplies no information on this item — declaration changes nothing about third-party obligations. Counsel requirement retained. Exact closure criteria: counsel-signed compatibility note per licence group, filed in `docs/legal/`.
- **U3 addendum 2026-11-26:** previous NOT DOCUMENTED → recorded: NOT DOCUMENTED (unchanged; no scope list on file) + founder points 6–7 filed as DECLARED (unverified) intent only. Counsel requirement retained (scope determination + owner sign-off). Exact closure criteria: filed enumerated scope list + counsel confirmation.
- **U4 addendum 2026-11-26:** previous PARTIALLY DOCUMENTED → recorded: PARTIALLY DOCUMENTED (unchanged; pre-extraction authorship still unevidenced) + founder points 1–2 filed as DECLARED (unverified) authorship pointer. Owner + counsel requirements retained. Exact closure criteria: per-file authorship table sourced to records + filed contributor declarations.
- **U5 addendum 2026-11-26:** previous NOT DOCUMENTED → recorded: NOT DOCUMENTED (unchanged; official text still NOT fetched) + founder point 6 filed as DECLARED (unverified) intent only. Owner + counsel requirements retained. Exact closure criteria: verified fetched text on file + verification note (publication itself stays withheld per U12).
- **U6 addendum 2026-11-26:** previous PARTIALLY DOCUMENTED → recorded: PARTIALLY DOCUMENTED (unchanged). The declaration supplies no information on this item — declaration changes nothing about third-party obligations. Counsel requirement retained. Exact closure criteria: counsel clearance per group, same as U2.
- **U7 addendum 2026-11-26:** previous NOT DOCUMENTED → recorded: NOT DOCUMENTED (unchanged; no brand instrument on file) + founder points 1–5 filed as DECLARED (unverified). Counsel + brand-holder signatory requirements retained. Exact closure criteria: signed brand instrument + counsel note; any rename executed only after that.
- **U8 addendum 2026-11-26:** previous NOT DOCUMENTED → recorded: NOT DOCUMENTED (unchanged; no authorisation on file) + founder points 1–5 filed as DECLARED (unverified). Counsel + signatory requirements retained. Exact closure criteria: filed authorisation covering trademark/service-name use and rename authority + counsel note.
- **U9 addendum 2026-11-26:** previous NOT DOCUMENTED → recorded: NOT DOCUMENTED (unchanged; no relicensing instrument on file) + founder points 4–5 filed as DECLARED (unverified). Counsel + controlling-party signatory requirements retained. Exact closure criteria: signed relicensing/transfer instrument from the controlling party + counsel confirmation.
- **U10 addendum 2026-11-26:** previous NOT DOCUMENTED → recorded: NOT DOCUMENTED (unchanged; no instrument on file) + founder points 4–5 filed as DECLARED (unverified). Counsel + signatory requirements retained. Exact closure criteria: signed instrument of the same class as U9 + counsel note.
- **U11 addendum 2026-11-26:** previous PARTIALLY DOCUMENTED → recorded: PARTIALLY DOCUMENTED (unchanged). The declaration supplies no information on this item — declaration changes nothing about third-party obligations. Counsel requirement retained. Exact closure criteria: counsel-signed clearance records per row/group.
- **U12 addendum 2026-11-26:** previous PARTIALLY DOCUMENTED → recorded: PARTIALLY DOCUMENTED (unchanged; gate approvals still absent; package still WITHHELD). The declaration grants no clearance. Counsel + owner requirements retained. Exact closure criteria: every U1–U11 item closed with filed artefacts + written counsel publication approval; until then no `LICENSE`/`NOTICE` files, no headers, no notice changes.
