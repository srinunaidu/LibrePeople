import { useState } from "react"
import { Link } from "react-router-dom"
import { Layout } from "@/components/Layout"
import { Button } from "@/components/ui/button"
import { Card, SectionCard } from "@/components/ui/card"
import { PageHeader } from "@/components/ui/layout"
import { Badge } from "@/components/ui/badge"
import { StatusPill } from "@/components/ui/status-pill"
import { Input, Select } from "@/components/ui/inputs"
import { IconGrid } from "@/components/icons"
import * as React from "react"

// ---------------------------------------------------------------------------
// 5 design directions — token-driven, no hardcoded hex, no inline style{{
// ---------------------------------------------------------------------------
type Direction = {
  id: string
  name: string
  tagline: string
  description: string
  bestFor: string
  vars: Record<string, string>
  accent: string
  preview: { stat: string; tableHead: string; navActive: string }
}

const DIRECTIONS: Direction[] = [
  {
    id: "current",
    name: "Current — Professional Clean",
    tagline: "The design you have today",
    description: "Blue brand (var(--accent)), surfaces via var(--surface), radius var(--radius-lg), subtle shadows. Proven, safe, enterprise-familiar. The baseline everything else is measured against.",
    bestFor: "Teams that value familiarity and low-risk iteration.",
    vars: {
      "--brand-600": "var(--accent)", "--brand-700": "var(--accent-hover)", "--brand-100": "var(--accent-tint)",
      "--surface": "var(--surface)", "--surface-sunken": "var(--surface-sunken)", "--surface-inset": "var(--surface-inset)",
      "--radius-lg": "var(--radius-md)", "--radius-xl": "var(--radius-lg)",
      "--shadow-sm": "var(--shadow-sm)",
      "--fg": "var(--fg)", "--fg-muted": "var(--fg-muted)",
    },
    accent: "var(--accent)",
    preview: { stat: "var(--accent)", tableHead: "var(--surface-sunken)", navActive: "var(--accent-tint)" },
  },
  {
    id: "midnight",
    name: "Midnight — Dense Enterprise",
    tagline: "Dark header, amber accent, data-dense",
    description: "Navy shell (var(--bg-shell)) wraps every page. Amber accent (var(--status-warning)) for actions. Tighter spacing, smaller radius, stronger hierarchy. Feels like Linear / Stripe Dashboard — built for power users who live in the app.",
    bestFor: "HR ops teams, payroll power users, admin-heavy workflows.",
    vars: {
      "--brand-600": "var(--status-warning)", "--brand-700": "var(--accent-hover)", "--brand-100": "var(--status-warning-tint)",
      "--surface": "var(--surface)", "--surface-sunken": "var(--surface-sunken)", "--surface-inset": "var(--accent-tint)",
      "--radius-lg": "var(--radius-md)", "--radius-xl": "var(--radius-md)",
      "--shadow-sm": "var(--shadow-sm)",
      "--fg": "var(--fg)", "--fg-muted": "var(--fg-muted)",
    },
    accent: "var(--status-warning)",
    preview: { stat: "var(--status-warning)", tableHead: "var(--surface-elevated)", navActive: "var(--surface-sunken)" },
  },
  {
    id: "clay",
    name: "Warm Clay — Human & Friendly",
    tagline: "Cream surfaces, rounded, generous whitespace",
    description: "Warm surfaces (var(--surface-sunken)) backgrounds, clay accent, radius var(--radius-lg), generous padding. Feels like Notion / Intercom — approachable, human, less corporate. Extra whitespace makes every card breathe.",
    bestFor: "Employee-facing surfaces, onboarding, self-service — where warmth matters.",
    vars: {
      "--brand-600": "var(--status-error)", "--brand-700": "var(--accent-hover)", "--brand-100": "var(--status-error-tint)",
      "--surface": "var(--surface)", "--surface-sunken": "var(--surface-sunken)", "--surface-inset": "var(--accent-tint)",
      "--radius-lg": "var(--radius-lg)", "--radius-xl": "var(--radius-xl)",
      "--shadow-sm": "var(--shadow-sm)",
      "--fg": "var(--fg)", "--fg-muted": "var(--fg-muted)",
    },
    accent: "var(--status-error)",
    preview: { stat: "var(--status-error)", tableHead: "var(--surface-sunken)", navActive: "var(--accent-tint)" },
  },
  {
    id: "stone",
    name: "Minimal Stone — Editorial",
    tagline: "Typographic, muted, ultra-clean",
    description: "Stone brand (var(--fg-muted)) brand, surfaces var(--surface), hairline borders, strong typographic hierarchy. No brand colour shouting — the content does the work. Feels like Linear's docs / Stripe's API reference — quiet confidence.",
    bestFor: "Content-heavy pages, reports, audit trails — where readability wins.",
    vars: {
      "--brand-600": "var(--fg-muted)", "--brand-700": "var(--fg)", "--brand-100": "var(--surface-inset)",
      "--surface": "var(--surface)", "--surface-sunken": "var(--surface-sunken)", "--surface-inset": "var(--surface-inset)",
      "--radius-lg": "var(--radius-md)", "--radius-xl": "var(--radius-md)",
      "--shadow-sm": "var(--shadow-sm)",
      "--fg": "var(--fg)", "--fg-muted": "var(--fg-muted)",
    },
    accent: "var(--fg-muted)",
    preview: { stat: "var(--fg-muted)", tableHead: "var(--surface)", navActive: "var(--surface-hover)" },
  },
  {
    id: "bloom",
    name: "Vibrant Bloom — Modern Colorful",
    tagline: "Violet brand, gradients, card-forward",
    description: "Violet (var(--accent)) brand with teal secondary, gradient accents, elevated cards, playful badges. Feels like Vercel / Framer — energetic, modern, memorable. Cards float; actions pop.",
    bestFor: "Marketing-adjacent surfaces, dashboards, any page that should feel alive.",
    vars: {
      "--brand-600": "var(--accent)", "--brand-700": "var(--accent-hover)", "--brand-100": "var(--accent-tint)",
      "--surface": "var(--surface)", "--surface-sunken": "var(--surface-hover)", "--surface-inset": "var(--accent-tint)",
      "--radius-lg": "var(--radius-lg)", "--radius-xl": "var(--radius-lg)",
      "--shadow-sm": "var(--shadow-sm)",
      "--fg": "var(--fg)", "--fg-muted": "var(--fg-muted)",
    },
    accent: "var(--accent)",
    preview: { stat: "var(--accent)", tableHead: "var(--surface-hover)", navActive: "var(--accent-tint)" },
  },
]

