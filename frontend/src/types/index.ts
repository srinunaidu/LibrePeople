export interface Employee {
  id: number
  employee_id: string
  first_name: string
  last_name: string
  email: string
  phone?: string
  hire_date: string
  job_id: number
  department_id: number
  manager_id?: number
  status: string
  employment_type?: string | null
  termination_date?: string | null
  salary?: number
  pan_number?: string | null
  tax_regime?: string | null
  pf_uan?: string | null
  esi_number?: string | null
  ifsc_code?: string | null
}

/** One effective-dated employment change, as `GET /employees/{id}/history` reports it. */
export interface EmployeeHistoryEntry {
  id: number
  field: string
  previous_value?: string | null
  new_value?: string | null
  effective_from: string
  effective_to?: string | null
  reason?: string | null
  changed_by?: string | null
  changed_at?: string | null
}

/** Where a page sits in its collection, as the contract's `PageMeta` says. */
export interface PageMeta {
  page: number
  page_size: number
  total: number
  total_pages: number
}

/** `GET /employees/` — the contract's paged envelope, not a bare list. */
export interface EmployeePage {
  items: Employee[]
  meta: PageMeta
}

export interface Department {
  id: number
  name: string
  code: string
  description?: string
  is_active: boolean
}

export interface Job {
  id: number
  title: string
  code: string
  department_id: number
  min_salary?: number
  max_salary?: number
  is_active: boolean
}

export interface Requisition {
  id: number
  req_number: string
  title: string
  department_id: number
  job_id?: number
  location?: string
  employment_type: string
  openings: number
  status: string
  description?: string
  posted_date?: string
  closing_date?: string
}

export interface Candidate {
  id: number
  first_name: string
  last_name: string
  email: string
  phone?: string
  source?: string
  resume_url?: string
  status: string
}

export interface Application {
  id: number
  requisition_id: number
  candidate_id: number
  status: string
  notes?: string
  applied_date: string
}

export interface Offer {
  id: number
  offer_number: string
  application_id: number
  job_id?: number
  salary_offered?: number
  start_date: string
  offer_date: string
  expiry_date?: string
  status: string
  letter_url?: string
}

export interface OnboardingTask {
  id: number
  employee_id: number
  title: string
  description?: string
  category: string
  assigned_to?: string
  due_date?: string
  status: string
}

export interface OnboardingDocument {
  id: number
  employee_id: number
  document_type: string
  file_name: string
  storage_url: string
  status: string
  uploaded_at?: string
}

export interface OnboardingSummary {
  employee_id: number
  total_tasks: number
  completed_tasks: number
  progress_percent: number
  documents_uploaded: number
}

export interface User {
  id: number
  username: string
  email: string
  role: string
  is_active: boolean
}

export interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  /** The account must replace an administrator-set password before use. */
  mustChangePassword: boolean
  setMustChangePassword: (value: boolean) => void
  login: (token: string, user: User, mustChange?: boolean) => void
  logout: () => void
  /** Impersonation (SuperAdmin sudo view-as). */
  originalToken: string | null
  originalUser: User | null
  isImpersonating: boolean
  impersonate: (token: string, user: User) => void
  exitImpersonation: () => void
}

export interface TimeEntry {
  id: number
  employee_id: number
  work_date: string
  clock_in?: string
  clock_out?: string
  break_minutes: number
  worked_hours: number
  overtime_hours: number
  source: string
  status: string
  notes?: string
}

export interface Timesheet {
  id: number
  employee_id: number
  period_start: string
  period_end: string
  total_hours: number
  overtime_hours: number
  entry_count: number
  status: string
  approved_by?: number
}

/** POST /time/corrections — an employee's request to fix a clock record. */
export interface TimeCorrection {
  id: number
  employee_id: number
  time_entry_id?: number | null
  work_date: string
  requested_clock_in?: string | null
  requested_clock_out?: string | null
  reason?: string | null
  status: string
  requested_by?: number | null
  decided_by?: number | null
  decided_at?: string | null
}

/** POST /time/period-locks/lock — a locked attendance period. */
export interface PeriodLock {
  id: number
  period_start: string
  period_end: string
  is_locked: boolean
  locked_by?: number | null
  locked_at?: string | null
  reopened_by?: number | null
  reopened_at?: string | null
}

/** GET /time/period-locks/status — whether a period is locked. */
export interface PeriodLockStatus {
  period_start: string
  period_end: string
  is_locked: boolean
}

export interface ShiftTemplate {
  id: number
  name: string
  code: string
  start_time: string
  end_time: string
  break_minutes: number
  is_night: boolean
  is_active: boolean
}

export interface RosterEntry {
  id: number
  employee_id: number
  work_date: string
  shift_template_id?: number
  start_time: string
  end_time: string
  is_night: boolean
  status: string
}

