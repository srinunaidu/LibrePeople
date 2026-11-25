/**
 * Pay setup — the records a pay run is built from (FD-08).
 *
 * Pay periods, pay components and employee pay profiles were served and had
 * no create surface: the Payroll tab lists them, and a deployment without a
 * period cannot create a run at all. This page is the create surface, and it
 * keeps the three reads independent — a 403 on the periods must not blank the
 * profiles.
 *
 * Two facts the form respects rather than prettifies:
 *   * the pay frequency is sent in the engine's vocabulary (`Monthly`,
 *     `Semimonthly`, `Biweekly`, `Weekly`) because `period_hours()` maps those
 *     tokens; a prettier `Semi-monthly` would silently fall back to monthly.
 *   * a bank account is stored but never printed. The list says one is on
 *     file; the value is not copied into the DOM.
 */
import { useCallback, useEffect, useState, type FormEvent } from "react"
import { Layout } from "@/components/Layout"
import { EmptyState, Alert,
  Button,
  LoadingRegion,
  PageHeader,
  RetryableAlert,
  PendingVerificationAlert,
  SectionCard,
  TableSkeleton, } from "@/components/ui"
import { Checkbox, Input, Select } from "@/components/ui/inputs"
import { useAuth } from "@/context/AuthContext"
import api from "@/lib/api"
import { useFieldErrors } from "@/lib/useFieldErrors"
import { readableLoadError, isPendingVerification } from "@/lib/api"
import { fetchAllEmployees } from "@/lib/employees"
import type {
  Employee,
  PayComponentRow,
  PayProfileRow,
  PayrollPeriodRow,
} from "@/types"
import { fmtDate, money, PayrollLinks } from "./shared"

const READ_ROLES = ["SuperAdmin", "HR", "PayrollViewer"]
const MANAGE_ROLES = ["SuperAdmin", "HR"]

const COMPONENT_TYPES = ["Earning", "Deduction", "Tax"]
const PAY_FREQUENCIES = [
  { value: "Monthly", label: "Monthly" },
  { value: "Semimonthly", label: "Semi-monthly" },
  { value: "Biweekly", label: "Bi-weekly" },
  { value: "Weekly", label: "Weekly" },
]

const PT_STATES = [
  { value: "", label: "— (none, no PT)" },
  { value: "KA", label: "KA — Karnataka" },
  { value: "MH", label: "MH — Maharashtra" },
  { value: "TN", label: "TN — Tamil Nadu" },
  { value: "TG", label: "TG — Telangana" },
  { value: "WB", label: "WB — West Bengal" },
]

