import { ModulePage } from "@/components/marketing/ModulePage"

export default function OnboardingPage() {
  return (
    <ModulePage
      stageId="onboard"
      kicker="Module — Onboarding · stage 2 of the thread"
      title="Onboarding — day one, arranged before day one"
      intro="Resumable preboarding checklists, document acknowledgements and industry templates that pre-fill the org — so a hire's first day is configuration, not improvisation."
      facts={[
        { label: "Checklists", value: "Resumable" },
        { label: "Templates", value: "6 industry kits" },
        { label: "Import", value: "Dry run first" },
      ]}
      shipTitle="What onboarding ships today"
      ships={[
        {
          title: "Resumable preboarding checklist",
          desc: "Offers become onboarding checklists grouped by step with state kept per hire — a half-finished onboarding resumes exactly where it stopped.",
          refs: ["OB-01", "RC-05"],
          icon: "＋",
          accent: "icon-tile-teal",
        },
        {
          title: "Information collection + acknowledgements",
          desc: "Employee details are collected before day one and document acknowledgements are recorded — the paperwork stops being a folder of loose scans.",
          refs: ["OB-02", "HR-07"],
          icon: "◈",
          accent: "icon-tile-brand",
        },
        {
          title: "Offer acceptance with e-signature",
          desc: "Offers, signatures and background-check states are tracked records with integrity from accepted-offer to onboarded-employee.",
          refs: ["RC-08"],
          icon: "✍",
          accent: "icon-tile-green",
        },
        {
          title: "Industry kits pre-fill the org",
          desc: "Six validated industry templates bring departments, job families, shift patterns, leave types and dashboards — the setup is never a blank page.",
          refs: ["CF-01", "CF-03", "CF-04", "CF-05"],
          icon: "▦",
          accent: "icon-tile-violet",
        },
        {
          title: "Bulk hires via CSV, dry-run first",
          desc: "Import counts what it will create, reports bad rows before writing, idempotent on natural keys and idempotent re-runs change nothing.",
          refs: ["IM-04", "IM-05", "IM-06", "IM-07"],
          icon: "⇄",
          accent: "icon-tile-amber",
        },
        {
          title: "Auto-generated identity",
          desc: "New hires get their employee number generated in the family (like EMP-0007) — masters ready from the first save.",
          refs: ["HR-01"],
          icon: "⑴",
          accent: "icon-tile-slate",
        },
      ]}
      inTitle="Next in sequence for onboarding"
      inDesign={[
        { text: "Equipment, access and task assignment to owners with due dates", refs: ["OB-03"] },
        { text: "Probation tracking, confirmation and reminders", refs: ["OB-04"] },
        { text: "Transfers, promotions and contract renewals as onboarding flows", refs: ["OB-05"] },
        { text: "The ten-step guided journey with resumable progress", refs: ["CF-11"] },
      ]}
      connect={[
        {
          title: "Straight from recruiting",
          desc: "Accepted offers become hires with the transaction intact — candidate to directory row without a retype.",
          to: "/recruiting",
          label: "Recruiting module",
        },
        {
          title: "Into time and leave",
          desc: "A completed onboarding record is a working employee record — capture, ledger and schedule all pointing at the same person.",
          to: "/time",
          label: "Time module",
        },
        {
          title: "Self-service starts here",
          desc: "Employees sign in to their own record from day one — profile, payslips, leave requests in the employee's hands.",
          to: "/platform/payroll",
          label: "Payslip self-service",
        },
      ]}
      cta="Book an onboarding demo"
    />
  )
}
