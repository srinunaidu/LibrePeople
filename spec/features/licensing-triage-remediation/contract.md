# Feature: licensing-triage-remediation

## Behavior
Triage-only pass over every Review / Blocked / Unknown row from the last scanner run (575 Confirmed / 2 Review / 3 Blocked / 133 Unknown, 713 rows). Investigates each item, records package/version/direct-vs-transitive/license/source/distribution/attribution/compatibility/remediation/final-classification, updates inventory + SBOM + allowlist with defensible reasons, reruns `ci/check_licences.py --check-only` report-only, and appends U/L entries. No dependency removal, upgrade, LICENSE publication, or enforcement change.

## Acceptance criteria
1. Every Review (2), Blocked (3, MPL-2.0 axe-core test-only), and Unknown (133, UNVERIFIED backend) row has a triage record with 9 fields (package, version, direct/transitive, license, source, distribution, attribution, compatibility, remediation) plus final classification.
2. Zero Unknown rows are reclassified to Confirmed without registry/lockfile metadata evidence.
3. MPL-2.0 (axe-core), LGPL (fpdf2), Oracle UPL, and ISC (lucide-react) each have written compatibility notes in the compliance report.
4. `docs/legal/*` inventory JSON + MD updated; timestamped SBOM regenerated and fresh (timestamp >= triage date).
5. Scanner allowlist updated only with defensible reasons; no concealment or silent suppression of Unknown/Blocked.
6. `ci/check_licences.py --check-only` exits 0 in report-only mode and its output is recorded.
7. No `LICENSE` file created/modified; no production dependency file edited (`package.json`, lockfiles, `requirements*`, `pyproject.toml`, Dockerfiles); no header insertion.
8. No `git push` and no merge performed; `git diff --stat` touches only `docs/legal/**`, `ci/**`, and `spec/features/licensing-triage-remediation/**`.
9. U/L log appended with triage findings and counts.

## Non-goals
- No dependency removal, upgrade, downgrade, or substitution without a usage assessment.
- No LICENSE publication or license-text changes.
- No copyright header insertion.
- No enforcement switch (check-only stays check-only; no CI gate hardening).
- No push, merge, or release.

## Interfaces / data
- Inputs: last scanner CSV/JSON (713 rows), `docs/legal/` inventory JSON + MD, SBOM dir, scanner allowlist, `ci/check_licences.py`.
- Outputs: updated inventory JSON/MD, new timestamped SBOM, updated allowlist with reasons, updated compliance report, U/L appendix entries.
- Backwards compatible: docs/CI-only change; no runtime, API, schema, migration, or config change.

## Test plan
- `jq` counts: Confirm Review/Blocked/Unknown triage rows equal 2/3/133 with all 9 fields + remediation non-empty.
- `python3 -m json.tool` validates inventory JSON and SBOM JSON parse.
- `python3 ci/check_licences.py --check-only` (or repo-documented equivalent) exits 0; capture output.
- `git status --short && git diff --stat` shows changes scoped to `docs/legal/**`, `ci/**`, `spec/features/licensing-triage-remediation/**` only.
- New tests: none (docs/CI report-only); validator re-runs the four commands above.

## Risk tier
1 (irreversible)

## Rollback
`git checkout -- docs/legal ci spec/features/licensing-triage-remediation` (or `git reset --hard` on `chore/licensing-transition` if unpushed); delete regenerated SBOM timestamp file; no prod/data rollback needed.

## Open decisions
- None for lead to ask human: scope, report-only mode, and no-removal constraint are fixed by this task. Flag any new license texts found during triage back to lead as follow-up.
