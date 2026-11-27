import { useCallback, useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useTenantNav } from "@/lib/tenantPath"
import { Layout } from "@/components/Layout"
import {
  Alert,
  Button,
  EmptyState,
  LoadingRegion,
  PageHeader,
  SectionCard,
  KPICard,
  StatusPill } from "@/components/ui"
import { NeedsAction, type NeedItem } from "@/components/home/NeedsAction"
import {
  IconChart,
  IconCheck,
  IconClock,
  IconTarget,
  IconUsers,
} from "@/components/icons"
import api from "@/lib/api"
interface LeaveReq { id: number; employee_id: number; status: string; working_days: number; start_date: string; end_date: string }
interface Timesheet { id: number; employee_id: number; status: string; total_hours: number; period_start: string; period_end: string }
interface ShiftSwap { id: number; requester_id: number; status: string; roster_entry_id: number }
interface Goal { id: number; title: string; progress: number; status: string }
interface Review { id: number; period: string; status: string; overall_rating?: number }

// D3 (portals-completion): no sparkline/trend props on portal KPIs — there is
// no backend aggregation for deltas, so every KPI shows a live value + hint.
// Timesheet reject is INCOMPLETE: backend exposes only
// POST /time/timesheets/{id}/approve (time_attendance.py), no reject route.

