import axios from "axios"
import { getTenantSlug } from "@/lib/tenantSlugStore"
import type {
  PayrollPeriodRow,
  PayComponentRow,
  PayProfileRow,
  PayRunRow,
  PaySlipRow,
  PayRunReconciliation,
} from "@/types"

export interface ApiErrorBody {
  code: string
  category: string
  message: string
  retryable: boolean
  details?: Record<string, unknown>
  request_id?: string
}

const baseURL = import.meta.env.VITE_API_URL || "/api/v1"

export interface EmployeeOut {
  id: number
  employee_id: string
  first_name: string
  last_name: string
  email: string
  department_id?: number | null
  department_name?: string | null
  job_title?: string | null
  manager_id?: number | null
  manager_name?: string | null
  status: string
  hire_date?: string | null
}

export interface EmployeePage { items: EmployeeOut[]; total: number; page: number; page_size: number; total_pages: number }

const api = axios.create({
  baseURL,
  headers: {
    "Content-Type": "application/json",
  },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("karmathy_token")
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  // Skip tenant header on public/auth routes (e.g. login) where no
  // tenant context has been established yet.
  const isPublicAuth = config.url && /^\/auth\/(login|password|mfa)/.test(config.url)
  const slug = getTenantSlug()
  if (slug && !isPublicAuth) {
    config.headers["X-Tenant-Slug"] = slug
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const data = error?.response?.data
    if (data && typeof data === "object") {
      if (data.error && typeof data.error === "object") {
        data.detail = data.error.message
        error.apiError = data.error as ApiErrorBody
        // Retry-After tells the UI whether offering "Retry" makes sense.
        const retryAfter = error?.response?.headers?.["retry-after"]
        if (retryAfter && !error.apiError.retryable) {
          error.apiError.retryable = true
        }
        // The account must replace an administrator-set password before it
        // can use the API. Every other call is refused by the server, so
        // send the user to the one screen that can help. A full navigation
        // is deliberate: it discards the in-memory session state.
        if (error.apiError.code === "password_change_required") {
          localStorage.setItem("karmathy_must_change_password", "1")
          if (!window.location.pathname.startsWith("/change-password")) {
            window.location.assign("/change-password")
          }
        }
      } else if (Array.isArray(data.detail)) {
        // Preserve raw array for fieldErrors() before collapsing to string.
        ;(error as any).validationDetail = data.detail
        // FastAPI validation errors: surface the first field message.
        const first = data.detail[0]
        if (first) {
          const loc = Array.isArray(first.loc) ? first.loc.slice(1).join(".") : ""
          data.detail = loc ? `${loc}: ${first.msg}` : first.msg
        }
      }
    }
    return Promise.reject(error)
  }
)

/** Read a user-safe message from any thrown axios error. */
export function errorMessage(err: unknown, fallback = "Something went wrong"): string {
  const e = err as {
    response?: { data?: { detail?: unknown; error?: { message?: string } } }
    apiError?: ApiErrorBody
  }
  // Network failure (!response) is a distinct branch — callers must not show
  // "Something went wrong" for it. Keep the message truthful; RetryableAlert
  // will render the "Check your connection" hint on !response.
  const detail = e?.response?.data?.detail
  if (typeof detail === "string" && detail) return detail
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { loc?: unknown[]; msg?: string }
    if (first?.msg) {
      const loc = Array.isArray(first.loc) ? (first.loc as unknown[]).slice(1).join(".") : ""
      return loc ? `${loc}: ${first.msg}` : first.msg
    }
  }
  const msg = e?.response?.data?.error?.message
  if (typeof msg === "string" && msg) return msg
  // Also surface apiError message if response unwrap differs
  const apiMsg = e?.apiError?.message
  if (typeof apiMsg === "string" && apiMsg) return apiMsg
  // Fallback to detail string from validationDetail if present
  const vd = (e as unknown as { validationDetail?: unknown[] })?.validationDetail
  if (Array.isArray(vd) && vd.length > 0) {
    const first = vd[0] as { loc?: unknown[]; msg?: string }
    if (first?.msg) {
      const loc = Array.isArray(first.loc) ? (first.loc as unknown[]).slice(1).join(".") : ""
      return loc ? `${loc}: ${first.msg}` : first.msg
    }
  }
  return fallback
}

