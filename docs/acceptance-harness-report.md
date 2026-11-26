# Acceptance harness report (dry-run) — 2026-11-26

- Branch: `agent/qa/acceptance-harness` from main HEAD `d67ff7059af4a43289cc52c9581d23bb46305a31`
- Harness: `scripts/acceptance_harness.py` (left READ-ONLY, no edits)
- Command: `cd backend && SECRET_KEY=dummy-local-test-key python3 ../scripts/acceptance_harness.py --dry-run`
- Result: **BLOCKED — exit 2 in <5s, zero suites invoked, CSV untouched.** Verbatim stderr:
  `harness: missing column 'Requirement ID'`
- `--dry-run` flag verified in source: "evidence only; do not modify CSV". No CSV write attempted or made.

## Root cause (tree drift since Karmathy transfer)

1. `docs/product/requirements-traceability.csv` now carries a 5-line `#` prologue (reconciliation notes, 2026-11-24); header is on line 6. The harness uses raw `csv.DictReader`, so the first comment line becomes `fieldnames` → missing-column abort before any mapping.
2. Status-vocabulary drift behind the same gate: tree data has BLOCKED 18 / DEFERRED 8 / IN PROGRESS 3 / IMPLEMENTED 105 / VERIFIED 2 / TESTED 0, while the harness end-gates assert BLOCKED==3, `DEFERRED BY APPROVAL`==8, IN PROGRESS==3. A comment-skip compat fix alone would still fail these gates, so no fix was applied (changing gates would exceed the minimal-compat mandate). Harness stays read-only; CSV unmodified (136 `LP-` rows confirmed intact).

## Counts

- Rows mapped: 0 | Passed: 0 | Failed: 0 | Crashed: 1 (pre-suite parse abort) | Duration: <5s
- In-scope under harness logic would have been 105 (IMPLEMENTED only; TESTED 0); VERIFIED rows are silently out of scope.

## Expenses UI route check

**MISSING** — `grep -ri expense frontend/src` returns zero matches (App.tsx count 0, no expense page/component anywhere). No expense route exists.

## Next step for architect

Decide: (a) update harness (skip `#` prologue + reconcile gates to BLOCKED 18 / DEFERRED vocab), or (b) declare harness superseded. Either is a design decision — not taken here.
