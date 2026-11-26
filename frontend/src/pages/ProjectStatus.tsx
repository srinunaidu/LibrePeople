/**
 * Project Status — the single source of truth, browsable.
 *
 * Renders `frontend/src/lib/projectStatus.ts` — the canonical data.
 * Token-driven obsidian styling: var(--surface), var(--border), var(--accent), var(--status-*)
 * Compact cards, tabular-nums, no hardcoded hex or inline style double-brace.
 *
 * Read-only. No mutation. No backend fetch.
 */
import { useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { Layout } from "@/components/Layout"
import { PageHeader } from "@/components/ui/layout"
import { Table } from "@/components/ui"
import { useTenantNav } from "@/lib/tenantPath"
import { cn } from "@/lib/utils"
import {
  HEALTH,
  GATES,
  PHASES,
  DEPLOYS,
  REFERENCES,
  type TaskStatus,
  type PhaseStatus,
  type GateStatus,
} from "@/lib/projectStatus"

// ---------------------------------------------------------------------------
// Badge — token-driven, no inline style
// ---------------------------------------------------------------------------
const PHASE_TONE: Record<PhaseStatus, string> = {
  done: "bg-[var(--success-light)] text-[var(--success-text)] border border-[var(--success-border)]",
  running: "bg-[var(--warning-light)] text-[var(--warning-text)] border border-[var(--warning-border)]",
  pending: "bg-[var(--surface-inset)] text-[var(--fg-muted)] border border-[var(--border-default)]",
}

const TASK_TONE: Record<TaskStatus, string> = {
  done: "bg-[var(--success-light)] text-[var(--success-text)] border border-[var(--success-border)]",
  running: "bg-[var(--warning-light)] text-[var(--warning-text)] border border-[var(--warning-border)]",
  pending: "bg-[var(--surface-inset)] text-[var(--fg-muted)] border border-[var(--border-default)]",
  open: "bg-[var(--surface-inset)] text-[var(--fg-muted)] border border-[var(--border-default)]",
}

const GATE_TONE: Record<GateStatus, string> = {
  pass: "bg-[var(--success-light)] text-[var(--success-text)] border border-[var(--success-border)]",
  open: "bg-[var(--surface-inset)] text-[var(--fg-muted)] border border-[var(--border-default)]",
}

function Badge({
  tone,
  children,
}: {
  tone: string
  children: React.ReactNode
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded px-2 py-0.5 text-xs font-semibold whitespace-nowrap",
        tone
      )}
    >
      {children}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function ProjectStatus() {
  const tenantNav = useTenantNav()
  const [filter, setFilter] = useState<TaskStatus | "all">("all")
  const [phaseFilter, setPhaseFilter] = useState<PhaseStatus | "all">("all")

  const filtered = useMemo(() => {
    if (phaseFilter === "all") return PHASES
    return PHASES.filter((p) => p.status === phaseFilter)
  }, [phaseFilter])

  const counts = useMemo(() => {
    const all = PHASES.flatMap((p) => p.tasks)
    return {
      done: all.filter((t) => t.status === "done").length,
      running: all.filter((t) => t.status === "running").length,
      pending: all.filter((t) => t.status === "pending").length,
      open: all.filter((t) => t.status === "open").length,
      total: all.length,
    }
  }, [])

  const now = new Date().toISOString().replace("T", " ").slice(0, 16) + " UTC"
  const commit = "95d9cbd"

  const codeCls = "bg-[var(--surface-elevated)] px-1 py-0.5 rounded text-xs border border-[var(--border)]"
  const linkCls = "text-[var(--brand-text)] hover:underline"
  const h2Cls = "text-lg font-bold mt-6 mb-1 pt-1 text-[var(--fg)]"

  return (
    <Layout>
      <div className="max-w-[900px] mx-auto px-4">
        <h1 className="text-xl font-bold mt-5 mb-1 text-[var(--fg)] tabular-nums">
          LibrePeople HCM — Project Status
        </h1>
        <p className="text-sm text-[var(--fg-muted)] m-0 tabular-nums">
          Rendered {now} · commit <code className={codeCls}>{commit}</code> on <code className={codeCls}>main</code> ·{" "}
          <Link to={tenantNav.to("/dashboard")} className={linkCls}>
            ← back to dashboard
          </Link>
        </p>
        <p className="text-sm text-[var(--fg-muted)] mt-1">
          Single source: <code className={codeCls}>frontend/src/lib/projectStatus.ts</code> — edit there; this page and{" "}
          <code className={codeCls}>STATUS.md</code> follow it.
        </p>

        {/* Health */}
        <h2 className={h2Cls}>Health</h2>
        <ul className="text-sm leading-6 pl-5 my-2 list-disc marker:text-[var(--fg-muted)]">
          {HEALTH.map((h) => (
            <li key={h.label}>
              {h.label}: <strong className="text-[var(--fg)]">{h.value}</strong>
              {h.detail ? <span className="text-[var(--fg-muted)]"> · {h.detail}</span> : null}
            </li>
          ))}
        </ul>
        <p className="text-sm text-[var(--fg-muted)] mt-2">
          Spec order of work: <strong className="text-[var(--fg)]">security → contracts → import → core HCM → forecasting → payroll → experience → AI → release</strong>.
          No phase starts until its gate passes. Phases 8 (AI) and the remaining hardening in Phase 9 are explicitly deferred — not debt.
        </p>

        {/* Gates */}
        <h2 className={h2Cls}>Gates</h2>
        <ul className="list-none p-0 my-2 space-y-1">
          {GATES.map((g) => (
            <li key={g.id} className="text-sm leading-6">
              <Badge tone={GATE_TONE[g.status]}>{g.status}</Badge>{" "}
              <strong className="text-[var(--fg)]">{g.label}</strong>: <span className="text-[var(--fg-muted)]">{g.detail}</span>
            </li>
          ))}
        </ul>

        {/* Filter bar */}
        <div className="flex flex-wrap gap-2 items-center mt-4 mb-1 text-sm">
          <span className="text-[var(--fg-muted)] tabular-nums">
            {counts.done} done · {counts.open} open · {counts.pending} pending · {counts.running} running · {counts.total} total
          </span>
          <span className="ml-auto inline-flex gap-1.5 flex-wrap">
            {(["all", "done", "open", "pending", "running"] as const).map((s) => (
              <button
                key={s}
                onClick={() => setFilter(s)}
                className={cn(
                  "rounded px-2 py-0.5 text-xs font-medium border transition-colors",
                  filter === s
                    ? "bg-[var(--brand-700)] border-[var(--brand-700)] text-white"
                    : "bg-[var(--surface)] border-[var(--border)] text-[var(--fg-muted)] hover:bg-[var(--surface-hover)]"
                )}
              >
                {s}
              </button>
            ))}
            <span className="w-2" />
            {(["all", "done", "running", "pending"] as const).map((s) => (
              <button
                key={`p-${s}`}
                onClick={() => setPhaseFilter(s)}
                className={cn(
                  "rounded px-2 py-0.5 text-xs font-medium border transition-colors",
                  phaseFilter === s
                    ? "bg-[var(--brand-700)] border-[var(--brand-700)] text-white"
                    : "bg-[var(--surface)] border-[var(--border)] text-[var(--fg-muted)] hover:bg-[var(--surface-hover)]"
                )}
              >
                phase:{s}
              </button>
            ))}
          </span>
        </div>

        {/* Phases */}
        <h2 className={h2Cls}>Phases</h2>
        {filtered.map((phase) => {
          const tasks =
            filter === "all" ? phase.tasks : phase.tasks.filter((t) => t.status === filter)
          const visible = tasks.length
          return (
            <section
              key={phase.id}
              className="border-t border-[var(--border)] pt-3 mt-3 bg-[var(--surface)] rounded-[var(--radius-md)] p-3"
            >
              <h3 className="text-base font-bold m-0 mb-1 flex items-center gap-2 flex-wrap text-[var(--fg)]">
                <Badge tone={PHASE_TONE[phase.status]}>{phase.status}</Badge>
                {phase.title}
                {visible !== phase.tasks.length ? (
                  <span className="text-xs text-[var(--fg-muted)] font-normal tabular-nums">
                    ({visible}/{phase.tasks.length} tasks match filter)
                  </span>
                ) : null}
              </h3>
              <p className="text-sm text-[var(--fg-muted)] mb-2">
                <code className={codeCls}>{phase.code}</code> — {phase.gate}
              </p>
              {visible === 0 ? (
                <p className="text-sm text-[var(--fg-muted)] italic">No tasks match the current filter.</p>
              ) : (
                <ul className="text-sm leading-6 pl-5 my-1 list-disc marker:text-[var(--fg-muted)]">
                  {tasks.map((t) => (
                    <li key={t.id} className="mb-0.5">
                      <Badge tone={TASK_TONE[t.status]}>{t.status}</Badge>{" "}
                      <code className={codeCls}>{t.id}</code> — <span className="text-[var(--fg)]">{t.detail}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )
        })}

        {/* Deploys */}
        <h2 className={h2Cls}>Deploys — last 5</h2>
        <Table
            columns={[
              { key: "time", header: "Time", accessor: (d) => <span className="text-[var(--fg-muted)]">{d.time}</span> },
              { key: "commit", header: "Commit", accessor: (d) => <code className={codeCls}>{d.commit}</code> },
              { key: "notes", header: "Notes", accessor: (d) => <span className="text-[var(--fg)]">{d.notes}</span> },
            ]}
            data={DEPLOYS.map((d, i) => ({ ...d, _k: i }))}
            keyAccessor={(d) => d._k}
            caption="Deploys — last 5"
            sortable={false}
          />

        {/* References */}
        <h2 className={h2Cls}>References</h2>
        <ul className="text-sm leading-7 pl-5 my-2 mb-8 list-disc marker:text-[var(--fg-muted)]">
          {REFERENCES.map((r) => (
            <li key={r.path}>
              <code className={codeCls}>{r.path}</code> — <span className="text-[var(--fg-muted)]">{r.desc}</span>
            </li>
          ))}
        </ul>
      </div>
    </Layout>
  )
}
