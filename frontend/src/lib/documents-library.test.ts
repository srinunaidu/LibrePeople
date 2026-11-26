/* Documents library contract tests (LP-DOC-001/002, frontend only).
 * Covers: R8 expiry-badge rule (30-day threshold), R10 client-side
 * filters (no network), and the six-endpoint api-path allowlist.
 */
import { readFileSync } from "fs"
import { join } from "path"
import { describe, expect, test } from "vitest"
import {
  API_PATHS,
  EXPIRY_SOON_DAYS,
  DOCUMENT_TYPES,
  expiryBadge,
  filterDocuments,
  type EmployeeDocument,
} from "@/pages/documents/DocumentsLibrary"

const NOW = new Date("2026-06-15T12:00:00Z")
const iso = (d: Date) => d.toISOString().slice(0, 10)
const daysFromNow = (n: number) => iso(new Date(NOW.getTime() + n * 86400000))

const doc = (over: Partial<EmployeeDocument> = {}): EmployeeDocument => ({
  id: 1,
  employee_id: 7,
  document_type: "Contract",
  file_name: "contract.pdf",
  storage_url: "/api/v1/files/contract.pdf",
  current_version: 1,
  status: "Active",
  expiry_date: null,
  uploaded_at: "2026-01-01",
  ...over,
})

describe("R8 expiry badge rule (30-day threshold)", () => {
  test("threshold constant is 30 days", () => {
    expect(EXPIRY_SOON_DAYS).toBe(30)
  })

  test("status=Expired always badges Expired even with future date", () => {
    expect(expiryBadge(doc({ status: "Expired", expiry_date: daysFromNow(300) }), NOW)).toBe("Expired")
  })

  test("past expiry date badges Expired", () => {
    expect(expiryBadge(doc({ expiry_date: daysFromNow(-1) }), NOW)).toBe("Expired")
  })

  test("expiry within 30 days badges Expiring (boundary inclusive)", () => {
    expect(expiryBadge(doc({ expiry_date: daysFromNow(30) }), NOW)).toBe("Expiring")
    expect(expiryBadge(doc({ expiry_date: daysFromNow(1) }), NOW)).toBe("Expiring")
  })

  test("expiry beyond 30 days badges Valid", () => {
    expect(expiryBadge(doc({ expiry_date: daysFromNow(31) }), NOW)).toBe("Valid")
  })

  test("missing or unparsable expiry badges Valid", () => {
    expect(expiryBadge(doc({ expiry_date: null }), NOW)).toBe("Valid")
    expect(expiryBadge(doc({ expiry_date: "not-a-date" }), NOW)).toBe("Valid")
  })
})

describe("R10 client-side filters (no network)", () => {
  const docs: EmployeeDocument[] = [
    doc({ id: 1, employee_id: 7, document_type: "Contract", file_name: "offer-2024.pdf", status: "Active", expiry_date: daysFromNow(90) }),
    doc({ id: 2, employee_id: 7, document_type: "ID", file_name: "passport.png", status: "Active", expiry_date: daysFromNow(10) }),
    doc({ id: 3, employee_id: 9, document_type: "Tax", file_name: "w2-2025.pdf", status: "Expired", expiry_date: daysFromNow(-5) }),
  ]
  const base = { q: "", type: "all", status: "all", bucket: "all" as const }

  test("text query matches file/type/employee without network", () => {
    expect(filterDocuments(docs, { ...base, q: "passport" }, NOW).map((d) => d.id)).toEqual([2])
    expect(filterDocuments(docs, { ...base, q: "tax" }, NOW).map((d) => d.id)).toEqual([3])
    expect(filterDocuments(docs, { ...base, q: "9" }, NOW).map((d) => d.id)).toEqual([3])
  })

  test("type filter narrows to one category", () => {
    expect(filterDocuments(docs, { ...base, type: "ID" }, NOW).map((d) => d.id)).toEqual([2])
  })

  test("status filter narrows to Expired", () => {
    expect(filterDocuments(docs, { ...base, status: "Expired" }, NOW).map((d) => d.id)).toEqual([3])
  })

  test("expiry-bucket filter uses the 30-day rule", () => {
    expect(filterDocuments(docs, { ...base, bucket: "Expiring" }, NOW).map((d) => d.id)).toEqual([2])
    expect(filterDocuments(docs, { ...base, bucket: "Expired" }, NOW).map((d) => d.id)).toEqual([3])
    expect(filterDocuments(docs, { ...base, bucket: "Valid" }, NOW).map((d) => d.id)).toEqual([1])
  })

  test("combined filters intersect", () => {
    expect(filterDocuments(docs, { ...base, q: "pdf", status: "Active" }, NOW).map((d) => d.id)).toEqual([1])
  })
})

describe("endpoint allowlist — only the six contract paths", () => {
  test("api-path constants match the contract", () => {
    expect(API_PATHS.collection).toBe("/employee-documents")
    expect(API_PATHS.employeeParam).toBe("employee_id")
    expect(API_PATHS.versions(5)).toBe("/employee-documents/5/versions")
    expect(API_PATHS.ack(5)).toBe("/employee-documents/5/ack")
  })

  test("document_type uses model values (no invented category)", () => {
    expect(DOCUMENT_TYPES).toEqual(["Contract", "ID", "Tax", "Certificate", "Policy", "Other"])
  })

  test("page source calls only the six contract endpoints", () => {
    const src = readFileSync(join(process.cwd(), "src/pages/documents/DocumentsLibrary.tsx"), "utf8")
    // All api calls go through the API_PATHS constants (asserted above) —
    // no raw endpoint string literal may appear in an api.* call.
    const literalCalls = [...src.matchAll(/api\.(get|post|put|patch|delete)\s*(?:<[^>]*>)?\(\s*['"`]/g)]
    expect(literalCalls, `raw endpoint literals: ${JSON.stringify(literalCalls.map((m) => m[0]))}`).toEqual([])
    expect(src).toContain("API_PATHS.collection")
    expect(src).toContain("API_PATHS.versions(")
    expect(src).toContain("API_PATHS.ack(")
    // R7 download anchors at the row's own storage_url via fileUrl().
    expect(src).toContain("fileUrl(d.storage_url)")
    const code = src.replace(/\/\*[\s\S]*?\*\//g, "")
    expect(code).not.toMatch(/access-?log/i)
    expect(code).not.toMatch(/reminder|sendEmail|push/i)
  })
})
