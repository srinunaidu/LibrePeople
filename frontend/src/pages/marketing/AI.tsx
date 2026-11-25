import { ModulePage } from "@/components/marketing/ModulePage"

export default function AIPage() {
  return (
    <ModulePage
      kicker="Roadmap — Phase 8 · AI & intelligence"
      title="AI — sequenced behind the gates, not promised"
      intro="Intelligence capabilities are designed in three tiers with mandatory controls and explicit prohibitions. They sit in Phase 8 of the spec order — after security, contracts, import, core HCM, forecasting, payroll and experience work has landed."
      facts={[
        { label: "Spec order", value: "Phase 8 of 9" },
        { label: "Controls", value: "13, before first launch" },
        { label: "Prohibitions", value: "No autonomous hiring decisions" },
      ]}
      shipTitle="What analytics are live today (the foundation AI builds on)"
      ships={[
        {
          title: "Forecasting with accuracy scoring",
          desc: "Labour-demand forecasts run against attendance and roster history, with model version and confidence surfaced — a forecast that admits its error margin.",
          refs: ["AN-04", "AN-07"],
          icon: "◔",
          accent: "icon-tile-brand",
        },
        {
          title: "Headcount and staffing scenarios",
          desc: "What-if scenarios compare plans against actuals — the analytical workflow AI assistance will extend, working today.",
          refs: ["AN-05"],
          icon: "▤",
          accent: "icon-tile-teal",
        },
        {
          title: "Governed metrics and drill-downs",
          desc: "Metric definitions and data lineage are governed — an insight is only as good as the definition underneath it, and that's version-controlled.",
          refs: ["AN-02"],
          icon: "◈",
          accent: "icon-tile-green",
        },
        {
          title: "Payslip traceability",
          desc: "Every pay figure traces to approved inputs — the discipline that makes AI payroll-explanation honest rather than probabilistic.",
          refs: ["PY-03"],
          icon: "₵",
          accent: "icon-tile-violet",
        },
        {
          title: "Hash-chained audit trail",
          desc: "The evidence layer AI actions will write to: chained, tamper-evident, verified entry by entry.",
          refs: ["AD-07"],
          icon: "⛓",
          accent: "icon-tile-slate",
        },
        {
          title: "Curated product help (no generation)",
          desc: "The help index is curated today — a deliberate design that keeps generated answers out until the controls ship.",
          refs: ["CF-13"],
          icon: "✓",
          accent: "icon-tile-amber",
        },
      ]}
      inTitle="The designed AI capabilities — three tiers, thirteen controls"
      inDesign={[
        { text: "Tier A — HR policy search with citations; document classification with human verification", refs: ["AI-01", "AI-02"] },
        { text: "Tier A — drafting job descriptions and communications; summarising authorised cases", refs: ["AI-03", "AI-04"] },
        { text: "Tier B — schedule recommendations, skills-gap analysis, workforce cost and attrition analysis", refs: ["AI-07", "AI-08", "AI-09"] },
        { text: "Tier B — payroll exception explanations from verified calculation inputs", refs: ["AI-10"] },
        { text: "Tier C — draft change, check permissions, show impact, request approval, execute, record", refs: ["AI-11"] },
        { text: "13 mandatory controls: permission-aware retrieval, no PII in prompts, no training on customer data, injection defence, human approval, traceability, kill switch", refs: ["AI-12"] },
        { text: "Prohibitions: no autonomous candidate rejection, eligibility, termination or compensation decisions", refs: ["AI-13"] },
      ]}
      connect={[
        {
          title: "The status, verifiable",
          desc: "This page paraphrases the plan of record — the sequencing and gates live in the product status documentation.",
          to: "/about",
          label: "How we build",
        },
        {
          title: "Analytics that already work",
          desc: "The forecasting and scenario surface is live today — see it in the platform tour.",
          to: "/platform#reporting",
          label: "Platform tour",
        },
        {
          title: "Ask what ships next",
          desc: "Talk to the founding team about where AI assistance lands in your rollout order.",
          to: "/contact",
          label: "Contact us",
        },
      ]}
      cta="Discuss the AI timeline"
    />
  )
}
