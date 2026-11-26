/**
 * Break-glass emergency access — SuperAdmin + MFA grants.
 *
 * Gates mirror backend/app/api/v1/endpoints/break_glass.py:
 *  POST /break-glass/access (SuperAdmin + MFA, body: actor_id/target_tenant_id/purpose/ttl_minutes)
 *  GET  /break-glass/grants (SuperAdmin)
 *  DELETE /break-glass/grants/{id} (SuperAdmin)
 *
 * Every grant is written to the audit trail (create_break_glass_grant / revoke_break_glass_grant).
 */
import { useState, type FormEvent } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Layout } from "@/components/Layout"
import { Input, Textarea, Select,Alert, Button, EmptyState, LoadingRegion, PageHeader, SectionCard, TableSkeleton, RetryableAlert} from "@/components/ui"

import { StatusPill } from "@/components/ui/status-pill"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { errorMessage, listClients } from "@/lib/api"

interface BreakGlassGrantOut {
  id: number
  actor_id: number
  target_tenant_id: string
  purpose: string
  ttl_minutes: number
  granted_at: string | null
  expires_at: string | null
  revoked_at: string | null
  granted_by: number | null
  is_active: boolean
}

function fmtDate(v?: string | null) {
  if (!v) return "—"
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return v.slice(0, 19).replace("T", " ")
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(d)
}

