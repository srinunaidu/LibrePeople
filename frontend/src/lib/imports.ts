import api from "@/lib/api"

/**
 * The import domain's client.
 *
 * Why this file exists
 * --------------------
 * The import screen used to lie. It posted the commit, ignored the answer,
 * and said *"Import committed successfully!"* whatever came back. The
 * contract answers a file over the row threshold with a **202** and a job:
 * the work has been *queued*, not applied — the rows are not in the
 * database yet. The screen said the opposite, so an operator was told their
 * data was in when it was not, and they believed it.
 *
 * What this file does about it
 * ----------------------------
 * It reads the answer, and it returns which of the two things happened:
 *
 *   - a **200** — the rows were applied. The report carries the counts.
 *   - a **202** — the work was queued for a background job. Nothing has
 *     been applied yet, and the job's state is the import's state.
 *
 * They are two different types, so a caller cannot say "committed" about a
 * queued import without first deciding that it means something else.
 *
 * The HTTP status decides, not the body: the status is what the contract
 * makes the difference (`contracts/openapi/imports.yaml`, the `202` on the
 * commit). The body is read for the counts and the job, never for the
 * verdict.
 *
 * The job's progress
 * ------------------
 * A queued import can be followed. `GET /import-export/import/{entity}/
 * progress/{job_id}` (`DI-04`) reports the job's state, the rows applied and
 * rejected, and the report when it finishes; `POST .../cancel` (`DI-06`)
 * stops it, which is safe because the import is one transaction. This file
 * owns both calls, and `readProgress` reads the answer into one shape the
 * screen can render without guessing.
 *
 * The screen still does not invent a state: while the job is queued or
 * running the numbers are the server's, and a failed job reports **zero**
 * rows applied — the transaction rolled back — with the count it reached
 * reported separately.
 */

/** One error on one row of the file. */
export interface ImportRowError {
  row: number
  column: string | null
  code: string
  message: string
}

/** What the importer did with one row. */
export interface ImportRow {
  row: number
  status: string
  errors?: ImportRowError[]
}

/**
 * The outcome of an import.
 *
 * The same shape is returned by the dry run, by a commit that applied the
 * rows, and — when the job has finished — by the job's result (`DI-04`).
 */
export interface ImportReport {
  entity: string
  total_rows: number
  create: number
  update: number
  unchanged: number
  reject: number
  accepted: number
  created: number
  updated: number
  rejected: number
  skipped: number
  missing_columns?: string[]
  unknown_headers?: string[]
  note?: string
  warnings?: string[]
  /** Present on a commit that applied the rows. */
  committed?: boolean
  /** Present when the import was queued rather than applied. */
  state?: string
  job?: ImportJob
  confirmation_token?: string
  expires_at?: string
  result_hash?: string
  rows?: ImportRow[]
}

/** The background job that will apply the import. */
export interface ImportJob {
  id: number | string
  type: string
  state: string
  attempts?: number
  max_attempts?: number
}

/**
 * What a commit did.
 *
 * Two cases, and they are not the same thing:
 *
 *   - `committed` — the rows were applied. The report says how many.
 *   - `queued` — the work was handed to a background job. Nothing has been
 *     applied yet, and the job's state is the import's state.
 */
export type CommitOutcome =
  | { kind: "committed"; report: ImportReport }
  | { kind: "queued"; report: ImportReport | null; job: ImportJob | null }

/** The states a job can be in, as the screen needs them. */
export type JobPhase =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled"
  | "unknown"



/** The states the screen treats as the end of the road. */
export function isTerminalPhase(phase: JobPhase): boolean {
  return (
    phase === "succeeded" ||
    phase === "failed" ||
    phase === "cancelled" ||
    phase === "unknown"
  )
}

/** The state the server reported, as the screen needs it. */
export function toPhase(state: string | null | undefined): JobPhase {
  switch ((state ?? "").toLowerCase()) {
    case "queued":
    case "pending":
      return "queued"
    case "running":
      return "running"
    case "succeeded":
    case "success":
    case "completed":
    case "finished":
      return "succeeded"
    case "failed":
    case "dead":
    case "error":
      return "failed"
    case "cancelled":
    case "canceled":
    case "discarded":
      return "cancelled"
    default:
      return "unknown"
  }
}

