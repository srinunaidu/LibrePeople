import { ModulePage } from "@/components/marketing/ModulePage"

export default function BenefitsPage() {
  return (
    <ModulePage
      stageId="grow"
      kicker="Module — Benefits"
      title="Benefits — enrolment without the envelope stack"
      intro="Benefit plans, eligibility rules, enrolment windows and dependant records live on the one employee record — with leaves of absence and life events wired to the same lifecycle."
      facts={[
        { label: "Plans", value: "Eligibility rules" },
        { label: "Enrolment", value: "Windows, dependants" },
        { label: "Lifecycle", value: "Life events, LOA" },
      ]}
      shipTitle="What benefits ships today"
      ships={[
        {
          title: "Plans with real eligibility",
          desc: "Benefit plans carry eligibility rules so 'who can be in this plan' is a configuration, not a hallway conversation.",
          refs: ["BN-01"],
          icon: "✚",
          accent: "icon-tile-green",
        },
        {
          title: "Enrolment windows",
          desc: "Enrolment periods open and close visibly; the window state, not the HR inbox, governs who can join and when.",
          refs: ["BN-01"],
          icon: "◷",
          accent: "icon-tile-brand",
        },
        {
          title: "Dependants as records",
          desc: "Dependant details are stored per enrolment — coverage decisions stop living in email attachments.",
          refs: ["BN-01"],
          icon: "◈",
          accent: "icon-tile-teal",
        },
        {
          title: "Leaves of absence",
          desc: "LOA records track the period and type on the same lifecycle — adjacent to the ledger that payroll reads.",
          refs: ["BN-01", "LV-05"],
          icon: "☾",
          accent: "icon-tile-amber",
        },
        {
          title: "Life events trigger the move",
          desc: "Life events open the enrolment changes that marriage, birth or loss of coverage legally require.",
          refs: ["BN-01"],
          icon: "✓",
          accent: "icon-tile-violet",
        },
        {
          title: "Audit trail on every row",
          desc: "Enrolments are audited like everything else — who changed coverage, when, from which address.",
          refs: ["AD-07"],
          icon: "▤",
          accent: "icon-tile-slate",
        },
      ]}
      inTitle="Next in sequence for benefits"
      inDesign={[
        { text: "Employer contributions and reimbursements with claim status", refs: ["BN-02"] },
        { text: "Plan renewals and benefit documentation reminders", refs: ["BN-03"] },
        { text: "Benefit deduction loops as full payroll components", refs: ["BN-02", "PY-02"] },
      ]}
      connect={[
        {
          title: "Into payroll components",
          desc: "Benefit deductions are one of the payroll component families the calculation reads — see how components are structured.",
          to: "/platform/payroll",
          label: "Payroll module",
        },
        {
          title: "Life events meet leave",
          desc: "Life events, LOA and the leave ledger share the lifecycle — coverage and absence never contradict.",
          to: "/leave",
          label: "Leave module",
        },
        {
          title: "Grow the total picture",
          desc: "Benefits sit beside learning, talent and succession in the 'grow' stage of the thread.",
          to: "/platform",
          label: "Platform tour",
        },
      ]}
    />
  )
}
