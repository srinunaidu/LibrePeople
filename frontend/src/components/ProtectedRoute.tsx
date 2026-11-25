import { Navigate } from "react-router-dom"
import { useAuth } from "@/context/AuthContext"

interface ProtectedRouteProps {
  children: React.ReactNode
  /**
   * Allow this route even when the account must change its password.
   *
   * The server refuses every other API call for such an account, so the
   * password-change screen is the only thing it can reach.
   */
  allowPasswordChange?: boolean
  /**
   * Roles allowed to render this route. When set, the user's role must be
   * included, otherwise a 403 is shown instead of a blank page.
   */
  roles?: string[]
}

export function ProtectedRoute({
  children,
  allowPasswordChange = false,
  roles,
}: ProtectedRouteProps) {
  const { isAuthenticated, mustChangePassword, user } = useAuth()
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  if (mustChangePassword && !allowPasswordChange) {
    return <Navigate to="/change-password" replace />
  }
  if (roles && roles.length > 0) {
    const userRole = user?.role
    if (!userRole || !roles.includes(userRole)) {
      return (
        <div className="mk-card p-6 text-center">
          <h2 className="text-fg font-semibold mb-2">403 — Forbidden</h2>
          <p className="text-fg-muted mb-4">
            Your role ({userRole ?? "unknown"}) is not authorised to access this page.
          </p>
        </div>
      )
    }
  }
  return <>{children}</>
}
