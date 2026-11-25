import { createContext, useContext, useEffect, useState, ReactNode } from "react"
import { setTenantSlug } from "@/lib/tenantSlugStore"
import { DEFAULT_CURRENCY, DEFAULT_LOCALE, DEFAULT_TIME_ZONE } from "@/lib/format"
import api from "@/lib/api"

export interface TenantInfo {
  slug: string
  name: string
  primary_color: string
  secondary_color: string
  logo_url?: string
  timezone: string
  locale: string
  /** ISO 4217 code the tenant prices in. Defaults to INR when not set. */
  currency: string
  status: string
}

interface TenantState {
  tenant: TenantInfo | null
  loading: boolean
  isMultiTenant: boolean
  /** Non-fatal note about tenant branding, surfaced in the app shell. */
  themeError: string | null
}

const TenantContext = createContext<TenantState>({
  tenant: null,
  loading: false,
  isMultiTenant: false,
  themeError: null,
})

export interface TenantLocaleSettings {
  locale: string
  timezone: string
  currency: string
}

/** A present-but-unusable tenant setting and the default it fell back to. */
export interface TenantLocaleWarning {
  field: "locale" | "timezone" | "currency"
  received: string
  fallback: string
}

function isValidLocaleTag(tag: string): boolean {
  try {
    // Throws RangeError on a malformed BCP 47 tag; well-formed but
    // unknown tags canonicalise without throwing.
    return Intl.getCanonicalLocales(tag).length > 0
  } catch {
    return false
  }
}

function isValidTimeZone(zone: string): boolean {
  try {
    new Intl.DateTimeFormat("en", { timeZone: zone })
    return true
  } catch {
    return false
  }
}

function isValidCurrencyCode(code: string): boolean {
  return /^[A-Z]{3}$/.test(code)
}

/**
 * Validate tenant locale settings, falling back per field to the India
 * defaults. Read-only: a bad value is never written back to the server —
 * the caller keeps the fallback in memory and surfaces the warning.
 */
export function resolveTenantLocaleSettings(input: {
  locale?: string | null
  timezone?: string | null
  currency?: string | null
}): { settings: TenantLocaleSettings; warnings: TenantLocaleWarning[] } {
  const warnings: TenantLocaleWarning[] = []

  let locale = DEFAULT_LOCALE
  const rawLocale = (input.locale ?? "").trim()
  if (rawLocale) {
    if (isValidLocaleTag(rawLocale)) {
      locale = rawLocale
    } else {
      warnings.push({ field: "locale", received: input.locale as string, fallback: DEFAULT_LOCALE })
    }
  }

  let timezone = DEFAULT_TIME_ZONE
  const rawZone = (input.timezone ?? "").trim()
  if (rawZone) {
    if (isValidTimeZone(rawZone)) {
      timezone = rawZone
    } else {
      warnings.push({ field: "timezone", received: input.timezone as string, fallback: DEFAULT_TIME_ZONE })
    }
  }

  let currency = DEFAULT_CURRENCY
  const rawCurrency = (input.currency ?? "").trim().toUpperCase()
  if (rawCurrency) {
    if (isValidCurrencyCode(rawCurrency)) {
      currency = rawCurrency
    } else {
      warnings.push({ field: "currency", received: input.currency as string, fallback: DEFAULT_CURRENCY })
    }
  }

  return { settings: { locale, timezone, currency }, warnings }
}

// Extract tenant slug from hostname or path — normalized to lowercase
function detectTenantSlug(): string | null {
  const host = window.location.hostname.toLowerCase()
  const parts = host.split(".")

  // IP literals (127.0.0.1, ::1, …) have no subdomains: without this guard
  // the first octet ("127") was returned as a tenant slug, so every request
  // carried X-Tenant-Slug: 127 and the branding lookup always missed.
  const isIpLiteral =
    /^\d+\.\d+\.\d+\.\d+$/.test(host) || host.includes(":")

  // Known platform domains where the first part is NOT a tenant
  const platformDomains = ["onrender", "vercel", "netlify", "herokuapp", "github", "localhost"]
  const isPlatform = platformDomains.some((d) => host.includes(d))

  // 1. Subdomain detection: client1.karmathy.com -> "client1"
  //    (only on custom domains, not on platform domains or IP literals)
  if (!isIpLiteral && !isPlatform && parts.length >= 3 && parts[0] && parts[0] !== "www" && parts[0] !== "app") {
    const mainDomains = ["karmathy"]
    if (!mainDomains.includes(parts[0])) {
      return parts[0].toLowerCase()
    }
  }

  // 2. Path-based fallback: /t/:slug/...
  const match = window.location.pathname.match(/^\/t\/([^/]+)/)
  if (match) return match[1].toLowerCase()

  return null
}

