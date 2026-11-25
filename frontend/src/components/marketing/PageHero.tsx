/**
 * PageHero + PageBody — the standard top band and container rhythm for every
 * marketing page, matching the ModulePage shell so the whole site reads as
 * one design. (360 redesign: aurora band, eyebrow kicker, display title.)
 */
import type { ReactNode } from "react"

export function PageHero({
  kicker,
  title,
  intro,
  align = "left",
  children,
}: {
  kicker: string
  title: ReactNode
  intro?: ReactNode
  align?: "left" | "center"
  children?: ReactNode
}) {
  const centered = align === "center"
  return (
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
      <div
        className={`relative max-w-container mx-auto px-4 sm:px-6 lg:px-8 pt-14 pb-12 ${
          centered ? "text-center" : ""
        }`}
      >
        <div className={centered ? "mx-auto max-w-3xl" : "max-w-3xl"}>
          <p className={`mk-eyebrow w-fit ${centered ? "mx-auto" : ""}`}>{kicker}</p>
          <h1 className="mt-6 mk-h2 md:!text-[clamp(2.2rem,4.6vw,3.4rem)] text-white">{title}</h1>
          {intro && <p className={`text-body text-fg-muted max-w-2xl mt-4 ${centered ? "mx-auto" : ""}`}>{intro}</p>}
          {children}
        </div>
      </div>
    </section>
  )
}

export function PageBody({ children, narrow = false }: { children: ReactNode; narrow?: boolean }) {
  return (
    <section className="max-w-container mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-20">
      <div className={narrow ? "max-w-3xl" : ""}>{children}</div>
    </section>
  )
}
