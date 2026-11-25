import { Link } from "react-router-dom"
import { PublicLayout } from "@/components/PublicLayout"
import { PageHero, PageBody } from "@/components/marketing/PageHero"

const ACHIEVED = [
  { title: "Data isolation", desc: "One schema per customer. No cross-tenant queries by construction, not by WHERE clause.", icon: "⬢", tile: "icon-tile-brand" },
  { title: "RBAC — 300+ ops", desc: "SuperAdmin, HR, Manager, Associate, PayrollViewer. Every endpoint is role-gated.", icon: "◈", tile: "icon-tile-violet" },
  { title: "Audit trail", desc: "Hash-chained, tamper-evident. Every mutation is attributable: who, when, on which record.", icon: "≡", tile: "icon-tile-teal" },
  { title: "mTLS", desc: "Oracle Autonomous Database connections over mutual TLS. No public DB endpoint.", icon: "◎", tile: "icon-tile-green" },
  { title: "Encrypted secrets", desc: "Integration credentials and tokens encrypted at rest, versioned, and rotatable.", icon: "●", tile: "icon-tile-amber" },
  { title: "Least privilege", desc: "Service accounts and humans are scoped to the minimum needed. No ambient access.", icon: "⬣", tile: "icon-tile-slate" },
]

const IN_PROGRESS = [
  { title: "SOC 2 Type II", desc: "In progress. Controls operate today; the audit window is agreed with the assessor — no date promised.", pill: "In progress" },
  { title: "ISO 27001", desc: "Roadmap. ISMS and risk register underway; certification cycle to follow SOC 2.", pill: "In progress" },
]

const POSTURE = [
  { title: "GDPR / CCPA", desc: "Rights, retention, and erasure workflows. DPA available on request." },
  { title: "Data residency", desc: "Pinned to your Oracle Cloud region. No cross-region replication without consent." },
  { title: "DPA", desc: "Data Processing Addendum available on request for all tiers; BAA on Enterprise." },
  { title: "Backups & retention", desc: "Automated backups, point-in-time recovery, and configurable retention policies." },
  { title: "Pen-test summary", desc: "Available under NDA on Enterprise. Findings tracked, remediated, and re-tested." },
]

