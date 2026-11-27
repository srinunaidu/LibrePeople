/**
 * Break-glass emergency access ledger — SuperAdmin + MFA.
 *
 * Gates mirror backend/app/api/v1/endpoints/break_glass.py:
 *  POST /break-glass/access (SuperAdmin + MFA, body: actor_id/target_tenant_id/purpose/ttl_minutes)
 *  GET  /break-glass/grants (SuperAdmin)
 *  DELETE /break-glass/grants/{id} (SuperAdmin)
 *
 * Single-tenant install: the cross-tenant grant-scope enforcement was
 * removed — no data endpoint honors a grant to reach another tenant.
 * Grants are recorded here as a time-boxed, fully audited ledger only.
 *
 * Every grant is written to the audit trail (create_break_glass_grant / revoke_break_glass_grant).
 */
import { useState, type FormEvent } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Layout } from "@/components/Layout"
import { Input, Textarea, Alert, Button, EmptyState, LoadingRegion, PageHeader, SectionCard, TableSkeleton, RetryableAlert, StatusPill, Table } from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { errorMessage } from "@/lib/api"

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
      setNotice(`Break-glass grant #${data.id} recorded (scope "${data.target_tenant_id}") — expires ${fmtDate(data.expires_at)}. Ledger entry only; it confers no access to another tenant.`)
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
          <PageHeader compact title="Break-glass" description="Emergency access ledger — SuperAdmin + MFA only. Grants are recorded and audited; they confer no access to another tenant in this single-tenant install." />
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
          description="Emergency access ledger — SuperAdmin + MFA only. Grants are recorded and audited; they confer no access to another tenant in this single-tenant install."
        />

        <p className="text-xs text-[color:var(--fg-muted)] border border-[color:var(--border)] rounded-[var(--radius-md)] px-3 py-2 bg-[color:var(--surface)]">
          Single-tenant install: no data endpoint honors a break-glass grant, so a grant cannot open access to any other tenant. This screen is an audited ledger of time-boxed emergency records — nothing here reaches across tenants because there is only one company in this install.
        </p>

        <p className="text-xs text-[color:var(--fg-muted)] border border-[color:var(--border)] rounded-[var(--radius-md)] px-3 py-2 bg-[color:var(--surface)]">
          Audit note: Every grant is written to the audit trail (<code className="font-mono text-xs">create_break_glass_grant</code> / <code className="font-mono text-xs">revoke_break_glass_grant</code>). TTL is capped at 480 minutes (8 hours), default 240. Break-glass is never honored for FSM or registry modification.
        </p>

        {notice && <Alert tone="success">{notice}</Alert>}
        {revokeError && <Alert tone="error" title="Could not revoke grant">{revokeError}</Alert>}

        {/* Create grant form — POST /break-glass/access */}
        <SectionCard
          compact
          title="Create grant"
          description="POST /break-glass/access — SuperAdmin + MFA. The grant is time-boxed and audited. TTL max 480m (default 240m). Ledger entry only — confers no cross-tenant access."
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
                <Input
                  id="bg-tenant"
                  value={targetTenant}
                  onChange={(e) => setTargetTenant(e.target.value)}
                  placeholder="tenant slug e.g. acme"
                />
                <p className="text-caption text-[color:var(--fg-muted)] mt-1">Scope label required by the API; recorded in the ledger only. There is no second tenant in this install.</p>
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
            <Table
              columns={[
                { key: "id", header: "ID", accessor: (g) => <span className="font-mono text-xs">#{g.id}</span> },
                { key: "actor", header: "Actor", accessor: (g) => <span className="text-xs">{g.actor_id}</span> },
                { key: "scope", header: "Scope · target tenant", accessor: (g) => <span className="font-mono text-xs">{g.target_tenant_id}</span> },
                {
                  key: "purpose",
                  header: "Purpose",
                  accessor: (g) => (
                    <span className="text-xs max-w-[260px] truncate" title={g.purpose}>
                      {g.purpose}
                    </span>
                  ),
                },
                { key: "created", header: "Created", accessor: (g) => <span className="text-xs whitespace-nowrap">{fmtDate(g.granted_at)}</span> },
                { key: "expires", header: "Expires", accessor: (g) => <span className="text-xs whitespace-nowrap">{fmtDate(g.expires_at)}</span> },
                {
                  key: "status",
                  header: "Status",
                  accessor: (g) =>
                    g.revoked_at ? (
                      <StatusPill status="Revoked" />
                    ) : g.is_active ? (
                      <StatusPill status="Active" />
                    ) : (
                      <StatusPill status="Expired" />
                    ),
                },
                {
                  key: "action",
                  header: "Action",
                  accessor: (g) =>
                    !g.revoked_at && g.is_active ? (
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
                    ),
                },
              ]}
              data={grants}
              keyAccessor={(g) => g.id}
              caption="Break-glass grants"
              sortable={false}
            />
          )}
          {grantsQuery.data && grantsQuery.data.length > 0 && (
            <p className="text-xs text-[color:var(--fg-muted)] mt-3 px-1">DELETE /break-glass/grants/{"{id}"} revokes a grant. Revoked and expired grants remain in the ledger.</p>
          )}
        </SectionCard>
      </div>
    </Layout>
  )
}