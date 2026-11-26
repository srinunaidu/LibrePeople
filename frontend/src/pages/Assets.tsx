import { useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {
  Button,
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

  const load = async () => {
    setLoading(true)
    setError("")
    const results = await Promise.allSettled([
      api.get("/assets"),
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

  return (
    <Layout>
      <PageHeader
        compact
        icon={<IconBriefcase />}
        title="Assets"
        description="Track company assets and who holds them. Custody moves are explicit and audited."
        actions={
          <Button variant="secondary" size="sm" type="button" onClick={load}>
            <IconRefresh className="w-4 h-4" /> Reload
          </Button>
        }
      />

      {error && (
        <Alert tone="error" title="Asset action refused" action={
          <Button variant="secondary" size="sm" type="button" onClick={load}>Reload</Button>
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
            <section className="card mb-5" aria-label="Register an asset">
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
            </section>
          )}

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5 mb-5">
            <SectionCard compact icon={<IconBriefcase />} title="Register"
              description={isAdmin ? "Every asset in this tenant." : "Assets in your custody scope (read-only)."}>
              {assets.length === 0 ? (
                <EmptyState title="No assets" description={isAdmin ? "Register the first asset above." : "Nothing is in your custody yet."} />
              ) : (
                <div className="table-scroll max-h-[420px] overflow-y-auto">
                  <table className="table-base table-striped">
                    <caption className="sr-only">Asset register</caption>
                    <thead>
                      <tr>
                        <th scope="col">Tag</th>
                        <th scope="col">Name</th>
                        <th scope="col">Status</th>
                        <th scope="col">Holder</th>
                        {isAdmin && <th scope="col"><span className="sr-only">Actions</span></th>}
                      </tr>
                    </thead>
                    <tbody>
                      {assets.map((a) => (
                        <tr key={a.id}>
                          <td className="font-mono">{a.tag}</td>
                          <td>{a.name}</td>
                          <td><StatusPill status={ASSET_STATUS_LABELS[a.status] ?? a.status} /></td>
                          <td>{holderOf(a.id)}</td>
                          {isAdmin && (
                            <td>
                              <Button variant="secondary" size="sm" type="button"
                                onClick={() => { setSelected(a); setHolderId(""); setCondition("good") }}>
                                Manage
                              </Button>
                            </td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
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
                    <Button variant="secondary" disabled={busy === "retire"}
                      onClick={() => act("retire", () => api.post(`/assets/${selected.id}/retire`, {}), "Asset retired.")}>
                      Retire
                    </Button>
                  )}
                  <Button variant="secondary" onClick={() => setSelected(null)}>Close</Button>
                </div>
              </SectionCard>
            )}
          </div>
        </>
      )}
    </Layout>
  )
}