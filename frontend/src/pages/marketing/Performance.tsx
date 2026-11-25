import { ModulePage } from "@/components/marketing/ModulePage"

export default function PerformancePage() {
  return (
    <ModulePage
      stageId="perform"
      kicker="Module — Performance · stage 6 of the thread"
      title="Performance — fair goals, reviews you'd sign your name to"
      intro="Goals, continuous feedback and one-to-ones alongside structured review cycles — with compensation bands on the same record, so a pay decision never floats free of the performance evidence."
      facts={[
        { label: "Goals", value: "OKR-style, shared" },
        { label: "Reviews", value: "Cycle-based" },
        { label: "Comp", value: "Bands, merit cycles" },
      ]}
      shipTitle="Performance that reads like the work"
      ships={[
        {
          title: "Goals, OKRs and continuous feedback",
          desc: "Shared objectives with check-ins; one-to-ones and feedback recorded as history rather than living in a manager's notebook.",
          refs: ["PM-01"],
          icon: "⬢",
          accent: "icon-tile-violet",
        },
        {
          title: "Structured review cycles",
          desc: "Self-assessments and manager reviews flow together in a cycle the owner can actually monitor — completion visible, reminders sane.",
          refs: ["PM-02"],
          icon: "◷",
          accent: "icon-tile-brand",
        },
        {
          title: "Succession and talent reviews",
          desc: "Critical roles carry named succession plans so a resignation is a transition, not an incident.",
          refs: ["PM-05"],
          icon: "◈",
          accent: "icon-tile-teal",
        },
        {
          title: "Compensation bands + merit cycles",
          desc: "Bands and merit allocations live beside performance — a raise proposal cites both, and out-of-band values require the explicit reason.",
          refs: ["PY-06"],
          icon: "₵",
          accent: "icon-tile-green",
        },
        {
          title: "Effective-dated outcomes",
          desc: "A promotion or salary revision lands as a dated change with history preserved — the compensation trail matches the review trail.",
          refs: ["HR-03", "PY-06"],
          icon: "↗",
          accent: "icon-tile-amber",
        },
        {
          title: "Manager views that surface the data",
          desc: "Team availability, approvals and performance share one manager queue — the review conversation starts from evidence, not memory.",
          refs: ["UX-04"],
          icon: "▤",
          accent: "icon-tile-slate",
        },
      ]}
      inTitle="Next in sequence for performance"
      inDesign={[
        { text: "Competency frameworks, calibration and completion tracking", refs: ["PM-03"] },
        { text: "Improvement plans, recognition and development objectives", refs: ["PM-04"] },
        { text: "Promotion readiness and talent analytics with scoped access", refs: ["PM-06"] },
        { text: "360° feedback patterns", refs: ["PM-02"] },
      ]}
      connect={[
        {
          title: "Into grow — learning and skills",
          desc: "Review outcomes point at growth: courses, certifications and talent pools are on the same record so a development plan is assigned, not discussed.",
          to: "/platform/learning",
          label: "Learning module",
        },
        {
          title: "Into pay, provably",
          desc: "Merit outcomes flow to payroll as effective-dated changes; the payslip trail and the review trail agree.",
          to: "/platform/payroll",
          label: "Payroll module",
        },
        {
          title: "The AI plan, stated honestly",
          desc: "Performance analytics are part of the Phase-8 AI sequence — deferred behind the release gates, not quietly promised.",
          to: "/ai",
          label: "AI roadmap",
        },
      ]}
    />
  )
}
