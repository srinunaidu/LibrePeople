import { Layout } from "@/components/Layout"
import { PageHeader, SectionCard, KPICard } from "@/components/ui"
import { IconChart, IconUsers, IconClock, IconPalm } from "@/components/icons"
import { NextBestActionCards, deriveActionCards } from "@/components/home/NextBestActionCards"
import { useNavigate } from "react-router-dom"
import { useTenantNav } from "@/lib/tenantPath"
import { useEffect, useState } from "react"
import api from "@/lib/api"

/**
 * Generic fallback dashboard for users without a specific role mapping.
 * Shows the standard overview cards. Action counts are live from API with
 * fallback to 0; deriveActionCards remains pure for unit tests.
 */
export default function DashboardFallback() {
  const navigate = useNavigate()
  const tenantNav = useTenantNav()
  const [counts, setCounts] = useState({ pendingApprovals: 0, unfilledShifts: 0, upcomingDeadlines: 0 })

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const [leaveRes, shiftsRes, deadlinesRes] = await Promise.all([
          api.get("/leave/requests").catch(() => ({ data: [] })),
          api.get("/scheduling/roster").catch(() => ({ data: [] })),
          api.get("/reports/audit?limit=50").catch(() => ({ data: [] })),
        ])
        if (cancelled) return
        const pending = Array.isArray(leaveRes.data)
          ? leaveRes.data.filter((r: any) => r.status === "Pending" || r.status === "pending").length
          : 0
        const unfilled = Array.isArray(shiftsRes.data)
          ? shiftsRes.data.filter((s: any) => !s.assigned_to && !s.employee_id).length
          : 0
        const deadlines = Array.isArray(deadlinesRes.data)
          ? deadlinesRes.data.filter((d: any) => {
              const due = d.due_date || d.deadline || d.created_at
              if (!due) return false
              const diff = new Date(due).getTime() - Date.now()
              return diff >= 0 && diff <= 7 * 24 * 60 * 60 * 1000
            }).length
          : 0
        setCounts({ pendingApprovals: pending, unfilledShifts: unfilled, upcomingDeadlines: deadlines })
      } catch {
        if (!cancelled) setCounts({ pendingApprovals: 0, unfilledShifts: 0, upcomingDeadlines: 0 })
      }
    }
    void load()
    return () => { cancelled = true }
  }, [])

  const actionCards = deriveActionCards({
    pendingApprovals: counts.pendingApprovals,
    unfilledShifts: counts.unfilledShifts,
    upcomingDeadlines: counts.upcomingDeadlines,
    onApprovals: () => navigate(tenantNav.to("/leave")),
    onShifts: () => navigate(tenantNav.to("/scheduling")),
    onDeadlines: () => navigate(tenantNav.to("/reports")),
  })

  return (
    <Layout>
      <PageHeader
        compact
        icon={<IconChart />}
        title="Dashboard"
        description="Welcome to LibrePeople HCM. Select a module from the workspace rail to get started."
      />
      <NextBestActionCards cards={actionCards} />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KPICard
          label="Employees"
          value="—"
          hint="Connect HR data"
          icon={<IconUsers className="w-5 h-5" />}
          tone="brand"
        />
        <KPICard
          label="Time Entries"
          value="—"
          hint="Clock in to start"
          icon={<IconClock className="w-5 h-5" />}
          tone="green"
        />
        <KPICard
          label="Leave Balance"
          value="—"
          hint="Request leave"
          icon={<IconPalm className="w-5 h-5" />}
          tone="amber"
        />
        <KPICard
          label="Tasks"
          value="—"
          hint="No pending items"
          icon={<IconChart className="w-5 h-5" />}
          tone="violet"
        />
      </div>
      <div className="card p-8 text-center">
        <IconUsers className="w-12 h-12 mx-auto text-fg-muted mb-4" />
        <h2 className="text-h3-app text-fg mb-2">Welcome!</h2>
        <p className="text-sm text-fg-muted max-w-md mx-auto">
          Use the navigation on the left to explore the platform. Start with
          People, Time, Leave, or Reports.
        </p>
        <div className="flex flex-wrap justify-center gap-x-4 gap-y-2 mt-4 text-sm">
          <button className="action-link" onClick={() => navigate(tenantNav.to("/people"))}>People</button>
          <button className="action-link" onClick={() => navigate(tenantNav.to("/time"))}>Time</button>
          <button className="action-link" onClick={() => navigate(tenantNav.to("/leave"))}>Leave</button>
          <button className="action-link" onClick={() => navigate(tenantNav.to("/reports"))}>Reports</button>
        </div>
      </div>
    </Layout>
  )
}
