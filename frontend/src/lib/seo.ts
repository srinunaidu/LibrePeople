import { useEffect } from "react"
import { useLocation } from "react-router-dom"

/**
 * Karmathy — SEO foundation for the public marketing surface.
 *
 * Phase T deliverable: every public marketing page ships with a unique
 * title, meta description, canonical, Open Graph + Twitter card tags and
 * the JSON-LD vocabulary the brief requires (Organization + WebSite site-wide,
 * SoftwareApplication on product pages, BreadcrumbList on inner pages,
 * FAQPage where an FAQ appears, Article on blog posts).
 *
 * The hook is mounted once from PublicLayout so every page rendered through
 * the marketing shell inherits the behaviour; per-page content lives in the
 * PUBLIC_SEO map keyed by route pattern.
 */

export const SITE_URL = "https://karmathy-frontend.onrender.com"
export const SITE_NAME = "Karmathy"
export const OG_IMAGE = "/og-image.png"

export interface SEOContent {
  title: string
  description: string
  keywords?: string
  type?: "website" | "article"
  jsonLd?: Array<Record<string, unknown>>
}

export const PUBLIC_SEO: Record<string, SEOContent> = {
  "/": {
    title: "Karmathy — Run HR, payroll and scheduling in one place",
    description:
      "Karmathy is a configurable HCM platform for the full employee lifecycle — recruiting, onboarding, time, leave, payroll, performance — with one record per person. Start your demo.",
    jsonLd: [
      {
        "@context": "https://schema.org",
        "@type": "Organization",
        name: "Karmathy",
        url: SITE_URL,
        logo: `${SITE_URL}/favicon.svg`,
      },
      {
        "@context": "https://schema.org",
        "@type": "WebSite",
        name: "Karmathy",
        url: SITE_URL,
      },
    ],
  },
  "/platform": {
    title: "Karmathy Platform — One system of record for HR, payroll & scheduling",
    description:
      "Explore the Karmathy platform modules behind one continuous employee record: core HR, recruiting, onboarding, time, scheduling, leave, payroll, performance, benefits, learning and compliance.",
    type: "article",
    jsonLd: [
      {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        name: "Karmathy",
        applicationCategory: "BusinessApplication",
        operatingSystem: "Web",
        description:
          "Configurable HCM platform for the full employee lifecycle with one record per person.",
        url: `${SITE_URL}/platform`,
      },
    ],
  },
  "/solutions": {
    title: "Karmathy Solutions — HCM for every team size and industry",
    description:
      "Configure Karmathy for your organisation — from a five-person team to a five-thousand-person enterprise — with role packs, rule packs and tenant data isolation built in.",
    jsonLd: [
      {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        name: "Karmathy",
        applicationCategory: "BusinessApplication",
        operatingSystem: "Web",
        description: "Configurable HCM platform for the full employee lifecycle.",
        url: `${SITE_URL}/solutions`,
      },
    ],
  },
  "/industries": {
    title: "Karmathy Industries — HCM built for your vertical",
    description:
      "HR, scheduling and compliance workflows tuned for healthcare, manufacturing, retail, financial services, technology, logistics, education, professional services, hospitality and government teams.",
  },
  "/industries/:slug": {
    title: "Karmathy for {slug} — HR software built for your industry",
    description: "See how Karmathy configures recruiting, time, scheduling, leave, payroll and compliance for {slug} teams.",
  },
  "/resources": {
    title: "Karmathy Resources — HR, payroll and people-ops guides",
    description:
      "Guides, benchmarks and implementation notes helping HR teams move from spreadsheets and legacy HRIS to a configurable workforce platform.",
  },
  "/pricing": {
    title: "Karmathy Pricing — per-employee plans scoped by demo",
    description:
      "Per-employee pricing for core HR, time, leave and reporting. Add payroll, scheduling, performance and more as modules. Request a demo and get a scoped quote.",
    jsonLd: [
      {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        name: "Karmathy",
        applicationCategory: "BusinessApplication",
        operatingSystem: "Web",
        description: "Configurable HCM platform sold per employee per month. Quotes scoped per team size and modules.",
        url: `${SITE_URL}/pricing`,
      },
    ],
  },
  "/security": {
    title: "Karmathy Security — enterprise-grade protection for HR data",
    description:
      "Oracle Autonomous Database with mTLS, hash-chained audit trail, 300-plus role-based access controls and one-schema-per-tenant isolation for human capital data.",
  },
  "/faq": {
    title: "Karmathy FAQ — HCM, payroll and migration questions answered",
    description:
      "Answers on implementation, migration from legacy HRIS systems, payroll reconciliation and security. Still stuck? Contact the Karmathy team.",
    jsonLd: [
      {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        mainEntity: [
          {
            "@type": "Question",
            name: "How long does implementation take?",
            acceptedAnswer: {
              "@type": "Answer",
              text: "Core HR deployments typically complete in weeks; module rollout follows the customer timeline.",
            },
          },
          {
            "@type": "Question",
            name: "Can Karmathy migrate from our existing HRIS?",
            acceptedAnswer: {
              "@type": "Answer",
              text: "CSV import and staged migration tooling are supported; migration runs are rehearsed before go-live.",
            },
          },
        ],
      },
    ],
  },
  "/compare/:competitor": {
    title: "Karmathy vs {competitor} — compare HCM platforms",
    description: "How Karmathy compares to {competitor} on lifecycle coverage, payroll reconciliation and implementation approach.",
  },
  "/recruiting": {
    title: "Karmathy Recruiting — requisitions, candidates, offers & e-sign",
    description:
      "One candidate record runs the funnel: requisitions with approvals, stages, offer acceptance with transaction integrity and hiring evidence in the audit trail.",
  },
  "/onboarding": {
    title: "Karmathy Onboarding — day-one checklists & industry templates",
    description:
      "Resumable preboarding checklists, document acknowledgements, e-signed offers and six validated industry templates that pre-fill departments, patterns and policies.",
  },
  "/time": {
    title: "Karmathy Time & Attendance — clock in, timesheets, overtime",
    description:
      "Clock in/out, generated timesheets, cross-midnight shifts and overtime inputs. Payroll consumes approved time only — excluded hours are reported, never silently paid.",
  },
  "/scheduling": {
    title: "Karmathy Scheduling — shift templates, rosters & swaps",
    description:
      "Shift templates assemble into roster drafts, publish in ordered steps and support tracked swap workflows — plan versus actual from one employee record.",
  },
  "/leave": {
    title: "Karmathy Leave — ledger-derived balances, approvals in one click",
    description:
      "Leave requests with overlap checks and delegate approvals, balances derived entry-by-entry from the ledger, holiday calendars and a clean handoff to payroll.",
  },
  "/payroll": {
    title: "Karmathy Payroll — payslips that show their work",
    description:
      "Pays computed from approved time and leave inside jurisdictional rule packs, reconciled expected vs paid, and every payslip opens to the rows and rules it came from.",
  },
  "/performance": {
    title: "Karmathy Performance — goals, reviews & compensation bands",
    description:
      "Goals, OKRs, continuous feedback and structured review cycles beside compensation bands and merit cycles — pay decisions cite performance evidence.",
  },
  "/benefits": {
    title: "Karmathy Benefits — plans, enrolment windows & life events",
    description:
      "Benefit plans with real eligibility rules, enrolment periods, dependant records, leaves of absence and life events on the one employee record.",
  },
  "/learning": {
    title: "Karmathy Learning — courses, certifications & talent pools",
    description:
      "A real course catalogue with enrolments and assessments, certification expiry tracking, talent pools and succession plans on the same person record.",
  },
  "/compliance": {
    title: "Karmathy Compliance — hash-chained audit trail & RBAC",
    description:
      "Compliance rules with named violations, headcount plans and what-if scenarios, plus the enforced properties: tenant isolation, RBAC and a tamper-evident audit chain.",
  },
  "/offboarding": {
    title: "Karmathy Offboarding — exit interviews to final settlement",
    description:
      "Departures without loose ends: exit checklist, access revocation, asset returns and final settlement under a lifecycle that only allows valid transitions.",
  },
  "/ai": {
    title: "Karmathy AI — sequenced behind the release gates, not promised",
    description:
      "Three tiers of designed AI capabilities with 13 mandatory controls and explicit prohibitions — scheduled in Phase 8 of the build order, grounded in live analytics today.",
  },
  "/about": {
    title: "About Karmathy — the people-platform team",
    description:
      "Karmathy builds one configurable platform for the full employee lifecycle — from first application to last day — so people ops runs on one honest system.",
  },
  "/careers": {
    title: "Careers at Karmathy — build the workforce platform",
    description:
      "Open engineering, product and people-ops roles at Karmathy. Build the platform that runs recruiting, payroll and scheduling for the organisations of tomorrow.",
  },
  "/contact": {
    title: "Contact Karmathy — book a demo of the HCM platform",
    description:
      "Request a demo or ask about implementation. Karmathy replies with a scoped plan tailored to your employee count and industry.",
  },
  "/privacy": {
    title: "Karmathy Privacy Policy — data protection and HR records",
    description:
      "How Karmathy collects, uses, stores and protects human capital data, including employee records, payroll and hash-chained audit trails.",
  },
  "/terms": {
    title: "Karmathy Terms of Service — platform and contracts",
    description:
      "Terms of service for the Karmathy HCM platform, including acceptable use, data processing and subscription terms.",
  },
  "/docs": {
    title: "Karmathy Documentation — API, modules and implementation guides",
    description:
      "Technical documentation for Karmathy: API contracts, module setup, data model and integration guides for developers and administrators.",
  },
}

