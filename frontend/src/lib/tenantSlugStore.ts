let tenantSlug: string | null = null

export function setTenantSlug(s: string | null) {
  tenantSlug = s ? s.toLowerCase() : null
}

export function getTenantSlug() {
  return tenantSlug
}
