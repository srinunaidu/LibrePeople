import { createContext, useContext, useState, useEffect, ReactNode } from "react"
import { AuthState, User } from "@/types"

const AuthContext = createContext<AuthState | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem("karmathy_token")
  )
  const [user, setUser] = useState<User | null>(() => {
    try {
      const raw = localStorage.getItem("karmathy_user")
      return raw ? (JSON.parse(raw) as User) : null
    } catch {
      return null
    }
  })
  // True when the account must replace an administrator-set password before
  // it can use the API. The server enforces this; the flag only decides
  // where the user is sent.
  const [mustChangePassword, setMustChangePassword] = useState<boolean>(() => {
    try {
      return localStorage.getItem("karmathy_must_change_password") === "1"
    } catch {
      return false
    }
  })

  // Impersonation: keep the admin's original credentials so Exit restores them.
  const [originalToken, setOriginalToken] = useState<string | null>(() => {
    try {
      return localStorage.getItem("karmathy_original_token")
    } catch {
      return null
    }
  })
  const [originalUser, setOriginalUser] = useState<User | null>(() => {
    try {
      const raw = localStorage.getItem("karmathy_original_user")
      return raw ? (JSON.parse(raw) as User) : null
    } catch {
      return null
    }
  })

  const isImpersonating = !!originalToken && !!originalUser

  useEffect(() => {
    if (token) {
      localStorage.setItem("karmathy_token", token)
    } else {
      localStorage.removeItem("karmathy_token")
    }
  }, [token])

  useEffect(() => {
    if (user) {
      localStorage.setItem("karmathy_user", JSON.stringify(user))
    } else {
      localStorage.removeItem("karmathy_user")
    }
  }, [user])

  useEffect(() => {
    if (mustChangePassword) {
      localStorage.setItem("karmathy_must_change_password", "1")
    } else {
      localStorage.removeItem("karmathy_must_change_password")
    }
  }, [mustChangePassword])

  useEffect(() => {
    if (originalToken) {
      localStorage.setItem("karmathy_original_token", originalToken)
    } else {
      localStorage.removeItem("karmathy_original_token")
    }
  }, [originalToken])

  useEffect(() => {
    if (originalUser) {
      localStorage.setItem("karmathy_original_user", JSON.stringify(originalUser))
    } else {
      localStorage.removeItem("karmathy_original_user")
    }
  }, [originalUser])

  const login = (newToken: string, newUser: User, mustChange = false) => {
    setToken(newToken)
    setUser(newUser)
    setMustChangePassword(mustChange)
  }

  const logout = () => {
    setToken(null)
    setUser(null)
    setMustChangePassword(false)
    setOriginalToken(null)
    setOriginalUser(null)
  }

  const impersonate = (newToken: string, newUser: User) => {
    // Save current admin credentials once — nested impersonation keeps the root.
    if (!originalToken && token) {
      setOriginalToken(token)
      localStorage.setItem("karmathy_original_token", token)
    }
    if (!originalUser && user) {
      setOriginalUser(user)
      localStorage.setItem("karmathy_original_user", JSON.stringify(user))
    }
    setToken(newToken)
    setUser(newUser)
  }

  const exitImpersonation = () => {
    if (originalToken && originalUser) {
      setToken(originalToken)
      setUser(originalUser)
      setOriginalToken(null)
      setOriginalUser(null)
      localStorage.removeItem("karmathy_original_token")
      localStorage.removeItem("karmathy_original_user")
      localStorage.setItem("karmathy_token", originalToken)
      localStorage.setItem("karmathy_user", JSON.stringify(originalUser))
    } else {
      // No original to restore — fall back to logout.
      logout()
    }
  }

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        isAuthenticated: !!token,
        mustChangePassword,
        setMustChangePassword,
        login,
        logout,
        originalToken,
        originalUser,
        isImpersonating,
        impersonate,
        exitImpersonation,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}
