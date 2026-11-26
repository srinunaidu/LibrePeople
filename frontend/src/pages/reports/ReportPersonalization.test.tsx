import { describe, expect, test, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import "@testing-library/jest-dom/vitest"
import {
  canShareView,
  canUsePersonalization,
  EMPTY_SCHEDULES_CTA,
  EMPTY_SCHEDULES_TITLE,
  EMPTY_VIEWS_CTA,
  EMPTY_VIEWS_TITLE,
  parseRecipientIds,
  REPORT_KEY_LABELS,
  SavedViewsPanel,
  SchedulesPanel,
  validateScheduleInput,
  type ReportSchedule,
  type SavedView,
} from "@/pages/reports/ReportPersonalization"

// Reporting-personalization: the UI rules mirror the backend contract in
// backend/app/api/v1/endpoints/report_personalization.py (REPORTS_ROLES for
// the routes, HR/SuperAdmin to publish) and the empty states AC4 names.

describe("role gates (REPORTS_ROLES for routes, HR/SuperAdmin to share)", () => {
  test("only REPORTS_ROLES may use personalization", () => {
    expect(canUsePersonalization("SuperAdmin")).toBe(true)
    expect(canUsePersonalization("HR")).toBe(true)
    expect(canUsePersonalization("PayrollViewer")).toBe(true)
    expect(canUsePersonalization("Manager")).toBe(false)
    expect(canUsePersonalization("Associate")).toBe(false)
    expect(canUsePersonalization(undefined)).toBe(false)
    expect(canUsePersonalization(null)).toBe(false)
  })

  test("only HR and SuperAdmin may publish a shared view", () => {
    expect(canShareView("SuperAdmin")).toBe(true)
    expect(canShareView("HR")).toBe(true)
    // A Manager or Associate publish attempt is refused 403 — and a
    // PayrollViewer self-publish is refused too.
    expect(canShareView("PayrollViewer")).toBe(false)
    expect(canShareView("Manager")).toBe(false)
    expect(canShareView("Associate")).toBe(false)
  })
})

describe("schedule validation (mirrors the server 422s)", () => {
  const base = {
    report_key: "joiners",
    frequency: "weekly",
    timezone: "Asia/Kolkata",
    recipient_user_ids: "12, 34",
    output_format: "csv",
  }

  test("a well-formed draft passes", () => {
    expect(validateScheduleInput(base)).toBeNull()
  })

  test("unknown report key refused", () => {
    expect(validateScheduleInput({ ...base, report_key: "turnover-magic" })).toMatch(/joiners/)
  })

  test("bad frequency refused", () => {
    expect(validateScheduleInput({ ...base, frequency: "hourly" })).toMatch(/daily/)
  })

  test("unknown timezone refused", () => {
    expect(validateScheduleInput({ ...base, timezone: "Mars/Olympus" })).toMatch(/IANA/)
  })

  test("non-numeric recipients refused", () => {
    expect(validateScheduleInput({ ...base, recipient_user_ids: "12, abc" })).toMatch(/user ids/)
  })
})

describe("recipient parsing", () => {
  test("comma-separated ids become integers", () => {
    expect(parseRecipientIds("12, 34")).toEqual([12, 34])
    expect(parseRecipientIds("")).toEqual([])
    expect(parseRecipientIds(" 7 ")).toEqual([7])
  })
})

function view(over: Partial<SavedView> = {}): SavedView {
  return {
    id: 1,
    owner_id: 9,
    name: "Q1 joiners",
    report_key: "joiners",
    filters: { from: "2026-01-01" },
    visibility: "personal",
    ...over,
  }
}

describe("saved views empty state (AC4)", () => {
  test("a new user sees 'No saved views yet' with a create CTA", () => {
    const onCreate = vi.fn()
    render(
      <SavedViewsPanel views={[]} canShare onCreate={onCreate} onDelete={() => {}} onToggleShare={() => {}} />,
    )
    expect(screen.getByText(EMPTY_VIEWS_TITLE)).toBeInTheDocument()
    const cta = screen.getByRole("button", { name: EMPTY_VIEWS_CTA })
    expect(cta).toBeInTheDocument()
    fireEvent.click(cta)
    expect(onCreate).toHaveBeenCalledTimes(1)
  })

  test("views list replaces the empty state", () => {
    render(
      <SavedViewsPanel views={[view(), view({ id: 2, name: "Shared leavers", report_key: "leavers", visibility: "shared" })]}
        canShare onCreate={() => {}} onDelete={() => {}} onToggleShare={() => {}} />,
    )
    expect(screen.queryByText(EMPTY_VIEWS_TITLE)).not.toBeInTheDocument()
    expect(screen.getByText("Q1 joiners")).toBeInTheDocument()
    expect(screen.queryByText(REPORT_KEY_LABELS["payroll-summary"])).not.toBeInTheDocument()
    expect(screen.getByText("Shared with role")).toBeInTheDocument()
  })

  test("share toggle hidden without the publish role", () => {
    render(
      <SavedViewsPanel views={[view()]} canShare={false} onCreate={() => {}} onDelete={() => {}} onToggleShare={() => {}} />,
    )
    expect(screen.queryByRole("button", { name: /share/i })).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: /delete/i })).toBeInTheDocument()
  })

  test("delete fires with the view id", () => {
    const onDelete = vi.fn()
    render(
      <SavedViewsPanel views={[view({ id: 42 })]} canShare onCreate={() => {}} onDelete={onDelete} onToggleShare={() => {}} />,
    )
    fireEvent.click(screen.getByRole("button", { name: /delete/i }))
    expect(onDelete).toHaveBeenCalledWith(42)
  })
})