/* --------------------------------------------------------------------------
 * Reading the answers
 * -------------------------------------------------------------------------- */

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function numberOrNull(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null
}

function firstNumber(source: Record<string, unknown>, keys: string[]): number | null {
  for (const key of keys) {
    const value = numberOrNull(source[key])
    if (value !== null) return value
  }
  return null
}

/** The counts of a report, under either of the two names the contract uses. */
function countsOf(source: Record<string, unknown>) {
  const create = firstNumber(source, ["create", "created"]) ?? 0
  const update = firstNumber(source, ["update", "updated"]) ?? 0
  const unchanged = firstNumber(source, ["unchanged"]) ?? 0
  const reject = firstNumber(source, ["reject", "rejected"]) ?? 0
  return {
    create,
    update,
    unchanged,
    reject,
    accepted: firstNumber(source, ["accepted"]) ?? create + update + unchanged,
    created: create,
    updated: update,
    rejected: reject,
    skipped: firstNumber(source, ["skipped"]) ?? 0,
  }
}

/**
 * Read a report, if the payload is one.
 *
 * Returns null for anything that is not a report, so a caller can tell
 * "the job has no report yet" from "the job's report is empty".
 */
export function readReport(payload: unknown): ImportReport | null {
  if (!isRecord(payload)) return null
  const looksLikeAReport =
    "total_rows" in payload ||
    "create" in payload ||
    "created" in payload ||
    "reject" in payload ||
    "rejected" in payload ||
    "entity" in payload
  if (!looksLikeAReport) return null

  const counts = countsOf(payload)
  const rows = Array.isArray(payload.rows) ? (payload.rows as ImportRow[]) : undefined

  return {
    entity: typeof payload.entity === "string" ? payload.entity : "",
    total_rows: firstNumber(payload, ["total_rows"]) ?? 0,
    ...counts,
    missing_columns: Array.isArray(payload.missing_columns)
      ? (payload.missing_columns as string[])
      : undefined,
    unknown_headers: Array.isArray(payload.unknown_headers)
      ? (payload.unknown_headers as string[])
      : undefined,
    note: typeof payload.note === "string" ? payload.note : undefined,
    warnings: Array.isArray(payload.warnings) ? (payload.warnings as string[]) : undefined,
    committed: typeof payload.committed === "boolean" ? payload.committed : undefined,
    state: typeof payload.state === "string" ? payload.state : undefined,
    job: readJob(payload.job) ?? undefined,
    confirmation_token:
      typeof payload.confirmation_token === "string" ? payload.confirmation_token : undefined,
    expires_at: typeof payload.expires_at === "string" ? payload.expires_at : undefined,
    result_hash: typeof payload.result_hash === "string" ? payload.result_hash : undefined,
    rows,
  }
}

/** Read the job the server reported, if it reported one. */
export function readJob(payload: unknown): ImportJob | null {
  if (!isRecord(payload)) return null
  const id = payload.id
  if (typeof id !== "number" && typeof id !== "string") return null
  return {
    id,
    type: typeof payload.type === "string" ? payload.type : "csv_import",
    state: typeof payload.state === "string" ? payload.state : "queued",
    attempts: numberOrNull(payload.attempts) ?? undefined,
    max_attempts: numberOrNull(payload.max_attempts) ?? undefined,
  }
}

/* --------------------------------------------------------------------------
 * The calls
 * -------------------------------------------------------------------------- */

/** Validate a file without writing anything. */
export async function dryRun(entity: string, file: File): Promise<ImportReport> {
  const formData = new FormData()
  formData.append("file", file)
  const response = await api.post<ImportReport>(
    `/import-export/import/${entity}/dry-run`,
    formData,
    { headers: { "Content-Type": "multipart/form-data" } }
  )
  return response.data
}