export default function PayrollSetup() {
  const { user } = useAuth()
  const canRead = READ_ROLES.includes(user?.role ?? "")
  const canManage = MANAGE_ROLES.includes(user?.role ?? "")

  const [periods, setPeriods] = useState<PayrollPeriodRow[]>([])
  const [components, setComponents] = useState<PayComponentRow[]>([])
  const [profiles, setProfiles] = useState<PayProfileRow[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [loading, setLoading] = useState(true)
  const [errors, setErrors] = useState<Record<string, unknown>>({})
  const [loadError, setLoadError] = useState<Record<string, unknown>>({})

  const [periodForm, setPeriodForm] = useState({
    name: "",
    start_date: "",
    end_date: "",
    pay_date: "",
  })
  const [componentForm, setComponentForm] = useState({
    code: "",
    name: "",
    component_type: "Earning",
    is_taxable: true,
    is_pre_tax: false,
  })
  const [profileForm, setProfileForm] = useState({
    employee_id: "",
    base_salary: "",
    pay_frequency: "Monthly",
    tax_withholding: "",
    bank_account: "",
    pt_state: "",
  })
  const [busy, setBusy] = useState<"" | "period" | "component" | "profile">("")
  const [notice, setNotice] = useState("")
  const [formErrors, setFormErrors] = useState<Record<string, unknown>>({})
  const periodFieldErrors = useFieldErrors(formErrors.period)
  const componentFieldErrors = useFieldErrors(formErrors.component)
  const profileFieldErrors = useFieldErrors(formErrors.profile)

  const load = useCallback(async () => {
    setLoading(true)
    setErrors({})
    const [periodResult, componentResult, profileResult, employeeResult] =
      await Promise.allSettled([
        canRead ? api.get<PayrollPeriodRow[]>("/payroll/periods") : Promise.resolve(null),
        canRead ? api.get<PayComponentRow[]>("/payroll/components") : Promise.resolve(null),
        api.get<PayProfileRow[]>("/payroll/pay-profiles"),
        fetchAllEmployees(),
      ])

    const next: Record<string, unknown> = {}

    if (periodResult.status === "fulfilled") {
      setPeriods(periodResult.value?.data ?? [])
    } else {
      setPeriods([])
      next.periods = periodResult.reason
    }
    if (componentResult.status === "fulfilled") {
      setComponents(componentResult.value?.data ?? [])
    } else {
      setComponents([])
      next.components = componentResult.reason
    }
    if (profileResult.status === "fulfilled") {
      setProfiles(profileResult.value.data)
    } else {
      setProfiles([])
      next.profiles = profileResult.reason
    }
    if (employeeResult.status === "fulfilled") {
      setEmployees(employeeResult.value.items)
    } else {
      setEmployees([])
    }

    setErrors(next)
    setLoading(false)
  }, [canRead])

  useEffect(() => {
    void load()
  }, [load])

  const employeeName = (id: number) => {
    const found = employees.find((row) => row.id === id)
    return found ? `${found.first_name} ${found.last_name}` : `Employee #${id}`
  }

  async function submitPeriod(event: FormEvent) {
    event.preventDefault()
    if (busy) return
    setFormErrors((current) => ({ ...current, period: "" }))
    setNotice("")
    
    if (!periodForm.start_date || !periodForm.end_date || !periodForm.pay_date) {
      setFormErrors((current) => ({
        ...current,
        period: "A period needs a start date, an end date and a pay date.",
      }))
      return
    }
    if (periodForm.end_date < periodForm.start_date) {
      setFormErrors((current) => ({
        ...current,
        period: "The end date cannot be before the start date.",
      }))
      return
    }
    setBusy("period")
    try {
      await api.post("/payroll/periods", {
        name: periodForm.name.trim(),
        start_date: periodForm.start_date,
        end_date: periodForm.end_date,
        pay_date: periodForm.pay_date,
      })
      setPeriodForm({ name: "", start_date: "", end_date: "", pay_date: "" })
      setNotice("Pay period created.")
      await load()
    } catch (err) {
      setFormErrors((current) => ({
        ...current,
        period: err,
      }))
    } finally {
      setBusy("")
    }
  }

  async function submitComponent(event: FormEvent) {
    event.preventDefault()
    if (busy) return
    setFormErrors((current) => ({ ...current, component: "" }))
    setNotice("")
    
    setBusy("component")
    try {
      await api.post("/payroll/components", {
        code: componentForm.code.trim(),
        name: componentForm.name.trim(),
        component_type: componentForm.component_type,
        is_taxable: componentForm.is_taxable,
        is_pre_tax: componentForm.is_pre_tax,
      })
      setComponentForm({
        code: "",
        name: "",
        component_type: "Earning",
        is_taxable: true,
        is_pre_tax: false,
      })
      setNotice("Pay component created.")
      await load()
    } catch (err) {
      setFormErrors((current) => ({
        ...current,
        component: err,
      }))
    } finally {
      setBusy("")
    }
  }

  async function submitProfile(event: FormEvent) {
    event.preventDefault()
    if (busy) return
    setFormErrors((current) => ({ ...current, profile: "" }))
    setNotice("")
    
    if (!profileForm.employee_id) {
      setFormErrors((current) => ({ ...current, profile: "Choose the employee." }))
      return
    }
    setBusy("profile")
    try {
      await api.post("/payroll/pay-profiles", {
        employee_id: Number(profileForm.employee_id),
        base_salary: Number(profileForm.base_salary || 0),
        pay_frequency: profileForm.pay_frequency,
        tax_withholding: Number(profileForm.tax_withholding || 0),
        bank_account: profileForm.bank_account.trim() || null,
        pt_state: profileForm.pt_state || null,
      })
      setProfileForm({
        employee_id: "",
        base_salary: "",
        pay_frequency: "Monthly",
        tax_withholding: "",
        bank_account: "",
        pt_state: "",
      })
      setNotice("Pay profile created.")
      await load()
    } catch (err) {
      setFormErrors((current) => ({
        ...current,
        profile: err,
      }))
    } finally {
      setBusy("")
    }
  }

  return (
    <Layout>
      <PageHeader compact
        title="Pay setup"
        description="The pay periods, components and employee pay profiles a run is built from. Creating these is limited to SuperAdmin and HR; reading the periods and components is limited to SuperAdmin, HR and PayrollViewer."
      />



      {!canRead && (
        <Alert tone="info">
          Your role does not read the organisation's pay periods and components. A pay profile
          is read only for the people you may see.
        </Alert>
      )}
      {notice ? <Alert tone="success">{notice}</Alert> : null}
      <SectionCard compact
        title="Pay periods"
        description="A run belongs to one period. The pay date decides which rule pack is in force."
      >
        {loading ? (
          <LoadingRegion label="Loading pay periods…">
            <TableSkeleton rows={3} cols={4} />
          </LoadingRegion>
        ) : errors.periods ? (
          <div className="p-5">
            {isPendingVerification(errors.periods) ? <PendingVerificationAlert /> : <RetryableAlert err={errors.periods} title="The pay periods could not be read" fallback="The pay periods could not be read." onRetry={load} />}
          </div>
        ) : (
          <>
            {canManage && (
              <form onSubmit={submitPeriod} className="p-5 border-b border-border">
                {!!formErrors.period && (
                  periodFieldErrors.hasFieldErrors ? (
                    periodFieldErrors.globalError ? <p className="text-sm text-error-text mb-3" role="alert">{periodFieldErrors.globalError}</p> : null
                  ) : isPendingVerification(formErrors.period) ? <div className="mb-3"><PendingVerificationAlert /></div> : <div className="mb-3"><RetryableAlert err={formErrors.period} title="The pay period could not be created" fallback="The pay period could not be created." /></div>
                )}
                <div className="flex flex-wrap gap-3 items-end">
                  <div className="flex-1 min-w-[200px]">
                    <label htmlFor="period-name" className="block text-xs font-medium text-text-secondary mb-1">
                      Name
                    </label>
                    <Input
                      id="period-name"
                      value={periodForm.name}
                      onChange={(event) =>
                        setPeriodForm((form) => ({ ...form, name: event.target.value }))
                      }
                      placeholder="e.g. October 2026"
                      required
                      error={!!periodFieldErrors.get("name")}
                    />
                    {periodFieldErrors.get("name") && <p role="alert" id="period-name-error" className="text-xs text-error-text mt-1">{periodFieldErrors.get("name")}</p>}
                  </div>
                  <div className="min-w-[150px]">
                    <label htmlFor="period-start" className="block text-xs font-medium text-text-secondary mb-1">
                      Start date
                    </label>
                    <Input
                      id="period-start"
                      type="date"
                      value={periodForm.start_date}
                      onChange={(event) =>
                        setPeriodForm((form) => ({ ...form, start_date: event.target.value }))
                      }
                      required
                      error={!!periodFieldErrors.get("start_date")}
                    />
                    {periodFieldErrors.get("start_date") && <p role="alert" id="period-start-error" className="text-xs text-error-text mt-1">{periodFieldErrors.get("start_date")}</p>}
                  </div>
                  <div className="min-w-[150px]">
                    <label htmlFor="period-end" className="block text-xs font-medium text-text-secondary mb-1">
                      End date
                    </label>
                    <Input
                      id="period-end"
                      type="date"
                      value={periodForm.end_date}
                      onChange={(event) =>
                        setPeriodForm((form) => ({ ...form, end_date: event.target.value }))
                      }
                      required
                      error={!!periodFieldErrors.get("end_date")}
                    />
                    {periodFieldErrors.get("end_date") && <p role="alert" id="period-end-error" className="text-xs text-error-text mt-1">{periodFieldErrors.get("end_date")}</p>}
                  </div>
                  <div className="min-w-[150px]">
                    <label htmlFor="period-pay-date" className="block text-xs font-medium text-text-secondary mb-1">
                      Pay date
                    </label>
                    <Input
                      id="period-pay-date"
                      type="date"
                      value={periodForm.pay_date}
                      onChange={(event) =>
                        setPeriodForm((form) => ({ ...form, pay_date: event.target.value }))
                      }
                      required
                      error={!!periodFieldErrors.get("pay_date")}
                    />
                    {periodFieldErrors.get("pay_date") && <p role="alert" id="period-pay-date-error" className="text-xs text-error-text mt-1">{periodFieldErrors.get("pay_date")}</p>}
                  </div>
                  <Button type="submit" loading={busy === "period"}>
                    Create period
                  </Button>
                </div>
              </form>
            )}

            {periods.length === 0 ? (
              <EmptyState title="No pay periods yet" description="A run cannot be created until one does." action={<Button onClick={load}>Retry</Button>} />
            ) : (
              <div className="table-scroll">
                <table className="table-base table-compact w-full text-sm">
                  <caption className="sr-only">Pay periods of this deployment</caption>
                  <thead>
                    <tr>
                      <th scope="col">Name</th>
                      <th scope="col">Starts</th>
                      <th scope="col">Ends</th>
                      <th scope="col">Pay date</th>
                      <th scope="col">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {periods.map((period) => (
                      <tr key={period.id}>
                        <td>{period.name}</td>
                        <td>{fmtDate(period.start_date)}</td>
                        <td>{fmtDate(period.end_date)}</td>
                        <td>{fmtDate(period.pay_date)}</td>
                        <td>{period.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </SectionCard>

      <SectionCard compact
        title="Pay components"
        description="The earnings, deductions and tax lines a pay profile can name. The platform does not publish a statutory value."
      >
        {loading ? (
          <LoadingRegion label="Loading pay components…">
            <TableSkeleton rows={3} cols={5} />
          </LoadingRegion>
        ) : errors.components ? (
          <div className="p-5">
            {isPendingVerification(errors.components) ? <PendingVerificationAlert /> : <RetryableAlert err={errors.components} title="The pay components could not be read" fallback="The pay components could not be read." onRetry={load} />}
          </div>
        ) : (
          <>
            {canManage && (
              <form onSubmit={submitComponent} className="p-5 border-b border-border">
                {!!formErrors.component && (
                  componentFieldErrors.hasFieldErrors ? (
                    componentFieldErrors.globalError ? <p className="text-sm text-error-text mb-3" role="alert">{componentFieldErrors.globalError}</p> : null
                  ) : isPendingVerification(formErrors.component) ? <div className="mb-3"><PendingVerificationAlert /></div> : <div className="mb-3"><RetryableAlert err={formErrors.component} title="The pay component could not be created" fallback="The pay component could not be created." /></div>
                )}
                <div className="flex flex-wrap gap-3 items-end">
                  <div className="min-w-[130px]">
                    <label htmlFor="component-code" className="block text-xs font-medium text-text-secondary mb-1">
                      Code
                    </label>
                    <Input
                      id="component-code"
                      value={componentForm.code}
                      onChange={(event) =>
                        setComponentForm((form) => ({ ...form, code: event.target.value }))
                      }
                      placeholder="e.g. BONUS"
                      required
                      error={!!componentFieldErrors.get("code")}
                    />
                    {componentFieldErrors.get("code") && <p role="alert" id="component-code-error" className="text-xs text-error-text mt-1">{componentFieldErrors.get("code")}</p>}
                  </div>
                  <div className="flex-1 min-w-[180px]">
                    <label htmlFor="component-name" className="block text-xs font-medium text-text-secondary mb-1">
                      Name
                    </label>
                    <Input
                      id="component-name"
                      value={componentForm.name}
                      onChange={(event) =>
                        setComponentForm((form) => ({ ...form, name: event.target.value }))
                      }
                      placeholder="e.g. Performance bonus"
                      required
                      error={!!componentFieldErrors.get("name")}
                    />
                    {componentFieldErrors.get("name") && <p role="alert" id="component-name-error" className="text-xs text-error-text mt-1">{componentFieldErrors.get("name")}</p>}
                  </div>
                  <div className="min-w-[150px]">
                    <label htmlFor="component-type" className="block text-xs font-medium text-text-secondary mb-1">
                      Type
                    </label>
                    <Select
                      id="component-type"
                      value={componentForm.component_type}
                      onChange={(event) =>
                        setComponentForm((form) => ({
                          ...form,
                          component_type: event.target.value,
                        }))
                      }
                      error={!!componentFieldErrors.get("component_type")}
                    >
                      {COMPONENT_TYPES.map((type) => (
                        <option key={type} value={type}>
                          {type}
                        </option>
                      ))}
                    </Select>
                    {componentFieldErrors.get("component_type") && <p role="alert" id="component-type-error" className="text-xs text-error-text mt-1">{componentFieldErrors.get("component_type")}</p>}
                  </div>
                  <Checkbox
                    id="component-taxable"
                    label="Taxable"
                    checked={componentForm.is_taxable}
                    onChange={(event) =>
                      setComponentForm((form) => ({
                        ...form,
                        is_taxable: event.target.checked,
                      }))
                    }
                  />
                  <Checkbox
                    id="component-pre-tax"
                    label="Pre-tax"
                    checked={componentForm.is_pre_tax}
                    onChange={(event) =>
                      setComponentForm((form) => ({
                        ...form,
                        is_pre_tax: event.target.checked,
                      }))
                    }
                  />
                  <Button type="submit" loading={busy === "component"}>
                    Create component
                  </Button>
                </div>
              </form>
            )}

            {components.length === 0 ? (
              <EmptyState title="No pay components yet" description="No pay components exist yet." action={<Button onClick={load}>Retry</Button>} />
            ) : (
              <div className="table-scroll">
                <table className="table-base table-compact w-full text-sm">
                  <caption className="sr-only">Pay components of this deployment</caption>
                  <thead>
                    <tr>
                      <th scope="col">Code</th>
                      <th scope="col">Name</th>
                      <th scope="col">Type</th>
                      <th scope="col">Taxable</th>
                      <th scope="col">Pre-tax</th>
                      <th scope="col">Active</th>
                    </tr>
                  </thead>
                  <tbody>
                    {components.map((component) => (
                      <tr key={component.id}>
                        <td className="font-mono text-xs">{component.code}</td>
                        <td>{component.name}</td>
                        <td>{component.component_type}</td>
                        <td>{component.is_taxable ? "Yes" : "No"}</td>
                        <td>{component.is_pre_tax ? "Yes" : "No"}</td>
                        <td>{component.is_active ? "Yes" : "No"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </SectionCard>

      <SectionCard compact
        title="Employee pay profiles"
        description="One profile per employee: the base salary for the pay period and the frequency the engine uses."
      >
        {loading ? (
          <LoadingRegion label="Loading pay profiles…">
            <TableSkeleton rows={3} cols={5} />
          </LoadingRegion>
        ) : errors.profiles ? (
          <div className="p-5">
            {isPendingVerification(errors.profiles) ? <PendingVerificationAlert /> : <RetryableAlert err={errors.profiles} title="The pay profiles could not be read" fallback="The pay profiles could not be read." onRetry={load} />}
          </div>
        ) : (
          <>
            {canManage && (
              <form onSubmit={submitProfile} className="p-5 border-b border-border">
                {!!formErrors.profile && (
                  profileFieldErrors.hasFieldErrors ? (
                    profileFieldErrors.globalError ? <p className="text-sm text-error-text mb-3" role="alert">{profileFieldErrors.globalError}</p> : null
                  ) : isPendingVerification(formErrors.profile) ? <div className="mb-3"><PendingVerificationAlert /></div> : <div className="mb-3"><RetryableAlert err={formErrors.profile} title="The pay profile could not be created" fallback="The pay profile could not be created." /></div>
                )}
                <div className="flex flex-wrap gap-3 items-end">
                  <div className="flex-1 min-w-[220px]">
                    <label htmlFor="profile-employee" className="block text-xs font-medium text-text-secondary mb-1">
                      Employee
                    </label>
                    <Select
                      id="profile-employee"
                      value={profileForm.employee_id}
                      onChange={(event) =>
                        setProfileForm((form) => ({
                          ...form,
                          employee_id: event.target.value,
                        }))
                      }
                      required
                      error={!!profileFieldErrors.get("employee_id")}
                    >
                      <option value="">Select an employee…</option>
                      {employees.map((employee) => (
                        <option key={employee.id} value={employee.id}>
                          {employee.first_name} {employee.last_name} · {employee.employee_id}
                        </option>
                      ))}
                    </Select>
                    {profileFieldErrors.get("employee_id") && <p role="alert" id="profile-employee-error" className="text-xs text-error-text mt-1">{profileFieldErrors.get("employee_id")}</p>}
                  </div>
                  <div className="min-w-[160px]">
                    <label htmlFor="profile-salary" className="block text-xs font-medium text-text-secondary mb-1">
                      Base salary per period
                    </label>
                    <Input
                      id="profile-salary"
                      type="number"
                      min="0"
                      step="0.01"
                      value={profileForm.base_salary}
                      onChange={(event) =>
                        setProfileForm((form) => ({
                          ...form,
                          base_salary: event.target.value,
                        }))
                      }
                      required
                      error={!!profileFieldErrors.get("base_salary")}
                    />
                    {profileFieldErrors.get("base_salary") && <p role="alert" id="profile-salary-error" className="text-xs text-error-text mt-1">{profileFieldErrors.get("base_salary")}</p>}
                  </div>
                  <div className="min-w-[150px]">
                    <label htmlFor="profile-frequency" className="block text-xs font-medium text-text-secondary mb-1">
                      Frequency
                    </label>
                    <Select
                      id="profile-frequency"
                      value={profileForm.pay_frequency}
                      onChange={(event) =>
                        setProfileForm((form) => ({
                          ...form,
                          pay_frequency: event.target.value,
                        }))
                      }
                      error={!!profileFieldErrors.get("pay_frequency")}
                    >
                      {PAY_FREQUENCIES.map((frequency) => (
                        <option key={frequency.value} value={frequency.value}>
                          {frequency.label}
                        </option>
                      ))}
                    </Select>
                    {profileFieldErrors.get("pay_frequency") && <p role="alert" id="profile-frequency-error" className="text-xs text-error-text mt-1">{profileFieldErrors.get("pay_frequency")}</p>}
                  </div>
                  <div className="min-w-[140px]">
                    <label htmlFor="profile-tax" className="block text-xs font-medium text-text-secondary mb-1">
                      Tax withholding
                    </label>
                    <Input
                      id="profile-tax"
                      type="number"
                      min="0"
                      step="0.01"
                      value={profileForm.tax_withholding}
                      onChange={(event) =>
                        setProfileForm((form) => ({
                          ...form,
                          tax_withholding: event.target.value,
                        }))
                      }
                      error={!!profileFieldErrors.get("tax_withholding")}
                    />
                    {profileFieldErrors.get("tax_withholding") && <p role="alert" id="profile-tax-error" className="text-xs text-error-text mt-1">{profileFieldErrors.get("tax_withholding")}</p>}
                  </div>
                  <div className="flex-1 min-w-[200px]">
                    <label htmlFor="profile-bank" className="block text-xs font-medium text-text-secondary mb-1">
                      Bank account (optional)
                    </label>
                    <Input
                      id="profile-bank"
                      value={profileForm.bank_account}
                      onChange={(event) =>
                        setProfileForm((form) => ({
                          ...form,
                          bank_account: event.target.value,
                        }))
                      }
                      autoComplete="off"
                      error={!!profileFieldErrors.get("bank_account")}
                    />
                    {profileFieldErrors.get("bank_account") && <p role="alert" id="profile-bank-error" className="text-xs text-error-text mt-1">{profileFieldErrors.get("bank_account")}</p>}
                  </div>
                  <div className="min-w-[160px]">
                    <label htmlFor="profile-pt-state" className="block text-xs font-medium text-text-secondary mb-1">
                      PT state (IN only)
                    </label>
                    <Select
                      id="profile-pt-state"
                      value={profileForm.pt_state}
                      onChange={(event) =>
                        setProfileForm((form) => ({
                          ...form,
                          pt_state: event.target.value,
                        }))
                      }
                      error={!!profileFieldErrors.get("pt_state")}
                    >
                      {PT_STATES.map((s) => (
                        <option key={s.value} value={s.value}>
                          {s.label}
                        </option>
                      ))}
                    </Select>
                    {profileFieldErrors.get("pt_state") && <p role="alert" id="profile-pt-state-error" className="text-xs text-error-text mt-1">{profileFieldErrors.get("pt_state")}</p>}
                  </div>
                  <Button type="submit" loading={busy === "profile"}>
                    Create pay profile
                  </Button>
                </div>
                <p className="text-xs text-text-secondary mt-2">
                  The bank account is stored; this screen never prints it back. PT state selects the professional-tax table (KA/MH/TN/TG/WB) for India runs.
                </p>
              </form>
            )}

            {profiles.length === 0 ? (
              <EmptyState title="No pay profiles yet" description="A run writes a payslip only for an employee who has one." action={<Button onClick={load}>Retry</Button>} />
            ) : (
              <div className="table-scroll">
                <table className="table-base table-compact w-full text-sm">
                  <caption className="sr-only">Pay profiles this account may read</caption>
                  <thead>
                    <tr>
                      <th scope="col">Employee</th>
                      <th scope="col" className="num">Base salary</th>
                      <th scope="col">Frequency</th>
                      <th scope="col" className="num">Tax withholding</th>
                      <th scope="col">Bank account</th>
                      <th scope="col">PT state</th>
                    </tr>
                  </thead>
                  <tbody>
                    {profiles.map((profile) => (
                      <tr key={profile.id}>
                        <td>{employeeName(profile.employee_id)}</td>
                        <td className="num tabular-nums">{money(profile.base_salary)}</td>
                        <td>{profile.pay_frequency}</td>
                        <td className="num tabular-nums">{money(profile.tax_withholding)}</td>
                        <td>{profile.bank_account ? "On file" : "—"}</td>
                        <td>{profile.pt_state || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </SectionCard>

      <PayrollLinks current="setup" />
    </Layout>
  )
}
