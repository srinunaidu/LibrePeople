# Feature: honesty-sweep (R2)

## Behavior
Sweep the 7 named fake-data screens, sampled dead controls, and 8 flag-shim screens to wire-if-backend-exists, else honest EmptyState/disabled-with-reason. Finding: E-UX-02 already made 6 of 7 screens and 7 of 8 shims honest — this sweep verifies and closes the one real gap (InterviewScheduling vs live `/interviews` CRUD).

## Acceptance criteria
1. Triage: `spec/features/defective-backend-fix/contract.md` IS the R0 contract (LP-AUD-005/006, LP-DATA-001, backend/test-only) — stage it for commit; do not alter it here.
2. HEAD: 3e3d08d verified.
3. VERIFY-ONLY (already honest, no code change): Import.tsx:91-100, ManagerAssignments.tsx:39-40, JurisdictionRules.tsx:47-65, AnnouncementsDirectory.tsx:42-62, ContingentWorkers.tsx:41-59, ProbationTracking.tsx:40-55, RehireHandling.tsx:40-55, SkillGaps.tsx:40-55, SavedViews.tsx:50ff, StatesDiscipline.tsx:38-52, ExitInterviews.tsx:26 — each keeps a header comment citing its gap ID and real endpoint (add the comment if missing).
4. WIRE: InterviewScheduling — rewire list/create/update to GET/POST/PUT /api/v1/interviews (endpoints/interviews.py:32,55,76,88; api.py:53). Add listInterviews/createInterview/updateInterview helpers to frontend/src/lib/api.ts ONLY (no other api.ts changes). Update feedback-slice2.test.ts:182-185 which locks the old flag-shim (lead-approved).
5. Marketing: ProductMockup.tsx:154-156 caption stays; relabel the Live pulse (:29-32) to Preview.
6. FIX: ProjectStatus.tsx:93 hardcoded commit — replace with build-time injected value if trivial (Vite define), else remove the stamp (document choice in commit message).
7. DesignGallery.tsx: add one-line /* internal preview — not product data */ comment; no functional change.
8. Dead controls: validator re-runs the count; any control that does nothing user-visible must show a reason string, else it is removed — not silently enabled.
9. Decision rule: wire-if-backend-exists → else honest EmptyState/disabled-with-reason + comment citing gap; no invented endpoints, no fake data, no hidden buttons. Missing endpoint ⇒ STOP, report, do not build backend here.
## Non-goals
No backend changes, migrations, or new endpoints. No visual redesign. No touching the R0 contract's scope.
## Test plan
New frontend/src/lib/honesty-sweep.test.ts: assert no Math.random|dummy|lorem|sampleData in pages/ + components/marketing/; assert InterviewScheduling hits /api/v1/interviews not feature-flags/interview_type; assert ProjectStatus has no hardcoded 7-hex commit. Run vitest + tsc + existing feedback-slice2.test.ts green.
## Risk tier
2 (normal)
## Rollback
git revert the sweep commit(s). No data migration to unwind.
