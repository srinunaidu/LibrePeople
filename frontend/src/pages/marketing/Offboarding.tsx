import { ModulePage } from "@/components/marketing/ModulePage"

export default function OffboardingPage() {
  return (
    <ModulePage
      stageId="offboard"
      kicker="Module — Offboarding · stage 8 of the thread"
      title="Offboarding — departures without loose ends"
      intro="Exit interviews, access revocation, asset returns and final settlement tracked on the same employee record — with a lifecycle that only allows the transitions the law and good practice do."
      facts={[
        { label: "Tasks", value: "Exit checklist set" },
        { label: "Records", value: "History preserved" },
        { label: "Lifecycle", value: "Enforced transitions" },
      ]}
      shipTitle="What offboarding ships today"
      ships={[
        {
          title: "Exit interview, revocation, assets, settlement",
          desc: "The departure checklist is one record: exit interview state, access revocation, asset returns and the final settlement so nothing is discovered later.",
          refs: ["OB-06"],
          icon: "▸",
          accent: "icon-tile-teal",
        },
        {
          title: "Termination only via the lifecycle",
          desc: "Active or on-leave can leave; a terminated employee can only be rehired — never quietly reactivated. Illegal transitions are refused with the moves allowed named.",
          refs: ["HR-02"],
          icon: "✓",
          accent: "icon-tile-green",
        },
        {
          title: "Effective-dated changes, complete history",
          desc: "The status change records its first day, why and who; a newer change closes the old row and the whole employment history stays readable.",
          refs: ["HR-03"],
          icon: "◈",
          accent: "icon-tile-brand",
        },
        {
          title: "Final settlement flows to payroll",
          desc: "Separations feed the payroll record — leave paid out, approved-but-unpaid time handled per policy, and the auditable reason on every line.",
          refs: ["OB-06", "PY-03"],
          icon: "₵",
          accent: "icon-tile-violet",
        },
        {
          title: "Audit trail to the last entry",
          desc: "The hash-chained chain covers the offboarding actions like everything else — proof for whoever asks next.",
          refs: ["AD-07"],
          icon: "⛓",
          accent: "icon-tile-amber",
        },
        {
          title: "The record ends, the history doesn't",
          desc: "A terminated employee disappears from the productive surfaces but their history, payslips and audit rows are retained and retrievable.",
          refs: ["HR-03", "AD-07"],
          icon: "▤",
          accent: "icon-tile-slate",
        },
      ]}
      inTitle="Next in sequence for offboarding"
      inDesign={[
        { text: "Rehire handling with the reason preserved from the last exit", refs: ["OB-07"] },
        { text: "Offboarding dashboards and overdue-task escalation", refs: ["OB-07"] },
        { text: "Retention and erasure workflows for privacy rights on exit", refs: ["AD-09"] },
      ]}
      connect={[
        {
          title: "Settlement is payroll's story",
          desc: "Final sums, leave payouts and the excluded entries read the same payslip drill-down as every run.",
          to: "/platform/payroll",
          label: "Payroll module",
        },
        {
          title: "The chain closes the loop",
          desc: "An offboarding record makes a future rehire a lifecycle transition, not a duplicate person.",
          to: "/recruiting",
          label: "Recruiting",
        },
        {
          title: "One audit trail, end to end",
          desc: "The compliance module describes the trail that already covers every action in the thread.",
          to: "/platform/compliance",
          label: "Compliance module",
        },
      ]}
    />
  )
}
