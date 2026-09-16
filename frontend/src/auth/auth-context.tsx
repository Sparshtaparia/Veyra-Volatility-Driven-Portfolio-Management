import { createContext, useContext, useEffect, useMemo, useState } from "react"
import { supabase } from "@/lib/supabase"

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

function toCurrentUser(user: {
  id: string
  email?: string
  user_metadata?: Record<string, unknown>
}): CurrentUser {
  const metadata = user.user_metadata ?? {}
  return {
    id: user.id,
    email: user.email ?? "",
    name: String(metadata.full_name ?? metadata.name ?? user.email?.split("@")[0] ?? "Investor"),
    role: metadata.role === "ADMIN" ? "ADMIN" : "INVESTOR",
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supabase.auth
      .getSession()
      .then(({ data, error }) => {
        if (error) console.warn("Unable to restore Supabase session")
        setUser(data.session?.user ? toCurrentUser(data.session.user) : null)
      })
      .finally(() => setLoading(false))

    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ? toCurrentUser(session.user) : null)
      setLoading(false)
    })
    return () => listener.subscription.unsubscribe()
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      signIn: async (email, password) => {
        const { data, error } = await supabase.auth.signInWithPassword({ email, password })
        if (error) throw new Error(error.message)
        const { data: sessionData, error: sessionError } = await supabase.auth.getSession()
        if (sessionError || !sessionData.session || !data.user) {
          throw new Error(sessionError?.message ?? "Supabase did not create a session.")
        }
        const currentUser = toCurrentUser(data.user)
        setUser(currentUser)
        return currentUser
      },
      createInvestor: async (name, email, password) => {
        const { error } = await supabase.auth.signUp({
          email,
          password,
          options: { data: { full_name: name, role: "INVESTOR" } },
        })
        if (error) throw new Error(error.message)
      },
      resetPassword: async (email) => {
        const { error } = await supabase.auth.resetPasswordForEmail(email, {
          redirectTo: `${window.location.origin}/sign-in`,
        })
        if (error) throw new Error(error.message)
      },
      signOut: async () => {
        const { error } = await supabase.auth.signOut()
        if (error) throw new Error(error.message)
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
