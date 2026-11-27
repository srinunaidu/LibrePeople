import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useTenantNav } from "@/lib/tenantPath"
import { fetchAllEmployees } from "@/lib/employees"
import { Layout } from "@/components/Layout"
import {
  Alert,
  EmptyState,
  LoadingRegion,
  PageHeader,
  SectionCard,
  KPICard,
  Button,
} from "@/components/ui"
import { NeedsAction, type NeedItem } from "@/components/home/NeedsAction"
import { formatCurrency } from "@/lib/format"
import {
  IconCalendar,
  IconCheck,
  IconClock,
  IconFile,
  IconInbox,
  IconPalm,
  IconSparkle,
  IconWallet,
} from "@/components/icons"
import api from "@/lib/api"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import { StatusPill } from "@/components/ui/status-pill"

interface LeaveBalance { available_days: number; leave_type_name?: string; entitlement_year: number }
interface RosterEntry { id: number; work_date: string; start_time: string; end_time: string; status: string }
interface Payslip { id: number; period_start: string; period_end: string; net_pay?: number; status: string }
interface OnboardingTask { id: number; title: string; status: string; due_date?: string }
interface Announcement { id: number; title: string; content: string; priority?: string; category?: string; published_at?: string }

// D3 (portals-completion): no sparkline/trend props on portal KPIs — there is
// no backend aggregation for deltas, so every KPI shows a live value + hint.

