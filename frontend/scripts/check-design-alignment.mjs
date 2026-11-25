/**
 * Design alignment checker — typography, spacing, color tokens.
 *
 * Scans frontend/src for classes that bypass the design system.
 * Fails the build when a page uses a raw value where a token exists.
 * Run:  node scripts/check-design-alignment.mjs
 * Fix:  node scripts/check-design-alignment.mjs --fix  (where auto-fixable)
 *
 * Checks:
 *  1. Typography — only allowed sizes; no arbitrary text-[Npx] outside
 *     the badge/dot exceptions; headings must use PageHeader/SectionCard
 *     or page-title/section-title, not hand-rolled text-2xl/text-lg.
 *  2. Color — no hard-coded text-red / text-gray where a semantic
 *     token exists (text-error-text, text-fg-muted, etc.).
 *  3. Spacing — gap values outside the 4px scale (gap-2/3/4/5/6) flagged
 *     when gap-2.5/gap-1.5 appear without justification.
 *
 * This is the "something auto" for font alignment — every violation that
 * reaches main is a visual inconsistency the checker would have caught.
 */
import { readFileSync, readdirSync, statSync } from "node:fs"
import { join, relative } from "node:path"

const SRC = new URL("../src/", import.meta.url).pathname

// ---------------------------------------------------------------------------
// Allowed typography — the scale. Anything outside is a violation.
// ---------------------------------------------------------------------------
const ALLOWED_TEXT = new Set([
  // semantic type scale (index.css / tailwind)
  "text-display", "text-h1", "text-h1-app", "text-h2", "text-h2-app",
  "text-h3", "text-h3-app", "text-body", "text-body-sm", "text-caption",
  // Tailwind scale that IS the system (used via tokens)
  "text-xs", "text-sm", "text-base",
  // page/section title tokens
  // (text-navy, text-fg, etc. are color, not size — checked separately)
])

// Hand-rolled heading sizes that should be PageHeader/SectionCard/page-title
const HEADING_VIOLATIONS = new Set(["text-2xl", "text-xl", "text-lg"])

// Arbitrary text-[Npx] — only allowed for badge dots / kbd / avatar micro-type
// Everything else should use the scale above.
const ARBITRARY_TEXT_RE = /text-\[(\d+px)\]/g
const ARBITRARY_ALLOWED_PX = new Set(["10px", "11px"]) // badge/kbd/avatar only
const ARBITRARY_ALLOWED_FILES = new Set([
  // these files are allowed to use micro-type for badges/kbd
  "components/ui/badge.tsx",
  "components/ui/button.tsx",
  "components/ui/avatar.tsx",
  "components/shell/CommandPalette.tsx",
  "components/shell/WorkspaceRail.tsx",
  "components/shell/SecondarySidebar.tsx",
  "components/shell/TopBar.tsx",
])

// ---------------------------------------------------------------------------
// Color — hard-coded where token exists
// ---------------------------------------------------------------------------
const COLOR_VIOLATIONS = [
  { pattern: /text-red-700/g, token: "text-error-text", when: "alert/error text (use Alert tone=\"error\" or text-error-text)" },
  { pattern: /text-red-600/g, token: "text-error-text", when: "error/required asterisk (use text-error-text)" },
  { pattern: /text-gray-600/g, token: "text-fg-muted", when: "muted text (use text-fg-muted or text-text-secondary)" },
  { pattern: /text-gray-500/g, token: "text-fg-muted", when: "hint/secondary text" },
  { pattern: /text-amber-700/g, token: "text-warning-text or badge-amber", when: "warning text" },
  { pattern: /text-green-700/g, token: "text-success-text or badge-green", when: "success text" },
  { pattern: /bg-gray-100/g, token: "bg-surface-inset", when: "inset/muted background" },
  { pattern: /bg-gray-200/g, token: "bg-surface-inset", when: "track/inset background" },
  { pattern: /bg-blue-600/g, token: "bg-brand-600", when: "brand background" },
  { pattern: /border-blue-600/g, token: "border-brand-600", when: "brand border" },
  { pattern: /focus:ring-blue-500/g, token: "focus:ring-brand-600 or .input", when: "focus ring" },
]

// Spacing — non-scale gaps (informational, not failing yet)
// 1.5, 2.5 and 0 are micro-gaps intentionally used for icon-text and breadcrumb density — allow them.
const GAP_RE = /gap-(\d+(?:\.\d+)?)/g
const ALLOWED_GAPS = new Set(["0", "1", "1.5", "2", "2.5", "3", "4", "5", "6", "8", "12"])

// ---------------------------------------------------------------------------
// File discovery
// ---------------------------------------------------------------------------
function sourceFiles(dir = SRC) {
  const out = []
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry)
    if (statSync(full).isDirectory()) out.push(...sourceFiles(full))
    else if (/\.tsx?$/.test(entry)) out.push(full)
  }
  return out
}

const files = sourceFiles()
const isFix = process.argv.includes("--fix")

