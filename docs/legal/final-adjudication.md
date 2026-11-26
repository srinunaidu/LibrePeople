# Final Adjudication — DRAFT RECOMMENDATIONS ONLY

> DRAFT — NOT EXECUTED — NO LEGAL EFFECT. Nothing here is legal advice,
> no legal conclusion is stated as final, and no determination below
> constitutes approval. Every finding is a draft recommendation only and
> requires owner/counsel action. Branch `agent/legal/final-adjudication`
> from main HEAD `f817cd7b299611b176d44dc1244fc0db6a895e3` (verified
> before branching). New files only; no LICENSE/NOTICE/COPYING created.

## Consolidated evidence base (read as inputs)

- U1–U12 register: `docs/legal/unresolved-blocker-register.md` (all 12
  recorded UNRESOLVED). Ownership register:
  `docs/legal/ownership-and-provenance-register.md` (22 rows, transfer and
  authorship rows UNRESOLVED). Ownership evidence:
  `docs/legal/final-ownership-decision-register.md` (from main
  `d80c0cd7f350be4be08b768d9a05573ef41a628f`; ESTABLISHED-BY-EVIDENCE:
  none). Licensing evidence:
  `docs/legal/final-licensing-decision-register.md` (21 backend pins
  evidenced; mechanical mapping only, counsel must confirm). Decision
  package: `docs/legal/legal-review-package.md` (§1–§10, O1–O5 OPEN) +
  `docs/legal/decision-register.md` (D1–D10). Compliance docs:
  `docs/legal/compliance-ci.md` (report-only; triage notes L2/L8, L3/L9,
  L10, L11) + `docs/legal/commercial-open-source-strategy.md` (draft,
  owner TBD). Clearance register: `docs/legal/legal-clearance-register.md`
  (L1–L17, all UNVERIFIED/PROPOSED/DRAFT). Inventory:
  `docs/legal/dependency-licence-inventory.json` (715 rows: 64 direct /
  651 transitive; 642 unique package@version). SBOMs:
  `docs/legal/sbom-20261126T012556Z.json` (713 components, historical) +
  `docs/legal/sbom-20261126T043959Z.json` (715 components, fresh).
  Checker `ci/check_licences.py --check-only`: Confirmed 672 / Review 34 /
  Blocked 9 / Unknown 0 (Blocked 9 = fpdf2×2, axe-core×3, certifi, crc32c,
  orjson, psycopg2-binary; mechanical, counsel-gated). Chain of title:
  `docs/legal/chain-of-title-appendix.md`. Withholding facts: no root
  LICENSE/COPYING/NOTICE; official AGPL text NOT fetched
  (`docs/legal/LICENSE.AGPL-3.0.prepared`); no SPDX headers under
  `backend/app` / `frontend/src`.

### 1. Ownership

- Question: Is authorship/provenance sufficient to support a future grant?
- Evidence: 22-row register (above); U4; `chain-of-title-appendix.md`
  (e.g. `backend/app/api/v1/endpoints/payroll.py`, 1 revision;
  `frontend/src/pages/payroll/PayRunDetail.tsx`, 2 revisions);
  zero `Signed-off-by` in 198 commits; pre-extraction history absent.
- Analysis summary: In-repo window (2026-11-25–26) is recorded; transfer
  instruments, employer/contractor agreements, and declarations are absent;
  Karmathy marks preserved verbatim. Requires counsel/owner to judge
  sufficiency — not judged here.
- Finding: RECOMMENDED: PARTIALLY DOCUMENTED (in-repo window only;
  pre-extraction and instruments missing). Confidence: Medium.
- Missing evidence: Signed assignment/transfer instruments; contributor
  declarations (templates in `docs/legal/instruments/` are unexecuted
  blanks); pre-extraction authorship records; DCO sign-offs.
- Required approval + party: Requires counsel (sufficiency) + owner-side
  signatory (UNKNOWN — requires owner to identify; no names invented).
- Next action: Owner identifies rights holder(s); counsel confirms
  instrument sufficiency; file executed instruments.

### 2. Distribution rights

- Question: May any part of the tree be distributed under a licence grant?
- Evidence: U12/L17 WITHHELD package status
  (`docs/legal/licensing-package-status.md`); U1, U7–U10 (no transfer
  instruments); no root LICENSE/COPYING/NOTICE; no headers.
- Analysis summary: No effective grant exists anywhere in-repo; every
  publishable-effect file class is recorded withheld. Whether any subset
  could be distributed is for counsel/owner — not determined here.
