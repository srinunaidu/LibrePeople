import { PublicLayout } from "@/components/PublicLayout"
import { PageHero, PageBody } from "@/components/marketing/PageHero"

const SECTIONS: { h: string; p: string }[] = [
  {
    h: "Data we collect",
    p: "We collect information you provide directly: account credentials, employee records, and usage data necessary to operate the platform.",
  },
  {
    h: "How we use data",
    p: "Data is used solely to provide and improve the LibrePeople service, process payroll, manage leave, and generate reports for your organization.",
  },
  {
    h: "Data security",
    p: "All data is encrypted in transit (TLS) and at rest. Oracle Autonomous Database provides enterprise-grade security with mTLS.",
  },
]

export default function Privacy() {
  return (
    <PublicLayout>
      <PageHero
        kicker="Legal · Privacy"
        title="Privacy Policy"
        intro="LibrePeople is committed to protecting the privacy of your personal data. This policy describes how we collect, use, and safeguard your information."
      />

      <PageBody narrow>
        <div className="mk-card mk-card-flat p-6 lg:p-8">
          <p className="mk-kicker">Policy sections</p>
          <div className="mt-6 space-y-8">
            {SECTIONS.map((s, i) => (
              <div key={s.h} className={`mk-reveal ${i > 0 ? "pt-6 border-t border-white/[0.06]" : ""}`}>
                <h2 className="text-[var(--font-size-lg)] font-semibold text-fg tracking-tight">{s.h}</h2>
                <p className="text-body text-fg-muted mt-2 leading-relaxed">{s.p}</p>
              </div>
            ))}
            <div className="pt-6 border-t border-white/[0.06] mk-reveal">
              <h2 className="text-[var(--font-size-lg)] font-semibold text-fg tracking-tight">Contact</h2>
              <p className="text-body text-fg-muted mt-2 leading-relaxed">
                For privacy questions, contact us via the Contact page.
              </p>
            </div>
          </div>
        </div>
      </PageBody>
    </PublicLayout>
  )
}