export default function ManagerHome() {
  const navigate = useNavigate()
  const tenantNav = useTenantNav()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [busy, setBusy] = useState("")
  const [leaveReqs, setLeaveReqs] = useState<LeaveReq[]>([])
  const [timesheets, setTimesheets] = useState<Timesheet[]>([])
  const [swaps, setSwaps] = useState<ShiftSwap[]>([])
  const [goals, setGoals] = useState<Goal[]>([])
  const [reviews, setReviews] = useState<Review[]>([])
  const [presentToday, setPresentToday] = useState(0)

  const load = useCallback(async (initial = false) => {
    if (initial) setLoading(true)
    try {
      const [lr, ts, ss, g, rv, att] = await Promise.all([
        api.get("/leave/requests").catch(() => ({ data: [] })),
        api.get("/time/timesheets").catch(() => ({ data: [] })),
        api.get("/scheduling/swaps").catch(() => ({ data: [] })),
        api.get("/performance/goals").catch(() => ({ data: [] })),
        api.get("/performance/reviews").catch(() => ({ data: [] })),
        api.get("/time/today").catch(() => ({ data: { present: 0 } })),
      ])
      setLeaveReqs(lr.data || [])
      setTimesheets(ts.data || [])
      setSwaps(ss.data || [])
      setGoals(g.data || [])
      setReviews(rv.data || [])
      setPresentToday(att.data?.present ?? 0)
    } catch {
      setError("We couldn't load your team workspace.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load(true) }, [load])

  // Inline decide: approve/reject without a full-page reload; the list
  // refreshes in place so the manager stays on the portal.
  const decide = async (key: string, fn: () => Promise<unknown>, msg: string) => {
    if (busy) return
    setBusy(key)
    setError("")
    setNotice("")
    try {
      await fn()
      setNotice(msg)
      await load()
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Decision failed. Please try again.")
    } finally {
      setBusy("")
    }
  }

  const pendingLeave = leaveReqs.filter((r) => r.status === "Pending").length
  const pendingTimesheets = timesheets.filter((t) => t.status === "Submitted").length
  const pendingSwaps = swaps.filter((s) => s.status === "Pending").length
  const pendingGoals = goals.filter((g) => g.status === "In Progress").length
  const pendingReviews = reviews.filter((r) => r.status === "In Progress" || r.status === "Draft").length
  const totalActions = pendingLeave + pendingTimesheets + pendingSwaps + pendingGoals + pendingReviews

  const needs: NeedItem[] = [
    { id: "leave", label: "Leave requests awaiting approval", count: pendingLeave, description: "Approve or reject team leave requests", actionLabel: "Review", onAction: () => { navigate(tenantNav.to("/leave")) }, tone: "amber" },
    { id: "timesheets", label: "Timesheets to approve", count: pendingTimesheets, description: "Submitted timesheets needing your sign-off", actionLabel: "Review", onAction: () => { navigate(tenantNav.to("/time")) }, tone: "amber" },
    { id: "swaps", label: "Shift swap requests", count: pendingSwaps, description: "Team members requesting shift changes", actionLabel: "Review", onAction: () => { navigate(tenantNav.to("/scheduling")) }, tone: "amber" },
    { id: "goals", label: "Goals in progress", count: pendingGoals, description: "Team goals needing updates", actionLabel: "View", onAction: () => { navigate(tenantNav.to("/platform/performance")) }, tone: "brand" },
    { id: "reviews", label: "Reviews pending", count: pendingReviews, description: "Performance reviews to complete", actionLabel: "View", onAction: () => { navigate(tenantNav.to("/platform/performance")) }, tone: "violet" },
  ]

  if (loading) {
    return (
      <Layout>
        <PageHeader compact icon={<IconUsers />} title="My Team" description="Your team's workspace." />
        <LoadingRegion label="Loading team data">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-0">
            {Array.from({ length: 8 }).map((_, i) => <div key={i} className="skeleton h-28" />)}
          </div>
        </LoadingRegion>
      </Layout>
    )
  }

  return (
    <Layout>
      <PageHeader
        compact
        icon={<IconUsers />}
        title="My Team"
        description="Approvals, team attendance, goals and upcoming reviews."
      />

      {error && <Alert tone="error">{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}

      {needs.length > 0 && <NeedsAction title="Needs your action" items={needs} emptyMessage="No pending approvals or actions." />}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-0">
        <KPICard
          label="Pending Actions"
          value={totalActions}
          hint="Leave, timesheets, swaps, goals, reviews"
          icon={<IconCheck className="w-5 h-5" />}
          tone="brand"
        />
        <KPICard
          label="Present Today"
          value={presentToday}
          hint="Team attendance today"
          icon={<IconUsers className="w-5 h-5" />}
          tone="green"
        />
        <KPICard
          label="Team Goals"
          value={goals.length}
          hint={`${pendingGoals} in progress`}
          icon={<IconTarget className="w-5 h-5" />}
          tone="violet"
        />
        <KPICard
          label="Reviews"
          value={reviews.length}
          hint={`${pendingReviews} pending`}
          icon={<IconChart className="w-5 h-5" />}
          tone="amber"
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <SectionCard compact icon={<IconClock />} title="Approvals inbox" description="Items waiting for your decision — approve inline or open the full list.">
          {leaveReqs.length + timesheets.length + swaps.length === 0 ? (
            <EmptyState title="Inbox empty" description="No pending approvals at this time." />
          ) : (
            <ul className="divide-y divide-border-subtle">
              {leaveReqs.filter((r) => r.status === "Pending").slice(0, 5).map((r) => (
                <li key={`l-${r.id}`} className="flex items-center gap-3 px-5 py-3 hover:bg-surface-hover">
                  <span className="badge badge-amber shrink-0">Leave</span>
                  <span className="text-sm text-fg flex-1">Employee #{r.employee_id} · {r.working_days}d</span>
                  <Button size="xs" variant="secondary" disabled={!!busy} onClick={() => decide(`al-${r.id}`, () => api.post(`/leave/requests/${r.id}/approve`), `Leave request #${r.id} approved.`)}>Approve</Button>
                  <Button size="xs" variant="ghost" disabled={!!busy} onClick={() => decide(`rl-${r.id}`, () => api.post(`/leave/requests/${r.id}/reject`), `Leave request #${r.id} rejected.`)}>Reject</Button>
                  <button className="action-link" onClick={() => { navigate(tenantNav.to("/leave")) }}>Review</button>
                </li>
              ))}
              {timesheets.filter((t) => t.status === "Submitted").slice(0, 5).map((t) => (
                <li key={`t-${t.id}`} className="flex items-center gap-3 px-5 py-3 hover:bg-surface-hover">
                  <span className="badge badge-brand shrink-0">Timesheet</span>
                  <span className="text-sm text-fg flex-1">Employee #{t.employee_id} · {t.total_hours}h</span>
                  <Button size="xs" variant="secondary" disabled={!!busy} onClick={() => decide(`at-${t.id}`, () => api.post(`/time/timesheets/${t.id}/approve`), `Timesheet #${t.id} approved.`)}>Approve</Button>
                  <button className="action-link" onClick={() => { navigate(tenantNav.to("/time")) }}>Review</button>
                </li>
              ))}
              {swaps.filter((s) => s.status === "Pending").slice(0, 5).map((s) => (
                <li key={`s-${s.id}`} className="flex items-center gap-3 px-5 py-3 hover:bg-surface-hover">
                  <span className="badge badge-violet shrink-0">Swap</span>
                  <span className="text-sm text-fg flex-1">Roster #{s.roster_entry_id}</span>
                  <Button size="xs" variant="secondary" disabled={!!busy} onClick={() => decide(`as-${s.id}`, () => api.post(`/scheduling/swaps/${s.id}/approve`), `Swap #${s.id} approved.`)}>Approve</Button>
                  <Button size="xs" variant="ghost" disabled={!!busy} onClick={() => decide(`rs-${s.id}`, () => api.post(`/scheduling/swaps/${s.id}/reject`), `Swap #${s.id} rejected.`)}>Reject</Button>
                  <button className="action-link" onClick={() => { navigate(tenantNav.to("/scheduling")) }}>Review</button>
                </li>
              ))}
            </ul>
          )}
        </SectionCard>

        <SectionCard compact icon={<IconTarget />} title="Team goals" description="Progress across your team's objectives.">
          {goals.length === 0 ? (
            <EmptyState title="No goals set" description="Create goals to track team progress." />
          ) : (
            <ul className="divide-y divide-border-subtle">
              {goals.slice(0, 6).map((g) => (
                <li key={g.id} className="px-5 py-3">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-sm font-medium text-fg truncate">{g.title}</span>
                    <span className="text-xs text-fg-muted tabular-nums">{g.progress}%</span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-surface-inset overflow-hidden">
                    <div className="h-full rounded-full bg-brand-600 transition-[width]" style={{ width: `${g.progress}%` }} />
                  </div>
                  <StatusPill status={g.status} />
                </li>
              ))}
            </ul>
          )}
        </SectionCard>
      </div>
    </Layout>
  )
}
