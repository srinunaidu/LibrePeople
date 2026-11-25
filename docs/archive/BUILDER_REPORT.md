# Builder Report: Fix Design Alignment Contrast Issues

## Implemented
Fixed the remaining color-contrast issues revealed by `design-alignment.spec.ts` (axe `color-contrast` violations on small text over light surfaces).

1. **`frontend/src/marketing.css` — `.mk-chip` (line 446)**
   - `background: rgba(17, 27, 49, 0.6);` → `background: rgba(17, 27, 49, 0.85);`
   - Darker chip bg raises white-text contrast from ~3.24:1 to ~4.8:1 (≥ 4.5:1 for small text). Addresses StatusPill "open"/"pending" chips (People.tsx renders via `StatusPill` → `mk-chip`), so no separate People.tsx edit was needed.

2. **`frontend/src/components/ui/table.tsx` — table header (line 241)**
   - `"... text-fg-muted ..."` → `"... text-fg ..."` in the header cell className.
   - Header text now uses the default foreground (~#111827 light mode) instead of `#64748b` on `#f8fafc` (~11:1 vs 4.32:1, ≥ 4.5:1).

## Files Modified
- `frontend/src/marketing.css` — `.mk-chip` background opacity 0.6 → 0.85
- `frontend/src/components/ui/table.tsx` — header `text-fg-muted` → `text-fg`

## Branch/worktree
- Worktree: `/Users/srinivas/LLM/Workforce/Karmathy` (repo root)
- Branch: `fix/design-alignment-contrast-issues`
- Base commit: `df80045907f9276c912f61e76a1eaaba39cf4f9c`

## Tests
All run from `frontend/`:
- `npm run build` → **PASS** (vite build, 2.71s, exit 0)
- `npm run typecheck` → **PASS** (tsc --noEmit, exit 0)
- `npm run check:classes` → **PASS** (Class integrity OK, exit 0)

Note: `design-alignment.spec.ts` is a Playwright runtime test requiring a dev server + signed-in browser session; I ran the static verification suite (build/typecheck/check:classes) which all pass. I did not execute the Playwright e2e suite.

## Contract deviations
none

## Risks for the validator
- Pre-existing uncommitted changes were already present in the working directory before this task (unrelated marketing/design-system work); they are not part of this change set.
- `frontend/dist` build output is gitignored, so it won't pollute the tree.
- Untracked pre-existing items: `frontend/src/components/platform/`, `packages/tokens/combine-tokens.js` (not touched by this task).
