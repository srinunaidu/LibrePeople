/**
 * Compliance Center — rules and violations CRUD.
 *
 * Gates mirror backend/app/api/v1/endpoints/compliance.py:
 *  GET  /compliance/compliance-rules              ADMIN_ROLES (SuperAdmin, HR)
 *  POST /compliance/compliance-rules              ADMIN_ROLES  body: code/name/category/description/severity/is_active
 *  GET  /compliance/compliance-violations         WORKFORCE_ROLES (visibility-scoped, filterable)
 *  POST /compliance/compliance-violations         ADMIN_ROLES  body: rule_id/employee_id/notes/status
 *  PUT  /compliance/compliance-violations/{id}/resolve  ADMIN_ROLES
 *
 * Every create/resolve is written to the audit trail (create_compliance_rule,
 * create_compliance_violation, resolve_compliance_violation).
 */
import { useState, type FormEvent } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Layout } from "@/components/Layout"
import {
  PendingVerificationAlert,
  Button,
  Input,
  Textarea,
  Select,
  Alert,
  EmptyState,
  LoadingRegion,
  PageHeader,
  RetryableAlert,
  SectionCard,
  TableSkeleton,
  Table, StatusPill } from "@/components/ui"

import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { errorMessage, getFiling, isPendingVerification } from "@/lib/api"

interface ComplianceRuleOut {
  id: number
  code: string
  name: string
  category: string
  description?: string | null
  severity: string
  is_active: boolean
  created_at?: string | null
}

interface ComplianceViolationOut {
  id: number
  employee_id?: number | null
  rule_id: number
  status: string
  notes?: string | null
  detected_at?: string | null
  resolved_at?: string | null
}

function fmtDate(v?: string | null) {
  if (!v) return "—"
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return v.slice(0, 19).replace("T", " ")
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(d)
}

function severityTone(s: string): "rose" | "amber" | "slate" | "brand" {
  if (s === "Critical" || s === "critical") return "rose"
  if (s === "High" || s === "high") return "rose"
  if (s === "Medium" || s === "medium") return "amber"
  if (s === "Low" || s === "low") return "slate"
  return "slate"
}