export interface ShiftSwap {
  id: number
  roster_entry_id: number
  requester_id: number
  target_id?: number
  proposed_date?: string
  status: string
}

export interface LeaveType {
  id: number
  name: string
  code: string
  is_paid: boolean
  max_days_per_year: number
  is_active: boolean
}

export interface LeaveBalance {
  id: number
  employee_id: number
  leave_type_id: number
  entitlement_year: number
  entitled_days: number
  carried_over_days: number
  used_days: number
  available_days: number
  leave_type_name?: string
}

export interface LeaveRequest {
  id: number
  employee_id: number
  leave_type_id: number
  start_date: string
  end_date: string
  working_days: number
  reason?: string
  status: string
  decided_at?: string
}

export interface OffboardingTask {
  id: number
  name: string
  description?: string
  category: string
  is_required: boolean
  is_active: boolean
}

export interface OffboardingItem {
  id: number
  termination_id: number
  name: string
  category: string
  assigned_to?: string
  status: string
}

export interface Termination {
  id: number
  employee_id: number
  last_working_date: string
  termination_type: string
  reason?: string
  status: string
  final_pay_amount?: number
  items: OffboardingItem[]
}

export interface AuditLog {
  id: number
  actor_name?: string
  action: string
  entity_type: string
  entity_id?: number
  details?: string
  created_at?: string
}

/** Where the audit chain stopped holding, as `GET /admin/audit/verify` reports it. */
export interface AuditFirstBroken {
  id?: string | null
  index: number
  reason: string
}

/**
 * The result of walking the audit chain.
 *
 * `head` is the value to record outside the database: a chain rebuilt from
 * the first entry is internally consistent, and only an external anchor
 * detects that.
 */
export interface AuditVerification {
  verified: boolean
  checked_entries: number
  head?: string | null
  head_id?: number | null
  first_broken?: AuditFirstBroken | null
  verified_at: string
}

export interface Client {
  id: number
  name: string
  slug: string
  industry?: string
  country?: string
  timezone: string
  locale: string
  currency?: string | null
  primary_color: string
  secondary_color: string
  logo_url?: string
  status: string
  contact_name?: string
  contact_email?: string
}

export interface FeatureFlag {
  id: number
  client_id: number
  key: string
  name: string
  description?: string
  enabled: boolean
  config?: string
}

export interface Integration {
  id: number
  client_id: number
  name: string
  kind: string
  endpoint?: string
  username?: string
  status: string
  last_tested_at?: string
  last_sync_at?: string
  last_error?: string
  notes?: string
  has_secret: boolean
}

export interface MigrationJob {
  id: number
  client_id: number
  integration_id?: number
  entity: string
  status: string
  total: number
  processed: number
  succeeded: number
  failed: number
  error_log?: string
  started_at?: string
  finished_at?: string
}

export interface OnboardingStep {
  id: number
  client_id: number
  key: string
  title: string
  description?: string
  order_index: number
  completed: boolean
  completed_at?: string
  owner?: string
}


/* ------------------------------------------------------------------ *
 * Scheduling v2 — solver drafts, versions, attendance (SC-02..SC-05)  *
 * ------------------------------------------------------------------ */

/** One assignment produced by the roster solver. */
export interface RosterAssignment {
  slot_instance: string
  slot_id: string
  base_slot_id?: string
  employee_id: number
  date: string
  location?: string | null
  role?: string | null
  start: string
  end: string
  is_night?: boolean
}

/** A demand slot the solver could not fill, with the cause. */
export interface RosterUnfilledSlot {
  slot_id: string
  date: string
  location?: string | null
  role?: string | null
  headcount: number
  cause: string
  blocking_constraint?: string | null
  constraint?: string | null
}

export interface RosterWeightBreakdown {
  fairness?: Record<string, number>
  preference?: number
  cost?: number
  continuity?: number
  weights?: Record<string, number>
}

/** POST /scheduling/rosters/generate */
export interface RosterGenerateResponse {
  draft_id: number
  status: string
  solver_status: string
  timed_out: boolean
  objective_value?: number | null
  weight_breakdown?: RosterWeightBreakdown
  assignments: RosterAssignment[]
  roster?: RosterAssignment[]
  unfilled_slots: RosterUnfilledSlot[]
  unfilled?: RosterUnfilledSlot[]
  input_hash?: string
}

/** GET /scheduling/rosters/draft/{draft_id} */
export interface RosterDraftDetail {
  draft_id: number
  location_code?: string | null
  period_start: string
  period_end: string
  status: string
  solver_status?: string | null
  created_at: string
  assignments: RosterAssignment[]
  roster?: RosterAssignment[]
  unfilled_slots: RosterUnfilledSlot[]
  unfilled?: RosterUnfilledSlot[]
  weight_breakdown?: RosterWeightBreakdown
  objective_value?: number | null
  input_hash?: string
}

