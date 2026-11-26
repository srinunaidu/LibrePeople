/**
 * Employee Self-Service hub — profile, files, notifications, directory and org chart.
 * Phase 3: high-density token-driven cards (obsidian surfaces var(--surface), hairline var(--border), violet var(--accent), compact 12-16px, radius var(--radius-md), tabular-nums).
 *
 * Mirrors PayrollSetup.tsx / PerformanceHub.tsx structure:
 * - PageHeader + Alert + SectionCard + TableSkeleton + EmptyState + StatusPill
 * - Independent reads via Promise.allSettled — one 403 must not blank others
 * - Role gates mirror backend/app/api/deps.py and backend/app/api/v1/endpoints/ess_hr.py:
 *   ADMIN_ROLES     = SuperAdmin, HR
 *   MANAGER_ROLES   = SuperAdmin, HR, Manager
 *   WORKFORCE_ROLES = SuperAdmin, HR, Manager, Associate
 *   ALL_ROLES       = SuperAdmin, HR, Manager, Associate, PayrollViewer
 *   - profile GET/POST/PUT                 : WORKFORCE
 *   - notifications GET + PUT read         : WORKFORCE, POST : ADMIN
 *   - employee-files GET                   : WORKFORCE, POST : ADMIN
 *   - directory GET                        : WORKFORCE, POST sync : ADMIN
 *   - org-chart GET                        : WORKFORCE, POST rebuild : ADMIN
 *   - goal-alignments GET                  : WORKFORCE, POST : MANAGER
 *   - continuous-feedback GET/POST         : WORKFORCE
 *   - announcements GET                    : ALL_ROLES, POST/PUT publish : ADMIN
 *   - compliance-checks GET + POST run     : ADMIN
 *
 * Note: the profile routes are declared in ess_hr.py as "/ess/profile/..."
 * inside a router already mounted at "/ess", so the live path is
 * "/ess/ess/profile/...". See security_test_suite.py expectation.
 */

import { useCallback, useEffect, useState, type FormEvent } from "react"
import { Layout } from "@/components/Layout"
import {Alert, EmptyState, LoadingRegion, PageHeader, SectionCard, Table, TableSkeleton, RetryableAlert} from "@/components/ui"
import { Button } from "@/components/ui/button"
import { Checkbox, Input, Select, Textarea } from "@/components/ui/inputs"
import { StatusPill } from "@/components/ui/status-pill"
import { Field } from "@/components/ui/layout"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import { formatDate, formatDateTime } from "@/lib/format"
import api, { errorMessage } from "@/lib/api"
import { fetchAllEmployees } from "@/lib/employees"
import type {
  AnnouncementRow,
  ComplianceCheckRow,
  ContinuousFeedbackRow,
  DirectoryEntryRow,
  Employee,
  EmployeeFileRow,
  ESSProfileRow,
  GoalAlignmentRow,
  LeaveBalance,
  LeaveRequest,
  LeaveType,
  NotificationRow,
  OrgNodeRow,
  PaySlipRow,
} from "@/types"

const WORKFORCE_ROLES = ["SuperAdmin", "HR", "Manager", "Associate"] as const
const MANAGER_ROLES = ["SuperAdmin", "HR", "Manager"] as const
const ADMIN_ROLES = ["SuperAdmin", "HR"] as const
// ALL_ROLES includes PayrollViewer for announcements
const ALL_ROLES = ["SuperAdmin", "HR", "Manager", "Associate", "PayrollViewer"] as const

// The live profile prefix includes the duplicated "/ess" from the router file.
const PROFILE_BASE = "/ess/ess/profile"