- Finding: RECOMMENDED: WITHHELD — NOT CLEARED FOR DISTRIBUTION.
  Confidence: High (withheld state observed).
- Missing evidence: All U1–U11 closure artefacts + written counsel
  publication approval.
- Required approval + party: Requires counsel (publication gate) + owner
  sign-off (O4 OPEN).
- Next action: Keep all grants withheld; re-check header absence at
  closure; obtain written counsel publication approval.

### 3. Third-party compatibility

- Question: Are third-party terms compatible with the proposed posture?
- Evidence: 715-row inventory + both SBOMs (counts above); checker 672 /
  34 / 9 / 0; compliance-ci triage notes (MPL-2.0 3 rows; LGPL fpdf2 +
  psycopg2-binary + crc32c; Oracle UPL dual oracledb/oci; ISC
  lucide-react; Python-2.0 argparse; CC-BY-4.0 caniuse-lite); L1–L5,
  L8–L11, L15–L16 (all UNVERIFIED).
- Analysis summary: Technical inventory is now complete (0 Unknown rows),
  but compatibility was recorded as mechanical mapping only; counsel
  clearance per group is absent. Triage is evidence-gathering only.
- Finding: RECOMMENDED: PARTIALLY DOCUMENTED (inventory complete;
  compatibility undetermined). Confidence: Medium.
- Missing evidence: Counsel-signed compatibility note per licence group.
- Required approval + party: Requires counsel (per-group clearance:
  LGPL boundary, Oracle dual scope/terms, MPL confinement, CC-BY-4.0 /
  Python-2.0 / ISC posture).
- Next action: Counsel issues per-group clearance notes filed in
  `docs/legal/`; owner pins/locks boto3 (unbounded pin noted).

### 4. AGPL suitability

- Question: Is AGPL-3.0-or-later a suitable posture for this tree?
- Evidence: U2, U5, U6, U11, U12; L1–L5, L8–L11, L15–L17;
  `LICENSE.AGPL-3.0.prepared` (text NOT fetched); AGPL §13/§5/§6/§10/§11
  triggers described factually in Track 2 Q6 (no business-model content).
- Analysis summary: AGPL remains PROPOSED only; suitability depends on
  unresolved transfer gaps, unverified third-party groups, and unfetched
  text — all for counsel/owner, not determined here.
- Finding: RECOMMENDED: NOT DOCUMENTED (no suitability determination on
  file). Confidence: High for absence; no view offered on suitability.
- Missing evidence: Fetched + verified official text; U1–U11 closures;
  counsel suitability note.
- Required approval + party: Requires counsel + owner (O2 OPEN;
  business-model decision requires counsel + owner).
- Next action: Fetch/verify text (owner-side) + counsel suitability note
  before any publication step (publication itself stays withheld).

### 5. Docs licensing

- Question: What scope of docs could a proposed CC BY 4.0 grant cover?
- Evidence: U3 (no scope statement beyond "original docs only"); L6
  (PROPOSED); candidate scope `README.md`, `docs/licensing/`,
  `docs/legal/` package.
- Analysis summary: No enumerated scope list exists; the grant is
  proposal-only and its sufficiency is for counsel/owner.
- Finding: RECOMMENDED: NOT DOCUMENTED (scope undefined). Confidence: High.
- Missing evidence: Enumerated scope list + counsel confirmation.
- Required approval + party: Requires counsel (scope determination) +
  owner sign-off.
- Next action: Owner proposes enumerated scope list; counsel confirms;
  file both before any docs grant.

### 6. Commercial strategy

- Question: Is a dual/commercial strategy viable, and on what terms?
- Evidence: `commercial-open-source-strategy.md` (draft; dual-licence
  decision-maker TBD, no terms exist); U2, U6, U11, U12; L1–L5, L8–L11,
  L15–L17; Track 2 Q6 (business-model decision requires counsel + owner).
- Analysis summary: Strategy is draft posture only; viability and terms
  depend on ownership settlement + third-party clearance, for
  counsel/owner — not determined here.
- Finding: RECOMMENDED: NOT DOCUMENTED (no commercial terms on file).
  Confidence: High for absence; no viability view offered.
- Missing evidence: Settled ownership; per-group clearances; owner +
  counsel commercial decision with written terms.
- Required approval + party: Requires counsel + owner (O3 OPEN).
- Next action: Owner + counsel decide dual/commercial lane; record terms
  in writing; designate commercial owner.

### 7. Statutory readiness

