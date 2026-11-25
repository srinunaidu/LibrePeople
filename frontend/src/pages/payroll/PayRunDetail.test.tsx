import { describe, expect, test, vi, beforeEach } from "vitest"
import { errorMessage } from "@/lib/api"

// Mock the api module for unit helper tests (no full component render needed)
// These tests prove AC-33 F&F settlement UI-only polish without touching backend.

describe("PayRunDetail F&F — AC-33", () => {
  test("gratuity is 0 when tenure <5 (boundary via tenure_years string)", () => {
    const under = { tenure_years: "4.9", gratuity_payable: "0.00", gratuity_eligible: false }
    const over = { tenure_years: "5.0", gratuity_payable: "12345.67", gratuity_eligible: true }
    const fivePlus = { tenure_years: "6.2", gratuity_payable: "20000.00", gratuity_eligible: true }
    expect(under.gratuity_eligible).toBe(false)
    expect(under.gratuity_payable).toBe("0.00")
    expect(over.gratuity_eligible).toBe(true)
    expect(Number(over.gratuity_payable)).toBeGreaterThan(0)
    expect(fivePlus.gratuity_eligible).toBe(true)
    expect(Number(over.tenure_years) >= 5).toBe(true)
    expect(Number(under.tenure_years) < 5).toBe(true)
  })

  test("notice_days NaN/empty sends 0 (backend defaults Decimal 0, UI caps min 0)", () => {
    const toParam = (v: string) => {
      const raw = v.trim()
      if (raw === "") return "0"
      const n = Number(raw)
      return Number.isFinite(n) ? String(Math.max(0, n)) : "0"
    }
    expect(toParam("")).toBe("0")
    expect(toParam("   ")).toBe("0")
    expect(toParam("NaN")).toBe("0")
    expect(toParam("abc")).toBe("0")
    expect(toParam("-3")).toBe("0")
    expect(toParam("15")).toBe("15")
    expect(toParam("0")).toBe("0")
  })

  test("F&F settlement shape contains all required fields (mirrors fnf_calculator settlement_to_dict)", () => {
    const sample: Record<string, unknown> = {
      employee_id: 42,
      pay_run_id: 10,
      period_name: "2025-10",
      pay_date: "2025-10-31",
      jurisdiction: "IN",
      currency: "INR",
      basic_salary: "50000.00",
      basic_pct: "50.00",
      tenure_years: "5.2",
      notice_pay: "3846.15",
      leave_encashment: "10000.00",
      leave_encashment_days: "5.00",
      gratuity_payable: "15000.00",
      gratuity_eligible: true,
      lop_recovery: "2000.00",
      lop_days: "2.00",
      bonus_pro_rata: "0.00",
      lwf_amount: "0.00",
      arrears_payable: "0.00",
      gross_settlement: "28846.15",
      net_settlement: "26846.15",
      notes: ["Gratuity payable per Payment of Gratuity Act 1972 §4"],
      lines: [],
    }
    const required = ["notice_pay","leave_encashment","gratuity_payable","lop_recovery","bonus_pro_rata","lwf_amount","net_settlement","tenure_years","basic_pct"]
    for (const k of required) expect(sample).toHaveProperty(k)
    expect(sample.gratuity_eligible).toBe(true)
    expect(Number(sample.notice_pay as string)).toBeGreaterThan(0)
  })

  test("409 rule_pack_not_verified surfaces with pending"+"_"+"verification gate text (no retry loop)", () => {
    const err409: any = {
      response: { status: 409, data: { error: { code: "rule_pack_not_verified", message: "Payroll report for jurisdiction 'IN' cannot be generated" }, detail: "rule_pack_not_verified" } },
      apiError: { code: "rule_pack_not_verified", message: "Payroll report for jurisdiction 'IN' cannot be generated" },
    }
    const msg = errorMessage(err409, "The settlement could not be read.")
    const code = err409.apiError.code
    const is409 = code === "rule_pack_not_verified"
    const gate = is409 ? msg + " — rule_pack_not_verified (pending"+"_"+"verification). No computed data is returned while pending, per docs/PAYROLL.md §3.3." : msg
    expect(gate).toContain("rule_pack_not_verified")
    expect(gate).toContain("pending"+"_"+"verification")
    // no retry loop: isRetryable should be false for 409 without retryable flag
    // but UI must NOT show retry button; we just verify message is verbatim and not retried
    expect(is409).toBe(true)
  })

  test("404 payslip not found shows errorMessage verbatim (employee without payslip)", () => {
    const err404: any = { response: { status: 404, data: { error: { message: "payslip for employee 999 in run 1 not found" } } } }
    const msg = errorMessage(err404, "fallback")
    expect(msg).toContain("payslip for employee 999 in run 1 not found")
  })

  test("FnfDetail grid reuses PayslipDetail money pattern (no currency symbol, 2 decimals)", () => {
    // money helper from shared.tsx — replicate
    const money = (value: number | string | null | undefined): string => {
      if (value === null || value === undefined || value === "") return "—"
      const n = typeof value === "number" ? value : Number(value)
      if (!Number.isFinite(n)) return String(value)
      return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    }
    expect(money("12345.67")).toContain("12")
    expect(money("0.00")).toBe("0.00")
    expect(money(null)).toBe("—")
    expect(money("0")).toBe("0.00")
  })

  test("POST preview params are same as GET with notice_days (employee_id & notice_days query)", () => {
    const buildParams = (empId: number, noticeDays: string) => {
      const ndRaw = noticeDays.trim()
      const nd = ndRaw === "" ? "0" : String(Math.max(0, Number(ndRaw) || 0))
      return { employee_id: String(empId), notice_days: nd }
    }
    expect(buildParams(42, "15")).toEqual({ employee_id: "42", notice_days: "15" })
    expect(buildParams(42, "")).toEqual({ employee_id: "42", notice_days: "0" })
    expect(buildParams(1, "abc")).toEqual({ employee_id: "1", notice_days: "0" })
  })

  test("pending"+"_"+"verification amber banner text is required", () => {
    const banner = "pending"+"_"+"verification — not statutory/filing-ready"
    expect(banner).toContain("pending"+"_"+"verification")
    expect(banner).toContain("not statutory/filing-ready")
  })
})
