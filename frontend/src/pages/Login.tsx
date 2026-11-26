import { useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "@/context/AuthContext"
import { Button, RetryableAlert } from "@/components/ui"
import api from "@/lib/api"

/**
 * Turn a failed sign-in into a message that names the actual failure class.
 *
 * A blocked request, a CORS rejection and a timeout all arrive without a
 * `response`; showing "check your username and password" for those sends the
 * user to fix something that is not broken. The server's detail is still
 * preferred for credential and validation errors.
 */
export function loginErrorMessage(err: any): string {
  const response = err?.response
  const status = response?.status
  const detail = response?.data?.detail

  if (!response) {
    return "We can't reach the server right now. Check your connection and try again."
  }
  if (
    (typeof status === "number" && status >= 500) ||
    err?.apiError?.code === "dependency_unavailable"
  ) {
    return "The service is temporarily unavailable. Please try again in a moment."
  }
  if (status === 429) {
    return typeof detail === "string" && detail
      ? detail
      : "Too many sign-in attempts. Please wait and try again."
  }
  if ((status === 400 || status === 401 || status === 403) && typeof detail === "string") {
    return detail
  }
  return "We couldn't sign you in. Check your username and password and try again."
}

export default function Login() {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<unknown | null>(null)
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()
  const { login } = useAuth()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (busy) return // prevents duplicate submissions creating extra sessions
    setBusy(true)
    setError(null)
    try {
      const res = await api.post("/auth/login", { username, password })
      localStorage.setItem("karmathy_token", res.data.access_token)
      const mustChange = res.data.must_change_password === true
      login(
        res.data.access_token,
        {
          id: 0,
          username: res.data.username || username,
          email: "",
          role: res.data.role || "Associate",
          is_active: true,
        },
        mustChange
      )
      // An account that must replace its password can only reach the
      // password-change screen; every other route is refused by the server.
      navigate(mustChange ? "/change-password" : "/dashboard", { replace: true })
    } catch (err: any) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen bg-page flex flex-col">
      <header className="bg-surface border-b border-border">
        <div className="max-w-container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center">
            <span className="flex items-center gap-2.5">
              <span className="brand-mark" aria-hidden="true">K</span>
              <span className="text-[var(--font-size-lg)] font-bold text-[var(--semantic-brand-text)] tracking-tight">LibrePeople</span>
            </span>
          </div>
        </div>
      </header>

      <main id="main-content" tabIndex={-1} className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          <div className="text-center mb-7">
            <h1 className="text-[var(--font-size-2xl)] font-bold text-fg tracking-tight">Sign in to LibrePeople</h1>
            <p className="text-sm text-text-secondary mt-1.5">
              Access your organisation's HCM workspace.
            </p>
          </div>

          <div className="card p-6 sm:p-7">
            {!!error && (
              <div className="mb-4">
                <RetryableAlert err={error} title="Sign-in failed" fallback={loginErrorMessage(error)} onRetry={() => handleSubmit({ preventDefault: () => {} } as any)} />
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="field">
                <label htmlFor="login-username" className="field-label">
                  Username <span className="text-error-text" aria-hidden="true">*</span>
                </label>
                <input
                  id="login-username"
                  name="username"
                  type="text"
                  autoComplete="username"
                  autoFocus
                  className="input"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  aria-required="true"
                  required
                />
              </div>

              <div className="field">
                <label htmlFor="login-password" className="field-label">
                  Password <span className="text-error-text" aria-hidden="true">*</span>
                </label>
                <input
                  id="login-password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  className="input"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  aria-required="true"
                  required
                />
              </div>

              <Button variant="primary" className="w-full" type="submit" disabled={busy}>
                {busy ? "Signing in…" : "Sign in"}
              </Button>
            </form>
          </div>

          <p className="text-center text-xs text-text-secondary mt-5">
            People. Potential. Progress.
          </p>
        </div>
      </main>
    </div>
  )
}