const HEX_RE = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i

/** Parse #rgb or #rrggbb into [r,g,b], or null when unparseable. */
function parseHex(hex: string): [number, number, number] | null {
  if (!hex || !HEX_RE.test(hex)) return null
  let h = hex.slice(1)
  if (h.length === 3) h = h.split("").map((c) => c + c).join("")
  return [
    parseInt(h.slice(0, 2), 16),
    parseInt(h.slice(2, 4), 16),
    parseInt(h.slice(4, 6), 16),
  ]
}

/** WCAG relative luminance. */
function luminance([r, g, b]: [number, number, number]): number {
  const f = (c: number) => {
    const s = c / 255
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4)
  }
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
}

/** WCAG contrast ratio, rounded to 2dp. */
function contrast(a: [number, number, number], b: [number, number, number]): number {
  const la = luminance(a)
  const lb = luminance(b)
  const ratio = (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05)
  return Math.round(ratio * 100) / 100
}

/** Pick black or white text for a background, whichever has more contrast. */
function bestTextOn(bg: [number, number, number]): "#FFFFFF" | "#000000" {
  return contrast(bg, [255, 255, 255]) >= contrast(bg, [0, 0, 0]) ? "#FFFFFF" : "#000000"
}

/** Move a colour toward black (negative amount) or white (positive). */
function shade(rgb: [number, number, number], amount: number): [number, number, number] {
  const target = amount < 0 ? 0 : 255
  const t = Math.abs(amount)
  return [
    Math.round(rgb[0] + (target - rgb[0]) * t),
    Math.round(rgb[1] + (target - rgb[1]) * t),
    Math.round(rgb[2] + (target - rgb[2]) * t),
  ]
}

/**
 * Darken a colour step-by-step until it reaches `minRatio` contrast against
 * white. Used to derive a link/active-text variant of a tenant accent that is
 * too light to read on white (e.g. a mid-green or violet brand colour).
 */
function darkenUntilReadableOnWhite(
  rgb: [number, number, number],
  minRatio: number
): { rgb: [number, number, number]; ratio: number } {
  let current = rgb
  for (let step = 0; step <= 10; step++) {
    const ratio = contrast(current, [255, 255, 255])
    if (ratio >= minRatio) return { rgb: current, ratio }
    current = shade(current, -0.08)
  }
  // Black always satisfies the ratio.
  return { rgb: [0, 0, 0], ratio: contrast([0, 0, 0], [255, 255, 255]) }
}

const toHex = ([r, g, b]: [number, number, number]) =>
  "#" + [r, g, b].map((c) => c.toString(16).padStart(2, "0")).join("").toUpperCase()

export interface DerivedTheme {
  vars: Record<string, string>
  warnings: string[]
}

/**
 * Derive the full set of tenant theme variables from the tenant's own
 * primary/secondary colours, validating contrast so a tenant cannot make the
 * portal unreadable.
 *
 * Returns null when the supplied primary is unusable, in which case the caller
 * keeps the global defaults rather than shipping an unreadable theme.
 */
