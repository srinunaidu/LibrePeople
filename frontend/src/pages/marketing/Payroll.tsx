import { ModulePage } from "@/components/marketing/ModulePage"

export default function PayrollPage() {
  return (
    <ModulePage
      stageId="pay"
      kicker="Module — Payroll · stage 5 of the thread"
      title="Payroll — every number can show its work"
      intro="Pay is calculated from the time and leave an approver accepted, in jurisdictional rule packs with versioned test fixtures. A payslip opens to show what it was paid from — and the run reconciles expected against paid before you commit."
      facts={[
        { label: "Inputs", value: "Approved time + leave only" },
        { label: "Rules", value: "Versioned jurisdiction packs" },
        { label: "Trace", value: "Payslip → source rows" },
      ]}
      shipTitle="Payroll, the way you'd design it from scratch"
      ships={[
        {
          title: "Approved inputs, excluded entries named",
          desc: "The run consumes approved time and leave, pays overtime at the employee's own rate, and reports every entry it excluded — with the reason.",
          refs: ["PY-03"],
          icon: "≡",
          accent: "icon-tile-green",
        },
        {
          title: "Payslip drill-down",
          desc: "Open a payslip and see the approved hours and leave it consumed, the unapproved entries it deliberately left out, and the rule, version and calculation behind every line — stored figures shown, never recalculated.",
          refs: ["PY-03", "PY-04"],
          icon: "◎",
          accent: "icon-tile-brand",
        },
        {
          title: "Reconciled expected vs paid",
          desc: "Before a run is committed, expected net is reconciled against the calculated result; payslip results are matched line by line so variance is surfaced, not discovered.",
          refs: ["PY-04"],
          icon: "⇄",
          accent: "icon-tile-teal",
        },
        {
          title: "Jurisdiction rule packs",
          desc: "Statutory contributions live in versioned packs for different locations, each verified by rule-specific test fixtures — the generic calculator is separated from verified statutory capability.",
          refs: ["PY-09", "PY-10"],
          icon: "▤",
          accent: "icon-tile-violet",
        },
        {
          title: "Salary structures with effective dating",
          desc: "Pay components, revisions and structures are effective-dated on the one employee record; history is preserved rather than overwritten.",
          refs: ["PY-01", "PY-06"],
          icon: "◈",
        },
        {
          title: "Historical records, controlled corrections",
          desc: "Past runs remain readable history; corrections are controlled transactions that record why, so the audit trail reads like the accounting.",
          refs: ["PY-05"],
          icon: "✓",
          accent: "icon-tile-slate",
        },
      ]}
      inTitle="Before we call payroll customer-ready"
      inDesign={[
        { text: "Pay-run approval and lock — a run is proposed, approved, then immutable", refs: ["PY-04"] },
        { text: "Off-cycle and out-of-run corrections", refs: ["PY-04"] },
        { text: "Proration for mid-period starters and leavers", refs: ["PY-04"] },
        { text: "Explicit currency and pay-period semantics surfaced in the contract", refs: ["PY-08"] },
        { text: "Bank-ready payment export", refs: ["PY-07"] },
      ]}
      connect={[
        {
          title: "Consumes time and leave",
          desc: "Approved timesheets and the leave ledger are payroll's inputs — the source of the pay figure is always one click away.",
          to: "/time",
          label: "Time module",
        },
        {
          title: "Reaches the employee",
          desc: "Self-service payslips land in the employee's own view — payroll transparency without HR forwarding files.",
          to: "/onboarding",
          label: "Self-service hub",
        },
        {
          title: "Compared honestly",
          desc: "See how our reconciliation-first payroll approach compares to the legacy suites on the comparison pages.",
          to: "/compare/bamboohr",
          label: "Compare",
        },
      ]}
      cta="Request a payroll walkthrough"
    />
  )
}
