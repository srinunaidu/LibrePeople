/**
 * ProductMockup — the flagship "floating dashboard" for the hero.
 *
 * Code-built (no raster art): a glass product window with sidebar, KPI row,
 * approved-time table, and a reconciled payroll panel, wrapped in floating
 * evidence badges. All numbers are illustrative sample data from a mock
 * window — explicitly captioned as such.
 */
export function ProductMockup() {
  return (
    <div className="relative mx-auto max-w-4xl mk-float" data-testid="product-mockup">
      {/* ambient glow under the window */}
      <div
        aria-hidden="true"
        className="absolute -inset-x-10 -top-10 bottom-6 -z-10"
        style={{
          backgroundImage:
            "radial-gradient(560px 260px at 50% 30%, rgba(37,99,235,0.35), transparent 70%), radial-gradient(380px 220px at 22% 90%, rgba(34,211,238,0.22), transparent 70%), radial-gradient(420px 220px at 82% 80%, rgba(139,92,246,0.20), transparent 70%)",
          filter: "blur(6px)",
        }}
      />
      <div className="mk-window">
        {/* window chrome */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-white/10 bg-white/[0.03]">
          <span className="h-2.5 w-2.5 rounded-full bg-[rgba(239,68,68,0.7)]" aria-hidden="true" />
          <span className="h-2.5 w-2.5 rounded-full bg-[var(--amber-300)]" aria-hidden="true" />
          <span className="h-2.5 w-2.5 rounded-full bg-[var(--semantic-status-success)]" aria-hidden="true" />
          <span className="ml-3 text-xs font-medium text-fg-muted">app.karmathy.com — Payroll · November run</span>
          <span className="ml-auto inline-flex items-center gap-1.5 text-xs text-fg-muted">
            <span className="mk-pulse inline-block h-1.5 w-1.5 rounded-full bg-[var(--teal-400)]" aria-hidden="true" />
            Live
          </span>
        </div>

        <div className="grid grid-cols-[7.5rem_1fr] sm:grid-cols-[11rem_1fr]">
          {/* sidebar */}
          <div className="border-r border-white/[0.07] bg-white/[0.02] p-3 sm:p-4 space-y-1">
            <div className="flex items-center gap-2 px-1 pb-3">
              <span
                aria-hidden="true"
                className="grid h-6 w-6 place-items-center rounded-md text-white font-bold text-[0.6rem]"
                style={{ background: "linear-gradient(135deg, #2563EB 0%, #22D3EE 100%)" }}
              >
                K
              </span>
              <span className="hidden sm:block text-sm font-semibold tracking-tight">Karmathy</span>
            </div>
            {[
              { label: "People", active: false },
              { label: "Time", active: true },
              { label: "Leave", active: false },
              { label: "Scheduling", active: false },
              { label: "Payroll", active: false },
              { label: "Reports", active: false },
            ].map((item) => (
              <div
                key={item.label}
                className={`flex items-center gap-2 rounded-md px-2 py-1.5 text-xs font-medium ${
                  item.active
                    ? "bg-brand-600/20 text-brand-soft-fg border border-brand-600/30"
                    : "text-fg-muted border border-transparent"
                }`}
              >
                <span className={`h-1.5 w-1.5 rounded-full ${item.active ? "bg-[var(--semantic-status-info)]" : "bg-[var(--semantic-foreground-muted)]"}`} aria-hidden="true" />
                <span className={item.label === "Payroll" ? "hidden sm:inline" : ""}>{item.label}</span>
              </div>
            ))}
          </div>

          {/* main panel */}
          <div className="p-4 sm:p-5 space-y-4">
            {/* KPI row */}
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: "Headcount", value: "248", sub: "+12 this month" },
                { label: "On leave today", value: "12", sub: "ledger verified" },
                { label: "Unapproved time", value: "0 rows", sub: "cut-off locked" },
              ].map((k) => (
                <div key={k.label} className="rounded-lg border border-white/[0.08] bg-white/[0.04] px-3 py-2.5">
                  <div className="text-[0.65rem] sm:text-xs font-semibold tracking-widest uppercase text-fg-subtle">{k.label}</div>
                  <div className="mt-1 text-lg sm:text-2xl font-bold tracking-tight text-white tabular-nums">{k.value}</div>
                  <div className="text-[0.65rem] sm:text-xs text-fg-subtle">{k.sub}</div>
                </div>
              ))}
            </div>

            {/* payroll reconcile panel */}
            <div className="rounded-lg border border-white/[0.08] bg-white/[0.03] p-3.5">
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs sm:text-sm font-semibold">Reconcile — expected vs paid</p>
                <span className="badge badge-green text-xs">Matched</span>
              </div>
              {/* bar compare */}
              <div className="mt-3 space-y-2">
                <div>
                  <div className="flex justify-between text-[0.65rem] sm:text-xs text-fg-subtle mb-1">
                    <span>Expected net</span>
                    <span className="tabular-nums">example rows shown</span>
                  </div>
                  <div className="h-2 rounded-full bg-white/[0.06] overflow-hidden">
                    <div className="h-full w-4/5 rounded-full" style={{ background: "linear-gradient(90deg, #2563EB, #60A5FA)" }} />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-[0.65rem] sm:text-xs text-fg-subtle mb-1">
                    <span>Calculated paid</span>
                    <span className="tabular-nums">line-by-line match</span>
                  </div>
                  <div className="h-2 rounded-full bg-white/[0.06] overflow-hidden">
                    <div className="h-full w-4/5 rounded-full" style={{ background: "linear-gradient(90deg, #22D3EE, #67E8F9)" }} />
                  </div>
                </div>
              </div>
            </div>

            {/* approved-time table */}
            <div className="rounded-lg border border-white/[0.08] bg-white/[0.02] overflow-hidden">
              <div className="px-3.5 py-2 border-b border-white/[0.07] flex items-center justify-between">
                <p className="text-xs sm:text-sm font-semibold">November timesheet — approved inputs</p>
                <span className="hidden sm:inline text-xs text-fg-subtle">payslip traces to these rows</span>
              </div>
              <table className="w-full text-left">
                <thead>
                  <tr className="text-[0.65rem] sm:text-xs text-fg-subtle border-b border-white/[0.07]">
                    <th scope="col" className="px-3.5 py-2 font-medium">Employee</th>
                    <th scope="col" className="px-3.5 py-2 font-medium hidden sm:table-cell">Type</th>
                    <th scope="col" className="px-3.5 py-2 font-medium">Hours</th>
                    <th scope="col" className="px-3.5 py-2 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody className="text-xs sm:text-sm">
                  {[
                    { name: "TM-001 · Line operator", type: "Overtime", hours: "6.5", ok: true },
                    { name: "TM-002 · Team lead", type: "Regular", hours: "80.0", ok: true },
                    { name: "TM-003 · Cross-midnight", type: "Shift ×2", hours: "7.0", ok: true },
                  ].map((r) => (
                    <tr key={r.name} className="border-b border-white/[0.05] last:border-0">
                      <td className="px-3.5 py-2 text-fg-muted">{r.name}</td>
                      <td className="px-3.5 py-2 text-fg-subtle hidden sm:table-cell">{r.type}</td>
                      <td className="px-3.5 py-2 text-white tabular-nums">{r.hours}</td>
                      <td className="px-3.5 py-2">
                        <span className="inline-flex items-center gap-1 text-[var(--semantic-status-success-border)]">
                          <span className="h-1 w-1 rounded-full bg-[var(--semantic-status-success)]" aria-hidden="true" /> Approved
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <p className="border-t border-white/[0.07] px-4 py-2.5 text-center text-[0.65rem] sm:text-xs text-fg-subtle">
          Illustrative window — sample rows, styled preview of the real interface
        </p>
      </div>

      {/* floating evidence badges */}
      <div className="mk-float-b absolute -left-4 sm:-left-8 top-14 hidden md:block">
        <div className="mk-chip">
          <span className="mk-chip-dot" aria-hidden="true" /> Audit trail — hash-chained
        </div>
      </div>
      <div className="mk-float-b absolute -right-4 sm:-right-8 top-1/3 hidden md:block">
        <div className="mk-chip">
          <span className="mk-chip-dot" style={{ background: "#67e8f9", boxShadow: "0 0 8px rgba(103,232,249,0.9)" }} aria-hidden="true" />
          Payroll reconciled before commit
        </div>
      </div>
      <div className="mk-float-b absolute left-1/4 -bottom-5 hidden md:block">
        <div className="mk-chip">
          <span className="mk-chip-dot" style={{ background: "#c4b5fd", boxShadow: "0 0 8px rgba(196,181,253,0.9)" }} aria-hidden="true" />
          One record per person
        </div>
      </div>
    </div>
  )
}
