import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {
  Button,
  Select,
  Textarea,Alert,
  EmptyState,
  LoadingRegion,
  Modal,
  ModalContent,
  ModalDescription,
  ModalHeader,
  ModalTitle,
  PageHeader,
  SectionCard,
  TableSkeleton, RetryableAlert} from "@/components/ui"

import { IconGrid, IconRefresh } from "@/components/icons"
import type { PageMeta } from "@/types"
import { StatusPill, type StatusTone } from "@/components/ui/status-pill"
import api, { errorMessage } from "@/lib/api"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import { formatDateTime } from "@/lib/format"

/**
 * `/jobs` is the background-jobs monitor (PS-10).
 *
 * The queue that runs imports, forecasts and roster solves had no operator
 * surface: a dead job could only be found in the database. This screen reads
 * `GET /admin/jobs` — paged, newest first, with state and type filters, and
 * dead rows never hidden — and offers the two actions the contract defines:
 * retry a failed or dead job (same attempt budget), and discard a waiting job
 * (the row is kept as evidence).
 *
 * The job-title catalogue is a different thing with a similar name; it lives
 * at `/people/jobs` (the Jobs tab of People).
 *
 * Role reality: every `/admin/jobs` operation is `ADMIN_ROLES` server-side
 * (SuperAdmin and HR). Anything below gets the readable explanation instead
 * of a table that would only ever be empty.
 */

const ADMIN_ROLES = ["SuperAdmin", "HR"]

const STATES = [
  { value: "", label: "All states" },
  { value: "pending", label: "Pending" },
  { value: "running", label: "Running" },
  { value: "succeeded", label: "Succeeded" },
  { value: "failed", label: "Failed" },
  { value: "dead", label: "Dead" },
  { value: "cancelled", label: "Cancelled" },
  { value: "discarded", label: "Discarded" },
]

const JOB_TYPES = [
  { value: "", label: "All types" },
  { value: "csv_import", label: "CSV import" },
  { value: "forecast_run", label: "Forecast run" },
  { value: "roster_solve", label: "Roster solve" },
  { value: "payroll_process", label: "Payroll process" },
  { value: "document_render", label: "Document render" },
  { value: "webhook_deliver", label: "Webhook delivery" },
  { value: "retention_run", label: "Retention run" },
  { value: "erasure_run", label: "Erasure run" },
]

const STATE_TONE: Record<string, StatusTone> = {
  pending: "amber",
  running: "brand",
  succeeded: "green",
  failed: "rose",
  dead: "rose",
  cancelled: "rose",
  discarded: "slate",
}

interface Job {
  id: string
  type: string
  state: string
  attempts: number
  max_attempts: number
  created_at: string
  updated_at: string
  started_at?: string | null
  last_error_at?: string | null
  error_code?: string | null
  error_message?: string | null
  /** The stored input, returned by the detail operation. */
  payload?: Record<string, unknown> | null
  /** The stored result, returned when the job finished. */
  result?: Record<string, unknown> | null
}

interface PaginatedJobs {
  items: Job[]
  meta: PageMeta
}

const PAGE_SIZE = 25

const stateLabel = (state: string) =>
  state ? state.charAt(0).toUpperCase() + state.slice(1) : "—"

const typeLabel = (type: string) => {
  const known = JOB_TYPES.find((t) => t.value === type)
  if (known) return known.label
  return type
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ")
}

