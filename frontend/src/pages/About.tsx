import { Link } from "react-router-dom"
import { PublicLayout } from "@/components/PublicLayout"
import { PageHero, PageBody } from "@/components/marketing/PageHero"

const ATTRIBUTES: { title: string; desc: string; icon: string; accent: string }[] = [
  { title: "Trustworthy", desc: "Hash-chained audit trail, least-privilege RBAC, one schema per customer.", icon: "⛓", accent: "icon-tile-brand" },
  { title: "Precise", desc: "Payroll reconciled against the approved time and leave it was calculated from.", icon: "≡", accent: "icon-tile-green" },
  { title: "Connected", desc: "One employee record every module reads — no second source of truth.", icon: "◈", accent: "icon-tile-teal" },
  { title: "Adaptable", desc: "Configurable workflows and jurisdiction rule packs.", icon: "⬢", accent: "icon-tile-violet" },
]

export default function About() {
  return (
    <PublicLayout>
      <PageHero
        kicker="Company"
        title="About LibrePeople"
        intro="LibrePeople is a global, end-to-end Human Capital Management (HCM) SaaS platform that brings together the employee lifecycle, workforce management, HR operations, talent, payroll, analytics, and connected people processes in one configurable platform."
      />

      <PageBody narrow>
        {/* Mission */}
        <div className="mk-card mk-reveal p-6 lg:p-8">
          <p className="mk-kicker">Our mission</p>
          <p className="text-body text-fg-muted mt-3 leading-relaxed">
            One system of record for the whole employee lifecycle — hire to off-board — where payroll, time and
            compliance all read the same records. We believe the organisations that will run people ops best over
            the next decade are the ones that stopped managing a workforce with a stack of spreadsheets and got
            one honest platform behind it.
          </p>
        </div>

        {/* Brand attributes */}
        <div className="mt-8">
          <p className="mk-kicker mk-reveal">Brand attributes</p>
          <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-5">
            {ATTRIBUTES.map((a, i) => (
              <div key={a.title} className={`mk-card mk-reveal ${i % 2 === 1 ? "mk-reveal-d1" : ""} p-6`}>
                <span className={`icon-tile ${a.accent}`} aria-hidden="true">
                  <span className="text-sm font-bold">{a.icon}</span>
                </span>
                <h2 className="mt-4 font-semibold text-fg text-base tracking-tight">{a.title}</h2>
                <p className="mt-2 text-body-sm text-fg-muted leading-relaxed">{a.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Signature + CTA */}
        <div className="mt-10 mk-card mk-reveal p-6 flex flex-col sm:flex-row sm:items-center gap-5">
          <div>
            <p className="text-sm font-semibold text-fg" style={{ fontFamily: "var(--font-display)" }}>
              People. Potential. Progress.
            </p>
            <p className="text-xs text-fg-subtle mt-1">The brand signature — and the standard the product is held to.</p>
          </div>
          <div className="flex gap-3 sm:ml-auto shrink-0">
            <Link to="/contact" className="mk-cta !py-2.5 !px-5 text-sm">
              Request a demo
            </Link>
            <Link to="/careers" className="mk-ghost !py-2.5 !px-5 text-sm">
              Join the team
            </Link>
          </div>
        </div>
      </PageBody>
    </PublicLayout>
  )
}
