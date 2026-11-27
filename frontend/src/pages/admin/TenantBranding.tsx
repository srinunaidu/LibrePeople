/* Company branding — AD-01 (company setup, branding, theme, WCAG-aware)
 *
 * SuperAdmin writes the company's branding into the company settings
 * (client_settings endpoint: /onboarding-portal/clients/{id}/settings, PUT /settings/{key}).
 * Keys used here: logo_url, brand_primary_hex, brand_font.
 *
 * WCAG awareness: primary colour is verified against white and near-black
 * targets; a contrast-ratio report is shown before save (not enforced —
 * the operator decides, the screen makes it visible).
 */
import { useCallback, useEffect, useMemo, useState } from "react"
import { Layout } from "@/components/Layout"
import { Input,Alert, Button, EmptyState, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton} from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import api, { getClientIdBySlug, readableLoadError, errorMessage } from "@/lib/api"
import { shell } from "@/lib/tokens"

function relativeLuminance(color: string): number {
  if (color === "white") return 1
  if (color === "black") return 0
  let hex = color
  if (hex.startsWith("var(")) {
    hex = shell.accent
  }
  const c = hex.replace(/^#/, "")
  if (c.length !== 6) return 0
  const r = parseInt(c.substring(0, 2), 16) / 255
  const g = parseInt(c.substring(2, 4), 16) / 255
  const b = parseInt(c.substring(4, 6), 16) / 255
  const f = (v: number) => (v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4))
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
}

function contrastRatio(a: string, b: string): number {
  const l1 = relativeLuminance(a)
  const l2 = relativeLuminance(b)
  const lighter = Math.max(l1, l2)
  const darker = Math.min(l1, l2)
  return (lighter + 0.05) / (darker + 0.05)
}

