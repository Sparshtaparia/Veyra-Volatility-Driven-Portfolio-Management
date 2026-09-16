import { createContext, useContext, useEffect, useMemo, useState } from "react"
import { isSupabaseConfigured, supabase } from "@/lib/supabase"

export type Role = "INVESTOR" | "ADMIN"
export type CurrentUser = { id: string; name: string; email: string; role: Role }
type AuthContextValue = { user: CurrentUser | null; loading: boolean; signIn: (email: string, password: string) => Promise<CurrentUser>; createInvestor: (email: string, password: string) => Promise<void>; resetPassword: (email: string) => Promise<void>; signOut: () => Promise<void> }
const AuthContext = createContext<AuthContextValue | null>(null)

function toCurrentUser(user: { id: string; email?: string; user_metadata?: Record<string, unknown> }): CurrentUser {
  const metadata = user.user_metadata ?? {}
  return { id: user.id, email: user.email ?? "", name: String(metadata.full_name ?? metadata.name ?? user.email?.split("@")[0] ?? "Investor"), role: metadata.role === "ADMIN" ? "ADMIN" : "INVESTOR" }
}
function requireConfiguration() { if (!isSupabaseConfigured) throw new Error("Supabase is not configured. Add VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY to frontend/.env.") }

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    if (!isSupabaseConfigured) { setLoading(false); return }
    supabase.auth.getSession().then(({ data }) => setUser(data.session?.user ? toCurrentUser(data.session.user) : null)).finally(() => setLoading(false))
    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => setUser(session?.user ? toCurrentUser(session.user) : null))
    return () => listener.subscription.unsubscribe()
  }, [])
  const value = useMemo<AuthContextValue>(() => ({
    user, loading,
    signIn: async (email, password) => { requireConfiguration(); const { data, error } = await supabase.auth.signInWithPassword({ email, password }); if (error || !data.user) throw new Error(error?.message ?? "Unable to sign in."); return toCurrentUser(data.user) },
    createInvestor: async (email, password) => { requireConfiguration(); const { error } = await supabase.auth.signUp({ email, password, options: { data: { role: "INVESTOR" } } }); if (error) throw new Error(error.message) },
    resetPassword: async (email) => { requireConfiguration(); const { error } = await supabase.auth.resetPasswordForEmail(email, { redirectTo: `${window.location.origin}/sign-in` }); if (error) throw new Error(error.message) },
    signOut: async () => { await supabase.auth.signOut(); setUser(null) },
  }), [user, loading])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
export function useAuth() { const value = useContext(AuthContext); if (!value) throw new Error("useAuth must be used inside AuthProvider"); return value }
export function useRole() { return useAuth().user?.role ?? null }
