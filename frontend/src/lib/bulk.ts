import { errorMessage } from "@/lib/api"

export interface BulkFailure {
  id: number
  message: string
}

/**
 * Summarise Promise.allSettled bulk results so the UI can render honest
 * feedback: a success count plus the raw backend detail for every failure.
 */
export function summarizeBulk(
  ids: number[],
  results: PromiseSettledResult<unknown>[],
  verbPast: string,
  noun: string,
): { okCount: number; failures: BulkFailure[]; notice: string; error: string } {
  const failures: BulkFailure[] = []
  let okCount = 0
  results.forEach((r, i) => {
    if (r.status === "fulfilled") {
      okCount += 1
    } else {
      failures.push({
        id: ids[i],
        message: errorMessage(r.reason, `Request #${ids[i]} failed`),
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
      ? `${verbPast} failed for ${failures.length} of ${total}: ${failures.map((f) => `#${f.id}: ${f.message}`).join("; ")}. Adjust and retry the failed items.`
      : ""
  return { okCount, failures, notice, error }
}
