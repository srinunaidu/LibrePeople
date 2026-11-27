/* Update & version management (update-system slice, SuperAdmin only).
 * Consent-gated manual updates: version panel, changelog view, pre-install
 * gate checks, install button (enabled only when all gates pass; dry-run
 * first), install-attempt history. The app never self-overwrites; the
 * install endpoint records history and returns operator deploy steps.
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import { Alert, Button, EmptyState, LoadingRegion, PageHeader, SectionCard, RetryableAlert } from "@/components/ui"
import { useAuth } from "@/context/AuthContext"
import api, { errorMessage } from "@/lib/api"

type Gate = { gate: string; passed: boolean; remediation: string; plan?: string }

type GateReason = { gates?: Gate[] }

const reasonOf = (e: unknown): GateReason | undefined => {
  const r = e as { response?: { data?: { error?: { details?: { reason?: GateReason } } } } }
  return r.response?.data?.error?.details?.reason
}
type Manifest = {
  version: string
  channel: string
  released_at: string
  git_sha: string
  app_version: string
  db_head_revision: string
  min_version: string
  breaking_changes: string[]
  notes_url: string
  changelog: string
  artifacts: { name: string; sha256: string }[]
  manifest_sha256: string
  signature: { alg: string; key_id: string; sig: string }
}

export default function Updates() {
  const { user } = useAuth()
  const canView = user?.role === "SuperAdmin"

  const [current, setCurrent] = useState<Record<string, unknown> | null>(null)
  const [manifest, setManifest] = useState<Manifest | null>(null)
  const [devWarning, setDevWarning] = useState<string | null>(null)
  const [remote, setRemote] = useState<{ allowed: boolean; reason: string } | null>(null)
  const [gates, setGates] = useState<Gate[] | null>(null)
  const [history, setHistory] = useState<Record<string, unknown>[]>([])
  const [loading, setLoading] = useState(true)
  const [checking, setChecking] = useState(false)
  const [installing, setInstalling] = useState(false)
  const [notice, setNotice] = useState("")
  const [error, setError] = useState<unknown | null>(null)

  const load = useCallback(async () => {
    if (!canView) { setLoading(false); return }
    setLoading(true); setError(null); setNotice("")
    try {
      const [cur, avail, hist] = await Promise.all([
        api.get("/admin/updates/current"),
        api.get("/admin/updates/available"),
        api.get("/admin/updates/history"),
      ])
      setCurrent(cur.data)
      setManifest(avail.data.manifest)
      setDevWarning(avail.data.dev_warning ?? null)
      setRemote(avail.data.remote)
      setHistory(hist.data.entries ?? [])
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [canView])

  useEffect(() => { load() }, [load])

  const runCheck = async () => {
    setChecking(true); setNotice(""); setError(null)
    try {
      // Dry-run first: gates without committing to an install.
      await api.post("/admin/updates/check", { dry_run: true })
      setNotice("All pre-install gates passed. The release is safe to stage for deploy.")
      const hist = await api.get("/admin/updates/history")
      setHistory(hist.data.entries ?? [])
    } catch (e) {
      const msg = errorMessage(e)
      const reason = reasonOf(e)
      if (reason?.gates) setGates(reason.gates)
      setError(e)
      if (!reason?.gates) setNotice(msg)
    } finally { setChecking(false) }
  }

  const runInstall = async () => {
    if (!manifest) return
    setInstalling(true); setNotice(""); setError(null)
    try {
      const { data } = await api.post("/admin/updates/install", {
        manifest_sha256: manifest.manifest_sha256,
      })
      setNotice(`Install staged for ${data.version}. Operator action: ${data.operator_action}`)
      const hist = await api.get("/admin/updates/history")
      setHistory(hist.data.entries ?? [])
    } catch (e) {
      const reason = reasonOf(e)
      if (reason?.gates) setGates(reason.gates)
      setError(e)
    } finally { setInstalling(false) }
  }

  if (!canView) {
    return (
      <Layout>
        <PageHeader title="Updates" description="Platform version management" />
        <EmptyState title="SuperAdmin only" description="Upgrade state is a platform-operator concern." />
      </Layout>
    )
  }

  if (loading) {
    return (
      <Layout>
        <PageHeader title="Updates" description="Consent-gated manual updates — the system never pulls code by itself" />
        <LoadingRegion label="Updates">Loading update status…</LoadingRegion>
      </Layout>
    )
  }

  const allPass = gates !== null && gates.length > 0 && gates.every((g) => g.passed)

  return (
    <Layout>
      <PageHeader
        title="Updates"
        description="Consent-gated manual updates — the system never pulls code by itself"
        actions={<Button onClick={load}>Refresh</Button>}
      />
      {notice && <Alert tone="success">{notice}</Alert>}
      {!!error && <RetryableAlert err={error} title="The update status could not be read." onRetry={load} />}
      {devWarning && <Alert tone="warning">{devWarning}</Alert>}
        <SectionCard title="Installed version">
          {current ? (
            <dl>
              <dt>Application</dt><dd>{String(current.app_version)} ({String(current.project)})</dd>
              <dt>Database revision</dt><dd>{String(current.current_revision ?? "unknown")}</dd>
              <dt>Code head</dt><dd>{String(current.head_revision ?? "unknown")}</dd>
              <dt>Up to date</dt><dd>{current.up_to_date ? "yes" : "no"}</dd>
            </dl>
          ) : (
            <EmptyState title="No version data" description="Could not read the installed version." />
          )}
        </SectionCard>

        <SectionCard title="Available release (local manifest)">
          {manifest ? (
            <>
              <p>Version {manifest.version} ({manifest.channel}) — released {manifest.released_at}</p>
              <p>Minimum installed version: {manifest.min_version} · DB head: {manifest.db_head_revision}</p>
              <h4>Changelog</h4>
              <p>{manifest.changelog || "—"}</p>
              {manifest.breaking_changes.length > 0 && (
                <>
                  <h4>Breaking changes</h4>
                  <ul>{manifest.breaking_changes.map((b) => <li key={b}>{b}</li>)}</ul>
                </>
              )}
              <p>Signature: {manifest.signature.alg} / {manifest.signature.key_id}</p>
              {remote && <p>Remote check: {remote.allowed ? "permitted" : `off — ${remote.reason}`}</p>}
            </>
          ) : (
            <EmptyState title="No manifest" description="No local release manifest found." />
          )}
        </SectionCard>

        <SectionCard
          title="Pre-install gates"
          actions={
            <>
              <Button onClick={runCheck} disabled={checking || !manifest}>
                {checking ? "Checking…" : "Dry-run check"}
              </Button>
              <Button onClick={runInstall} disabled={installing || !allPass} variant="primary">
                {installing ? "Staging…" : "Stage install"}
              </Button>
            </>
          }
        >
          {gates === null ? (
            <EmptyState
              title="Not checked yet"
              description="Run a dry-run check first. The install button enables only when every gate passes."
            />
          ) : (
            <ul>
              {gates.map((g) => (
                <li key={g.gate}>
                  {g.passed ? "✓" : "✗"} {g.gate}
                  {!g.passed && g.remediation && <p>{g.remediation}</p>}
                  {g.passed && g.plan && <p>{g.plan}</p>}
                </li>
              ))}
            </ul>
          )}
        </SectionCard>

        <SectionCard title="Install history">
          {history.length === 0 ? (
            <EmptyState title="No attempts yet" description="Install attempts are recorded here and in the audit chain." />
          ) : (
            <ul>
              {history.map((h, i) => (
                <li key={i}>
                  {String(h.version)} — {h.accepted ? "staged" : "refused"} by {String(h.actor)} at {String(h.recorded_at)}
                </li>
              ))}
            </ul>
          )}
        </SectionCard>
    </Layout>
  )
}
