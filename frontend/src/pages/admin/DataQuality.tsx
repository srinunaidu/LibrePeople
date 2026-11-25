/**
 * Data Quality — checks, issues and scans.
 *
 * Gates mirror backend/app/api/v1/endpoints/data_quality.py: ADMIN_ROLES
 * (SuperAdmin, HR). Every read is independent so a 403 on checks must not
 * blank the issues table. The issue list is the ledger that keeps the
 * directory honest — an empty report is "checked and found nothing", not
 * "not checked".
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert,
  Button,
  EmptyState,
  LoadingRegion,
  PageHeader,
  SectionCard,
  TableSkeleton, RetryableAlert} from "@/components/ui"
import { StatusPill } from "@/components/ui/status-pill"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { errorMessage } from "@/lib/api"
import type {
  DataQualityChecksResponse,
  DataQualityIssuesResponse,
  DataQualityIssueRow,
  DataQualityScanResult,
} from "@/types"

function fmtDate(value?: string | null) {
  if (!value) return "—"
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value.slice(0, 19).replace("T", " ")
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(d)
}

function severityTone(sev: string): "rose" | "amber" | "slate" | "brand" {
  if (sev === "critical") return "rose"
  if (sev === "warning") return "amber"
  if (sev === "info") return "brand"
  return "slate"
}

export default function DataQuality() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const canRead = ["SuperAdmin", "HR"].includes(user?.role ?? "")

  const [checksData, setChecksData] = useState<DataQualityChecksResponse | null>(null)
  const [issuesData, setIssuesData] = useState<DataQualityIssuesResponse | null>(null)
  const [scanResult, setScanResult] = useState<DataQualityScanResult | null>(null)

  const [loading, setLoading] = useState(true)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [scanBusy, setScanBusy] = useState(false)
  const [scanError, setScanError] = useState("")
  const [notice, setNotice] = useState("")

  const load = useCallback(async () => {
    setLoading(true)
    setErrors({})
    const checksPromise = canRead ? api.get<DataQualityChecksResponse>("/data-quality/checks") : Promise.resolve(null)
    const issuesPromise = canRead ? api.get<DataQualityIssuesResponse>("/data-quality/issues") : Promise.resolve(null)

    const [checksResult, issuesResult] = await Promise.allSettled([checksPromise, issuesPromise])

    const next: Record<string, string> = {}
    if (checksResult.status === "fulfilled") {
      setChecksData((checksResult.value?.data as unknown as DataQualityChecksResponse) ?? null)
    } else if (canRead) {
      setChecksData(null)
      next.checks = checksResult.reason
    }
    if (issuesResult.status === "fulfilled") {
      setIssuesData((issuesResult.value?.data as unknown as DataQualityIssuesResponse) ?? null)
    } else if (canRead) {
      setIssuesData(null)
      next.issues = issuesResult.reason
    }
    setErrors(next)
    setLoading(false)
  }, [canRead])

  useEffect(() => {
    void load()
  }, [load])

  const runScan = async () => {
    if (scanBusy) return
    setScanBusy(true)
    setScanError("")
    setNotice("")
    try {
      const res = await api.post<DataQualityScanResult>("/data-quality/scan")
      setScanResult(res.data)
      // Refresh issues after a scan — the ledger just changed.
      await load()
      setNotice(`Scan complete: ${res.data.summary.total} issue(s) — critical ${res.data.summary.by_severity?.critical ?? 0} · warning ${res.data.summary.by_severity?.warning ?? 0} · info ${res.data.summary.by_severity?.info ?? 0}`)
    } catch (err) {
      setScanError(errorMessage(err, "The scan could not be run."))
    } finally {
      setScanBusy(false)
    }
  }

  if (!canRead) {
    return (
      <Layout>
        <div data-tenant-slug={tenant?.slug ?? "—"}>
          <PageHeader
            compact
            title="Data Quality"
            description="Checks, issues and scans — the ledger that keeps the directory honest"
          />
          <EmptyState
            title="Not visible for your role"
            description={`Data quality requires SuperAdmin or HR; your role is ${user?.role || "unknown"}.`}
          />
        </div>
      </Layout>
    )
  }

  const issueRows: DataQualityIssueRow[] = issuesData?.issues ?? []

  return (
    <Layout>
      <div data-tenant-slug={tenant?.slug ?? "—"}>
        <PageHeader
        compact
        title="Data Quality"
        description="Checks, issues and scans — the ledger that keeps the directory honest"
        actions={
          <Button onClick={runScan} loading={scanBusy}>
            Run scan
          </Button>
        }
      />

      {!!scanError && <Alert tone="error" title="The scan could not be run">{scanError}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}

      {/* Checks — GET /data-quality/checks */}
      <SectionCard
        compact
        title="Checks"
        description="Which data-quality rules are registered. Read-only; remediation is a separate, audited action."
      >
        {loading ? (
          <LoadingRegion label="Loading checks…">
            <TableSkeleton rows={4} cols={3} />
          </LoadingRegion>
        ) : errors.checks ? (
          <div className="p-5">
            <RetryableAlert err={errors.checks} title="The checks could not be read" fallback="The checks could not be read" onRetry={load} />
          </div>
        ) : !checksData || checksData.checks.length === 0 ? (
          <div className="p-5">
            <EmptyState
              title="No checks registered"
              description="No data-quality rules are registered on this deployment."
            />
          </div>
        ) : (
          <div className="table-scroll">
            <table className="table-base table-compact w-full text-sm">
              <caption className="sr-only">Data-quality checks</caption>
              <thead>
                <tr>
                  <th scope="col">Check (code)</th>
                  <th scope="col">Severities</th>
                  <th scope="col">Note</th>
                </tr>
              </thead>
              <tbody>
                {checksData.checks.map((code) => (
                  <tr key={code}>
                    <td className="font-mono text-xs">{code}</td>
                    <td className="text-xs text-text-secondary">{checksData.severities.join(", ")}</td>
                    <td className="text-xs text-text-secondary max-w-[320px] truncate" title={checksData.note}>
                      {checksData.note}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          )
          }

      </SectionCard>
      {/* Issues — GET /data-quality/issues */}
      <SectionCard
        compact
        title="Issues"
        description="Findings worst-first. An empty report means checked and found nothing — not 'not checked'."
        actions={
          <Button variant="secondary" onClick={() => void load()} disabled={loading}>
            Refresh
          </Button>
        }
      >
        {loading ? (
          <LoadingRegion label="Loading issues…">
            <TableSkeleton rows={6} cols={5} />
          </LoadingRegion>
        ) : errors.issues ? (
          <div className="p-5">
            <RetryableAlert err={errors.issues} title="The issues could not be read" fallback="The issues could not be read" onRetry={load} />
          </div>
        ) : issueRows.length === 0 ? (
          <div className="p-5">
            <EmptyState
              title="No issues"
              description="The checks ran and found nothing. That is an empty report, not a missed run."
            />
          </div>
        ) : (
          <>
            {issuesData?.summary && (
              <div className="px-5 py-3 border-b border-border text-xs text-text-secondary">
                {issuesData.summary.total} total · critical {issuesData.summary.by_severity?.critical ?? 0} · warning{" "}
                {issuesData.summary.by_severity?.warning ?? 0} · info {issuesData.summary.by_severity?.info ?? 0}
                {issuesData.truncated && <> · truncated at {issuesData.returned}</>} · checked at{" "}
                {fmtDate(issuesData.summary.checked_at)}
              </div>
            )}
            <div className="table-scroll">
              <table className="table-base table-compact w-full text-sm">
                <caption className="sr-only">Data-quality issues</caption>
                <thead>
                  <tr>
                    <th scope="col">Check / code</th>
                    <th scope="col">Severity</th>
                    <th scope="col">Entity</th>
                    <th scope="col">Message</th>
                    <th scope="col">Owner</th>
                  </tr>
                </thead>
                <tbody>
                  {issueRows.map((issue, idx) => (
                    <tr key={`${issue.code}-${issue.entity_id ?? idx}`}>
                      <td className="font-mono text-xs" title={issue.code}>
                        {issue.code}
                      </td>
                      <td>
                        <StatusPill status={issue.severity} tone={severityTone(issue.severity)} />
                      </td>
                      <td className="text-xs">
                        {issue.entity_type}
                        {issue.entity_id ? ` #${issue.entity_id}` : ""}
                      </td>
                      <td className="max-w-[360px]">
                        <p className="font-medium text-xs">{issue.title}</p>
                        <p className="text-xs text-text-secondary line-clamp-2" title={issue.explanation}>
                          {issue.explanation}
                        </p>
                      </td>
                      <td className="text-xs">{issue.owner_role}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}</SectionCard>

      {/* Scan — POST /data-quality/scan */}
      <SectionCard
        compact
        title="Scan"
        description="Run every check now and record it in the audit trail. Use before go-live and after a bulk import."
      >
        <div className="p-5">
          <p className="text-sm text-text-secondary mb-3">
            A scan is an action, not a page load. It walks every registered rule and returns the summary. The call
            is audited as <code className="font-mono text-xs">data_quality_scan</code>.
          </p>
          <Button onClick={runScan} loading={scanBusy}>
            Run full scan
          </Button>
          {scanResult && (
            <div className="mt-4 p-4 border border-border rounded-lg bg-surface-sunken">
              <p className="text-sm font-medium">Last scan</p>
              <p className="text-xs text-text-secondary mt-1">
                Total {scanResult.summary.total} · by severity{" "}
                {JSON.stringify(scanResult.summary.by_severity)} · by code{" "}
                {JSON.stringify(scanResult.summary.by_code)} · at {fmtDate(scanResult.summary.checked_at)}
              </p>
            </div>
          )}
        </div>
      </SectionCard>
      </div>
    </Layout>
  )
}