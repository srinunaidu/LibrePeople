/* AD-03 — Locale/TZ/currency/date/working week (depends AD-01)
 * Settings endpoint /clients/:slug/settings (verified); no fabricated locales.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, EmptyState, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

export default function LocaleConfig() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [locale, setLocale] = useState("en-IN")
  const [tz, setTz] = useState("Asia/Kolkata")
  const [currency, setCurrency] = useState("INR")
  const [weekStart, setWeekStart] = useState("Monday")
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState("")
  const [actionError, setActionError] = useState("")
  const [error, setError] = useState<unknown | null>(null)

  const load = useCallback(async () => {
    if (!canWrite) { setLoading(false); return }
    setLoading(true); setError(null); setNotice("")
    const id = await getClientIdBySlug()
    setClientId(id)
    if (id === null) {
      setError("Could not resolve the company. Check the server connection and retry.");
      setLoading(false);
      return;
    }
    try {
      const { data } = await api.get(`/onboarding-portal/clients/${id}/settings`)
      const m: Record<string, string> = {}
      for (const s of data || []) (m as any)[s.key] = s.value
      setLocale(m["locale"] || "en-IN")
      setTz(m["timezone"] || "Asia/Kolkata")
      setCurrency(m["currency"] || "INR")
      setWeekStart(m["week_start"] || "Monday")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (!clientId) {
      setError("Could not resolve the company. Check the server connection and retry.")
      return
    }
    if (clientId === null) return

    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/settings/locale`, { value: locale })
      await api.put(`/onboarding-portal/clients/${clientId}/settings/timezone`, { value: tz })
      await api.put(`/onboarding-portal/clients/${clientId}/settings/currency`, { value: currency })
      await api.put(`/onboarding-portal/clients/${clientId}/settings/week_start`, { value: weekStart })
      setNotice("Locale / working-week saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Locale">Loading locale config…</LoadingRegion></Layout>
  if (error && !clientId) {
    return (
      <Layout>
        <SectionCard compact title="Company not resolved" description="Could not resolve the company. Check the server connection and retry.">
          <EmptyState title="Could not resolve the company" description="Could not resolve the company. Check the server connection and retry." />
          <div className="mt-4">
            <Button onClick={() => load()}>Retry</Button>
          </div>
        </SectionCard>
      </Layout>
    )
  }
  return (
    <Layout>
      <PageHeader compact title="Locale & Working Week" description="AD-03 · locale / TZ / currency / working-start; depends AD-01 (company branding verified)" />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The locale & working week could not be read." fallback="The locale & working week could not be read." onRetry={load} />}
        <SectionCard compact title="Settings" description="Per-tenant from /clients/:slug/settings; no fabricated locale packs.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div><label htmlFor="lc-locale">Locale</label><Input id="lc-locale" value={locale} onChange={e => setLocale(e.target.value)} disabled={!canWrite || saving || !clientId} /></div>
            <div><label htmlFor="lc-tz">Time zone</label><Input id="lc-tz" value={tz} onChange={e => setTz(e.target.value)} disabled={!canWrite || saving || !clientId} /></div>
            <div><label htmlFor="lc-currency">Currency</label><Input id="lc-currency" value={currency} onChange={e => setCurrency(e.target.value)} disabled={!canWrite || saving || !clientId} /></div>
            <div><label htmlFor="lc-week">Week starts</label><Input id="lc-week" value={weekStart} onChange={e => setWeekStart(e.target.value)} disabled={!canWrite || saving || !clientId} /></div>
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save locale"}</Button>
        </SectionCard>
        <div className="text-xs text-fg-muted">AD-03 · R2 · depends AD-01 · feeds PY-08 / PY-09 / SC-01.</div>
      </div>
    </Layout>
  )
}