/** Whether the caller should be offered a retry button. */
export function isRetryable(err: unknown): boolean {
  const e = err as { apiError?: ApiErrorBody; response?: { status?: number }; message?: string }
  if (e?.apiError?.retryable) return true
  if (!e?.response) return !!e?.message
  const status = e.response.status
  return status === 429 || (status !== undefined && status >= 500)
}

/** The correlation id, for quoting to support. */
export function requestId(err: unknown): string | undefined {
  return (err as { apiError?: ApiErrorBody })?.apiError?.request_id
}

/** Whether this error is the 409 pending"+"_"+"verification gate. */
export function isPendingVerification(err: unknown): boolean {
  const e = err as {
    apiError?: ApiErrorBody
    response?: { status?: number; data?: { error?: { code?: string }; code?: string; detail?: unknown } }
  }
  const status = e?.response?.status
  if (status !== 409) return false
  const code =
    e?.apiError?.code ||
    e?.response?.data?.error?.code ||
    (e?.response?.data as unknown as { code?: string })?.code ||
    ""
  return code === "rule_pack_not_verified"
}

/**
 * Parse a FastAPI 422 validation detail array into a field → message map.
 * loc is sliced from index 1 (dropping "body"/"query") to yield the field name.
 * Also handles the `details` Record shape if the backend returned a map.
 */
export function fieldErrors(err: unknown): Map<string, string> {
  const out = new Map<string, string>()
  const e = err as {
    response?: { data?: { detail?: unknown; error?: { details?: unknown } }; status?: number }
    validationDetail?: unknown[]
    apiError?: ApiErrorBody
  }
  // 1) FastAPI detail array (either still on response.data.detail or preserved)
  const rawDetail =
    (e?.validationDetail as unknown[]) ??
    (Array.isArray(e?.response?.data?.detail) ? (e.response.data.detail as unknown[]) : null)
  if (Array.isArray(rawDetail)) {
    for (const item of rawDetail as Array<{ loc?: unknown[]; msg?: string }>) {
      if (!item || typeof item.msg !== "string") continue
      const loc = Array.isArray(item.loc) ? (item.loc as unknown[]).slice(1) : []
      // Join loc parts with "."; if empty, use "_global" as key for form-level fallback
      const key = loc.length > 0 ? loc.map(String).join(".") : "_global"
      if (!out.has(key)) out.set(key, item.msg)
    }
    if (out.size > 0) return out
  }
  // 2) apiError.details Record<string,unknown> where value is string message
  const details = (e?.apiError?.details ?? (e?.response?.data?.error as unknown as { details?: unknown })?.details) as
    | Record<string, unknown>
    | undefined
  if (details && typeof details === "object" && !Array.isArray(details)) {
    for (const [k, v] of Object.entries(details)) {
      if (typeof v === "string" && v) out.set(k, v)
      else if (Array.isArray(v) && typeof v[0] === "string") out.set(k, v[0] as string)
    }
  }
  return out
}

/** Alias for consumers that import `fieldErrorsFromError`. */
export const fieldErrorsFromError = fieldErrors

/** Read the raw details Record if present (for debugging, not for rendering rates). */
export function errorDetails(err: unknown): Record<string, unknown> | undefined {
  const e = err as { apiError?: ApiErrorBody; response?: { data?: { error?: { details?: unknown } } } }
  const d = e?.apiError?.details ?? (e?.response?.data?.error as unknown as { details?: unknown })?.details
  if (d && typeof d === "object" && !Array.isArray(d)) return d as Record<string, unknown>
  return undefined
}

/**
 * Global helper: shape a load-failure message for the response status.
 * Was in pages/forecasting/shared.tsx; now global so every page reuses it.
 */
