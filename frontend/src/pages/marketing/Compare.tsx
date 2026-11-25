import { Link, useParams } from "react-router-dom"
import { PublicLayout } from "@/components/PublicLayout"
import { PageHero } from "@/components/marketing/PageHero"

type Cell = "yes" | "partial" | "no"

interface Row {
  module: string
  karmathy: Cell
  bamboohr: Cell
  note?: string
}

const MODULES: Row[] = [
  { module: "Core HR", karmathy: "yes", bamboohr: "yes" },
  { module: "Recruiting", karmathy: "yes", bamboohr: "yes" },
  { module: "Onboarding", karmathy: "yes", bamboohr: "partial", note: "Checklists; limited workflow config" },
  { module: "Time", karmathy: "yes", bamboohr: "partial", note: "Via partner / add-on" },
  { module: "Scheduling", karmathy: "yes", bamboohr: "no" },
  { module: "Leave", karmathy: "yes", bamboohr: "yes" },
  { module: "Offboarding", karmathy: "yes", bamboohr: "partial", note: "Basic exit tasks" },
  { module: "Payroll", karmathy: "yes", bamboohr: "partial", note: "US-only; via partner in many regions" },
  { module: "Performance", karmathy: "yes", bamboohr: "partial", note: "Reviews; no 360° or bands" },
  { module: "Benefits", karmathy: "yes", bamboohr: "partial", note: "Enrolment; narrow carrier support" },
  { module: "Learning", karmathy: "yes", bamboohr: "no" },
  { module: "Reporting", karmathy: "yes", bamboohr: "partial", note: "Dashboards; limited custom reports" },
]

const COMPETITORS: Record<string, { label: string; ready: boolean }> = {
  bamboohr: { label: "BambooHR", ready: true },
  rippling: { label: "Rippling", ready: false },
  workday: { label: "Workday", ready: false },
}

function CellBadge({ value }: { value: Cell }) {
  if (value === "yes") return <span className="badge badge-green">✓ Yes</span>
  if (value === "partial") return <span className="badge badge-amber">◐ Partial</span>
  return <span className="badge badge-slate">—</span>
}

