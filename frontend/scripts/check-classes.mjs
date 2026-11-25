/**
 * Dead utility class check.
 *
 * A Tailwind class that is not generated is not an error — the element
 * simply keeps whatever style it had. That is how a class like
 * `text-blue-200/90` survives: Tailwind cannot apply an opacity
 * modifier to a colour defined as a CSS variable, so the class is never
 * emitted, and the text falls back to the inherited colour — which on a
 * dark surface is invisible.
 *
 * This check reads the built stylesheet and reports any colour utility
 * used in the source that the build did not emit.
 *
 * Run with: npm run check:classes  (after a build)
 */
import { readFileSync, readdirSync, statSync } from "node:fs"
import { join, relative } from "node:path"

const ROOT = new URL("..", import.meta.url).pathname
const SRC = join(ROOT, "src")
const DIST = join(ROOT, "dist")

/** Utilities whose absence changes how the page looks. */
const UTILITY_PREFIXES = [
  "text-",
  "bg-",
  "border-",
  "from-",
  "via-",
  "to-",
  "ring-",
  "divide-",
  "fill-",
  "stroke-",
  "placeholder-",
  "decoration-",
  "outline-",
  "shadow-",
  "accent-",
]

/** Prefixes that are state or layout, not a colour; skipped. */
const IGNORED = [
  "text-",
  "bg-",
  "border-",
  "from-",
  "via-",
  "to-",
  "ring-",
  "divide-",
  "fill-",
  "stroke-",
  "placeholder-",
  "decoration-",
  "outline-",
  "shadow-",
  "accent-",
]

/** class names that are not colour utilities. */
const NOT_COLOURS = new Set([
  "text-center", "text-left", "text-right", "text-justify",
  "text-nowrap", "text-balance", "text-pretty",
  "text-xs", "text-sm", "text-base", "text-lg", "text-xl",
  "text-2xl", "text-3xl", "text-4xl", "text-5xl", "text-6xl",
  "text-7xl", "text-8xl", "text-9xl",
  "text-h1", "text-h2", "text-h3", "text-body", "text-body-sm",
  "text-ellipsis", "text-clip",
  "bg-none", "bg-fixed", "bg-local", "bg-scroll",
  "bg-cover", "bg-contain", "bg-repeat", "bg-no-repeat",
  "bg-auto", "bg-center", "bg-top", "bg-bottom", "bg-left", "bg-right",
  "border-solid", "border-dashed", "border-dotted", "border-double",
  "border-none", "border-collapse", "border-separate",
  "shadow-sm", "shadow", "shadow-md", "shadow-lg", "shadow-xl",
  "shadow-2xl", "shadow-inner", "shadow-none",
  "shadow-card", "shadow-card-lg", "shadow-card-hover",
  "ring-none", "ring-0", "ring-1", "ring-2", "ring-4", "ring-8",
  "fill-current", "stroke-current", "fill-none", "stroke-none",
  "stroke-0", "stroke-1", "stroke-2",
  "outline-none", "outline-hidden", "outline-solid", "outline-dashed",
  "outline-dotted", "outline-double", "outline-offset-0",
  "outline-offset-1", "outline-offset-2", "outline-offset-4",
  "outline-offset-8",
  "decoration-solid", "decoration-double", "decoration-dotted",
  "decoration-dashed", "decoration-none",
  "accent-auto", "accent-none",
])

function sourceFiles(dir = SRC) {
  const out = []
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry)
    if (statSync(full).isDirectory()) {
      out.push(...sourceFiles(full))
    } else if (/\.tsx?$/.test(entry)) {
      out.push(full)
    }
  }
  return out
}

function readBuiltCss() {
  const assets = join(DIST, "assets")
  let files
  try {
    files = readdirSync(assets).filter((f) => f.endsWith(".css"))
  } catch {
    console.error(
      "\n✗ No built stylesheet found. Run `npm run build` before this check.\n"
    )
    process.exit(1)
  }
  if (!files.length) {
    console.error("\n✗ No built stylesheet found. Run `npm run build` first.\n")
    process.exit(1)
  }
  return files.map((f) => readFileSync(join(assets, f), "utf8")).join("\n")
}

/** Escape a class name so it can be searched for in the stylesheet. */
function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
}

/**
 * Undo the CSS escaping Tailwind applies to a class name, so
 * `.bg-\[rgba\(2\,6\,23\,0\.5\)\]` becomes `bg-[rgba(2,6,23,0.5)]`.
 */
function unescapeCss(value) {
  return value.replace(/\\([0-9a-fA-F]{1,6})\s?/g, (_, hex) =>
    String.fromCodePoint(parseInt(hex, 16))
  ).replace(/\\(.)/g, "$1")
}

const css = readBuiltCss()

/** The class names the build actually emitted. */
const emitted = new Set()
for (const match of css.matchAll(/\.((?:\\.|[^\s,{>+~}])+)/g)) {
  // The whole match is one class name. It is not split on dots: an
  // arbitrary value such as `bg-[rgba(2,6,23,0.5)]` contains one.
  const name = unescapeCss(match[1])
  if (name) emitted.add(name)
}