export default function AssociateHome() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const navigate = useNavigate()
  const tenantNav = useTenantNav()
  const localeOpts = { locale: tenant?.locale, timeZone: tenant?.timezone }
  const currency = tenant?.currency || undefined
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [clockedIn, setClockedIn] = useState(false)
  const [clocking, setClocking] = useState(false)
  // The associate's own employee record. Clock in/out is per employee
  // (`ClockIn.employee_id` is required, time_attendance.py:39), so the id has
  // to come from the list this screen already loads — posting `{}` is a 422.
  const [employeeId, setEmployeeId] = useState<number | null>(null)
  const [balances, setBalances] = useState<LeaveBalance[]>([])
  const [shifts, setShifts] = useState<RosterEntry[]>([])
  const [payslips, setPayslips] = useState<Payslip[]>([])
  const [tasks, setTasks] = useState<OnboardingTask[]>([])
  const [announcements, setAnnouncements] = useState<Announcement[]>([])

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const { items: employees } = await fetchAllEmployees()
        const me = employees.find(
          (e: any) => e.email === user?.email || e.employee_id === user?.username
        )
        const empId = me?.id
        if (empId) setEmployeeId(empId)

        const fetches: Promise<any>[] = [
          api.get("/leave/balances").catch(() => ({ data: [] })),
          api.get("/scheduling/roster").catch(() => ({ data: [] })),
          api.get("/payroll/payslips").catch(() => ({ data: [] })),
          api.get("/ess/announcements").catch(() => ({ data: [] })),
        ]
        if (empId) fetches.push(api.get(`/onboarding/${empId}/tasks`).catch(() => ({ data: [] })))
        const [b, r, p, a, t] = await Promise.all(fetches)
        if (cancelled) return
        setBalances(b.data || [])
        setShifts(r.data || [])
        setPayslips(p.data || [])
        setAnnouncements(a.data || [])
        if (t) setTasks(t.data || [])
      } catch {
        if (!cancelled) setError("We couldn't load your workspace. Please try again.")
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [user])

  const clockAction = async (action: "in" | "out") => {
    if (!employeeId) {
      setError(
        "No employee record is linked to your account, so the clock cannot be punched. Ask HR to connect your login to your employee record.",
      )
      return
    }
    setClocking(true)
    try {
      await api.post(action === "in" ? "/time/clock-in" : "/time/clock-out", {
        employee_id: employeeId,
      })
      setClockedIn(action === "in")
    } catch {
      setError("Clock action failed. Please try again.")
    } finally {
      setClocking(false)
    }
  }

  const myBalances = balances.filter((b) => b.available_days > 0)
  const upcomingShifts = shifts.slice(0, 5)
  const pendingTasks = tasks.filter((t) => t.status !== "Completed")
  const totalLeaveDays = myBalances.reduce((sum, b) => sum + b.available_days, 0)
  const upcomingShiftsCount = upcomingShifts.length

  const needs: NeedItem[] = ([
    {
      id: "tasks",
      label: "Onboarding tasks to complete",
      count: pendingTasks.length,
      description: "New-hire checklist items pending your attention",
      actionLabel: "Open",
      onAction: () => { navigate(tenantNav.to("/onboarding")) },
      icon: <IconCheck className="w-4 h-4" />,
      tone: "amber" as const,
    },
  ] as NeedItem[]).filter((i) => i.count > 0)

  if (loading) {
    return (
      <Layout>
        <PageHeader compact icon={<IconSparkle />} title="My Work" description="Your personal workspace." />
        <LoadingRegion label="Loading your workspace">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-0">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="skeleton h-28" />
            ))}
          </div>
        </LoadingRegion>
      </Layout>
    )
  }

  return (
    <Layout>
      <PageHeader
        compact
        icon={<IconSparkle />}
        title={`Good ${greeting()}, ${user?.username || "there"}`}
        description="Your personal workspace — clock, leave, shifts, payslips and tasks."
      />

      {error && <Alert tone="error">{error}</Alert>}

      {needs.length > 0 && <NeedsAction items={needs} />}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-0">
        <KPICard
          label="Total Leave Balance"
          value={totalLeaveDays}
          hint={`${myBalances.length} leave types`}
          icon={<IconPalm className="w-5 h-5" />}
          tone="green"
          className="mk-reveal-d1"
        />
        <KPICard
          label="Upcoming Shifts"
          value={upcomingShiftsCount}
          hint="Next 7 days"
          icon={<IconCalendar className="w-5 h-5" />}
          tone="brand"
          className="mk-reveal-d2"
        />
        <KPICard
          label="Clock Status"
          value={clockedIn ? "Clocked In" : "Clocked Out"}
          hint={clockedIn ? "Currently clocked in" : "Ready to start"}
          icon={<IconClock className="w-5 h-5" />}
          tone={clockedIn ? "green" : "slate"}
          className="mk-reveal-d1"
        />
        <KPICard
          label="Pending Tasks"
          value={pendingTasks.length}
          hint={`${tasks.length} total tasks`}
          icon={<IconCheck className="w-5 h-5" />}
          tone="amber"
          className="mk-reveal-d2"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-0">
        {/* Clock card */}
        <SectionCard compact icon={<IconClock />} title="Clock in / out" description="Record your working hours for today." className="lg:col-span-1 mk-reveal mk-reveal-d1">
          <div className="p-5">
            <p className="text-sm text-fg-muted mb-4">
              {employeeId === null
                ? "Your login is not linked to an employee record yet, so the clock is unavailable."
                : clockedIn
                  ? "You are currently clocked in."
                  : "You are not currently clocked in."}
            </p>
            <div className="flex gap-2 flex-wrap">
              <Button
                variant="primary"
                disabled={clockedIn || clocking}
                onClick={() => clockAction("in")}
              >
                <IconClock className="w-4 h-4" />
                {clocking ? "Clocking in…" : "Clock in"}
              </Button>
              <Button
                variant="secondary"
                disabled={!clockedIn || clocking}
                onClick={() => clockAction("out")}
              >
                <IconCheck className="w-4 h-4" />
                {clocking ? "Clocking out…" : "Clock out"}
              </Button>
            </div>
          </div>
        </SectionCard>

        {/* Leave balance */}
        <SectionCard compact icon={<IconPalm />} title="Leave balance" description="Your available leave days this year." className="lg:col-span-1 mk-reveal mk-reveal-d2">
          <div className="p-5">
            {myBalances.length === 0 ? (
              <p className="text-sm text-fg-muted">No leave balances assigned yet.</p>
            ) : (
              <ul className="space-y-3">
                {myBalances.map((b, i) => (
                  <li key={i} className="flex items-center justify-between p-3 bg-surface-inset rounded-lg">
                    <div className="flex items-center gap-3">
                      <span className="icon-tile icon-tile-green"><IconPalm className="w-4 h-4" /></span>
                      <span className="text-sm font-medium text-fg">{b.leave_type_name || "Leave"}</span>
                    </div>
                    <span className="text-base font-bold text-fg tabular-nums">{b.available_days}d</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </SectionCard>

        {/* Upcoming shifts */}
        <SectionCard compact icon={<IconCalendar />} title="Upcoming shifts" description="Your roster for the next few days." className="lg:col-span-1 mk-reveal mk-reveal-d1">
          <div className="p-5">
            {upcomingShifts.length === 0 ? (
              <p className="text-sm text-fg-muted">No upcoming shifts scheduled.</p>
            ) : (
              <ul className="space-y-2">
                {upcomingShifts.map((s) => (
                  <li key={s.id} className="flex items-center justify-between p-3 bg-surface-inset rounded-lg">
                    <div className="flex items-center gap-3">
                      <span className="icon-tile icon-tile-brand"><IconCalendar className="w-4 h-4" /></span>
                      <span className="text-sm text-fg">{s.work_date}</span>
                    </div>
                    <span className="text-sm text-fg-muted tabular-nums">
                      {s.start_time}–{s.end_time}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </SectionCard>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {/* Payslips */}
        <SectionCard compact icon={<IconWallet />} title="Recent payslips" description="Your latest pay statements." className="mk-reveal mk-reveal-d1">
          {payslips.length === 0 ? (
            <EmptyState title="No payslips yet" description="Payslips appear after your first payroll run." />
          ) : (
            <div className="table-scroll">
              <table className="table-base table-compact table-striped">
                <caption className="sr-only">Recent payslips</caption>
                <thead>
                  <tr>
                    <th scope="col">Period</th>
                    <th scope="col" className="num">Net pay</th>
                    <th scope="col">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {payslips.slice(0, 5).map((p) => (
                    <tr key={p.id}>
                      <td className="whitespace-nowrap">{p.period_start} → {p.period_end}</td>
                      <td className="num font-medium">
                        {formatCurrency(p.net_pay, { ...localeOpts, currency, minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                      <td><StatusPill status={p.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        {/* Onboarding tasks */}
        <SectionCard compact icon={<IconCheck />} title="My tasks" description="Onboarding and compliance items needing attention." className="mk-reveal mk-reveal-d2">
          {pendingTasks.length === 0 ? (
            <EmptyState title="All caught up" description="No pending onboarding or compliance tasks." />
          ) : (
            <ul className="divide-y divide-border-subtle">
              {pendingTasks.slice(0, 6).map((t) => (
                <li key={t.id} className="flex items-center justify-between px-5 py-3">
                  <span className="text-sm text-fg">{t.title}</span>
                  <span className="text-xs text-fg-muted">{t.due_date || "No due date"}</span>
                </li>
              ))}
            </ul>
          )}
        </SectionCard>
      </div>

      {/* Announcements */}
      {announcements.length > 0 && (
        <SectionCard compact icon={<IconInbox />} title="Announcements" description="Company-wide updates and notices." className="mt-0 mk-reveal">
          <ul className="divide-y divide-border-subtle">
            {announcements.slice(0, 5).map((a) => (
              <li key={a.id} className="px-5 py-4">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-semibold text-fg">{a.title}</span>
                  {a.priority === "high" && <span className="mk-chip">High priority</span>}
                </div>
                <p className="text-sm text-fg-muted line-clamp-2">{a.content}</p>
              </li>
            ))}
          </ul>
        </SectionCard>
      )}
    </Layout>
  )
}

function greeting() {
  const h = new Date().getHours()
  if (h < 12) return "morning"
  if (h < 17) return "afternoon"
  return "evening"
}