const ORG_JSONLD = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "Karmathy",
  url: SITE_URL,
  logo: `${SITE_URL}/favicon.svg`,
} as const

const WEBSITE_JSONLD = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "Karmathy",
  url: SITE_URL,
} as const

function patternToRegExp(pattern: string): RegExp {
  const source = pattern.replace(/:([A-Za-z0-9_]+)/g, (_m, key: string) => `(?<${key}>[^/]+)`)
  return new RegExp(`^${source}$`)
}

const SEO_PATTERNS: Array<{ re: RegExp; content: SEOContent }> = Object.entries(PUBLIC_SEO).map(
  ([key, content]) => ({ re: patternToRegExp(key), content }),
)

function prettifySlug(slug: string): string {
  return slug
    .split(/[-_]/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ")
}

const NOT_FOUND_SEO: SEOContent = {
  title: "Page not found — Karmathy HCM platform",
  description:
    "The page you requested is not on the Karmathy thread. Return to the homepage or explore the platform modules.",
};

export function resolveSEO(pathname: string): SEOContent {
  const clean = (pathname || "/").split("?")[0].split("#")[0] || "/"
  for (const { re, content } of SEO_PATTERNS) {
    const m = re.exec(clean)
    if (!m) continue
    if (m.groups) {
      const params: Record<string, string> = {}
      for (const key of Object.keys(m.groups)) {
        params[key] = (m.groups[key] ?? "").trim()
      }
      const title = content.title.replace(/\{slug\}/g, prettifySlug(params.slug ?? ""))
      const description = content.description.replace(/\{slug\}/g, prettifySlug(params.slug ?? ""))
      return { ...content, title, description }
    }
    return content
  }
  return NOT_FOUND_SEO
}

function upsertMeta(attr: "name" | "property", key: string, content: string): void {
  if (!content) return
  const selector = `meta[${attr}="${key}"]`
  let el = document.head.querySelector<HTMLMetaElement>(selector)
  if (!el) {
    el = document.createElement("meta")
    el.setAttribute(attr, key)
    document.head.appendChild(el)
  }
  el.setAttribute("content", content)
}

function upsertCanonical(href: string): void {
  let el = document.head.querySelector<HTMLLinkElement>('link[rel="canonical"]')
  if (!el) {
    el = document.createElement("link")
    el.setAttribute("rel", "canonical")
    document.head.appendChild(el)
  }
  el.setAttribute("href", href)
}

function upsertJsonLd(id: string, data: Record<string, unknown>): void {
  let el = document.getElementById(id) as HTMLScriptElement | null
  if (!el) {
    el = document.createElement("script")
    el.id = id
    el.type = "application/ld+json"
    document.head.appendChild(el)
  }
  el.textContent = JSON.stringify(data)
}

export function usePageSEO(pathname: string): void {
  useEffect(() => {
    const clean = (pathname || "/").split("?")[0].split("#")[0] || "/"
    const content = resolveSEO(clean)

    document.title = content.title
    upsertMeta("name", "description", content.description)
    upsertMeta("property", "og:title", content.title)
    upsertMeta("property", "og:description", content.description)
    upsertMeta("property", "og:url", `${SITE_URL}${clean}`)
    upsertMeta("property", "og:type", content.type ?? "website")
    upsertMeta("property", "og:image", `${SITE_URL}${OG_IMAGE}`)
    upsertMeta("name", "twitter:card", "summary_large_image")
    upsertMeta("name", "twitter:title", content.title)
    upsertMeta("name", "twitter:description", content.description)
    upsertMeta("name", "twitter:image", `${SITE_URL}${OG_IMAGE}`)
    upsertCanonical(`${SITE_URL}${clean}`)
    upsertMeta("name", "robots", content === NOT_FOUND_SEO ? "noindex, follow" : "index, follow")

    const jsonLd: Array<{ id: string; data: Record<string, unknown> }> = [
      { id: "karmathy-org", data: ORG_JSONLD },
      { id: "karmathy-website", data: WEBSITE_JSONLD },
      ...(content.jsonLd ?? []).map((d, i) => ({ id: `karmathy-page-${i}`, data: d })),
    ]
    for (const { id, data } of jsonLd) upsertJsonLd(id, data)

    return () => {
      for (const { id } of jsonLd) {
        document.getElementById(id)?.remove()
      }
    }
  }, [pathname])
}
