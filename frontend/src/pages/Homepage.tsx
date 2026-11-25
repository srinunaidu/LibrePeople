import { Link } from "react-router-dom"
import { PublicLayout } from "@/components/PublicLayout"
import { ThreadDark, Network } from "@/components/marketing/Artwork"
import { ProductMockup } from "@/components/marketing/ProductMockup"
import { THREAD_STAGES } from "@/lib/designSystem"

const FEATURES: { title: string; desc: string; accent: string; icon: string; span: string }[] = [
  {
    title: "Single source of truth",
    desc: "Cut reconciliation work — one employee record, every module reads it. No duplicate spreadsheets, no drift.",
    accent: "icon-tile-brand",
    icon: "◈",
    span: "lg:col-span-2",
  },
  {
    title: "Automate approvals",
    desc: "Approve leave in one click. Configurable chains route by role, location and policy — not inbox spelunking.",
    accent: "icon-tile-teal",
    icon: "✓",
    span: "lg:col-span-2",
  },
  {
    title: "Reduce payroll errors",
    desc: "Reconcile every run against the rule pack before you pay. Net matches calculation — with a paper trail.",
    accent: "icon-tile-green",
    icon: "≡",
    span: "",
  },
  {
    title: "Onboard in 2 days, not 2 weeks",
    desc: "Reusable checklists and e-signatures automate offer, documents and day-one tasks.",
    accent: "icon-tile-violet",
    icon: "↗",
    span: "",
  },
  {
    title: "Audit-ready by default",
    desc: "Every action logged — who did what, when, on which record. Export the trail on demand.",
    accent: "icon-tile-amber",
    icon: "◎",
    span: "",
  },
  {
    title: "Migrate in minutes",
    desc: "CSV import/export for every entity. Leave Bamboo, ADP or spreadsheets without a services engagement.",
    accent: "icon-tile-slate",
    icon: "⇄",
    span: "",
  },
]

const MODULES: { title: string; desc: string; icon: string; accent: string; hash: string }[] = [
  { title: "Core HR", desc: "One record per person — positions, departments and history in sync.", icon: "◈", accent: "icon-tile-brand", hash: "corehr" },
  { title: "Payroll", desc: "Cut payroll errors — rule-pack reconciliation and payslip traceability.", icon: "₵", accent: "icon-tile-brand", hash: "payroll" },
  { title: "Performance", desc: "Ensure fairness — goals, reviews, 360° and compensation bands.", icon: "⬢", accent: "icon-tile-violet", hash: "performance" },
  { title: "Benefits", desc: "Plans, eligibility, enrolment windows and life events.", icon: "✚", accent: "icon-tile-green", hash: "benefits" },
  { title: "Learning", desc: "Courses, certifications, talent pools and succession.", icon: "▤", accent: "icon-tile-slate", hash: "learning" },
  { title: "Integrations", desc: "REST API, HMAC webhooks, SSO config, SFTP and CSV bulk flows.", icon: "⇄", accent: "icon-tile-teal", hash: "integrations" },
  { title: "Compliance", desc: "Hash-chained audit trail, RBAC and headcount scenarios.", icon: "⬢", accent: "icon-tile-brand", hash: "compliance" },
  { title: "Import / Export", desc: "CSV import/export for every entity — migrate without a services engagement.", icon: "⇅", accent: "icon-tile-amber", hash: "importexport" },
]

const INDUSTRIES: { name: string; pain: string; icon: string; slug: string }[] = [
  { name: "Manufacturing", pain: "Roster coverage across shifts and plants.", icon: "⬣", slug: "manufacturing" },
  { name: "Healthcare", pain: "Credential tracking and shift compliance.", icon: "+", slug: "healthcare" },
  { name: "Retail", pain: "High-volume hiring and seasonal scheduling.", icon: "◈", slug: "retail" },
  { name: "Financial Services", pain: "Audit trail and access controls.", icon: "⬢", slug: "financial-services" },
  { name: "Technology", pain: "Fast onboarding and performance cycles.", icon: "◆", slug: "technology" },
  { name: "Logistics", pain: "Time capture across sites and routes.", icon: "⇄", slug: "logistics" },
  { name: "Education", pain: "Term-based contracts and leave policies.", icon: "◎", slug: "education" },
  { name: "Professional Services", pain: "Utilisation, leave and project staffing.", icon: "▦", slug: "professional-services" },
  { name: "Hospitality", pain: "Rostering, swaps and tip-adjacent pay.", icon: "☾", slug: "hospitality" },
  { name: "Government", pain: "Compliance, headcount plans and scenarios.", icon: "▤", slug: "government" },
]

