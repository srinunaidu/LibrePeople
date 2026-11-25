import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react"
import { useLocation, useNavigate } from "react-router-dom"
import { Layout } from "@/components/Layout"
import {Alert,
  Button,
  Card,
  EmptyState,
  Input,
  LoadingRegion,
  Modal,
  ModalContent,
  ModalDescription,
  ModalHeader,
  ModalTitle,
  PageHeader,
  Select,
  SectionCard,
  Table,
  TableSkeleton, RetryableAlert} from "@/components/ui"
import { Field } from "@/components/ui/layout"
import { StatusPill } from "@/components/ui/status-pill"
import { useAuth } from "@/context/AuthContext"
import api, { errorMessage } from "@/lib/api"
import { fetchEmployeePage } from "@/lib/employees"
import type { Department, Employee, EmployeeHistoryEntry, Job } from "@/types"

interface Location {
  id: number
  name: string
  code: string
  address?: string | null
  city?: string | null
  country?: string | null
  timezone: string
  is_active: boolean
}

/**
 * One employee document, as `POST /core-hr/employee-documents` stores it.
 *
 * The product does not upload a file here: the storage is the customer's, and
 * the record points at the object it already holds. That is why the form asks
 * for a storage URL rather than a file — and why this is honest about being a
 * register, not an uploader.
 */
interface EmployeeDocument {
  id: number
  employee_id: number
  document_type: string
  file_name: string
  storage_url: string
  status: string
  expiry_date?: string | null
  uploaded_at?: string | null
}

interface Position {
  id: number
  code: string
  title: string
  job_id: number
  department_id: number
  location_id?: number | null
  reports_to_position_id?: number | null
  fte: number | string
  is_active: boolean
}

interface CostCenter {
  id: number
  code: string
  name: string
  department_id?: number | null
  is_active: boolean
}

const EMPLOYEE_STATUSES = ["Active", "On Leave", "Terminated", "Rehired"]
const EMPLOYMENT_TYPES = ["Full-time", "Part-time", "Contract", "Intern"]

/** Today in the form the date input speaks; a future date is refused by the server. */
const todayISO = () => new Date().toISOString().slice(0, 10)

/**
 * The most rows one directory read asks for. The contract caps `page_size` at
 * 200; asking for the maximum keeps a large tenant to a handful of reads. The
 * screen pages with `page` and knows `meta.total`, so it can say how many
 * employees exist without reading them all.
 */
const DIRECTORY_PAGE_SIZE = 200

/** Tabs are addressed by path so every sidebar link lands on a real URL. */
const TABS = [
  "directory",
  "departments",
  "jobs",
  "locations",
  "positions",
  "cost-centers",
] as const
type TabKey = (typeof TABS)[number]

function tabFromPath(pathname: string): TabKey {
  const segment = pathname.split("/").filter(Boolean).pop() ?? ""
  return (TABS as readonly string[]).includes(segment)
    ? (segment as TabKey)
    : "directory"
}

// --- the reference entities ------------------------------------------------

type EntityKind = "department" | "job" | "location" | "position" | "costCenter"

interface EditorState {
  kind: EntityKind
  row?: { id: number } & Record<string, any>
}

/** Where each entity lives, so one editor can drive all five. */
const ENDPOINT: Record<EntityKind, { create: string; item: (id: number) => string }> = {
  department: { create: "/departments/", item: (id) => `/departments/${id}` },
  job: { create: "/jobs/", item: (id) => `/jobs/${id}` },
  location: { create: "/core-hr/locations", item: (id) => `/core-hr/locations/${id}` },
  position: { create: "/core-hr/positions", item: (id) => `/core-hr/positions/${id}` },
  costCenter: {
    create: "/core-hr/cost-centers",
    item: (id) => `/core-hr/cost-centers/${id}`,
  },
}

const LABEL: Record<EntityKind, string> = {
  department: "Department",
  job: "Job",
  location: "Location",
  position: "Position",
  costCenter: "Cost centre",
}

/** The fields the server takes as an id or a number rather than as text. */
const NUMERIC_FIELDS: Record<EntityKind, string[]> = {
  department: [],
  job: ["department_id", "min_salary", "max_salary"],
  location: [],
  position: ["job_id", "department_id", "location_id", "reports_to_position_id", "fte"],
  costCenter: ["department_id"],
}

interface FieldSpec {
  name: string
  label: string
  type?: "text" | "number" | "select"
  required?: boolean
  placeholder?: string
  step?: string
  min?: string
  max?: string
  options?: { value: string; label: string }[]
}

/** Prefix families the server auto-generates when the code is left blank. */
const AUTO_CODE: Partial<Record<EntityKind, string>> = {
  department: "DEP-0004",
  job: "JOB-0004",
  location: "LOC-0004",
  position: "POS-0004",
  costCenter: "CC-0004",
}

function fieldsFor(
  kind: EntityKind,
  context: {
    departments: Department[]
    jobs: Job[]
    locations: Location[]
    positions: Position[]
    excludeId?: number
    creating?: boolean
  }
): FieldSpec[] {
  const departmentOptions = context.departments.map((d) => ({
    value: String(d.id),
    label: d.is_active ? d.name : `${d.name} (archived)`,
  }))
  const jobOptions = context.jobs.map((j) => ({
    value: String(j.id),
    label: j.is_active ? j.title : `${j.title} (archived)`,
  }))
  const locationOptions = context.locations.map((l) => ({
    value: String(l.id),
    label: l.is_active ? l.name : `${l.name} (archived)`,
  }))
  // A position may not report to itself; the server refuses it, and the form
  // does not offer it.
  const positionOptions = context.positions
    .filter((p) => p.id !== context.excludeId)
    .map((p) => ({
      value: String(p.id),
      label: p.is_active ? `${p.code} — ${p.title}` : `${p.code} — ${p.title} (archived)`,
    }))

  // On create the code is optional: the server auto-generates the next free
  // identifier in the prefix family (app/core/ids.py). On edit it is
  // required — an existing row already owns a code.
  const auto = (spec: FieldSpec): FieldSpec =>
    context.creating
      ? { ...spec, required: false, placeholder: `Auto (${AUTO_CODE[kind] ?? "ABC-0001"})` }
      : spec

  switch (kind) {
    case "department":
      return [
        { name: "name", label: "Name", required: true },
        auto({ name: "code", label: "Code", required: true, placeholder: "OPS" }),
        { name: "description", label: "Description" },
      ]
    case "job":
      return [
        { name: "title", label: "Title", required: true },
        auto({ name: "code", label: "Code", required: true, placeholder: "ENG-01" }),
        {
          name: "department_id",
          label: "Department",
          type: "select",
          required: true,
          options: departmentOptions,
        },
        { name: "min_salary", label: "Minimum salary", type: "number", min: "0", step: "0.01" },
        { name: "max_salary", label: "Maximum salary", type: "number", min: "0", step: "0.01" },
      ]
    case "location":
      return [
        { name: "name", label: "Name", required: true },
        auto({ name: "code", label: "Code", required: true, placeholder: "BLR" }),
        { name: "city", label: "City" },
        { name: "country", label: "Country" },
        { name: "timezone", label: "Timezone", required: true, placeholder: "Asia/Kolkata" },
        { name: "address", label: "Address" },
      ]
    case "position":
      return [
        auto({ name: "code", label: "Code", required: true, placeholder: "POS-01" }),
        { name: "title", label: "Title", required: true },
        { name: "job_id", label: "Job", type: "select", required: true, options: jobOptions },
        {
          name: "department_id",
          label: "Department",
          type: "select",
          required: true,
          options: departmentOptions,
        },
        { name: "location_id", label: "Location", type: "select", options: locationOptions },
        {
          name: "reports_to_position_id",
          label: "Reports to",
          type: "select",
          options: positionOptions,
        },
        {
          name: "fte",
          label: "FTE",
          type: "number",
          required: true,
          min: "0.01",
          max: "1",
          step: "0.01",
        },
      ]
    case "costCenter":
      return [
        auto({ name: "code", label: "Code", required: true, placeholder: "CC-01" }),
        { name: "name", label: "Name", required: true },
        {
          name: "department_id",
          label: "Department",
          type: "select",
          options: departmentOptions,
        },
      ]
  }
}

