/**
 * Playwright configuration for the Karmathy frontend journeys.
 *
 * The suite runs against a locally seeded backend (SQLite) and the built
 * frontend served by `vite preview`. Both are started by the web servers
 * declared below, so `npx playwright test` needs no manual setup.
 */
import { defineConfig, devices } from "@playwright/test"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

const HERE = dirname(fileURLToPath(import.meta.url))
const BACKEND = join(HERE, "..", "backend")

const FRONTEND_PORT = 4173
const BACKEND_PORT = 8010

// The interpreter that runs the backend. Locally it is the project virtualenv;
// in CI the dependencies are installed into the runner's Python, so the
// workflow sets `KARMA_PYTHON=python` and nothing else changes.
const PYTHON = process.env.KARMA_PYTHON ?? join(BACKEND, ".venv", "bin", "python")

// The API the journeys read the database through.
//
// The same value is used by the staging configuration, so one set of specs
// runs against both environments and the configuration is the only thing
// that differs between them. The environment may override it — the guard
// checks whatever value is used, so an override cannot make the run unsafe.
process.env.KARMA_API_URL =
  process.env.KARMA_API_URL ?? `http://127.0.0.1:${BACKEND_PORT}/api/v1`

export default defineConfig({
  testDir: "./e2e",
  // The guard: a run pointed at production stops here, before the first
  // journey signs in. See `e2e/support/environment.ts`.
  globalSetup: "./e2e/support/global-setup.ts",
  timeout: 60_000,
  expect: { timeout: 10_000 },
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
      // Every journey except the responsive one: that file sets its own
      // viewport for each of the four widths, so running it here as well
      // would measure the same thing twice at the wrong size.
      name: "desktop",
      use: { ...devices["Desktop Chrome"] },
      testIgnore: /responsive\.spec\.ts/,
    },
    {
      // The four widths the mandate names — 360, 768, 1024 and 1440 px — are
      // set by the spec itself. The layout is driven by CSS breakpoints, so
      // the width is what matters; touch behaviour is not claimed. This
      // project used to be called `mobile` and matched a file that did not
      // exist, so it ran nothing (D-021).
      name: "responsive",
      use: { ...devices["Desktop Chrome"] },
      testMatch: /responsive\.spec\.ts/,
    },
  ],
  webServer: [
    {
      // Always start a fresh backend. The journeys rotate passwords, so a
      // reused server would leave the next run signing in with a password
      // that no longer exists. The server rebuilds its database on start.
      command: `${PYTHON} ${join(BACKEND, "scripts", "e2e_server.py")}`,
      url: `http://127.0.0.1:${BACKEND_PORT}/health`,
      reuseExistingServer: true,
      timeout: 180_000,
      env: {
        DATABASE_URL: `sqlite:///${join(HERE, ".e2e", "e2e_backend.db")}`,
        SECRET_KEY: "e2e_secret_key_at_least_32_characters_long",
        ENVIRONMENT: "development",
        ALGORITHM: "HS256",
        BACKEND_CORS_ORIGINS: `http://127.0.0.1:${FRONTEND_PORT}`,
        STORAGE_BACKEND: "local",
        PUBLIC_DIAGNOSTIC_ENDPOINTS: "false",
        E2E_PORT: String(BACKEND_PORT),
        E2E_ADMIN_PASSWORD: "E2e!Bootstrap#2026",
      },
    },
    {
      command: `npm run build && npx vite preview --port ${FRONTEND_PORT} --host 127.0.0.1`,
      url: `http://127.0.0.1:${FRONTEND_PORT}`,
      reuseExistingServer: true,
      timeout: 300_000,
      env: {
        VITE_API_URL: `http://127.0.0.1:${BACKEND_PORT}/api/v1`,
      },
    },
  ],
})