/** POST /scheduling/rosters/draft/{draft_id}/adjust */
export interface DraftAdjustmentResponse {
  draft_id: number
  assignments: RosterAssignment[]
  unfilled_slots: RosterUnfilledSlot[]
  violations: string[]
  valid: boolean
}

/** One entry of the stored, immutable roster of a version. */
export interface RosterVersionEntry {
  id: number
  employee_id: number
  work_date: string
  shift_template_id?: number | null
  start_time: string
  end_time: string
  is_night: boolean
  status: string
  notes?: string | null
}

/** GET /scheduling/rosters/versions — one row. */
export interface RosterVersionRow {
  id: number
  location_code?: string | null
  period_start: string
  period_end: string
  status: string
  published_by?: number | null
  published_at?: string | null
  solver_status?: string | null
  created_at?: string | null
  entry_count: number
  unfilled_count: number
}

/** GET /scheduling/rosters/versions/{version_id} */
export interface RosterVersionDetail extends RosterVersionRow {
  entries: RosterVersionEntry[]
  assignments?: RosterAssignment[]
  unfilled_slots?: RosterUnfilledSlot[]
  objective_value?: number | null
  input_hash?: string
}

export interface VersionDiffEntry {
  type: "added" | "removed" | "changed"
  entry?: RosterVersionEntry | null
  base_entry?: RosterVersionEntry | null
  changes?: Record<string, unknown>
}

/** GET /scheduling/rosters/versions/{version_id}/compare?base_version_id=… */
export interface VersionCompareResponse {
  version_id: number
  base_version_id: number
  added: VersionDiffEntry[]
  removed: VersionDiffEntry[]
  changed: VersionDiffEntry[]
  summary: Record<string, number>
}

/** The time entry paired with a roster entry in the attendance view. */
export interface AttendanceTimeEntry {
  id: number
  employee_id: number
  work_date: string
  clock_in?: string | null
  clock_out?: string | null
  worked_hours?: number
  overtime_hours?: number
  source?: string
  status?: string
}

export interface RosterAttendanceEntry {
  roster_entry: RosterVersionEntry
  time_entry?: AttendanceTimeEntry | null
}

/** GET /scheduling/rosters/{version_id}/attendance */
export interface RosterAttendanceResponse {
  version_id: number
  location_code?: string | null
  period_start: string
  period_end: string
  entries: RosterAttendanceEntry[]
  summary: Record<string, number>
}

export interface WorkingTimeViolation {
  id: number
  employee_id: number
  work_date: string
  kind: string
  severity: string
  minutes?: number
  detected_at?: string
  resolved?: boolean
}

export interface RosterDeviationEntry {
  roster_entry: RosterVersionEntry
  time_entry?: AttendanceTimeEntry | null
  violations: WorkingTimeViolation[]
}

/** GET /scheduling/rosters/{version_id}/attendance/deviations */
export interface RosterDeviationsResponse {
  version_id: number
  period_start: string
  period_end: string
  deviations: RosterDeviationEntry[]
  summary: Record<string, number>
}

/** POST /scheduling/rosters/{version_id}/attendance/auto-create */
export interface AutoCreateAttendanceResponse {
  version_id: number
  created_count: number
  skipped_count: number
}

/* ------------------------------------------------------------------ *
 * Payroll operations (FD-08) — add-only.                              *
 *                                                                     *
 * These mirror backend/app/schemas/payroll.py 1:1. The served shapes  *
 * are the record (L-017); the OpenAPI fragment still declares some of *
 * these operations as planned with a different shape, which is        *
 * recorded as a contract gap in agents/requests/PY-04.md.             *
 * ------------------------------------------------------------------ */

/** GET /payroll/periods — one pay period. */
export interface PayrollPeriodRow {
  id: number
  name: string
  start_date: string
  end_date: string
  pay_date: string
  status: string
  created_at?: string | null
}

/** GET /payroll/components — one earning, deduction or tax component. */
export interface PayComponentRow {
  id: number
  code: string
  name: string
  /** Earning, Deduction or Tax. */
  component_type: string
  is_taxable: boolean
  is_pre_tax: boolean
  is_active: boolean
  created_at?: string | null
}

/** GET /payroll/pay-profiles — the pay profile of one employee. */
export interface PayProfileRow {
  id: number
  employee_id: number
  base_salary: number
  pay_frequency: string
  /** Stored, but the screen shows only that one is on file. */
  bank_account?: string | null
  tax_withholding: number
  pt_state?: string | null
  created_at?: string | null
  updated_at?: string | null
}

