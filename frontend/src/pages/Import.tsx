import React, { useEffect, useRef, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert,
  Button,
  Card,
  CardSkeleton,
  EmptyState,
  Input,
  LoadingRegion,
  PageHeader,
  SectionCard,
  Select,
  Table,
  TableSkeleton, RetryableAlert} from "@/components/ui"
import { Badge } from "@/components/ui/badge"
import { Field } from "@/components/ui/layout"
import { StatusPill } from "@/components/ui/status-pill"
import api, { errorMessage } from "@/lib/api"
import {
  cancelImport,
  commit as commitImport,
  dryRun,
  fetchProgress,
  fetchRowErrors,
  forgetQueuedWatch,
  isTerminalPhase,
  readQueuedWatch,
  saveBlob,
  saveQueuedWatch,
  toPhase,
  type CommitOutcome,
  type ImportProgress,
  type ImportReport,
  type JobPhase,
  type QueuedWatch,
} from "@/lib/imports"

/**
 * CSV Import.
 *
 * What this screen refuses to do
 * ------------------------------
 * The contract answers a commit in two different ways, and they are not the
 * same thing: a **200** says the rows were applied, a **202** says the file
 * was large enough to be queued for a background job — started, not
 * finished, and nothing written yet. This screen reads the status it gets
 * and says which one happened. It must never say "committed" about a
 * queued import: the operator believes the screen, and the data would not
 * be there.
 *
 * Following the job
 * -----------------
 * A queued import is watched through the job's own progress operation
 * (`DI-04`): the screen polls while the job is queued or running, shows the
 * rows applied and rejected as the server reports them, and stops when the
 * job is finished or the import is cancelled. Nothing is counted in the
 * browser, and a failed job is shown as **zero rows applied** — the
 * transaction rolled back — with the count it reached reported separately.
 *
 * The screen also offers **Cancel** while the import has not been
 * committed, because the import is one transaction and stopping it is
 * therefore always safe. The confirmation token is needed for that and it
 * is deliberately kept in memory only: after a reload the screen can follow
 * the job (by its id) but not cancel it.
 */

/** The badge class for a job's state, through the shared phase reader. */
const PHASE_BADGE: Record<JobPhase, "amber" | "green" | "rose" | "slate"> = {
  queued: "amber",
  running: "amber",
  succeeded: "green",
  failed: "rose",
  cancelled: "rose",
  unknown: "slate",
}

/** A short human time for "queued at" stamps. */
function shortTime(v?: string | null): string {
  if (!v) return "—"
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return v.replace("T", " ").slice(0, 16)
  return new Intl.DateTimeFormat(undefined, { dateStyle: "short", timeStyle: "short" }).format(d)
}

