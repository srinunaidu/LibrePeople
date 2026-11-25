import { PublicLayout } from "@/components/PublicLayout"
import { PageHero, PageBody } from "@/components/marketing/PageHero"

const GUIDES: { title: string; desc: string; icon: string; accent: string }[] = [
  { title: "Getting Started", desc: "Set up your account and configure your organization.", icon: "＋", accent: "icon-tile-brand" },
  { title: "API Reference", desc: "Full REST API documentation with all endpoints.", icon: "⇄", accent: "icon-tile-teal" },
  { title: "Client Onboarding", desc: "Step-by-step guide to onboarding a new client.", icon: "◈", accent: "icon-tile-green" },
  { title: "Migration Guide", desc: "How to migrate data from any system.", icon: "⇪", accent: "icon-tile-violet" },
  { title: "Feature Flags", desc: "Enable and configure modules per client.", icon: "○", accent: "icon-tile-amber" },
  { title: "Integrations", desc: "Connect to Oracle ADB, REST, SFTP, and webhooks.", icon: "⬢", accent: "icon-tile-slate" },
]

export default function Documentation() {
  return (
    <PublicLayout>
      <PageHero
        kicker="Documentation"
        title="Everything you need to get started"
        intro="Set-up guides, the API reference and the migration playbook — the same documents our implementation uses."
      />

      <PageBody>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {GUIDES.map((d, i) => (
            <div key={d.title} className={`mk-card mk-card-flat mk-reveal ${i % 3 === 1 ? "mk-reveal-d1" : i % 3 === 2 ? "mk-reveal-d2" : ""} p-6`}>
              <span className={`icon-tile ${d.accent}`} aria-hidden="true">
                <span className="text-sm font-bold">{d.icon}</span>
              </span>
              <h2 className="mt-4 font-semibold text-fg text-base tracking-tight">{d.title}</h2>
              <p className="text-body-sm text-fg-muted mt-2">{d.desc}</p>
            </div>
          ))}
        </div>

        <div className="mt-10 text-center mk-reveal">
          <a href="https://karmathy-backend.onrender.com/docs" target="_blank" rel="noreferrer" className="mk-cta">
            Open API Docs <span aria-hidden="true">↗</span>
          </a>
        </div>
      </PageBody>
    </PublicLayout>
  )
}
