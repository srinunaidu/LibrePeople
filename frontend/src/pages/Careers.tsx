import { Link } from "react-router-dom"
import { PublicLayout } from "@/components/PublicLayout"
import { PageHero, PageBody } from "@/components/marketing/PageHero"

const JOBS: { title: string; dept: string; location: string; accent: string }[] = [
  { title: "Senior Backend Engineer", dept: "Engineering", location: "Hyderabad", accent: "icon-tile-brand" },
  { title: "Frontend Engineer", dept: "Engineering", location: "Remote", accent: "icon-tile-teal" },
  { title: "Product Designer", dept: "Design", location: "Hyderabad", accent: "icon-tile-violet" },
  { title: "HR Business Partner", dept: "People", location: "Hyderabad", accent: "icon-tile-green" },
]

export default function Careers() {
  return (
    <PublicLayout>
      <PageHero
        kicker="Careers"
        title="Build the platform people run on"
        intro="Join us in building the future of workforce management."
      />

      <PageBody narrow>
        <p className="mk-kicker mk-reveal">Open positions</p>
        <div className="mt-5 space-y-4">
          {JOBS.map((j, i) => (
            <div key={j.title} className={`mk-card mk-reveal ${i % 2 === 1 ? "mk-reveal-d1" : ""} p-5 flex flex-wrap items-center gap-4`}>
              <span className={`icon-tile ${j.accent}`} aria-hidden="true">
                <span className="text-sm font-bold">⬢</span>
              </span>
              <div className="min-w-0">
                <h2 className="font-semibold text-fg">{j.title}</h2>
                <p className="text-sm text-fg-muted mt-0.5">
                  <span className="badge badge-slate">{j.dept}</span>{" "}
                  <span className="badge badge-slate">{j.location}</span>
                </p>
              </div>
              <Link to="/contact" className="mk-ghost !py-2 !px-4 text-sm sm:ml-auto shrink-0">
                Apply
              </Link>
            </div>
          ))}
        </div>

        <div className="mt-10 mk-card mk-reveal p-6 flex flex-col sm:flex-row sm:items-center gap-5">
          <div>
            <p className="font-semibold text-fg">Don&apos;t see your role?</p>
            <p className="text-body-sm text-fg-muted mt-1">We hire people, not job descriptions — tell us what you do best.</p>
          </div>
          <Link to="/contact" className="mk-cta !py-2.5 !px-5 text-sm sm:ml-auto shrink-0">
            Contact us
          </Link>
        </div>
      </PageBody>
    </PublicLayout>
  )
}