export default function ComplianceCenter() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const qc = useQueryClient()
  const canAdmin = ["SuperAdmin", "HR"].includes(user?.role ?? "")
  const [activeTab, setActiveTab] = useState("rules")
  const [notice, setNotice] = useState("")
  const [resolveError, setResolveError] = useState("")

  // Rules form state
  const [code, setCode] = useState("")
  const [name, setName] = useState("")
  const [category, setCategory] = useState("Labor Law")
  const [description, setDescription] = useState("")
  const [severity, setSeverity] = useState("Medium")
  const [isActive, setIsActive] = useState(true)
  const [ruleError, setRuleError] = useState("")

  // Violations form state
  const [vRuleId, setVRuleId] = useState("")
  const [vEmployeeId, setVEmployeeId] = useState("")
  const [vNotes, setVNotes] = useState("")
  const [vStatus, setVStatus] = useState("Open")
  const [violationError, setViolationError] = useState("")
  const [resolveConfirm, setResolveConfirm] = useState<number | null>(null)

  // India payroll reports state (slice 4)
  const [payrollPeriod, setPayrollPeriod] = useState("")
  const [payrollReports, setPayrollReports] = useState<any>(null)
  const [payrollPendingMsg, setPayrollPendingMsg] = useState("")
  const [payrollLoading, setPayrollLoading] = useState(false)
  // Filings (AC-34..36) — 5 types under payroll-IN
  const [filingType, setFilingType] = useState("24q")
  const [filingPeriod, setFilingPeriod] = useState("")
  const [filingState, setFilingState] = useState("KA")
  const [filingData, setFilingData] = useState<string | null>(null)
  const [filingError, setFilingError] = useState("")
  const [filingLoading, setFilingLoading] = useState(false)
  const [filingHeaders, setFilingHeaders] = useState<Record<string, string>>({})
  const loadPayrollReports = async () => {
    setPayrollLoading(true); setPayrollPendingMsg(""); setPayrollReports(null)
    try {
      const params: Record<string,string> = { jurisdiction: "IN" }
      if (payrollPeriod.trim()) params.period = payrollPeriod.trim()
      const { data } = await api.get("/reports/payroll", { params })
      setPayrollReports(data)
    } catch (e: any) {
      const msg = errorMessage(e, "Could not load payroll reports.")
      const code = (e as any)?.apiError?.code || (e as any)?.response?.data?.error?.code
      if (code === "rule_pack_not_verified") {
        setPayrollPendingMsg(msg + " — rule_pack_not_verified (pending_verification). No computed data is returned while pending, per docs/PAYROLL.md §3.3.")
      } else {
        setPayrollPendingMsg(msg)
      }
    } finally { setPayrollLoading(false) }
  }

  const filingTypeToFilenamePart = (ft: string, state?: string) => {
    const m: Record<string, string> = {
      "24q": "24Q_QUARTERLY",
      "24q_quarterly": "24Q_QUARTERLY",
      "form16_annual": "FORM16_ANNUAL",
      "form16": "FORM16_ANNUAL",
      "pf_ecr": "PF_ECR",
      "esi_return": "ESI_RETURN",
      "pt_challan": state ? `PT_CHALLAN_${state.toUpperCase()}` : "PT_CHALLAN",
      "pt_return": state ? `PT_CHALLAN_${state.toUpperCase()}` : "PT_CHALLAN",
    }
    return m[ft] || ft.toUpperCase()
  }

  const loadFiling = async () => {
    const periodTrim = filingPeriod.trim()
    if (!periodTrim) {
      setFilingError("Period is required (YYYY-MM, or YYYY for Form 16).")
      return
    }
    const isForm16 = filingType === "form16_annual"
    const periodValid = isForm16 ? /^\d{4}(-\d{2})?$/.test(periodTrim) : /^\d{4}-\d{2}$/.test(periodTrim)
    if (!periodValid) {
      setFilingError("period must be YYYY-MM (or YYYY for Form 16)")
      return
    }
    // Include state only for PT
    const isPT = filingType === "pt_challan"
    const stateParam = isPT && filingState ? filingState.trim().toUpperCase() : undefined
    setFilingLoading(true); setFilingError(""); setFilingData(null); setFilingHeaders({})
    try {
      const { data, headers } = await getFiling(
        filingType,
        { jurisdiction: "IN", period: periodTrim, state: stateParam },
        { responseType: "text" },
      )
      // axios may return string or object; ensure string
      const text = typeof data === "string" ? data : String(data ?? "")
      setFilingData(text)
      setFilingHeaders(headers as Record<string, string>)
    } catch (e: any) {
      const msg = errorMessage(e, "Could not load filing.")
      const code = (e as any)?.apiError?.code || (e as any)?.response?.data?.error?.code || ""
      const status = (e as any)?.response?.status
      // surface verbatim messages for 422/409
      const detail = (e as any)?.response?.data?.detail
      const detailMsg = typeof detail === "string" ? detail : ""
      if (status === 409 || code === "rule_pack_not_verified") {
        setFilingError(msg + " — rule_pack_not_verified")
      } else if (status === 422) {
        setFilingError(detailMsg || msg)
      } else {
        setFilingError(msg)
      }
    } finally { setFilingLoading(false) }
  }

  const downloadFiling = () => {
    if (!filingData) return
    const isPT = filingType === "pt_challan"
    const stateSuffix = isPT && filingState ? `_${filingState.trim().toUpperCase()}` : ""
    // Try Content-Disposition header first (filings.py:329)
    let filename = ""
    const cd = (filingHeaders as any)?.["content-disposition"] || (filingHeaders as any)?.["Content-Disposition"] || ""
    if (cd && typeof cd === "string") {
      const m = cd.match(/filename="?([^"]+)"?/)
      if (m) filename = m[1]
    }
    if (!filename) {
      const typePart = filingTypeToFilenamePart(filingType, isPT ? filingState : undefined)
      const periodClean = filingPeriod.trim()
      filename = `IN_${typePart}_${periodClean}.txt`
      // PT already includes state in typePart, avoid double
      if (isPT && stateSuffix && !filename.includes(stateSuffix)) {
        // typePart already has it, so fine
      }
    }
    const blob = new Blob([filingData], { type: "text/plain" })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
  }

  const rulesQuery = useQuery({
    queryKey: ["compliance-rules"],
    queryFn: async () => {
      const { data } = await api.get<ComplianceRuleOut[]>("/compliance/compliance-rules")
      return data
    },
    enabled: canAdmin,
  })

  const violationsQuery = useQuery({
    queryKey: ["compliance-violations"],
    queryFn: async () => {
      const { data } = await api.get<ComplianceViolationOut[]>("/compliance/compliance-violations")
      return data
    },
    enabled: canAdmin,
  })

  const createRuleMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        code: code.trim(),
        name: name.trim(),
        category: category.trim() || "Labor Law",
        description: description.trim() || null,
        severity,
        is_active: isActive,
      }
      const { data } = await api.post<ComplianceRuleOut>("/compliance/compliance-rules", payload)
      return data
    },
    onSuccess: (data) => {
      setNotice(`Compliance rule created: ${data.code} — ${data.name}.`)
      setResolveError("")
      qc.invalidateQueries({ queryKey: ["compliance-rules"] })
      setCode("")
      setName("")
      setDescription("")
      setRuleError("")
    },
    onError: (err: unknown) => {
      setRuleError(errorMessage(err, "Could not create rule."))
    },
  })

  const createViolationMutation = useMutation({
    mutationFn: async () => {
      const payload: Record<string, unknown> = {
        rule_id: Number(vRuleId),
        status: vStatus,
        notes: vNotes.trim() || null,
      }
      if (vEmployeeId.trim()) payload.employee_id = Number(vEmployeeId)
      const { data } = await api.post<ComplianceViolationOut>("/compliance/compliance-violations", payload)
      return data
    },
    onSuccess: (data) => {
      setNotice(`Violation #${data.id} recorded for rule #${data.rule_id}.`)
      setResolveError("")
      qc.invalidateQueries({ queryKey: ["compliance-violations"] })
      setVNotes("")
      setViolationError("")
    },
    onError: (err: unknown) => {
      setViolationError(errorMessage(err, "Could not create violation."))
    },
  })

  const resolveMutation = useMutation({
    mutationFn: async (id: number) => {
      const { data } = await api.put<ComplianceViolationOut>(`/compliance/compliance-violations/${id}/resolve`)
      return data
    },
    onSuccess: (data) => {
      setNotice(`Violation #${data.id} resolved.`)
      setResolveError("")
      qc.invalidateQueries({ queryKey: ["compliance-violations"] })
      setResolveConfirm(null)
    },
    onError: (err: unknown) => {
      setResolveError(errorMessage(err, "Could not resolve violation."))
    },
  })

  const handleRuleSubmit = (e: FormEvent) => {
    e.preventDefault()
    setRuleError("")
    setNotice("")
    setResolveError("")
    if (!code.trim()) {
      setRuleError("Code is required (e.g. HR-11).")
      return
    }
    if (!name.trim()) {
      setRuleError("Name is required.")
      return
    }
    createRuleMutation.mutate()
  }

  const handleViolationSubmit = (e: FormEvent) => {
    e.preventDefault()
    setViolationError("")
    setNotice("")
    setResolveError("")
    if (!vRuleId || Number.isNaN(Number(vRuleId)) || Number(vRuleId) <= 0) {
      setViolationError("Rule ID is required (numeric).")
      return
    }
    createViolationMutation.mutate()
  }

  if (!canAdmin) {
    return (
      <Layout>
        <div data-tenant-slug={tenant?.slug ?? "—"}>
          <PageHeader compact title="Compliance Center" description="Rules and violations — SuperAdmin / HR only. Every action is written to audit trail." />
          <EmptyState title="Not visible for your role" description={`Compliance requires SuperAdmin or HR; your role is ${user?.role || "unknown"}.`} />
        </div>
      </Layout>
    )
  }

  const rules = rulesQuery.data ?? []
  const violations = violationsQuery.data ?? []

  return (
    <Layout>
      <div data-tenant-slug={tenant?.slug ?? "—"} className="space-y-4">
        <PageHeader compact title="Compliance Center" description="Rules and violations — SuperAdmin / HR only. Every action is written to audit trail." />

        <p className="text-xs text-[color:var(--fg-muted)] border border-[color:var(--border)] rounded-[var(--radius-md)] px-3 py-2 bg-[color:var(--surface)]">
          Audit note: Every action is written to audit trail (<code className="font-mono text-xs">create_compliance_rule</code> / <code className="font-mono text-xs">create_compliance_violation</code> / <code className="font-mono text-xs">resolve_compliance_violation</code>).
        </p>

        {notice && <Alert tone="success">{notice}</Alert>}
        {resolveError && <Alert tone="error" title="Could not resolve violation">{resolveError}</Alert>}

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="rules">Rules {rules.length > 0 ? `(${rules.length})` : ""}</TabsTrigger>
            <TabsTrigger value="violations">Violations {violations.length > 0 ? `(${violations.length})` : ""}</TabsTrigger>
            <TabsTrigger value="payroll-in">Payroll IN</TabsTrigger>
          </TabsList>

          {/* Rules tab */}
          <TabsContent value="rules" className="space-y-4 mt-4">
            <SectionCard compact title="Create rule" description="POST /compliance/compliance-rules — SuperAdmin / HR. Fields: code, name, category, description, severity, status.">
              <form onSubmit={handleRuleSubmit} className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="cr-code" className="block text-xs font-medium text-[color:var(--fg)] mb-1">
                      Code <span className="text-[color:var(--error)]">(required)</span>
                    </label>
                    <Input id="cr-code" value={code} onChange={(e) => setCode(e.target.value)} placeholder="e.g. HR-11" required />
                  </div>
                  <div>
                    <label htmlFor="cr-name" className="block text-xs font-medium text-[color:var(--fg)] mb-1">
                      Name <span className="text-[color:var(--error)]">(required)</span>
                    </label>
                    <Input id="cr-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Overtime limit" required />
                  </div>
                  <div>
                    <label htmlFor="cr-category" className="block text-xs font-medium text-[color:var(--fg)] mb-1">
                      Category
                    </label>
                    <Select id="cr-category" value={category} onChange={(e) => setCategory(e.target.value)}>
                      <option value="Labor Law">Labor Law</option>
                      <option value="Policy">Policy</option>
                      <option value="Certification">Certification</option>
                      <option value="Safety">Safety</option>
                    </Select>
                  </div>
                  <div>
                    <label htmlFor="cr-severity" className="block text-xs font-medium text-[color:var(--fg)] mb-1">
                      Severity
                    </label>
                    <Select id="cr-severity" value={severity} onChange={(e) => setSeverity(e.target.value)}>
                      <option value="Low">Low</option>
                      <option value="Medium">Medium</option>
                      <option value="High">High</option>
                      <option value="Critical">Critical</option>
                    </Select>
                  </div>
                </div>
                <div>
                  <label htmlFor="cr-description" className="block text-xs font-medium text-[color:var(--fg)] mb-1">
                    Description
                  </label>
                  <Textarea id="cr-description" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What this rule enforces" rows={2} />
                </div>
                <div className="flex items-center gap-2">
                  <label htmlFor="cr-active" className="flex items-center gap-2 text-xs text-[color:var(--fg)]">
                    <input id="cr-active" type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} className="h-4 w-4 rounded border-[color:var(--border)]" />
                    Active
                  </label>
                  <span className="text-xs text-[color:var(--fg-muted)]">Inactive rules are retained but not enforced.</span>
                </div>
                {ruleError && (
                  <Alert tone="error" title="Could not create rule">
                    {ruleError}
                  </Alert>
                )}
                {createRuleMutation.isError && !ruleError && (
                  <Alert tone="error" title="Request failed">
                    {errorMessage(createRuleMutation.error, "Could not create rule.")}
                  </Alert>
                )}
                <div className="flex items-center gap-2">
                  <Button type="submit" loading={createRuleMutation.isPending}>
                    Create rule
                  </Button>
                  <span className="text-xs text-[color:var(--fg-muted)]">Writes <code className="font-mono text-xs">create_compliance_rule</code> to audit trail.</span>
                </div>
              </form>
            </SectionCard>

            <SectionCard
              compact
              title="Rules"
              description="GET /compliance/compliance-rules — ordered by code. Compact table, tabular numerals."
              actions={
                <Button variant="secondary" size="sm" onClick={() => rulesQuery.refetch()} disabled={rulesQuery.isFetching}>
                  {rulesQuery.isFetching ? "Refreshing…" : "Refresh"}
                </Button>
              }
            >
              {rulesQuery.isLoading ? (
                <LoadingRegion label="Loading rules…">
                  <TableSkeleton rows={5} cols={5} />
                </LoadingRegion>
              ) : rulesQuery.isError ? (
                <RetryableAlert err={rulesQuery.error} title="Could not load rules" fallback="The rules could not be read." onRetry={() => rulesQuery.refetch()} />
              ) : rules.length === 0 ? (
                <EmptyState title="No rules" description="No compliance rules are configured yet. Create one above — it will appear here and in the audit trail." />
              ) : (
                <Table
                  columns={[
                    { key: "code", header: "Code", accessor: (r) => <span className="font-mono text-xs tabular-nums">{r.code}</span> },
                    { key: "name", header: "Name", accessor: (r) => (
                      <span className="font-medium max-w-[240px] truncate" title={r.name}>
                        {r.name}
                      </span>
                    ) },
                    { key: "category", header: "Category", accessor: (r) => <span className="text-xs">{r.category}</span> },
                    { key: "severity", header: "Severity", accessor: (r) => (
                      <StatusPill status={r.severity} tone={severityTone(r.severity)} />
                    ) },
                    { key: "status", header: "Status", accessor: (r) => (
                      <StatusPill status={r.is_active ? "Active" : "Inactive"} />
                    ) },
                    { key: "created", header: "Created", accessor: (r) => <span className="whitespace-nowrap">{fmtDate(r.created_at)}</span> },
                  ]}
                  data={rules}
                  keyAccessor={(r) => r.id}
                  caption="Compliance rules"
                  sortable={false}
                />
              )}
            </SectionCard>
          </TabsContent>

          {/* Violations tab */}
          <TabsContent value="violations" className="space-y-4 mt-4">
            <SectionCard compact title="Record violation" description="POST /compliance/compliance-violations — SuperAdmin / HR. Fields: rule_id, employee_id, details (notes), status.">
              <form onSubmit={handleViolationSubmit} className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <label htmlFor="cv-rule" className="block text-xs font-medium text-[color:var(--fg)] mb-1">
                      Rule ID <span className="text-[color:var(--error)]">(required)</span>
                    </label>
                    {rules.length > 0 ? (
                      <Select id="cv-rule" value={vRuleId} onChange={(e) => setVRuleId(e.target.value)}>
                        <option value="">Select rule…</option>
                        {rules.map((r) => (
                          <option key={r.id} value={String(r.id)}>
                            #{r.id} {r.code} — {r.name}
                          </option>
                        ))}
                      </Select>
                    ) : (
                      <Input id="cv-rule" type="number" min={1} value={vRuleId} onChange={(e) => setVRuleId(e.target.value)} placeholder="e.g. 1" required />
                    )}
                  </div>
                  <div>
                    <label htmlFor="cv-employee" className="block text-xs font-medium text-[color:var(--fg)] mb-1">
                      Employee ID
                    </label>
                    <Input id="cv-employee" type="number" min={1} value={vEmployeeId} onChange={(e) => setVEmployeeId(e.target.value)} placeholder="e.g. 42 (optional)" />
                  </div>
                  <div>
                    <label htmlFor="cv-status" className="block text-xs font-medium text-[color:var(--fg)] mb-1">
                      Status
                    </label>
                    <Select id="cv-status" value={vStatus} onChange={(e) => setVStatus(e.target.value)}>
                      <option value="Open">Open</option>
                      <option value="In Progress">In Progress</option>
                      <option value="Resolved">Resolved</option>
                      <option value="Dismissed">Dismissed</option>
                    </Select>
                  </div>
                </div>
                <div>
                  <label htmlFor="cv-notes" className="block text-xs font-medium text-[color:var(--fg)] mb-1">
                    Details / notes
                  </label>
                  <Textarea id="cv-notes" value={vNotes} onChange={(e) => setVNotes(e.target.value)} placeholder="What was detected, context, next steps" rows={2} />
                </div>
                {violationError && (
                  <Alert tone="error" title="Could not create violation">
                    {violationError}
                  </Alert>
                )}
                {createViolationMutation.isError && !violationError && (
                  <Alert tone="error" title="Request failed">
                    {errorMessage(createViolationMutation.error, "Could not create violation.")}
                  </Alert>
                )}
                <div className="flex items-center gap-2">
                  <Button type="submit" loading={createViolationMutation.isPending}>
                    Record violation
                  </Button>
                  <span className="text-xs text-[color:var(--fg-muted)]">Writes <code className="font-mono text-xs">create_compliance_violation</code> to audit trail.</span>
                </div>
              </form>
            </SectionCard>

            <SectionCard
              compact
              title="Violations"
              description="GET /compliance/compliance-violations — most recent first. Resolve uses PUT /{id}/resolve."
              actions={
                <Button variant="secondary" size="sm" onClick={() => violationsQuery.refetch()} disabled={violationsQuery.isFetching}>
                  {violationsQuery.isFetching ? "Refreshing…" : "Refresh"}
                </Button>
              }
            >
              {violationsQuery.isLoading ? (
                <LoadingRegion label="Loading violations…">
                  <TableSkeleton rows={5} cols={6} />
                </LoadingRegion>
              ) : violationsQuery.isError ? (
                <RetryableAlert err={violationsQuery.error} title="Could not load violations" fallback="The violations could not be read." onRetry={() => violationsQuery.refetch()} />
              ) : violations.length === 0 ? (
                <EmptyState title="No violations" description="No violations have been recorded. Create one above — open violations become queue items instead of memos." />
              ) : (
                <Table
                  columns={[
                    { key: "id", header: "ID", accessor: (v) => <span className="font-mono text-xs tabular-nums">#{v.id}</span> },
                    { key: "rule", header: "Rule", accessor: (v) => <span className="font-mono text-xs tabular-nums">#{v.rule_id}</span> },
                    { key: "employee", header: "Employee", accessor: (v) => <span className="text-xs tabular-nums">{v.employee_id ? `#${v.employee_id}` : "\u2014"}</span> },
                    { key: "status", header: "Status", accessor: (v) => <StatusPill status={v.status} /> },
                    { key: "detected", header: "Detected", accessor: (v) => <span className="whitespace-nowrap">{fmtDate(v.detected_at)}</span> },
                    { key: "resolved", header: "Resolved", accessor: (v) => <span className="whitespace-nowrap">{fmtDate(v.resolved_at)}</span> },
                    { key: "notes", header: "Notes", accessor: (v) => (
                      <span className="text-xs max-w-[220px] truncate" title={v.notes ?? ""}>
                        {v.notes || "\u2014"}
                      </span>
                    ) },
                    { key: "action", header: "Action", accessor: (v) => (
                      v.status !== "Resolved" && !v.resolved_at ? (
                        resolveConfirm === v.id ? (
                          <span className="inline-flex items-center gap-1">
                            <Button size="xs" variant="primary" loading={resolveMutation.isPending} onClick={() => resolveMutation.mutate(v.id)}>
                              Confirm
                            </Button>
                            <Button size="xs" variant="ghost" onClick={() => setResolveConfirm(null)}>
                              Cancel
                            </Button>
                          </span>
                        ) : (
                          <Button size="xs" variant="secondary" onClick={() => setResolveConfirm(v.id)}>
                            Resolve
                          </Button>
                        )
                      ) : (
                        <span className="text-xs text-[color:var(--fg-muted)]">{"\u2014"}</span>
                      )
                    ) },
                  ]}
                  data={violations}
                  keyAccessor={(v) => v.id}
                  caption="Compliance violations"
                  sortable={false}
                />
              )}
              {violations.length > 0 && (
                <p className="text-xs text-[color:var(--fg-muted)] mt-3 px-1">PUT /compliance/compliance-violations/{"{id}"}/resolve marks a violation resolved and writes <code className="font-mono text-xs">resolve_compliance_violation</code> to the audit trail.</p>
              )}
            </SectionCard>
          </TabsContent>

          <TabsContent value="payroll-in" className="space-y-4 mt-4">
            <SectionCard compact title="India payroll compliance reports" description="GET /reports/payroll?jurisdiction=IN&period=YYYY-MM — Payroll Register (all payslips with statutory columns), TDS liability (tax+rebate), PF/ESI summary (EE/ER + ceilings 15000/21000), PT by state. Requires verified pack; pending shows rule_pack_not_verified gate (409). Unverified export refused like docs/PAYROLL.md §3.3.">
              <div className="flex flex-wrap gap-3 items-end">
                <div>
                  <label className="block text-xs font-medium mb-1">Period (YYYY-MM)</label>
                  <Input value={payrollPeriod} onChange={e=>setPayrollPeriod(e.target.value)} placeholder="e.g. 2025-10" style={{ width: 160 }} />
                </div>
                <Button onClick={loadPayrollReports} loading={payrollLoading}>Load IN reports</Button>
                <span className="text-xs text-[color:var(--fg-muted)]">Jurisdiction=IN fixed · verified pack required · pending returns 409 rule_pack_not_verified</span>
              </div>
              {payrollPendingMsg && <div className="mt-3">{payrollPendingMsg.includes("rule_pack_not_verified") ? <PendingVerificationAlert /> : <Alert tone="error" title="Payroll report gated"><span data-testid="payroll-report-pending">{payrollPendingMsg}</span></Alert>}</div>}
              {payrollReports && (
                <div className="mt-4 space-y-4">
                  <div className="text-xs text-[color:var(--fg-muted)]">
                    Lineage: <span className="font-mono">{payrollReports.lineage?.rule_pack_id} v{payrollReports.lineage?.version}</span> · {payrollReports.lineage?.effective_from} → {payrollReports.lineage?.effective_to} · Currency {payrollReports.currency} · Pack status {payrollReports.pack_status}
                  </div>
                  <SectionCard compact title={`Payroll Register — ${payrollReports.payroll_register_count} payslips`} description="All payslips with statutory columns (BASIC, TAX_*, REBATE_87A, PF/ESI EE, PT_{STATE}) from deductions_json/earnings_json">
                    <div className="table-scroll overflow-x-auto">
                      <Table
                        columns={[
                          { key: "payslip", header: "Payslip", accessor: (r: any) => `#${r.payslip_id}` },
                          { key: "employee", header: "Employee", accessor: (r: any) => `#${r.employee_id}` },
                          { key: "gross", header: "Gross", accessor: (r: any) => r.gross, cellClassName: "num tabular-nums" },
                          { key: "net", header: "Net", accessor: (r: any) => r.net, cellClassName: "num tabular-nums" },
                          { key: "basic", header: "BASIC", accessor: (r: any) => r.basic, cellClassName: "num tabular-nums" },
                          { key: "tax", header: "TAX", accessor: (r: any) => r.tax, cellClassName: "num tabular-nums" },
                          { key: "rebate", header: "Rebate", accessor: (r: any) => r.rebate_87a, cellClassName: "num tabular-nums" },
                          { key: "pf", header: "PF EE", accessor: (r: any) => r.pf_ee, cellClassName: "num tabular-nums" },
                          { key: "esi", header: "ESI EE", accessor: (r: any) => r.esi_ee, cellClassName: "num tabular-nums" },
                          { key: "pt", header: "PT", accessor: (r: any) => r.pt_state ? `${r.pt_state}: ${r.pt_amount}` : "\u2014" },
                          { key: "currency", header: "Currency", accessor: (r: any) => r.currency || "INR" },
                        ]}
                        data={payrollReports.payroll_register || []}
                        keyAccessor={(r: any) => r.payslip_id}
                        caption={`Payroll Register — ${payrollReports.payroll_register_count} payslips`}
                        sortable={false}
                      />
                    </div>
                  </SectionCard>
                  <div className="grid sm:grid-cols-3 gap-4">
                    <SectionCard compact title="TDS liability"><div className="p-4 text-sm space-y-1"><div>Total TDS: <span className="font-mono tabular-nums">{payrollReports.tds_liability?.total_tds}</span></div><div>Rebate 87A: <span className="font-mono tabular-nums">{payrollReports.tds_liability?.total_rebate_87a}</span></div><div>Net TDS: <span className="font-mono tabular-nums">{payrollReports.tds_liability?.net_tds}</span></div><div className="text-xs text-[color:var(--fg-muted)]">{payrollReports.tds_liability?.payslips} payslips</div></div></SectionCard>
                    <SectionCard compact title="PF/ESI summary"><div className="p-4 text-sm space-y-1"><div>PF EE: <span className="font-mono">{payrollReports.pf_esi_summary?.total_pf_ee}</span></div><div>ESI EE: <span className="font-mono">{payrollReports.pf_esi_summary?.total_esi_ee}</span></div><div>Employee contribs: <span className="font-mono">{payrollReports.pf_esi_summary?.total_employee_contributions}</span></div><div>Employer contribs: <span className="font-mono">{payrollReports.pf_esi_summary?.total_employer_contributions}</span></div><div className="text-xs text-[color:var(--fg-muted)]">Ceilings PF 15000 · ESI 21000 · {payrollReports.pf_esi_summary?.payslips} slips</div></div></SectionCard>
                    <SectionCard compact title="PT by state"><div className="p-4 text-sm space-y-1"><div>Total PT: <span className="font-mono">{payrollReports.pt_by_state?.total_pt}</span></div>{Object.entries(payrollReports.pt_by_state?.by_state || {}).map(([st,amt]:any)=>(<div key={st}>{st}: <span className="font-mono">{String(amt)}</span></div>))}<div className="text-xs text-[color:var(--fg-muted)]">{payrollReports.pt_by_state?.payslips} slips</div></div></SectionCard>
                  </div>
                </div>
              )}
            </SectionCard>

            {/* Filings sub-tabs (AC-34..36) — 5 types under payroll-IN */}
            <SectionCard
              compact
              title="India filings — statutory exports"
              description="GET /reports/filings/{type}?jurisdiction=IN&period=YYYY-MM&state=KA/MH/TN/TG/WB — 5 types: 24q, form16_annual, pf_ecr, esi_return, pt_challan. Period YYYY-MM (YYYY for Form 16). PT state select; unknown state 422. Download IN_{TYPE}_{PERIOD}.txt via blob Content-Disposition (filings.py:329). Pending gate 409 rule_pack_not_verified reuses payroll-in Alert pattern."
            >
              <div className="space-y-4">
                <PendingVerificationAlert />

                <Tabs value={filingType} onValueChange={setFilingType}>
                  <TabsList>
                    <TabsTrigger value="24q">24Q</TabsTrigger>
                    <TabsTrigger value="form16_annual">Form 16</TabsTrigger>
                    <TabsTrigger value="pf_ecr">PF ECR</TabsTrigger>
                    <TabsTrigger value="esi_return">ESI Return</TabsTrigger>
                    <TabsTrigger value="pt_challan">PT Challan</TabsTrigger>
                  </TabsList>
                </Tabs>

                <div className="flex flex-wrap gap-3 items-end">
                  <div>
                    <label className="block text-xs font-medium mb-1">
                      Period {filingType === "form16_annual" ? "(YYYY or YYYY-MM)" : "(YYYY-MM)"}
                    </label>
                    <Input
                      value={filingPeriod}
                      onChange={(e) => setFilingPeriod(e.target.value)}
                      placeholder={filingType === "form16_annual" ? "e.g. 2025 or 2025-10" : "e.g. 2025-10"}
                      style={{ width: 160 }}
                      data-testid="filing-period"
                    />
                  </div>
                  {filingType === "pt_challan" && (
                    <div>
                      <label className="block text-xs font-medium mb-1">PT state</label>
                      <Select
                        value={filingState}
                        onChange={(e) => setFilingState(e.target.value)}
                        style={{ width: 140 }}
                        data-testid="filing-state"
                      >
                        <option value="KA">KA</option>
                        <option value="MH">MH</option>
                        <option value="TN">TN</option>
                        <option value="TG">TG</option>
                        <option value="WB">WB</option>
                      </Select>
                      <p className="text-xs text-[color:var(--fg-muted)]">Outside 5 → 422 pt state must be one of …</p>
                    </div>
                  )}
                  <Button onClick={loadFiling} loading={filingLoading} data-testid="filing-load">
                    Load filing
                  </Button>
                  {filingData && (
                    <Button variant="secondary" onClick={downloadFiling} data-testid="filing-download">
                      Download IN_{filingTypeToFilenamePart(filingType, filingType === "pt_challan" ? filingState : undefined)}_{filingPeriod.trim() || "PERIOD"}.txt
                    </Button>
                  )}
                  <span className="text-xs text-[color:var(--fg-muted)]">GET /reports/filings/{filingType}?jurisdiction=IN&amp;period={filingPeriod || "YYYY-MM"}{filingType === "pt_challan" ? `&state=${filingState}` : ""}</span>
                </div>

                {filingError && (
                  filingError.includes("rule_pack_not_verified") ? <PendingVerificationAlert /> : <Alert tone="error" title="Filing gated or invalid"><span data-testid="filing-pending">{filingError}</span>{filingError.includes("pt state must be one of") && <span data-testid="filing-422-pt"> — pt state must be one of …</span>}</Alert>
                )}

                {filingData && !filingError && (
                  <div className="space-y-3" data-testid="filing-result">
                    <div className="text-xs text-[color:var(--fg-muted)]">Raw txt split by comma → table. Content-Disposition handled for download filename IN_{"{TYPE}"}_{"{PERIOD}"}.txt (PT suffix _{filingState}).</div>
                    {/* KIT EXCLUSION (contract: design-system-finish) — raw filing-txt
                        preview: rows are comma-split at runtime with comment/header/body
                        row kinds and a dynamic column count, not tabular data with
                        fixed string headers, so this table stays raw by design. */}
                    <div className="table-scroll overflow-x-auto">
                      <table className="table-base table-compact w-full text-sm">
                        <caption className="sr-only">Filing {filingType} — period {filingPeriod}</caption>
                        <tbody>
                          {filingData
                            .split("\n")
                            .filter((l) => l.trim().length > 0)
                            .map((line, idx) => {
                              const isComment = line.trim().startsWith("#")
                              if (isComment) {
                                return (
                                  <tr key={idx} className="bg-[color:var(--surface)]">
                                    <td colSpan={10} className="px-3 py-1 text-xs text-[color:var(--fg-muted)] font-mono">
                                      {line}
                                    </td>
                                  </tr>
                                )
                              }
                              const cells = line.split(",")
                              // First non-comment line is header → render as header row
                              const isHeader = idx === 1 || (idx === 0 && !filingData.split("\n")[0].startsWith("#"))
                              if (isHeader && cells.length > 1) {
                                return (
                                  <tr key={idx} className="border-b border-[color:var(--border)]">
                                    {cells.map((c, ci) => (
                                      <th key={ci} className="px-3 py-2 text-xs font-semibold text-[color:var(--fg-muted)] text-left">
                                        {c}
                                      </th>
                                    ))}
                                  </tr>
                                )
                              }
                              return (
                                <tr key={idx} className="border-b border-[color:var(--border)]">
                                  {cells.map((c, ci) => (
                                    <td key={ci} className="px-3 py-2 text-xs tabular-nums">
                                      {c}
                                    </td>
                                  ))}
                                </tr>
                              )
                            })}
                        </tbody>
                      </table>
                    </div>
                    <div className="flex gap-2">
                      <Button variant="secondary" size="sm" onClick={downloadFiling}>
                        Download IN_{filingTypeToFilenamePart(filingType, filingType === "pt_challan" ? filingState : undefined)}_{filingPeriod.trim()}.txt
                      </Button>
                      <span className="text-xs text-[color:var(--fg-muted)] self-center">Blob download — handles Content-Disposition at filings.py:329; PT suffix _KA etc.</span>
                    </div>
                  </div>
                )}
              </div>
            </SectionCard>
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  )
}