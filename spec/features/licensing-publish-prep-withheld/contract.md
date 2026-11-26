# Feature: licensing-publish-prep-withheld

## Behavior
Phase 4 PREPARED-ONLY publish preparation in an isolated reviewable branch `chore/licensing-publish-prep` cut from `chore/licensing-transition @ d13a3a7` (base; main `f3ee5cf` untouched): draft `docs/legal/publication-package-withheld.md` stating per-file what is prepared vs withheld, with blockers U1–U12 / L1–L17, isolation of uncleared components, and no invented holder/year/contact. Official AGPL text stays NOT fetched (placeholder only, no vendoring). No LICENSE/COPYING/NOTICE/headers land on main or prep-branch root. No merge to main, no push without approval, no publication.

## Acceptance criteria
1. `docs/legal/publication-package-withheld.md` exists on the prep branch with a per-file prepared-vs-withheld table (LICENSE/COPYING/NOTICE, official AGPL text, source headers, NOTICE/third-party files, docs CC BY, policy/strategy refs, SECURITY/CoC contacts).
2. Withheld file cites blockers U1–U12 UNRESOLVED and L1–L17 UNVERIFIED/BLOCKED and states scanner state (575/2/3/133), SBOM fresh, no LICENSE — publication not cleared.
3. Branch `chore/licensing-publish-prep` exists locally, based on `d13a3a7`, and is unpushed: `git branch --list chore/licensing-publish-prep` non-empty and `git status -sb` shows no ahead-of-remote / `git log origin/chore/licensing-publish-prep..HEAD` fails or empty.
4. No invented holder/year/contacts: `grep -riE "Copyright.*(202[0-9]|Karmathy|[A-Za-z]+ Inc|contact@|security@)" docs/legal/publication-package-withheld.md` returns only TBD markers (e.g. `TBD`, `DO NOT INVENT`), no asserted holder/year/contact.
5. No LICENSE/COPYING/NOTICE added: `test ! -e LICENSE && test ! -e COPYING && test ! -e NOTICE` passes on prep-branch root (and main root verified clean).
6. No source headers added: `grep -ri "SPDX-License-Identifier" backend/app frontend/src` returns empty on the prep branch.
7. No production change: `git diff d13a3a7..HEAD --name-only -- backend frontend packages ci .github` is empty; only `docs/legal/publication-package-withheld.md` plus `spec/features/licensing-publish-prep-withheld/contract.md` added.
8. No push or visibility change and no merge to main: `git log --oneline main..HEAD` contains only the prep commit(s) and `git branch --merged main` does not list the prep branch.

## Non-goals
- No publication or effective licensing (no root LICENSE/COPYING/NOTICE, no header insertion, no NOTICE/third-party finalization).
- No fetching `gnu.org` AGPL text and claiming it official; no vendoring/modifying official text.
- No ownership clearance: U1–U12 / L1–L17 stay UNRESOLVED/UNVERIFIED/BLOCKED; no invented holder/year/contacts.
- No merge to main, no push without explicit approval, no release/visibility change, no CI/prod/dependency change.

## Interfaces / data
- Isolated branch only: `chore/licensing-publish-prep` from `d13a3a7`; main `f3ee5cf` read-only reference, never a merge target.
- Create (prep branch): `docs/legal/publication-package-withheld.md` (per-file prepared vs withheld, blockers, isolation, TBD-only contacts). New spec dir `spec/features/licensing-publish-prep-withheld/`.
- Verify read-only: root `LICENSE/COPYING/NOTICE` absent; `docs/legal/LICENSE.AGPL-3.0.prepared` placeholder still states NOT fetched; SECURITY/CoC contacts remain TBD.
- Backwards compatible: docs-only; no runtime, API, schema, migration, or config change.

## Test plan
- `git branch --list 'chore/licensing-publish-prep'; git log --oneline -3; git status -sb`
- `ls docs/legal/publication-package-withheld.md spec/features/licensing-publish-prep-withheld/contract.md`
- `test ! -e LICENSE && test ! -e COPYING && test ! -e NOTICE`
- `grep -ri "SPDX-License-Identifier" backend/app frontend/src` (expect empty); `grep -in "WITHHELD\|WITHHELD" docs/legal/publication-package-withheld.md`
- `grep -in "U1\|U12" docs/legal/publication-package-withheld.md; grep -in "L1\|L17" docs/legal/publication-package-withheld.md`
- `git diff d13a3a7..HEAD --name-only`; `git log --oneline main..HEAD`; `git branch --merged main`
- New tests: none (docs-only); validator re-runs the guards above on the prep branch and confirms main root clean.

## Risk tier
1 (irreversible) — rights-sensitive publication packaging even though PREPARED-ONLY, branch-isolated, docs-only.

## Rollback
`git checkout chore/licensing-transition && git branch -D chore/licensing-publish-prep && rm -rf spec/features/licensing-publish-prep-withheld`; no prod/data rollback needed; confirm `git branch --list` empty and main `f3ee5cf` untouched.

## Open decisions
- None for lead to ask human before building beyond standing TBDs: holder/year/contacts stay TBD (do not invent); push/merge/publication each require separate explicit human approval.
