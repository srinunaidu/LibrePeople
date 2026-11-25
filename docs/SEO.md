# Karmathy HCM — SEO & Pre-Launch Checklist (Phase T)

**Owner:** Frontend & Design. **Introduced:** 2026-10-28 (Phase T — marketing site rebuild).

---

## 1. Per-Page SEO Table

| URL | Title | Meta description | H1 | Primary keyword | OG image | Schema types |
|-----|-------|------------------|----|----|-----------|--------------|
| `/` | Run HR, payroll and scheduling in one place | Karmathy is a configurable HCM platform for the full employee lifecycle — recruiting, onboarding, time, leave, payroll, performance — with one record per person. Start your demo. | Run HR, payroll and scheduling in one place — onboard a new hire in 2 days, not 2 weeks. | HCM platform | `/og-image.png` | Organization, WebSite |
| `/platform` | Karmathy Platform — One system of record for HR, payroll & scheduling | Explore the Karmathy platform modules behind one continuous employee record: core HR, recruiting, onboarding, time, scheduling, leave, payroll, performance, benefits, learning and compliance. | (PlatformShowcase hero headline) | HCM platform modules | `/og-image.png` | SoftwareApplication |
| `/solutions` | Karmathy Solutions — HCM for every team size and industry | Configure Karmathy for your organisation — from a five-person team to a five-thousand-person enterprise — with role packs, rule packs and tenant data isolation built in. | Solutions | HCM configuration | `/og-image.png` | SoftwareApplication |
| `/industries` | Karmathy Industries — HCM built for your vertical | HR, scheduling and compliance workflows tuned for healthcare, manufacturing, retail, financial services, technology, logistics, education, professional services, hospitality and government teams. | Built for every industry | HCM for industry | `/og-image.png` | — |
| `/industries/{slug}` | Karmathy for {slug} — HR software built for your industry | See how Karmathy configures recruiting, time, scheduling, leave, payroll and compliance for {slug} teams. | {Industry name} | HCM for {slug} | `/og-image.png` | — |
| `/resources` | Karmathy Resources — HR, payroll and people-ops guides | Guides, benchmarks and implementation notes helping HR teams move from spreadsheets and legacy HRIS to a configurable workforce platform. | Resources | HR implementation guides | `/og-image.png` | — |
| `/pricing` | Karmathy Pricing — HCM from six dollars per employee | Per-employee pricing for core HR, time, leave and reporting. Add payroll, scheduling, performance and more as modules. Request a demo and get a scoped quote. | Simple pricing for every stage | HCM pricing | `/og-image.png` | SoftwareApplication (offers) |
| `/security` | Karmathy Security — enterprise-grade protection for HR data | Oracle Autonomous Database with mTLS, hash-chained audit trail, 300-plus role-based access controls and one-schema-per-tenant isolation for human capital data. | Security & Trust | HCM security | `/og-image.png` | — |
| `/faq` | Karmathy FAQ — HCM, payroll and migration questions answered | Answers on implementation, migration from legacy HRIS systems, payroll reconciliation and security. Still stuck? Contact the Karmathy team. | Frequently asked questions | HCM FAQ | `/og-image.png` | FAQPage |
| `/compare/{competitor}` | Karmathy vs {competitor} — compare HCM platforms | How Karmathy compares to {competitor} on lifecycle coverage, payroll reconciliation and implementation approach. | Karmathy vs {label} | HCM comparison | `/og-image.png` | — |
| `/about` | About Karmathy — the people-platform team | Karmathy builds one configurable platform for the full employee lifecycle — from first application to last day — so people ops runs on one honest system. | About Karmathy | — | `/og-image.png` | Organization, WebSite |
| `/careers` | Careers at Karmathy — build the workforce platform | Open engineering, product and people-ops roles at Karmathy. Build the platform that runs recruiting, payroll and scheduling for the organisations of tomorrow. | Careers at Karmathy | — | `/og-image.png` | — |
| `/contact` | Contact Karmathy — book a demo of the HCM platform | Request a demo or ask about implementation. Karmathy replies with a scoped plan tailored to your employee count and industry. | Contact Us | HCM demo request | `/og-image.png` | — |
| `/privacy` | Karmathy Privacy Policy — data protection and HR records | How Karmathy collects, uses, stores and protects human capital data, including employee records, payroll and hash-chained audit trails. | Privacy Policy | HR data privacy | `/og-image.png` | — |
| `/terms` | Karmathy Terms of Service — platform and contracts | Terms of service for the Karmathy HCM platform, including acceptable use, data processing and subscription terms. | Terms of Service | — | `/og-image.png` | — |
| `/docs` | Karmathy Documentation — API, modules and implementation guides | Technical documentation for Karmathy: API contracts, module setup, data model and integration guides for developers and administrators. | Documentation | HCM API docs | `/og-image.png` | — |

### SEO engine

- `frontend/src/lib/seo.ts` — `usePageSEO(pathname)` mounted from `PublicLayout`; resolves entries from
  the `PUBLIC_SEO` pattern map (static + `:param` keys), applies title / meta description / canonical /
  Open Graph / Twitter card / robots + JSON-LD.
- `frontend/index.html` — static defaults (title, description, OG, Twitter, theme-color) for the first
  paint before React hydrates.
- `frontend/public/og-image.png` — 1200×630 Open Graph image (Phase T).
- `frontend/public/sitemap.xml` — public marketing URLs only; app routes excluded.
- `frontend/public/robots.txt` — public marketing allowed, authenticated app surface disallowed.

---

## 2. Content Rules (Phase T)

- Unique title per page, 50–60 characters, primary keyword first, brand last.
- Unique meta description, 145–160 characters, benefit + call to action.
- One H1 per page matching search intent; H2/H3 in logical order.
- Clean lowercase hyphenated URLs; keep existing URLs working with 301 redirects for any changes.
- Self-referencing canonical on every page, production domain.
- Open Graph and Twitter Card tags, unique 1200×630 og:image per page.
- Images in WebP or AVIF, lazy-loaded below the fold, width and height set to prevent layout shift.
- JSON-LD: Organization and WebSite site-wide; SoftwareApplication on product pages; BreadcrumbList on
  inner pages; FAQPage where an FAQ appears; Article on blog posts.
- XML sitemap and robots.txt.
- Internal links between related modules with descriptive anchor text.

## 3. Performance (Phase T)

- Inline critical CSS for the hero. Defer the thread's JavaScript if it has any. Avoid loading animation
  libraries for effects CSS can handle.
- Server-render or pre-render all marketing pages so content is visible without JavaScript.

## 4. Pre-Launch Checklist

- [ ] Lighthouse: LCP < 2.5s, CLS < 0.1, INP < 200ms on all marketing pages
- [ ] Rich Results Test: passes for Organization / WebSite / SoftwareApplication / FAQPage
- [ ] WAVE accessibility scan: no critical violations on public pages
- [ ] Reduced-motion check: thread shows final state, no animation
- [ ] Mobile: thread becomes vertical; cards stack; tap targets ≥ 44px
- [ ] Keyboard: full navigation, visible focus rings, skip-to-content present
- [ ] Contrast: WCAG 2.2 AA on all marketing surfaces (thread blue #2563EB vs white)
- [ ] Sitemap submitted; robots.txt verified; canonicals unique
- [ ] 404 page: broken thread, stops at missing node, links back home + modules
- [ ] Login: minimal, centred, no navigation distractions

---

*Phase T scope note: the authenticated app shell keeps its own document titles; this checklist covers
the public marketing surface.*
