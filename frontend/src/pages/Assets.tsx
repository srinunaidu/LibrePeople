import { useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {
  Button,
  Table,
  Alert,
  EmptyState,
  LoadingRegion,
  PageHeader,
  SectionCard,
  StatusPill,
} from "@/components/ui"
import { IconBriefcase, IconRefresh } from "@/components/icons"
import api, { errorMessage } from "@/lib/api"
import { fetchAllEmployees } from "@/lib/employees"
import { useAuth } from "@/context/AuthContext"

/* ------------------------------------------------------------------ *
 * Shared types and pure rules (mirrored by the backend contract in
 * backend/app/services/assets_service.py — keep the two in sync).
 * ------------------------------------------------------------------ */

export interface AssetRow {
  id: number
  tenant_id?: string | null
  tag: string
  name: string
  category: string
  description?: string | null
  serial_number?: string | null
  status: string
}

export interface AssignmentRow {
  id: number
  asset_id: number
  employee_id: number
  status: string
  notes?: string | null
  assigned_at?: string | null
  acknowledged_at?: string | null
  closed_at?: string | null
  close_reason?: string | null
  return_condition?: string | null
}

export type ReturnCondition = "good" | "damaged" | "lost"

export const RETURN_CONDITIONS: ReturnCondition[] = ["good", "damaged", "lost"]

/** A return's condition decides the asset's next status (backend FSM). */
export function conditionToStatus(condition: ReturnCondition): string {
  return { good: "in_stock", damaged: "maintenance", lost: "lost" }[condition]
}

/** Manage (create/assign/transfer/return/maintenance/retire) is HR/Admin. */
export function canManageAssets(role?: string | null): boolean {
  return role === "SuperAdmin" || role === "HR"
}

/** Only an open, unacknowledged spell can be acknowledged — self-only. */
export function ackable(a: AssignmentRow): boolean {
  return a.status === "open" && !a.acknowledged_at
}

/** The lifecycle actions the FSM allows from a status (409 otherwise). */
export function actionsForStatus(status: string): string[] {
  switch (status) {
    case "in_stock":
      return ["assign", "maintenance_start", "retire"]
    case "assigned":
      // Maintenance is blocked while assigned: custody must end first.
      return ["transfer", "return"]
    case "maintenance":
      return ["maintenance_complete", "retire"]
    default:
      // retired and lost are final.
      return []
  }
}

/** The open custody spell of an asset, if any (single-open rule). */
export function openAssignmentFor(
  assignments: AssignmentRow[],
  assetId: number
): AssignmentRow | undefined {
  return assignments.find((a) => a.asset_id === assetId && a.status === "open")
}

/** Managers (and HR/Admin) may view asset clearance; Associates may not. */
export function canViewClearance(role?: string | null): boolean {
  return role === "SuperAdmin" || role === "HR" || role === "Manager"
}

/** Query params for GET /assets — empty filters are omitted entirely. */
export function buildAssetListParams(
  statusFilter: string,
  categoryFilter: string
): Record<string, string> {
  const params: Record<string, string> = {}
  const s = (statusFilter || "").trim()
  const c = (categoryFilter || "").trim()
  if (s) params.status = s
  if (c) params.category = c
  return params
}

export interface AssetEditInput {
  tag: string
  name: string
  category: string
  description?: string | null
  serial_number?: string | null
  /** Anything carrying a status must not leak it into the PATCH payload. */
  status?: string | null
  [key: string]: unknown
}

/**
 * Metadata PATCH payload: tag/name/category/description/serial only.
 * Status is never editable — even if present on the input it is dropped.
 * Empty-string description/serial are omitted (no null writes).
 */
export function buildAssetEditPayload(input: AssetEditInput): Record<string, string> {
  const payload: Record<string, string> = {}
  const tag = (input.tag ?? "").toString().trim()
  const name = (input.name ?? "").toString().trim()
  const category = (input.category ?? "").toString().trim()
  if (tag) payload.tag = tag
  if (name) payload.name = name
  if (category) payload.category = category
  const desc = input.description == null ? "" : input.description.toString().trim()
  if (desc) payload.description = desc
  const serial = input.serial_number == null ? "" : input.serial_number.toString().trim()
  if (serial) payload.serial_number = serial
  return payload
}

/** Retirement is final: a reason plus an explicit confirm are required. */
export function isRetireReady(reason: string, confirmed: boolean): boolean {
  return (reason || "").trim().length > 0 && confirmed === true
}

export interface AssetClearanceItem {
  assignment_id: number
  asset_id: number
  tag: string
  name: string
  assigned_at?: string | null
  acknowledged_at?: string | null
}

export interface AssetClearance {
  employee_id: number
  clear: boolean
  outstanding_count: number
  outstanding: AssetClearanceItem[]
}

/** Human rendering of a clearance projection: "clear" or "N outstanding". */
export function clearanceStatusText(c: AssetClearance): string {
  if (c.clear || c.outstanding_count === 0) return "clear"
  return `${c.outstanding_count} outstanding`
}

export const ASSET_STATUS_LABELS: Record<string, string> = {
  in_stock: "In stock",
  assigned: "Assigned",
  maintenance: "Maintenance",
  retired: "Retired",
  lost: "Lost",
}

/* ------------------------------------------------------------------ *
 * The register page (HR/Admin manage; other roles read their scope).
 * ------------------------------------------------------------------ */

export default function Assets() {
  const { user } = useAuth()
  const isAdmin = canManageAssets(user?.role)
  const [assets, setAssets] = useState<AssetRow[]>([])
  const [assignments, setAssignments] = useState<AssignmentRow[]>([])
  const [employees, setEmployees] = useState<{ id: number; first_name: string; last_name: string; employee_id: string; status: string }[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [busy, setBusy] = useState("")
  const [selected, setSelected] = useState<AssetRow | null>(null)
  const [form, setForm] = useState({ tag: "", name: "", category: "IT", serial_number: "" })
  const [holderId, setHolderId] = useState("")
  const [condition, setCondition] = useState<ReturnCondition>("good")
  const [statusFilter, setStatusFilter] = useState("")
  const [categoryFilter, setCategoryFilter] = useState("")
  const [edit, setEdit] = useState({ tag: "", name: "", category: "", description: "", serial_number: "" })
  const [history, setHistory] = useState<AssignmentRow[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [clearanceEmpId, setClearanceEmpId] = useState("")
  const [clearance, setClearance] = useState<AssetClearance | null>(null)
  const [clearanceBusy, setClearanceBusy] = useState(false)
  const [clearanceError, setClearanceError] = useState("")
  const [retireReason, setRetireReason] = useState("")
  const [retireConfirm, setRetireConfirm] = useState(false)
  const canClear = canViewClearance(user?.role)

  const load = async (over?: { status?: string; category?: string }) => {
    setLoading(true)
    setError("")
    const sf = over && "status" in over ? (over.status ?? "") : statusFilter
    const cf = over && "category" in over ? (over.category ?? "") : categoryFilter
    const params = buildAssetListParams(sf, cf)
    const results = await Promise.allSettled([
      api.get("/assets", { params }),
      api.get("/assets/assignments"),
      isAdmin ? fetchAllEmployees().then(({ items }) => ({ data: items })) : Promise.resolve({ data: [] }),
    ])
    const [a, s, e] = results
    if (a.status === "fulfilled") setAssets(a.value.data)
    if (s.status === "fulfilled") setAssignments(s.value.data)
    if (e.status === "fulfilled") setEmployees(e.value.data)
    if (a.status !== "fulfilled") {
      setError(errorMessage(a.reason, "Could not load the asset register."))
    }
    setLoading(false)
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Refetch the register whenever a filter changes (AC1: ?status=&category=).
  useEffect(() => {
    load({ status: statusFilter, category: categoryFilter })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, categoryFilter])

  // Per-asset custody history via GET /assets/assignments?asset_id= (AC3).
  useEffect(() => {
    if (!selected) {
      setHistory([])
      return
    }
    setHistoryLoading(true)
    api
      .get("/assets/assignments", { params: { asset_id: selected.id } })
      .then((r) => setHistory(r.data))
      .catch(() => setHistory(assignments.filter((a) => a.asset_id === selected.id)))
      .finally(() => setHistoryLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected?.id])

  const act = async (key: string, run: () => Promise<unknown>, ok: string) => {
    setBusy(key)
    setError("")
    setNotice("")
    try {
      await run()
      setNotice(ok)
      setSelected(null)
      setHolderId("")
      setCondition("good")
      setRetireReason("")
      setRetireConfirm(false)
      await load()
    } catch (err) {
      // 409s (invalid_state_transition, duplicate_natural_key,
      // employee_not_active, asset_already_assigned…) carry the server's
      // message verbatim — the FSM refuses with a reason, not a guess.
      setError(errorMessage(err, "The asset action was refused."))
    } finally {
      setBusy("")
    }
  }

  const select = (a: AssetRow) => {
    setSelected(a)
    setHolderId("")
    setCondition("good")
    setRetireReason("")
    setRetireConfirm(false)
    setEdit({
      tag: a.tag ?? "",
      name: a.name ?? "",
      category: a.category ?? "",
      description: a.description ?? "",
      serial_number: a.serial_number ?? "",
    })
  }

  const checkClearance = async () => {
    const id = clearanceEmpId.trim()
    if (!id) return
    setClearanceBusy(true)
    setClearanceError("")
    setClearance(null)
    try {
      const r = await api.get(`/assets/clearance/${id}`)
      setClearance(r.data)
    } catch (err) {
      setClearanceError(errorMessage(err, "Could not load clearance."))
    } finally {
      setClearanceBusy(false)
    }
  }

  const employeeName = (id: number) => {
    const e = employees.find((x) => x.id === id)
    return e ? `${e.first_name} ${e.last_name}` : `Employee ${id}`
  }

  const holderOf = (assetId: number) => {
    const open = openAssignmentFor(assignments, assetId)
    return open ? employeeName(open.employee_id) : "—"
  }

  const allowed = selected ? actionsForStatus(selected.status) : []
  const activeEmployees = employees.filter((e) => e.status === "Active")

  const categories = Array.from(new Set(assets.map((a) => a.category).filter(Boolean))).sort()

  return (
    <Layout>
      <PageHeader
        compact
        icon={<IconBriefcase />}
        title="Assets"
        description="Track company assets and who holds them. Custody moves are explicit and audited."
        actions={
          <Button variant="secondary" size="sm" type="button" onClick={() => load()}>
            <IconRefresh className="w-4 h-4" /> Reload
          </Button>
        }
      />

      {error && (
        <Alert tone="error" title="Asset action refused" action={
          <Button variant="secondary" size="sm" type="button" onClick={() => load()}>Reload</Button>
        }>
          {error}
        </Alert>
      )}
      {notice && <Alert tone="success">{notice}</Alert>}

      {loading ? (
        <LoadingRegion label="Loading assets">
          <div className="skeleton h-48" />
        </LoadingRegion>
      ) : (
        <>
          {isAdmin && (
            <SectionCard compact icon={<IconBriefcase />} title="Register a new asset"
              description="Tag and name are required; the asset starts In stock.">
              <div className="toolbar">
                <div className="field">
                  <label htmlFor="ast-tag" className="field-label">Tag (required, unique)</label>
                  <input id="ast-tag" className="input" value={form.tag}
                    onChange={(e) => setForm({ ...form, tag: e.target.value })} placeholder="AST-0001" />
                </div>
                <div className="field grow min-w-[180px]">
                  <label htmlFor="ast-name" className="field-label">Name (required)</label>
                  <input id="ast-name" className="input" value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="MacBook Pro 14" />
                </div>
                <div className="field">
                  <label htmlFor="ast-cat" className="field-label">Category</label>
                  <input id="ast-cat" className="input" value={form.category}
                    onChange={(e) => setForm({ ...form, category: e.target.value })} />
                </div>
                <div className="field">
                  <label htmlFor="ast-serial" className="field-label">Serial number</label>
                  <input id="ast-serial" className="input" value={form.serial_number}
                    onChange={(e) => setForm({ ...form, serial_number: e.target.value })} />
                </div>
                <Button variant="primary" disabled={!form.tag.trim() || !form.name.trim() || busy === "create"}
                  onClick={() => act("create", () => api.post("/assets", {
                    tag: form.tag.trim(),
                    name: form.name.trim(),
                    category: form.category.trim() || "General",
                    serial_number: form.serial_number.trim() || undefined,
                  }), "Asset registered (in stock).")}>
                  {busy === "create" ? "Registering…" : "Register asset"}
                </Button>
              </div>
            </SectionCard>
          )}

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5 mb-5">
            <SectionCard compact icon={<IconBriefcase />} title="Register"
              description={isAdmin ? "Every asset in this tenant." : "Assets in your custody scope (read-only)."}>
              <div className="toolbar mb-3">
                <div className="field">
                  <label htmlFor="ast-fstatus" className="field-label">Status filter</label>
                  <select id="ast-fstatus" className="input" value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}>
                    <option value="">All statuses</option>
                    {Object.entries(ASSET_STATUS_LABELS).map(([v, l]) => (
                      <option key={v} value={v}>{l}</option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="ast-fcat" className="field-label">Category filter</label>
                  <select id="ast-fcat" className="input" value={categoryFilter}
                    onChange={(e) => setCategoryFilter(e.target.value)}>
                    <option value="">All categories</option>
                    {categories.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
                {(statusFilter || categoryFilter) && (
                  <Button variant="secondary" size="sm" type="button"
                    onClick={() => { setStatusFilter(""); setCategoryFilter("") }}>
                    Clear filters
                  </Button>
                )}
              </div>
              {assets.length === 0 ? (
                <EmptyState title="No assets" description={isAdmin ? "Register the first asset above." : "Nothing is in your custody yet."} />
              ) : (
                <Table
                  className="max-h-[420px] overflow-y-auto"
                  columns={[
                    { key: "tag", header: "Tag", accessor: (a) => <span className="font-mono">{a.tag}</span> },
                    { key: "name", header: "Name", accessor: (a) => a.name },
                    { key: "status", header: "Status", accessor: (a) => <StatusPill status={ASSET_STATUS_LABELS[a.status] ?? a.status} /> },
                    { key: "holder", header: "Holder", accessor: (a) => holderOf(a.id) },
                    ...(isAdmin ? [{
                      key: "actions", header: "", accessor: (a: AssetRow) => (
                        <Button variant="secondary" size="sm" type="button"
                          onClick={() => select(a)}>
                          Manage
                        </Button>
                      ),
                    }] : []),
                  ]}
                  data={assets}
                  keyAccessor={(a) => a.id}
                  caption="Asset register"
                  sortable={false}
                />
              )}
            </SectionCard>

            {isAdmin && selected && (
              <SectionCard compact title={`Manage ${selected.tag}`}
                description={`${selected.name} — ${ASSET_STATUS_LABELS[selected.status] ?? selected.status}. Only legal moves are offered; the server refuses the rest with a reason.`}>
                {allowed.length === 0 && (
                  <p className="text-sm text-fg-muted" role="note">
                    {ASSET_STATUS_LABELS[selected.status] ?? selected.status} is a final state — no further moves.
                  </p>
                )}
                {(allowed.includes("assign") || allowed.includes("transfer")) && (
                  <div className="toolbar mb-3">
                    <div className="field grow">
                      <label htmlFor="ast-holder" className="field-label">
                        {allowed.includes("assign") ? "Assign to (active employee)" : "Transfer to (active employee)"}
                      </label>
                      <select id="ast-holder" className="input" value={holderId}
                        onChange={(e) => setHolderId(e.target.value)}>
                        <option value="">Select employee…</option>
                        {activeEmployees.map((e) => (
                          <option key={e.id} value={e.id}>
                            {e.first_name} {e.last_name} ({e.employee_id})
                          </option>
                        ))}
                      </select>
                    </div>
                    {allowed.includes("assign") ? (
                      <Button variant="primary" disabled={!holderId || busy === "assign"}
                        onClick={() => act("assign", () => api.post(`/assets/${selected.id}/assign`, { employee_id: Number(holderId) }),
                          "Assigned. The employee must acknowledge receipt.")}>
                        {busy === "assign" ? "Assigning…" : "Assign"}
                      </Button>
                    ) : (
                      <Button variant="primary" disabled={!holderId || busy === "transfer"}
                        onClick={() => act("transfer", () => api.post(`/assets/${selected.id}/transfer`, { employee_id: Number(holderId) }),
                          "Transferred. The new holder must acknowledge afresh.")}>
                        {busy === "transfer" ? "Transferring…" : "Transfer"}
                      </Button>
                    )}
                  </div>
                )}
                {allowed.includes("return") && (
                  <div className="toolbar mb-3">
                    <div className="field">
                      <label htmlFor="ast-cond" className="field-label">Return condition</label>
                      <select id="ast-cond" className="input" value={condition}
                        onChange={(e) => setCondition(e.target.value as ReturnCondition)}>
                        {RETURN_CONDITIONS.map((c) => (
                          <option key={c} value={c}>{c} → {ASSET_STATUS_LABELS[conditionToStatus(c)]}</option>
                        ))}
                      </select>
                    </div>
                    <Button variant="primary" disabled={busy === "return"}
                      onClick={() => act("return", () => api.post(`/assets/${selected.id}/return`, { condition }),
                        `Returned (${condition}).`)}>
                      {busy === "return" ? "Returning…" : "Take return"}
                    </Button>
                  </div>
                )}
                {allowed.includes("retire") && (
                  <div className="toolbar mb-3">
                    <div className="field grow min-w-[160px]">
                      <label htmlFor="ast-retire-reason" className="field-label">Retire reason (required, final)</label>
                      <input id="ast-retire-reason" className="input" value={retireReason}
                        onChange={(e) => setRetireReason(e.target.value)}
                        placeholder="e.g. end of life, beyond repair" />
                    </div>
                    <label htmlFor="ast-retire-confirm" className="flex items-center gap-2 text-sm">
                      <input id="ast-retire-confirm" type="checkbox" checked={retireConfirm}
                        onChange={(e) => setRetireConfirm(e.target.checked)} />
                      I confirm retirement is final
                    </label>
                    <Button variant="secondary" disabled={!isRetireReady(retireReason, retireConfirm) || busy === "retire"}
                      onClick={() => act("retire", () => api.post(`/assets/${selected.id}/retire`, { reason: retireReason.trim() }), "Asset retired.")}>
                      {busy === "retire" ? "Retiring…" : "Retire"}
                    </Button>
                  </div>
                )}
                <div className="flex flex-wrap gap-2">
                  {allowed.includes("maintenance_start") && (
                    <Button variant="secondary" disabled={busy === "maint"}
                      onClick={() => act("maint", () => api.post(`/assets/${selected.id}/maintenance/start`, {}), "Sent to maintenance.")}>
                      Send to maintenance
                    </Button>
                  )}
                  {allowed.includes("maintenance_complete") && (
                    <Button variant="secondary" disabled={busy === "maint"}
                      onClick={() => act("maint", () => api.post(`/assets/${selected.id}/maintenance/complete`, {}), "Maintenance complete — back in stock.")}>
                      Complete maintenance
                    </Button>
                  )}
                  {allowed.includes("retire") && (
                    <span className="text-sm text-fg-muted self-center">Retirement uses the reason above.</span>
                  )}
                  <Button variant="secondary" onClick={() => setSelected(null)}>Close</Button>
                </div>
                <div className="mt-4 border-t pt-3">
                  <h4 className="section-title mb-2">Metadata (status is never editable)</h4>
                  <div className="toolbar mb-2">
                    <div className="field">
                      <label htmlFor="ast-edit-tag" className="field-label">Tag</label>
                      <input id="ast-edit-tag" className="input" value={edit.tag}
                        onChange={(e) => setEdit({ ...edit, tag: e.target.value })} />
                    </div>
                    <div className="field grow min-w-[140px]">
                      <label htmlFor="ast-edit-name" className="field-label">Name</label>
                      <input id="ast-edit-name" className="input" value={edit.name}
                        onChange={(e) => setEdit({ ...edit, name: e.target.value })} />
                    </div>
                    <div className="field">
                      <label htmlFor="ast-edit-cat" className="field-label">Category</label>
                      <input id="ast-edit-cat" className="input" value={edit.category}
                        onChange={(e) => setEdit({ ...edit, category: e.target.value })} />
                    </div>
                  </div>
                  <div className="toolbar">
                    <div className="field grow min-w-[140px]">
                      <label htmlFor="ast-edit-desc" className="field-label">Description</label>
                      <input id="ast-edit-desc" className="input" value={edit.description}
                        onChange={(e) => setEdit({ ...edit, description: e.target.value })} />
                    </div>
                    <div className="field">
                      <label htmlFor="ast-edit-serial" className="field-label">Serial number</label>
                      <input id="ast-edit-serial" className="input" value={edit.serial_number}
                        onChange={(e) => setEdit({ ...edit, serial_number: e.target.value })} />
                    </div>
                    <Button variant="secondary" disabled={busy === "edit"}
                      onClick={() => act("edit", () => api.patch(`/assets/${selected.id}`, buildAssetEditPayload(edit)), "Asset metadata updated.")}>
                      {busy === "edit" ? "Saving…" : "Save metadata"}
                    </Button>
                  </div>
                </div>
                <div className="mt-4 border-t pt-3">
                  <h4 className="section-title mb-2">Custody history</h4>
                  {historyLoading ? (
                    <p className="text-sm text-fg-muted">Loading history…</p>
                  ) : history.length === 0 ? (
                    <p className="text-sm text-fg-muted">No custody spells for this asset.</p>
                  ) : (
                    <Table
                      columns={[
                        { key: "holder", header: "Holder", accessor: (h) => employeeName(h.employee_id) },
                        { key: "ack", header: "Ack", accessor: (h) => (h.acknowledged_at ? h.acknowledged_at.slice(0, 10) : "Pending") },
                        { key: "reason", header: "Close reason", accessor: (h) => h.close_reason ?? (h.status === "open" ? "open" : "—") },
                        { key: "condition", header: "Condition", accessor: (h) => h.return_condition ?? "—" },
                      ]}
                      data={history}
                      keyAccessor={(h) => h.id}
                      caption={`Custody history for ${selected.tag}`}
                      sortable={false}
                    />
                  )}
                </div>
              </SectionCard>
            )}
          </div>
          {canClear && (
            <SectionCard compact title="Clearance"
              description="Read-only offboarding check: enter an employee id to list open custody, or clear.">
              <div className="toolbar mb-3">
                <div className="field">
                  <label htmlFor="ast-clear-emp" className="field-label">Employee id</label>
                  <input id="ast-clear-emp" className="input" value={clearanceEmpId}
                    onChange={(e) => setClearanceEmpId(e.target.value)}
                    placeholder="e.g. 100" inputMode="numeric" />
                </div>
                <Button variant="secondary" disabled={!clearanceEmpId.trim() || clearanceBusy}
                  onClick={checkClearance}>
                  {clearanceBusy ? "Checking…" : "Check clearance"}
                </Button>
              </div>
              {clearanceError && <Alert tone="error">{clearanceError}</Alert>}
              {clearance && (
                clearance.clear ? (
                  <p className="text-sm" role="status">Employee {clearance.employee_id} is clear — no outstanding custody.</p>
                ) : (
                  <div className="table-scroll max-h-[220px] overflow-y-auto">
                    <p className="text-sm mb-2" role="status">
                      Employee {clearance.employee_id}: {clearanceStatusText(clearance)}.
                    </p>
                    <Table
                      columns={[
                        { key: "tag", header: "Tag", accessor: (o) => <span className="font-mono">{o.tag}</span> },
                        { key: "asset", header: "Asset", accessor: (o) => o.name },
                        { key: "assigned", header: "Assigned", accessor: (o) => (o.assigned_at ? o.assigned_at.slice(0, 10) : "—") },
                        { key: "receipt", header: "Receipt", accessor: (o) => (o.acknowledged_at ? "Acknowledged" : "Pending") },
                      ]}
                      data={clearance.outstanding}
                      keyAccessor={(o) => o.assignment_id}
                      caption="Outstanding custody"
                      sortable={false}
                    />
                  </div>
                )
              )}
            </SectionCard>
          )}
        </>
      )}
    </Layout>
  )
}