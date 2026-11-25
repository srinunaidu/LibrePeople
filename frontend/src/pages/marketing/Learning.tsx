import { ModulePage } from "@/components/marketing/ModulePage"

export default function LearningPage() {
  return (
    <ModulePage
      stageId="grow"
      kicker="Module — Learning & talent"
      title="Learning — growth that's tracked, not assumed"
      intro="A course catalogue with real enrolments, assessment state and certification expiry tracking on the one employee record — plus talent pools and succession feeding the longer game."
      facts={[
        { label: "Catalogue", value: "Courses + paths" },
        { label: "Certifications", value: "Expiry tracking" },
        { label: "Talent", value: "Pools + succession" },
      ]}
      shipTitle="What learning ships today"
      ships={[
        {
          title: "Courses, enrolments, assessments",
          desc: "The catalogue is real: course records with enrolments, assessment state and learning paths — an education plan is assigned data, not a memo.",
          refs: ["LN-01"],
          icon: "▤",
          accent: "icon-tile-brand",
        },
        {
          title: "Certification expiry tracking",
          desc: "Certifications carry expiry dates; the record surfaces what lapses soon — a credential you forgot stops being a disclosed date on a form.",
          refs: ["LN-03"],
          icon: "◎",
          accent: "icon-tile-amber",
        },
        {
          title: "Talent pools + succession plans",
          desc: "People are cultivated, not just filed: talent-pool records and succession plans for critical roles share the same source of truth.",
          refs: ["PM-05", "LN-01"],
          icon: "◈",
          accent: "icon-tile-violet",
        },
        {
          title: "Industry template pre-fill",
          desc: "Role families in each industry preset bring the training pattern with them — a carer onboarding checklist, a manager track, a compliance refresher.",
          refs: ["CF-03", "CF-08"],
          icon: "⬢",
          accent: "icon-tile-teal",
        },
        {
          title: "Document acknowledgements",
          desc: "Handbooks and policy documents record who acknowledged what and when — the learning evidence auditors actually ask for.",
          refs: ["HR-07", "OB-02"],
          icon: "✓",
          accent: "icon-tile-green",
        },
        {
          title: "Where performance points",
          desc: "Review outcomes reference growth needs; development becomes a tracked continuation of the thread, not a separate app.",
          refs: ["PM-01"],
          icon: "↗",
          accent: "icon-tile-slate",
        },
      ]}
      inTitle="Next in sequence for learning"
      inDesign={[
        { text: "Mandatory training and compliance assignment", refs: ["LN-02"] },
        { text: "Skills taxonomy with proficiency levels and reviewed profiles", refs: ["LN-04"] },
        { text: "Skill gaps, career paths and internal opportunities", refs: ["LN-05"] },
        { text: "Completion and effectiveness analytics", refs: ["LN-07"] },
      ]}
      connect={[
        {
          title: "From the review cycle",
          desc: "Performance outcomes feed learning — one thread from feedback to skills to succession.",
          to: "/platform/performance",
          label: "Performance module",
        },
        {
          title: "Into succession and growth",
          desc: "Talent pools and critical-role coverage live here in the 'grow' stage of the lifecycle.",
          to: "/platform#performance",
          label: "Succession view",
        },
        {
          title: "The AI plan, honestly",
          desc: "Skills-gap and learning recommendations are Phase-8 AI capabilities — deferred behind the release gates, not promised.",
          to: "/ai",
          label: "AI roadmap",
        },
      ]}
    />
  )
}
