/**
 * Theme Studio — global presets, not per-token color pickers.
 *
 * 10 predefined themes, each with its own loading style. One click
 * applies the entire palette + radius + shadow to the whole app via
 * CSS variables on :root. No page-specific overrides.
 */
import { useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { StatusPill } from "@/components/ui/status-pill"
import { Alert } from "@/components/ui/feedback"
import {RetryableAlert, TableSkeleton} from "@/components/ui"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api from "@/lib/api"

// ---------------------------------------------------------------------------
// 10 presets — each is a complete theme + a distinct loading style
// ---------------------------------------------------------------------------
type Preset = {
  id: string
  name: string
  tagline: string
  vars: Record<string, string>
  /** How loading / skeleton looks in this theme */
  loading: "shimmer" | "pulse" | "dots" | "bar" | "skeleton-card" | "skeleton-line" | "skeleton-wave" | "skeleton-shimmer" | "skeleton-dots" | "skeleton-bar"
  loadingHint: string
}

const PRESETS: Preset[] = [
  {
    id: "default",
    name: "Karmathy Default",
    tagline: "Blue · clean · balanced",
    vars: {
      "--brand-600": "#2563eb", "--brand-700": "#1d4ed8", "--brand-100": "#dbeafe", "--brand-soft": "#eff6ff",
      "--surface": "#ffffff", "--surface-sunken": "#f8fafc", "--surface-inset": "#f1f5f9", "--surface-hover": "#f8fafc",
      "--radius-lg": "16px", "--radius-md": "12px",
      "--shadow-sm": "0 1px 3px rgba(15,23,42,0.06), 0 4px 12px rgba(15,23,42,0.04), 0 0 0 1px rgba(15,23,42,0.06)",
      "--error": "#b91c1c",
    },
    loading: "shimmer",
    loadingHint: "Shimmer sweep — gradient slides across",
  },
  {
    id: "midnight",
    name: "Midnight",
    tagline: "Amber on navy · dense · enterprise",
    vars: {
      "--brand-600": "#d97706", "--brand-700": "#b45309", "--brand-100": "#fffbeb", "--brand-soft": "#fef3c7",
      "--surface": "#ffffff", "--surface-sunken": "#f8fafc", "--surface-inset": "#fef3c7", "--surface-hover": "#fffbeb",
      "--radius-lg": "10px", "--radius-md": "8px",
      "--shadow-sm": "0 1px 3px rgba(15,23,42,0.10), 0 4px 12px rgba(15,23,42,0.06), 0 0 0 1px rgba(15,23,42,0.08)",
      "--error": "#b91c1c",
    },
    loading: "bar",
    loadingHint: "Progress bar — determinate, brand-coloured",
  },
  {
    id: "clay",
    name: "Warm Clay",
    tagline: "Terracotta on cream · spacious · human",
    vars: {
      "--brand-600": "#c2410c", "--brand-700": "#9a3412", "--brand-100": "#ffedd5", "--brand-soft": "#fff7ed",
      "--surface": "#fffbeb", "--surface-sunken": "#fef7ed", "--surface-inset": "#fed7aa", "--surface-hover": "#ffedd5",
      "--radius-lg": "20px", "--radius-md": "14px",
      "--shadow-sm": "0 2px 8px rgba(124,45,18,0.07), 0 8px 24px rgba(124,45,18,0.04), 0 0 0 1px rgba(124,45,18,0.06)",
      "--error": "#9f1239",
    },
    loading: "dots",
    loadingHint: "Bouncing dots — warm, friendly",
  },
  {
    id: "forest",
    name: "Forest",
    tagline: "Emerald · calm · grounded",
    vars: {
      "--brand-600": "#059669", "--brand-700": "#047857", "--brand-100": "#d1fae5", "--brand-soft": "#ecfdf5",
      "--surface": "#ffffff", "--surface-sunken": "#f0fdf4", "--surface-inset": "#dcfce7", "--surface-hover": "#f0fdf4",
      "--radius-lg": "14px", "--radius-md": "10px",
      "--shadow-sm": "0 1px 3px rgba(5,122,74,0.08), 0 4px 12px rgba(5,122,74,0.05), 0 0 0 1px rgba(5,122,74,0.07)",
      "--error": "#b91c1c",
    },
    loading: "pulse",
    loadingHint: "Soft pulse — calm, organic",
  },
  {
    id: "ocean",
    name: "Ocean",
    tagline: "Teal · fresh · airy",
    vars: {
      "--brand-600": "#0891b2", "--brand-700": "#0e7490", "--brand-100": "#cffafe", "--brand-soft": "#ecfeff",
      "--surface": "#ffffff", "--surface-sunken": "#ecfeff", "--surface-inset": "#a5f3fc", "--surface-hover": "#cffafe",
      "--radius-lg": "16px", "--radius-md": "12px",
      "--shadow-sm": "0 1px 3px rgba(8,145,178,0.08), 0 4px 12px rgba(8,145,178,0.05), 0 0 0 1px rgba(8,145,178,0.07)",
      "--error": "#b91c1c",
    },
    loading: "skeleton-wave",
    loadingHint: "Wave — teal tint sweep",
  },
  {
    id: "berry",
    name: "Berry",
    tagline: "Rose · bold · expressive",
    vars: {
      "--brand-600": "#e11d48", "--brand-700": "#be123c", "--brand-100": "#ffe4e6", "--brand-soft": "#fff1f2",
      "--surface": "#ffffff", "--surface-sunken": "#fff1f2", "--surface-inset": "#fecdd3", "--surface-hover": "#ffe4e6",
      "--radius-lg": "18px", "--radius-md": "12px",
      "--shadow-sm": "0 1px 3px rgba(225,29,72,0.08), 0 4px 12px rgba(225,29,72,0.05), 0 0 0 1px rgba(225,29,72,0.07)",
      "--error": "#9f1239",
    },
    loading: "skeleton-card",
    loadingHint: "Card skeleton — stacked, rounded",
  },
  {
    id: "violet",
    name: "Violet Bloom",
    tagline: "Violet · vibrant · modern",
    vars: {
      "--brand-600": "#7c3aed", "--brand-700": "#6d28d9", "--brand-100": "#ede9fe", "--brand-soft": "#f5f3ff",
      "--surface": "#ffffff", "--surface-sunken": "#f5f3ff", "--surface-inset": "#ddd6fe", "--surface-hover": "#ede9fe",
      "--radius-lg": "16px", "--radius-md": "12px",
      "--shadow-sm": "0 4px 12px rgba(124,58,237,0.08), 0 8px 24px rgba(124,58,237,0.04), 0 0 0 1px rgba(124,58,237,0.07)",
      "--error": "#b91c1c",
    },
    loading: "skeleton-shimmer",
    loadingHint: "Violet shimmer — gradient with brand tint",
  },
  {
    id: "slate",
    name: "Slate Minimal",
    tagline: "Slate · quiet · editorial",
    vars: {
      "--brand-600": "#475569", "--brand-700": "#334155", "--brand-100": "#f1f5f9", "--brand-soft": "#f8fafc",
      "--surface": "#ffffff", "--surface-sunken": "#f8fafc", "--surface-inset": "#e2e8f0", "--surface-hover": "#f1f5f9",
      "--radius-lg": "10px", "--radius-md": "8px",
      "--shadow-sm": "0 1px 2px rgba(15,23,42,0.04), 0 0 0 1px rgba(15,23,42,0.06)",
      "--error": "#991b1b",
    },
    loading: "skeleton-line",
    loadingHint: "Thin lines — minimal, editorial",
  },
  {
    id: "amber",
    name: "Amber Glow",
    tagline: "Amber · warm · energetic",
    vars: {
      "--brand-600": "#f59e0b", "--brand-700": "#d97706", "--brand-100": "#fef3c7", "--brand-soft": "#fffbeb",
      "--surface": "#ffffff", "--surface-sunken": "#fffbeb", "--surface-inset": "#fde68a", "--surface-hover": "#fef3c7",
      "--radius-lg": "16px", "--radius-md": "12px",
      "--shadow-sm": "0 1px 3px rgba(245,158,11,0.10), 0 4px 12px rgba(245,158,11,0.06), 0 0 0 1px rgba(245,158,11,0.08)",
      "--error": "#b91c1c",
    },
    loading: "skeleton-bar",
    loadingHint: "Bar + text — amber meter",
  },
  {
    id: "ink",
    name: "Ink",
    tagline: "Charcoal · sharp · premium",
    vars: {
      "--brand-600": "#0f172a", "--brand-700": "#020617", "--brand-100": "#e2e8f0", "--brand-soft": "#f1f5f9",
      "--surface": "#ffffff", "--surface-sunken": "#f8fafc", "--surface-inset": "#e2e8f0", "--surface-hover": "#f1f5f9",
      "--radius-lg": "12px", "--radius-md": "8px",
      "--shadow-sm": "0 1px 3px rgba(0,0,0,0.08), 0 4px 12px rgba(0,0,0,0.06), 0 0 0 1px rgba(0,0,0,0.06)",
      "--error": "#991b1b",
    },
    loading: "skeleton-dots",
    loadingHint: "Dot pulse — sharp, premium",
  },
]

// ---------------------------------------------------------------------------
// Loading preview per preset
// ---------------------------------------------------------------------------
function LoadingPreview({ preset }: { preset: Preset }) {
  const c = preset.vars["--brand-600"]!
  switch (preset.loading) {
    case "shimmer":
      return <div className="space-y-2"><div className="skeleton h-3 w-3/4 rounded" /><div className="skeleton h-3 w-1/2 rounded" /><div className="skeleton h-8 w-full rounded-lg" /></div>
    case "pulse":
      return <div className="space-y-2"><div className="h-3 w-3/4 rounded animate-pulse" style={{ background: `${c}18` }} /><div className="h-3 w-1/2 rounded animate-pulse" style={{ background: `${c}12`, animationDelay: "150ms" }} /><div className="h-8 w-full rounded-lg animate-pulse" style={{ background: `${c}10`, animationDelay: "300ms" }} /></div>
    case "dots":
      return <div className="flex items-center gap-1.5 py-2"><span className="h-2.5 w-2.5 rounded-full animate-bounce" style={{ background: c }} /><span className="h-2.5 w-2.5 rounded-full animate-bounce" style={{ background: c, animationDelay: "150ms" }} /><span className="h-2.5 w-2.5 rounded-full animate-bounce" style={{ background: c, animationDelay: "300ms" }} /><span className="text-xs ml-2" style={{ color: c }}>Loading…</span></div>
    case "bar":
      return <div className="space-y-2"><div className="h-1.5 w-full rounded-full overflow-hidden" style={{ background: `${c}18` }}><div className="h-full rounded-full animate-pulse" style={{ background: c, width: "62%" }} /></div><div className="flex gap-1.5"><div className="h-6 flex-1 rounded" style={{ background: `${c}10` }} /><div className="h-6 flex-1 rounded" style={{ background: `${c}10` }} /></div></div>
    case "skeleton-card":
      return <div className="space-y-2"><div className="h-16 rounded-xl border flex items-center gap-3 p-3" style={{ borderColor: `${c}18`, background: `${c}06` }}><div className="h-8 w-8 rounded-lg" style={{ background: `${c}18` }} /><div className="flex-1 space-y-1.5"><div className="h-2.5 w-3/4 rounded" style={{ background: `${c}14` }} /><div className="h-2 w-1/2 rounded" style={{ background: `${c}10` }} /></div></div><div className="h-8 rounded-lg" style={{ background: `${c}08` }} /></div>
    case "skeleton-line":
      return <div className="space-y-2"><div className="h-px w-full" style={{ background: `${c}18` }} /><div className="h-2 w-full rounded" style={{ background: `${c}08` }} /><div className="h-2 w-5/6 rounded" style={{ background: `${c}08` }} /><div className="h-2 w-4/6 rounded" style={{ background: `${c}06` }} /></div>
    case "skeleton-wave":
      return <div className="space-y-2"><div className="h-3 w-3/4 rounded" style={{ background: `linear-gradient(90deg, ${c}10, ${c}18, ${c}10)`, backgroundSize: "200% 100%", animation: "shimmer 1.2s ease-in-out infinite" }} /><div className="h-3 w-1/2 rounded" style={{ background: `${c}10` }} /><div className="h-8 w-full rounded-lg" style={{ background: `${c}08` }} /></div>
    case "skeleton-shimmer":
      return <div className="space-y-2"><div className="h-3 w-3/4 rounded" style={{ background: `linear-gradient(90deg, ${c}0a, ${c}1a, ${c}0a)`, backgroundSize: "200% 100%", animation: "shimmer 1.2s ease-in-out infinite" }} /><div className="h-3 w-1/2 rounded" style={{ background: `${c}0c` }} /><div className="h-8 w-full rounded-lg" style={{ background: `${c}08` }} /></div>
    case "skeleton-dots":
      return <div className="flex items-center gap-2 py-1"><span className="h-1.5 w-1.5 rounded-full" style={{ background: c, opacity: 0.9 }} /><span className="h-1.5 w-1.5 rounded-full" style={{ background: c, opacity: 0.5 }} /><span className="h-1.5 w-1.5 rounded-full" style={{ background: c, opacity: 0.25 }} /><span className="text-xs ml-1" style={{ color: c, letterSpacing: "0.06em" }}>LOADING</span></div>
    case "skeleton-bar":
      return <div className="space-y-2"><div className="h-2 w-full rounded-full overflow-hidden flex" style={{ background: `${c}12` }}><div className="h-full rounded-full" style={{ background: c, width: "44%" }} /><div className="h-full rounded-full ml-1" style={{ background: `${c}60`, width: "18%" }} /></div><div className="h-2.5 w-2/3 rounded" style={{ background: `${c}10` }} /></div>
    default:
      return <div className="skeleton h-8 w-full rounded-lg" />
  }
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function ThemeStudio() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const isAdmin = user?.role === "SuperAdmin"
  const [activeId, setActiveId] = useState("default")
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [saveError, setSaveError] = useState<unknown | null>(null)
  const [previewing, setPreviewing] = useState<string | null>(null)

  const active = PRESETS.find((p) => p.id === activeId) ?? PRESETS[0]!

  // Live preview: apply active preset vars to :root (reversible)
  const applyPreview = (id: string) => {
    const preset = PRESETS.find((p) => p.id === id)
    if (!preset) return
    const root = document.documentElement
    Object.entries(preset.vars).forEach(([k, v]) => root.style.setProperty(k, v))
    setPreviewing(id)
  }

  const clearPreview = () => {
    const preset = PRESETS.find((p) => p.id === previewing)
    if (!preset) return
    const root = document.documentElement
    Object.keys(preset.vars).forEach((k) => root.style.removeProperty(k))
    setPreviewing(null)
  }

  const applyPreset = (id: string) => {
    // Clear previous preview if different
    if (previewing && previewing !== id) {
      const prev = PRESETS.find((p) => p.id === previewing)
      if (prev) Object.keys(prev.vars).forEach((k) => document.documentElement.style.removeProperty(k))
    }
    setActiveId(id)
    applyPreview(id)
    setSaved(false)
  }

  const resetAll = () => {
    if (previewing) {
      const p = PRESETS.find((x) => x.id === previewing)
      if (p) Object.keys(p.vars).forEach((k) => document.documentElement.style.removeProperty(k))
    }
    setPreviewing(null)
    setActiveId("default")
    setSaved(false)
    setSaveError(null)
    // Remove all overrides, back to CSS defaults
    const root = document.documentElement
    PRESETS.flatMap((p) => Object.keys(p.vars)).forEach((k) => root.style.removeProperty(k))
  }

  const saveTenantTheme = async () => {
    if (!tenant) return
    const preset = PRESETS.find((p) => p.id === activeId)
    if (!preset) return
    setSaving(true)
    setSaveError(null)
    try {
      await api.patch(`/onboarding-portal/clients/${tenant.slug}/settings`, {
        primary_color: preset.vars["--brand-600"],
      })
      setSaved(true)
    } catch (e: unknown) {
      setSaveError(e instanceof Error ? e.message : "Could not save theme")
    } finally {
      setSaving(false)
    }
  }

  // Keep preview in sync when active changes
  useEffect(() => {
    if (activeId !== "default" || previewing) {
      applyPreview(activeId)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeId])

  return (
    <Layout>
      <div className="page-header">
        <div>
          <h1 className="page-title">Theme Studio</h1>
          <p className="page-description">
            10 predefined themes — pick one, the entire application follows. Each theme sets the brand, surfaces, radius and shadow globally via CSS variables on <code className="bg-surface-inset px-1 py-0.5 rounded text-xs">:root</code>.
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Button variant="secondary" size="sm" onClick={resetAll}>
            Reset to default
          </Button>
          {isAdmin && tenant && (
            <Button size="sm" onClick={saveTenantTheme} disabled={saving}>
              {saving ? "Saving…" : saved ? "Saved ✓" : "Save as tenant theme"}
            </Button>
          )}
        </div>
      </div>

      {!isAdmin && (
        <Alert tone="info">You can preview themes. Saving as tenant theme requires SuperAdmin.</Alert>
      )}
      {!!saveError && <RetryableAlert err={saveError} title="The theme could not be saved" fallback="The theme could not be saved." />}
      {saved && null /* toast.success replaces Alert success */}
      {previewing && previewing !== activeId && (
        <Alert tone="info">
          Previewing <strong>{PRESETS.find((p) => p.id === previewing)?.name}</strong> — click a theme's <em>Apply</em> to keep it, or <button onClick={clearPreview} className="underline font-medium">clear preview</button>.
        </Alert>
      )}

      {/* Active theme banner — real components in the applied theme */}
      <div className="card p-4 mb-6 flex flex-wrap items-center gap-3" style={{ borderLeft: `4px solid ${active.vars["--brand-600"]}` }}>
        <span className="h-3 w-3 rounded-full" style={{ background: active.vars["--brand-600"] }} />
        <span className="text-sm font-semibold" style={{ color: active.vars["--brand-600"] as string }}>
          Active: {active.name}
        </span>
        <span className="text-xs text-fg-muted">— {active.tagline}</span>
        <span className="ml-auto flex flex-wrap items-center gap-2">
          <Button size="sm" style={{ background: active.vars["--brand-600"], borderColor: active.vars["--brand-600"] as string }}>Primary</Button>
          <Button variant="secondary" size="sm">Secondary</Button>
          <Badge variant="brand">Brand</Badge>
          <StatusPill status="Active" />
          <StatusPill status="Pending" />
        </span>
      </div>

      {/* 10 presets grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {PRESETS.map((preset) => {
          const isActive = preset.id === activeId
          const isPreviewing = preset.id === previewing
          return (
            <div
              key={preset.id}
              role="button"
              tabIndex={0}
              onClick={() => applyPreset(preset.id)}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); applyPreset(preset.id) } }}
              aria-pressed={isActive}
              aria-label={`${preset.name} — ${isActive ? "active" : "apply"}`}
              className={`card overflow-hidden cursor-pointer text-left transition-all ${isActive ? "ring-2" : "hover:shadow-md"}`}
              style={isActive ? { boxShadow: `0 0 0 2px ${preset.vars["--brand-600"]}` } : undefined}
            >
              {/* top bar — brand colour */}
              <div className="h-1.5 w-full" style={{ background: preset.vars["--brand-600"] as string }} />

              <div className="p-3">
                <div className="flex items-start justify-between gap-2 mb-1">
                  <h3 className="font-semibold text-sm leading-tight" style={{ color: preset.vars["--brand-600"] as string }}>{preset.name}</h3>
                  {isActive && (
                    <span className="shrink-0 text-caption font-bold px-1.5 py-0.5 rounded text-white" style={{ background: preset.vars["--brand-600"] as string }}>ACTIVE</span>
                  )}
                  {isPreviewing && !isActive && (
                    <span className="shrink-0 text-caption font-medium px-1.5 py-0.5 rounded border" style={{ borderColor: preset.vars["--brand-600"] as string, color: preset.vars["--brand-600"] as string }}>PREVIEW</span>
                  )}
                </div>
                <p className="text-xs text-fg-muted mb-2">{preset.tagline}</p>

                {/* palette row */}
                <div className="flex gap-1 mb-3">
                  {(["--brand-600", "--surface-sunken", "--surface-inset"] as const).map((k) => (
                    <span key={k} className="h-6 w-6 rounded border shrink-0" style={{ background: preset.vars[k] as string, borderColor: "rgba(0,0,0,0.06)" }} title={k} />
                  ))}
                  <span className="h-6 px-1.5 rounded border flex items-center text-caption font-mono shrink-0" style={{ borderColor: "rgba(0,0,0,0.06)", background: preset.vars["--surface"] as string }}>{preset.vars["--radius-lg"]}</span>
                </div>

                {/* loading preview */}
                <div className="rounded-lg border p-2.5" style={{ borderColor: "var(--border-subtle)", background: "var(--surface-sunken)" }}>
                  <div className="text-caption font-bold uppercase tracking-wider text-fg-muted mb-1.5">{preset.loading} · loading</div>
                  <LoadingPreview preset={preset} />
                  <div className="text-caption text-fg-muted mt-1.5">{preset.loadingHint}</div>
                </div>

                <div className="mt-3">
                  {isActive ? (
                    <span className="w-full inline-flex justify-center text-xs font-medium py-1.5 rounded-lg text-white" style={{ background: preset.vars["--brand-600"] as string }}>✓ Active</span>
                  ) : (
                    <span className="w-full inline-flex justify-center text-xs font-medium py-1.5 rounded-lg border bg-surface hover:bg-surface-hover transition-colors" style={{ borderColor: preset.vars["--brand-600"] as string, color: preset.vars["--brand-600"] as string }}>Apply</span>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <div className="card p-4 mt-6">
        <h2 className="font-semibold text-fg mb-1">How this works</h2>
        <ul className="list-disc pl-5 text-sm text-text-secondary space-y-1">
          <li>Click any theme — its brand, surfaces, radius and shadow apply to <strong>the entire application</strong> via CSS variables on <code className="bg-surface-inset px-1 rounded text-xs">:root</code>. No page has its own colour.</li>
          <li>Each theme has a distinct <strong>loading style</strong> (shimmer, pulse, dots, bar, card, wave…) — the skeleton you see while data loads matches the theme's character.</li>
          <li><strong>Active</strong> is the theme the app is rendering in right now. Change it and every card, button, badge and table follows.</li>
          <li><strong>Save as tenant theme</strong> (SuperAdmin) persists the brand colour to the tenant — survives reloads for that workspace.</li>
          <li>Guarded by <code className="bg-surface-inset px-1 rounded text-xs">check:design</code> in <code className="bg-surface-inset px-1 rounded text-xs">npm run verify</code> — hard-coded colours fail the build.</li>
        </ul>
      </div>
    </Layout>
  )
}
