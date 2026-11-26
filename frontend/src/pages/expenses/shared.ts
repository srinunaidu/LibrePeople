/* LP-EXP-001/002/003 — expenses UI (list/detail/create + L1/L2 approve + mark-paid + receipts).
 * Reads the real /expenses/* API (backend/app/api/v1/endpoints/expenses.py).
 * No fabricated claims; the server is the source of truth (refetch after
 * every mutation). No CSV/PDF/payroll-export — out of scope by contract.
 */

export interface ExpenseClaim {
  id: number
  employee_id: number
  category_id: number
  expense_date: string
  amount: number
  currency: string
  description?: string | null
  status: string
  payment_status: string
  rejection_reason?: string | null
}

export interface ExpenseCategory {
  id: number
  code: string
  name: string
  description?: string | null
  is_active: boolean
}

export interface ExpenseReceipt {
  id: number
  claim_id: number
  file_name: string
  content_type: string
  size_bytes: number
  download_url: string
  uploaded_at?: string | null
}

export interface ExpenseCreateBody {
  employee_id: number
  category_id: number
  expense_date: string
  amount: number
  currency: string
  description?: string
}

/** Mirrors backend MANAGER_ROLES (deps.py): SuperAdmin, HR, Manager. */
export const MANAGER_ROLES = ["SuperAdmin", "HR", "Manager"] as const
/** Mirrors backend ADMIN_ROLES (deps.py): SuperAdmin, HR. */
export const ADMIN_ROLES = ["SuperAdmin", "HR"] as const

export function isManagerRole(role?: string | null): boolean {
  return role !== undefined && role !== null && (MANAGER_ROLES as readonly string[]).includes(role)
}

export function isAdminRole(role?: string | null): boolean {
  return role !== undefined && role !== null && (ADMIN_ROLES as readonly string[]).includes(role)
}

/** L1 approve is Manager+ on SUBMITTED claims only (expenses.py:398-416). */
export function canL1Approve(role: string | undefined | null, status: string): boolean {
  return isManagerRole(role) && status === "SUBMITTED"
}

/** Final approve is HR/Admin on L1_APPROVED claims only (:419-437). */
export function canFinalApprove(role: string | undefined | null, status: string): boolean {
  return isAdminRole(role) && status === "L1_APPROVED"
}

/** Mark-paid needs APPROVED + UNPAID, else the 409 expense_invalid_payment_state (:483-520). */
export function canMarkPaid(
  role: string | undefined | null,
  status: string,
  paymentStatus: string,
): boolean {
  return isAdminRole(role) && status === "APPROVED" && paymentStatus === "UNPAID"
}

/** Reject is Manager+ on the two middle states (:439-460). */
export function canReject(role: string | undefined | null, status: string): boolean {
  return isManagerRole(role) && (status === "SUBMITTED" || status === "L1_APPROVED")
}

export function canSubmit(status: string): boolean {
  return status === "DRAFT"
}

export function canRework(status: string): boolean {
  return status === "REJECTED"
}

/** Receipts attach only while the claim is still being put together (:541-556). */
export function canUploadReceipt(status: string): boolean {
  return status === "DRAFT" || status === "SUBMITTED"
}

/** Associate clicks are never sent — approve/pay buttons stay hidden. */
export function showApproveActions(role: string | undefined | null): boolean {
  return isManagerRole(role)
}

export const CLAIM_STATUS_FILTERS = ["DRAFT", "SUBMITTED", "L1_APPROVED", "APPROVED", "REJECTED"] as const

export function statusLabel(status: string): string {
  switch (status) {
    case "DRAFT":
      return "Draft"
    case "SUBMITTED":
      return "Submitted"
    case "L1_APPROVED":
      return "L1 approved"
    case "APPROVED":
      return "Approved"
    case "REJECTED":
      return "Rejected"
    default:
      return status
  }
}
