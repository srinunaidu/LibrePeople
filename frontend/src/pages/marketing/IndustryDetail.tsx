import { Link, useParams } from "react-router-dom"
import { useState } from "react"
import { PublicLayout } from "@/components/PublicLayout"
import { INDUSTRIES } from "@/lib/industries"
import { Button } from "@/components/ui"

const RICH_SLUGS = new Set(["healthcare", "manufacturing"])

export default function IndustryDetail() {
  const { slug } = useParams<{ slug: string }>()
  const industry = INDUSTRIES.find((i) => i.slug === slug)
  const [email, setEmail] = useState("")
  const [submitted, setSubmitted] = useState(false)

  if (!industry) {
    return (
      <PublicLayout>
        <div className="max-w-container mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center">
          <h1 className="text-h1 font-bold text-fg">Industry not found</h1>
          <p className="text-body text-fg-muted mt-3">
            We couldn&apos;t find that industry.
          </p>
          <Link to="/industries" className="btn btn-primary mt-6">
            Explore all industries →
          </Link>
        </div>
      </PublicLayout>
    )
  }

  const isRich = RICH_SLUGS.has(industry.slug)

  return (
    <PublicLayout>
      {/* Hero */}
      <section className="relative overflow-hidden border-b border-white/[0.06]">
        <div
          aria-hidden="true"
          className="absolute inset-0"
          style={{
            backgroundImage:
              "radial-gradient(760px 340px at 12% -20%, rgba(37,99,235,0.30), transparent 62%), radial-gradient(600px 300px at 90% -30%, rgba(34,211,238,0.12), transparent 60%)",
          }}
        />
        <div aria-hidden="true" className="mk-grid absolute inset-0" />
        <div className="relative max-w-container mx-auto px-4 sm:px-6 lg:px-8 pt-14 pb-12">
        <nav aria-label="Breadcrumb" className="breadcrumb">
          <Link to="/industries">Industries</Link>
          <span aria-hidden="true">/</span>
          <span aria-current="page">{industry.name}</span>
        </nav>
        <div className="flex items-center gap-4 mt-2">
          <span className="icon-tile icon-tile-brand text-2xl w-12 h-12" aria-hidden="true">
            {industry.icon}
          </span>
          <div>
            <h1 className="text-h1 font-bold text-fg">{industry.name}</h1>
            <p className="text-body text-fg-muted mt-1 max-w-2xl">{industry.pain[0]}</p>
          </div>
        </div>
        </div>
      </section>

      {/* Coming soon banner for non-rich industries */}
      {!isRich && (
        <section className="max-w-container mx-auto px-4 sm:px-6 lg:px-8 pb-6">
          <div className="alert alert-info">
            <div>
              <p className="font-semibold">Coming soon — this playbook is being refined with design partners.</p>
              <p className="text-sm mt-1">
                The overview below is live. For the full tailored rollout,{" "}
                <Link to={`/contact?industry=${industry.slug}`} className="action-link">
                  talk to us →
                </Link>
              </p>
              <form
                className="mt-3 flex flex-wrap gap-2"
                onSubmit={(e) => {
                  e.preventDefault()
                  if (email.trim()) setSubmitted(true)
                }}
              >
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Work email"
                  className="input max-w-xs"
                  aria-label="Work email for early access"
                />
                <Button variant="primary" type="submit">
                  Get early access
                </Button>
              </form>
              {submitted && (
                <p className="text-sm mt-2 text-success-text">Thanks — we&apos;ll be in touch.</p>
              )}
            </div>
          </div>
        </section>
      )}

      {/* Pain */}
      <section className="max-w-container mx-auto px-4 sm:px-6 lg:px-8 pb-8">
        <div className="card p-6">
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <h2 className="text-h2 font-semibold text-fg">Why {industry.name} is different</h2>
            <span className="badge badge-slate">{industry.regulation}</span>
          </div>
          <ul className="space-y-3 text-body-sm text-fg-muted">
            {industry.pain.map((p) => (
              <li key={p} className="flex gap-2">
                <span className="text-brand-600 mt-0.5 shrink-0" aria-hidden="true">
                  •
                </span>
                <span>{p}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Workflow */}
      <section className="max-w-container mx-auto px-4 sm:px-6 lg:px-8 pb-8">
        <h2 className="text-h2 font-semibold text-fg mb-4">LibrePeople workflow</h2>
        <div className="flex flex-col gap-3">
          {industry.workflow.map((w, idx) => (
            <div key={w.step} className="flex gap-3">
              <div className="flex flex-col items-center">
                <span className="w-8 h-8 rounded-full bg-brand-600 text-white flex items-center justify-center text-sm font-semibold shrink-0">
                  {idx + 1}
                </span>
                {idx < industry.workflow.length - 1 && (
                  <span className="w-px flex-1 bg-border-default mt-1 min-h-[12px]" aria-hidden="true" />
                )}
              </div>
              <div className="card p-4 flex-1 mb-1">
                <h3 className="font-semibold text-fg text-sm">{w.step}</h3>
                <p className="text-body-sm text-fg-muted mt-1">{w.detail}</p>
              </div>
              {idx < industry.workflow.length - 1 && (
                <span className="hidden sm:flex items-center text-fg-subtle" aria-hidden="true">
                  ↓
                </span>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Outcome */}
      <section className="max-w-container mx-auto px-4 sm:px-6 lg:px-8 pb-8">
        <div className="card p-6">
          <p className="text-xs font-semibold tracking-wider uppercase text-fg-subtle">Outcome</p>
          <p className="stat-value mt-2">{industry.stat}</p>
          <p className="text-body-sm text-fg-muted mt-2">{industry.outcome}</p>
          {isRich && (
            <blockquote className="mt-4 border-l-4 border-brand-200 pl-4 text-body-sm text-fg-muted italic">
              &ldquo;The first HR platform where the compliance chain does not need a human bridge — credential, roster, time and payroll hold each other.&rdquo;
            </blockquote>
          )}
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-container mx-auto px-4 sm:px-6 lg:px-8 pb-12">
        <div className="card p-6 text-center bg-page">
          <h2 className="text-h2 font-semibold text-fg">Ready to see it for {industry.name}?</h2>
          <Link to={`/contact?industry=${industry.slug}`} className="btn btn-primary mt-4">
            Talk to us about {industry.name} →
          </Link>
        </div>
      </section>
    </PublicLayout>
  )
}
