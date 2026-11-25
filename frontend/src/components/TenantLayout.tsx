import { useParams, Outlet } from "react-router-dom"
import { Layout } from "@/components/Layout"

export function TenantLayout({ children }: { children?: React.ReactNode }) {
  const { slug } = useParams<{ slug: string }>()
  // slug is available for tenant-scoped operations; TenantProvider detects it from URL
  return <Layout>{children ?? <Outlet />}</Layout>
}
