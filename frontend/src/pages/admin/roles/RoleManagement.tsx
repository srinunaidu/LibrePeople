/* Role Management - SuperAdmin only
 * Manages roles and permissions rules
 * AD-07 audit chain on every change
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton} from "@/components/ui"
import { Input } from "@/components/ui/inputs"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { errorMessage, getClientIdBySlug  } from "@/lib/api"

export default function RoleManagement() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [role, setRole] = useState("SuperAdmin")
  const [permissions, setPermissions] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [notice, setNotice] = useState("")
  const [error, setError] = useState("")

  const load = useCallback(async () => {
    setLoading(true)
    setError("")
    setNotice("")
    const id = await getClientIdBySlug()
    setClientId(id)
    if (id === null) {
      setError("Could not resolve tenant — verify the tenant exists.")
      return
    }
    try {
      const { data } = await api.get(`/onboarding-portal/clients/${id}/feature-flags`)
      const getCfg = (k: string) => (data as any[])?.find((x: any) => x.key === k)?.config
      setRole((getCfg("role") ?? "SuperAdmin"))
      const perms = getCfg("permissions") ? String(getCfg("permissions")).split(",") : []
      setPermissions(perms)
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setLoading(false)
    }
  }, []);
  useEffect(() => {
    load()
  }, [])

  const [saving, setSaving] = useState(false)
  const save = async () => {
    if (clientId === null) return

    setSaving(true)
    setError("")
    setNotice("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/role`, { config: role })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/permissions`, {
        value: permissions.join(","),
      })
      setNotice("Role configuration saved — audit row (AD-07) written.")
      load()
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setSaving(false)
    }
  }

  const ROLES = [
    { value: "SuperAdmin", label: "Super Admin" },
    { value: "HR", label: "Human Resources" },
    { value: "Manager", label: "Manager" },
    { value: "Employee", label: "Employee" },
  ]

  const PERMISSIONS = [
    { value: "read_departments", label: "Read Departments" },
    { value: "write_departments", label: "Write Departments" },
    { value: "read_jobs", label: "Read Jobs" },
    { value: "write_jobs", label: "Write Jobs" },
    { value: "read_employees", label: "Read Employees" },
    { value: "write_employees", label: "Write Employees" },
    { value: "manage_roles", label: "Manage Roles" },
  ]

  if (loading) {
    return (
      <Layout>
        <LoadingRegion label="Role Management"><TableSkeleton rows={4} cols={4} /></LoadingRegion>
      </Layout>
    )
  }

  return (
    <Layout>
      <PageHeader compact
        title="Role Management + Permissions"
        description="SuperAdmin only · manages roles and permissions rules · AD-07 audit on save."
      />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {error && <Alert tone="error">{error}</Alert>}

        <SectionCard compact
          title="Role Configuration"
          description="Per-tenant from /clients/:slug/feature-flags."
        >
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label>Role</label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                {ROLES.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label>Permissions</label>
              <select
                value={permissions.join(",")}
                onChange={(e) =>
                  setPermissions(e.target.value.split(",").filter(Boolean))}
                multiple
                className="w-full rounded border px-3 py-2"
              >
                {PERMISSIONS.map((p) => (
                  <option
                    key={p.value}
                    value={p.value}
                    selected={permissions.includes(p.value)}
                  >
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <Button
            onClick={save}
            disabled={!canWrite || saving || !clientId}
            className="mt-4"
          >
            {saving ? "Saving…" : "Save role"}
          </Button>
        </SectionCard>

        <SectionCard compact title="Permissions List">
          <div className="table-scroll">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th>Permission</th>
                  <th className="text-center">Active</th>
                </tr>
              </thead>
              <tbody>
                {PERMISSIONS.map((p) => (
                  <tr key={p.value} className="border-b">
                    <td>{p.label}</td>
                    <td className="text-center">
                      {permissions.includes(p.value) ? "Yes" : "No"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <div className="text-xs text-fg-muted">
          SuperAdmin only · AD-07 audit on every save · no role impersonation.
        </div>
      </div>
    </Layout>
  )
}