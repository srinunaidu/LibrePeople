import { describe, expect, it } from "vitest"
import { resolveTenantLocaleSettings } from "./TenantContext"
import { DEFAULT_CURRENCY, DEFAULT_LOCALE, DEFAULT_TIME_ZONE } from "@/lib/format"

describe("resolveTenantLocaleSettings", () => {
  it("passes valid settings through without warnings", () => {
    const { settings, warnings } = resolveTenantLocaleSettings({
      locale: "de-DE",
      timezone: "Europe/Berlin",
      currency: "usd",
    })
    expect(warnings).toEqual([])
    expect(settings).toEqual({ locale: "de-DE", timezone: "Europe/Berlin", currency: "USD" })
  })

  it("falls back to India defaults when nothing is stored, without warnings", () => {
    const { settings, warnings } = resolveTenantLocaleSettings({})
    expect(warnings).toEqual([])
    expect(settings).toEqual({
      locale: DEFAULT_LOCALE,
      timezone: DEFAULT_TIME_ZONE,
      currency: DEFAULT_CURRENCY,
    })
  })

  it("falls back per field with a warning for each invalid value", () => {
    const { settings, warnings } = resolveTenantLocaleSettings({
      locale: "not a locale!!",
      timezone: "Moon/Olympus",
      currency: "XX",
    })
    expect(settings).toEqual({
      locale: DEFAULT_LOCALE,
      timezone: DEFAULT_TIME_ZONE,
      currency: DEFAULT_CURRENCY,
    })
    expect(warnings.map((w) => w.field).sort()).toEqual(["currency", "locale", "timezone"])
    for (const w of warnings) {
      expect(w.fallback).toBeTruthy()
      expect(w.received).toBeTruthy()
    }
  })

  it("keeps valid fields while falling back only the invalid one", () => {
    const { settings, warnings } = resolveTenantLocaleSettings({
      locale: "en-IN",
      timezone: "Mars/Space",
      currency: "INR",
    })
    expect(settings.locale).toBe("en-IN")
    expect(settings.currency).toBe("INR")
    expect(settings.timezone).toBe(DEFAULT_TIME_ZONE)
    expect(warnings.map((w) => w.field)).toEqual(["timezone"])
  })
})
