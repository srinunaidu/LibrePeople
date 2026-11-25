/**
 * The environment the journeys run against, and the guard that keeps them off
 * production.
 *
 * Why this is a module and not a line in the configuration
 * --------------------------------------------------------
 * A journey that talks to production is an incident waiting to happen: the
 * import journey writes a department, the payroll journey writes payslips,
 * and the accounts they use are real ones. The guard is therefore **asserted**
 * on every run rather than assumed by whoever reads the configuration:
 *
 *   - `assertNotProduction` is called by the global setup, so a run aimed at a
 *     production host stops before the first journey starts; and
 *   - the same function is called inside the journeys that talk to the API,
 *     so the property holds for the traffic they actually produce.
 *
 * The list of production hosts is not a guess. The deployment is a Render
 * service: `karmathy-backend.onrender.com` is the API and
 * `karmathy-frontend.onrender.com` is the static site (`docs/DEPLOYMENT.md`).
 * Staging is local — `127.0.0.1`, against a scratch Oracle schema — so every
 * `*.onrender.com` host is production. A hosted staging service, which is a
 * paid decision nobody has approved (ESC-004), would have to be listed here
 * as an explicit exception before the guard would let it through.
 */

/** The hosts that are production. */
export const PRODUCTION_HOSTS: readonly string[] = [
  "karmathy-backend.onrender.com",
  "karmathy-frontend.onrender.com",
]

/**
 * The API the journeys talk to when nothing says otherwise.
 *
 * Both environments use it: the local suite starts its own backend on 8010
 * and `scripts/staging/run.sh` starts one on the same port. The two
 * configurations set `KARMA_API_URL` explicitly; this is the fallback, and it
 * is the same value in both.
 */
export const DEFAULT_API_BASE_URL = "http://127.0.0.1:8010/api/v1"

/** The API base URL this run is pointed at. */
export function apiBaseUrl(): string {
  const raw = process.env.KARMA_API_URL || DEFAULT_API_BASE_URL
  return raw.replace(/\/+$/, "")
}

/** The host of a URL, lower-cased. Empty when the URL cannot be parsed. */
export function hostOf(url: string): string {
  try {
    return new URL(url).host.toLowerCase()
  } catch {
    return ""
  }
}

/** Whether a host belongs to production. */
export function isProductionHost(host: string): boolean {
  const value = host.toLowerCase()
  if (!value) return false
  if (PRODUCTION_HOSTS.includes(value)) return true
  // Every Render service in this project is production. Staging is local.
  return value === "onrender.com" || value.endsWith(".onrender.com")
}

/**
 * Refuse a target that is production.
 *
 * Throws with a message that says what was refused and why. A URL that
 * cannot be parsed is refused too: a guard that gives up when it cannot
 * understand the input is not a guard.
 */
export function assertNotProduction(target: string, what = "the target"): void {
  const host = hostOf(target)
  if (!host) {
    throw new Error(
      `refusing to run: ${what} "${target}" is not an absolute URL, so the ` +
        `guard cannot establish that it is not production.`
    )
  }
  if (isProductionHost(host)) {
    throw new Error(
      `refusing to run: ${what} "${target}" is a production host (${host}). ` +
        `The journeys write to the database they are pointed at, and the ` +
        `accounts they use are real ones. This suite may only run against a ` +
        `local file or the staging schema.`
    )
  }
}
