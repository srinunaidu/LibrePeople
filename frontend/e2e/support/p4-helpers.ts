import { createHmac } from "node:crypto"
import { expect, type APIRequestContext, type Page } from "@playwright/test"

/**
 * Shared setup for the P4 journey specs. Additive only: nothing in the
 * existing harness or configuration is changed by this module.
 */

import { apiBaseUrl, assertNotProduction } from "./environment"

export const ADMIN_USERNAME = "admin"
export const ADMIN_PASSWORD = "E2e!Bootstrap#2026"

export async function signIn(page: Page) {
  await page.goto("/login")
  await page.locator("#login-username").fill(ADMIN_USERNAME)
  await page.locator("#login-password").fill(ADMIN_PASSWORD)
  await page.getByRole("button", { name: "Sign in" }).click()
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 20_000 })
}

export function runToken(): string {
  return Math.random().toString(36).slice(2, 8).toUpperCase()
}

export async function apiLogin(
  request: APIRequestContext,
  username: string,
  password: string
): Promise<string> {
  const api = apiBaseUrl()
  assertNotProduction(api, "the API base URL")
  const res = await request.post(`${api}/auth/login`, {
    data: { username, password },
  })
  expect(res.status(), "API login answers 200").toBe(200)
  const body = await res.json()
  expect(body.access_token, "login returns a token").toBeTruthy()
  return body.access_token as string
}

export const auth = (token: string) => ({ Authorization: `Bearer ${token}` })

function base32Decode(input: string): Buffer {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
  const clean = input.replace(/=+$/, "").toUpperCase()
  let bits = 0
  let value = 0
  const out: number[] = []
  for (const char of clean) {
    const index = alphabet.indexOf(char)
    if (index < 0) throw new Error(`bad base32 character ${char}`)
    value = (value << 5) | index
    bits += 5
    if (bits >= 8) {
      out.push((value >>> (bits - 8)) & 0xff)
      bits -= 8
    }
  }
  return Buffer.from(out)
}

/** RFC 6238 TOTP (SHA-1, 30 s step) for one counter step. */
function totpAt(secret: string, step: number): string {
  const key = base32Decode(secret)
  const counter = Buffer.alloc(8)
  counter.writeBigUInt64BE(BigInt(step))
  const digest = createHmac("sha1", key).update(counter).digest()
  const offset = digest[digest.length - 1] & 0x0f
  const code =
    ((digest[offset] & 0x7f) << 24) |
    (digest[offset + 1] << 16) |
    (digest[offset + 2] << 8) |
    digest[offset + 3]
  return String(code % 1_000_000).padStart(6, "0")
}

/**
 * Enroll the shared admin in MFA so its token passes the privileged-role
 * gate (`get_current_active_user` refuses unenrolled SuperAdmin/HR with
 * 403). The server accepts the neighbouring 30 s steps, so each candidate
 * is tried in turn. Idempotent: a second run finds MFA already enabled and
 * carries on.
 */
export async function ensureAdminMfa(
  request: APIRequestContext,
  adminToken: string
): Promise<void> {
  const api = apiBaseUrl()
  const status = await request.get(`${api}/auth/mfa/status`, {
    headers: auth(adminToken),
  })
  expect(status.status(), "MFA status answers 200").toBe(200)
  const statusBody = await status.json()
  if (statusBody.mfa_enabled) return

  const enroll = await request.post(`${api}/auth/mfa/enroll`, {
    headers: auth(adminToken),
  })
  if (enroll.status() === 409) return // another worker enrolled first
  expect(enroll.status(), "MFA enroll answers 200").toBe(200)
  const enrollBody = await enroll.json()
  const uri = enrollBody.provisioning_uri as string
  const secret = new URL(uri).searchParams.get("secret")
  expect(secret, "the provisioning URI carries the secret").toBeTruthy()

  const step = Math.floor(Date.now() / 30_000)
  let confirmed = false
  for (const candidate of [step - 1, step, step + 1]) {
    const confirm = await request.post(`${api}/auth/mfa/confirm`, {
      headers: auth(adminToken),
      data: { totp_code: totpAt(secret!, candidate) },
    })
    if (confirm.status() === 200) {
      confirmed = true
      break
    }
  }
  expect(confirmed, "MFA confirmation accepts a current code").toBe(true)
}

export async function adminSession(
  request: APIRequestContext
): Promise<{ token: string; headers: Record<string, string> }> {
  const token = await apiLogin(request, ADMIN_USERNAME, ADMIN_PASSWORD)
  await ensureAdminMfa(request, token)
  return { token, headers: auth(token) }
}

export async function createAssociate(
  request: APIRequestContext,
  adminHeaders: Record<string, string>,
  prefix: string,
  tag: string
): Promise<{ id: number; username: string; token: string }> {
  const api = apiBaseUrl()
  const username = `${prefix}${tag}`.toLowerCase()
  const password = `T3st!P4-${tag}2026x`
  const created = await request.post(`${api}/auth/users`, {
    headers: adminHeaders,
    data: {
      user_in: {
        username,
        email: `${username}@example.com`,
        password,
        role: "Associate",
      },
    },
  })
  expect(created.status(), "associate creation answers 201").toBe(201)
  const createdBody = await created.json()
  const token = await apiLogin(request, username, password)
  return { id: createdBody.id as number, username, token }
}

export async function createEmployee(
  request: APIRequestContext,
  adminHeaders: Record<string, string>,
  prefix: string,
  tag: string
): Promise<{ id: number; number: string }> {
  const api = apiBaseUrl()
  const [deps, jobs] = await Promise.all([
    request.get(`${api}/departments/`, { headers: adminHeaders }),
    request.get(`${api}/jobs/`, { headers: adminHeaders }),
  ])
  expect(deps.status(), "departments list answers 200").toBe(200)
  expect(jobs.status(), "jobs list answers 200").toBe(200)
  const depList = (await deps.json()) as Array<{ id: number }>
  const jobList = (await jobs.json()) as Array<{ id: number }>
  expect(depList.length, "seed departments exist").toBeGreaterThan(0)
  expect(jobList.length, "seed jobs exist").toBeGreaterThan(0)

  const number = `${prefix}-${tag}`
  const res = await request.post(`${api}/employees/`, {
    headers: adminHeaders,
    data: {
      employee_id: number,
      first_name: "P4",
      last_name: `Fixture ${tag}`,
      email: `${prefix}-${tag.toLowerCase()}@example.com`,
      hire_date: "2026-01-05",
      job_id: jobList[0].id,
      department_id: depList[0].id,
    },
  })
  expect(res.status(), "employee creation answers 201").toBe(201)
  const body = await res.json()
  return { id: body.id as number, number }
}