export function readableLoadError(err: unknown, fallback: string): string {
  const status = (err as { response?: { status?: number } })?.response?.status
  const msg = errorMessage(err, fallback)
  if (!err || !(err as { response?: unknown })?.response) {
    return "We can't reach the server right now. Check your connection and try again."
  }
  if (status === 403) {
    return `${msg} — forecasting is served to SuperAdmin, HR and Manager roles only, so the most likely cause is the signed-in role.`
  }
  if (status === 404) {
    return `${msg} — the record may have been removed; reload to refresh.`
  }
  if (status === 422) {
    return `${msg} (the server rejected the request details; check the values and retry).`
  }
  return msg
}

export interface ClientOut { id: number; slug: string; name: string; status: string; /* ... */ }

export interface FeatureFlagOut {
  id: number
  client_id: number
  key: string
  name: string
  description?: string | null
  enabled: boolean
  config?: string | null
}

/** Read employees from /employees endpoint */
export async function listEmployees(params?: Record<string, any>): Promise<EmployeeOut[]> {
  const { data } = await api.get<EmployeePage>("/employees", { params })
  return (data as any).items ?? data ?? []
}

/** Rebuild org chart from employee master data */
export async function rebuildOrgChart(): Promise<{ nodes: number }> {
  const { data } = await api.post<{ nodes: number }>("/ess/org-chart/rebuild")
  return data
}

/** Client list */
export async function listClients(): Promise<ClientOut[]> {
  const { data } = await api.get<ClientOut[]>("/onboarding-portal/clients")
  return data
}

/** Resolve the current tenant's slug to its integer client ID.
 * Required because admin endpoints use /onboarding-portal/clients/{id}/...
 * (integer), not /clients/{slug}/... (string). Case-insensitive. */
export async function getClientIdBySlug(): Promise<number | null> {
  const slug = getTenantSlug()
  if (!slug) return null
  try {
    const { data } = await api.get<ClientOut[]>("/onboarding-portal/clients")
    const lower = slug.toLowerCase()
    const match = (data ?? []).find(c => c.slug.toLowerCase() === lower)
    return match?.id ?? null
  } catch {
    return null
  }
}

/** Lookup a client by slug (returns full client including numeric id) */
export async function getClientBySlug(slug: string): Promise<ClientOut | null> {
  const clients = await listClients()
  const lower = slug.toLowerCase()
  return clients.find((c) => c.slug.toLowerCase() === lower) ?? null
}

/** Feature flags for a client */
export async function listFeatureFlags(clientId: number): Promise<FeatureFlagOut[]> {
  const { data } = await api.get<FeatureFlagOut[]>(`/onboarding-portal/clients/${clientId}/feature-flags`)
  return data
}

/** Update a feature flag (enabled and/or config) — backend upserts if missing */
export async function updateFeatureFlag(
  clientId: number,
  key: string,
  payload: boolean | { enabled?: boolean; config?: string },
): Promise<FeatureFlagOut> {
  // Back-compat: allow boolean shorthand
  const body: Record<string, unknown> = typeof payload === "boolean" ? { enabled: payload } : payload
  const { data } = await api.put<FeatureFlagOut>(`/onboarding-portal/clients/${clientId}/feature-flags/${key}`, body)
  return data
}
// Overload support for legacy boolean call: updateFeatureFlag(id, key, true)
export async function updateFeatureFlagLegacy(clientId: number, key: string, enabled: boolean): Promise<FeatureFlagOut> {
  return updateFeatureFlag(clientId, key, { enabled })
}

/** Impersonation: SuperAdmin sudo view-as */
export interface ImpersonateResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: { id: number; username: string; email: string; role: string; is_active: boolean }
  impersonated_by: { id: number; username: string; email: string; role: string }
}
export async function impersonateUser(targetUserId: number): Promise<ImpersonateResponse> {
  const { data } = await api.post<ImpersonateResponse>("/auth/impersonate", { target_user_id: targetUserId })
  return data
}
export async function impersonateUserByUsername(targetUsername: string): Promise<ImpersonateResponse> {
  const { data } = await api.post<ImpersonateResponse>("/auth/impersonate", { target_username: targetUsername })
  return data
}

