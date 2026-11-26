import { readFileSync, readdirSync, statSync } from "fs"
import { join } from "path"
import { describe, expect, test } from "vitest"

// R2 honesty-sweep: fake-data markers are gone from product screens, the
// InterviewScheduling flag-shim is rewired to the live interviews CRUD, and
// ProjectStatus no longer hardcodes a commit hash (build-time __BUILD__).

const read = (p: string) => readFileSync(join(process.cwd(), p), "utf8")

function collect(dir: string, out: string[] = []): string[] {
  for (const e of readdirSync(join(process.cwd(), dir))) {
    if (e.endsWith(".test.tsx") || e.endsWith(".test.ts")) continue
    if (e === "__snapshots__") continue
    const rel = join(dir, e)
    const st = statSync(join(process.cwd(), rel))
    if (st.isDirectory()) collect(rel, out)
    else if (/\.(tsx?|jsx?)$/.test(e)) out.push(rel)
  }
  return out
}

// Negative assertions scan code only — header comments document the removed
// fabrications/dead endpoints and legitimately mention their names.
const code = (src: string) => src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|\s)\/\/.*$/gm, "$1")

describe("honesty-sweep — no fake-data markers in product screens", () => {
  const files = [...collect("src/pages"), ...collect("src/components/marketing")]
  test(`scans ${files.length} screen/marketing files`, () => {
    expect(files.length).toBeGreaterThan(10)
  })
  for (const marker of ["Math.random", "dummy", "lorem", "sampleData"]) {
    test(`no "${marker}" in pages/ or components/marketing/`, () => {
      const hits = files.filter((f) => code(read(f)).includes(marker))
      expect(hits).toEqual([])
    })
  }
})

describe("honesty-sweep — InterviewScheduling on live CRUD", () => {
  const src = read("src/pages/admin/InterviewScheduling.tsx")
  test("hits /api/v1/interviews, not the flag shim", () => {
    expect(src).toContain("/api/v1/interviews")
    expect(src).not.toContain("feature-flags/interview_type")
  })
  test("api.ts exposes interviews helpers and nothing else changed there", () => {
    const api = code(read("src/lib/api.ts"))
    for (const h of ["listInterviews", "createInterview", "updateInterview"]) {
      expect(api).toContain(h)
    }
    expect(api).toContain('"/interviews"')
    expect(api).not.toContain("interview_type")
  })
})

describe("honesty-sweep — marketing + status honesty", () => {
  test("ProductMockup pulse reads Preview, caption keeps the sample-rows disclosure", () => {
    const src = read("src/components/marketing/ProductMockup.tsx")
    expect(src).toContain("Preview")
    expect(src).not.toMatch(/>\s*Live\s*</)
    expect(src).toContain("sample rows")
  })
  test("ProjectStatus has no hardcoded commit hash (uses build-time __BUILD__)", () => {
    const src = code(read("src/pages/ProjectStatus.tsx"))
    expect(src).not.toMatch(/=\s*["'][0-9a-f]{7}["']/)
    expect(src).toContain("__BUILD__")
  })
  test("DesignGallery carries the internal-preview disclaimer", () => {
    expect(read("src/pages/DesignGallery.tsx")).toContain("internal preview")
  })
})
