/**
 * Hand-drawn SVG artwork for the marketing site — the "high-end graphics"
 * layer. All decorative, `aria-hidden`, scales crisply at any DPI, adds zero
 * raster weight, and stays exactly on the house palette (navy #0B1220,
 * sapphire #2563EB, teal #22D3EE, violet #8B5CF6).
 *
 * Three motifs, drawn once:
 *   • ThreadDark  — lifecycle thread on navy (homepage / module CTA bands)
 *   • ThreadLight — the same thread on the light surface (platform band)
 *   • Network     — integration constellation (integrations band)
 */
import type { CSSProperties } from "react"

/* ------------------------------------------------------------------ */
/* ThreadDark — the lifecycle thread, glowing on navy                  */
/* ------------------------------------------------------------------ */
export function ThreadDark({ className, style }: { className?: string; style?: CSSProperties }) {
  return (
    <svg viewBox="0 0 1440 420" fill="none" className={className} style={style} preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <defs>
        <linearGradient id="td-thread" x1="0" y1="0" x2="1440" y2="0" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#2563EB" stopOpacity="0.15" />
          <stop offset="0.22" stopColor="#2563EB" />
          <stop offset="0.72" stopColor="#22D3EE" />
          <stop offset="1" stopColor="#8B5CF6" stopOpacity="0.4" />
        </linearGradient>
        <radialGradient id="td-glow-a" cx="0.16" cy="0.1" r="0.55">
          <stop offset="0" stopColor="#22D3EE" stopOpacity="0.28" />
          <stop offset="1" stopColor="#22D3EE" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="td-glow-b" cx="0.9" cy="0.2" r="0.6">
          <stop offset="0" stopColor="#2563EB" stopOpacity="0.4" />
          <stop offset="1" stopColor="#2563EB" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="td-glow-c" cx="0.5" cy="1.1" r="0.55">
          <stop offset="0" stopColor="#8B5CF6" stopOpacity="0.22" />
          <stop offset="1" stopColor="#8B5CF6" stopOpacity="0" />
        </radialGradient>
        <filter id="td-blur" x="-60%" y="-60%" width="220%" height="220%">
          <feGaussianBlur stdDeviation="7" />
        </filter>
      </defs>

      <rect width="1440" height="420" fill="transparent" />
      <rect width="1440" height="420" fill="url(#td-glow-a)" />
      <rect width="1440" height="420" fill="url(#td-glow-b)" />
      <rect width="1440" height="420" fill="url(#td-glow-c)" />

      {/* fine grid, masked to the thread's orbit */}
      <g opacity="0.06" stroke="#93C5FD" strokeWidth="1">
        {Array.from({ length: 25 }, (_, i) => (
          <line key={`v${i}`} x1={i * 60} y1="0" x2={i * 60} y2="420" />
        ))}
        {Array.from({ length: 7 }, (_, i) => (
          <line key={`h${i}`} x1="0" y1={i * 60} x2="1440" y2={i * 60} />
        ))}
      </g>

      {/* the thread */}
      <path
        d="M-40,300 C 180,180 320,330 520,240 S 760,120 940,200 S 1240,300 1500,170"
        stroke="url(#td-thread)"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      {/* glow echo */}
      <path
        d="M-40,300 C 180,180 320,330 520,240 S 760,120 940,200 S 1240,300 1500,170"
        stroke="#2563EB"
        strokeWidth="10"
        strokeLinecap="round"
        opacity="0.12"
        filter="url(#td-blur)"
      />

      {/* eight lifecycle nodes on the thread */}
      {[
        { x: 100, y: 248 },
        { x: 282, y: 244 }, // recruit
        { x: 452, y: 253 }, // onboard
        { x: 610, y: 214 }, // time
        { x: 772, y: 158 }, // leave
        { x: 940, y: 200 }, // pay
        { x: 1130, y: 242 }, // perform/grow
        { x: 1310, y: 214 }, // offboard
      ].map((n, i) => (
        <g key={i}>
          <circle cx={n.x} cy={n.y} r="14" fill="#2563EB" opacity="0.1" filter="url(#td-blur)" />
          <circle cx={n.x} cy={n.y} r="5" fill={i === 4 ? "#22D3EE" : "#93C5FD"} />
          <circle cx={n.x} cy={n.y} r="12" stroke={i === 4 ? "#22D3EE" : "#60A5FA"} strokeOpacity="0.5" strokeWidth="1.2" fill="none" />
        </g>
      ))}

      {/* bokeh particles */}
      {[
        { x: 210, y: 120, r: 3 }, { x: 380, y: 96, r: 2 }, { x: 700, y: 84, r: 2.5 },
        { x: 1040, y: 108, r: 3 }, { x: 1230, y: 140, r: 2 }, { x: 540, y: 330, r: 2 },
        { x: 880, y: 318, r: 2.5 }, { x: 1330, y: 320, r: 2 },
      ].map((p, i) => (
        <circle key={`p${i}`} cx={p.x} cy={p.y} r={p.r} fill="#93C5FD" opacity="0.35" />
      ))}
    </svg>
  )
}