export default function BreakGlass() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const qc = useQueryClient()
  const isSuperAdmin = user?.role === "SuperAdmin"

  const [actorId, setActorId] = useState<string>(() => (user?.id ? String(user.id) : ""))
  const [targetTenant, setTargetTenant] = useState("")
  const [purpose, setPurpose] = useState("")
  const [ttlMinutes, setTtlMinutes] = useState<number>(240)
  const [formError, setFormError] = useState("")
  const [notice, setNotice] = useState("")
  const [revokeError, setRevokeError] = useState("")
  const [revokeConfirm, setRevokeConfirm] = useState<number | null>(null)

  const clientsQuery = useQuery({
    queryKey: ["clients"],
    queryFn: listClients,
    enabled: isSuperAdmin,
  })

  const grantsQuery = useQuery({
    queryKey: ["break-glass-grants"],
    queryFn: async () => {
      const { data } = await api.get<BreakGlassGrantOut[]>("/break-glass/grants")
      return data
    },
    enabled: isSuperAdmin,
  })

  const createMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        actor_id: Number(actorId),
        target_tenant_id: targetTenant,
        purpose: purpose.trim(),
        ttl_minutes: Number(ttlMinutes),
      }
      const { data } = await api.post<BreakGlassGrantOut>("/break-glass/access", payload)
      return data
    },
    onSuccess: (data) => {
      setNotice(`Break-glass grant #${data.id} created for tenant ${data.target_tenant_id} — expires ${fmtDate(data.expires_at)}.`)
      setRevokeError("")
      qc.invalidateQueries({ queryKey: ["break-glass-grants"] })
      setPurpose("")
      setFormError("")
    },
    onError: (err: unknown) => {
      setFormError(errorMessage(err, "Could not create grant. Requires SuperAdmin + MFA."))
    },
  })

  const revokeMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/break-glass/grants/${id}`)
      return id
    },
    onSuccess: (id) => {
      setNotice(`Grant #${id} revoked.`)
      setRevokeError("")
      qc.invalidateQueries({ queryKey: ["break-glass-grants"] })
      setRevokeConfirm(null)
    },
    onError: (err: unknown) => {
      setRevokeError(errorMessage(err, "Could not revoke grant."))
    },
  })

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    setFormError("")
    setNotice("")
    setRevokeError("")
    if (!actorId || Number.isNaN(Number(actorId)) || Number(actorId) <= 0) {
      setFormError("Actor ID is required (numeric).")
      return
    }
    if (!targetTenant) {
      setFormError("Target tenant is required.")
      return
    }
    if (!purpose.trim()) {
      setFormError("Purpose is required.")
      return
    }
    const ttl = Number(ttlMinutes)
    if (!ttl || ttl < 1 || ttl > 480) {
      setFormError("TTL must be between 1 and 480 minutes (max 8h, default 240).")
      return
    }
    createMutation.mutate()
  }

  if (!isSuperAdmin) {
    return (
      <Layout>
        <div data-tenant-slug={tenant?.slug ?? "—"}>
          <PageHeader compact title="Break-glass" description="Emergency cross-tenant access — SuperAdmin + MFA only. Every grant is written to the audit trail." />
          <EmptyState title="Not visible for your role" description={`Break-glass requires SuperAdmin; your role is ${user?.role || "unknown"}.`} />
        </div>
      </Layout>
    )
  }

  const grants = grantsQuery.data ?? []

  return (
    <Layout>
      <div data-tenant-slug={tenant?.slug ?? "—"} className="space-y-4">
        <PageHeader
          compact
          title="Break-glass"
          description="Emergency cross-tenant access — SuperAdmin + MFA only. Every grant is written to the audit trail."
        />

        <p className="text-xs text-[color:var(--fg-muted)] border border-[color:var(--border)] rounded-[var(--radius-md)] px-3 py-2 bg-[color:var(--surface)]">
          Audit note: Every grant is written to the audit trail (<code className="font-mono text-xs">create_break_glass_grant</code> / <code className="font-mono text-xs">revoke_break_glass_grant</code>). TTL is capped at 480 minutes (8 hours), default 240. Break-glass is never honored for FSM or registry modification.
        </p>

        {notice && <Alert tone="success">{notice}</Alert>}
        {revokeError && <Alert tone="error" title="Could not revoke grant">{revokeError}</Alert>}

        {/* Create grant form — POST /break-glass/access */}
        <SectionCard
          compact
          title="Create grant"
          description="POST /break-glass/access — SuperAdmin + MFA. The grant is time-boxed and audited. TTL max 480m (default 240m)."
        >
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label htmlFor="bg-actor" className="block text-xs font-medium text-[color:var(--fg)] mb-1">
                  Actor ID <span className="text-[color:var(--error)]">(required)</span>
                </label>
                <Input
                  id="bg-actor"
                  type="number"
                  min={1}
                  value={actorId}
                  onChange={(e) => setActorId(e.target.value)}
                  placeholder={user?.id ? String(user.id) : "e.g. 2"}
                />
                <p className="text-caption text-[color:var(--fg-muted)] mt-1">Defaults to current user. Must be a valid user ID.</p>
              </div>
              <div>
                <label htmlFor="bg-tenant" className="block text-xs font-medium text-[color:var(--fg)] mb-1">
                  Target tenant <span className="text-[color:var(--error)]">(required)</span>
                </label>
                {clientsQuery.data && clientsQuery.data.length > 0 ? (
                  <Select id="bg-tenant" value={targetTenant} onChange={(e) => setTargetTenant(e.target.value)}>
                    <option value="">Select tenant…</option>
                    {clientsQuery.data.map((c) => (
                      <option key={c.id} value={c.slug}>
                        {c.name} ({c.slug})
                      </option>
                    ))}
                  </Select>
                ) : (
                  <Input
                    id="bg-tenant"
                    value={targetTenant}
                    onChange={(e) => setTargetTenant(e.target.value)}
                    placeholder="tenant slug e.g. acme"
                  />
                )}
                {clientsQuery.isError && (
                  <p className="text-caption text-[color:var(--error)] mt-1">{errorMessage(clientsQuery.error, "Could not load tenants")}</p>
                )}
              </div>
              <div>
                <label htmlFor="bg-ttl" className="block text-xs font-medium text-[color:var(--fg)] mb-1">
                  TTL (minutes) <span className="text-[color:var(--error)]">(required)</span>
                </label>
                <Input id="bg-ttl" type="number" min={1} max={480} value={String(ttlMinutes)} onChange={(e) => setTtlMinutes(Number(e.target.value))} />
                <p className="text-caption text-[color:var(--fg-muted)] mt-1">Min 1, max 480 (8h). Default 240.</p>
              </div>
            </div>

            <div>
              <label htmlFor="bg-purpose" className="block text-xs font-medium text-[color:var(--fg)] mb-1">
                Purpose <span className="text-[color:var(--error)]">(required)</span>
              </label>
              <Textarea
                id="bg-purpose"
                value={purpose}
                onChange={(e) => setPurpose(e.target.value)}
                placeholder="Emergency justification — this is written to the audit trail"
                rows={3}
                required
              />
            </div>

            {formError && (
              <Alert tone="error" title="Could not create grant">
                {formError}
              </Alert>
            )}

            {createMutation.isError && !formError && (
              <Alert tone="error" title="Request failed">
                {errorMessage(createMutation.error, "Could not create grant.")}
              </Alert>
            )}

            <div className="flex items-center gap-2">
              <Button type="submit" loading={createMutation.isPending}>
                Grant access
              </Button>
              <span className="text-xs text-[color:var(--fg-muted)]">Requires SuperAdmin + MFA (server returns 401/403 otherwise).</span>
            </div>
          </form>
        </SectionCard>

        {/* Grants table — GET /break-glass/grants */}
        <SectionCard
          compact
          title="Grants"
          description="GET /break-glass/grants — SuperAdmin only. Revoke to end a grant early."
          actions={
            <Button variant="secondary" size="sm" onClick={() => grantsQuery.refetch()} disabled={grantsQuery.isFetching}>
              {grantsQuery.isFetching ? "Refreshing…" : "Refresh"}
            </Button>
          }
        >
          {grantsQuery.isLoading ? (
            <LoadingRegion label="Loading grants…">
              <TableSkeleton rows={5} cols={7} />
            </LoadingRegion>
          ) : grantsQuery.isError ? (
            <Alert tone="error" title="Could not load grants">
              {errorMessage(grantsQuery.error, "The grants could not be read.")}
            </Alert>
          ) : grants.length === 0 ? (
            <EmptyState title="No grants" description="No break-glass grants have been issued yet. Create one above — it will appear here and in the audit trail." />
          ) : (
            <div className="table-scroll overflow-x-auto">
              <table className="table-base table-compact w-full text-sm" style={{ borderCollapse: "collapse" }}>
                <caption className="sr-only">Break-glass grants</caption>
                <thead>
                  <tr className="border-b border-[color:var(--border)] text-left">
                    <th scope="col" className="px-3 py-2 text-xs font-semibold text-[color:var(--fg-muted)]">
                      ID
                    </th>
                    <th scope="col" className="px-3 py-2 text-xs font-semibold text-[color:var(--fg-muted)]">
                      Actor
                    </th>
                    <th scope="col" className="px-3 py-2 text-xs font-semibold text-[color:var(--fg-muted)]">
                      Target tenant
                    </th>
                    <th scope="col" className="px-3 py-2 text-xs font-semibold text-[color:var(--fg-muted)]">
                      Purpose
                    </th>
                    <th scope="col" className="px-3 py-2 text-xs font-semibold text-[color:var(--fg-muted)]">
                      Created
                    </th>
                    <th scope="col" className="px-3 py-2 text-xs font-semibold text-[color:var(--fg-muted)]">
                      Expires
                    </th>
                    <th scope="col" className="px-3 py-2 text-xs font-semibold text-[color:var(--fg-muted)]">
                      Status
                    </th>
                    <th scope="col" className="px-3 py-2 text-xs font-semibold text-[color:var(--fg-muted)]">
                      Action
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {grants.map((g) => (
                    <tr key={g.id} className="border-b border-[color:var(--border)] hover:bg-[color:var(--surface-hover)]">
                      <td className="px-3 py-2 font-mono text-xs">#{g.id}</td>
                      <td className="px-3 py-2 text-xs">{g.actor_id}</td>
                      <td className="px-3 py-2 font-mono text-xs">{g.target_tenant_id}</td>
                      <td className="px-3 py-2 text-xs max-w-[260px] truncate" title={g.purpose}>
                        {g.purpose}
                      </td>
                      <td className="px-3 py-2 text-xs whitespace-nowrap">{fmtDate(g.granted_at)}</td>
                      <td className="px-3 py-2 text-xs whitespace-nowrap">{fmtDate(g.expires_at)}</td>
                      <td className="px-3 py-2">
                        {g.revoked_at ? (
                          <StatusPill status="Revoked" />
                        ) : g.is_active ? (
                          <StatusPill status="Active" />
                        ) : (
                          <StatusPill status="Expired" />
                        )}
                      </td>
                      <td className="px-3 py-2">
                        {!g.revoked_at && g.is_active ? (
                          revokeConfirm === g.id ? (
                            <span className="inline-flex items-center gap-1">
                              <Button size="xs" variant="danger" loading={revokeMutation.isPending} onClick={() => revokeMutation.mutate(g.id)}>
                                Confirm
                              </Button>
                              <Button size="xs" variant="ghost" onClick={() => setRevokeConfirm(null)}>
                                Cancel
                              </Button>
                            </span>
                          ) : (
                            <Button size="xs" variant="secondary" onClick={() => setRevokeConfirm(g.id)}>
                              Revoke
                            </Button>
                          )
                        ) : (
                          <span className="text-xs text-[color:var(--fg-muted)]">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {grantsQuery.data && grantsQuery.data.length > 0 && (
            <p className="text-xs text-[color:var(--fg-muted)] mt-3 px-1">DELETE /break-glass/grants/{"{id}"} revokes a grant. Revoked and expired grants remain in the ledger.</p>
          )}
        </SectionCard>
      </div>
    </Layout>
  )
}