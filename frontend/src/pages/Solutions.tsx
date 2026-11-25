import { Link } from "react-router-dom"
import { PublicLayout } from "@/components/PublicLayout"
import { PageHero, PageBody } from "@/components/marketing/PageHero"

const SOLUTIONS: { title: string; desc: string; to: string; icon: string; accent: string }[] = [
  { title: "By Industry", desc: "Tailored HCM for manufacturing, healthcare, retail, financial services, technology, logistics, education, and more.", to: "/industries", icon: "⬣", accent: "icon-tile-brand" },
  { title: "By Company Size", desc: "From startups to global enterprises — scalable plans for every organization size.", to: "/pricing", icon: "◈", accent: "icon-tile-teal" },
  { title: "Integrations", desc: "Oracle ADB over mTLS, REST APIs, SFTP, CSV, HMAC webhooks and SSO configuration.", to: "/platform", icon: "⇄", accent: "icon-tile-violet" },
  { title: "Client Onboarding", desc: "Self-service tenant setup with feature flags, branding, and data migration.", to: "/docs", icon: "＋", accent: "icon-tile-green" },
  { title: "Platform Modules", desc: "All 14 HCM modules in one configurable platform.", to: "/platform", icon: "⬢", accent: "icon-tile-amber" },
  { title: "Reporting & Analytics", desc: "Headcount, labour cost, attendance and audit trails — dashboards that answer, not just chart.", to: "/docs", icon: "▤", accent: "icon-tile-slate" },
]

export default function Solutions() {
  return (
    <PublicLayout>
      <PageHero
        kicker="Solutions"
        title="Solutions for every stage of scale"
        intro="LibrePeople adapts to your industry, size, and existing systems. Explore the solutions that fit your organization."
      />

      <PageBody>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {SOLUTIONS.map((s, i) => (
            <Link key={s.title} to={s.to} className={`mk-card mk-reveal ${i % 3 === 1 ? "mk-reveal-d1" : i % 3 === 2 ? "mk-reveal-d2" : ""} p-6 flex flex-col group`}>
              <span className={`icon-tile ${s.accent}`} aria-hidden="true">
                <span className="text-sm font-bold">{s.icon}</span>
              </span>
              <h2 className="mt-4 font-semibold text-fg text-base tracking-tight">{s.title}</h2>
              <p className="text-body-sm text-fg-muted mt-2 flex-1">{s.desc}</p>
              <span className="mt-4 text-xs font-semibold text-brand-600 group-hover:underline">
                Explore <span aria-hidden="true">→</span>
              </span>
            </Link>
          ))}
        </div>

        <div className="mt-12 text-center mk-reveal">
          <Link to="/contact" className="mk-cta">
            Request a demo <span aria-hidden="true">→</span>
          </Link>
        </div>
      </PageBody>
    </PublicLayout>
  )
}
