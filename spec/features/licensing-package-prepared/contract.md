# Feature: licensing-package-prepared

## Behavior
Phase 5 PREPARED-ONLY packaging of the licensing transition on `chore/licensing-transition`: verify no effective licence has been published (official AGPL text NOT fetched from gnu.org, `LICENSE.AGPL-3.0.prepared` placeholder accurate), create `docs/legal/licensing-package-status.md` stating what is prepared vs withheld with per-file publication blockers and isolation of uncleared Karmathy-derived + third-party components, and append U12/L17 recording what prevents publication. No publication, no enforcement, no code change.

## Acceptance criteria
1. `docs/legal/licensing-package-status.md` exists with prepared-vs-withheld table plus per-file publication blockers referencing U1–U12 / L12–L17.
2. Status file lists as WITHHELD: root `LICENSE`, `COPYING`, `NOTICE`, official AGPL-3.0 text, all source headers, and any third-party notice change.
3. Status file isolates uncleared Karmathy-derived components (PublicLayout `© 2026 Karmathy`, DashboardFallback, ProductMockup, Thread, `karmathy:*` events, `karmathy-backend/frontend` names, backend core/main, contracts/rules, render/docker/makefile/scripts) as UNRESOLVED non-publishable, and states third-party terms are unchanged.
4. `test ! -e LICENSE && test ! -e COPYING && test ! -e NOTICE` passes at repo root.
5. No source header inserted: `grep -ri "SPDX-License-Identifier" backend/app frontend/src` returns empty.
6. No official text vendored without verification: `docs/legal/LICENSE.AGPL-3.0.prepared` still states text NOT fetched, and no file under `docs/legal/` contains the full AGPL grant text (no `fetch`/vendor claiming official).
7. No production/dependency/CI change: `git diff --name-only -- backend frontend ci .github package.json lockfiles requirements* pyproject.toml Dockerfile* render.yaml docker-compose.yml Makefile` is empty.
8. U12 appended to `unresolved-blocker-register.md` and L17 appended to `legal-clearance-register.md`, numbered sequentially, both UNRESOLVED/UNVERIFIED; no `git push` or merge performed.

## Non-goals
- No publication of any effective licence (no root LICENSE/COPYING/NOTICE, no header insertion).
- No fetching `gnu.org` text and claiming it official, and no vendoring/modifying official text.
- No removal, scrub, rename, or relicensing of Karmathy-derived or third-party notices; no invented holders/dates.
- No enforcement change, CI gate hardening, dependency add/remove/upgrade, or SBOM regeneration beyond status references.
- No push, merge, release, or visibility change.

## Interfaces / data
- Docs-only. Verify (read-only): `docs/legal/LICENSE.AGPL-3.0.prepared` (placeholder accuracy, no fetch). Create: `docs/legal/licensing-package-status.md`. Append-only: `docs/legal/unresolved-blocker-register.md` (U12), `docs/legal/legal-clearance-register.md` (L17). New spec dir `spec/features/licensing-package-prepared/`.
- Inputs: triage state (575/2/3/133, SBOM `sbom-20261126T043959Z.json`), ownership registers (U1–U10, L12–L14 UNRESOLVED), policy + commercial strategy drafts (already on file, not rewritten).
- Backwards compatible: no runtime, API, schema, migration, or config change.

## Test plan
- `ls docs/legal/licensing-package-status.md docs/legal/LICENSE.AGPL-3.0.prepared spec/features/licensing-package-prepared/contract.md`
- `test ! -e LICENSE && test ! -e COPYING && test ! -e NOTICE`
- `grep -ri "SPDX-License-Identifier" backend/app frontend/src` (expect empty); `grep -c "NOT yet been fetched" docs/legal/LICENSE.AGPL-3.0.prepared` (non-zero)
- `grep -in "WITHHELD" docs/legal/licensing-package-status.md`; `grep -in "UNRESOLVED" docs/legal/unresolved-blocker-register.md | tail`; `grep -in "L17" docs/legal/legal-clearance-register.md`
- `git status --porcelain -- docs/legal spec/features` and `git diff --name-only -- backend frontend ci .github` (scoped/empty as above); confirm no push (`git log origin --` or remote check untouched).
- New tests: none (docs-only); validator re-runs the guards above.

## Risk tier
1 (irreversible) — rights-sensitive packaging doc even though PREPARED-ONLY and docs-only.

## Rollback
`git checkout -- docs/legal/ && rm -f docs/legal/licensing-package-status.md && rm -rf spec/features/licensing-package-prepared`; no prod/data rollback needed.

## Open decisions
- None for lead to ask human before building: ownership (U1–U10, L12–L14) stays UNRESOLVED by mandate; publication blockers are recorded as U12/L17 for the legal reviewer.
