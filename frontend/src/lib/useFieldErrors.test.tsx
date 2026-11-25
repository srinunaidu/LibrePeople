import { describe, expect, test } from "vitest"
import { render, screen } from "@testing-library/react"
import "@testing-library/jest-dom/vitest"
import { fieldErrors } from "./api"
import { useFieldErrors } from "./useFieldErrors"
import { Input } from "@/components/ui/inputs"

function FieldWithError({ err, field }: { err: unknown; field: string }) {
  const fe = useFieldErrors(err)
  const msg = fe.get(field)
  return (
    <div>
      <Input id="test-field" error={!!msg} />
      {msg && <p role="alert">{msg}</p>}
    </div>
  )
}

describe("field 422 inline", () => {
  test("fieldErrors parses 422 detail array (loc slice 1)", () => {
    const err = {
      response: {
        status: 422,
        data: {
          detail: [
            { loc: ["body", "jurisdiction"], msg: "Field required", type: "missing" },
            { loc: ["body", "currency"], msg: "Invalid currency", type: "value_error" },
          ],
        },
      },
    }
    const map = fieldErrors(err)
    expect(map.get("jurisdiction")).toBe("Field required")
    expect(map.get("currency")).toBe("Invalid currency")
  })

  test("fieldErrors handles details Record", () => {
    const err = {
      response: { status: 422, data: { error: { details: { jurisdiction: "bad" } } } },
      apiError: { code: "validation_error", category: "client", message: "bad", retryable: false, details: { jurisdiction: "bad" } },
    }
    const map = fieldErrors(err)
    expect(map.get("jurisdiction")).toBe("bad")
  })

  test("Input error prop adds aria-invalid and red border, inline p role=alert", () => {
    const err = {
      response: { status: 422, data: { detail: [{ loc: ["body", "test-field"], msg: "Required" }] } },
    }
    // Simulate hook's key is "test-field" -> map key "test-field"
    const map = fieldErrors(err)
    expect(map.get("test-field")).toBe("Required")
    render(<FieldWithError err={err} field="test-field" />)
    const input = screen.getByRole("textbox")
    expect(input).toHaveAttribute("aria-invalid", "true")
    expect(input).toHaveAttribute("aria-describedby", "test-field-error")
    expect(screen.getByRole("alert")).toHaveTextContent("Required")
  })

  test("fallback global alert only when no field matches", () => {
    const err = {
      response: { status: 422, data: { detail: [{ loc: ["body"], msg: "Global error" }] } },
    }
    const map = fieldErrors(err)
    expect(map.get("_global")).toBe("Global error")
    const fe = (() => {
      const m = fieldErrors(err)
      return { hasFieldErrors: m.size > 0 && !(m.size === 1 && m.has("_global")), globalError: m.get("_global") }
    })()
    expect(fe.hasFieldErrors).toBe(false)
    expect(fe.globalError).toBe("Global error")
  })
})
