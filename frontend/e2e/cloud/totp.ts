import { createHmac } from "node:crypto"
import { expect, type APIRequestContext } from "@playwright/test"

/**
 * Cloud E2E: RFC 6238 TOTP + the MFA completion step, node:crypto only.
 *
 * The deployed backend has no login-time MFA challenge: `POST /auth/login`
 * is password-only and always mints a pair. Enforcement is a gate —
 * `get_current_active_user` refuses unenrolled SuperAdmin/HR accounts with
 * 403 on every endpoint but `/auth/mfa/*` — so what an HR login needs after
 * the password step is *enrollment completion*, not a per-request code.
 * Once `mfa_enabled` is true the plain JWT works on privileged endpoints.
 *
 * `completeMfaIfRequired` therefore: checks `/auth/mfa/status`; returns
 * immediately when enabled; otherwise — and only when a provisioned
 * `E2E_<ROLE>_MFA_SECRET` is present — attempts a SINGLE
 * `POST /auth/mfa/confirm` with the current code and then asserts the final
 * JWT works on a privileged endpoint. It never enrolls (enrolling mints a
 * server-side secret nobody holds — a lockout after the run shreds memory),
 * never retries a rejected code, and never logs a secret. A missing secret
 * is not papered over: the caller proceeds and the privileged calls fail
 * loudly with the gate envelope, which is the evidence the report needs.
 */

function base32Decode(input: string): Buffer {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
  const clean = input.replace(/=+$/, "").toUpperCase()
  let bits = 0
  let value = 0
  const out: number[] = []
  for (const char of clean) {
    const index = alphabet.indexOf(char)
    if (index < 0) throw new Error("bad base32 character in MFA secret")
    value = (value << 5) | index
    bits += 5
    if (bits >= 8) {
      out.push((value >>> (bits - 8)) & 0xff)
      bits -= 8
    }
  }
  return Buffer.from(out)
}

/** RFC 6238 TOTP: SHA-1, 30 s step, 6 digits. `stepOffset` shifts whole steps. */
export function totpCode(secret: string, atMs = Date.now(), stepOffset = 0): string {
  const key = base32Decode(secret)
  const counter = Math.floor(atMs / 30_000) + stepOffset
  const message = Buffer.alloc(8)
  message.writeBigUInt64BE(BigInt(counter))
  const digest = createHmac("sha1", key).update(message).digest()
  const offset = digest[digest.length - 1] & 0x0f
  const code =
    ((digest[offset] & 0x7f) << 24) |
    (digest[offset + 1] << 16) |
    (digest[offset + 2] << 8) |
    digest[offset + 3]
  return String(code % 1_000_000).padStart(6, "0")
}

/** The provisioned TOTP secret for an HR role, or null when unset. */
export function mfaSecretFor(role: "HRADMIN" | "HREXEC"): string | null {
  return process.env[`E2E_${role}_MFA_SECRET`] ?? null
}

const auth = (token: string) => ({ Authorization: `Bearer ${token}` })

/**
 * Complete the MFA step for an HR login when (and only when) the account
 * still requires it. Asserts the resulting JWT works on a privileged
 * endpoint. Single confirm attempt; no retries, no enrollment, no logging.
 */
export async function completeMfaIfRequired(
  request: APIRequestContext,
  api: string,
  token: string,
  mfaSecret: string | null
): Promise<void> {
  const status = await request.get(`${api}/auth/mfa/status`, {
    headers: auth(token),
  })
  expect(status.status(), "MFA status answers 200").toBe(200)
  const body = (await status.json()) as { mfa_enabled?: boolean }
  if (body.mfa_enabled === true) return
  if (!mfaSecret) return

  const confirm = await request.post(`${api}/auth/mfa/confirm`, {
    headers: auth(token),
    data: { totp_code: totpCode(mfaSecret) },
  })
  expect(confirm.status(), "MFA confirm answers 200").toBe(200)

  const rechecked = await request.get(`${api}/auth/mfa/status`, {
    headers: auth(token),
  })
  expect(rechecked.status(), "MFA status answers 200").toBe(200)
  const recheckedBody = (await rechecked.json()) as { mfa_enabled?: boolean }
  expect(recheckedBody.mfa_enabled, "MFA is enabled after confirm").toBe(true)

  const probe = await request.get(`${api}/departments/`, {
    headers: auth(token),
  })
  expect(probe.status(), "JWT works on a privileged endpoint after MFA").toBe(
    200
  )
}
