import { ModulePage } from "@/components/marketing/ModulePage"

export default function TimePage() {
  return (
    <ModulePage
      stageId="time"
      kicker="Module — Time & Attendance · stage 3 of the thread"
      title="Time & attendance — hours you can defend"
      intro="Clock in and out, generated timesheets, cross-midnight shifts and overtime inputs flow straight into payroll calculation — unapproved hours are excluded and reported, never silently paid."
      facts={[
        { label: "Capture", value: "Clock-in/out + breaks" },
        { label: "Handoff", value: "Approved time → payroll" },
        { label: "Cut-off", value: "Timesheet lock + adjustments" },
      ]}
      shipTitle="Time capture that survives an audit"
      ships={[
        {
          title: "Clock in/out with break capture",
          desc: "Punches record the worked day in sequence; timesheets are generated from the capture rather than retyped, so the numbers start from the source.",
          refs: ["TM-01"],
          icon: "◷",
        },
        {
          title: "Approved time, or no pay",
          desc: "Payroll consumes only approved entries. Unapproved hours are excluded from the run and reported — the computation states what it did not use.",
          refs: ["TM-01", "PY-03"],
          icon: "✓",
          accent: "icon-tile-green",
        },
        {
          title: "Cross-midnight + overtime inputs",
          desc: "Overnight shifts, overtime lines and exception rows are carried precisely — the shift that ends at 4 a.m. lands on the right day with the right rate.",
          refs: ["TM-03"],
          icon: "◐",
          accent: "icon-tile-violet",
        },
        {
          title: "Cut-off and timesheet lock",
          desc: "After the payroll cut-off the period locks; corrections become recorded adjustments instead of edits — who changed what stays on the audit trail.",
          refs: ["TM-05"],
          icon: "▤",
          accent: "icon-tile-teal",
        },
        {
          title: "One employee record underneath",
          desc: "Time reads the same record the directory, leave and payroll read: job, location and manager changes re-point capture automatically.",
          refs: ["HR-02", "HR-03"],
          icon: "◈",
        },
        {
          title: "Approvals where managers live",
          desc: "Timesheet approval sits on the manager's action queue with filtering by person, status and period — not an inbox scavenger hunt.",
          refs: ["UX-04"],
          icon: "⬢",
          accent: "icon-tile-slate",
        },
      ]}
      inTitle="Next in sequence for time"
      inDesign={[
        { text: "Attendance policies with configurable rules and missed-punch correction flows", refs: ["TM-02"] },
        { text: "Attendance reasoning for shift-based and fixed schedules", refs: ["TM-04"] },
        { text: "Team availability surfaces inside the manager views", refs: ["UX-04"] },
      ]}
      connect={[
        {
          title: "Feeds payroll, provably",
          desc: "The payslip shows the approved hours and leave it consumed and names the entries it excluded — time is the input payroll can trace.",
          to: "/platform/payroll",
          label: "Payroll module",
        },
        {
          title: "Leave sits beside the timesheet",
          desc: "Approved leave reduces pay but appears in the ledger; overlap checks stop double-counting a day as both leave and work.",
          to: "/leave",
          label: "Leave module",
        },
        {
          title: "Scheduled shifts set the frame",
          desc: "Scheduling drafts the roster before the week, time captures what actually happened — plan versus actual reads cleanly.",
          to: "/scheduling",
          label: "Scheduling module",
        },
      ]}
    />
  )
}