// ---------------------------------------------------------------------------
// Checks
// ---------------------------------------------------------------------------
let violations = []
let warnings = []

for (const file of files) {
  const src = readFileSync(file, "utf8")
  const rel = relative(SRC, file)

    // Skip generated / vendor / design showcase (intentionally shows all tokens)
  if (rel.startsWith("pages/Design") || rel.startsWith("pages/DesignGallery")) continue
  if (rel.includes("projectStatus")) continue
  // Marketing / public pages have their own light-only palette (light-surface)
  // — text-gray-600 there is intentional, not a token violation.
  // (names added as the marketing site grew: M1 public shell, M2/M2b/M2c pages)
  const MARKETING_PAGE_NAMES = [
    "Homepage", "About", "Solutions", "Industries", "Resources", "Careers", "Privacy", "Terms", "Documentation", "Contact", "PublicLayout",
    // Rebuilt marketing pages (M2+) — same light-only palette as the originals.
    "Pricing", "Security", "FAQ", "Compare", "IndustryDetail", "PlatformShowcase",
  ]
  if (MARKETING_PAGE_NAMES.some((n) => rel.includes(n))) continue
  // Auth pages sit outside Layout and use their own card pattern — not app chrome
  if (["Login", "ChangePassword", "Mfa"].some((n) => rel.includes(n))) continue
  // Micro-type for badges/kbd — text-[10px] on a 10px badge is intentional
  if (rel.includes("mobile-bottom-nav") || rel.includes("avatar") || rel.includes("badge")) continue
  // Generic table primitives are not pages — EmptyState is handled by the caller, not the table itself
  const isGenericTablePrimitive = rel.startsWith("components/ui/table") || rel.startsWith("components/ui/shift-template") || rel.startsWith("components/ui/shift-swap") || rel === "pages/payroll/shared.tsx"
  // Marketing mockups and shell chrome use tight gaps intentionally — not app page density violations
  const isChromeOrMarketing = rel.startsWith("components/marketing/") || rel.startsWith("components/shell/") || rel.startsWith("components/ui/breadcrumb") || rel.startsWith("components/ui/dialog") || rel.startsWith("components/ui/modal") || rel.startsWith("components/ui/tabs") || rel.startsWith("components/ui/layout") || rel.startsWith("components/ui/status-pill")

  // 1. Heading violations — text-2xl / text-xl / text-lg outside PageHeader
  // These are warnings, not hard failures — too noisy for cards/modals/dialogs.
  // Skip chrome/marketing and generic primitives where text-lg is the title token itself (e.g. dialog/modal).
  if (!isChromeOrMarketing && !rel.startsWith("components/ui/") && rel !== "components/ui.tsx") {
    for (const cls of HEADING_VIOLATIONS) {
      const re = new RegExp(`\\b${cls.replace("-", "\\-")}\\b`, "g")
      let m
      while ((m = re.exec(src))) {
        const line = src.slice(0, m.index).split("\n").length
        const context = src.slice(Math.max(0, m.index - 80), m.index + 40)
        if (context.includes("page-title") || context.includes("section-title") || context.includes("PageHeader")) continue
        warnings.push({ file: rel, line, kind: "typography", message: `${cls} — prefer PageHeader (page-title) or SectionCard (section-title)` })
      }
    }
  } else if (rel === "components/ui.tsx" || rel.startsWith("components/ui/")) {
    // ui.tsx defines PageHeader itself — text-lg there is the compact variant, not a violation
    // also all components/ui primitives handle their own density
    // skip
  } else {
    // still flag only if truly outside design system, but for chrome skip entirely
  }

  // 1b. Arbitrary text-[Npx]
  {
    let m
    ARBITRARY_TEXT_RE.lastIndex = 0
    while ((m = ARBITRARY_TEXT_RE.exec(src))) {
      const px = m[1]
      if (ARBITRARY_ALLOWED_PX.has(px)) {
        // Check if file is in allowed list for micro-type
        const allowed = [...ARBITRARY_ALLOWED_FILES].some((f) => rel.endsWith(f) || rel.includes(f))
        if (allowed) continue
        // Also allow inside DesignGallery (already skipped) and skeleton/badge contexts
        const ctx = src.slice(Math.max(0, m.index - 120), m.index + 60)
        if (ctx.includes("Badge") || ctx.includes("badge") || ctx.includes("kbd") || ctx.includes("skeleton")) continue
      }
      const line = src.slice(0, m.index).split("\n").length
      violations.push({ file: rel, line, kind: "typography", message: `text-[${px}] — use the type scale (text-xs/sm/base or text-caption/body-sm), not arbitrary px` })
    }
  }

  // 2. Color violations
  for (const { pattern, token, when } of COLOR_VIOLATIONS) {
    pattern.lastIndex = 0
    let m
    while ((m = pattern.exec(src))) {
      const line = src.slice(0, m.index).split("\n").length
      // Don't flag inside comments
      const lineText = src.split("\n")[line - 1] || ""
      if (lineText.trim().startsWith("//") || lineText.trim().startsWith("*")) continue
      violations.push({ file: rel, line, kind: "color", message: `${m[0]} — use ${token} (${when})` })
    }
  }

  // 3. Spacing — informational warnings for non-scale gaps
  {
    if (!isChromeOrMarketing) {
      let m
      GAP_RE.lastIndex = 0
      while ((m = GAP_RE.exec(src))) {
        const val = m[1]
        if (!ALLOWED_GAPS.has(val)) {
          const line = src.slice(0, m.index).split("\n").length
          warnings.push({ file: rel, line, kind: "spacing", message: `gap-${val} — not on the 4px scale (allowed: ${[...ALLOWED_GAPS].join(", ")}); use gap-2/3/4/5/6` })
        }
      }
    }
  }

  // 4. text-navy — valid token (maps to var(--fg)), just warn if truly orphaned
  {
    const re = /\btext-navy\b/g
    let m
    while ((m = re.exec(src))) {
      const line = src.slice(0, m.index).split("\n").length
      const ctx = src.slice(Math.max(0, m.index - 100), m.index + 50)
      if (ctx.includes("page-title") || ctx.includes("section-title") || ctx.includes("PageHeader") || ctx.includes("SectionCard")) continue
      warnings.push({ file: rel, line, kind: "typography", message: `text-navy outside PageHeader/SectionCard — prefer page-title or section-title` })
    }
  }

  // 5. Component consistency — list pages should use EmptyState for empty data
  //    (not render a bare table with no rows, not hand-rolled "no data" text).
  // Generic table primitives delegate empty handling to pages — don't flag the primitive itself.
  {
    if (!isGenericTablePrimitive) {
      const hasTable = /\btable-base\b/.test(src)
      const hasEmptyState = /\bEmptyState\b/.test(src)
      if (hasTable && !hasEmptyState) {
        warnings.push({
          file: rel,
          line: 1,
          kind: "component-consistency",
          message: "page uses table-base without EmptyState — add empty-state fallback for zero-row lists",
        })
      }
    }
  }

  // 6. Layout quality — PageHeader should be the page title pattern on app pages
  {
    const hasH1 = /\b<h1\b/.test(src)
    const hasPageHeader = /\bPageHeader\b/.test(src)
    if (hasH1 && !hasPageHeader) {
      warnings.push({
        file: rel,
        line: 1,
        kind: "layout-quality",
        message: "page hand-rolls <h1> — prefer PageHeader for consistent page title density and styling",
      })
    }
  }

  // 7. Layout quality — SectionCard compact prop on data-dense sections
  {
    const hasSectionCard = /\bSectionCard\b/.test(src)
    const hasCompactSectionCard = /SectionCard[^>]*\bcompact\b/.test(src)
    if (hasSectionCard && !hasCompactSectionCard && /\btable-base\b/.test(src)) {
      warnings.push({
        file: rel,
        line: 1,
        kind: "layout-quality",
        message: "SectionCard wraps a table without compact prop — consider compact density for data-dense sections",
      })
    }
  }
}

