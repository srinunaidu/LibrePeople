# FEATURES_TRACKING.md — scope + work ledger

> This file is the **fast index** for "what should we build / fix next".
> The canonical, evidence-backed status of record stays in
> `docs/product/FEATURE_MATRIX.md` (143 capabilities) and
> `frontend/src/lib/projectStatus.ts` (rendered at `/project-status`).
> Update *those* when a capability lands; add entries here for discrete
> work items and tick them off as shipped.

**Last updated:** 2026-11-03 · HEAD after R1 batch-1 (retention + streaming-parse proof) · capabilities 38/143 implemented per `projectStatus.ts` · tracker.py: BASELINE verified 28/28, R1 2/14 shipped

---

## 1. Capability snapshot (mirrors projectStatus.ts)

| Label | Value |
|---|---|
| Health (capabilities) | 38 / 143 (26.6 %) — ~53 partial · ~52 missing · 0 broken |
| Requests | done 60 · partial 2 · not started 0 |
| Defects | 3 low open (D-029 operationId · D-017 seed guard · D-045 picker search) |
| Deploy evidence | status of record in `projectStatus.ts` → `DEPLOYS` |

Phases (spec order — security → contracts → import → core HCM → forecasting → payroll → experience → AI → release):
G0–G7 landed per the gates table; **Phase 8 (AI) explicitly deferred behind G9 release gating — not debt**; Phase 9 hardening remainder is scheduled, not missing.

## 2. Recently shipped (latest batches)

- **R1 batch 1 of 14 — retention schedule + streaming parse proof (2026-11-03, `845de88`)**: IM-10 (upload retention) — nothing ever scheduled `retention_run`; the purge existed, the schedule didn't. Now `RETENTION_SCHEDULE_ENABLED` (opt-in, default off) wires one boot tick + 24h interval into the worker family, deduped while a job is pending/running, fail-closed (a failed enqueue never takes the API down), proven by a new 11-test suite. IM-03 (streaming parse) — the shipped pipeline already parses via `iter_records` with strict RFC 4180 + byte/row caps; the HTTP-level limits were gated, the streaming layer wasn't proven — a new 8-test suite proves row cap enforced *during* iteration, byte cap on chunked uploads, embedded newlines, malformed quoting refused. Both suites wired into `ci/run_backend_tests.sh`: **35/35 suites green, 4,230 checks, exit 0**. `tracker.py`: IM-10 → shipped, IM-03 → shipped (R1 remains 2 of 14 shipped; R1 E2E + release-close pending the rest).
- **Hire→terminated E2E validation extended to 70 checks (2026-11-03)**

- **Hire→terminated E2E validation extended to 70 checks (2026-11-03)**: payroll processing from synthetic verified fixture pack (QQ), reconciliation expected==paid, segregation-of-duties defence verified, approve+finalize lock, minimum-privilege RBAC asserted both directions, audit chain verification endpoint asserted. Payroll suite crash fixed (missing import) — 251/251 green. Full backend gate 33/33.
- **Alignment pass across every marketing page (2026-11-03)**: shared `PageHero`/`PageBody` (aurora band + eyebrow kicker + display title) rolled out to all pages; About/Solutions/Resources/Careers/Documentation/Privacy/Terms/Contact/FAQ/Security/Compare/Industries/IndustryDetail/404 each corrected to the one design; light cards → `mk-card`; tones normalized to fg tokens; nav breakpoint fixed at lg; all 32 public URLs 200 in prod.

- **360° visual redesign (2026-11-02)**: dark-first scoped design system `frontend/src/marketing.css` — `.mkt-root` re-declares the token variables dark inside the marketing subtree only (legacy pages auto-dark), Space Grotesk display type (Google Fonts), glass nav, gradient-border cards, glow CTAs, floating code-built dashboard mockup (`ProductMockup.tsx`), capability marquee + reveal-on-scroll, giant-wordmark footer; `ModulePage` shell + `/pricing` restyled; stack unchanged, zero new dependencies.
- **Marketing site makeover (2026-11-02)**: all 12 lifecycle module pages rebuilt through a shared `ModulePage` shell — evidence-grounded capability grids (catalog refs as chips), honest "designed and sequenced" roadmap strips, true prev/next thread links, dark CTA band with hand-drawn ThreadDark SVG artwork; pricing page rebuilt with per-tier inclusions + honesty note; homepage integrations section turned into a capability wall (vendor logos removed); FAQ/Solutions/Security claims grounded (SCIM, DocuSign/Adobe, "200+ tools", stale "Q2 2026" removed); SEO meta entries added for all 12 module pages (they previously resolved to the 404 meta).
- **Marketing site rebuild — Phase T "The Thread"** (`recruit → onboard → time → leave → pay → perform → grow → offboard`): ThreadHero / ThreadCompact / broken-thread 404, SEO engine (`frontend/src/lib/seo.ts`), module pages `/recruiting … /compliance`, `/pricing` (with `[price]` placeholders), honest `/ai` module referencing the real Phase-8 deferral.
- **Auto-generated natural keys** (backend `app/core/ids.py` `next_code`, optional-create schemas): employees `EMP-####`, departments `DEP-####`, jobs `JOB-####`, positions `POS-####`, locations `LOC-####`, cost centres `CC-####`. Explicit values still win; generated values are conflict-checked.
- **Front-end create forms (People portal)**: optional ID/code fields with "Auto (PREFIX-0004)" placeholders, inline required/email validation, generated key surfaced in the success notice.
- **Client onboarding**: after creating a client, the workspace URL `/t/{slug}/dashboard` is shown (create notice + "Open" link in the client header) — path-based workspaces, honestly labelled.

## 3. Work backlog (tick when shipped)

### Front end gaps
- [ ] Employee detail: emergency contacts (catalog `HR-01`) — no model or screen yet.
- [ ] Contract / probation / notice fields (catalog `HR-02`) — schema + effective-dating.
- [ ] Picker search (defect `D-045`) — searchable dropdowns for large option sets.
- [ ] Dark mode: verify every shipped marketing page against token palette (no hardcoded colours).
- [ ] `[price]` placeholders on `/pricing` → replace with real tiers when finance signs off.
- [ ] `D-029` — restore operationIds in the OpenAPI contract after contract regen.

### Back end gaps
- [ ] Seed guard (`D-017`) — refuse seeds against a DATABASE_URL that looks like production.
- [ ] Rate-limit coverage review on all public (`/public/*`) endpoints.
- [ ] Import templates: optional auto-ID column header ("leave empty to auto-generate").

### Process / release
- [ ] Full 4,172-check backend gate re-run after the auto-ID schema batch.
- [ ] Drift check (contracts vs routes) after schema change: 314 checks expected green.
- [ ] Staging gate + browser suites re-run; then the follow-up docs commit (STATUS.md, agents/*, info.md).

## 4. Ground rules for new entries

- One row per work item; include the catalogue ID when one exists.
- No invented features: link to the matching `projectStatus.ts` phase or `FEATURE_CATALOG.md` ID.
- "Shipped" means merged to `main`, both services deployed, and prod-confirmed (health 200 / smoke pass).
