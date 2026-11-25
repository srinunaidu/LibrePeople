import { ModulePage } from "@/components/marketing/ModulePage"

export default function CompliancePage() {
  return (
    <ModulePage
      stageId="offboard"
      kicker="Module — Compliance & assurance"
      title="Compliance — enforced by the system, not the handbook"
      intro="Rules, violations, headcount plans and scenarios — plus the enforced properties that make everything compliant automatically: one record per tenant, RBAC at every endpoint, and a tamper-evident audit chain."
      facts={[
        { label: "Rules", value: "Configured, versioned" },
        { label: "Violations", value: "Surfaced + named" },
        { label: "Audit", value: "Hash-chained" },
      ]}
      shipTitle="Assurance that's enforced in code"
      ships={[
        {
          title: "Compliance rules with violation tracking",
          desc: "Rules are configured records, violations are surfaced with the record and rule named — an audit finding becomes a queue item instead of a memo.",
          refs: ["HR-11", "AD-07"],
          icon: "§",
          accent: "icon-tile-brand",
        },
        {
          title: "Headcount plans and scenarios",
          desc: "Plan headcount by department with what-if scenarios — growth decisions carry their own what-if state and compare cleanly.",
          refs: ["AN-05"],
          icon: "▤",
          accent: "icon-tile-teal",
        },
        {
          title: "Hash-chained audit trail",
          desc: "Every action is chained to the last entry; the database refuses edits and the chain verifier names the entry that broke it — tamper-evidence in the schema.",
          refs: ["AD-07"],
          icon: "⛓",
          accent: "icon-tile-green",
        },
        {
          title: "RBAC enforced everywhere",
          desc: "300+ role-based checks authority-gate every endpoint; employee visibility is scoped, so a manager sees a team, not a company.",
          refs: ["AD-04"],
          icon: "⬢",
          accent: "icon-tile-violet",
        },
        {
          title: "One customer per database",
          desc: "Tenant isolation means another company's people, pay and records can never be seen by yours — enforced by the data model.",
          refs: ["AD-04"],
          icon: "◈",
          accent: "icon-tile-amber",
        },
        {
          title: "Import safety built in",
          desc: "Bulk CSV runs validate types, dates, references and duplicates, rehearsal-dry-runs first, and mask personal values in every error report.",
          refs: ["IM-04", "IM-06", "IM-11"],
          icon: "✓",
          accent: "icon-tile-slate",
        },
      ]}
      inTitle="Next in sequence for assurance"
      inDesign={[
        { text: "Data retention, export and erasure workflows for privacy rights", refs: ["AD-09"] },
        { text: "Backup and restoration verification drives", refs: ["AD-08"] },
        { text: "Scheduled reporting exports with permission control", refs: ["AN-08"] },
      ]}
      connect={[
        {
          title: "The full security posture",
          desc: "Read the honest security page — encryption, isolation, controls and what is (and is not yet) certified.",
          to: "/security",
          label: "Security posture",
        },
        {
          title: "Audit on every module",
          desc: "The chain runs beneath the whole thread: payroll, leave, employee changes, every create and edit.",
          to: "/platform",
          label: "Platform tour",
        },
        {
          title: "Headcount into forecasting",
          desc: "Headcount plans feed the forecast engine, where actual-versus-plan comparison keeps budgets honest.",
          to: "/platform#reporting",
          label: "Forecasting",
        },
      ]}
    />
  )
}
