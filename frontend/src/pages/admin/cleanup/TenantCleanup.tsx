/* Tenant Cleanup - SuperAdmin only
 * Removes departments and jobs at tenant level
 * AD-07 audit chain on every deletion
 */
import { useCallback, useEffect, useState } from "react"
import { Layout } from "@/components/Layout"
import {Alert, Button, LoadingRegion, PageHeader, SectionCard, RetryableAlert, TableSkeleton} from "@/components/ui"
import { useAuth } from "@/context/AuthContext"
import { useTenant } from "@/context/TenantContext"
import api, { errorMessage, getClientIdBySlug } from "@/lib/api"

export default function TenantCleanup() {
  const { user } = useAuth()
  const { tenant } = useTenant()
  const isSuperAdmin = user?.role === "SuperAdmin"
  const canDelete = isSuperAdmin
  const [clientId, setClientId] = useState<number | null>(null)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [department, setDepartment] = useState("")
  const [job, setJob] = useState("")
  const [loading, setLoading] = useState(true)
  const [notice, setNotice] = useState("")
  const [error, setError] = useState("")

  const load = useCallback(async () => {
    setLoading(true)
    setError("")
    setNotice("")
    try {
      const id = await getClientIdBySlug()
      setClientId(id)
      if (id === null) {
        setError("Could not resolve tenant — verify the tenant exists.")
        return
      }
      const { data } = await api.get(`/onboarding-portal/clients/${id}/settings`)
      const m: Record<string, string> = {}
      for (const s of data || []) {
        ;(m as any)[s.key] = s.value
      }
      setDepartment(m["dept_default"] || "")
    } catch (e: unknown) {
      setError(errorMessage(e))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [])

  const deleteDepartment = async () => {
    setNotice("")
    setError("")
    try {
      const id = await getClientIdBySlug()
      setClientId(id)
      if (id === null) {
        setError("Could not resolve tenant — verify the tenant exists.")
        return
      }
      await api.delete(`/onboarding-portal/clients/${id}/departments/${department}`)
      setNotice("Department deleted — audit row (AD-07) written.")
      setDepartment("")
      setShowDeleteModal(false)
      load()
    } catch (e: unknown) {
      setError(errorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  const deleteJob = async () => {
    setNotice("")
    setError("")
    try {
      const id = await getClientIdBySlug()
      setClientId(id)
      if (id === null) {
        setError("Could not resolve tenant — verify the tenant exists.")
        return
      }
      await api.delete(`/onboarding-portal/clients/${id}/jobs/${job}`)
      setNotice("Job deleted — audit row (AD-07) written.")
      setJob("")
      setShowDeleteModal(false)
      load()
    } catch (e: unknown) {
      setError(errorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <Layout>
        <LoadingRegion label="Tenant Cleanup"><TableSkeleton rows={4} cols={4} /></LoadingRegion>
      </Layout>
    )
  }

  return (
    <Layout>
      <PageHeader compact
        title="Tenant Cleanup"
        description="SuperAdmin only · remove departments/jobs at tenant level · AD-07 audit on every deletion."
      />
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {notice && <Alert tone="success">{notice}</Alert>}
        {error && <Alert tone="error">{error}</Alert>}

        <SectionCard compact
          title="Delete Department"
          description="Permanently remove a department. Department must have no dependent employees or jobs."
        >
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label>Department</label>
              <select
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                <option value="">Select department</option>
                <option value="Engineering">Engineering</option>
                <option value="Sales">Sales</option>
                <option value="Finance">Finance</option>
                <option value="HR">HR</option>
                <option value="Operations">Operations</option>
                <option value="Marketing">Marketing</option>
                <option value="Support">Support</option>
                <option value="Other">Other</option>
              </select>
            </div>
            <div />
          </div>
          <Button
            onClick={() => setShowDeleteModal(true)}
            disabled={!canDelete || loading}
            className="mt-4"
          >
            {showDeleteModal ? "Cancel" : "Delete Department"}
          </Button>
        </SectionCard>

        <SectionCard compact
          title="Delete Job"
          description="Permanently remove a job. Job must have no dependent employees or applications."
        >
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label>Job</label>
              <select
                value={job}
                onChange={(e) => setJob(e.target.value)}
                className="w-full rounded border px-3 py-2"
              >
                <option value="">Select job</option>
                <option value="engineer">Engineer</option>
                <option value="manager">Manager</option>
                <option value="analyst">Analyst</option>
                <option value="coordinator">Coordinator</option>
                <option value="director">Director</option>
                <option value="intern">Intern</option>
              </select>
            </div>
            <div />
            <div />
          </div>
          <Button
            onClick={() => setShowDeleteModal(true)}
            disabled={!canDelete || loading}
            className="mt-4"
          >
            {showDeleteModal ? "Cancel" : "Delete Job"}
          </Button>
        </SectionCard>

        {showDeleteModal && (
          <>
            <div className="mt-4 text-xs text-fg-muted">
              <p>This action cannot be undone.</p>
              <p>
                Department will be removed only if no employees or jobs depend
                on it.
              </p>
              <p>Job will be removed only if no employees are assigned to it.</p>
            </div>
            <div className="mt-4 flex gap-3">
              <Button
                onClick={deleteDepartment}
                disabled={!canDelete || loading}
              >
                Delete Department
              </Button>
              <Button
                onClick={deleteJob}
                disabled={!canDelete || loading}
              >
                Delete Job
              </Button>
              <Button
                onClick={() => setShowDeleteModal(false)}
                className="ml-2"
                disabled={loading}
              >
                Cancel
              </Button>
            </div>
          </>
        )}

        <div className="text-xs text-fg-muted">
          SuperAdmin only · AD-07 audit chain on every deletion · no fabricated
          data removal.
        </div>
      </div>
    </Layout>
  )
}