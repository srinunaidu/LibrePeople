import api from "@/lib/api"
import type { Employee, EmployeePage } from "@/types"

/** The query the directory operation accepts. Every filter is the server's. */
export interface EmployeeQuery {
  page?: number
  page_size?: number
  search?: string
  department_id?: number
  status?: string
  manager_id?: number
  sort?: "employee_number" | "last_name" | "hire_date"
  order?: "asc" | "desc"
}

/** One page of the directory, in the contract's envelope. */
export async function fetchEmployeePage(
  params: EmployeeQuery = {},
): Promise<EmployeePage> {
  const response = await api.get<EmployeePage>("/employees/", { params })
  return response.data
}

/**
 * Read the whole directory, a page at a time.
 *
 * The screens that only need a list of people to choose from (leave, time,
 * scheduling, onboarding, offboarding) used to read one page and treat it as
 * everyone, because the old endpoint returned a bare list capped at 100. They
 * now read the paged operation until `meta.total_pages` is exhausted.
 *
 * The safety cap exists so a pathological directory cannot turn one screen
 * into thousands of requests. When it is reached the caller gets the rows read
 * so far and `complete: false`; the screens that need to be exhaustive (the
 * People directory) do not use this helper — they page explicitly and show
 * the server's total.
 */
export async function fetchAllEmployees(
  params: Omit<EmployeeQuery, "page" | "page_size"> = {},
  maxPages = 50,
): Promise<{ items: Employee[]; total: number; complete: boolean }> {
  const items: Employee[] = []
  const seen = new Set<number>()
  let page = 1
  let totalPages = 1
  let total = 0

  do {
    const data = await fetchEmployeePage({ ...params, page, page_size: 200 })
    total = data.meta.total
    totalPages = Math.max(1, data.meta.total_pages)
    for (const employee of data.items) {
      if (!seen.has(employee.id)) {
        seen.add(employee.id)
        items.push(employee)
      }
    }
    if (data.items.length === 0) break
    page += 1
  } while (page <= totalPages && page <= maxPages)

  return { items, total, complete: items.length >= total }
}
