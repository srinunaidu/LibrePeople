import { useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {
  Button,
  Alert,
  EmptyState,
  LoadingRegion,
  PageHeader,
  SectionCard,
  StatusPill, Table } from "@/components/ui"
import { IconBriefcase, IconCheck, IconRefresh } from "@/components/icons"
import api, { errorMessage } from "@/lib/api"
import { ackable, ASSET_STATUS_LABELS, type AssetRow, type AssignmentRow } from "@/pages/Assets"

/**
 * My Assets — the employee's own custody view.
 *
 * The backend scopes this list to the caller (`mine=true`); an Associate
 * cannot see anyone else's custody. Acknowledgement is self-only: the
 * button appears exactly when the spell is open and unacknowledged, and
 * the server refuses anyone else (even HR) with 403.
 */
export default function MyAssets() {
  const [assignments, setAssignments] = useState<AssignmentRow[]>([])
  const [assets, setAssets] = useState<AssetRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [busy, setBusy] = useState<number | null>(null)

  const load = async () => {
    setLoading(true)
    setError("")
    const [a, s] = await Promise.allSettled([
      api.get("/assets"),
      api.get("/assets/assignments", { params: { mine: true } }),
    ])
    if (a.status === "fulfilled") setAssets(a.value.data)
    if (s.status === "fulfilled") setAssignments(s.value.data)
    if (s.status !== "fulfilled") {
      setError(errorMessage(s.reason, "Could not load your assets."))
    }
    setLoading(false)
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const acknowledge = async (a: AssignmentRow) => {
    setBusy(a.id)
    setError("")
    setNotice("")
    try {
      await api.post(`/assets/assignments/${a.id}/ack`)
      setNotice("Receipt acknowledged. The asset is now recorded as yours.")
      await load()
    } catch (err) {
      setError(errorMessage(err, "Could not acknowledge receipt."))
    } finally {
      setBusy(null)
    }
  }

  const assetOf = (id: number) => assets.find((x) => x.id === id)
  const open = assignments.filter((a) => a.status === "open")
  const history = assignments.filter((a) => a.status !== "open")
  const pendingAck = open.filter(ackable).length

  return (
    <Layout>
      <PageHeader
        compact
        icon={<IconBriefcase />}
        title="My Assets"
        description="Equipment assigned to you. Acknowledge receipt so custody is on record."
        actions={
          <Button variant="secondary" size="sm" type="button" onClick={load}>
            <IconRefresh className="w-4 h-4" /> Reload
          </Button>
        }
      />

      {error && (
        <Alert tone="error" title="My assets unavailable" action={
          <Button variant="secondary" size="sm" type="button" onClick={load}>Retry</Button>
        }>
          {error}
        </Alert>
      )}
      {notice && <Alert tone="success">{notice}</Alert>}
      {!loading && pendingAck > 0 && (
        <Alert tone="warning" title={`${pendingAck} asset${pendingAck === 1 ? "" : "s"} awaiting your acknowledgement`}>
          Acknowledge receipt below — only you can do this, not HR on your behalf.
        </Alert>
      )}

      {loading ? (
        <LoadingRegion label="Loading your assets">
          <div className="skeleton h-40" />
        </LoadingRegion>
      ) : (
        <div className="grid grid-cols-1 gap-5 mb-5">
          <SectionCard compact icon={<IconBriefcase />} title="In your custody"
            description="Open assignments. Returns and transfers are handled by HR.">
            {open.length === 0 ? (
              <EmptyState title="Nothing assigned" description="You hold no company assets right now." />
            ) : (
              <Table
                columns={[
                  { key: "tag", header: "Tag", accessor: (a) => <span className="font-mono">{assetOf(a.asset_id)?.tag ?? `#${a.asset_id}`}</span> },
                  { key: "asset", header: "Asset", accessor: (a) => assetOf(a.asset_id)?.name ?? "Asset" },
                  { key: "assigned", header: "Assigned", accessor: (a) => (a.assigned_at ? a.assigned_at.slice(0, 10) : "—") },
                  {
                    key: "receipt",
                    header: "Receipt",
                    accessor: (a) => <StatusPill status={a.acknowledged_at ? "Acknowledged" : "Pending"} />,
                  },
                  {
                    key: "actions",
                    header: "",
                    accessor: (a) => (
                      ackable(a) ? (
                        <Button variant="primary" size="sm" type="button"
                          disabled={busy === a.id}
                          onClick={() => acknowledge(a)}>
                          <IconCheck className="w-4 h-4" />
                          {busy === a.id ? "Acknowledging…" : "Acknowledge receipt"}
                        </Button>
                      ) : (
                        <span className="text-sm text-fg-muted">On record</span>
                      )
                    ),
                  },
                ]}
                data={open}
                keyAccessor={(a) => a.id}
                caption="Assets currently in your custody"
                sortable={false}
              />
            )}
          </SectionCard>

          <SectionCard compact title="Custody history"
            description="Spells that ended by return or transfer.">
            {history.length === 0 ? (
              <EmptyState title="No history" description="Past assignments will appear here." />
            ) : (
              <Table
                columns={[
                  { key: "tag", header: "Tag", accessor: (a) => <span className="font-mono">{assetOf(a.asset_id)?.tag ?? `#${a.asset_id}`}</span> },
                  { key: "asset", header: "Asset", accessor: (a) => assetOf(a.asset_id)?.name ?? "Asset" },
                  { key: "closed", header: "Closed", accessor: (a) => (a.closed_at ? a.closed_at.slice(0, 10) : "—") },
                  {
                    key: "how",
                    header: "How",
                    accessor: (a) =>
                      a.close_reason === "returned"
                        ? `Returned (${a.return_condition ?? "—"})`
                        : a.close_reason === "transferred"
                          ? "Transferred"
                          : "Closed",
                  },
                ]}
                data={history}
                keyAccessor={(a) => a.id}
                caption="Your past asset assignments"
                sortable={false}
              />
            )}
          </SectionCard>

          <p className="text-sm text-fg-muted" role="note">
            Asset status key: {Object.values(ASSET_STATUS_LABELS).join(" · ")}. Register changes are made by HR/Admin.
          </p>
        </div>
      )}
    </Layout>
  )
}