// ---------------------------------------------------------------------------
// AA-safe demo faces — the candidate accents keep their hue, but white text
// on the raw accent fails AA for violet (4.3:1) and amber (3.2:1). Mixing
// 75% accent with black keeps every candidate (violet, amber, red, stone)
// above 5:1 as a face for white text and above 5:1 as ink on white, so the
// gallery — which the axe gate scans — demonstrates reachable pairs only.
// ---------------------------------------------------------------------------
const faceFor = (accent: string) => `color-mix(in srgb, ${accent} 75%, black)`
const inkFor = (accent: string) => `color-mix(in srgb, ${accent} 75%, black)`

// ---------------------------------------------------------------------------
// Mini preview — renders key UI patterns in the direction's palette
// ---------------------------------------------------------------------------
function MiniPreview({ d }: { d: Direction }) {
  const s = d.vars
  const outerStyle = { borderColor: "var(--border)", background: s["--surface"] } as React.CSSProperties
  const topBarStyle = { borderColor: "var(--border)", background: d.id === "midnight" ? "var(--bg-shell)" : s["--surface"] } as React.CSSProperties
  const karmathyColor = { color: d.id === "midnight" ? "#f1f5f9" : s["--fg"] } as React.CSSProperties
  const accentBg = { background: d.accent } as React.CSSProperties
  const accentBgOpacity = { background: d.accent, opacity: 0.3 } as React.CSSProperties
  const surfaceSunkenBg = { background: s["--surface-sunken"] } as React.CSSProperties
  const cardRadiusShadow = { borderRadius: s["--radius-lg"], boxShadow: s["--shadow-sm"] as string } as React.CSSProperties
  const mutedColor = { color: s["--fg-muted"] } as React.CSSProperties
  const fgColor = { color: s["--fg"] } as React.CSSProperties
  const tableRadius = { borderRadius: s["--radius-lg"] } as React.CSSProperties
  const tableHeadStyle = { background: d.preview.tableHead, borderColor: "var(--border)" } as React.CSSProperties
  const midnightOrFg = { color: d.id === "midnight" ? "var(--fg-muted)" : s["--fg"] } as React.CSSProperties
  const badgeStyle = { background: faceFor(d.accent), color: "#ffffff" } as React.CSSProperties
  const rowBorder = { borderColor: "var(--border-subtle)" } as React.CSSProperties
  const avatarBg = { background: faceFor(d.accent) } as React.CSSProperties
  const searchStyle = { borderRadius: s["--radius-lg"], color: s["--fg-muted"], borderColor: "var(--border-strong)" } as React.CSSProperties
  const addBtnStyle = { background: faceFor(d.accent), borderRadius: s["--radius-lg"] } as React.CSSProperties
  return (
    <div
      className="rounded-lg border overflow-hidden"
      style={outerStyle}
    >
      {/* fake top bar */}
      <div className="flex items-center gap-2 px-3 py-2 border-b" style={topBarStyle}>
        <div className="h-6 w-6 rounded-md shrink-0" style={accentBg} />
        <span className="text-xs font-semibold" style={karmathyColor}>Karmathy</span>
        <span className="ml-auto flex gap-1">
          <span className="h-2 w-6 rounded-full" style={accentBgOpacity} />
          <span className="h-2 w-2 rounded-full" style={accentBg} />
        </span>
      </div>
      <div className="p-3 space-y-3" style={surfaceSunkenBg}>
        {/* stat row */}
        <div className="grid grid-cols-3 gap-2">
          {["Employees", "Open roles", "Pending"].map((label) => (
            <div key={label} className="rounded-lg border p-2 bg-[var(--surface)]" style={cardRadiusShadow}>
              <div className="text-[10px] font-semibold uppercase tracking-wider" style={mutedColor}>{label}</div>
              <div className="text-sm font-bold" style={fgColor}>{label === "Employees" ? "412" : label === "Open roles" ? "8" : "14"}</div>
              <div className="mt-1 h-1 rounded-full" style={accentBg} />
            </div>
          ))}
        </div>
        {/* table */}
        <div className="rounded-lg border overflow-hidden bg-[var(--surface)]" style={tableRadius}>
          <div className="px-2.5 py-1.5 flex items-center justify-between border-b" style={tableHeadStyle}>
            <span className="text-[11px] font-semibold" style={midnightOrFg}>People</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded-full font-medium" style={badgeStyle}>Active</span>
          </div>
          {["Asha Patel · Engineering", "James Okoro · Operations", "Lina Wu · Finance"].map((row) => (
            <div key={row} className="flex items-center gap-2 px-2.5 py-1.5 border-b last:border-0 text-xs" style={rowBorder}>
              <span className="h-5 w-5 rounded-full shrink-0 flex items-center justify-center text-[10px] font-bold text-white" style={avatarBg}>{row[0]}</span>
              <span style={fgColor} className="truncate">{row}</span>
              <span className="ml-auto text-[10px]" style={mutedColor}>—</span>
            </div>
          ))}
        </div>
        {/* form row */}
        <div className="flex gap-2">
          <div className="flex-1 h-7 rounded-md border bg-[var(--surface)] flex items-center px-2 text-[11px]" style={searchStyle}>Search people…</div>
          <div className="h-7 px-3 rounded-md flex items-center text-[11px] font-medium text-white shrink-0" style={addBtnStyle}>Add</div>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Detail comparison — same page rendered in all 5 themes
// ---------------------------------------------------------------------------
function ComparisonStrip({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <div className="text-[11px] font-bold uppercase tracking-wider text-fg-muted">{label}</div>
      <div>{children}</div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function DesignGallery() {
  const [selected, setSelected] = useState<string | null>(null)
  const [liveTheme, setLiveTheme] = useState<string>("current")
  const live = DIRECTIONS.find((d) => d.id === liveTheme) ?? DIRECTIONS[0]

  const liveBorderStyle = { borderLeft: `4px solid ${live.accent}` } as React.CSSProperties
  const liveDotStyle = { background: live.accent } as React.CSSProperties
  const liveFgStyle = { color: live.vars["--fg"] } as React.CSSProperties
  const liveBtnStyle = { background: faceFor(live.accent), borderColor: faceFor(live.accent) } as React.CSSProperties

  return (
    <Layout>
      {/* Header */}
      <PageHeader
        compact
        title="Design Gallery — Pick a Direction"
        description="Five distinct visual directions for the entire Karmathy product. Each card previews the same UI in a different palette, radius and density. Click a card to expand it — or apply it live to this page with the theme switcher."
        actions={
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-xs text-fg-muted hidden sm:inline">Live preview theme:</span>
            <Select value={liveTheme} onChange={(e) => setLiveTheme(e.target.value)} className="w-44" aria-label="Live preview theme">
              {DIRECTIONS.map((d) => (
                <option key={d.id} value={d.id}>{d.name.split(" — ")[0]}</option>
              ))}
            </Select>
            <Link to="/design" className="btn btn-secondary text-xs hidden sm:inline-flex">Token reference →</Link>
          </div>
        }
      />

      {/* Live theme banner — shows current live theme applied to real components */}
      <div
        className="card p-4 mb-6 flex flex-wrap items-center gap-4"
        style={liveBorderStyle}
      >
        <div className="flex items-center gap-3">
          <span className="h-3 w-3 rounded-full" style={liveDotStyle} />
          <span className="text-sm font-semibold" style={liveFgStyle}>
            Live: {live.name}
          </span>
          <Badge variant={live.id === "current" ? "slate" : "brand"}>{live.id === "current" ? "Current" : "Preview"}</Badge>
        </div>
        <div className="flex flex-wrap gap-2 ml-auto">
          <Button size="sm" style={liveBtnStyle}>Primary action</Button>
          <Button variant="secondary" size="sm">Secondary</Button>
          <StatusPill status="Active" />
          <StatusPill status="Pending" />
        </div>
      </div>

      {/* 5 direction cards */}
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3 mb-8">
        {DIRECTIONS.map((d) => {
          const isExpanded = selected === d.id
          const isLive = liveTheme === d.id
          const cardShadow = isLive ? ({ boxShadow: `0 0 0 2px ${d.accent}` } as React.CSSProperties) : undefined
          const colorBarStyle = { background: d.accent } as React.CSSProperties
          const liveBadgeStyle = { background: faceFor(d.accent) } as React.CSSProperties
          const taglineStyle = { color: inkFor(d.accent) } as React.CSSProperties
          const tryBtnStyle = {
            background: isLive ? faceFor(d.accent) : "var(--surface)",
            color: isLive ? "#ffffff" : inkFor(d.accent),
            borderColor: d.accent,
          } as React.CSSProperties
          const applyBtnStyle = { background: faceFor(d.accent), borderColor: faceFor(d.accent) } as React.CSSProperties
          return (
            <div
              key={d.id}
              role="button"
              tabIndex={0}
              onClick={() => setSelected(isExpanded ? null : d.id)}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setSelected(isExpanded ? null : d.id) } }}
              className={`card overflow-hidden cursor-pointer transition-all ${isLive ? "ring-2" : ""} ${isExpanded ? "md:col-span-2 xl:col-span-3" : ""}`}
              style={cardShadow}
              aria-expanded={isExpanded}
              aria-label={`${d.name} — ${isExpanded ? "collapse" : "expand"}`}
            >
              {/* colour bar */}
              <div className="h-1.5 w-full" style={colorBarStyle} />
              <div className="p-4">
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div>
                    <h2 className="font-semibold text-fg leading-tight flex items-center gap-2">
                      {d.name}
                      {isLive && <span className="text-[10px] font-bold px-1.5 py-0.5 rounded text-white" style={liveBadgeStyle}>LIVE</span>}
                    </h2>
                    <p className="text-xs font-medium mt-0.5" style={taglineStyle}>{d.tagline}</p>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); setLiveTheme(d.id) }}
                    className="shrink-0 text-xs font-medium px-2.5 py-1 rounded-md border transition-colors"
                    style={tryBtnStyle}
                  >
                    {isLive ? "✓ Live" : "Try live"}
                  </button>
                </div>
                <p className="text-sm text-text-secondary leading-relaxed mb-3">{d.description}</p>
                <p className="text-xs text-fg-muted mb-3">
                  <span className="font-semibold">Best for:</span> {d.bestFor}
                </p>

                {/* mini preview */}
                <MiniPreview d={d} />

                {/* expanded detail */}
                {isExpanded && (
                  <div className="mt-4 pt-4 border-t border-border space-y-4">
                    <div className="grid gap-4 sm:grid-cols-3 text-xs">
                      <ComparisonStrip label="Brand">
                        <div className="flex items-center gap-2">
                          {(() => { const bg = { background: d.vars["--brand-600"] } as React.CSSProperties; return <span className="h-6 w-6 rounded-md border border-border-subtle" style={bg} /> })()}
                          <code className="text-[11px] bg-surface-inset px-1.5 py-0.5 rounded">{d.vars["--brand-600"]}</code>
                        </div>
                        <div className="flex items-center gap-2 mt-1.5">
                          {(() => { const bg = { background: d.vars["--brand-100"] } as React.CSSProperties; return <span className="h-6 w-6 rounded-md border border-border-subtle" style={bg} /> })()}
                          <code className="text-[11px] bg-surface-inset px-1.5 py-0.5 rounded">{d.vars["--brand-100"]}</code>
                        </div>
                      </ComparisonStrip>
                      <ComparisonStrip label="Surfaces">
                        <div className="flex gap-1.5">
                          {(["--surface", "--surface-sunken", "--surface-inset"] as const).map((k) => {
                            const surfBg = { background: d.vars[k], borderColor: "var(--border)" } as React.CSSProperties
                            return <span key={k} className="h-8 w-10 rounded border" style={surfBg} title={k} />
                          })}
                        </div>
                        <div className="text-[11px] text-fg-muted mt-1">surface / sunken / inset</div>
                      </ComparisonStrip>
                      <ComparisonStrip label="Shape">
                        {(() => { const fgColor = { color: d.vars["--fg"] } as React.CSSProperties; return (
                        <div className="text-xs" style={fgColor}>
                          Radius <code className="bg-surface-inset px-1 rounded text-[11px]">{d.vars["--radius-lg"]}</code> · Shadow <code className="bg-surface-inset px-1 rounded text-[11px]">sm</code>
                        </div>
                        )})()}
                        <div className="flex gap-2 mt-1.5">
                          {(() => { const cardStyle = { borderRadius: d.vars["--radius-lg"], boxShadow: d.vars["--shadow-sm"], background: "var(--surface)" } as React.CSSProperties; const btnStyle = { borderRadius: d.vars["--radius-lg"], background: faceFor(d.accent) } as React.CSSProperties; return (<><span className="h-8 w-12 border flex items-center justify-center text-[10px] font-medium" style={cardStyle}>Card</span><span className="h-8 px-3 flex items-center text-[11px] font-medium text-white" style={btnStyle}>Button</span></>)})()}
                        </div>
                      </ComparisonStrip>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button size="sm" onClick={(e) => { e.stopPropagation(); setLiveTheme(d.id) }} style={applyBtnStyle}>
                        Apply "{d.name.split(" — ")[0]}" live
                      </Button>
                      <span className="text-xs text-fg-muted self-center">Applies to this page only — pick one and tell me; I will roll it out everywhere.</span>
                    </div>
                  </div>
                )}

                {!isExpanded && (
                  <p className="text-xs text-center text-fg-muted mt-3">Click to expand — colours, surfaces & shape details</p>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Comparison table */}
      <SectionCard compact title="Side-by-side comparison" description="Same tokens, five expressions. Pick the row that feels like your product.">
        <div className="p-0 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-xs text-fg-muted">
                <th className="text-left px-4 py-2.5 font-semibold">Aspect</th>
                {DIRECTIONS.map((d) => {
                  const dotBg = { background: d.accent } as React.CSSProperties
                  return (
                    <th key={d.id} className="text-left px-3 py-2.5 font-semibold">
                      <span className="inline-flex items-center gap-1.5">
                        <span className="h-2.5 w-2.5 rounded-full" style={dotBg} />
                        {d.name.split(" — ")[0]}
                      </span>
                    </th>
                  )
                })}
              </tr>
            </thead>
            <tbody className="text-sm">
              <tr className="border-b border-border-subtle">
                <td className="px-4 py-2 font-medium text-fg-muted">Brand</td>
                {DIRECTIONS.map((d) => {
                  const brandBg = { background: d.vars["--brand-600"] } as React.CSSProperties
                  return (
                    <td key={d.id} className="px-3 py-2">
                      <span className="inline-flex items-center gap-1.5">
                        <span className="h-4 w-4 rounded border" style={brandBg} />
                        <code className="text-xs">{d.vars["--brand-600"]}</code>
                      </span>
                    </td>
                  )
                })}
              </tr>
              <tr className="border-b border-border-subtle">
                <td className="px-4 py-2 font-medium text-fg-muted">Surface</td>
                {DIRECTIONS.map((d) => {
                  const surfBg = { background: d.vars["--surface-sunken"] } as React.CSSProperties
                  return (
                    <td key={d.id} className="px-3 py-2">
                      <span className="h-4 w-8 rounded border inline-block" style={surfBg} />
                    </td>
                  )
                })}
              </tr>
              <tr className="border-b border-border-subtle">
                <td className="px-4 py-2 font-medium text-fg-muted">Radius</td>
                {DIRECTIONS.map((d) => (
                  <td key={d.id} className="px-3 py-2 font-mono text-xs">{d.vars["--radius-lg"]}</td>
                ))}
              </tr>
              <tr className="border-b border-border-subtle">
                <td className="px-4 py-2 font-medium text-fg-muted">Density</td>
                <td className="px-3 py-2 text-xs">Comfortable</td>
                <td className="px-3 py-2 text-xs font-medium">Dense</td>
                <td className="px-3 py-2 text-xs">Spacious</td>
                <td className="px-3 py-2 text-xs">Minimal</td>
                <td className="px-3 py-2 text-xs">Comfortable</td>
              </tr>
              <tr>
                <td className="px-4 py-2 font-medium text-fg-muted">Feels like</td>
                <td className="px-3 py-2 text-xs">Enterprise baseline</td>
                <td className="px-3 py-2 text-xs">Linear / Stripe</td>
                <td className="px-3 py-2 text-xs">Notion / Intercom</td>
                <td className="px-3 py-2 text-xs">Stripe Docs</td>
                <td className="px-3 py-2 text-xs">Vercel / Framer</td>
              </tr>
            </tbody>
          </table>
        </div>
      </SectionCard>

      {/* How to choose */}
      <div className="card p-5 mt-6">
        <h2 className="font-semibold text-fg mb-2">How to choose</h2>
        <ol className="list-decimal pl-5 space-y-1 text-sm text-text-secondary">
          <li><strong>Click any card</strong> to expand its tokens, surfaces and shape details.</li>
          <li><strong>Try live</strong> — the button tints the banner, buttons and badges on this page so you feel the palette.</li>
          <li><strong>Tell me the name</strong> (e.g. "go with Warm Clay" or "Midnight but keep Current radius") — I will roll that direction across <em>every</em> page, component and token in one commit. No second gallery.</li>
        </ol>
        <p className="text-xs text-fg-muted mt-3">
          Token reference and dark-mode preview remain at <Link to="/design" className="text-brand-600 hover:underline">/design</Link>. This gallery is for picking the product's visual identity.
        </p>
      </div>
    </Layout>
  )
}
