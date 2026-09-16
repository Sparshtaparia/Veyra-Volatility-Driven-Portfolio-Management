import { createContext, useContext, useMemo, useState } from "react"

export type Role = "INVESTOR" | "ADMIN"
export type CurrentUser = { id: string; name: string; email: string; role: Role }

type AuthContextValue = {
  user: CurrentUser | null
  signIn: (email: string, password: string) => CurrentUser | null
  createInvestor: (email: string) => CurrentUser
  signOut: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

// Development-only mock account. Replace with the backend auth endpoint before production.
const demoAdmin = { id: "demo-admin", name: "Veyra Admin", email: "admin@gmail.com", role: "ADMIN" as const }

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const value = useMemo<AuthContextValue>(() => ({
    user,
    signIn: (email, password) => {
      if (email.trim().toLowerCase() === demoAdmin.email && password === "admin") { setUser(demoAdmin); return demoAdmin }
      if (email.includes("@") && password.length > 0) { const investor = { id: "demo-investor", name: "Demo Investor", email, role: "INVESTOR" as const }; setUser(investor); return investor }
      return null
    },
    createInvestor: (email) => { const investor = { id: "demo-investor", name: "Demo Investor", email, role: "INVESTOR" as const }; setUser(investor); return investor },
    signOut: () => setUser(null),
  }), [user])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() { const value = useContext(AuthContext); if (!value) throw new Error("useAuth must be used inside AuthProvider"); return value }
export function useRole() { return useAuth().user?.role ?? null }
