import { useAuth } from "@/context/AuthContext"
import AssociateHome from "@/components/home/AssociateHome"
import ManagerHome from "@/components/home/ManagerHome"
import HRHome from "@/components/home/HRHome"
import PayrollHome from "@/components/home/PayrollHome"
import SuperAdminHome from "@/components/home/SuperAdminHome"
import DashboardFallback from "@/components/home/DashboardFallback"

/**
 * Role-based home screen.
 *
 * The dashboard route stays the same; the component rendered depends on the
 * user's role. Unknown / missing roles fall back to a generic overview.
 */
export default function Dashboard() {
  const { user } = useAuth()
  const role = user?.role

  switch (role) {
    case "Associate":
      return <AssociateHome />
    case "Manager":
      return <ManagerHome />
    case "HR":
      return <HRHome />
    case "PayrollViewer":
      return <PayrollHome />
    case "SuperAdmin":
      return <SuperAdminHome />
    default:
      return <DashboardFallback />
  }
}