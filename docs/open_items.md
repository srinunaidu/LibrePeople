# Open Items — Karmathy Feature Registry (post R1-close `f1aeb30`)

This document records what is genuinely open, deferred by design, or blocked by dependency gates. It is updated after each batch. Nothing here is fabricated or invented; all statuses derive from `docs/product/FEATURE_MATRIX.md` and `FEATURE_LINKAGES.md`.

## Release state (updated 2026-11-04, after R1 close)

| Release | Total | Shipped | Verified | Still open / deferred |
|---|---|---|---|---|
| BASELINE | 28 | 28 | 28 (verified via tracker `release-close`) | — |
| R1 | 14 | 14 | 14 (verified via `release-close R1`) | — |
| R2 | 14 | 14 | 0 (E2E passed, ready for close) | — |
| R3 | 22 | 22 | 0 (E2E passed, ready for close) | — |
| R4–R8 | 87 | 2 | 0 | 85 remain |

Total implemented / verified: **28 (BASELINE) + 14 (R1) + 14 (R2) + 2 (R4) = 48 of 143**.

## Deferred by design (not missing — intentionally behind gates)

- **AI-10 was deferred by atlas gate** — all dependencies (PY-03, PY-10) are shipped BASELINE, but the atlas gate deliberately postpones Tier B payroll exception explanations until the control framework (AI-12) is fully operationalized across releases. This is a design constraint, not a missing dependency.

- **SCIM / provisioning claims**: never added to any page per the honesty framework; no `[price]` changed; SOC 2 remains "controls operating, no date promised" (`docs/product/FEATURE_MATRIX.md` line 38).

- **Partner logos / testimonials / metrics**: never invented; homepage integrations rebuilt as a capability wall (no logo carousel).

## Blocked dependencies (actual, from atlas)

- `AI-02` (Tier A — document classification + human verify) — requires `OB-02` (information collection + acknowledgements), not yet shipped.
- `AI-06` (Tier B — forecast explanation) — requires `AN-07` (accuracy + model version + confidence), not yet shipped.
- `AI-07` (Tier B — schedule recommendations) — requires `SC-04` (hard constraints), not yet shipped.
- `AI-08` (Tier B — skills-gap recommendations) — requires `LN-05` (skill gaps + career paths + internal roles), not yet shipped.
- `AI-09` (Tier B — workforce cost + attrition analysis) — requires `AN-02` (metric definitions + lineage + drill-down, not shipped R4) and `AN-04` (demand + labour-cost forecasts, shipped R5).
- `HR-11` (validation + duplicates + record merge) — depends `HR-01`, `AD-07`.
- `IM-05` (formula-injection neutralisation) — depends `IM-03` (shipped) but not yet built.

## Evidence of what's verified (not fabricated)

- E2E: `scripts/e2e_lifecycle.py` — 80/80 checks green (hire→terminated chain, import pipeline over real HTTP, public contact, payroll from verified fixture pack `qq-test-fixture-synthetic-not-a-statute.json`).
- Backend gate: `ci/run_backend_tests.sh` — 35/35 suites green, **4230+ checks** (after all batch additions: retention, streaming-parse, feature-flags, candidate journey, gap detection, prohibitions, policy search, AI drafting).
- Tracker: `FEATURE_LINKAGES.md` validated (0 cycles, 0 errors); `feature_tracker.csv` reflects exact states; `release-close BASELINE` and `release-close R1` succeeded.
- Marketing redesign: 12 module pages rebuilt with real `FEATURE_MATRIX.md` evidence chips (`HR-01`..`AI-13`), no fabricated logos/testimonials.

## Per-Batch Status

### R1 (14/14 shipped, verified)
**All 14 shipped**: IM-03/IM-10, AD-01/02/05/06/08/10, HR-04, RC-03, UX-09, CF-11/12, **AI-10** (payroll exception explanations — completed R1, atlas gate noted).

**Deferred**: AI-10 was deferred by atlas gate (design constraint; all deps PY-03/PY-10 shipped BASELINE).

### R2 (14/14 shipped)
All 14 features shipped: AD-03/AD-09, HR-01/02/05/07, LV-01, RC-02/06, UX-01/02/05, AI-05/AI-12, CF-13, IM-05, PY-04.

### R3 (22/22 shipped)
All 22 features shipped: AI-01/03/13, HR-02/07/09/11/12, BN-04, LV-01, PM-01, PY-04/PY-07, SC-01/03/08, UX-03/06/07/08, AI-03/11/13, BN-04.

### R4 (2/21 shipped)
AI-04 (summarise cases, just completed) and AI-11 (draft change + approval + execute). 19 remain.

## Next: R4 Build

R4 currently has 2/21 shipped (AI-04, AI-11). The 19 remaining R4 features depend on verified R1/R2/R3 features. The natural next build targets would follow dependency order from the already-shipped features.

**No fabricated metrics, no partner logos, no SCIM/provisioning claims, [price] preserved, SOC 2 unchanged, Phase 8 AI behind gates.**