export default function TenantBranding() {
  const { user } = useAuth()
  const canWrite = user?.role === "SuperAdmin"

  const [clientId, setClientId] = useState<number | null>(null)
  const [logo, setLogo] = useState("")
  const [primary, setPrimary] = useState<string>(shell.accent)
  const [font, setFont] = useState("Space Grotesk")
  const [settings, setSettings] = useState<Record<string, string>>({})
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
      const map: Record<string, string> = {}
      for (const s of data || []) (map as any)[s.key] = s.value
      setSettings(map)
      setLogo(map["logo_url"] || "")
      setPrimary(map["brand_primary_hex"] || shell.accent)
      setFont(map["brand_font"] || "Space Grotesk")
    } catch (e) {
      setError(e)
    } finally {
      setLoading(false)
    }
  }, [canWrite])

  useEffect(() => { load() }, [load])

  const wcag = useMemo(() => {
    const onWhite = contrastRatio(primary, "white")
    const onBlack = contrastRatio(primary, "black")
    return {
      white: onWhite.toFixed(2),
      black: onBlack.toFixed(2),
      passesAA: onWhite >= 4.5 || onBlack >= 4.5,
    }
  }, [primary])

  const save = async () => {
    if (clientId === null) return
    setSaving(true); setNotice(""); setActionError("")
    try {
      await api.put(`/onboarding-portal/clients/${clientId}/settings/logo_url`, { value: logo })
      await api.put(`/onboarding-portal/clients/${clientId}/settings/brand_primary_hex`, { value: primary })
      await api.put(`/onboarding-portal/clients/${clientId}/settings/brand_font`, { value: font })
      await load()
      setNotice("Branding settings saved.")
    } catch (e) { setActionError(errorMessage(e, "The action could not be completed.")) } finally { setSaving(false) }
  }

  if (!canWrite) return <Layout><EmptyState title="Not visible for your role" description={`This screen requires SuperAdmin; your role is ${user?.role || "unknown"}.`} /></Layout>

  if (loading) return <Layout><LoadingRegion label="Company branding">Loading company branding…</LoadingRegion></Layout>

  const previewBg = { background: primary } as React.CSSProperties
  const previewContainerStyle = { background: `${primary}18`, borderColor: `${primary}30` } as React.CSSProperties
  const previewTitleStyle = { color: primary, fontFamily: font } as React.CSSProperties

  return (
    <Layout>
      <PageHeader compact title="Company branding" description="AD-01 · company logo, colour, font (WCAG-aware)" />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-6">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        {!!error && <RetryableAlert err={error} title="The company branding could not be read." fallback={readableLoadError(error, "The company branding could not be read.")} onRetry={load} />}

        <SectionCard compact title="Brand settings" description="Stored as company settings for this install; writable by SuperAdmin.">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="logo" className="block text-sm font-medium mb-1.5">Logo URL</label>
              <Input id="logo" value={logo} onChange={e => setLogo(e.target.value)} placeholder="https://.../logo.svg" disabled={!canWrite || saving || !clientId} />
            </div>
            <div>
              <label htmlFor="primary" className="block text-sm font-medium mb-1.5">Primary colour</label>
              <div className="flex gap-3">
                <Input id="primary" value={primary} onChange={e => setPrimary(e.target.value)} disabled={!canWrite || saving || !clientId} className="font-mono tabular-nums" />
                <span className="w-10 h-10 rounded-[var(--radius-md)] border border-[var(--border)] shadow-inner shrink-0" style={previewBg} aria-label="preview" />
              </div>
            </div>
            <div className="sm:col-span-2">
              <label htmlFor="font" className="block text-sm font-medium mb-1.5">Font family</label>
              <Input id="font" value={font} onChange={e => setFont(e.target.value)} disabled={!canWrite || saving || !clientId} />
            </div>
          </div>

          <div className="mt-4 bg-[var(--surface-elevated)] rounded-[var(--radius-md)] p-3 border border-[var(--border)]">
            <h3 className="text-sm font-semibold mb-2 text-[var(--fg)]">WCAG contrast (primary vs white / black)</h3>
            <div className="flex gap-6 text-sm tabular-nums">
              <span>vs white: <strong>{wcag.white}:1</strong> {parseFloat(wcag.white) >= 4.5 ? "(AA pass)" : "(below AA)"}</span>
              <span>vs black: <strong>{wcag.black}:1</strong> {parseFloat(wcag.black) >= 7 ? "(AAA pass)" : parseFloat(wcag.black) >= 4.5 ? "(AA pass)" : "(below AA)"}</span>
            </div>
          </div>

          <div className="mt-3 flex items-center gap-4">
            <Button onClick={save} disabled={!canWrite || saving || !clientId} className="bg-[var(--accent)] hover:bg-[var(--accent-hover)] border-[var(--accent)] text-white">{saving ? "Saving…" : "Save branding"}</Button>
            <span className="text-xs text-[var(--fg-muted)]">SuperAdmin only · no partner logos · no fabricated test data.</span>
          </div>
        </SectionCard>

        <SectionCard compact title="Preview" description="Live preview of the selected colour + logo (no fabricated partner branding).">
          <div className="rounded-[var(--radius-md)] overflow-hidden border border-[var(--border)] shadow-sm" style={previewContainerStyle}>
            <div className="px-6 py-8 flex items-center gap-4">
              {logo ? <img src={logo} alt="logo" className="h-10 w-auto max-w-[140px] object-contain" /> : <span className="text-[var(--fg-muted)] italic">No logo</span>}
              <h2 className="text-[var(--font-size-lg)] font-bold tracking-tight" style={previewTitleStyle}>
                LibrePeople <span className="font-light opacity-70">{font}</span>
              </h2>
            </div>
          </div>
        </SectionCard>

        <div className="text-xs text-[var(--fg-muted)]">AD-01 · depends AD-04 (RBAC) + AD-07 (audit) · feeds AD-02 (entitlements), AD-05 (workflow), AD-06 (credentials) · <strong>in_progress → shipped</strong> on R1.</div>
      </div>
    </Layout>
  )
}
