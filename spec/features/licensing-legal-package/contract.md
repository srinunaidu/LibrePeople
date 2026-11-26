# Feature: licensing-legal-package

## Behavior
Phase 7 PREPARED-ONLY final legal review package on `chore/licensing-transition`: create `docs/legal/legal-review-package.md` with 10 sections and an explicit 5-way separation (engineering-complete vs evidence-complete vs legal-review vs owner-decisions vs publication blockers), giving the legal reviewer exact questions + evidence pointers and the owner exact decisions, with blockers U1–U12 / L1–L17. No approvals invented.

## Acceptance criteria
1. `docs/legal/legal-review-package.md` exists with all 10 sections: (1) ownership, (2) Karmathy extraction rights, (3) third-party obligations, (4) contributor rights, (5) holder identity, (6) AGPL suitability, (7) docs licensing, (8) trademark/brand, (9) commercial/dual strategy, (10) distribution/publication authorisation.
2. Package contains explicit 5-bucket separation with H1/H2 headings: engineering-complete, evidence-complete, legal-review, owner-decisions, publication blockers — `grep -c "^#\|^##" docs/legal/legal-review-package.md` shows all five buckets present.
3. Each legal-review item states an exact question + evidence pointer referencing: blocker registers (U1–U12, L1–L17), inventory/SBOM/triage (713 files, 575/2/3/133, SBOM `sbom-20261126T043959Z.json`), scanner `--strict`, governance docs, ownership 22 rows, and package-status (U12/L17 WITHHELD).
4. Owner-decisions section lists only open decisions requiring human/owner sign-off (holder identity, AGPL adoption, dual/commercial strategy, publication authorisation, trademark use); no decision marked approved/granted/cleared.
5. Publication blockers section enumerates U1–U12 / L1–L17 as UNRESOLVED/UNVERIFIED with per-file withholding (no root LICENSE/COPYING/NOTICE, no headers, no official AGPL text).
6. No effective licence published: `test ! -e LICENSE && test ! -e COPYING && test ! -e NOTICE` passes; `grep -ri "SPDX-License-Identifier" backend/app frontend/src` returns empty; no clearance/approval language invented in package (`grep -in "approved\|granted\|cleared\|authorised to publish" docs/legal/legal-review-package.md` returns empty or only in question form).
7. No production/dependency/CI change: `git diff --name-only -- backend frontend ci .github package.json lockfiles` is empty; docs-only diff under `docs/legal spec/features`.
8. No push or merge performed; branch remains `chore/licensing-transition` unpushed for this change.

## Non-goals
- No publication of any effective licence, header insertion, or NOTICE/COPYING creation.
- No clearance claim, ownership assertion, holder/date invention, or Karmathy/third-party notice removal/rewrite.
- No SBOM regeneration, dependency change, scanner or CI gate change, governance rewrite.
- No push, merge, release, or visibility change.

## Interfaces / data
- Create: `docs/legal/legal-review-package.md` (10 sections + 5 buckets + questions/evidence + owner decisions + blockers). Read-only inputs: `docs/legal/` registers (unresolved-blocker, legal-clearance), inventory/SBOM/triage outputs, scanner config, governance docs, ownership registers, `licensing-package-status.md`. New spec dir `spec/features/licensing-legal-package/`.
- Backwards compatible: docs-only, no runtime/API/schema/migration/config change.

## Test plan
- `ls docs/legal/legal-review-package.md spec/features/licensing-legal-package/contract.md`
- `grep -in "^# " docs/legal/legal-review-package.md` (10 sections); `grep -in "engineering-complete\|evidence-complete\|legal-review\|owner-decision\|publication blocker" docs/legal/legal-review-package.md` (5 buckets)
- `grep -in "U12\|L17\|sbom-20261126T043959Z\|575" docs/legal/legal-review-package.md` (evidence refs); `grep -in "UNRESOLVED\|UNVERIFIED\|WITHHELD" docs/legal/legal-review-package.md`
- `test ! -e LICENSE && test ! -e COPYING && test ! -e NOTICE`; `grep -ri "SPDX-License-Identifier" backend/app frontend/src` (expect empty)
- `git status --porcelain -- docs/legal spec/features`; `git diff --name-only -- backend frontend ci .github` (expect empty); confirm no push.
- New tests: none (docs-only); validator re-runs guards above.

## Risk tier
1 (irreversible) — rights-sensitive legal handoff doc though PREPARED-ONLY and docs-only.

## Rollback
`git checkout -- docs/legal/ && rm -f docs/legal/legal-review-package.md && rm -rf spec/features/licensing-legal-package`; no prod/data rollback needed.

## Open decisions
- Holder identity + copyright line wording — lead must ask human before any LICENSE/NOTICE text is drafted.
- AGPL-3.0-only suitability + dual/commercial licensing strategy — owner + legal reviewer decision, not engineering.
- Distribution/publication authorisation (when/if withheld files may be created) — explicit owner + legal sign-off required; currently blocked by U1–U12/L1–L17.
