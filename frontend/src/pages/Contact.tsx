import { useState, type FormEvent, useEffect } from "react"
import { useSearchParams, Link } from "react-router-dom"
import { PublicLayout } from "@/components/PublicLayout"
import { PageHero } from "@/components/marketing/PageHero"
import api from "@/lib/api"

export default function Contact() {
  const [searchParams] = useSearchParams()
  const interestParam = searchParams.get("interest") || searchParams.get("plan") || searchParams.get("industry") || ""

  const [form, setForm] = useState({ name: "", email: "", company: "", company_size: "", interest: interestParam, phone: "", message: "" })
  const [status, setStatus] = useState<"idle" | "submitting" | "sent" | "error">("idle")
  const [error, setError] = useState("")

  // Prefill interest from query (?interest= / ?plan= / ?industry=)
  useEffect(() => {
    if (interestParam) {
      setForm((prev) => ({ ...prev, interest: interestParam }))
    }
  }, [interestParam])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (status === "submitting") return
    setStatus("submitting")
    setError("")
    try {
      // Public endpoint — no token required. The marketing site has no auth.
      await api.post("/public/contact", {
        name: form.name,
        email: form.email,
        message: form.message,
        company: form.company || undefined,
        company_size: form.company_size || undefined,
        interest: form.interest || undefined,
        phone: form.phone || undefined,
      })
      setStatus("sent")
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "We couldn't send your message. Please check your connection and try again — your message has been kept."
      setError(detail)
      setStatus("error")
    }
  }

  return (
    <PublicLayout>
      <PageHero
        kicker="Contact"
        title="Talk to the founding team"
        intro="Have questions? We'd love to hear from you. Tell us about your team and what you're looking for."
        align="center"
      >
        <p className="text-sm text-fg-muted mt-4">
          We reply within <strong className="text-fg">1 business day</strong>. Or{" "}
          <a href="mailto:hello@karmathy.com" className="mk-link">
            email us directly at hello@karmathy.com
          </a>
          .
        </p>
      </PageHero>

      <div className="max-w-container mx-auto px-4 sm:px-6 lg:px-8 py-14 lg:py-20">
        <div className="max-w-2xl mk-card p-6 lg:p-8">
          {status === "sent" ? (
            <div className="mk-card mk-card-flat p-6 border border-[rgba(16,185,129,0.3)] bg-[rgba(16,185,129,0.1)]" role="status">
              <div>
                <p className="font-semibold text-fg">Thank you! Your message has been received.</p>
                <p className="text-sm text-fg-muted mt-1">We&apos;ll get back to you within 1 business day.</p>
                <p className="text-sm mt-3">
                  In a hurry? <Link to="/pricing" className="mk-link">See pricing</Link> or{" "}
                  <Link to="/docs" className="mk-link">browse the docs</Link>.
                </p>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4" noValidate={false}>
              {status === "error" && (
                <div className="mk-card mk-card-flat p-4 border border-[rgba(239,68,68,0.3)] bg-[rgba(239,68,68,0.1)]" role="alert">
                  <p className="text-fg">{error}</p>
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="contact-name" className="block text-sm font-medium text-fg-muted mb-1">
                    Name <span className="text-error-text" aria-hidden="true">*</span>
                  </label>
                  <input
                    id="contact-name"
                    name="name"
                    autoComplete="name"
                    className="input w-full"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    aria-required="true"
                    required
                  />
                </div>
                <div>
                  <label htmlFor="contact-email" className="block text-sm font-medium text-fg-muted mb-1">
                    Work email <span className="text-error-text" aria-hidden="true">*</span>
                  </label>
                  <input
                    id="contact-email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    className="input w-full"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                    aria-required="true"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="contact-company" className="block text-sm font-medium text-fg-muted mb-1">
                    Company
                  </label>
                  <input
                    id="contact-company"
                    name="company"
                    autoComplete="organization"
                    className="input w-full"
                    placeholder="Acme Inc."
                    value={form.company}
                    onChange={(e) => setForm({ ...form, company: e.target.value })}
                  />
                </div>
                <div>
                  <label htmlFor="contact-size" className="block text-sm font-medium text-fg-muted mb-1">
                    Company size
                  </label>
                  <select
                    id="contact-size"
                    className="input w-full"
                    value={form.company_size}
                    onChange={(e) => setForm({ ...form, company_size: e.target.value })}
                  >
                    <option value="">Select…</option>
                    <option value="1-50">1–50 employees</option>
                    <option value="51-200">51–200 employees</option>
                    <option value="201-1000">201–1 000 employees</option>
                    <option value="1000+">1 000+ employees</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="contact-interest" className="block text-sm font-medium text-fg-muted mb-1">
                    What can we help with?
                  </label>
                  <select
                    id="contact-interest"
                    className="input w-full"
                    value={form.interest}
                    onChange={(e) => setForm({ ...form, interest: e.target.value })}
                  >
                    <option value="">Select…</option>
                    <option value="demo">Request a demo</option>
                    <option value="pricing">Pricing question</option>
                    <option value="migration">Migration / switch</option>
                    <option value="hiring">Hiring & recruiting</option>
                    <option value="payroll">Payroll</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="contact-phone" className="block text-sm font-medium text-fg-muted mb-1">
                    Phone <span className="text-fg-subtle text-xs">(optional)</span>
                  </label>
                  <input
                    id="contact-phone"
                    name="phone"
                    type="tel"
                    autoComplete="tel"
                    className="input w-full"
                    placeholder="+1 …"
                    value={form.phone}
                    onChange={(e) => setForm({ ...form, phone: e.target.value })}
                  />
                </div>
              </div>

              <div>
                <label htmlFor="contact-message" className="block text-sm font-medium text-fg-muted mb-1">
                  Message <span className="text-error-text" aria-hidden="true">*</span>
                </label>
                <textarea
                  id="contact-message"
                  name="message"
                  rows={4}
                  className="input w-full"
                  placeholder="Tell us about your team, current tools and what you need…"
                  value={form.message}
                  onChange={(e) => setForm({ ...form, message: e.target.value })}
                  aria-required="true"
                  required
                />
              </div>

              <button className="mk-cta w-full" type="submit" disabled={status === "submitting"}>
                {status === "submitting" ? "Sending…" : "Send message"}
              </button>
              <p className="text-xs text-fg-muted">
                By sending, you agree to our <Link to="/privacy" className="mk-link">Privacy</Link> and{" "}
                <Link to="/terms" className="mk-link">Terms</Link>.
              </p>
            </form>
          )}
        </div>
      </div>
    </PublicLayout>
  )
}
