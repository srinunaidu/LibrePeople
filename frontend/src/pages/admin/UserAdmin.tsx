/**
 * User Administration — accounts, roles and access.
 *
 * Gates mirror backend/app/api/v1/endpoints/auth.py:
 *  GET /auth/users, POST /auth/users, PATCH /auth/users/{id}, POST /auth/users/{id}/password
 * all require_roles(*ADMIN_ROLES) (SuperAdmin, HR). POST /auth/users expects
 * { user_in: { username, email, password, role, is_active } } — UserCreateAdmin.
 */
import { useCallback, useEffect, useState, type FormEvent } from "react"
import { Layout } from "@/components/Layout"
import {Alert,
  Button,
  EmptyState,
  LoadingRegion,
  PageHeader,
  SectionCard,
  TableSkeleton, RetryableAlert} from "@/components/ui"
import { Input, Select } from "@/components/ui/inputs"
import { StatusPill } from "@/components/ui/status-pill"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import { formatDate } from "@/lib/format"
import api, { errorMessage, impersonateUser } from "@/lib/api"
import type { AdminUserRow } from "@/types"
import { useNavigate } from "react-router-dom"
import { useTenantNav } from "@/lib/tenantPath"

const VALID_ROLES = ["SuperAdmin", "HR", "Manager", "Associate", "PayrollViewer"] as const

