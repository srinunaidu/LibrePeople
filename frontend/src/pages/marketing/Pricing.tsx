import { Link } from "react-router-dom"
import { PublicLayout } from "@/components/PublicLayout"

const INCLUSIONS: { tier: string; note: string; items: string[]; cta: string; featured?: boolean }[] = [
  {
    tier: "Starter",
    note: "Up to 50 employees",
    items: [
      "Core HR — one record per person, effective-dated history",
      "Attendance: clock in/out, timesheets, cut-off lock",
      "Leave — ledger-derived balances, approvals in one click",
      "Reports: headcount, absence and turnover",
      "Audit trail — hash-chained, exportable",
      "CSV import & export with dry-run",
    ],
    cta: "Start with Starter",
  },
  {
    tier: "Growth",
    note: "51–500 employees",
    featured: true,
    items: [
      "Everything in Starter, plus:",
      "Recruiting — requisitions to accepted offers with e-sign",
      "Onboarding checklists + industry templates",
      "Scheduling — roster drafts, publishing, swaps",
      "Payroll — reconciled runs, payslip drill-down",
      "Performance — goals, reviews, compensation bands",
      "Benefits & learning modules",
    ],
    cta: "Request a demo",
  },
  {
    tier: "Enterprise",
    note: "500+ employees",
    items: [
      "Everything in Growth, plus:",
      "SSO by configuration (SAML / OIDC / OAuth2)",
      "Data-processing agreement; dedicated onboarding",
      "Scoped connection plan (SFTP, mTLS integrations)",
      "Multi-entity organisation structures",
      "SLA and custom jurisdiction rule packs",
    ],
    cta: "Contact sales",
  },
]

export default function PricingPage() {
  return (
    <PublicLayout>
      <section className="relative overflow-hidden border-b border-white/[0.06]">
        <div
          aria-hidden="true"
          className="absolute inset-0"
          style={{
            backgroundImage:
              "radial-gradient(760px 340px at 12% -20%, rgba(37,99,235,0.30), transparent 62%), radial-gradient(600px 300px at 90% -30%, rgba(34,211,238,0.12), transparent 60%)",
          }}
        />
        <div aria-hidden="true" className="mk-grid absolute inset-0" />
        <div className="relative max-w-container mx-auto px-4 sm:px-6 lg:px-8 pt-14 pb-12">
          <p className="mk-eyebrow w-fit">Pricing</p>
          <h1 className="mt-6 mk-h2 md:!text-[clamp(2.2rem,4.6vw,3.6rem)] text-fg max-w-3xl">Simple pricing, scaled to your stage</h1>
          <p className="text-body text-fg-muted max-w-2xl mt-4">
            Per-employee pricing for core HR, time, leave and reporting. Add payroll, scheduling, performance and more as
            modules. Quotes are scoped per organisation — no seat games, no flat-fee surprises.
          </p>

          {/* tiers */}
          <div className="mt-10 grid grid-cols-1 md:grid-cols-3 gap-6">
            {INCLUSIONS.map((t) => (
              <div
                key={t.tier}
                className={`mk-card p-6 flex flex-col ${t.featured ? "shadow-lg relative" : ""}`}
              >
                {t.featured && (
                  <span className="absolute -top-3 left-6 rounded-full bg-brand-600 px-3 py-1 text-xs font-semibold text-white">
                    Most teams start here
                  </span>
                )}
                <h2 className="mk-h2 font-semibold text-fg">{t.tier}</h2>
                <p className="text-caption text-fg-subtle mt-1">{t.note}</p>
                <p className="mk-h2 font-bold text-brand-600 mt-3">
                  {t.tier === "Enterprise" ? "Scoped" : <span aria-label="placeholder price">[price]</span>}
                </p>
                <p className="text-xs text-fg-subtle">per employee / month — scoped on the demo</p>
                <ul className="mt-4 space-y-2 flex-1">
                  {t.items.map((i) => (
                    <li key={i} className="flex items-start gap-2 text-body-sm text-fg-muted">
                      <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500" aria-hidden="true" />
                      {i}
                    </li>
                  ))}
                </ul>
                <Link
                  to="/contact"
                  className={`w-full mt-5 ${t.cta === "Contact sales" ? "mk-ghost" : "mk-cta"}`}
                >
                  {t.cta}
                </Link>
              </div>
            ))}
          </div>

          {/* honesty + FAQ strip */}
          <div className="mt-12 grid md:grid-cols-2 gap-6">
            <div className="mk-card mk-card-flat p-6 mk-reveal">
              <h2 className="mk-h2 font-semibold text-fg">Why no numbers on the page?</h2>
              <p className="text-body-sm text-fg-muted mt-2">
                Because pricing that fits a 60-person manufacturer rarely fits a 400-person hospital chain. Employee
                count, industry rule pack, modules and implementation depth define the quote. A 20-minute call produces
                the real number — we don't publish one we'd move next week.
              </p>
              <ul className="mt-3 space-y-2 text-body-sm text-fg-muted">
                {[
                  "Seat pricing — no per-module tax on core features",
                  "Data migration via CSV import included — no services engagement",
                  "Cancel anytime; history exports as CSV",
                ].map((i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--semantic-status-success)]" aria-hidden="true" />
                    {i}
                  </li>
                ))}
              </ul>
            </div>
            <div className="mk-card mk-card-flat p-6 mk-reveal">
              <h2 className="mk-h2 font-semibold text-fg">Implementation, honestly</h2>
              <ul className="mt-3 space-y-2 text-body-sm text-fg-muted">
                {[
                  "Setup starts from an industry template, not a blank page — departments, shift patterns and policies pre-filled.",
                  "A readiness check tells you what is still unconfigured before go-live, with an onboarding checklist per gap.",
                  "Bulk data enters through a dry run first: counts and bad rows are reported before anything is written.",
                  "Payroll switches over with rehearsal runs — reconciled, payslip-traceable, before the first real calculation.",
                ].map((i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500" aria-hidden="true" />
                    {i}
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-xs text-fg-subtle">
                Questions first? The <Link to="/faq" className="mk-link">FAQ</Link> answers the
                implementation, migration and security questions we hear most.
              </p>
            </div>
          </div>

          <p className="mt-10 text-center text-caption text-fg-muted">
            Prices on this page are placeholders on purpose — real quotes come from a demo conversation tailored to your
            employee count, industry and module selection.
          </p>
        </div>
      </section>
    </PublicLayout>
  )
}
