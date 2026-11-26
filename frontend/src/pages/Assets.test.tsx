import { describe, expect, test } from "vitest"
import { errorMessage } from "@/lib/api"
import {
  ackable,
  actionsForStatus,
  buildAssetEditPayload,
  buildAssetListParams,
  canManageAssets,
  canViewClearance,
  clearanceStatusText,
  conditionToStatus,
  isRetireReady,
  openAssignmentFor,
  ASSET_STATUS_LABELS,
  type AssignmentRow,
} from "@/pages/Assets"

// Assets module — the UI rules mirror the backend contract in
// backend/app/services/assets_service.py (FSM, self-only ack, role gate).

function spell(over: Partial<AssignmentRow> = {}): AssignmentRow {
  return {
    id: 1,
    asset_id: 10,
    employee_id: 100,
    status: "open",
    assigned_at: "2026-11-01T09:00:00Z",
    acknowledged_at: null,
    closed_at: null,
    close_reason: null,
    return_condition: null,
    ...over,
  }
}

describe("Assets — role gate (HR/Admin manage, Associate own-only)", () => {
  test("only SuperAdmin and HR may manage the register", () => {
    expect(canManageAssets("SuperAdmin")).toBe(true)
    expect(canManageAssets("HR")).toBe(true)
    expect(canManageAssets("Manager")).toBe(false)
    expect(canManageAssets("Associate")).toBe(false)
    expect(canManageAssets("PayrollViewer")).toBe(false)
    expect(canManageAssets(undefined)).toBe(false)
    expect(canManageAssets(null)).toBe(false)
  })
})

describe("Assets — FSM actions offered per status (409 otherwise)", () => {
  test("in_stock offers assign, maintenance start and retire", () => {
    expect(actionsForStatus("in_stock")).toEqual(["assign", "maintenance_start", "retire"])
  })

  test("assigned offers transfer and return — maintenance is blocked while assigned", () => {
    const actions = actionsForStatus("assigned")
    expect(actions).toEqual(["transfer", "return"])
    expect(actions).not.toContain("maintenance_start")
  })

  test("maintenance offers complete and retire", () => {
    expect(actionsForStatus("maintenance")).toEqual(["maintenance_complete", "retire"])
  })

  test("retired and lost are final — no actions", () => {
    expect(actionsForStatus("retired")).toEqual([])
    expect(actionsForStatus("lost")).toEqual([])
  })

  test("every FSM status has a human label", () => {
    for (const s of ["in_stock", "assigned", "maintenance", "retired", "lost"]) {
      expect(ASSET_STATUS_LABELS[s]).toBeTruthy()
    }
  })
})

describe("Assets — return condition decides the next status", () => {
  test("good -> in_stock, damaged -> maintenance, lost -> lost (backend CONDITION_TO_STATUS)", () => {
    expect(conditionToStatus("good")).toBe("in_stock")
    expect(conditionToStatus("damaged")).toBe("maintenance")
    expect(conditionToStatus("lost")).toBe("lost")
  })
})

describe("MyAssets — acknowledgement is self-only and single-shot", () => {
  test("an open, unacknowledged spell shows the Acknowledge button", () => {
    expect(ackable(spell())).toBe(true)
  })

  test("an acknowledged spell does not offer ack again (server would 409)", () => {
    expect(ackable(spell({ acknowledged_at: "2026-11-02T10:00:00Z" }))).toBe(false)
  })

  test("a closed spell can never be acknowledged (server would 409)", () => {
    expect(ackable(spell({ status: "closed", close_reason: "returned", return_condition: "good" }))).toBe(false)
    expect(ackable(spell({ status: "closed", close_reason: "transferred" }))).toBe(false)
  })

  test("a transfer opens a fresh unacknowledged spell — re-ack is required", () => {
    const reopened = spell({ id: 2, employee_id: 200, acknowledged_at: null })
    expect(ackable(reopened)).toBe(true)
  })
})

describe("Assets — single open assignment per asset", () => {
  const rows = [
    spell({ id: 1, asset_id: 10, status: "closed", close_reason: "transferred" }),
    spell({ id: 2, asset_id: 10 }),
    spell({ id: 3, asset_id: 20 }),
  ]

  test("holder lookup finds the open spell, not the closed history", () => {
    expect(openAssignmentFor(rows, 10)?.id).toBe(2)
  })

  test("an asset with no open spell has no holder", () => {
    expect(openAssignmentFor(rows, 99)).toBeUndefined()
  })
})

