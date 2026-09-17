import { createContext, useContext, useEffect, useMemo, useState } from "react"

export type Role = "INVESTOR" | "ADMIN"
export type CurrentUser = { id: string; name: string; email: string; role: Role }

type AuthContextValue = {
  user: CurrentUser | null
  loading: boolean
  signIn: (email: string, password: string) => Promise<CurrentUser>
  createInvestor: (name: string, email: string, password: string) => Promise<void>
  resetPassword: (email: string) => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

function parseJwt(token: string) {
  try {
    const base64Url = token.split(".")[1]
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/")
    const jsonPayload = decodeURIComponent(
      window.atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    )
    return JSON.parse(jsonPayload)
  } catch (e) {
    return null
  }
}

function getUserFromToken(token: string | null): CurrentUser | null {
  if (!token) return null
  const payload = parseJwt(token)
  if (!payload || !payload.exp || payload.exp * 1000 < Date.now()) {
    return null // Expired or invalid
  }
  return {
    id: payload.sub,
    email: payload.email,
    name: payload.user_metadata?.full_name || payload.email.split("@")[0],
    role: payload.user_metadata?.role === "ADMIN" ? "ADMIN" : "INVESTOR",
  }
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1"

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem("auth_token")
    if (token) {
      const currentUser = getUserFromToken(token)
      if (currentUser) {
        setUser(currentUser)
      } else {
        localStorage.removeItem("auth_token")
      }
    }
    setLoading(false)
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      signIn: async (email, password) => {
        const response = await fetch(`${apiBaseUrl}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        })
        if (!response.ok) {
          const err = await response.json().catch(() => ({}))
          throw new Error(err.detail || "Failed to sign in")
        }
        const data = await response.json()
        localStorage.setItem("auth_token", data.access_token)
        const currentUser = getUserFromToken(data.access_token)
        if (!currentUser) throw new Error("Invalid token received")
        setUser(currentUser)
        return currentUser
      },
      createInvestor: async (name, email, password) => {
        const response = await fetch(`${apiBaseUrl}/auth/signup`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, email, password }),
        })
        if (!response.ok) {
          const err = await response.json().catch(() => ({}))
          throw new Error(err.detail || "Failed to sign up")
        }
        const data = await response.json()
        localStorage.setItem("auth_token", data.access_token)
        const currentUser = getUserFromToken(data.access_token)
        setUser(currentUser)
      },
      resetPassword: async (email) => {
        // Mocked or implement later
        console.log("Reset password requested for", email)
      },
      signOut: async () => {
        localStorage.removeItem("auth_token")
        setUser(null)
      },
    }),
    [user, loading],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error("useAuth must be used inside AuthProvider")
  return value
}

export function useRole() {
  return useAuth().user?.role ?? null
}
