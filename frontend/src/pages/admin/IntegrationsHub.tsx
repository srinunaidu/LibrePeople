/**
 * Integrations — webhooks, SSO, background checks and e-signatures.
 *
 * Gates mirror backend/app/api/v1/endpoints/integrations_platform.py:
 *  - SSO configs & webhooks (incl. deliveries & deliver): require_roles("SuperAdmin")
 *  - Background checks & e-signatures: require_roles(*ADMIN_ROLES) (SuperAdmin, HR)
 * The page therefore shows the whole surface to SuperAdmin; HR sees background
 * checks and e-signatures but gets an explicit empty state for the SuperAdmin-only
 * sections rather than a blank page. Any other role gets a page-level gate.
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
import api, { errorMessage } from "@/lib/api"
import type {
  BackgroundCheckRow,
  ESignatureRow,
  SSOConfigRow,
  WebhookDeliveryRow,
  WebhookRow,
} from "@/types"

function truncateUrl(url: string, max = 36): string {
  if (url.length <= max) return url
  return `${url.slice(0, max)}…`
}

function fmtDate(value?: string | null) {
  if (!value) return "—"
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value.slice(0, 19).replace("T", " ")
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(d)
}

export default function IntegrationsHub() {
  const { user } = useAuth()
  const isSuperAdmin = user?.role === "SuperAdmin"
  const isAdmin = ["SuperAdmin", "HR"].includes(user?.role ?? "")

  const [ssoRows, setSsoRows] = useState<SSOConfigRow[]>([])
  const [webhooks, setWebhooks] = useState<WebhookRow[]>([])
  const [checks, setChecks] = useState<BackgroundCheckRow[]>([])
  const [sigs, setSigs] = useState<ESignatureRow[]>([])
  const [deliveriesByWebhook, setDeliveriesByWebhook] = useState<Record<number, WebhookDeliveryRow[]>>({})
  const [deliveriesLoading, setDeliveriesLoading] = useState<Record<number, boolean>>({})

  const [loading, setLoading] = useState(true)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [notice, setNotice] = useState("")
  const [formErrors, setFormErrors] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState<"" | "sso" | "webhook" | "check" | "sig" | string>("")

  const [ssoForm, setSsoForm] = useState({ provider: "", entity_id: "", sso_url: "", is_active: false })
  const [webhookForm, setWebhookForm] = useState({ url: "", events: "", is_active: true })
  const [checkForm, setCheckForm] = useState({ candidate_id: "", provider: "manual" })
  const [sigForm, setSigForm] = useState({ document_type: "", signer_email: "", signer_name: "", provider: "internal" })

  // Mirrors deps.py: ADMIN_ROLES vs SuperAdmin gate; each read is independent so
  // a 403 on webhooks must not blank the checks.
  const load = useCallback(async () => {
    setLoading(true)
    setErrors({})
    const ssoPromise = isSuperAdmin ? api.get<SSOConfigRow[]>("/platform/sso-configs") : Promise.resolve(null)
    const webhookPromise = isSuperAdmin ? api.get<WebhookRow[]>("/platform/webhooks") : Promise.resolve(null)
    const checkPromise = isAdmin ? api.get<BackgroundCheckRow[]>("/platform/background-checks") : Promise.resolve(null)
    const sigPromise = isAdmin ? api.get<ESignatureRow[]>("/platform/e-signatures") : Promise.resolve(null)

    const [ssoResult, webhookResult, checkResult, sigResult] = await Promise.allSettled([
      ssoPromise,
      webhookPromise,
      checkPromise,
      sigPromise,
    ])

    const next: Record<string, string> = {}
    if (ssoResult.status === "fulfilled") {
      setSsoRows((ssoResult.value?.data as unknown as SSOConfigRow[]) ?? [])
    } else if (isSuperAdmin) {
      setSsoRows([])
      next.sso = errorMessage(ssoResult.reason, "The SSO configs could not be read.")
    }
    if (webhookResult.status === "fulfilled") {
      setWebhooks((webhookResult.value?.data as unknown as WebhookRow[]) ?? [])
    } else if (isSuperAdmin) {
      setWebhooks([])
      next.webhooks = errorMessage(webhookResult.reason, "The webhooks could not be read.")
    }
    if (checkResult.status === "fulfilled") {
      setChecks((checkResult.value?.data as unknown as BackgroundCheckRow[]) ?? [])
    } else if (isAdmin) {
      setChecks([])
      next.checks = errorMessage(checkResult.reason, "The background checks could not be read.")
    }
    if (sigResult.status === "fulfilled") {
      setSigs((sigResult.value?.data as unknown as ESignatureRow[]) ?? [])
    } else if (isAdmin) {
      setSigs([])
      next.sigs = errorMessage(sigResult.reason, "The e-signatures could not be read.")
    }
    setErrors(next)
    setLoading(false)
  }, [isSuperAdmin, isAdmin])

  useEffect(() => {
    void load()
  }, [load])

  async function submitSso(event: FormEvent) {
    event.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, sso: "" }))
    setNotice("")
    if (!ssoForm.provider.trim()) {
      setFormErrors((c) => ({ ...c, sso: "Provider is required." }))
      return
    }
    setBusy("sso")
    try {
      await api.post("/platform/sso-configs", {
        provider: ssoForm.provider.trim(),
        entity_id: ssoForm.entity_id.trim() || null,
        sso_url: ssoForm.sso_url.trim() || null,
        is_active: ssoForm.is_active,
      })
      setSsoForm({ provider: "", entity_id: "", sso_url: "", is_active: false })
      setNotice("SSO config created.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, sso: errorMessage(err, "The SSO config could not be created.") }))
    } finally {
      setBusy("")
    }
  }

  async function submitWebhook(event: FormEvent) {
    event.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, webhook: "" }))
    setNotice("")
    if (!webhookForm.url.trim() || !webhookForm.events.trim()) {
      setFormErrors((c) => ({ ...c, webhook: "URL and events are required." }))
      return
    }
    setBusy("webhook")
    try {
      await api.post("/platform/webhooks", {
        url: webhookForm.url.trim(),
        events: webhookForm.events.trim(),
        is_active: webhookForm.is_active,
      })
      setWebhookForm({ url: "", events: "", is_active: true })
      setNotice("Webhook created.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, webhook: errorMessage(err, "The webhook could not be created.") }))
    } finally {
      setBusy("")
    }
  }

  async function deliverWebhook(id: number) {
    if (busy) return
    setBusy(`deliver-${id}`)
    setFormErrors((c) => ({ ...c, webhook: "" }))
    try {
      await api.post(`/platform/webhooks/${id}/deliver`, null, { params: { event: "test" } })
      setNotice(`Delivery triggered for webhook #${id}.`)
      // Refresh deliveries for this webhook if already open
      if (deliveriesByWebhook[id]) {
        void fetchDeliveries(id)
      }
    } catch (err) {
      setFormErrors((c) => ({ ...c, webhook: errorMessage(err, "The delivery could not be triggered.") }))
    } finally {
      setBusy("")
    }
  }

  async function fetchDeliveries(webhookId: number) {
    setDeliveriesLoading((c) => ({ ...c, [webhookId]: true }))
    try {
      const res = await api.get<WebhookDeliveryRow[]>(`/platform/webhooks/${webhookId}/deliveries`)
      setDeliveriesByWebhook((c) => ({ ...c, [webhookId]: res.data ?? [] }))
    } catch (err) {
      setDeliveriesByWebhook((c) => ({ ...c, [webhookId]: [] }))
      setFormErrors((c) => ({ ...c, webhook: errorMessage(err, "The deliveries could not be read.") }))
    } finally {
      setDeliveriesLoading((c) => ({ ...c, [webhookId]: false }))
    }
  }

  async function submitCheck(event: FormEvent) {
    event.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, check: "" }))
    setNotice("")
    if (!checkForm.candidate_id) {
      setFormErrors((c) => ({ ...c, check: "Candidate ID is required." }))
      return
    }
    setBusy("check")
    try {
      await api.post("/platform/background-checks", {
        candidate_id: Number(checkForm.candidate_id),
        provider: checkForm.provider.trim() || "manual",
      })
      setCheckForm({ candidate_id: "", provider: "manual" })
      setNotice("Background check created.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, check: errorMessage(err, "The background check could not be created.") }))
    } finally {
      setBusy("")
    }
  }

  async function completeCheck(id: number) {
    if (busy) return
    setBusy(`complete-${id}`)
    try {
      await api.put(`/platform/background-checks/${id}/complete`, null, {
        params: { result: "Clear", status: "Clear" },
      })
      setNotice(`Background check #${id} marked Clear.`)
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, check: errorMessage(err, "The background check could not be completed.") }))
    } finally {
      setBusy("")
    }
  }

  async function submitSig(event: FormEvent) {
    event.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, sig: "" }))
    setNotice("")
    if (!sigForm.document_type.trim() || !sigForm.signer_email.trim()) {
      setFormErrors((c) => ({ ...c, sig: "Document type and signer email are required." }))
      return
    }
    setBusy("sig")
    try {
      await api.post("/platform/e-signatures", {
        document_type: sigForm.document_type.trim(),
        signer_email: sigForm.signer_email.trim(),
        signer_name: sigForm.signer_name.trim() || null,
        provider: sigForm.provider.trim() || "internal",
      })
      setSigForm({ document_type: "", signer_email: "", signer_name: "", provider: "internal" })
      setNotice("E-signature request created.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, sig: errorMessage(err, "The e-signature could not be created.") }))
    } finally {
      setBusy("")
    }
  }

  async function signDoc(id: number) {
    if (busy) return
    setBusy(`sign-${id}`)
    try {
      await api.put(`/platform/e-signatures/${id}/sign`)
      setNotice(`Document #${id} signed.`)
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, sig: errorMessage(err, "The document could not be signed.") }))
    } finally {
      setBusy("")
    }
  }

  const copyUrl = async (url: string) => {
    try {
      await navigator.clipboard.writeText(url)
      setNotice("URL copied.")
    } catch {
      setFormErrors((c) => ({ ...c, webhook: `Clipboard unavailable — copy manually: ${url}` }))
    }
  }

  // Whole-page gate: integrations_platform.py uses require_roles("SuperAdmin")
  // for SSO/webhooks. The page-level sentence matches the spec.
  if (!isSuperAdmin && !isAdmin) {
    return (
      <Layout>
        <PageHeader compact
          title="Integrations"
          description="Webhooks, SSO, background checks and e-signatures — SuperAdmin only"
        />
        <EmptyState
          title="Integrations are managed by SuperAdmin"
          description={`Your role (${user?.role || "unknown"}) does not permit this page. SSO and webhooks require SuperAdmin; background checks and e-signatures require SuperAdmin or HR.`}
        />
      </Layout>
    )
  }

  return (
    <Layout>
      <PageHeader compact
        title="Integrations"
        description="Webhooks, SSO, background checks and e-signatures — SuperAdmin only"
      />

      {notice && <Alert tone="success">{notice}</Alert>}

      {/* SSO configs — SuperAdmin only */}
      <SectionCard compact
        title="SSO configs"
        description="Provider and domain (entity ID). SuperAdmin only — mirrors require_roles('SuperAdmin') on GET/POST /platform/sso-configs."
      >
        {!isSuperAdmin ? (
          <div className="p-5">
            <EmptyState
              title="Integrations are managed by SuperAdmin"
              description={`SSO configs require SuperAdmin; your role is ${user?.role || "unknown"}.`}
            />
          </div>
        ) : loading ? (
          <LoadingRegion label="Loading SSO configs…">
            <TableSkeleton rows={3} cols={4} />
          </LoadingRegion>
        ) : errors.sso ? (
          <div className="p-5">
            <RetryableAlert err={errors.sso} title="The SSO configs could not be read" fallback="The SSO configs could not be read" onRetry={load} />
          </div>
        ) : (
          <>
            <form onSubmit={submitSso} className="p-5 border-b border-border">
              {formErrors.sso && <Alert tone="error" className="mb-3">{formErrors.sso}</Alert>}
              <div className="flex flex-wrap gap-3 items-end">
                <div className="min-w-[160px] flex-1">
                  <label htmlFor="sso-provider" className="block text-xs font-medium text-text-secondary mb-1">
                    Provider
                  </label>
                  <Input
                    id="sso-provider"
                    value={ssoForm.provider}
                    onChange={(e) => setSsoForm((f) => ({ ...f, provider: e.target.value }))}
                    placeholder="SAML / OIDC / OAuth2"
                    required
                  />
                </div>
                <div className="min-w-[180px] flex-1">
                  <label htmlFor="sso-entity" className="block text-xs font-medium text-text-secondary mb-1">
                    Domain / entity ID
                  </label>
                  <Input
                    id="sso-entity"
                    value={ssoForm.entity_id}
                    onChange={(e) => setSsoForm((f) => ({ ...f, entity_id: e.target.value }))}
                    placeholder="e.g. example.com or entity id"
                  />
                </div>
                <div className="min-w-[200px] flex-1">
                  <label htmlFor="sso-url" className="block text-xs font-medium text-text-secondary mb-1">
                    SSO URL
                  </label>
                  <Input
                    id="sso-url"
                    value={ssoForm.sso_url}
                    onChange={(e) => setSsoForm((f) => ({ ...f, sso_url: e.target.value }))}
                    placeholder="https://…"
                  />
                </div>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={ssoForm.is_active}
                    onChange={(e) => setSsoForm((f) => ({ ...f, is_active: e.target.checked }))}
                    className="h-4 w-4"
                  />
                  Active
                </label>
                <Button type="submit" loading={busy === "sso"}>
                  Create SSO config
                </Button>
              </div>
            </form>

            {ssoRows.length === 0 ? (
              <div className="p-5 text-sm text-text-secondary">No SSO configs exist.</div>
            ) : (
              <div className="table-scroll">
                <table className="table-base table-compact w-full text-sm">
                  <caption className="sr-only">SSO configurations</caption>
                  <thead>
                    <tr>
                      <th scope="col">Provider</th>
                      <th scope="col">Domain / entity ID</th>
                      <th scope="col">Active</th>
                      <th scope="col">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ssoRows.map((row) => (
                      <tr key={row.id}>
                        <td>{row.provider}</td>
                        <td>{row.entity_id || row.domain || "—"}</td>
                        <td>{row.is_active ? "Yes" : "No"}</td>
                        <td>{fmtDate(row.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </SectionCard>

      {/* Webhooks — SuperAdmin only */}
      <SectionCard compact
        title="Webhooks"
        description="Outbound subscriptions. POST /{id}/deliver sends a test event; GET /{id}/deliveries lists attempts."
      >
        {!isSuperAdmin ? (
          <div className="p-5">
            <EmptyState
              title="Integrations are managed by SuperAdmin"
              description={`Webhooks require SuperAdmin; your role is ${user?.role || "unknown"}.`}
            />
          </div>
        ) : loading ? (
          <LoadingRegion label="Loading webhooks…">
            <TableSkeleton rows={3} cols={4} />
          </LoadingRegion>
        ) : errors.webhooks ? (
          <div className="p-5">
            <RetryableAlert err={errors.webhooks} title="The webhooks could not be read" fallback="The webhooks could not be read" onRetry={load} />
          </div>
        ) : (
          <>
            <form onSubmit={submitWebhook} className="p-5 border-b border-border">
              {formErrors.webhook && <Alert tone="error" className="mb-3">{formErrors.webhook}</Alert>}
              <div className="flex flex-wrap gap-3 items-end">
                <div className="flex-1 min-w-[220px]">
                  <label htmlFor="wh-url" className="block text-xs font-medium text-text-secondary mb-1">
                    URL
                  </label>
                  <Input
                    id="wh-url"
                    value={webhookForm.url}
                    onChange={(e) => setWebhookForm((f) => ({ ...f, url: e.target.value }))}
                    placeholder="https://…"
                    required
                  />
                </div>
                <div className="flex-1 min-w-[180px]">
                  <label htmlFor="wh-events" className="block text-xs font-medium text-text-secondary mb-1">
                    Events (comma-separated)
                  </label>
                  <Input
                    id="wh-events"
                    value={webhookForm.events}
                    onChange={(e) => setWebhookForm((f) => ({ ...f, events: e.target.value }))}
                    placeholder="employee.created, leave.approved"
                    required
                  />
                </div>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={webhookForm.is_active}
                    onChange={(e) => setWebhookForm((f) => ({ ...f, is_active: e.target.checked }))}
                    className="h-4 w-4"
                  />
                  Active
                </label>
                <Button type="submit" loading={busy === "webhook"}>
                  Create webhook
                </Button>
              </div>
            </form>

            {webhooks.length === 0 ? (
              <div className="p-5 text-sm text-text-secondary">No webhooks exist.</div>
            ) : (
              <div className="table-scroll">
                <table className="table-base table-compact w-full text-sm">
                  <caption className="sr-only">Webhooks</caption>
                  <thead>
                    <tr>
                      <th scope="col">URL</th>
                      <th scope="col">Events</th>
                      <th scope="col">Active</th>
                      <th scope="col">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {webhooks.map((wh) => (
                      <tr key={wh.id}>
                        <td>
                          <span title={wh.url} className="font-mono text-xs">
                            {truncateUrl(wh.url)}
                          </span>{" "}
                          <button
                            type="button"
                            onClick={() => void copyUrl(wh.url)}
                            className="text-xs text-brand-700 hover:underline ml-1"
                          >
                            Copy
                          </button>
                        </td>
                        <td className="max-w-[240px] truncate" title={wh.events}>
                          {wh.events}
                        </td>
                        <td>
                          <span className={wh.is_active ? "text-success-text" : "text-text-secondary"}>
                            {wh.is_active ? "Yes" : "No"}
                          </span>
                        </td>
                        <td>
                          <div className="flex gap-2">
                            <Button
                              variant="secondary"
                              size="sm"
                              loading={busy === `deliver-${wh.id}`}
                              onClick={() => void deliverWebhook(wh.id)}
                            >
                              Deliver
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => void fetchDeliveries(wh.id)}
                            >
                              Deliveries
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Deliveries sub-tables */}
            {webhooks.map((wh) =>
              deliveriesByWebhook[wh.id] !== undefined ? (
                <div key={`del-${wh.id}`} className="border-t border-border p-4 bg-surface-sunken">
                  <h3 className="text-sm font-semibold mb-2">
                    Deliveries for webhook #{wh.id}
                  </h3>
                  {deliveriesLoading[wh.id] ? (
                    <TableSkeleton rows={2} cols={3} />
                  ) : deliveriesByWebhook[wh.id].length === 0 ? (
                    <p className="text-sm text-text-secondary">No deliveries yet.</p>
                  ) : (
                    <div className="table-scroll">
                      <table className="table-base table-compact w-full text-sm">
                        <thead>
                          <tr>
                            <th scope="col">Event</th>
                            <th scope="col">Status</th>
                            <th scope="col">Code</th>
                            <th scope="col">Attempted at</th>
                          </tr>
                        </thead>
                        <tbody>
                          {deliveriesByWebhook[wh.id].map((d) => (
                            <tr key={d.id}>
                              <td>{d.event}</td>
                              <td>
                                <StatusPill status={d.status} />
                              </td>
                              <td>{d.response_code ?? "—"}</td>
                              <td>{fmtDate(d.created_at ?? d.attempted_at)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              ) : null
            )}
          </>
        )}
      </SectionCard>

      {/* Background checks — ADMIN_ROLES */}
      <SectionCard compact
        title="Background checks"
        description="Candidate checks. PUT /{id}/complete marks Clear. Visible to SuperAdmin and HR."
      >
        {!isAdmin ? (
          <div className="p-5">
            <EmptyState
              title="Not visible for your role"
              description={`Background checks require SuperAdmin or HR; your role is ${user?.role || "unknown"}.`}
            />
          </div>
        ) : loading ? (
          <LoadingRegion label="Loading background checks…">
            <TableSkeleton rows={3} cols={4} />
          </LoadingRegion>
        ) : errors.checks ? (
          <div className="p-5">
            <RetryableAlert err={errors.checks} title="The background checks could not be read" fallback="The background checks could not be read" onRetry={load} />
          </div>
        ) : (
          <>
            <form onSubmit={submitCheck} className="p-5 border-b border-border">
              {formErrors.check && <Alert tone="error" className="mb-3">{formErrors.check}</Alert>}
              <div className="flex flex-wrap gap-3 items-end">
                <div className="min-w-[140px]">
                  <label htmlFor="bc-candidate" className="block text-xs font-medium text-text-secondary mb-1">
                    Candidate ID
                  </label>
                  <Input
                    id="bc-candidate"
                    type="number"
                    min={1}
                    value={checkForm.candidate_id}
                    onChange={(e) => setCheckForm((f) => ({ ...f, candidate_id: e.target.value }))}
                    required
                  />
                </div>
                <div className="min-w-[160px]">
                  <label htmlFor="bc-provider" className="block text-xs font-medium text-text-secondary mb-1">
                    Provider
                  </label>
                  <Select
                    id="bc-provider"
                    value={checkForm.provider}
                    onChange={(e) => setCheckForm((f) => ({ ...f, provider: e.target.value }))}
                  >
                    <option value="manual">manual</option>
                    <option value="checkr">checkr</option>
                    <option value="hireright">hireright</option>
                  </Select>
                </div>
                <Button type="submit" loading={busy === "check"}>
                  Create check
                </Button>
              </div>
            </form>

            {checks.length === 0 ? (
              <div className="p-5 text-sm text-text-secondary">No background checks.</div>
            ) : (
              <div className="table-scroll">
                <table className="table-base table-compact w-full text-sm">
                  <caption className="sr-only">Background checks</caption>
                  <thead>
                    <tr>
                      <th scope="col">Candidate</th>
                      <th scope="col">Provider</th>
                      <th scope="col">Status</th>
                      <th scope="col">Result</th>
                      <th scope="col">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {checks.map((row) => (
                      <tr key={row.id}>
                        <td>Candidate #{row.candidate_id}</td>
                        <td>{row.provider}</td>
                        <td>
                          <StatusPill status={row.status} />
                        </td>
                        <td>{row.result ?? "—"}</td>
                        <td>
                          {row.status !== "Clear" && row.status !== "Signed" ? (
                            <Button
                              variant="secondary"
                              size="sm"
                              loading={busy === `complete-${row.id}`}
                              onClick={() => void completeCheck(row.id)}
                            >
                              Complete
                            </Button>
                          ) : (
                            <span className="text-xs text-text-secondary">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </SectionCard>

      {/* E-signatures — ADMIN_ROLES */}
      <SectionCard compact
        title="E-signatures"
        description="Signature requests. PUT /{id}/sign marks Signed. Visible to SuperAdmin and HR."
      >
        {!isAdmin ? (
          <div className="p-5">
            <EmptyState
              title="Not visible for your role"
              description={`E-signatures require SuperAdmin or HR; your role is ${user?.role || "unknown"}.`}
            />
          </div>
        ) : loading ? (
          <LoadingRegion label="Loading e-signatures…">
            <TableSkeleton rows={3} cols={4} />
          </LoadingRegion>
        ) : errors.sigs ? (
          <div className="p-5">
            <RetryableAlert err={errors.sigs} title="The e-signatures could not be read" fallback="The e-signatures could not be read" onRetry={load} />
          </div>
        ) : (
          <>
            <form onSubmit={submitSig} className="p-5 border-b border-border">
              {formErrors.sig && <Alert tone="error" className="mb-3">{formErrors.sig}</Alert>}
              <div className="flex flex-wrap gap-3 items-end">
                <div className="min-w-[160px]">
                  <label htmlFor="sig-doc" className="block text-xs font-medium text-text-secondary mb-1">
                    Document type
                  </label>
                  <Input
                    id="sig-doc"
                    value={sigForm.document_type}
                    onChange={(e) => setSigForm((f) => ({ ...f, document_type: e.target.value }))}
                    placeholder="Offer / Contract / Policy / NDA"
                    required
                  />
                </div>
                <div className="min-w-[200px] flex-1">
                  <label htmlFor="sig-email" className="block text-xs font-medium text-text-secondary mb-1">
                    Signer email
                  </label>
                  <Input
                    id="sig-email"
                    type="email"
                    value={sigForm.signer_email}
                    onChange={(e) => setSigForm((f) => ({ ...f, signer_email: e.target.value }))}
                    required
                  />
                </div>
                <div className="min-w-[160px]">
                  <label htmlFor="sig-name" className="block text-xs font-medium text-text-secondary mb-1">
                    Signer name
                  </label>
                  <Input
                    id="sig-name"
                    value={sigForm.signer_name}
                    onChange={(e) => setSigForm((f) => ({ ...f, signer_name: e.target.value }))}
                    placeholder="Optional"
                  />
                </div>
                <div className="min-w-[140px]">
                  <label htmlFor="sig-provider" className="block text-xs font-medium text-text-secondary mb-1">
                    Provider
                  </label>
                  <Select
                    id="sig-provider"
                    value={sigForm.provider}
                    onChange={(e) => setSigForm((f) => ({ ...f, provider: e.target.value }))}
                  >
                    <option value="internal">internal</option>
                    <option value="docusign">docusign</option>
                    <option value="adobe">adobe</option>
                  </Select>
                </div>
                <Button type="submit" loading={busy === "sig"}>
                  Create request
                </Button>
              </div>
            </form>

            {sigs.length === 0 ? (
              <div className="p-5 text-sm text-text-secondary">No e-signature requests.</div>
            ) : (
              <div className="table-scroll">
                <table className="table-base table-compact w-full text-sm">
                  <caption className="sr-only">E-signature requests</caption>
                  <thead>
                    <tr>
                      <th scope="col">Document type</th>
                      <th scope="col">Signer</th>
                      <th scope="col">Status</th>
                      <th scope="col">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sigs.map((row) => (
                      <tr key={row.id}>
                        <td>{row.document_type}</td>
                        <td>
                          {row.signer_name ? `${row.signer_name} · ` : ""}
                          <span className="font-mono text-xs">{row.signer_email}</span>
                        </td>
                        <td>
                          <StatusPill status={row.status} />
                        </td>
                        <td>
                          {row.status !== "Signed" ? (
                            <Button
                              variant="secondary"
                              size="sm"
                              loading={busy === `sign-${row.id}`}
                              onClick={() => void signDoc(row.id)}
                            >
                              Sign
                            </Button>
                          ) : (
                            <span className="text-xs text-text-secondary">—</span>
                          )}
                        </td>
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