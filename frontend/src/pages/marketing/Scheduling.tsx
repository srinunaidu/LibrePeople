import { ModulePage } from "@/components/marketing/ModulePage"

export default function SchedulingPage() {
  return (
    <ModulePage
      stageId="time"
      kicker="Module — Scheduling & rostering"
      title="Scheduling — rosters that survive contact with a shift"
      intro="Shift templates, roster drafts, publishing and swap workflows share one record with time capture — the plan before the week and the reality after it read from the same source."
      facts={[
        { label: "Drafting", value: "Templates → roster" },
        { label: "Publish", value: "One ordered step" },
        { label: "Swaps", value: "Tracked, approved" },
      ]}
      shipTitle="What scheduling ships today"
      ships={[
        {
          title: "Shift templates, open shifts, drafts",
          desc: "Reusable shift patterns assemble into roster drafts; open shifts sit in the draft until assigned — no more spreadsheets with forty hidden assumptions.",
          refs: ["SC-01", "CF-04"],
          icon: "▦",
          accent: "icon-tile-green",
        },
        {
          title: "Draft → publish lifecycle",
          desc: "A roster is drafted, adjusted, then published as an ordered step — people are notified from a concrete published version, not a guess.",
          refs: ["SC-01"],
          icon: "▚",
          accent: "icon-tile-teal",
        },
        {
          title: "Swap and replacement workflows",
          desc: "Employees request swaps with coverage intact; the approval records who covered which shift and when — disputes stop being archaeology.",
          refs: ["SC-06"],
          icon: "⇄",
          accent: "icon-tile-amber",
        },
        {
          title: "Industry-pattern templates",
          desc: "Validated industry presets ship shift templates and working patterns — hospital rotations and retail peaks arrive pre-configured.",
          refs: ["CF-01", "CF-04"],
          icon: "◈",
          accent: "icon-tile-brand",
        },
        {
          title: "Feeds time capture cleanly",
          desc: "Published shifts frame the period; time capture fills the actuals — cross-midnight and overtime handling follows the same record.",
          refs: ["SC-01", "TM-03"],
          icon: "◷",
          accent: "icon-tile-violet",
        },
        {
          title: "Labour-cost visibility",
          desc: "Headcount and labour-cost metrics read the roster and actuals, so a coverage decision is made with a cost figure on the table.",
          refs: ["AN-01"],
          icon: "▤",
          accent: "icon-tile-slate",
        },
      ]}
      inTitle="Optimisation, sequenced not skipped"
      inDesign={[
        { text: "Demand-based staffing by location, role, skill and interval", refs: ["SC-02"] },
        { text: "Availability and preference honoring, approved-leave aware", refs: ["SC-03"] },
        { text: "Hard constraints — rest, hours, certifications, double-booking rules", refs: ["SC-04"] },
        { text: "Coverage-gap and overtime alerts", refs: ["SC-07"] },
        { text: "Schedule versioning with change history and notifications", refs: ["SC-09"] },
      ]}
      connect={[
        {
          title: "Into the week's time",
          desc: "Published rosters are the frame; time capture records the actuals; exceptions carry to payroll with the story intact.",
          to: "/time",
          label: "Time module",
        },
        {
          title: "Forecasting continues the story",
          desc: "Labour-demand forecasting with accuracy scoring builds on the same attendance and roster history — a scenario, not a séance.",
          to: "/platform#reporting",
          label: "Forecasting",
        },
        {
          title: "Pacific-sized teams start here",
          desc: "Scheduling templates are part of every industry preset — see the platform tour for the whole configured surface.",
          to: "/platform",
          label: "Platform tour",
        },
      ]}
      cta="Book a scheduling demo"
    />
  )
}
