# Feature: licensing-compliance-ci

## Behavior
Add report-only licensing compliance CI on `chore/licensing-transition` (PREPARED-ONLY).
New check (`ci/check_licences.py` + caller `.github/workflows/licence-compliance.yml`)
inventories direct deps, lists transitive, flags missing/restricted licence metadata,
checks NOTICE presence, validates SBOM freshness, detects proprietary files via
gitignore-aware allowlist, and emits per-dependency `Confirmed / Review required /
Blocked / Unknown` plus a markdown+json report artifact per RC. Add
`docs/legal/compliance-ci.md` describing statuses and triage.
> Human gate: NO push to main, NO merge to main, NO release without explicit human
> approval. All work stays on `chore/licensing-transition`, unpushed unless approved.

## Acceptance criteria
1. `.github/workflows/licence-compliance.yml` exists and parses via `python -c "yaml.safe_load(...)"`.
2. `ci/check_licences.py` exists; `python -m py_compile` passes and `--check-only` exits 0 on current repo.
3. Script outputs all 4 statuses and never marks `UNVERIFIED`/missing metadata as `Confirmed`.
4. Restricted set (GPL/AGPL/LGPL/MPL/commercial/unknown) flagged `Blocked` or `Review required` per policy.
5. SBOM freshness check validates `docs/legal/sbom-*.json` against inventory (stale => `Review required`, not silent pass).
6. Proprietary-file detection (e.g. `wallet/*.key` via allowlist) reports findings report-only.
7. No root `LICENSE` file added; `git status --porcelain` shows changes only under `.github/` + `ci/` + `docs/legal/`, excluding harness task input under `spec/features/` and uncommitted sibling-slice paths on the same branch.
8. Existing CI unbroken: `.github/workflows/ci.yml` still YAML-valid; no jobs removed/renamed.
9. `git branch --show-current` is `chore/licensing-transition`; `main` ref untouched (no push/merge).

## Non-goals
- No enforcement blocking merges yet (report-only; `continue-on-error` or non-blocking).
- No dependency additions/removals/upgrades; no licence header insertion (slices 1-2 have no headers).
- No visibility change, publication, push/merge to main, or release.

## Interfaces / data
- New: `ci/check_licences.py [--check-only]`, `.github/workflows/licence-compliance.yml`, `docs/legal/compliance-ci.md`.
- Reads: `backend/requirements.txt`, `frontend/package.json`, `docs/legal/dependency-licence-inventory.{json,md}`, `docs/legal/sbom-*.json`, NOTICE files, `.gitignore` allowlist.
- Writes: stdout status table + `licensing-compliance-report.{md,json}` CI artifacts only. No migrations, no config changes, backwards compatible.

## Test plan
- `python -m py_compile ci/check_licences.py`
- `python -c "import yaml; yaml.safe_load(open('.github/workflows/licence-compliance.yml'))"` (and same for `ci.yml`)
- `python ci/check_licences.py --check-only` dry-run; assert exit 0 and 4 statuses present
- `git diff --stat` scoped to `.github/ + ci/ + docs/legal/`; `git status --porcelain` shows no root LICENSE
- `make -n test` inspection only. No full suite execution required.

## Risk tier
2 (normal; new CI + docs only, report-only, reversible)

## Rollback
Delete `.github/workflows/licence-compliance.yml`, `ci/check_licences.py`, `docs/legal/compliance-ci.md` and generated report artifacts; no other files touched.

## Open decisions
- None for build; pending human approval only for any future push/merge to main or enforcement (blocking) mode.