function schedule(over: Partial<ReportSchedule> = {}): ReportSchedule {
  return {
    id: 7,
    owner_id: 9,
    report_key: "leavers",
    filters: {},
    frequency: "weekly",
    timezone: "Asia/Kolkata",
    recipient_user_ids: [12],
    output_format: "csv",
    next_due_at: "2026-12-01T00:00:00+00:00",
    active: true,
    ...over,
  }
}

describe("schedules empty state (AC4)", () => {
  test("no schedules yet shows the empty state with a create CTA", () => {
    const onCreate = vi.fn()
    render(
      <SchedulesPanel schedules={[]} runs={[]} onCreate={onCreate} onRunNow={() => {}} onToggleActive={() => {}} onDelete={() => {}} onDownload={() => {}} busy={false} />,
    )
    expect(screen.getByText(EMPTY_SCHEDULES_TITLE)).toBeInTheDocument()
    const cta = screen.getByRole("button", { name: EMPTY_SCHEDULES_CTA })
    fireEvent.click(cta)
    expect(onCreate).toHaveBeenCalledTimes(1)
  })

  test("schedules list replaces the empty state, with run-now and pause", () => {
    const onRunNow = vi.fn()
    render(
      <SchedulesPanel schedules={[schedule()]} runs={[]} onCreate={() => {}} onRunNow={onRunNow} onToggleActive={() => {}} onDelete={() => {}} onDownload={() => {}} busy={false} />,
    )
    expect(screen.queryByText(EMPTY_SCHEDULES_TITLE)).not.toBeInTheDocument()
    expect(screen.getByText("Leavers")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /run now/i }))
    expect(onRunNow).toHaveBeenCalledWith(7)
    expect(screen.getByRole("button", { name: /pause/i })).toBeInTheDocument()
  })

  test("recent runs offer a download when a file exists", () => {
    const onDownload = vi.fn()
    const run = { id: 3, schedule_id: 7, status: "delivered", recipient_count: 2, payload_format: "csv", has_payload: true as boolean, error: null as string | null }
    render(
      <SchedulesPanel schedules={[schedule()]} runs={[run]} onCreate={() => {}} onRunNow={() => {}} onToggleActive={() => {}} onDelete={() => {}} onDownload={onDownload} busy={false} />,
    )
    const dl = screen.getByRole("button", { name: /download csv/i })
    fireEvent.click(dl)
    expect(onDownload).toHaveBeenCalledWith(run)
  })

  test("a run without a file offers no download", () => {
    const run = { id: 4, schedule_id: 7, status: "failed", recipient_count: 2, payload_format: null as string | null, has_payload: false as boolean, error: "boom" as string | null }
    render(
      <SchedulesPanel schedules={[schedule()]} runs={[run]} onCreate={() => {}} onRunNow={() => {}} onToggleActive={() => {}} onDelete={() => {}} onDownload={() => {}} busy={false} />,
    )
    expect(screen.getByText("No file yet")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /download/i })).not.toBeInTheDocument()
  })
})