- Question: Is any statutory-compliance position evidenced for release?
- Evidence: No statutory clearance record found in the `docs/legal/`
  package; only code-level pointers exist (e.g. rule packs
  `backend/rule_packs/in-standard.json:609` bearing `signed_by: Karmathy
  Compliance`, Karmathy-titled schemas — U9; commercial strategy notes
  payroll/statutory rule-pack verification as future implementation work).
- Analysis summary: The legal package contains no statutory determination;
  rule-pack signatures are Karmathy records, not grants; readiness is for
  owner/counsel with domain evidence — not determined here.
- Finding: RECOMMENDED: NOT DOCUMENTED (no statutory clearance on file).
  Confidence: High for absence of legal-package evidence.
- Missing evidence: Statutory-rule attestation; transfer/relicensing
  instrument for Karmathy-signed packs; counsel determination.
- Required approval + party: Requires counsel + owner-designated
  responsible party (UNKNOWN — requires owner to designate).
- Next action: Owner designates attesting party; counsel advises on
  required statutory evidence; file written attestation.

### 8. Payroll readiness

- Question: Is payroll-module readiness evidenced for release?
- Evidence: Code pointers only (`backend/app/api/v1/endpoints/payroll.py`
  in chain-of-title appendix; `frontend/src/pages/payroll/`); no
  payroll-readiness clearance in any `docs/legal/` register (U/L series
  contain no payroll item); commercial strategy lists payroll
  rule-pack verification as future work.
- Analysis summary: No readiness determination exists in the evidence
  base; whether payroll is releasable is for owner/counsel with functional
  + legal evidence — not determined here.
- Finding: RECOMMENDED: NOT DOCUMENTED (no payroll clearance on file).
  Confidence: High for absence of legal-package evidence.
- Missing evidence: Payroll correctness/verification evidence; provenance
  attestation; counsel/owner readiness sign-off.
- Required approval + party: Requires owner (readiness sign-off) +
  counsel (licensing-transfer implications via U9).
- Next action: Owner commissions payroll verification; files attestation;
  counsel confirms U9 instrument coverage.

### 9. Filing readiness

- Question: Is filing-output readiness (generated records/hashes)
  evidenced for release?
- Evidence: Track 2 Q3 notes `filing_record.py` "generated bytes" are
  hashes of outputs (prose only, no codegen); no filing-readiness
  clearance in any register; seed provenance unattested (seed files
  `seed/dev/seed_dev.py`, `seed/prod/seed_prod.py` — owner attestation
  pending per ownership register row 17/Track 1).
- Analysis summary: No readiness determination exists; filing readiness
  is for owner/counsel — not determined here.
- Finding: RECOMMENDED: NOT DOCUMENTED (no filing clearance on file).
  Confidence: Medium (pointer-based; substance not re-audited).
- Missing evidence: Filing-output verification; seed provenance
  attestation incl. no-production/personal-data confirmation; counsel note
  if seed ships.
- Required approval + party: Requires owner (attestation by designated
  party, UNKNOWN) + counsel if seed/filings ship.
- Next action: Owner designates attesting party; files seed/filing
  attestation; counsel advises on ship implications.

### 10. Release approval

- Question: May any release, merge to main, push, or visibility change
  proceed on the basis of this adjudication?
- Evidence: U12/L17 gate (every U1–U11 open; every L-row UNVERIFIED/
  PROPOSED/DRAFT); O1–O5 all OPEN; compliance-ci human push gate (no
  push/merge/release/enforcement without explicit human approval);
  withholding facts (above).
- Analysis summary: Gate criteria are unmet on every item; this file
  grants nothing and lifts no gate. The release decision belongs solely
  to the owner with counsel — not made here.
- Finding: RECOMMENDED: RELEASE NOT APPROVED (all gates remain closed).
  Confidence: High.
- Missing evidence: All U1–U11 closure artefacts; all L-row counsel
  clearances; O1–O5 explicit sign-offs; written counsel publication
  approval.
- Required approval + party: Requires owner + counsel (explicit, written).
- Next action: No release, push, merge, or visibility change; close items
  in register order; return for re-adjudication when artefacts are filed.

---

## Explicit non-approval statement

No verdict, finding, or recommendation in this file constitutes approval
of any kind — not of ownership, licensing posture, third-party
compatibility, AGPL suitability, docs or commercial terms, statutory /
payroll / filing readiness, or release. The release decision belongs
exclusively to the owner acting with counsel; this adjudication only
recommends, and every item above requires owner/counsel action before
anything is published, distributed, or released.