export default function ImportPage() {
  /* ------------------------------------------------------------------ *
   * 1. The entities the importer serves — from the server, not a         *
   *    hardcoded list: a name the deployment refuses would end in a 404. *
   * ------------------------------------------------------------------ */
  const [entities, setEntities] = useState<string[]>([])
  const [entitiesStatus, setEntitiesStatus] = useState<"loading" | "ready" | "error">("loading")
  const [entitiesError, setEntitiesError] = useState("")
  const [entity, setEntity] = useState("")
  const [entitiesAttempt, setEntitiesAttempt] = useState(0)
  const loadedAttempt = useRef(-1)

  useEffect(() => {
    // Settled once: the guard is set before the request and both endings
    // (data and error) set a final state, so a failed fetch never re-fires
    // this effect on every render. Retrying is a deliberate act on the
    // button, not an invisible loop. (L-016.)
    if (loadedAttempt.current === entitiesAttempt) return
    loadedAttempt.current = entitiesAttempt
    let cancelled = false
    setEntitiesStatus("loading")
    setEntitiesError("")
    api
      .get("/import-export/entities")
      .then((res: { data?: { entities?: unknown } }) => {
        if (cancelled) return
        const list = Array.isArray(res.data?.entities)
          ? res.data.entities.filter((e): e is string => typeof e === "string" && e.length > 0)
          : []
        setEntities(list)
        setEntity((prev: string) => (list.includes(prev) ? prev : list[0] ?? ""))
        setEntitiesStatus("ready")
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setEntitiesError(
          errorMessage(err, "The importer did not answer with its list of entities.")
        )
        setEntitiesStatus("error")
      })
    return () => {
      cancelled = true
    }
  }, [entitiesAttempt])

  /* ------------------------------------------------------------------ *
   * 2. The dry run                                                      *
   * ------------------------------------------------------------------ */
  const [file, setFile] = useState<File | null>(null)
  const [dryStatus, setDryStatus] = useState<"idle" | "loading" | "ready" | "error">("idle")
  const [dryRunReport, setDryRunReport] = useState<ImportReport | null>(null)
  const [dryError, setDryError] = useState("")

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      setFile(e.target.files[0])
      setDryError("")
    }
  }

  const handleDryRun = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file || !entity) return
    setDryStatus("loading")
    setDryError("")
    try {
      const report = await dryRun(entity, file)
      // A new preview is a new import: the previous commit's outcome is not
      // this one's, and its confirmation token has been spent.
      setDryRunReport(report)
      setOutcome(null)
      setCommitError("")
      setDryStatus("ready")
    } catch (err) {
      setDryRunReport(null)
      setOutcome(null)
      setDryError(errorMessage(err, "The dry run failed."))
      setDryStatus("error")
    }
  }

  /* ------------------------------------------------------------------ *
   * 3. The commit — the answer is read, whatever it is                  *
   * ------------------------------------------------------------------ */
  const [outcome, setOutcome] = useState<CommitOutcome | null>(null)
  const [committing, setCommitting] = useState(false)
  const [commitError, setCommitError] = useState("")
  const [watch, setWatch] = useState<QueuedWatch | null>(() => readQueuedWatch())

  const handleCommit = async () => {
    const token = dryRunReport?.confirmation_token
    if (!token || !entity) return
    setCommitting(true)
    setCommitError("")
    try {
      const result = await commitImport(entity, token)
      setOutcome(result)
      if (result.kind === "queued") {
        // The queued watch remembers the job's identity and nothing else:
        // its real state is the job's, on the server.
        const next: QueuedWatch = {
          entity,
          jobId: result.job?.id ?? null,
          jobType: result.job?.type ?? null,
          jobState: result.job?.state ?? null,
          queuedAt: new Date().toISOString(),
        }
        saveQueuedWatch(next)
        setWatch(next)
      }
    } catch (err) {
      setOutcome(null)
      setCommitError(errorMessage(err, "The commit failed."))
    } finally {
      setCommitting(false)
    }
  }

  /* ------------------------------------------------------------------ *
   * 4. Following the job — read from the server, never counted here     *
   * ------------------------------------------------------------------ */
  const [progress, setProgress] = useState<ImportProgress | null>(null)
  const [progressError, setProgressError] = useState("")
  const [cancelling, setCancelling] = useState(false)

  // While the queued answer is on screen the token is in memory and the
  // import can be cancelled. After a reload only the job's identity
  // survives — enough to follow it, not enough to stop it.
  const activeEntity = outcome?.kind === "queued" ? entity : (watch?.entity ?? null)
  const activeJobId = outcome?.kind === "queued" ? (outcome.job?.id ?? null) : (watch?.jobId ?? null)
  const canCancel =
    outcome?.kind === "queued" &&
    Boolean(outcome.job?.id) &&
    Boolean(dryRunReport?.confirmation_token)

  useEffect(() => {
    if (!activeEntity || activeJobId === null || activeJobId === undefined) {
      setProgress(null)
      return
    }
    let alive = true
    let timer: number | undefined

    const tick = async () => {
      try {
        const next = await fetchProgress(activeEntity, activeJobId)
        if (!alive) return
        setProgress(next)
        setProgressError("")
        // Stop at the end of the road: the job finished, or the import was
        // cancelled (a cancelled job the worker never ran stays queued).
        const done =
          isTerminalPhase(next.phase) || next.importStatus === "cancelled"
        if (!done) timer = window.setTimeout(tick, 2000)
      } catch (err) {
        if (!alive) return
        // A read that failed is not a job that failed: say the read failed
        // and try again, without inventing a state.
        setProgressError(errorMessage(err, "The job's progress could not be read."))
        timer = window.setTimeout(tick, 5000)
      }
    }

    tick()
    return () => {
      alive = false
      if (timer) window.clearTimeout(timer)
    }
  }, [activeEntity, activeJobId])

  const handleCancel = async () => {
    const token = dryRunReport?.confirmation_token
    if (!token || !entity) return
    setCancelling(true)
    setProgressError("")
    try {
      await cancelImport(entity, token)
      if (activeJobId !== null && activeJobId !== undefined) {
        setProgress(await fetchProgress(entity, activeJobId))
      }
    } catch (err) {
      setProgressError(
        errorMessage(err, "The import could not be cancelled.")
      )
    } finally {
      setCancelling(false)
    }
  }

  /* The row-error file — a request with the bearer token, not a
     navigation, which could never carry one. */
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState("")

  const handleDownload = async () => {
    const token = dryRunReport?.confirmation_token
    if (!token || !entity) return
    setDownloading(true)
    setDownloadError("")
    try {
      const errors = await fetchRowErrors(entity, token)
      saveBlob(errors.blob, errors.filename)
    } catch (err) {
      setDownloadError(errorMessage(err, "The row-error file could not be downloaded."))
    } finally {
      setDownloading(false)
    }
  }

  const handleForget = () => {
    forgetQueuedWatch()
    setWatch(null)
  }

  /* ------------------------------------------------------------------ *
   * 5. Columns preview, template and export — add-only (B3)             *
   *    GET /import-export/columns/{entity}, /template/{entity},         *
   *    /export/{entity}. Each read is independent; the entity comes      *
   *    from the server list, not a hard-coded value.                     *
   * ------------------------------------------------------------------ */
  const [columnsData, setColumnsData] = useState<{
    entity: string
    label?: string
    natural_key?: string[]
    columns: { name: string; kind?: string; required?: boolean; description?: string | null }[]
  } | null>(null)
  const [columnsStatus, setColumnsStatus] = useState<"idle" | "loading" | "ready" | "error">("idle")
  const [columnsError, setColumnsError] = useState("")
  const [templateBusy, setTemplateBusy] = useState(false)
  const [templateError, setTemplateError] = useState("")
  const [exportBusy, setExportBusy] = useState(false)
  const [exportError, setExportError] = useState("")

  useEffect(() => {
    if (!entity) {
      setColumnsData(null)
      setColumnsStatus("idle")
      return
    }
    let cancelled = false
    setColumnsStatus("loading")
    setColumnsError("")
    api
      .get(`/import-export/columns/${entity}`)
      .then((res: { data: typeof columnsData }) => {
        if (cancelled) return
        setColumnsData(res.data as typeof columnsData)
        setColumnsStatus("ready")
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setColumnsData(null)
        setColumnsError(errorMessage(err, "The columns could not be read."))
        setColumnsStatus("error")
      })
    return () => {
      cancelled = true
    }
  }, [entity])

  const handleTemplateDownload = async () => {
    if (!entity || templateBusy) return
    setTemplateBusy(true)
    setTemplateError("")
    try {
      const res = await api.get(`/import-export/template/${entity}`, { responseType: "blob" })
      const disposition = (res.headers?.["content-disposition"] as string | undefined) ?? ""
      const m = /filename="?([^";]+)"?/.exec(disposition)
      saveBlob(res.data as Blob, m?.[1] ?? `${entity}-template.csv`)
    } catch (err) {
      setTemplateError(errorMessage(err, "The template could not be downloaded."))
    } finally {
      setTemplateBusy(false)
    }
  }

  const handleExportDownload = async () => {
    if (!entity || exportBusy) return
    setExportBusy(true)
    setExportError("")
    try {
      const res = await api.get(`/import-export/export/${entity}`, { responseType: "blob" })
      const disposition = (res.headers?.["content-disposition"] as string | undefined) ?? ""
      const m = /filename="?([^";]+)"?/.exec(disposition)
      saveBlob(res.data as Blob, m?.[1] ?? `${entity}.csv`)
    } catch (err) {
      setExportError(errorMessage(err, "The export could not be downloaded."))
    } finally {
      setExportBusy(false)
    }
  }

  /* ------------------------------------------------------------------ *
   * Derived reading of the preview                                      *
   * ------------------------------------------------------------------ */
  const rejected = dryRunReport?.rejected ?? 0
  const rowErrors =
    dryRunReport?.rows?.flatMap((r) => (r.errors ?? []).map((err) => err)) ?? []
  const shownRowErrors = rowErrors.slice(0, 10).map((err, i) => ({ ...err, __index: i }))
  const queuedPhase = toPhase(
    outcome?.kind === "queued"
      ? (outcome.job?.state ?? "queued")
      : (readQueuedWatch()?.jobState ?? null)
  )

  return (
    <Layout>
      <div className="p-8">
        <PageHeader compact
          title="CSV Import"
          description="Upload CSV files to import data into Karmathy. All imports require a dry run first."
        />

        <div className="max-w-3xl space-y-6">
          {/* The queued-import watch: the job's identity, kept across
              navigation and reloads. Its state is the server's. */}
          {watch &&
            outcome?.kind !== "queued" && (
              <Card className="p-5">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="mk-h2 text-fg mb-1">Queued import watch</p>
                    <p className="text-xs text-fg-muted mt-1">
                      {watch.entity}
                      {watch.jobId !== null && <> · job #{watch.jobId}</>}
                      {watch.jobType && <> · {watch.jobType}</>}
                      {watch.jobState && <> · {watch.jobState}</>}
                      {watch.queuedAt && <> · accepted {shortTime(watch.queuedAt)}</>}
                    </p>
                    <p className="text-xs text-fg-muted mt-1">
                      The job's identity is kept here; its state is read from the
                      server. A queued import is applied entirely or not at all.
                      {watch.jobId === null && (
                        <> This answer did not carry a job reference, so it cannot be followed.</>
                      )}
                    </p>
                    <Badge
                      variant={PHASE_BADGE[progress?.phase ?? toPhase(watch.jobState)] as any}
                      className="mt-2 inline-block"
                    >
                      {progress
                        ? progress.state
                        : toPhase(watch.jobState) === "unknown"
                        ? "state unknown"
                        : toPhase(watch.jobState)}
                    </Badge>
                    {progress && (
                      <p className="text-xs text-fg-muted mt-2" role="status">
                        {progress.rowsApplied} of {progress.rowsTotal} rows applied ·{" "}
                        {progress.rowsRejected} rejected · {progress.percent}%
                        {progress.note && <> — {progress.note}</>}
                      </p>
                    )}
                  </div>
                  <Button variant="outline" onClick={handleForget} className="shrink-0">
                    Forget
                  </Button>
                </div>
              </Card>
            )}

          {/* 1 — the entities */}
          <Card>
            <h2 className="mk-h2 text-fg mb-4">1. Select Entity</h2>
            {entitiesStatus === "loading" && (
              <LoadingRegion label="Loading the entities the importer serves">
                <CardSkeleton lines={2} />
              </LoadingRegion>
            )}
            {entitiesStatus === "error" && (
              <div className="space-y-3">
                <Alert tone="error" title="The entity list could not be read">
                  <p>{entitiesError}</p>
                  <p className="mt-1">
                    The importer serves the list itself; nothing is hardcoded on this
                    screen.
                  </p>
                </Alert>
                <Button
                  variant="outline"
                  onClick={() => setEntitiesAttempt((a) => a + 1)}
                >
                  Try again
                </Button>
              </div>
            )}
            {entitiesStatus === "ready" && entities.length === 0 && (
              <EmptyState
                title="Nothing can be imported here"
                description="The deployment serves no importable entities. Ask for one to be added."
              />
            )}
            {entitiesStatus === "ready" && entities.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {entities.map((ent) => (
                  <button
                    key={ent}
                    onClick={() => setEntity(ent)}
                    className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                      entity === ent
                        ? "bg-[var(--brand-700)] text-white"
                        : "bg-surface border border-border text-fg-muted hover:bg-surface-hover"
                    }`}
                  >
                    {ent}
                  </button>
                ))}
              </div>
            )}
          </Card>

          {/* 2 — the file and the dry run */}
          <Card>
            <h2 className="mk-h2 text-fg mb-4">2. Upload CSV</h2>
            <form onSubmit={handleDryRun} className="space-y-4">
              <Field htmlFor="import-file" label="CSV File" required>
                <Input
                  id="import-file"
                  type="file"
                  accept=".csv"
                  onChange={handleFileChange}
                />
                {file && (
                  <p className="text-xs text-fg-muted mt-1">
                    {file.name} — the dry run validates every row and writes nothing;
                    the commit applies it only after you confirm.
                  </p>
                )}
              </Field>
              <Button
                type="submit"
                disabled={!file || !entity || dryStatus === "loading"}
                className="w-full"
              >
                {dryStatus === "loading" ? "Validating…" : "Run dry run"}
              </Button>
              {dryError && (
                <Alert tone="error" title="The preview failed">
                  <p>{dryError}</p>
                  <p className="mt-1">
                    Nothing was written; the file can be corrected and tried again.
                  </p>
                </Alert>
              )}
            </form>
          </Card>

          {/* 3 — the preview, and then the verdict */}
          {/* Columns preview + template + export — below the import flow, not inside it */}
          {entity && (
            <SectionCard compact
              title="Columns"
              description={`What ${entity} accepts. GET /import-export/columns/${entity} — the contract for this entity.`}
            >
              {columnsStatus === "loading" ? (
                <LoadingRegion label="Loading columns…">
                  <TableSkeleton rows={4} cols={3} />
                </LoadingRegion>
              ) : columnsStatus === "error" ? (
                <RetryableAlert err={columnsError} title="The columns could not be read" fallback="The columns could not be read" onRetry={() => window.location.reload()} />
              ) : columnsStatus === "idle" || !columnsData ? (
                <div className="p-5 text-sm text-fg-muted">Select an entity to see its columns.</div>
              ) : (
                <div className="p-5">
                  {columnsData.label && (
                    <p className="text-sm text-fg-muted mb-2">
                      {columnsData.label}
                      {columnsData.natural_key && columnsData.natural_key.length > 0 && (
                        <> · natural key: {columnsData.natural_key.join(", ")}</>
                      )}
                    </p>
                  )}
                  <Table
                    columns={[
                      { key: "name", header: "Column", accessor: (col: any) => <span className="font-mono text-xs">{col.name}</span> },
                      { key: "required", header: "Required", accessor: (col: any) => (col.required ? "Yes" : "No") },
                      { key: "kind", header: "Kind", accessor: (col: any) => <span className="text-xs">{col.kind ?? "—"}</span> },
                      { key: "description", header: "Description", accessor: (col: any) => <span className="text-xs text-fg-muted">{col.description ?? "—"}</span> },
                    ]}
                    data={columnsData.columns}
                    keyAccessor={(col: any) => col.name}
                    caption={`Columns for ${entity}`}
                    sortable={false}
                    filterable={false}
                    emptyMessage="No columns defined"
                  />
                </div>
              )}
            </SectionCard>
          )}

          {entity && (
            <SectionCard compact
              title="Template"
              description={`A CSV with the correct headers for ${entity} and one example row. GET /import-export/template/${entity}.`}
            >
              <div className="p-5">
                <p className="text-sm text-fg-muted mb-3">
                  Download the template, fill it, then run a dry run above. The headers must match exactly.
                </p>
                <Button onClick={handleTemplateDownload} loading={templateBusy} variant="secondary">
                  Download template CSV
                </Button>
                {templateError && (
                  <Alert tone="error" title="The template could not be downloaded">
                    {templateError}
                  </Alert>
                )}
              </div>
            </SectionCard>
          )}

          {entity && (
            <SectionCard compact
              title="Export"
              description={`The current ${entity} rows as CSV — the same columns the import accepts, so an export can be edited and re-imported. GET /import-export/export/${entity}.`}
            >
              <div className="p-5">
                <p className="text-sm text-fg-muted mb-3">
                  The export is the live data. The file name is <code className="font-mono text-xs">{entity}.csv</code>.
                </p>
                <Button onClick={handleExportDownload} loading={exportBusy} variant="secondary">
                  Download export CSV
                </Button>
                {exportError && (
                  <Alert tone="error" title="The export could not be downloaded">
                    {exportError}
                  </Alert>
                )}
              </div>
            </SectionCard>
          )}

          {dryRunReport && (
            <SectionCard compact
              title="Dry Run Results"
              description="What would happen if this file were committed now — nothing has been written yet."
            >
              <div className="p-5 space-y-6">
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  <Card className="p-3 bg-[var(--semantic-status-success-light)]">
                    <p className="text-xs font-medium text-[var(--semantic-text-safe-green)]">Created</p>
                    <p className="text-[var(--font-size-lg)] font-bold text-fg">{dryRunReport.created}</p>
                  </Card>
                  <Card className="p-3 bg-[var(--semantic-brand-soft)]">
                    <p className="text-xs font-medium text-[var(--semantic-text-safe-brand)]">Updated</p>
                    <p className="text-[var(--font-size-lg)] font-bold text-fg">{dryRunReport.updated}</p>
                  </Card>
                  <Card className="p-3 bg-[var(--semantic-brand-soft)]">
                    <p className="text-xs font-medium text-[var(--semantic-text-safe-brand)]">Unchanged</p>
                    <p className="text-[var(--font-size-lg)] font-bold text-fg">{dryRunReport.unchanged}</p>
                  </Card>
                  <Card className="p-3 bg-[var(--semantic-status-error-light)]">
                    <p className="text-xs font-medium text-[var(--semantic-text-safe-error)]">Rejected</p>
                    <p className="text-[var(--font-size-lg)] font-bold text-fg">{dryRunReport.rejected}</p>
                  </Card>
                  <Card className="p-3 bg-[var(--semantic-status-warning-light)]">
                    <p className="text-xs font-medium text-[var(--semantic-text-safe-warning)]">Rows in file</p>
                    <p className="text-[var(--font-size-lg)] font-bold text-fg">{dryRunReport.total_rows}</p>
                  </Card>
                </div>

                {rowErrors.length > 0 && (
                  <div>
                    <h3 className="mk-h2 text-fg mb-2">Row errors</h3>
                    <div className="overflow-x-auto">
                      <Table
                        columns={[
                          { key: "row", header: "Row", accessor: (err: any) => err.row },
                          { key: "column", header: "Column", accessor: (err: any) => err.column || "—" },
                          { key: "message", header: "Error", accessor: (err: any) => err.message },
                        ]}
                        data={shownRowErrors}
                        keyAccessor={(err: any) => err.__index}
                        caption="Row errors (first 10)"
                        sortable={false}
                        filterable={false}
                        emptyMessage="No errors"
                      />
                    </div>
                    {rowErrors.length > shownRowErrors.length && (
                      <p className="text-xs text-fg-muted mt-2">
                        Showing the first {shownRowErrors.length} of{" "}
                        {rowErrors.length} errors — the CSV download holds them all.
                      </p>
                    )}
                    <p className="text-xs text-fg-muted mt-2">
                      A rejected row is never written. The commit stays disabled until this
                      file has no rejected rows — download the error file to see why each
                      one was refused, fix it, and run the dry run again.
                    </p>
                    {downloadError && (
                      <Alert tone="error" title="The error file could not be downloaded">
                        <p>{downloadError}</p>
                      </Alert>
                    )}
                  </div>
                )}

                <div className="flex gap-3">
                  <Button
                    onClick={handleCommit}
                    disabled={
                      rejected > 0 ||
                      committing ||
                      outcome !== null ||
                      !dryRunReport.confirmation_token
                    }
                    className="flex-1"
                  >
                    {committing ? "Committing…" : "Commit Import"}
                  </Button>
                  {/* Offered only when there is something to download:
                      without rejected rows there is no error file. */}
                  {rejected > 0 && (
                    <Button
                      onClick={handleDownload}
                      variant="outline"
                      disabled={downloading}
                      className="flex-1"
                    >
                      {downloading ? "Downloading…" : "Download Error CSV"}
                    </Button>
                  )}
                </div>

                {commitError && (
                  <Alert tone="error" title="The commit was not accepted">
                    <p>{commitError}</p>
                    <p className="mt-1">
                      Nothing is applied until the server answers that it was; a commit
                      that failed can be tried again.
                    </p>
                  </Alert>
                )}

                {outcome?.kind === "committed" && (
                  <Alert tone="success" title="Import committed successfully">
                    {outcome.report.created + outcome.report.updated} row
                    {outcome.report.created + outcome.report.updated === 1 ? "" : "s"} applied
                    ({outcome.report.created} created, {outcome.report.updated} updated).
                    Nothing further is pending for this file.
                  </Alert>
                )}

                {outcome?.kind === "queued" && (
                  <div role="status" className="mt-4">
                    <h3 className="mk-h2 text-fg">
                      Import queued — it is running in the background
                    </h3>
                    <p className="text-sm text-fg-muted mt-1">
                      The file is large, so the server queued it for a background job
                      {outcome.job ? (
                        <> — job #{outcome.job.id} · {outcome.job.type}</>
                      ) : (
                        " — the job's reference was not in the response"
                      )}
                      . Queued{" "}
                      {outcome.job ? (
                        <Badge variant={PHASE_BADGE[queuedPhase] as any} className="inline-block">
                          {outcome.job.state}
                        </Badge>
                      ) : (
                        "state: unknown"
                      )}
                    </p>
                    <p className="text-sm text-fg mt-2 font-medium">
                      This import has not been committed: nothing has been applied yet.
                      The job applies the file in one transaction — every row the
                      preview showed, or none of them.
                    </p>
                    <div className="mt-3" role="status" aria-live="polite">
                      {progressError && (
                        <Alert tone="error" title="The job's progress could not be read">
                          <p>{progressError}</p>
                          <p className="mt-1">
                            This is a failed read, not a failed job. The screen keeps
                            asking; it never shows a state the server did not send.
                          </p>
                        </Alert>
                      )}
                      {progress ? (
                        <>
                          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-fg">
                            <Badge variant={PHASE_BADGE[progress.phase] as any} className="inline-block">
                              {progress.state}
                            </Badge>
                            <span>
                              {progress.rowsApplied} of {progress.rowsTotal} rows applied
                            </span>
                            <span>{progress.rowsRejected} rejected</span>
                            <span>{progress.percent}%</span>
                            {progress.batchesTotal > 0 && (
                              <span>
                                batch {progress.batchesDone} of {progress.batchesTotal}
                              </span>
                            )}
                          </div>
                          {progress.note && (
                            <p className="text-sm text-fg-muted mt-2">
                              {progress.note}
                            </p>
                          )}
                          {progress.phase === "failed" &&
                            progress.rowsAppliedBeforeFailure > 0 && (
                              <p className="text-sm text-fg-muted mt-1">
                                It had reached {progress.rowsAppliedBeforeFailure} rows
                                before it failed. The import is one transaction, so the
                                rollback took them back: none of them is in the database.
                              </p>
                            )}
                          {progress.failure?.message && (
                            <Alert tone="error" title="The job failed">
                              <p>{progress.failure.message}</p>
                            </Alert>
                          )}
                          {progress.result && (
                            <p className="text-sm text-fg mt-2 font-medium">
                              Applied: created {progress.result.created} · updated{" "}
                              {progress.result.updated} · unchanged{" "}
                              {progress.result.unchanged} · rejected{" "}
                              {progress.result.rejected}.
                            </p>
                          )}
                          {canCancel &&
                            !isTerminalPhase(progress.phase) &&
                            progress.importStatus !== "cancelled" && (
                              <Button
                                variant="outline"
                                onClick={handleCancel}
                                disabled={cancelling}
                                className="mt-3"
                              >
                                {cancelling ? "Cancelling…" : "Cancel this import"}
                              </Button>
                            )}
                        </>
                      ) : (
                        <p className="text-sm text-fg-muted">
                          Reading the job&rsquo;s progress…
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </SectionCard>
          )}
        </div>
      </div>
    </Layout>
  )
}