function initialValues(
  kind: EntityKind,
  row?: Record<string, any>
): Record<string, string> {
  const source = row ?? {}
  const get = (name: string, fallback = "") =>
    source[name] === null || source[name] === undefined ? fallback : String(source[name])

  switch (kind) {
    case "department":
      return { name: get("name"), code: get("code"), description: get("description") }
    case "job":
      return {
        title: get("title"),
        code: get("code"),
        department_id: get("department_id"),
        min_salary: get("min_salary"),
        max_salary: get("max_salary"),
      }
    case "location":
      return {
        name: get("name"),
        code: get("code"),
        city: get("city"),
        country: get("country"),
        timezone: get("timezone", "UTC"),
        address: get("address"),
      }
    case "position":
      return {
        code: get("code"),
        title: get("title"),
        job_id: get("job_id"),
        department_id: get("department_id"),
        location_id: get("location_id"),
        reports_to_position_id: get("reports_to_position_id"),
        fte: get("fte", "1"),
      }
    case "costCenter":
      return {
        code: get("code"),
        name: get("name"),
        department_id: get("department_id"),
      }
  }
}

function payloadFrom(kind: EntityKind, values: Record<string, string>): Record<string, unknown> {
  const numeric = NUMERIC_FIELDS[kind]
  const payload: Record<string, unknown> = {}
  for (const [name, raw] of Object.entries(values)) {
    const text = raw.trim()
    payload[name] = numeric.includes(name)
      ? text === ""
        ? null
        : Number(text)
      : text === ""
      ? null
      : text
  }
  // Codes are compared case-insensitively by the server; storing them upper
  // case keeps the catalogue readable.
  if (typeof payload.code === "string") payload.code = payload.code.toUpperCase()
  // A location has a timezone and a position has an FTE; neither column takes
  // null, so a cleared field falls back to the value the server defaults to.
  if (kind === "location" && !payload.timezone) payload.timezone = "UTC"
  if (kind === "position" && payload.fte == null) payload.fte = 1
  return payload
}

function ReferenceToolbar({
  title,
  description,
  canManage,
  addLabel,
  onAdd,
}: {
  title: string
  description: string
  canManage: boolean
  addLabel: string
  onAdd: () => void
}) {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 className="mk-h3 text-fg">{title}</h2>
        <p className="text-xs text-fg-muted">{description}</p>
      </div>
      {canManage && (
        <Button size="sm" onClick={onAdd}>
          {addLabel}
        </Button>
      )}
    </div>
  )
}

function RowActions({
  label,
  active,
  busy,
  onEdit,
  onToggle,
  onDelete,
}: {
  label: string
  active: boolean
  busy: boolean
  onEdit: () => void
  onToggle: () => void
  onDelete: () => void
}) {
  return (
    <div className="flex justify-end gap-1">
      <Button
        variant="ghost"
        size="sm"
        onClick={onEdit}
        disabled={busy}
        aria-label={`Edit ${label}`}
      >
        Edit
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onClick={onToggle}
        disabled={busy}
        aria-label={`${active ? "Archive" : "Restore"} ${label}`}
      >
        {active ? "Archive" : "Restore"}
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onClick={onDelete}
        disabled={busy}
        aria-label={`Delete ${label}`}
        className="text-error-text"
      >
        Delete
      </Button>
    </div>
  )
}

/**
 * People area.
 *
 * Tabs cover the employee directory and the five records that describe the
 * workforce around it: departments, job definitions, locations, positions and
 * cost centres. Each of the five can be created, edited, archived, restored and
 * — only while nothing points at it — deleted, against the same rules the
 * server enforces.
 *
 * The server scopes the employee list to what the caller may see (an
 * Associate sees only themselves, a Manager sees their reporting line, HR
 * and SuperAdmin see everyone). The UI mirrors that by only offering the
 * "Add employee" action to roles the server will accept it from — the
 * server remains the authority.
 */
