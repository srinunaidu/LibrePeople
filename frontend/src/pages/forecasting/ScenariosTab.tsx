/**
 * Scenarios — list/create, version timeline, edit-as-next-version, fork and
 * compare (AN-05).
 *
 * Honesty points this screen keeps:
 *  - assumptions may arrive on the wire as a JSON string; normalised before use;
 *  - costs in the comparison appear ONLY when rates were supplied with the
 *    request — when absent the column reads "—", and the label shown is the
 *    one the response sent ("excludes statutory on-costs");
 *  - the cost projection applies the DEFAULT rate (the scenario series has no
 *    role split — the schema allows extra keys but they do nothing here, and
 *    the screen says so).
 */
import { useEffect, useRef, useState } from "react"
import {Alert,
  Button,
  EmptyState,
  Input,
  LoadingRegion,
  SectionCard,
  TableSkeleton, RetryableAlert} from "@/components/ui"
import { StatusPill } from "@/components/ui/status-pill"
import api, { isRetryable } from "@/lib/api" // RetryableAlert gate
import type {
  ComparisonPeriod,
  ForecastRunOut,
  PaginatedScenarios,
  ScenarioAssumption,
  ScenarioComparison,
  ScenarioCostProjectionOut,
  ScenarioOut,
  ScenarioVersionList,
} from "@/types"
import {
  AssumptionEditor,
  assumptionsToDrafts,
  AssumptionRowDraft,
  draftsToAssumptions,
  fmtCost,
  fmtDate,
  fmtDateTime,
  fmtNum,
  normaliseAssumptions,
  readableLoadError,
  SimpleTable,
} from "./shared"