export async function getFnf(runId: number, employeeId: number, noticeDays?: number | string) {
  const params: Record<string, string> = { employee_id: String(employeeId) }
  if (noticeDays !== undefined && noticeDays !== null && String(noticeDays).trim() !== "") {
    const n = Number(noticeDays)
    params.notice_days = Number.isFinite(n) ? String(Math.max(0, n)) : "0"
  }
  const { data } = await api.get(`/payroll/runs/${runId}/fnf`, { params })
  return data
}

export async function postFnf(runId: number, employeeId: number, noticeDays?: number | string) {
  const params: Record<string, string> = { employee_id: String(employeeId) }
  if (noticeDays !== undefined && noticeDays !== null && String(noticeDays).trim() !== "") {
    const n = Number(noticeDays)
    params.notice_days = Number.isFinite(n) ? String(Math.max(0, n)) : "0"
  } else {
    params.notice_days = "0"
  }
  const { data } = await api.post(`/payroll/runs/${runId}/fnf`, null, { params })
  return data
}

export async function previewPayRun(runId: number) {
  const { data } = await api.post(`/payroll/runs/${runId}/process`, null, { params: { dry_run: true } })
  return data
}

export async function getPayRunHistory(runId: number) {
  const { data } = await api.get(`/payroll/runs/${runId}/history`)
  return data
}

export async function getFiling(
  filingType: string,
  params: { jurisdiction?: string; period: string; state?: string },
  opts?: { responseType?: "text" | "blob" },
) {
  const q: Record<string, string> = { jurisdiction: params.jurisdiction || "IN", period: params.period }
  if (params.state) q.state = params.state
  const responseType = opts?.responseType || "text"
  const { data, headers } = await api.get(`/reports/filings/${filingType}`, {
    params: q,
    responseType: responseType as any,
  })
  return { data, headers } as { data: any; headers: Record<string, string> }
}

/** Interviews — live recruiting CRUD (backend/app/api/v1/endpoints/interviews.py).
 * R2 honesty-sweep: replaces the former feature-flags/interview_type shim. */
export interface InterviewOut {
  id: number
  candidate_id: number
  requisition_id?: number | null
  stage: string
  scheduled_at?: string | null
  interviewers: string[]
  status: string
  feedback?: string | null
  created_at?: string | null
}

export interface InterviewCreate {
  candidate_id: number
  requisition_id?: number | null
  stage?: string
  scheduled_at?: string | null
  interviewers?: string[]
}

export interface InterviewUpdate {
  stage?: string
  scheduled_at?: string | null
  interviewers?: string[]
  status?: string
  feedback?: string | null
}

/** List interviews from GET /api/v1/interviews */
export async function listInterviews(params?: {
  candidate_id?: number
  requisition_id?: number
  status?: string
  skip?: number
  limit?: number
}): Promise<InterviewOut[]> {
  const { data } = await api.get<InterviewOut[]>("/interviews", { params })
  return data ?? []
}

/** Schedule an interview via POST /api/v1/interviews */
export async function createInterview(payload: InterviewCreate): Promise<InterviewOut> {
  const { data } = await api.post<InterviewOut>("/interviews", payload)
  return data
}

/** Reschedule / restage / record outcome via PUT /api/v1/interviews/{id} */
export async function updateInterview(id: number, payload: InterviewUpdate): Promise<InterviewOut> {
  const { data } = await api.put<InterviewOut>(`/interviews/${id}`, payload)
  return data
}

export default api

// Base URL for backend-served files (offer letters, uploads).
const filesBase = (import.meta.env.VITE_API_URL || "/api/v1").replace(/\/api\/v1\/?$/, "")
export const fileUrl = (path: string) =>
  path.startsWith("http") ? path : `${filesBase}${path}`