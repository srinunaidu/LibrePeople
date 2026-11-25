import { errorMessage } from "@/lib/api"

export interface BulkAdminFailure {
  /** Numeric row id (feature flags, violations) or string id (admin jobs). */
  id: number | string
  message: string
}

/**
 * Slice-2 admin bulk summary — same honest-feedback contract as slice-1
 * `summarizeBulk` (lib/bulk.ts, frozen), widened to string ids because
 * admin surfaces key rows by module key ("payroll") and job id (uuid).
 *
 * Summarises Promise.allSettled results so the UI renders a success count
 * plus the raw backend detail for every failed item. Never swallows a
 * rejection and never claims success for an item that failed.
 */
export function summarizeBulkAdmin(
  ids: (number | string)[],
  results: PromiseSettledResult<unknown>[],
  verbPast: string,
  noun: string,
): { okCount: number; failures: BulkAdminFailure[]; notice: string; error: string } {
  const failures: BulkAdminFailure[] = []
  let okCount = 0
  results.forEach((r, i) => {
    if (r.status === "fulfilled") {
      okCount += 1
    } else {
      failures.push({
        id: ids[i],
        message: errorMessage(r.reason, `Request ${ids[i]} failed`),
      })
    }
  })
  const total = ids.length
  const notice =
    okCount > 0
      ? `${verbPast} ${okCount} of ${total} ${noun}${total === 1 ? "" : "(s)"}${failures.length > 0 ? ` — ${failures.length} failed` : ""}`
      : ""
  const error =
    failures.length > 0
      ? `${verbPast} failed for ${failures.length} of ${total}: ${failures.map((f) => `${f.id}: ${f.message}`).join("; ")}. Adjust and retry the failed items.`
      : ""
  return { okCount, failures, notice, error }
}
