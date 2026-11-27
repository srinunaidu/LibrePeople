/* UX-07 — Saved views + keyboard nav + palette (depends UX-02)
 * E-UX-02: shortcut list now mirrors the shortcuts actually registered by
 * the shell (components/shell/WorkspaceRail.tsx GOTO_AREAS + lib/keyboard.ts),
 * and the default-view / keyboard-nav controls are editable and persist via
 * /clients/:id/feature-flags (require_roles("SuperAdmin")).
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, EmptyState, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton} from "@/components/ui"
import { useAuth } from "@/context/AuthContext"
import api, { getClientIdBySlug, errorMessage } from "@/lib/api"

/* Mirrors GOTO_AREAS in components/shell/WorkspaceRail.tsx and the single-key
 * shortcuts in lib/keyboard.ts. Keep in sync when the shell changes. */
const KEYBOARD_SHORTCUTS = [
  { key: "g h", label: "Go to Home" },
  { key: "g p", label: "Go to People" },
  { key: "g t", label: "Go to Time" },
  { key: "g s", label: "Go to Scheduling" },
  { key: "g g", label: "Go to Forecast" },
  { key: "g l", label: "Go to Leave" },
  { key: "g r", label: "Go to Recruiting" },
  { key: "g y", label: "Go to Payroll" },
  { key: "⌘K / Ctrl+K", label: "Command palette" },
  { key: "?", label: "Shortcut help" },
  { key: "t", label: "Toggle theme" },
  { key: "esc", label: "Close drawer / modals" },
]

const VIEW_OPTIONS = [
  { value: "dashboard", label: "Home / dashboard" },
  { value: "people", label: "People" },
  { value: "time", label: "Time" },
  { value: "leave", label: "Leave" },
]

export default function SavedViews() {
  const { user } = useAuth()
  const [clientId, setClientId] = useState<number | null>(null)

  const canWrite = user?.role === "SuperAdmin"
  const [view, setView] = useState("dashboard")
  const [keyboardEnabled, setKeyboardEnabled] = useState(true)
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
      const { data } = await api.get(`/onboarding-portal/clients/${id}/feature-flags`)
      const getCfg = (k: string) => (data as any[])?.find((x: any) => x.key === k)?.config
      setView((getCfg("saved_view") ?? "dashboard"))
      setKeyboardEnabled(getCfg("keyboard_nav") === "1")
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canWrite])
  useEffect(() => { load() }, [load])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/saved_view`, { config: view })
      await api.put(`/onboarding-portal/clients/${clientId}/feature-flags/keyboard_nav`, { config: keyboardEnabled ? "1" : "0" })
      await load()
      setNotice("View preferences saved.")
    } catch (e) { setActionError(errorMessage(e, "The view preferences could not be saved.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`Saved views require SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Saved Views"><TableSkeleton rows={4} cols={4} /></LoadingRegion></Layout>

  return (
    <Layout>
      <PageHeader compact title="Saved Views + Keyboard Nav + Palette" description="UX-07 · default view + keyboard-nav preference · persists via /clients/:id/feature-flags (SuperAdmin)." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The saved view preferences could not be read." fallback="The saved view preferences could not be read." onRetry={load} />}
        <SectionCard compact title="Saved view + keyboard" description="Per-tenant preferences from /clients/:id/feature-flags.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label htmlFor="sv-view">Default view</label>
              <select id="sv-view" value={view} onChange={e => setView(e.target.value)} className="w-full rounded border px-3 py-2" disabled={!canWrite || saving || !clientId}>
                {VIEW_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="sv-keyboard">Keyboard navigation</label>
              <div className="flex items-center gap-2">
                <input id="sv-keyboard" type="checkbox" checked={keyboardEnabled} onChange={e => setKeyboardEnabled(e.target.checked)} disabled={!canWrite || saving || !clientId} className="rounded text-brand-600 focus:ring-brand-500" />
                <span className="text-sm text-fg">{keyboardEnabled ? "Enabled" : "Disabled"}</span>
              </div>
            </div>
            <div />
          </div>
          <Button onClick={save} disabled={!canWrite || saving || !clientId} className="mt-4">{saving ? "Saving…" : "Save views"}</Button>
        </SectionCard>

        <SectionCard compact title="Keyboard shortcuts" description="Shortcuts registered by the workspace shell (WorkspaceRail + lib/keyboard).">
          {KEYBOARD_SHORTCUTS.map(s => (
            <div key={s.key} className="p-2 rounded border">
              <span><span className="font-mono">{s.key}</span>: {s.label}</span>
            </div>
          ))}
        </SectionCard>

        <div className="text-xs text-fg-muted">UX-07 · R3 · depends UX-02 · shortcut list mirrors the shell registrations.</div>
      </div>
    </Layout>
  )
}