const STAGE_LINKS: Record<string, string> = {
  recruit: "/recruiting",
  onboard: "/onboarding",
  time: "/time",
  leave: "/leave",
  pay: "/platform/payroll",
  perform: "/platform/performance",
  grow: "/platform/learning",
  offboard: "/offboarding",
}

const MARQUEE = [
  "One record per person",
  "Hash-chained audit trail",
  "Ledger-derived leave balances",
  "Reconciled payroll runs",
  "Payslip drill-down",
  "Roster → publish → swap",
  "Cross-midnight shifts",
  "HMAC-signed webhooks",
  "Dry-run CSV import",
  "RBAC — 300+ operations",
  "Certification expiry tracking",
  "Auto-generated employee keys",
]

export default function Homepage() {
  return (
    <PublicLayout>
      {/* ══ HERO ═════════════════════════════════════════════════════════ */}
      <section className="relative overflow-hidden">
        {/* aurora mesh */}
        <div
          aria-hidden="true"
          className="absolute inset-0"
          style={{
            backgroundImage:
              "radial-gradient(1100px 560px at 18% -12%, rgba(37,99,235,0.38), transparent 62%), radial-gradient(880px 480px at 88% 4%, rgba(34,211,238,0.16), transparent 60%), radial-gradient(760px 440px at 52% 100%, rgba(139,92,246,0.15), transparent 65%)",
          }}
        />
        <div aria-hidden="true" className="mk-grid absolute inset-0" />
        <div aria-hidden="true" className="mk-noise absolute inset-0 opacity-[0.05]" />

        <div className="relative max-w-container mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-16 md:pt-28 md:pb-20">
          {/* centered display headline */}
          <div className="mx-auto max-w-4xl text-center">
            <span className="mk-eyebrow mk-reveal">
              <span className="mk-pulse inline-block h-1.5 w-1.5 rounded-full bg-teal-300" aria-hidden="true" />
              HCM platform for teams that outgrew spreadsheets
            </span>

            <h1 className="mt-7 mk-h1 mk-reveal">
              <span className="mk-gradient-text">Run HR, payroll and scheduling</span>
              <br />
              <span className="text-white">in one place.</span>
              <span className="block mt-3 text-fg-muted" style={{ fontSize: "clamp(1.05rem, 2vw, 1.35rem)", fontWeight: 500, letterSpacing: "0" }}>
                One record per person — onboard a new hire in 2 days, not 2 weeks.
              </span>
            </h1>

            <ul className="mt-7 flex flex-wrap justify-center gap-x-6 gap-y-2 text-sm text-fg-muted mk-reveal mk-reveal-d1">
              {[
                "Cut payroll errors with reconciliation",
                "Approve leave in one click",
                "Migrate from Bamboo/ADP via CSV in minutes",
              ].map((t) => (
                <li key={t} className="flex items-center gap-2">
                  <span className="h-1 w-1 rounded-full bg-brand-400" aria-hidden="true" />
                  {t}
                </li>
              ))}
            </ul>

            <div className="mt-10 flex flex-wrap justify-center gap-3 mk-reveal mk-reveal-d1">
              <Link to="/contact" className="mk-cta">
                Request a demo
                <span aria-hidden="true">→</span>
              </Link>
              <Link to="/platform" className="mk-ghost">
                Watch 2-min tour
              </Link>
            </div>
          </div>

          {/* floating product mockup */}
          <div className="mt-16 mk-reveal mk-reveal-d2">
            <ProductMockup />
          </div>

          {/* proof strip */}
          <div className="mt-16 mk-reveal">
            <div className="flex flex-wrap items-end justify-center gap-x-12 gap-y-6">
              <div>
                <div className="text-[var(--font-size-3xl)] md:text-[var(--font-size-4xl)] font-bold tracking-tight text-white tabular-nums" style={{ fontFamily: "var(--font-display)" }}>
                  12<span className="mk-gradient-blue"> modules live</span>
                </div>
                <div className="text-xs text-fg-muted mt-1">
                  Core HR → reporting, one record.{" "}
                  <Link to="/about" className="underline decoration-white/30 underline-offset-4 hover:text-fg">
                    How we count →
                  </Link>
                </div>
              </div>
              <div className="border-l border-white/10 pl-6 md:border-t-0">
                <div className="text-[var(--font-size-3xl)] md:text-[var(--font-size-4xl)] font-bold tracking-tight text-white" style={{ fontFamily: "var(--font-display)" }}>
                  &lt; 2 days
                </div>
                <div className="text-xs text-fg-muted mt-1">Typical onboarding with checklists + e-sign.</div>
              </div>
              <div className="border-l border-white/10 pl-6">
                <div className="text-[var(--font-size-3xl)] md:text-[var(--font-size-4xl)] font-bold tracking-tight text-white" style={{ fontFamily: "var(--font-display)" }}>
                  0.4%
                </div>
                <div className="text-xs text-fg-muted mt-1">Illustrative — the variance a reconciled run reports.</div>
              </div>
            </div>
          </div>
        </div>

        {/* capability marquee */}
        <div className="relative border-y border-white/[0.07] bg-[rgba(248,250,252,0.02)] py-4">
          <div className="mk-marquee" aria-hidden="false">
            <div className="mk-marquee-track">
              {[...MARQUEE, ...MARQUEE].map((label, i) => (
                <span key={`${label}-${i}`} className="mk-chip" aria-hidden={i >= MARQUEE.length}>
                  <span className="mk-chip-dot" style={i % 3 === 1 ? { background: "var(--teal-300)", boxShadow: "0 0 8px rgba(103,232,249,0.9)" } : i % 3 === 2 ? { background: "var(--violet-300)", boxShadow: "0 0 8px rgba(196,181,253,0.9)" } : undefined} />
                  {label}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* the thread — lifecycle deep links */}
        <div className="relative max-w-container mx-auto px-4 sm:px-6 lg:px-8 pt-10 pb-14">
          <div className="mk-reveal">
            <p className="text-center mk-kicker">The employee thread — click any stage</p>
            <ol className="mt-6 flex flex-wrap justify-center items-center gap-x-1 gap-y-3">
              {THREAD_STAGES.map((stage, i) => (
                <li key={stage.id} className="flex items-center gap-1">
                  <Link
                    to={STAGE_LINKS[stage.id] ?? "/platform"}
                    className="mk-chip hover:border-brand-200 hover:text-fg transition-colors"
                  >
                    <span className="text-fg-subtle tabular-nums">{i + 1}</span>
                    {stage.label}
                  </Link>
                  {i < THREAD_STAGES.length - 1 && (
                    <span aria-hidden="true" className="text-fg-subtle">
                      →
                    </span>
                  )}
                </li>
              ))}
            </ol>
          </div>
        </div>
      </section>

      {/* ══ BENTO FEATURES ═══════════════════════════════════════════════ */}
      <section className="max-w-container mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-28">
        <div className="max-w-2xl mk-reveal">
          <p className="mk-kicker">Why Karmathy</p>
          <h2 className="mt-2 mk-h2 text-white">The complete HCM platform — without the enterprise freight</h2>
          <p className="mt-4 text-body text-fg-muted">
            Six outcomes buyers ask for. Each one maps to a real module you can try today — not a roadmap promise.
          </p>
        </div>
        <div className="mt-12 grid grid-cols-1 lg:grid-cols-4 gap-5 lg:gap-6">
          {FEATURES.map((f) => (
            <div key={f.title} className={`mk-card mk-reveal p-6 flex flex-col ${f.span} group`}>
              <div className={`icon-tile ${f.accent} group-hover:scale-105 transition-transform`} aria-hidden="true">
                <span className="text-base font-bold">{f.icon}</span>
              </div>
              <h3 className="mt-4 text-[var(--font-size-lg)] font-semibold tracking-tight text-white">{f.title}</h3>
              <p className="mt-2 text-body-sm text-fg-muted leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ══ MODULES BENTO ════════════════════════════════════════════════ */}
      <section id="modules" className="relative py-20 lg:py-28 border-y border-white/[0.06] bg-[rgba(248,250,252,0.015)]">
        <div className="max-w-container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-end justify-between gap-4 mb-10 mk-reveal">
            <div className="max-w-2xl">
              <p className="mk-kicker">Modules</p>
              <h2 className="mt-2 mk-h2 text-white">Eight modules that cover the lifecycle</h2>
              <p className="mt-3 text-body-sm text-fg-muted">Curated from 12 live — every card deep-links to its section on the platform.</p>
            </div>
            <Link to="/platform" className="mk-link shrink-0">
              View all 12 →
            </Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 lg:gap-6">
            {MODULES.map((m) => (
              <Link key={m.title} to={`/platform#${m.hash}`} className="mk-card mk-reveal p-5 flex flex-col group">
                <div className="flex items-start justify-between gap-3">
                  <span className={`icon-tile ${m.accent}`} aria-hidden="true">
                    <span className="text-sm font-bold">{m.icon}</span>
                  </span>
                  <span className="text-brand-400 group-hover:translate-x-0.5 transition-transform" aria-hidden="true">
                    →
                  </span>
                </div>
                <h3 className="mt-4 font-semibold text-white text-base tracking-tight">{m.title}</h3>
                <p className="mt-1.5 text-xs leading-relaxed text-fg-muted flex-1">{m.desc}</p>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ══ INDUSTRIES ═══════════════════════════════════════════════════ */}
      <section className="max-w-container mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-28">
        <div className="max-w-2xl mb-10 mk-reveal">
          <p className="mk-kicker">Industries</p>
          <h2 className="mt-2 mk-h2 text-white">Built for every industry — configured for yours</h2>
          <p className="mt-3 text-body-sm text-fg-muted">Each card names the pain we solve most often in that sector.</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-5">
          {INDUSTRIES.map((ind) => (
            <Link key={ind.name} to={`/industries/${ind.slug}`} className="mk-card mk-reveal p-5 flex flex-col group">
              <span className={`icon-tile ${ind.slug === "healthcare" ? "icon-tile-brand" : "icon-tile-slate"}`} aria-hidden="true">
                <span className="text-xs font-bold">{ind.icon}</span>
              </span>
              <h3 className="mt-3 font-semibold text-white text-sm tracking-tight">{ind.name}</h3>
              <p className="mt-1 text-xs leading-relaxed text-fg-muted flex-1">{ind.pain}</p>
              <span className="mt-3 text-xs font-semibold text-brand-400 group-hover:underline">Explore →</span>
            </Link>
          ))}
        </div>
      </section>

      {/* ══ INTEGRATIONS — capability wall ═══════════════════════════════ */}
      <section id="integrations" className="relative py-20 lg:py-28 border-y border-white/[0.06] bg-[rgba(248,250,252,0.015)]">
        <div className="max-w-container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-10 lg:gap-12 items-start">
            <div className="mk-reveal">
              <p className="mk-kicker">Integrations &amp; extensibility</p>
              <h2 className="mt-2 mk-h2 text-white">An integration layer, not a locked box</h2>
              <p className="mt-4 text-body-sm text-fg-muted">
                Bulk CSV for migration, a full REST API for real-time, HMAC-signed webhook subscriptions for events,
                SSO via SAML/OIDC/OAuth2 configuration, and SFTP + mTLS to Oracle Autonomous Database. We name
                capabilities, not partners — connection work happens with a scoped plan, not a marquee.
              </p>
              <div className="mt-6 flex flex-wrap gap-2">
                {["REST API", "CSV import/export", "HMAC webhooks", "SSO config", "SFTP", "Oracle ADB mTLS"].map((p) => (
                  <span key={p} className="mk-chip">
                    <span className="mk-chip-dot" aria-hidden="true" />
                    {p}
                  </span>
                ))}
              </div>
              <div className="mt-6 flex flex-wrap gap-4">
                <Link to="/docs" className="mk-link">
                  View integrations →
                </Link>
                <Link to="/security" className="text-sm font-medium text-fg-muted hover:text-fg">
                  Security posture
                </Link>
              </div>
            </div>
            <div className="mk-card mk-card-flat mk-reveal mk-reveal-d1 p-6">
              <Network className="w-full h-32 -mx-2" />
              <div className="grid grid-cols-2 gap-3 mt-2">
                {[
                  "Oracle ADB (mTLS)",
                  "REST APIs",
                  "SFTP",
                  "CSV import/export",
                  "HMAC-signed webhooks",
                  "SSO (SAML/OIDC/OAuth2)",
                  "E-signature records",
                  "Encrypted secrets at rest",
                ].map((label) => (
                  <div key={label} className="rounded-lg bg-page border border-border px-3 py-3 text-center text-xs font-medium text-fg-muted">
                    {label}
                  </div>
                ))}
              </div>
              <p className="mt-4 text-xs text-fg-subtle text-center">
                Delivery log for every webhook · secrets encrypted, never logged · scoped connection plan on enterprise
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ══ SECURITY — trust strip ═══════════════════════════════════════ */}
      <section className="max-w-container mx-auto px-4 sm:px-6 lg:px-8 py-14">
        <div className="mk-card mk-reveal p-6 lg:p-8">
          <div className="flex flex-col lg:flex-row lg:items-center gap-6 lg:gap-8">
            <div className="shrink-0">
              <p className="mk-kicker">Security &amp; compliance</p>
              <h2 className="mt-1 text-[var(--font-size-xl)] font-bold tracking-tight text-white">Trust, stated honestly</h2>
            </div>
            <div className="flex flex-wrap gap-2">
              {["Data isolation", "RBAC", "mTLS", "Encrypted"].map((b) => (
                <span key={b} className="mk-chip">
                  <span className="mk-chip-dot" aria-hidden="true" />
                  {b}
                </span>
              ))}
            </div>
            <p className="text-sm text-fg-muted lg:ml-auto">
              Controls operating today · certifications in progress{" "}
              <Link to="/security" className="mk-link">
                → the honest security posture
              </Link>
            </p>
          </div>
        </div>
      </section>

      {/* ══ RESOURCES ════════════════════════════════════════════════════ */}
      <section className="max-w-container mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-28">
        <div className="flex flex-wrap items-end justify-between gap-4 mb-10 mk-reveal">
          <div>
            <p className="mk-kicker">Resources</p>
            <h2 className="mt-2 mk-h2 text-white">Trade an email for the good stuff</h2>
            <p className="mt-3 text-body-sm text-fg-muted">Gated assets for buyers doing due diligence — plus open docs.</p>
          </div>
          <Link to="/resources" className="mk-link shrink-0">
            All resources →
          </Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 lg:gap-6">
          {[
            { to: "/contact", badge: "PDF · email gate", badgeClass: "badge-amber", title: "HCM Migration Checklist", desc: "The 30-point list we use with every CSV migration — fields, validations and rollback plan.", cta: "Get the checklist →" },
            { to: "/contact", badge: "Interactive teaser", badgeClass: "badge-teal", title: "Hidden cost of spreadsheets", desc: "ROI calculator — estimate hours lost to manual payroll, leave and roster fixes.", cta: "Try the calculator →" },
            { to: "/docs", badge: "Open", badgeClass: "badge-brand", title: "API Documentation", desc: "Full REST reference — every endpoint, auth and webhook. No gate, just docs.", cta: "Open API docs →" },
          ].map((r) => (
            <Link key={r.title} to={r.to} className="mk-card mk-reveal p-6 flex flex-col group">
              <span className={`badge text-xs w-fit ${r.badgeClass}`} >
                {r.badge}
              </span>
              <h3 className="mt-4 font-semibold text-white">{r.title}</h3>
              <p className="mt-2 text-body-sm text-fg-muted flex-1">{r.desc}</p>
              <span className="mt-4 text-sm font-semibold text-brand-400 group-hover:underline">{r.cta}</span>
            </Link>
          ))}
        </div>
      </section>

      {/* ══ FINAL CTA ════════════════════════════════════════════════════ */}
      <section className="relative overflow-hidden border-t border-white/[0.06]">
        <ThreadDark className="absolute inset-0 h-full w-full" aria-hidden="true" />
        <div
          aria-hidden="true"
          className="absolute inset-0"
          style={{
            backgroundImage:
              "radial-gradient(800px 400px at 20% 0%, rgba(37,99,235,0.30), transparent 60%), linear-gradient(transparent 30%, rgba(6,11,21,0.9) 95%)",
          }}
        />
        <div className="mk-noise absolute inset-0 opacity-[0.04]" aria-hidden="true" />
        <div className="relative max-w-container mx-auto px-4 sm:px-6 lg:px-8 py-24 lg:py-32 text-center">
          <h2 className="mk-h1 text-white !text-[clamp(2rem,4.6vw,3.4rem)]">
            Ready to run HR <span className="mk-gradient-blue">without spreadsheets?</span>
          </h2>
          <p className="mt-4 text-body-sm text-fg-muted max-w-2xl mx-auto">Talk to the founding team — we reply within 1 business day.</p>
          <div className="mt-9 flex flex-wrap justify-center gap-3">
            <Link to="/contact" className="mk-cta">
              Request a demo
              <span aria-hidden="true">→</span>
            </Link>
            <Link to="/pricing" className="mk-ghost">
              See pricing
            </Link>
          </div>
          <p className="mt-6 text-xs text-fg-subtle">No credit card · CSV migration support included · Cancel anytime</p>
        </div>
      </section>
    </PublicLayout>
  )
}
