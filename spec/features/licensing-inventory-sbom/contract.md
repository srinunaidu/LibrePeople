# Feature: licensing-inventory-sbom

## Behavior
Slice 2 (PREPARED-ONLY, report-only) of LibrePeople AGPL transition. Produces: (a) machine-readable `docs/legal/dependency-licence-inventory.json` plus human-readable `.md` view covering backend 19 direct + 114 transitive freeze rows and frontend 24 deps + 19 devDeps + transitive lock entries — each row carries package, version, direct/transitive, licence, source, redistribution obligations, attribution, compatibility assessment, required action; (b) updated timestamped SBOM extending existing SBOM format (CycloneDX or current JSON shape), marking UNVERIFIED/UNKNOWN explicitly, never compliant; (c) appended U/L register entries recording new findings (fpdf2 LGPL, Oracle UPL, MPL-2.0 test-only, ISC). Prospective holder LibrePeople project only (no rights claim); AGPL-3.0-or-later + CC BY 4.0 docs-only remain PROPOSED. No root LICENSE publication.

## Acceptance criteria
1. `test -f docs/legal/dependency-licence-inventory.json && test -f docs/legal/dependency-licence-inventory.md` passes.
2. `python3 -c "import json;json.load(open('docs/legal/dependency-licence-inventory.json'))"` exits 0 (schema-valid JSON; every row has the 9 required fields).
3. Every backend direct dep in `backend/requirements.txt` (19) has a matching inventory row verified via `jq` count comparison.
4. Every frontend dep/devDep in `frontend/package.json` (24 + 19) has a matching inventory row verified via `jq` count comparison.
5. Timestamped SBOM exists under `docs/legal/` (or updated `docs/licensing/sbom/` extension) and every UNVERIFIED/UNKNOWN entry is explicit; `jq` shows zero rows with licence "compliant" or invented certainty.
6. U/L registers appended (not rewritten) with fpdf2 LGPL, Oracle UPL, MPL-2.0 test-only, ISC findings, each marked UNVERIFIED clearance-required.
7. `test ! -e LICENSE && test ! -e COPYING` at root passes; `grep -ri "SPDX-License-Identifier" backend/app frontend/src` returns empty (no header insertion).
8. `git status --porcelain` shows changes only under `docs/legal/` (and SBOM path if extended); `backend/requirements.txt`, `frontend/package.json`, `frontend/package-lock.json` unmodified.
9. `git log --oneline -3` shows no history rewrite (no filter-branch/filter-repo/force-push).

## Non-goals
No pip-licenses/npm registry fetch claiming legal certainty (unfetched sources recorded as UNVERIFIED); no dependency removal/addition/upgrade; no CI workflow changes (slice 3); no contribution-docs changes; no repo visibility change; no trademark reassignment or GNU/FSF endorsement claim; no effective licensing.

## Interfaces / data
Docs/data-only. New: `docs/legal/dependency-licence-inventory.json` (array of row objects with the 9 fields), `docs/legal/dependency-licence-inventory.md` (rendered view), timestamped SBOM file; append-only edits to `unresolved-blocker-register.md` + `legal-clearance-register.md`. No API, migration, schema, or config change. Backwards compatible.

## Test plan
- `python3 -c "import json; d=json.load(open('docs/legal/dependency-licence-inventory.json')); assert all(set(r)=={'package','version','scope','licence','source','redistribution_obligations','attribution','compatibility','required_action'} for r in d)"`.
- `jq 'length' docs/legal/dependency-licence-inventory.json`; `jq '[.[]|select(.scope=="direct")]|length'` vs 19+43 frontend-direct rows; grep guards: `test ! -e LICENSE`; `grep -ri "SPDX-License-Identifier" backend/app frontend/src` empty.
- `git diff --stat` scoped to docs/legal (+ SBOM); `make -n test` inspection only, no suite execution; markdownlint if available.

## Risk tier
1 (irreversible) — licence inventory misstatement creates legal exposure; mitigated by PREPARED-ONLY, UNVERIFIED-never-compliant rule, no publication, docs-only.

## Rollback
Delete staged inventory files only (`git checkout -- docs/legal/ docs/licensing/sbom/` or scoped `git clean -f docs/legal/dependency-licence-inventory.* docs/legal/sbom*`); no production code, migration, or root files touched.

## Open decisions
- Legal reviewer must clear fpdf2 LGPL boundary, Oracle UPL deploy-path scope, MPL-2.0 test-only confinement, ISC lucide-react compatibility before any effective grant.
- Confirm SBOM format choice (extend current JSON vs CycloneDX) and timestamp source before build.
- Confirm CC BY 4.0 "original docs" scope still deferred from slice 1.
