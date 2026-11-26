/* PY-07 — Bank export integration (depends PY-04)
 * Real endpoint: POST /payroll/runs/{id}/payment-file?format=nacha|neft
 * (backend/app/api/v1/endpoints/payroll.py — require_roles(*ADMIN_ROLES)).
 * The former "Export bank data" card POSTed /admin/bank/export, which does
 * not exist in the backend; it was removed in E-UX-02 (see programme doc).
 */
import { useState } from "react"
import { Layout } from "@/components/Layout"
import { Input, Alert, Button, PageHeader, SectionCard } from "@/components/ui"

import { useAuth } from "@/context/AuthContext"
import api, { errorMessage } from "@/lib/api"

export default function BankExport() {
  const { user } = useAuth()
  const canWrite = ["SuperAdmin", "HR"].includes(user?.role ?? "")
  const [payFormat, setPayFormat] = useState<"nacha" | "neft">("nacha")
  const [runIdForExport, setRunIdForExport] = useState("")
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState("")
  const [actionError, setActionError] = useState("")

  const exportPayrollFile = async () => {
    if (!runIdForExport.trim() || !/^\d+$/.test(runIdForExport.trim())) {
      setActionError("Enter a numeric pay run id for payroll file export.")
      return
    }
    setSaving(true); setNotice(""); setActionError("")
    try {
      const res = await api.post(`/payroll/runs/${runIdForExport.trim()}/payment-file?format=${payFormat}`, null, { responseType: "blob" })
      const blob = new Blob([res.data], { type: "text/plain" })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = payFormat === "neft" ? `payroll_run_${runIdForExport.trim()}_neft.txt` : `payroll_run_${runIdForExport.trim()}_payment.txt`
      document.body.appendChild(a); a.click(); a.remove(); window.URL.revokeObjectURL(url)
      setNotice(`Payroll payment file (${payFormat.toUpperCase()}) downloaded for run #${runIdForExport.trim()}.`)
    } catch (e) {
      setActionError(errorMessage(e, "The payment file could not be generated."))
    } finally { setSaving(false) }
  }

  return (
    <Layout>
      <PageHeader compact title="Bank Export Integration" description="PY-07 · bank export integration · depends PY-04 (shipped R3) · real POST /payroll/runs/:id/payment-file endpoint (SuperAdmin / HR)." />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {actionError && <Alert tone="error">{actionError}</Alert>}
        <SectionCard compact title="Payroll payment file" description="POST /payroll/runs/{id}/payment-file?format=nacha|neft — IN auto-selects neft, else nacha. NEFT header is NEFT with beneficiary_name|account_number|ifsc_code|net|currency|reference|pf_uan. NACHA keeps pipe format.">
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label htmlFor="bx-run">Pay run id</label>
              <Input id="bx-run" value={runIdForExport} onChange={e => setRunIdForExport(e.target.value)} placeholder="e.g. 123" disabled={!canWrite || saving} />
            </div>
            <div>
              <label htmlFor="bx-format">Format</label>
              <select id="bx-format" value={payFormat} onChange={e => setPayFormat(e.target.value as "nacha" | "neft")} className="w-full rounded border px-3 py-2" disabled={!canWrite || saving}>
                <option value="nacha">NACHA (US)</option>
                <option value="neft">NEFT/RTGS (IN)</option>
              </select>
            </div>
            <div className="flex items-end"><Button onClick={exportPayrollFile} disabled={!canWrite || saving}>{saving ? "Generating…" : "Download payroll file"}</Button></div>
          </div>
          {!canWrite && <p className="text-xs text-fg-muted mt-2">Payment-file export requires SuperAdmin or HR; your role is {user?.role || "unknown"}.</p>}
          <p className="text-xs text-text-secondary mt-2">Default is nacha for backwards compat; IN auto-selects neft when format absent. Raw PAN/IFSC/account only in server export, never in DOM; list shows masked.</p>
        </SectionCard>
        <div className="text-xs text-fg-muted">PY-07 · R3 · depends PY-04 · server-generated payment files only.</div>
      </div>
    </Layout>
  )
}