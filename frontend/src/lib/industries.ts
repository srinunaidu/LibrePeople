export interface Industry {
  slug: string
  name: string
  icon: string
  pain: string[]
  regulation: string
  workflow: { step: string; detail: string }[]
  outcome: string
  stat: string
}

export const INDUSTRIES: Industry[] = [
  {
    slug: "manufacturing",
    name: "Manufacturing",
    icon: "🏭",
    pain: [
      "Complex shift rotations and overtime rules across multiple plants make manual scheduling error-prone and costly.",
      "Safety incidents and compliance audits require traceable training records and certification tracking.",
      "High turnover on the shop floor means weeks lost to fragmented onboarding and buddy-system knowledge transfer.",
    ],
    regulation: "OSHA · ISO 45001 · SOC 2",
    workflow: [
      { step: "Hire & Screen", detail: "Requisition → candidate pipeline → offer. Safety-sensitive roles flagged for background and certification checks." },
      { step: "Onboard & Certify", detail: "Day-one checklist assigns PPE, safety training, and machine-specific certifications with expiry tracking." },
      { step: "Schedule & Roster", detail: "Shift templates model 2/3-crew rotations, overtime rules, and rest-day constraints. Auto-generate rosters with conflict guard." },
      { step: "Time & Attendance", detail: "Clock in/out on kiosk or mobile, overtime auto-calculated, exceptions routed to supervisors." },
      { step: "Payroll & Comply", detail: "Hours flow to payroll, deductions and shift premiums applied, audit trail ready for OSHA and labour inspections." },
    ],
    outcome: "Design partner goal: 40% reduction in scheduling admin and zero certification lapses across a 1,200-person plant network.",
    stat: "40% less scheduling admin",
  },
  {
    slug: "healthcare",
    name: "Healthcare",
    icon: "🏥",
    pain: [
      "Clinicians working without a valid license or credential exposes the organisation to patient-safety and liability risk.",
      "Rostering around specialty coverage, on-call pools, and fatigue rules is a full-time job without automation.",
      "Fragmented time capture across wards and home visits creates payroll leakage and burnout blind spots.",
    ],
    regulation: "HIPAA · Joint Commission · State Boards",
    workflow: [
      { step: "Credential check", detail: "Every hire verified against license, DEA, and specialty board registries. Expiry alerts at 60/30/7 days; roster blocked if lapsed." },
      { step: "Roster with license guard", detail: "Scheduling engine respects scope-of-practice, fatigue rules, and coverage ratios. No shift assigned without a valid credential." },
      { step: "Time capture", detail: "Ward kiosk, mobile, and EHR-adjacent capture with break and on-call differentials. Geofenced for home-health visits." },
      { step: "Leave & coverage", detail: "PTO and FMLA requests show real-time coverage impact. Manager approves with one-click backfill from qualified float pool." },
      { step: "Payroll", detail: "Hours, differentials, and on-call pay flow to payroll with full audit trail for cost-centre and grant reporting." },
    ],
    outcome: "Target: onboarding from 12 days to 3 days for credentialed hires; zero shifts staffed with an expired license.",
    stat: "12 days → 3 days onboarding",
  },
  {
    slug: "retail",
    name: "Retail",
    icon: "🛍️",
    pain: [
      "Seasonal spikes demand hiring 3× headcount in weeks, then scaling down without losing top performers.",
      "Part-time availability, student schedules, and multi-location coverage make fair rostering a constant puzzle.",
      "High frontline turnover erodes service quality when onboarding is inconsistent across stores.",
    ],
    regulation: "FLSA · Predictive Scheduling Laws",
    workflow: [
      { step: "Seasonal hiring", detail: "Bulk requisitions, one-click offers, and templated onboarding checklists per store format." },
      { step: "Availability-driven rostering", detail: "Staff availability + demand forecast → optimised roster with fair-hours guardrails." },
      { step: "Shift swaps", detail: "Employee-initiated swaps with manager approval and eligibility checks." },
      { step: "Time & payroll", detail: "POS-integrated clock, break compliance, and weekly payroll ready for multi-location rollup." },
    ],
    outcome: "Target: fill seasonal roles 50% faster and cut no-shows by 25% with availability-aware scheduling.",
    stat: "50% faster seasonal hiring",
  },
  {
    slug: "financial-services",
    name: "Financial Services",
    icon: "🏦",
    pain: [
      "Regulatory scrutiny demands immutable audit trails for every HR decision and compensation change.",
      "Licensed roles (Series 7/63, CPA) require continuous credential and disclosure tracking.",
      "Compensation cycles must reconcile performance, risk adjustments, and deferrals without spreadsheet risk.",
    ],
    regulation: "SOX · FINRA · SOC 2",
    workflow: [
      { step: "Hire & vet", detail: "Background, fingerprint, and Form U4/U5 disclosure checks wired into the offer workflow." },
      { step: "Onboard & attest", detail: "Code-of-conduct and policy attestations tracked to completion with e-signature." },
      { step: "Performance & comp", detail: "Review cycles feed compensation bands with risk-adjusted bonus and deferral modelling." },
      { step: "Audit & reporting", detail: "Every record versioned; regulator-ready exports with who/what/when on every field." },
    ],
    outcome: "Target: audit preparation from 6 weeks to 5 days with tamper-evident HR records.",
    stat: "6 weeks → 5 days audit prep",
  },
  {
    slug: "technology",
    name: "Technology",
    icon: "💻",
    pain: [
      "Distributed teams across time zones make synchronous scheduling and leave coordination fragile.",
      "Billable vs. non-billable time is hard to attribute when engineers context-switch across projects.",
      "Talent retention hinges on growth paths that feel personal, not templated.",
    ],
    regulation: "GDPR · SOC 2 · ISO 27001",
    workflow: [
      { step: "Hire & onboard remote", detail: "Async offer, e-sign, and remote onboarding checklist with equipment and access provisioning." },
      { step: "Project time capture", detail: "Lightweight time entry mapped to projects and cost centres with approval routing." },
      { step: "Performance & growth", detail: "Continuous feedback, 360° reviews, and learning paths tied to role-based skill matrices." },
      { step: "Leave & async coverage", detail: "Team-aware PTO calendar with async handoff notes and auto-delegation." },
    ],
    outcome: "Target: 30% reduction in time-to-productivity for new engineers with structured remote onboarding.",
    stat: "30% faster ramp",
  },
  {
    slug: "logistics",
    name: "Logistics",
    icon: "🚚",
    pain: [
      "Driver scheduling must balance Hours-of-Service limits, route assignments, and last-mile surge windows.",
      "Overtime and per-diem calculations vary by lane, contract, and jurisdiction — spreadsheets break at scale.",
      "High churn among warehouse and driver roles inflates recruiting and safety-training costs.",
    ],
    regulation: "FMCSA (HOS) · DOT · OSHA",
    workflow: [
      { step: "Hire & certify drivers", detail: "CDL, medical card, and MVR checks with expiry guard that blocks dispatch if lapsed." },
      { step: "Demand-aware rostering", detail: "Forecast-driven shift generation respects HOS rest rules and equipment assignments." },
      { step: "Time & exceptions", detail: "ELD-adjacent time capture with overtime, per-diem, and detention pay auto-applied." },
      { step: "Payroll & compliance", detail: "Hours flow to payroll; HOS and DOT audit packs exported on demand." },
    ],
    outcome: "Target: cut overtime leakage by 18% and eliminate HOS scheduling violations.",
    stat: "18% less overtime leakage",
  },
  {
    slug: "education",
    name: "Education",
    icon: "🎓",
    pain: [
      "Academic calendars, term contracts, and adjunct pools don't fit a 9-to-5 HR model.",
      "Credential and background checks must clear before anyone steps into a classroom.",
      "Grant-funded positions need cost-centre attribution that survives headcount and budget reporting.",
    ],
    regulation: "FERPA · Title IX · State credentialing",
    workflow: [
      { step: "Hire & clear", detail: "Faculty and staff requisitions with credential, background, and reference workflows per role type." },
      { step: "Term-based onboarding", detail: "Semester-aligned checklists for course assignment, systems access, and compliance training." },
      { step: "Schedule & leave", detail: "Academic calendar-aware scheduling with sabbatical and term-break leave policies." },
      { step: "Payroll & grants", detail: "Term payroll with grant and department cost allocation and effort reporting." },
    ],
    outcome: "Target: onboarding for adjunct faculty from 4 weeks to 1 week with term-templated workflows.",
    stat: "4 weeks → 1 week adjunct onboarding",
  },
  {
    slug: "professional-services",
    name: "Professional Services",
    icon: "💼",
    pain: [
      "Utilisation and billable hours live in different tools, so staffing decisions lag reality.",
      "Project assignments compete for the same senior talent with no single view of capacity.",
      "Client-mandated compliance and disclosure checks vary by engagement and are easy to miss.",
    ],
    regulation: "SOC 2 · Client-specific NDAs",
    workflow: [
      { step: "Hire & bench", detail: "Requisitions tied to pipeline forecast; bench and utilisation tracked from day one." },
      { step: "Project staffing", detail: "Capacity-aware assignments with skills and availability matching across the portfolio." },
      { step: "Time & billing", detail: "Billable hours captured by project with approval and client-billing export." },
      { step: "Performance & growth", detail: "Engagement feedback feeds reviews and staffing for the next cycle." },
    ],
    outcome: "Target: lift billable utilisation by 12 points with a single view of capacity and assignments.",
    stat: "+12 pts utilisation",
  },
  {
    slug: "hospitality",
    name: "Hospitality",
    icon: "🏨",
    pain: [
      "No-shows and last-minute swaps ripple across front desk, housekeeping, and F&B with no buffer.",
      "Seasonal and event-driven demand means headcount can swing 40% month to month.",
      "Multi-property operations need consistent onboarding but locally tuned scheduling rules.",
    ],
    regulation: "FLSA · Local fair-workweek ordinances",
    workflow: [
      { step: "Rapid hiring", detail: "High-volume pipeline with SMS-friendly applications and same-day offer templates." },
      { step: "Event-aware rostering", detail: "Demand forecast from occupancy and events → roster with swap and stand-by pools." },
      { step: "Time & tips", detail: "Clock with tip and service-charge attribution; break compliance built in." },
      { step: "Cross-property reporting", detail: "Labour cost and coverage dashboards rolled up across properties." },
    ],
    outcome: "Target: 35% fewer uncovered shifts with event-aware rostering and stand-by pools.",
    stat: "35% fewer uncovered shifts",
  },
  {
    slug: "government",
    name: "Government",
    icon: "🏛️",
    pain: [
      "Hiring is governed by classification, grade, and competitive procedures that resist ad-hoc workarounds.",
      "Position control and budget authority must reconcile before any offer can be made.",
      "FOIA, records-retention, and audit requirements demand complete, immutable HR history.",
    ],
    regulation: "OPM · FISMA · State civil-service rules",
    workflow: [
      { step: "Requisition & classify", detail: "Position classified by grade, series, and authority with budget check before posting." },
      { step: "Competitive hire", detail: "Merit-based screening, veterans' preference, and structured interview tracking." },
      { step: "Onboard & attest", detail: "Oath, ethics, and systems-access checklists with records-retention tagging." },
      { step: "Lifecycle & audit", detail: "Every personnel action versioned and exportable for audit and FOIA response." },
    ],
    outcome: "Target: time-to-hire reduced by 25% with structured, audit-ready workflows still fully compliant.",
    stat: "25% faster time-to-hire",
  },
]