export default function Compare() {
  const { competitor: raw } = useParams<{ competitor: string }>()
  const key = (raw ?? "").toLowerCase()
  const meta = COMPETITORS[key]
  const label = meta?.label ?? raw ?? "Competitor"
  const isReady = meta?.ready === true

  if (!meta) {
    return (
      <PublicLayout>
        <div className="max-w-container mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center">
          <h1 className="mk-h1 font-bold text-fg">Comparison not found</h1>
          <p className="text-body text-fg-muted mt-3">We don&apos;t have a comparison for &ldquo;{raw}&rdquo; yet.</p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            {Object.entries(COMPETITORS).map(([k, v]) => (
              <Link key={k} to={`/compare/${k}`} className="mk-ghost !py-2 !px-4 text-sm">
                Karmathy vs {v.label}
              </Link>
            ))}
          </div>
        </div>
      </PublicLayout>
    )
  }

  if (!isReady) {
    return (
      <PublicLayout>
        <section className="max-w-container mx-auto px-4 sm:px-6 lg:px-8 pt-10 pb-6">
          <h1 className="mk-h1 font-bold text-fg">Karmathy vs {label}</h1>
          <p className="text-body text-fg-muted mt-3 max-w-2xl">
            A detailed, module-by-module comparison for {label} is being prepared with design partners.
          </p>
        </section>
        <section className="max-w-container mx-auto px-4 sm:px-6 lg:px-8 pb-12">
          <div className="mk-card mk-card-flat p-6">
            <div>
              <p className="font-semibold text-fg">Coming soon — detailed comparison being prepared.</p>
              <p className="text-sm text-fg-muted mt-1">
                Want a tailored walkthrough in the meantime?{" "}
                <Link to="/contact" className="mk-link">
                  Request a demo →
                </Link>
              </p>
            </div>
          </div>
          <div className="mt-6 flex flex-wrap gap-3">
            {Object.entries(COMPETITORS).map(([k, v]) => (
              <Link
                key={k}
                to={`/compare/${k}`}
                className={k === key ? "mk-cta !py-2 !px-4 text-sm" : "mk-ghost !py-2 !px-4 text-sm"}
              >
                vs {v.label}
              </Link>
            ))}
          </div>
        </section>
      </PublicLayout>
    )
  }

  // BambooHR — fully written
  return (
    <PublicLayout>
      {/* Hero */}
      <PageHero
        kicker="Comparison"
        title={<>Karmathy <span className="mk-gradient-blue">vs {label}</span></>}
        intro="Two modern HR platforms — but only one covers the full lifecycle without add-ons and partners."
      />

      {/* Why switch */}
      <section className="max-w-container mx-auto px-4 sm:px-6 lg:px-8 pb-8">
        <div className="mk-card mk-card-flat p-6 mk-reveal">
          <h2 className="mk-h2 font-semibold text-fg">Why teams switch from {label}</h2>
          <ul className="mt-3 space-y-2 text-body-sm text-fg-muted">
            <li>• <strong>Full lifecycle in one place</strong> — scheduling, offboarding, learning and payroll are native, not add-ons or partners.</li>
            <li>• <strong>Configurable workflows</strong> — approval chains, onboarding checklists and leave policies adapt to your org, not the other way around.</li>
            <li>• <strong>Multi-tenant and audit-ready</strong> — per-client isolation, RBAC, and an immutable audit trail on every record.</li>
          </ul>
        </div>
      </section>

      {/* Matrix */}
      <section className="max-w-container mx-auto px-4 sm:px-6 lg:px-8 pb-8">
        <h2 className="mk-h2 font-semibold text-fg mb-4 mk-reveal">Module comparison</h2>
        <div className="mk-card mk-reveal overflow-hidden">
          <div className="table-scroll">
            <table className="table-base">
              <thead>
                <tr>
                  <th>Module</th>
                  <th>Karmathy</th>
                  <th>{label}</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {MODULES.map((r) => (
                  <tr key={r.module}>
                    <td>{r.module}</td>
                    <td>
                      <CellBadge value={r.karmathy} />
                    </td>
                    <td>
                      <CellBadge value={r.bamboohr} />
                    </td>
                    <td className="text-fg-subtle text-xs">{r.note ?? ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <p className="text-xs text-fg-subtle mt-2">
          Based on publicly available product information as of Oct 2026. Capabilities vary by plan and region.
        </p>
      </section>

      {/* Migrating */}
      <section className="max-w-container mx-auto px-4 sm:px-6 lg:px-8 pb-8">
        <div className="mk-card mk-card-flat p-6 mk-reveal">
          <h2 className="mk-h2 font-semibold text-fg">Migrating from {label}</h2>
          <ol className="mt-3 space-y-2 text-body-sm text-fg-muted list-decimal list-inside">
            <li>
              <strong>Export from {label}</strong> — download employees, time-off balances and documents via CSV or API.
            </li>
            <li>
              <strong>Import into Karmathy</strong> — use the CSV import wizard (or the bulk API) for all entities; validation catches missing fields before cutover.
            </li>
            <li>
              <strong>Cutover plan</strong> — run both systems in parallel for one pay cycle, reconcile, then switch. Most teams complete migration in under 2 weeks.
            </li>
          </ol>
          <p className="text-body-sm text-fg-muted mt-3">
            Need help? Our onboarding team will map your fields and handle the import for you.
          </p>
        </div>
      </section>

      {/* Competitor switcher */}
      <section className="max-w-container mx-auto px-4 sm:px-6 lg:px-8 pb-4">
        <div className="flex flex-wrap gap-3">
          {Object.entries(COMPETITORS).map(([k, v]) => (
            <Link
              key={k}
              to={`/compare/${k}`}
              className={k === key ? "mk-cta !py-2 !px-4 text-sm" : "mk-ghost !py-2 !px-4 text-sm"}
            >
              vs {v.label}
            </Link>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-container mx-auto px-4 sm:px-6 lg:px-8 pb-12">
        <div className="mk-card mk-card-flat p-6 md:p-8 text-center mk-reveal">
          <h2 className="mk-h2 font-semibold text-fg">See Karmathy in action</h2>
          <p className="text-body-sm text-fg-muted mt-2">A 20-minute walkthrough tailored to your team.</p>
          <Link to="/contact" className="mk-cta mt-4">
            Request a demo →
          </Link>
        </div>
      </section>
    </PublicLayout>
  )
}
