/**
 * i18n foundation — locale-aware formatting wrappers (India-first defaults).
 *
 * Every helper in this module **never throws**: an invalid value falls back
 * to a plain rendering ("—" for missing, the raw value for unparseable) so a
 * bad locale, currency, timezone or server payload can never white-screen a
 * page. Callers pass the tenant's locale/timezone/currency (see
 * `TenantContext`); when omitted the India defaults below apply.
 */

export const DEFAULT_LOCALE = "en-IN"
export const DEFAULT_TIME_ZONE = "Asia/Kolkata"
export const DEFAULT_CURRENCY = "INR"

/** Shown when there is no value to format. */
export const EMPTY_PLACEHOLDER = "—"

export interface LocaleOptions {
  /** BCP 47 tag, e.g. "en-IN". Defaults to {@link DEFAULT_LOCALE}. */
  locale?: string | null
  /** IANA timezone, e.g. "Asia/Kolkata". Defaults to {@link DEFAULT_TIME_ZONE}. */
  timeZone?: string | null
}

export interface CurrencyOptions extends LocaleOptions {
  /** ISO 4217 code, e.g. "INR". Defaults to {@link DEFAULT_CURRENCY}. */
  currency?: string | null
  maximumFractionDigits?: number
  minimumFractionDigits?: number
}

type Formattable = number | string | null | undefined

function isMissing(value: Formattable): boolean {
  return value === null || value === undefined || value === ""
}

/** `null` for missing; `NaN` (non-finite) when the value is not a number. */
function coerceNumber(value: Formattable): number | null {
  if (isMissing(value)) return null
  const n = typeof value === "number" ? value : Number(value)
  return Number.isFinite(n) ? n : NaN
}

/**
 * Format a plain number with locale grouping (en-IN gives lakh grouping:
 * 100000 → "1,00,000"). Missing → "—"; non-numeric → the raw value.
 */
export function formatNumber(
  value: Formattable,
  options?: LocaleOptions & { maximumFractionDigits?: number; minimumFractionDigits?: number },
): string {
  if (isMissing(value)) return EMPTY_PLACEHOLDER
  const n = coerceNumber(value)
  if (n === null) return EMPTY_PLACEHOLDER
  if (Number.isNaN(n)) return String(value)
  const locale = options?.locale || DEFAULT_LOCALE
  const fmt: Intl.NumberFormatOptions = {}
  if (options?.minimumFractionDigits !== undefined) fmt.minimumFractionDigits = options.minimumFractionDigits
  if (options?.maximumFractionDigits !== undefined) fmt.maximumFractionDigits = options.maximumFractionDigits
  try {
    return new Intl.NumberFormat(locale, fmt).format(n)
  } catch {
    try {
      return new Intl.NumberFormat(DEFAULT_LOCALE, fmt).format(n)
    } catch {
      return String(value)
    }
  }
}

/**
 * Format money with a currency symbol (default INR: 100000 → "₹1,00,000").
 * An unknown currency code falls back to INR rather than throwing.
 * Missing → "—"; non-numeric → the raw value.
 */
export function formatCurrency(value: Formattable, options?: CurrencyOptions): string {
  if (isMissing(value)) return EMPTY_PLACEHOLDER
  const n = coerceNumber(value)
  if (n === null) return EMPTY_PLACEHOLDER
  if (Number.isNaN(n)) return String(value)
  const locale = options?.locale || DEFAULT_LOCALE
  const currency = (options?.currency || DEFAULT_CURRENCY).toUpperCase()
  const fmt: Intl.NumberFormatOptions = { style: "currency", currency }
  if (options?.minimumFractionDigits !== undefined) fmt.minimumFractionDigits = options.minimumFractionDigits
  if (options?.maximumFractionDigits !== undefined) fmt.maximumFractionDigits = options.maximumFractionDigits
  try {
    return new Intl.NumberFormat(locale, fmt).format(n)
  } catch {
    // Bad locale tag and/or bad currency code: retry with safe defaults.
    try {
      return new Intl.NumberFormat(DEFAULT_LOCALE, {
        ...fmt,
        currency: DEFAULT_CURRENCY,
      }).format(n)
    } catch {
      return String(value)
    }
  }
}

