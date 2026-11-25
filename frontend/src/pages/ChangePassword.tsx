import { useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "@/context/AuthContext"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/inputs"
import api, { errorMessage } from "@/lib/api"

/**
 * Forced password change.
 *
 * An account whose password was set by an administrator — or bootstrapped
 * from an environment secret — is in a `must_change_password` state. The
 * server refuses every API call except reading the user's own profile,
 * changing the password and signing out, so this page is the only place
 * such an account can do anything at all.
 *
 * The policy is enforced by the server; this page mirrors it so the user is
 * told the requirement before they submit. The server is the authority.
 */
export default function ChangePassword() {
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()
  const { login, logout, user } = useAuth()

  const mismatch = confirmPassword.length > 0 && newPassword !== confirmPassword
  const tooShort = newPassword.length > 0 && newPassword.length < 12

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (busy) return
    if (newPassword !== confirmPassword) {
      setError("The two new passwords do not match.")
      return
    }
    setBusy(true)
    setError("")
    try {
      const res = await api.post("/auth/password", {
        current_password: currentPassword,
        new_password: newPassword,
      })
      // Changing the password revokes every existing session, so the server
      // issues a fresh pair. Use it.
      localStorage.setItem("karmathy_token", res.data.access_token)
      login(res.data.access_token, {
        id: user?.id ?? 0,
        username: res.data.username || user?.username || "",
        email: user?.email ?? "",
        role: res.data.role || user?.role || "Associate",
        is_active: true,
      })
      navigate("/dashboard", { replace: true })
    } catch (err) {
      setError(errorMessage(err, "We couldn't change your password. Try again."))
    } finally {
      setBusy(false)
    }
  }

  const signOut = () => {
    logout()
    navigate("/login", { replace: true })
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
            <h1 className="text-[var(--font-size-2xl)] font-bold text-fg tracking-tight">Set a new password</h1>
            <p className="text-sm text-text-secondary mt-1.5">
              Your password was set by an administrator. Choose a new one before you
              continue.
            </p>
          </div>

          <div className="bg-surface border border-border rounded-xl p-6 shadow-sm">
            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
              {error ? (
                <div
                  role="alert"
                  className="rounded-lg bg-error-bg border border-error-border px-3.5 py-2.5 text-sm text-error"
                >
                  {error}
                </div>
              ) : null}

              <div>
                <label htmlFor="current-password" className="block text-sm font-medium text-fg mb-1.5">
                  Current password
                </label>
                <Input
                  id="current-password"
                  name="current-password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                />
              </div>

              <div>
                <label htmlFor="new-password" className="block text-sm font-medium text-fg mb-1.5">
                  New password
                </label>
                <Input
                  id="new-password"
                  name="new-password"
                  type="password"
                  autoComplete="new-password"
                  required
                  aria-describedby="new-password-hint"
                  aria-invalid={tooShort || undefined}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
                <p id="new-password-hint" className="text-xs text-text-secondary mt-1.5">
                  At least 12 characters, mixing at least three of: lower case, upper
                  case, digits and symbols. It must not contain your username or email
                  address, and it cannot be one of the most commonly used passwords.
                </p>
              </div>

              <div>
                <label htmlFor="confirm-password" className="block text-sm font-medium text-fg mb-1.5">
                  Confirm new password
                </label>
                <Input
                  id="confirm-password"
                  name="confirm-password"
                  type="password"
                  autoComplete="new-password"
                  required
                  aria-invalid={mismatch || undefined}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
                {mismatch ? (
                  <p className="text-xs text-error mt-1.5">The two passwords do not match.</p>
                ) : null}
              </div>

              <Button type="submit" className="w-full" disabled={busy || mismatch}>
                {busy ? "Saving…" : "Save password and continue"}
              </Button>

              <button
                type="button"
                onClick={signOut}
                className="w-full text-center text-sm text-text-secondary hover:text-brand-600 underline underline-offset-2"
              >
                Sign out instead
              </button>
            </form>
          </div>
        </div>
      </main>
    </div>
  )
}
