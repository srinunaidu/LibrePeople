/**
 * Onboarding Configuration — presets, readiness and configuration gaps.
 *
 * Role gates mirror backend/app/api/v1/endpoints/onboarding.py:
 *  ADMIN_ROLES = SuperAdmin, HR
 *   - GET /onboarding/presets, /presets/{id}, /presets/{id}/diff, /readiness → ADMIN
 *  ALL_ROLES = SuperAdmin, HR, Manager, Associate, PayrollViewer
 *   - GET /onboarding/{id}/summary, /{id}/tasks, /{id}/documents → ALL_ROLES
 *
 * Reads are independent (Promise.allSettled) — one failed GET must not blank the others.
 * If an endpoint returns 404 the section shows an honest "not yet served" empty state.
 */
import { Fragment, useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert,
  EmptyState,
  LoadingRegion,
  PageHeader,
  SectionCard,
  TableSkeleton, RetryableAlert} from "@/components/ui"
import { StatusPill } from "@/components/ui/status-pill"
import { Meter } from "@/components/ui/feedback"
import { Select } from "@/components/ui/inputs"
import { useAuth } from "@/context/AuthContext"
import api, { errorMessage } from "@/lib/api"
import { fetchAllEmployees } from "@/lib/employees"
import type {
  Employee,
  OnboardingDocument,
  OnboardingSummary,
  OnboardingTask,
  PresetDetail,
  PresetDifference,
  PresetSummary,
  ReadinessReport,
} from "@/types"

const ADMIN_ROLES = ["SuperAdmin", "HR"] as const

function fmtDate(value?: string | null): string {
  if (!value) return "—"
  return value.slice(0, 10)
}

function severityBadge(severity: string): string {
  const s = severity.toLowerCase()
  if (s === "error" || s === "critical" || s === "high") return "rose"
  if (s === "warning" || s === "medium") return "amber"
  if (s === "info" || s === "low") return "slate"
  return "slate"
}

function isNotFound(err: unknown): boolean {
  const e = err as { response?: { status?: number } }
  return e?.response?.status === 404
}

function isForbidden(err: unknown): boolean {
  const e = err as { response?: { status?: number } }
  return e?.response?.status === 403
}

