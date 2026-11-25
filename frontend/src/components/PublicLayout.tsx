import { Link, useLocation } from "react-router-dom"
import { useEffect } from "react"
import type { ReactNode } from "react"
import { usePageSEO } from "@/lib/seo"

const LINKS = [
  { to: "/platform", label: "Platform" },
  { to: "/solutions", label: "Solutions" },
  { to: "/industries", label: "Industries" },
  { to: "/resources", label: "Resources" },
  { to: "/about", label: "Company" },
]

const FOOTER = [
  {
    title: "Platform",
    links: [
      { to: "/platform", label: "Platform modules" },
      { to: "/solutions", label: "Solutions" },
      { to: "/resources", label: "Resources" },
    ],
  },
  {
    title: "Explore",
    links: [
      { to: "/industries", label: "Industries" },
      { to: "/docs", label: "Documentation" },
      { to: "/contact", label: "Contact us" },
    ],
  },
  {
    title: "Company",
    links: [
      { to: "/about", label: "About" },
      { to: "/careers", label: "Careers" },
      { to: "/privacy", label: "Privacy" },
      { to: "/terms", label: "Terms" },
    ],
  },
]

/**
 * Shell for unauthenticated marketing pages.
 *
 * Intentionally separate from the app Layout: signed-out visitors must not be
 * shown the product sidebar, account avatar or sign-out control, which are
 * meaningless (and misleading) before authentication.
 *
 * 360 redesign: the subtree runs on the scoped dark system (`mkt-root` in
 * marketing.css) — glass sticky nav, glow CTAs, and a footer with the giant
 * gradient wordmark. A tiny IntersectionObserver adds `.mk-in` to `.mk-reveal`
 * children as they enter the viewport.
 */
export function PublicLayout({ children }: { children: ReactNode }) {
  const { pathname } = useLocation()
  usePageSEO(pathname)

  // Reveal-on-scroll for `.mk-reveal` elements inside the current page.
  useEffect(() => {
    const els = Array.from(document.querySelectorAll<HTMLElement>(".mk-reveal"))
    if (els.length === 0) return
    if (!("IntersectionObserver" in window)) {
      els.forEach((el) => el.classList.add("mk-in"))
      return
    }
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            e.target.classList.add("mk-in")
            io.unobserve(e.target)
          }
        }
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" },
    )
    els.forEach((el) => io.observe(el))
    return () => io.disconnect()
  }, [])

  return (
    // The marketing pages run dark-first under the scoped mkt design system
    // (marketing.css). The application shell outside is untouched.
    <div className="min-h-screen bg-page light-surface mkt-root flex flex-col">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      <header className="mkt-nav">
        <div className="max-w-container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between gap-4">
            {/* brand mark */}
            <Link to="/" className="flex items-center gap-2.5 shrink-0 group">
              <span
                aria-hidden="true"
                className="grid h-8 w-8 place-items-center rounded-lg text-white font-bold text-sm"
                style={{
                  background: "linear-gradient(135deg, var(--brand-600) 0%, var(--teal-400) 100%)",
                  boxShadow: "0 2px 10px rgba(37,99,235,0.5), inset 0 1px 0 rgba(255,255,255,0.25)",
                }}
              >
                L
              </span>
              <span className="text-lg font-bold tracking-tight" style={{ fontFamily: "var(--font-display)" }}>
                <span className="mk-gradient-blue">LibrePeople</span>
              </span>
            </Link>

            <nav aria-label="Main" className="hidden lg:block">
              <ul className="flex items-center gap-6">
                {LINKS.map((l) => (
                  <li key={l.to}>
                    <Link to={l.to} className="mkt-nav-link">
                      {l.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>

            <div className="flex items-center gap-3 shrink-0">
              <Link to="/login" className="hidden sm:inline-block text-sm font-medium text-fg-muted hover:text-fg transition-colors">
                Sign in
              </Link>
              <Link to="/contact" className="mk-cta !py-2 !px-4 text-sm">
                Request a demo
              </Link>
            </div>
          </div>

          {/* Compact nav for small screens */}
          <nav aria-label="Main mobile" className="lg:hidden pb-3 -mx-1 overflow-x-auto">
            <ul className="flex items-center gap-5 whitespace-nowrap px-1">
              {LINKS.map((l) => (
                <li key={l.to}>
                  <Link to={l.to} className="mkt-nav-link">
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </header>

      <main id="main-content" tabIndex={-1} className="flex-1">
        {children}
      </main>

      {/* ── Footer — giant wordmark ─────────────────────────────────────── */}
      <footer className="relative overflow-hidden border-t border-white/10">
        <div
          aria-hidden="true"
          className="absolute inset-0"
          style={{
            backgroundImage:
              "radial-gradient(700px 300px at 15% 0%, rgba(37,99,235,0.14), transparent 60%), radial-gradient(600px 260px at 85% 100%, rgba(34,211,238,0.08), transparent 60%)",
          }}
        />
        <div className="relative max-w-container mx-auto px-4 sm:px-6 lg:px-8 pt-16 pb-10">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-10">
            <div className="col-span-2 md:col-span-1">
              <div className="flex items-center gap-2">
                <span
                  aria-hidden="true"
                  className="grid h-7 w-7 place-items-center rounded-lg text-white font-bold text-xs"
                  style={{ background: "linear-gradient(135deg, var(--brand-600) 0%, var(--teal-400) 100%)" }}
                >
                  L
                </span>
                <span className="font-bold" style={{ fontFamily: "var(--font-display)" }}>
                  LibrePeople
                </span>
              </div>
              <p className="mt-3 text-sm text-fg-muted">People. Potential. Progress.</p>
              <p className="mt-6 text-xs leading-relaxed text-fg-subtle">
                One record per person, an audit trail on every action, and payroll that shows its work.
              </p>
            </div>
            {FOOTER.map((col) => (
              <nav key={col.title} aria-label={col.title}>
                <h2 className="text-xs font-semibold tracking-widest uppercase text-fg-subtle mb-4">{col.title}</h2>
                <ul className="space-y-2.5 text-sm">
                  {col.links.map((l) => (
                    <li key={l.to}>
                      <Link to={l.to} className="text-fg-muted hover:text-fg transition-colors">
                        {l.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </nav>
            ))}
          </div>

          {/* giant wordmark */}
          <div aria-hidden="true" className="mk-wordmark mt-14 text-center">
            LibrePeople
          </div>

          <div className="mt-8 pt-6 border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-fg-subtle">
            <p>&copy; 2026 LibrePeople. All rights reserved.</p>
            <p>Controls operating today · certifications in progress · one record per person</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
