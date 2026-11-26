# Feature: licensing-compliance-hardening

## Behavior
Harden report-only licensing compliance (`ci/check_licences.py` + `licence-compliance.yml` + `docs/legal/compliance-ci.md`) for deterministic, secret-free reporting with a documented future enforcement path. Default stays report-only (exit 0); new `--strict` flag returns non-zero on Blocked/Unknown for future use only. The Confirmed/Review/Blocked/Unknown distinction is preserved; uncertainty never maps to PASS.

## Acceptance criteria
1. `python ci/check_licences.py --help` documents `--check-only` (exit 0) and `--strict` (non-zero on Blocked/Unknown) exit codes.
2. `python ci/check_licences.py --check-only` exits 0 on current inventory (3 Blocked / 133 Unknown) and writes no report files.
3. `python ci/check_licences.py --strict` (or `--strict --check-only`) exits non-zero on current inventory due to Blocked/Unknown; exits 0 only when zero Blocked/Unknown rows and no Blocked/Unknown findings.
4. All four statuses (Confirmed/Review/Blocked/Unknown) remain reachable; UNVERIFIED/missing licence never verdicts Confirmed (spot-check `verdict()`).
5. Output is deterministic: repeated runs byte-identical (sorted rows/findings, stable key order); SBOM freshness check compares inventory package@version set vs `docs/legal/sbom-*.json` components.
6. `grep -riE 'api[_-]?key|secret|token|password' licensing-compliance-report.*` and workflow logs show no secret values; script prints only package names/versions/licences/findings.
7. Workflow `.github/workflows/licence-compliance.yml` stays report-only (`continue-on-error: true`, no required-check gate) with a commented enforcement snippet; `python -c "yaml.safe_load(...)"` passes.
8. This slice's 4 files (`ci/check_licences.py`, `ci/test_check_licences.py`, `.github/workflows/licence-compliance.yml`, `docs/legal/compliance-ci.md`) are under `ci/`+`.github/`+`docs/legal/`; tracked prod diff empty; `git status` full may show documented stacked sibling-slice paths + harness `spec/features` inputs (excluded); no push to `main`.

## Non-goals
- No active enforcement (no blocking check, no required status, no merge/release gate change).
- No LICENSE/NOTICE text grant, no licence-header insertion, no inventory verdict edits to force PASS.
- No dependency add/remove/upgrade, no SBOM regeneration beyond freshness verification.
- No push/merge to `main`, no release.

## Interfaces / data
- `ci/check_licences.py`: add `--strict` flag; deterministic ordering (sorted verdict rows, findings, JSON keys); stdout/report schema unchanged (meta/summary/findings/verdicts).
- `.github/workflows/licence-compliance.yml`: report-only default retained; documented (commented) `--strict` enforcement path.
- `docs/legal/compliance-ci.md`: add exit-code table + enforcement-policy section (report-only now, human approval required to enable `--strict`).
- Backwards compatible: default invocation behavior and exit code unchanged.

## Test plan
- `python -m py_compile ci/check_licences.py`
- `python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/licence-compliance.yml'))"`
- `python ci/check_licences.py --check-only; echo $?` expects 0; `python ci/check_licences.py --strict --check-only; echo $?` expects non-zero (Blocked/Unknown present).
- Determinism: run twice, `diff` stdout and JSON report identical.
- `grep -riE 'api[_-]?key|bearer|sessionkey' licensing-compliance-report.*` expects no hits; `git diff --name-only` scoped to `ci/` + `.github/` + `docs/legal/`.
- New/updated tests: `--strict` exit-code cases, determinism case, verdict four-status case.

## Risk tier
2 (normal)

## Rollback
`git checkout -- ci/check_licences.py .github/workflows/licence-compliance.yml docs/legal/compliance-ci.md` or revert hardening commit; workflow returns to prior report-only script with exit 0.

## Open decisions
- None. Mandate and scanner baseline (575/2/3/133) fix scope; enforcement activation stays a future human decision.