/** GET /payroll/runs — one pay run. Status is the stored vocabulary. */
export interface PayRunRow {
  id: number
  period_id: number
  jurisdiction?: string | null
  rule_pack_id?: string | null
  run_type?: string | null
  reversal_of_run_id?: number | null
  /** Draft, Processing, Approved, Finalized or Paid. */
  status: string
  total_gross: number
  total_deductions: number
  total_net: number
  headcount: number
  run_date?: string | null
  processed_by?: number | null
  processed_at?: string | null
  approved_by?: number | null
  approved_at?: string | null
  finalized_by?: number | null
  finalized_at?: string | null
  warning?: string | null
  created_at?: string | null
  currency?: string | null
}

/** GET /payroll/payslips — one payslip, with the lines the run wrote. */
export interface PaySlipRow {
  id: number
  pay_run_id: number
  employee_id: number
  gross_pay: number
  net_pay: number
  total_deductions: number
  employee_contributions?: number | null
  employer_contributions?: number | null
  /** JSON string: code, name, amount, type, rule_id, rule_version, … */
  earnings_json?: string | null
  deductions_json?: string | null
  /** JSON string: the approved time and leave the slip consumed. */
  inputs_json?: string | null
  status: string
  created_at?: string | null
}

/* ------------------------------------------------------------------ *
 * Payroll reconciliation (PR-05)                                      *
 * ------------------------------------------------------------------ */

/** GET /payroll/runs/{run_id}/reconciliation */
export interface PayRunReconciliation {
  matched: boolean
  run_id: number
  rule_pack_id?: string | null
  rule_pack_version?: string | null
  totals: Record<string, string | number>
  discrepancies: { code: string; message: string }[]
  payslips: {
    payslip_id: number
    employee_id: number
    gross: string | number
    net: string | number
    total_deductions: string | number
    employee_contributions?: string | number
    employer_contributions?: string | number
    trace_id?: string | null
  }[]
  generated_at: string
  content_hash?: string | null
}

export interface PayRunHistoryEntry {
  id: number
  action: string
  actor_id?: number | null
  actor_name?: string | null
  details?: string | null
  created_at?: string | null
}

export interface PayRunHistory {
  run_id: number
  run_type?: string | null
  reversal_of_run_id?: number | null
  status: string
  history: PayRunHistoryEntry[]
}

/** GET/POST /payroll/runs/{run_id}/fnf — mirrors backend/app/services/fnf_calculator.py settlement_to_dict */
export interface FnfSettlement {
  employee_id: number
  pay_run_id: number
  period_name: string
  pay_date: string
  jurisdiction: string
  currency: string
  basic_salary: string
  basic_pct: string | null
  tenure_years: string | null
  notice_pay: string
  leave_encashment: string
  leave_encashment_days: string
  gratuity_payable: string
  gratuity_eligible: boolean
  lop_recovery: string
  lop_days: string
  bonus_pro_rata: string
  lwf_amount: string
  arrears_payable: string
  gross_settlement: string
  net_settlement: string
  notes: string[]
  lines: Record<string, unknown>[]
}

/* Performance (B1) */

