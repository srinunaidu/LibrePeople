import type { FullConfig } from "@playwright/test"

import { apiBaseUrl, assertNotProduction } from "./environment"

/**
 * The guard, run before the first journey.
 *
 * This is the check the pilot gate's criterion 7 asks for: a run must prove
 * that it is not pointed at production. The proof is that the run **stops**
 * when it is, and it stops here — before any journey has signed in, written
 * a row or rotated a password.
 *
 * It is a global setup rather than a journey on purpose. A journey would be
 * one of the twelve the gate counts, and the guard is not a user story: it
 * is the thing that makes the other twelve safe to run.
 */
export default async function globalSetup(config: FullConfig) {
  const api = apiBaseUrl()
  assertNotProduction(api, "the API base URL")

  // The screen under test is checked as well. A run against the deployed
  // frontend would be pointed at the deployed API whatever the API base URL
  // says, because the frontend build carries its own.
  const base = config.use?.baseURL
  if (typeof base === "string") {
    assertNotProduction(base, "the base URL")
  }
  for (const project of config.projects ?? []) {
    const projectBase = project.use?.baseURL
    if (typeof projectBase === "string") {
      assertNotProduction(projectBase, `the "${project.name}" base URL`)
    }
  }

  console.log(
    `[journeys] api ${api} — the guard has checked that it is not production`
  )
}