export default function BackgroundJobs() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const allowed = !!user?.role && ADMIN_ROLES.includes(user.role)
  // Job timestamps render in the tenant timezone/locale via format.ts —
  // never the browser default.
  const formatDate = (value?: string | null) =>
    formatDateTime(value, { locale: tenant?.locale, timeZone: tenant?.timezone })

  const [page, setPage] = useState(1)
  const [stateFilter, setStateFilter] = useState("")
  const [typeFilter, setTypeFilter] = useState("")
  const [data, setData] = useState<PaginatedJobs | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [busyId, setBusyId] = useState<string | null>(null)
  const [selected, setSelected] = useState<Job | null>(null)
  // The modal shows what the detail operation returns, not the list row.
  // The row can be stale: the job may have moved on since this page loaded,
  // and `result` is only served by the detail operation.
  const [detail, setDetail] = useState<Job | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState("")
  const [discarding, setDiscarding] = useState<Job | null>(null)
  const [reason, setReason] = useState("")

  const load = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const response = await api.get<PaginatedJobs>("/admin/jobs", {
        params: {
          page,
          page_size: PAGE_SIZE,
          state: stateFilter || undefined,
          type: typeFilter || undefined,
        },
      })
      setData(response.data)
    } catch (err) {
      setError(errorMessage(err, "The background jobs could not be loaded."))
    } finally {
      setLoading(false)
    }
  }, [page, stateFilter, typeFilter])

  useEffect(() => {
    if (allowed) load()
  }, [allowed, load])

  const openDetail = async (job: Job) => {
    setSelected(job)
    setDetail(null)
    setDetailError("")
    setDetailLoading(true)
    try {
      // No `include_payload`: the stored input can carry a confirmation
      // token, which is an authorisation and does not belong on a screen.
      const response = await api.get<Job>(`/admin/jobs/${job.id}`)
      setDetail(response.data)
    } catch (err) {
      setDetailError(
        errorMessage(err, "The job's detail could not be read. The row below is the list's copy.")
      )
    } finally {
      setDetailLoading(false)
    }
  }

  const changeState = (value: string) => {
    setPage(1)
    setStateFilter(value)
  }

  const changeType = (value: string) => {
    setPage(1)
    setTypeFilter(value)
  }

  const act = async (job: Job, action: "retry" | "discard", why = "") => {
    setBusyId(job.id)
    setError("")
    setNotice("")
    try {
      await api.post(
        `/admin/jobs/${job.id}/${action}`,
        null,
        action === "discard" && why ? { params: { reason: why } } : undefined,
      )
      setNotice(
        action === "retry"
          ? `Job ${job.id} was put back in the queue.`
          : `Job ${job.id} was discarded; its record is kept.`,
      )
      setDiscarding(null)
      setReason("")
      await load()
    } catch (err) {
      setError(errorMessage(err, `The ${action} was refused.`))
    } finally {
      setBusyId(null)
    }
  }

  if (!allowed) {
    return (
      <Layout>
        <PageHeader compact
          icon={<IconGrid />}
          title="Background jobs"
          description="The queue monitor for imports, forecasts and roster solves."
        />
        <Alert tone="error" title="Not permitted">
          <p>
            Your role ({user?.role || "unknown"}) cannot open the background-jobs
            monitor. Every operation on this screen — the listing, one job, retry and
            discard — is served to SuperAdmin and HR roles only.
          </p>
        </Alert>
      </Layout>
    )
  }

  const jobs = data?.items ?? []
  const totalPages = data?.meta?.total_pages ?? 1

  return (
    <Layout>
      <PageHeader compact
        icon={<IconGrid />}
        title="Background jobs"
        description="Imports, forecasts and roster solves the queue is running, has run, or gave up on."
        actions={
          <Button variant="secondary" onClick={load} loading={loading}>
            <IconRefresh className="h-4 w-4" aria-hidden="true" />
            Refresh
          </Button>
        }
      />

      {error && <Alert tone="error">{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}

      <Alert tone="info">
        Dead jobs are never hidden. Retrying a failed or dead job gives it one more
        attempt under the same budget; discarding a waiting job stops it but keeps its
        record as evidence.
      </Alert>

      <SectionCard compact
        icon={<IconGrid />}
        title="Job queue"
        description={
          data
            ? `${data.meta.total} job${data.meta.total === 1 ? "" : "s"} · page ${data.meta.page} of ${totalPages}`
            : "Loading the queue"
        }
      >
        <div className="mb-4 flex flex-wrap items-end gap-3">
          <div className="min-w-[10rem]">
            <label htmlFor="job-state" className="mb-1 block text-sm font-medium text-fg">
              State
            </label>
            <Select
              id="job-state"
              value={stateFilter}
              onChange={(event) => changeState(event.target.value)}
            >
              {STATES.map((state) => (
                <option key={state.value || "all"} value={state.value}>
                  {state.label}
                </option>
              ))}
            </Select>
          </div>
          <div className="min-w-[12rem]">
            <label htmlFor="job-type" className="mb-1 block text-sm font-medium text-fg">
              Type
            </label>
            <Select
              id="job-type"
              value={typeFilter}
              onChange={(event) => changeType(event.target.value)}
            >
              {JOB_TYPES.map((type) => (
                <option key={type.value || "all"} value={type.value}>
                  {type.label}
                </option>
              ))}
            </Select>
          </div>
        </div>

        {loading && !data ? (
          <LoadingRegion label="Loading the background jobs">
            <TableSkeleton rows={6} cols={6} />
          </LoadingRegion>
        ) : jobs.length === 0 ? (
          <EmptyState
            title="No jobs match these filters"
            description="Imports, forecasts and roster solves appear here when the queue runs them."
          />
        ) : (
          <div className="table-scroll">
            <table className="table-base table-striped">
              <caption className="sr-only">
                Background jobs with type, state, attempts, activity and actions
              </caption>
              <thead>
                <tr>
                  <th scope="col">Job</th>
                  <th scope="col">Type</th>
                  <th scope="col">State</th>
                  <th scope="col">Attempts</th>
                  <th scope="col">Last activity</th>
                  <th scope="col">Error</th>
                  {/* A visible header, like every other column. A
                      visually-hidden span here was `position: absolute` with
                      no positioned ancestor, so on a 360px screen it was
                      placed at the far right of the 797px table — outside
                      every scroll container — and pushed the whole document
                      378px sideways. */}
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id}>
                    <td className="font-mono text-xs whitespace-nowrap">#{job.id}</td>
                    <td className="font-medium">{typeLabel(job.type)}</td>
                    <td>
                      <StatusPill
                        status={stateLabel(job.state)}
                        tone={STATE_TONE[job.state] ?? "slate"}
                        dot
                      />
                    </td>
                    <td className="num whitespace-nowrap">
                      {job.attempts}/{job.max_attempts}
                    </td>
                    <td className="text-text-secondary whitespace-nowrap">
                      {formatDate(job.updated_at)}
                    </td>
                    <td className="max-w-[16rem] truncate text-text-secondary" title={job.error_message || undefined}>
                      {job.error_code || job.error_message || "—"}
                    </td>
                    <td className="whitespace-nowrap">
                      <div className="flex flex-wrap gap-2">
                        <Button
                          variant="ghost"
                          size="xs"
                          onClick={() => openDetail(job)}
                        >
                          View
                        </Button>
                        {(job.state === "failed" || job.state === "dead") && (
                          <Button
                            variant="secondary"
                            size="xs"
                            loading={busyId === job.id}
                            onClick={() => act(job, "retry")}
                          >
                            Retry
                          </Button>
                        )}
                        {(job.state === "pending" ||
                          job.state === "failed" ||
                          job.state === "dead") && (
                          <Button
                            variant="danger"
                            size="xs"
                            disabled={busyId === job.id}
                            onClick={() => {
                              setReason("")
                              setDiscarding(job)
                            }}
                          >
                            Discard
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-text-secondary">
            {data
              ? `Page ${data.meta.page} of ${totalPages} · ${data.meta.total} job${data.meta.total === 1 ? "" : "s"}`
              : ""}
          </p>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={page <= 1 || loading}
              onClick={() => setPage((current) => Math.max(1, current - 1))}
            >
              Previous
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={page >= totalPages || loading}
              onClick={() => setPage((current) => current + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      </SectionCard>

      <Modal open={!!selected} onOpenChange={(open) => !open && setSelected(null)}>
        <ModalContent size="lg">
          <ModalHeader>
            <ModalTitle>Job #{selected?.id}</ModalTitle>
            <ModalDescription>
              Read from the job itself. The queue stores the input beside its hash and the
              result beside its own; the input can hold an authorisation, so it is not
              shown here.
            </ModalDescription>
          </ModalHeader>

          {detailLoading && (
            <p className="text-sm text-text-secondary" role="status">
              Reading job #{selected?.id}…
            </p>
          )}

          {detailError && (
            <div className="mb-3">
              <RetryableAlert err={detailError} title="The job's detail could not be read" fallback="The job's detail could not be read" onRetry={load} />
            </div>
          )}

          {(() => {
            // The detail when it arrived, the list row otherwise. The row is
            // labelled as such while the read is in flight or has failed.
            const job = detail ?? selected
            if (!job) return null
            return (
              <dl className="grid grid-cols-1 gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
                <div>
                  <dt className="font-medium text-fg">Type</dt>
                  <dd className="text-text-secondary">{typeLabel(job.type)}</dd>
                </div>
                <div>
                  <dt className="font-medium text-fg">State</dt>
                  <dd>
                    <StatusPill
                      status={stateLabel(job.state)}
                      tone={STATE_TONE[job.state] ?? "slate"}
                    />
                  </dd>
                </div>
                <div>
                  <dt className="font-medium text-fg">Attempts</dt>
                  <dd className="text-text-secondary">
                    {job.attempts} of {job.max_attempts}
                  </dd>
                </div>
                <div>
                  <dt className="font-medium text-fg">Created</dt>
                  <dd className="text-text-secondary">{formatDate(job.created_at)}</dd>
                </div>
                <div>
                  <dt className="font-medium text-fg">Started</dt>
                  <dd className="text-text-secondary">{formatDate(job.started_at)}</dd>
                </div>
                <div>
                  <dt className="font-medium text-fg">Last activity</dt>
                  <dd className="text-text-secondary">{formatDate(job.updated_at)}</dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="font-medium text-fg">Error</dt>
                  <dd className="text-text-secondary">
                    {job.error_code || job.error_message
                      ? `${job.error_code ? `${job.error_code}: ` : ""}${job.error_message || ""}`
                      : "—"}
                  </dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="font-medium text-fg">Last error at</dt>
                  <dd className="text-text-secondary">{formatDate(job.last_error_at)}</dd>
                </div>
                {detail && (
                  <div className="sm:col-span-2">
                    <dt className="font-medium text-fg">Result</dt>
                    <dd className="text-text-secondary">
                      {detail.result ? (
                        <pre className="mt-1 max-h-56 overflow-auto rounded-lg bg-surface-sunken p-3 text-xs">
                          {JSON.stringify(detail.result, null, 2)}
                        </pre>
                      ) : (
                        "The job has not stored a result."
                      )}
                    </dd>
                  </div>
                )}
              </dl>
            )
          })()}
        </ModalContent>
      </Modal>

      <Modal open={!!discarding} onOpenChange={(open) => !open && setDiscarding(null)}>
        <ModalContent>
          <ModalHeader>
            <ModalTitle>Discard job #{discarding?.id}?</ModalTitle>
            <ModalDescription>
              The job will not be picked up again. Its record stays in the queue as
              evidence, and the reason is written to the audit trail.
            </ModalDescription>
          </ModalHeader>
          <label htmlFor="discard-reason" className="mb-1 block text-sm font-medium text-fg">
            Reason (optional)
          </label>
          <Textarea
            id="discard-reason"
            value={reason}
            maxLength={500}
            onChange={(event) => setReason(event.target.value)}
            placeholder="Why this job should not run"
          />
          <div className="mt-4 flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setDiscarding(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              loading={busyId === discarding?.id}
              onClick={() => discarding && act(discarding, "discard", reason.trim())}
            >
              Discard job
            </Button>
          </div>
        </ModalContent>
      </Modal>

      <p className="mt-4 text-xs text-text-secondary">
        SuperAdmin and HR can retry or discard. Every action on this screen is written to
        the audit trail.
      </p>
    </Layout>
  )
}
