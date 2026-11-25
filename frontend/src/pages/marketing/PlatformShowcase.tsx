import { Link } from "react-router-dom"
import { PublicLayout } from "@/components/PublicLayout"
import { ThreadCompact } from "@/components/marketing/Thread"
import { THREAD_STAGES } from "@/lib/designSystem"

const MODULES: { title: string; desc: string; icon: string; accent: string; to: string }[] = [
  { title: "Core HR & directory", desc: "One record per person — positions, departments and history in sync.", icon: "◈", accent: "icon-tile-brand", to: "/people" },
  { title: "Recruiting", desc: "Requisitions to accepted offers — e-sign and background state on the record.", icon: "⬣", accent: "icon-tile-teal", to: "/recruiting" },
  { title: "Onboarding", desc: "Requisitions to day-one checklists. Automate offers and e-signatures.", icon: "＋", accent: "icon-tile-teal", to: "/onboarding" },
  { title: "Time & Attendance", desc: "Clock in, timesheets and overtime — with approval in one click.", icon: "◷", accent: "icon-tile-violet", to: "/time" },
  { title: "Scheduling & Rostering", desc: "Templates, roster drafts, publishing and shift swaps.", icon: "▦", accent: "icon-tile-green", to: "/scheduling" },
  { title: "Leave", desc: "Ledger-derived balances — requests, approvals and overlap checks.", icon: "☾", accent: "icon-tile-amber", to: "/leave" },
  { title: "Payroll", desc: "Approved inputs only — rule-pack reconciliation and payslip traceability.", icon: "₵", accent: "icon-tile-brand", to: "/platform/payroll" },
  { title: "Performance", desc: "Goals, reviews and compensation bands on the same record.", icon: "⬢", accent: "icon-tile-violet", to: "/platform/performance" },
  { title: "Benefits", desc: "Plans, eligibility, enrolment windows and life events.", icon: "✚", accent: "icon-tile-green", to: "/platform/benefits" },
  { title: "Learning & talent", desc: "Courses, certifications, talent pools and succession.", icon: "▤", accent: "icon-tile-slate", to: "/platform/learning" },
  { title: "Compliance & assurance", desc: "Hash-chained audit trail, RBAC and headcount scenarios.", icon: "⬢", accent: "icon-tile-brand", to: "/platform/compliance" },
  { title: "Offboarding", desc: "Exit interviews, revocation, settlement — via the enforced lifecycle.", icon: "▸", accent: "icon-tile-amber", to: "/offboarding" },
]

const INTEGRATIONS = ["Oracle ADB (mTLS)", "REST API", "CSV import/export", "HMAC webhooks", "SSO config (SAML/OIDC)", "SFTP"]

const SECURITY_STRIP = [
  { icon: "◎", label: "Data isolation — one schema per customer" },
  { icon: "≡", label: "RBAC + MFA enforced; SSO configurable for enterprise" },
  { icon: "⬢", label: "Hash-chained audit trail" },
  { icon: "✓", label: "Encrypted secrets, versioned" },
]