describe("Assets — register filters wire to GET /assets params (AC1)", () => {
  test("empty filters are omitted entirely", () => {
    expect(buildAssetListParams("", "")).toEqual({})
  })

  test("selecting assigned sends status=assigned", () => {
    expect(buildAssetListParams("assigned", "")).toEqual({ status: "assigned" })
  })

  test("status and category combine", () => {
    expect(buildAssetListParams("in_stock", "IT")).toEqual({ status: "in_stock", category: "IT" })
  })

  test("whitespace-only filters are omitted", () => {
    expect(buildAssetListParams("  ", " ")).toEqual({})
  })
})

describe("Assets — metadata edit payload never carries status (AC2)", () => {
  test("tag/name/category/description/serial pass through, trimmed", () => {
    expect(
      buildAssetEditPayload({
        tag: " AST-0001 ",
        name: " MacBook ",
        category: " IT ",
        description: " dev laptop ",
        serial_number: " SN1 ",
      })
    ).toEqual({
      tag: "AST-0001",
      name: "MacBook",
      category: "IT",
      description: "dev laptop",
      serial_number: "SN1",
    })
  })

  test("a status smuggled onto the input is dropped", () => {
    const payload = buildAssetEditPayload({
      tag: "AST-0001",
      name: "MacBook",
      category: "IT",
      status: "retired",
    })
    expect(payload).not.toHaveProperty("status")
    expect(payload).toEqual({ tag: "AST-0001", name: "MacBook", category: "IT" })
  })

  test("empty description/serial are omitted, never nulled", () => {
    const payload = buildAssetEditPayload({
      tag: "AST-0001",
      name: "MacBook",
      category: "IT",
      description: "  ",
      serial_number: "",
    })
    expect(payload).not.toHaveProperty("description")
    expect(payload).not.toHaveProperty("serial_number")
  })
})

describe("Assets — clearance visibility and rendering (AC4)", () => {
  test("HR, Manager and SuperAdmin may view clearance; Associate may not", () => {
    expect(canViewClearance("SuperAdmin")).toBe(true)
    expect(canViewClearance("HR")).toBe(true)
    expect(canViewClearance("Manager")).toBe(true)
    expect(canViewClearance("Associate")).toBe(false)
    expect(canViewClearance(undefined)).toBe(false)
  })

  test("a clear projection renders as clear", () => {
    expect(
      clearanceStatusText({ employee_id: 7, clear: true, outstanding_count: 0, outstanding: [] })
    ).toBe("clear")
  })

  test("outstanding custody renders the count", () => {
    expect(
      clearanceStatusText({
        employee_id: 7,
        clear: false,
        outstanding_count: 2,
        outstanding: [
          { assignment_id: 1, asset_id: 10, tag: "AST-0001", name: "MacBook" },
          { assignment_id: 2, asset_id: 11, tag: "AST-0002", name: "Phone" },
        ],
      })
    ).toBe("2 outstanding")
  })
})

describe("Assets — retire requires reason plus explicit confirm (AC5)", () => {
  test("blank reason is never ready, even when confirmed", () => {
    expect(isRetireReady("", true)).toBe(false)
    expect(isRetireReady("   ", true)).toBe(false)
  })

  test("a reason without the confirm checkbox is not ready", () => {
    expect(isRetireReady("end of life", false)).toBe(false)
  })

  test("reason plus confirm is ready", () => {
    expect(isRetireReady("end of life", true)).toBe(true)
  })
})

describe("Assets — server refusals surface verbatim (shared error envelope)", () => {
  const err = (status: number, code: string, message: string) => ({
    response: { status, data: { error: { code, message } } },
  })

  test("409 invalid_state_transition shows the FSM reason", () => {
    const e = err(409, "invalid_state_transition", "Cannot move asset from 'assigned' to 'maintenance'. Allowed from: ['in_stock'].")
    expect(errorMessage(e, "fallback")).toContain("Cannot move asset from 'assigned' to 'maintenance'")
  })

  test("409 duplicate_natural_key shows the per-tenant tag rule", () => {
    const e = err(409, "duplicate_natural_key", "Asset already uses the tag 'AST-0001' in this tenant. Tags are unique per tenant.")
    expect(errorMessage(e, "fallback")).toContain("unique per tenant")
  })

  test("409 employee_not_active shows the custody rule", () => {
    const e = err(409, "employee_not_active", "Employee 7 is Terminated; assets may only be assigned to active employees.")
    expect(errorMessage(e, "fallback")).toContain("active employees")
  })

  test("409 tenant_mismatch shows the tenancy refusal", () => {
    const e = err(409, "tenant_mismatch", "The supplied tenant id does not match the resolved tenant.")
    expect(errorMessage(e, "fallback")).toContain("does not match the resolved tenant")
  })

  test("403 self-only ack refusal is surfaced, not swallowed", () => {
    const e = { response: { status: 403, data: { detail: "Only the assigned employee may acknowledge receipt of an asset." } } }
    expect(errorMessage(e, "fallback")).toContain("Only the assigned employee")
  })
})