export default function OnboardingConfig() {
  const { user } = useAuth()
  const role = user?.role ?? ""
  const canAdmin = (ADMIN_ROLES as readonly string[]).includes(role)

  // Presets + detail/diff
  const [presets, setPresets] = useState<PresetSummary[]>([])
  const [readiness, setReadiness] = useState<ReadinessReport | null>(null)
  const [employees, setEmployees] = useState<Employee[]>([])
  const [loading, setLoading] = useState(true)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [notFound, setNotFound] = useState<Record<string, boolean>>({})

  // Preset expand/collapse
  const [expandedPreset, setExpandedPreset] = useState<string | null>(null)
  const [presetDetail, setPresetDetail] = useState<Record<string, PresetDetail>>({})
  const [presetDiff, setPresetDiff] = useState<Record<string, PresetDifference>>({})
  const [detailLoading, setDetailLoading] = useState<string | null>(null)
  const [detailErrors, setDetailErrors] = useState<Record<string, string>>({})

  // Employee drill
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<string>("")
  const [drillSummary, setDrillSummary] = useState<OnboardingSummary | null>(null)
  const [drillTasks, setDrillTasks] = useState<OnboardingTask[]>([])
  const [drillDocs, setDrillDocs] = useState<OnboardingDocument[]>([])
  const [drillLoading, setDrillLoading] = useState(false)
  const [drillErrors, setDrillErrors] = useState<Record<string, string>>({})
  const [drillNotFound, setDrillNotFound] = useState<Record<string, boolean>>({})

  const load = useCallback(async () => {
    setLoading(true)
    setErrors({})
    setNotFound({})
    const next: Record<string, string> = {}
    const nf: Record<string, boolean> = {}

    const presetsP = canAdmin
      ? api.get<PresetSummary[]>("/onboarding/presets")
      : Promise.resolve({ data: [] as PresetSummary[] })
    const readinessP = canAdmin
      ? api.get<ReadinessReport>("/onboarding/readiness")
      : Promise.resolve({ data: null as unknown as ReadinessReport })

    const [presetsR, readinessR, employeesR] = await Promise.allSettled([
      presetsP,
      readinessP,
      fetchAllEmployees(),
    ])

    if (presetsR.status === "fulfilled") {
      const v = presetsR.value as { data: PresetSummary[] }
      setPresets(v.data ?? [])
    } else if (canAdmin) {
      setPresets([])
      if (isNotFound(presetsR.reason)) nf.presets = true
      else if (!isForbidden(presetsR.reason)) next.presets = errorMessage(presetsR.reason, "The presets could not be read.")
    }

    if (readinessR.status === "fulfilled") {
      const v = readinessR.value as { data: ReadinessReport | null }
      setReadiness(v.data ?? null)
    } else if (canAdmin) {
      setReadiness(null)
      if (isNotFound(readinessR.reason)) nf.readiness = true
      else if (!isForbidden(readinessR.reason)) next.readiness = errorMessage(readinessR.reason, "The readiness report could not be read.")
    }

    if (employeesR.status === "fulfilled") {
      const v = employeesR.value as { items: Employee[] }
      if (v && Array.isArray((v as unknown as { items: unknown }).items)) {
        const items = v.items
        setEmployees(items)
        if (!selectedEmployeeId && items.length > 0) setSelectedEmployeeId(String(items[0].id))
      } else setEmployees([])
    } else {
      setEmployees([])
    }

    setErrors(next)
    setNotFound(nf)
    setLoading(false)
  }, [canAdmin, selectedEmployeeId])

  useEffect(() => {
    void load()
  }, [load])

  const loadDrill = useCallback(async (employeeId: number) => {
    setDrillLoading(true)
    setDrillErrors({})
    setDrillNotFound({})
    const next: Record<string, string> = {}
    const nf: Record<string, boolean> = {}
    const [summaryR, tasksR, docsR] = await Promise.allSettled([
      api.get<OnboardingSummary>(`/onboarding/${employeeId}/summary`),
      api.get<OnboardingTask[]>(`/onboarding/${employeeId}/tasks`),
      api.get<OnboardingDocument[]>(`/onboarding/${employeeId}/documents`),
    ])
    if (summaryR.status === "fulfilled") {
      setDrillSummary((summaryR.value as { data: OnboardingSummary }).data ?? null)
    } else {
      setDrillSummary(null)
      if (isNotFound(summaryR.reason)) nf.summary = true
      else next.summary = errorMessage(summaryR.reason, "The onboarding summary could not be read.")
    }
    if (tasksR.status === "fulfilled") {
      setDrillTasks((tasksR.value as { data: OnboardingTask[] }).data ?? [])
    } else {
      setDrillTasks([])
      if (isNotFound(tasksR.reason)) nf.tasks = true
      else next.tasks = errorMessage(tasksR.reason, "The onboarding tasks could not be read.")
    }
    if (docsR.status === "fulfilled") {
      setDrillDocs((docsR.value as { data: OnboardingDocument[] }).data ?? [])
    } else {
      setDrillDocs([])
      if (isNotFound(docsR.reason)) nf.documents = true
      else next.documents = errorMessage(docsR.reason, "The onboarding documents could not be read.")
    }
    setDrillErrors(next)
    setDrillNotFound(nf)
    setDrillLoading(false)
  }, [])

  useEffect(() => {
    if (selectedEmployeeId) void loadDrill(Number(selectedEmployeeId))
    else {
      setDrillSummary(null)
      setDrillTasks([])
      setDrillDocs([])
    }
  }, [selectedEmployeeId, loadDrill])

  async function togglePreset(presetId: string) {
    if (expandedPreset === presetId) {
      setExpandedPreset(null)
      return
    }
    setExpandedPreset(presetId)
    if (presetDetail[presetId] && presetDiff[presetId]) return
    setDetailLoading(presetId)
    setDetailErrors((c) => ({ ...c, [presetId]: "" }))
    const [detailR, diffR] = await Promise.allSettled([
      api.get<PresetDetail>(`/onboarding/presets/${presetId}`),
      api.get<PresetDifference>(`/onboarding/presets/${presetId}/diff`),
    ])
    const err: Record<string, string> = {}
    if (detailR.status === "fulfilled") {
      setPresetDetail((m) => ({ ...m, [presetId]: (detailR.value as { data: PresetDetail }).data }))
    } else {
      if (isNotFound(detailR.reason)) err[presetId] = "This preset is planned on the server — not yet served."
      else err[presetId] = errorMessage(detailR.reason, "The preset detail could not be read.")
    }
    if (diffR.status === "fulfilled") {
      setPresetDiff((m) => ({ ...m, [presetId]: (diffR.value as { data: PresetDifference }).data }))
    } else {
      const key = `${presetId}__diff`
      if (isNotFound(diffR.reason)) err[key] = "Preset diff is planned on the server — not yet served."
      else err[key] = errorMessage(diffR.reason, "The preset diff could not be read.")
    }
    if (Object.keys(err).length) setDetailErrors((c) => ({ ...c, ...err }))
    setDetailLoading(null)
  }

  const employeeName = (id: number) => {
    const e = employees.find((r) => r.id === id)
    return e ? `${e.first_name} ${e.last_name}` : `Employee #${id}`
  }

  // Config gaps are part of readiness — no separate endpoint
  const gapsCount = readiness
    ? (readiness.missing.length + readiness.inconsistent.length)
    : 0

  return (
    <Layout>
      <PageHeader compact
        title="Onboarding Configuration"
        description="Presets, readiness and configuration gaps — setup intelligence."
      />

      {/* Presets */}
      <SectionCard compact
        title="Presets"
        description="The catalogue of starting configurations, one per kind of business. Click a row to see what it would change."
      >
        {!canAdmin ? (
          <div className="p-5">
            <EmptyState
              title="Onboarding config requires HR"
              description="Presets are managed by SuperAdmin and HR. Your role does not read onboarding presets. An administrator can grant a workforce role."
            />
          </div>
        ) : loading ? (
          <LoadingRegion label="Loading presets…">
            <TableSkeleton rows={3} cols={5} />
          </LoadingRegion>
        ) : notFound.presets ? (
          <div className="p-5">
            <EmptyState
              title="Presets — not yet served"
              description="This is planned on the server — not yet served."
            />
          </div>
        ) : errors.presets ? (
          <div className="p-5">
            <RetryableAlert err={errors.presets} title="The presets could not be read" fallback="The presets could not be read" onRetry={load} />
          </div>
        ) : presets.length === 0 ? (
          <div className="p-5 text-sm text-text-secondary">No presets are published yet.</div>
        ) : (
          <div className="table-scroll">
            <table className="table-base table-compact w-full text-sm">
              <caption className="sr-only">Onboarding presets</caption>
              <thead>
                <tr>
                  <th scope="col">Name</th>
                  <th scope="col">Industry</th>
                  <th scope="col">Version</th>
                  <th scope="col">Status</th>
                  <th scope="col">Modules</th>
                  <th scope="col">Details</th>
                </tr>
              </thead>
              <tbody>
                {presets.map((p) => (
                  <Fragment key={p.id}>
                    <tr>
                      <td className="font-medium">{p.name}</td>
                      <td>{p.industry ?? "—"}</td>
                      <td className="font-mono text-xs">{p.version}</td>
                      <td><StatusPill status={p.status} /></td>
                      <td className="max-w-[360px] truncate" title={p.modules.join(", ")}>{p.modules.join(", ") || "—"}</td>
                      <td>
                        <button
                          type="button"
                          className="action-link"
                          aria-expanded={expandedPreset === p.id}
                          onClick={() => void togglePreset(p.id)}
                        >
                          {expandedPreset === p.id ? "Hide" : "View"}
                        </button>
                      </td>
                    </tr>
                    {expandedPreset === p.id && (
                      <tr>
                        <td colSpan={6} className="bg-surface-sunken p-0">
                          {detailLoading === p.id ? (
                            <div className="p-4">
                              <LoadingRegion label="Loading preset detail…">
                                <TableSkeleton rows={2} cols={3} />
                              </LoadingRegion>
                            </div>
                          ) : detailErrors[p.id] ? (
                            <div className="p-4">
                              <Alert tone="error">{detailErrors[p.id]}</Alert>
                              {detailErrors[`${p.id}__diff`] && <p className="text-xs text-text-secondary mt-2">{detailErrors[`${p.id}__diff`]}</p>}
                            </div>
                          ) : (
                            <div className="p-4 space-y-4">
                              {presetDetail[p.id] && (
                                <div>
                                  <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Preset detail</p>
                                  <p className="text-sm text-text-secondary mb-2">{presetDetail[p.id].description}</p>
                                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
                                    <div><span className="font-medium">Business type:</span> {presetDetail[p.id].business_type}</div>
                                    <div><span className="font-medium">Version:</span> {presetDetail[p.id].version}</div>
                                    <div><span className="font-medium">Modules:</span> {presetDetail[p.id].modules.join(", ") || "—"}</div>
                                  </div>
                                  {presetDetail[p.id].module_dependencies && Object.keys(presetDetail[p.id].module_dependencies).length > 0 && (
                                    <div className="mt-3">
                                      <p className="text-xs font-medium mb-1">Module dependencies</p>
                                      <ul className="text-xs text-text-secondary list-disc list-inside">
                                        {Object.entries(presetDetail[p.id].module_dependencies).map(([mod, deps]) => (
                                          <li key={mod}>{mod}: {deps.length ? deps.join(", ") : "no dependencies"}</li>
                                        ))}
                                      </ul>
                                    </div>
                                  )}
                                </div>
                              )}
                              {presetDiff[p.id] && (
                                <div className="border-t border-border pt-4">
                                  <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">What this preset would change</p>
                                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs mb-3">
                                    <div className="card p-3"><p className="font-semibold">Adds</p><p className="text-[var(--font-size-lg)]">{presetDiff[p.id].adds.length}</p></div>
                                    <div className="card p-3"><p className="font-semibold">Overwrites</p><p className="text-[var(--font-size-lg)]">{presetDiff[p.id].overwrites.length}</p></div>
                                    <div className="card p-3"><p className="font-semibold">Unchanged</p><p className="text-[var(--font-size-lg)]">{presetDiff[p.id].unchanged.length}</p></div>
                                    <div className="card p-3"><p className="font-semibold">Tenant only</p><p className="text-[var(--font-size-lg)]">{presetDiff[p.id].tenant_only.length}</p></div>
                                  </div>
                                  {presetDiff[p.id].modules_to_enable.length > 0 && (
                                    <p className="text-xs"><span className="font-medium">Modules to enable:</span> {presetDiff[p.id].modules_to_enable.join(", ")}</p>
                                  )}
                                  {presetDiff[p.id].adds.length > 0 && (
                                    <div className="mt-3">
                                      <p className="text-xs font-medium mb-1">Adds (first 10)</p>
                                      <ul className="text-xs text-text-secondary space-y-1">
                                        {presetDiff[p.id].adds.slice(0, 10).map((ch, i) => (
                                          <li key={i}><span className="font-mono">{ch.path}</span> — {ch.module} ({ch.action})</li>
                                        ))}
                                        {presetDiff[p.id].adds.length > 10 && <li className="italic">…and {presetDiff[p.id].adds.length - 10} more</li>}
                                      </ul>
                                    </div>
                                  )}
                                  {detailErrors[`${p.id}__diff`] && <p className="text-xs text-text-secondary mt-2">{detailErrors[`${p.id}__diff`]}</p>}
                                  <p className="text-xs text-text-secondary mt-2">Generated {fmtDate(presetDiff[p.id].generated_at)}</p>
                                </div>
                              )}
                              {!presetDetail[p.id] && !presetDiff[p.id] && !detailErrors[p.id] && (
                                <p className="text-sm text-text-secondary">No detail is available for this preset.</p>
                              )}
                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      {/* Readiness */}
      <SectionCard compact
        title="Readiness"
        description="What is configured, what is missing, what is inconsistent and what is merely recommended."
      >
        {!canAdmin ? (
          <div className="p-5">
            <EmptyState
              title="Onboarding config requires HR"
              description="Readiness is assessed by SuperAdmin and HR. Your role does not read readiness checks."
            />
          </div>
        ) : loading ? (
          <LoadingRegion label="Loading readiness…">
            <TableSkeleton rows={4} cols={4} />
          </LoadingRegion>
        ) : notFound.readiness ? (
          <div className="p-5">
            <EmptyState
              title="Readiness — not yet served"
              description="This is planned on the server — not yet served."
            />
          </div>
        ) : errors.readiness ? (
          <div className="p-5">
            <RetryableAlert err={errors.readiness} title="The readiness report could not be read" fallback="The readiness report could not be read" onRetry={load} />
          </div>
        ) : !readiness ? (
          <div className="p-5 text-sm text-text-secondary">No readiness report is available yet.</div>
        ) : (
          <div className="p-5 space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="card p-3">
                <p className="text-xs text-text-secondary">Configured</p>
                <p className="text-[var(--font-size-lg)] font-semibold text-success-text">{readiness.configured.length}</p>
              </div>
              <div className="card p-3">
                <p className="text-xs text-text-secondary">Missing</p>
                <p className="text-[var(--font-size-lg)] font-semibold text-warning-text">{readiness.missing.length}</p>
              </div>
              <div className="card p-3">
                <p className="text-xs text-text-secondary">Inconsistent</p>
                <p className="text-[var(--font-size-lg)] font-semibold text-error-text">{readiness.inconsistent.length}</p>
              </div>
              <div className="card p-3">
                <p className="text-xs text-text-secondary">Recommended</p>
                <p className="text-[var(--font-size-lg)] font-semibold">{readiness.recommended.length}</p>
              </div>
            </div>
            {(readiness.preset_id || readiness.preset_version) && (
              <p className="text-xs text-text-secondary">
                Preset {readiness.preset_id ?? "—"} · version {readiness.preset_version ?? "—"} · generated {fmtDate(readiness.generated_at)}
              </p>
            )}
            {readiness.findings.length > 0 ? (
              <div className="table-scroll">
                <table className="table-base table-compact w-full text-sm">
                  <caption className="sr-only">Readiness findings</caption>
                  <thead>
                    <tr>
                      <th scope="col">Severity</th>
                      <th scope="col">Title / Message</th>
                      <th scope="col">Category</th>
                      <th scope="col">Code</th>
                      <th scope="col">Recommendation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {readiness.findings.map((f, i) => (
                      <tr key={`${f.rule_id}-${i}`}>
                        <td><span className={`badge badge-${severityBadge(f.severity)}`}>{f.severity}</span></td>
                        <td className="max-w-[320px]">
                          <span className="font-medium">{f.title ?? f.message}</span>
                          {f.title && f.message !== f.title && <span className="block text-xs text-text-secondary">{f.message}</span>}
                        </td>
                        <td className="text-xs">{f.category}</td>
                        <td className="font-mono text-xs">{f.code ?? f.rule_id}</td>
                        <td className="text-xs max-w-[260px] truncate" title={f.recommendation ?? ""}>{f.recommendation ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-text-secondary">No findings — this deployment is ready for the selected preset.</p>
            )}
          </div>
        )}
      </SectionCard>

      {/* Config Gaps */}
      <SectionCard compact
        title="Configuration gaps"
        description="The settings and modules that are still missing or inconsistent — the publish blockers."
      >
        {!canAdmin ? (
          <div className="p-5">
            <EmptyState
              title="Onboarding config requires HR"
              description="Configuration gaps are read by SuperAdmin and HR."
            />
          </div>
        ) : loading ? (
          <LoadingRegion label="Loading gaps…">
            <TableSkeleton rows={3} cols={3} />
          </LoadingRegion>
        ) : notFound.readiness || errors.readiness ? (
          <div className="p-5">
            <EmptyState
              title="Gaps — via readiness"
              description="Config gaps are part of the readiness check. The readiness report could not be loaded."
            />
          </div>
        ) : !readiness ? (
          <div className="p-5 text-sm text-text-secondary">Config gaps are part of the readiness check — no report is available yet.</div>
        ) : gapsCount === 0 ? (
          <div className="p-5 text-sm text-text-secondary">No configuration gaps — all checks are configured or recommended.</div>
        ) : (
          <div className="p-5 space-y-4">
            <p className="text-sm text-text-secondary">
              {gapsCount} gap{gapsCount === 1 ? "" : "s"} — the missing and inconsistent findings that block publishing.
            </p>
            <div className="table-scroll">
              <table className="table-base table-compact w-full text-sm">
                <caption className="sr-only">Configuration gaps</caption>
                <thead>
                  <tr>
                    <th scope="col">State</th>
                    <th scope="col">Title</th>
                    <th scope="col">Severity</th>
                    <th scope="col">Recommendation</th>
                  </tr>
                </thead>
                <tbody>
                  {[...readiness.missing.map((f) => ({ ...f, _state: "Missing" })), ...readiness.inconsistent.map((f) => ({ ...f, _state: "Inconsistent" }))].map((f, i) => (
                    <tr key={`${f.rule_id}-${i}`}>
                      <td><StatusPill status={f._state} /></td>
                      <td className="font-medium">{f.title ?? f.message}</td>
                      <td><span className={`badge badge-${severityBadge(f.severity)}`}>{f.severity}</span></td>
                      <td className="text-xs max-w-[320px] truncate" title={f.recommendation ?? ""}>{f.recommendation ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-text-secondary">Config gaps are the missing + inconsistent findings of the readiness check — there is no separate config-gaps endpoint.</p>
          </div>
        )}
      </SectionCard>

      {/* Employee onboarding drill */}
      <SectionCard compact
        title="Employee onboarding drill"
        description="Pick an employee to see their checklist progress, tasks and documents. Any workforce role may read this."
      >
        <div className="p-5 border-b border-border">
          <div className="flex flex-wrap gap-3 items-end">
            <div className="flex-1 min-w-[240px]">
              <label htmlFor="onboarding-drill-employee" className="block text-xs font-medium text-text-secondary mb-1">Employee</label>
              <Select
                id="onboarding-drill-employee"
                value={selectedEmployeeId}
                onChange={(e) => setSelectedEmployeeId(e.target.value)}
              >
                <option value="">Select an employee…</option>
                {employees.map((emp) => (
                  <option key={emp.id} value={emp.id}>
                    {emp.first_name} {emp.last_name} · {emp.employee_id}
                  </option>
                ))}
              </Select>
            </div>
            {drillSummary && (
              <div className="flex-1 min-w-[240px]">
                <Meter
                  percent={drillSummary.progress_percent}
                  label={`${drillSummary.completed_tasks} of ${drillSummary.total_tasks} tasks complete · ${drillSummary.documents_uploaded} document${drillSummary.documents_uploaded === 1 ? "" : "s"}`}
                />
              </div>
            )}
          </div>
          {employees.length === 0 && !loading && (
            <p className="text-xs text-text-secondary mt-2">No employees are visible to your account yet.</p>
          )}
        </div>

        {!selectedEmployeeId ? (
          <div className="p-5 text-sm text-text-secondary">Choose an employee above to see their onboarding progress.</div>
        ) : drillLoading ? (
          <LoadingRegion label="Loading onboarding drill…">
            <TableSkeleton rows={3} cols={4} />
          </LoadingRegion>
        ) : (
          <>
            {drillNotFound.summary || drillErrors.summary ? (
              <div className="p-5">
                {drillNotFound.summary ? (
                  <EmptyState title="Summary — not yet served" description="This is planned on the server — not yet served." />
                ) : (
                  <Alert tone="error">{drillErrors.summary}</Alert>
                )}
              </div>
            ) : drillSummary ? (
              <div className="p-5 grid grid-cols-3 gap-3">
                <div className="card p-3 text-center">
                  <p className="text-xs text-text-secondary">Tasks</p>
                  <p className="text-[var(--font-size-lg)] font-semibold">{drillSummary.completed_tasks}/{drillSummary.total_tasks}</p>
                </div>
                <div className="card p-3 text-center">
                  <p className="text-xs text-text-secondary">Progress</p>
                  <p className="text-[var(--font-size-lg)] font-semibold">{drillSummary.progress_percent}%</p>
                </div>
                <div className="card p-3 text-center">
                  <p className="text-xs text-text-secondary">Documents</p>
                  <p className="text-[var(--font-size-lg)] font-semibold">{drillSummary.documents_uploaded}</p>
                </div>
                <p className="text-xs text-text-secondary col-span-3">Employee {employeeName(drillSummary.employee_id)} · {drillSummary.progress_percent}% complete</p>
              </div>
            ) : null}

            <div className="px-5 pb-1">
              <h3 className="text-sm font-semibold mt-2">Tasks</h3>
            </div>
            {drillNotFound.tasks ? (
              <div className="p-5"><EmptyState title="Tasks — not yet served" description="This is planned on the server — not yet served." /></div>
            ) : drillErrors.tasks ? (
              <div className="p-5"><Alert tone="error">{drillErrors.tasks}</Alert></div>
            ) : drillTasks.length === 0 ? (
              <div className="p-5 text-sm text-text-secondary">No onboarding tasks for this employee.</div>
            ) : (
              <div className="table-scroll">
                <table className="table-base table-compact w-full text-sm">
                  <caption className="sr-only">Onboarding tasks for the selected employee</caption>
                  <thead>
                    <tr>
                      <th scope="col">Task</th>
                      <th scope="col">Category</th>
                      <th scope="col">Due</th>
                      <th scope="col">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {drillTasks.map((t) => (
                      <tr key={t.id}>
                        <td className="font-medium">{t.title}</td>
                        <td>{t.category}</td>
                        <td>{fmtDate(t.due_date)}</td>
                        <td><StatusPill status={t.status} dot /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="px-5 pb-1 border-t border-border mt-3">
              <h3 className="text-sm font-semibold mt-3">Documents</h3>
            </div>
            {drillNotFound.documents ? (
              <div className="p-5"><EmptyState title="Documents — not yet served" description="This is planned on the server — not yet served." /></div>
            ) : drillErrors.documents ? (
              <div className="p-5"><Alert tone="error">{drillErrors.documents}</Alert></div>
            ) : drillDocs.length === 0 ? (
              <div className="p-5 text-sm text-text-secondary">No documents uploaded for this employee.</div>
            ) : (
              <div className="table-scroll">
                <table className="table-base table-compact w-full text-sm">
                  <caption className="sr-only">Onboarding documents for the selected employee</caption>
                  <thead>
                    <tr>
                      <th scope="col">Type</th>
                      <th scope="col">File</th>
                      <th scope="col">Status</th>
                      <th scope="col">Uploaded</th>
                    </tr>
                  </thead>
                  <tbody>
                    {drillDocs.map((d) => (
                      <tr key={d.id}>
                        <td>{d.document_type}</td>
                        <td>{d.file_name}</td>
                        <td><StatusPill status={d.status} /></td>
                        <td>{fmtDate(d.uploaded_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </SectionCard>
    </Layout>
  )
}