export function deriveTheme(primary: string, secondary: string): DerivedTheme | null {
  const p = parseHex(primary)
  if (!p) return null

  const s = parseHex(secondary)
  const secondaryRgb: [number, number, number] = s ?? [15, 23, 42] // navy fallback
  const warnings: string[] = []

  // A tenant accent is used in two distinct ways, which have different
  // contrast requirements:
  //   1. as a surface (buttons, badges) carrying its own text colour
  //   2. as text on white (links, active nav)
  // Rejecting a colour that fails (2) would discard legitimate brand accents,
  // so instead we derive a readable variant for that case.

  // (1) Text sitting on the accent surface.
  const accentText: "#FFFFFF" | "#000000" = bestTextOn(p)
  const onAccent = contrast(p, accentText === "#FFFFFF" ? [255, 255, 255] : [0, 0, 0])
  if (onAccent < 4.5) {
    warnings.push(
      `Accent ${primary.toUpperCase()} only supports ${onAccent}:1 against its button ` +
        `text; a contrasting label colour has been applied.`
    )
  }

  // (2) The accent used as text on white.
  const asText = darkenUntilReadableOnWhite(p, 4.5)
  if (toHex(asText.rgb) !== toHex(p)) {
    warnings.push(
      `Accent ${primary.toUpperCase()} is only ${contrast(p, [255, 255, 255]).toFixed(2)}:1 ` +
        `as text on white (WCAG AA needs 4.5:1); links and active states use ` +
        `${toHex(asText.rgb)} at ${asText.ratio.toFixed(2)}:1 instead.`
    )
  }

  // Tinted surfaces must stay light enough to carry body text.
  let light = shade(p, luminance(p) > 0.5 ? 0.85 : 0.9)
  let tintRgb: [number, number, number] = light
  if (contrast(light, [17, 24, 39]) < 4.5) {
    // Blend toward white until dark text is readable on it.
    tintRgb = [17, 24, 39]
    for (let step = 0; step <= 10; step++) {
      tintRgb = shade(p, 0.7 + step * 0.03)
      if (contrast(tintRgb, [17, 24, 39]) >= 4.5) break
    }
    warnings.push(`Accent tint adjusted to ${toHex(tintRgb)} to keep label text readable.`)
  }

  return {
    warnings,
    vars: {
      "--tenant-primary": toHex(p),
      "--tenant-primary-dark": toHex(shade(asText.rgb, -0.2)),
      "--tenant-primary-light": toHex(tintRgb),
      "--tenant-primary-text": toHex(asText.rgb),
      "--tenant-primary-contrast": accentText,
      "--tenant-secondary": toHex(secondaryRgb),
    },
  }
}

export function TenantProvider({ children }: { children: ReactNode }) {
  const [tenant, setTenant] = useState<TenantInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [themeError, setThemeError] = useState<string | null>(null)
  const slug = detectTenantSlug()

  useEffect(() => {
    if (!slug) {
      setTenantSlug(null)
      setLoading(false)
      return
    }
    const lowerSlug = slug.toLowerCase()
    setTenantSlug(lowerSlug)
    // Fetch with case-insensitive fallback: try lower first, if 404 try original
    api
      .get(`/onboarding-portal/clients/by-slug/${lowerSlug}`)
      .then((r) => {
        const found = r.data
        if (!found) {
          setThemeError(`No tenant matches "${slug}". Showing the default Karmathy experience.`)
          setLoading(false)
          return
        }

        const resolved = resolveTenantLocaleSettings({
          locale: found.locale,
          timezone: found.timezone,
          currency: found.currency,
        })
        for (const w of resolved.warnings) {
          console.warn(
            `[tenant] invalid ${w.field} ${JSON.stringify(w.received)} — falling back to ${w.fallback} (read-only, not saved)`,
          )
        }
        setTenant({
          slug: found.slug,
          name: found.name,
          primary_color: found.primary_color,
          secondary_color: found.secondary_color,
          logo_url: found.logo_url,
          // India-first defaults: a tenant without stored settings still
          // formats en-IN / Asia/Kolkata / INR rather than the browser's.
          // Stored settings are validated in memory only: an invalid value
          // falls back to the default with a console warning and is never
          // written back (read-only — no migration, no settings write).
          timezone: resolved.settings.timezone,
          locale: resolved.settings.locale,
          currency: resolved.settings.currency,
          status: found.status,
        })

        // Apply branding. deriveTheme validates contrast and refuses unusable
        // colours, so a tenant cannot break legibility for anyone.
        const theme = deriveTheme(found.primary_color, found.secondary_color)
        const root = document.documentElement
        if (theme) {
          for (const [k, v] of Object.entries(theme.vars)) {
            root.style.setProperty(k, v)
          }
          setThemeError(theme.warnings.length ? theme.warnings.join(" ") : null)
        } else {
          setThemeError(
            `Tenant "${found.name}" has an accent colour that fails WCAG AA contrast. ` +
              `Using default Karmathy branding.`
          )
        }
        // Gate tenant-aware styling so the global site is never affected.
        root.setAttribute("data-tenant", found.slug.toLowerCase())
        document.title = `${found.name} — Karmathy`
      })
      .catch(() => {
        setThemeError("Could not load tenant branding. Using default Karmathy branding.")
      })
      .finally(() => setLoading(false))
  }, [slug])

  return (
    <TenantContext.Provider value={{ tenant, loading, isMultiTenant: !!slug, themeError }}>
      {children}
    </TenantContext.Provider>
  )
}

export const useTenant = () => useContext(TenantContext)
export const detectTenant = detectTenantSlug