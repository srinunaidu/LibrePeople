import { describe, expect, test } from "vitest"
import { loginErrorMessage } from "./Login"

// The login screen must name the actual failure class: a blocked request is
// not a wrong password, and a 503 is not one either.

describe("loginErrorMessage", () => {
  test("no response (network/CORS/DNS/timeout) is a connectivity message", () => {
    expect(loginErrorMessage({ message: "Network Error" })).toBe(
      "We can't reach the server right now. Check your connection and try again."
    )
  })

  test("5xx is a service-unavailable message", () => {
    expect(loginErrorMessage({ response: { status: 503, data: {} } })).toBe(
      "The service is temporarily unavailable. Please try again in a moment."
    )
    expect(loginErrorMessage({ response: { status: 500, data: {} } })).toBe(
      "The service is temporarily unavailable. Please try again in a moment."
    )
  })

  test("dependency_unavailable is a service-unavailable message even without 5xx", () => {
    expect(
      loginErrorMessage({
        response: { status: 404, data: {} },
        apiError: { code: "dependency_unavailable" },
      })
    ).toBe("The service is temporarily unavailable. Please try again in a moment.")
  })

  test("429 uses the server detail when present, otherwise a wait message", () => {
    expect(
      loginErrorMessage({
        response: { status: 429, data: { detail: "Too many attempts from this address." } },
      })
    ).toBe("Too many attempts from this address.")
    expect(loginErrorMessage({ response: { status: 429, data: {} } })).toBe(
      "Too many sign-in attempts. Please wait and try again."
    )
  })

  test("401 keeps the server detail", () => {
    expect(
      loginErrorMessage({
        response: { status: 401, data: { detail: "Invalid username or password" } },
      })
    ).toBe("Invalid username or password")
  })

  test("400 and 403 keep the server detail", () => {
    expect(
      loginErrorMessage({ response: { status: 400, data: { detail: "Account is locked" } } })
    ).toBe("Account is locked")
    expect(
      loginErrorMessage({ response: { status: 403, data: { detail: "Sign-in is disabled" } } })
    ).toBe("Sign-in is disabled")
  })

  test("anything else falls back to the credentials message", () => {
    expect(loginErrorMessage({ response: { status: 422, data: {} } })).toBe(
      "We couldn't sign you in. Check your username and password and try again."
    )
    expect(loginErrorMessage({ response: { status: 418, data: {} } })).toBe(
      "We couldn't sign you in. Check your username and password and try again."
    )
  })
})
