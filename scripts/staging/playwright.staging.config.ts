/**
 * The journey suite against the staging environment.
 *
 * The suite's own configuration starts a throwaway SQLite backend and a
 * preview build. This one reuses what `scripts/staging/run.sh` already has
 * running: the application against a real Oracle schema, and the built
 * frontend.
 *
 *   cd frontend && npx playwright test --config ../scripts/staging/playwright.staging.config.ts
 *
 * The result is a different claim from the local suite's: not "the journeys
 * pass against a file", but "the journeys pass against a database engine that
 * is the one production uses".
 */
import { join, resolve } from "node:path"

// This file lives outside the frontend package, so it is loaded as CommonJS:
// `import.meta` is not available and `@playwright/test` does not resolve from
// here. The suite is run from the frontend directory, so the module is taken
// from that directory's own node_modules.
const FRONTEND_ROOT = resolve(process.cwd())
const { defineConfig, devices } = require(join(FRONTEND_ROOT, "node_modules", "@playwright", "test"))
const FRONTEND_PORT = Number(process.env.FRONTEND_PORT ?? 4173)
// The staging harness uses 8011, so it does not collide with the local
// suite, which starts its own backend on 8010.
const BACKEND_PORT = Number(process.env.BACKEND_PORT ?? 8011)

// The API the journeys read the database through. The same value the local
// configuration sets, so one set of specs runs against both environments.
// The environment may override it — the guard checks whatever value is used,
// so an override cannot make the run unsafe.
process.env.KARMA_API_URL =
  process.env.KARMA_API_URL ?? `http://127.0.0.1:${BACKEND_PORT}/api/v1`

export default defineConfig({
  testDir: join(FRONTEND_ROOT, "e2e"),
  // The guard: a run pointed at production stops here, before the first
  // journey signs in. See `frontend/e2e/support/environment.ts`.
  globalSetup: join(FRONTEND_ROOT, "e2e", "support", "global-setup.ts"),
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: `http://127.0.0.1:${FRONTEND_PORT}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "desktop",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  // The servers are already running: `scripts/staging/run.sh` started them.
  // The staging environment is the thing under test, so it is never started
  // and torn down by the suite.
  webServer: undefined,
})

export const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`