/**
 * Split a className string into class names.
 *
 * An arbitrary value may contain spaces — `bg-[url(data:image/svg+xml,…)]`
 * — so the split has to respect brackets and quotes.
 */
function splitClasses(chunk) {
  const out = []
  let current = ""
  let depth = 0
  let quote = null
  for (const ch of chunk) {
    if (quote) {
      current += ch
      if (ch === quote) quote = null
      continue
    }
    if (ch === '"' || ch === "'") {
      quote = ch
      current += ch
      continue
    }
    if (ch === "[") depth += 1
    if (ch === "]") depth -= 1
    if (/\s/.test(ch) && depth === 0) {
      if (current) out.push(current)
      current = ""
      continue
    }
    current += ch
  }
  if (current) out.push(current)
  return out
}

/**
 * Every string literal inside a `className=` expression.
 *
 * `cn("a", "b", cond && "c")` has three. The check used to match
 * `\{[^}]*?"([^"]*)"`, which stops at the *first* quoted string — so every
 * argument after it was invisible. That is how `text-fm-muted`, a typo for
 * `text-fg-muted`, survived in `ui/tabs.tsx`: it was the second argument.
 * A check that cannot see its input is not a check.
 */
function classChunks(source) {
  const chunks = []
  const opener = /className\s*=\s*/g
  let match
  while ((match = opener.exec(source))) {
    let i = opener.lastIndex
    while (i < source.length && /\s/.test(source[i])) i += 1
    const first = source[i]

    // className="..."
    if (first === '"' || first === "'") {
      const end = source.indexOf(first, i + 1)
      if (end < 0) break
      chunks.push(source.slice(i + 1, end))
      opener.lastIndex = end + 1
      continue
    }

    // className={...} — scan to the matching brace, then take every literal.
    // Comments are dropped: a class name mentioned in prose is not a class.
    if (first === "{") {
      let depth = 0
      let quote = null
      let body = ""
      let j = i
      for (; j < source.length; j += 1) {
        const ch = source[j]
        if (quote) {
          body += ch
          if (ch === "\\") {
            body += source[j + 1] ?? ""
            j += 1
          } else if (ch === quote) {
            quote = null
          }
          continue
        }
        if (ch === '"' || ch === "'" || ch === "`") {
          quote = ch
          body += ch
          continue
        }
        if (ch === "/" && source[j + 1] === "/") {
          while (j < source.length && source[j] !== "\n") j += 1
          body += "\n"
          continue
        }
        if (ch === "/" && source[j + 1] === "*") {
          j += 2
          while (j < source.length && !(source[j] === "*" && source[j + 1] === "/")) j += 1
          j += 1
          continue
        }
        if (ch === "{") depth += 1
        else if (ch === "}") {
          depth -= 1
          if (depth === 0) break
        }
        body += ch
      }
      for (const literal of body.matchAll(/"([^"]*)"|'([^']*)'|`([^`]*)`/g)) {
        chunks.push(literal[1] ?? literal[2] ?? literal[3] ?? "")
      }
      opener.lastIndex = j + 1
      continue
    }

    // Some other expression, e.g. className={styles.row}: nothing to read.
    opener.lastIndex = i
  }
  return chunks
}

const used = new Map()
for (const file of sourceFiles()) {
  const source = readFileSync(file, "utf8")
  const rel = relative(SRC, file)
  for (const chunk of classChunks(source)) {
    for (const token of splitClasses(chunk)) {
      if (!token) continue
      if (!UTILITY_PREFIXES.some((p) => token.startsWith(p))) continue
      if (NOT_COLOURS.has(token)) continue
      // Skip template expressions and conditional fragments.
      if (token.includes("${") || token.includes("?") || token.includes(":")) continue
      // An arbitrary value may contain a URL with its own quotes; keep it
      // as one class.
      if (token.startsWith("bg-[url(") || token.startsWith("stroke-width=")) continue
      if (!used.has(token)) used.set(token, rel)
    }
  }
}

const problems = []
for (const [token, file] of used) {
  if (emitted.has(token)) continue
  problems.push({ file, token })
}

if (problems.length) {
  console.error(`\n✗ ${problems.length} class(es) used in the source but not emitted by the build:\n`)
  for (const p of problems) console.error(`  ${p.file}  →  ${p.token}`)
  console.error(
    "\n  A class the build does not emit is not an error — the element keeps\n" +
      "  whatever style it had. Tailwind cannot apply an opacity modifier to a\n" +
      "  colour defined as a CSS variable, so `text-blue-200/90` is silently\n" +
      "  dropped. Use a literal arbitrary value, e.g. `text-[rgba(..)]`.\n"
  )
  process.exit(1)
}

console.log(`✓ Class integrity OK — every colour utility in the source was emitted.`)