export interface GoalRow {
  id: number
  employee_id: number
  title: string
  description?: string | null
  weight: number
  progress: number
  status: string
  due_date?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface ReviewRow {
  id: number
  employee_id: number
  reviewer_id?: number | null
  period: string
  status: string
  overall_rating?: number | null
  manager_comments?: string | null
  employee_comments?: string | null
  created_at?: string | null
  updated_at?: string | null
  finalized_at?: string | null
}

export interface FeedbackRow {
  id: number
  review_id: number
  from_employee_id?: number | null
  feedback_type: string
  rating?: number | null
  comments?: string | null
  created_at?: string | null
}

export interface BandRow {
  id: number
  job_id: number
  level: string
  min_salary: number
  mid_salary: number
  max_salary: number
  currency: string
  created_at?: string | null
}

export interface MeritCycleRow {
  id: number
  name: string
  year: number
  budget_percent: number
  start_date: string
  end_date: string
  status: string
  created_at?: string | null
}

export interface MeritAllocationRow {
  id: number
  cycle_id: number
  employee_id: number
  current_salary: number
  proposed_salary: number
  increase_percent: number
  status: string
  created_at?: string | null
}

/* ==================================================================== *
 * Forecasting workspace (PL-01..PL-06, AN-03..AN-06) — add-only.        *
 *                                                                      *
 * Shapes mirror backend/app/schemas/forecasting.py 1:1 (the served      *
 * code is the contract of record, L-017). All dates arrive as ISO       *
 * strings; MAPE arrives as a **fraction** (0.10 == 10 %) — format it    *
 * locally, never re-scale it before sending. Assumptions are stored    *
 * by the backend as a JSON string per row and re-validated on the way  *
 * out, so every assumption field is typed as list-or-string and must   *
 * go through `normaliseAssumptions` before use.                        *
 * ==================================================================== */

/** One value of a demand series: forecast/actual hours per date. */
export interface ForecastSeriesPoint {
  date: string
  value: number
}

/** One forecast result row (GET .../runs/{id}/results). */
export interface ForecastResultOut {
  horizon_step: number
  forecast_date: string
  predicted_value: number
  lower_bound?: number | null
  upper_bound?: number | null
  method_used?: string | null
  input_hash?: string | null
  rule_version?: string | null
  data_start_date?: string | null
  data_end_date?: string | null
  series_key?: string | null
}

/** GET/POST /forecasting/runs (ForecastRunOut). */
export interface ForecastRunOut {
  id: number
  name: string
  description?: string | null
  status: string
  horizon_days: number
  method: string
  data_start_date?: string | null
  data_end_date?: string | null
  backtest_mape?: number | null
  backtest_mase?: number | null
  backtest_holdout_days?: number | null
  created_at: string
  finished_at?: string | null
  results: ForecastResultOut[]
  location_id?: number | null
  role_id?: number | null
}

/** POST /forecasting/runs body (ForecastCreate). */
export interface ForecastRunCreateRequest {
  name?: string | null
  description?: string | null
  series_data: ForecastSeriesPoint[]
  horizon_days?: number
  method?: "seasonal_naive" | "holt_winters" | "auto"
  seasonality?: number
  series_selector?: string | null
  location_id?: number | null
  role_id?: number | null
}

/* ---- Demand layer ------------------------------------------------- */

/** One point of POST /forecasting/demand/series. */
export interface DemandSeriesPoint {
  date: string
  value: number
  actual_hours?: number | null
  leave_hours?: number | null
  scheduled_hours?: number | null
  location_id?: number | null
  role?: string | null
}

export interface DemandSeriesResponse {
  count: number
  series: DemandSeriesPoint[]
}

/** POST /forecasting/demand/series body (DemandSeriesRequest). */
export interface DemandSeriesQueryRequest {
  start_date: string
  end_date: string
  location_id?: number | null
  role?: string | null
  job_id?: number | null
  include_time_entries?: boolean
  include_leave?: boolean
  include_roster?: boolean
}

/** One point of the driver CSV validation (POST /forecasting/drivers[.|/import]). */
export interface DriverSeriesPoint {
  date: string
  value: number
  location_id?: number | null
  location_code?: string | null
  role?: string | null
}

export interface DriverCSVResponse {
  count: number
  series: DriverSeriesPoint[]
}

/* ---- Scenarios (AN-03 / AN-05) ------------------------------------- */

/** One named assumption. `value` is numeric except for `method_override`. */
export interface ScenarioAssumption {
  key: string
  value: number | string
  unit: string
  note?: string | null
}

/**
 * Assumptions as they can arrive on the wire: the ORM column is a JSON
 * string; the response models parse it, but defensive callers normalise.
 */
export type AssumptionsWire = ScenarioAssumption[] | string

export interface ScenarioOut {
  id: number
  name: string
  description?: string | null
  base_run_id: number
  assumptions: AssumptionsWire
  created_at: string
  created_by?: number | null
  version_no: number
  root_id?: number | null
  source: string
  forked_from_scenario_id?: number | null
  results: ForecastResultOut[]
}

/** GET /forecasting/scenarios (PaginatedScenarios). */
export interface PaginatedScenarios {
  items: ScenarioOut[]
  total: number
  page: number
  page_size: number
}

/** GET /forecasting/scenarios/{id}/versions (ScenarioVersionSummaryOut). */
export interface ScenarioVersionSummaryOut {
  id: number
  name: string
  description?: string | null
  base_run_id: number
  assumptions: AssumptionsWire
  version_no: number
  root_id?: number | null
  source: string
  forked_from_scenario_id?: number | null
  created_at: string
  created_by?: number | null
  results: ForecastResultOut[]
}

export interface ScenarioVersionList {
  items: ScenarioVersionSummaryOut[]
}

/** POST /forecasting/scenarios body (ScenarioCreate). */
export interface ScenarioCreateRequest {
  base_run_id: number
  name: string
  description?: string | null
  assumptions: ScenarioAssumption[]
}

/** POST /forecasting/scenarios/{id}/versions body (ScenarioEditCreate). */
export interface ScenarioEditRequest {
  assumptions: ScenarioAssumption[]
  name?: string | null
  description?: string | null
}

/** POST /forecasting/scenarios/{id}/fork body (ScenarioForkCreate). */
export interface ScenarioForkRequest {
  name?: string | null
  description?: string | null
}

/** POST /forecasting/scenarios/compare (ScenarioComparisonRequest). */
export interface ScenarioCompareRequest {
  scenario_ids: number[]
  hourly_costs?: Record<string, number> | null
}

/** One period row of a comparison: deltas are against the FIRST participant. */
export interface ComparisonPeriod {
  horizon_step: number
  forecast_date: string
  base_value?: number | null
  /** JSON object keys: the wire serialises the scenario-id keys as strings. */
  scenario_values: Record<string, number | null>
  deltas: Record<string, number | null>
  assumptions: Record<string, AssumptionsWire>
}

/** One cost line of a participant's cost projection. */
export interface ScenarioCostRowOut {
  period: string
  hours: number
  hourly_cost: number
  cost: number
  cost_basis: string
}

export interface ScenarioCostProjectionOut {
  scenario_id: number
  hourly_costs: Record<string, number>
  wage_growth_pct: number
  rows: ScenarioCostRowOut[]
  total_hours: number
  total_cost: number
  total_cost_delta?: number | null
  label: string
  cost_basis: string
}

/** POST /forecasting/scenarios/compare response (ScenarioComparison). */
export interface ScenarioComparison {
  scenarios: ScenarioOut[]
  comparison: ComparisonPeriod[]
  /** JSON object keys: string scenario ids. Present ONLY when rates were sent. */
  costs?: Record<string, ScenarioCostProjectionOut> | null
}

/* ---- Cost forecast (AN-04) ----------------------------------------- */

/** POST /forecasting/runs/{id}/cost-forecast body (CostForecastCreate). */
export interface CostForecastCreateRequest {
  hourly_costs: Record<string, number>
  start_date?: string | null
  end_date?: string | null
}

export interface CostForecastRowOut {
  period: string
  location_id?: number | null
  location_code?: string | null
  role_id?: number | null
  role?: string | null
  role_code?: string | null
  hours: number
  hourly_cost: number
  cost: number
}

export interface CostForecastVersionSummary {
  id: number
  forecast_run_id: number
  version: number
  label: string
  cost_basis: string
  hourly_costs: Record<string, number>
  input_hash: string
  start_date?: string | null
  end_date?: string | null
  periods: number
  total_hours: number
  total_cost: number
  created_at: string
}

export interface CostForecastVersionSummaryList {
  items: CostForecastVersionSummary[]
}

export interface CostForecastOut extends CostForecastVersionSummary {
  message?: string | null
  location_id?: number | null
  location_code?: string | null
  role_id?: number | null
  role?: string | null
  role_code?: string | null
  rows: CostForecastRowOut[]
}

/* ---- Accuracy (AN-06) ---------------------------------------------- */

export interface ForecastAccuracyRecordOut {
  id: number
  forecast_run_id: number
  model_version: string
  method_used: string
  period: string
  location_id?: number | null
  role_id?: number | null
  forecast_hours: number
  actual_hours: number
  /** A fraction (0.10 == 10 %), or null when every measured day was zero-actual. */
  mape?: number | null
  mae: number
  bias: number
  sample_size: number
  status: "ok" | "review" | "degraded"
  measured_at?: string | null
}

/** POST /forecasting/accuracy/sync body (ForecastAccuracySyncRequest). */
export interface ForecastAccuracySyncRequest {
  start_date: string
  end_date: string
  location_id?: number | null
  role_id?: number | null
  run_id?: number | null
  review_threshold?: number
  degraded_threshold?: number
}

export interface ForecastAccuracySyncResult {
  start_date: string
  end_date: string
  review_threshold: number
  degraded_threshold: number
  replaced: number
  records: ForecastAccuracyRecordOut[]
}

/** GET /forecasting/accuracy (PaginatedForecastAccuracy). */
export interface PaginatedForecastAccuracy {
  items: ForecastAccuracyRecordOut[]
  total: number
  page: number
  page_size: number
}

/* Learning (B1) */

export interface CourseRow {
  id: number
  title: string
  code: string
  description?: string | null
  category: string
  duration_hours: number
  is_mandatory: boolean
  is_active: boolean
  created_at?: string | null
}

export interface EnrollmentRow {
  id: number
  employee_id: number
  course_id: number
  status: string
  score?: number | null
  started_at?: string | null
  completed_at?: string | null
  created_at?: string | null
}

export interface CertificationRow {
  id: number
  employee_id: number
  name: string
  issuer?: string | null
  issued_date: string
  expiry_date?: string | null
  certificate_url?: string | null
  created_at?: string | null
}

export interface TalentPoolRow {
  id: number
  name: string
  description?: string | null
  created_at?: string | null
}

export interface TalentPoolMemberRow {
  id: number
  pool_id: number
  employee_id: number
  readiness: string
  notes?: string | null
  created_at?: string | null
}

export interface SuccessionPlanRow {
  id: number
  position_id: number
  primary_successor_id?: number | null
  backup_successor_id?: number | null
  readiness: string
  notes?: string | null
  created_at?: string | null
}

/* Benefits (B1) */

export interface BenefitPlanRow {
  id: number
  name: string
  code: string
  plan_type: string
  provider?: string | null
  employer_contribution: number
  employee_contribution: number
  is_active: boolean
  created_at?: string | null
}

export interface BenefitEnrollmentRow {
  id: number
  employee_id: number
  plan_id: number
  effective_date: string
  end_date?: string | null
  status: string
  created_at?: string | null
}

export interface LifeEventRow {
  id: number
  employee_id: number
  event_type: string
  event_date: string
  description?: string | null
  status: string
  created_at?: string | null
}

export interface LeaveOfAbsenceRow {
  id: number
  employee_id: number
  leave_type: string
  start_date: string
  end_date?: string | null
  status: string
  notes?: string | null
  approved_by?: number | null
  created_at?: string | null
}

/* Integrations (B3) — mirrors backend/app/schemas/integrations_platform.py + models */
export interface SSOConfigRow {
  id: number
  provider: string
  entity_id?: string | null
  sso_url?: string | null
  certificate?: string | null
  client_id_ext?: string | null
  client_secret?: string | null
  domain?: string | null
  is_active: boolean
  client_id?: number | null
  created_at?: string | null
  updated_at?: string | null
}

export interface WebhookRow {
  id: number
  url: string
  events: string
  secret?: string | null
  is_active: boolean
  client_id?: number | null
  last_triggered_at?: string | null
  created_at?: string | null
}

export interface WebhookDeliveryRow {
  id: number
  webhook_id: number
  event: string
  status: string
  response_code?: number | null
  attempts: number
  payload?: string | null
  created_at?: string | null
  attempted_at?: string | null
}

export interface BackgroundCheckRow {
  id: number
  candidate_id: number
  provider: string
  status: string
  result?: string | null
  completed_at?: string | null
  created_at?: string | null
}

export interface ESignatureRow {
  id: number
  document_type: string
  entity_id?: number | null
  signer_email: string
  signer_name?: string | null
  provider: string
  status: string
  provider_ref?: string | null
  signed_at?: string | null
  created_at?: string | null
}

/* Data quality (B3) — mirrors backend/app/services/data_quality.py Issue.as_dict() */
export interface DataQualityCheckRow {
  code: string
  severity?: string | null
  title?: string | null
}

export interface DataQualityIssueRow {
  code: string
  severity: string
  title: string
  entity_type: string
  entity_id?: number | null
  explanation: string
  source: string
  owner_role: string
  recommendation: string
  details: Record<string, unknown>
  message?: string
  status?: string
  check?: string
  entity?: string
}

export interface DataQualitySummary {
  total: number
  by_severity: Record<string, number>
  by_code: Record<string, number>
  checked_at: string
}

export interface DataQualityIssuesResponse {
  summary: DataQualitySummary
  returned: number
  truncated: boolean
  issues: DataQualityIssueRow[]
}

export interface DataQualityChecksResponse {
  checks: string[]
  severities: string[]
  note: string
}

export interface DataQualityScanResult {
  summary: DataQualitySummary
  scanned: boolean
}

/* ------------------------------------------------------------------ *
 * Onboarding Config (Presets & Readiness) — mirrors                  *
 * backend/app/schemas/onboarding.py PresetSummaryOut,               *
 * PresetDetailOut, PresetDifferenceOut, ReadinessOut               *
 * ------------------------------------------------------------------ */

export interface PresetSummary {
  id: string
  name: string
  industry?: string | null
  modules: string[]
  default_roles: Record<string, unknown>[]
  recommended_settings: Record<string, unknown>
  version: string
  status: string
  description: string
}

export interface PresetDetail extends PresetSummary {
  business_type: string
  created_at: string
  updated_at: string
  module_dependencies: Record<string, string[]>
  organisation_templates: Record<string, unknown>
  dashboards: Record<string, unknown>
  forecast_drivers: Record<string, unknown>
  import_templates: Record<string, unknown>[]
  validations: Record<string, unknown>[]
  exclusions: Record<string, unknown>[]
  configuration: Record<string, unknown>
  preset: Record<string, unknown>
}

export interface SettingChange {
  path: string
  module: string
  action: string
  preset_value?: unknown
  tenant_value?: unknown
  note: string
}

export interface ProvenanceRecord {
  path: string
  module: string
  state: string
  origin: string
  preset_value?: unknown
  tenant_value?: unknown
}

export interface PresetDifference {
  preset_id: string
  preset_version: string
  adds: SettingChange[]
  unchanged: SettingChange[]
  overwrites: SettingChange[]
  undecided: SettingChange[]
  tenant_only: SettingChange[]
  modules_to_enable: string[]
  modules_left_alone: string[]
  exclusions: Record<string, unknown>[]
  provenance: ProvenanceRecord[]
  generated_at: string
}

export interface ReadinessFinding {
  rule_id: string
  category: string
  severity: string
  message: string
  fix_target: string
  entity?: string | null
  module?: string | null
  auto_fixable: boolean
  // readiness report also carries these when serialised via as_dict
  code?: string
  title?: string
  status?: string
  recommendation?: string
}

export interface ReadinessReport {
  preset_id?: string | null
  preset_version?: string | null
  configured: ReadinessFinding[]
  missing: ReadinessFinding[]
  inconsistent: ReadinessFinding[]
  recommended: ReadinessFinding[]
  findings: ReadinessFinding[]
  generated_at: string
}

/* ------------------------------------------------------------------ *
 * Leave Ledger & Reconciliation — mirrors backend/app/schemas/leave.py *
 * LeaveLedgerEntryOut, LeaveReconciliationRow/Out,                  *
 * LeavePayrollInputOut                                               *
 * ------------------------------------------------------------------ */

export interface LeaveLedgerEntry {
  id: number
  balance_id: number
  employee_id: number
  leave_type_id: number
  entitlement_year: number
  entry_type: string
  signed_days: number
  reference_type?: string | null
  reference_id?: number | null
  description?: string | null
  created_at?: string | null
  running_balance: number
  source: string
}

export interface LeaveReconciliationRow {
  balance_id: number
  employee_id: number
  leave_type_id: number
  leave_type_name?: string | null
  entitlement_year: number
  cached_entitled_days: number
  cached_carried_over_days: number
  cached_used_days: number
  cached_available_days: number
  ledger_available_days: number
  difference_days: number
  ledger_entries: number
  state: string
}

export interface LeaveReconciliationSummary {
  balances: number
  in_sync: number
  out_of_sync: number
  no_ledger: number
  difference_days: number
}

export interface LeaveReconciliation {
  year?: number | null
  rows: LeaveReconciliationRow[]
  summary: LeaveReconciliationSummary
}

export interface LeavePayrollInputEntry {
  employee_id: number
  leave_type_id: number
  leave_type_code: string
  is_paid: boolean
  leave_request_id: number
  start_date: string
  end_date: string
  quantity_days: number
}

export interface LeavePayrollInput {
  period_start: string
  period_end: string
  entries: LeavePayrollInputEntry[]
  total_days: number
}

/* ESS Hub (completion) — mirrors backend/app/schemas/ess_hr.py */
export interface ESSProfileRow {
  id: number
  employee_id: number
  preferred_name?: string | null
  emergency_contact_name?: string | null
  emergency_contact_phone?: string | null
  emergency_contact_relation?: string | null
  bank_name?: string | null
  bank_account?: string | null
  bank_routing?: string | null
  tax_id?: string | null
  direct_deposit_enabled: boolean
  notification_email?: boolean | null
  notification_sms?: boolean | null
  notification_push?: boolean | null
  language: string
  theme_preference: string
  created_at?: string | null
  updated_at?: string | null
}

export interface NotificationRow {
  id: number
  recipient_id: number
  title: string
  message: string
  notification_type: string
  category: string
  entity_type?: string | null
  entity_id?: number | null
  is_read: boolean
  read_at?: string | null
  email_sent?: boolean | null
  created_at?: string | null
}

export interface EmployeeFileRow {
  id: number
  employee_id: number
  document_type: string
  file_name: string
  storage_url: string
  status: string
  expiry_date?: string | null
  uploaded_by?: string | null
  notes?: string | null
  version?: number | null
  created_at?: string | null
}

export interface AnnouncementRow {
  id: number
  title: string
  content: string
  category: string
  priority: string
  target_audience: string
  target_value?: string | null
  published: boolean
  published_at?: string | null
  expires_at?: string | null
  created_by?: number | null
  created_at?: string | null
}

export interface DirectoryEntryRow {
  id: number
  employee_id: number
  full_name: string
  email: string
  department?: string | null
  job_title?: string | null
  location?: string | null
  phone?: string | null
  avatar_url?: string | null
  is_active: boolean
}

export interface OrgNodeRow {
  employee_id: number
  manager_id?: number | null
  depth: number
  path?: string | null
}

export interface GoalAlignmentRow {
  id: number
  goal_id: number
  parent_goal_id?: number | null
  created_at?: string | null
}

export interface ContinuousFeedbackRow {
  id: number
  from_employee_id: number
  to_employee_id: number
  feedback_type: string
  message: string
  is_private: boolean
  created_at?: string | null
}

export interface ComplianceCheckRow {
  id: number
  rule_id: number
  run_at?: string | null
  passed: boolean
  details?: string | null
}

/* User admin (B3) — mirrors backend/app/schemas/user.py UserOut */
export interface AdminUserRow {
  id: number
  username: string
  email: string
  role: string
  is_active: boolean
  must_change_password?: boolean
  created_at?: string | null
  password_changed_at?: string | null
  is_locked?: boolean
  mfa_enabled?: boolean
}
