/**
 * Shared pieces of the payroll operation screens (FD-08).
 *
 * Money is shown as the run recorded it. The served run does **not** name a
 * currency (the contract promises one; `PayRunOut` does not carry it), so the
 * screen never prints a symbol: a "$" invented in the browser would be a
 * claim about the money that the server did not make.
 */
import { Link } from "react-router-dom"
import { useTenantNav } from "@/lib/tenantPath"
import { formatCurrency, formatDate, formatDateTime, formatNumber } from "@/lib/format"
import type { PaySlipRow } from "@/types"

/** Two decimal places, thousands separated, and no currency symbol. */
export function money(value: number | string | null | undefined): string {
  // Plain grouping only: the run names its own currency elsewhere, so the
  // amounts never invent a symbol. See format.ts for the locale plumbing.
  return formatNumber(value, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

/** Tenant-aware money with the run/tenant currency symbol — always 2dp pinned. */
export function moneyIn(
  value: number | string | null | undefined,
  currency?: string | null,
): string {
  // Display parity: explicit currency + fixed 2dp (no Intl per-currency
  // defaults). IN-INR is the gated scope; JPY (0dp) / KWD (3dp) Intl
  // defaults are intentionally out of scope — see format.test.ts parity.
  return formatCurrency(value, {
    currency: currency || undefined,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

export function hours(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—"
  const n = typeof value === "number" ? value : Number(value)
  if (!Number.isFinite(n)) return String(value)
  return `${formatNumber(n, { maximumFractionDigits: 2 })} h`
}

export function days(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—"
  const n = typeof value === "number" ? value : Number(value)
  if (!Number.isFinite(n)) return String(value)
  return `${formatNumber(n, { maximumFractionDigits: 2 })} d`
}

/** An ISO date as the operator reads it; the time zone is not shifted. */
export function fmtDate(value?: string | null): string {
  return formatDate(value)
}

export function fmtDateTime(value?: string | null): string {
  return formatDateTime(value)
}

export function parseJson<T>(raw?: string | null): T | null {
  if (!raw) return null
  try {
    return JSON.parse(raw) as T
  } catch {
    return null
  }
}

/** One line of a payslip, as `_lines_as_json` writes it. */
export interface PayLine {
  code: string
  name: string
  amount: string
  type?: string
  rule_id?: string | null
  rule_version?: string | null
  input_source?: string | null
  calculation?: string | null
}

/** The approved time and leave a payslip consumed (`inputs_json`). */
export interface PayInputs {
  approved_time_entries?: number
  approved_worked_hours?: number
  approved_overtime_hours?: number
  unapproved_time_entries?: number
  approved_leave_requests?: number
  paid_leave_days?: number
  unpaid_leave_days?: number
}

/** The three payroll operation screens, and the one the reader is on. */
export function PayrollLinks({ current }: { current: "overview" | "runs" | "setup" }) {
  const tenantNav = useTenantNav()
  const links = [
    { key: "overview" as const, label: "Payroll overview", to: "/platform/payroll" },
    { key: "runs" as const, label: "Pay runs", to: "/platform/payroll/runs" },
    { key: "setup" as const, label: "Pay setup", to: "/platform/payroll/setup" },
  ]
  return (
    <nav aria-label="More in payroll" className="flex flex-wrap items-center gap-3 text-sm">
      <span className="text-text-secondary">More in payroll:</span>
      {links
        .filter((link) => link.key !== current)
        .map((link) => (
          <Link
            key={link.key}
            to={tenantNav.to(link.to)}
            className="text-brand-700 hover:underline"
          >
            {link.label}
          </Link>
        ))}
    </nav>
  )
}

/** One payslip, opened: what it paid and what it was paid from. */
export function PayslipDetail({ slip, packStatus }: { slip: PaySlipRow; packStatus?: string }) {
  const earnings = parseJson<PayLine[]>(slip.earnings_json) ?? []
  const deductions = parseJson<PayLine[]>(slip.deductions_json) ?? []
  const inputs = parseJson<PayInputs>(slip.inputs_json)
  const hasStatutory = deductions.some((l) => /^(PT_|TAX_|REBATE_87A|PF_|ESI_)/.test(l.code))
  const ptLines = deductions.filter((l) => l.code.startsWith("PT_"))
  const taxLines = deductions.filter((l) => l.code.startsWith("TAX_"))
  const rebateLines = deductions.filter((l) => l.code === "REBATE_87A")

  return (
    <div className="border-t border-border p-4 space-y-4" data-testid="payslip-detail">
      <div>
        <h3 className="font-semibold text-fg">
          Payslip #{slip.id} · employee {slip.employee_id}
        </h3>
        <p className="text-xs text-text-secondary mt-0.5">
          The figures the run wrote. Nothing on this panel is recalculated in the browser.
        </p>
        {packStatus === "pending_verification" && (
          <p className="text-xs text-warning-text mt-1" data-testid="pack-pending-watermark">
            configurable calculation — pending_verification — not statutory/filing-ready
          </p>
        )}
        {hasStatutory && (
          <p className="text-xs text-text-secondary mt-1" data-testid="statutory-header">
            Statutory lines: {earnings.some((l) => l.code === "BASIC") ? "BASIC" : ""} {taxLines.length ? `· TAX (${taxLines.length})` : ""} {rebateLines.length ? "· REBATE_87A" : ""} {ptLines.length ? `· ${ptLines.map((l) => l.code).join(", ")}` : ""} · PF/ESI
            {" "}· PF_EE/ESI_EE · PF_ER/ESI_ER (employer)
          </p>
        )}
      </div>

      <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
        <div>
          <dt className="text-xs text-text-secondary">Gross</dt>
          <dd className="font-medium tabular-nums">{money(slip.gross_pay)}</dd>
        </div>
        <div>
          <dt className="text-xs text-text-secondary">Deductions</dt>
          <dd className="font-medium tabular-nums">{money(slip.total_deductions)}</dd>
        </div>
        <div>
          <dt className="text-xs text-text-secondary">Net</dt>
          <dd className="font-medium tabular-nums">{money(slip.net_pay)}</dd>
        </div>
        <div>
          <dt className="text-xs text-text-secondary">Status</dt>
          <dd className="font-medium">{slip.status}</dd>
        </div>
        <div>
          <dt className="text-xs text-text-secondary">Employee contributions</dt>
          <dd className="font-medium tabular-nums">{money(slip.employee_contributions)}</dd>
        </div>
        <div>
          <dt className="text-xs text-text-secondary">Employer contributions</dt>
          <dd className="font-medium tabular-nums">{money(slip.employer_contributions)}</dd>
        </div>
      </dl>

      <div>
        <h4 className="text-sm font-semibold text-fg mb-1">What this slip was paid from</h4>
        {inputs ? (
          <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
            <div>
              <dt className="text-xs text-text-secondary">Approved time entries</dt>
              <dd>{inputs.approved_time_entries ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs text-text-secondary">Approved hours</dt>
              <dd>{hours(inputs.approved_worked_hours)}</dd>
            </div>
            <div>
              <dt className="text-xs text-text-secondary">Approved overtime</dt>
              <dd>{hours(inputs.approved_overtime_hours)}</dd>
            </div>
            <div>
              <dt className="text-xs text-text-secondary">Unapproved entries (excluded)</dt>
              <dd>{inputs.unapproved_time_entries ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs text-text-secondary">Approved leave requests</dt>
              <dd>{inputs.approved_leave_requests ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs text-text-secondary">Paid leave</dt>
              <dd>{days(inputs.paid_leave_days)}</dd>
            </div>
            <div>
              <dt className="text-xs text-text-secondary">Unpaid leave (deducted)</dt>
              <dd>{days(inputs.unpaid_leave_days)}</dd>
            </div>
          </dl>
        ) : (
          <p className="text-sm text-text-secondary">
            This payslip carries no record of its inputs. It was written before the record existed.
          </p>
        )}
      </div>

      {[
        { title: "Earnings", lines: earnings },
        { title: "Deductions", lines: deductions },
      ].map(({ title, lines }) => (
        <div key={title}>
          <h4 className="text-sm font-semibold text-fg mb-1">{title}</h4>
          {lines.length === 0 ? (
            <p className="text-sm text-text-secondary">No {title.toLowerCase()} lines on this slip.</p>
          ) : (
            <div className="table-scroll">
              <table className="table-base table-compact w-full text-sm">
                <caption className="sr-only">{title} of this payslip and the rule behind each line</caption>
                <thead>
                  <tr>
                    <th scope="col">Code</th>
                    <th scope="col">Name</th>
                    <th scope="col" className="num">Amount</th>
                    <th scope="col">Rule</th>
                    <th scope="col">Calculation</th>
                  </tr>
                </thead>
                <tbody>
                  {lines.map((line, index) => (
                    <tr key={`${line.code}-${index}`}>
                      <td className="font-mono text-xs">{line.code}</td>
                      <td>{line.name}</td>
                      <td className="num tabular-nums">{money(line.amount)}</td>
                      <td className="text-xs text-text-secondary">
                        {line.rule_id ? `${line.rule_id} v${line.rule_version ?? "?"}` : "—"}
                      </td>
                      <td className="text-xs text-text-secondary">
                        {line.calculation || line.input_source || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