/* ------------------------------------------------------------------ */
/* ThreadLight — airy thread on the light surface                      */
/* ------------------------------------------------------------------ */
export function ThreadLight({ className, style }: { className?: string; style?: CSSProperties }) {
  return (
    <svg viewBox="0 0 1440 320" fill="none" className={className} style={style} preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <defs>
        <linearGradient id="tl-thread" x1="0" y1="0" x2="1440" y2="0" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#2563EB" stopOpacity="0.25" />
          <stop offset="0.5" stopColor="#2563EB" />
          <stop offset="1" stopColor="#22D3EE" stopOpacity="0.55" />
        </linearGradient>
        <radialGradient id="tl-glow" cx="0.5" cy="0.4" r="0.7">
          <stop offset="0" stopColor="#2563EB" stopOpacity="0.10" />
          <stop offset="1" stopColor="#2563EB" stopOpacity="0" />
        </radialGradient>
        <filter id="tl-blur" x="-60%" y="-60%" width="220%" height="220%">
          <feGaussianBlur stdDeviation="6" />
        </filter>
      </defs>

      <rect width="1440" height="320" fill="url(#tl-glow)" />

      {/* ghost geometry */}
      <g opacity="0.35" stroke="#BFDBFE" strokeWidth="1" fill="none">
        <rect x="1150" y="48" width="86" height="86" rx="20" />
        <circle cx="1280" cy="112" r="44" />
        <rect x="70" y="120" width="60" height="60" rx="16" />
      </g>

      {/* thread */}
      <path d="M-30,210 C 240,110 420,250 660,180 S 980,90 1180,170 S 1360,190 1500,140"
        stroke="url(#tl-thread)" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M-30,210 C 240,110 420,250 660,180 S 980,90 1180,170 S 1360,190 1500,140"
        stroke="#2563EB" strokeWidth="9" strokeLinecap="round" opacity="0.08" filter="url(#tl-blur)" />

      {[
        { x: 120, y: 180 }, { x: 330, y: 168 }, { x: 530, y: 189 }, { x: 690, y: 171 },
        { x: 860, y: 132 }, { x: 1030, y: 141 }, { x: 1200, y: 165 }, { x: 1360, y: 168 },
      ].map((n, i) => (
        <g key={i}>
          <circle cx={n.x} cy={n.y} r="11" fill="#2563EB" opacity="0.08" filter="url(#tl-blur)" />
          <circle cx={n.x} cy={n.y} r="4.5" fill="#2563EB" />
          <circle cx={n.x} cy={n.y} r="10" stroke="#93C5FD" strokeOpacity="0.8" strokeWidth="1.2" fill="none" />
        </g>
      ))}
    </svg>
  )
}

/* ------------------------------------------------------------------ */
/* Network — integration constellation on navy                         */
/* ------------------------------------------------------------------ */
export function Network({ className, style }: { className?: string; style?: CSSProperties }) {
  const nodes: { x: number; y: number; c: string }[] = [
    { x: 140, y: 300, c: "#60A5FA" }, { x: 320, y: 160, c: "#22D3EE" }, { x: 520, y: 280, c: "#93C5FD" },
    { x: 700, y: 130, c: "#2563EB" }, { x: 880, y: 260, c: "#8B5CF6" }, { x: 1060, y: 150, c: "#60A5FA" },
    { x: 1230, y: 290, c: "#22D3EE" },
  ]
  return (
    <svg viewBox="0 0 1360 400" fill="none" className={className} style={style} preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <defs>
        <radialGradient id="nw-glow" cx="0.45" cy="0.35" r="0.65">
          <stop offset="0" stopColor="#2563EB" stopOpacity="0.18" />
          <stop offset="1" stopColor="#2563EB" stopOpacity="0" />
        </radialGradient>
        <filter id="nw-blur" x="-60%" y="-60%" width="220%" height="220%">
          <feGaussianBlur stdDeviation="5" />
        </filter>
      </defs>
      <rect width="1360" height="400" fill="url(#nw-glow)" />

      <g stroke="#2563EB" strokeOpacity="0.4" strokeWidth="1.5">
        {nodes.map((n, i) => {
          const next = nodes[(i + 1) % nodes.length]
          return <path key={`e${i}`} d={`M${n.x},${n.y} Q ${(n.x + next.x) / 2},${(n.y + next.y) / 2 - 70} ${next.x},${next.y}`} fill="none" />
        })}
        <path d="M140,300 L 700,130 M520,280 L 1230,290" strokeOpacity="0.2" />
      </g>

      {nodes.map((n, i) => (
        <g key={`n${i}`}>
          <circle cx={n.x} cy={n.y} r="16" fill={n.c} opacity="0.15" filter="url(#nw-blur)" />
          <circle cx={n.x} cy={n.y} r="6" fill={n.c} />
          <circle cx={n.x} cy={n.y} r="13" stroke={n.c} strokeOpacity="0.55" strokeWidth="1.2" fill="none" />
        </g>
      ))}

      {/* data-flow particles */}
      {[
        { x: 240, y: 240, r: 2.5 }, { x: 430, y: 205, r: 2 }, { x: 610, y: 218, r: 2.5 },
        { x: 800, y: 172, r: 2 }, { x: 985, y: 232, r: 2.5 }, { x: 1150, y: 205, r: 2 },
      ].map((p, i) => (
        <circle key={`p${i}`} cx={p.x} cy={p.y} r={p.r} fill="#93C5FD" opacity="0.5" />
      ))}

      {/* faint grid */}
      <g opacity="0.05" stroke="#93C5FD" strokeWidth="1">
        {Array.from({ length: 23 }, (_, i) => (
          <line key={`v${i}`} x1={i * 60} y1="0" x2={i * 60} y2="400" />
        ))}
      </g>
    </svg>
  )
}