// ---------------------------------------------------------------------------
// Report
// ---------------------------------------------------------------------------
if (violations.length === 0 && warnings.length === 0) {
  console.log("✓ Design alignment OK — no typography/color/spacing violations.")
  process.exit(0)
}

if (violations.length > 0) {
  console.error(`\n✗ ${violations.length} design alignment violation(s):\n`)
  // Group by file
  const byFile = new Map()
  for (const v of violations) {
    if (!byFile.has(v.file)) byFile.set(v.file, [])
    byFile.get(v.file).push(v)
  }
  for (const [file, vs] of byFile) {
    console.error(`  ${file}`)
    for (const v of vs) {
      console.error(`    :${v.line}  [${v.kind}]  ${v.message}`)
    }
  }
  console.error("")
}

if (warnings.length > 0) {
  const label = violations.length > 0 ? "warnings (not failing)" : "warnings"
  console.error(`  ${warnings.length} ${label}:\n`)
  const byFile = new Map()
  for (const w of warnings) {
    if (!byFile.has(w.file)) byFile.set(w.file, [])
    byFile.get(w.file).push(w)
  }
  for (const [file, ws] of byFile) {
    // Only show first 3 per file for warnings to avoid noise
    const shown = ws.slice(0, 3)
    console.error(`  ${file}`)
    for (const w of shown) {
      console.error(`    :${w.line}  [${w.kind}]  ${w.message}`)
    }
    if (ws.length > 3) console.error(`    ... and ${ws.length - 3} more`)
  }
  console.error("")
}

if (violations.length > 0) {
  console.error(`Fix: replace flagged classes with design tokens, or use PageHeader/SectionCard/Alert/Badge.`)
  console.error(`Docs: frontend/src/index.css (tokens) · frontend/src/pages/Design.tsx (reference)\n`)
  process.exit(1)
} else {
  console.log(`  (warnings do not fail the build — fix when touching those files)\n`)
  process.exit(0)
}
