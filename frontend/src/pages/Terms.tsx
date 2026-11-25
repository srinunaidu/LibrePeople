import { PublicLayout } from "@/components/PublicLayout"
import { PageHero, PageBody } from "@/components/marketing/PageHero"

const SECTIONS: { h: string; p: string }[] = [
  {
    h: "Use of service",
    p: "Karmathy provides a cloud-based HCM platform. You are responsible for maintaining the confidentiality of your account credentials.",
  },
  {
    h: "Data ownership",
    p: "You retain ownership of all data you enter into Karmathy. We process your data solely to provide the service.",
  },
  {
    h: "Service availability",
    p: "We strive for high availability. Free-tier deployments may experience cold starts and spin-down during inactivity.",
  },
]

export default function Terms() {
  return (
    <PublicLayout>
      <PageHero
        kicker="Legal · Terms"
        title="Terms of Service"
        intro="By using Karmathy, you agree to these terms of service."
      />

      <PageBody narrow>
        <div className="mk-card mk-card-flat p-6 lg:p-8">
          <p className="mk-kicker">Terms sections</p>
          <div className="mt-6 space-y-8">
            {SECTIONS.map((s, i) => (
              <div key={s.h} className={`mk-reveal ${i > 0 ? "pt-6 border-t border-white/[0.06]" : ""}`}>
                <h2 className="text-[var(--font-size-lg)] font-semibold text-fg tracking-tight">{s.h}</h2>
                <p className="text-body text-fg-muted mt-2 leading-relaxed">{s.p}</p>
              </div>
            ))}
          </div>
        </div>
      </PageBody>
    </PublicLayout>
  )
}