export default function Security() {
  return (
    <PublicLayout>
      {/* Hero */}
      <PageHero
        kicker="Security & trust — by design, not by promise"
        align="center"
        title="Security & Trust"
        intro="Your people data is isolated, audited and encrypted — by design, not by promise."
      >
        <p className="text-body-sm text-fg-subtle mt-3 max-w-2xl mx-auto">
          We are honest about what is shipped and what is in progress. Achieved controls are solid; in-progress items are clearly marked.
        </p>
      </PageHero>

      {/* Achieved / In progress / Posture */}
      <PageBody>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Achieved */}
          <div className="lg:col-span-2">
            <h2 className="mk-h2 font-semibold text-fg mb-4 flex items-center gap-2 mk-reveal">
              <span className="w-2 h-2 rounded-full bg-[var(--semantic-status-success)]" aria-hidden="true" /> Achieved
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {ACHIEVED.map((a, i) => (
                <div key={a.title} className={`mk-card mk-reveal ${i % 2 === 1 ? "mk-reveal-d1" : ""} p-5`}>
                  <div className="flex items-start gap-3">
                    <span className={`icon-tile ${a.tile} text-sm`} aria-hidden="true">{a.icon}</span>
                    <div className="min-w-0">
                      <h3 className="font-semibold text-fg text-sm">{a.title}</h3>
                      <p className="text-xs text-fg-muted mt-1 leading-relaxed">{a.desc}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* In progress + posture side stack */}
          <div className="space-y-6">
            <div>
              <h2 className="mk-h2 font-semibold text-fg mb-4 flex items-center gap-2 mk-reveal">
                <span className="w-2 h-2 rounded-full bg-[var(--semantic-status-warning)]" aria-hidden="true" /> In progress
              </h2>
              <div className="space-y-3">
                {IN_PROGRESS.map((item, i) => (
                  <div key={item.title} className={`mk-card mk-card-flat mk-reveal ${i === 1 ? "mk-reveal-d1" : ""} p-4 border border-[rgba(245,158,11,0.3)]`}>
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="font-semibold text-fg text-sm">{item.title}</h3>
                      <span className="badge badge-amber shrink-0">{item.pill}</span>
                    </div>
                    <p className="text-xs text-fg-muted mt-1 leading-relaxed">{item.desc}</p>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h2 className="mk-h2 font-semibold text-fg mb-3 mk-reveal">Posture</h2>
              <div className="mk-card mk-card-flat p-5 mk-reveal">
                <ul className="space-y-3">
                  {POSTURE.map((p, i) => (
                    <li key={p.title} className={`flex gap-3 ${i > 0 ? "pt-3 border-t border-white/[0.06]" : ""}`}>
                      <span className="w-1.5 h-1.5 rounded-full bg-brand-500 mt-2 shrink-0" aria-hidden="true" />
                      <div>
                        <span className="text-sm font-medium text-fg">{p.title}</span>
                        <span className="text-sm text-fg-muted"> — {p.desc}</span>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>
      </PageBody>

      {/* Deep sections */}
      <section className="border-y border-white/[0.06] bg-white/[0.015] py-14">
        <div className="max-w-container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="mk-card p-6 mk-reveal">
              <div className="flex items-center gap-3 mb-3">
                <span className="icon-tile icon-tile-slate" aria-hidden="true">⬢</span>
                <h2 className="mk-h2 font-semibold text-fg">Infrastructure</h2>
              </div>
              <p className="text-body-sm text-fg-muted leading-relaxed">
                Hosted on Oracle Cloud with Oracle Autonomous Database. Connections use <strong className="text-fg">mTLS</strong> — the database has no public endpoint. Network isolation, automated patching, and private subnets.
              </p>
              <ul className="mt-3 space-y-1 text-xs text-fg-muted">
                <li>• Oracle ADB + mTLS</li>
                <li>• No public DB ingress</li>
                <li>• Region-pinned deployments</li>
              </ul>
            </div>

            <div className="mk-card p-6 mk-reveal">
              <div className="flex items-center gap-3 mb-3">
                <span className="icon-tile icon-tile-violet" aria-hidden="true">◈</span>
                <h2 className="mk-h2 font-semibold text-fg">Access</h2>
              </div>
              <p className="text-body-sm text-fg-muted leading-relaxed">
                <strong className="text-fg">RBAC</strong> with least privilege — 300+ permission checks. <strong className="text-fg">MFA</strong> for all users. <strong className="text-fg">SSO configuration</strong> via SAML / OIDC / OAuth2 on Enterprise, scoped per customer.
              </p>
              <ul className="mt-3 space-y-1 text-xs text-fg-muted">
                <li>• 5 roles, 300+ operations</li>
                <li>• MFA enforced</li>
                <li>• SSO by configuration (Enterprise)</li>
              </ul>
            </div>

            <div className="mk-card p-6 mk-reveal">
              <div className="flex items-center gap-3 mb-3">
                <span className="icon-tile icon-tile-teal" aria-hidden="true">◎</span>
                <h2 className="mk-h2 font-semibold text-fg">Data</h2>
              </div>
              <p className="text-body-sm text-fg-muted leading-relaxed">
                <strong className="text-fg">Isolation</strong> — one schema per customer, so a bug cannot leak rows. <strong className="text-fg">Encryption</strong> in transit (TLS) and at rest, with versioned secrets. <strong className="text-fg">Audit</strong> — hash-chained, tamper-evident.
              </p>
              <ul className="mt-3 space-y-1 text-xs text-fg-muted">
                <li>• One schema per customer</li>
                <li>• Encrypted secrets (versioned)</li>
                <li>• Hash-chained audit trail</li>
              </ul>
            </div>

            <div className="mk-card p-6 mk-reveal">
              <div className="flex items-center gap-3 mb-3">
                <span className="icon-tile icon-tile-green" aria-hidden="true">✓</span>
                <h2 className="mk-h2 font-semibold text-fg">Compliance</h2>
              </div>
              <p className="text-body-sm text-fg-muted leading-relaxed">
                <strong className="text-fg">GDPR / CCPA</strong> workflows. <strong className="text-fg">DPA</strong> available on request for all tiers; BAA on Enterprise. <strong className="text-fg">SOC 2 Type II</strong>{" "}
                <span className="badge badge-amber text-[11px] align-middle">In progress</span> — controls operating; the audit window is agreed with the assessor at engagement. ISO 27001 follows on the roadmap.
              </p>
              <ul className="mt-3 space-y-1 text-xs text-fg-muted">
                <li>• GDPR / CCPA</li>
                <li>• DPA on request; BAA on Enterprise</li>
                <li>• SOC 2 Type II — in progress, no date promised</li>
              </ul>
            </div>

            <div className="mk-card p-6 md:col-span-2 lg:col-span-2 mk-reveal">
              <div className="flex items-center gap-3 mb-3">
                <span className="icon-tile icon-tile-brand" aria-hidden="true">◐</span>
                <h2 className="mk-h2 font-semibold text-fg">Operational</h2>
              </div>
              <p className="text-body-sm text-fg-muted leading-relaxed">
                <strong className="text-fg">Uptime</strong> — 99.98% platform uptime; status page and incident history available. <strong className="text-fg">Incident response</strong> — defined runbooks, on-call rotation, and customer notification. <strong className="text-fg">Sub-processors</strong> listed in the DPA.
              </p>
              <ul className="mt-3 space-y-1 text-xs text-fg-muted">
                <li>• Uptime status &amp; incident response — <Link to="/project-status" className="mk-link">Status</Link></li>
                <li>• Sub-processors disclosed in DPA</li>
                <li>• Backups with point-in-time recovery</li>
                <li>• Support: email included; SLA tiers on Enterprise</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-container mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="mk-card mk-card-flat p-6 md:p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 mk-reveal">
          <div>
            <h2 className="mk-h2 font-semibold text-fg">Questions about security?</h2>
            <p className="text-body-sm text-fg-muted mt-1">
              Contact <a href="mailto:security@karmathy.com" className="mk-link">security@karmathy.com</a> or reach our team.
            </p>
            <p className="text-xs text-fg-subtle mt-2">
              We publish what is achieved as solid and what is in progress with a clear target — no vague &ldquo;enterprise-grade&rdquo; promises.
            </p>
          </div>
          <Link to="/contact" className="mk-cta shrink-0">
            Contact us →
          </Link>
        </div>
        <p className="text-center text-xs text-fg-subtle mt-4">
          See also <Link to="/privacy" className="mk-link">Privacy</Link> and{" "}
          <Link to="/docs" className="mk-link">Documentation</Link>.
        </p>
      </section>
    </PublicLayout>
  )
}