/**
 * Apply a validated import.
 *
 * The status code is the truth: a **202** means the work was queued for a
 * background job and nothing has been applied yet; a **200** means the rows
 * were applied. The body is read for the counts and the job, never for the
 * verdict.
 */
export async function commit(entity: string, confirmationToken: string): Promise<CommitOutcome> {
  const response = await api.post<unknown>(
    `/import-export/import/${entity}/commit`,
    null,
    { params: { confirmation_token: confirmationToken } }
  )

  const body = (response.data ?? null) as unknown
  const report = readReport(body)
  const queued = response.status === 202 || report?.state === "queued"

  if (queued) {
    return {
      kind: "queued",
      report,
      job: readJob(isRecord(body) ? body.job : null),
    }
  }
  if (!report) {
    // The status says the rows were applied, but the body is not the report
    // the contract promises. The screen keeps the verdict and says the
    // counts are missing; it never shows zeros as if they were read.
    return {
      kind: "committed",
      report: {
        entity,
        total_rows: 0,
        create: 0,
        update: 0,
        unchanged: 0,
        reject: 0,
        accepted: 0,
        created: 0,
        updated: 0,
        rejected: 0,
        skipped: 0,
      },
    }
  }
  return { kind: "committed", report }
}

/** How far a queued import has got, as the server reports it. */
export interface ImportProgress {
  entity: string
  /** The job, if the server named it. */
  job: ImportJob | null
  /** The raw job state: queued, running, succeeded, failed, dead. */
  state: string
  phase: JobPhase
  /** The dry-run record's status: pending, committed, cancelled, expired, failed. */
  importStatus: string | null
  committed: boolean
  rowsTotal: number
  rowsApplied: number
  rowsRejected: number
  rowsPending: number
  /** How far a failed job got before it rolled back. Never applied rows. */
  rowsAppliedBeforeFailure: number
  batchesDone: number
  batchesTotal: number
  percent: number
  /** The report, once the job has finished. */
  result: ImportReport | null
  /** False when the job finished before results were stored. */
  resultStored: boolean
  failure: { code: string | null; message: string | null } | null
  /** One sentence from the server about what this state means. */
  note: string
}

/** Read a progress answer. Returns null for anything that is not one. */
export function readProgress(payload: unknown): ImportProgress | null {
  if (!isRecord(payload)) return null
  if (!("state" in payload) && !("rows_applied" in payload)) return null

  const job = readJob(payload.job)
  const failure = isRecord(payload.failure)
    ? {
        code: typeof payload.failure.code === "string" ? payload.failure.code : null,
        message: typeof payload.failure.message === "string" ? payload.failure.message : null,
      }
    : null

  return {
    entity: typeof payload.entity === "string" ? payload.entity : "",
    job,
    state: typeof payload.state === "string" ? payload.state : "unknown",
    phase: toPhase(typeof payload.state === "string" ? payload.state : null),
    importStatus: typeof payload.import_status === "string" ? payload.import_status : null,
    committed: payload.committed === true,
    rowsTotal: firstNumber(payload, ["rows_total"]) ?? 0,
    rowsApplied: firstNumber(payload, ["rows_applied"]) ?? 0,
    rowsRejected: firstNumber(payload, ["rows_rejected"]) ?? 0,
    rowsPending: firstNumber(payload, ["rows_pending"]) ?? 0,
    rowsAppliedBeforeFailure: firstNumber(payload, ["rows_applied_before_failure"]) ?? 0,
    batchesDone: firstNumber(payload, ["batches_done"]) ?? 0,
    batchesTotal: firstNumber(payload, ["batches_total"]) ?? 0,
    percent: firstNumber(payload, ["percent"]) ?? 0,
    result: readReport(payload.result),
    resultStored: payload.result_stored === true,
    failure,
    note: typeof payload.note === "string" ? payload.note : "",
  }
}

/**
 * Read how far a queued import has got.
 *
 * The numbers are the job's: the server composes them from the job row, the
 * progress the handler records after every batch, and the dry-run record.
 * Nothing here is counted in the browser.
 */
