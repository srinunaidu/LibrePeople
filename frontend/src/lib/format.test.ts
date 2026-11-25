import { describe, expect, it } from "vitest"
import { formatCurrency, formatDate, formatDateTime, formatInteger, formatNumber, formatPercent } from "./format"

describe("formatNumber", () => {
  it("groups lakhs en-IN style by default", () => {
    // Indian digit grouping: 1,00,000 — not the Western 100,000.
    expect(formatNumber(100000)).toBe("1,00,000")
    expect(formatNumber(10000000)).toBe("1,00,00,000")
  })

  it("returns the placeholder for missing values", () => {
    expect(formatNumber(null)).toBe("—")
    expect(formatNumber(undefined)).toBe("—")
    expect(formatNumber("")).toBe("—")
  })

  it("returns the raw value for invalid numbers instead of throwing", () => {
    expect(formatNumber("abc")).toBe("abc")
    expect(formatNumber("12,000")).toBe("12,000")
  })

  it("honours fraction-digit options", () => {
    expect(formatNumber(1234.5, { minimumFractionDigits: 2 })).toBe("1,234.50")
  })
})

describe("formatCurrency", () => {
  it("formats INR with lakh grouping by default", () => {
    const out = formatCurrency(100000)
    expect(out).toContain("₹")
    expect(out).toContain("1,00,000")
  })

  it("returns the placeholder for missing values", () => {
    expect(formatCurrency(null)).toBe("—")
    expect(formatCurrency(undefined)).toBe("—")
  })

  it("returns the raw value for invalid amounts instead of throwing", () => {
    expect(formatCurrency("abc")).toBe("abc")
    expect(() => formatCurrency("abc")).not.toThrow()
  })

  it("falls back to INR for an unknown currency code instead of throwing", () => {
    let out = ""
    expect(() => {
      out = formatCurrency(100, { currency: "XX" })
    }).not.toThrow()
    expect(out).toContain("₹")
  })

  it("falls back to en-IN for a bad locale tag instead of throwing", () => {
    let out = ""
    expect(() => {
      out = formatCurrency(100000, { locale: "not a locale!!" })
    }).not.toThrow()
    expect(out).toContain("1,00,000")
  })

  it("switches symbol and grouping with the tenant currency/locale (no conversion)", () => {
    // INR tenant (India default): ₹ with lakh grouping.
    const inr = formatCurrency(100000, { locale: "en-IN", currency: "INR" })
    expect(inr).toContain("₹")
    expect(inr).toContain("1,00,000")

    // USD tenant: $ with Western grouping under en-US.
    const usd = formatCurrency(100000, { locale: "en-US", currency: "USD" })
    expect(usd).toContain("$")
    expect(usd).toContain("100,000")

    // Non-English locale: German grouping and decimal comma.
    const de = formatNumber(100000, { locale: "de-DE" })
    expect(de).toBe("100.000")
    const deMoney = formatCurrency(1234.5, { locale: "de-DE", currency: "USD" })
    expect(deMoney).toContain("1.234,50")

    // No tenant currency stored (null/undefined) falls back to INR.
    expect(formatCurrency(100, { currency: null })).toContain("₹")
    expect(formatCurrency(100, {})).toContain("₹")
  })

  it("renders the placeholder for missing and the raw value for invalid instead of throwing", () => {
    expect(formatCurrency("", {})).toBe("—")
    expect(formatCurrency("12,000", {})).toBe("12,000")
    expect(() => formatCurrency("12,000", { locale: "en-IN", currency: "USD" })).not.toThrow()
  })
})

