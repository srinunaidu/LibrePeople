/**
 * ModulePage — the shared shell every lifecycle module page renders through.
 *
 * 360 restyle: aurora hero band with display type, gradient-border "ships
 * today" grid grounded in the feature catalog (refs shown as evidence chips,
 * not promises), an honest "in design" strip for capabilities deliberately
 * sequenced later, connect cards linking the actual prev/next lifecycle
 * stages, and a dark CTA band carrying the ThreadDark artwork.
 *
 * Honesty rule: anything listed under `inDesign` is phrased as scheduled
 * work — never as a capability the product already has.
 */
import { Link } from "react-router-dom"
import { PublicLayout } from "@/components/PublicLayout"
import { ThreadCompact } from "@/components/marketing/Thread"
import { ThreadDark } from "@/components/marketing/Artwork"
import { THREAD_STAGES } from "@/lib/designSystem"

export interface ShipFeature {
  title: string
  desc: string
  icon: string
  /** Feature-catalog IDs backing this capability (evidence, not decoration). */
  refs?: string[]
  accent?: string
}

export interface DesignItem {
  text: string
  refs?: string[]
}

export interface ConnectCard {
  title: string
  desc: string
  to: string
  label: string
}

export interface MetaFact {
  label: string
  value: string
}

export function ModulePage({
  stageId,
  kicker,
  title,
  intro,
  facts,
  shipTitle = "What ships today",
  ships,
  inTitle = "Designed and sequenced — not promised",
  inDesign,
  connect,
  cta = "Book a demo",
}: {
  stageId?: string
  kicker: string
  title: string
  intro: string
  facts: MetaFact[]
  shipTitle?: string
  ships: ShipFeature[]
  inTitle?: string
  inDesign: DesignItem[]
  connect: ConnectCard[]
  cta?: string
}) {
  return (
    <PublicLayout>
      {/* ── Hero band ─────────────────────────────────────────────────── */}
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
          <p className="mk-eyebrow w-fit">{kicker}</p>
          <h1 className="mt-6 mk-h2 md:!text-[clamp(2.2rem,4.6vw,3.6rem)] text-white max-w-3xl">{title}</h1>
          <p className="text-body text-fg-muted max-w-2xl mt-4">{intro}</p>

          {/* fact strip */}
          <dl className="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-2xl">
            {facts.map((f) => (
              <div key={f.label} className="mk-card mk-card-flat px-4 py-3">
                <dt className="text-xs font-semibold tracking-widest uppercase text-fg-subtle">{f.label}</dt>
                <dd className="text-body-sm font-semibold text-white mt-1">{f.value}</dd>
              </div>
            ))}
          </dl>

          <div className="flex flex-wrap items-center justify-between gap-4 mt-10">
            <ThreadCompact stages={THREAD_STAGES} currentStageId={stageId} />
            <Link to="/contact" className="mk-cta !py-2.5 !px-5 text-sm shrink-0">
              {cta}
            </Link>
          </div>
        </div>
      </section>

      {/* ── Ships today ───────────────────────────────────────────────── */}
      <section className="max-w-container mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-20">
        <div className="flex flex-wrap items-end justify-between gap-4 mb-8 mk-reveal">
          <div className="max-w-2xl">
            <p className="mk-kicker">Live in the product</p>
            <h2 className="mt-2 mk-h2 text-white">{shipTitle}</h2>
          </div>
          <span className="badge badge-green dot">
            {ships.length} capabilities, evidence-checked
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {ships.map((f, i) => (
            <div key={f.title} className={`mk-card mk-reveal ${i % 3 === 1 ? "mk-reveal-d1" : i % 3 === 2 ? "mk-reveal-d2" : ""} p-5 flex flex-col`}>
              <div className="flex items-start justify-between gap-3">
                <span className={`icon-tile ${f.accent ?? "icon-tile-brand"} shrink-0`} aria-hidden="true">
                  <span className="text-sm font-bold">{f.icon}</span>
                </span>
                {f.refs && (
                  <span className="flex flex-wrap justify-end gap-1">
                    {f.refs.map((r) => (
                      <span
                        key={r}
                        className="rounded bg-page border border-border px-1.5 py-0.5 font-mono text-xs text-fg-subtle"
                      >
                        {r}
                      </span>
                    ))}
                  </span>
                )}
              </div>
              <h3 className="mt-3 font-semibold text-white text-base leading-tight">{f.title}</h3>
              <p className="text-body-sm text-fg-muted mt-1.5 leading-relaxed flex-1">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── In design — honest strip ──────────────────────────────────── */}
      <section className="relative border-y border-white/[0.06] bg-white/[0.015] py-14">
        <div
          aria-hidden="true"
          className="absolute inset-0"
          style={{
            backgroundImage: "radial-gradient(600px 240px at 8% 0%, rgba(217,119,6,0.08), transparent 60%)",
          }}
        />
        <div className="relative max-w-container mx-auto px-4 sm:px-6 lg:px-8">
          <p className="mk-kicker" style={{ color: "#fcd34d" }}>
            Roadmap, sequenced by the release gates
          </p>
          <h2 className="mt-2 mk-h2 text-white">{inTitle}</h2>
          <ul className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-3">
            {inDesign.map((d) => (
              <li key={d.text} className="flex items-start gap-2">
                <span className="mt-1.5 h-2 w-2 shrink-0 rounded-sm bg-[var(--semantic-status-warning)]" aria-hidden="true" />
                <span className="text-body-sm text-fg-muted">
                  {d.text}
                  {d.refs && <span className="ml-2 font-mono text-xs text-fg-subtle">{d.refs.join(" · ")}</span>}
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-6 text-xs text-fg-subtle">
            Sequencing is deliberate — every capability lands behind the release gates before the previous phase is
            declared done. Ask for the current sequence on a demo call, or read the security posture on{" "}
            <Link to="/security" className="mk-link text-sm">
              how we protect your data
            </Link>
            .
          </p>
        </div>
      </section>

      {/* ── Connect ───────────────────────────────────────────────────── */}
      <section className="max-w-container mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-20">
        <h2 className="mk-h2 text-white mb-8 mk-reveal">Where this sits in the thread</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {connect.map((c, i) => (
            <div key={c.title} className={`mk-card mk-reveal ${i === 1 ? "mk-reveal-d1" : i === 2 ? "mk-reveal-d2" : ""} p-6 flex flex-col`}>
              <h3 className="font-semibold text-white text-base leading-tight">{c.title}</h3>
              <p className="text-body-sm text-fg-muted mt-1.5 flex-1">{c.desc}</p>
              <Link to={c.to} className="mk-link mt-4">
                {c.label} <span aria-hidden="true">→</span>
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA band with artwork ─────────────────────────────────────── */}
      <section className="relative overflow-hidden border-t border-white/[0.06]">
        <ThreadDark className="absolute inset-0 h-full w-full" />
        <div
          aria-hidden="true"
          className="absolute inset-0"
          style={{
            backgroundImage:
              "radial-gradient(700px 320px at 50% 120%, rgba(37,99,235,0.35), transparent 65%), linear-gradient(transparent 40%, rgba(6,11,22,0.9) 92%)",
          }}
        />
        <div className="relative max-w-container mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center">
          <h2 className="mk-h2 text-white">
            See <span className="mk-gradient-blue">{title.split(" — ")[0].toLowerCase()}</span> running live
          </h2>
          <p className="mt-3 text-body-sm text-fg-muted max-w-xl mx-auto">
            A short, honest walkthrough — what is live today, what is sequenced next, and how the module fits your
            audit, payroll and scheduling reality.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link to="/contact" className="mk-cta">
              {cta}
            </Link>
            <Link to="/platform" className="mk-ghost">
              Explore the platform
            </Link>
          </div>
        </div>
      </section>
    </PublicLayout>
  )
}