export default function People() {
  const { user } = useAuth()
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const canManage = user?.role === "SuperAdmin" || user?.role === "HR"

  const tab = tabFromPath(pathname)
  const setTab = (next: string) => {
    // A refusal from one tab is not about the next one.
    setActionError(null)
    setNotice(null)
    navigate(next === "directory" ? "/people" : `/people/${next}`)
  }
  const [employees, setEmployees] = useState<Employee[]>([])
  const [departments, setDepartments] = useState<Department[]>([])
  const [jobs, setJobs] = useState<Job[]>([])
  const [locations, setLocations] = useState<Location[]>([])
  const [positions, setPositions] = useState<Position[]>([])
  const [costCenters, setCostCenters] = useState<CostCenter[]>([])

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const [query, setQuery] = useState("")
  const [statusFilter, setStatusFilter] = useState("")
  const [departmentFilter, setDepartmentFilter] = useState("")

  const [selected, setSelected] = useState<Employee | null>(null)
  // The documents of the employee whose detail panel is open. Read when the
  // panel opens, so the panel never shows another employee's documents.
  const [documents, setDocuments] = useState<EmployeeDocument[]>([])
  const [docsLoading, setDocsLoading] = useState(false)
  const [docsError, setDocsError] = useState<string | null>(null)
  const [docSaving, setDocSaving] = useState(false)
  const [docForm, setDocForm] = useState({
    document_type: "Contract",
    file_name: "",
    storage_url: "",
    expiry_date: "",
  })
  // The employment history and the status change. Both are read and written
  // for the selected employee only, so the panel never shows another person's
  // changes.
  const [historyRows, setHistoryRows] = useState<EmployeeHistoryEntry[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyError, setHistoryError] = useState<string | null>(null)
  // The form covers the dated fields, not only status: the operation records
  // job, department, manager, salary and employment type as history too, and
  // a screen that offered only status would leave most of it unusable.
  const [employmentForm, setEmploymentForm] = useState({
    status: "Active",
    employment_type: "Full-time",
    job_id: "",
    department_id: "",
    manager_id: "",
    salary: "",
    effective_from: todayISO(),
    reason: "",
  })
  const [statusSaving, setStatusSaving] = useState(false)
  const [statusError, setStatusError] = useState<string | null>(null)
  const [statusNotice, setStatusNotice] = useState<string | null>(null)
  // The directory is read in pages and the server applies the filters, so a
  // search reaches employees the screen has not loaded. `meta.total` is the
  // number this caller may see; the screen says how many it has read and
  // offers the next page until it has read them all. It never calls a page
  // "everyone".
  const [directoryPage, setDirectoryPage] = useState(1)
  const [directoryTotal, setDirectoryTotal] = useState(0)
  const [loadingMore, setLoadingMore] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Reference editor state
  const [editor, setEditor] = useState<EditorState | null>(null)
  const [editorValues, setEditorValues] = useState<Record<string, string>>({})
  const [editorError, setEditorError] = useState<string | null>(null)
  const [rowBusy, setRowBusy] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const [form, setForm] = useState({
    employee_id: "",
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    hire_date: "",
    job_id: "",
    department_id: "",
    manager_id: "",
    status: "Active",
  })

  // Reference data (departments, jobs) is fetched independently of the
  // directory list on purpose: one failing endpoint — say, an /employees 403
  // for the account's role — must not blank the Department dropdown in the
  // add-employee form.
  const loadReference = useCallback(async () => {
    const [deptRes, jobRes] = await Promise.allSettled([
      // The maintenance tabs have to see an archived row in order to
      // restore it; the forms that offer a department filter it back out.
      api.get<Department[]>("/departments/", { params: { include_inactive: true } }),
      api.get<Job[]>("/jobs/", { params: { include_inactive: true } }),
    ])
    if (deptRes.status === "fulfilled") setDepartments(deptRes.value.data)
    if (jobRes.status === "fulfilled") setJobs(jobRes.value.data)
    if (deptRes.status === "rejected" && jobRes.status === "rejected") {
      setError(
        errorMessage(
          deptRes.reason,
          "Could not load the departments and jobs the directory uses.",
        ),
      )
    }
  }, [])

  const loadDirectory = useCallback(
    async (page = 1, append = false) => {
      if (append) setLoadingMore(true)
      else setLoading(true)
      if (!append) setError(null)
      try {
        const data = await fetchEmployeePage({
          page,
          page_size: DIRECTORY_PAGE_SIZE,
          search: query.trim() || undefined,
          status: statusFilter || undefined,
          department_id: departmentFilter ? Number(departmentFilter) : undefined,
        })
        setEmployees((current) => {
          if (!append) return data.items
          // A row can appear twice if one was added between two page reads;
          // keep the list a list of distinct people.
          const seen = new Set(current.map((employee) => employee.id))
          return [...current, ...data.items.filter((employee) => !seen.has(employee.id))]
        })
        setDirectoryPage(data.meta.page)
        setDirectoryTotal(data.meta.total)
      } catch (err) {
        if (!append) {
          setEmployees([])
          setDirectoryTotal(0)
        }
        setError(errorMessage(err, "Could not load the people directory."))
      } finally {
        setLoading(false)
        setLoadingMore(false)
      }
    },
    [query, statusFilter, departmentFilter],
  )

  const loadAll = useCallback(async () => {
    await Promise.all([loadReference(), loadDirectory(1)])
  }, [loadReference, loadDirectory])

  useEffect(() => {
    loadReference()
  }, [loadReference])

  // A filter change asks the server for a new first page. The short delay is
  // a debounce for the search box; the select filters land in the same path.
  useEffect(() => {
    const timer = setTimeout(() => {
      void loadDirectory(1)
    }, 250)
    return () => clearTimeout(timer)
  }, [loadDirectory])

  // The three reference lists below the directory are fetched lazily, when
  // their tab is first opened, and always including archived rows so that the
  // maintenance list can restore one.
  const loadLocations = useCallback(async () => {
    const res = await api.get<Location[]>("/core-hr/locations", {
      params: { include_inactive: true },
    })
    setLocations(res.data)
  }, [])

  const loadPositions = useCallback(async () => {
    const res = await api.get<Position[]>("/core-hr/positions", {
      params: { include_inactive: true },
    })
    setPositions(res.data)
  }, [])

  const loadCostCenters = useCallback(async () => {
    const res = await api.get<CostCenter[]>("/core-hr/cost-centers", {
      params: { include_inactive: true },
    })
    setCostCenters(res.data)
  }, [])

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        if (tab === "locations" && locations.length === 0) {
          await loadLocations()
        } else if (tab === "positions" && positions.length === 0) {
          await loadPositions()
        } else if (tab === "cost-centers" && costCenters.length === 0) {
          await loadCostCenters()
        }
      } catch (err) {
        if (!cancelled) {
          setError(errorMessage(err, "Could not load the reference data."))
        }
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [tab, locations.length, positions.length, costCenters.length, loadLocations, loadPositions, loadCostCenters])

  /** Read the next page of the directory and append it. */
  const loadMoreEmployees = async () => {
    if (loadingMore) return
    await loadDirectory(directoryPage + 1, true)
  }

  const openEmployee = useCallback(async (employee: Employee | null) => {
    setSelected(employee)
    setDocuments([])
    setDocsError(null)
    setDocForm({ document_type: "Contract", file_name: "", storage_url: "", expiry_date: "" })
    setHistoryRows([])
    setHistoryError(null)
    setHistoryLoading(false)
    setStatusError(null)
    setStatusNotice(null)
    if (!employee) return
    setEmploymentForm({
      status: employee.status,
      employment_type: employee.employment_type || "",
      job_id: String(employee.job_id),
      department_id: String(employee.department_id),
      manager_id: employee.manager_id ? String(employee.manager_id) : "",
      salary: employee.salary != null ? String(employee.salary) : "",
      effective_from: todayISO(),
      reason: "",
    })

    setDocsLoading(true)
    try {
      const response = await api.get<EmployeeDocument[]>("/core-hr/employee-documents", {
        params: { employee_id: employee.id },
      })
      setDocuments(response.data)
    } catch (err) {
      setDocsError(errorMessage(err, "This employee's documents could not be read."))
    } finally {
      setDocsLoading(false)
    }

    setHistoryLoading(true)
    try {
      const response = await api.get<EmployeeHistoryEntry[]>(
        `/employees/${employee.id}/history`,
      )
      setHistoryRows(response.data)
    } catch (err) {
      setHistoryError(
        errorMessage(err, "This employee's employment history could not be read."),
      )
    } finally {
      setHistoryLoading(false)
    }
  }, [])

  async function changeEmployment(event: FormEvent) {
    event.preventDefault()
    if (!selected || statusSaving) return

    // Send only what the operator changed. Sending every field would write a
    // history row for an untouched value (or, worse, silently change a field
    // whose option is not in the list). The comparison is against the record
    // the panel opened, not against the last render.
    const changed: Record<string, unknown> = {}
    if (employmentForm.status !== selected.status) {
      changed.status = employmentForm.status
    }
    if (employmentForm.employment_type !== (selected.employment_type || "")) {
      changed.employment_type = employmentForm.employment_type || null
    }
    // A select with no option loaded (a failed reference read) must not
    // become `0` and turn a status change into a 422 about a job id.
    if (employmentForm.job_id && Number(employmentForm.job_id) !== selected.job_id) {
      changed.job_id = Number(employmentForm.job_id)
    }
    if (
      employmentForm.department_id &&
      Number(employmentForm.department_id) !== selected.department_id
    ) {
      changed.department_id = Number(employmentForm.department_id)
    }
    if (
      employmentForm.manager_id !==
      (selected.manager_id ? String(selected.manager_id) : "")
    ) {
      changed.manager_id = employmentForm.manager_id
        ? Number(employmentForm.manager_id)
        : null
    }
    const salaryText = employmentForm.salary.trim()
    if (salaryText === "") {
      // Clearing a recorded salary is a change; an empty field on a record
      // with no salary is not.
      if (selected.salary != null) changed.salary = null
    } else if (Number(salaryText) !== Number(selected.salary ?? NaN)) {
      changed.salary = Number(salaryText)
    }

    if (Object.keys(changed).length === 0) {
      setStatusError(null)
      setStatusNotice("Nothing to record: the record already holds those values.")
      return
    }

    changed.effective_from = employmentForm.effective_from || undefined
    if (employmentForm.reason.trim()) changed.reason = employmentForm.reason.trim()

    setStatusSaving(true)
    setStatusError(null)
    setStatusNotice(null)
    try {
      const response = await api.patch<Employee>(`/employees/${selected.id}`, changed)
      const updated = response.data
      setSelected(updated)
      setEmployees((current) =>
        current.map((employee) => (employee.id === updated.id ? updated : employee)),
      )
      setEmploymentForm((current) => ({
        ...current,
        status: updated.status,
        employment_type: updated.employment_type || "",
        job_id: String(updated.job_id),
        department_id: String(updated.department_id),
        manager_id: updated.manager_id ? String(updated.manager_id) : "",
        salary: updated.salary != null ? String(updated.salary) : "",
        reason: "",
      }))
      setStatusNotice("Employment updated. The change is in the history below.")
      const rows = await api.get<EmployeeHistoryEntry[]>(
        `/employees/${updated.id}/history`,
      )
      setHistoryRows(rows.data)
    } catch (err) {
      setStatusError(errorMessage(err, "The employment change was refused."))
    } finally {
      setStatusSaving(false)
    }
  }

  const addDocument = async (event: FormEvent) => {
    event.preventDefault()
    if (!selected) return
    setDocSaving(true)
    setDocsError(null)
    try {
      const response = await api.post<EmployeeDocument>("/core-hr/employee-documents", {
        employee_id: selected.id,
        document_type: docForm.document_type,
        file_name: docForm.file_name,
        storage_url: docForm.storage_url,
        expiry_date: docForm.expiry_date || null,
      })
      setDocuments((current) => [response.data, ...current])
      setDocForm({ document_type: "Contract", file_name: "", storage_url: "", expiry_date: "" })
      setNotice("Document recorded.")
    } catch (err) {
      setDocsError(errorMessage(err, "The document could not be recorded."))
    } finally {
      setDocSaving(false)
    }
  }

  const deptById = useMemo(
    () => new Map(departments.map((d) => [d.id, d])),
    [departments]
  )
  // The maintenance lists include archived rows so they can be restored; the
  // forms that offer a value must not offer an archived one.
  const activeDepartments = useMemo(
    () => departments.filter((d) => d.is_active),
    [departments]
  )
  const activeJobs = useMemo(() => jobs.filter((j) => j.is_active), [jobs])
  const jobById = useMemo(() => new Map(jobs.map((j) => [j.id, j])), [jobs])
  const locationById = useMemo(
    () => new Map(locations.map((l) => [l.id, l])),
    [locations]
  )
  const employeeById = useMemo(
    () => new Map(employees.map((e) => [e.id, e])),
    [employees]
  )

  const hasMoreEmployees = employees.length < directoryTotal

  function resetForm() {
    setForm({
      employee_id: "",
      first_name: "",
      last_name: "",
      email: "",
      phone: "",
      hire_date: "",
      job_id: "",
      department_id: "",
      manager_id: "",
      status: "Active",
    })
    setFormError(null)
  }

  function validateEmployeeForm(): string | null {
    // Client-side first line of defence: whitespace-only values and a
    // malformed email are stopped here instead of round-tripping to the API
    // where the same fields are validated again.
    if (!form.first_name.trim()) return "First name is required."
    if (!form.last_name.trim()) return "Last name is required."
    if (!/^\S+@\S+\.\S+$/.test(form.email.trim())) {
      return "Enter a valid email address — the directory keys the record on it."
    }
    if (!form.hire_date) return "Hire date is required."
    if (!form.department_id) return "Choose a department."
    if (!form.job_id) return "Choose a job."
    return null
  }

  async function createEmployee(e: React.FormEvent) {
    e.preventDefault()
    if (saving) return
    setFormError(null)
    const invalid = validateEmployeeForm()
    if (invalid) {
      setFormError(invalid)
      return
    }
    const idWasBlank = !form.employee_id.trim()
    setSaving(true)
    try {
      const created = await api.post("/employees/", {
        employee_id: form.employee_id.trim(),
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        email: form.email.trim(),
        phone: form.phone.trim() || null,
        hire_date: form.hire_date,
        job_id: Number(form.job_id),
        department_id: Number(form.department_id),
        manager_id: form.manager_id ? Number(form.manager_id) : null,
        status: form.status,
      })
      setShowCreate(false)
      resetForm()
      const generated = created.data?.employee_id
      setNotice(
        idWasBlank && generated
          ? `Employee added to the directory — ID ${generated} auto-generated.`
          : "Employee added to the directory.",
      )
      await loadAll()
    } catch (err) {
      setFormError(errorMessage(err, "Could not add the employee."))
    } finally {
      setSaving(false)
    }
  }

  const editorFields = useMemo(
    () =>
      editor
        ? fieldsFor(editor.kind, {
            departments,
            jobs,
            locations,
            positions,
            excludeId: editor.row?.id,
            creating: !editor.row,
          })
        : [],
    [editor, departments, jobs, locations, positions]
  )

  async function refreshAfterWrite(kind: EntityKind) {
    if (kind === "department" || kind === "job") {
      await loadAll()
      return
    }
    if (kind === "location") await loadLocations()
    if (kind === "position") await loadPositions()
    if (kind === "costCenter") await loadCostCenters()
  }

  function openEditor(kind: EntityKind, row?: { id: number } & Record<string, any>) {
    setEditor({ kind, row })
    setEditorValues(initialValues(kind, row))
    setEditorError(null)
    setActionError(null)
  }

  function closeEditor() {
    setEditor(null)
    setEditorValues({})
    setEditorError(null)
  }

  async function saveReference(e: React.FormEvent) {
    e.preventDefault()
    if (!editor || saving) return
    setSaving(true)
    setEditorError(null)
    try {
      const payload = payloadFrom(editor.kind, editorValues)
      const kind = editor.kind
      if (editor.row) {
        // Send only what the operator actually changed. The server writes the
        // fields it receives and nothing else, and an unchanged field cannot
        // overwrite a concurrent edit.
        const before = initialValues(kind, editor.row)
        const changed: Record<string, unknown> = {}
        for (const [name, value] of Object.entries(payload)) {
          if ((editorValues[name] ?? "") !== (before[name] ?? "")) {
            changed[name] = value
          }
        }
        if (Object.keys(changed).length === 0) {
          setEditorError("Nothing changed.")
          setSaving(false)
          return
        }
        await api.patch(ENDPOINT[kind].item(editor.row.id), changed)
        setNotice(`${LABEL[kind]} updated.`)
      } else {
        const codeWasBlank = !(editorValues.code ?? "").trim()
        const created = await api.post(ENDPOINT[kind].create, payload)
        const name = created.data.code ?? created.data.name ?? created.data.title
        setNotice(
          codeWasBlank && created.data.code
            ? `${LABEL[kind]} "${name}" created — code auto-generated — it is selectable in the forms now.`
            : `${LABEL[kind]} "${name}" created — it is selectable in the forms now.`,
        )
        if (kind === "department") {
          // Preselect the fresh department so the add-employee form can use it
          // immediately; the operator sees the dropdown filled.
          setForm((f) => ({ ...f, department_id: String(created.data.id) }))
        }
      }
      closeEditor()
      await refreshAfterWrite(kind)
    } catch (err) {
      setEditorError(
        errorMessage(err, `Could not save the ${LABEL[editor.kind].toLowerCase()}.`),
      )
    } finally {
      setSaving(false)
    }
  }

  async function toggleReference(
    kind: EntityKind,
    row: { id: number; code: string; is_active: boolean }
  ) {
    setRowBusy(`${kind}:${row.id}`)
    setActionError(null)
    try {
      await api.patch(ENDPOINT[kind].item(row.id), { is_active: !row.is_active })
      setNotice(
        row.is_active
          ? `${LABEL[kind]} ${row.code} archived — the forms no longer offer it.`
          : `${LABEL[kind]} ${row.code} restored.`,
      )
      await refreshAfterWrite(kind)
    } catch (err) {
      setActionError(
        errorMessage(
          err,
          `Could not ${row.is_active ? "archive" : "restore"} ${LABEL[kind].toLowerCase()} ${row.code}.`,
        ),
      )
    } finally {
      setRowBusy(null)
    }
  }

  const [deleteTarget, setDeleteTarget] = useState<{ kind: EntityKind; row: { id: number; code: string } } | null>(null)

  async function deleteReference(kind: EntityKind, row: { id: number; code: string }) {
    setDeleteTarget({ kind, row })
  }

  async function confirmDelete() {
    if (!deleteTarget) return
    const { kind, row } = deleteTarget
    setDeleteTarget(null)
    setRowBusy(`${kind}:${row.id}`)
    setActionError(null)
    try {
      await api.delete(ENDPOINT[kind].item(row.id))
      setNotice(`${LABEL[kind]} ${row.code} deleted.`)
      await refreshAfterWrite(kind)
    } catch (err) {
      setActionError(
        errorMessage(err, `Could not delete ${LABEL[kind].toLowerCase()} ${row.code}.`),
      )
    } finally {
      setRowBusy(null)
    }
  }

  // Build table columns for the directory
  const directoryColumns = useMemo(() => [
    { key: "id", header: "ID", accessor: (e: Employee) => <span className="font-mono text-xs">{e.employee_id}</span> },
    { key: "name", header: "Name", accessor: (e: Employee) => (
      <div>
        <button
          type="button"
          onClick={() => openEmployee(e)}
          className="text-left font-medium text-fg hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600"
        >
          {e.first_name} {e.last_name}
        </button>
        <span className="block text-xs text-fg-muted">{e.email}</span>
      </div>
    ) },
    { key: "job", header: "Job", accessor: (e: Employee) => <span className="text-fg-muted">{jobById.get(e.job_id)?.title ?? "—"}</span> },
    { key: "department", header: "Department", accessor: (e: Employee) => <span className="text-fg-muted">{deptById.get(e.department_id)?.name ?? "—"}</span> },
    { key: "manager", header: "Manager", accessor: (e: Employee) => {
      const manager = e.manager_id ? employeeById.get(e.manager_id) : undefined
      return <span className="text-fg-muted">{manager ? `${manager.first_name} ${manager.last_name}` : "—"}</span>
    } },
    { key: "hired", header: "Hired", accessor: (e: Employee) => <span className="text-fg-muted">{e.hire_date}</span> },
    { key: "status", header: "Status", accessor: (e: Employee) => <StatusPill status={e.status} dot /> },
  ], [jobById, deptById, employeeById])

  // Build table columns for departments
  const departmentsColumns = useMemo(() => [
    { key: "code", header: "Code", accessor: (d: Department) => <span className="font-mono text-xs">{d.code}</span> },
    { key: "name", header: "Name", accessor: (d: Department) => d.name },
    { key: "description", header: "Description", accessor: (d: Department) => d.description ?? "—" },
    { key: "status", header: "Status", accessor: (d: Department) => <StatusPill status={d.is_active ? "Active" : "Draft"} /> },
    ...(canManage ? [{
      key: "actions",
      header: "Actions",
      accessor: (d: Department) => (
        <RowActions
          label={`department ${d.code}`}
          active={d.is_active}
          busy={rowBusy === `department:${d.id}`}
          onEdit={() => openEditor("department", d)}
          onToggle={() => toggleReference("department", d)}
          onDelete={() => deleteReference("department", d)}
        />
      ),
    }] : []),
  ], [canManage, rowBusy])

  // Build table columns for jobs
  const jobsColumns = useMemo(() => [
    { key: "code", header: "Code", accessor: (j: Job) => <span className="font-mono text-xs">{j.code}</span> },
    { key: "title", header: "Title", accessor: (j: Job) => j.title },
    { key: "department", header: "Department", accessor: (j: Job) => deptById.get(j.department_id)?.name ?? "—" },
    { key: "salary", header: "Salary range", accessor: (j: Job) =>
      j.min_salary != null || j.max_salary != null
        ? `${j.min_salary ?? "—"} – ${j.max_salary ?? "—"}`
        : "—"
    },
    { key: "status", header: "Status", accessor: (j: Job) => <StatusPill status={j.is_active ? "Active" : "Draft"} /> },
    ...(canManage ? [{
      key: "actions",
      header: "Actions",
      accessor: (j: Job) => (
        <RowActions
          label={`job ${j.code}`}
          active={j.is_active}
          busy={rowBusy === `job:${j.id}`}
          onEdit={() => openEditor("job", j)}
          onToggle={() => toggleReference("job", j)}
          onDelete={() => deleteReference("job", j)}
        />
      ),
    }] : []),
  ], [deptById, canManage, rowBusy])

  // Build table columns for locations
  const locationsColumns = useMemo(() => [
    { key: "code", header: "Code", accessor: (l: Location) => <span className="font-mono text-xs">{l.code}</span> },
    { key: "name", header: "Name", accessor: (l: Location) => l.name },
    { key: "city", header: "City", accessor: (l: Location) => l.city ?? "—" },
    { key: "country", header: "Country", accessor: (l: Location) => l.country ?? "—" },
    { key: "timezone", header: "Timezone", accessor: (l: Location) => l.timezone },
    { key: "status", header: "Status", accessor: (l: Location) => <StatusPill status={l.is_active ? "Active" : "Draft"} /> },
    ...(canManage ? [{
      key: "actions",
      header: "Actions",
      accessor: (l: Location) => (
        <RowActions
          label={`location ${l.code}`}
          active={l.is_active}
          busy={rowBusy === `location:${l.id}`}
          onEdit={() => openEditor("location", l)}
          onToggle={() => toggleReference("location", l)}
          onDelete={() => deleteReference("location", l)}
        />
      ),
    }] : []),
  ], [canManage, rowBusy])

  // Build table columns for positions
  const positionsColumns = useMemo(() => [
    { key: "code", header: "Code", accessor: (pos: Position) => <span className="font-mono text-xs">{pos.code}</span> },
    { key: "title", header: "Title", accessor: (pos: Position) => pos.title },
    { key: "job", header: "Job", accessor: (pos: Position) => jobById.get(pos.job_id)?.title ?? "—" },
    { key: "department", header: "Department", accessor: (pos: Position) => deptById.get(pos.department_id)?.name ?? "—" },
    { key: "location", header: "Location", accessor: (pos: Position) => pos.location_id ? (locationById.get(pos.location_id)?.name ?? "—") : "—" },
    { key: "fte", header: "FTE", accessor: (pos: Position) => String(pos.fte) },
    { key: "status", header: "Status", accessor: (pos: Position) => <StatusPill status={pos.is_active ? "Active" : "Draft"} /> },
    ...(canManage ? [{
      key: "actions",
      header: "Actions",
      accessor: (pos: Position) => (
        <RowActions
          label={`position ${pos.code}`}
          active={pos.is_active}
          busy={rowBusy === `position:${pos.id}`}
          onEdit={() => openEditor("position", pos)}
          onToggle={() => toggleReference("position", pos)}
          onDelete={() => deleteReference("position", pos)}
        />
      ),
    }] : []),
  ], [jobById, deptById, locationById, canManage, rowBusy])

  // Build table columns for cost centers
  const costCentersColumns = useMemo(() => [
    { key: "code", header: "Code", accessor: (cc: CostCenter) => <span className="font-mono text-xs">{cc.code}</span> },
    { key: "name", header: "Name", accessor: (cc: CostCenter) => cc.name },
    { key: "department", header: "Department", accessor: (cc: CostCenter) => cc.department_id ? (deptById.get(cc.department_id)?.name ?? "—") : "—" },
    { key: "status", header: "Status", accessor: (cc: CostCenter) => <StatusPill status={cc.is_active ? "Active" : "Draft"} /> },
    ...(canManage ? [{
      key: "actions",
      header: "Actions",
      accessor: (cc: CostCenter) => (
        <RowActions
          label={`cost centre ${cc.code}`}
          active={cc.is_active}
          busy={rowBusy === `costCenter:${cc.id}`}
          onEdit={() => openEditor("costCenter", cc)}
          onToggle={() => toggleReference("costCenter", cc)}
          onDelete={() => deleteReference("costCenter", cc)}
        />
      ),
    }] : []),
  ], [deptById, canManage, rowBusy])

  return (
    <Layout>
      <div className="card p-8">
        <PageHeader compact
          title="People"
          description="The employee directory and the structure that surrounds it."
          actions={
            canManage && (
              <Button
                onClick={() => {
                  resetForm()
                  setShowCreate((v) => !v)
                }}
                variant={showCreate ? "secondary" : "primary"}
              >
                {showCreate ? "Cancel" : "Add employee"}
              </Button>
            )
          }
        />

        {error && (
          <RetryableAlert err={error} title="Error" fallback="Error." />
        )}
        {notice && (
          <Alert tone="info" title="Notice">
            {notice}
          </Alert>
        )}
        {actionError && (
          <Alert tone="error" title="Error">
            {actionError}
          </Alert>
        )}

        {showCreate && canManage && (
          <Card className="mb-6">
            <h2 className="mk-h2 text-fg mb-4">New employee</h2>
            <form onSubmit={createEmployee} className="space-y-4" aria-label="Add employee">
              {formError && (
                <Alert tone="error" title="Form Error">
                  {formError}
                </Alert>
              )}
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <Field htmlFor="new-employee-id" label="Employee ID" hint="Leave blank and the ID is auto-generated">
                  <Input
                    id="new-employee-id"
                    value={form.employee_id}
                    onChange={(e) => setForm({ ...form, employee_id: e.target.value })}
                    placeholder="Auto (EMP-0007)"
                  />
                </Field>
                <Field htmlFor="new-first-name" label="First name" required>
                  <Input
                    id="new-first-name"
                    required
                    value={form.first_name}
                    onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                  />
                </Field>
                <Field htmlFor="new-last-name" label="Last name" required>
                  <Input
                    id="new-last-name"
                    required
                    value={form.last_name}
                    onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                  />
                </Field>
                <Field htmlFor="new-email" label="Email" required>
                  <Input
                    id="new-email"
                    type="email"
                    required
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                  />
                </Field>
                <Field htmlFor="new-phone" label="Phone">
                  <Input
                    id="new-phone"
                    value={form.phone}
                    onChange={(e) => setForm({ ...form, phone: e.target.value })}
                  />
                </Field>
                <Field htmlFor="new-hire-date" label="Hire date" required>
                  <Input
                    id="new-hire-date"
                    type="date"
                    required
                    value={form.hire_date}
                    onChange={(e) => setForm({ ...form, hire_date: e.target.value })}
                  />
                </Field>
                <Field htmlFor="new-department" label="Department" required>
                  <Select
                    id="new-department"
                    required
                    value={form.department_id}
                    onChange={(e) => setForm({ ...form, department_id: e.target.value })}
                  >
                    <option value="">Select a department</option>
                    {activeDepartments.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name}
                      </option>
                    ))}
                  </Select>
                  {!loading && activeDepartments.length === 0 && (
                    <p className="mt-1 text-xs text-fg-muted" role="note">
                      No departments available yet
                      {canManage
                        ? " — create one in the Departments tab below; it becomes selectable here immediately."
                        : " — ask an HR or SuperAdmin user to create one in People › Departments."}
                    </p>
                  )}
                </Field>
                <Field htmlFor="new-job" label="Job" required>
                  <Select
                    id="new-job"
                    required
                    value={form.job_id}
                    onChange={(e) => setForm({ ...form, job_id: e.target.value })}
                  >
                    <option value="">Select a job</option>
                    {activeJobs.map((j) => (
                      <option key={j.id} value={j.id}>
                        {j.title}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field htmlFor="new-manager" label="Manager">
                  <Select
                    id="new-manager"
                    value={form.manager_id}
                    onChange={(e) => setForm({ ...form, manager_id: e.target.value })}
                  >
                    <option value="">No manager</option>
                    {employees.map((e) => (
                      <option key={e.id} value={e.id}>
                        {e.first_name} {e.last_name} ({e.employee_id})
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field htmlFor="new-status" label="Status" required>
                  <Select
                    id="new-status"
                    required
                    value={form.status}
                    onChange={(e) => setForm({ ...form, status: e.target.value })}
                  >
                    {EMPLOYEE_STATUSES.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </Select>
                </Field>
              </div>
              <div className="mt-4 flex justify-end">
                <Button type="submit" loading={saving}>
                  {saving ? "Adding…" : "Add employee"}
                </Button>
              </div>
            </form>
          </Card>
        )}

        <div className="mk-reveal">
          <div role="tablist" aria-label="People sections" className="border-b border-border mb-6">
            {TABS.map((t) => (
              <button
                key={t}
                role="tab"
                aria-selected={tab === t}
                aria-controls={`panel-${t}`}
                id={`tab-${t}`}
                tabIndex={tab === t ? 0 : -1}
                onClick={() => setTab(t)}
                className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                  tab === t
                    ? "border-brand-600 text-fg"
                    : "border-transparent text-fg hover:text-fg hover:border-border"
                }`}
              >
                {t.charAt(0).toUpperCase() + t.slice(1).replace("-", " ")}
              </button>
            ))}
          </div>

          {/* Directory tab */}
          <div role="tabpanel" id="panel-directory" aria-labelledby="tab-directory" hidden={tab !== "directory"}>
            <SectionCard compact title="Employee Directory" description="Search and filter the employees visible to your account.">
              <div className="flex flex-wrap gap-3 items-end mb-4">
                <div className="flex-1 min-w-[220px]">
                  <Field htmlFor="directory-search" label="Search">
                    <Input
                      id="directory-search"
                      type="search"
                      placeholder="Name, employee number or email"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                    />
                  </Field>
                </div>
                <div className="min-w-[160px]">
                  <Field htmlFor="directory-status" label="Status">
                    <Select
                      id="directory-status"
                      value={statusFilter}
                      onChange={(e) => setStatusFilter(e.target.value)}
                    >
                      <option value="">All statuses</option>
                      {EMPLOYEE_STATUSES.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </Select>
                  </Field>
                </div>
                <div className="min-w-[160px]">
                  <Field htmlFor="directory-department" label="Department">
                    <Select
                      id="directory-department"
                      value={departmentFilter}
                      onChange={(e) => setDepartmentFilter(e.target.value)}
                    >
                      <option value="">All departments</option>
                      {activeDepartments.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name}
                        </option>
                      ))}
                    </Select>
                  </Field>
                </div>
                <Button variant="secondary" onClick={loadAll} loading={loading}>
                  Refresh
                </Button>
              </div>

              <p className="text-xs text-fg-muted mb-3" role="status">
                {loading
                  ? "Loading…"
                  : `${employees.length} of ${directoryTotal} ${
                      directoryTotal === 1 ? "employee" : "employees"
                    } shown`}
              </p>

              {loading ? (
                <LoadingRegion label="Loading employees">
                  <TableSkeleton rows={5} cols={7} />
                </LoadingRegion>
              ) : (
                <Table
                  columns={directoryColumns}
                  data={employees}
                  keyAccessor={(e: Employee) => e.id}
                  caption="Employees visible to you, with their job, department, manager and employment status."
                  sortable={false}
                  filterable={false}
                  emptyMessage={query || statusFilter || departmentFilter
                    ? "No employees match the current filters."
                    : "No employees are visible to your account yet."}
                />
              )}

              {hasMoreEmployees && (
                <div className="mt-3 flex flex-wrap items-center gap-3">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={loadMoreEmployees}
                    loading={loadingMore}
                  >
                    Load more employees
                  </Button>
                  <p className="text-xs text-fg-muted">
                    The directory is read a page at a time. Search covers the employees
                    loaded so far; load the rest to search them too.
                  </p>
                </div>
              )}
            </SectionCard>
          </div>

          {/* Departments tab */}
          <div role="tabpanel" id="panel-departments" aria-labelledby="tab-departments" hidden={tab !== "departments"}>
            <ReferenceToolbar
              title="Departments"
              description="Every employee belongs to one. Archived departments stay listed here so they can be restored."
              canManage={canManage}
              addLabel="Add department"
              onAdd={() => openEditor("department")}
            />
            {loading ? (
              <LoadingRegion label="Loading departments">
                <TableSkeleton rows={5} cols={5} />
              </LoadingRegion>
            ) : (
              <Table
                columns={departmentsColumns}
                data={departments}
                keyAccessor={(d: Department) => d.id}
                caption="Departments"
                sortable={false}
                filterable={false}
                emptyMessage="No departments have been defined."
              />
            )}
          </div>

          {/* Jobs tab */}
          <div role="tabpanel" id="panel-jobs" aria-labelledby="tab-jobs" hidden={tab !== "jobs"}>
            <ReferenceToolbar
              title="Job definitions"
              description="The titles employees, positions and requisitions point at. A job still held is archived rather than deleted."
              canManage={canManage}
              addLabel="Add job"
              onAdd={() => openEditor("job")}
            />
            {loading ? (
              <LoadingRegion label="Loading jobs">
                <TableSkeleton rows={5} cols={6} />
              </LoadingRegion>
            ) : (
              <Table
                columns={jobsColumns}
                data={jobs}
                keyAccessor={(j: Job) => j.id}
                caption="Job definitions"
                sortable={false}
                filterable={false}
                emptyMessage="No jobs have been defined."
              />
            )}
          </div>

          {/* Locations tab */}
          <div role="tabpanel" id="panel-locations" aria-labelledby="tab-locations" hidden={tab !== "locations"}>
            <ReferenceToolbar
              title="Locations"
              description="The work sites positions sit at. A site a position still names is archived rather than deleted."
              canManage={canManage}
              addLabel="Add location"
              onAdd={() => openEditor("location")}
            />
            {loading ? (
              <LoadingRegion label="Loading locations">
                <TableSkeleton rows={5} cols={7} />
              </LoadingRegion>
            ) : (
              <Table
                columns={locationsColumns}
                data={locations}
                keyAccessor={(l: Location) => l.id}
                caption="Locations"
                sortable={false}
                filterable={false}
                emptyMessage="No locations have been defined."
              />
            )}
          </div>

          {/* Positions tab */}
          <div role="tabpanel" id="panel-positions" aria-labelledby="tab-positions" hidden={tab !== "positions"}>
            <ReferenceToolbar
              title="Positions"
              description="The funded slots in the org structure. A position another position reports to is archived rather than deleted."
              canManage={canManage}
              addLabel="Add position"
              onAdd={() => openEditor("position")}
            />
            {loading ? (
              <LoadingRegion label="Loading positions">
                <TableSkeleton rows={5} cols={8} />
              </LoadingRegion>
            ) : (
              <Table
                columns={positionsColumns}
                data={positions}
                keyAccessor={(pos: Position) => pos.id}
                caption="Positions"
                sortable={false}
                filterable={false}
                emptyMessage="No positions have been defined."
              />
            )}
          </div>

          {/* Cost centres tab */}
          <div role="tabpanel" id="panel-cost-centers" aria-labelledby="tab-cost-centers" hidden={tab !== "cost-centers"}>
            <ReferenceToolbar
              title="Cost centres"
              description="What spend is booked against. Nothing else in the schema points at a cost centre, so it can be deleted outright."
              canManage={canManage}
              addLabel="Add cost centre"
              onAdd={() => openEditor("costCenter")}
            />
            {loading ? (
              <LoadingRegion label="Loading cost centres">
                <TableSkeleton rows={5} cols={5} />
              </LoadingRegion>
            ) : (
              <Table
                columns={costCentersColumns}
                data={costCenters}
                keyAccessor={(cc: CostCenter) => cc.id}
                caption="Cost centres"
                sortable={false}
                filterable={false}
                emptyMessage="No cost centres have been defined."
              />
            )}
          </div>
        </div>

        <Modal
          open={editor !== null}
          onOpenChange={(open) => {
            if (!open) closeEditor()
          }}
        >
          <ModalContent size="lg">
            <ModalHeader>
              <ModalTitle>
                {editor
                  ? `${editor.row ? "Edit" : "Add"} ${LABEL[editor.kind].toLowerCase()}`
                  : ""}
              </ModalTitle>
              <ModalDescription>
                {editor?.row
                  ? "Only the fields you change are written. The code stays unique across the entity."
                  : "The new record becomes selectable in the forms that use it as soon as it is saved."}
              </ModalDescription>
            </ModalHeader>
            {editor && (
              <form onSubmit={saveReference} aria-label={`${editor.row ? "Edit" : "Add"} ${LABEL[editor.kind]}`}>
                {editorError && (
                  <Alert tone="error" title="Error">
                    {editorError}
                  </Alert>
                )}
                <div className="grid gap-4 sm:grid-cols-2">
                  {editorFields.map((spec) => (
                    <Field
                      key={spec.name}
                      htmlFor={`ref-${spec.name}`}
                      label={spec.label}
                      required={spec.required}
                    >
                      {spec.type === "select" ? (
                        <Select
                          id={`ref-${spec.name}`}
                          required={spec.required}
                          value={editorValues[spec.name] ?? ""}
                          onChange={(e) =>
                            setEditorValues({ ...editorValues, [spec.name]: e.target.value })
                          }
                        >
                          <option value="">{spec.required ? "Select…" : "None"}</option>
                          {spec.options?.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </Select>
                      ) : (
                        <Input
                          id={`ref-${spec.name}`}
                          type={spec.type === "number" ? "number" : "text"}
                          required={spec.required}
                          step={spec.step}
                          min={spec.min}
                          max={spec.max}
                          placeholder={spec.placeholder}
                          value={editorValues[spec.name] ?? ""}
                          onChange={(e) =>
                            setEditorValues({ ...editorValues, [spec.name]: e.target.value })
                          }
                        />
                      )}
                    </Field>
                  ))}
                </div>
                <div className="mt-5 flex justify-end gap-2">
                  <Button type="button" variant="secondary" onClick={closeEditor}>
                    Cancel
                  </Button>
                  <Button type="submit" loading={saving}>
                    {editor.row ? "Save changes" : `Add ${LABEL[editor.kind].toLowerCase()}`}
                  </Button>
                </div>
              </form>
            )}
          </ModalContent>
        </Modal>

        {selected && (
          <div
            className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-16"
            role="dialog"
            aria-modal="true"
            aria-labelledby="employee-detail-heading"
          >
            <div
              className="absolute inset-0 bg-[rgba(2,6,23,0.5)]"
              onClick={() => openEmployee(null)}
              aria-hidden="true"
            />
            <div className="relative w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-xl border border-border bg-surface-raised p-6 shadow-xl">
              <div className="flex items-start justify-between gap-4 mb-4">
                <div>
                  <h2 id="employee-detail-heading" className="mk-h2 text-fg">
                    {selected.first_name} {selected.last_name}
                  </h2>
                  <p className="text-xs text-fg-muted font-mono">{selected.employee_id}</p>
                </div>
                <Button variant="ghost" size="sm" onClick={() => openEmployee(null)}>
                  Close
                </Button>
              </div>
              <dl className="grid grid-cols-[auto,1fr] gap-x-4 gap-y-2 text-sm">
                <dt className="text-fg-muted">Email</dt>
                <dd className="break-all">{selected.email}</dd>
                <dt className="text-fg-muted">Phone</dt>
                <dd>{selected.phone || "—"}</dd>
                <dt className="text-fg-muted">Job</dt>
                <dd>{jobById.get(selected.job_id)?.title ?? "—"}</dd>
                <dt className="text-fg-muted">Department</dt>
                <dd>{deptById.get(selected.department_id)?.name ?? "—"}</dd>
                <dt className="text-fg-muted">Manager</dt>
                <dd>
                  {selected.manager_id
                    ? (() => {
                        const m = employeeById.get(selected.manager_id)
                        return m ? `${m.first_name} ${m.last_name}` : "—"
                      })()
                    : "—"}
                </dd>
                <dt className="text-fg-muted">Hire date</dt>
                <dd>{selected.hire_date}</dd>
                <dt className="text-fg-muted">Employment type</dt>
                <dd>{selected.employment_type || "—"}</dd>
                <dt className="text-fg-muted">Status</dt>
                <dd>
                  <StatusPill status={selected.status} dot />
                </dd>
                {selected.termination_date && (
                  <>
                    <dt className="text-fg-muted">Termination date</dt>
                    <dd>{selected.termination_date}</dd>
                  </>
                )}
              </dl>

              {canManage && (
                <section
                  className="mt-6 border-t border-border pt-4"
                  aria-labelledby="employee-employment"
                >
                  <h3 id="employee-employment" className="mk-h3 text-fg">
                    Change employment
                  </h3>
                  <p className="text-xs text-fg-muted mt-0.5">
                    The server enforces the lifecycle. A move it does not allow is refused
                    with the moves that are allowed, and nothing changes. A future date is
                    refused: there is no scheduler to apply a planned change.
                  </p>
                  <form className="mt-3 grid gap-3 sm:grid-cols-2" onSubmit={changeEmployment}>
                    <Field htmlFor="employment-status" label="Status" required>
                      <Select
                        id="employment-status"
                        value={employmentForm.status}
                        onChange={(event) =>
                          setEmploymentForm((current) => ({
                            ...current,
                            status: event.target.value,
                          }))
                        }
                      >
                        {EMPLOYEE_STATUSES.map((status) => (
                          <option key={status} value={status}>
                            {status}
                          </option>
                        ))}
                      </Select>
                    </Field>
                    <Field htmlFor="employment-type" label="Employment type">
                      <Select
                        id="employment-type"
                        value={employmentForm.employment_type}
                        onChange={(event) =>
                          setEmploymentForm((current) => ({
                            ...current,
                            employment_type: event.target.value,
                          }))
                        }
                      >
                        <option value="">Not recorded</option>
                        {EMPLOYMENT_TYPES.map((type) => (
                          <option key={type} value={type}>
                            {type}
                          </option>
                        ))}
                      </Select>
                    </Field>
                    <Field htmlFor="employment-job" label="Job">
                      <Select
                        id="employment-job"
                        value={employmentForm.job_id}
                        onChange={(event) =>
                          setEmploymentForm((current) => ({
                            ...current,
                            job_id: event.target.value,
                          }))
                        }
                      >
                        {jobs.map((job) => (
                          <option key={job.id} value={job.id}>
                            {job.title} ({job.code})
                          </option>
                        ))}
                      </Select>
                    </Field>
                    <Field htmlFor="employment-department" label="Department">
                      <Select
                        id="employment-department"
                        value={employmentForm.department_id}
                        onChange={(event) =>
                          setEmploymentForm((current) => ({
                            ...current,
                            department_id: event.target.value,
                          }))
                        }
                      >
                        {activeDepartments.map((department) => (
                          <option key={department.id} value={department.id}>
                            {department.name}
                          </option>
                        ))}
                      </Select>
                    </Field>
                    <Field htmlFor="employment-manager" label="Manager">
                      <Select
                        id="employment-manager"
                        value={employmentForm.manager_id}
                        onChange={(event) =>
                          setEmploymentForm((current) => ({
                            ...current,
                            manager_id: event.target.value,
                          }))
                        }
                      >
                        <option value="">No manager</option>
                        {employees
                          .filter((employee) => employee.id !== selected.id)
                          .map((employee) => (
                            <option key={employee.id} value={employee.id}>
                              {employee.first_name} {employee.last_name} ({employee.employee_id})
                            </option>
                          ))}
                      </Select>
                    </Field>
                    <Field htmlFor="employment-salary" label="Salary">
                      <Input
                        id="employment-salary"
                        type="number"
                        min="0"
                        step="0.01"
                        value={employmentForm.salary}
                        onChange={(event) =>
                          setEmploymentForm((current) => ({
                            ...current,
                            salary: event.target.value,
                          }))
                        }
                      />
                    </Field>
                    <Field htmlFor="employment-from" label="Effective from" required>
                      <Input
                        id="employment-from"
                        type="date"
                        max={todayISO()}
                        value={employmentForm.effective_from}
                        onChange={(event) =>
                          setEmploymentForm((current) => ({
                            ...current,
                            effective_from: event.target.value,
                          }))
                        }
                      />
                    </Field>
                    <div className="sm:col-span-2">
                      <Field htmlFor="employment-reason" label="Reason">
                        <Input
                          id="employment-reason"
                          value={employmentForm.reason}
                          maxLength={500}
                          onChange={(event) =>
                            setEmploymentForm((current) => ({
                              ...current,
                              reason: event.target.value,
                            }))
                          }
                        />
                      </Field>
                    </div>
                    <div className="sm:col-span-2">
                      <Button type="submit" loading={statusSaving}>
                        Record the change
                      </Button>
                    </div>
                  </form>
                  {statusNotice && (
                    <Alert tone="success">{statusNotice}</Alert>
                  )}
                  {statusError && (
                    <Alert tone="error" title="Error">
                      {statusError}
                    </Alert>
                  )}
                </section>
              )}

              <section
                className="mt-6 border-t border-border pt-4"
                aria-labelledby="employee-history"
              >
                <h3 id="employee-history" className="mk-h3 text-fg">
                  Employment history
                </h3>
                <p className="text-xs text-fg-muted mt-0.5">
                  Effective-dated changes, oldest first. A row is closed when a newer change
                  takes over; nothing is edited. The history begins with the feature, so
                  changes made before it existed are not listed.
                </p>
                {historyLoading && (
                  <LoadingRegion label="Reading employment history">
                    <TableSkeleton rows={5} cols={7} />
                  </LoadingRegion>
                )}
                {historyError && (
                  <Alert tone="error" title="Error">
                    {historyError}
                  </Alert>
                )}
                {!historyLoading && !historyError && historyRows.length === 0 && (
                  <p className="text-sm text-fg-muted mt-2">
                    No employment changes recorded yet.
                  </p>
                )}
                {historyRows.length > 0 && (
                  <div
                    className="table-scroll mt-2 max-h-64 overflow-y-auto"
                    tabIndex={0}
                    role="region"
                    aria-label="Employment history"
                  >
                    <Table
                      columns={[
                        { key: "field", header: "Field", accessor: (row: EmployeeHistoryEntry) => row.field.replace(/_/g, " ") },
                        { key: "from", header: "From", accessor: (row: EmployeeHistoryEntry) => row.effective_from },
                        { key: "to", header: "To", accessor: (row: EmployeeHistoryEntry) => row.effective_to || "—" },
                        { key: "previous", header: "Previous", accessor: (row: EmployeeHistoryEntry) => row.previous_value ?? "—" },
                        { key: "new", header: "New", accessor: (row: EmployeeHistoryEntry) => row.new_value ?? "—" },
                        { key: "by", header: "By", accessor: (row: EmployeeHistoryEntry) => row.changed_by || "—" },
                        { key: "reason", header: "Reason", accessor: (row: EmployeeHistoryEntry) => row.reason || "—" },
                      ]}
                      data={historyRows}
                      keyAccessor={(row: EmployeeHistoryEntry) => row.id}
                      caption="Employment history, oldest first"
                      sortable={false}
                      filterable={false}
                      emptyMessage="No employment changes recorded yet."
                    />
                  </div>
                )}
              </section>

              <section className="mt-6 border-t border-border pt-4" aria-labelledby="employee-documents">
                <h3 id="employee-documents" className="mk-h3 text-fg">
                  Documents
                </h3>
                <p className="text-xs text-fg-muted mt-0.5">
                  The register of this employee's documents. The file itself lives in the
                  customer's storage; this record points at it.
                </p>

                {docsLoading && (
                  <LoadingRegion label="Reading documents">
                    <TableSkeleton rows={3} cols={4} />
                  </LoadingRegion>
                )}

                {docsError && (
                  <Alert tone="error" title="Error">
                    {docsError}
                  </Alert>
                )}

                {!docsLoading && !docsError && documents.length === 0 && (
                  <p className="text-sm text-fg-muted mt-2">
                    No documents recorded for this employee.
                  </p>
                )}

                {documents.length > 0 && (
                  <div
                    className="table-scroll mt-2 max-h-56 overflow-y-auto"
                    tabIndex={0}
                    role="region"
                    aria-label="Documents recorded for this employee"
                  >
                    <Table
                      columns={[
                        { key: "type", header: "Type", accessor: (doc: EmployeeDocument) => doc.document_type },
                        { key: "file", header: "File", accessor: (doc: EmployeeDocument) =>
                          doc.storage_url ? (
                            <a
                              href={doc.storage_url}
                              target="_blank"
                              rel="noreferrer noopener"
                              className="text-brand-600 hover:underline break-all"
                            >
                              {doc.file_name}
                            </a>
                          ) : (
                            doc.file_name
                          )
                        },
                        { key: "status", header: "Status", accessor: (doc: EmployeeDocument) => doc.status },
                        { key: "expiry", header: "Expires", accessor: (doc: EmployeeDocument) => doc.expiry_date || "—" },
                      ]}
                      data={documents}
                      keyAccessor={(doc: EmployeeDocument) => doc.id}
                      caption="Documents recorded for this employee"
                      sortable={false}
                      filterable={false}
                      emptyMessage="No documents recorded for this employee."
                    />
                  </div>
                )}

                {canManage ? (
                  <form className="mt-4 grid gap-2 sm:grid-cols-2" onSubmit={addDocument}>
                    <Field htmlFor="doc-type" label="Type" required>
                      <Select
                        id="doc-type"
                        value={docForm.document_type}
                        onChange={(event) =>
                          setDocForm((current) => ({ ...current, document_type: event.target.value }))
                        }
                        required
                      >
                        {["Contract", "Identification", "Certificate", "Policy", "Other"].map((type) => (
                          <option key={type} value={type}>
                            {type}
                          </option>
                        ))}
                      </Select>
                    </Field>
                    <Field htmlFor="doc-file" label="File name" required>
                      <Input
                        id="doc-file"
                        value={docForm.file_name}
                        onChange={(event) =>
                          setDocForm((current) => ({ ...current, file_name: event.target.value }))
                        }
                        required
                      />
                    </Field>
                    <Field htmlFor="doc-url" label="Storage URL" required>
                      <Input
                        id="doc-url"
                        type="url"
                        value={docForm.storage_url}
                        onChange={(event) =>
                          setDocForm((current) => ({ ...current, storage_url: event.target.value }))
                        }
                        placeholder="https://…"
                        required
                      />
                    </Field>
                    <Field htmlFor="doc-expiry" label="Expiry date">
                      <Input
                        id="doc-expiry"
                        type="date"
                        value={docForm.expiry_date}
                        onChange={(event) =>
                          setDocForm((current) => ({ ...current, expiry_date: event.target.value }))
                        }
                      />
                    </Field>
                    <div className="sm:col-span-2 flex justify-end">
                      <Button type="submit" size="sm" loading={docSaving}>
                        Record document
                      </Button>
                    </div>
                  </form>
                ) : (
                  <p className="text-xs text-fg-muted mt-3">
                    Recording a document requires SuperAdmin or HR.
                  </p>
                )}
              </section>
            </div>
          </div>
        )}
        {/* Delete confirmation — replaces window.confirm */}
        {deleteTarget && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-label={`Delete ${LABEL[deleteTarget.kind].toLowerCase()}`}>
            <div className="absolute inset-0 bg-[rgba(2,6,23,0.5)]" onClick={() => setDeleteTarget(null)} aria-hidden="true" />
            <div className="relative card p-6 w-full max-w-md">
              <h2 className="mk-h2 text-fg mb-1">Delete {LABEL[deleteTarget.kind].toLowerCase()} {deleteTarget.row.code}?</h2>
              <p className="text-sm text-fg-muted mb-4">This is refused while anything still points at it. Archive it instead to take it out of the forms without losing the link.</p>
              <div className="flex justify-end gap-2">
                <Button variant="secondary" onClick={() => setDeleteTarget(null)}>Cancel</Button>
                <Button variant="danger" onClick={confirmDelete}>Delete</Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}