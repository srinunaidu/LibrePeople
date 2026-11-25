import { useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {
  Alert,
  EmptyState,
  LoadingRegion,
  PageHeader,
  SectionCard,
  KPICard,
  StatCard,
} from "@/components/ui"
import { NeedsAction, type NeedItem } from "@/components/home/NeedsAction"
import {
  IconCalendar,
  IconChart,
  IconCheck,
  IconClock,
  IconTarget,
  IconUsers,
  IconTrendingUp,
} from "@/components/icons"
import api from "@/lib/api"
import { StatusPill } from "@/components/ui/status-pill"

interface LeaveReq { id: number; employee_id: number; status: string; working_days: number; start_date: string; end_date: string }
interface Timesheet { id: number; employee_id: number; status: string; total_hours: number; period_start: string; period_end: string }
interface ShiftSwap { id: number; requester_id: number; status: string; roster_entry_id: number }
interface Goal { id: number; title: string; progress: number; status: string }
interface Review { id: number; period: string; status: string; overall_rating?: number }

const mockSparklineData = [8, 12, 10, 15, 13, 18, 16, 20, 18, 22, 20, 24]
const mockLeaveSparkline = [3, 5, 4, 6, 5, 7, 6, 8, 7, 9, 8, 10]
const mockTimesheetSparkline = [12, 15, 13, 18, 16, 20, 18, 22, 20, 24, 22, 26]

export default function ManagerHome() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [leaveReqs, setLeaveReqs] = useState<LeaveReq[]>([])
  const [timesheets, setTimesheets] = useState<Timesheet[]>([])
  const [swaps, setSwaps] = useState<ShiftSwap[]>([])
  const [goals, setGoals] = useState<Goal[]>([])
  const [reviews, setReviews] = useState<Review[]>([])
  const [presentToday, setPresentToday] = useState(0)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const [lr, ts, ss, g, rv, att] = await Promise.all([
          api.get("/leave/requests").catch(() => ({ data: [] })),
          api.get("/time/timesheets").catch(() => ({ data: [] })),
          api.get("/scheduling/swaps").catch(() => ({ data: [] })),
          api.get("/performance/goals").catch(() => ({ data: [] })),
          api.get("/performance/reviews").catch(() => ({ data: [] })),
          api.get("/time/today").catch(() => ({ data: { present: 0 } })),
        ])
        if (cancelled) return
        setLeaveReqs(lr.data || [])
        setTimesheets(ts.data || [])
        setSwaps(ss.data || [])
        setGoals(g.data || [])
        setReviews(rv.data || [])
        setPresentToday(att.data?.present ?? 0)
      } catch {
        if (!cancelled) setError("We couldn't load your team workspace.")
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const pendingLeave = leaveReqs.filter((r) => r.status === "Pending").length
  const pendingTimesheets = timesheets.filter((t) => t.status === "Submitted").length
  const pendingSwaps = swaps.filter((s) => s.status === "Pending").length
  const pendingGoals = goals.filter((g) => g.status === "In Progress").length
  const pendingReviews = reviews.filter((r) => r.status === "In Progress" || r.status === "Draft").length
  const totalActions = pendingLeave + pendingTimesheets + pendingSwaps + pendingGoals + pendingReviews

  const needs: NeedItem[] = [
    { id: "leave", label: "Leave requests awaiting approval", count: pendingLeave, description: "Approve or reject team leave requests", actionLabel: "Review", onAction: () => { window.location.href = "/leave" }, tone: "amber" },
    { id: "timesheets", label: "Timesheets to approve", count: pendingTimesheets, description: "Submitted timesheets needing your sign-off", actionLabel: "Review", onAction: () => { window.location.href = "/time" }, tone: "amber" },
    { id: "swaps", label: "Shift swap requests", count: pendingSwaps, description: "Team members requesting shift changes", actionLabel: "Review", onAction: () => { window.location.href = "/scheduling" }, tone: "amber" },
    { id: "goals", label: "Goals in progress", count: pendingGoals, description: "Team goals needing updates", actionLabel: "View", onAction: () => { window.location.href = "/platform" }, tone: "brand" },
    { id: "reviews", label: "Reviews pending", count: pendingReviews, description: "Performance reviews to complete", actionLabel: "View", onAction: () => { window.location.href = "/platform" }, tone: "violet" },
  ]

  if (loading) {
    return (
      <Layout>
        <PageHeader icon={<IconUsers />} title="My Team" description="Your team's workspace." />
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
        icon={<IconUsers />}
        title="My Team"
        description="Approvals, team attendance, goals and upcoming reviews."
      />

      {error && <Alert tone="error">{error}</Alert>}

      {needs.length > 0 && <NeedsAction title="Needs your action" items={needs} emptyMessage="No pending approvals or actions." />}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-0">
        <KPICard
          label="Pending Actions"
          value={totalActions}
          hint="Leave, timesheets, swaps, goals, reviews"
          icon={<IconCheck className="w-5 h-5" />}
          tone="brand"
          sparklineData={mockSparklineData}
          trendValue={15}
          trendLabel="vs last month"
        />
        <KPICard
          label="Present Today"
          value={presentToday}
          hint="Team attendance"
          icon={<IconUsers className="w-5 h-5" />}
          tone="green"
          sparklineData={mockTimesheetSparkline}
          trendValue={8}
          trendLabel="vs avg"
        />
        <KPICard
          label="Team Goals"
          value={goals.length}
          hint={`${pendingGoals} in progress`}
          icon={<IconTarget className="w-5 h-5" />}
          tone="violet"
          sparklineData={[goals.length - 2, goals.length - 1, goals.length, goals.length + 1]}
          trendValue={12}
          trendLabel="completion rate"
        />
        <KPICard
          label="Reviews"
          value={reviews.length}
          hint={`${pendingReviews} pending`}
          icon={<IconChart className="w-5 h-5" />}
          tone="amber"
          sparklineData={mockLeaveSparkline}
          trendValue={-5}
          trendLabel="overdue"
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <SectionCard icon={<IconClock />} title="Approvals inbox" description="Items waiting for your decision.">
          {leaveReqs.length + timesheets.length + swaps.length === 0 ? (
            <EmptyState title="Inbox empty" description="No pending approvals at this time." />
          ) : (
            <ul className="divide-y divide-border-subtle">
              {leaveReqs.filter((r) => r.status === "Pending").slice(0, 5).map((r) => (
                <li key={`l-${r.id}`} className="flex items-center gap-3 px-5 py-3 hover:bg-surface-hover">
                  <span className="badge badge-amber shrink-0">Leave</span>
                  <span className="text-sm text-fg flex-1">Employee #{r.employee_id} · {r.working_days}d</span>
                  <button className="action-link" onClick={() => { window.location.href = "/leave" }}>Review</button>
                </li>
              ))}
              {timesheets.filter((t) => t.status === "Submitted").slice(0, 5).map((t) => (
                <li key={`t-${t.id}`} className="flex items-center gap-3 px-5 py-3 hover:bg-surface-hover">
                  <span className="badge badge-brand shrink-0">Timesheet</span>
                  <span className="text-sm text-fg flex-1">Employee #{t.employee_id} · {t.total_hours}h</span>
                  <button className="action-link" onClick={() => { window.location.href = "/time" }}>Review</button>
                </li>
              ))}
              {swaps.filter((s) => s.status === "Pending").slice(0, 5).map((s) => (
                <li key={`s-${s.id}`} className="flex items-center gap-3 px-5 py-3 hover:bg-surface-hover">
                  <span className="badge badge-violet shrink-0">Swap</span>
                  <span className="text-sm text-fg flex-1">Roster #{s.roster_entry_id}</span>
                  <button className="action-link" onClick={() => { window.location.href = "/scheduling" }}>Review</button>
                </li>
              ))}
            </ul>
          )}
        </SectionCard>

        <SectionCard icon={<IconTarget />} title="Team goals" description="Progress across your team's objectives.">
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
