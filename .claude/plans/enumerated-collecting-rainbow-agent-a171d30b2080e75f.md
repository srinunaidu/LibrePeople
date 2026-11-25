# Plan: Marketing Site Rebuild — Modern, Elegant, Professional, Built to Convert

**Date:** 2026-10-27 · **Branch:** `main` @ `5501a6d` · **Build:** 103 routes, verify green
**Trigger:** "completely change https://karmathy-frontend.onrender.com/ — modern and elegant, professional, check all hyperlinks, create sub-pages with detailed info, add industry insights that sell and attract companies"
**Audits:** 2 sub-agents — hyperlink audit (38% dead links), content quality audit (no pricing/testimonials/case studies/industry depth), full file inventory. Every section below cites `file:line`.

---

## Context

### What the marketing site is today

- `frontend/src/pages/Homepage.tsx` (372 lines) has its own bespoke `<nav>` — every other public page uses `components/PublicLayout.tsx`. Two shells to maintain, already drifted.
- 9 public routes: `/`, `/solutions`, `/industries`, `/resources`, `/about`, `/careers`, `/contact`, `/privacy`, `/terms`, `/docs`. The nav advertises `Platform` (5th item) but `/platform` is a `ProtectedRoute` — anonymous click → login wall.
- **38% of Homepage links are dead** (10/26 hit protected routes or wrong targets). `Solutions` 4/6 cards dead (to `/login`), `Resources` 5/6 dead, footer 10/16 dead. Every dead link renders as a login wall, not a 404 (wildcard → `/` masks it).
- **Product preview is a gray placeholder** — `Homepage.tsx:149-163` gradient box with text, no screenshot/video. The #1 "old/empty" signal.
- **Content sells architecture, not outcomes** — 6 FEATURES + 12 MODULES + 10 industry pills + 8 integrations + 6 security items, all one-sentence glosses. No pain, no metric, no ROI verb (`cut`, `automate`, `save`). Hero `Empowering People. Enabling Possibilities.` could be any consultancy.
- **Missing everything a B2B buyer needs:** no pricing, no testimonials/logos/case studies, no comparison, no FAQ, no industry playbook, no trust centre (SOC 2 etc.), no gated lead magnet, no Calendly. Contact form `POST /core-hr/cases` is auth-gated — the primary conversion path silently drops anonymous leads (the demo request is never delivered).

### What modern B2B HCM marketing does (Workday / BambooHR / Rippling pattern)

Outcome headline + metric → logo wall + count → testimonial with headshot + persona → transparent pricing tier + ROI calculator → industry pages with workflow diagram + pain + compliance → product screenshots / 90-sec video / interactive tour → comparison matrix + migration path → trust centre (SOC 2, GDPR, uptime) → gated resources → calendar-scheduled demo → FAQ.

Karmathy does **none** of the right column today.

### What the user asked for (must all be in this plan)

1. Completely modern & elegant, professional look
2. Every hyperlink correct — no dead/protected links from public pages
3. Sub-pages with detailed information (not one-line cards)
4. Industry insights that sell and attract companies

---

## Design Direction for the Rebuild

