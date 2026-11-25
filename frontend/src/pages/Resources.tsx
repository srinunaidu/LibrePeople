import { Link } from "react-router-dom"
import { PublicLayout } from "@/components/PublicLayout"
import { PageHero, PageBody } from "@/components/marketing/PageHero"

const RESOURCES: { title: string; desc: string; to: string; icon: string; accent: string }[] = [
  { title: "API Documentation", desc: "Full REST API reference with all endpoints, schemas, and examples.", to: "/docs", icon: "▤", accent: "icon-tile-brand" },
  { title: "ROI Calculator", desc: "What does spreadsheet HR cost you? Estimate savings in 30 seconds.", to: "/pricing", icon: "₵", accent: "icon-tile-teal" },
  { title: "Migration Checklist", desc: "5 steps from spreadsheet to Karmathy — download as PDF.", to: "/security", icon: "✓", accent: "icon-tile-green" },
  { title: "Platform Modules", desc: "Overview of all 14 HCM modules.", to: "/platform", icon: "⬢", accent: "icon-tile-violet" },
  { title: "Security & Trust", desc: "Data isolation, audit trail, RBAC, encryption and compliance posture.", to: "/security", icon: "⛓", accent: "icon-tile-amber" },
  { title: "FAQ", desc: "Migration, payroll, integrations, data ownership and more.", to: "/faq", icon: "◎", accent: "icon-tile-slate" },
]

export default function Resources() {
  return (
    <PublicLayout>
      <PageHero
        kicker="Resources"
        title="Documentation, guides and references"
        intro="Documentation, guides, and API references to help you get the most out of Karmathy."
      />

      <PageBody>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {RESOURCES.map((r, i) => (
            <Link key={r.title} to={r.to} className={`mk-card mk-reveal ${i % 3 === 1 ? "mk-reveal-d1" : i % 3 === 2 ? "mk-reveal-d2" : ""} p-6 flex flex-col group`}>
              <span className={`icon-tile ${r.accent}`} aria-hidden="true">
                <span className="text-sm font-bold">{r.icon}</span>
              </span>
              <h2 className="mt-4 font-semibold text-fg text-base tracking-tight">{r.title}</h2>
              <p className="text-body-sm text-fg-muted mt-2 flex-1">{r.desc}</p>
              <span className="mt-4 text-xs font-semibold text-brand-600 group-hover:underline">
                Open <span aria-hidden="true">→</span>
              </span>
            </Link>
          ))}
        </div>
      </PageBody>
    </PublicLayout>
  )
}
