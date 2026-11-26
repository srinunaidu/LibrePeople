# Feature: licensing-ownership-final

## Behavior
Complete the PREPARED-ONLY ownership/provenance register (Phase 3). Read-only audit of every file group via grep/glob (no history rewrite); extend `docs/legal/ownership-and-provenance-register.md` so each group carries origin / holder / licence / history / evidence / relicensable / approval; append Karmathy-derived gaps to U/L registers; add `docs/legal/provenance-evidence.md` listing evidence paths. No scrub, no grant, no enforcement.

## Acceptance criteria
1. Register covers all 10 groups: LibrePeople-created, Karmathy-transferred, third-party, copied-adapted, unclear, generated, vendored, fonts/icons/assets, historical notices, contributor authorship.
2. Every Karmathy-derived row (PublicLayout `© 2026 Karmathy`, DashboardFallback, ProductMockup, Thread, `karmathy:*` events, `karmathy-backend/frontend` names, backend core/main, contracts/rules, render/docker/makefile/scripts) is classified `Karmathy-transferred — UNRESOLVED`.
3. Each register row has all 7 fields: origin, holder, licence, history, evidence, relicensable (yes/no/UNRESOLVED), approval.
4. U-register appended with Karmathy-derived relicensing gaps; every such gap is UNRESOLVED.
5. L-register appended for Karmathy-derived licence questions; none marked cleared/compliant.
6. `docs/legal/provenance-evidence.md` exists and lists the evidence path for every register row.
7. No attribution, copyright notice, or Karmathy string removed, renamed, or scrubbed (grep for `Karmathy` count does not decrease).
8. No root `LICENSE` / `COPYING` / `NOTICE` added; no source header inserted.
9. No production code, dependency, or CI change attributable to this slice: tracked `git diff --name-only -- backend frontend ci .github Makefile render.yaml docker-compose.yml requirements package.json` is empty; `git status --porcelain` scoped to `docs/legal` + `spec` shows only this slice's 4 files plus documented stacked sibling-slice paths and harness `spec/features` inputs (excluded).

## Non-goals
- No LICENSE/COPYING/NOTICE publication or effective grant; no header insertion.
- No dependency, SBOM, or CI workflow changes; no push/merge/release.
- No history rewrite, rename, scrub, or trademark claim; no legal advice.

## Interfaces / data
Docs-only. Touches: `docs/legal/ownership-and-provenance-register.md` (extend), `docs/legal/unresolved-blocker-register.md` + `docs/legal/legal-clearance-register.md` (append-only, next U/L numbers), new `docs/legal/provenance-evidence.md`. New spec dir `spec/features/licensing-ownership-final/`. Backwards compatible: report-only, no code paths.

## Test plan
- `ls docs/legal/ownership-and-provenance-register.md docs/legal/provenance-evidence.md spec/features/licensing-ownership-final/contract.md`
- `grep -c Karmathy docs/legal/ownership-and-provenance-register.md` (non-zero, not decreased vs base); `grep -in "UNRESOLVED" docs/legal/unresolved-blocker-register.md`
- `head -1 docs/legal/ownership-and-provenance-register.md docs/legal/provenance-evidence.md` (H1 titles present)
- `test ! -e LICENSE && test ! -e COPYING && test ! -e NOTICE`
- `git status --porcelain -- docs/legal spec/features` + `git diff --name-only -- backend frontend ci .github Makefile render.yaml docker-compose.yml` (empty)
- New checks: register has all 10 group labels; every row has 7 fields; U/L appends numbered sequentially.

## Risk tier
1 (irreversible) — PREPARED-ONLY docs; Tier 1 because ownership assertions are rights-sensitive even though docs-only.

## Rollback
`git checkout -- docs/legal/ && rm -f docs/legal/provenance-evidence.md && rm -rf spec/features/licensing-ownership-final`; no prod state to restore.

## Open decisions
- None — mandate fixes UNRESOLVED-without-legal; confirm lead wants contributor-authorship rows sourced from `git log` or left `unknown`?
