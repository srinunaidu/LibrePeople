/**
 * Cloud E2E configuration: the DEPLOYED Render environment.
 *
 * Deliberately separate from the root `playwright.config.ts`, whose
 * global-setup guard refuses any `*.onrender.com` target (and whose
 * webServers start local backends). This config starts nothing and guards
 * nothing — the explicit opt-in below is the guard: a cloud run only starts
 * when the operator sets `CLOUD_E2E_ACK=1`, acknowledging that the run
 * writes namespaced synthetic rows to the deployed tenant.
 *
 * Run from `frontend/` with the `E2E_*` + `CLOUD_*` variables exported:
 *   CLOUD_E2E_ACK=1 npx playwright test --config=e2e/cloud/playwright.cloud.config.ts
 */
import { defineConfig, devices } from "@playwright/test"

const API =
  process.env.CLOUD_API_URL ??
  "https://librepeople-backend.onrender.com/api/v1"
const APP =
  process.env.CLOUD_APP_URL ?? "https://librepeople-frontend.onrender.com"

if (process.env.CLOUD_E2E_ACK !== "1") {
  throw new Error(
    "refusing cloud run without CLOUD_E2E_ACK=1: this config writes " +
      "namespaced synthetic rows to the deployed tenant, so the run must " +
      "be acknowledged explicitly."
  )
}

// The specs under testDir read KARMA_API_URL only if they ask for it; set it
// to the deployed API so nothing falls back to localhost.
process.env.KARMA_API_URL = API

export default defineConfig({
  testDir: ".",
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: APP,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "cloud-chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
})
