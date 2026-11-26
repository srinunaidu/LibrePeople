# Feature: licensing-provenance-baseline

## Behavior
Slice 1 (PREPARED-ONLY) of LibrePeople AGPL transition. Establishes provenance baseline without making any licence effective: (a) new `docs/legal/ownership-and-provenance-register.md` classifying each recon group as LibrePeople-created / Karmathy-transferred / third-party / copied-adapted / unclear; (b) PREPARED AGPL package staged as drafts only — `docs/legal/licensing-policy.md` (AGPL-3.0-or-later SPDX proposed), third-party-licences draft referencing existing `docs/licensing/`, plus `docs/legal/LICENSE.AGPL-3.0.prepared` or `LICENSE.prepared` with note that official text not yet fetched from gnu.org and no COPYING/NOTICE published as effective; (c) decision register + legal-clearance register + unresolved-blocker register with exact questions/evidence for legal reviewer; (d) governance note that repo visibility is report-only, left unchanged per human instruction.

## Acceptance criteria
1. `docs/legal/ownership-and-provenance-register.md` exists and classifies every recon item (README, 6 licensing docs, sbom/backend-transitive.json, requirements.txt, pyproject `karmathy-backend`, package.json/lock `karmathy-frontend`, offer_letter.py fpdf2 lazy, backends.py/database.py oci lazy, Dockerfiles, compose/render/deploy.yml, PublicLayout.tsx `© 2026 Karmathy`, Makefile/ci script) with one of the five labels; `unclear` where evidence missing.
2. `test -f` confirms PREPARED artefacts exist under `docs/legal/` and `test ! -e LICENSE && test ! -e COPYING` at repo root passes (no root licence claiming effectiveness).
3. `grep -ri "SPDX-License-Identifier" backend/app frontend/src --include="*.py" --include="*.tsx" --include="*.ts"` returns empty (no source header insertion in this slice).
4. Register contains zero invented owners/dates: every Karmathy→LibrePeople transfer row is marked UNRESOLVED and every date is sourced or marked unknown.
5. No third-party relicensing: draft policy states code stays AGPL-proposed, original docs CC BY 4.0 PROPOSED only, third-party terms unchanged; `grep -ri "relicen" docs/legal/` shows no relicensing claim.
6. No history rewrite: `git log --oneline -5` still shows existing history and no `filter-branch`/`filter-repo`/force-push performed.
7. No deletion: all recon files listed above still exist via file-existence checks.
8. Governance note in `docs/legal/` explicitly states repo visibility left unchanged (report-only, no change made).

## Non-goals
No root LICENSE/COPYING/NOTICE publication as effective; no source SPDX header insertion; no dependency addition/removal/upgrade; no repo visibility change; no trademark assignment or Karmathy-mark removal claim; no GNU/FSF endorsement claim; no licence-enforcement action.

## Interfaces / data
Docs-only. New files under `docs/legal/` (ownership register, licensing-policy draft, third-party draft, decision/legal-clearance/unresolved-blocker registers, governance note). No schema, migration, API, or config change. Backwards compatible by construction.

## Test plan
- `ls docs/legal/` and `test ! -e LICENSE; test ! -e COPYING` checks.
- Grep guards: SPDX-header absence; `grep -ri "Karmathy" docs/legal/ownership-and-provenance-register.md` must show Karmathy refs preserved, not scrubbed.
- Markdown lint if available (`npx markdownlint-cli docs/legal/*.md` or `mdl`), else `python3 -c` front-matter/heading sanity check.
- Read-only regression: `make -n test` / inspect `Makefile`, `ci/run_backend_tests.sh`; do not execute full suite in this slice, record that existing tests were not modified.

## Risk tier
1 (irreversible) — ownership/licence misstatement is legally irreversible; mitigated by PREPARED-ONLY, no publication, UNRESOLVED transfer flag.

## Rollback
Delete staged `docs/legal/` slice files only (`git checkout -- docs/legal/` or `git clean -f` scoped); no production data, no migration, no root files touched.

## Open decisions
- Karmathy→LibrePeople transfer evidence/authority unresolved — needs legal reviewer sign-off before any effective licensing.
- 19 direct / 114 transitive backend licences UNVERIFIED; fpdf2 LGPL-3.0-only, Oracle UPL (oci lazy), MPL-2.0 test-only, ISC lucide-react compatibility — needs legal clearance.
- CC BY 4.0 for original docs is PROPOSED only — confirm scope before Slice 2.