export default function UserAdmin() {
  const { user, impersonate, isImpersonating } = useAuth()
  const { tenant } = useTenant()
  // Account timestamps render in the tenant locale/timezone via format.ts —
  // never the browser default.
  const fmtDate = (value?: string | null) =>
    formatDate(value, { locale: tenant?.locale, timeZone: tenant?.timezone })
  const navigate = useNavigate()
  const tenantNav = useTenantNav()
  const canRead = ["SuperAdmin", "HR"].includes(user?.role ?? "")
  const canImpersonate = user?.role === "SuperAdmin"

  const [users, setUsers] = useState<AdminUserRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [formErrors, setFormErrors] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState<"" | "create" | string>("")

  const [createForm, setCreateForm] = useState({
    username: "",
    email: "",
    password: "",
    role: "Associate" as string,
  })

  // Per-user inline edit: role + password reset
  const [roleDrafts, setRoleDrafts] = useState<Record<number, string>>({})
  const [passwordDrafts, setPasswordDrafts] = useState<Record<number, string>>({})

  const load = useCallback(async () => {
    if (!canRead) {
      setLoading(false)
      return
    }
    setLoading(true)
    setError("")
    try {
      const res = await api.get<AdminUserRow[]>("/auth/users")
      setUsers(res.data ?? [])
    } catch (err) {
      setUsers([])
      setError(errorMessage(err, "The users could not be read."))
    } finally {
      setLoading(false)
    }
  }, [canRead])

  useEffect(() => {
    void load()
  }, [load])

  async function submitCreate(event: FormEvent) {
    event.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, create: "" }))
    setNotice("")
    if (!createForm.username.trim() || !createForm.email.trim() || !createForm.password) {
      setFormErrors((c) => ({ ...c, create: "Username, email and password are required." }))
      return
    }
    if (!VALID_ROLES.includes(createForm.role as typeof VALID_ROLES[number])) {
      setFormErrors((c) => ({ ...c, create: `Role must be one of ${VALID_ROLES.join(", ")}.` }))
      return
    }
    setBusy("create")
    try {
      await api.post("/auth/users", {
        user_in: {
          username: createForm.username.trim(),
          email: createForm.email.trim(),
          password: createForm.password,
          role: createForm.role,
          is_active: true,
        },
      })
      setCreateForm({ username: "", email: "", password: "", role: "Associate" })
      setNotice("User created.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, create: errorMessage(err, "The user could not be created.") }))
    } finally {
      setBusy("")
    }
  }

  async function patchRole(userId: number) {
    const role = roleDrafts[userId]
    if (!role) return
    if (!VALID_ROLES.includes(role as typeof VALID_ROLES[number])) {
      setFormErrors((c) => ({ ...c, [`role-${userId}`]: `Role must be one of ${VALID_ROLES.join(", ")}.` }))
      return
    }
    setBusy(`role-${userId}`)
    setFormErrors((c) => ({ ...c, [`role-${userId}`]: "" }))
    try {
      await api.patch(`/auth/users/${userId}`, { role })
      setNotice(`Role updated for user #${userId}.`)
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, [`role-${userId}`]: errorMessage(err, "The role could not be changed.") }))
    } finally {
      setBusy("")
    }
  }

  async function resetPassword(userId: number) {
    const new_password = passwordDrafts[userId]
    if (!new_password) {
      setFormErrors((c) => ({ ...c, [`pwd-${userId}`]: "New password is required." }))
      return
    }
    setBusy(`pwd-${userId}`)
    setFormErrors((c) => ({ ...c, [`pwd-${userId}`]: "" }))
    try {
      await api.post(`/auth/users/${userId}/password`, { new_password })
      setPasswordDrafts((c) => ({ ...c, [userId]: "" }))
      setNotice(`Password reset for user #${userId}. They must change it at next sign-in.`)
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, [`pwd-${userId}`]: errorMessage(err, "The password could not be reset.") }))
    } finally {
      setBusy("")
    }
  }

  async function handleImpersonate(target: AdminUserRow) {
    if (target.id === user?.id) return
    const confirmed = window.confirm(
      `Impersonate ${target.username} (${target.role})?\n\nYou will view as this user. Your actions will be audited as impersonated by ${user?.username}.`
    )
    if (!confirmed) return
    setBusy(`imp-${target.id}`)
    setNotice("")
    setFormErrors((c) => ({ ...c, impersonate: "" }))
    try {
      const res = await impersonateUser(target.id)
      impersonate(res.access_token, {
        id: res.user.id,
        username: res.user.username,
        email: res.user.email,
        role: res.user.role,
        is_active: res.user.is_active,
      })
      setNotice(`Impersonating ${res.user.username} (${res.user.role})`)
      navigate(tenantNav.to("/dashboard"))
    } catch (err) {
      setFormErrors((c) => ({ ...c, impersonate: errorMessage(err, "Impersonation failed") }))
    } finally {
      setBusy("")
    }
  }

  if (!canRead) {
    return (
      <Layout>
        <div data-tenant-slug={tenant?.slug ?? "—"}>
          <PageHeader compact
            title="User Administration"
            description="Accounts, roles and access — SuperAdmin and HR"
          />
          <EmptyState
            title="Not visible for your role"
            description={`User administration requires SuperAdmin or HR; your role is ${user?.role || "unknown"}.`}
          />
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <div data-tenant-slug={tenant?.slug ?? "—"}>
        <PageHeader compact
        title="User Administration"
        description="Accounts, roles and access — SuperAdmin and HR"
        actions={
          <Button variant="secondary" onClick={() => void load()} disabled={loading}>
            Refresh
          </Button>
        }
      />

      {notice && <Alert tone="success">{notice}</Alert>}
      {formErrors.impersonate && <Alert tone="error">{formErrors.impersonate}</Alert>}
      {error && (
        <RetryableAlert err={error} title="The users could not be read" fallback="The users could not be read" onRetry={load} />
      )}

      {/* User list — GET /auth/users */}
      <SectionCard
        compact
        title="Users"
        description="Every account in this deployment. PATCH /{id} changes role; POST /{id}/password resets it (must_change_password)."
      >
        {loading ? (
          <LoadingRegion label="Loading users…">
            <TableSkeleton rows={5} cols={5} />
          </LoadingRegion>
        ) : error ? (
          <div className="p-5">
            <EmptyState title="The users could not be read" description={error} />
          </div>
        ) : users.length === 0 ? (
          <div className="p-5">
            <EmptyState title="No users" description="No accounts exist yet." />
          </div>
        ) : (
          <div className="table-scroll">
            <table className="table-base table-compact w-full text-sm">
              <caption className="sr-only">Users</caption>
              <thead>
                <tr>
                  <th scope="col">Username</th>
                  <th scope="col">Email</th>
                  <th scope="col">Role</th>
                  <th scope="col">Active</th>
                  <th scope="col">Must change password</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td className="font-medium">{u.username}</td>
                    <td className="font-mono text-xs">{u.email}</td>
                    <td>
                      <StatusPill status={u.role} />
                    </td>
                    <td>{u.is_active ? "Yes" : "No"}</td>
                    <td>{u.must_change_password ? "Yes" : "No"}</td>
                    <td>
                      <div className="flex flex-wrap items-center gap-2">
                        <Select
                          value={roleDrafts[u.id] ?? u.role}
                          onChange={(e) => setRoleDrafts((c) => ({ ...c, [u.id]: e.target.value }))}
                          className="h-8 text-xs min-w-[130px]"
                          aria-label={`Role for ${u.username}`}
                        >
                          {VALID_ROLES.map((r) => (
                            <option key={r} value={r}>
                              {r}
                            </option>
                          ))}
                        </Select>
                        <Button
                          variant="secondary"
                          size="sm"
                          loading={busy === `role-${u.id}`}
                          onClick={() => void patchRole(u.id)}
                          disabled={(roleDrafts[u.id] ?? u.role) === u.role}
                        >
                          Save role
                        </Button>
                        {formErrors[`role-${u.id}`] && (
                          <span className="text-xs text-error-text" role="alert">
                            {formErrors[`role-${u.id}`]}
                          </span>
                        )}
                      </div>
                      <div className="flex flex-wrap items-center gap-2 mt-2">
                        <Input
                          type="password"
                          placeholder="New password"
                          value={passwordDrafts[u.id] ?? ""}
                          onChange={(e) => setPasswordDrafts((c) => ({ ...c, [u.id]: e.target.value }))}
                          className="h-8 text-xs min-w-[160px]"
                          aria-label={`New password for ${u.username}`}
                          autoComplete="new-password"
                        />
                        <Button
                          variant="ghost"
                          size="sm"
                          loading={busy === `pwd-${u.id}`}
                          onClick={() => void resetPassword(u.id)}
                        >
                          Reset password
                        </Button>
                        {formErrors[`pwd-${u.id}`] && (
                          <span className="text-xs text-error-text" role="alert">
                            {formErrors[`pwd-${u.id}`]}
                          </span>
                        )}
                      </div>
                      {canImpersonate && u.id !== user?.id && (
                        <div className="mt-2">
                          <Button
                            variant="secondary"
                            size="sm"
                            loading={busy === `imp-${u.id}`}
                            onClick={() => void handleImpersonate(u)}
                            aria-label={`Impersonate ${u.username}`}
                            data-testid={`impersonate-${u.id}`}
                            disabled={isImpersonating}
                            title={isImpersonating ? "Exit current impersonation first" : `View as ${u.username}`}
                          >
                            Impersonate
                          </Button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          )}
      </SectionCard>

      {/* Create user — POST /auth/users */}
      <SectionCard
        compact
        title="Create user"
        description="POST /auth/users with { user_in: { username, email, password, role } }. The role is one of SuperAdmin, HR, Manager, Associate, PayrollViewer."
      >
        <form onSubmit={submitCreate} className="p-5 space-y-4">
          {formErrors.create && (
            <p className="text-sm text-error-text" role="alert">
              {formErrors.create}
            </p>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

            <div>
              <label htmlFor="ua-username" className="block text-xs font-medium text-text-secondary mb-1">
                Username
              </label>
              <Input
                id="ua-username"
                value={createForm.username}
                onChange={(e) => setCreateForm((f) => ({ ...f, username: e.target.value }))}
                placeholder="e.g. j.doe"
                required
                autoComplete="username"
              />
            </div>
            <div>
              <label htmlFor="ua-email" className="block text-xs font-medium text-text-secondary mb-1">
                Email
              </label>
              <Input
                id="ua-email"
                type="email"
                value={createForm.email}
                onChange={(e) => setCreateForm((f) => ({ ...f, email: e.target.value }))}
                placeholder="j.doe@example.com"
                required
                autoComplete="email"
              />
            </div>
            <div>
              <label htmlFor="ua-password" className="block text-xs font-medium text-text-secondary mb-1">
                Password
              </label>
              <Input
                id="ua-password"
                type="password"
                value={createForm.password}
                onChange={(e) => setCreateForm((f) => ({ ...f, password: e.target.value }))}
                required
                autoComplete="new-password"
              />
              <p className="text-xs text-text-secondary mt-1">At least 12 chars, mixed case and digits.</p>
            </div>
            <div>
              <label htmlFor="ua-role" className="block text-xs font-medium text-text-secondary mb-1">
                Role
              </label>
              <Select
                id="ua-role"
                value={createForm.role}
                onChange={(e) => setCreateForm((f) => ({ ...f, role: e.target.value }))}
              >
                {VALID_ROLES.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </Select>
            </div>
          </div>
          <Button type="submit" loading={busy === "create"}>
            Create user
          </Button>
        </form>
      </SectionCard>
      </div>
    </Layout>
  )
}