describe("display parity — IN-INR 2dp pin (stored == CSV == PDF == money/moneyIn)", () => {
  // Every money display passes explicit { currency, minimumFractionDigits: 2,
  // maximumFractionDigits: 2 } — no Intl per-currency default applies.
  // Stored slip text is already 2dp (money() HALF_UP), CSV carries it
  // verbatim, PDF _money renders it, and the helpers below must agree.
  const PIN = { locale: "en-IN", currency: "INR", minimumFractionDigits: 2, maximumFractionDigits: 2 } as const

  // Mirrors shared.tsx money() (plain 2dp, no symbol — the run names no currency).
  const money = (v: number | string | null | undefined) =>
    formatNumber(v, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  // Mirrors shared.tsx moneyIn() (tenant currency symbol, 2dp pinned).
  const moneyIn = (v: number | string | null | undefined, c?: string | null) =>
    formatCurrency(v, { currency: c || undefined, minimumFractionDigits: 2, maximumFractionDigits: 2 })
  // Mirrors payroll.py PDF _money (stored text is already 2dp: format only).
  const pdfMoney = (v: unknown) => {
    try {
      const d = Number(String(v))
      if (!Number.isFinite(d)) return String(v)
      return d.toFixed(2)
    } catch {
      return String(v)
    }
  }

  it.each(["80000.00", "174562.50", "-2729.16", "208.50", "0.00", "15000.00"])(
    "stored %s renders identically everywhere",
    (stored) => {
      // money() keeps the exact 2dp digits (en-IN grouping may add commas).
      expect(money(stored).replace(/,/g, "")).toBe(stored)
      // moneyIn() carries the same digits with the ₹ symbol.
      expect(moneyIn(stored, "INR")).toContain("₹")
      expect(moneyIn(stored, "INR").replace(/[₹,\s−-]/g, "").replace(/-/g, "")).toBe(
        stored.replace(/-/g, ""),
      )
      // PDF _money agrees on stored (already-2dp) text.
      expect(pdfMoney(stored)).toBe(stored)
    },
  )

  it("null/empty renders the placeholder everywhere (CSV empty cell, PDF/UI —)", () => {
    expect(money(null)).toBe("—")
    expect(money(undefined)).toBe("—")
    expect(money("")).toBe("—")
    expect(moneyIn(null, "INR")).toBe("—")
    expect(formatCurrency(null, PIN)).toBe("—")
  })

  it("negative and zero keep sign and cents", () => {
    expect(moneyIn("-2729.16", "INR")).toContain("2,729.16")
    expect(money("0")).toBe("0.00")
    expect(moneyIn("0", "INR")).toContain("0.00")
  })

  it("x.xx5 edge: HALF_UP (stored) vs half-even (PDF format) is documented", () => {
    // Stored values are quantised HALF_UP before display, so the edge is
    // unreachable on the stored path — pinned here, see
    // backend/app/rules/test_display_parity.py::TestHalfUpVsHalfEvenEdge.
    // 2.665 HALF_UP → 2.67; JS toFixed(2) (half-even-ish binary) on the
    // *unquantised* double may give 2.66 — never fed unquantised text.
    expect(money("2.67")).toBe("2.67")
    expect(pdfMoney("2.67")).toBe("2.67")
  })

  it("JPY/KWD Intl defaults are out of scope (IN runs are INR-gated)", () => {
    // With the explicit 2dp pin, even JPY renders 2dp — the Intl 0dp/3dp
    // defaults never apply because minimum/maximumFractionDigits are set.
    expect(formatCurrency("1000", { locale: "en-IN", currency: "JPY", minimumFractionDigits: 2, maximumFractionDigits: 2 })).toContain("1,000.00")
  })

  it("Reports.tsx labour-cost override removed: monthly_cost/total pin 2dp (snapshot)", () => {
    // Reports.tsx:469,477 previously passed maximumFractionDigits: 0. The
    // override is removed — labour cost now matches payroll 2dp parity.
    const monthlyCost = formatCurrency("123456.70", PIN)
    const total = formatCurrency(2387654.5, PIN)
    expect(monthlyCost).toContain("1,23,456.70")
    expect(total).toContain("23,87,654.50")
    expect({ monthlyCost, total }).toMatchSnapshot()
  })
})

describe("formatInteger", () => {
  it("groups integers en-IN style by default", () => {
    expect(formatInteger(100000)).toBe("1,00,000")
    expect(formatInteger("42")).toBe("42")
  })

  it("truncates fractional input toward zero", () => {
    expect(formatInteger(1.9)).toBe("1")
    expect(formatInteger(-1.9)).toBe("-1")
  })

  it("renders the placeholder for missing and the raw value for invalid instead of throwing", () => {
    expect(formatInteger(null)).toBe("—")
    expect(formatInteger(undefined)).toBe("—")
    expect(formatInteger("")).toBe("—")
    expect(formatInteger("abc")).toBe("abc")
    expect(() => formatInteger("abc")).not.toThrow()
  })

  it("falls back to en-IN for a bad locale tag instead of throwing", () => {
    let out = ""
    expect(() => {
      out = formatInteger(100000, { locale: "not a locale!!" })
    }).not.toThrow()
    expect(out).toBe("1,00,000")
  })
})

describe("formatPercent", () => {
  it("formats a ratio as a percentage", () => {
    expect(formatPercent(0.25)).toBe("25%")
    expect(formatPercent("0.5")).toContain("50")
  })

  it("honours fraction-digit options", () => {
    expect(formatPercent(0.1234, { maximumFractionDigits: 1 })).toContain("12.3")
  })

  it("renders the placeholder for missing and the raw value for invalid instead of throwing", () => {
    expect(formatPercent(null)).toBe("—")
    expect(formatPercent(undefined)).toBe("—")
    expect(formatPercent("")).toBe("—")
    expect(formatPercent("abc")).toBe("abc")
    expect(() => formatPercent("abc")).not.toThrow()
    expect(() => formatPercent(0.25, { locale: "not a locale!!" })).not.toThrow()
  })
})

describe("formatDate / formatDateTime", () => {
  it("keeps date-only values on the calendar day named (no TZ shift)", () => {
    expect(formatDate("2026-03-05")).toBe("2026-03-05")
    expect(formatDate("2026-03-05T00:00:00")).toBe("2026-03-05")
  })

  it("formats timestamps with the default timezone instead of throwing", () => {
    // Noon UTC stays on the same calendar day in Asia/Kolkata.
    const out = formatDateTime("2026-03-05T12:00:00Z")
    expect(out).toContain("2026")
    expect(out).toContain("05")
    expect(() => formatDateTime("2026-03-05T12:00:00Z")).not.toThrow()
  })

  it("returns the placeholder for missing and the raw value for invalid", () => {
    expect(formatDate(null)).toBe("—")
    expect(formatDateTime(undefined)).toBe("—")
    expect(formatDate("not-a-date")).toBe("not-a-date")
    expect(formatDateTime("not-a-date")).toBe("not-a-date")
  })
})
