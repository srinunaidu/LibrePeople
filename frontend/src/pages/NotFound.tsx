import { Link } from "react-router-dom"
import { PublicLayout } from "@/components/PublicLayout"
import { ThreadHero } from "@/components/marketing/Thread"
import { THREAD_STAGES } from "@/lib/designSystem"

/**
 * 404 — the broken thread.
 *
 * Phase T: the lifecycle thread visibly stops at a missing node. The page
 * links back to the home page and onward to the modules so the visitor can
 * find the node they were actually looking for.
 */
const BROKEN_STAGES = THREAD_STAGES.map((stage) =>
  stage.id === "offboard" ? { ...stage, missing: true } : stage,
)

export default function NotFound() {
  return (
    <PublicLayout>
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
        <div className="relative max-w-container mx-auto px-4 sm:px-6 lg:px-8 pt-16 pb-16 md:pt-24 md:pb-20 text-center">
          <p className="mk-eyebrow w-fit mx-auto">Error 404 — lost node</p>

          <h1 className="mt-6 mk-h2 md:!text-[clamp(2.2rem,4.6vw,3.4rem)] text-white">This page isn’t on the thread</h1>

          <p className="text-body text-fg-muted mt-3 max-w-2xl mx-auto">
            The Karmathy thread runs from a first application to a last day — Recruit, Onboard, Time,
            Leave, Pay, Perform, Grow, Offboard. The address you followed doesn’t match a node on the
            lifecycle path, so the record can’t continue here.
          </p>

          <div className="mt-12">
            <ThreadHero stages={BROKEN_STAGES} broken className="max-w-3xl mx-auto" />
          </div>

          <p className="mt-6 text-body-sm text-fg-muted">
            The thread visibly stops at a missing node — the lifecycle resumes at the last known stage.
          </p>

          <div className="mt-10 flex flex-wrap gap-3 justify-center">
            <Link to="/" className="mk-cta">
              Back to home
            </Link>
            <Link to="/contact" className="mk-ghost">
              Book a demo
            </Link>
          </div>
        </div>
      </section>
    </PublicLayout>
  )
}
