# Phase T — Pre-Launch Checklist (The Thread)

**Status:** all Phase T code live (`2c7d4ba` → `caa1f3a` → `a29a394` chain on `main`).

- [x] The Thread design-system file (`designSystem.ts`) — 8 lifecycle stages
- [x] AI capacities module (`/ai`) — planned, not debt; references G0–G9 gates + Phase 8 spec order in projectStatus.ts; live demo CTA + real capabilities list
- [x] ThreadCompact (compact variant) wired into `/platform`, `/recruiting` + module pages
- [x] Thread draw-once CSS + `prefers-reduced-motion` (final state immediate)
- [x] Broken-thread 404 page + 404 SEO (noindex) + catch-all route (no redirect)
- [x] Per-page SEO engine (`seo.ts`) + `PublicLayout` mount
- [x] SEO per-page table, robots + sitemap corrected, OG 1200×630 image
- [x] Design check `0 violations`; routes `108`; build OK; classes OK
- [x] Production checks: backend `/health` 200, `POST /public/contact` 201, frontend 200 across all marketing pages + unknown (SPAs serve 404)

Remaining per brief (next mini-batch): module page feature cards, Pricing placeholder + FAQ schema on `/pricing`, Solutions/Industry pages deep copy, Resources/blog article template, legal TOC, final Lighthouse/WAVE check.
