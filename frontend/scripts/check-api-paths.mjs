/**
 * API path check.
 *
 * The axios instance in `lib/api.ts` is created with
 * `baseURL = VITE_API_URL || "/api/v1"`. Any request path that already
 * starts with `/api/v1` is therefore requested twice — `/api/v1/api/v1/...`
 * — and the server answers 404 with no obvious cause. That is how the
 * Jobs, Import and MFA screens ended up silently empty.
 *
 * This check fails the build when a page passes an absolute path that
 * repeats the prefix.
 */
import { readFileSync, readdirSync, statSync } from "node:fs"
import { join, relative } from "node:path"

const SRC = new URL("../src/", import.meta.url).pathname

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

const problems = []

// api.get("/x") / api.post("/x") / api.delete("/x")
const callRe = /\bapi\.(?:get|post|put|patch|delete|head)\s*(?:<[^>]*>)?\(\s*[`"']([^`"']*)[`"']/g
// `api.defaults.baseURL}/x`
const baseRe = /\$\{api\.defaults\.baseURL\}([^`"']*)/g

for (const file of sourceFiles()) {
  const source = readFileSync(file, "utf8")
  const rel = relative(SRC, file)

  for (const re of [callRe, baseRe]) {
    re.lastIndex = 0
    let m
    while ((m = re.exec(source))) {
      const target = m[1]
      if (!target) continue
      if (!target.startsWith("/api/v1")) continue
      const line = source.slice(0, m.index).split("\n").length
      problems.push({
        file: rel,
        line,
        target,
        why: "the axios baseURL already ends in /api/v1",
      })
    }
  }
}

if (problems.length) {
  console.error(`\n✗ ${problems.length} API path problem(s) found:\n`)
  for (const p of problems) {
    console.error(`  ${p.file}:${p.line}  →  ${p.target}`)
    console.error(`      ${p.why}`)
  }
  console.error("\n")
  process.exit(1)
}

console.log("✓ API path integrity OK — no request repeats the /api/v1 prefix.")