export default function PlatformShowcase() {
  return (
    <PublicLayout>
      {/* Hero — outcome-led, mirrors the homepage language */}
      <section className="relative overflow-hidden bg-surface-sunken">
        <div
          aria-hidden="true"
          className="absolute inset-0"
          style={{
            backgroundImage:
              "radial-gradient(1100px 520px at 12% -10%, rgba(6,182,212,0.32), transparent 60%), radial-gradient(900px 480px at 92% 8%, rgba(37,99,235,0.42), transparent 62%), radial-gradient(700px 420px at 55% 105%, rgba(139,92,246,0.18), transparent 65%)",
          }}
        />
        <div
          aria-hidden="true"
          className="absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,0.9) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.9) 1px, transparent 1px)",
            backgroundSize: "56px 56px",
            maskImage: "radial-gradient(circle at 50% 20%, black, transparent 75%)",
            WebkitMaskImage: "radial-gradient(circle at 50% 20%, black, transparent 75%)",
          }}
        />
        <div
          aria-hidden="true"
          className="absolute inset-0 opacity-[0.035]"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.5'/%3E%3C/svg%3E")`,
          }}
        />

        <div className="relative max-w-container mx-auto px-4 sm:px-6 lg:px-8 py-20 md:py-28 lg:py-32">
          <div className="max-w-3xl">
            <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 backdrop-blur px-3.5 py-1.5 text-xs font-semibold tracking-wide text-white/90">
              <span className="h-1.5 w-1.5 rounded-full bg-teal-400 animate-pulse" aria-hidden="true" />
              The platform behind the promise
            </span>
            <h1 className="mt-6 text-display font-bold leading-[1.05] tracking-tight text-white">
              <span className="mk-gradient-text">
                One platform. Every person. Every lifecycle stage.
              </span>
            </h1>
            <p className="mt-6 text-lg leading-relaxed text-[rgba(219,234,254,0.9)] max-w-2xl">
              Core HR, recruiting, onboarding, time, scheduling, leave, offboarding, payroll, performance, benefits, learning and reporting — wired to a single source of truth and one audit trail.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Link to="/contact" className="mk-cta">
                Request a demo
              </Link>
              <Link to="/industries" className="mk-ghost">
                Explore by industry
              </Link>
            </div>

            {/* Compact Thread — module context (current stage: all modules shown together) */}
            <div className="mt-10 max-w-2xl mx-auto">
              <ThreadCompact stages={THREAD_STAGES} currentStageId="pay" />
            </div>
          </div>
        </div>
      </section>

      {/* Modules */}
      <section id="modules" className="max-w-container mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-24">
        <div className="max-w-2xl">
          <h2 className="text-h2 font-semibold text-fg">Eight modules that cover the full lifecycle</h2>
          <p className="text-body text-fg-muted mt-3">
            Not a module box — an operating system. Each module reads from the same employee record, so there is never a second source of truth.
          </p>
        </div>
        <div className="mt-12 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {MODULES.map((m) => (
            <Link key={m.title} to={m.to} className="card p-6 card-hover group">
              <span className={`icon-tile ${m.accent}`} aria-hidden="true">{m.icon}</span>
              <h3 className="font-semibold text-fg text-lg mt-4">{m.title}</h3>
              <p className="text-body-sm text-fg-muted mt-2">{m.desc}</p>
              <span className="text-xs font-semibold text-brand-600 mt-3 group-hover:underline">Explore the module →</span>
            </Link>
          ))}
        </div>
      </section>

      {/* Integrations + security strip */}
      <section className="border-y border-white/[0.06] bg-white/[0.015] py-16">
        <div className="max-w-container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-h2 font-semibold text-fg">Works with your stack, honestly</h2>
              <p className="text-body text-fg-muted mt-3">
                Oracle Autonomous Database over mTLS, a full REST API under the product, HMAC-signed webhook
                subscriptions with a delivery log, SSO configuration for SAML / OIDC / OAuth2, SFTP and CSV bulk flows.
                We name capabilities rather than logos — provider connection plans are scoped per customer.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                {INTEGRATIONS.map((i) => (
                  <span key={i} className="badge badge-slate font-mono">{i}</span>
                ))}
              </div>
            </div>
            <div>
              <h2 className="text-h2 font-semibold text-fg">Secure by construction</h2>
              <ul className="mt-6 space-y-4">
                {SECURITY_STRIP.map((s) => (
                  <li key={s.label} className="flex items-start gap-3">
                    <span className="icon-tile icon-tile-teal w-8 h-8 text-xs shrink-0" aria-hidden="true">{s.icon}</span>
                    <span className="text-body-sm text-fg-muted">{s.label}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-container mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-24 text-center">
        <h2 className="text-h2 font-semibold text-fg">See the platform on your data, not a demo script.</h2>
        <p className="text-body text-fg-muted mt-3 max-w-2xl mx-auto">
          Bring a CSV of your people — we&apos;ll run it through the modules live during the pilot.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link to="/contact" className="btn btn-primary">Request a demo →</Link>
          <Link to="/pricing" className="btn btn-secondary">See pricing</Link>
        </div>
      </section>
    </PublicLayout>
  )
}
