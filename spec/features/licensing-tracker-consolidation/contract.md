# Feature: licensing-tracker-consolidation

## Behavior
Docs-only consolidation slice. Builder verifies actual git state via shell and creates `docs/legal/licensing-transition-tracker.md` consolidating slices 1–3 done, slice 4+ missing, uncommitted/stacked changes, conflicts, main drift, and publication blockers (U1–U6 / L1–L11), with a no-push-to-main-until-review gate.

## Acceptance criteria
1. `docs/legal/licensing-transition-tracker.md` exists with tables for slices/deliverables, blockers (U1–U6/L1–L11 with status), and commits/branches.
2. Tracker records verbatim (or fenced code blocks of) outputs of: `git branch -a`, `git status --porcelain` (full + scoped `docs/legal spec/features`), `git log --oneline -10` (current + main), `git rev-parse HEAD main origin/main`, `git merge-base HEAD main`, `git diff --stat main...HEAD`, `git worktree list`.
3. `git log --oneline -3` after the slice shows no new commits by this slice; `git status --porcelain` shows only the new tracker file as untracked/modified.
4. `test ! -e LICENSE && test ! -e COPYING && test ! -e NOTICE` passes at repo root (no root licence added).
5. `grep -ri "karmathy" docs/legal/licensing-transition-tracker.md` returns matches (Karmathy refs preserved, not scrubbed).
6. No production code changed: `git diff --stat main...HEAD -- backend/ frontend/ ci/ Makefile` shows nothing new from this slice, and no `*.py`/`*.tsx`/`*.ts` touched.
7. Tracker states explicit no-push-to-main-until-review gate and lists publication blockers as unresolved.

## Non-goals
No slice 4 docs (CONTRIBUTING/CODE_OF_CONDUCT/SECURITY/templates/commercial strategy); no inventory/SBOM changes; no scanner/CI changes (`ci/check_licences.py`, `licence-compliance.yml`); no merge/rebase/push/force-push; no history rewrite.

## Interfaces / data
Docs-only. One new file: `docs/legal/licensing-transition-tracker.md`. No schema, migration, API, or config change. Backwards compatible.

## Test plan
- `test -f docs/legal/licensing-transition-tracker.md && head -1 docs/legal/licensing-transition-tracker.md | grep -q "^# "`.
- `git branch -a; git status --porcelain; git log --oneline -10; git rev-parse HEAD; git worktree list` all exit 0; outputs pasted into tracker.
- `test ! -e LICENSE; test ! -e COPYING`; `grep -ri karmathy docs/legal/licensing-transition-tracker.md` non-empty.
- `git status --porcelain -- docs/legal spec/features` shows only tracker file changed.

## Risk tier
2 (normal)

## Rollback
Delete tracker file only: `rm docs/legal/licensing-transition-tracker.md`; no commits to revert, no other files touched.

## Open decisions
- Actual git state unverified (prior recon had no shell) — builder must verify branch/log/rev-parse via shell and record; lead to confirm `chore/licensing-transition` base vs main.
- Whether tracker should also cover commercial-strategy input once legal reviewer responds — needs human/lead sign-off before slice 4.
