import { Link } from "react-router-dom"
import { PublicLayout } from "@/components/PublicLayout"
import { PageHero } from "@/components/marketing/PageHero"
import { INDUSTRIES } from "@/lib/industries"

export default function Industries() {
  return (
    <PublicLayout>
      {/* Hero */}
      <PageHero
        kicker="HR, tailored to your industry"
        title="Built for every industry"
        intro="From factory floors to hospital wards — one platform, tailored to your world."
      />

      {/* Card grid */}
      <section className="max-w-container mx-auto px-4 sm:px-6 lg:px-8 pb-12">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {INDUSTRIES.map((ind) => (
            <div key={ind.slug} className="mk-card p-6 flex flex-col">
              <div className="flex items-start gap-3">
                <span className="icon-tile icon-tile-brand shrink-0" aria-hidden="true">
                  {ind.icon}
                </span>
                <div className="min-w-0">
                  <h2 className="font-semibold text-fg text-lg leading-tight">{ind.name}</h2>
                  <p className="text-body-sm text-fg-muted mt-1.5 line-clamp-2">{ind.pain[0]}</p>
                </div>
              </div>
              <div className="mt-4">
                <Link
                  to={`/industries/${ind.slug}`}
                  className="action-link inline-flex items-center gap-1.5"
                >
                  Explore <span aria-hidden="true">→</span>
                </Link>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-10 text-center">
          <p className="text-body-sm text-fg-muted">
            Not sure where you fit?{" "}
            <Link to="/contact" className="action-link">
              Talk to us <span aria-hidden="true">→</span>
            </Link>
          </p>
        </div>
      </section>
    </PublicLayout>
  )
}
