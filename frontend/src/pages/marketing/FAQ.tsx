import { Link } from "react-router-dom"
import { PublicLayout } from "@/components/PublicLayout"
import { PageHero, PageBody } from "@/components/marketing/PageHero"

const FAQS = [
  {
    q: "How long does migration take?",
    a: "CSV import in minutes — templates for all entities (people, time, leave, pay runs, and more) are built in. A small org can cut over in 2 days; a 500+ org typically takes up to 2 weeks including mapping, validation, and parallel payroll. Migration is included on all tiers; dedicated onboarding on Enterprise.",
  },
  {
    q: "Do you support multi-country / multi-currency payroll?",
    a: "Payroll uses rule packs per jurisdiction — earnings, deductions, and contributions are jurisdiction-aware. Currency is per pay profile (currently single-currency per profile; multi-currency on the roadmap). If you run multiple countries today, each jurisdiction gets its own rule pack and pay profile.",
  },
  {
    q: "What integrations are live?",
    a: "REST APIs under the product, HMAC-signed webhook subscriptions with a delivery log, SSO configuration via SAML / OIDC / OAuth2, SFTP and CSV import/export. Oracle Autonomous Database is connected over mTLS. E-signature and background-check state are tracked as Platform-module records; provider-specific connection plans are scoped per customer.",
  },
  {
    q: "Who owns my data?",
    a: "You do. One schema per customer — your data is isolated by construction. Full CSV export for all entities, any time. DPA available on request; no vendor lock-in.",
  },
  {
    q: "What if we need HIPAA?",
    a: "Audit trail (hash-chained, tamper-evident) + RBAC (300+ ops) + encryption in transit and at rest + DPA are in place for all customers. HIPAA BAA is available on Enterprise. Contact us to scope the controls that map to your HIPAA program.",
  },
  {
    q: "What is the Oracle cold-start impact?",
    a: "Honest answer: the Oracle free tier may spin down after idle, which can cause a ~30s cold start on the next request. The paid tier eliminates it with always-on compute. Most pilots use the paid tier; if you are on the free tier during evaluation, the first load after idle is the one that spins it up.",
  },
  {
    q: "What does support cost?",
    a: "Email support is included on all tiers. Priority support on Growth; dedicated CSM and SLA tiers on Enterprise. Response targets and escalation paths are documented in the DPA / order form — no hidden support fees.",
  },
  {
    q: "Can we self-host or export our data?",
    a: "Cloud-only — there is no self-hosted deployment. You can export everything via CSV (all entities) at any time. If you leave, you take your data; the schema is yours, the export is complete, and we delete per the DPA retention schedule.",
  },
] as const

const INTEGRATION_PILLS = ["REST", "Webhooks", "SSO — SAML / OIDC", "SFTP", "CSV", "Oracle ADB (mTLS)", "mTLS"]

export default function FAQ() {
  return (
    <PublicLayout>
      {/* Hero */}
      <PageHero
        kicker="LibrePeople FAQ"
        align="center"
        title="Frequently asked questions"
        intro="Straight answers — including the trade-offs. If you don't see your question, talk to us."
      />

      {/* FAQ accordion */}
      <section className="max-w-container mx-auto px-4 sm:px-6 lg:px-8 py-14 lg:py-20">
        <div className="max-w-3xl mx-auto space-y-3">
          {FAQS.map((faq, idx) => (
            <details
              key={faq.q}
              className="mk-card mk-card-flat p-5 group open:-translate-y-0"
              open={idx === 0}
            >
              <summary className="font-medium text-fg cursor-pointer list-none flex items-start justify-between gap-4">
                <span className="flex gap-3">
                  <span className="icon-tile icon-tile-slate w-7 h-7 text-xs shrink-0 mt-0.5" aria-hidden="true">
                    {idx + 1}
                  </span>
                  <span>{faq.q}</span>
                </span>
                <span className="text-fg-subtle group-open:rotate-180 transition-transform shrink-0 mt-1" aria-hidden="true">
                  ▾
                </span>
              </summary>
              <div className="mt-3 ml-10">
                <p className="text-body-sm text-fg-muted leading-relaxed">{faq.a}</p>
                {idx === 2 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {INTEGRATION_PILLS.map((pill) => (
                      <span key={pill} className="badge badge-slate font-mono text-xs">{pill}</span>
                    ))}
                  </div>
                )}
                {idx === 5 && (
                  <p className="mt-3 text-xs text-fg-subtle">
                    Tip: if you notice a cold start, a periodic health probe keeps the free tier warm.
                  </p>
                )}
              </div>
            </details>
          ))}
        </div>

        <div className="max-w-3xl mx-auto mt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-sm text-fg-muted">
            Don&apos;t see your question? <Link to="/contact" className="mk-link">Talk to us →</Link>
          </p>
          <div className="flex gap-3">
            <Link to="/pricing" className="mk-ghost !py-2 !px-4 text-sm">See pricing</Link>
            <Link to="/contact" className="mk-cta !py-2 !px-4 text-sm">Contact us</Link>
          </div>
        </div>
      </section>

      {/* Related links bento */}
      <section className="border-t border-white/[0.06] bg-white/[0.015] py-16">
        <div className="max-w-container mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-lg font-semibold text-fg text-center">More to explore</h2>
          <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4 max-w-3xl mx-auto">
            <Link to="/security" className="mk-card p-5 block mk-reveal">
              <span className="icon-tile icon-tile-teal mb-3" aria-hidden="true">◎</span>
              <h3 className="font-semibold text-fg">Security &amp; Trust</h3>
              <p className="text-xs text-fg-muted mt-1">Isolation, audit trail, encryption — and what&apos;s in progress.</p>
              <span className="text-xs text-brand-600 font-medium mt-3 inline-block">Explore →</span>
            </Link>
            <Link to="/platform" className="mk-card p-5 block mk-reveal">
              <span className="icon-tile icon-tile-brand mb-3" aria-hidden="true">⬢</span>
              <h3 className="font-semibold text-fg">Platform modules</h3>
              <p className="text-xs text-fg-muted mt-1">14 HCM modules in one configurable platform.</p>
              <span className="text-xs text-brand-600 font-medium mt-3 inline-block">Explore →</span>
            </Link>
            <Link to="/docs" className="mk-card p-5 block mk-reveal">
              <span className="icon-tile icon-tile-violet mb-3" aria-hidden="true">≡</span>
              <h3 className="font-semibold text-fg">Documentation</h3>
              <p className="text-xs text-fg-muted mt-1">Guides, API reference, and migration docs.</p>
              <span className="text-xs text-brand-600 font-medium mt-3 inline-block">Open docs →</span>
            </Link>
          </div>
        </div>
      </section>
    </PublicLayout>
  )
}