**Visual language:** Use the existing token system (`index.css` — Inter Variable, warm surfaces, soft shadows, glass header, pill tabs — already modernised in `f2206c2`) as the foundation. Marketing pages have always been `light-surface` (cream #fef7ed) + Inter tight tracking — keep that. What changes is **content architecture and component quality**:

- **Hero:** Outcome headline + metric, not inspirational tagline. Single saturated value prop with supporting pills → `Request a demo` + secondary `Watch 2-min tour` (public video page, not `/platform`).
- **Layout:** Section `py-24 lg:py-32` generous breathing + containment variance (not mechanical `py-20` alternating `bg-page/white`). Bento grids with `col-span 2/1` + `icon-tile 44px gradient` + hover `ring` + staggered `gap-6 lg:gap-8`.
- **Preview:** Real screenshot / looped video behind glass, not placeholder. Even a styled mock of `/people` or `/payroll` behind `backdrop-blur` sells more than a gradient box.
- **Proof:** Logo wall (even 6 design partners), 3 testimonial cards (headshot + title + metric quote), G2 badge placeholder, count strip with footnotes.
- **Tone:** Buyer verbs (`cut`, `automate`, `ensure`, `reduce`) + regulation names (`HIPAA`, `OSHA`, `GDPR`) + quantified outcomes (`60%`, `2 days`), not architecture nouns (`multi-tenant`, `mTLS` — keep behind a `Technical details` toggle).
- **Shell:** Unify — `Homepage.tsx` renders `PublicLayout` (delete bespoke nav, add `variant="homepage"` if needed). One nav, one footer, every link correct.

---

## Phase M1 — Fix What Is Broken (no new content, just correctness)

**Goal:** Every public link works for an anonymous visitor. No marketing CTA hits an auth wall. Contact/demo flow delivers.

| # | File | Change |
|---|---|---|
| M1.1 | `frontend/src/pages/Homepage.tsx:50-69` + `components/PublicLayout.tsx:4-10` | **Unify shells:** Homepage renders `PublicLayout` (remove bespoke nav 50-69). Nav `Platform` → `Platform` public showcase: either create a lightweight public `/platform` page (feature tour, not the app) or retarget nav item to `/solutions` with label `Platform` → `Solutions` + keep `/platform` as app-only. Until the showcase exists, nav `Platform` links to `/solutions` (or new `/platform` marketing page — see M2.1). Same fix in `PublicLayout.tsx:5`. |
| M1.2 | `frontend/src/pages/Contact.tsx:18-23` | **Fix conversion:** `POST /core-hr/cases` → public endpoint. Options: (a) `POST /api/v1/contact` public (new backend, `CONTACT_ROLES = ()` allow anonymous, rate-limited, writes to `cases` with `Intake` or to a new `leads` table) — preferred; (b) allow anonymous create on `/core-hr/cases` with `category=General` + captcha — less clean. Also add fields `Company`, `Size` (1-50/51-200/201-1000/1000+), `Interest` (Hire/Time/Payroll/All), `Phone`. Add success `We'll reply within 1 business day — or book now` + Calendly embed link. Preserve demo message delivery on failure (don't silently drop). |
| M1.3 | `frontend/src/pages/Solutions.tsx:5-10` + `Resources.tsx:4-11` | **Fix 9 dead cards:** Every card's `to` must be a public route. `By Company Size` / `Integrations` → `/pricing` or `/docs` (not `/login`). `Client Onboarding` / `Platform Modules` / `Reporting` → new public pages under `/solutions/*` or `/platform` showcase (see M2.1). No public card may link to `/login` or a `ProtectedRoute`. If a destination doesn't exist yet, link to `/contact` with prefilled `interest` or to `/docs` — never to login. Make this a rule enforced by `check:routes` (marketing pages flagged if they link to protected paths). |
| M1.4 | `frontend/src/pages/Homepage.tsx:297-351` + `components/PublicLayout` footer | **Fix 10 dead footer links + API Reference target:** `API Reference → /docs` (not `/resources`), `Platform Modules → /platform` showcase (or `/solutions`), product app links (`/dashboard`, `/recruiting`, `/time`, `/leave`, `/reports`, `/client-onboarding`) → remove from public footer or retarget to their public showcase equivalents. Footer `Dashboard/Recruiting/Time/Leave` today invite prospects into login walls — replace with `Core HR`, `Hiring`, `Time & Pay`, `Insights` linking to public pages. |
| M1.5 | `frontend/public/sitemap.xml:9-12` + `robots.txt:13,18` | **Reconcile SEO contradiction:** `sitemap` lists `/platform` pri 0.9 while `robots.txt` disallows it. Either make `/platform` public showcase (then allow + keep in sitemap) or remove from sitemap until it is. Also remove hard-coded `karmathy-frontend.onrender.com` domain — generate at build via `VITE_PUBLIC_URL` or keep relative. Add `lastmod` dates. |
| M1.6 | `frontend/index.html:8-22` | **Per-page SEO:** Add `react-helmet-async` (or `useEffect document.title` + meta) so every public route sets unique `<title>`, `description`, `canonical`, `og:image`/`og:url`/`twitter:*`. Add `JSON-LD` `Organization` to Homepage + `SoftwareApplication` to Platform showcase. Add `og-image.png` to `public/`. Without this, all public routes share one static title/description and link previews are text-only. |

**Verification M1:** `node scripts/check-routes.mjs` + new rule: no public page may link to a `ProtectedRoute` path — script flags it. Manual: open every public page incognito, click every link, no login wall. `curl -s https://karmathy-backend.onrender.com/api/v1/contact` (or new public endpoint) returns 201 without auth.

---

## Phase M2 — Marketing Site Rebuild (new pages, new content architecture)

### M2.1 — Public Platform showcase (`/platform` marketing, not the app)

**New file:** `frontend/src/pages/marketing/PlatformShowcase.tsx` (or `pages/PlatformMarketing.tsx` — distinct from the protected `pages/Platform.tsx` app screen; use `pages/marketing/*` folder for all new marketing pages to avoid collision).

- Route `/platform` becomes **public** for this page; the authenticated app moves to `/app/platform` or keeps `/platform` but `PublicLayout` vs `Layout` is chosen by auth state (public visitors see the showcase, authenticated see the app — simplest: keep `/platform` public, app stays at `/platform` but `Platform.tsx` checks `isAuthenticated` and renders showcase for anonymous, app for authenticated — or split to `/product` vs `/platform` and redirect old marketing links to `/product`). **Recommendation:** keep `/platform` as the public showcase (it's the marketed URL), move the app's platform screen to `/app` or keep it at `/platform` behind auth and make the showcase the unauthenticated view of the same path (auth gate decides). This preserves SEO and fixes every existing `/platform` link without retargeting.
- Content: hero `One platform, hire to retire` → 6-step journey `Hire → Onboard → Time & Scheduling → Leave → Payroll → Offboard` as a horizontal stepper (each step links to its public sub-page), then per-module deep cards (Core HR, Recruiting, Onboarding, Time, Scheduling, Leave, Offboarding, Payroll, Performance, Benefits, Learning, Compliance, Reporting) with `Pain → Feature → Outcome` + `icon-tile` + `StatusPill` for maturity. Ends with `Integrations & extensibility` (partner logos, not protocol names) and CTA.

### M2.2 — Homepage rebuild (`Homepage.tsx` — complete rewrite, keep route `/`)

| Section | Current | New |
|---|---|---|
| **Nav** | Bespoke, 5 items, Platform → login wall | `PublicLayout` (unified). Nav: `Platform / Solutions / Industries / Resources / Company` — all public. `Sign in → /login`, `Request a demo → /contact` + `Watch tour → /platform#tour` (or `/resources#tour`). |
| **Hero** | `Empowering People. Enabling Possibilities.` + feature-led sub + 2 CTAs | **Outcome headline** e.g. `Run HR, payroll and scheduling in one place — onboard a new hire in 2 days, not 2 weeks.` Sub: 3 outcome bullets `• Cut payroll errors with reconciliation  • Approve leave in one click  • Migrate from Bamboo/ADP via CSV in minutes`. CTAs: `Request a demo → /contact` + `Watch 2-min tour → /platform#tour` (low-commitment). Eyebrow `HCM platform for teams that outgrew spreadsheets`. |
| **Proof strip** | `24+ modules / 11 countries / 99.98% / <2 days` — unverified, no footnote | **Real numbers with footnotes** or remove until true: `12 modules live · 214-employee demo tenant · CSV migration in minutes` + link `How we count → /about#transparency`. Add **logo wall** (6 design partners / placeholder + `Trusted by` + G2 badge placeholder). |
| **Preview** | Gradient placeholder + `Sign in to explore` | **Real screenshot** of `/people` or `/project-status` behind `card p-4 shadow-xl` + `backdrop-blur` + annotated callouts, or looped `aspect-video` with `poster` + `play` overlay linking to `/platform#tour`. |
| **Features (6 cards)** | `Unified lifecycle` etc. — architecture jargon | **Bento grid** `col-span 2/1` staggered, `icon-tile 44px gradient`, `Pain → Solution` + metric where possible, `hover ring`. Same 6 features but buyer-voiced: `Single source of truth — one employee record, every module reads it` etc. |
| **Modules (12 cards)** | Inventory list, 1-line desc | **8-card bento** (collapse to key 8, link `View all 12 → /platform`), each with `icon-tile + metric/outcome` + `→` chevron to sub-page. |
| **Industries (10 pills)** | Grey pills, no link | **10 industry cards** — each with icon, 1-line pain + `Explore → /industries/:slug` (see M2.5). |
| **Integrations** | Protocol names, grey pills | **Partner logo wall** (Oracle, Okta, Slack, etc. — muted SVG, `hover opacity-100`) + `Works with 200+ tools via REST, SCIM, webhooks` + `View integrations → /platform#integrations`. |
| **Security (6 cards)** | Infra vocab, no cert | **Trust strip** — `Data isolation · RBAC · mTLS · Encrypted secrets` as 4 badges + `SOC 2 in progress (Q2 2026) · GDPR · DPA available → /security` + uptime link. Honest, not claiming unachieved certs. |
| **Resources (3 cards)** | `API Docs → /docs` etc. | **Gated assets** — `HCM Migration Checklist (PDF) → /resources/migration-checklist` (email gate), `Hidden cost of spreadsheets — ROI calculator → /resources/roi-calculator` (interactive), `API Docs → /docs`. Capture MQLs. |
| **Final CTA** | `Join organizations that trust…` (empty claim) | `Ready to run HR without spreadsheets?` + `Request a demo` + `See pricing → /pricing` + `Talk to founding team — reply in 1 business day`. |
| **Footer** | 4 cols, 10 dead links | **Rebuilt footer:** `Product` (Platform, Solutions, Pricing, Changelog), `Industries` (10 slugs), `Resources` (Docs, API, Migration, ROI, Security, FAQ), `Company` (About, Careers, Contact, Privacy, Terms). 30+ indexable links, zero protected targets. |

### M2.3 — Solutions by persona & pain (`Solutions.tsx` rebuild + sub-pages)

**File:** `frontend/src/pages/marketing/Solutions.tsx` (or overwrite `Solutions.tsx` — keep route `/solutions`).

- Replace 6 vague cards with **3 persona cards**: `For HR Leaders — single source of truth, 1-click approvals, audit trail` / `For Finance — accurate labor cost, payroll reconciliation, headcount planning` / `For IT — SSO/SCIM/mTLS + CSV/API migration, no vendor lock-in`. Each: `Pain (3 bullets) → Feature → ROI` + comparison `Still on spreadsheets vs Karmathy` mini-table + `Talk to us → /contact?persona=hr`.
- Add **sub-pages** `frontend/src/pages/marketing/solutions/ByCompanySize.tsx` (`/solutions/company-size`) and `solutions/Integrations.tsx` (`/solutions/integrations`) so the old dead cards have real destinations. `By Company Size` → `Starter (1-50) / Growth (51-500) / Enterprise (500+)` with module matrix + `From $X/employee/mo → /pricing`. `Integrations` → partner grid + flow `HRIS → Karmathy → Payroll/Accounting` + `View API docs → /docs`.

### M2.4 — Pricing (`/pricing` — new)

**New file:** `frontend/src/pages/marketing/Pricing.tsx`.

- 3 tiers: `Starter — up to 50 employees — Core HR + Time + Leave` / `Growth — 51-500 — + Scheduling + Payroll + Performance` / `Enterprise — 500+ — + SSO/SCIM + DPA + dedicated onboarding`. Each with `per employee / month` (or `Contact sales` if not ready to publish numbers — but must show *range* to avoid bounce) + feature checklist + `Most popular` badge on Growth + `30-day pilot · Migration included · Cancel anytime`.
- Feature comparison table (rows = 12 modules, cols = tiers, cells = `✓ / — / Add-on`).
- FAQ mini: `What's included in migration?`, `Do you handle multi-country payroll?`, `What if we outgrow Starter?`.
- CTA `Request a demo → /contact?plan=growth` + `Compare → /compare/*`.

### M2.5 — Industries — deep pages (`/industries` + `/industries/:slug`)

**Files:** `frontend/src/pages/marketing/Industries.tsx` (rebuild index) + `frontend/src/pages/marketing/industries/IndustryDetail.tsx` (param `:slug`).

- Index: 10 industries as **cards with icon + 2-line pain + Explore → /industries/:slug** (not divs). Same 10 as today but linkable.
- Detail (per slug): `Pain (3 bullets + regulation: HIPAA/OSHA/SOX/GDPR) → Karmathy workflow (diagram: e.g. Healthcare Credential → Roster → Time → Payroll with license-expiry guard) → Outcome metric (even if placeholder, cite as design-partner target: "Target: cut agency spend 18%") → Persona quote placeholder → CTA → /contact?industry=healthcare`. Start with **2 verticals fully written** (Healthcare + Manufacturing — highest HCM pain), remaining 8 as `Coming soon — talk to us` with email capture.
- Data: `frontend/src/lib/industries.ts` — array of 10 `{ slug, name, icon, pain: string[], regulation, workflow: string[], outcome }`.

### M2.6 — Resources — gated funnel (`Resources.tsx` rebuild + 2 assets)

**File:** `frontend/src/pages/marketing/Resources.tsx` (rebuild).

- Replace 6 dead tiles with **2 gated assets + Docs link**: `HCM Migration Checklist (PDF) — 5 steps from spreadsheet to Karmathy` (email gate → download) + `Hidden cost of spreadsheets — ROI calculator` (interactive: `employees × hours/week × rate → $/year saved` with `Request a demo` CTA) + `API Documentation → /docs` + `Security & Trust → /security` + `FAQ → /faq` + `Changelog → /docs#changelog`.
- Each gated asset: `Card` with `icon-tile` + description + `Download →` that opens `Dialog` with `email + company` form → `POST /api/v1/contact` with `interest: "migration-checklist"` (lead capture) → success `Check your email` (or direct download for now). This is the MQL funnel competitors use to nurture before demo.

### M2.7 — Trust Center (`/security` — new)

**New file:** `frontend/src/pages/marketing/Security.tsx`.

- Be honest: `Built on Oracle Cloud, data encrypted in transit (mTLS) and at rest, RBAC + audit trail, DPA available on request, SOC 2 Type II in progress (target Q2 2026), GDPR/CCPA posture, data residency: Oracle Cloud region, backups & retention, uptime status link (even Render status), pen-test summary, sub-processors, contact for security@`.
- Badges: aspirational vs achieved — show achieved (`mTLS`, `RBAC`, `Audit trail`, `Encrypted secrets`) as solid, in-progress (`SOC 2`, `ISO 27001`) as `In progress` pill — don't claim unachieved certs.
- Links from Homepage security cards + footer `Resources → Security`.

### M2.8 — FAQ (`/faq` — new) + Homepage accordion

**New file:** `frontend/src/pages/marketing/FAQ.tsx`.

- Seed with 8 objections: `How long does migration take?` `Do you support multi-country/currency payroll?` `What integrations are live?` `Who owns my data?` `What if we need HIPAA?` `What is the Oracle cold-start impact?` `What does support cost?` `Can we self-host or export our data?` — accordion (`Radix Accordion` or `details/summary`) with honest answers (include `Free-tier may spin-down` disclosure from Terms, but framed).
- Homepage: FAQ accordion section (3 of the 8) above final CTA, `View all → /faq`.

### M2.9 — Comparison (`/compare/:competitor` — new)

**New file:** `frontend/src/pages/marketing/Compare.tsx` (param `:competitor`).

- Matrix: rows = 12 modules, cols = `Karmathy | Workday | BambooHR | Rippling` (or per-competitor view `Karmathy vs BambooHR`), cells `✓ / — / Partial` + `Migrating from X` guide. Captures high-intent `Karmathy vs` search. Start with one competitor fully written (BambooHR — closest ICP), others as `Coming soon`.

### M2.10 — Legal + Contact polish

- `Privacy.tsx` / `Terms.tsx`: add effective date, data controller, contact email, DPA link, cookie policy, version. Link `Privacy → Contact` (fix `Privacy.tsx:29` missing link). Not marketing-critical but procurement requires it.
- `Contact.tsx`: add fields `Company, Size, Interest, Phone`, `interest` prefill from `?interest=` / `?industry=` / `?plan=` query, honeypot/captcha, auto-confirmation `We'll reply within 1 business day`, Calendly embed link.

---

## Phase M3 — SEO & Polish

| # | File | Change |
|---|---|---|
| M3.1 | `frontend/index.html` + `PublicLayout.tsx` | `react-helmet-async` (or `useEffect` title/meta) — unique `<title>`, `description`, `canonical`, `og:image`/`og:url` per public route. Add `og-image.png` to `public/` (hero preview). |
| M3.2 | `frontend/public/sitemap.xml` + `robots.txt` | Generate at build from `App.tsx` public routes (or keep manual but correct: remove protected paths, add `/pricing`, `/security`, `/faq`, `/compare/:c`, `/industries/:slug`). Env-agnostic domain. |
| M3.3 | `frontend/src/pages/Homepage.tsx` + all marketing | Replace unverified stats (`24+ modules`, `11 countries`, `99.98%`) with auditable numbers or remove until true. Add footnotes/links to `ProjectStatus` transparency. |
| M3.4 | `frontend/src/components/PublicLayout.tsx` | Footer: 30+ indexable links (integrations, industries, templates, glossary) for long-tail SEO. Add `JSON-LD` `Organization` + `SoftwareApplication` to Homepage + Platform showcase. |

---

## Batching

| Batch | Content | Files | Effort |
|---|---|---|---|
| **M1 — Fix broken** | M1.1–M1.6 — unify shells, fix contact form (public endpoint), fix 9 dead cards, fix 10 footer links, reconcile SEO, per-page meta | `Homepage.tsx`, `PublicLayout.tsx`, `Solutions.tsx`, `Resources.tsx`, `Contact.tsx`, `sitemap.xml`, `robots.txt`, `index.html`, `App.tsx`, `tailwind.config` + new `backend/app/api/v1/endpoints/contact.py` | S–M |
| **M2a — Homepage + Platform showcase** | M2.1 + M2.2 — public `/platform` showcase + Homepage rebuild (hero, proof strip, preview, bento, industries, integrations, security, resources, CTA, footer) | `pages/marketing/*`, `Homepage.tsx`, `PublicLayout.tsx`, `App.tsx` | L |
| **M2b — Solutions, Pricing, Industries deep** | M2.3–M2.5 — persona cards + 2 sub-pages, `/pricing` tier + matrix, `/industries` index + 2 deep pages (Healthcare/Manufacturing) + `lib/industries.ts` | `pages/marketing/*`, `App.tsx` | L |
| **M2c — Resources, Trust, FAQ, Comparison** | M2.6–M2.9 — gated checklist + ROI calculator, `/security` trust centre, `/faq` accordion, `/compare/:c` matrix | `pages/marketing/*`, `App.tsx` | L |
| **M3 — SEO & polish** | M3.1–M3.4 — helmet, sitemap, stats, footer | `index.html`, `PublicLayout.tsx`, `sitemap.xml`, `robots.txt` | S |

Each batch: one commit, push to `main`, prod-verified (`/health` 200, frontend 200, `check:routes` + `check:design` + `verify` green). No batch blocks the next — M1 can ship alone and already fixes conversion.

---

## Route Map After (public)

```
/                          Homepage (rebuilt)
/platform                  Platform showcase (public) — was auth wall
/solutions                 Solutions by persona (HR/Finance/IT)
/solutions/company-size    By Company Size
/solutions/integrations   Integrations
/pricing                   Pricing tiers + matrix
/industries                Industries index (10 cards → detail)
/industries/:slug          Industry deep page (Healthcare, Manufacturing fully written; 8 coming soon)
/resources                 Resources funnel (checklist + ROI + Docs + Security + FAQ)
/resources/migration-checklist  Gated PDF (email gate)
/resources/roi-calculator  Interactive calculator
/security                  Trust Center
/faq                       FAQ accordion
/compare/:competitor       Comparison matrix
/about, /careers, /contact, /privacy, /terms, /docs  (existing, polished)
```

---

## Risks

| Risk | Mitigation |
|---|---|
| Public `/platform` collides with app `/platform` | Auth gate decides: anonymous → showcase, authenticated → app (check `isAuthenticated` in `Platform.tsx` or split to `/product` + redirect). Simplest: keep `/platform` public showcase, app stays at `/platform` behind `ProtectedRoute` — the showcase is the unauthenticated view of the same path, no route change. |
| No real screenshots yet | Use styled mock of `/people` + `/project-status` behind glass for now; replace with real screenshot when available. Placeholder is still better than the current fake gradient box. |
| Contact public endpoint needs backend | If backend not ready, wire to `Formspree`/`Loops`/`HubSpot` embed as interim — no auth, no 401. Swap to `POST /api/v1/contact` when backend lands. |
| Pricing numbers not decided | Ship `Contact sales` with `Starting at $X/employee/mo — includes Y modules` or `From $8/employee` range — showing a range is better than showing nothing. Owner decides numbers; page ships with placeholder and note. |
| Industry deep pages need domain expertise | Start with 2 fully written (Healthcare + Manufacturing), 8 as `Coming soon` with email capture — proves the pattern without blocking. |
| SEO helmet adds dep | `react-helmet-async` is 3 kB; alternative is `useEffect document.title` + meta — smaller, no dep. Recommend the latter for minimal footprint. |

---

## Verification

1. **M1:** `npm run verify` (now includes `check:design` + `check:routes` that flags public→protected links) green. Manual incognito: every public page link works, no login wall. `curl POST /api/v1/contact` returns 201 without auth. `curl /platform` returns 200 public showcase (not redirect to login).
2. **M2a–c:** Visual spot-check every public page at 360/768/1024/1440 (responsive), `check:routes` 11x→~130 routes, `check:design` green. Homepage hero outcome headline + proof strip with footnotes + preview screenshot + bento + logo wall + trust strip all render. Industry deep pages have `Pain → Workflow → Outcome` arc with regulation named.
3. **M3:** Per-page `<title>`/`description`/`og:image` unique, `sitemap.xml` lists only public routes, `robots.txt` consistent, JSON-LD valid (validator). No `text-gray-600` where `text-fg-muted` exists (already enforced by `check:design`).
4. **After each batch:** push to `main`, prod `/health` 200, frontend 200 with new bundle, `check:design` + `verify` green.

---

## What NOT In This Plan

- Backend `POST /api/v1/contact` is the only backend change (M1.2) — one endpoint, public, rate-limited. All other work is frontend.
- No new npm deps except optionally `react-helmet-async` (recommend `useEffect` instead — zero dep).
- No CMS/blog — Resources funnel uses 2 static gated assets + `changelog` link to `Documentation.tsx`.
- No comparison for all competitors — one fully written (BambooHR), others `Coming soon`.
- No pricing calculator backend — ROI calculator is client-side math (`employees × hours × rate`).
