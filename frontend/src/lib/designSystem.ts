/**
 * Karmathy design system — "The Thread" (Phase T).
 *
 * The single design concept for the marketing website: one continuous
 * record for every employee, from first application to last day. The
 * lifecycle stages are the nodes of one blue thread:
 *
 *   Recruit → Onboard → Time → Leave → Pay → Perform → Grow → Offboard
 *
 * This file is the source of truth for the numbers the Thread and the
 * pages are built against (DEC-033 design batch — Phase T):
 *   - colour tokens (primary/ink/muted/line/background/success/warning)
 *   - type scale (H1 56/32 · H2 36/26 · H3 22 · body 18/17, line-height 1.6)
 *   - spacing scale (8px base · 96px section desktop · 64px mobile)
 *   - radii (cards/buttons 12px) and the 1px-border-over-shadow rule
 */

export interface ThreadStage {
  /** Stable lifecycle slug — also the module-ish key for deep links. */
  id: string
  /** Visible label under the node. Carries the meaning; never decorative. */
  label: string
  /** Marks a terminal node that is absent (used by the broken-thread 404). */
  missing?: boolean
}

export const THREAD_STAGES: ThreadStage[] = [
  { id: "recruit", label: "Recruit" },
  { id: "onboard", label: "Onboard" },
  { id: "time", label: "Time" },
  { id: "leave", label: "Leave" },
  { id: "pay", label: "Pay" },
  { id: "perform", label: "Perform" },
  { id: "grow", label: "Grow" },
  { id: "offboard", label: "Offboard" },
]

export const DESIGN_SYSTEM = {
  colors: {
    primary: "#2563EB", // the thread, primary CTAs, active states
    ink: "#0F172A", // headings
    muted: "#64748B", // body secondary text
    line: "#E2E8F0", // dividers
    background: "#FFFFFF",
    success: "#16A34A", // status only — never decoration
    warning: "#D97706", // status only — never decoration
  },
  typeScale: {
    h1: { desktop: 56, mobile: 32, lineHeight: 1.05 },
    h2: { desktop: 36, mobile: 26, lineHeight: 1.2 },
    h3: { desktop: 22, mobile: 22, lineHeight: 1.3 },
    body: { desktop: 18, mobile: 17, lineHeight: 1.6 },
    maxLineLengthCh: 70,
  },
  spacing: {
    base: 8, // 8px grid
    sectionDesktop: 96, // vertical padding per section, desktop
    sectionMobile: 64, // vertical padding per section, mobile
  },
  radius: {
    card: 12,
    button: 12,
  },
} as const