/**
 * Format a plain integer with locale grouping (en-IN gives lakh grouping:
 * 100000 → "1,00,000"). Fractional input is truncated toward zero
 * (1.9 → "1"); use {@link formatNumber} when decimals matter.
 * Missing → "—"; non-numeric → the raw value. Never throws.
 */
export function formatInteger(
  value: Formattable,
  options?: LocaleOptions,
): string {
  if (isMissing(value)) return EMPTY_PLACEHOLDER
  const n = coerceNumber(value)
  if (n === null) return EMPTY_PLACEHOLDER
  if (Number.isNaN(n)) return String(value)
  const locale = options?.locale || DEFAULT_LOCALE
  try {
    return new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(Math.trunc(n))
  } catch {
    try {
      return new Intl.NumberFormat(DEFAULT_LOCALE, { maximumFractionDigits: 0 }).format(Math.trunc(n))
    } catch {
      return String(value)
    }
  }
}

/**
 * Format a ratio as a percentage (0.25 → "25%"). The value is a fraction of
 * 1, matching `Intl.NumberFormat` percent style. Missing → "—";
 * non-numeric → the raw value. Never throws.
 */
export function formatPercent(
  value: Formattable,
  options?: LocaleOptions & { maximumFractionDigits?: number; minimumFractionDigits?: number },
): string {
  if (isMissing(value)) return EMPTY_PLACEHOLDER
  const n = coerceNumber(value)
  if (n === null) return EMPTY_PLACEHOLDER
  if (Number.isNaN(n)) return String(value)
  const locale = options?.locale || DEFAULT_LOCALE
  const fmt: Intl.NumberFormatOptions = { style: "percent" }
  if (options?.minimumFractionDigits !== undefined) fmt.minimumFractionDigits = options.minimumFractionDigits
  if (options?.maximumFractionDigits !== undefined) fmt.maximumFractionDigits = options.maximumFractionDigits
  try {
    return new Intl.NumberFormat(locale, fmt).format(n)
  } catch {
    try {
      return new Intl.NumberFormat(DEFAULT_LOCALE, fmt).format(n)
    } catch {
      return String(value)
    }
  }
}

const DATE_ONLY_RE = /^\d{4}-\d{2}-\d{2}/

/**
 * Format a date for reading. A date-only value ("2026-03-05…") is shown as
 * the calendar day it names — the timezone is never shifted. Anything else
 * goes through `Intl.DateTimeFormat` with the tenant locale/timezone.
 * Missing → "—"; unparseable → the raw value.
 */
export function formatDate(value?: string | null, options?: LocaleOptions): string {
  if (!value) return EMPTY_PLACEHOLDER
  if (DATE_ONLY_RE.test(value)) return value.slice(0, 10)
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  const locale = options?.locale || DEFAULT_LOCALE
  const timeZone = options?.timeZone || DEFAULT_TIME_ZONE
  try {
    return new Intl.DateTimeFormat(locale, {
      timeZone,
      year: "numeric",
      month: "short",
      day: "2-digit",
    }).format(parsed)
  } catch {
    try {
      return new Intl.DateTimeFormat(DEFAULT_LOCALE, {
        timeZone: DEFAULT_TIME_ZONE,
        year: "numeric",
        month: "short",
        day: "2-digit",
      }).format(parsed)
    } catch {
      return value.slice(0, 10)
    }
  }
}

/**
 * Format a timestamp with date and time in the tenant timezone
 * (default Asia/Kolkata). Missing → "—"; unparseable → the raw value.
 */
export function formatDateTime(value?: string | null, options?: LocaleOptions): string {
  if (!value) return EMPTY_PLACEHOLDER
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  const locale = options?.locale || DEFAULT_LOCALE
  const timeZone = options?.timeZone || DEFAULT_TIME_ZONE
  try {
    return new Intl.DateTimeFormat(locale, {
      timeZone,
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(parsed)
  } catch {
    try {
      return new Intl.DateTimeFormat(DEFAULT_LOCALE, {
        timeZone: DEFAULT_TIME_ZONE,
        year: "numeric",
        month: "short",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      }).format(parsed)
    } catch {
      return value.replace("T", " ").slice(0, 19)
    }
  }
}