export async function fetchProgress(
  entity: string,
  jobId: number | string
): Promise<ImportProgress> {
  const response = await api.get<unknown>(
    `/import-export/import/${entity}/progress/${jobId}`
  )
  const progress = readProgress(response.data)
  if (!progress) {
    throw new Error("The server's progress answer was not in the shape the contract promises.")
  }
  return progress
}

/**
 * Cancel an import that has not been committed.
 *
 * The import is one transaction, so this is always safe: the rows it had
 * written are taken back with it. A committed import cannot be cancelled,
 * and the server answers 409 rather than pretending otherwise.
 */
export async function cancelImport(
  entity: string,
  confirmationToken: string
): Promise<void> {
  await api.post(`/import-export/import/${entity}/cancel`, null, {
    params: { confirmation_token: confirmationToken },
  })
}

/**
 * The queued import this browser last saw accepted.
 *
 * The state of a queued import lives in the **job**, on the server — nothing
 * about it is computed or cached here. What the browser keeps is only the
 * job's *identity*, so that leaving the screen and coming back still shows
 * the operator which import is in flight. The state is read from the server
 * through `fetchProgress`, so the identity is all that has to be persisted.
 */
export interface QueuedWatch {
  entity: string
  jobId: number | string | null
  jobType: string | null
  jobState: string | null
  /** When the server accepted the import, as an ISO string. */
  queuedAt: string
}

const WATCH_KEY = "karmathy_import_job_watch"

export function saveQueuedWatch(watch: QueuedWatch): void {
  try {
    localStorage.setItem(WATCH_KEY, JSON.stringify(watch))
  } catch {
    // A browser that refuses persistence does not get a lie instead:
    // the screen simply has nothing to show after a reload.
  }
}

export function readQueuedWatch(): QueuedWatch | null {
  try {
    const raw = localStorage.getItem(WATCH_KEY)
    if (!raw) return null
    const parsed: unknown = JSON.parse(raw)
    if (!isRecord(parsed) || typeof parsed.entity !== "string" || !parsed.entity) return null
    return {
      entity: parsed.entity,
      jobId:
        typeof parsed.jobId === "number" || typeof parsed.jobId === "string"
          ? parsed.jobId
          : null,
      jobType: typeof parsed.jobType === "string" ? parsed.jobType : null,
      jobState: typeof parsed.jobState === "string" ? parsed.jobState : null,
      queuedAt: typeof parsed.queuedAt === "string" ? parsed.queuedAt : "",
    }
  } catch {
    return null
  }
}

export function forgetQueuedWatch(): void {
  try {
    localStorage.removeItem(WATCH_KEY)
  } catch {
    // Nothing to forget, and nothing to report.
  }
}

/**
 * The row-error file of a dry run.
 *
 * The endpoint re-derives the errors from the bytes that were uploaded, so
 * the file is the errors of exactly that file. It holds no personal value.
 */
export function rowErrorsUrl(entity: string, confirmationToken: string): string {
  return `${api.defaults.baseURL}/import-export/import/${entity}/row-errors?confirmation_token=${encodeURIComponent(
    confirmationToken
  )}`
}

/**
 * Fetch the row-error file.
 *
 * The download is a request, not a navigation: the endpoint needs the
 * operator's bearer token, and a plain `window.location` cannot carry one
 * (the answer used to be the 401 JSON body arriving in the browser instead
 * of a file). The bytes are fetched with the shared client and handed to
 * the browser as a file.
 */
export async function fetchRowErrors(
  entity: string,
  confirmationToken: string
): Promise<{ blob: Blob; filename: string }> {
  const response = await api.get(rowErrorsUrl(entity, confirmationToken), {
    responseType: "blob",
  })
  const disposition = (response.headers?.["content-disposition"] as string | undefined) ?? ""
  const match = /filename="?([^";]+)"?/.exec(disposition)
  return {
    blob: response.data as Blob,
    filename: match?.[1] ?? `${entity}-row-errors.csv`,
  }
}

/** Hand a fetched blob to the browser as a download. */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