export default function ESSHub() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const localeOpts = { locale: tenant?.locale, timeZone: tenant?.timezone }
  // Dates render in the tenant locale/timezone via format.ts —
  // never the browser default.
  const fmtDate = (value?: string | null) => formatDate(value, localeOpts)
  const fmtDateTime = (value?: string | null) => formatDateTime(value, localeOpts)
  const role = user?.role ?? ""
  const canWorkforce = (WORKFORCE_ROLES as readonly string[]).includes(role)
  const canManager = (MANAGER_ROLES as readonly string[]).includes(role)
  const canAdmin = (ADMIN_ROLES as readonly string[]).includes(role)
  const canAll = (ALL_ROLES as readonly string[]).includes(role)

  const [employees, setEmployees] = useState<Employee[]>([])
  const [loading, setLoading] = useState(true)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [notice, setNotice] = useState("")
  const [formErrors, setFormErrors] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState<string>("")

  // Profile
  const [profile, setProfile] = useState<ESSProfileRow | null>(null)
  const [profileNotFound, setProfileNotFound] = useState(false)
  const [profileEmployeeId, setProfileEmployeeId] = useState<string>("")
  const [profileForm, setProfileForm] = useState({
    preferred_name: "",
    emergency_contact_name: "",
    emergency_contact_phone: "",
    emergency_contact_relation: "",
    bank_name: "",
    bank_account: "",
    bank_routing: "",
    tax_id: "",
    direct_deposit_enabled: false,
    notification_email: true,
    notification_sms: false,
    notification_push: true,
    language: "en",
    theme_preference: "light",
  })

  // Notifications
  const [notifications, setNotifications] = useState<NotificationRow[]>([])
  const [notifRecipientId, setNotifRecipientId] = useState<string>("")
  const [notifUnreadOnly, setNotifUnreadOnly] = useState(false)
  const [notifForm, setNotifForm] = useState({
    recipient_id: "",
    title: "",
    message: "",
    notification_type: "info",
    category: "system",
    entity_type: "",
    entity_id: "",
  })

  // Files
  const [files, setFiles] = useState<EmployeeFileRow[]>([])
  const [fileForm, setFileForm] = useState({
    employee_id: "",
    document_type: "",
    file_name: "",
    storage_url: "",
    status: "Active",
    expiry_date: "",
    notes: "",
  })

  // Directory
  const [directory, setDirectory] = useState<DirectoryEntryRow[]>([])
  const [dirQuery, setDirQuery] = useState("")
  const [dirDepartment, setDirDepartment] = useState("")

  // Org chart
  const [orgNodes, setOrgNodes] = useState<OrgNodeRow[]>([])

  // Goal alignments
  const [goalAlignments, setGoalAlignments] = useState<GoalAlignmentRow[]>([])
  const [goalAlignForm, setGoalAlignForm] = useState({ goal_id: "", parent_goal_id: "" })

  // Continuous feedback
  const [continuousFeedback, setContinuousFeedback] = useState<ContinuousFeedbackRow[]>([])
  const [cfForm, setCfForm] = useState({
    from_employee_id: "",
    to_employee_id: "",
    feedback_type: "Praise",
    message: "",
    is_private: false,
  })

  // Announcements
  const [announcements, setAnnouncements] = useState<AnnouncementRow[]>([])
  const [annPublishedOnly, setAnnPublishedOnly] = useState(false)
  const [annForm, setAnnForm] = useState({
    title: "",
    content: "",
    category: "General",
    priority: "Normal",
    target_audience: "All",
    target_value: "",
    published: false,
    expires_at: "",
  })

  // Compliance
  const [complianceChecks, setComplianceChecks] = useState<ComplianceCheckRow[]>([])

  // Payslips
  const [payslips, setPayslips] = useState<PaySlipRow[]>([])

  // Leave
  const [leaveTypes, setLeaveTypes] = useState<LeaveType[]>([])
  const [leaveBalances, setLeaveBalances] = useState<LeaveBalance[]>([])
  const [leaveRequests, setLeaveRequests] = useState<LeaveRequest[]>([])
  const [leaveForm, setLeaveForm] = useState({
    leave_type_id: "",
    start_date: "",
    end_date: "",
    reason: "",
  })

  const employeeName = (id: number) => {
    const e = employees.find((r) => r.id === id)
    return e ? `${e.first_name} ${e.last_name}` : `Employee #${id}`
  }

  const load = useCallback(async () => {
    setLoading(true)
    setErrors({})
    const next: Record<string, string> = {}

    // Determine my employee id from already-loaded employees or fetch fresh.
    // We fetch employees first so profile can be resolved.
    let empItems: Employee[] = employees
    let empFetchError = ""
    try {
      const empRes = await fetchAllEmployees()
      empItems = empRes.items
      setEmployees(empItems)
    } catch (err) {
      empFetchError = errorMessage(err, "The employees could not be read.")
      setEmployees([])
      empItems = []
      // not a section error — auxiliary
      void empFetchError
    }

    const myEmployeeId =
      profileEmployeeId
        ? Number(profileEmployeeId)
        : (() => {
            const byEmail = empItems.find((e) => e.email === user?.email)
            return byEmail?.id ?? empItems[0]?.id ?? 0
          })()

    // Build promises — role-gated, independent via allSettled
    const profileP = canWorkforce && myEmployeeId
      ? api.get<ESSProfileRow>(`${PROFILE_BASE}/${myEmployeeId}`)
      : Promise.resolve(null as unknown as { data: ESSProfileRow })

    const notifParams: Record<string, unknown> = {}
    if (notifRecipientId) notifParams.recipient_id = Number(notifRecipientId)
    if (notifUnreadOnly) notifParams.unread_only = true
    const notificationsP = canWorkforce
      ? api.get<NotificationRow[]>("/ess/notifications", { params: notifParams })
      : Promise.resolve({ data: [] as NotificationRow[] } as unknown as { data: NotificationRow[] })

    const filesP = canWorkforce
      ? api.get<EmployeeFileRow[]>("/ess/employee-files")
      : Promise.resolve({ data: [] as EmployeeFileRow[] } as unknown as { data: EmployeeFileRow[] })

    const dirParams: Record<string, unknown> = {}
    if (dirQuery.trim()) dirParams.q = dirQuery.trim()
    if (dirDepartment.trim()) dirParams.department = dirDepartment.trim()
    const directoryP = canWorkforce
      ? api.get<DirectoryEntryRow[]>("/ess/directory", { params: dirParams })
      : Promise.resolve({ data: [] as DirectoryEntryRow[] } as unknown as { data: DirectoryEntryRow[] })

    const orgP = canWorkforce
      ? api.get<OrgNodeRow[]>("/ess/org-chart")
      : Promise.resolve({ data: [] as OrgNodeRow[] } as unknown as { data: OrgNodeRow[] })

    const goalAlignP = canWorkforce
      ? api.get<GoalAlignmentRow[]>("/ess/goal-alignments")
      : Promise.resolve({ data: [] as GoalAlignmentRow[] } as unknown as { data: GoalAlignmentRow[] })

    const cfP = canWorkforce
      ? api.get<ContinuousFeedbackRow[]>("/ess/continuous-feedback")
      : Promise.resolve({ data: [] as ContinuousFeedbackRow[] } as unknown as { data: ContinuousFeedbackRow[] })

    const annParams: Record<string, unknown> = {}
    if (annPublishedOnly) annParams.published_only = true
    const announcementsP = canAll
      ? api.get<AnnouncementRow[]>("/ess/announcements", { params: annParams })
      : Promise.resolve({ data: [] as AnnouncementRow[] } as unknown as { data: AnnouncementRow[] })

    const complianceP = canAdmin
      ? api.get<ComplianceCheckRow[]>("/ess/compliance-checks")
      : Promise.resolve({ data: [] as ComplianceCheckRow[] } as unknown as { data: ComplianceCheckRow[] })

    const year = new Date().getFullYear()
    const payslipsP = canWorkforce && myEmployeeId
      ? api.get<PaySlipRow[]>("/payroll/payslips", { params: { employee_id: myEmployeeId } })
      : Promise.resolve({ data: [] as PaySlipRow[] } as unknown as { data: PaySlipRow[] })

    const leaveTypesP = canWorkforce
      ? api.get<LeaveType[]>("/leave/types")
      : Promise.resolve({ data: [] as LeaveType[] } as unknown as { data: LeaveType[] })

    const balancesP = canWorkforce && myEmployeeId
      ? api.get<LeaveBalance[]>("/leave/balances", { params: { employee_id: myEmployeeId, year } })
      : Promise.resolve({ data: [] as LeaveBalance[] } as unknown as { data: LeaveBalance[] })

    const requestsP = canWorkforce && myEmployeeId
      ? api.get<LeaveRequest[]>("/leave/requests", { params: { employee_id: myEmployeeId } })
      : Promise.resolve({ data: [] as LeaveRequest[] } as unknown as { data: LeaveRequest[] })

    const [profileR, notifR, filesR, dirR, orgR, goalAlignR, cfR, annR, compR, payR, ltR, balR, reqR] = await Promise.allSettled([
      profileP,
      notificationsP,
      filesP,
      directoryP,
      orgP,
      goalAlignP,
      cfP,
      announcementsP,
      complianceP,
      payslipsP,
      leaveTypesP,
      balancesP,
      requestsP,
    ])

    if (payR.status === "fulfilled") {
      setPayslips((payR.value as unknown as { data: PaySlipRow[] }).data ?? [])
    } else if (canWorkforce && myEmployeeId) {
      setPayslips([])
      next.payslips = errorMessage(payR.reason, "The payslips could not be read.")
    }

    if (ltR.status === "fulfilled") {
      setLeaveTypes((ltR.value as unknown as { data: LeaveType[] }).data ?? [])
    } else if (canWorkforce) {
      setLeaveTypes([])
      next.leaveTypes = errorMessage(ltR.reason, "The leave types could not be read.")
    }

    if (balR.status === "fulfilled") {
      setLeaveBalances((balR.value as unknown as { data: LeaveBalance[] }).data ?? [])
    } else if (canWorkforce && myEmployeeId) {
      setLeaveBalances([])
      next.leaveBalances = errorMessage(balR.reason, "The leave balances could not be read.")
    }

    if (reqR.status === "fulfilled") {
      setLeaveRequests((reqR.value as unknown as { data: LeaveRequest[] }).data ?? [])
    } else if (canWorkforce && myEmployeeId) {
      setLeaveRequests([])
      next.leaveRequests = errorMessage(reqR.reason, "The leave requests could not be read.")
    }

    if (profileR.status === "fulfilled") {
      const v = profileR.value as unknown as { data: ESSProfileRow } | null
      if (v && (v as { data: ESSProfileRow }).data) {
        const data = (v as { data: ESSProfileRow }).data
        setProfile(data)
        setProfileNotFound(false)
        setProfileEmployeeId(String(data.employee_id))
        setProfileForm({
          preferred_name: data.preferred_name ?? "",
          emergency_contact_name: data.emergency_contact_name ?? "",
          emergency_contact_phone: data.emergency_contact_phone ?? "",
          emergency_contact_relation: data.emergency_contact_relation ?? "",
          bank_name: data.bank_name ?? "",
          bank_account: data.bank_account ?? "",
          bank_routing: (data as unknown as { bank_routing?: string | null }).bank_routing ?? "",
          tax_id: (data as unknown as { tax_id?: string | null }).tax_id ?? "",
          direct_deposit_enabled: Boolean(data.direct_deposit_enabled),
          notification_email: (data as unknown as { notification_email?: boolean }).notification_email ?? true,
          notification_sms: (data as unknown as { notification_sms?: boolean }).notification_sms ?? false,
          notification_push: (data as unknown as { notification_push?: boolean }).notification_push ?? true,
          language: data.language ?? "en",
          theme_preference: data.theme_preference ?? "light",
        })
      } else if (canWorkforce && myEmployeeId) {
        // No profile yet — keep null but mark not found if the GET was skipped (no myId) don't show 404
        // If promise resolved with null (gated off), don't treat as not found
        if (profileP !== (Promise.resolve(null as unknown as { data: ESSProfileRow }) as unknown as Promise<unknown>)) {
          // we attempted a fetch but got null envelope — treat as empty
        }
        // Check if the fetch was attempted and returned 404: allSettled would be rejected, not fulfilled
        // So this branch is for when we didn't fetch; keep profile null
        if (myEmployeeId && (profileR.value as unknown) === null) {
          // not fetched due to gating — keep null
        }
      }
    } else if (canWorkforce && myEmployeeId) {
      const msg = errorMessage(profileR.reason, "The profile could not be read.")
      // 404 means no profile yet — show EmptyState, not error
      const status = (profileR.reason as { response?: { status?: number } })?.response?.status
      const detail = (profileR.reason as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? ""
      if (status === 404 || detail.toLowerCase().includes("not found")) {
        setProfile(null)
        setProfileNotFound(true)
        // seed employee id for create form
        if (!profileEmployeeId) setProfileEmployeeId(String(myEmployeeId))
      } else {
        setProfile(null)
        setProfileNotFound(false)
        next.profile = msg
      }
    }

    if (notifR.status === "fulfilled") {
      const v = notifR.value as unknown as { data: NotificationRow[] }
      setNotifications(v.data ?? [])
    } else if (canWorkforce) {
      setNotifications([])
      next.notifications = errorMessage(notifR.reason, "The notifications could not be read.")
    }

    if (filesR.status === "fulfilled") {
      const v = filesR.value as unknown as { data: EmployeeFileRow[] }
      setFiles(v.data ?? [])
    } else if (canWorkforce) {
      setFiles([])
      next.files = errorMessage(filesR.reason, "The files could not be read.")
    }

    if (dirR.status === "fulfilled") {
      const v = dirR.value as unknown as { data: DirectoryEntryRow[] }
      setDirectory(v.data ?? [])
    } else if (canWorkforce) {
      setDirectory([])
      next.directory = errorMessage(dirR.reason, "The directory could not be read.")
    }

    if (orgR.status === "fulfilled") {
      const v = orgR.value as unknown as { data: OrgNodeRow[] }
      setOrgNodes(v.data ?? [])
    } else if (canWorkforce) {
      setOrgNodes([])
      next.org = errorMessage(orgR.reason, "The org chart could not be read.")
    }

    if (goalAlignR.status === "fulfilled") {
      const v = goalAlignR.value as unknown as { data: GoalAlignmentRow[] }
      setGoalAlignments(v.data ?? [])
    } else if (canWorkforce) {
      setGoalAlignments([])
      next.goalAlignments = errorMessage(goalAlignR.reason, "The goal alignments could not be read.")
    }

    if (cfR.status === "fulfilled") {
      const v = cfR.value as unknown as { data: ContinuousFeedbackRow[] }
      setContinuousFeedback(v.data ?? [])
    } else if (canWorkforce) {
      setContinuousFeedback([])
      next.continuousFeedback = errorMessage(cfR.reason, "The continuous feedback could not be read.")
    }

    if (annR.status === "fulfilled") {
      const v = annR.value as unknown as { data: AnnouncementRow[] }
      setAnnouncements(v.data ?? [])
    } else if (canAll) {
      setAnnouncements([])
      next.announcements = errorMessage(annR.reason, "The announcements could not be read.")
    }

    if (compR.status === "fulfilled") {
      const v = compR.value as unknown as { data: ComplianceCheckRow[] }
      setComplianceChecks(v.data ?? [])
    } else if (canAdmin) {
      setComplianceChecks([])
      next.compliance = errorMessage(compR.reason, "The compliance checks could not be read.")
    }

    setErrors(next)
    setLoading(false)
  }, [canAdmin, canAll, canWorkforce, dirDepartment, dirQuery, notifRecipientId, notifUnreadOnly, annPublishedOnly, profileEmployeeId, user?.email]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    void load()
  }, [load])

  // Handlers — Profile
  async function handleCreateProfile(e: FormEvent) {
    e.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, profile: "" }))
    setNotice("")
    const eid = Number(profileEmployeeId)
    if (!eid) {
      setFormErrors((c) => ({ ...c, profile: "Choose the employee for this profile." }))
      return
    }
    setBusy("profile")
    try {
      await api.post(`${PROFILE_BASE}`, {
        employee_id: eid,
        preferred_name: profileForm.preferred_name.trim() || null,
        emergency_contact_name: profileForm.emergency_contact_name.trim() || null,
        emergency_contact_phone: profileForm.emergency_contact_phone.trim() || null,
        emergency_contact_relation: profileForm.emergency_contact_relation.trim() || null,
        bank_name: profileForm.bank_name.trim() || null,
        bank_account: profileForm.bank_account.trim() || null,
        bank_routing: profileForm.bank_routing.trim() || null,
        tax_id: profileForm.tax_id.trim() || null,
        direct_deposit_enabled: profileForm.direct_deposit_enabled,
        notification_email: profileForm.notification_email,
        notification_sms: profileForm.notification_sms,
        notification_push: profileForm.notification_push,
        language: profileForm.language || "en",
        theme_preference: profileForm.theme_preference || "light",
      })
      setNotice("Profile created.")
      setProfileNotFound(false)
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, profile: errorMessage(err, "The profile could not be created.") }))
    } finally {
      setBusy("")
    }
  }

  async function handleUpdateProfile(e: FormEvent) {
    e.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, profile: "" }))
    setNotice("")
    const eid = Number(profileEmployeeId) || profile?.employee_id
    if (!eid) {
      setFormErrors((c) => ({ ...c, profile: "Choose the employee for this profile." }))
      return
    }
    setBusy("profile-update")
    try {
      await api.put(`${PROFILE_BASE}/${eid}`, {
        employee_id: eid,
        preferred_name: profileForm.preferred_name.trim() || null,
        emergency_contact_name: profileForm.emergency_contact_name.trim() || null,
        emergency_contact_phone: profileForm.emergency_contact_phone.trim() || null,
        emergency_contact_relation: profileForm.emergency_contact_relation.trim() || null,
        bank_name: profileForm.bank_name.trim() || null,
        bank_account: profileForm.bank_account.trim() || null,
        bank_routing: profileForm.bank_routing.trim() || null,
        tax_id: profileForm.tax_id.trim() || null,
        direct_deposit_enabled: profileForm.direct_deposit_enabled,
        notification_email: profileForm.notification_email,
        notification_sms: profileForm.notification_sms,
        notification_push: profileForm.notification_push,
        language: profileForm.language || "en",
        theme_preference: profileForm.theme_preference || "light",
      })
      setNotice("Profile updated.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, profile: errorMessage(err, "The profile could not be updated.") }))
    } finally {
      setBusy("")
    }
  }

  // Notifications
  async function handleCreateNotification(e: FormEvent) {
    e.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, notification: "" }))
    setNotice("")
    if (!notifForm.recipient_id) {
      setFormErrors((c) => ({ ...c, notification: "Choose the recipient." }))
      return
    }
    if (!notifForm.title.trim() || !notifForm.message.trim()) {
      setFormErrors((c) => ({ ...c, notification: "Title and message are required." }))
      return
    }
    setBusy("notification")
    try {
      await api.post("/ess/notifications", {
        recipient_id: Number(notifForm.recipient_id),
        title: notifForm.title.trim(),
        message: notifForm.message.trim(),
        notification_type: notifForm.notification_type || "info",
        category: notifForm.category || "system",
        entity_type: notifForm.entity_type.trim() || null,
        entity_id: notifForm.entity_id ? Number(notifForm.entity_id) : null,
      })
      setNotifForm({ recipient_id: "", title: "", message: "", notification_type: "info", category: "system", entity_type: "", entity_id: "" })
      setNotice("Notification created.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, notification: errorMessage(err, "The notification could not be created.") }))
    } finally {
      setBusy("")
    }
  }

  async function handleMarkRead(id: number) {
    if (busy) return
    setBusy(`read-${id}`)
    setNotice("")
    setFormErrors((c) => ({ ...c, notification: "" }))
    try {
      await api.put(`/ess/notifications/${id}/read`)
      setNotice(`Notification #${id} marked as read.`)
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, notification: errorMessage(err, "The notification could not be marked as read.") }))
    } finally {
      setBusy("")
    }
  }

  // Files
  async function handleCreateFile(e: FormEvent) {
    e.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, file: "" }))
    setNotice("")
    if (!fileForm.employee_id) {
      setFormErrors((c) => ({ ...c, file: "Choose the employee." }))
      return
    }
    if (!fileForm.document_type.trim() || !fileForm.file_name.trim() || !fileForm.storage_url.trim()) {
      setFormErrors((c) => ({ ...c, file: "Document type, file name and storage URL are required." }))
      return
    }
    setBusy("file")
    try {
      await api.post("/ess/employee-files", {
        employee_id: Number(fileForm.employee_id),
        document_type: fileForm.document_type.trim(),
        file_name: fileForm.file_name.trim(),
        storage_url: fileForm.storage_url.trim(),
        status: fileForm.status || "Active",
        expiry_date: fileForm.expiry_date || null,
        notes: fileForm.notes.trim() || null,
      })
      setFileForm({ employee_id: "", document_type: "", file_name: "", storage_url: "", status: "Active", expiry_date: "", notes: "" })
      setNotice("File created.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, file: errorMessage(err, "The file could not be created.") }))
    } finally {
      setBusy("")
    }
  }

  // Directory sync
  async function handleSyncDirectory() {
    if (busy) return
    setBusy("directory-sync")
    setNotice("")
    setFormErrors((c) => ({ ...c, directory: "" }))
    try {
      await api.post("/ess/directory/sync")
      setNotice("Directory synced.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, directory: errorMessage(err, "The directory could not be synced.") }))
    } finally {
      setBusy("")
    }
  }

  // Org chart rebuild
  async function handleRebuildOrg() {
    if (busy) return
    setBusy("org-rebuild")
    setNotice("")
    setFormErrors((c) => ({ ...c, org: "" }))
    try {
      await api.post("/ess/org-chart/rebuild")
      setNotice("Org chart rebuilt.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, org: errorMessage(err, "The org chart could not be rebuilt.") }))
    } finally {
      setBusy("")
    }
  }

  // Goal alignments
  async function handleCreateGoalAlignment(e: FormEvent) {
    e.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, goalAlignment: "" }))
    setNotice("")
    if (!goalAlignForm.goal_id) {
      setFormErrors((c) => ({ ...c, goalAlignment: "Goal is required." }))
      return
    }
    setBusy("goalAlignment")
    try {
      await api.post("/ess/goal-alignments", {
        goal_id: Number(goalAlignForm.goal_id),
        parent_goal_id: goalAlignForm.parent_goal_id ? Number(goalAlignForm.parent_goal_id) : null,
      })
      setGoalAlignForm({ goal_id: "", parent_goal_id: "" })
      setNotice("Goal alignment created.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, goalAlignment: errorMessage(err, "The goal alignment could not be created.") }))
    } finally {
      setBusy("")
    }
  }

  // Continuous feedback
  async function handleCreateContinuousFeedback(e: FormEvent) {
    e.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, cf: "" }))
    setNotice("")
    if (!cfForm.from_employee_id || !cfForm.to_employee_id || !cfForm.message.trim()) {
      setFormErrors((c) => ({ ...c, cf: "From, to and message are required." }))
      return
    }
    setBusy("cf")
    try {
      await api.post("/ess/continuous-feedback", {
        from_employee_id: Number(cfForm.from_employee_id),
        to_employee_id: Number(cfForm.to_employee_id),
        feedback_type: cfForm.feedback_type || "Praise",
        message: cfForm.message.trim(),
        is_private: cfForm.is_private,
      })
      setCfForm({ from_employee_id: "", to_employee_id: "", feedback_type: "Praise", message: "", is_private: false })
      setNotice("Feedback submitted.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, cf: errorMessage(err, "The feedback could not be submitted.") }))
    } finally {
      setBusy("")
    }
  }

  // Announcements
  async function handleCreateAnnouncement(e: FormEvent) {
    e.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, announcement: "" }))
    setNotice("")
    if (!annForm.title.trim() || !annForm.content.trim()) {
      setFormErrors((c) => ({ ...c, announcement: "Title and content are required." }))
      return
    }
    setBusy("announcement")
    try {
      await api.post("/ess/announcements", {
        title: annForm.title.trim(),
        content: annForm.content.trim(),
        category: annForm.category || "General",
        priority: annForm.priority || "Normal",
        target_audience: annForm.target_audience || "All",
        target_value: annForm.target_value.trim() || null,
        published: annForm.published,
        expires_at: annForm.expires_at ? new Date(annForm.expires_at).toISOString() : null,
      })
      setAnnForm({ title: "", content: "", category: "General", priority: "Normal", target_audience: "All", target_value: "", published: false, expires_at: "" })
      setNotice("Announcement created.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, announcement: errorMessage(err, "The announcement could not be created.") }))
    } finally {
      setBusy("")
    }
  }

  async function handlePublishAnnouncement(id: number) {
    if (busy) return
    setBusy(`publish-${id}`)
    setNotice("")
    setFormErrors((c) => ({ ...c, announcement: "" }))
    try {
      await api.put(`/ess/announcements/${id}/publish`)
      setNotice(`Announcement #${id} published.`)
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, announcement: errorMessage(err, "The announcement could not be published.") }))
    } finally {
      setBusy("")
    }
  }

  // Leave request
  async function handleSubmitLeaveRequest(e: FormEvent) {
    e.preventDefault()
    if (busy) return
    setFormErrors((c) => ({ ...c, leave: "" }))
    setNotice("")
    if (!leaveForm.leave_type_id || !leaveForm.start_date || !leaveForm.end_date || !leaveForm.reason.trim()) {
      setFormErrors((c) => ({ ...c, leave: "Leave type, start date, end date and reason are required." }))
      return
    }
    if (new Date(leaveForm.end_date) < new Date(leaveForm.start_date)) {
      setFormErrors((c) => ({ ...c, leave: "End date must not be before the start date." }))
      return
    }
    setBusy("leave")
    try {
      const eid = profileEmployeeId ? Number(profileEmployeeId) : (employees.find((e) => e.email === user?.email)?.id ?? employees[0]?.id ?? 0)
      await api.post("/leave/requests", {
        employee_id: eid,
        leave_type_id: Number(leaveForm.leave_type_id),
        start_date: leaveForm.start_date,
        end_date: leaveForm.end_date,
        reason: leaveForm.reason.trim(),
      })
      setLeaveForm({ leave_type_id: "", start_date: "", end_date: "", reason: "" })
      setNotice("Leave request submitted.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, leave: errorMessage(err, "The leave request could not be submitted.") }))
    } finally {
      setBusy("")
    }
  }

  // Compliance
  async function handleRunCompliance() {
    if (busy) return
    setBusy("compliance-run")
    setNotice("")
    setFormErrors((c) => ({ ...c, compliance: "" }))
    try {
      await api.post("/ess/compliance-checks/run")
      setNotice("Compliance checks run.")
      await load()
    } catch (err) {
      setFormErrors((c) => ({ ...c, compliance: errorMessage(err, "The compliance checks could not be run.") }))
    } finally {
      setBusy("")
    }
  }

  const unreadCount = notifications.filter((n) => !n.is_read).length

  return (
    <Layout>
      <PageHeader compact title="Employee Self-Service" description="Your profile, files, notifications, directory and org chart" />

      {notice && <Alert tone="success">{notice}</Alert>}

      {/* My Profile */}
      <SectionCard compact
        title="My Profile"
        description="Your ESS profile — preferred name, emergency contact, bank, notifications prefs, language/theme. Any workforce role may read and maintain their own profile."
      >
        {!canWorkforce ? (
          <div className="p-5">
            <EmptyState title="Profiles are available to SuperAdmin, HR, Manager and Associate" description="Your role does not read ESS profiles." />
          </div>
        ) : loading ? (
          <LoadingRegion label="Loading profile…">
            <TableSkeleton rows={3} cols={4} />
          </LoadingRegion>
        ) : errors.profile ? (
          <div className="p-5">
            <RetryableAlert err={errors.profile} title="The profile could not be read" fallback="The profile could not be read" onRetry={load} />
          </div>
        ) : (
          <>
            <div className="p-5 border-b border-border">
              <div className="flex flex-wrap gap-3 items-end">
                <div className="min-w-[220px] flex-1">
                  <Field label="Employee" htmlFor="profile-employee">
                    <Select id="profile-employee" value={profileEmployeeId} onChange={(e) => setProfileEmployeeId(e.target.value)}>
                      <option value="">Select an employee…</option>
                      {employees.map((emp) => (
                        <option key={emp.id} value={emp.id}>
                          {emp.first_name} {emp.last_name} · {emp.employee_id}
                        </option>
                      ))}
                    </Select>
                  </Field>
                </div>
                <Button variant="secondary" onClick={() => void load()} loading={busy === "profile" || busy === "profile-update"}>Load profile</Button>
              </div>
            </div>

            {profileNotFound && !profile ? (
              <div className="p-5">
                <EmptyState title="No profile yet — create one" description="No ESS profile exists for the selected employee. Fill the form below to create it." />
              </div>
            ) : profile ? (
              <Table
                columns={[
                  { key: "employee", header: "Employee", accessor: (pr) => employeeName(pr.employee_id) },
                  { key: "preferred", header: "Preferred name", accessor: (pr) => pr.preferred_name ?? "\u2014" },
                  { key: "emergency", header: "Emergency contact", accessor: (pr) => pr.emergency_contact_name ? `${pr.emergency_contact_name} \u00b7 ${pr.emergency_contact_phone ?? ""} (${pr.emergency_contact_relation ?? ""})` : "\u2014" },
                  { key: "bank", header: "Bank", accessor: (pr) => <>{pr.bank_name ?? "\u2014"}{pr.bank_account ? " \u00b7 On file" : ""}</> },
                  { key: "language", header: "Language", accessor: (pr) => pr.language },
                  { key: "theme", header: "Theme", accessor: (pr) => pr.theme_preference },
                  { key: "dd", header: "Direct deposit", accessor: (pr) => pr.direct_deposit_enabled ? "Yes" : "No" },
                ]}
                data={[profile]}
                keyAccessor={(pr) => pr.employee_id}
                caption="ESS profile"
                sortable={false}
              />
            ) : (
              <div className="p-5 text-sm text-text-secondary">Select an employee and load the profile.</div>
            )}

            <form onSubmit={profile ? handleUpdateProfile : handleCreateProfile} className="p-5 border-t border-border">
              {formErrors.profile && <p className="text-sm text-error-text mb-3" role="alert">{formErrors.profile}</p>}
              <div className="flex flex-wrap gap-3 items-end">
                <div className="min-w-[160px]"><Field label="Preferred name" htmlFor="profile-preferred"><Input id="profile-preferred" value={profileForm.preferred_name} onChange={(e) => setProfileForm((f) => ({ ...f, preferred_name: e.target.value }))} placeholder="Optional" /></Field></div>
                <div className="min-w-[180px]"><Field label="Emergency contact name" htmlFor="profile-ec-name"><Input id="profile-ec-name" value={profileForm.emergency_contact_name} onChange={(e) => setProfileForm((f) => ({ ...f, emergency_contact_name: e.target.value }))} /></Field></div>
                <div className="min-w-[160px]"><Field label="Emergency phone" htmlFor="profile-ec-phone"><Input id="profile-ec-phone" value={profileForm.emergency_contact_phone} onChange={(e) => setProfileForm((f) => ({ ...f, emergency_contact_phone: e.target.value }))} /></Field></div>
                <div className="min-w-[160px]"><Field label="Relation" htmlFor="profile-ec-relation"><Input id="profile-ec-relation" value={profileForm.emergency_contact_relation} onChange={(e) => setProfileForm((f) => ({ ...f, emergency_contact_relation: e.target.value }))} /></Field></div>
                <div className="min-w-[160px]"><Field label="Bank name" htmlFor="profile-bank-name"><Input id="profile-bank-name" value={profileForm.bank_name} onChange={(e) => setProfileForm((f) => ({ ...f, bank_name: e.target.value }))} /></Field></div>
                <div className="min-w-[160px]"><Field label="Bank account" htmlFor="profile-bank-account"><Input id="profile-bank-account" value={profileForm.bank_account} onChange={(e) => setProfileForm((f) => ({ ...f, bank_account: e.target.value }))} autoComplete="off" /></Field></div>
                <div className="min-w-[140px]"><Field label="Routing" htmlFor="profile-routing"><Input id="profile-routing" value={profileForm.bank_routing} onChange={(e) => setProfileForm((f) => ({ ...f, bank_routing: e.target.value }))} /></Field></div>
                <div className="min-w-[140px]"><Field label="Tax ID" htmlFor="profile-tax"><Input id="profile-tax" value={profileForm.tax_id} onChange={(e) => setProfileForm((f) => ({ ...f, tax_id: e.target.value }))} /></Field></div>
                <div className="min-w-[100px]"><Field label="Language" htmlFor="profile-language"><Select id="profile-language" value={profileForm.language} onChange={(e) => setProfileForm((f) => ({ ...f, language: e.target.value }))}><option value="en">en</option><option value="fr">fr</option><option value="es">es</option><option value="de">de</option></Select></Field></div>
                <div className="min-w-[120px]"><Field label="Theme" htmlFor="profile-theme"><Select id="profile-theme" value={profileForm.theme_preference} onChange={(e) => setProfileForm((f) => ({ ...f, theme_preference: e.target.value }))}><option value="light">light</option><option value="dark">dark</option></Select></Field></div>
                <Checkbox id="profile-dd" label="Direct deposit" checked={profileForm.direct_deposit_enabled} onChange={(e) => setProfileForm((f) => ({ ...f, direct_deposit_enabled: e.target.checked }))} />
                <Checkbox id="profile-email" label="Email notifs" checked={profileForm.notification_email} onChange={(e) => setProfileForm((f) => ({ ...f, notification_email: e.target.checked }))} />
                <Checkbox id="profile-sms" label="SMS notifs" checked={profileForm.notification_sms} onChange={(e) => setProfileForm((f) => ({ ...f, notification_sms: e.target.checked }))} />
                <Checkbox id="profile-push" label="Push notifs" checked={profileForm.notification_push} onChange={(e) => setProfileForm((f) => ({ ...f, notification_push: e.target.checked }))} />
                <Button type="submit" loading={busy === "profile" || busy === "profile-update"}>{profile ? "Update profile" : "Create profile"}</Button>
              </div>
            </form>
          </>
        )}
      </SectionCard>

      {/* Notifications */}
      <SectionCard compact title="Notifications" description="Inbox for workforce roles. Mark as read is workforce; creating is limited to SuperAdmin and HR." actions={unreadCount > 0 ? <span className="badge badge-rose">{unreadCount} unread</span> : undefined}>
        {!canWorkforce ? (
          <div className="p-5"><EmptyState title="Notifications are available to SuperAdmin, HR, Manager and Associate" description="Your role does not read notifications." /></div>
        ) : loading ? (
          <LoadingRegion label="Loading notifications…"><TableSkeleton rows={3} cols={5} /></LoadingRegion>
        ) : errors.notifications ? (
          <div className="p-5"><RetryableAlert err={errors.notifications} title="The notifications could not be read" fallback="The notifications could not be read" onRetry={load} /></div>
        ) : (
          <>
            <div className="p-5 border-b border-border">
              <div className="flex flex-wrap gap-3 items-end">
                <div className="min-w-[220px]"><Field label="Recipient filter" htmlFor="notif-recipient"><Select id="notif-recipient" value={notifRecipientId} onChange={(e) => setNotifRecipientId(e.target.value)}><option value="">All visible</option>{employees.map((emp) => (<option key={emp.id} value={emp.id}>{emp.first_name} {emp.last_name}</option>))}</Select></Field></div>
                <Checkbox id="notif-unread" label="Unread only" checked={notifUnreadOnly} onChange={(e) => setNotifUnreadOnly(e.target.checked)} />
                <Button variant="secondary" onClick={() => void load()}>Apply filters</Button>
              </div>
            </div>

            {canAdmin ? (
              <form onSubmit={handleCreateNotification} className="p-5 border-b border-border">
                {formErrors.notification && <p className="text-sm text-error-text mb-3" role="alert">{formErrors.notification}</p>}
                <div className="flex flex-wrap gap-3 items-end">
                  <div className="min-w-[200px] flex-1"><Field label="Recipient" htmlFor="notif-create-recipient" required><Select id="notif-create-recipient" value={notifForm.recipient_id} onChange={(e) => setNotifForm((f) => ({ ...f, recipient_id: e.target.value }))} required><option value="">Select an employee…</option>{employees.map((emp) => (<option key={emp.id} value={emp.id}>{emp.first_name} {emp.last_name}</option>))}</Select></Field></div>
                  <div className="min-w-[180px] flex-1"><Field label="Title" htmlFor="notif-title" required><Input id="notif-title" value={notifForm.title} onChange={(e) => setNotifForm((f) => ({ ...f, title: e.target.value }))} required /></Field></div>
                  <div className="min-w-[140px]"><Field label="Type" htmlFor="notif-type"><Select id="notif-type" value={notifForm.notification_type} onChange={(e) => setNotifForm((f) => ({ ...f, notification_type: e.target.value }))}><option value="info">info</option><option value="warning">warning</option><option value="alert">alert</option></Select></Field></div>
                  <div className="min-w-[140px]"><Field label="Category" htmlFor="notif-category"><Select id="notif-category" value={notifForm.category} onChange={(e) => setNotifForm((f) => ({ ...f, category: e.target.value }))}><option value="system">system</option><option value="hr">hr</option><option value="payroll">payroll</option></Select></Field></div>
                  <div className="min-w-[140px]"><Field label="Entity type" htmlFor="notif-entity-type"><Input id="notif-entity-type" value={notifForm.entity_type} onChange={(e) => setNotifForm((f) => ({ ...f, entity_type: e.target.value }))} /></Field></div>
                  <div className="min-w-[120px]"><Field label="Entity id" htmlFor="notif-entity-id"><Input id="notif-entity-id" type="number" value={notifForm.entity_id} onChange={(e) => setNotifForm((f) => ({ ...f, entity_id: e.target.value }))} /></Field></div>
                  <Button type="submit" loading={busy === "notification"}>Create notification</Button>
                </div>
                <div className="mt-3"><Field label="Message" htmlFor="notif-message" required><Textarea id="notif-message" value={notifForm.message} onChange={(e) => setNotifForm((f) => ({ ...f, message: e.target.value }))} rows={2} required /></Field></div>
              </form>
            ) : (
              <div className="px-5 pt-4"><EmptyState title="Creating notifications requires SuperAdmin or HR" description="Your role may read and mark notifications as read, but only SuperAdmin and HR may create them." /></div>
            )}

            {notifications.length === 0 ? (
              <div className="p-5 text-sm text-text-secondary">No notifications.</div>
            ) : (
              <Table
                columns={[
                  { key: "title", header: "Title", accessor: (n) => (
                    <span className="font-medium">{n.title}<div className="text-xs text-text-secondary truncate max-w-[260px]" title={n.message}>{n.message}</div></span>
                  ) },
                  { key: "recipient", header: "Recipient", accessor: (n) => employeeName(n.recipient_id) },
                  { key: "type", header: "Type", accessor: (n) => <StatusPill status={n.notification_type} /> },
                  { key: "category", header: "Category", accessor: (n) => n.category },
                  { key: "read", header: "Read", accessor: (n) => n.is_read ? <span className="badge badge-green">Read</span> : <span className="badge badge-amber">Unread</span> },
                  { key: "created", header: "Created", accessor: (n) => fmtDateTime(n.created_at) },
                  { key: "actions", header: "Actions", accessor: (n) => (
                    !n.is_read ? <Button size="xs" variant="secondary" loading={busy === `read-${n.id}`} onClick={() => handleMarkRead(n.id)}>Mark read</Button> : <></>
                  ) },
                ]}
                data={notifications}
                keyAccessor={(n) => n.id}
                caption="Notifications"
                sortable={false}
              />
            )}
          </>
        )}
      </SectionCard>

      {/* My Files */}
      <SectionCard compact title="My Files" description="Employee files. Reading is workforce; creating is limited to SuperAdmin and HR.">
        {!canWorkforce ? (
          <div className="p-5"><EmptyState title="Files are available to SuperAdmin, HR, Manager and Associate" description="Your role does not read employee files." /></div>
        ) : loading ? (
          <LoadingRegion label="Loading files…"><TableSkeleton rows={3} cols={5} /></LoadingRegion>
        ) : errors.files ? (
          <div className="p-5"><RetryableAlert err={errors.files} title="The files could not be read" fallback="The files could not be read" onRetry={load} /></div>
        ) : (
          <>
            {canAdmin ? (
              <form onSubmit={handleCreateFile} className="p-5 border-b border-border">
                {formErrors.file && <p className="text-sm text-error-text mb-3" role="alert">{formErrors.file}</p>}
                <div className="flex flex-wrap gap-3 items-end">
                  <div className="min-w-[200px] flex-1"><Field label="Employee" htmlFor="file-employee" required><Select id="file-employee" value={fileForm.employee_id} onChange={(e) => setFileForm((f) => ({ ...f, employee_id: e.target.value }))} required><option value="">Select an employee…</option>{employees.map((emp) => (<option key={emp.id} value={emp.id}>{emp.first_name} {emp.last_name}</option>))}</Select></Field></div>
                  <div className="min-w-[140px]"><Field label="Document type" htmlFor="file-doctype" required><Input id="file-doctype" value={fileForm.document_type} onChange={(e) => setFileForm((f) => ({ ...f, document_type: e.target.value }))} placeholder="e.g. Contract" required /></Field></div>
                  <div className="min-w-[180px]"><Field label="File name" htmlFor="file-name" required><Input id="file-name" value={fileForm.file_name} onChange={(e) => setFileForm((f) => ({ ...f, file_name: e.target.value }))} required /></Field></div>
                  <div className="min-w-[200px] flex-1"><Field label="Storage URL" htmlFor="file-url" required><Input id="file-url" value={fileForm.storage_url} onChange={(e) => setFileForm((f) => ({ ...f, storage_url: e.target.value }))} placeholder="https://..." required /></Field></div>
                  <div className="min-w-[120px]"><Field label="Status" htmlFor="file-status"><Select id="file-status" value={fileForm.status} onChange={(e) => setFileForm((f) => ({ ...f, status: e.target.value }))}><option value="Active">Active</option><option value="Expired">Expired</option><option value="Pending">Pending</option></Select></Field></div>
                  <div className="min-w-[140px]"><Field label="Expiry" htmlFor="file-expiry"><Input id="file-expiry" type="date" value={fileForm.expiry_date} onChange={(e) => setFileForm((f) => ({ ...f, expiry_date: e.target.value }))} /></Field></div>
                  <Button type="submit" loading={busy === "file"}>Add file</Button>
                </div>
                <div className="mt-3"><Field label="Notes" htmlFor="file-notes"><Input id="file-notes" value={fileForm.notes} onChange={(e) => setFileForm((f) => ({ ...f, notes: e.target.value }))} /></Field></div>
              </form>
            ) : (
              <div className="px-5 pt-4"><EmptyState title="Creating files requires SuperAdmin or HR" description="Your role may read files, but only SuperAdmin and HR may upload them." /></div>
            )}

            {files.length === 0 ? (
              <div className="p-5 text-sm text-text-secondary">No files.</div>
            ) : (
              <Table
                columns={[
                  { key: "employee", header: "Employee", accessor: (f) => employeeName(f.employee_id) },
                  { key: "doctype", header: "Document type", accessor: (f) => f.document_type },
                  { key: "file", header: "File name", accessor: (f) => <a href={f.storage_url} target="_blank" rel="noreferrer" className="text-brand-600 hover:underline">{f.file_name}</a> },
                  { key: "status", header: "Status", accessor: (f) => <StatusPill status={f.status} /> },
                  { key: "expiry", header: "Expiry", accessor: (f) => fmtDate(f.expiry_date) },
                  { key: "version", header: "Version", accessor: (f) => f.version ?? "\u2014" },
                ]}
                data={files}
                keyAccessor={(f) => f.id}
                caption="Employee files"
                sortable={false}
              />
            )}
          </>
        )}
      </SectionCard>

      {/* Directory */}
      <SectionCard compact
        title="Directory"
        description="Employee directory. Reading is workforce; syncing is limited to SuperAdmin and HR."
        actions={canAdmin ? <Button size="xs" variant="secondary" loading={busy === "directory-sync"} onClick={handleSyncDirectory}>Sync directory</Button> : undefined}
      >
        {!canWorkforce ? (
          <div className="p-5"><EmptyState title="Directory is available to SuperAdmin, HR, Manager and Associate" description="Your role does not read the directory." /></div>
        ) : loading ? (
          <LoadingRegion label="Loading directory…"><TableSkeleton rows={3} cols={6} /></LoadingRegion>
        ) : errors.directory ? (
          <div className="p-5"><RetryableAlert err={errors.directory} title="The directory could not be read" fallback="The directory could not be read" onRetry={load} /></div>
        ) : (
          <>
            {formErrors.directory && <div className="px-5 pt-4"><Alert tone="error">{formErrors.directory}</Alert></div>}
            <div className="p-5 border-b border-border">
              <div className="flex flex-wrap gap-3 items-end">
                <div className="min-w-[200px] flex-1"><Field label="Search" htmlFor="dir-q"><Input id="dir-q" value={dirQuery} onChange={(e) => setDirQuery(e.target.value)} placeholder="Name, email or job title" /></Field></div>
                <div className="min-w-[160px]"><Field label="Department" htmlFor="dir-dept"><Input id="dir-dept" value={dirDepartment} onChange={(e) => setDirDepartment(e.target.value)} placeholder="e.g. Engineering" /></Field></div>
                <Button variant="secondary" onClick={() => void load()}>Search</Button>
                {!canAdmin && <span className="text-xs text-text-secondary">Sync requires SuperAdmin or HR.</span>}
              </div>
            </div>

            {directory.length === 0 ? (
              <div className="p-5 text-sm text-text-secondary">No directory entries.</div>
            ) : (
              <Table
                columns={[
                  { key: "name", header: "Name", accessor: (d) => <span className="font-medium">{d.full_name}</span> },
                  { key: "email", header: "Email", accessor: (d) => d.email },
                  { key: "dept", header: "Department", accessor: (d) => d.department ?? "\u2014" },
                  { key: "title", header: "Job title", accessor: (d) => d.job_title ?? "\u2014" },
                  { key: "loc", header: "Location", accessor: (d) => d.location ?? "\u2014" },
                  { key: "phone", header: "Phone", accessor: (d) => d.phone ?? "\u2014" },
                ]}
                data={directory}
                keyAccessor={(d) => d.id}
                caption="Directory"
                sortable={false}
              />
            )}
          </>
        )}
      </SectionCard>

      {/* Org Chart */}
      <SectionCard compact
        title="Org Chart"
        description="Organisation chart. Reading is workforce; rebuilding is limited to SuperAdmin and HR."
        actions={canAdmin ? <Button size="xs" variant="secondary" loading={busy === "org-rebuild"} onClick={handleRebuildOrg}>Rebuild</Button> : undefined}
      >
        {!canWorkforce ? (
          <div className="p-5"><EmptyState title="Org chart is available to SuperAdmin, HR, Manager and Associate" description="Your role does not read the org chart." /></div>
        ) : loading ? (
          <LoadingRegion label="Loading org chart…"><TableSkeleton rows={3} cols={4} /></LoadingRegion>
        ) : errors.org ? (
          <div className="p-5"><RetryableAlert err={errors.org} title="The org chart could not be read" fallback="The org chart could not be read" onRetry={load} /></div>
        ) : (
          <>
            {formErrors.org && <div className="px-5 pt-4"><Alert tone="error">{formErrors.org}</Alert></div>}
            {!canAdmin && <div className="p-5"><EmptyState title="Rebuilding the org chart requires SuperAdmin or HR" description="Your role may view the chart, but only SuperAdmin and HR may rebuild it." /></div>}
            {orgNodes.length === 0 ? (
              <div className="p-5 text-sm text-text-secondary">No org nodes. An admin can rebuild the chart from employee manager relationships.</div>
            ) : (
              <Table
                columns={[
                  { key: "employee", header: "Employee", accessor: (n) => (
                    <span style={{ paddingLeft: `${Math.min(n.depth * 16, 64) + 8}px` }}>{employeeName(n.employee_id)}</span>
                  ) },
                  { key: "manager", header: "Manager", accessor: (n) => n.manager_id ? employeeName(n.manager_id) : "\u2014" },
                  { key: "depth", header: "Depth", accessor: (n) => n.depth },
                  { key: "path", header: "Path", accessor: (n) => <span className="font-mono text-xs">{n.path ?? "\u2014"}</span> },
                ]}
                data={orgNodes}
                keyAccessor={(n) => n.employee_id}
                caption="Org chart"
                sortable={false}
              />
            )}
          </>
        )}
      </SectionCard>

      {/* Goal Alignments */}
      <SectionCard compact title="Goal Alignments" description="OKR goal alignments. Reading is workforce; creating is limited to SuperAdmin, HR and Manager.">
        {!canWorkforce ? (
          <div className="p-5"><EmptyState title="Goal alignments are available to SuperAdmin, HR, Manager and Associate" description="Your role does not read goal alignments." /></div>
        ) : loading ? (
          <LoadingRegion label="Loading goal alignments…"><TableSkeleton rows={3} cols={4} /></LoadingRegion>
        ) : errors.goalAlignments ? (
          <div className="p-5"><RetryableAlert err={errors.goalAlignments} title="The goal alignments could not be read" fallback="The goal alignments could not be read" onRetry={load} /></div>
        ) : (
          <>
            {canManager ? (
              <form onSubmit={handleCreateGoalAlignment} className="p-5 border-b border-border">
                {formErrors.goalAlignment && <p className="text-sm text-error-text mb-3" role="alert">{formErrors.goalAlignment}</p>}
                <div className="flex flex-wrap gap-3 items-end">
                  <div className="min-w-[140px]"><Field label="Goal ID" htmlFor="ga-goal" required><Input id="ga-goal" type="number" value={goalAlignForm.goal_id} onChange={(e) => setGoalAlignForm((f) => ({ ...f, goal_id: e.target.value }))} required /></Field></div>
                  <div className="min-w-[140px]"><Field label="Parent goal ID" htmlFor="ga-parent"><Input id="ga-parent" type="number" value={goalAlignForm.parent_goal_id} onChange={(e) => setGoalAlignForm((f) => ({ ...f, parent_goal_id: e.target.value }))} /></Field></div>
                  <Button type="submit" loading={busy === "goalAlignment"}>Align goal</Button>
                </div>
              </form>
            ) : (
              <div className="px-5 pt-4"><EmptyState title="Creating goal alignments requires SuperAdmin, HR or Manager" description="Your role may read alignments, but only managers and admins may create them." /></div>
            )}

            {goalAlignments.length === 0 ? (
              <div className="p-5 text-sm text-text-secondary">No goal alignments.</div>
            ) : (
              <Table
                columns={[
                  { key: "id", header: "ID", accessor: (g) => g.id },
                  { key: "goal", header: "Goal", accessor: (g) => `#${g.goal_id}` },
                  { key: "parent", header: "Parent goal", accessor: (g) => g.parent_goal_id ?? "\u2014" },
                  { key: "created", header: "Created", accessor: (g) => fmtDateTime(g.created_at) },
                ]}
                data={goalAlignments}
                keyAccessor={(g) => g.id}
                caption="Goal alignments"
                sortable={false}
              />
            )}
          </>
        )}
      </SectionCard>

      {/* Continuous Feedback */}
      <SectionCard compact title="Continuous Feedback" description="Peer feedback. Any workforce role may read and submit feedback.">
        {!canWorkforce ? (
          <div className="p-5"><EmptyState title="Continuous feedback is available to SuperAdmin, HR, Manager and Associate" description="Your role does not read feedback." /></div>
        ) : loading ? (
          <LoadingRegion label="Loading feedback…"><TableSkeleton rows={3} cols={5} /></LoadingRegion>
        ) : errors.continuousFeedback ? (
          <div className="p-5"><RetryableAlert err={errors.continuousFeedback} title="The continuous feedback could not be read" fallback="The continuous feedback could not be read" onRetry={load} /></div>
        ) : (
          <>
            <form onSubmit={handleCreateContinuousFeedback} className="p-5 border-b border-border">
              {formErrors.cf && <p className="text-sm text-error-text mb-3" role="alert">{formErrors.cf}</p>}
              <div className="flex flex-wrap gap-3 items-end">
                <div className="min-w-[200px] flex-1"><Field label="From employee" htmlFor="cf-from" required><Select id="cf-from" value={cfForm.from_employee_id} onChange={(e) => setCfForm((f) => ({ ...f, from_employee_id: e.target.value }))} required><option value="">Select…</option>{employees.map((emp) => (<option key={emp.id} value={emp.id}>{emp.first_name} {emp.last_name}</option>))}</Select></Field></div>
                <div className="min-w-[200px] flex-1"><Field label="To employee" htmlFor="cf-to" required><Select id="cf-to" value={cfForm.to_employee_id} onChange={(e) => setCfForm((f) => ({ ...f, to_employee_id: e.target.value }))} required><option value="">Select…</option>{employees.map((emp) => (<option key={emp.id} value={emp.id}>{emp.first_name} {emp.last_name}</option>))}</Select></Field></div>
                <div className="min-w-[140px]"><Field label="Type" htmlFor="cf-type"><Select id="cf-type" value={cfForm.feedback_type} onChange={(e) => setCfForm((f) => ({ ...f, feedback_type: e.target.value }))}><option value="Praise">Praise</option><option value="Constructive">Constructive</option><option value="Suggestion">Suggestion</option></Select></Field></div>
                <Checkbox id="cf-private" label="Private" checked={cfForm.is_private} onChange={(e) => setCfForm((f) => ({ ...f, is_private: e.target.checked }))} />
                <Button type="submit" loading={busy === "cf"}>Submit feedback</Button>
              </div>
              <div className="mt-3"><Field label="Message" htmlFor="cf-message" required><Textarea id="cf-message" value={cfForm.message} onChange={(e) => setCfForm((f) => ({ ...f, message: e.target.value }))} rows={2} placeholder="What went well? What could be better?" required /></Field></div>
            </form>

            {continuousFeedback.length === 0 ? (
              <div className="p-5 text-sm text-text-secondary">No feedback yet.</div>
            ) : (
              <Table
                columns={[
                  { key: "from", header: "From", accessor: (fb) => employeeName(fb.from_employee_id) },
                  { key: "to", header: "To", accessor: (fb) => employeeName(fb.to_employee_id) },
                  { key: "type", header: "Type", accessor: (fb) => <StatusPill status={fb.feedback_type} /> },
                  { key: "message", header: "Message", accessor: (fb) => <span className="max-w-[260px] truncate" title={fb.message}>{fb.message}</span> },
                  { key: "private", header: "Private", accessor: (fb) => fb.is_private ? "Yes" : "No" },
                  { key: "created", header: "Created", accessor: (fb) => fmtDateTime(fb.created_at) },
                ]}
                data={continuousFeedback}
                keyAccessor={(fb) => fb.id}
                caption="Continuous feedback"
                sortable={false}
              />
            )}
          </>
        )}
      </SectionCard>

      {/* Announcements */}
      <SectionCard compact title="Announcements" description="Company announcements. Everyone may read; publishing and creating is limited to SuperAdmin and HR.">
        {loading ? (
          <LoadingRegion label="Loading announcements…"><TableSkeleton rows={3} cols={5} /></LoadingRegion>
        ) : errors.announcements ? (
          <div className="p-5"><RetryableAlert err={errors.announcements} title="The announcements could not be read" fallback="The announcements could not be read" onRetry={load} /></div>
        ) : (
          <>
            <div className="p-5 border-b border-border">
              <div className="flex flex-wrap gap-3 items-end">
                <Checkbox id="ann-published-only" label="Published only" checked={annPublishedOnly} onChange={(e) => { setAnnPublishedOnly(e.target.checked); }} />
                <Button variant="secondary" onClick={() => void load()}>Apply filter</Button>
              </div>
            </div>

            {canAdmin ? (
              <form onSubmit={handleCreateAnnouncement} className="p-5 border-b border-border">
                {formErrors.announcement && <p className="text-sm text-error-text mb-3" role="alert">{formErrors.announcement}</p>}
                <div className="flex flex-wrap gap-3 items-end">
                  <div className="min-w-[180px] flex-1"><Field label="Title" htmlFor="ann-title" required><Input id="ann-title" value={annForm.title} onChange={(e) => setAnnForm((f) => ({ ...f, title: e.target.value }))} required /></Field></div>
                  <div className="min-w-[120px]"><Field label="Category" htmlFor="ann-category"><Select id="ann-category" value={annForm.category} onChange={(e) => setAnnForm((f) => ({ ...f, category: e.target.value }))}><option value="General">General</option><option value="HR">HR</option><option value="Payroll">Payroll</option></Select></Field></div>
                  <div className="min-w-[120px]"><Field label="Priority" htmlFor="ann-priority"><Select id="ann-priority" value={annForm.priority} onChange={(e) => setAnnForm((f) => ({ ...f, priority: e.target.value }))}><option value="Normal">Normal</option><option value="High">High</option><option value="Urgent">Urgent</option></Select></Field></div>
                  <div className="min-w-[120px]"><Field label="Audience" htmlFor="ann-aud"><Select id="ann-aud" value={annForm.target_audience} onChange={(e) => setAnnForm((f) => ({ ...f, target_audience: e.target.value }))}><option value="All">All</option><option value="Department">Department</option><option value="Location">Location</option></Select></Field></div>
                  <div className="min-w-[140px]"><Field label="Target value" htmlFor="ann-target-val"><Input id="ann-target-val" value={annForm.target_value} onChange={(e) => setAnnForm((f) => ({ ...f, target_value: e.target.value }))} placeholder="Optional" /></Field></div>
                  <div className="min-w-[140px]"><Field label="Expires at" htmlFor="ann-expires"><Input id="ann-expires" type="datetime-local" value={annForm.expires_at} onChange={(e) => setAnnForm((f) => ({ ...f, expires_at: e.target.value }))} /></Field></div>
                  <Checkbox id="ann-published" label="Published" checked={annForm.published} onChange={(e) => setAnnForm((f) => ({ ...f, published: e.target.checked }))} />
                  <Button type="submit" loading={busy === "announcement"}>Create announcement</Button>
                </div>
                <div className="mt-3"><Field label="Content" htmlFor="ann-content" required><Textarea id="ann-content" value={annForm.content} onChange={(e) => setAnnForm((f) => ({ ...f, content: e.target.value }))} rows={2} required /></Field></div>
              </form>
            ) : (
              <div className="px-5 pt-4"><EmptyState title="Creating announcements requires SuperAdmin or HR" description="Your role may read announcements, but only SuperAdmin and HR may create or publish them." /></div>
            )}

            {announcements.length === 0 ? (
              <div className="p-5 text-sm text-text-secondary">No announcements.</div>
            ) : (
              <Table
                columns={[
                  { key: "title", header: "Title", accessor: (a) => (
                    <span className="font-medium">{a.title}<div className="text-xs text-text-secondary max-w-[260px] truncate" title={a.content}>{a.content}</div></span>
                  ) },
                  { key: "category", header: "Category", accessor: (a) => a.category },
                  { key: "priority", header: "Priority", accessor: (a) => <StatusPill status={a.priority} /> },
                  { key: "audience", header: "Audience", accessor: (a) => <>{a.target_audience}{a.target_value ? ` \u00b7 ${a.target_value}` : ""}</> },
                  { key: "published", header: "Published", accessor: (a) => a.published ? <span className="badge badge-green">Published</span> : <span className="badge badge-slate">Draft</span> },
                  { key: "created", header: "Created", accessor: (a) => fmtDateTime(a.created_at) },
                  ...(canAdmin ? [{
                    key: "actions", header: "Actions", accessor: (a: (typeof announcements)[number]) => (
                      !a.published ? <Button size="xs" loading={busy === `publish-${a.id}`} onClick={() => handlePublishAnnouncement(a.id)}>Publish</Button>
                      : <span className="text-xs text-text-secondary">{fmtDateTime(a.published_at)}</span>
                    ),
                  }] : []),
                ]}
                data={announcements}
                keyAccessor={(a) => a.id}
                caption="Announcements"
                sortable={false}
              />
            )}
          </>
        )}
      </SectionCard>

      {/* Compliance Checks */}
      <SectionCard compact title="Compliance Checks" description="Compliance check results. Viewing and running checks requires SuperAdmin or HR." actions={canAdmin ? <Button size="xs" loading={busy === "compliance-run"} onClick={handleRunCompliance}>Run checks</Button> : undefined}>
        {!canAdmin ? (
          <div className="p-5"><EmptyState title="Compliance checks require Admin" description="Only SuperAdmin and HR may view or run compliance checks." /></div>
        ) : loading ? (
          <LoadingRegion label="Loading compliance checks…"><TableSkeleton rows={3} cols={4} /></LoadingRegion>
        ) : errors.compliance ? (
          <div className="p-5"><RetryableAlert err={errors.compliance} title="The compliance checks could not be read" fallback="The compliance checks could not be read" onRetry={load} /></div>
        ) : (
          <>
            {formErrors.compliance && <div className="px-5 pt-4"><Alert tone="error">{formErrors.compliance}</Alert></div>}
            {complianceChecks.length === 0 ? (
              <div className="p-5 text-sm text-text-secondary">No compliance checks yet. Run the checks to evaluate active rules.</div>
            ) : (
              <Table
                columns={[
                  { key: "rule", header: "Rule", accessor: (c) => `#${c.rule_id}` },
                  { key: "passed", header: "Passed", accessor: (c) => c.passed ? <span className="badge badge-green">Passed</span> : <span className="badge badge-rose">Failed</span> },
                  { key: "details", header: "Details", accessor: (c) => <span className="max-w-[320px] truncate" title={c.details ?? ""}>{c.details ?? "\u2014"}</span> },
                  { key: "runat", header: "Run at", accessor: (c) => fmtDateTime(c.run_at) },
                ]}
                data={complianceChecks}
                keyAccessor={(c) => c.id}
                caption="Compliance checks"
                sortable={false}
              />
            )}
          </>
        )}
      </SectionCard>

      {/* My Payslips */}
      <SectionCard compact
        title="My Payslips"
        description="Your payslips — gross pay, deductions and net pay, scoped to your own employee record."
      >
        {!canWorkforce ? (
          <div className="p-5"><EmptyState title="Payslips are available to workforce roles" description="Your role does not read payslips." /></div>
        ) : loading ? (
          <LoadingRegion label="Loading payslips…"><TableSkeleton rows={3} cols={5} /></LoadingRegion>
        ) : errors.payslips ? (
          <div className="p-5"><RetryableAlert err={errors.payslips} title="The payslips could not be read" fallback="The payslips could not be read" onRetry={load} /></div>
        ) : (
          <>
            {payslips.length === 0 ? (
              <div className="p-5 text-sm text-text-secondary">No payslips found for your employee record.</div>
            ) : (
              <Table
                columns={[
                  { key: "run", header: "Pay run", accessor: (p) => `#${p.pay_run_id}` },
                  { key: "gross", header: "Gross pay", accessor: (p) => String(p.gross_pay) },
                  { key: "ded", header: "Deductions", accessor: (p) => String(p.total_deductions) },
                  { key: "net", header: "Net pay", accessor: (p) => <span className="font-medium">{String(p.net_pay)}</span> },
                  { key: "status", header: "Status", accessor: (p) => <StatusPill status={p.status} /> },
                  { key: "date", header: "Date", accessor: (p) => fmtDate(p.created_at) },
                ]}
                data={payslips}
                keyAccessor={(p) => p.id}
                caption="Payslips"
                sortable={false}
              />
            )}
          </>
        )}
      </SectionCard>

      {/* Leave */}
      <SectionCard compact
        title="Leave"
        description="Leave balances by type and the leave request flow. Requests are created in Pending state and routed to your manager."
      >
        {!canWorkforce ? (
          <div className="p-5"><EmptyState title="Leave is available to workforce roles" description="Your role does not read leave." /></div>
        ) : loading ? (
          <LoadingRegion label="Loading leave…"><TableSkeleton rows={3} cols={5} /></LoadingRegion>
        ) : errors.leaveBalances || errors.leaveRequests || errors.leaveTypes ? (
          <div className="p-5"><Alert tone="error">{errors.leaveBalances || errors.leaveRequests || errors.leaveTypes}</Alert></div>
        ) : (
          <>
            <div className="p-5 border-b border-border">
              <div className="flex flex-wrap gap-3 items-end">
                <div className="min-w-[200px] flex-1"><Field label="Leave type" htmlFor="leave-type" required><Select id="leave-type" value={leaveForm.leave_type_id} onChange={(e) => setLeaveForm((f) => ({ ...f, leave_type_id: e.target.value }))} required><option value="">Select a leave type…</option>{leaveTypes.map((t) => (<option key={t.id} value={t.id}>{t.name}</option>))}</Select></Field></div>
                <div className="min-w-[140px]"><Field label="From" htmlFor="leave-from" required><Input id="leave-from" type="date" value={leaveForm.start_date} onChange={(e) => setLeaveForm((f) => ({ ...f, start_date: e.target.value }))} required /></Field></div>
                <div className="min-w-[140px]"><Field label="To" htmlFor="leave-to" required><Input id="leave-to" type="date" value={leaveForm.end_date} onChange={(e) => setLeaveForm((f) => ({ ...f, end_date: e.target.value }))} required /></Field></div>
                <Button type="submit" loading={busy === "leave"} form="leave-request-form">Request leave</Button>
              </div>
            </div>

            {formErrors.leave && <p className="text-sm text-error-text mb-3" role="alert">{formErrors.leave}</p>}
            <form id="leave-request-form" onSubmit={handleSubmitLeaveRequest} className="p-5 border-t border-border">
              <div className="mt-3"><Field label="Reason" htmlFor="leave-reason2" required><Textarea id="leave-reason2" value={leaveForm.reason} onChange={(e) => setLeaveForm((f) => ({ ...f, reason: e.target.value }))} rows={2} required /></Field></div>
              <div className="mt-3"><Button type="submit" loading={busy === "leave"}>Submit leave request</Button></div>
            </form>

            <div className="p-5 border-t border-border">
              <h3 className="text-sm font-semibold mb-2">Balances</h3>
              {leaveBalances.length === 0 ? (
                <div className="p-4 text-sm text-text-secondary">No leave balances found for the current year.</div>
              ) : (
                <Table
                columns={[
                  { key: "type", header: "Leave type", accessor: (b) => b.leave_type_name ?? "\u2014" },
                  { key: "year", header: "Year", accessor: (b) => b.entitlement_year },
                  { key: "entitled", header: "Entitled", accessor: (b) => String(b.entitled_days) },
                  { key: "used", header: "Used", accessor: (b) => String(b.used_days) },
                  { key: "remaining", header: "Remaining", accessor: (b) => <span className="font-medium">{String(b.available_days)}</span> },
                ]}
                data={leaveBalances}
                keyAccessor={(b) => b.id}
                caption="Leave balances"
                sortable={false}
              />
              )}
            </div>

            <div className="p-5 border-t border-border">
              <h3 className="text-sm font-semibold mb-2">Your requests</h3>
              {leaveRequests.length === 0 ? (
                <div className="p-4 text-sm text-text-secondary">No leave requests yet.</div>
              ) : (
                <Table
                columns={[
                  { key: "type", header: "Leave type", accessor: (r) => leaveTypes.find((t) => t.id === r.leave_type_id)?.name ?? "\u2014" },
                  { key: "from", header: "From", accessor: (r) => fmtDate(r.start_date) },
                  { key: "to", header: "To", accessor: (r) => fmtDate(r.end_date) },
                  { key: "days", header: "Days", accessor: (r) => String(r.working_days) },
                  { key: "status", header: "Status", accessor: (r) => <StatusPill status={r.status} /> },
                  { key: "decided", header: "Decided", accessor: (r) => fmtDate(r.decided_at) },
                ]}
                data={leaveRequests}
                keyAccessor={(r) => r.id}
                caption="Leave requests"
                sortable={false}
              />
              )}
            </div>
          </>
        )}
      </SectionCard>
    </Layout>
  )
}
