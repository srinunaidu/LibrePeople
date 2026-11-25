import { ModulePage } from "@/components/marketing/ModulePage"

export default function LeavePage() {
  return (
    <ModulePage
      stageId="leave"
      kicker="Module — Leave · stage 4 of the thread"
      title="Leave — balances that can't quietly drift"
      intro="Requests, approvals and cancellations backed by an entry-by-entry balance ledger: every accrual, use, carry-over or adjustment is a line, so the balance shown is derived, not remembered."
      facts={[
        { label: "Balances", value: "Ledger-derived" },
        { label: "Approvals", value: "Role-configured chains" },
        { label: "Overlap", value: "Refused, with dates" },
      ]}
      shipTitle="Leave done properly, not politely"
      ships={[
        {
          title: "Requests with overlap checks",
          desc: "A request that collides with an existing one, an approval that exceeds the balance, or a cancelled request under approval is refused with the dates named.",
          refs: ["LV-02"],
          icon: "☾",
          accent: "icon-tile-teal",
        },
        {
          title: "Ledger-derived balances",
          desc: "The balance shown is the sum of ledger entries — accruals, uses, expiries and adjustments. Nothing disagrees with the ledger because the balance is the ledger.",
          refs: ["LV-03"],
          icon: "≡",
          accent: "icon-tile-green",
        },
        {
          title: "Leave types, accruals, holidays",
          desc: "Configurable leave types with accrual parameters per policy, public-holiday calendars and carry-over rules — tuned per location, not one global default.",
          refs: ["LV-01", "CF-05"],
          icon: "◈",
        },
        {
          title: "Approvals in one click",
          desc: "Configurable chains route by role, location and policy; the approver sees balance, team overlap and history on the decision itself.",
          refs: ["LV-02", "UX-04"],
          icon: "✓",
          accent: "icon-tile-amber",
        },
        {
          title: "Only unpaid leave reduces pay",
          desc: "The payroll run consumes approved leave by type; paid leave never quietly costs the employee a day's salary, and the payslip records the leave it consumed.",
          refs: ["LV-05", "PY-03"],
          icon: "₵",
          accent: "icon-tile-brand",
        },
        {
          title: "Delegation keeps pipelines moving",
          desc: "Approver unavailable? Delegation hands the approval bucket to a stand-in with the same checks — leave never stalls in an absent inbox.",
          refs: ["LV-02"],
          icon: "⇄",
          accent: "icon-tile-slate",
        },
      ]}
      inTitle="Next in sequence for leave"
      inDesign={[
        { text: "Team availability and absence calendars for the manager view", refs: ["LV-04"] },
        { text: "Forecast-driven absence projections in analytics", refs: ["AN-03"] },
      ]}
      connect={[
        {
          title: "Into the payroll run",
          desc: "Approved leave is a payroll input the payslip can trace — unpaid types reduce pay, paid types don't, and every excluded entry is named.",
          to: "/platform/payroll",
          label: "Payroll module",
        },
        {
          title: "Beside the timesheet",
          desc: "Overlap checks mean a day is never both approved leave and worked time — time capture and the leave ledger agree by construction.",
          to: "/time",
          label: "Time module",
        },
        {
          title: "Configured by industry preset",
          desc: "Leave types and accrual parameters arrive pre-configured for your industry template — retail and hospital patterns, not a blank form.",
          to: "/industries",
          label: "Industry presets",
        },
      ]}
    />
  )
}
