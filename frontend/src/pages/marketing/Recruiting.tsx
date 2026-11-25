import { ModulePage } from "@/components/marketing/ModulePage"

export default function RecruitingPage() {
  return (
    <ModulePage
      stageId="recruit"
      kicker="Module — Recruiting · stage 1 of the thread"
      title="Recruiting — find people who fit the record"
      intro="Requisitions, candidates, applications, offers and e-signature inside one candidate record — every funnel step traceable, every accepted offer landing in the directory without a retype."
      facts={[
        { label: "Funnel", value: "Requisition → hire" },
        { label: "Offers", value: "Accept = hire, intact" },
        { label: "Evidence", value: "E-sign + background" },
      ]}
      shipTitle="What recruiting ships today"
      ships={[
        {
          title: "Requisitions with approvals",
          desc: "A requisition is a record with an approval state — headcount opens deliberately, teams know exactly what's open and why.",
          refs: ["RC-01"],
          icon: "⬣",
          accent: "icon-tile-brand",
        },
        {
          title: "Candidates, applications, stages",
          desc: "One candidate record drives the funnel; applications and stage moves are transactions, not scattered emails.",
          refs: ["RC-03"],
          icon: "◈",
          accent: "icon-tile-teal",
        },
        {
          title: "Offers with acceptance integrity",
          desc: "Offer approval tracked end to end; acceptance and hire are one transaction — no candidate lost between the offer and the directory.",
          refs: ["RC-05"],
          icon: "✓",
          accent: "icon-tile-green",
        },
        {
          title: "E-signature + background checks",
          desc: "Signed statuses and background-check completions are first-class records — hiring evidence exists where the audit expects it.",
          refs: ["RC-08"],
          icon: "✍",
          accent: "icon-tile-violet",
        },
        {
          title: "Straight into onboarding",
          desc: "A placed candidate moves into the onboarding module — day-one checklists and document collection reuse the same person record.",
          refs: ["OB-01"],
          icon: "↗",
          accent: "icon-tile-amber",
        },
        {
          title: "One audit trail underneath",
          desc: "Every funnel change lands in the hash-chained chain — recruiting inherits the platform's evidence layer by default.",
          refs: ["AD-07"],
          icon: "⛓",
          accent: "icon-tile-slate",
        },
      ]}
      inTitle="Next in sequence for recruiting"
      inDesign={[
        { text: "Interview scheduling, interview kits, scorecards, feedback", refs: ["RC-04"] },
        { text: "Candidate communications and career-site integration", refs: ["RC-06"] },
        { text: "Funnel and source analytics — time-to-fill, conversion", refs: ["RC-07"] },
        { text: "Hiring budgets inside the approval flow", refs: ["RC-01"] },
      ]}
      connect={[
        {
          title: "Into day one",
          desc: "Onboarding picks up at acceptance: checklists, acknowledgements and documents on the same record.",
          to: "/onboarding",
          label: "Onboard module",
        },
        {
          title: "Into headcount truth",
          desc: "Funnel accuracy makes headcount reporting honest by construction — recruiters see where requisitions actually sit.",
          to: "/platform#reporting",
          label: "Reporting",
        },
        {
          title: "The AI plan, honestly",
          desc: "No autonomous candidate rejection — a prohibition written into the AI design. AI capabilities are sequenced, not promised.",
          to: "/ai",
          label: "AI roadmap",
        },
      ]}
      cta="Book a demo of recruiting"
    />
  )
}
