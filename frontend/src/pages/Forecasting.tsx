/**
 * The forecasting workspace (FD-06, PL-01…PL-06).
 *
 * Four URL-addressable tabs in the People style: /forecasting (runs),
 * /forecasting/demand, /forecasting/scenarios, /forecasting/accuracy —
 * every sidebar link lands on a real URL, both globally and inside
 * /t/:slug tenant workspaces.
 *
 * Role reality: EVERY forecasting endpoint is `require_roles(*MANAGER_ROLES)`
 * server-side (app/api/deps.py) — SuperAdmin, HR and Manager. Anything below
 * gets the readable explanation below instead of silent emptiness, and the
 * read paths still degrade per-section (allSettled, never a blank page).
 */
import { Link, useLocation } from "react-router-dom"
import { Layout } from "@/components/Layout"
import {Alert, PageHeader, RetryableAlert, TableSkeleton} from "@/components/ui"
import { useAuth } from "@/context/AuthContext"
import { useTenantNav } from "@/lib/tenantPath"
import { canForecast } from "./forecasting/shared"
import RunsTab from "./forecasting/RunsTab"
import DemandTab from "./forecasting/DemandTab"
import ScenariosTab from "./forecasting/ScenariosTab"
import AccuracyTab from "./forecasting/AccuracyTab"

/** Tabs are addressed by path so every sidebar link lands on a real URL. */
const TABS = [
  { key: "runs", label: "Runs", segment: "forecasting" },
  { key: "demand", label: "Demand & drivers", segment: "demand" },
  { key: "scenarios", label: "Scenarios", segment: "scenarios" },
  { key: "accuracy", label: "Accuracy", segment: "accuracy" },
] as const

type TabKey = (typeof TABS)[number]["key"]

function tabFromPath(pathname: string): TabKey {
  const segments = pathname.split("/").filter(Boolean)
  const last = segments[segments.length - 1] ?? "forecasting"
  const hit = TABS.find((t) => t.segment === last)
  return hit ? hit.key : "runs"
}

export default function Forecasting() {
  const { user } = useAuth()
  const { pathname } = useLocation()
  const tenantNav = useTenantNav()
  const allowed = canForecast(user?.role)
  const tab = tabFromPath(pathname)

  if (!allowed) {
    return (
      <Layout>
        <PageHeader compact title="Forecast" description="Runs of the statistical engine over demand series, what-if scenarios, cost forecasts and forecast-vs-actual accuracy." />
        <RetryableAlert err={user?.role || "unknown"} title="Not permitted" fallback="Not permitted." />
      </Layout>
    )
  }

  return (
    <Layout>
      <PageHeader compact title="Forecast" description="The forecasting workspace: runs of the statistical engine over demand series, what-if scenarios with explicit named assumptions, cost forecasts labelled “excludes statutory on-costs”, and forecast-vs-actual accuracy." />

      <div className="tablist" role="tablist" aria-label="Forecast sections">
        {TABS.map((t) => (
          <Link
            key={t.key}
            role="tab"
            aria-selected={tab === t.key}
            to={t.segment === "forecasting" ? tenantNav.to("/forecasting") : tenantNav.to(`/forecasting/${t.segment}`)}
            id={`forecast-tab-${t.key}`}
            className={`tab ${tab === t.key ? "tab-active" : "tab-idle"}`}
          >
            {t.label}
          </Link>
        ))}
      </div>

      <div
        role="tabpanel"
        id={`forecast-panel-${tab}`}
        aria-labelledby={`forecast-tab-${tab}`}
        className="mt-4"
      >
        {tab === "runs" && <RunsTab />}
        {tab === "demand" && <DemandTab />}
        {tab === "scenarios" && <ScenariosTab />}
        {tab === "accuracy" && <AccuracyTab />}
      </div>
    </Layout>
  )
}