export default function ScenariosTab() {
  const [scenarios, setScenarios] = useState<ScenarioOut[]>([])
  const [runs, setRuns] = useState<ForecastRunOut[]>([])
  const [loading, setLoading] = useState(true)
  const [listError, setListError] = useState("")
  const [attempt, setAttempt] = useState(0)
  const loadedAttempt = useRef(-1)

  useEffect(() => {
    if (loadedAttempt.current === attempt) return
    loadedAttempt.current = attempt
    let cancelled = false
    setLoading(true)
    setListError("")
    const scenRes = api.get<PaginatedScenarios>("/forecasting/scenarios?page_size=200")
    const runsRes = api.get<ForecastRunOut[]>("/forecasting/runs?limit=100")
    void Promise.allSettled([scenRes, runsRes]).then(([sScen, sRuns]) => {
      if (cancelled) return
      if (sScen.status === "fulfilled") setScenarios(sScen.value.data.items ?? [])
      else setListError(readableLoadError(sScen.reason, "Could not load the scenarios."))
      if (sRuns.status === "fulfilled") setRuns(sRuns.value.data)
      setLoading(false)
    })
    return () => {
      cancelled = true
    }
  }, [attempt])

  /* ---- selected scenario + its versions ---------------------------- */
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [versions, setVersions] = useState<ScenarioVersionList["items"]>([])
  const [versionsError, setVersionsError] = useState("")
  const [versionsLoading, setVersionsLoading] = useState(false)
  const selected = scenarios.find((s) => s.id === selectedId) ?? null

  useEffect(() => {
    if (selectedId == null) return
    let cancelled = false
    setVersionsLoading(true)
    setVersionsError("")
    api
      .get<ScenarioVersionList>(`/forecasting/scenarios/${selectedId}/versions`)
      .then((res) => {
        if (!cancelled) setVersions(res.data.items ?? [])
      })
      .catch((err) => {
        if (!cancelled)
          setVersionsError(readableLoadError(err, "The version timeline could not be loaded."))
      })
      .finally(() => {
        if (!cancelled) setVersionsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [selectedId])

  const [notice, setNotice] = useState("")

  /* ---- create ------------------------------------------------------- */
  const [createName, setCreateName] = useState("")
  const [createDescription, setCreateDescription] = useState("")
  const [baseRunId, setBaseRunId] = useState("")
  const [createRows, setCreateRows] = useState<AssumptionRowDraft[]>([])
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState("")

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    const { assumptions, error } = draftsToAssumptions(createRows)
    if (error) {
      setCreateError(error)
      return
    }
    if (!baseRunId) {
      setCreateError("Choose the base forecast run this scenario variants.")
      return
    }
    setCreating(true)
    setCreateError("")
    try {
      const res = await api.post<ScenarioOut>("/forecasting/scenarios", {
        base_run_id: Number(baseRunId),
        name: createName.trim(),
        description: createDescription.trim() || null,
        assumptions,
      })
      setScenarios((prev) => [res.data, ...prev])
      setSelectedId(res.data.id)
      setCreateName("")
      setCreateDescription("")
      setBaseRunId("")
      setCreateRows([])
      setNotice(`Scenario "${res.data.name}" created as an explicit assumption set.`)
    } catch (err) {
      setCreateError(readableLoadError(err, "The scenario could not be created."))
    } finally {
      setCreating(false)
    }
  }

  /* ---- edit -> next version ----------------------------------------- */
  const [editRows, setEditRows] = useState<AssumptionRowDraft[] | null>(null)
  const [editing, setEditing] = useState(false)
  const [editError, setEditError] = useState("")
  const [editName, setEditName] = useState("")

  // An edit starts from the CURRENT assumption set of the selected scenario:
  // reset on selection and let the seed effect run when the fresh timeline
  // lands (stale versions from a previous scenario must never seed it).
  useEffect(() => {
    setEditRows(null)
    setEditError("")
    setEditName("")
    setVersions([])
  }, [selectedId])
  // Seed the editor each time a fresh version timeline lands and no edit
  // is in flight (after an edit this re-seeds from the new latest version).
  useEffect(() => {
    if (selectedId == null) return
    if (editRows != null) return
    const latest = versions[versions.length - 1]
    if (!latest) return
    setEditRows(assumptionsToDrafts(normaliseAssumptions(latest.assumptions)))
  }, [versions, selectedId, editRows])

  async function handleEditSubmit() {
    if (selectedId == null || editRows == null || editing) return
    const { assumptions, error } = draftsToAssumptions(editRows)
    if (error) {
      setEditError(error)
      return
    }
    setEditing(true)
    setEditError("")
    try {
      const res = await api.post<ScenarioOut>(`/forecasting/scenarios/${selectedId}/versions`, {
        assumptions,
        name: editName.trim() || null,
      })
      setNotice(`Version ${res.data.version_no} stored — the previous versions stay intact and comparable.`)
      setEditRows(null)
      const resVersions = await api.get<ScenarioVersionList>(`/forecasting/scenarios/${selectedId}/versions`)
      setVersions(resVersions.data.items ?? [])
      setAttempt((a) => a + 1)
    } catch (err) {
      setEditError(readableLoadError(err, "The edit was refused."))
    } finally {
      setEditing(false)
    }
  }

  /* ---- fork --------------------------------------------------------- */
  const [forkName, setForkName] = useState("")
  const [forking, setForking] = useState(false)
  const [forkError, setForkError] = useState("")

  async function handleFork() {
    if (selectedId == null || forking) return
    setForking(true)
    setForkError("")
    try {
      const res = await api.post<ScenarioOut>(`/forecasting/scenarios/${selectedId}/fork`, {
        name: forkName.trim() || null,
      })
      setScenarios((prev) => [res.data, ...prev])
      setSelectedId(res.data.id)
      setForkName("")
      setNotice(`Forked into "${res.data.name}" (id ${res.data.id}) — an independent lineage starting at version 1.`)
      const resVersions = await api.get<ScenarioVersionList>(`/forecasting/scenarios/${res.data.id}/versions`)
      setVersions(resVersions.data.items ?? [])
    } catch (err) {
      setForkError(readableLoadError(err, "The fork was refused."))
    } finally {
      setForking(false)
    }
  }

  /* ---- compare ------------------------------------------------------ */
  const [compareIds, setCompareIds] = useState<number[]>([])
  const [compareDefaultRate, setCompareDefaultRate] = useState("")
  const [comparing, setComparing] = useState(false)
  const [compareError, setCompareError] = useState("")
  const [comparison, setComparison] = useState<ScenarioComparison | null>(null)

  const toggleCompare = (id: number) => {
    setCompareIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  async function handleCompare() {
    if (compareIds.length < 2 || comparing) return
    setComparing(true)
    setCompareError("")
    setComparison(null)
    try {
      const body: {
        scenario_ids: number[]
        hourly_costs?: Record<string, number>
      } = { scenario_ids: compareIds }
      if (compareDefaultRate !== "") body.hourly_costs = { default: Number(compareDefaultRate) }
      const res = await api.post<ScenarioComparison>("/forecasting/scenarios/compare", body)
      setComparison(res.data)
    } catch (err) {
      setCompareError(readableLoadError(err, "The comparison was refused."))
    } finally {
      setComparing(false)
    }
  }

  /* ------------------------------------------------------------------ */
  return (
    <div className="space-y-5">
      {notice && (
        null /* toast.success replaces Alert success */
      )}
      {listError && (
        <RetryableAlert err={listError} title="The scenario list failed to load" fallback="The scenario list failed to load." />
      )}

      <SectionCard title="Scenarios" description="Explicit, named assumption sets applied to a base forecast run.">
        <div className="p-5">
          {loading ? (
            <TableSkeleton rows={3} cols={6} />
          ) : scenarios.length === 0 ? (
            <EmptyState
              title="No scenarios yet"
              description="Create one below: pick a base run, name the assumptions, and the server applies nothing silently."
            />
          ) : (
            <SimpleTable
              caption="Scenarios"
              columns={["Name", "Base run", "Version", "Source", "Assumptions", "Created", "Lineage", ""]}
              rows={scenarios.map((s) => [
                <span key="n" className="font-medium text-fg">{s.name}</span>,
                `#${s.base_run_id}`,
                `v${s.version_no} of root ${s.root_id ?? s.id}`,
                s.source,
                <button
                  key="a"
                  type="button"
                  className="text-brand-700 hover:underline"
                  onClick={() => setSelectedId(s.id)}
                >
                  {normaliseAssumptions(s.assumptions).length} named
                </button>,
                fmtDateTime(s.created_at),
                <StatusPill key="p" status={s.forked_from_scenario_id ? "forked" : s.source} />,
                <Button
                  key="sel"
                  variant={selectedId === s.id ? "primary" : "outline"}
                  size="xs"
                  onClick={() => setSelectedId(s.id)}
                >
                  {selectedId === s.id ? "Selected" : "Open"}
                </Button>,
              ])}
            />
          )}
        </div>
      </SectionCard>

      {selected && (
        <SectionCard
          title={`"${selected.name}" — versions & actions`}
          description={`Base run #${selected.base_run_id} · lineage root ${selected.root_id ?? selected.id}${selected.forked_from_scenario_id ? ` · forked from scenario ${selected.forked_from_scenario_id}` : ""}`}
        >
          <div className="p-5 space-y-5">
            {versionsError && (
              <Alert tone="error" title="Version timeline unavailable">
                {versionsError}
              </Alert>
            )}
            {versionsLoading ? (
              <TableSkeleton rows={2} cols={5} />
            ) : (
              <SimpleTable
                caption="Version timeline, oldest first"
                columns={["Version", "Name", "Source", "Assumptions", "Forecast points", "Created"]}
                rows={versions.map((v) => [
                  <strong key="v">v{v.version_no}</strong>,
                  v.name,
                  v.source === "edited" ? "edited (new version stored)" : v.source,
                  <ul key="a" className="list-disc pl-4 text-xs">
                    {normaliseAssumptions(v.assumptions).map((a, i) => (
                      <li key={i}>
                        {a.key}: <strong>{String(a.value)}</strong>
                        {a.unit === "percent" ? " %" : ` (${a.unit})`}
                        {a.note ? <> — {a.note}</> : null}
                      </li>
                    ))}
                  </ul>,
                  v.results.length,
                  fmtDateTime(v.created_at),
                ])}
              />
            )}

            {/* Edit -> NEXT version */}
            <div className="border border-border rounded-lg p-4">
              <h3 className="text-sm font-semibold text-fg mb-2">
                Edit — stores the NEXT version
              </h3>
              <p className="text-xs text-text-secondary mb-3">
                Editing never overwrites: the assumption set becomes version{" "}
                {versions.length > 0 ? versions[versions.length - 1].version_no + 1 : "?"} of this
                lineage and the old versions stay comparable.
              </p>
              {editError && (
                <Alert tone="error" title="The edit was refused">
                  {editError}
                </Alert>
              )}
              {editRows == null ? (
                <Button variant="secondary" onClick={() => setEditRows(assumptionsToDrafts(normaliseAssumptions(versions[versions.length - 1]?.assumptions)))} disabled={versions.length === 0}>
                  Start editing from the latest assumptions
                </Button>
              ) : (
                <>
                  <AssumptionEditor rows={editRows} onChange={setEditRows} />
                  <div className="flex flex-wrap items-end gap-3 mt-3">
                    <label className="text-xs font-medium text-text-secondary">
                      Name for the new version (optional)
                      <Input
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="mt-1 block w-64"
                      />
                    </label>
                    <Button loading={editing} onClick={handleEditSubmit}>
                      Store as next version
                    </Button>
                    <Button variant="ghost" onClick={() => setEditRows(null)}>
                      Cancel edit
                    </Button>
                  </div>
                </>
              )}
            </div>

            {/* Fork */}
            <div className="border border-border rounded-lg p-4">
              <h3 className="text-sm font-semibold text-fg mb-2">Fork into a new lineage</h3>
              <p className="text-xs text-text-secondary mb-3">
                Copies this version's assumptions, starts its own version line at 1, and records
                exactly which version it forked from. The source changes nothing.
              </p>
              {forkError && (
                <Alert tone="error" title="The fork was refused">
                  {forkError}
                </Alert>
              )}
              <div className="flex flex-wrap items-end gap-3">
                <label className="text-xs font-medium text-text-secondary">
                  Name (optional)
                  <Input
                    value={forkName}
                    onChange={(e) => setForkName(e.target.value)}
                    className="mt-1 block w-64"
                  />
                </label>
                <Button variant="secondary" loading={forking} onClick={handleFork}>
                  Fork
                </Button>
              </div>
            </div>
          </div>
        </SectionCard>
      )}

      <SectionCard
        title="Compare scenarios side-by-side"
        description="Any two (or more) scenario versions; deltas are relative to the FIRST participant. Costs appear only when you supply an hourly rate."
      >
        <div className="p-5 space-y-4">
          {compareError && (
            <Alert tone="error" title="The comparison was refused">
              {compareError}
            </Alert>
          )}
          <div className="flex flex-wrap gap-2" role="group" aria-label="Pick scenarios to compare">
            {scenarios.length === 0 && (
              <p className="text-xs text-text-secondary">No scenarios to compare yet.</p>
            )}
            {scenarios.map((s) => {
              const active = compareIds.includes(s.id)
              return (
                <button
                  key={s.id}
                  type="button"
                  aria-pressed={active}
                  onClick={() => toggleCompare(s.id)}
                  className={`px-3 py-1.5 rounded-md text-sm font-medium border ${
                    active
                      ? "bg-brand-600 text-white border-brand-600"
                      : "bg-surface text-text-secondary border-border hover:bg-surface-hover"
                  }`}
                >
                  {s.name} <span className="text-xs">v{s.version_no}</span>
                </button>
              )
            })}
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <label className="text-xs font-medium text-text-secondary">
              Optional hourly rate used for the cost projection — the "default" rate
              <Input
                type="number"
                step="any"
                min="0"
                value={compareDefaultRate}
                onChange={(e) => setCompareDefaultRate(e.target.value)}
                placeholder="empty = compare demand only"
                className="mt-1 block w-72"
              />
            </label>
            <Button loading={comparing} disabled={compareIds.length < 2} onClick={handleCompare}>
              {compareIds.length < 2
                ? "Pick at least two"
                : `Compare ${compareIds.length}`}
            </Button>
            <p className="text-xs text-text-secondary max-w-md">
              The scenario series has no role split, so the projection applies the default rate (the
              schema accepts extra role keys, but they would not change this projection). Rates are
              explicit assumptions — none is ever guessed.
            </p>
          </div>

          {comparison && <ComparisonBody comparison={comparison} />}
        </div>
      </SectionCard>

      <SectionCard
        title="Create a scenario"
        description="An explicit, named assumption set applied to a base forecast run."
      >
        <form onSubmit={handleCreate} className="p-5 space-y-4" aria-label="Create scenario">
          {createError && (
            <Alert tone="error" title="The scenario was refused">
              {createError}
            </Alert>
          )}
          <div className="grid gap-4 sm:grid-cols-3">
            <label className="text-xs font-medium text-text-secondary">
              Name <span className="text-error-text" aria-hidden="true">*</span>
              <Input required maxLength={200} value={createName} onChange={(e) => setCreateName(e.target.value)} className="mt-1" />
            </label>
            <label className="text-xs font-medium text-text-secondary">
              Description
              <Input value={createDescription} onChange={(e) => setCreateDescription(e.target.value)} className="mt-1" />
            </label>
            <label className="text-xs font-medium text-text-secondary">
              Base forecast run <span className="text-error-text" aria-hidden="true">*</span>
              <select required className="input mt-1" value={baseRunId} onChange={(e) => setBaseRunId(e.target.value)}>
                <option value="">Pick a run…</option>
                {runs.map((r) => (
                  <option key={r.id} value={r.id}>
                    #{r.id} {r.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <AssumptionEditor rows={createRows} onChange={setCreateRows} />
          <Button type="submit" loading={creating}>
            Create scenario
          </Button>
        </form>
      </SectionCard>
    </div>
  )
}

/** Renders the comparison response: per-period values, deltas, assumptions,
 * and the optional cost projections exactly as labelled by the response. */
function ComparisonBody({ comparison }: { comparison: ScenarioComparison }) {
  const costs = comparison.costs ?? null
  const participants = comparison.scenarios
  return (
    <div className="space-y-5">
      <SimpleTable
        caption="Period-by-period comparison; deltas relative to the first participant"
        columns={["Date", ...participants.map((p) => `${p.name} (v${p.version_no})`), ...participants.slice(1).map((p) => `Δ ${p.name}`)]}
        rows={comparison.comparison.map((row: ComparisonPeriod) => [
          fmtDate(row.forecast_date),
          ...participants.map((p) => fmtNum(row.scenario_values[String(p.id)] ?? null)),
          ...participants.slice(1).map((p) => {
            const d = row.deltas[String(p.id)]
            return d == null ? "—" : (
              <span className={d >= 0 ? "text-success-text" : "text-error-text"}>
                {d >= 0 ? "+" : ""}
                {fmtNum(d)}
              </span>
            )
          }),
        ])}
      />

      {participants.map((p) => {
        const rows = normaliseAssumptions(p.assumptions)
        return (
          <div key={p.id}>
            <h3 className="text-sm font-semibold text-fg">
              {p.name} (v{p.version_no}) assumptions
            </h3>
            {rows.length === 0 ? (
              <p className="text-xs text-text-secondary">none recorded</p>
            ) : (
              <ul className="list-disc pl-4 text-xs">
                {rows.map((a: ScenarioAssumption, i) => (
                  <li key={i}>
                    {a.key}: <strong>{String(a.value)}</strong>
                    {a.unit === "percent" ? " %" : ` (${a.unit})`}
                    {a.note ? <> — {a.note}</> : null}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )
      })}

      {costs ? (
        <div className="space-y-3">
          <p className="text-xs font-medium text-text-secondary">
            Cost projections — {Object.values(costs)[0]?.cost_basis ?? "excludes statutory on-costs"}
          </p>
          <div className="grid gap-4 lg:grid-cols-2">
            {Object.entries(costs).map(([sid, proj]) => (
              <CostProjectionCard key={sid} sid={Number(sid)} proj={proj} />
            ))}
          </div>
        </div>
      ) : (
        <p className="text-xs text-text-secondary" role="note">
          Costs: — (no hourly rates were supplied with the comparison; supply one above to see the
          cost projection, which then appears with the statutory label).
        </p>
      )}
    </div>
  )
}

function CostProjectionCard({ sid, proj }: { sid: number; proj: ScenarioCostProjectionOut }) {
  const participant = proj.scenario_id ?? sid
  const delta = proj.total_cost_delta
  return (
    <div className="border border-border rounded-lg p-4">
      <h3 className="text-sm font-semibold text-fg">
        Scenario #{participant} — {proj.label}
      </h3>
      <dl className="grid grid-cols-3 gap-3 text-sm mt-2">
        <div>
          <dt className="text-xs text-text-secondary">Total hours</dt>
          <dd className="font-semibold">{fmtNum(proj.total_hours)}</dd>
        </div>
        <div>
          <dt className="text-xs text-text-secondary">Total cost — {proj.cost_basis}</dt>
          <dd className="font-semibold">{fmtCost(proj.total_cost)}</dd>
        </div>
        <div>
          <dt className="text-xs text-text-secondary">Δ vs first</dt>
          <dd className={`font-semibold ${delta != null && delta > 0 ? "text-error-text" : "text-success-text"}`}>
            {delta == null ? "—" : `${delta >= 0 ? "+" : ""}${fmtCost(delta)}`}
          </dd>
        </div>
      </dl>
      <p className="text-xs text-text-secondary mt-1">
        wage growth applied: {fmtNum(proj.wage_growth_pct)} % · rate {fmtCost(Object.values(proj.hourly_costs)[0] ?? null)}
      </p>
      <div className="mt-2">
        <SimpleTable
          caption={`Cost projection rows for scenario ${participant}`}
          columns={["Period", "Hours", "Hourly cost", "Cost — excludes statutory on-costs"]}
          rows={proj.rows.map((r, i) => [
            r.period,
            fmtNum(r.hours),
            fmtCost(r.hourly_cost),
            <strong key={`c${i}`}>{fmtCost(r.cost)}</strong>,
          ])}
        />
      </div>
    </div>
  )
}
