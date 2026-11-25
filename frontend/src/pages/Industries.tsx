import { Link } from "react-router-dom"
import { PublicLayout } from "@/components/PublicLayout"

const INDUSTRIES = [
  { name: "Manufacturing", desc: "Shift scheduling, time tracking, and compliance for factory floors." },
  { name: "Healthcare", desc: "Credential tracking, shift rostering, and leave management for clinical staff." },
  { name: "Retail", desc: "Seasonal hiring, part-time scheduling, and multi-location management." },
  { name: "Financial Services", desc: "Compliance, audit trails, and secure employee data management." },
  { name: "Technology", desc: "Remote workforce, project time tracking, and talent management." },
  { name: "Logistics", desc: "Driver scheduling, overtime tracking, and workforce planning." },
  { name: "Education", desc: "Academic calendars, faculty scheduling, and staff management." },
  { name: "Professional Services", desc: "Billable hours, project assignments, and resource planning." },
  { name: "Hospitality", desc: "Shift swaps, seasonal staffing, and multi-site operations." },
  { name: "Government", desc: "Compliance, audit trails, and structured HR processes." },
]

export default function Industries() {
  return (
    <PublicLayout>
      <div className="max-w-4xl">
        <h1 className="mk-h1 text-fg mb-2">Industries</h1>
        <p className="text-body text-fg-muted mb-8">
          LibrePeople adapts to the unique workforce needs of every industry.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {INDUSTRIES.map((ind) => (
            <div key={ind.name} className="mk-card p-6">
              <h2 className="font-semibold text-fg text-[var(--font-size-lg)]">{ind.name}</h2>
              <p className="text-body-sm text-fg-muted mt-2">{ind.desc}</p>
            </div>
          ))}
        </div>
        <div className="mt-10 text-center">
          <Link to="/contact" className="mk-cta">Request a demo</Link>
        </div>
      </div>
    </PublicLayout>
  )
}
